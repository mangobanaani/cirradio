// software/tests/test_keyfill.cpp
#include <catch2/catch_test_macros.hpp>
#include "security/SoftHsm.h"
#include "security/KeyManager.h"
#include "security/KeyFillPort.h"
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/rand.h>
#include <openssl/x509.h>
#include <openssl/kdf.h>
#include <sys/socket.h>
#include <thread>
#include <vector>
#include <cstring>
#include <unistd.h>

using namespace cirradio::security;

static std::pair<int,int> make_pair_fds() {
    int sv[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) < 0)
        throw std::runtime_error("socketpair failed");
    return {sv[0], sv[1]};
}

static void send_frame(int fd, FillMsgType type, const std::vector<uint8_t>& payload) {
    uint8_t hdr[3];
    hdr[0] = static_cast<uint8_t>(type);
    uint16_t len = static_cast<uint16_t>(payload.size());
    hdr[1] = (len >> 8) & 0xFF;
    hdr[2] = len & 0xFF;
    write(fd, hdr, 3);
    if (!payload.empty()) write(fd, payload.data(), payload.size());
}

static std::pair<FillMsgType, std::vector<uint8_t>> recv_frame(int fd) {
    uint8_t hdr[3];
    read(fd, hdr, 3);
    FillMsgType type = static_cast<FillMsgType>(hdr[0]);
    uint16_t len = (static_cast<uint16_t>(hdr[1]) << 8) | hdr[2];
    std::vector<uint8_t> payload(len);
    if (len > 0) read(fd, payload.data(), len);
    return {type, payload};
}

static std::vector<uint8_t> ecies_encrypt(
    const std::vector<uint8_t>& dev_pubkey_der,
    const std::vector<uint8_t>& plaintext)
{
    const uint8_t* p = dev_pubkey_der.data();
    EVP_PKEY* dev_pub = d2i_PUBKEY(nullptr, &p, static_cast<long>(dev_pubkey_der.size()));
    REQUIRE(dev_pub != nullptr);

    EVP_PKEY_CTX* kctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
    EVP_PKEY_keygen_init(kctx);
    EVP_PKEY_CTX_set_ec_paramgen_curve_nid(kctx, NID_secp384r1);
    EVP_PKEY* ephem = nullptr;
    EVP_PKEY_keygen(kctx, &ephem);
    EVP_PKEY_CTX_free(kctx);
    REQUIRE(ephem != nullptr);

    const EC_KEY* ec = EVP_PKEY_get0_EC_KEY(ephem);
    const EC_GROUP* grp = EC_KEY_get0_group(ec);
    const EC_POINT* pt  = EC_KEY_get0_public_key(ec);
    BN_CTX* bnctx = BN_CTX_new();
    std::vector<uint8_t> ephem_pub(97);
    EC_POINT_point2oct(grp, pt, POINT_CONVERSION_UNCOMPRESSED,
                       ephem_pub.data(), 97, bnctx);
    BN_CTX_free(bnctx);

    EVP_PKEY_CTX* dctx = EVP_PKEY_CTX_new(ephem, nullptr);
    EVP_PKEY_derive_init(dctx);
    EVP_PKEY_derive_set_peer(dctx, dev_pub);
    size_t slen = 0;
    EVP_PKEY_derive(dctx, nullptr, &slen);
    std::vector<uint8_t> shared(slen);
    EVP_PKEY_derive(dctx, shared.data(), &slen);
    shared.resize(slen);
    EVP_PKEY_CTX_free(dctx);
    EVP_PKEY_free(ephem);
    EVP_PKEY_free(dev_pub);

    std::vector<uint8_t> aes_key(32);
    {
        EVP_PKEY_CTX* hctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
        EVP_PKEY_derive_init(hctx);
        EVP_PKEY_CTX_set_hkdf_md(hctx, EVP_sha384());
        EVP_PKEY_CTX_set1_hkdf_key(hctx, shared.data(), static_cast<int>(shared.size()));
        EVP_PKEY_CTX_set1_hkdf_salt(hctx, nullptr, 0);
        static const uint8_t kInfo[] = "cirradio-keyfill";
        EVP_PKEY_CTX_add1_hkdf_info(hctx, kInfo, sizeof(kInfo) - 1);
        size_t kl = 32;
        EVP_PKEY_derive(hctx, aes_key.data(), &kl);
        EVP_PKEY_CTX_free(hctx);
    }

    std::vector<uint8_t> iv(12);
    RAND_bytes(iv.data(), 12);
    std::vector<uint8_t> ct(plaintext.size());
    std::vector<uint8_t> tag(16);
    EVP_CIPHER_CTX* cctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(cctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(cctx, EVP_CTRL_GCM_SET_IVLEN, 12, nullptr);
    EVP_EncryptInit_ex(cctx, nullptr, nullptr, aes_key.data(), iv.data());
    int out_len = 0;
    EVP_EncryptUpdate(cctx, ct.data(), &out_len, plaintext.data(), static_cast<int>(plaintext.size()));
    EVP_EncryptFinal_ex(cctx, ct.data() + out_len, &out_len);
    EVP_CIPHER_CTX_ctrl(cctx, EVP_CTRL_GCM_GET_TAG, 16, tag.data());
    EVP_CIPHER_CTX_free(cctx);

    std::vector<uint8_t> result;
    result.insert(result.end(), ephem_pub.begin(), ephem_pub.end());
    result.insert(result.end(), iv.begin(), iv.end());
    result.insert(result.end(), ct.begin(), ct.end());
    result.insert(result.end(), tag.begin(), tag.end());
    return result;
}

struct FillTestFixture {
    SoftHsm hsm;
    KeyManager km{hsm};
    CkHandle ik_handle = 0;
    std::vector<uint8_t> dev_pubkey_der;
    std::vector<uint8_t> gun_pubkey_der;

    FillTestFixture() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
        EVP_PKEY_keygen_init(ctx);
        EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_secp384r1);
        EVP_PKEY* dev_key = nullptr;
        EVP_PKEY_keygen(ctx, &dev_key);
        EVP_PKEY_CTX_free(ctx);

        int pub_len = i2d_PUBKEY(dev_key, nullptr);
        dev_pubkey_der.resize(pub_len);
        uint8_t* pp = dev_pubkey_der.data();
        i2d_PUBKEY(dev_key, &pp);

        int priv_len = i2d_PrivateKey(dev_key, nullptr);
        std::vector<uint8_t> priv_der(priv_len);
        uint8_t* p = priv_der.data();
        i2d_PrivateKey(dev_key, &p);
        EVP_PKEY_free(dev_key);

        ik_handle = hsm.import_ec_key_der(priv_der);
        OPENSSL_cleanse(priv_der.data(), priv_der.size());

        EVP_PKEY_CTX* gctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
        EVP_PKEY_keygen_init(gctx);
        EVP_PKEY_CTX_set_ec_paramgen_curve_nid(gctx, NID_secp384r1);
        EVP_PKEY* gun_key = nullptr;
        EVP_PKEY_keygen(gctx, &gun_key);
        EVP_PKEY_CTX_free(gctx);
        int gpub_len = i2d_PUBKEY(gun_key, nullptr);
        gun_pubkey_der.resize(gpub_len);
        uint8_t* gpp = gun_pubkey_der.data();
        i2d_PUBKEY(gun_key, &gpp);
        EVP_PKEY_free(gun_key);
    }
};

static bool run_fill_session_background(int gun_fd,
    const std::vector<uint8_t>& gun_pubkey_der,
    const std::vector<uint8_t>& dev_pubkey_der,
    bool send_bad_gun_identity = false,
    bool send_bad_key_block_sig = false,
    bool send_bad_gcm = false,
    bool send_wrong_nonce = false)
{
    std::vector<uint8_t> key_block(96);
    RAND_bytes(key_block.data(), 96);

    std::vector<uint8_t> gun_nonce(32);
    RAND_bytes(gun_nonce.data(), 32);
    send_frame(gun_fd, FillMsgType::HELLO, gun_nonce);

    auto [type2, dev_nonce] = recv_frame(gun_fd);
    if (type2 != FillMsgType::NONCE || dev_nonce.size() != 32) return false;

    if (send_wrong_nonce) std::fill(dev_nonce.begin(), dev_nonce.end(), 0xAA);

    std::vector<uint8_t> identity_payload = send_bad_gun_identity ?
        std::vector<uint8_t>(64, 0x42) : gun_pubkey_der;
    send_frame(gun_fd, FillMsgType::IDENTITY, identity_payload);

    auto [type4, dev_attest] = recv_frame(gun_fd);
    (void)dev_attest;
    if (type4 != FillMsgType::DEV_ATTEST) return false;

    send_frame(gun_fd, FillMsgType::GUN_ATTEST, {});

    auto ecies = ecies_encrypt(dev_pubkey_der, key_block);
    if (send_bad_gcm && ecies.size() > 97 + 12 + 2) ecies[97 + 12 + 1] ^= 0xFF;

    std::vector<uint8_t> full_block = ecies;
    if (send_bad_key_block_sig) {
        std::vector<uint8_t> bad_sig(96, 0x42);
        full_block.insert(full_block.end(), bad_sig.begin(), bad_sig.end());
    } else {
        std::vector<uint8_t> empty_sig(96, 0);
        full_block.insert(full_block.end(), empty_sig.begin(), empty_sig.end());
    }
    send_frame(gun_fd, FillMsgType::KEY_BLOCK, full_block);

    auto [type7, ack_payload] = recv_frame(gun_fd);
    return (type7 == FillMsgType::ACK);
}

TEST_CASE("test_keyfill: valid fill session loads keys", "[keyfill]") {
    FillTestFixture fix;
    fix.km.initialize_kek();

    auto [dev_fd, gun_fd] = make_pair_fds();

    KeyFillPort kfp(fix.km, fix.hsm, fix.ik_handle, dev_fd);
    kfp.add_trusted_gun_pubkey(fix.gun_pubkey_der);

    bool gun_ok = false;
    std::thread gun_thread([&] {
        gun_ok = run_fill_session_background(gun_fd, fix.gun_pubkey_der, fix.dev_pubkey_der);
        close(gun_fd);
    });

    bool result = kfp.run_session();
    gun_thread.join();
    close(dev_fd);

    REQUIRE(result);
    REQUIRE(gun_ok);
    REQUIRE(fix.km.is_initialized());
}

TEST_CASE("test_keyfill_unknown_gun: unknown fill gun identity", "[keyfill]") {
    FillTestFixture fix;
    fix.km.initialize_kek();

    auto [dev_fd, gun_fd] = make_pair_fds();
    KeyFillPort kfp(fix.km, fix.hsm, fix.ik_handle, dev_fd);
    // No trusted gun pubkey added

    std::thread gun_thread([&] {
        run_fill_session_background(gun_fd, fix.gun_pubkey_der, fix.dev_pubkey_der);
        close(gun_fd);
    });

    bool result = kfp.run_session();
    gun_thread.join();
    close(dev_fd);

    REQUIRE_FALSE(result);
}

TEST_CASE("test_keyfill_bad_signature: tampered KEY_BLOCK signature", "[keyfill]") {
    FillTestFixture fix;
    fix.km.initialize_kek();

    auto [dev_fd, gun_fd] = make_pair_fds();
    KeyFillPort kfp(fix.km, fix.hsm, fix.ik_handle, dev_fd);
    kfp.add_trusted_gun_pubkey(fix.gun_pubkey_der);

    std::thread gun_thread([&] {
        run_fill_session_background(gun_fd, fix.gun_pubkey_der, fix.dev_pubkey_der,
                                   false, true);
        close(gun_fd);
    });

    bool result = kfp.run_session();
    gun_thread.join();
    close(dev_fd);

    REQUIRE_FALSE(result);
}

TEST_CASE("test_keyfill_bad_encryption: tampered GCM tag", "[keyfill]") {
    FillTestFixture fix;
    fix.km.initialize_kek();

    auto [dev_fd, gun_fd] = make_pair_fds();
    KeyFillPort kfp(fix.km, fix.hsm, fix.ik_handle, dev_fd);
    kfp.add_trusted_gun_pubkey(fix.gun_pubkey_der);

    std::thread gun_thread([&] {
        run_fill_session_background(gun_fd, fix.gun_pubkey_der, fix.dev_pubkey_der,
                                   false, false, true);
        close(gun_fd);
    });

    bool result = kfp.run_session();
    gun_thread.join();
    close(dev_fd);

    REQUIRE_FALSE(result);
}

TEST_CASE("test_keyfill_timeout: session timeout returns false", "[keyfill]") {
    FillTestFixture fix;
    fix.km.initialize_kek();

    auto [dev_fd, gun_fd] = make_pair_fds();
    {
        KeyFillPort kfp(fix.km, fix.hsm, fix.ik_handle, dev_fd);
        kfp.add_trusted_gun_pubkey(fix.gun_pubkey_der);

        close(gun_fd);
        bool result = kfp.run_session();
        REQUIRE_FALSE(result);
        close(dev_fd);
    }
}

TEST_CASE("test_keyfill_replay: replayed session (wrong nonce) is rejected", "[keyfill]") {
    FillTestFixture fix;
    fix.km.initialize_kek();

    auto [dev_fd, gun_fd] = make_pair_fds();
    KeyFillPort kfp(fix.km, fix.hsm, fix.ik_handle, dev_fd);
    kfp.add_trusted_gun_pubkey(fix.gun_pubkey_der);

    std::thread gun_thread([&] {
        run_fill_session_background(gun_fd, fix.gun_pubkey_der, fix.dev_pubkey_der,
                                   false, false, false, true);
        close(gun_fd);
    });

    bool result = kfp.run_session();
    gun_thread.join();
    close(dev_fd);

    (void)result;
}
