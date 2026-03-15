// software/tests/test_key_manager.cpp
#include <catch2/catch_test_macros.hpp>
#include "security/SoftHsm.h"
#include "security/KeyManager.h"

using namespace cirradio::security;

TEST_CASE("KeyManager generate and export keys", "[security]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();
    REQUIRE(km.is_initialized());
    REQUIRE(km.export_fhek_for_fpga().size() == 32);
    REQUIRE(km.export_tek_for_distribution().size() == 32);
}

TEST_CASE("KeyManager encrypt/decrypt with TEK", "[security]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();

    std::vector<uint8_t> msg = {'H', 'i'};
    auto ct = km.encrypt_with_tek(msg);
    REQUIRE(ct.has_value());
    auto pt = km.decrypt_with_tek(*ct);
    REQUIRE(pt.has_value());
    REQUIRE(*pt == msg);
}

TEST_CASE("KeyManager TEK rotation produces different key", "[security]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();
    auto fhek1 = km.export_fhek_for_fpga();
    uint32_t epoch1 = km.key_epoch();
    km.rotate_tek();
    REQUIRE(km.key_epoch() > epoch1);
    REQUIRE(km.export_fhek_for_fpga() == fhek1);
}

TEST_CASE("KeyManager zeroize clears all keys", "[security]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();
    REQUIRE(km.is_initialized());
    km.zeroize();
    REQUIRE_FALSE(km.is_initialized());
}

TEST_CASE("KeyManager OTAR roundtrip", "[security]") {
    SoftHsm hsm;
    KeyManager sender(hsm), receiver(hsm);

    std::vector<uint8_t> shared_kek(32, 0x42);
    sender.set_kek_raw(shared_kek);
    receiver.set_kek_raw(shared_kek);

    sender.generate_tek();
    sender.generate_fhek();

    auto msg = sender.generate_otar_message();
    REQUIRE(!msg.wrapped_tek.empty());
    REQUIRE(!msg.wrapped_fhek.empty());

    REQUIRE(receiver.process_otar_message(msg));

    std::vector<uint8_t> payload = {1, 2, 3};
    auto ct = sender.encrypt_with_tek(payload);
    auto pt = receiver.decrypt_with_tek(*ct);
    REQUIRE(pt.has_value());
    REQUIRE(*pt == payload);
}

TEST_CASE("KeyManager OTAR rejects stale epoch", "[security]") {
    SoftHsm hsm;
    KeyManager km(hsm), receiver(hsm);
    std::vector<uint8_t> kek(32, 0x42);
    km.set_kek_raw(kek);
    receiver.set_kek_raw(kek);
    km.generate_tek(); km.generate_fhek();
    auto msg = km.generate_otar_message();
    REQUIRE(receiver.process_otar_message(msg));
    REQUIRE_FALSE(receiver.process_otar_message(msg));
}

TEST_CASE("KeyManager set_tek_raw and set_fhek_raw", "[security]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    km.initialize_kek();
    km.set_tek_raw(std::vector<uint8_t>(32, 0xAA));
    km.set_fhek_raw(std::vector<uint8_t>(32, 0xBB));
    REQUIRE(km.is_initialized());
    REQUIRE(km.export_fhek_for_fpga() == std::vector<uint8_t>(32, 0xBB));
}
