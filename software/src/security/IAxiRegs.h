// software/src/security/IAxiRegs.h
#pragma once
#include <cstdint>

namespace cirradio::security {

// Abstract AXI register interface for ZeroizeEngine.
// Production: implemented by AxiRegs (UIO mmap). Tests: NullAxiRegs.
class IAxiRegs {
public:
    virtual ~IAxiRegs() = default;
    // Writes 0 to FHEK_0..7, then asserts CTRL_FHEK_ZEROIZE.
    virtual void zeroize_fhek() = 0;
    // Writes CTRL_CLOCK_HALT to kill FPGA clock enables.
    virtual void halt_fpga_clocks() = 0;
};

// No-op stub for tests on macOS / non-hardware builds.
class NullAxiRegs : public IAxiRegs {
public:
    void zeroize_fhek() override {}
    void halt_fpga_clocks() override {}
};

}  // namespace cirradio::security
