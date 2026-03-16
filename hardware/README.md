# Hardware — CIRRADIO Dev Board

Custom 8-layer dev board for the CIRRADIO radio. Designed for bring-up and
field testing. Not yet fabricated.

## Board Overview

| Component         | Part / Notes                                        |
|-------------------|-----------------------------------------------------|
| SoC               | Xilinx Zynq-7045 (xc7z045ffg900-2)                 |
| RF Transceiver    | Analog Devices AD9361 (70 MHz – 6 GHz)              |
| DDR3L RAM         | 1 GB DDR3L-1333, 32-bit bus                         |
| HSM               | PKCS#11-compatible HSM module slot (SPI/I2C)        |
| GPS               | u-blox NEO-M8N, 1PPS output                         |
| RF Front-End      | LNA (low-noise amp), PA (power amp), bandpass filter,|
|                   | RF T/R switch, SMA connector                        |
| Power             | 5 V DC input, LDOs for 1.8 V / 1.0 V / 3.3 V rails |
| Interfaces        | USB-UART (debug), JTAG (Vivado), Gigabit Ethernet   |

## Schematic and PCB Generation

The board design is captured as Python generators that produce KiCad
S-expression files (`.kicad_sch`, `.kicad_pcb`). Requires KiCad 7+.

```bash
cd hardware/cirradio-devboard

# Generate all schematics
python3 gen_power_sch.py
python3 gen_zynq.py
python3 gen_ddr3l.py
python3 gen_ad9361.py
python3 gen_rf.py
python3 gen_peripherals.py
python3 gen_connectors.py

# Generate PCB (netlist → placement → planes → routing)
python3 gen_pcb_netlist.py
python3 gen_pcb_placement.py
python3 gen_pcb_planes.py
python3 gen_pcb_routing.py

# DRC check
python3 gen_pcb_drc.py
# Expected: PASS — 434 nets, 316 components, 717 segments, 394 vias, 13 zones
```

## Fabrication Notes

See [`hardware/cirradio-devboard/fab/fab-notes.txt`](cirradio-devboard/fab/fab-notes.txt)
for stackup, controlled impedance specs, drill requirements, and surface finish.

## Board Status

Design complete. PCB not yet fabricated. Board bring-up scripts (SSH + serial
console) are in [`tools/board-test/`](../tools/board-test/README.md) and support
`--dry-run` mode for local verification.
