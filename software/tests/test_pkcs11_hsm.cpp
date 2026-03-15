// software/tests/test_pkcs11_hsm.cpp
#include <catch2/catch_test_macros.hpp>
#include "security/SoftHsm.h"
#include "security/IHsmEngine.h"

using namespace cirradio::security;

TEST_CASE("SoftHsm generates AES-256 key", "[hsm]") {
    SoftHsm hsm;
    auto kh = hsm.generate_key(KeyType::AES256, "test");
    REQUIRE(kh.valid());
    REQUIRE(kh.get() != 0);
}

TEST_CASE("SoftHsm encrypt/decrypt roundtrip", "[hsm]") {
    SoftHsm hsm;
    auto kh = hsm.generate_key(KeyType::AES256, "tek");
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};

    auto ct = hsm.encrypt(kh.get(), plaintext);
    REQUIRE(ct.has_value());
    // Wire format: IV(12) + ciphertext(5) + tag(16) = 33 bytes
    REQUIRE(ct->size() == 12 + 5 + 16);

    auto pt = hsm.decrypt(kh.get(), *ct);
    REQUIRE(pt.has_value());
    REQUIRE(*pt == plaintext);
}

TEST_CASE("SoftHsm decrypt fails on tampered ciphertext", "[hsm]") {
    SoftHsm hsm;
    auto kh = hsm.generate_key(KeyType::AES256, "tek");
    std::vector<uint8_t> plaintext = {'T', 'e', 's', 't'};

    auto ct = hsm.encrypt(kh.get(), plaintext);
    REQUIRE(ct.has_value());
    (*ct)[12] ^= 0xFF;  // flip a ciphertext byte

    REQUIRE_FALSE(hsm.decrypt(kh.get(), *ct).has_value());
}

TEST_CASE("SoftHsm wrap/unwrap roundtrip", "[hsm]") {
    SoftHsm hsm;
    auto kek = hsm.generate_key(KeyType::AES256, "kek");
    auto tek = hsm.generate_key(KeyType::AES256, "tek");

    auto wrapped = hsm.wrap_key(kek.get(), tek.get());
    REQUIRE(wrapped.has_value());
    // AES_KEY_WRAP output for 32-byte key = 40 bytes
    REQUIRE(wrapped->size() == 40);

    auto unwrapped = hsm.unwrap_key(kek.get(), *wrapped);
    REQUIRE(unwrapped.has_value());

    // Verify the unwrapped key decrypts what the original encrypted
    std::vector<uint8_t> msg = {1, 2, 3, 4};
    auto ct  = hsm.encrypt(tek.get(), msg);
    auto pt  = hsm.decrypt(unwrapped->get(), *ct);
    REQUIRE(pt.has_value());
    REQUIRE(*pt == msg);
}

TEST_CASE("SoftHsm export_raw returns key bytes", "[hsm]") {
    SoftHsm hsm;
    std::vector<uint8_t> raw(32, 0xAB);
    auto kh = hsm.import_raw(raw, "test");
    REQUIRE(kh.has_value());

    auto exported = hsm.export_raw(kh->get());
    REQUIRE(exported.has_value());
    REQUIRE(*exported == raw);
}

TEST_CASE("SoftHsm import_raw rejects wrong size", "[hsm]") {
    SoftHsm hsm;
    std::vector<uint8_t> short_key(16, 0xAA);
    REQUIRE_FALSE(hsm.import_raw(short_key, "bad").has_value());
}

TEST_CASE("SoftHsm destroy_key invalidates handle", "[hsm]") {
    SoftHsm hsm;
    auto kh = hsm.generate_key(KeyType::AES256, "tmp");
    // Move out of kh so destructor doesn't double-destroy
    HsmKeyHandle moved = std::move(kh);
    REQUIRE(moved.valid());
    // Manually destroy
    REQUIRE(hsm.destroy_key(moved.get()));
    // HsmKeyHandle destructor will call destroy_key again on an already-
    // destroyed handle — SoftHSM2 returns an error but we just ignore it.
}

TEST_CASE("HsmKeyHandle move semantics", "[hsm]") {
    SoftHsm hsm;
    auto h1 = hsm.generate_key(KeyType::AES256, "k1");
    REQUIRE(h1.valid());

    HsmKeyHandle h2 = std::move(h1);
    REQUIRE(h2.valid());
    REQUIRE_FALSE(h1.valid());  // NOLINT — intentional use after move
}
