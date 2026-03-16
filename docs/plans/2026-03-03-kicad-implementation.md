# CIRRADIO Dev Board KiCad Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete KiCad project for the CIRRADIO dev board -- schematic capture, PCB layout, and manufacturing outputs (Gerbers, BOM, assembly files) ready for fabrication.

**Architecture:** Hierarchical 8-sheet schematic feeding a 10-layer controlled-impedance PCB. 160x100mm Eurocard format. Zynq-7045 + AD9361 as central components with complete power, RF front-end, memory, and peripheral subsystems.

**Tech Stack:** KiCad 9.x, 10-layer stackup, 0.8mm pitch BGA, LVDS/DDR3L high-speed routing, 50-ohm RF microstrip.

**Reference Documents:**
- Design spec: `docs/plans/2026-03-03-dev-board-design.md`
- Xilinx UG585: Zynq-7000 Technical Reference Manual
- Xilinx UG865: Zynq-7000 Packaging and Pinout (FFG900)
- AD9361 Reference Manual (ADI UG-570)
- AD-FMCOMMS3 reference design (ADI, KiCad-compatible)

---

## Phase A: Project Setup

### Task 1: Install KiCad and Create Project Structure

**Files:**
- Create: `hardware/cirradio-devboard/cirradio-devboard.kicad_pro`
- Create: `hardware/cirradio-devboard/cirradio-devboard.kicad_sch`
- Create: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`
- Create: `hardware/cirradio-devboard/lib/` (custom library directory)
- Create: `hardware/.gitignore`

**Step 1: Install KiCad**

```bash
brew install --cask kicad
```

Verify: `kicad-cli version` should show 9.x.

**Step 2: Create directory structure**

```bash
mkdir -p hardware/cirradio-devboard/lib/cirradio.pretty
mkdir -p hardware/cirradio-devboard/fab/{gerbers,bom,assembly}
```

**Step 3: Create .gitignore for hardware**

```gitignore
# KiCad backup/autosave
*-backups/
*.kicad_sch-bak
*.kicad_pcb-bak
_autosave-*
fp-info-cache
*.kicad_prl

# Manufacturing outputs (regenerate from source)
fab/gerbers/*
fab/bom/*
fab/assembly/*
```

**Step 4: Initialize KiCad project**

Open KiCad, create new project at `hardware/cirradio-devboard/cirradio-devboard`. This creates the `.kicad_pro`, `.kicad_sch`, and `.kicad_pcb` files.

**Step 5: Commit**

```bash
git add hardware/
git commit -m "add KiCad project skeleton for dev board"
```

---

### Task 2: Configure Design Rules and Board Stackup

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb` (Board Setup)

**Step 1: Set board dimensions**

In PCB Editor → Board Setup → Board:
- Board outline: 160 x 100 mm rectangle
- 4x M3 mounting holes at corners (5mm inset from edges): (5,5), (155,5), (5,95), (155,95)

**Step 2: Configure 10-layer stackup**

Board Setup → Physical Stackup:

| Layer | Name | Type | Thickness | Cu Weight | Er |
|-------|------|------|-----------|-----------|-----|
| F.Cu | TOP | Signal+Components | 35 um | 1 oz | - |
| - | Prepreg | Dielectric | 0.10 mm | - | 4.2 |
| In1.Cu | GND1 | Ground plane | 35 um | 1 oz | - |
| - | Core | Dielectric | 0.20 mm | - | 4.5 |
| In2.Cu | SIG1 | Signal (LVDS, DDR DQ) | 35 um | 1 oz | - |
| - | Prepreg | Dielectric | 0.10 mm | - | 4.2 |
| In3.Cu | GND2 | Ground plane | 35 um | 1 oz | - |
| - | Core | Dielectric | 0.20 mm | - | 4.5 |
| In4.Cu | SIG2 | Signal (DDR addr/cmd) | 35 um | 1 oz | - |
| - | Prepreg | Dielectric | 0.10 mm | - | 4.2 |
| In5.Cu | PWR | Power planes | 35 um | 1 oz | - |
| - | Core | Dielectric | 0.20 mm | - | 4.5 |
| In6.Cu | SIG3 | Signal (low-speed) | 35 um | 1 oz | - |
| - | Prepreg | Dielectric | 0.10 mm | - | 4.2 |
| In7.Cu | GND3 | Ground plane | 35 um | 1 oz | - |
| - | Core | Dielectric | 0.20 mm | - | 4.5 |
| In8.Cu | SIG4 | Signal (SPI, I2C) | 35 um | 1 oz | - |
| - | Prepreg | Dielectric | 0.10 mm | - | 4.2 |
| B.Cu | BOT | Signal+Components | 35 um | 1 oz | - |

Total thickness: ~1.6 mm

**Step 3: Configure design rules**

Board Setup → Design Rules → Constraints:

| Rule | Value |
|------|-------|
| Minimum clearance | 0.1 mm |
| Minimum track width | 0.1 mm |
| Minimum via drill | 0.2 mm |
| Minimum via annular ring | 0.125 mm |
| Minimum copper to edge | 0.5 mm |
| Minimum hole to hole | 0.25 mm |

**Step 4: Create net classes**

Board Setup → Design Rules → Net Classes:

| Net Class | Track Width | Clearance | Via Drill | Via Diameter | Diff Pair Width | Diff Pair Gap |
|-----------|------------|-----------|-----------|-------------|-----------------|---------------|
| Default | 0.15 mm | 0.1 mm | 0.3 mm | 0.55 mm | - | - |
| Power | 0.4 mm | 0.2 mm | 0.4 mm | 0.7 mm | - | - |
| Power_Wide | 0.8 mm | 0.2 mm | 0.4 mm | 0.7 mm | - | - |
| RF_50ohm | 0.28 mm | 0.2 mm | 0.3 mm | 0.55 mm | - | - |
| LVDS | 0.12 mm | 0.12 mm | 0.2 mm | 0.45 mm | 0.12 mm | 0.20 mm |
| DDR3 | 0.10 mm | 0.1 mm | 0.2 mm | 0.45 mm | - | - |
| DDR3_DiffPair | 0.10 mm | 0.1 mm | 0.2 mm | 0.45 mm | 0.10 mm | 0.15 mm |

**Step 5: Set impedance targets as notes**

Add text notes on User.Comments layer:
- RF microstrip (F.Cu over GND1): 50 ohm = 0.28 mm width
- LVDS stripline (In2.Cu between GND1/GND2): 100 ohm diff = 0.12 mm width, 0.20 mm gap
- DDR3 stripline (In2.Cu/In4.Cu): 50 ohm = 0.18 mm width

**Step 6: Commit**

```bash
git add hardware/cirradio-devboard/
git commit -m "configure 10-layer stackup and design rules"
```

---

## Phase B: Component Libraries

### Task 3: Acquire Standard Library Components

**Files:**
- Reference: KiCad built-in libraries

**Step 1: Verify available standard parts**

Open KiCad Symbol Editor, confirm these exist in default libraries:

| Component | Expected Library | Symbol |
|-----------|-----------------|--------|
| Resistor 0402 | Device | R |
| Capacitor 0402 | Device | C |
| Inductor 0402 | Device | L |
| Ferrite bead | Device | FerriteBead |
| LED | Device | LED |
| Tactile switch | Switch | SW_Push |
| DIP switch 2-pos | Switch | SW_DIP_x02 |
| Barrel jack 2.5mm | Connector | Barrel_Jack |
| SMA edge-mount | Connector_Coaxial | SMA_Amphenol_132289_EdgeMount |
| USB-A receptacle | Connector_USB | USB_A |
| USB Micro-B | Connector_USB | USB_Micro-B |
| RJ-45 w/ magnetics | Connector_RJ | RJ45_Shielded_MagJack |
| 2x7 0.05" header | Connector_PinHeader_1.27mm | PinHeader_2x07_P1.27mm_Vertical |
| 2x20 0.1" header | Connector_PinHeader_2.54mm | PinHeader_2x20_P2.54mm_Vertical |
| Micro-SD slot | Connector_Card | microSD_Card_Det |
| U.FL connector | Connector_Coaxial | U.FL |
| Electrolytic cap | Device | CP |
| Crystal oscillator (4-pin) | Oscillator | ASE-xxxMHz |

**Step 2: Check for existing IC symbols**

Check if these exist in KiCad libraries:

| IC | Library to check | Likely status |
|----|-----------------|---------------|
| FT232RQ | Interface_USB | Likely present |
| KSZ9031RNXIA | Interface_Ethernet | Likely present |

Note which are missing -- all missing symbols go into Task 4.

**Step 3: No commit needed (read-only verification)**

---

### Task 4: Create Custom Component Symbols

**Files:**
- Create: `hardware/cirradio-devboard/lib/cirradio.kicad_sym`

All custom symbols go in the project-local `cirradio` symbol library. For each IC below, either:
- Download from manufacturer/SnapEDA/Ultra Librarian and import
- Create manually in KiCad Symbol Editor from datasheet

**Step 1: Add project-local symbol library**

In KiCad Symbol Editor → Preferences → Manage Symbol Libraries → Project Libraries tab, add:
- Nickname: `cirradio`
- Path: `${KIPRJMOD}/lib/cirradio.kicad_sym`

**Step 2: XC7Z045-2FFG900I (Zynq-7045)**

Source: Download from AMD/Xilinx or use community library (e.g., `kicad-xilinx` on GitHub).

Multi-unit symbol with units for each bank:
- Unit A: PS Config (PS_CLK, PS_POR_B, PS_SRST_B, INIT_B, DONE, PROG_B, boot mode pins)
- Unit B: PS MIO (MIO[0:53])
- Unit C: PS DDR (DDR3 interface: DQ, DQS, DM, A, BA, CKE, ODT, CS, RAS, CAS, WE, CK, RESET)
- Unit D: PS GigE (MDIO, MDC + RGMII via EMIO)
- Unit E: PS USB (ULPI via MIO)
- Unit F: PL Bank 13 (HR, 50 pins) -- AD9361 control, misc I/O
- Unit G: PL Bank 33 (HP, 50 pins) -- AD9361 LVDS data
- Unit H: PL Bank 34 (HP, 50 pins) -- AD9361 LVDS data overflow, test points
- Unit I: PL Bank 12 (HR) -- GPIO header, LEDs, buttons
- Unit J: PL Banks 35/others -- spare I/O
- Unit K: Power (VCCINT, VCCAUX, VCCBRAM, VCCO_xx, GND, VCCPINT, VCCPAUX, VCCPLL)

900 pins total. Verify every pin against UG865 FFG900 pinout table.

**Step 3: AD9361BBCZ**

Source: Analog Devices provides KiCad-compatible schematic symbols, or download from SnapEDA.

144-pin BGA. Key pin groups:
- P0_D[11:0] (LVDS data), DATA_CLK, FB_CLK, RX_FRAME, TX_FRAME
- P1_D[11:0] (second port, optional)
- SPI: SCLK, MOSI, MISO, CS_n
- CTRL_IN[3:0], CTRL_OUT[7:0]
- EN_AGC, ENABLE, TXNRX
- RESETB
- XTALP, XTALN (reference clock input)
- VDDA_xxx, VDDD_xxx power pins (multiple)
- RX1A+/-, RX1B+/-, RX1C+/-, TX1A, TX1B, TX2A, TX2B (RF ports)

Verify all pins against AD9361 datasheet Table 5 (Ball Map).

**Step 4: MT41K256M16HA-125 (DDR3L)**

Source: KiCad may have generic DDR3 symbols. If not, download from SnapEDA.

96-ball BGA. Key pins:
- DQ[15:0], DQS/DQS#, DM (data)
- A[14:0] (address), BA[2:0] (bank), RAS#, CAS#, WE#
- CK/CK#, CKE, CS#, ODT, RESET#
- VDD, VDDQ, VSS, VSSQ, VREFDQ, ZQ

**Step 5: RF front-end ICs**

Create or download symbols for:

**TGA2594-SM (PA module):**
- RF_IN, RF_OUT, VDD1, VDD2, VDD3, GND, NC pins
- Reference: Qorvo TGA2594 datasheet

**PE42525 (T/R switch):**
- RFC, RF1, RF2, V1, V2, VDD, GND
- QFN-16 package
- Reference: pSemi PE42525 datasheet

**ADL5523ACPZ (LNA):**
- RFIN, RFOUT, VCC, VPDC, GND, DECL pins
- LFCSP-16 package

**ADL5606ACPZ (Driver amp):**
- INP, INM, OUTP, OUTM, VCC, VEE, PWDN pins
- LFCSP-24 package

**Step 6: Power management ICs**

**TPS54360B (buck, 2 instances):**
- VIN, SW, BOOT, EN, SS/TR, COMP, VSENSE, RT/CLK, GND, PWRGD
- SOIC-8 or HSOP-8 package

**TPS62913 (buck, 4 instances -- 1.8V, 1.35V, 1.0V, 1.5V):**
- VIN, SW, EN, FB, PG, VOUT, GND, MODE/SYNC, NR/SS
- SOT-23 variant or WSON

**TPS51200 (DDR VTT terminator):**
- VIN, VLDOIN, VTTREF, VTTSNS, EN, PG, GND, VOUT
- WSON-10 or similar

**TPS3808G01 (supervisor):**
- VDD, GND, SENSE, MR, CT, RESET
- SOT-23-5

**Step 7: Peripheral ICs**

**MAX-M10S (GPS):**
- VCC_IO, V_BCKP, VCC, GND, RF_IN, EXTINT, RXD, TXD, TIMEPULSE, D_SEL, SDA, SCL, RESET_N
- LCC-16 package
- Reference: u-blox MAX-M10S datasheet

**OX200-SC-040.0M (OCXO):**
- VCC, GND, OUTPUT, ENABLE (or VCTRL)
- DIP-14 (many pins NC)

**USB3320C-EZK (USB PHY):**
- ULPI interface: DATA[7:0], CLK, DIR, STP, NXT
- VBUS, VDD, VDDA, GND, RBIAS, DP, DM, CPEN, ID
- QFN-32 package

**KSZ9031RNXIA (Ethernet PHY):**
- RGMII: TXD[3:0], TX_CLK, TX_EN, RXD[3:0], RX_CLK, RX_DV
- MDIO, MDC
- LED[2:0]
- TXP/TXN, RXP/RXN (magnetics side)
- QFN-48 package

**FT232RQ (USB-UART):** Likely in KiCad library. Verify. If not:
- USBDP, USBDM, TXD, RXD, RTS, CTS, DTR, DSR, DCD, RI
- QFN-32 package

**S25FL256SAGNFI001 (QSPI flash):**
- CS#, SCK, SI/IO0, SO/IO1, WP#/IO2, HOLD#/IO3, VCC, GND
- WSON-8

**MTFC8GAKAJCN-4M (eMMC):**
- CLK, CMD, DAT[7:0], DS, RST, VCC, VCCQ, GND
- BGA-153 (but only ~20 functional balls for 8-bit mode)

**DSC1001CI2-33.333 (PS clock oscillator):**
- VDD, GND, OUT, EN (or NC)
- 4-pin SMD

**Step 8: Verify all symbols have correct pin types**

For each custom symbol, verify:
- Power pins marked as Power Input
- Output pins marked as Output
- Bidirectional pins (data buses) marked as Bidirectional
- No-connect pins marked as Not Connected
- Pin numbers match datasheet exactly

**Step 9: Commit**

```bash
git add hardware/cirradio-devboard/lib/cirradio.kicad_sym
git commit -m "add custom schematic symbols for all ICs"
```

---

### Task 5: Create Custom Footprints

**Files:**
- Create: `hardware/cirradio-devboard/lib/cirradio.pretty/*.kicad_mod`

**Step 1: Add project-local footprint library**

In KiCad Footprint Editor → Preferences → Manage Footprint Libraries → Project Libraries tab:
- Nickname: `cirradio`
- Path: `${KIPRJMOD}/lib/cirradio.pretty`

**Step 2: BGA footprints**

For all BGA parts, use KiCad's Footprint Wizard where possible, or import from manufacturer.

**XC7Z045 FFG900 (BGA-900, 0.8mm pitch):**
- 30x30 grid
- Pad diameter: 0.45 mm (NSMD)
- Via-in-pad: 0.2 mm drill, filled and capped
- Paste mask: custom aperture reduction per fab house spec
- Thermal pad: none (ground balls handle thermal)
- Reference: Xilinx UG865 package drawing

**AD9361 CSSP (BGA-144, 0.8mm pitch):**
- 12x12 grid
- Pad diameter: 0.45 mm
- Via-in-pad for ground thermal pads
- Exposed pad (center ground) if present

**MT41K256M16HA (BGA-96, 0.8mm pitch):**
- Need 2 instances on board
- Standard DDR3 BGA-96 footprint
- KiCad may have this in Package_BGA

**MTFC8GAKAJCN (BGA-153, 0.5mm pitch):**
- eMMC standard BGA
- Pad diameter: 0.25 mm
- Tighter design rules for 0.5mm pitch

**Step 3: QFN/LFCSP footprints**

For each QFN/LFCSP package, create or verify:

| Part | Package | Pad Pitch | Exposed Pad |
|------|---------|-----------|-------------|
| PE42525 | QFN-16 (3x3mm) | 0.5 mm | Yes |
| ADL5523 | LFCSP-16 (3x3mm) | 0.5 mm | Yes |
| ADL5606 | LFCSP-24 (4x4mm) | 0.5 mm | Yes |
| USB3320C | QFN-32 (5x5mm) | 0.5 mm | Yes |
| KSZ9031 | QFN-48 (7x7mm) | 0.5 mm | Yes |

All QFN/LFCSP exposed pads need thermal via array (6-16 vias depending on pad size).

**Step 4: Specialty footprints**

**TGA2594-SM (PA module):**
- Custom SMT package -- must match Qorvo recommended land pattern exactly
- Large thermal pad with minimum 20 thermal vias (0.3mm drill)
- 4x M2 heatsink mounting holes around perimeter

**OX200-SC-040.0M (OCXO, DIP-14):**
- Through-hole DIP-14 (0.3" row spacing)
- Most pins NC, verify active pins from datasheet

**MAX-M10S (LCC-16):**
- u-blox custom LCC footprint
- Download from u-blox or create from package drawing

**Step 5: Verify all footprints**

For each footprint:
- Courtyard present and correctly sized
- Fab layer outline matches package dimensions
- Pin 1 marking on silkscreen and fab layers
- 3D model assigned if available
- Paste mask apertures appropriate for the pad sizes

**Step 6: Commit**

```bash
git add hardware/cirradio-devboard/lib/cirradio.pretty/
git commit -m "add custom footprints for BGA and specialty packages"
```

---

## Phase C: Schematic Capture

### Task 6: Power Supply Sheet

**Files:**
- Create: `hardware/cirradio-devboard/power.kicad_sch`

This sheet is done first because it defines all power nets used by every other sheet.

**Step 1: Define power nets (global labels)**

| Net Name | Voltage | Source |
|----------|---------|--------|
| +12V | 12V | Input barrel jack |
| +5V | 5.0V | TPS54360B #1 |
| +3V3 | 3.3V | TPS54360B #2 |
| +1V8 | 1.8V | TPS62913 #1 |
| +1V35 | 1.35V | TPS62913 #2 |
| VTT | 0.675V | TPS51200 |
| VTTREF | 0.675V | TPS51200 |
| +1V0 | 1.0V | TPS62913 #3 |
| +1V5 | 1.5V | TPS62913 #4 |
| GND | 0V | Ground |

**Step 2: Input power section**

- Barrel jack (2.5mm, center-positive) → polarity protection (P-MOSFET or Schottky) → +12V
- Input bulk capacitors: 2x 100uF MLCC (1210) + 1x 470uF/25V electrolytic
- Power LED (green) with 4.7K resistor from +12V

**Step 3: 5V rail (PA bias)**

TPS54360B #1 circuit:
- VIN = +12V
- VOUT = +5V, 3A max
- Design with TI WEBENCH or reference design from datasheet
- Key components: inductor (10uH/3A), output caps (2x 22uF MLCC), bootstrap cap, feedback divider
- Output LC pi-filter before PA: 100nH + 100nF + 100nH (suppress switcher noise in RF)
- Net: +5V_PA (isolated from +5V digital)

**Step 4: 3.3V rail**

TPS54360B #2 circuit:
- VIN = +12V
- VOUT = +3.3V, 2A max
- Same topology as 5V rail, different feedback divider
- Ferrite bead split: +3V3 → FB → +3V3A (analog, for AD9361/OCXO/GPS)
- Net: +3V3

**Step 5: 1.8V rail (AD9361 digital, QSPI, eMMC, Zynq VCCO)**

TPS62913 #1 circuit:
- VIN = +3V3
- VOUT = +1V8, 1A max
- Low-noise mode for mixed-signal
- Net: +1V8

**Step 6: 1.35V rail (DDR3L)**

TPS62913 #2 circuit:
- VIN = +3V3
- VOUT = +1V35, 2A max
- Net: +1V35

**Step 7: DDR VTT termination**

TPS51200 circuit:
- VIN = +1V35 (VLDOIN)
- VTTREF = +1V35/2 = 0.675V (internal divider or external)
- VOUT = VTT (0.675V, tracks VTTREF)
- Nets: VTT, VTTREF

**Step 8: 1.0V rail (Zynq VCCINT)**

TPS62913 #3 circuit:
- VIN = +3V3
- VOUT = +1V0, 3A max (this is the highest current rail)
- May need parallel devices or larger variant if 3A exceeds TPS62913 rating
- **Note:** Verify TPS62913 current rating. If insufficient, substitute TPS62912 or similar 3A+ part.
- Net: +1V0

**Step 9: 1.5V rail (Zynq VCCAUX)**

TPS62913 #4 circuit:
- VIN = +3V3
- VOUT = +1V5, 500mA
- Net: +1V5

**Step 10: Power sequencing**

TPS3808G01 supervisor circuit:
- Monitors: +1V0 (VCCINT must be first)
- RC delay chain on EN pins to sequence:
  1. +1V0 (VCCINT) -- enabled directly from +12V present
  2. +1V5 (VCCAUX) -- EN from +1V0 PG (power-good)
  3. +1V8 (VCCO) -- EN from +1V5 PG
  4. +1V35, +3V3, +5V -- EN from +1V8 PG
- PS_POR_B: driven by TPS3808 RESET output (active-low, held low until all rails stable)
- Add 100ms RC delay on PS_POR_B after last PG assertion

Connect PG (power-good) outputs in daisy chain:
```
+1V0_PG → +1V5_EN
+1V5_PG → +1V8_EN
+1V8_PG → +1V35_EN, +3V3_EN, +5V_EN
All PG → AND gate (or wired-AND with pull-up) → TPS3808 SENSE → PS_POR_B
```

**Step 11: Add power flags and net labels**

- Place PWR_FLAG on +12V and GND at input
- Place global labels for all power nets
- Add text notes describing sequencing order

**Step 12: Run ERC on this sheet**

Verify no errors. Common issues: missing power flags, undriven power pins.

**Step 13: Commit**

```bash
git add hardware/cirradio-devboard/power.kicad_sch
git commit -m "add power supply schematic sheet"
```

---

### Task 7: Zynq-7045 Sheet

**Files:**
- Create: `hardware/cirradio-devboard/zynq.kicad_sch`

**Step 1: Place Zynq-7045 symbol**

Place XC7Z045-2FFG900I. If using multi-unit symbol, place all units.

**Step 2: Power connections**

Connect all Zynq power pins:

| Power Group | Net | Pin Count (approx) |
|-------------|-----|-------------------|
| VCCINT | +1V0 | ~40 pins |
| VCCAUX | +1V5 | ~12 pins |
| VCCBRAM | +1V0 | ~4 pins |
| VCCO_MIO (Bank 500/501) | +1V8 | ~8 pins |
| VCCO_13 (PL Bank 13) | +3V3 | ~4 pins |
| VCCO_33 (PL Bank 33) | +1V8 | ~4 pins |
| VCCO_34 (PL Bank 34) | +1V8 | ~4 pins |
| VCCO_12 (PL Bank 12) | +3V3 | ~4 pins |
| VCCPINT | +1V0 | ~10 pins |
| VCCPAUX | +1V8 | ~4 pins |
| VCCPLL | +1V8 | ~2 pins |
| GND | GND | ~100+ pins |

**Step 3: Decoupling capacitors**

Per Xilinx UG483 (decoupling guidelines):
- VCCINT: 20x 100nF (0402) + 4x 10uF (0805) placed under BGA
- VCCAUX: 8x 100nF + 2x 10uF
- Each VCCO bank: 4x 100nF + 1x 10uF
- VCCPINT: 8x 100nF + 2x 10uF
- VCCPAUX: 4x 100nF + 1x 10uF
- VCCBRAM: 4x 100nF + 1x 10uF

Use 100nF 0402 X7R ceramics. Use 10uF 0805 X5R ceramics.

**Step 4: Boot configuration**

- Boot mode pins (directly from Zynq or via MIO):
  - BOOT_MODE[0]: via MIO[2-8] or DIP switch → selects JTAG/QSPI
  - Use 2-position DIP switch:
    - Position 1 (BOOT[0]): JTAG=0, QSPI=1
    - Position 2 (BOOT[1]): reserved/GND
  - Add 10K pull-down resistors on boot mode pins
- INIT_B: pull-up 4.7K to VCCO
- DONE: LED (green) via 330 ohm resistor, also pull-up 4.7K
- PROG_B: pull-up 4.7K to VCCO, optional pushbutton to GND

**Step 5: PS_CLK**

- DSC1001CI2-33.333 oscillator → PS_CLK input (pin F7 on FFG900)
- 33.333 MHz, 3.3V output, series 22 ohm resistor
- Decoupling: 100nF on oscillator VDD

**Step 6: Reset and control**

- PS_POR_B: from power sequencing circuit (Task 6), global label
- PS_SRST_B: tactile pushbutton to GND + 10K pull-up + 100nF debounce cap

**Step 7: JTAG**

- TCK, TDI, TDO, TMS routed to 2x7 1.27mm header (ARM standard)
- Pin mapping:
  - 1: VCC (3.3V)
  - 2: TMS
  - 3: GND
  - 4: TCK
  - 5: GND
  - 6: TDO
  - 7: GND (or KEY, pin removed)
  - 8: TDI
  - 9: GND
  - 10: SRST (PS_SRST_B)
  - 11-14: GND or NC
- Series 33 ohm resistors on TCK, TDI, TMS

**Step 8: PS MIO assignments**

Route MIO pins with hierarchical labels to other sheets:

| MIO Pins | Function | Destination Sheet |
|----------|----------|------------------|
| MIO[1:6] | QSPI | Peripherals |
| MIO[16:27] | GEM0 (Ethernet RGMII) | Peripherals |
| MIO[28:39] | USB0 (ULPI) | Peripherals |
| MIO[40:45] | SD0 (Micro-SD) | Peripherals |
| MIO[46:47] | UART0 (spare) | Connectors |
| MIO[48:49] | UART1 (console, to FT232RQ) | Peripherals |
| MIO[50:51] | I2C0 | Connectors |
| MIO[0,7:15,52:53] | GPIO | Connectors |

**Step 9: PL I/O assignments (hierarchical labels)**

Route PL bank pins to other sheets:

| PL Bank | VCCO | Function | Destination |
|---------|------|----------|-------------|
| Bank 33 HP | +1V8 | AD9361 LVDS data P0_D[11:0], clocks, frames | AD9361 sheet |
| Bank 34 HP | +1V8 | AD9361 LVDS overflow, CTRL signals | AD9361 sheet |
| Bank 13 HR | +3V3 | AD9361 SPI, RESET, enables, misc | AD9361 sheet |
| Bank 12 HR | +3V3 | GPIO header, LEDs, buttons, 1PPS | Connectors sheet |

Place hierarchical labels for all PL-connected signals.

**Step 10: PS DDR interface (hierarchical labels)**

Route all PS DDR pins to DDR3L sheet:
- DDR_DQ[31:0], DDR_DQS_P/N[3:0], DDR_DM[3:0]
- DDR_A[14:0], DDR_BA[2:0]
- DDR_CAS_N, DDR_RAS_N, DDR_WE_N
- DDR_CK_P/N, DDR_CKE, DDR_CS_N, DDR_ODT
- DDR_RESET_N
- DDR_VREF

**Step 11: Commit**

```bash
git add hardware/cirradio-devboard/zynq.kicad_sch
git commit -m "add zynq-7045 schematic sheet"
```

---

### Task 8: DDR3L Memory Sheet

**Files:**
- Create: `hardware/cirradio-devboard/ddr3l.kicad_sch`

**Step 1: Place 2x MT41K256M16HA-125**

- U_DDR0: byte lanes 0 and 1 (DQ[15:0])
- U_DDR1: byte lanes 2 and 3 (DQ[31:16])

**Step 2: Data bus connections**

| Signal | U_DDR0 | U_DDR1 | Zynq PS DDR |
|--------|--------|--------|-------------|
| DQ[7:0] | DQ[7:0] | - | DDR_DQ[7:0] |
| DQ[15:8] | DQ[15:8] | - | DDR_DQ[15:8] |
| DQ[23:16] | - | DQ[7:0] | DDR_DQ[23:16] |
| DQ[31:24] | - | DQ[15:8] | DDR_DQ[31:24] |
| DQS0_P/N | LDQS/LDQS# | - | DDR_DQS_P/N[0] |
| DQS1_P/N | UDQS/UDQS# | - | DDR_DQS_P/N[1] |
| DQS2_P/N | - | LDQS/LDQS# | DDR_DQS_P/N[2] |
| DQS3_P/N | - | UDQS/UDQS# | DDR_DQS_P/N[3] |
| DM0 | LDM | - | DDR_DM[0] |
| DM1 | UDM | - | DDR_DM[1] |
| DM2 | - | LDM | DDR_DM[2] |
| DM3 | - | UDM | DDR_DM[3] |

**Step 3: Address/command bus (shared between both chips)**

Both chips share:
- A[14:0], BA[2:0]
- RAS#, CAS#, WE#
- CK/CK# (differential clock)
- CKE, CS# (active-low)
- ODT
- RESET#

Connect to Zynq PS DDR pins via hierarchical labels.

**Step 4: Power connections**

- VDD: +1V35 (each chip has multiple VDD pins)
- VDDQ: +1V35 (I/O supply)
- VREFDQ: voltage divider from +1V35 (0.675V) with 240 ohm / 240 ohm, decoupled with 100nF
- VSS, VSSQ: GND
- ZQ: 240 ohm 1% resistor to GND (calibration)

**Step 5: Decoupling**

Per chip:
- VDD: 4x 100nF (0402) + 1x 10uF (0805)
- VDDQ: 4x 100nF (0402) + 1x 10uF (0805)

**Step 6: VTT termination**

TPS51200 output (VTT = 0.675V) connects to:
- Series termination resistors on A/BA/CMD signals (not typically needed for point-to-point)
- Actually for 2-chip point-to-point DDR3L, fly-by topology with VTT termination at end:
  - Route address/command as fly-by: Zynq → U_DDR0 → U_DDR1 → VTT termination resistor pack (47 ohm)
  - Only CK requires source termination (series resistor at Zynq end, ~22 ohm)

**Step 7: Routing notes (text annotations on schematic)**

Add notes:
- "DQ byte lanes: length-match within byte lane +/- 25 mil"
- "Address/command: fly-by topology, length-match within group +/- 100 mil"
- "DQS to CK skew: per Micron spec"
- "Route on In2.Cu (SIG1) and In4.Cu (SIG2)"
- "Keep DDR3L group compact, directly below Zynq"

**Step 8: Commit**

```bash
git add hardware/cirradio-devboard/ddr3l.kicad_sch
git commit -m "add DDR3L memory schematic sheet"
```

---

### Task 9: AD9361 + LVDS Sheet

**Files:**
- Create: `hardware/cirradio-devboard/ad9361.kicad_sch`

**Step 1: Place AD9361BBCZ**

**Step 2: Reference clock input**

- XTALP/XTALN: 40 MHz OCXO output
  - OCXO (OX200) output → AC coupling cap (100pF) → series 22 ohm → XTALP
  - XTALN: 100pF to GND (single-ended drive into differential input)
- Place OCXO on this sheet with its own decoupling:
  - VCC: +3V3A (analog 3.3V)
  - 100nF + 10uF decoupling on VCC
  - ENABLE: tie to VCC (always on)

**Step 3: LVDS data interface to Zynq PL**

All LVDS signals route to Zynq PL Bank 33/34 via hierarchical labels:

| AD9361 Pin | Net Name | Zynq Bank | Type |
|------------|----------|-----------|------|
| P0_D[11:0]_P/N | AD_D[11:0]_P/N | Bank 33 | LVDS |
| DATA_CLK_P/N | AD_DCLK_P/N | Bank 33 | LVDS |
| FB_CLK_P/N | AD_FBCLK_P/N | Bank 33 | LVDS |
| RX_FRAME_P/N | AD_RXFRAME_P/N | Bank 33 | LVDS |
| TX_FRAME_P/N | AD_TXFRAME_P/N | Bank 33 | LVDS |

Total: 16 LVDS pairs (32 pins on Zynq side).

Add 100 ohm differential termination resistors at Zynq end (close to PL pins) for each pair. (Check: Zynq HP banks have internal diff termination -- may not need external.)

**Step 4: SPI control interface**

AD9361 SPI connects to Zynq PS (via MIO or EMIO):

| Signal | Net Name | Zynq Connection |
|--------|----------|----------------|
| SPI_CLK | AD_SCLK | PS SPI0_SCLK (MIO[10] or EMIO) |
| SPI_DI | AD_MOSI | PS SPI0_MOSI |
| SPI_DO | AD_MISO | PS SPI0_MISO |
| SPI_ENB | AD_CS_N | PS SPI0_CS |

Series 33 ohm resistors on SPI signals.

**Step 5: Control and status pins**

| AD9361 Pin | Net Name | Zynq Connection |
|------------|----------|----------------|
| CTRL_IN[3:0] | AD_CTRL_IN[3:0] | PL Bank 13 GPIO |
| CTRL_OUT[7:0] | AD_CTRL_OUT[7:0] | PL Bank 13 GPIO |
| EN_AGC | AD_EN_AGC | PL Bank 13 GPIO |
| ENABLE | AD_ENABLE | PL Bank 13 GPIO |
| TXNRX | AD_TXNRX | PL Bank 13 GPIO |
| RESETB | AD_RESET_N | PL Bank 13 GPIO (active-low) |

RESETB: pull-up 10K to +1V8, Zynq PL can assert low.

**Step 6: RF port connections (hierarchical labels to RF sheet)**

| AD9361 Pin | Net | Destination |
|------------|-----|-------------|
| RX1A_P/N | AD_RX1A_P/N | RF Front-End (from LNA output via SAW) |
| TX1A | AD_TX1A | RF Front-End (to driver amp input) |

Second port (RX1B/C, TX1B, RX2, TX2): route to test points or leave NC per design.

**Step 7: AD9361 power connections and decoupling**

Per AD9361 datasheet and reference design (UG-570 / AD-FMCOMMS3):

| Power Pin Group | Net | Decoupling |
|-----------------|-----|-----------|
| VDDA1P3_xxx (1.3V analog) | Generated from +1V8 via LDO (ADP151-1.3) | 4x 100nF + 1x 10uF each |
| VDDD1P3_DIGITAL | Same 1.3V LDO or dedicated | 4x 100nF + 1x 10uF |
| VDDA_GP_xxx (1.3V GP) | Same rail | per ADI ref design |
| VDDD_IF (1.8V digital IF) | +1V8 | 4x 100nF + 1x 10uF |
| VDDA3P3 (3.3V analog) | +3V3A | 2x 100nF + 1x 10uF |

**Important:** AD9361 requires a 1.3V supply for its analog core. This needs a dedicated LDO from 1.8V or 3.3V. Add an ADP151-1.3 (or similar low-noise LDO, SOT-23-5) on this sheet:
- VIN = +1V8
- VOUT = +1V3_AD (1.3V, 200mA typical)
- Decoupling: 1uF input, 1uF output

**Step 8: Commit**

```bash
git add hardware/cirradio-devboard/ad9361.kicad_sch
git commit -m "add AD9361 and LVDS interface schematic sheet"
```

---

### Task 10: RF Front-End Sheet

**Files:**
- Create: `hardware/cirradio-devboard/rf-frontend.kicad_sch`

**Step 1: Antenna input (SMA connector)**

- SMA edge-mount female connector
- 50-ohm trace to bandpass filter

**Step 2: Input bandpass filter (225-512 MHz)**

- 3-section LC bandpass or Johanson SAW filter
- If discrete LC:
  - Series L (47nH) → shunt C (22pF to GND) → series L (47nH) → shunt C (22pF) → series L (47nH)
  - Values are approximate; tune in simulation (use Qucs or similar)
  - Use 0402 components, ATC/Murata RF-grade
- If SAW: single component, specify part number and matching network
- Target: <1 dB insertion loss in-band, >30 dB rejection out-of-band

**Step 3: T/R switch (PE42525)**

- RFC: from BPF output
- RF1: RX path (to LNA)
- RF2: TX path (from harmonic filter)
- V1, V2: control pins from Zynq PL GPIO (active-high, +3V3 logic)
  - V1=H, V2=L → RFC-RF1 (RX mode)
  - V1=L, V2=H → RFC-RF2 (TX mode)
- VDD: +3V3, 100nF decoupling
- GND: solid ground pour

**Step 4: RX path -- LNA (ADL5523)**

- RFIN: from PE42525 RF1 (50 ohm)
- RFOUT: to SAW filter
- VCC: +3V3A via bias inductor (100nH) + 100nF + 10nF decoupling
- Input/output matching per ADL5523 datasheet for 225-512 MHz
- Gain: ~20 dB, NF: ~1.0 dB

**Step 5: RX path -- SAW filter (stage 2)**

- Between LNA output and AD9361 RX input
- Purpose: image rejection, further OOB suppression
- Select appropriate SAW for 225-512 MHz (if available) or use LC filter
- Must maintain 50-ohm interface

**Step 6: RX path to AD9361**

- SAW output → AC coupling cap (100pF) → AD_RX1A_P (via hierarchical label)
- AD_RX1A_N: AC coupling cap to GND (single-ended to differential conversion handled inside AD9361)

**Step 7: TX path from AD9361**

- AD_TX1A (hierarchical label) → AC coupling cap (100pF) → matching network → ADL5606 input

**Step 8: TX path -- Driver amplifier (ADL5606)**

- Differential input: can be driven single-ended with balun or AC coupling
- Output: 50-ohm, ~+20 dBm
- VCC: +5V_PA (or +3V3 depending on datasheet), proper decoupling
- PWDN: connect to Zynq PL GPIO (active-low) via 10K pull-up

**Step 9: TX path -- PA (TGA2594-SM)**

- RF_IN: from ADL5606 output (may need attenuator pad for level control)
- RF_OUT: +37 dBm max (5W)
- VDD: +5V_PA, heavy decoupling (10uF + 100nF + 10nF at each VDD pin)
- Bias: per TGA2594 datasheet, may need external bias resistors
- Thermal: 20+ vias under thermal pad to ground planes

**Step 10: TX path -- Harmonic LPF**

After PA, before T/R switch:
- 3-element Chebyshev low-pass filter
- Cutoff: ~600 MHz (passes fundamental 225-512 MHz, rejects 2nd harmonic 450-1024 MHz)
- Approximate values (0402 RF grade):
  - Shunt C (33pF) → Series L (27nH) → Shunt C (33pF)
  - Or 5-element for better rejection: C-L-C-L-C
- Target: 2nd harmonic >40 dBc, 3rd harmonic >40 dBc

**Step 11: RF shield footprint**

- Add solder pads (1mm wide, 2mm keepout inside) around entire RF section perimeter
- For stamped metal shield can
- On F.Cu layer with corresponding B.Cu ground pour

**Step 12: Routing notes**

Add text:
- "All RF traces: 50-ohm microstrip on F.Cu, 0.28mm width"
- "Ground via stitching along all RF traces, every 1mm"
- "PA thermal pad: minimum 20x 0.3mm vias to GND planes"
- "AD9361 ↔ T/R switch: minimize trace length, <10mm"

**Step 13: Commit**

```bash
git add hardware/cirradio-devboard/rf-frontend.kicad_sch
git commit -m "add RF front-end schematic sheet"
```

---

### Task 11: Peripherals Sheet

**Files:**
- Create: `hardware/cirradio-devboard/peripherals.kicad_sch`

**Step 1: QSPI Flash (S25FL256SAGNFI001)**

- CS#: MIO[1]
- SCK: MIO[6] (verify MIO assignment from Zynq bank 500 table)
- IO0/SI: MIO[2]
- IO1/SO: MIO[3]
- IO2/WP#: MIO[4] (pull-up 10K to +1V8)
- IO3/HOLD#: MIO[5] (pull-up 10K to +1V8)
- VCC: +1V8 (or +3V3, check part voltage range -- this part supports 3V)
- Decoupling: 100nF

**Step 2: eMMC (MTFC8GAKAJCN-4M)**

- 8-bit data mode: DAT[7:0]
- CLK, CMD
- Connected to Zynq PS via EMIO or dedicated pins
- **Note:** Zynq PS SDIO can do 8-bit via EMIO. Route through PL or use MIO (MIO only supports 4-bit SD).
- For 8-bit eMMC: use EMIO SDIO1 → PL pins → eMMC
- VCC: +3V3, VCCQ: +1V8
- Decoupling: 100nF on each supply
- RST: tie to +1V8 via 10K (or connect to GPIO for reset control)

**Step 3: USB PHY (USB3320C-EZK)**

Connected to Zynq PS USB0 via MIO[28:39]:

| USB3320C Pin | Net | MIO |
|-------------|-----|-----|
| DATA[7:0] | USB_D[7:0] | MIO[32:39] |
| CLK | USB_CLK | MIO[36] |
| DIR | USB_DIR | MIO[29] |
| STP | USB_STP | MIO[30] |
| NXT | USB_NXT | MIO[31] |

- VDD, VDDA: +3V3, decoupling 100nF + 10uF each
- RBIAS: 12.1K 1% to GND
- DP, DM: to USB-A receptacle via series 22 ohm resistors
- CPEN: USB power control output (drives P-FET for VBUS 5V to USB-A connector)
- Crystal: 24 MHz (or check if internal oscillator is sufficient)

**Step 4: Ethernet PHY (KSZ9031RNXIA)**

RGMII interface to Zynq PS GEM0 via MIO[16:27]:

| KSZ9031 Pin | Net | MIO |
|-------------|-----|-----|
| TXD[3:0] | ETH_TXD[3:0] | MIO[16:19] |
| TX_CLK | ETH_TX_CLK | MIO[20] |
| TX_EN | ETH_TX_EN | MIO[21] |
| RXD[3:0] | ETH_RXD[3:0] | MIO[22:25] |
| RX_CLK | ETH_RX_CLK | MIO[26] |
| RX_DV | ETH_RX_DV | MIO[27] |
| MDIO | ETH_MDIO | Zynq PS MDIO |
| MDC | ETH_MDC | Zynq PS MDC |

- VDD: +1V8 (core), VDDIO: +1V8 (I/O to match Zynq MIO bank voltage)
- Transformer-coupled to RJ-45 with integrated magnetics
- LED[2:0]: to RJ-45 integrated LEDs (link, activity, speed)
- RESET#: from Zynq GPIO or power-on reset, 10K pull-up
- Config straps (MODE[3:0]): set via resistors for RGMII mode, address
- 25 MHz crystal (or use REF_CLK from Zynq)

**Step 5: UART-USB bridge (FT232RQ)**

- TXD: from Zynq MIO[48] (UART1_TX)
- RXD: to Zynq MIO[49] (UART1_RX)
- USBDP/USBDM: to USB Micro-B connector via series 22 ohm resistors
- VCC: +3V3 (or USB VBUS if self-powered; prefer 3.3V for reliability)
- Decoupling: 100nF + 10uF on VCC, 100nF on VCCIO
- RESET#: 100nF cap to GND + 10K pull-up (RC reset)
- Ferrite bead on USB shield to GND

**Step 6: GPS module (MAX-M10S)**

- VCC: +3V3A, decoupling 100nF + 10uF
- V_BCKP: optional backup battery (CR1220 holder) or tie to VCC
- RF_IN: from U.FL connector via DC block (10nF) and LNA/SAW (internal to MAX-M10S)
- TXD/RXD: to Zynq PS UART0 (MIO[46:47]) or PL GPIO via EMIO
- TIMEPULSE (1PPS): critical signal → route to Zynq PL input (Bank 12) via global label `GPS_1PPS`
- D_SEL: GND for UART mode (or VCC for I2C mode)
- RESET_N: 10K pull-up to VCC, optional GPIO connection
- EXTINT: tie to GND if unused

**Step 7: Micro-SD card slot**

Connected to Zynq PS SDIO0 via MIO[40:45]:

| SD Pin | Net | MIO |
|--------|-----|-----|
| CLK | SD_CLK | MIO[40] |
| CMD | SD_CMD | MIO[41] |
| DAT[3:0] | SD_DAT[3:0] | MIO[42:45] |
| CD# | SD_CD_N | Zynq GPIO |

- VDDIO: +3V3
- 10K pull-up on CMD and DAT lines
- Card-detect switch to Zynq GPIO (active-low)

**Step 8: Commit**

```bash
git add hardware/cirradio-devboard/peripherals.kicad_sch
git commit -m "add peripherals schematic sheet"
```

---

### Task 12: Connectors and Debug Sheet

**Files:**
- Create: `hardware/cirradio-devboard/connectors.kicad_sch`

**Step 1: GPIO header (2x20, 0.1" pitch)**

Pin assignment (active pins connected to Zynq PL Bank 12 and PS):

| Pin | Net | Pin | Net |
|-----|-----|-----|-----|
| 1 | +3V3 | 2 | +5V |
| 3 | PL_IO0 | 4 | +5V |
| 5 | PL_IO1 | 6 | GND |
| 7 | PL_IO2 | 8 | UART0_TX (MIO[46]) |
| 9 | GND | 10 | UART0_RX (MIO[47]) |
| 11 | PL_IO3 | 12 | PL_IO4 |
| 13 | PL_IO5 | 14 | GND |
| 15 | PL_IO6 | 16 | PL_IO7 |
| 17 | +3V3 | 18 | PL_IO8 |
| 19 | PS_SPI1_MOSI | 20 | GND |
| 21 | PS_SPI1_MISO | 22 | PL_IO9 |
| 23 | PS_SPI1_SCLK | 24 | PS_SPI1_CS |
| 25 | GND | 26 | PL_IO10 |
| 27 | PS_I2C0_SDA (MIO[50]) | 28 | PS_I2C0_SCL (MIO[51]) |
| 29 | PL_IO11 | 30 | GND |
| 31 | PL_IO12 | 32 | PL_IO13 |
| 33 | PL_IO14 | 34 | GND |
| 35 | PL_IO15 | 36 | PL_IO16 |
| 37 | PL_IO17 | 38 | PL_IO18 |
| 39 | GND | 40 | PL_IO19 |

Series 33 ohm resistors on all PL I/O for ESD protection.

**Step 2: Status LEDs**

4 LEDs (0603 package):
| LED | Color | Net | Source |
|-----|-------|-----|--------|
| Power | Green | +3V3 | Always on (via 4.7K) |
| Heartbeat | Green | PL_LED_HB | PL Bank 12 GPIO |
| TX | Red | PL_LED_TX | PL Bank 12 GPIO |
| RX | Green | PL_LED_RX | PL Bank 12 GPIO |

Each GPIO LED: active-high, 330 ohm series resistor.

**Step 3: User buttons**

2x tactile pushbuttons:
- BTN0: PL Bank 12 GPIO, 10K pull-up to +3V3, 100nF debounce
- BTN1: PL Bank 12 GPIO, 10K pull-up to +3V3, 100nF debounce
- Active-low (pressed = GND)

**Step 4: Test points**

Add test points (PTH or SMD pads) for:
- All power rails: +12V, +5V, +3V3, +1V8, +1V35, +1V0, +1V5, VTT
- GND
- PS_CLK, AD9361 ref clock
- GPS_1PPS
- AD9361 RX1B (unused RF port, for test/debug)
- JTAG signals

**Step 5: Board ID / version**

- Text on silkscreen: "CIRRADIO DevBoard v1.0"
- Optional: I2C EEPROM (24C02, SOT-23-5) for board ID, connected to PS I2C

**Step 6: Commit**

```bash
git add hardware/cirradio-devboard/connectors.kicad_sch
git commit -m "add connectors and debug schematic sheet"
```

---

### Task 13: Top-Level Schematic

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_sch`

**Step 1: Create hierarchical sheet references**

In the top-level schematic, add 7 hierarchical sheet symbols:

| Sheet | File | Approximate Position |
|-------|------|---------------------|
| Power Supply | power.kicad_sch | Bottom-left |
| Zynq-7045 | zynq.kicad_sch | Center |
| DDR3L Memory | ddr3l.kicad_sch | Center-right |
| AD9361 + LVDS | ad9361.kicad_sch | Top-center |
| RF Front-End | rf-frontend.kicad_sch | Top-left |
| Peripherals | peripherals.kicad_sch | Bottom-center |
| Connectors & Debug | connectors.kicad_sch | Bottom-right |

**Step 2: Connect hierarchical pins**

Wire all hierarchical pins between sheets. Key inter-sheet connections:

| From Sheet | Signal Group | To Sheet |
|-----------|-------------|----------|
| Zynq | DDR bus (50+ signals) | DDR3L |
| Zynq | LVDS (32 signals) | AD9361 |
| Zynq | AD9361 SPI + control | AD9361 |
| AD9361 | RF ports (RX1A, TX1A) | RF Front-End |
| Zynq | MIO groups | Peripherals |
| Zynq | PL GPIO | Connectors |
| Power | All rails + POR | All sheets |

**Step 3: Add block diagram annotations**

Add text notes and rectangles showing signal flow between blocks. Include revision box:
- Title: CIRRADIO Dev Board
- Revision: 1.0
- Date: 2026-03-03

**Step 4: Run full-design ERC**

Schematic → Inspect → Electrical Rules Check. Fix all errors:
- Missing power flags
- Unconnected pins (add no-connect flags where intentional)
- Pin type conflicts
- Missing net labels

**Step 5: Commit**

```bash
git add hardware/cirradio-devboard/*.kicad_sch
git commit -m "complete top-level schematic with all hierarchical connections"
```

---

## Phase D: PCB Layout

### Task 14: Import Netlist and Board Setup

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: Update PCB from schematic**

Tools → Update PCB from Schematic (F8). Import all components.

**Step 2: Verify component count**

Check that all components imported correctly. Expected approximate counts:
- ICs: ~15 (Zynq, AD9361, 2x DDR3, QSPI, eMMC, GPS, OCXO, USB PHY, ETH PHY, FT232, 4x TPS62913, 2x TPS54360, TPS51200, TPS3808, LDO)
- Passives: ~300+ (decoupling caps, resistors, inductors, ferrite beads)
- Connectors: ~12 (SMA, USB-A, USB Micro-B, RJ-45, barrel jack, JTAG, GPIO header, SD slot, U.FL, DIP switch, buttons)
- LEDs: 5+

**Step 3: Assign net classes**

Assign nets to the classes defined in Task 2:
- Power nets (+12V, +5V, +3V3, etc.) → Power or Power_Wide
- RF traces → RF_50ohm
- AD9361 LVDS pairs → LVDS
- DDR3 signals → DDR3 or DDR3_DiffPair
- Everything else → Default

**Step 4: Draw board outline**

On Edge.Cuts layer:
- Rectangle: 160 x 100 mm, origin at (0,0)
- Corner radius: 1mm (optional)
- 4x M3 mounting holes at (5, 5), (155, 5), (5, 95), (155, 95)

**Step 5: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "import netlist and set up board outline"
```

---

### Task 15: Component Placement

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: Place major ICs per zone plan**

Follow the design doc placement zones:

| Zone | Components | Approximate Area |
|------|-----------|-----------------|
| Top-left (0-60mm, 0-40mm) | RF front-end: BPF, PE42525, ADL5523, SAW, ADL5606, TGA2594, harmonic filter | Shield can outline |
| Top-center (60-100mm, 0-40mm) | AD9361 + OCXO + LDO | Adjacent to RF |
| Center (40-120mm, 30-70mm) | Zynq-7045 (BGA takes ~24x24mm) | Centered for routing |
| Center-right (100-140mm, 25-55mm) | 2x DDR3L | Close to Zynq PS DDR balls |
| Bottom-left (0-60mm, 60-100mm) | Power supply: regulators, inductors, caps | Isolated from RF |
| Bottom-right (100-160mm, 60-100mm) | Connectors: USB, Ethernet, JTAG, GPIO | Board edge |
| Right edge (155-160mm, 30-50mm) | SMA antenna connector | Edge-mount |
| Top-right (140-160mm, 0-30mm) | GPS module + U.FL | Near board edge |

**Step 2: Place Zynq BGA fanout area**

- Zynq-7045 at board center (~80, 50)
- Reserve 5mm clearance on all sides for BGA fanout vias
- Decoupling capacitors on B.Cu directly under BGA

**Step 3: Place DDR3L memories**

- Both DDR3L chips close to Zynq PS DDR ball cluster
- Oriented for minimal DQ trace length
- VTT termination resistors at far end (fly-by termination)

**Step 4: Place AD9361 near RF section**

- AD9361 between Zynq PL HP bank balls and T/R switch
- LVDS traces should be short on Zynq side, RF traces short on RF side

**Step 5: Place decoupling capacitors**

- For BGA ICs: place decoupling caps on B.Cu directly under the IC
- For other ICs: place caps as close as possible to power pins
- 10uF bulk caps slightly further away (within 10mm)

**Step 6: Place power supply components**

- Group each regulator with its inductor, input/output caps, feedback resistors
- Keep switching node traces short (inductor close to SW pin)
- Orient regulators for good thermal via connection to ground

**Step 7: Place connectors on board edges**

- SMA: right edge, centered vertically in RF zone
- RJ-45: bottom-right edge
- USB-A, USB Micro-B: bottom edge
- Barrel jack: bottom-left corner
- JTAG header: bottom-right area
- GPIO header: right side, bottom area
- Micro-SD: bottom edge

**Step 8: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "place all components per zone plan"
```

---

### Task 16: Power Plane Design

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: Ground planes**

- In1.Cu (GND1): solid ground plane, full board coverage
- In3.Cu (GND2): solid ground plane, full board coverage
- In7.Cu (GND3): solid ground plane, full board coverage
- Avoid splits under high-speed signals
- Single star-point connection between RF ground region and digital ground

**Step 2: Power plane (In5.Cu - PWR)**

Split into regions:
- +1V0 region: largest area (Zynq VCCINT, highest current)
- +1V35 region: DDR3L area
- +1V5 region: small, near Zynq VCCAUX pins
- +1V8 region: moderate, covers AD9361, Zynq VCCO
- +3V3 region: moderate, general peripherals
- +5V region: small, PA area only

Each region connected to its regulator output via wide trace or pour.

**Step 3: Verify no high-speed signals cross plane splits**

DDR3, LVDS, and RF traces must NOT cross gaps in reference planes. Use DRC custom rules or visual inspection.

**Step 4: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "design power and ground planes"
```

---

### Task 17: High-Speed Routing (DDR3L + LVDS)

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: DDR3L byte lane routing**

Route on In2.Cu (SIG1) and In4.Cu (SIG2):

- Byte lane 0 (DQ[7:0], DQS0, DM0): match lengths within +/- 25 mil
- Byte lane 1 (DQ[15:8], DQS1, DM1): match lengths within +/- 25 mil
- Byte lane 2 (DQ[23:16], DQS2, DM2): match lengths within +/- 25 mil
- Byte lane 3 (DQ[31:24], DQS3, DM3): match lengths within +/- 25 mil

DQS pairs: 100-ohm differential, route as diff pairs.

**Step 2: DDR3L address/command routing**

- Fly-by topology: Zynq → U_DDR0 → U_DDR1
- Address A[14:0], BA[2:0], RAS#, CAS#, WE#, CKE, CS#, ODT: match within group +/- 100 mil
- Clock CK/CK#: differential pair, source-terminated (22 ohm series at Zynq end)

**Step 3: Use length-matching tools**

KiCad PCB Editor → Route → Interactive Router → Diff Pair Routing and Length Tuning:
- Add serpentine/meandering to match trace lengths
- Check with Inspect → Board Statistics or DRC length rules

**Step 4: AD9361 LVDS routing**

Route on In2.Cu (SIG1), between GND1 and GND2 reference planes:

- 16 differential pairs: 100-ohm differential impedance
- Width: 0.12 mm, gap: 0.20 mm
- Length matching: +/- 50 mil within each pair, +/- 200 mil between pairs
- Keep total LVDS trace length under 50mm
- No vias in LVDS path if possible (route entirely on SIG1)

**Step 5: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "route DDR3L and LVDS high-speed signals"
```

---

### Task 18: RF Routing

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: 50-ohm microstrip traces**

All RF traces on F.Cu (TOP) only:
- Width: 0.28 mm (50-ohm microstrip over 0.10mm prepreg to GND1, Er=4.2)
- Keep RF traces as short as possible
- No sharp bends; use 45-degree or curved traces
- Maintain 3x trace-width clearance from other signals

**Step 2: Route RX path**

SMA pad → BPF → T/R switch RFC → (RF1) → LNA in → LNA out → SAW → AD9361 RX1A

**Step 3: Route TX path**

AD9361 TX1A → driver amp in → driver amp out → PA in → PA out → harmonic filter → T/R switch (RF2) → RFC → BPF → SMA

**Step 4: Ground via stitching along RF traces**

- Place ground vias every 1mm along both sides of every RF trace
- Via drill: 0.3mm, pad: 0.55mm
- Connects F.Cu ground to GND1 plane

**Step 5: PA thermal vias**

- Under TGA2594 thermal pad: array of 20+ vias (0.3mm drill)
- Grid pattern, ~1mm spacing
- Connects to all ground planes for heat spreading

**Step 6: RF shield can footprint**

- Draw pad outline on F.Cu around RF section
- 1mm wide pads, ~2mm spacing between pads
- Matching ground pour on B.Cu with via connections
- Internal clearance: 2mm from shield to nearest RF component

**Step 7: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "route RF signal paths with microstrip and shielding"
```

---

### Task 19: General Routing

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: Route power distribution**

- Wide traces (0.8mm+) from regulators to bulk capacitors
- Power plane connections via multiple vias from component pads to In5.Cu
- Each Zynq power ball: via to appropriate power plane

**Step 2: Route SPI buses**

- AD9361 SPI: short traces, 33 ohm series resistors near Zynq
- QSPI: route on SIG4 layer if needed, series resistors
- eMMC: route on SIG3/SIG4, keep clock and data matched

**Step 3: Route Ethernet RGMII**

- KSZ9031 to Zynq MIO: length-match TX group and RX group separately
- TX_CLK to TXD skew: per KSZ9031 datasheet requirements
- Route to RJ-45: differential pairs for magnetics interface

**Step 4: Route USB ULPI**

- USB3320C to Zynq MIO: 8 data lines + CLK + DIR + STP + NXT
- Match data lines to CLK +/- 100 mil
- USB D+/D- to connectors: 90-ohm differential pair

**Step 5: Route UART, I2C, GPIO**

- FT232RQ to USB Micro-B: USB pair (90-ohm diff)
- FT232RQ TXD/RXD to Zynq MIO: simple routing
- GPS UART: route to Zynq, include 1PPS to PL bank
- I2C: route with series resistors, pull-ups near devices
- GPIO header: route PL bank pins via series resistors to header

**Step 6: Route Micro-SD**

- SD_CLK, SD_CMD, SD_DAT[3:0] from Zynq MIO to card slot
- Series 33-ohm resistors on all lines
- Keep traces short (<30mm)

**Step 7: Route JTAG**

- TCK, TDI, TDO, TMS from Zynq to 2x7 header
- Series 33-ohm resistors near Zynq

**Step 8: Route LED and button nets**

- Simple routing from PL pins to LEDs/buttons on bottom edge

**Step 9: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "complete general signal routing"
```

---

### Task 20: Copper Fills, Via Stitching, and Silkscreen

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: Ground copper pours**

- F.Cu: ground flood fill on all unused areas
- B.Cu: ground flood fill on all unused areas
- Connect flood fills to GND net
- Minimum pour width: 0.2mm
- Thermal relief on all through-hole pads

**Step 2: Via stitching**

- Board perimeter: ground vias every 2mm, connecting F.Cu/B.Cu floods to internal ground planes
- Around RF section: additional via stitching ring
- Under all BGA ICs: via array connecting B.Cu ground to internal planes

**Step 3: Silkscreen**

- All component reference designators visible and not overlapping pads
- Board title: "CIRRADIO DevBoard v1.0" on F.SilkS
- Pin 1 markers clearly visible for all ICs
- Connector labels (SMA, USB, ETH, JTAG, GPIO, PWR, SD)
- Power rail test point labels
- Placement outline on F.Fab layer

**Step 4: Board edge clearance check**

Verify 0.5mm minimum copper to board edge everywhere.

**Step 5: Commit**

```bash
git add hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
git commit -m "add copper fills, via stitching, and silkscreen"
```

---

## Phase E: Verification and Manufacturing

### Task 21: Design Rule Check

**Files:**
- Modify: `hardware/cirradio-devboard/cirradio-devboard.kicad_pcb`

**Step 1: Run DRC**

Inspect → Design Rules Check. Fix all violations:
- Clearance violations
- Unconnected nets (ratsnest)
- Via-in-pad violations (ensure filled/capped vias are configured correctly)
- Minimum width violations
- Courtyard overlap

**Step 2: Run ERC on final schematic**

Re-run ERC after any schematic changes during layout. Zero errors required.

**Step 3: Cross-check critical nets**

Manually verify these nets are correctly connected:
- [ ] All Zynq VCCINT pins → +1V0
- [ ] All DDR3 DQ pins → correct Zynq DDR balls
- [ ] AD9361 LVDS pairs → correct Zynq HP bank pins
- [ ] Power sequencing chain (PG → EN)
- [ ] PS_POR_B connected to supervisor output
- [ ] RF path continuity: SMA → BPF → T/R → LNA → SAW → AD9361

**Step 4: Impedance verification**

Use a stackup calculator (KiCad built-in or Saturn PCB Toolkit) to verify:
- 50-ohm microstrip on F.Cu: confirm 0.28mm width is correct for actual stackup
- 100-ohm diff stripline on In2.Cu: confirm 0.12mm/0.20mm width/gap
- 50-ohm stripline on In2.Cu/In4.Cu for DDR3: confirm 0.18mm width

**Step 5: Commit**

```bash
git add hardware/cirradio-devboard/
git commit -m "pass DRC and ERC verification"
```

---

### Task 22: Generate Manufacturing Outputs

**Files:**
- Create: `hardware/cirradio-devboard/fab/gerbers/*.gbr`
- Create: `hardware/cirradio-devboard/fab/gerbers/*.drl`
- Create: `hardware/cirradio-devboard/fab/bom/bom.csv`
- Create: `hardware/cirradio-devboard/fab/assembly/positions.csv`

**Step 1: Generate Gerber files**

File → Fabrication Outputs → Gerbers:
- All 10 copper layers
- F.Mask, B.Mask (solder mask)
- F.SilkS, B.SilkS (silkscreen)
- F.Paste, B.Paste (stencil)
- Edge.Cuts (board outline)
- Output: `fab/gerbers/`

Drill files:
- File → Fabrication Outputs → Drill Files
- Excellon format, PTH and NPTH separate
- Output: `fab/gerbers/`

Or via CLI:
```bash
kicad-cli pcb export gerbers \
  --output hardware/cirradio-devboard/fab/gerbers/ \
  hardware/cirradio-devboard/cirradio-devboard.kicad_pcb

kicad-cli pcb export drill \
  --output hardware/cirradio-devboard/fab/gerbers/ \
  hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
```

**Step 2: Generate BOM**

```bash
kicad-cli sch export bom \
  --output hardware/cirradio-devboard/fab/bom/bom.csv \
  hardware/cirradio-devboard/cirradio-devboard.kicad_sch
```

Verify BOM contains:
- All components with reference designators
- Part numbers (MPN)
- Values
- Footprints
- Quantities

**Step 3: Generate pick-and-place file**

```bash
kicad-cli pcb export pos \
  --output hardware/cirradio-devboard/fab/assembly/positions.csv \
  --format csv \
  hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
```

**Step 4: Generate 3D rendering**

Optional but useful for review:
```bash
kicad-cli pcb export vrml \
  --output hardware/cirradio-devboard/fab/cirradio-devboard.wrl \
  hardware/cirradio-devboard/cirradio-devboard.kicad_pcb
```

**Step 5: Create fab notes**

Create `hardware/cirradio-devboard/fab/fab-notes.txt`:
```
CIRRADIO Dev Board v1.0
Fabrication Notes

Layer count: 10
Board size: 160 x 100 mm
Board thickness: 1.6 mm
Copper weight: 1 oz all layers
Surface finish: ENIG (for BGA reliability)
Solder mask: green
Silkscreen: white
Min trace/space: 0.1mm / 0.1mm
Min drill: 0.2mm
Via-in-pad: Yes, filled and capped (for BGA breakout)
Impedance control: Yes
  - 50 ohm single-ended microstrip (F.Cu): 0.28mm trace, ref GND1
  - 100 ohm differential stripline (In2.Cu): 0.12mm trace, 0.20mm gap, ref GND1/GND2
  - 50 ohm single-ended stripline (In2.Cu/In4.Cu): 0.18mm trace
Material: FR-4 (TG170+ for lead-free assembly)
IPC Class: 2
```

**Step 6: Verify Gerbers in viewer**

Open Gerbers in KiCad GerbView or online viewer (e.g., tracespace.io):
- All layers align correctly
- Board outline matches dimensions
- Drill hits align with pads
- No missing features or artifacts

**Step 7: Commit**

```bash
git add hardware/cirradio-devboard/fab/fab-notes.txt
git commit -m "generate manufacturing outputs and fab notes"
```

---

## Summary

| Phase | Tasks | Estimated Effort |
|-------|-------|-----------------|
| A: Project Setup | 1-2 | Setup + design rules |
| B: Component Libraries | 3-5 | Symbol/footprint creation |
| C: Schematic Capture | 6-13 | 8 sheets + top-level + ERC |
| D: PCB Layout | 14-20 | Placement + routing + fills |
| E: Verification + Mfg | 21-22 | DRC + Gerbers + BOM |

**Critical path items:**
1. Zynq-7045 symbol (900 pins -- verify against UG865 pinout)
2. DDR3L routing (tight length-matching required)
3. AD9361 LVDS routing (100-ohm differential impedance)
4. RF trace impedance (stackup-dependent, verify with calculator)
5. Power sequencing (must follow Xilinx-specified order)

**Before sending to fab:**
- [ ] DRC passes with zero errors
- [ ] ERC passes with zero errors
- [ ] All BGA footprints verified against manufacturer package drawings
- [ ] Impedance calculations verified against actual fab stackup data
- [ ] Gerbers reviewed in independent viewer
- [ ] BOM complete with all part numbers and quantities
