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

    // TRANSEC control
    virtual void     set_emcon_ctrl(uint32_t value) = 0;
    virtual void     write_emcon_unlock() = 0;
    virtual void     set_tx_power(int32_t dBm_x100) = 0;
    virtual void     set_interleaver_depth(uint32_t depth) = 0;
    virtual void     set_hop_rate(uint32_t cycles_per_hop) = 0;
    virtual uint32_t emcon_level() const = 0;
};

// No-op stub for tests on macOS / non-hardware builds.
class NullAxiRegs : public IAxiRegs {
public:
    void zeroize_fhek() override {}
    void halt_fpga_clocks() override {}
    void     set_emcon_ctrl(uint32_t) override {}
    void     write_emcon_unlock() override {}
    void     set_tx_power(int32_t) override {}
    void     set_interleaver_depth(uint32_t) override {}
    void     set_hop_rate(uint32_t) override {}
    uint32_t emcon_level() const override { return 2; }
};

}  // namespace cirradio::security
