# FPGA RTL

SystemVerilog implementation of the CIRRADIO FPGA firmware for the Zynq-7045 PL.
All modules have XSim testbenches that pass in batch simulation.

## Modules

### `axi_regs` — AXI4-Lite Register Slave
Hand-written 4 KB AXI4-Lite slave providing the PS↔PL control plane.
Defines all read/write registers (FHEK, blacklist, slot bitmap, TX power,
status, RSSI, hop counter, per-slot error counts). Register offsets are the
single source of truth — kept in sync with `software/embedded/drivers/axi_regs.hpp`
by `fpga/scripts/check_regmap.py`.

### `ad9361_if` — AD9361 LVDS Interface
Bridges the Zynq-7045 fabric and the AD9361 transceiver over the 6-bit DDR
LVDS interface. RX: IBUFDS → ISERDESE2 → XPM FIFO CDC → AXI-stream to PS.
TX: AXI-stream from PS → XPM FIFO CDC → OSERDESE2 DDR serialiser → OBUFDS.
FB_CLK loopback provided via ODDR + OBUFDS for AD9361 TX timing alignment.

### `channelizer` — DDC/DUC with CIC + FIR
Digital down/up converter for the 225–512 MHz UHF band. RX: CIC decimator
(rate 16) → FIR low-pass (`fir_lp_rx` Xilinx FIR Compiler IP, 4× decimation,
17-tap equiripple). TX: FIR interpolation → CIC interpolator. Reduces the
122.88 MHz baseband rate to the symbol rate for the modem.

### `fhss_engine` — AES-256 Frequency-Hop Sequencer
Implements the CIRRADIO hop sequence using AES-256-ECB. Plaintext format:
`[slot(1)][pad(3)][frame LE(4)][zeros(7)][attempt(1)]` — output bytes [0:7]
as little-endian uint64 mod 287 = channel index. Supports a 20-frequency
blacklist with up to 5 retry attempts. Synchronises frame counter to GPS 1PPS;
falls back to AXI Timer on GPS loss (holdover mode).

### `modem` — QPSK Modem with Viterbi FEC
TX: LFSR scrambler → rate-1/2 K=7 convolutional encoder (CCSDS generators
G0=0x5B, G1=0x79) → QPSK mapper → RRC pulse shaper (`fir_rrc`, 4× interpolation,
α=0.35). RX: RRC matched filter (`fir_rrc`, 4× decimation) → Gardner timing
error detector (2 samples/symbol) → Costas loop (second-order PLL, K1=0.01,
K2=0.001) → soft slicer → Viterbi K=7 (`viterbi_k7` Xilinx IP) → descrambler.

### `tdma_mac` — TDMA Slot Engine
Manages 20 TDMA slots per frame. Controls TXNRX/T-R switch timing and preamble
insertion. Slot assignment driven by REG_SLOT_BITMAP register. Frame timing
locked to GPS 1PPS via the FHSS engine; slot 19 is reserved as the net-join
rendezvous frequency (fixed, not hopping).

## Prerequisites

- Vivado 2024.2 (any edition; WebPACK is sufficient for all modules except
  the Xilinx Security AES IP — see note in `create_project.tcl`)
- Part: `xc7z045ffg900-2`

## Recreate the Vivado Project

```bash
vivado -mode batch -source fpga/scripts/create_project.tcl
```

This creates `fpga/vivado/cirradio.xpr` from scratch, adds all RTL sources,
instantiates Xilinx IP (FIR Compiler, Viterbi, AXI DMA, AXI GPIO, AXI Timer,
AXI VIP), and generates IP output products.

## Run a Simulation

```bash
vivado -mode batch -source fpga/scripts/run_sim.tcl -tclargs axi_regs_tb
# Available: axi_regs_tb  ad9361_if_tb  fhss_engine_tb  modem_tb  tdma_mac_tb
```

## Validate Register Map Sync

```bash
python3 fpga/scripts/check_regmap.py
# REGMAP CHECK PASSED: N registers match between svh and hpp
```

## Block Design Testbench

`fpga/sim/cirradio_bd_tb.sv` tests the full block design integration. It
requires the Vivado block design (BD) to be created via the Vivado GUI and
exported as XSA first — it cannot run standalone. See `fpga/scripts/create_project.tcl`
for IP configuration and the Vivado project setup.
