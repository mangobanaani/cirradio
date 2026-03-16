// fpga/src/axi_regs/regs.svh
// AXI register map — single source of truth for RTL.
// Synced with software/embedded/drivers/axi_regs.hpp by check_regmap.py.
// All offsets are byte addresses within the 4 KB AXI4-Lite page.

// --- Write registers (PS → PL) ---
// FHEK: 32-byte key stored as 8 x 32-bit registers, little-endian
localparam REG_FHEK_0          = 12'h000; // FHEK[31:0]
localparam REG_FHEK_1          = 12'h004; // FHEK[63:32]
localparam REG_FHEK_2          = 12'h008; // FHEK[95:64]
localparam REG_FHEK_3          = 12'h00C; // FHEK[127:96]
localparam REG_FHEK_4          = 12'h010; // FHEK[159:128]
localparam REG_FHEK_5          = 12'h014; // FHEK[191:160]
localparam REG_FHEK_6          = 12'h018; // FHEK[223:192]
localparam REG_FHEK_7          = 12'h01C; // FHEK[255:224]

// Blacklist: 20 jammed frequencies, stored as kHz (225000-512000)
// Offset = REG_BLACKLIST_BASE + (index * 4)
localparam REG_BLACKLIST_BASE  = 12'h020; // [0] = 0x020 ... [19] = 0x06C
localparam REG_BLACKLIST_COUNT = 5'd20;

// Slot assignment: bit N = 1 means this node owns slot N (slots 0-19)
localparam REG_SLOT_BITMAP     = 12'h070;

// TX power setpoint: signed, units = dBm * 100 (e.g., 3700 = 37.0 dBm)
localparam REG_TX_POWER        = 12'h074;

// Control register (write-only): zeroize and halt commands
localparam REG_CONTROL         = 12'h07C;
localparam CTRL_FHEK_ZEROIZE   = 32'h0000_0001; // bit 0: clear FHEK + reset FHSS engine
localparam CTRL_CLOCK_HALT     = 32'h0000_0002; // bit 1: kill FPGA clock enables

// --- Read registers (PL → PS) ---
// Status flags
localparam REG_STATUS          = 12'h080;
localparam STATUS_HOP_LOCK_BIT     = 0; // 1 = hop sequencer locked to GPS
localparam STATUS_GPS_HOLDOVER_BIT = 1; // 1 = GPS 1PPS lost, running on AXI Timer

// RSSI: signed 32-bit, units = dBm * 100
localparam REG_RSSI            = 12'h084;

// Hop counter: bits [7:0]=slot, bits [31:8]=frame
localparam REG_HOP_COUNTER     = 12'h088;

// Per-slot error count: 20 x 32-bit. Offset = REG_ERR_BASE + (slot * 4)
localparam REG_ERR_BASE        = 12'h08C; // [0]=0x08C ... [19]=0x0D8

// Reset values
localparam REG_STATUS_RESET    = 32'h0000_0002; // GPS holdover at reset (no lock)
localparam REG_RSSI_RESET      = 32'hFFFF_8300; // -32000 = -320.00 dBm (invalid)
localparam REG_TX_POWER_RESET  = 32'h00000000;
localparam REG_SLOT_BITMAP_RESET = 32'h00000000;
