#include <catch2/catch_test_macros.hpp>
#include <vector>
#include <cstdint>

#include "tdma/Frame.h"
#include "tdma/SlotScheduler.h"

TEST_CASE("Frame has 20 slots with correct types", "[tdma]") {
    cirradio::tdma::Frame frame(0);
    REQUIRE(frame.slot_count() == 20);
    REQUIRE(frame.slot_type(0) == cirradio::tdma::SlotType::Beacon);
    for (uint8_t i = 1; i <= 14; ++i)
        REQUIRE(frame.slot_type(i) == cirradio::tdma::SlotType::Traffic);
    for (uint8_t i = 15; i <= 17; ++i)
        REQUIRE(frame.slot_type(i) == cirradio::tdma::SlotType::DataOnly);
    REQUIRE(frame.slot_type(18) == cirradio::tdma::SlotType::KeyMgmt);
    REQUIRE(frame.slot_type(19) == cirradio::tdma::SlotType::Discovery);
}

TEST_CASE("Node can claim and release traffic slots", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler(1);
    REQUIRE(scheduler.claim_slot(5));
    REQUIRE(scheduler.owner_of(5) == 1);
    REQUIRE_FALSE(scheduler.claim_slot(0));   // can't claim beacon
    REQUIRE_FALSE(scheduler.claim_slot(18));  // can't claim keymgmt
    REQUIRE_FALSE(scheduler.claim_slot(19));  // can't claim discovery
    scheduler.release_slot(5);
    REQUIRE(scheduler.owner_of(5) == 0);
}

TEST_CASE("Cannot claim already-claimed slot", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler_a(1);
    cirradio::tdma::SlotScheduler scheduler_b(2);
    // Simulate: scheduler_a claims slot 5, then scheduler_b's frame gets slot map applied
    scheduler_a.claim_slot(5);
    scheduler_b.apply_slot_map(scheduler_a.current_frame());
    REQUIRE_FALSE(scheduler_b.claim_slot(5));  // already taken
    REQUIRE(scheduler_b.claim_slot(6));  // this one is free
}

TEST_CASE("Beacon controller rotates", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler(1);
    std::vector<uint32_t> nodes = {1, 2, 3};
    REQUIRE(scheduler.beacon_controller(0, nodes) == 1);
    REQUIRE(scheduler.beacon_controller(1, nodes) == 2);
    REQUIRE(scheduler.beacon_controller(2, nodes) == 3);
    REQUIRE(scheduler.beacon_controller(3, nodes) == 1);  // wraps
}

TEST_CASE("my_voice_slot returns first claimed traffic slot", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler(1);
    REQUIRE_FALSE(scheduler.my_voice_slot().has_value());
    scheduler.claim_slot(7);
    scheduler.claim_slot(3);
    auto slot = scheduler.my_voice_slot();
    REQUIRE(slot.has_value());
    REQUIRE(*slot == 3);  // slot 3 is first traffic slot claimed
}

TEST_CASE("Frame number advances", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler(1);
    REQUIRE(scheduler.current_frame().frame_number() == 0);
    scheduler.advance_frame();
    REQUIRE(scheduler.current_frame().frame_number() == 1);
}
