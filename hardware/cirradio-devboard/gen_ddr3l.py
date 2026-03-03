#!/usr/bin/env python3
"""Generate DDR3L memory schematic sheet for CIRRADIO dev board.

2x MT41K256M16HA-125 (U_DDR0, U_DDR1) with fly-by address/command topology,
VREFDQ dividers, ZQ calibration resistors, VTT termination, and decoupling.
"""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

# Reference designator counters (offset to avoid conflicts with other sheets)
# Power sheet: U1-U8, C1-C~60, R1-R~30; Zynq sheet: C100+, R100+
# DDR sheet: start at 200
cap_idx = [200]
res_idx = [200]
pwr_idx = [200]

def next_cap():
    c = cap_idx[0]; cap_idx[0] += 1; return f"C{c}"

def next_res():
    r = res_idx[0]; res_idx[0] += 1; return f"R{r}"

def next_pwr():
    p = pwr_idx[0]; pwr_idx[0] += 1; return f"#PWR{p:04d}"

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

def resistor(value, x, y, angle=0, fp="Resistor_SMD:R_0402_1005Metric"):
    counts["resistors"] += 1
    ref = next_res()
    symbol_instance("Device:R", ref, value, x, y, angle=angle, footprint=fp)
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

    # MT41K256M16HA DDR3L symbol (from cirradio.kicad_sym)
    emit('''    (symbol "cirradio:MT41K256M16HA"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 1.27 0) (effects (font (size 1.27 1.27))))
      (property "Value" "MT41K256M16HA" (at 0 -1.27 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "MT41K256M16HA_0_1"
        (rectangle (start -12.7 55.88) (end 12.7 -55.88)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "MT41K256M16HA_1_1"''')

    # DQ pins (right side, bidirectional)
    dq_ball_map = [
        ("DQ0","B7"),("DQ1","C7"),("DQ2","D6"),("DQ3","E6"),
        ("DQ4","F7"),("DQ5","F8"),("DQ6","G7"),("DQ7","G8"),
        ("DQ8","B2"),("DQ9","C2"),("DQ10","D1"),("DQ11","D2"),
        ("DQ12","E1"),("DQ13","E2"),("DQ14","F1"),("DQ15","F2"),
    ]
    y = 53.34
    for name, ball in dq_ball_map:
        emit(f'        (pin bidirectional line (at 15.24 {y} 180) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')
        y -= 2.54
        if name == "DQ7":
            y = 30.48  # gap between byte lanes

    # DQS pairs
    for name, ball, yp in [("LDQS","C8",7.62),("~{LDQS}","D8",5.08),
                            ("UDQS","C1",2.54),("~{UDQS}","D3",0)]:
        emit(f'        (pin bidirectional line (at 15.24 {yp} 180) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # DM pins
    for name, ball, yp in [("LDM","E7",-2.54),("UDM","G1",-5.08)]:
        emit(f'        (pin input line (at 15.24 {yp} 180) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # Address pins (left side, input)
    addr_balls = ["H2","G4","H3","G6","H4","H5","J2","J3","K2","K3","G5","J1","H1","K1","L3"]
    y = 53.34
    for i, ball in enumerate(addr_balls):
        emit(f'        (pin input line (at -15.24 {y} 0) (length 2.54) (name "A{i}" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')
        y -= 2.54

    # Bank address
    ba_balls = [("BA0","H7",12.7),("BA1","H8",10.16),("BA2","J8",7.62)]
    for name, ball, yp in ba_balls:
        emit(f'        (pin input line (at -15.24 {yp} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # Command/control pins
    ctrl_pins = [
        ("~{RAS}","H6",2.54),("~{CAS}","J6",0),("~{WE}","K6",-2.54),
        ("CK","J4",-7.62),("~{CK}","K4",-10.16),
        ("CKE","L4",-12.7),("~{CS}","L6",-15.24),
        ("ODT","K7",-17.78),("~{RESET}","L1",-20.32),
    ]
    for name, ball, yp in ctrl_pins:
        emit(f'        (pin input line (at -15.24 {yp} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # ZQ and VREFDQ
    emit('        (pin passive line (at -15.24 -25.4 0) (length 2.54) (name "ZQ" (effects (font (size 1.27 1.27)))) (number "A8" (effects (font (size 1.27 1.27)))))')
    emit('        (pin input line (at -15.24 -27.94 0) (length 2.54) (name "VREFDQ" (effects (font (size 1.27 1.27)))) (number "K8" (effects (font (size 1.27 1.27)))))')

    # VDD power pins
    for ball in ["A4","G3","L8"]:
        emit(f'        (pin power_in line (at -15.24 -33.02 0) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # VDDQ power pins
    for ball in ["A2","A5","A7"]:
        emit(f'        (pin power_in line (at -15.24 -40.64 0) (length 2.54) (name "VDDQ" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # VSS pins
    for ball in ["A1","A3","A6","B4","B5"]:
        emit(f'        (pin power_in line (at 0 -58.42 90) (length 2.54) (name "VSS" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    # VSSQ pins
    for ball in ["B1","B3","B6","B8"]:
        emit(f'        (pin power_in line (at 0 -58.42 90) (length 2.54) (name "VSSQ" (effects (font (size 1.27 1.27)))) (number "{ball}" (effects (font (size 1.27 1.27)))))')

    emit('      )')
    emit('    )')

    # Power symbols
    for net in ["+1V35", "GND"]:
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
# Pin lists for the MT41K256M16HA symbol
# ============================================================
DDR_ALL_PINS = [
    # DQ
    "B7","C7","D6","E6","F7","F8","G7","G8",
    "B2","C2","D1","D2","E1","E2","F1","F2",
    # DQS
    "C8","D8","C1","D3",
    # DM
    "E7","G1",
    # Address
    "H2","G4","H3","G6","H4","H5","J2","J3","K2","K3","G5","J1","H1","K1","L3",
    # Bank address
    "H7","H8","J8",
    # Control
    "H6","J6","K6","J4","K4","L4","L6","K7","L1",
    # ZQ, VREFDQ
    "A8","K8",
    # VDD
    "A4","G3","L8",
    # VDDQ
    "A2","A5","A7",
    # VSS
    "A1","A3","A6","B4","B5",
    # VSSQ
    "B1","B3","B6","B8",
]


def place_ddr_chip(ref, value, cx, cy, dq_label_prefix, dq_start_index, dqs_labels, dm_labels, footprint):
    """Place one MT41K256M16HA and connect its data/strobe/mask pins.

    dq_label_prefix: e.g. "DDR_DQ"
    dq_start_index: 0 for U_DDR0 (DDR_DQ0..15), 16 for U_DDR1 (DDR_DQ16..31)
    dqs_labels: list of 4 labels [DQS_P_low, DQS_N_low, DQS_P_high, DQS_N_high]
    dm_labels:  list of 2 labels [DM_low, DM_high]
    """
    symbol_instance("cirradio:MT41K256M16HA", ref, value, cx, cy,
                    footprint=footprint)
    symbol_pins(DDR_ALL_PINS)

    hl_right = cx + 22  # hierarchical labels on right of data bus
    hl_left = cx - 22   # hierarchical labels on left for addr/ctrl

    # ---- Data bus (right side of symbol) ----
    # DQ[0:7] at symbol y offsets 53.34 down by 2.54
    for i in range(8):
        y = cy + 53.34 - i * 2.54
        wire(cx + 15.24, y, hl_right, y)
        hier_label(f"{dq_label_prefix}{dq_start_index + i}", hl_right, y, "bidirectional")

    # DQ[8:15] at symbol y offset 30.48 down by 2.54
    for i in range(8):
        y = cy + 30.48 - i * 2.54
        wire(cx + 15.24, y, hl_right, y)
        hier_label(f"{dq_label_prefix}{dq_start_index + 8 + i}", hl_right, y, "bidirectional")

    # DQS pairs (right side)
    dqs_y_offsets = [7.62, 5.08, 2.54, 0]  # LDQS, ~LDQS, UDQS, ~UDQS
    for idx, y_off in enumerate(dqs_y_offsets):
        y = cy + y_off
        wire(cx + 15.24, y, hl_right, y)
        hier_label(dqs_labels[idx], hl_right, y, "bidirectional")

    # DM pins (right side)
    dm_y_offsets = [-2.54, -5.08]  # LDM, UDM
    for idx, y_off in enumerate(dm_y_offsets):
        y = cy + y_off
        wire(cx + 15.24, y, hl_right, y)
        hier_label(dm_labels[idx], hl_right, y, "input", 0)

    # ---- Address bus (left side) - hierarchical labels ----
    for i in range(15):
        y = cy + 53.34 - i * 2.54
        wire(cx - 15.24, y, hl_left, y)
        hier_label(f"DDR_A{i}", hl_left, y, "input", 180)

    # Bank address
    ba_y = [12.7, 10.16, 7.62]
    for i in range(3):
        y = cy + ba_y[i]
        wire(cx - 15.24, y, hl_left, y)
        hier_label(f"DDR_BA{i}", hl_left, y, "input", 180)

    # Control signals
    ctrl_signals = [
        ("DDR_RAS_B", 2.54), ("DDR_CAS_B", 0), ("DDR_WE_B", -2.54),
        ("DDR_CK_P", -7.62), ("DDR_CK_N", -10.16),
        ("DDR_CKE", -12.7), ("DDR_CS_B", -15.24),
        ("DDR_ODT", -17.78), ("DDR_RESET_B", -20.32),
    ]
    for name, y_off in ctrl_signals:
        y = cy + y_off
        wire(cx - 15.24, y, hl_left, y)
        hier_label(name, hl_left, y, "input", 180)

    # ---- ZQ calibration resistor (240R 1% to GND) ----
    zq_y = cy - 25.4
    wire(cx - 15.24, zq_y, cx - 25, zq_y)
    resistor("240R 1%", cx - 32, zq_y, angle=90, fp="Resistor_SMD:R_0402_1005Metric")
    wire(cx - 25, zq_y, cx - 32 + 3.81, zq_y)
    wire(cx - 32 - 3.81, zq_y, cx - 40, zq_y)
    power_symbol("GND", cx - 40, zq_y)

    # ---- VREFDQ divider (2x 240R from +1V35 with 100nF bypass) ----
    vref_y = cy - 27.94
    wire(cx - 15.24, vref_y, cx - 25, vref_y)
    # Upper resistor (+1V35 to midpoint)
    resistor("240R", cx - 32, vref_y - 8, angle=0)
    wire(cx - 32, vref_y - 8 - 3.81, cx - 32, vref_y - 14)
    global_label("+1V35", cx - 32, vref_y - 14, "passive")
    wire(cx - 32, vref_y - 8 + 3.81, cx - 32, vref_y)
    wire(cx - 32, vref_y, cx - 25, vref_y)
    # Lower resistor (midpoint to GND)
    resistor("240R", cx - 32, vref_y + 8, angle=0)
    wire(cx - 32, vref_y + 8 - 3.81, cx - 32, vref_y)
    wire(cx - 32, vref_y + 8 + 3.81, cx - 32, vref_y + 14)
    power_symbol("GND", cx - 32, vref_y + 14)
    # Bypass cap on VREFDQ node
    cap("100n", cx - 25, vref_y + 6, "Capacitor_SMD:C_0402_1005Metric")
    wire(cx - 25, vref_y, cx - 25, vref_y + 2.19)
    wire(cx - 25, vref_y + 9.81, cx - 25, vref_y + 12)
    power_symbol("GND", cx - 25, vref_y + 12)

    # ---- Power connections ----
    # VDD (pin at cy - 33.02)
    vdd_y = cy - 33.02
    global_label("+1V35", cx - 22, vdd_y, "passive")
    wire(cx - 15.24, vdd_y, cx - 22, vdd_y)

    # VDDQ (pin at cy - 40.64)
    vddq_y = cy - 40.64
    global_label("+1V35", cx - 22, vddq_y, "passive")
    wire(cx - 15.24, vddq_y, cx - 22, vddq_y)

    # VSS/VSSQ (bottom, pin at cy - 58.42)
    vss_y = cy - 58.42
    power_symbol("GND", cx, vss_y + 2, angle=0)
    wire(cx, vss_y, cx, vss_y + 2)


def place_vtt_termination(x, y):
    """Place 47R series termination resistors at end of fly-by for address/command.

    These terminate the fly-by topology after U_DDR1.
    """
    text_note("VTT TERMINATION (47R at fly-by end)", x, y - 5, 1.27)
    text_note("Connect VTT to +1V35/2 = 0.675V from power sheet", x, y - 8, 1.0)

    # Address lines A[0:14] + BA[0:2] + RAS# + CAS# + WE# + CKE + CS# + ODT = 24 signals
    # CK/CK# are differential pair - terminated by on-die ODT, not here
    # RESET# is DC - no termination needed
    term_signals = (
        [f"DDR_A{i}" for i in range(15)] +
        ["DDR_BA0", "DDR_BA1", "DDR_BA2"] +
        ["DDR_RAS_B", "DDR_CAS_B", "DDR_WE_B", "DDR_CKE", "DDR_CS_B", "DDR_ODT"]
    )

    cx = x
    for i, sig in enumerate(term_signals):
        row = i // 12
        col = i % 12
        rx = cx + col * 8
        ry = y + row * 18

        hier_label(sig, rx - 3, ry, "input", 0)
        wire(rx - 3, ry, rx, ry)
        resistor("47R", rx + 4, ry, angle=90)
        wire(rx, ry, rx + 4 - 3.81, ry)
        wire(rx + 4 + 3.81, ry, rx + 10, ry)
        global_label("VTT", rx + 10, ry, "passive")


def main():
    # ================================================================
    # Header
    # ================================================================
    emit('(kicad_sch')
    emit('  (version 20231120)')
    emit('  (generator "cirradio_gen_ddr3l")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board - DDR3L Memory (2x MT41K256M16HA-125)")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "1GB DDR3L: 2x 256Mx16 = 32-bit bus, fly-by address/command")')
    emit('    (comment 2 "VDD=VDDQ=+1V35, ZQ=240R 1%, VREFDQ=VDD/2 divider")')
    emit('  )')
    emit('')

    # Library symbols
    emit_lib_symbols()
    emit('')

    # ================================================================
    # SECTION 1: U_DDR0 - Byte lanes 0,1 (DDR_DQ[0:15])
    # ================================================================
    text_note("DDR3L U_DDR0 - Byte Lanes 0,1 (DDR_DQ[0:15])", 30, 20, 2.0)
    text_note("MT41K256M16HA-125:E  256Mx16  DDR3L-1600  1.35V", 30, 25, 1.27)

    ddr0_x, ddr0_y = 100, 100
    place_ddr_chip(
        ref="U_DDR0", value="MT41K256M16HA-125",
        cx=ddr0_x, cy=ddr0_y,
        dq_label_prefix="DDR_DQ",
        dq_start_index=0,  # DDR_DQ0..DDR_DQ15
        dqs_labels=["DDR_DQS_P0", "DDR_DQS_N0", "DDR_DQS_P1", "DDR_DQS_N1"],
        dm_labels=["DDR_DM0", "DDR_DM1"],
        footprint="cirradio:BGA-96_9x14_0.8mm",
    )

    # ================================================================
    # SECTION 2: U_DDR1 - Byte lanes 2,3 (DDR_DQ[16:31])
    # ================================================================
    text_note("DDR3L U_DDR1 - Byte Lanes 2,3 (DDR_DQ[16:31])", 230, 20, 2.0)
    text_note("MT41K256M16HA-125:E  256Mx16  DDR3L-1600  1.35V", 230, 25, 1.27)

    ddr1_x, ddr1_y = 300, 100
    place_ddr_chip(
        ref="U_DDR1", value="MT41K256M16HA-125",
        cx=ddr1_x, cy=ddr1_y,
        dq_label_prefix="DDR_DQ",
        dq_start_index=16,  # DDR_DQ16..DDR_DQ31
        dqs_labels=["DDR_DQS_P2", "DDR_DQS_N2", "DDR_DQS_P3", "DDR_DQS_N3"],
        dm_labels=["DDR_DM2", "DDR_DM3"],
        footprint="cirradio:BGA-96_9x14_0.8mm",
    )

    # ================================================================
    # SECTION 3: U_DDR0 Decoupling
    # ================================================================
    text_note("U_DDR0 DECOUPLING", 30, 230, 2.0)

    # VDD: 4x 100nF + 1x 10uF
    decoupling_group("+1V35", 30, 250, 4, 1, "U_DDR0 VDD")

    # VDDQ: 4x 100nF + 1x 10uF
    decoupling_group("+1V35", 30, 280, 4, 1, "U_DDR0 VDDQ")

    # ================================================================
    # SECTION 4: U_DDR1 Decoupling
    # ================================================================
    text_note("U_DDR1 DECOUPLING", 230, 230, 2.0)

    decoupling_group("+1V35", 230, 250, 4, 1, "U_DDR1 VDD")
    decoupling_group("+1V35", 230, 280, 4, 1, "U_DDR1 VDDQ")

    # ================================================================
    # SECTION 5: VTT Termination at end of fly-by
    # ================================================================
    place_vtt_termination(30, 320)

    # ================================================================
    # SECTION 6: Routing notes
    # ================================================================
    text_note("ROUTING NOTES:", 30, 380, 2.0)
    text_note("1. Fly-by topology: Zynq -> U_DDR0 -> U_DDR1 for address/command/clock", 30, 386, 1.27)
    text_note("2. Match DQ/DQS trace lengths within each byte lane (+/- 5 mil)", 30, 390, 1.27)
    text_note("3. Match DQS-to-CK skew within each chip (+/- 10 mil)", 30, 394, 1.27)
    text_note("4. CK/CK# and DQS/DQS# are 100-ohm differential pairs", 30, 398, 1.27)
    text_note("5. Single-ended impedance target: 40 ohm (DDR3L)", 30, 402, 1.27)
    text_note("6. Differential impedance target: 80 ohm", 30, 406, 1.27)
    text_note("7. Place decoupling caps within 2mm of BGA balls", 30, 410, 1.27)
    text_note("8. ZQ resistor: 240R 1% tolerance, place within 5mm of ZQ ball", 30, 414, 1.27)
    text_note("9. VREFDQ divider: place within 10mm of VREFDQ ball", 30, 418, 1.27)
    text_note("10. VTT termination resistors at far end of fly-by (after U_DDR1)", 30, 422, 1.27)

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

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/ddr3l.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"Component counts:")
    print(f"  DDR3L chips: 2 (U_DDR0, U_DDR1)")
    print(f"  Capacitors: {counts['capacitors']}")
    print(f"  Resistors: {counts['resistors']}")
    print(f"  Power symbols: {pwr_idx[0] - 200}")
    print(f"  Wires: {counts['wires']}")
    print(f"  Global labels: {counts['gl_labels']}")
    print(f"  Hierarchical labels: {counts['hier_labels']}")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")

if __name__ == "__main__":
    main()
