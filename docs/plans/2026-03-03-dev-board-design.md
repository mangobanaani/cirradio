# CIRRADIO Custom Dev Board Design

Date: 2026-03-03

## Overview

Full custom development board for the CIRRADIO tactical SDR. Discrete Zynq-7045 + AD9361 on a single 10-layer PCB with complete RF front-end including 5W PA, GPS timing, and all debug/development interfaces. No HSM on this board -- crypto stays in FPGA/software; HSM deferred to production board.

## System Block Diagram

```
                              ANT (SMA)
                                |
                    +-----------+-----------+
                    |   RF FRONT-END        |
                    |                       |
                    |  BPF -> T/R SW        |
                    |         +--+--+       |
                    |      TX |     | RX    |
                    |         |    LNA      |
                    |   Drv--PA  (ADL5523)  |
                    |  (ADL5606)  |         |
                    |     |    SAW Filter   |
                    |  Harmonic    |        |
                    |  Filter      |        |
                    |     |        |        |
                    |     v        v        |
                    |  +--------------+     |
                    |  |   AD9361     |     |
                    |  |  (RFIC)      |     |
                    |  +------+-------+     |
                    +---------+-------------+
                              | LVDS + SPI
                    +---------+--------------------------+
                    |         ZYNQ-7045 (XC7Z045-2FFG900I)
                    |                                    |
                    |  +----------+   +--------------+   |
                    |  |   PL     |   |    PS        |   |
                    |  | (FPGA)   |   | ARM A9 x2   |   |
                    |  |          |AXI| @ 1 GHz      |   |
                    |  | AD9361 IF|<->|              |   |
                    |  | FHSS eng |   | DDR3L ctrl   |   |
                    |  | Modem    |   | USB,UART,SPI |   |
                    |  +----------+   | GigE,I2C,GPIO|   |
                    |                 +--------------+   |
                    +--------+---------------+-----------+
                             |               |
                    +--------+---+  +--------+----------+
                    | DDR3L      |  | Peripherals       |
                    | 1 GB       |  |                   |
                    | (2x 4Gbit) |  | QSPI Flash 256Mb  |
                    |            |  | eMMC 8 GB          |
                    |            |  | USB (debug + host) |
                    |            |  | GigE (debug)       |
                    |            |  | GPS (MAX-M10S)     |
                    |            |  | UART console       |
                    |            |  | JTAG               |
                    |            |  | LEDs, buttons      |
                    +------------+  +--------------------+
```

## Major Component Selection

| Component | Part Number | Package | Function |
|-----------|------------|---------|----------|
| FPGA/SoC | XC7Z045-2FFG900I | BGA-900 (0.8mm) | Zynq-7045, dual A9, 350K logic cells |
| RF Transceiver | AD9361BBCZ | BGA-144 (0.8mm) | 70 MHz - 6 GHz, 12-bit, 56 MHz BW |
| DDR3L | MT41K256M16HA-125 (x2) | BGA-96 | 2x 4Gbit = 1 GB, 1.35V |
| QSPI Flash | S25FL256SAGNFI001 | WSON-8 | 256 Mbit, FPGA bitstream + boot |
| eMMC | MTFC8GAKAJCN-4M IT | BGA-153 | 8 GB, root filesystem |
| GPS | u-blox MAX-M10S | LCC-16 | Multi-GNSS, 1PPS output |
| OCXO | Connor-Winfield OX200-SC-040.0M | DIP-14 | 40 MHz, +/-10 ppb, AD9361 ref clock |
| PS Clock | DSC1001CI2-33.333 | 4-SMD | 33.333 MHz, Zynq PS_CLK |
| T/R Switch | PE42525 | QFN-16 | <0.5 dB IL, >50 dB isolation, 300 ns |
| LNA | ADL5523ACPZ | LFCSP-16 | NF 1.0 dB, gain 20 dB, 400-4000 MHz |
| Driver Amp | ADL5606ACPZ | LFCSP-24 | 20 dB gain, OIP3 +42 dBm |
| PA Module | TGA2594-SM | SMT | 225-512 MHz, +37 dBm (5W), GaAs |
| BPF (input) | Custom / Johanson SAW | SMD | 225-512 MHz, >30 dB OOB rejection |
| SAW (stage 2) | TBD | SMD | Narrower passband, image rejection |
| Harmonic Filter | Discrete LC | 0402 | 3-element Chebyshev, 2nd/3rd >40 dBc |
| Power Supervisor | TPS3808G01 | SOT-23-5 | POR sequencing for Zynq |
| USB PHY | USB3320C-EZK | QFN-32 | USB 2.0 ULPI PHY |
| Ethernet PHY | KSZ9031RNXIA | QFN-48 | Gigabit Ethernet, RGMII |

## Power Architecture

Input: 12V DC via 2.5mm barrel jack or 2-pin Molex. Total budget: ~18W at full TX.

```
12V Input (2.5A)
  |
  +-> 5V / 3A   (TPS54360B buck)  -> PA bias supply
  |
  +-> 3.3V / 2A (TPS54360B buck)  -> AD9361 VDDA, GPS, OCXO, level shifters
  |
  +-> 1.8V / 1A (TPS62913 buck)   -> AD9361 VDDD_IF, QSPI, eMMC, Zynq VCCO
  |
  +-> 1.35V / 2A (TPS62913 buck)  -> DDR3L VDDQ
  |         +-> 0.675V (TPS51200) -> DDR3L VTT termination
  |
  +-> 1.0V / 3A (TPS62913 buck)   -> Zynq VCCINT (core)
  |
  +-> 1.5V / 500mA (TPS62913)     -> Zynq VCCAUX
```

### Power Sequencing (Zynq requirement)

1. VCCINT (1.0V) -- must be first
2. VCCAUX (1.5V) -- second
3. VCCO (1.8V) -- third
4. DDR3L, AD9361, peripherals -- last
5. PS_POR_B released after all rails stable (TPS3808 supervisor, RC delay chain)

### Design Notes

- All switchers from TI for WEBENCH compatibility
- Bulk input: 2x 100uF MLCC + 1x 470uF electrolytic
- Each rail has ferrite bead isolation between analog and digital loads
- PA supply has dedicated LC pi-filter to prevent switching noise in RF path
- Target overall efficiency: ~85%

## RF Front-End

### Signal Chain

**RX path:** Antenna -> BPF -> T/R Switch -> LNA (ADL5523) -> SAW -> AD9361 RX1

**TX path:** AD9361 TX1 -> Driver (ADL5606) -> PA (TGA2594) -> Harmonic LPF -> T/R Switch -> BPF -> Antenna

### RF Performance

| Parameter | Value |
|-----------|-------|
| System NF | ~2.2 dB (BPF 0.8 + SW 0.4 + LNA 1.0) |
| RX sensitivity (25 kHz BW, 10 dB SNR) | ~ -118 dBm |
| TX max output power | +37 dBm (5W) |
| TX min output power | ~ -3 dBm |
| TX spurious emissions | < -60 dBc |
| T/R switching time | < 1 us |
| Band | 225-512 MHz |

### Layout Rules

- RF section on dedicated ground copper pour, single-point star connection to digital ground
- 50-ohm microstrip traces on Layer 1 only
- AD9361 placed adjacent to T/R switch, minimize trace length
- PA thermal pad: minimum 20 thermal vias (0.3mm drill) to internal ground plane
- RF shield can footprint (solder pads for stamped metal shield) over entire front-end

## AD9361 Interface

### Data Interface (LVDS, routed to PL)

- Mode: 2R2T FDD, parallel LVDS (using 1R1T channels, second channel routed to test points)
- Signals: P0_D[11:0], DATA_CLK, FB_CLK, RX_FRAME, TX_FRAME
- LVDS pairs: 100-ohm differential impedance, length-matched +/- 50 mil within pairs, +/- 200 mil between pairs
- Routed on inner signal layers with adjacent ground reference planes

### Control Interface (to PS)

- SPI: SCLK, MOSI, MISO, CS_n (max 40 MHz)
- RESETB: active-low, Zynq GPIO controlled
- CTRL_IN[3:0]: real-time gain/mode control from PL
- CTRL_OUT[7:0]: status to PL
- EN_AGC, TXNRX, ENABLE: mode pins from PL

### Clocking

- AD9361 reference: 40 MHz OCXO (Connor-Winfield OX200, +/-10 ppb)
- Zynq PS_CLK: 33.333 MHz crystal oscillator
- GPS 1PPS: routed to Zynq PL input for FHSS timing synchronization
- OCXO provides excellent short-term stability for FHSS sync without GPS lock

## DDR3L Memory

- 2x Micron MT41K256M16HA-125 (4 Gbit each, 16-bit data bus each = 32-bit total)
- 1.35V DDR3L, 800 MHz (DDR3-1600)
- Connected to Zynq PS DDR controller
- Routing: all DQ/DQS/DM signals length-matched within each byte lane (+/- 25 mil)
- Address/command signals: length-matched within group (+/- 100 mil)
- On-die termination (ODT) used; external VTT termination via TPS51200

## Peripherals and Connectors

| Interface | IC / Connector | Notes |
|-----------|---------------|-------|
| JTAG | 2x7 0.05" header (ARM standard) | FPGA + ARM debug |
| UART console | USB-B micro via FT232RQ | 115200 baud default |
| USB 2.0 Host | USB-A receptacle via USB3320C PHY | Peripheral connection |
| Gigabit Ethernet | RJ-45 with integrated magnetics, KSZ9031 PHY | Debug/data network |
| GPIO | 2x20 0.1" header | 20 PL I/O + 10 PS I/O + power/ground |
| RF Antenna | SMA female, edge-mount | 50-ohm |
| Power | 2.5mm barrel jack (center positive) | 12V / 2.5A |
| SD Card | Micro-SD slot | Alternate boot, field updates |
| Boot mode | 2-position DIP switch | JTAG / QSPI boot select |
| Reset | Tactile pushbutton | PS_SRST_B |
| Status LEDs | 4x (power, heartbeat, TX, RX) | Green/red, GPIO-controlled |
| User buttons | 2x tactile | Connected to PL GPIO |
| GPS antenna | U.FL connector | For active GPS antenna |

## PCB Stackup (10-layer)

1.6mm total thickness, controlled impedance.

```
L1  (TOP)  - Signal + Components      35 um Cu
    Prepreg  0.10 mm (Er=4.2)
L2  (GND1) - Ground plane             35 um Cu
    Core     0.20 mm
L3  (SIG1) - Signal (LVDS, DDR3 DQ)   35 um Cu
    Prepreg  0.10 mm
L4  (GND2) - Ground plane             35 um Cu
    Core     0.20 mm
L5  (SIG2) - Signal (DDR3 addr/cmd)   35 um Cu
    Prepreg  0.10 mm
L6  (PWR)  - Power planes (split)     35 um Cu
    Core     0.20 mm (center)
L7  (SIG3) - Signal (low-speed)       35 um Cu
    Prepreg  0.10 mm
L8  (GND3) - Ground plane             35 um Cu
    Core     0.20 mm
L9  (SIG4) - Signal (SPI, I2C, misc)  35 um Cu
    Prepreg  0.10 mm
L10 (BOT)  - Signal + Components      35 um Cu
```

### Impedance Targets

| Trace Type | Layer | Target | Width |
|------------|-------|--------|-------|
| Single-ended microstrip (RF) | L1 | 50 ohm | ~0.28 mm |
| Differential LVDS stripline | L3 | 100 ohm diff | ~0.12 mm, 0.20 mm gap |
| DDR3 single-ended stripline | L3/L5 | 50 ohm | ~0.18 mm |
| Single-ended microstrip (L10) | L10 | 50 ohm | ~0.28 mm |

### Routing Strategy

- Zynq BGA fanout: outer 3 rows escape on L1, inner rows via down to L3/L5/L7/L9
- DDR3 DQ byte lanes on L3, address/command on L5
- LVDS pairs on L3, between GND1 and GND2 reference planes
- RF traces on L1 only, with ground flood and via stitching along edges
- No high-speed signals cross split planes on L6
- Ground via stitching every 2mm around board perimeter

## Board Dimensions and Mechanical

- Size: 160 x 100 mm (Eurocard standard)
- 4x M3 mounting holes at corners (3.2mm drill, 6mm keepout)
- Component placement zones:
  - Top-left: RF front-end (shielded)
  - Top-center: AD9361
  - Center: Zynq-7045 + DDR3
  - Bottom-left: Power supplies
  - Bottom-right: Connectors (USB, Ethernet, JTAG, GPIO)
  - Right edge: SMA antenna connector
- Board edge clearance: 2mm minimum for all components
- Heatsink mounting: PA module area has 4x M2 threaded standoff holes for clip-on heatsink

## Thermal

- PA module (TGA2594): ~10W dissipation at 5W RF output. Requires thermal via array to internal ground planes + external heatsink (clip-on aluminum, ~10 C/W)
- Zynq-7045: ~3W typical. Exposed pad soldered to ground pour + thermal vias. Passive heatsink recommended.
- AD9361: ~1.5W. Thermal pad to ground pour + vias.
- Total board dissipation at full TX: ~16W
- Ambient operating range: 0-50 C (dev board, not field-rated)

## BOM Estimate (5 boards)

| Category | Per Board | 5x Total |
|----------|-----------|----------|
| Zynq-7045 (XC7Z045-2FFG900I) | $500 | $2,500 |
| AD9361BBCZ | $200 | $1,000 |
| DDR3L (2x) | $20 | $100 |
| QSPI Flash + eMMC | $15 | $75 |
| OCXO (40 MHz) | $50 | $250 |
| GPS (MAX-M10S) | $30 | $150 |
| PA module (TGA2594) | $80 | $400 |
| LNA + Driver + T/R SW | $30 | $150 |
| Ethernet PHY + USB PHY | $15 | $75 |
| Power regulators + passives | $40 | $200 |
| PCB fab (10-layer, qty 5) | $120 | $600 |
| Assembly (turnkey, qty 5) | $200 | $1,000 |
| Connectors + misc | $30 | $150 |
| **Per board total** | **~$1,330** | |
| **5-board run total** | | **~$6,650** |

## Design Rules Summary (for KiCad DRC)

| Rule | Value |
|------|-------|
| Minimum trace width | 0.1 mm (4 mil) |
| Minimum clearance | 0.1 mm (4 mil) |
| Minimum via drill | 0.2 mm (8 mil) |
| Minimum via annular ring | 0.125 mm (5 mil) |
| BGA pad size | 0.45 mm (for 0.8mm pitch) |
| BGA via-in-pad | Yes, filled and capped |
| RF trace width (50 ohm) | 0.28 mm |
| LVDS trace width | 0.12 mm, gap 0.20 mm |
| Minimum copper to board edge | 0.5 mm |

## Schematic Hierarchy (KiCad sheets)

1. **Top-level** -- block diagram, inter-sheet connections
2. **Zynq-7045** -- FPGA/SoC, decoupling, boot config, JTAG
3. **DDR3L Memory** -- 2x DRAM, termination, routing notes
4. **AD9361 + LVDS** -- transceiver, reference clock, data interface
5. **RF Front-End** -- LNA, PA, T/R switch, filters, SMA
6. **Power Supply** -- all regulators, sequencing, supervisor
7. **Peripherals** -- GPS, USB PHY, Ethernet PHY, UART, eMMC, QSPI
8. **Connectors & Debug** -- headers, LEDs, buttons, test points
