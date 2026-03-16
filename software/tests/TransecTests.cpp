#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include "transec/TransecConfig.h"

using namespace cirradio::transec;
using Catch::Approx;

TEST_CASE("TransecConfig default RSSI for unknown peer is -90 dBm", "[transec]") {
    TransecConfig cfg;
    REQUIRE(cfg.required_power_dbm(42) == Approx(-80.0f)); // -90 + 10 dB margin
}

TEST_CASE("TransecConfig updates peer RSSI and recomputes required power", "[transec]") {
    TransecConfig cfg;
    cfg.update_peer_rssi(1, -60.0f);
    REQUIRE(cfg.required_power_dbm(1) == Approx(-50.0f)); // -60 + 10 dB margin
}

TEST_CASE("TransecConfig evicts stale peers after 300 seconds", "[transec]") {
    TransecConfig cfg;
    cfg.update_peer_rssi(99, -55.0f);
    REQUIRE(cfg.required_power_dbm(99) == Approx(-45.0f));
    cfg.evict_stale_peers(301'000); // 301 seconds elapsed
    REQUIRE(cfg.required_power_dbm(99) == Approx(-80.0f)); // back to default
}

TEST_CASE("TransecConfig rejects more than 256 peers", "[transec]") {
    TransecConfig cfg;
    for (uint32_t i = 0; i < 256; ++i)
        cfg.update_peer_rssi(i, -70.0f);
    // 257th peer: should not crash, table stays at 256
    cfg.update_peer_rssi(256, -70.0f);
    REQUIRE(cfg.peer_count() <= 256);
}

TEST_CASE("TransecConfig interleaver depth clamped to 1-32", "[transec]") {
    TransecConfig cfg;
    cfg.set_interleaver_depth(50);
    REQUIRE(cfg.interleaver_depth() == 32);
    cfg.set_interleaver_depth(0);
    REQUIRE(cfg.interleaver_depth() == 1);
    cfg.set_interleaver_depth(10);
    REQUIRE(cfg.interleaver_depth() == 10);
}
