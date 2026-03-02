#include <catch2/catch_test_macros.hpp>
#include <memory>
#include <vector>
#include <cstdint>
#include <algorithm>
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/x509.h>

#include "security/CryptoEngine.h"
#include "security/SoftCryptoHal.h"

using namespace cirradio::security;

namespace {

// Helper: generate a 32-byte key filled with a given byte value
std::vector<uint8_t> make_key(uint8_t fill = 0xAA) {
    return std::vector<uint8_t>(32, fill);
}

// Helper: serialize EVP_PKEY private key to DER
std::vector<uint8_t> private_key_to_der(EVP_PKEY* pkey) {
    int len = i2d_PrivateKey(pkey, nullptr);
    if (len <= 0) return {};
    std::vector<uint8_t> der(static_cast<size_t>(len));
    unsigned char* p = der.data();
    i2d_PrivateKey(pkey, &p);
    return der;
}

// Helper: serialize EVP_PKEY public key to DER
std::vector<uint8_t> public_key_to_der(EVP_PKEY* pkey) {
    int len = i2d_PUBKEY(pkey, nullptr);
    if (len <= 0) return {};
    std::vector<uint8_t> der(static_cast<size_t>(len));
    unsigned char* p = der.data();
    i2d_PUBKEY(pkey, &p);
    return der;
}

// RAII wrapper for test key pair generation
struct EcKeyPair {
    EVP_PKEY* pkey = nullptr;
    std::vector<uint8_t> private_der;
    std::vector<uint8_t> public_der;

    EcKeyPair() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
        REQUIRE(ctx != nullptr);
        REQUIRE(EVP_PKEY_keygen_init(ctx) == 1);
        REQUIRE(EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_secp384r1) == 1);
        REQUIRE(EVP_PKEY_keygen(ctx, &pkey) == 1);
        EVP_PKEY_CTX_free(ctx);

        private_der = private_key_to_der(pkey);
        public_der = public_key_to_der(pkey);
        REQUIRE(!private_der.empty());
        REQUIRE(!public_der.empty());
    }

    ~EcKeyPair() {
        EVP_PKEY_free(pkey);
    }

    EcKeyPair(const EcKeyPair&) = delete;
    EcKeyPair& operator=(const EcKeyPair&) = delete;
};

}  // namespace

TEST_CASE("AES-256-GCM encrypt then decrypt roundtrip", "[security]") {
    CryptoEngine engine;
    auto key = make_key();
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};

    auto encrypted = engine.encrypt(key, plaintext);
    REQUIRE(encrypted.has_value());

    // Encrypted output should be IV(12) + ciphertext(5) + tag(16) = 33 bytes
    REQUIRE(encrypted->size() == 12 + 5 + 16);

    auto decrypted = engine.decrypt(key, *encrypted);
    REQUIRE(decrypted.has_value());
    REQUIRE(*decrypted == plaintext);
}

TEST_CASE("Tampered ciphertext detected", "[security]") {
    CryptoEngine engine;
    auto key = make_key();
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};

    auto encrypted = engine.encrypt(key, plaintext);
    REQUIRE(encrypted.has_value());

    // Flip a byte in the ciphertext portion (after the 12-byte IV)
    (*encrypted)[12] ^= 0xFF;

    auto decrypted = engine.decrypt(key, *encrypted);
    REQUIRE_FALSE(decrypted.has_value());
}

TEST_CASE("Wrong key fails decryption", "[security]") {
    CryptoEngine engine;
    auto key_a = make_key(0xAA);
    auto key_b = make_key(0xBB);
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};

    auto encrypted = engine.encrypt(key_a, plaintext);
    REQUIRE(encrypted.has_value());

    auto decrypted = engine.decrypt(key_b, *encrypted);
    REQUIRE_FALSE(decrypted.has_value());
}

TEST_CASE("KEK wraps and unwraps TEK", "[security]") {
    CryptoEngine engine;
    auto kek = make_key(0xCC);
    auto tek = make_key(0xDD);  // 32-byte traffic encryption key

    auto wrapped = engine.wrap_key(kek, tek);
    REQUIRE(wrapped.has_value());

    auto unwrapped = engine.unwrap_key(kek, *wrapped);
    REQUIRE(unwrapped.has_value());
    REQUIRE(*unwrapped == tek);
}

TEST_CASE("Invalid key size rejected", "[security]") {
    CryptoEngine engine;
    std::vector<uint8_t> short_key(16, 0xAA);  // 16 bytes, not 32
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};

    auto encrypted = engine.encrypt(short_key, plaintext);
    REQUIRE_FALSE(encrypted.has_value());
}

TEST_CASE("Empty plaintext works", "[security]") {
    CryptoEngine engine;
    auto key = make_key();
    std::vector<uint8_t> plaintext;  // empty

    auto encrypted = engine.encrypt(key, plaintext);
    REQUIRE(encrypted.has_value());

    // Should be IV(12) + ciphertext(0) + tag(16) = 28 bytes
    REQUIRE(encrypted->size() == 12 + 0 + 16);

    auto decrypted = engine.decrypt(key, *encrypted);
    REQUIRE(decrypted.has_value());
    REQUIRE(decrypted->empty());
}

TEST_CASE("ECDSA sign and verify roundtrip", "[security]") {
    EcKeyPair kp;
    SoftCryptoHal hal;

    std::vector<uint8_t> data = {'T', 'e', 's', 't', ' ', 'd', 'a', 't', 'a'};

    auto signature = hal.sign(kp.private_der, data);
    REQUIRE(signature.has_value());
    REQUIRE(!signature->empty());

    REQUIRE(hal.verify(kp.public_der, data, *signature));
}

TEST_CASE("ECDSA verify detects tampered data", "[security]") {
    EcKeyPair kp;
    SoftCryptoHal hal;

    std::vector<uint8_t> data = {'T', 'e', 's', 't', ' ', 'd', 'a', 't', 'a'};

    auto signature = hal.sign(kp.private_der, data);
    REQUIRE(signature.has_value());

    // Tamper with the data
    data[0] ^= 0xFF;

    REQUIRE_FALSE(hal.verify(kp.public_der, data, *signature));
}
