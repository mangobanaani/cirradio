// software/embedded/drivers/axi_regs.hpp
// AXI register map — C++ side. Synced with fpga/src/axi_regs/regs.svh.
// DO NOT EDIT without updating regs.svh and re-running check_regmap.py.
#pragma once
#include <cstdint>
#include <cstddef>
#include <span>

namespace cirradio::drivers {

// Write registers (PS → PL)
constexpr uint32_t REG_FHEK_0          = 0x000;
constexpr uint32_t REG_FHEK_1          = 0x004;
constexpr uint32_t REG_FHEK_2          = 0x008;
constexpr uint32_t REG_FHEK_3          = 0x00C;
constexpr uint32_t REG_FHEK_4          = 0x010;
constexpr uint32_t REG_FHEK_5          = 0x014;
constexpr uint32_t REG_FHEK_6          = 0x018;
constexpr uint32_t REG_FHEK_7          = 0x01C;
constexpr uint32_t REG_BLACKLIST_BASE  = 0x020;
constexpr uint32_t REG_BLACKLIST_COUNT = 20;
constexpr uint32_t REG_SLOT_BITMAP     = 0x070;
constexpr uint32_t REG_TX_POWER        = 0x074;
constexpr uint32_t REG_CONTROL         = 0x07C;
constexpr uint32_t CTRL_FHEK_ZEROIZE   = 0x00000001u; // bit 0

constexpr uint32_t CTRL_CLOCK_HALT     = 0x00000002u; // bit 1

// TRANSEC registers (0x100–0x114)
constexpr uint32_t REG_HOP_RATE          = 0x100;
constexpr uint32_t REG_BLACKLIST_SIZE    = 0x104;
constexpr uint32_t REG_INTERLEAVER_DEPTH = 0x108;
constexpr uint32_t REG_PA_RAMP_STEPS     = 0x10C;
constexpr uint32_t REG_EMCON_CTRL        = 0x110;
constexpr uint32_t REG_EMCON_UNLOCK      = 0x114;

// Read registers (PL → PS)
constexpr uint32_t REG_STATUS          = 0x080;
constexpr uint32_t STATUS_HOP_LOCK     = (1u << 0);
constexpr uint32_t STATUS_GPS_HOLDOVER = (1u << 1);
constexpr uint32_t REG_RSSI            = 0x084;
constexpr uint32_t REG_HOP_COUNTER     = 0x088;
constexpr uint32_t REG_ERR_BASE        = 0x08C;

// Reset values
constexpr uint32_t REG_STATUS_RESET      = 0x00000002u;
constexpr uint32_t REG_RSSI_RESET        = 0xFFFF8300u;
constexpr uint32_t REG_TX_POWER_RESET    = 0x00000000u;
constexpr uint32_t REG_SLOT_BITMAP_RESET = 0x00000000u;

class AxiRegs {
public:
    static constexpr size_t PAGE_SIZE = 4096;
    explicit AxiRegs(const char* uio_dev = "/dev/uio0");
    ~AxiRegs();
    AxiRegs(const AxiRegs&) = delete;
    AxiRegs& operator=(const AxiRegs&) = delete;

    void set_fhek(std::span<const uint8_t> fhek);
    void set_blacklist(std::span<const uint32_t> freqs_khz);
    void set_slot_bitmap(uint32_t bitmap);
    void set_tx_power(int32_t dBm_x100);
    void zeroize_fhek();      // writes 0 to FHEK_0..7, then REG_CONTROL=CTRL_FHEK_ZEROIZE
    void halt_fpga_clocks();  // writes REG_CONTROL=CTRL_CLOCK_HALT

    // TRANSEC setters
    void set_hop_rate(uint32_t hops_per_sec);
    void set_blacklist_size(uint32_t count);
    void set_interleaver_depth(uint32_t depth);
    void set_pa_ramp_steps(uint32_t cycles);
    void set_emcon_ctrl(uint32_t value);
    void write_emcon_unlock();
    uint32_t emcon_level() const;

    uint32_t status() const;
    bool hop_locked() const;
    bool gps_holdover() const;
    int32_t rssi_dBm_x100() const;
    uint32_t hop_counter() const;

private:
    int fd_ = -1;
    volatile uint32_t* base_ = nullptr;
    void write_reg(uint32_t offset, uint32_t value);
    uint32_t read_reg(uint32_t offset) const;
};

} // namespace cirradio::drivers
