#include <catch2/catch_test_macros.hpp>
#include <vector>
#include <cstdint>

#include "fhss/HopSequencer.h"

TEST_CASE("Hop sequence is deterministic given same key and frame", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xAA);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);
    auto freq_a = seq.get_hop_frequency(0, 100);
    auto freq_b = seq.get_hop_frequency(0, 100);
    REQUIRE(freq_a == freq_b);
    auto freq_c = seq.get_hop_frequency(1, 100);
    REQUIRE(freq_a != freq_c);  // different slot = likely different freq
}

TEST_CASE("Hop frequencies stay within band", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xBB);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);
    for (uint32_t frame = 0; frame < 1000; ++frame) {
        for (uint8_t slot = 0; slot < 20; ++slot) {
            auto freq = seq.get_hop_frequency(slot, frame);
            REQUIRE(freq >= 225'000'000);
            REQUIRE(freq <= 512'000'000);
        }
    }
}

TEST_CASE("Different keys produce different sequences", "[fhss]") {
    std::vector<uint8_t> key_a(32, 0xAA);
    std::vector<uint8_t> key_b(32, 0xBB);
    cirradio::fhss::HopSequencer seq_a(key_a, 225'000'000, 512'000'000, 1'000'000);
    cirradio::fhss::HopSequencer seq_b(key_b, 225'000'000, 512'000'000, 1'000'000);
    bool any_different = false;
    for (uint32_t f = 0; f < 100; ++f) {
        if (seq_a.get_hop_frequency(0, f) != seq_b.get_hop_frequency(0, f)) {
            any_different = true;
            break;
        }
    }
    REQUIRE(any_different);
}

TEST_CASE("Blacklisted frequencies are skipped", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xCC);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);
    auto original = seq.get_hop_frequency(0, 0);
    seq.blacklist_frequency(original);
    auto replacement = seq.get_hop_frequency(0, 0);
    REQUIRE(replacement != original);
    REQUIRE(replacement >= 225'000'000);
    REQUIRE(replacement <= 512'000'000);
}

TEST_CASE("Clear blacklist restores original frequency", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xDD);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);
    auto original = seq.get_hop_frequency(0, 0);
    seq.blacklist_frequency(original);
    REQUIRE(seq.get_hop_frequency(0, 0) != original);
    seq.clear_blacklist();
    REQUIRE(seq.get_hop_frequency(0, 0) == original);
}

TEST_CASE("num_channels returns correct count", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xEE);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);
    // (512 - 225) = 287 channels at 1 MHz spacing
    REQUIRE(seq.num_channels() == 287);
}
