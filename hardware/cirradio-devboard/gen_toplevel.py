#!/usr/bin/env python3
"""Generate top-level schematic for CIRRADIO dev board.

Creates cirradio-devboard.kicad_sch with:
- 7 hierarchical sheet references to sub-schematics
- Block diagram annotations showing signal flow
- Title block with project metadata

All inter-sheet connectivity uses global labels defined in the
sub-schematics, so no hierarchical pins are needed on the sheet symbols.
"""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

lines = []
def emit(s):
    lines.append(s)

def text_note(txt, x, y, size=2.0):
    emit(f'    (text "{txt}" (at {x} {y} 0) (effects (font (size {size} {size}))))')

def rect_note(x1, y1, x2, y2, width=0.2, color_r=0, color_g=0, color_b=0, color_a=1.0,
              fill_r=255, fill_g=255, fill_b=255, fill_a=0.0):
    """Emit a rectangle annotation (polyline box)."""
    emit(f'    (polyline')
    emit(f'      (pts')
    emit(f'        (xy {x1} {y1})')
    emit(f'        (xy {x2} {y1})')
    emit(f'        (xy {x2} {y2})')
    emit(f'        (xy {x1} {y2})')
    emit(f'        (xy {x1} {y1})')
    emit(f'      )')
    emit(f'      (stroke (width {width}) (type dash) (color {color_r} {color_g} {color_b} {color_a}))')
    emit(f'      (uuid "{uid()}")')
    emit(f'    )')

def arrow_line(x1, y1, x2, y2, width=0.3):
    """Emit a line (used for signal flow arrows in annotations)."""
    emit(f'    (polyline')
    emit(f'      (pts (xy {x1} {y1}) (xy {x2} {y2}))')
    emit(f'      (stroke (width {width}) (type default) (color 0 100 0 1.0))')
    emit(f'      (uuid "{uid()}")')
    emit(f'    )')

def sheet_ref(name, filename, x, y, w, h):
    """Emit a hierarchical sheet reference."""
    emit(f'    (sheet (at {x} {y}) (size {w} {h})')
    emit(f'      (stroke (width 0.001) (type solid))')
    emit(f'      (fill (color 255 255 255 1.0))')
    emit(f'      (uuid "{uid()}")')
    emit(f'      (property "Sheetname" "{name}" (at {x} {y - 1} 0)')
    emit(f'        (effects (font (size 1.27 1.27))))')
    emit(f'      (property "Sheetfile" "{filename}" (at {x} {y + h + 1} 0)')
    emit(f'        (effects (font (size 1.27 1.27))))')
    emit(f'    )')


def main():
    # ================================================================
    # A3 paper: 420 x 297 mm
    # Layout plan (approximate positions on A3):
    #
    #   Top-left:     RF Front-End        Top-center:    AD9361 + LVDS
    #   Center:       Zynq-7045           Center-right:  DDR3L Memory
    #   Bottom-left:  Power Supply        Bottom-center: Peripherals
    #   Bottom-right: Connectors & Debug
    #
    # ================================================================

    # --- Header ---
    emit('(kicad_sch')
    emit('  (version 20231120)')
    emit('  (generator "custom")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "Tactical SDR Development Board")')
    emit('    (comment 2 "Zynq-7045 + AD9361")')
    emit('  )')
    emit('')

    # --- Lib symbols (empty - top-level has no placed components) ---
    emit('  (lib_symbols)')
    emit('')

    # ================================================================
    # HIERARCHICAL SHEET REFERENCES
    # ================================================================
    # Sheet dimensions and positions (x, y, width, height)
    # A3 usable area roughly 20..400, 20..280

    sheets = [
        # (name, filename, x, y, w, h)
        ("Power Supply",      "power.kicad_sch",        30,  195, 60, 30),
        ("Zynq-7045",         "zynq.kicad_sch",         145, 105, 70, 45),
        ("DDR3L Memory",      "ddr3l.kicad_sch",        270, 105, 55, 35),
        ("AD9361 + LVDS",     "ad9361.kicad_sch",       165, 30,  65, 40),
        ("RF Front-End",      "rf-frontend.kicad_sch",  30,  30,  65, 40),
        ("Peripherals",       "peripherals.kicad_sch",  145, 195, 65, 30),
        ("Connectors & Debug","connectors.kicad_sch",   270, 195, 65, 30),
    ]

    for name, filename, x, y, w, h in sheets:
        sheet_ref(name, filename, x, y, w, h)

    emit('')

    # ================================================================
    # BLOCK DIAGRAM ANNOTATIONS
    # ================================================================

    # --- Title text ---
    text_note("CIRRADIO Tactical SDR - Top-Level Block Diagram", 130, 12, 3.0)

    # --- Group labels inside/near each sheet block ---
    # RF Front-End
    text_note("225-512 MHz", 40, 53, 1.5)
    text_note("SMA, BPF, T/R Switch", 40, 57, 1.27)
    text_note("LNA, SAW, TX Driver, PA", 40, 61, 1.27)

    # AD9361
    text_note("AD9361 RF Transceiver", 175, 43, 1.5)
    text_note("LVDS Data Interface", 175, 47, 1.27)
    text_note("SPI Control", 175, 51, 1.27)

    # Zynq
    text_note("Xilinx Zynq-7045 SoC", 155, 118, 1.5)
    text_note("ARM Cortex-A9 + FPGA", 155, 122, 1.27)
    text_note("PS MIO + PL GPIO", 155, 126, 1.27)

    # DDR3L
    text_note("DDR3L x32 Memory", 280, 118, 1.5)
    text_note("2x MT41K256M16", 280, 122, 1.27)
    text_note("533 MHz / 1066 MT/s", 280, 126, 1.27)

    # Power
    text_note("Power Management", 40, 208, 1.5)
    text_note("+12V -> 5V/3.3V/1.8V/1.5V/1.35V/1.0V", 40, 212, 1.27)
    text_note("Sequenced rails, POR", 40, 216, 1.27)

    # Peripherals
    text_note("GbE, USB, I2C EEPROM", 155, 208, 1.5)
    text_note("GPS, uSD, QSPI Flash", 155, 212, 1.27)

    # Connectors
    text_note("JTAG, UART, FMC-LPC", 280, 208, 1.5)
    text_note("PL GPIO Header", 280, 212, 1.27)

    emit('')

    # ================================================================
    # SIGNAL FLOW ANNOTATIONS (arrows and labels between blocks)
    # ================================================================

    # --- RF Front-End <-> AD9361: RF ports ---
    # Arrow from RF sheet right edge to AD9361 sheet left edge
    arrow_line(95, 50, 165, 50)
    text_note("RF Ports (RX/TX)", 110, 46, 1.27)

    # --- AD9361 <-> Zynq: LVDS data + SPI ---
    # Arrow from AD9361 bottom to Zynq top
    arrow_line(195, 70, 180, 105)
    text_note("LVDS Data + SPI Control", 183, 88, 1.27)

    # --- Zynq <-> DDR3L: DDR3 bus ---
    # Arrow from Zynq right to DDR3L left
    arrow_line(215, 127, 270, 122)
    text_note("DDR3 Bus (Addr/Data/Ctrl)", 225, 115, 1.27)

    # --- Zynq <-> Peripherals: MIO ---
    # Arrow from Zynq bottom to Peripherals top
    arrow_line(180, 150, 180, 195)
    text_note("PS MIO Groups", 183, 175, 1.27)

    # --- Zynq <-> Connectors: PL GPIO + debug ---
    # Arrow from Zynq bottom-right to Connectors top
    arrow_line(210, 150, 300, 195)
    text_note("PL GPIO + JTAG/UART", 240, 170, 1.27)

    # --- Power -> All: Power rails ---
    # Arrow from Power top to Zynq (representative of all blocks)
    arrow_line(60, 195, 60, 155)
    arrow_line(60, 155, 145, 135)
    text_note("Power Rails + POR", 70, 160, 1.27)

    # Arrow from Power up to RF Front-End
    arrow_line(50, 195, 50, 70)
    text_note("+3V3, +3V3A, +5V_PA", 32, 140, 1.0)

    # Arrow from Power to AD9361
    arrow_line(70, 195, 180, 70)
    text_note("+1V8, +3V3A", 110, 130, 1.0)

    # Arrow from Power to DDR3L
    arrow_line(80, 195, 290, 140)
    text_note("+1V35, VTT", 170, 165, 1.0)

    # Arrow from Power to Peripherals
    arrow_line(90, 215, 145, 210)
    text_note("+3V3, +1V8", 110, 220, 1.0)

    # Arrow from Power to Connectors
    arrow_line(90, 220, 270, 210)
    text_note("+3V3", 175, 222, 1.0)

    emit('')

    # ================================================================
    # GLOBAL LABEL SUMMARY NOTES
    # ================================================================
    text_note("INTER-SHEET CONNECTIVITY (via Global Labels)", 30, 250, 2.0)
    text_note("Power rails: +1V0, +1V35, +1V5, +1V8, +3V3, +3V3A, +5V, +5V_PA, VTT, VTTREF", 30, 255, 1.0)
    text_note("Power control: +1V0_EN/PG, +1V35_EN/PG, +1V5_EN/PG, +1V8_EN/PG, +3V3_EN/PG, +5V_EN/PG, PS_POR_B", 30, 259, 1.0)
    text_note("Peripherals: ETH_MDC, ETH_MDIO, GPS_1PPS", 30, 263, 1.0)
    text_note("Connectors: PS_CLK, PS_UART0_TX/RX, PS_SPI_*, PS_I2C_*", 30, 267, 1.0)

    emit('')

    # ================================================================
    # DESIGN NOTES
    # ================================================================
    text_note("DESIGN NOTES", 30, 275, 1.5)
    text_note("1. All inter-sheet signals use global labels - no explicit wires on top-level", 30, 279, 1.0)
    text_note("2. Power sequencing: +5V -> +3V3/+3V3A -> +1V8 -> +1V5 -> +1V35 -> +1V0 -> PS_POR_B", 30, 283, 1.0)
    text_note("3. DDR3L requires VTT termination and VTTREF midpoint from power sheet", 30, 287, 1.0)
    text_note("4. AD9361 LVDS pairs: matched-length differential routing required", 30, 291, 1.0)

    # ================================================================
    # SYMBOL INSTANCES (empty - no placed symbols on top-level)
    # ================================================================
    emit('  (symbol_instances)')

    # ================================================================
    # SHEET INSTANCES
    # ================================================================
    emit('  (sheet_instances')
    emit('    (path "/"')
    emit('      (page "1")')
    emit('    )')
    emit('  )')

    # Close schematic
    emit(')')

    # --- Write output ---
    output = '\n'.join(lines)

    # Verify parenthesis balance
    opens = output.count('(')
    closes = output.count(')')
    if opens != closes:
        print(f"ERROR: Parenthesis imbalance! Opens: {opens}, Closes: {closes}", file=sys.stderr)
        depth = 0
        for i, ch in enumerate(output):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth < 0:
                line_num = output[:i].count('\n') + 1
                print(f"  Extra ')' at character {i}, line {line_num}", file=sys.stderr)
                break
        if depth > 0:
            print(f"  Missing {depth} closing parentheses at end", file=sys.stderr)
        sys.exit(1)

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/cirradio-devboard.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"  Sheet references: 7")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")


if __name__ == "__main__":
    main()
