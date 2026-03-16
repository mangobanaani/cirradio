#!/usr/bin/env python3
"""Generate peripherals schematic sheet for CIRRADIO dev board."""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

# Reference designator counters - start at 200 to avoid conflicts with other sheets
cap_idx = [200]
res_idx = [200]
pwr_idx = [200]
ic_idx = [10]
conn_idx = [10]
crystal_idx = [10]

def next_cap():
    c = cap_idx[0]; cap_idx[0] += 1; return f"C{c}"

def next_res():
    r = res_idx[0]; res_idx[0] += 1; return f"R{r}"

def next_pwr():
    p = pwr_idx[0]; pwr_idx[0] += 1; return f"#PWR{p:04d}"

def next_ic():
    i = ic_idx[0]; ic_idx[0] += 1; return f"U{i}"

def next_conn():
    c = conn_idx[0]; conn_idx[0] += 1; return f"J{c}"

def next_crystal():
    y = crystal_idx[0]; crystal_idx[0] += 1; return f"Y{y}"

# Track component counts
counts = {"capacitors": 0, "resistors": 0, "symbols": 0, "wires": 0,
           "labels": 0, "gl_labels": 0, "hier_labels": 0, "ics": 0,
           "connectors": 0}

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

def no_connect(x, y):
    emit(f'    (no_connect (at {x} {y}) (uuid "{uid()}"))')


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

    # Device:Crystal
    emit('''    (symbol "Device:Crystal"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "Y" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Crystal" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "Crystal_0_1"
        (rectangle (start -0.762 1.524) (end 0.762 -1.524) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -1.524 -1.27) (xy -1.524 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.524 -1.27) (xy 1.524 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "Crystal_1_1"
        (pin passive line (at -3.81 0 0) (length 2.286) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.286) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Connector:Conn_01x01 for U.FL
    emit('''    (symbol "Connector:Conn_Coaxial"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0.254 3.048 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_Coaxial" (at 2.286 -2.794 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "Conn_Coaxial_0_1"
        (circle (center 0 0) (radius 1.778) (stroke (width 0.254) (type default)) (fill (type none)))
        (arc (start -1.778 0) (mid 0 -1.778) (end 1.778 0) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "Conn_Coaxial_1_1"
        (pin passive line (at -3.81 0 0) (length 2.032) (name "In" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 2.032) (name "Ext" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- QSPI Flash S25FL256S (WSON-8) ----
    emit('''    (symbol "cirradio:S25FL256S"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 8.89 0) (effects (font (size 1.27 1.27))))
      (property "Value" "S25FL256S" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "S25FL256S_0_1"
        (rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "S25FL256S_1_1"
        (pin input line (at -10.16 5.08 0) (length 2.54) (name "CS#" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -10.16 2.54 0) (length 2.54) (name "IO1/SO" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -10.16 0 0) (length 2.54) (name "IO2/WP#" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -10.16 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 10.16 0 180) (length 2.54) (name "IO0/SI" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin input line (at 10.16 2.54 180) (length 2.54) (name "SCK" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 10.16 5.08 180) (length 2.54) (name "IO3/HOLD#" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 10.16 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -10.16 90) (length 2.54) (name "EP" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- eMMC MTFC8GAKAJCN (BGA-153) ----
    emit('''    (symbol "cirradio:MTFC8GAKAJCN"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 17.78 0) (effects (font (size 1.27 1.27))))
      (property "Value" "MTFC8GAKAJCN" (at 0 -17.78 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "cirradio:BGA-153_11.5x13mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "MTFC8GAKAJCN_0_1"
        (rectangle (start -10.16 16.51) (end 10.16 -16.51) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "MTFC8GAKAJCN_1_1"
        (pin bidirectional line (at -12.7 12.7 0) (length 2.54) (name "DAT0" (effects (font (size 1.27 1.27)))) (number "H2" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 10.16 0) (length 2.54) (name "DAT1" (effects (font (size 1.27 1.27)))) (number "J1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 7.62 0) (length 2.54) (name "DAT2" (effects (font (size 1.27 1.27)))) (number "J2" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 5.08 0) (length 2.54) (name "DAT3" (effects (font (size 1.27 1.27)))) (number "H1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 2.54 0) (length 2.54) (name "DAT4" (effects (font (size 1.27 1.27)))) (number "J3" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 0 0) (length 2.54) (name "DAT5" (effects (font (size 1.27 1.27)))) (number "K1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 -2.54 0) (length 2.54) (name "DAT6" (effects (font (size 1.27 1.27)))) (number "K2" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 -5.08 0) (length 2.54) (name "DAT7" (effects (font (size 1.27 1.27)))) (number "K3" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -10.16 0) (length 2.54) (name "CLK" (effects (font (size 1.27 1.27)))) (number "D1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -12.7 -12.7 0) (length 2.54) (name "CMD" (effects (font (size 1.27 1.27)))) (number "D2" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 12.7 180) (length 2.54) (name "RST#" (effects (font (size 1.27 1.27)))) (number "C1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 19.05 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "A3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 5.08 19.05 270) (length 2.54) (name "VCCQ" (effects (font (size 1.27 1.27)))) (number "E1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -19.05 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "B2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- USB PHY USB3320C (QFN-32) ----
    emit('''    (symbol "cirradio:USB3320C"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 22.86 0) (effects (font (size 1.27 1.27))))
      (property "Value" "USB3320C" (at 0 -22.86 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "USB3320C_0_1"
        (rectangle (start -12.7 21.59) (end 12.7 -21.59) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "USB3320C_1_1"
        (pin bidirectional line (at -15.24 17.78 0) (length 2.54) (name "DATA0" (effects (font (size 1.27 1.27)))) (number "17" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 15.24 0) (length 2.54) (name "DATA1" (effects (font (size 1.27 1.27)))) (number "18" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 12.7 0) (length 2.54) (name "DATA2" (effects (font (size 1.27 1.27)))) (number "19" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 10.16 0) (length 2.54) (name "DATA3" (effects (font (size 1.27 1.27)))) (number "20" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 7.62 0) (length 2.54) (name "DATA4" (effects (font (size 1.27 1.27)))) (number "21" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 5.08 0) (length 2.54) (name "DATA5" (effects (font (size 1.27 1.27)))) (number "22" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 2.54 0) (length 2.54) (name "DATA6" (effects (font (size 1.27 1.27)))) (number "23" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -15.24 0 0) (length 2.54) (name "DATA7" (effects (font (size 1.27 1.27)))) (number "24" (effects (font (size 1.27 1.27)))))
        (pin output line (at -15.24 -5.08 0) (length 2.54) (name "CLK" (effects (font (size 1.27 1.27)))) (number "15" (effects (font (size 1.27 1.27)))))
        (pin output line (at -15.24 -7.62 0) (length 2.54) (name "DIR" (effects (font (size 1.27 1.27)))) (number "16" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 -10.16 0) (length 2.54) (name "STP" (effects (font (size 1.27 1.27)))) (number "25" (effects (font (size 1.27 1.27)))))
        (pin output line (at -15.24 -12.7 0) (length 2.54) (name "NXT" (effects (font (size 1.27 1.27)))) (number "26" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 -17.78 0) (length 2.54) (name "RESETB" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 15.24 15.24 180) (length 2.54) (name "DP" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 15.24 12.7 180) (length 2.54) (name "DM" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 5.08 180) (length 2.54) (name "RBIAS" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -2.54 24.13 270) (length 2.54) (name "VDD3V3" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 2.54 24.13 270) (length 2.54) (name "VDDA3V3" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -24.13 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "33" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 -5.08 180) (length 2.54) (name "REFCLK" (effects (font (size 1.27 1.27)))) (number "27" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 -12.7 180) (length 2.54) (name "XO" (effects (font (size 1.27 1.27)))) (number "28" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 -15.24 180) (length 2.54) (name "XI" (effects (font (size 1.27 1.27)))) (number "29" (effects (font (size 1.27 1.27)))))
        (pin input line (at 15.24 -17.78 180) (length 2.54) (name "CLKIN" (effects (font (size 1.27 1.27)))) (number "30" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- Ethernet PHY KSZ9031 (QFN-48) ----
    emit('''    (symbol "cirradio:KSZ9031"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 30.48 0) (effects (font (size 1.27 1.27))))
      (property "Value" "KSZ9031RNXIA" (at 0 -30.48 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "KSZ9031_0_1"
        (rectangle (start -15.24 29.21) (end 15.24 -29.21) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "KSZ9031_1_1"
        (pin bidirectional line (at -17.78 25.4 0) (length 2.54) (name "RXD0" (effects (font (size 1.27 1.27)))) (number "20" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -17.78 22.86 0) (length 2.54) (name "RXD1" (effects (font (size 1.27 1.27)))) (number "21" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -17.78 20.32 0) (length 2.54) (name "RXD2" (effects (font (size 1.27 1.27)))) (number "22" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -17.78 17.78 0) (length 2.54) (name "RXD3" (effects (font (size 1.27 1.27)))) (number "23" (effects (font (size 1.27 1.27)))))
        (pin output line (at -17.78 12.7 0) (length 2.54) (name "RX_CLK" (effects (font (size 1.27 1.27)))) (number "19" (effects (font (size 1.27 1.27)))))
        (pin output line (at -17.78 10.16 0) (length 2.54) (name "RX_CTL" (effects (font (size 1.27 1.27)))) (number "18" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 5.08 0) (length 2.54) (name "TXD0" (effects (font (size 1.27 1.27)))) (number "27" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 2.54 0) (length 2.54) (name "TXD1" (effects (font (size 1.27 1.27)))) (number "28" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 0 0) (length 2.54) (name "TXD2" (effects (font (size 1.27 1.27)))) (number "29" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -2.54 0) (length 2.54) (name "TXD3" (effects (font (size 1.27 1.27)))) (number "30" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -7.62 0) (length 2.54) (name "TX_CLK" (effects (font (size 1.27 1.27)))) (number "26" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -10.16 0) (length 2.54) (name "TX_CTL" (effects (font (size 1.27 1.27)))) (number "25" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -15.24 0) (length 2.54) (name "RESET#" (effects (font (size 1.27 1.27)))) (number "42" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -17.78 -17.78 0) (length 2.54) (name "MDIO" (effects (font (size 1.27 1.27)))) (number "40" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -20.32 0) (length 2.54) (name "MDC" (effects (font (size 1.27 1.27)))) (number "41" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 25.4 180) (length 2.54) (name "TXP_A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 22.86 180) (length 2.54) (name "TXN_A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 17.78 180) (length 2.54) (name "RXP_A" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 15.24 180) (length 2.54) (name "RXN_A" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 10.16 180) (length 2.54) (name "TXP_B" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 7.62 180) (length 2.54) (name "TXN_B" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 2.54 180) (length 2.54) (name "RXP_B" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 0 180) (length 2.54) (name "RXN_B" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 -5.08 180) (length 2.54) (name "TXP_C" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 -7.62 180) (length 2.54) (name "TXN_C" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 -12.7 180) (length 2.54) (name "RXP_C" (effects (font (size 1.27 1.27)))) (number "16" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 -15.24 180) (length 2.54) (name "RXN_C" (effects (font (size 1.27 1.27)))) (number "17" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 -20.32 180) (length 2.54) (name "TXP_D" (effects (font (size 1.27 1.27)))) (number "31" (effects (font (size 1.27 1.27)))))
        (pin output line (at 17.78 -22.86 180) (length 2.54) (name "TXN_D" (effects (font (size 1.27 1.27)))) (number "32" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 -25.4 180) (length 2.54) (name "RXP_D" (effects (font (size 1.27 1.27)))) (number "33" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 -27.94 180) (length 2.54) (name "RXN_D" (effects (font (size 1.27 1.27)))) (number "34" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -25.4 0) (length 2.54) (name "XI" (effects (font (size 1.27 1.27)))) (number "37" (effects (font (size 1.27 1.27)))))
        (pin output line (at -17.78 -27.94 0) (length 2.54) (name "XO" (effects (font (size 1.27 1.27)))) (number "38" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -5.08 31.75 270) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 5.08 31.75 270) (length 2.54) (name "VDDIO" (effects (font (size 1.27 1.27)))) (number "24" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -31.75 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "49" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 -5.08 180) (length 2.54) (name "LED0" (effects (font (size 1.27 1.27)))) (number "43" (effects (font (size 1.27 1.27)))))
        (pin input line (at 17.78 -7.62 180) (length 2.54) (name "LED1" (effects (font (size 1.27 1.27)))) (number "44" (effects (font (size 1.27 1.27)))))
        (pin input line (at -17.78 -22.86 0) (length 2.54) (name "PHYAD0" (effects (font (size 1.27 1.27)))) (number "39" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- FT232RQ UART-USB bridge (QFN-32) ----
    emit('''    (symbol "cirradio:FT232RQ"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 17.78 0) (effects (font (size 1.27 1.27))))
      (property "Value" "FT232RQ" (at 0 -17.78 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "FT232RQ_0_1"
        (rectangle (start -10.16 16.51) (end 10.16 -16.51) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "FT232RQ_1_1"
        (pin output line (at -12.7 12.7 0) (length 2.54) (name "TXD" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 10.16 0) (length 2.54) (name "RXD" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 12.7 12.7 180) (length 2.54) (name "USBDP" (effects (font (size 1.27 1.27)))) (number "15" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 12.7 10.16 180) (length 2.54) (name "USBDM" (effects (font (size 1.27 1.27)))) (number "16" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 19.05 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -19.05 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 0 0) (length 2.54) (name "RESET#" (effects (font (size 1.27 1.27)))) (number "19" (effects (font (size 1.27 1.27)))))
        (pin output line (at -12.7 -5.08 0) (length 2.54) (name "CBUS0" (effects (font (size 1.27 1.27)))) (number "23" (effects (font (size 1.27 1.27)))))
        (pin output line (at -12.7 -7.62 0) (length 2.54) (name "CBUS1" (effects (font (size 1.27 1.27)))) (number "22" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 12.7 0 180) (length 2.54) (name "3V3OUT" (effects (font (size 1.27 1.27)))) (number "17" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- GPS MAX-M10S (LCC-16) ----
    emit('''    (symbol "cirradio:MAX-M10S"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 15.24 0) (effects (font (size 1.27 1.27))))
      (property "Value" "MAX-M10S" (at 0 -15.24 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "cirradio:LCC-16_MAX-M10S" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "MAX-M10S_0_1"
        (rectangle (start -10.16 13.97) (end 10.16 -13.97) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "MAX-M10S_1_1"
        (pin power_in line (at 0 16.51 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 10.16 0) (length 2.54) (name "RF_IN" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin output line (at 12.7 10.16 180) (length 2.54) (name "TXD" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 7.62 180) (length 2.54) (name "RXD" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin output line (at 12.7 2.54 180) (length 2.54) (name "TIMEPULSE" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -2.54 0) (length 2.54) (name "D_SEL" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin input line (at -12.7 -5.08 0) (length 2.54) (name "RESET#" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -12.7 -10.16 0) (length 2.54) (name "V_BCKP" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 12.7 -5.08 180) (length 2.54) (name "SDA" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
        (pin input line (at 12.7 -7.62 180) (length 2.54) (name "SCL" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- Connector_Generic:Conn_01x08 for micro-SD ----
    emit('''    (symbol "Connector_Generic:Conn_01x09"
      (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 12.7 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Micro_SD" (at 0 -12.7 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "Conn_01x09_1_1"
        (rectangle (start -1.27 11.43) (end 1.27 -11.43) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -3.81 10.16 0) (length 2.54) (name "DAT2" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 7.62 0) (length 2.54) (name "CD/DAT3" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 5.08 0) (length 2.54) (name "CMD" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 2.54 0) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 0 0) (length 2.54) (name "CLK" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -2.54 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -5.08 0) (length 2.54) (name "DAT0" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -7.62 0) (length 2.54) (name "DAT1" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -10.16 0) (length 2.54) (name "CD#" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- USB Type-A connector ----
    emit('''    (symbol "Connector:USB_A"
      (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 7.62 0) (effects (font (size 1.27 1.27))))
      (property "Value" "USB_A" (at 0 -7.62 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "USB_A_1_1"
        (rectangle (start -3.81 6.35) (end 3.81 -6.35) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin power_in line (at -6.35 5.08 0) (length 2.54) (name "VBUS" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -6.35 2.54 0) (length 2.54) (name "D-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -6.35 0 0) (length 2.54) (name "D+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -6.35 -2.54 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -5.08 0) (length 2.54) (name "Shield" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- USB Micro-B connector ----
    emit('''    (symbol "Connector:USB_B_Micro"
      (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 7.62 0) (effects (font (size 1.27 1.27))))
      (property "Value" "USB_B_Micro" (at 0 -7.62 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "USB_B_Micro_1_1"
        (rectangle (start -3.81 6.35) (end 3.81 -6.35) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin power_in line (at -6.35 5.08 0) (length 2.54) (name "VBUS" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -6.35 2.54 0) (length 2.54) (name "D-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at -6.35 0 0) (length 2.54) (name "D+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -2.54 0) (length 2.54) (name "ID" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -6.35 -5.08 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -7.62 0) (length 2.54) (name "Shield" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ---- Ethernet magnetics/RJ45 combined ----
    emit('''    (symbol "Connector:RJ45_Shielded"
      (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 12.7 0) (effects (font (size 1.27 1.27))))
      (property "Value" "RJ45_MagJack" (at 0 -12.7 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "RJ45_Shielded_1_1"
        (rectangle (start -3.81 11.43) (end 3.81 -11.43) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -6.35 10.16 0) (length 2.54) (name "TD+" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 7.62 0) (length 2.54) (name "TD-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 5.08 0) (length 2.54) (name "RD+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 2.54 0) (length 2.54) (name "RD-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 0 0) (length 2.54) (name "TCT+" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -2.54 0) (length 2.54) (name "TCT-" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -5.08 0) (length 2.54) (name "TDD+" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -7.62 0) (length 2.54) (name "TDD-" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 -10.16 0) (length 2.54) (name "Shield" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Power symbols
    for net in ["+1V8", "+3V3", "+3V3A", "+5V", "GND"]:
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


# ============================================================
# SECTION BUILDERS
# ============================================================

def build_qspi(base_x, base_y):
    """Section 1: QSPI Flash S25FL256S."""
    text_note("QSPI FLASH - S25FL256S (256Mbit)", base_x, base_y - 5, 2.0)
    text_note("CS#=MIO[1] SCK=MIO[6] IO[0:3]=MIO[2:5]", base_x, base_y, 1.27)

    ux, uy = base_x + 50, base_y + 30
    ref = next_ic(); counts["ics"] += 1
    symbol_instance("cirradio:S25FL256S", ref, "S25FL256S", ux, uy,
                    footprint="Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4mm")
    symbol_pins(["1","2","3","4","5","6","7","8","9"])

    # VCC = +1V8
    power_symbol("+1V8", ux, uy - 15)
    wire(ux, uy - 10.16, ux, uy - 15)

    # Decoupling 100nF
    cap("100n", ux + 8, uy - 15)
    power_symbol("+1V8", ux + 8, uy - 20)
    wire(ux + 8, uy - 18.81, ux + 8, uy - 20)
    power_symbol("GND", ux + 8, uy - 10)
    wire(ux + 8, uy - 11.19, ux + 8, uy - 10)

    # GND
    power_symbol("GND", ux, uy + 15)
    wire(ux, uy + 10.16, ux, uy + 15)

    # CS# = MIO1
    hl_x = ux - 20
    wire(ux - 10.16, uy + 5.08, hl_x, uy + 5.08)
    hier_label("QSPI_MIO1", hl_x, uy + 5.08, "bidirectional", 180)

    # IO1/SO = MIO3
    wire(ux - 10.16, uy + 2.54, hl_x, uy + 2.54)
    hier_label("QSPI_MIO3", hl_x, uy + 2.54, "bidirectional", 180)

    # IO2/WP# = MIO4 with 10K pull-up
    wire(ux - 10.16, uy, hl_x, uy)
    hier_label("QSPI_MIO4", hl_x, uy, "bidirectional", 180)
    resistor("10K", ux - 14, uy - 6, angle=0)
    wire(ux - 14, uy - 2.19, ux - 14, uy)
    power_symbol("+1V8", ux - 14, uy - 13)
    wire(ux - 14, uy - 9.81, ux - 14, uy - 13)

    # IO0/SI = MIO2
    wire(ux + 10.16, uy, hl_x + 45, uy)
    hier_label("QSPI_MIO2", hl_x + 45, uy, "bidirectional")

    # SCK = MIO6
    wire(ux + 10.16, uy + 2.54, hl_x + 45, uy + 2.54)
    hier_label("QSPI_MIO6", hl_x + 45, uy + 2.54, "bidirectional")

    # IO3/HOLD# = MIO5 with 10K pull-up
    wire(ux + 10.16, uy + 5.08, hl_x + 45, uy + 5.08)
    hier_label("QSPI_MIO5", hl_x + 45, uy + 5.08, "bidirectional")
    resistor("10K", ux + 18, uy - 2, angle=0)
    wire(ux + 18, uy + 1.81, ux + 18, uy + 5.08)
    wire(ux + 10.16, uy + 5.08, ux + 18, uy + 5.08)
    power_symbol("+1V8", ux + 18, uy - 9)
    wire(ux + 18, uy - 5.81, ux + 18, uy - 9)


def build_emmc(base_x, base_y):
    """Section 2: eMMC MTFC8GAKAJCN."""
    text_note("eMMC STORAGE - MTFC8GAKAJCN (8GB)", base_x, base_y - 5, 2.0)
    text_note("8-bit data via EMIO/PL pins", base_x, base_y, 1.27)

    ux, uy = base_x + 50, base_y + 35
    ref = next_ic(); counts["ics"] += 1
    symbol_instance("cirradio:MTFC8GAKAJCN", ref, "MTFC8GAKAJCN-8GB", ux, uy,
                    footprint="cirradio:BGA-153_11.5x13mm")
    symbol_pins(["H2","J1","J2","H1","J3","K1","K2","K3","D1","D2","C1","A3","E1","B2"])

    # VCC = +3V3
    power_symbol("+3V3", ux, uy - 25)
    wire(ux, uy - 19.05, ux, uy - 25)

    # VCCQ = +1V8
    power_symbol("+1V8", ux + 5.08, uy - 25)
    wire(ux + 5.08, uy - 19.05, ux + 5.08, uy - 25)

    # Decoupling - VCC
    cap("100n", ux - 8, uy - 25)
    power_symbol("+3V3", ux - 8, uy - 30)
    wire(ux - 8, uy - 28.81, ux - 8, uy - 30)
    power_symbol("GND", ux - 8, uy - 20)
    wire(ux - 8, uy - 21.19, ux - 8, uy - 20)

    # Decoupling - VCCQ
    cap("100n", ux + 13, uy - 25)
    power_symbol("+1V8", ux + 13, uy - 30)
    wire(ux + 13, uy - 28.81, ux + 13, uy - 30)
    power_symbol("GND", ux + 13, uy - 20)
    wire(ux + 13, uy - 21.19, ux + 13, uy - 20)

    # GND
    power_symbol("GND", ux, uy + 25)
    wire(ux, uy + 19.05, ux, uy + 25)

    # DAT[0:7] hierarchical labels
    hl_x = ux - 22
    dat_labels = ["EMMC_DAT0","EMMC_DAT1","EMMC_DAT2","EMMC_DAT3",
                  "EMMC_DAT4","EMMC_DAT5","EMMC_DAT6","EMMC_DAT7"]
    y_offsets = [12.7, 10.16, 7.62, 5.08, 2.54, 0, -2.54, -5.08]
    for lbl, yo in zip(dat_labels, y_offsets):
        wire(ux - 12.7, uy + yo, hl_x, uy + yo)
        hier_label(lbl, hl_x, uy + yo, "bidirectional", 180)

    # CLK
    wire(ux - 12.7, uy - 10.16, hl_x, uy - 10.16)
    hier_label("EMMC_CLK", hl_x, uy - 10.16, "bidirectional", 180)

    # CMD
    wire(ux - 12.7, uy - 12.7, hl_x, uy - 12.7)
    hier_label("EMMC_CMD", hl_x, uy - 12.7, "bidirectional", 180)

    # RST# with 10K pull-up to +3V3
    rst_x = ux + 22
    wire(ux + 12.7, uy + 12.7, rst_x, uy + 12.7)
    resistor("10K", rst_x + 4, uy + 6, angle=0)
    wire(rst_x, uy + 12.7, rst_x + 4, uy + 12.7)
    wire(rst_x + 4, uy + 9.81, rst_x + 4, uy + 12.7)
    power_symbol("+3V3", rst_x + 4, uy)
    wire(rst_x + 4, uy + 2.19, rst_x + 4, uy)


def build_usb_phy(base_x, base_y):
    """Section 3: USB PHY USB3320C."""
    text_note("USB PHY - USB3320C (ULPI)", base_x, base_y - 5, 2.0)
    text_note("ULPI DATA[0:7]/CLK/DIR/STP/NXT via MIO[28:39]", base_x, base_y, 1.27)

    ux, uy = base_x + 50, base_y + 40
    ref = next_ic(); counts["ics"] += 1
    symbol_instance("cirradio:USB3320C", ref, "USB3320C-EZK", ux, uy,
                    footprint="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm")
    symbol_pins(["17","18","19","20","21","22","23","24","15","16","25","26",
                 "4","11","12","14","1","9","33","27","28","29","30"])

    # VDD3V3
    power_symbol("+3V3", ux - 2.54, uy - 30)
    wire(ux - 2.54, uy - 24.13, ux - 2.54, uy - 30)

    # VDDA3V3
    power_symbol("+3V3", ux + 2.54, uy - 30)
    wire(ux + 2.54, uy - 24.13, ux + 2.54, uy - 30)

    # Decoupling VDD
    cap("100n", ux - 10, uy - 30)
    power_symbol("+3V3", ux - 10, uy - 35)
    wire(ux - 10, uy - 33.81, ux - 10, uy - 35)
    power_symbol("GND", ux - 10, uy - 25)
    wire(ux - 10, uy - 26.19, ux - 10, uy - 25)

    # Decoupling VDDA
    cap("100n", ux + 10, uy - 30)
    power_symbol("+3V3", ux + 10, uy - 35)
    wire(ux + 10, uy - 33.81, ux + 10, uy - 35)
    power_symbol("GND", ux + 10, uy - 25)
    wire(ux + 10, uy - 26.19, ux + 10, uy - 25)

    # GND
    power_symbol("GND", ux, uy + 30)
    wire(ux, uy + 24.13, ux, uy + 30)

    # ULPI data lines -> hierarchical labels matching Zynq MIO assignments
    hl_x = ux - 25
    # DATA[0:7] = MIO[28:35]
    ulpi_data = [("USB_MIO28", 17.78), ("USB_MIO29", 15.24), ("USB_MIO30", 12.7),
                 ("USB_MIO31", 10.16), ("USB_MIO32", 7.62), ("USB_MIO33", 5.08),
                 ("USB_MIO34", 2.54), ("USB_MIO35", 0)]
    for lbl, yo in ulpi_data:
        wire(ux - 15.24, uy + yo, hl_x, uy + yo)
        hier_label(lbl, hl_x, uy + yo, "bidirectional", 180)

    # CLK = MIO36
    wire(ux - 15.24, uy - 5.08, hl_x, uy - 5.08)
    hier_label("USB_MIO36", hl_x, uy - 5.08, "bidirectional", 180)

    # DIR = MIO37
    wire(ux - 15.24, uy - 7.62, hl_x, uy - 7.62)
    hier_label("USB_MIO37", hl_x, uy - 7.62, "bidirectional", 180)

    # STP = MIO38
    wire(ux - 15.24, uy - 10.16, hl_x, uy - 10.16)
    hier_label("USB_MIO38", hl_x, uy - 10.16, "bidirectional", 180)

    # NXT = MIO39
    wire(ux - 15.24, uy - 12.7, hl_x, uy - 12.7)
    hier_label("USB_MIO39", hl_x, uy - 12.7, "bidirectional", 180)

    # RESETB tied to +3V3 via 10K (active low, keep deasserted)
    resistor("10K", ux - 22, uy - 17.78, angle=90)
    wire(ux - 15.24, uy - 17.78, ux - 22 + 3.81, uy - 17.78)
    power_symbol("+3V3", ux - 30, uy - 17.78)
    wire(ux - 22 - 3.81, uy - 17.78, ux - 30, uy - 17.78)

    # RBIAS 12.1K 1% to GND
    rb_x = ux + 25
    wire(ux + 15.24, uy + 5.08, rb_x, uy + 5.08)
    resistor("12K1", rb_x + 5, uy + 5.08, angle=90)
    wire(rb_x, uy + 5.08, rb_x + 5 - 3.81, uy + 5.08)
    power_symbol("GND", rb_x + 12, uy + 5.08)
    wire(rb_x + 5 + 3.81, uy + 5.08, rb_x + 12, uy + 5.08)

    # DP/DM with 22R series to USB-A connector
    conn_x = ux + 55
    conn_ref = next_conn(); counts["connectors"] += 1
    symbol_instance("Connector:USB_A", conn_ref, "USB_A", conn_x, uy,
                    footprint="Connector_USB:USB_A_Molex_105057_Vertical")
    symbol_pins(["1","2","3","4","5"])

    # 22R series on DP
    resistor("22R", ux + 30, uy + 15.24, angle=90)
    wire(ux + 15.24, uy + 15.24, ux + 30 - 3.81, uy + 15.24)
    wire(ux + 30 + 3.81, uy + 15.24, conn_x - 10, uy + 15.24)
    wire(conn_x - 10, uy + 15.24, conn_x - 10, uy)
    wire(conn_x - 10, uy, conn_x - 6.35, uy)

    # 22R series on DM
    resistor("22R", ux + 30, uy + 12.7, angle=90)
    wire(ux + 15.24, uy + 12.7, ux + 30 - 3.81, uy + 12.7)
    wire(ux + 30 + 3.81, uy + 12.7, conn_x - 12, uy + 12.7)
    wire(conn_x - 12, uy + 12.7, conn_x - 12, uy + 2.54)
    wire(conn_x - 12, uy + 2.54, conn_x - 6.35, uy + 2.54)

    # USB VBUS = +5V
    power_symbol("+5V", conn_x - 6.35, uy + 10)
    wire(conn_x - 6.35, uy + 5.08, conn_x - 6.35, uy + 10)

    # USB GND
    power_symbol("GND", conn_x - 6.35, uy - 8)
    wire(conn_x - 6.35, uy - 2.54, conn_x - 6.35, uy - 8)

    # Shield to GND
    wire(conn_x - 6.35, uy - 5.08, conn_x - 6.35, uy - 8)

    # CLKIN tied low (use internal clock)
    power_symbol("GND", ux + 25, uy - 17.78)
    wire(ux + 15.24, uy - 17.78, ux + 25, uy - 17.78)


def build_ethernet(base_x, base_y):
    """Section 4: Ethernet PHY KSZ9031."""
    text_note("ETHERNET PHY - KSZ9031RNXIA (GigE RGMII)", base_x, base_y - 5, 2.0)
    text_note("RGMII to Zynq MIO[16:27], 25MHz crystal", base_x, base_y, 1.27)

    ux, uy = base_x + 55, base_y + 45
    ref = next_ic(); counts["ics"] += 1
    symbol_instance("cirradio:KSZ9031", ref, "KSZ9031RNXIA", ux, uy,
                    footprint="Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm")
    symbol_pins(["20","21","22","23","19","18","27","28","29","30","26","25",
                 "42","40","41","1","2","4","5","7","8","10","11","13","14","16","17",
                 "31","32","33","34","37","38","3","24","49","43","44","39"])

    # VDD = +1V8
    power_symbol("+1V8", ux - 5.08, uy - 38)
    wire(ux - 5.08, uy - 31.75, ux - 5.08, uy - 38)

    # VDDIO = +1V8
    power_symbol("+1V8", ux + 5.08, uy - 38)
    wire(ux + 5.08, uy - 31.75, ux + 5.08, uy - 38)

    # Decoupling VDD
    cap("100n", ux - 14, uy - 38)
    power_symbol("+1V8", ux - 14, uy - 43)
    wire(ux - 14, uy - 41.81, ux - 14, uy - 43)
    power_symbol("GND", ux - 14, uy - 33)
    wire(ux - 14, uy - 34.19, ux - 14, uy - 33)

    cap("10u", ux - 20, uy - 38, "Capacitor_SMD:C_0805_2012Metric")
    power_symbol("+1V8", ux - 20, uy - 43)
    wire(ux - 20, uy - 41.81, ux - 20, uy - 43)
    power_symbol("GND", ux - 20, uy - 33)
    wire(ux - 20, uy - 34.19, ux - 20, uy - 33)

    # Decoupling VDDIO
    cap("100n", ux + 14, uy - 38)
    power_symbol("+1V8", ux + 14, uy - 43)
    wire(ux + 14, uy - 41.81, ux + 14, uy - 43)
    power_symbol("GND", ux + 14, uy - 33)
    wire(ux + 14, uy - 34.19, ux + 14, uy - 33)

    # GND
    power_symbol("GND", ux, uy + 38)
    wire(ux, uy + 31.75, ux, uy + 38)

    # RGMII to Zynq - hierarchical labels
    hl_x = ux - 28
    # RXD[0:3] = MIO[22:25] (Zynq GEM0 rx data)
    rgmii_rx = [("ETH_MIO22", 25.4), ("ETH_MIO23", 22.86),
                ("ETH_MIO24", 20.32), ("ETH_MIO25", 17.78)]
    for lbl, yo in rgmii_rx:
        wire(ux - 17.78, uy + yo, hl_x, uy + yo)
        hier_label(lbl, hl_x, uy + yo, "bidirectional", 180)

    # RX_CLK = MIO[21]
    wire(ux - 17.78, uy + 12.7, hl_x, uy + 12.7)
    hier_label("ETH_MIO21", hl_x, uy + 12.7, "bidirectional", 180)

    # RX_CTL = MIO[20]
    wire(ux - 17.78, uy + 10.16, hl_x, uy + 10.16)
    hier_label("ETH_MIO20", hl_x, uy + 10.16, "bidirectional", 180)

    # TXD[0:3] = MIO[16:19]
    rgmii_tx = [("ETH_MIO16", 5.08), ("ETH_MIO17", 2.54),
                ("ETH_MIO18", 0), ("ETH_MIO19", -2.54)]
    for lbl, yo in rgmii_tx:
        wire(ux - 17.78, uy + yo, hl_x, uy + yo)
        hier_label(lbl, hl_x, uy + yo, "bidirectional", 180)

    # TX_CLK = MIO[26]
    wire(ux - 17.78, uy - 7.62, hl_x, uy - 7.62)
    hier_label("ETH_MIO26", hl_x, uy - 7.62, "bidirectional", 180)

    # TX_CTL = MIO[27]
    wire(ux - 17.78, uy - 10.16, hl_x, uy - 10.16)
    hier_label("ETH_MIO27", hl_x, uy - 10.16, "bidirectional", 180)

    # RESET# with 10K pull-up
    resistor("10K", ux - 25, uy - 20, angle=0)
    wire(ux - 17.78, uy - 15.24, ux - 25, uy - 15.24)
    wire(ux - 25, uy - 16.19, ux - 25, uy - 15.24)
    power_symbol("+1V8", ux - 25, uy - 27)
    wire(ux - 25, uy - 23.81, ux - 25, uy - 27)

    # MDIO/MDC hierarchical labels
    wire(ux - 17.78, uy - 17.78, hl_x, uy - 17.78)
    global_label("ETH_MDIO", hl_x, uy - 17.78, "bidirectional", 180)
    wire(ux - 17.78, uy - 20.32, hl_x, uy - 20.32)
    global_label("ETH_MDC", hl_x, uy - 20.32, "output", 180)

    # PHYAD0 tied low = address 0
    power_symbol("GND", ux - 25, uy - 22.86)
    wire(ux - 17.78, uy - 22.86, ux - 25, uy - 22.86)

    # 25 MHz crystal
    cryst_x = ux - 28
    cryst_y = uy - 28
    cryst_ref = next_crystal()
    symbol_instance("Device:Crystal", cryst_ref, "25MHz", cryst_x, cryst_y,
                    footprint="Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm")
    symbol_pins(["1", "2"])

    wire(cryst_x - 3.81, cryst_y, ux - 17.78, uy - 25.4)  # XI
    wire(cryst_x + 3.81, cryst_y, ux - 17.78, uy - 27.94)  # XO

    # Crystal load caps
    cap("15p", cryst_x - 6, cryst_y + 6)
    wire(cryst_x - 6, cryst_y + 2.19, cryst_x - 6, cryst_y)
    wire(cryst_x - 6, cryst_y, cryst_x - 3.81, cryst_y)
    power_symbol("GND", cryst_x - 6, cryst_y + 13)
    wire(cryst_x - 6, cryst_y + 9.81, cryst_x - 6, cryst_y + 13)

    cap("15p", cryst_x + 6, cryst_y + 6)
    wire(cryst_x + 6, cryst_y + 2.19, cryst_x + 6, cryst_y)
    wire(cryst_x + 6, cryst_y, cryst_x + 3.81, cryst_y)
    power_symbol("GND", cryst_x + 6, cryst_y + 13)
    wire(cryst_x + 6, cryst_y + 9.81, cryst_x + 6, cryst_y + 13)

    # RJ45 connector with integrated magnetics
    rj_x = ux + 55
    rj_ref = next_conn(); counts["connectors"] += 1
    symbol_instance("Connector:RJ45_Shielded", rj_ref, "RJ45_MagJack", rj_x, uy,
                    footprint="Connector_RJ:RJ45_Amphenol_ARJM11D7")
    symbol_pins(["1","2","3","4","5","6","7","8","9"])

    # Connect PHY MDI pairs to RJ45
    # Pair A: TXP_A/TXN_A -> pins 1,2
    wire(ux + 17.78, uy + 25.4, rj_x - 6.35, uy + 10.16)
    wire(ux + 17.78, uy + 22.86, rj_x - 6.35, uy + 7.62)

    # Pair B: RXP_A/RXN_A -> pins 3,4 (reversed pair)
    wire(ux + 17.78, uy + 17.78, rj_x - 6.35, uy + 5.08)
    wire(ux + 17.78, uy + 15.24, rj_x - 6.35, uy + 2.54)

    # Pair C: TXP_B/TXN_B -> pins 5,6
    wire(ux + 17.78, uy + 10.16, rj_x - 6.35, uy)
    wire(ux + 17.78, uy + 7.62, rj_x - 6.35, uy - 2.54)

    # Pair D: RXP_B/RXN_B -> pins 7,8
    wire(ux + 17.78, uy + 2.54, rj_x - 6.35, uy - 5.08)
    wire(ux + 17.78, uy, rj_x - 6.35, uy - 7.62)

    # Shield to GND
    power_symbol("GND", rj_x - 6.35, uy - 15)
    wire(rj_x - 6.35, uy - 10.16, rj_x - 6.35, uy - 15)


def build_uart_usb(base_x, base_y):
    """Section 5: UART-USB Bridge FT232RQ."""
    text_note("UART-USB BRIDGE - FT232RQ (Console)", base_x, base_y - 5, 2.0)
    text_note("TXD=MIO[48] RXD=MIO[49] -> USB Micro-B", base_x, base_y, 1.27)

    ux, uy = base_x + 50, base_y + 35
    ref = next_ic(); counts["ics"] += 1
    symbol_instance("cirradio:FT232RQ", ref, "FT232RQ", ux, uy,
                    footprint="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm")
    symbol_pins(["1","5","15","16","12","9","19","23","22","17"])

    # VCC = +3V3
    power_symbol("+3V3", ux, uy - 25)
    wire(ux, uy - 19.05, ux, uy - 25)

    # Decoupling
    cap("100n", ux + 8, uy - 25)
    power_symbol("+3V3", ux + 8, uy - 30)
    wire(ux + 8, uy - 28.81, ux + 8, uy - 30)
    power_symbol("GND", ux + 8, uy - 20)
    wire(ux + 8, uy - 21.19, ux + 8, uy - 20)

    cap("4u7", ux + 14, uy - 25, "Capacitor_SMD:C_0805_2012Metric")
    power_symbol("+3V3", ux + 14, uy - 30)
    wire(ux + 14, uy - 28.81, ux + 14, uy - 30)
    power_symbol("GND", ux + 14, uy - 20)
    wire(ux + 14, uy - 21.19, ux + 14, uy - 20)

    # GND
    power_symbol("GND", ux, uy + 25)
    wire(ux, uy + 19.05, ux, uy + 25)

    # TXD from Zynq MIO48 (FT232 TXD is output to Zynq RXD)
    hl_x = ux - 22
    wire(ux - 12.7, uy + 12.7, hl_x, uy + 12.7)
    hier_label("UART1_MIO49", hl_x, uy + 12.7, "bidirectional", 180)

    # RXD to Zynq MIO49 (FT232 RXD is input from Zynq TXD)
    wire(ux - 12.7, uy + 10.16, hl_x, uy + 10.16)
    hier_label("UART1_MIO48", hl_x, uy + 10.16, "bidirectional", 180)

    # RESET# with pull-up
    resistor("10K", ux - 18, uy - 4, angle=0)
    wire(ux - 12.7, uy, ux - 18, uy)
    wire(ux - 18, uy - 0.19, ux - 18, uy)
    power_symbol("+3V3", ux - 18, uy - 11)
    wire(ux - 18, uy - 7.81, ux - 18, uy - 11)

    # 3V3OUT decoupling (100nF to GND for internal regulator)
    cap("100n", ux + 20, uy)
    wire(ux + 12.7, uy, ux + 20, uy)
    wire(ux + 20, uy - 3.81, ux + 20, uy)
    power_symbol("GND", ux + 20, uy + 7)
    wire(ux + 20, uy + 3.81, ux + 20, uy + 7)

    # USB Micro-B connector
    conn_x = ux + 50
    conn_ref = next_conn(); counts["connectors"] += 1
    symbol_instance("Connector:USB_B_Micro", conn_ref, "USB_Micro_B", conn_x, uy,
                    footprint="Connector_USB:USB_Micro-B_Molex_47346-0001")
    symbol_pins(["1","2","3","4","5","6"])

    # 22R series on DP
    resistor("22R", ux + 30, uy + 12.7, angle=90)
    wire(ux + 12.7, uy + 12.7, ux + 30 - 3.81, uy + 12.7)
    wire(ux + 30 + 3.81, uy + 12.7, conn_x - 10, uy + 12.7)
    wire(conn_x - 10, uy + 12.7, conn_x - 10, uy)
    wire(conn_x - 10, uy, conn_x - 6.35, uy)

    # 22R series on DM
    resistor("22R", ux + 30, uy + 10.16, angle=90)
    wire(ux + 12.7, uy + 10.16, ux + 30 - 3.81, uy + 10.16)
    wire(ux + 30 + 3.81, uy + 10.16, conn_x - 12, uy + 10.16)
    wire(conn_x - 12, uy + 10.16, conn_x - 12, uy + 2.54)
    wire(conn_x - 12, uy + 2.54, conn_x - 6.35, uy + 2.54)

    # VBUS = +5V
    power_symbol("+5V", conn_x - 6.35, uy + 10)
    wire(conn_x - 6.35, uy + 5.08, conn_x - 6.35, uy + 10)

    # GND
    power_symbol("GND", conn_x - 6.35, uy - 10)
    wire(conn_x - 6.35, uy - 5.08, conn_x - 6.35, uy - 10)

    # Shield to GND
    wire(conn_x - 6.35, uy - 7.62, conn_x - 6.35, uy - 10)


def build_gps(base_x, base_y):
    """Section 6: GPS MAX-M10S."""
    text_note("GPS RECEIVER - MAX-M10S", base_x, base_y - 5, 2.0)
    text_note("UART mode, 1PPS output, U.FL antenna", base_x, base_y, 1.27)

    ux, uy = base_x + 50, base_y + 30
    ref = next_ic(); counts["ics"] += 1
    symbol_instance("cirradio:MAX-M10S", ref, "MAX-M10S", ux, uy,
                    footprint="cirradio:LCC-16_MAX-M10S")
    symbol_pins(["9","1","3","6","5","4","10","8","11","14","13"])

    # VCC = +3V3A (clean analog supply)
    power_symbol("+3V3A", ux, uy - 22)
    wire(ux, uy - 16.51, ux, uy - 22)

    # Decoupling 100nF + 10uF
    cap("100n", ux + 8, uy - 22)
    power_symbol("+3V3A", ux + 8, uy - 27)
    wire(ux + 8, uy - 25.81, ux + 8, uy - 27)
    power_symbol("GND", ux + 8, uy - 17)
    wire(ux + 8, uy - 18.19, ux + 8, uy - 17)

    cap("10u", ux + 14, uy - 22, "Capacitor_SMD:C_0805_2012Metric")
    power_symbol("+3V3A", ux + 14, uy - 27)
    wire(ux + 14, uy - 25.81, ux + 14, uy - 27)
    power_symbol("GND", ux + 14, uy - 17)
    wire(ux + 14, uy - 18.19, ux + 14, uy - 17)

    # GND
    power_symbol("GND", ux, uy + 22)
    wire(ux, uy + 16.51, ux, uy + 22)

    # RF_IN from U.FL
    ufl_x = ux - 25
    ufl_ref = next_conn(); counts["connectors"] += 1
    symbol_instance("Connector:Conn_Coaxial", ufl_ref, "U.FL_GPS", ufl_x, uy + 10.16,
                    footprint="Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical")
    symbol_pins(["1","2"])

    wire(ufl_x + 3.81, uy + 10.16, ux - 12.7, uy + 10.16)
    power_symbol("GND", ufl_x, uy + 17)
    wire(ufl_x, uy + 13.97, ufl_x, uy + 17)

    # TXD/RXD to Zynq (via UART0 or spare MIO)
    hl_x = ux + 22
    wire(ux + 12.7, uy + 10.16, hl_x, uy + 10.16)
    hier_label("GPS_TXD", hl_x, uy + 10.16, "output")

    wire(ux + 12.7, uy + 7.62, hl_x, uy + 7.62)
    hier_label("GPS_RXD", hl_x, uy + 7.62, "input")

    # TIMEPULSE (1PPS) -> global label GPS_1PPS
    wire(ux + 12.7, uy + 2.54, hl_x, uy + 2.54)
    global_label("GPS_1PPS", hl_x, uy + 2.54, "output")

    # D_SEL = GND for UART mode
    power_symbol("GND", ux - 18, uy - 2.54)
    wire(ux - 12.7, uy - 2.54, ux - 18, uy - 2.54)

    # RESET# with 10K pull-up
    resistor("10K", ux - 18, uy - 10, angle=0)
    wire(ux - 12.7, uy - 5.08, ux - 18, uy - 5.08)
    wire(ux - 18, uy - 6.19, ux - 18, uy - 5.08)
    power_symbol("+3V3A", ux - 18, uy - 17)
    wire(ux - 18, uy - 13.81, ux - 18, uy - 17)

    # V_BCKP to +3V3A (backup battery or rail)
    power_symbol("+3V3A", ux - 18, uy - 10.16)
    wire(ux - 12.7, uy - 10.16, ux - 18, uy - 10.16)

    # SDA/SCL not connected (UART mode)
    no_connect(ux + 12.7, uy - 5.08)
    no_connect(ux + 12.7, uy - 7.62)


def build_microsd(base_x, base_y):
    """Section 7: Micro-SD card slot."""
    text_note("MICRO-SD CARD SLOT", base_x, base_y - 5, 2.0)
    text_note("SD0: MIO[40:45], CD# to GPIO", base_x, base_y, 1.27)

    ux, uy = base_x + 50, base_y + 30
    ref = next_conn(); counts["connectors"] += 1
    symbol_instance("Connector_Generic:Conn_01x09", ref, "Micro_SD", ux, uy,
                    footprint="Connector_Card:microSD_HC_Hirose_DM3D-SF")
    symbol_pins(["1","2","3","4","5","6","7","8","9"])

    # VDD = +3V3
    power_symbol("+3V3", ux - 3.81, uy - 3)
    wire(ux - 3.81, uy + 2.54, ux - 3.81, uy - 3)

    # GND
    power_symbol("GND", ux - 3.81, uy + 8)
    wire(ux - 3.81, uy - 2.54, ux - 3.81, uy + 8)

    # Decoupling on VDDIO
    cap("100n", ux + 8, uy - 3)
    power_symbol("+3V3", ux + 8, uy - 8)
    wire(ux + 8, uy - 6.81, ux + 8, uy - 8)
    power_symbol("GND", ux + 8, uy + 2)
    wire(ux + 8, uy + 0.81, ux + 8, uy + 2)

    # Hierarchical labels for SD signals
    hl_x = ux - 15
    # DAT2 (pin 1) = MIO42
    wire(ux - 3.81, uy + 10.16, hl_x, uy + 10.16)
    hier_label("SD_MIO42", hl_x, uy + 10.16, "bidirectional", 180)
    # Pull-up
    resistor("10K", hl_x - 5, uy + 10.16, angle=90)
    wire(hl_x, uy + 10.16, hl_x - 5 + 3.81, uy + 10.16)
    power_symbol("+3V3", hl_x - 12, uy + 10.16)
    wire(hl_x - 5 - 3.81, uy + 10.16, hl_x - 12, uy + 10.16)

    # CD/DAT3 (pin 2) = MIO43
    wire(ux - 3.81, uy + 7.62, hl_x, uy + 7.62)
    hier_label("SD_MIO43", hl_x, uy + 7.62, "bidirectional", 180)
    resistor("10K", hl_x - 5, uy + 7.62, angle=90)
    wire(hl_x, uy + 7.62, hl_x - 5 + 3.81, uy + 7.62)
    power_symbol("+3V3", hl_x - 12, uy + 7.62)
    wire(hl_x - 5 - 3.81, uy + 7.62, hl_x - 12, uy + 7.62)

    # CMD (pin 3) = MIO41
    wire(ux - 3.81, uy + 5.08, hl_x, uy + 5.08)
    hier_label("SD_MIO41", hl_x, uy + 5.08, "bidirectional", 180)
    resistor("10K", hl_x - 5, uy + 5.08, angle=90)
    wire(hl_x, uy + 5.08, hl_x - 5 + 3.81, uy + 5.08)
    power_symbol("+3V3", hl_x - 12, uy + 5.08)
    wire(hl_x - 5 - 3.81, uy + 5.08, hl_x - 12, uy + 5.08)

    # CLK (pin 5) = MIO40
    wire(ux - 3.81, uy, hl_x, uy)
    hier_label("SD_MIO40", hl_x, uy, "bidirectional", 180)

    # DAT0 (pin 7) = MIO44
    wire(ux - 3.81, uy - 5.08, hl_x, uy - 5.08)
    hier_label("SD_MIO44", hl_x, uy - 5.08, "bidirectional", 180)
    resistor("10K", hl_x - 5, uy - 5.08, angle=90)
    wire(hl_x, uy - 5.08, hl_x - 5 + 3.81, uy - 5.08)
    power_symbol("+3V3", hl_x - 12, uy - 5.08)
    wire(hl_x - 5 - 3.81, uy - 5.08, hl_x - 12, uy - 5.08)

    # DAT1 (pin 8) = MIO45
    wire(ux - 3.81, uy - 7.62, hl_x, uy - 7.62)
    hier_label("SD_MIO45", hl_x, uy - 7.62, "bidirectional", 180)
    resistor("10K", hl_x - 5, uy - 7.62, angle=90)
    wire(hl_x, uy - 7.62, hl_x - 5 + 3.81, uy - 7.62)
    power_symbol("+3V3", hl_x - 12, uy - 7.62)
    wire(hl_x - 5 - 3.81, uy - 7.62, hl_x - 12, uy - 7.62)

    # CD# (pin 9) = GPIO card detect
    wire(ux - 3.81, uy - 10.16, hl_x, uy - 10.16)
    hier_label("SD_CD_N", hl_x, uy - 10.16, "input", 180)
    resistor("10K", hl_x - 5, uy - 10.16, angle=90)
    wire(hl_x, uy - 10.16, hl_x - 5 + 3.81, uy - 10.16)
    power_symbol("+3V3", hl_x - 12, uy - 10.16)
    wire(hl_x - 5 - 3.81, uy - 10.16, hl_x - 12, uy - 10.16)



def generate_tamper_section(base_x=30, base_y=500):
    """Tamper detection: mesh pull-down, lid switch pull-down, XADC alert label."""
    text_note('Tamper Detection (MIO0/MIO1/MIO2)', base_x, base_y - 5, size=2.0)

    # R_MESH: 10k pull-down on GPIO_TAMPER_MESH (MIO0)
    mesh_rx = base_x + 10
    mesh_ry = base_y + 10
    resistor('10k', mesh_rx, mesh_ry)
    wire(mesh_rx, mesh_ry - 2.54, mesh_rx, mesh_ry - 6)
    global_label('GPIO_TAMPER_MESH', mesh_rx, mesh_ry - 6, shape='input')
    wire(mesh_rx, mesh_ry + 2.54, mesh_rx, mesh_ry + 6)
    power_symbol('GND', mesh_rx, mesh_ry + 6)

    # R_LID: 10k pull-down on GPIO_TAMPER_LID (MIO1)
    lid_rx = base_x + 40
    lid_ry = base_y + 10
    resistor('10k', lid_rx, lid_ry)
    wire(lid_rx, lid_ry - 2.54, lid_rx, lid_ry - 6)
    global_label('GPIO_TAMPER_LID', lid_rx, lid_ry - 6, shape='input')
    wire(lid_rx, lid_ry + 2.54, lid_rx, lid_ry + 6)
    power_symbol('GND', lid_rx, lid_ry + 6)

    # XADC alert net label (MIO2) — combinational PL output, no pull resistor needed
    alert_x = base_x + 70
    alert_y = base_y + 10
    global_label('GPIO_ENV_ALERT', alert_x, alert_y, shape='output')

def main():
    # Header
    emit('(kicad_sch')
    emit('  (version 20231120)')
    emit('  (generator "cirradio_gen_peripherals")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board - Peripherals")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "QSPI, eMMC, USB PHY, Ethernet PHY, UART-USB, GPS, Micro-SD")')
    emit('    (comment 2 "Hierarchical labels match Zynq MIO assignments")')
    emit('  )')
    emit('')

    # Library symbols
    emit_lib_symbols()
    emit('')

    # ================================================================
    # SECTION 1: QSPI Flash (top-left)
    # ================================================================
    build_qspi(30, 20)

    # ================================================================
    # SECTION 2: eMMC Storage (top-right)
    # ================================================================
    build_emmc(200, 20)

    # ================================================================
    # SECTION 3: USB PHY (middle-left)
    # ================================================================
    build_usb_phy(30, 120)

    # ================================================================
    # SECTION 4: Ethernet PHY (middle-right)
    # ================================================================
    build_ethernet(200, 120)

    # ================================================================
    # SECTION 5: UART-USB Bridge (bottom-left)
    # ================================================================
    build_uart_usb(30, 280)

    # ================================================================
    # SECTION 6: GPS MAX-M10S (bottom-middle)
    # ================================================================
    build_gps(200, 280)

    # ================================================================
    # SECTION 7: Micro-SD Card Slot (bottom-right)
    # ================================================================
    build_microsd(30, 400)

    # ================================================================
    # SECTION 8: Tamper Detection (bottom)
    # ================================================================
    generate_tamper_section(30, 500)

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

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/peripherals.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"Component counts:")
    print(f"  ICs: {counts['ics']}")
    print(f"    - U10: S25FL256S (QSPI Flash)")
    print(f"    - U11: MTFC8GAKAJCN (eMMC 8GB)")
    print(f"    - U12: USB3320C (USB PHY)")
    print(f"    - U13: KSZ9031RNXIA (Ethernet PHY)")
    print(f"    - U14: FT232RQ (UART-USB Bridge)")
    print(f"    - U15: MAX-M10S (GPS)")
    print(f"  Connectors: {counts['connectors']}")
    print(f"    - USB-A (host), USB Micro-B (console), RJ45, U.FL (GPS), Micro-SD")
    print(f"  Crystal: 1 (25MHz for KSZ9031)")
    print(f"  Capacitors: {counts['capacitors']}")
    print(f"  Resistors: {counts['resistors']}")
    print(f"  Power symbols: {counts['symbols'] - counts['ics'] - counts['connectors'] - 1}")
    print(f"  Wires: {counts['wires']}")
    print(f"  Global labels: {counts['gl_labels']}")
    print(f"  Hierarchical labels: {counts['hier_labels']}")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")

if __name__ == "__main__":
    main()
