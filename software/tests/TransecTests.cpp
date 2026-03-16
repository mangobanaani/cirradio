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

#include "transec/EmconManager.h"
#include "security/IAxiRegs.h"

// Minimal stub IAxiRegs for testing
struct StubAxiRegs : cirradio::security::IAxiRegs {
    uint32_t last_emcon_ctrl  = 2;
    int32_t  last_tx_power    = 0;
    bool     unlock_written   = false;

    void set_emcon_ctrl(uint32_t v) override    { last_emcon_ctrl = v; }
    void write_emcon_unlock() override          { unlock_written = true; }
    void set_tx_power(int32_t v) override       { last_tx_power = v; }
    uint32_t emcon_level() const override       { return last_emcon_ctrl & 0x3u; }
    void set_interleaver_depth(uint32_t) override {}
    void set_hop_rate(uint32_t) override {}
    void zeroize_fhek() override {}
    void halt_fpga_clocks() override {}
};

TEST_CASE("EmconManager starts at EMCON 2", "[transec][emcon]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    REQUIRE(em.current_level() == 2);
}

TEST_CASE("EmconManager increasing restriction is always permitted", "[transec][emcon]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    REQUIRE(em.set_level(1));
    REQUIRE(em.current_level() == 1);
    REQUIRE(em.set_level(0));
    REQUIRE(em.current_level() == 0);
}

TEST_CASE("EmconManager locked downgrade is rejected without unlock", "[transec][emcon]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    em.set_level(0);                   // silence
    REQUIRE(!em.set_level(2));         // downgrade rejected (locked)
    REQUIRE(em.current_level() == 0);
}

TEST_CASE("EmconManager force_emcon0 overrides any level", "[transec][emcon]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    em.force_emcon0();
    REQUIRE(em.current_level() == 0);
    REQUIRE((regs.last_emcon_ctrl & 0x3u) == 0);
}

TEST_CASE("EmconManager downgrade with unlock token succeeds", "[transec][emcon]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    em.set_level(0);
    bool ok = em.set_level(2, /*unlock=*/true);
    REQUIRE(ok);
    REQUIRE(em.current_level() == 2);
    REQUIRE(regs.unlock_written);
}

TEST_CASE("EmconManager EMCON1 writes reduced TX power", "[transec][emcon]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    em.set_level(1);
    // Power should be reduced (negative value = attenuation)
    REQUIRE(regs.last_tx_power < 3700); // less than normal power of 3700
}

#include "mgmt/CLIShell.h"

TEST_CASE("CLIShell emcon command changes EMCON level", "[transec][cli]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    cirradio::mgmt::CLIShell cli;
    cli.set_emcon_manager(&em);
    auto r = cli.execute("emcon 1");
    REQUIRE(r.success);
    REQUIRE(em.current_level() == 1);
}

TEST_CASE("CLIShell transec status reports current state", "[transec][cli]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::transec::EmconManager em(regs, cfg);
    cirradio::mgmt::CLIShell cli;
    cli.set_emcon_manager(&em);
    cli.set_transec_config(&cfg);
    auto r = cli.execute("transec status");
    REQUIRE(r.success);
    REQUIRE(r.output.find("EMCON level") != std::string::npos);
}

TEST_CASE("CLIShell transec set interleaver updates config", "[transec][cli]") {
    StubAxiRegs regs;
    cirradio::transec::TransecConfig cfg;
    cirradio::mgmt::CLIShell cli;
    cli.set_transec_config(&cfg);
    auto r = cli.execute("transec set interleaver 20");
    REQUIRE(r.success);
    REQUIRE(cfg.interleaver_depth() == 20);
}
