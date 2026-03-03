#!/usr/bin/env python3
"""Generate AD9361 + LVDS interface schematic sheet for CIRRADIO dev board."""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

# Reference designator counters - start at 200 to avoid conflicts with other sheets
cap_idx = [200]
res_idx = [200]
pwr_idx = [200]
u_idx = [11]

def next_cap():
    c = cap_idx[0]; cap_idx[0] += 1; return f"C{c}"

def next_res():
    r = res_idx[0]; res_idx[0] += 1; return f"R{r}"

def next_pwr():
    p = pwr_idx[0]; pwr_idx[0] += 1; return f"#PWR{p:04d}"

def next_u():
    u = u_idx[0]; u_idx[0] += 1; return f"U{u}"

# Track component counts
counts = {"capacitors": 0, "resistors": 0, "symbols": 0, "wires": 0,
           "labels": 0, "gl_labels": 0, "hier_labels": 0}

lines = []
def emit(s):
    lines.append(s)

def symbol_instance(lib_id, ref, value, at_x, at_y, unit=1, angle=0, footprint="", mirror=""):
    """Emit a symbol placement."""
    counts["symbols"] += 1
    u = uid()
    at_str = f"(at {at_x} {at_y} {angle})"
    if mirror:
        at_str = f"(at {at_x} {at_y} {angle}) (mirror {mirror})"
    emit(f'    (symbol (lib_id "{lib_id}") {at_str}')
    emit(f'      (unit {unit}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)')
    emit(f'      (uuid "{u}")')
    emit(f'      (property "Reference" "{ref}" (at {at_x} {at_y - 2} 0) (effects (font (size 1.27 1.27))))')
    emit(f'      (property "Value" "{value}" (at {at_x} {at_y + 2} 0) (effects (font (size 1.27 1.27))))')
    fp = footprint if footprint else ""
    emit(f'      (property "Footprint" "{fp}" (at {at_x} {at_y} 0) (effects (font (size 1.27 1.27)) hide))')
    emit(f'      (property "Datasheet" "" (at {at_x} {at_y} 0) (effects (font (size 1.27 1.27)) hide))')

def symbol_pins(pin_list):
    """Emit pin UUIDs for a symbol."""
    for p in pin_list:
        emit(f'      (pin "{p}" (uuid "{uid()}"))')
    emit('    )')

def wire(x1, y1, x2, y2):
    counts["wires"] += 1
    emit(f'    (wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid()}"))')

def global_label(name, x, y, shape="passive", angle=0):
    counts["gl_labels"] += 1
    emit(f'    (global_label "{name}" (shape {shape}) (at {x} {y} {angle}) (effects (font (size 1.27 1.27))) (uuid "{uid()}")')
    emit(f'      (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} 0) (effects (font (size 0.5 0.5)) hide))')
    emit(f'    )')

def hier_label(name, x, y, shape="bidirectional", angle=0):
    counts["hier_labels"] += 1
    emit(f'    (hierarchical_label "{name}" (shape {shape}) (at {x} {y} {angle}) (effects (font (size 1.27 1.27))) (uuid "{uid()}"))')

def text_note(txt, x, y, size=2.0):
    emit(f'    (text "{txt}" (at {x} {y} 0) (effects (font (size {size} {size}))))')

def power_symbol(net, x, y, angle=0):
    """Place a power symbol (GND or +rail)."""
    ref = next_pwr()
    lib = f"power:{net}"
    symbol_instance(lib, ref, net, x, y, angle=angle)
    symbol_pins(["1"])

def cap(value, x, y, fp="Capacitor_SMD:C_0402_1005Metric"):
    """Place a capacitor."""
    counts["capacitors"] += 1
    ref = next_cap()
    symbol_instance("Device:C", ref, value, x, y, footprint=fp)
    symbol_pins(["1", "2"])

def resistor(value, x, y, angle=0):
    counts["resistors"] += 1
    ref = next_res()
    symbol_instance("Device:R", ref, value, x, y, angle=angle)
    symbol_pins(["1", "2"])


def decoupling_group(rail_net, x, y, n_100nf, n_10uf, label_text):
    """Place a group of decoupling caps for a power rail."""
    text_note(f"{label_text} decoupling", x, y - 5, 1.27)
    global_label(rail_net, x, y - 2, "passive")
    wire(x, y - 2, x, y)

    cx = x
    for i in range(n_100nf):
        wire(cx, y, cx, y + 1.27)
        cap("100n", cx, y + 5.08, "Capacitor_SMD:C_0402_1005Metric")
        wire(cx, y + 8.89, cx, y + 10)
        power_symbol("GND", cx, y + 10)
        cx += 5

    for i in range(n_10uf):
        wire(cx, y, cx, y + 1.27)
        cap("10u", cx, y + 5.08, "Capacitor_SMD:C_0805_2012Metric")
        wire(cx, y + 8.89, cx, y + 10)
        power_symbol("GND", cx, y + 10)
        cx += 5

    if n_100nf + n_10uf > 1:
        wire(x, y, x + (n_100nf + n_10uf - 1) * 5, y)

    return cx


def emit_lib_symbols():
    """Emit the lib_symbols section with all needed symbol definitions."""
    emit('  (lib_symbols')

    # Device:R
    emit('''    (symbol "Device:R"
      (pin_names (offset 0) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "R" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Value" "R" (at -2.032 0 90) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at -1.778 0 90) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "R_0_1"
        (rectangle (start -1.016 -2.54) (end 1.016 2.54) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Device:C
    emit('''    (symbol "Device:C"
      (pin_names (offset 0.254) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "C" (at 1.524 1.651 0) (effects (font (size 1.27 1.27)) (justify left)))
      (property "Value" "C" (at 1.524 -1.651 0) (effects (font (size 1.27 1.27)) (justify left)))
      (property "Footprint" "" (at 0.9652 -3.81 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "C_0_1"
        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
      )
      (symbol "C_1_1"
        (pin passive line (at 0 3.81 270) (length 3.048) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 3.048) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # AD9361BBCZ - 4-unit symbol (inline from library)
    emit('''    (symbol "cirradio:AD9361BBCZ"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 1.27 0) (effects (font (size 1.27 1.27))))
      (property "Value" "AD9361BBCZ" (at 0 -1.27 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "AD9361BBCZ_0_1"
        (rectangle (start -15.24 43.18) (end 15.24 -43.18) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "AD9361BBCZ_1_1"''')

    # Unit 1: LVDS data interface
    lvds_data_pins = [
        ("P0_D0+","L3",40.64),("P0_D0-","L2",38.1),
        ("P0_D1+","L5",35.56),("P0_D1-","L4",33.02),
        ("P0_D2+","K3",30.48),("P0_D2-","K2",27.94),
        ("P0_D3+","K5",25.4),("P0_D3-","K4",22.86),
        ("P0_D4+","J3",20.32),("P0_D4-","J2",17.78),
        ("P0_D5+","J5",15.24),("P0_D5-","J4",12.7),
        ("P0_D6+","H3",10.16),("P0_D6-","H2",7.62),
        ("P0_D7+","H5",5.08),("P0_D7-","H4",2.54),
        ("P0_D8+","G3",0),("P0_D8-","G2",-2.54),
        ("P0_D9+","G5",-5.08),("P0_D9-","G4",-7.62),
        ("P0_D10+","F3",-10.16),("P0_D10-","F2",-12.7),
        ("P0_D11+","F5",-15.24),("P0_D11-","F4",-17.78),
    ]
    for name, num, y in lvds_data_pins:
        emit(f'        (pin bidirectional line (at 17.78 {y} 180) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')

    lvds_clk_pins = [
        ("DATA_CLK+","M5",40.64,"output"),("DATA_CLK-","M4",38.1,"output"),
        ("FB_CLK+","M3",35.56,"input"),("FB_CLK-","M2",33.02,"input"),
        ("RX_FRAME+","E3",27.94,"output"),("RX_FRAME-","E2",25.4,"output"),
        ("TX_FRAME+","E5",22.86,"input"),("TX_FRAME-","E4",20.32,"input"),
    ]
    for name, num, y, ptype in lvds_clk_pins:
        emit(f'        (pin {ptype} line (at -17.78 {y} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')

    emit('      )')

    # Unit 2: SPI + Control
    emit('''      (symbol "AD9361BBCZ_2_1"
        (rectangle (start -12.7 20.32) (end 12.7 -20.32) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin input line (at -15.24 17.78 0) (length 2.54) (name "SPI_CLK" (effects (font (size 1.27 1.27)))) (number "A6" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 15.24 0) (length 2.54) (name "SPI_DI" (effects (font (size 1.27 1.27)))) (number "A5" (effects (font (size 1.27 1.27)))))
        (pin output line (at -15.24 12.7 0) (length 2.54) (name "SPI_DO" (effects (font (size 1.27 1.27)))) (number "A4" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 10.16 0) (length 2.54) (name "SPI_ENB" (effects (font (size 1.27 1.27)))) (number "A7" (effects (font (size 1.27 1.27)))))
        (pin input line (at 15.24 17.78 180) (length 2.54) (name "CTRL_IN0" (effects (font (size 1.27 1.27)))) (number "D1" (effects (font (size 1.27 1.27)))))
        (pin input line (at 15.24 15.24 180) (length 2.54) (name "CTRL_IN1" (effects (font (size 1.27 1.27)))) (number "C1" (effects (font (size 1.27 1.27)))))
        (pin input line (at 15.24 12.7 180) (length 2.54) (name "CTRL_IN2" (effects (font (size 1.27 1.27)))) (number "B1" (effects (font (size 1.27 1.27)))))
        (pin input line (at 15.24 10.16 180) (length 2.54) (name "CTRL_IN3" (effects (font (size 1.27 1.27)))) (number "A1" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 5.08 180) (length 2.54) (name "CTRL_OUT0" (effects (font (size 1.27 1.27)))) (number "D3" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 2.54 180) (length 2.54) (name "CTRL_OUT1" (effects (font (size 1.27 1.27)))) (number "D4" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 0 180) (length 2.54) (name "CTRL_OUT2" (effects (font (size 1.27 1.27)))) (number "D5" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 -2.54 180) (length 2.54) (name "CTRL_OUT3" (effects (font (size 1.27 1.27)))) (number "C2" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 -5.08 180) (length 2.54) (name "CTRL_OUT4" (effects (font (size 1.27 1.27)))) (number "C3" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 -7.62 180) (length 2.54) (name "CTRL_OUT5" (effects (font (size 1.27 1.27)))) (number "C4" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 -10.16 180) (length 2.54) (name "CTRL_OUT6" (effects (font (size 1.27 1.27)))) (number "C5" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 -12.7 180) (length 2.54) (name "CTRL_OUT7" (effects (font (size 1.27 1.27)))) (number "B2" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 5.08 0) (length 2.54) (name "EN_AGC" (effects (font (size 1.27 1.27)))) (number "B3" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 2.54 0) (length 2.54) (name "ENABLE" (effects (font (size 1.27 1.27)))) (number "B4" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 0 0) (length 2.54) (name "TXNRX" (effects (font (size 1.27 1.27)))) (number "B5" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 -5.08 0) (length 2.54) (name "RESETB" (effects (font (size 1.27 1.27)))) (number "A3" (effects (font (size 1.27 1.27)))))
      )''')

    # Unit 3: RF + Clock
    emit('''      (symbol "AD9361BBCZ_3_1"
        (rectangle (start -12.7 22.86) (end 12.7 -22.86) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -15.24 20.32 0) (length 2.54) (name "RX1A_P" (effects (font (size 1.27 1.27)))) (number "K12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 17.78 0) (length 2.54) (name "RX1A_N" (effects (font (size 1.27 1.27)))) (number "L12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 15.24 0) (length 2.54) (name "RX1B_P" (effects (font (size 1.27 1.27)))) (number "J11" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 12.7 0) (length 2.54) (name "RX1B_N" (effects (font (size 1.27 1.27)))) (number "J12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 10.16 0) (length 2.54) (name "RX1C_P" (effects (font (size 1.27 1.27)))) (number "H11" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 7.62 0) (length 2.54) (name "RX1C_N" (effects (font (size 1.27 1.27)))) (number "H12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 2.54 0) (length 2.54) (name "RX2A_P" (effects (font (size 1.27 1.27)))) (number "G11" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 0 0) (length 2.54) (name "RX2A_N" (effects (font (size 1.27 1.27)))) (number "G12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 20.32 180) (length 2.54) (name "TX1A" (effects (font (size 1.27 1.27)))) (number "E12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 17.78 180) (length 2.54) (name "TX1B" (effects (font (size 1.27 1.27)))) (number "D12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 12.7 180) (length 2.54) (name "TX2A" (effects (font (size 1.27 1.27)))) (number "C12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 -5.08 0) (length 2.54) (name "XTALP" (effects (font (size 1.27 1.27)))) (number "A12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 -7.62 0) (length 2.54) (name "XTALN" (effects (font (size 1.27 1.27)))) (number "A11" (effects (font (size 1.27 1.27)))))
      )''')

    # Unit 4: Power
    emit('''      (symbol "AD9361BBCZ_4_1"
        (rectangle (start -12.7 27.94) (end 12.7 -27.94) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin power_in line (at -15.24 25.4 0) (length 2.54) (name "VDDA1P3_BB" (effects (font (size 1.27 1.27)))) (number "M12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 22.86 0) (length 2.54) (name "VDDA1P3_BB" (effects (font (size 1.27 1.27)))) (number "M11" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 20.32 0) (length 2.54) (name "VDDA1P3_RX" (effects (font (size 1.27 1.27)))) (number "F12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 17.78 0) (length 2.54) (name "VDDA1P3_RX" (effects (font (size 1.27 1.27)))) (number "F11" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 15.24 0) (length 2.54) (name "VDDA1P3_TX" (effects (font (size 1.27 1.27)))) (number "B12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 12.7 0) (length 2.54) (name "VDDA1P3_TX" (effects (font (size 1.27 1.27)))) (number "B11" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 7.62 0) (length 2.54) (name "VDDD1P3_DIG" (effects (font (size 1.27 1.27)))) (number "M1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 5.08 0) (length 2.54) (name "VDDD1P3_DIG" (effects (font (size 1.27 1.27)))) (number "L1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 0 0) (length 2.54) (name "VDDD_IF" (effects (font (size 1.27 1.27)))) (number "D2" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 -2.54 0) (length 2.54) (name "VDDD_IF" (effects (font (size 1.27 1.27)))) (number "E1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 -7.62 0) (length 2.54) (name "VDDA3P3" (effects (font (size 1.27 1.27)))) (number "A10" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 -10.16 0) (length 2.54) (name "VDDA3P3" (effects (font (size 1.27 1.27)))) (number "A9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 25.4 180) (length 2.54) (name "GNDA" (effects (font (size 1.27 1.27)))) (number "K11" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 22.86 180) (length 2.54) (name "GNDA" (effects (font (size 1.27 1.27)))) (number "L11" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 20.32 180) (length 2.54) (name "GNDA" (effects (font (size 1.27 1.27)))) (number "M10" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 17.78 180) (length 2.54) (name "GNDA" (effects (font (size 1.27 1.27)))) (number "M9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 15.24 180) (length 2.54) (name "GNDA" (effects (font (size 1.27 1.27)))) (number "M8" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 12.7 180) (length 2.54) (name "GNDA" (effects (font (size 1.27 1.27)))) (number "M7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 7.62 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "M6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 5.08 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "L6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 2.54 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "K6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 0 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "J6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 -2.54 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "H6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 -5.08 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "G6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 -7.62 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "F6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 -10.16 180) (length 2.54) (name "GNDD" (effects (font (size 1.27 1.27)))) (number "E6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 15.24 -15.24 180) (length 2.54) (name "DGND_FILT" (effects (font (size 1.27 1.27)))) (number "F1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -15.24 -15.24 0) (length 2.54) (name "VDDD_FILT" (effects (font (size 1.27 1.27)))) (number "G1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -15.24 -20.32 0) (length 2.54) (name "RBIAS" (effects (font (size 1.27 1.27)))) (number "A8" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 -20.32 180) (length 2.54) (name "TEMP_SENSE" (effects (font (size 1.27 1.27)))) (number "A2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # OX200-SC-040.0M OCXO (14-pin DIP, pin 14=VCC, pin 8=OUTPUT, pin 7=GND)
    emit('''    (symbol "cirradio:OX200-SC-040.0M"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "Y" (at 0 8.89 0) (effects (font (size 1.27 1.27))))
      (property "Value" "OX200-SC-040.0M" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "OX200-SC-040.0M_0_1"
        (rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "OX200-SC-040.0M_1_1"
        (pin no_connect line (at -10.16 5.08 0) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at -10.16 2.54 0) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at -10.16 0 0) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at -10.16 -2.54 0) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at -10.16 -5.08 0) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -10.16 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin output line (at 10.16 2.54 180) (length 2.54) (name "OUTPUT" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -2.54 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 0 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 10.16 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Generic LDO (for ADP151-style 1.3V regulator) - SOT-23-5
    emit('''    (symbol "cirradio:LDO_Generic"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "LDO_Generic" (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "LDO_Generic_0_1"
        (rectangle (start -7.62 5.08) (end 7.62 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "LDO_Generic_1_1"
        (pin power_in line (at -10.16 2.54 0) (length 2.54) (name "VIN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -7.62 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin input line (at -10.16 -2.54 0) (length 2.54) (name "EN" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 10.16 -2.54 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin power_out line (at 10.16 2.54 180) (length 2.54) (name "VOUT" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Power symbols
    for net in ["+1V3_AD", "+1V8", "+3V3A", "GND"]:
        if net == "GND":
            emit(f'''    (symbol "power:GND"
      (power) (pin_names (offset 0)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "#PWR" (at 0 -6.35 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "GND" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "GND_0_1"
        (polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "GND_1_1"
        (pin power_in line (at 0 0 270) (length 0) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      )
    )''')
        else:
            emit(f'''    (symbol "power:{net}"
      (power) (pin_names (offset 0)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "{net}" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{net}_0_1"
        (polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "{net}_1_1"
        (pin power_in line (at 0 0 90) (length 0) (name "{net}" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      )
    )''')

    emit('  )')


def main():
    # Header
    emit('(kicad_sch')
    emit('  (version 20231120)')
    emit('  (generator "cirradio_gen_ad9361")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board - AD9361 RF Transceiver + LVDS Interface")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "AD9361BBCZ with OCXO, LVDS, SPI, control, RF ports, power")')
    emit('    (comment 2 "4 units: LVDS, SPI+Control, RF+Clock, Power")')
    emit('  )')
    emit('')

    # Library symbols
    emit_lib_symbols()
    emit('')

    # ================================================================
    # SECTION 1: AD9361 Unit 1 - LVDS Data Interface (top-left)
    # ================================================================
    text_note("AD9361 LVDS DATA INTERFACE (Unit 1)", 30, 20, 2.0)
    text_note("16 LVDS pairs: P0_D[11:0], DATA_CLK, FB_CLK, RX_FRAME, TX_FRAME", 30, 25, 1.27)

    u1_x, u1_y = 100, 80
    symbol_instance("cirradio:AD9361BBCZ", "U10", "AD9361BBCZ", u1_x, u1_y, unit=1,
                    footprint="cirradio:BGA-144_12x12_0.8mm")
    # Unit 1 pin numbers (LVDS data + clocks/frames)
    unit1_pins = ["L3","L2","L5","L4","K3","K2","K5","K4","J3","J2","J5","J4",
                  "H3","H2","H5","H4","G3","G2","G5","G4","F3","F2","F5","F4",
                  "M5","M4","M3","M2","E3","E2","E5","E4"]
    symbol_pins(unit1_pins)

    # Right side: P0_D[11:0] hierarchical labels to Zynq Bank 33
    hl_right = u1_x + 25
    data_pairs = [
        ("P0_D0_P", 40.64), ("P0_D0_N", 38.1),
        ("P0_D1_P", 35.56), ("P0_D1_N", 33.02),
        ("P0_D2_P", 30.48), ("P0_D2_N", 27.94),
        ("P0_D3_P", 25.4),  ("P0_D3_N", 22.86),
        ("P0_D4_P", 20.32), ("P0_D4_N", 17.78),
        ("P0_D5_P", 15.24), ("P0_D5_N", 12.7),
        ("P0_D6_P", 10.16), ("P0_D6_N", 7.62),
        ("P0_D7_P", 5.08),  ("P0_D7_N", 2.54),
        ("P0_D8_P", 0),     ("P0_D8_N", -2.54),
        ("P0_D9_P", -5.08), ("P0_D9_N", -7.62),
        ("P0_D10_P", -10.16), ("P0_D10_N", -12.7),
        ("P0_D11_P", -15.24), ("P0_D11_N", -17.78),
    ]
    for name, y_off in data_pairs:
        y = u1_y + y_off
        wire(u1_x + 17.78, y, hl_right, y)
        hier_label(name, hl_right, y, "bidirectional")

    # Left side: clock and frame signals hierarchical labels
    hl_left = u1_x - 25
    clk_frame_pairs = [
        ("DATA_CLK_P", 40.64), ("DATA_CLK_N", 38.1),
        ("FB_CLK_P", 35.56),   ("FB_CLK_N", 33.02),
        ("RX_FRAME_P", 27.94), ("RX_FRAME_N", 25.4),
        ("TX_FRAME_P", 22.86), ("TX_FRAME_N", 20.32),
    ]
    for name, y_off in clk_frame_pairs:
        y = u1_y + y_off
        wire(u1_x - 17.78, y, hl_left, y)
        hier_label(name, hl_left, y, "bidirectional", 180)

    # ================================================================
    # SECTION 2: AD9361 Unit 2 - SPI + Control (top-right)
    # ================================================================
    text_note("AD9361 SPI + CONTROL (Unit 2)", 200, 20, 2.0)
    text_note("SPI with 33R series, CTRL_IN/OUT, EN_AGC, ENABLE, TXNRX, RESETB", 200, 25, 1.27)

    u2_x, u2_y = 270, 65
    symbol_instance("cirradio:AD9361BBCZ", "U10", "AD9361BBCZ", u2_x, u2_y, unit=2,
                    footprint="cirradio:BGA-144_12x12_0.8mm")
    unit2_pins = ["A6","A5","A4","A7",
                  "D1","C1","B1","A1",
                  "D3","D4","D5","C2","C3","C4","C5","B2",
                  "B3","B4","B5","A3"]
    symbol_pins(unit2_pins)

    # SPI with 33R series resistors -> hierarchical labels
    spi_hl_x = u2_x - 35
    spi_signals = [
        ("AD_SCLK", "SPI_CLK", 17.78),
        ("AD_MOSI", "SPI_DI", 15.24),
        ("AD_MISO", "SPI_DO", 12.7),
        ("AD_CS_N", "SPI_ENB", 10.16),
    ]
    for label_name, pin_name, y_off in spi_signals:
        y = u2_y + y_off
        # 33R series resistor between hier label and pin
        res_x = u2_x - 25
        resistor("33R", res_x, y, angle=90)
        wire(u2_x - 15.24, y, res_x + 3.81, y)
        wire(res_x - 3.81, y, spi_hl_x, y)
        hier_label(label_name, spi_hl_x, y, "bidirectional", 180)

    # Control/status: EN_AGC, ENABLE, TXNRX -> hier labels
    ctrl_in_hl_x = u2_x - 30
    for label_name, y_off in [("EN_AGC", 5.08), ("ENABLE", 2.54), ("TXNRX", 0)]:
        y = u2_y + y_off
        wire(u2_x - 15.24, y, ctrl_in_hl_x, y)
        hier_label(label_name, ctrl_in_hl_x, y, "input", 180)

    # RESETB with 10K pull-up to +1V3_AD
    resetb_y = u2_y - 5.08
    wire(u2_x - 15.24, resetb_y, ctrl_in_hl_x, resetb_y)
    hier_label("RESETB", ctrl_in_hl_x, resetb_y, "input", 180)
    # 10K pull-up
    pu_x = u2_x - 22
    resistor("10K", pu_x, resetb_y - 7, angle=0)
    wire(pu_x, resetb_y - 3.19, pu_x, resetb_y)
    wire(pu_x, resetb_y - 10.81, pu_x, resetb_y - 13)
    power_symbol("+1V3_AD", pu_x, resetb_y - 13)

    # CTRL_IN[3:0] -> hier labels (right side of unit 2)
    ctrl_right_hl = u2_x + 22
    for i in range(4):
        y = u2_y + 17.78 - i * 2.54
        wire(u2_x + 15.24, y, ctrl_right_hl, y)
        hier_label(f"CTRL_IN{i}", ctrl_right_hl, y, "input")

    # CTRL_OUT[7:0] -> hier labels
    for i in range(8):
        y = u2_y + 5.08 - i * 2.54
        wire(u2_x + 15.24, y, ctrl_right_hl, y)
        hier_label(f"CTRL_OUT{i}", ctrl_right_hl, y, "output")

    # ================================================================
    # SECTION 3: AD9361 Unit 3 - RF + Clock (middle area)
    # ================================================================
    text_note("AD9361 RF PORTS + REFERENCE CLOCK (Unit 3)", 30, 175, 2.0)
    text_note("RX1A, TX1A to RF sheet; 40 MHz OCXO reference clock", 30, 180, 1.27)

    u3_x, u3_y = 100, 225
    symbol_instance("cirradio:AD9361BBCZ", "U10", "AD9361BBCZ", u3_x, u3_y, unit=3,
                    footprint="cirradio:BGA-144_12x12_0.8mm")
    unit3_pins = ["K12","L12","J11","J12","H11","H12","G11","G12",
                  "E12","D12","C12","A12","A11"]
    symbol_pins(unit3_pins)

    # RF port hierarchical labels (left side) -> to RF front-end sheet
    rf_hl_x = u3_x - 25
    hier_label("AD_RX1A_P", rf_hl_x, u3_y + 20.32, "input", 180)
    wire(u3_x - 15.24, u3_y + 20.32, rf_hl_x, u3_y + 20.32)
    hier_label("AD_RX1A_N", rf_hl_x, u3_y + 17.78, "input", 180)
    wire(u3_x - 15.24, u3_y + 17.78, rf_hl_x, u3_y + 17.78)

    # TX1A (right side) -> RF sheet
    rf_tx_hl_x = u3_x + 25
    hier_label("AD_TX1A", rf_tx_hl_x, u3_y + 20.32, "output")
    wire(u3_x + 15.24, u3_y + 20.32, rf_tx_hl_x, u3_y + 20.32)

    # Unused RF ports: RX1B, RX1C, RX2A, TX1B, TX2A - leave unconnected with note
    text_note("RX1B/C, RX2A, TX1B, TX2A: unused (NC)", u3_x - 25, u3_y + 10, 1.0)

    # ----------------------------------------------------------------
    # 40 MHz OCXO reference clock circuit
    # ----------------------------------------------------------------
    text_note("40 MHz OCXO (OX200-SC)", 200, 195, 1.27)

    ocxo_x, ocxo_y = 240, 220
    symbol_instance("cirradio:OX200-SC-040.0M", "Y2", "40.000MHz OCXO", ocxo_x, ocxo_y,
                    footprint="cirradio:DIP-14_W7.62mm")
    ocxo_pins = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14"]
    symbol_pins(ocxo_pins)

    # VCC (pin 14) to +3V3A
    power_symbol("+3V3A", ocxo_x, ocxo_y - 14)
    wire(ocxo_x, ocxo_y - 10.16, ocxo_x, ocxo_y - 14)

    # GND (pin 7)
    power_symbol("GND", ocxo_x, ocxo_y + 14)
    wire(ocxo_x, ocxo_y + 10.16, ocxo_x, ocxo_y + 14)

    # OCXO decoupling: 100nF + 10uF on VCC
    cap("100n", ocxo_x + 14, ocxo_y - 8, "Capacitor_SMD:C_0402_1005Metric")
    wire(ocxo_x + 14, ocxo_y - 11.81, ocxo_x + 14, ocxo_y - 14)
    power_symbol("+3V3A", ocxo_x + 14, ocxo_y - 14)
    wire(ocxo_x + 14, ocxo_y - 4.19, ocxo_x + 14, ocxo_y - 2)
    power_symbol("GND", ocxo_x + 14, ocxo_y - 2)

    cap("10u", ocxo_x + 20, ocxo_y - 8, "Capacitor_SMD:C_0805_2012Metric")
    wire(ocxo_x + 20, ocxo_y - 11.81, ocxo_x + 20, ocxo_y - 14)
    power_symbol("+3V3A", ocxo_x + 20, ocxo_y - 14)
    wire(ocxo_x + 20, ocxo_y - 4.19, ocxo_x + 20, ocxo_y - 2)
    power_symbol("GND", ocxo_x + 20, ocxo_y - 2)

    # OCXO OUTPUT (pin 8) -> 100pF AC coupling -> 22R series -> XTALP
    # Output is at (ocxo_x + 10.16, ocxo_y + 2.54)
    out_y = ocxo_y + 2.54

    # 100pF AC coupling cap
    ac_cap_x = ocxo_x + 18
    cap("100p", ac_cap_x, out_y, "Capacitor_SMD:C_0402_1005Metric")
    wire(ocxo_x + 10.16, out_y, ac_cap_x - 3.81, out_y)

    # 22R series resistor
    ser_r_x = ocxo_x + 28
    resistor("22R", ser_r_x, out_y, angle=90)
    wire(ac_cap_x + 3.81, out_y, ser_r_x - 3.81, out_y)

    # Wire from 22R output to XTALP on AD9361 Unit 3
    # XTALP is at (u3_x - 15.24, u3_y - 5.08)
    xtalp_y = u3_y - 5.08
    wire(ser_r_x + 3.81, out_y, ser_r_x + 10, out_y)
    wire(ser_r_x + 10, out_y, ser_r_x + 10, xtalp_y)
    wire(ser_r_x + 10, xtalp_y, u3_x - 15.24, xtalp_y)

    # XTALN: 100pF to GND
    xtaln_y = u3_y - 7.62
    xtaln_cap_x = u3_x - 25
    cap("100p", xtaln_cap_x, xtaln_y + 6, "Capacitor_SMD:C_0402_1005Metric")
    wire(u3_x - 15.24, xtaln_y, xtaln_cap_x, xtaln_y)
    wire(xtaln_cap_x, xtaln_y, xtaln_cap_x, xtaln_y + 2.19)
    wire(xtaln_cap_x, xtaln_y + 9.81, xtaln_cap_x, xtaln_y + 12)
    power_symbol("GND", xtaln_cap_x, xtaln_y + 12)

    # ================================================================
    # SECTION 4: AD9361 Unit 4 - Power (bottom area)
    # ================================================================
    text_note("AD9361 POWER (Unit 4)", 30, 290, 2.0)
    text_note("1.3V LDO from +1V8, per-group decoupling per ADI reference design", 30, 295, 1.27)

    u4_x, u4_y = 100, 360
    symbol_instance("cirradio:AD9361BBCZ", "U10", "AD9361BBCZ", u4_x, u4_y, unit=4,
                    footprint="cirradio:BGA-144_12x12_0.8mm")
    unit4_pins = ["M12","M11","F12","F11","B12","B11","M1","L1",
                  "D2","E1","A10","A9",
                  "K11","L11","M10","M9","M8","M7",
                  "M6","L6","K6","J6","H6","G6","F6","E6",
                  "F1","G1","A8","A2"]
    symbol_pins(unit4_pins)

    # ----------------------------------------------------------------
    # 1.3V LDO (ADP151-style, +1V8 -> +1V3_AD)
    # ----------------------------------------------------------------
    text_note("1.3V LDO (ADP151-style)", 200, 305, 1.27)
    ldo_x, ldo_y = 240, 325
    ldo_ref = next_u()
    symbol_instance("cirradio:LDO_Generic", ldo_ref, "ADP151-1.3", ldo_x, ldo_y,
                    footprint="cirradio:SOT-23-5")
    symbol_pins(["1","2","3","4","5"])

    # LDO VIN from +1V8
    power_symbol("+1V8", ldo_x - 18, ldo_y + 2.54)
    wire(ldo_x - 10.16, ldo_y + 2.54, ldo_x - 18, ldo_y + 2.54)

    # LDO EN tied to VIN (+1V8)
    wire(ldo_x - 10.16, ldo_y - 2.54, ldo_x - 14, ldo_y - 2.54)
    wire(ldo_x - 14, ldo_y - 2.54, ldo_x - 14, ldo_y + 2.54)

    # LDO GND
    power_symbol("GND", ldo_x, ldo_y + 12)
    wire(ldo_x, ldo_y + 7.62, ldo_x, ldo_y + 12)

    # LDO VOUT -> +1V3_AD net
    global_label("+1V3_AD", ldo_x + 18, ldo_y + 2.54, "passive")
    wire(ldo_x + 10.16, ldo_y + 2.54, ldo_x + 18, ldo_y + 2.54)

    # LDO input decoupling: 10uF + 100nF
    cap("10u", ldo_x - 16, ldo_y + 9, "Capacitor_SMD:C_0805_2012Metric")
    wire(ldo_x - 16, ldo_y + 5.19, ldo_x - 16, ldo_y + 2.54)
    wire(ldo_x - 16, ldo_y + 12.81, ldo_x - 16, ldo_y + 15)
    power_symbol("GND", ldo_x - 16, ldo_y + 15)

    cap("100n", ldo_x - 10, ldo_y + 9, "Capacitor_SMD:C_0402_1005Metric")
    wire(ldo_x - 10, ldo_y + 5.19, ldo_x - 10, ldo_y + 2.54)
    wire(ldo_x - 10, ldo_y + 12.81, ldo_x - 10, ldo_y + 15)
    power_symbol("GND", ldo_x - 10, ldo_y + 15)

    # LDO output decoupling: 10uF + 100nF
    cap("10u", ldo_x + 14, ldo_y + 9, "Capacitor_SMD:C_0805_2012Metric")
    wire(ldo_x + 14, ldo_y + 5.19, ldo_x + 14, ldo_y + 2.54)
    wire(ldo_x + 14, ldo_y + 12.81, ldo_x + 14, ldo_y + 15)
    power_symbol("GND", ldo_x + 14, ldo_y + 15)

    cap("100n", ldo_x + 20, ldo_y + 9, "Capacitor_SMD:C_0402_1005Metric")
    wire(ldo_x + 20, ldo_y + 5.19, ldo_x + 20, ldo_y + 2.54)
    wire(ldo_x + 20, ldo_y + 12.81, ldo_x + 20, ldo_y + 15)
    power_symbol("GND", ldo_x + 20, ldo_y + 15)

    # ----------------------------------------------------------------
    # Connect AD9361 power pins to rails
    # ----------------------------------------------------------------
    pwr_left_x = u4_x - 22

    # VDDA1P3_BB (pins M12, M11) -> +1V3_AD
    global_label("+1V3_AD", pwr_left_x, u4_y + 25.4, "passive", 180)
    wire(u4_x - 15.24, u4_y + 25.4, pwr_left_x, u4_y + 25.4)
    wire(u4_x - 15.24, u4_y + 22.86, pwr_left_x + 5, u4_y + 22.86)
    wire(pwr_left_x + 5, u4_y + 22.86, pwr_left_x + 5, u4_y + 25.4)

    # VDDA1P3_RX (pins F12, F11) -> +1V3_AD
    global_label("+1V3_AD", pwr_left_x, u4_y + 20.32, "passive", 180)
    wire(u4_x - 15.24, u4_y + 20.32, pwr_left_x, u4_y + 20.32)
    wire(u4_x - 15.24, u4_y + 17.78, pwr_left_x + 5, u4_y + 17.78)
    wire(pwr_left_x + 5, u4_y + 17.78, pwr_left_x + 5, u4_y + 20.32)

    # VDDA1P3_TX (pins B12, B11) -> +1V3_AD
    global_label("+1V3_AD", pwr_left_x, u4_y + 15.24, "passive", 180)
    wire(u4_x - 15.24, u4_y + 15.24, pwr_left_x, u4_y + 15.24)
    wire(u4_x - 15.24, u4_y + 12.7, pwr_left_x + 5, u4_y + 12.7)
    wire(pwr_left_x + 5, u4_y + 12.7, pwr_left_x + 5, u4_y + 15.24)

    # VDDD1P3_DIG (pins M1, L1) -> +1V3_AD
    global_label("+1V3_AD", pwr_left_x, u4_y + 7.62, "passive", 180)
    wire(u4_x - 15.24, u4_y + 7.62, pwr_left_x, u4_y + 7.62)
    wire(u4_x - 15.24, u4_y + 5.08, pwr_left_x + 5, u4_y + 5.08)
    wire(pwr_left_x + 5, u4_y + 5.08, pwr_left_x + 5, u4_y + 7.62)

    # VDDD_IF (pins D2, E1) -> +1V8
    global_label("+1V8", pwr_left_x, u4_y, "passive", 180)
    wire(u4_x - 15.24, u4_y, pwr_left_x, u4_y)
    wire(u4_x - 15.24, u4_y - 2.54, pwr_left_x + 5, u4_y - 2.54)
    wire(pwr_left_x + 5, u4_y - 2.54, pwr_left_x + 5, u4_y)

    # VDDA3P3 (pins A10, A9) -> +3V3A
    global_label("+3V3A", pwr_left_x, u4_y - 7.62, "passive", 180)
    wire(u4_x - 15.24, u4_y - 7.62, pwr_left_x, u4_y - 7.62)
    wire(u4_x - 15.24, u4_y - 10.16, pwr_left_x + 5, u4_y - 10.16)
    wire(pwr_left_x + 5, u4_y - 10.16, pwr_left_x + 5, u4_y - 7.62)

    # VDDD_FILT -> 100nF to GND (filtered digital supply)
    vfilt_y = u4_y - 15.24
    cap("100n", u4_x - 25, vfilt_y + 6, "Capacitor_SMD:C_0402_1005Metric")
    wire(u4_x - 15.24, vfilt_y, u4_x - 25, vfilt_y)
    wire(u4_x - 25, vfilt_y, u4_x - 25, vfilt_y + 2.19)
    wire(u4_x - 25, vfilt_y + 9.81, u4_x - 25, vfilt_y + 12)
    power_symbol("GND", u4_x - 25, vfilt_y + 12)

    # RBIAS: 10K to GND (precision bias resistor per ADI datasheet)
    rbias_y = u4_y - 20.32
    resistor("10K", u4_x - 25, rbias_y + 5, angle=0)
    wire(u4_x - 15.24, rbias_y, u4_x - 25, rbias_y)
    wire(u4_x - 25, rbias_y, u4_x - 25, rbias_y + 1.19)
    wire(u4_x - 25, rbias_y + 8.81, u4_x - 25, rbias_y + 11)
    power_symbol("GND", u4_x - 25, rbias_y + 11)

    # TEMP_SENSE: leave unconnected (NC note)
    text_note("TEMP_SENSE: NC", u4_x + 20, u4_y - 20.32, 1.0)

    # GNDA pins -> GND
    pwr_right_x = u4_x + 22
    power_symbol("GND", pwr_right_x, u4_y + 25.4)
    wire(u4_x + 15.24, u4_y + 25.4, pwr_right_x, u4_y + 25.4)

    # GNDD pins -> GND
    power_symbol("GND", pwr_right_x, u4_y + 7.62)
    wire(u4_x + 15.24, u4_y + 7.62, pwr_right_x, u4_y + 7.62)

    # DGND_FILT -> GND
    power_symbol("GND", pwr_right_x, u4_y - 15.24)
    wire(u4_x + 15.24, u4_y - 15.24, pwr_right_x, u4_y - 15.24)

    # ================================================================
    # SECTION 5: AD9361 Decoupling Capacitors (per ADI UG-570)
    # ================================================================
    text_note("AD9361 DECOUPLING (per ADI UG-570 Reference Design)", 30, 430, 2.0)

    # VDDA1P3 group (BB + RX + TX = 6 pins): 4x 100nF + 1x 10uF
    decoupling_group("+1V3_AD", 30, 450, 4, 1, "VDDA1P3 (BB+RX+TX)")

    # VDDD1P3_DIG (2 pins): 4x 100nF + 1x 10uF
    decoupling_group("+1V3_AD", 30, 490, 4, 1, "VDDD1P3_DIG")

    # VDDD_IF (2 pins): 4x 100nF + 1x 10uF
    decoupling_group("+1V8", 30, 530, 4, 1, "VDDD_IF")

    # VDDA3P3 (2 pins): 4x 100nF + 1x 10uF
    decoupling_group("+3V3A", 30, 570, 4, 1, "VDDA3P3")

    # Additional bypass per ADI ref: 2x 100nF on +1V3_AD close to BGA
    decoupling_group("+1V3_AD", 170, 450, 2, 0, "VDDA1P3 extra bypass")

    # +3V3A OCXO rail bypass
    decoupling_group("+3V3A", 170, 490, 2, 1, "OCXO +3V3A bypass")

    # ================================================================
    # Close schematic
    # ================================================================
    emit(')')

    # Write output
    output = '\n'.join(lines)

    # Verify parenthesis balance
    opens = output.count('(')
    closes = output.count(')')
    if opens != closes:
        print(f"WARNING: Parenthesis imbalance! Opens: {opens}, Closes: {closes}", file=sys.stderr)
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

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/ad9361.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"Component counts:")
    print(f"  AD9361 units placed: 4 (all as U10)")
    print(f"  OCXO: 1 (Y2, OX200-SC-040.0M)")
    print(f"  LDO: 1 ({ldo_ref}, ADP151-1.3)")
    print(f"  Capacitors: {counts['capacitors']}")
    print(f"  Resistors: {counts['resistors']}")
    print(f"  Power symbols: {pwr_idx[0] - 200}")
    print(f"  Wires: {counts['wires']}")
    print(f"  Global labels: {counts['gl_labels']}")
    print(f"  Hierarchical labels: {counts['hier_labels']}")
    print(f"  Total symbols: {counts['symbols']}")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")

if __name__ == "__main__":
    main()
