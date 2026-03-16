// software/tests/test_tamper.cpp
#include <catch2/catch_test_macros.hpp>
#include "security/SoftHsm.h"
#include "security/KeyManager.h"
#include "security/ZeroizeEngine.h"
#include "security/SecurityManager.h"
#include "security/IAxiRegs.h"

using namespace cirradio::security;

class RecordingAxiRegs : public IAxiRegs {
public:
    int fhek_zeroize_calls = 0;
    int clock_halt_calls   = 0;
    void zeroize_fhek()     override { ++fhek_zeroize_calls; }
    void halt_fpga_clocks() override { ++clock_halt_calls; }
};

static void init_km(KeyManager& km) {
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();
}

TEST_CASE("ZeroizeEngine clears FHEK registers", "[security][zeroize]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    init_km(km);
    RecordingAxiRegs axi;

    ZeroizeEngine ze(km, hsm, axi, 0);
    ZeroizeResult r = ze.run();

    REQUIRE(r.step1_fpga_ok);
    REQUIRE(axi.fhek_zeroize_calls == 1);
    REQUIRE(axi.clock_halt_calls   == 1);
}

TEST_CASE("ZeroizeEngine destroys HSM keys", "[security][zeroize]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    init_km(km);
    RecordingAxiRegs axi;

    REQUIRE(km.is_initialized());

    ZeroizeEngine ze(km, hsm, axi, 0);
    ZeroizeResult r = ze.run();

    REQUIRE(r.step2_hsm_ok);
    REQUIRE_FALSE(km.is_initialized());
}

TEST_CASE("ZeroizeEngine runs all 5 steps", "[security][zeroize]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    init_km(km);
    RecordingAxiRegs axi;

    ZeroizeEngine ze(km, hsm, axi, 0);
    ZeroizeResult r = ze.run();

    REQUIRE(r.step1_fpga_ok);
    REQUIRE(r.step2_hsm_ok);
    REQUIRE(r.step3_ram_ok);
    REQUIRE(r.step4_audit_ok);
    REQUIRE(ze.triggered());
}

TEST_CASE("ZeroizeEngine run twice does not crash", "[security][zeroize]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    init_km(km);
    RecordingAxiRegs axi;

    ZeroizeEngine ze(km, hsm, axi, 0);
    ze.run();
    REQUIRE_NOTHROW(ze.run());
}

TEST_CASE("SecurityManager zeroize_immediate is idempotent", "[security][secmgr]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    init_km(km);
    RecordingAxiRegs axi;

    SecurityManager sm(km, hsm, axi, 0);

    REQUIRE_FALSE(sm.is_zeroized());
    sm.zeroize_immediate();
    REQUIRE(sm.is_zeroized());

    REQUIRE_NOTHROW(sm.zeroize_immediate());
    REQUIRE(sm.is_zeroized());
}

TEST_CASE("SecurityManager construction succeeds with NullAxiRegs", "[security][secmgr]") {
    SoftHsm hsm;
    KeyManager km(hsm);
    init_km(km);
    NullAxiRegs axi;

    REQUIRE_NOTHROW(SecurityManager(km, hsm, axi, 0));
}
