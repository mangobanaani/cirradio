// software/embedded/drivers/axi_regs.hpp
// AXI register map — C++ side. Synced with fpga/src/axi_regs/regs.svh.
// DO NOT EDIT without updating regs.svh and re-running check_regmap.py.
#pragma once
#include <cstdint>

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

// Read registers (PL → PS)
constexpr uint32_t REG_STATUS          = 0x080;
constexpr uint32_t STATUS_HOP_LOCK     = (1u << 0);
constexpr uint32_t STATUS_GPS_HOLDOVER = (1u << 1);
constexpr uint32_t REG_RSSI            = 0x084;
constexpr uint32_t REG_HOP_COUNTER     = 0x088;
constexpr uint32_t REG_ERR_BASE        = 0x08C;

// Reset values
constexpr uint32_t REG_STATUS_RESET    = 0x00000002u;
constexpr uint32_t REG_RSSI_RESET      = 0xFFFF8300u;
constexpr uint32_t REG_TX_POWER_RESET  = 0x00000000u;
constexpr uint32_t REG_SLOT_BITMAP_RESET = 0x00000000u;

} // namespace cirradio::drivers
