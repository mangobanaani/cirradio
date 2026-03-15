#include <catch2/catch_test_macros.hpp>
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/x509.h>
#include "security/SoftHsm.h"
#include "security/CryptoEngine.h"
#include "security/EcSign.h"

using namespace cirradio::security;

namespace {
struct EcKeyPair {
    std::vector<uint8_t> private_der, public_der;
    EcKeyPair() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
        REQUIRE(ctx); EVP_PKEY_keygen_init(ctx);
        EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_secp384r1);
        EVP_PKEY* pkey = nullptr; EVP_PKEY_keygen(ctx, &pkey); EVP_PKEY_CTX_free(ctx);
        int n = i2d_PrivateKey(pkey, nullptr);
        private_der.resize(static_cast<size_t>(n));
        unsigned char* p = private_der.data(); i2d_PrivateKey(pkey, &p);
        n = i2d_PUBKEY(pkey, nullptr);
        public_der.resize(static_cast<size_t>(n));
        p = public_der.data(); i2d_PUBKEY(pkey, &p);
        EVP_PKEY_free(pkey);
    }
};
}  // namespace

TEST_CASE("CryptoEngine encrypt/decrypt roundtrip", "[security]") {
    SoftHsm hsm;
    auto kh = hsm.import_raw(std::vector<uint8_t>(32, 0xAA), "test").value();
    CryptoEngine engine(hsm, kh.get());

    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};
    auto ct = engine.encrypt(plaintext);
    REQUIRE(ct.has_value());
    REQUIRE(ct->size() == 12 + 5 + 16);

    auto pt = engine.decrypt(*ct);
    REQUIRE(pt.has_value());
    REQUIRE(*pt == plaintext);
}

TEST_CASE("CryptoEngine tampered ciphertext detected", "[security]") {
    SoftHsm hsm;
    auto kh = hsm.import_raw(std::vector<uint8_t>(32, 0xAA), "test").value();
    CryptoEngine engine(hsm, kh.get());

    std::vector<uint8_t> pt2 = {'H', 'e', 'l', 'l', 'o'};
    auto ct = engine.encrypt(pt2);
    REQUIRE(ct.has_value());
    (*ct)[12] ^= 0xFF;
    REQUIRE_FALSE(engine.decrypt(*ct).has_value());
}

TEST_CASE("CryptoEngine wrong key fails decryption", "[security]") {
    SoftHsm hsm;
    auto kh_a = hsm.import_raw(std::vector<uint8_t>(32, 0xAA), "a").value();
    auto kh_b = hsm.import_raw(std::vector<uint8_t>(32, 0xBB), "b").value();
    CryptoEngine ea(hsm, kh_a.get()), eb(hsm, kh_b.get());

    std::vector<uint8_t> pt3 = {'H', 'e', 'l', 'l', 'o'};
    auto ct = ea.encrypt(pt3);
    REQUIRE(ct.has_value());
    REQUIRE_FALSE(eb.decrypt(*ct).has_value());
}

TEST_CASE("CryptoEngine wrap/unwrap roundtrip", "[security]") {
    SoftHsm hsm;
    auto kek_kh = hsm.import_raw(std::vector<uint8_t>(32, 0xCC), "kek").value();
    auto tek_kh = hsm.import_raw(std::vector<uint8_t>(32, 0xDD), "tek").value();
    CryptoEngine kek_engine(hsm, kek_kh.get());

    auto wrapped = kek_engine.wrap_key(tek_kh.get());
    REQUIRE(wrapped.has_value());

    auto unwrapped = kek_engine.unwrap_key(*wrapped);
    REQUIRE(unwrapped.has_value());

    auto raw = hsm.export_raw(unwrapped->get());
    REQUIRE(raw.has_value());
    REQUIRE(*raw == std::vector<uint8_t>(32, 0xDD));
}

TEST_CASE("CryptoEngine single-byte plaintext works", "[security]") {
    SoftHsm hsm;
    auto kh = hsm.import_raw(std::vector<uint8_t>(32, 0xAA), "k").value();
    CryptoEngine engine(hsm, kh.get());

    std::vector<uint8_t> small_pt = {0x42};
    auto ct = engine.encrypt(small_pt);
    REQUIRE(ct.has_value());
    REQUIRE(ct->size() == 12 + 1 + 16);

    auto pt = engine.decrypt(*ct);
    REQUIRE(pt.has_value());
    REQUIRE(*pt == small_pt);
}

TEST_CASE("ec_sign / ec_verify roundtrip", "[security]") {
    EcKeyPair kp;
    std::vector<uint8_t> data = {'T', 'e', 's', 't'};
    auto sig = ec_sign(kp.private_der, data);
    REQUIRE(sig.has_value());
    REQUIRE(ec_verify(kp.public_der, data, *sig));
}

TEST_CASE("ec_verify detects tampered data", "[security]") {
    EcKeyPair kp;
    std::vector<uint8_t> data = {'T', 'e', 's', 't'};
    auto sig = ec_sign(kp.private_der, data);
    REQUIRE(sig.has_value());
    data[0] ^= 0xFF;
    REQUIRE_FALSE(ec_verify(kp.public_der, data, *sig));
}
