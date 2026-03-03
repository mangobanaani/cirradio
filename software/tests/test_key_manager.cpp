#include <catch2/catch_test_macros.hpp>
#include <vector>
#include <cstdint>

#include "security/KeyManager.h"

using namespace cirradio::security;

TEST_CASE("KeyManager manages key hierarchy", "[security]") {
    KeyManager km;
    km.initialize_kek();
    auto tek = km.generate_tek();
    REQUIRE(tek.size() == 32);
    auto fhek = km.generate_fhek();
    REQUIRE(fhek.size() == 32);
    REQUIRE(km.current_tek() == tek);
    REQUIRE(km.current_fhek() == fhek);
    REQUIRE(km.is_initialized());
}

TEST_CASE("TEK rotation produces new key", "[security]") {
    KeyManager km;
    km.initialize_kek();
    auto tek1 = km.generate_tek();
    auto epoch1 = km.key_epoch();
    auto tek2 = km.rotate_tek();
    REQUIRE(tek1 != tek2);
    REQUIRE(km.current_tek() == tek2);
    REQUIRE(km.key_epoch() > epoch1);
}

TEST_CASE("Zeroization clears all keys", "[security]") {
    KeyManager km;
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();
    REQUIRE(km.is_initialized());

    km.zeroize();
    REQUIRE_FALSE(km.is_initialized());
    REQUIRE_THROWS(km.current_tek());
    REQUIRE_THROWS(km.current_fhek());
}

TEST_CASE("OTAR message roundtrip", "[security]") {
    // Sender and receiver share the same KEK
    KeyManager sender;
    KeyManager receiver;

    std::vector<uint8_t> shared_kek(32, 0x42);
    sender.set_kek(shared_kek);
    receiver.set_kek(shared_kek);

    sender.generate_tek();
    sender.generate_fhek();

    auto msg = sender.generate_otar_message();
    REQUIRE(msg.wrapped_tek.size() > 0);
    REQUIRE(msg.wrapped_fhek.size() > 0);

    REQUIRE(receiver.process_otar_message(msg));
    REQUIRE(receiver.current_tek() == sender.current_tek());
    REQUIRE(receiver.current_fhek() == sender.current_fhek());
}

TEST_CASE("OTAR rejects stale epoch", "[security]") {
    KeyManager km;
    std::vector<uint8_t> kek(32, 0x42);
    km.set_kek(kek);
    km.generate_tek();
    km.generate_fhek();

    auto msg = km.generate_otar_message();
    // Process it once - should succeed
    KeyManager receiver;
    receiver.set_kek(kek);
    REQUIRE(receiver.process_otar_message(msg));

    // Process same message again - stale epoch, should reject
    REQUIRE_FALSE(receiver.process_otar_message(msg));
}

TEST_CASE("set_tek and set_fhek for net join", "[security]") {
    KeyManager km;
    km.initialize_kek();
    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    km.set_tek(tek);
    km.set_fhek(fhek);
    REQUIRE(km.current_tek() == tek);
    REQUIRE(km.current_fhek() == fhek);
}
