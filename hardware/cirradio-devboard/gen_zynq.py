#!/usr/bin/env python3
"""Generate Zynq-7045 schematic sheet for CIRRADIO dev board."""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

# Counters for reference designators (power sheet uses U1-U8, C1-C~60, R1-R~30, D1-D~2)
# We start fresh with high numbers to avoid conflicts
cap_idx = [100]  # mutable counter
res_idx = [100]
pwr_idx = [100]

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

def resistor(value, x, y, angle=0):
    counts["resistors"] += 1
    ref = next_res()
    symbol_instance("Device:R", ref, value, x, y, angle=angle)
    symbol_pins(["1", "2"])


def decoupling_group(rail_net, x, y, n_100nf, n_10uf, label_text):
    """Place a group of decoupling caps for a power rail."""
    text_note(f"{label_text} decoupling", x, y - 5, 1.27)
    # Power rail label at top
    global_label(rail_net, x, y - 2, "passive")
    wire(x, y - 2, x, y)

    # Place 100nF caps in a row
    cx = x
    for i in range(n_100nf):
        wire(cx, y, cx, y + 1.27)
        cap("100n", cx, y + 5.08, "Capacitor_SMD:C_0402_1005Metric")
        wire(cx, y + 8.89, cx, y + 10)
        power_symbol("GND", cx, y + 10)
        cx += 5

    # Place 10uF caps after
    for i in range(n_10uf):
        wire(cx, y, cx, y + 1.27)
        cap("10u", cx, y + 5.08, "Capacitor_SMD:C_0805_2012Metric")
        wire(cx, y + 8.89, cx, y + 10)
        power_symbol("GND", cx, y + 10)
        cx += 5

    # Horizontal bus wire connecting all caps
    if n_100nf + n_10uf > 1:
        wire(x, y, x + (n_100nf + n_10uf - 1) * 5, y)

    return cx  # return next free x


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

    # Device:LED
    emit('''    (symbol "Device:LED"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "D" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "LED" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "LED_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -1.27 0) (xy 1.27 0)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27) (xy -1.27 0) (xy 1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "LED_1_1"
        (pin passive line (at -3.81 0 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # XC7Z045 - 9-unit symbol (inline from library)
    emit('''    (symbol "cirradio:XC7Z045"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 1.27 0) (effects (font (size 1.27 1.27))))
      (property "Value" "XC7Z045-2FFG900I" (at 0 -1.27 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "XC7Z045_1_1"
        (rectangle (start -12.7 30.48) (end 12.7 -30.48) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin input line (at -15.24 27.94 0) (length 2.54) (name "PS_CLK" (effects (font (size 1.27 1.27)))) (number "C8" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 25.4 0) (length 2.54) (name "PS_POR_B" (effects (font (size 1.27 1.27)))) (number "B10" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 22.86 0) (length 2.54) (name "PS_SRST_B" (effects (font (size 1.27 1.27)))) (number "C10" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 15.24 27.94 180) (length 2.54) (name "INIT_B" (effects (font (size 1.27 1.27)))) (number "T12" (effects (font (size 1.27 1.27)))))
        (pin output line (at 15.24 25.4 180) (length 2.54) (name "DONE" (effects (font (size 1.27 1.27)))) (number "U11" (effects (font (size 1.27 1.27)))))
        (pin input line (at 15.24 22.86 180) (length 2.54) (name "PROG_B" (effects (font (size 1.27 1.27)))) (number "T11" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 17.78 0) (length 2.54) (name "BOOT_MODE0" (effects (font (size 1.27 1.27)))) (number "G7" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 15.24 0) (length 2.54) (name "BOOT_MODE1" (effects (font (size 1.27 1.27)))) (number "G8" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 12.7 0) (length 2.54) (name "BOOT_MODE2" (effects (font (size 1.27 1.27)))) (number "H7" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 10.16 0) (length 2.54) (name "BOOT_MODE3" (effects (font (size 1.27 1.27)))) (number "H8" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 5.08 0) (length 2.54) (name "TDI" (effects (font (size 1.27 1.27)))) (number "R13" (effects (font (size 1.27 1.27)))))
        (pin output line (at -15.24 2.54 0) (length 2.54) (name "TDO" (effects (font (size 1.27 1.27)))) (number "P13" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 0 0) (length 2.54) (name "TMS" (effects (font (size 1.27 1.27)))) (number "N13" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 -2.54 0) (length 2.54) (name "TCK" (effects (font (size 1.27 1.27)))) (number "M13" (effects (font (size 1.27 1.27)))))
        (pin input line (at -15.24 -5.08 0) (length 2.54) (name "TRST" (effects (font (size 1.27 1.27)))) (number "L13" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 17.78 180) (length 2.54) (name "PS_MIO_VREF_500" (effects (font (size 1.27 1.27)))) (number "C3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 15.24 15.24 180) (length 2.54) (name "PS_MIO_VREF_501" (effects (font (size 1.27 1.27)))) (number "E3" (effects (font (size 1.27 1.27)))))
      )
      (symbol "XC7Z045_2_1"
        (rectangle (start -10.16 72.39) (end 10.16 -72.39) (stroke (width 0.254) (type default)) (fill (type background)))''')

    # Unit 2 MIO pins
    for i in range(54):
        y_pos = 71.12 - i * 2.54
        mio_pins = {
            0:"A4",1:"B4",2:"A5",3:"B5",4:"A6",5:"B6",6:"A7",7:"E5",8:"D5",9:"E6",
            10:"B7",11:"D6",12:"C7",13:"E7",14:"D7",15:"B8",16:"A9",17:"B9",18:"E8",
            19:"D8",20:"C9",21:"E9",22:"D9",23:"A10",24:"E10",25:"D10",26:"C11",
            27:"B11",28:"A11",29:"E11",30:"D11",31:"A12",32:"B12",33:"C12",34:"D12",
            35:"E12",36:"A13",37:"B13",38:"C13",39:"D13",40:"E13",41:"F7",42:"F8",
            43:"F9",44:"F10",45:"F11",46:"F12",47:"F13",48:"G6",49:"G9",50:"G10",
            51:"G11",52:"G12",53:"G13"
        }
        pin_num = mio_pins[i]
        emit(f'        (pin bidirectional line (at 12.7 {y_pos} 180) (length 2.54) (name "MIO{i}" (effects (font (size 1.27 1.27)))) (number "{pin_num}" (effects (font (size 1.27 1.27)))))')

    emit('      )')

    # Unit 3 - DDR (simplified - just key signals)
    emit('''      (symbol "XC7Z045_3_1"
        (rectangle (start -12.7 53.34) (end 12.7 -53.34) (stroke (width 0.254) (type default)) (fill (type background)))''')

    # DDR DQ pins
    dq_pins = ["H1","H2","H3","J1","J2","J3","K1","K2","K3","L1","L2","L3","M1","M2","M3","N1",
               "N2","N3","P1","P2","P3","R1","R2","R3","T1","T2","T3","U1","U2","U3","V1","V2"]
    for i in range(32):
        y_pos = 50.8 - i * 2.54
        emit(f'        (pin bidirectional line (at 15.24 {y_pos} 180) (length 2.54) (name "DDR_DQ{i}" (effects (font (size 1.27 1.27)))) (number "{dq_pins[i]}" (effects (font (size 1.27 1.27)))))')

    # DQS pairs
    dqs_data = [("DDR_DQS_P0","H4",50.8),("DDR_DQS_N0","H5",48.26),
                ("DDR_DQS_P1","J4",45.72),("DDR_DQS_N1","J5",43.18),
                ("DDR_DQS_P2","K4",40.64),("DDR_DQS_N2","K5",38.1),
                ("DDR_DQS_P3","L4",35.56),("DDR_DQS_N3","L5",33.02)]
    for name, pin, y in dqs_data:
        emit(f'        (pin bidirectional line (at -15.24 {y} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{pin}" (effects (font (size 1.27 1.27)))))')

    # DM pins
    dm_data = [("DDR_DM0","M4",27.94),("DDR_DM1","M5",25.4),("DDR_DM2","N4",22.86),("DDR_DM3","N5",20.32)]
    for name, pin, y in dm_data:
        emit(f'        (pin output line (at -15.24 {y} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{pin}" (effects (font (size 1.27 1.27)))))')

    # Address pins
    addr_pins = ["P4","P5","R4","R5","T4","T5","U4","U5","V3","V4","V5","W3","W4","W5","Y3"]
    for i in range(15):
        y_pos = 15.24 - i * 2.54
        emit(f'        (pin output line (at -15.24 {y_pos} 0) (length 2.54) (name "DDR_A{i}" (effects (font (size 1.27 1.27)))) (number "{addr_pins[i]}" (effects (font (size 1.27 1.27)))))')

    # Bank address
    ba_data = [("DDR_BA0","Y4",-25.4),("DDR_BA1","Y5",-27.94),("DDR_BA2","AA3",-30.48)]
    for name, pin, y in ba_data:
        emit(f'        (pin output line (at -15.24 {y} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{pin}" (effects (font (size 1.27 1.27)))))')

    # Control signals
    ctrl_data = [("DDR_CAS_B","AA4",-33.02),("DDR_RAS_B","AA5",-35.56),("DDR_WE_B","AB3",-38.1),
                 ("DDR_CK_P","AB4",-40.64),("DDR_CK_N","AB5",-43.18),("DDR_CKE","AC3",-45.72),
                 ("DDR_CS_B","AC4",-48.26),("DDR_ODT","AC5",-50.8)]
    for name, pin, y in ctrl_data:
        emit(f'        (pin output line (at -15.24 {y} 0) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{pin}" (effects (font (size 1.27 1.27)))))')

    # DDR misc on right side
    misc_data = [("DDR_RESET_B","AD3",-33.02),("DDR_VREF0","AD4",-38.1),("DDR_VREF1","AD5",-40.64),
                 ("PS_DDR_VRN","AE3",-45.72),("PS_DDR_VRP","AE4",-48.26)]
    for name, pin, y in misc_data:
        ptype = "output" if "RESET" in name else "passive"
        emit(f'        (pin {ptype} line (at 15.24 {y} 180) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{pin}" (effects (font (size 1.27 1.27)))))')

    emit('      )')

    # Units 4-8 simplified (just rectangles with pin stubs for key signals)
    for unit_num, unit_name, pin_prefix, n_pins, pin_start_nums in [
        (4, "XC7Z045_4_1", "B33_L", 50, None),
        (5, "XC7Z045_5_1", "B34_L", 50, None),
        (6, "XC7Z045_6_1", "B13_IO", 50, None),
        (7, "XC7Z045_7_1", "B12_IO", 50, None),
        (8, "XC7Z045_8_1", "SPARE_IO", 50, None),
    ]:
        emit(f'      (symbol "{unit_name}"')
        emit(f'        (rectangle (start -10.16 66.04) (end 10.16 -66.04) (stroke (width 0.254) (type default)) (fill (type background)))')

        # Generate pin stubs - use simple sequential pin numbers
        # Pin numbers from the actual symbol library
        if unit_num == 4:
            pin_names_list = [f"B33_L{i//2}{'P' if i%2==0 else 'N'}" for i in range(48)] + ["B33_L24P", "B33_L24N"]
            base_pins = ["AA14","AA15","AB14","AB15","AC14","AC15","AD14","AD15",
                        "AE14","AE15","AF14","AF15","AA16","AA17","AB16","AB17",
                        "AC16","AC17","AD16","AD17","AE16","AE17","AF16","AF17",
                        "AA18","AA19","AB18","AB19","AC18","AC19","AD18","AD19",
                        "AE18","AE19","AF18","AF19","AA20","AA21","AB20","AB21",
                        "AC20","AC21","AD20","AD21","AE20","AE21","AF20","AF21",
                        "AA22","AA23"]
        elif unit_num == 5:
            pin_names_list = [f"B34_L{i//2}{'P' if i%2==0 else 'N'}" for i in range(48)] + ["B34_L24P", "B34_L24N"]
            base_pins = ["AA24","AA25","AB24","AB25","AC24","AC25","AD24","AD25",
                        "AE24","AE25","AF24","AF25","AA26","AA27","AB26","AB27",
                        "AC26","AC27","AD26","AD27","AE26","AE27","AF26","AF27",
                        "AA28","AA29","AB28","AB29","AC28","AC29","AD28","AD29",
                        "AE28","AE29","AF28","AF29","AA30","AB30","AC30","AD30",
                        "AE30","AF30","Y14","Y15","Y16","Y17","Y18","Y19",
                        "Y20","Y21"]
        elif unit_num == 6:
            pin_names_list = [f"B13_IO{i}" for i in range(50)]
            base_pins = ["A14","B14","C14","D14","E14","F14","A15","B15",
                        "C15","D15","E15","F15","A16","B16","C16","D16",
                        "E16","F16","A17","B17","C17","D17","E17","F17",
                        "A18","B18","C18","D18","E18","F18","A19","B19",
                        "C19","D19","E19","F19","A20","B20","C20","D20",
                        "E20","F20","A21","B21","C21","D21","E21","F21",
                        "A22","B22"]
        elif unit_num == 7:
            pin_names_list = [f"B12_IO{i}" for i in range(50)]
            base_pins = ["A23","B23","C23","D23","E23","F23","A24","B24",
                        "C24","D24","E24","F24","A25","B25","C25","D25",
                        "E25","F25","A26","B26","C26","D26","E26","F26",
                        "A27","B27","C27","D27","E27","F27","A28","B28",
                        "C28","D28","E28","F28","A29","B29","C29","D29",
                        "E29","F29","A30","B30","C30","D30","G14","G15",
                        "G16","G17"]
        else:  # unit 8
            pin_names_list = [f"SPARE_IO{i}" for i in range(50)]
            base_pins = ["H14","H15","H16","H17","J14","J15","J16","J17",
                        "K14","K15","K16","K17","L14","L15","L16","L17",
                        "M14","M15","M16","M17","N14","N15","N16","N17",
                        "P14","P15","P16","P17","R14","R15","R16","R17",
                        "T14","T15","T16","T17","U14","U15","U16","U17",
                        "V14","V15","V16","V17","W14","W15","W16","W17",
                        "Y6","Y7"]

        for i in range(n_pins):
            y_pos = 63.5 - i * 2.54
            if i == n_pins - 1:
                y_pos = -63.5  # last pin at bottom
            emit(f'        (pin bidirectional line (at 12.7 {y_pos} 180) (length 2.54) (name "{pin_names_list[i]}" (effects (font (size 1.27 1.27)))) (number "{base_pins[i]}" (effects (font (size 1.27 1.27)))))')
        emit('      )')

    # Unit 9 - Power
    emit('      (symbol "XC7Z045_9_1"')
    emit('        (rectangle (start -12.7 55.88) (end 12.7 -55.88) (stroke (width 0.254) (type default)) (fill (type background)))')

    # VCCINT pins (15 pins)
    vccint_pins = ["G18","G19","G20","G21","G22","G23","G24","G25","G26","G27","H18","H19","H20","H21","H22"]
    for p in vccint_pins:
        emit(f'        (pin power_in line (at -15.24 53.34 0) (length 2.54) (name "VCCINT" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # VCCAUX (4 pins)
    vccaux_pins = ["H23","H24","H25","H26"]
    for p in vccaux_pins:
        emit(f'        (pin power_in line (at -15.24 48.26 0) (length 2.54) (name "VCCAUX" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # VCCBRAM (2 pins)
    for p in ["H27","H28"]:
        emit(f'        (pin power_in line (at -15.24 43.18 0) (length 2.54) (name "VCCBRAM" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # VCCO banks
    for p in ["J18","J19"]:
        emit(f'        (pin power_in line (at -15.24 38.1 0) (length 2.54) (name "VCCO_33" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')
    for p in ["J20","J21"]:
        emit(f'        (pin power_in line (at -15.24 35.56 0) (length 2.54) (name "VCCO_34" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')
    for p in ["J22","J23"]:
        emit(f'        (pin power_in line (at -15.24 33.02 0) (length 2.54) (name "VCCO_13" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')
    for p in ["J24","J25"]:
        emit(f'        (pin power_in line (at -15.24 30.48 0) (length 2.54) (name "VCCO_12" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # VCCPINT (4 pins)
    for p in ["J26","J27","J28","K18"]:
        emit(f'        (pin power_in line (at -15.24 25.4 0) (length 2.54) (name "VCCPINT" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # VCCPAUX (2 pins)
    for p in ["K19","K20"]:
        emit(f'        (pin power_in line (at -15.24 20.32 0) (length 2.54) (name "VCCPAUX" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # VCCPLL (2 pins)
    for p in ["K21","K22"]:
        emit(f'        (pin power_in line (at -15.24 15.24 0) (length 2.54) (name "VCCPLL" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    # GND pins (many)
    gnd_pins = ["K23","K24","K25","K26","K27","K28","L18","L19","L20","L21","L22","L23",
                "L24","L25","L26","L27","L28","M18","M19","M20","M21","M22","M23","M24",
                "M25","M26","M27","M28","N18","N19","N20"]
    for p in gnd_pins:
        emit(f'        (pin power_in line (at 15.24 53.34 180) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "{p}" (effects (font (size 1.27 1.27)))))')

    emit('      )')
    emit('    )')

    # DSC1001CI2-33.333 oscillator
    emit('''    (symbol "cirradio:DSC1001CI2-33.333"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "Y" (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "DSC1001CI2-33.333" (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "DSC1001CI2-33.333_0_1"
        (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "DSC1001CI2-33.333_1_1"
        (pin input line (at -7.62 2.54 0) (length 2.54) (name "EN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -7.62 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin output line (at 7.62 2.54 180) (length 2.54) (name "OUT" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 7.62 270) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Connector_Generic:Conn_02x07_Odd_Even (JTAG header)
    emit('''    (symbol "Connector_Generic:Conn_02x07_Odd_Even"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 1.27 10.16 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_02x07_Odd_Even" (at 1.27 -10.16 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "Conn_02x07_Odd_Even_1_1"
        (rectangle (start -1.27 8.89) (end 3.81 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -3.81 7.62 0) (length 2.54) (name "Pin_1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 7.62 180) (length 2.54) (name "Pin_2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 5.08 0) (length 2.54) (name "Pin_3" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 5.08 180) (length 2.54) (name "Pin_4" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 2.54 0) (length 2.54) (name "Pin_5" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 2.54 180) (length 2.54) (name "Pin_6" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 0 0) (length 2.54) (name "Pin_7" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 0 180) (length 2.54) (name "Pin_8" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -2.54 0) (length 2.54) (name "Pin_9" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 -2.54 180) (length 2.54) (name "Pin_10" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -5.08 0) (length 2.54) (name "Pin_11" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 -5.08 180) (length 2.54) (name "Pin_12" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -3.81 -7.62 0) (length 2.54) (name "Pin_13" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 -7.62 180) (length 2.54) (name "Pin_14" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Switch:SW_DIP_x02
    emit('''    (symbol "Switch:SW_DIP_x02"
      (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "SW" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
      (property "Value" "SW_DIP_x02" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "SW_DIP_x02_0_1"
        (rectangle (start -3.81 3.81) (end 3.81 -3.81) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "SW_DIP_x02_1_1"
        (pin passive line (at -6.35 2.54 0) (length 2.54) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -6.35 0 0) (length 2.54) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 2.54 180) (length 2.54) (name "3" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 6.35 0 180) (length 2.54) (name "4" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Switch:SW_Push (reset button)
    emit('''    (symbol "Switch:SW_Push"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "SW" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
      (property "Value" "SW_Push" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "SW_Push_0_1"
        (circle (center -2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
        (circle (center 2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 1.524) (xy 0 3.048)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 1.524) (xy 2.54 1.524)) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "SW_Push_1_1"
        (pin passive line (at -5.08 0 0) (length 2.54) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 5.08 0 180) (length 2.54) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Power symbols
    for net, arrow_up in [("+1V0", True), ("+1V5", True), ("+1V8", True),
                           ("+3V3", True), ("+3V3A", True), ("GND", False)]:
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
    emit('  (generator "cirradio_gen_zynq")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board - Zynq-7045 SoC")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "Zynq-7045 with boot config, clocking, JTAG, decoupling")')
    emit('    (comment 2 "9 units: PS Config, PS MIO, PS DDR, PL Banks 33/34/13/12, Spare, Power")')
    emit('  )')
    emit('')

    # Library symbols
    emit_lib_symbols()
    emit('')

    # ================================================================
    # SECTION 1: Zynq Unit 1 - PS Config (top-left area)
    # ================================================================
    text_note("ZYNQ-7045 PS CONFIG (Unit 1)", 30, 20, 2.0)
    text_note("Boot mode, JTAG, clock, reset", 30, 25, 1.27)

    u1_x, u1_y = 80, 70
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u1_x, u1_y, unit=1)
    # Unit 1 pins: C8,B10,C10,T12,U11,T11,G7,G8,H7,H8,R13,P13,N13,M13,L13,C3,E3
    symbol_pins(["C8","B10","C10","T12","U11","T11","G7","G8","H7","H8",
                 "R13","P13","N13","M13","L13","C3","E3"])

    # PS_CLK oscillator circuit
    text_note("PS_CLK 33.333 MHz", 30, 35, 1.27)
    osc_x, osc_y = 40, 50
    symbol_instance("cirradio:DSC1001CI2-33.333", "Y1", "33.333MHz", osc_x, osc_y,
                    footprint="Package_SO:VDFN-4-1EP_2.5x2.0mm_P0.65mm")
    symbol_pins(["1","2","3","4"])

    # Oscillator VDD to +3V3
    power_symbol("+3V3", osc_x, osc_y - 10)
    wire(osc_x, osc_y - 7.62, osc_x, osc_y - 10)

    # Oscillator GND
    power_symbol("GND", osc_x, osc_y + 10)
    wire(osc_x, osc_y + 7.62, osc_x, osc_y + 10)

    # Oscillator decoupling cap
    cap("100n", osc_x + 10, osc_y - 4, "Capacitor_SMD:C_0402_1005Metric")
    wire(osc_x + 10, osc_y - 7.81, osc_x + 10, osc_y - 10)
    power_symbol("+3V3", osc_x + 10, osc_y - 10)
    wire(osc_x + 10, osc_y - 0.19, osc_x + 10, osc_y + 2)
    power_symbol("GND", osc_x + 10, osc_y + 2)

    # EN tied high
    wire(osc_x - 7.62, osc_y + 2.54, osc_x - 7.62, osc_y - 7.62)
    wire(osc_x - 7.62, osc_y - 7.62, osc_x, osc_y - 7.62)

    # Series 22R from oscillator OUT to PS_CLK
    resistor("22R", 55, osc_y + 2.54, angle=90)
    wire(osc_x + 7.62, osc_y + 2.54, 55 - 3.81, osc_y + 2.54)
    wire(55 + 3.81, osc_y + 2.54, u1_x - 15.24, u1_y - 2.06)
    # Connect to PS_CLK pin (at u1_x-15.24, u1_y+27.94-u1_y = 27.94 relative)
    wire(55 + 3.81, osc_y + 2.54, 62, osc_y + 2.54)
    wire(62, osc_y + 2.54, 62, u1_y - 2.06)
    wire(62, u1_y - 2.06, u1_x - 15.24, u1_y - 2.06)

    # PS_POR_B from power sheet
    global_label("PS_POR_B", u1_x - 25, u1_y - 4.6, "input")
    wire(u1_x - 25, u1_y - 4.6, u1_x - 15.24, u1_y - 4.6)

    # PS_SRST_B with pushbutton + pullup + debounce cap
    text_note("PS_SRST_B reset", 30, 90, 1.27)
    sw_x = 42
    sw_y = u1_y - 7.14  # align with PS_SRST_B pin

    symbol_instance("Switch:SW_Push", "SW2", "RESET", sw_x, sw_y,
                    footprint="Button_Switch_SMD:SW_SPST_B3U-1000P")
    symbol_pins(["1","2"])

    # Button to GND
    power_symbol("GND", sw_x - 8, sw_y)
    wire(sw_x - 5.08, sw_y, sw_x - 8, sw_y)

    # Button output to SRST pin with pullup
    wire(sw_x + 5.08, sw_y, sw_x + 10, sw_y)
    resistor("10K", sw_x + 10, sw_y - 7, angle=0)  # pullup
    power_symbol("+1V8", sw_x + 10, sw_y - 14)
    wire(sw_x + 10, sw_y - 10.81, sw_x + 10, sw_y - 14)
    wire(sw_x + 10, sw_y - 3.19, sw_x + 10, sw_y)

    # Debounce cap
    cap("100n", sw_x + 16, sw_y + 4, "Capacitor_SMD:C_0402_1005Metric")
    wire(sw_x + 16, sw_y + 0.19, sw_x + 16, sw_y)
    wire(sw_x + 10, sw_y, sw_x + 16, sw_y)
    wire(sw_x + 16, sw_y + 7.81, sw_x + 16, sw_y + 10)
    power_symbol("GND", sw_x + 16, sw_y + 10)

    wire(sw_x + 16, sw_y, u1_x - 15.24, sw_y)

    # Boot mode DIP switch
    text_note("BOOT MODE (JTAG=00, QSPI=01)", 30, 100, 1.27)
    dip_x, dip_y = 42, 112

    symbol_instance("Switch:SW_DIP_x02", "SW1", "BOOT_MODE", dip_x, dip_y,
                    footprint="Button_Switch_SMD:SW_DIP_SPSTx02_Slide_6.7x6.64mm_W8.61mm_P2.54mm")
    symbol_pins(["1","2","3","4"])

    # DIP switch common pins (3,4) to VCCO (+1V8)
    power_symbol("+1V8", dip_x + 12, dip_y)
    wire(dip_x + 6.35, dip_y + 2.54, dip_x + 12, dip_y + 2.54)
    wire(dip_x + 12, dip_y + 2.54, dip_x + 12, dip_y)
    wire(dip_x + 6.35, dip_y, dip_x + 12, dip_y)

    # Pull-down resistors on boot mode pins
    resistor("10K", dip_x - 12, dip_y + 2.54 + 5, angle=0)
    wire(dip_x - 6.35, dip_y + 2.54, dip_x - 12, dip_y + 2.54)
    wire(dip_x - 12, dip_y + 2.54, dip_x - 12, dip_y + 2.54 + 1.27)
    power_symbol("GND", dip_x - 12, dip_y + 2.54 + 10)
    wire(dip_x - 12, dip_y + 2.54 + 8.81, dip_x - 12, dip_y + 2.54 + 10)

    resistor("10K", dip_x - 18, dip_y + 5, angle=0)
    wire(dip_x - 6.35, dip_y, dip_x - 18, dip_y)
    wire(dip_x - 18, dip_y, dip_x - 18, dip_y + 1.19)
    power_symbol("GND", dip_x - 18, dip_y + 10)
    wire(dip_x - 18, dip_y + 8.81, dip_x - 18, dip_y + 10)

    # Boot mode to Zynq - BOOT_MODE0/1 connect, MODE2/3 tied low
    wire(dip_x - 12, dip_y + 2.54, u1_x - 15.24, u1_y - 12.22)  # BOOT_MODE0
    wire(dip_x - 18, dip_y, dip_x - 18, u1_y - 14.76)
    wire(dip_x - 18, u1_y - 14.76, u1_x - 15.24, u1_y - 14.76)  # BOOT_MODE1

    # BOOT_MODE2 and MODE3 tied to GND
    resistor("10K", u1_x - 25, u1_y - 17.3, angle=0)
    wire(u1_x - 25, u1_y - 17.3 + 3.81, u1_x - 25, u1_y - 17.3 + 6)
    power_symbol("GND", u1_x - 25, u1_y - 17.3 + 6)
    wire(u1_x - 25, u1_y - 17.3 - 3.81, u1_x - 25, u1_y - 17.3 - 5)
    wire(u1_x - 25, u1_y - 17.3 - 5, u1_x - 15.24, u1_y - 17.3)

    resistor("10K", u1_x - 25, u1_y - 19.84, angle=0)
    wire(u1_x - 25, u1_y - 19.84 + 3.81, u1_x - 25, u1_y - 19.84 + 6)
    power_symbol("GND", u1_x - 25, u1_y - 19.84 + 6)
    wire(u1_x - 25, u1_y - 19.84 - 3.81, u1_x - 25, u1_y - 19.84 - 5)
    wire(u1_x - 25, u1_y - 19.84 - 5, u1_x - 15.24, u1_y - 19.84)

    # INIT_B: 4.7K pull-up to VCCO
    resistor("4K7", u1_x + 25, u1_y - 2.06, angle=90)
    wire(u1_x + 15.24, u1_y - 2.06, u1_x + 25 - 3.81, u1_y - 2.06)
    power_symbol("+1V8", u1_x + 25, u1_y - 2.06 - 8)
    wire(u1_x + 25 + 3.81, u1_y - 2.06, u1_x + 30, u1_y - 2.06)
    wire(u1_x + 30, u1_y - 2.06, u1_x + 30, u1_y - 2.06 - 8)
    wire(u1_x + 30, u1_y - 2.06 - 8, u1_x + 25, u1_y - 2.06 - 8)

    # DONE: LED (green) via 330R + 4.7K pull-up
    text_note("DONE LED", u1_x + 20, u1_y - 4.6 - 3, 1.0)
    resistor("330R", u1_x + 25, u1_y - 4.6, angle=90)
    wire(u1_x + 15.24, u1_y - 4.6, u1_x + 25 - 3.81, u1_y - 4.6)

    counts["symbols"] += 1  # LED
    emit(f'    (symbol (lib_id "Device:LED") (at {u1_x + 35} {u1_y - 4.6} 0)')
    emit(f'      (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)')
    emit(f'      (uuid "{uid()}")')
    emit(f'      (property "Reference" "D3" (at {u1_x + 35} {u1_y - 7} 0) (effects (font (size 1.27 1.27))))')
    emit(f'      (property "Value" "GREEN" (at {u1_x + 35} {u1_y - 2} 0) (effects (font (size 1.27 1.27))))')
    emit(f'      (property "Footprint" "LED_SMD:LED_0603_1608Metric" (at {u1_x + 35} {u1_y - 4.6} 0) (effects (font (size 1.27 1.27)) hide))')
    emit(f'      (property "Datasheet" "" (at {u1_x + 35} {u1_y - 4.6} 0) (effects (font (size 1.27 1.27)) hide))')
    emit(f'      (pin "1" (uuid "{uid()}"))')
    emit(f'      (pin "2" (uuid "{uid()}"))')
    emit(f'    )')

    wire(u1_x + 25 + 3.81, u1_y - 4.6, u1_x + 35 - 3.81, u1_y - 4.6)
    wire(u1_x + 35 + 3.81, u1_y - 4.6, u1_x + 42, u1_y - 4.6)
    power_symbol("GND", u1_x + 42, u1_y - 4.6)

    # DONE pull-up
    resistor("4K7", u1_x + 22, u1_y - 4.6 - 6, angle=0)
    wire(u1_x + 22, u1_y - 4.6 - 6 - 3.81, u1_x + 22, u1_y - 4.6 - 12)
    power_symbol("+1V8", u1_x + 22, u1_y - 4.6 - 12)
    wire(u1_x + 22, u1_y - 4.6 - 6 + 3.81, u1_x + 22, u1_y - 4.6)

    # PROG_B: 4.7K pull-up
    resistor("4K7", u1_x + 25, u1_y - 7.14, angle=90)
    wire(u1_x + 15.24, u1_y - 7.14, u1_x + 25 - 3.81, u1_y - 7.14)
    wire(u1_x + 25 + 3.81, u1_y - 7.14, u1_x + 30, u1_y - 7.14)
    wire(u1_x + 30, u1_y - 7.14, u1_x + 30, u1_y - 15)
    power_symbol("+1V8", u1_x + 30, u1_y - 15)

    # VREF pins - connect via resistor divider to VCCO
    # PS_MIO_VREF_500 and _501 need VREF = VCCO/2 = 0.9V
    # Simplified: connect to VCCO via 10K/10K divider (or just label)
    global_label("+1V8", u1_x + 22, u1_y - 12.22, "passive")
    wire(u1_x + 15.24, u1_y - 12.22, u1_x + 22, u1_y - 12.22)
    # VREF_501
    wire(u1_x + 15.24, u1_y - 14.76, u1_x + 22, u1_y - 14.76)
    global_label("+1V8", u1_x + 22, u1_y - 14.76, "passive")

    # ================================================================
    # SECTION 2: JTAG Header
    # ================================================================
    text_note("JTAG (ARM 2x7 1.27mm)", 130, 35, 1.27)
    jtag_x, jtag_y = 155, 60

    symbol_instance("Connector_Generic:Conn_02x07_Odd_Even", "J2", "JTAG",
                    jtag_x, jtag_y,
                    footprint="Connector_PinHeader_1.27mm:PinHeader_2x07_P1.27mm_Vertical")
    symbol_pins(["1","2","3","4","5","6","7","8","9","10","11","12","13","14"])

    # ARM JTAG pinout:
    # Pin 1 = VTref(+3V3), Pin 2 = TMS, Pin 3 = GND, Pin 4 = TCK
    # Pin 5 = GND, Pin 6 = TDO, Pin 7 = KEY(NC), Pin 8 = TDI
    # Pin 9 = GND, Pin 10 = nRESET, Pin 11 = GND, Pin 12 = NC
    # Pin 13 = GND, Pin 14 = NC

    # Pin 1 (VTref) to +3V3
    power_symbol("+3V3", jtag_x - 12, jtag_y - 12)
    wire(jtag_x - 3.81, jtag_y + 7.62, jtag_x - 12, jtag_y + 7.62)
    wire(jtag_x - 12, jtag_y + 7.62, jtag_x - 12, jtag_y - 12)

    # GND pins (3,5,9,11,13)
    power_symbol("GND", jtag_x - 10, jtag_y + 14)
    wire(jtag_x - 3.81, jtag_y + 5.08, jtag_x - 10, jtag_y + 5.08)
    wire(jtag_x - 10, jtag_y + 5.08, jtag_x - 10, jtag_y + 14)
    wire(jtag_x - 3.81, jtag_y + 2.54, jtag_x - 10, jtag_y + 2.54)
    wire(jtag_x - 10, jtag_y + 2.54, jtag_x - 10, jtag_y + 5.08)
    wire(jtag_x - 3.81, jtag_y - 2.54, jtag_x - 10, jtag_y - 2.54)
    wire(jtag_x - 10, jtag_y - 2.54, jtag_x - 10, jtag_y + 2.54)
    wire(jtag_x - 3.81, jtag_y - 5.08, jtag_x - 10, jtag_y - 5.08)
    wire(jtag_x - 10, jtag_y - 5.08, jtag_x - 10, jtag_y - 2.54)
    wire(jtag_x - 3.81, jtag_y - 7.62, jtag_x - 10, jtag_y - 7.62)
    wire(jtag_x - 10, jtag_y - 7.62, jtag_x - 10, jtag_y - 5.08)

    # Pin 2 = TMS (series 33R)
    resistor("33R", jtag_x + 15, jtag_y + 7.62, angle=90)
    wire(jtag_x + 6.35, jtag_y + 7.62, jtag_x + 15 - 3.81, jtag_y + 7.62)
    wire(jtag_x + 15 + 3.81, jtag_y + 7.62, jtag_x + 22, jtag_y + 7.62)
    wire(jtag_x + 22, jtag_y + 7.62, jtag_x + 22, u1_y)
    wire(jtag_x + 22, u1_y, u1_x - 15.24, u1_y)  # TMS pin

    # Pin 4 = TCK (series 33R)
    resistor("33R", jtag_x + 15, jtag_y + 5.08, angle=90)
    wire(jtag_x + 6.35, jtag_y + 5.08, jtag_x + 15 - 3.81, jtag_y + 5.08)
    wire(jtag_x + 15 + 3.81, jtag_y + 5.08, jtag_x + 24, jtag_y + 5.08)
    wire(jtag_x + 24, jtag_y + 5.08, jtag_x + 24, u1_y - 2.54)
    wire(jtag_x + 24, u1_y - 2.54, u1_x - 15.24, u1_y - 2.54)  # TCK pin

    # Pin 6 = TDO (no series R needed, it's an output)
    wire(jtag_x + 6.35, jtag_y + 2.54, jtag_x + 26, jtag_y + 2.54)
    wire(jtag_x + 26, jtag_y + 2.54, jtag_x + 26, u1_y + 2.54)
    wire(jtag_x + 26, u1_y + 2.54, u1_x - 15.24, u1_y + 2.54)  # TDO pin

    # Pin 8 = TDI (series 33R)
    resistor("33R", jtag_x + 15, jtag_y, angle=90)
    wire(jtag_x + 6.35, jtag_y, jtag_x + 15 - 3.81, jtag_y)
    wire(jtag_x + 15 + 3.81, jtag_y, jtag_x + 28, jtag_y)
    wire(jtag_x + 28, jtag_y, jtag_x + 28, u1_y + 5.08)
    wire(jtag_x + 28, u1_y + 5.08, u1_x - 15.24, u1_y + 5.08)  # TDI pin

    # Pin 10 = nRESET (TRST) to Zynq TRST
    wire(jtag_x + 6.35, jtag_y - 2.54, jtag_x + 30, jtag_y - 2.54)
    wire(jtag_x + 30, jtag_y - 2.54, jtag_x + 30, u1_y - 5.08)
    wire(jtag_x + 30, u1_y - 5.08, u1_x - 15.24, u1_y - 5.08)  # TRST pin

    # ================================================================
    # SECTION 3: Zynq Unit 2 - PS MIO with hierarchical labels
    # ================================================================
    text_note("PS MIO (Unit 2)", 30, 150, 2.0)
    text_note("MIO pin assignments to peripheral sheets", 30, 155, 1.27)

    u2_x, u2_y = 80, 230
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u2_x, u2_y, unit=2)
    mio_pin_nums = ["A4","B4","A5","B5","A6","B6","A7","E5","D5","E6",
                    "B7","D6","C7","E7","D7","B8","A9","B9","E8","D8",
                    "C9","E9","D9","A10","E10","D10","C11","B11","A11","E11",
                    "D11","A12","B12","C12","D12","E12","A13","B13","C13","D13",
                    "E13","F7","F8","F9","F10","F11","F12","F13","G6","G9",
                    "G10","G11","G12","G13"]
    symbol_pins(mio_pin_nums)

    # Hierarchical labels for MIO assignments
    hl_x = u2_x + 18
    # QSPI: MIO[1:6]
    text_note("QSPI", hl_x + 5, u2_y - 72.39 + 68.58 - 3, 1.0)
    for i in range(1, 7):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"QSPI_MIO{i}", hl_x, y, "bidirectional")

    # GEM0 Ethernet RGMII: MIO[16:27]
    text_note("GEM0 RGMII", hl_x + 5, u2_y - 72.39 + 71.12 - 16*2.54 - 3, 1.0)
    for i in range(16, 28):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"ETH_MIO{i}", hl_x, y, "bidirectional")

    # USB0 ULPI: MIO[28:39]
    text_note("USB0 ULPI", hl_x + 5, u2_y - 72.39 + 71.12 - 28*2.54 - 3, 1.0)
    for i in range(28, 40):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"USB_MIO{i}", hl_x, y, "bidirectional")

    # SD0: MIO[40:45]
    text_note("SD0", hl_x + 5, u2_y - 72.39 + 71.12 - 40*2.54 - 3, 1.0)
    for i in range(40, 46):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"SD_MIO{i}", hl_x, y, "bidirectional")

    # UART0: MIO[46:47]
    text_note("UART0", hl_x + 5, u2_y - 72.39 + 71.12 - 46*2.54 - 3, 1.0)
    for i in range(46, 48):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"UART0_MIO{i}", hl_x, y, "bidirectional")

    # UART1 console: MIO[48:49]
    text_note("UART1", hl_x + 5, u2_y - 72.39 + 71.12 - 48*2.54 - 3, 1.0)
    for i in range(48, 50):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"UART1_MIO{i}", hl_x, y, "bidirectional")

    # I2C0: MIO[50:51]
    text_note("I2C0", hl_x + 5, u2_y - 72.39 + 71.12 - 50*2.54 - 3, 1.0)
    for i in range(50, 52):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"I2C_MIO{i}", hl_x, y, "bidirectional")

    # MIO0 - boot mode strapping, leave as no-connect label
    y0 = u2_y - 72.39 + 71.12
    wire(u2_x + 10.16, y0, hl_x, y0)
    text_note("BOOT_CS", hl_x + 2, y0, 1.0)

    # Unused MIO: 7-15, 52-53
    for i in list(range(7, 16)) + list(range(52, 54)):
        y = u2_y - 72.39 + 71.12 - i * 2.54
        wire(u2_x + 10.16, y, hl_x, y)
        hier_label(f"MIO{i}", hl_x, y, "bidirectional")

    # ================================================================
    # SECTION 4: Zynq Unit 3 - PS DDR with hierarchical labels
    # ================================================================
    text_note("PS DDR INTERFACE (Unit 3)", 180, 150, 2.0)
    text_note("DDR3L signals to memory sheet", 180, 155, 1.27)

    u3_x, u3_y = 230, 220
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u3_x, u3_y, unit=3)
    # DDR unit 3 pin numbers
    ddr_dq_pins = ["H1","H2","H3","J1","J2","J3","K1","K2","K3","L1","L2","L3","M1","M2","M3","N1",
                   "N2","N3","P1","P2","P3","R1","R2","R3","T1","T2","T3","U1","U2","U3","V1","V2"]
    ddr_unit_pins = ddr_dq_pins + ["H4","H5","J4","J5","K4","K5","L4","L5",
                               "M4","M5","N4","N5"] + \
                    ["P4","P5","R4","R5","T4","T5","U4","U5","V3","V4","V5","W3","W4","W5","Y3"] + \
                    ["Y4","Y5","AA3","AA4","AA5","AB3","AB4","AB5","AC3","AC4","AC5",
                     "AD3","AD4","AD5","AE3","AE4"]
    symbol_pins(ddr_unit_pins)

    # DDR DQ hierarchical labels (right side)
    ddr_hl_x = u3_x + 22
    for i in range(32):
        y = u3_y - 53.34 + 50.8 + 2.54 - i * 2.54
        wire(u3_x + 15.24, y, ddr_hl_x, y)
        hier_label(f"DDR_DQ{i}", ddr_hl_x, y, "bidirectional")

    # DDR left-side signals: DQS, DM, Address, Bank, Control
    ddr_left_x = u3_x - 22
    # DQS
    for i in range(4):
        for suffix, offset in [("P", 0), ("N", 1)]:
            y = u3_y - 53.34 + 50.8 - (i*2 + offset) * 2.54
            wire(u3_x - 15.24, y, ddr_left_x, y)
            hier_label(f"DDR_DQS_{suffix}{i}", ddr_left_x, y, "bidirectional", 180)

    # DM
    for i in range(4):
        y = u3_y - 53.34 + 27.94 - i * 2.54
        wire(u3_x - 15.24, y, ddr_left_x, y)
        hier_label(f"DDR_DM{i}", ddr_left_x, y, "output", 180)

    # Address
    for i in range(15):
        y = u3_y - 53.34 + 15.24 - i * 2.54
        wire(u3_x - 15.24, y, ddr_left_x, y)
        hier_label(f"DDR_A{i}", ddr_left_x, y, "output", 180)

    # Bank address
    for i, name in enumerate(["DDR_BA0","DDR_BA1","DDR_BA2"]):
        y = u3_y - 53.34 - 25.4 - i * 2.54
        wire(u3_x - 15.24, y, ddr_left_x, y)
        hier_label(name, ddr_left_x, y, "output", 180)

    # Control signals
    ctrl_names = ["DDR_CAS_B","DDR_RAS_B","DDR_WE_B","DDR_CK_P","DDR_CK_N",
                  "DDR_CKE","DDR_CS_B","DDR_ODT"]
    for i, name in enumerate(ctrl_names):
        y = u3_y - 53.34 - 33.02 - i * 2.54
        wire(u3_x - 15.24, y, ddr_left_x, y)
        hier_label(name, ddr_left_x, y, "output", 180)

    # Right-side misc DDR signals
    hier_label("DDR_RESET_B", ddr_hl_x, u3_y - 53.34 - 33.02, "output")
    wire(u3_x + 15.24, u3_y - 53.34 - 33.02, ddr_hl_x, u3_y - 53.34 - 33.02)

    # VREF pins connect to VTTREF
    global_label("VTTREF", ddr_hl_x, u3_y - 53.34 - 38.1, "passive")
    wire(u3_x + 15.24, u3_y - 53.34 - 38.1, ddr_hl_x, u3_y - 53.34 - 38.1)
    global_label("VTTREF", ddr_hl_x, u3_y - 53.34 - 40.64, "passive")
    wire(u3_x + 15.24, u3_y - 53.34 - 40.64, ddr_hl_x, u3_y - 53.34 - 40.64)

    # VRN/VRP - need 240R to GND/VDDQ
    resistor("240R", ddr_hl_x + 8, u3_y - 53.34 - 45.72, angle=90)
    wire(u3_x + 15.24, u3_y - 53.34 - 45.72, ddr_hl_x + 8 - 3.81, u3_y - 53.34 - 45.72)
    power_symbol("GND", ddr_hl_x + 15, u3_y - 53.34 - 45.72)
    wire(ddr_hl_x + 8 + 3.81, u3_y - 53.34 - 45.72, ddr_hl_x + 15, u3_y - 53.34 - 45.72)

    resistor("240R", ddr_hl_x + 8, u3_y - 53.34 - 48.26, angle=90)
    wire(u3_x + 15.24, u3_y - 53.34 - 48.26, ddr_hl_x + 8 - 3.81, u3_y - 53.34 - 48.26)
    global_label("+1V35", ddr_hl_x + 15, u3_y - 53.34 - 48.26, "passive")
    wire(ddr_hl_x + 8 + 3.81, u3_y - 53.34 - 48.26, ddr_hl_x + 15, u3_y - 53.34 - 48.26)

    # ================================================================
    # SECTION 5: PL Bank Units with hierarchical labels
    # ================================================================

    # Unit 4: Bank 33 HP - AD9361 LVDS
    text_note("PL BANK 33 HP - AD9361 LVDS (Unit 4)", 30, 340, 2.0)
    u4_x, u4_y = 65, 420
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u4_x, u4_y, unit=4)
    b33_pins = ["AA14","AA15","AB14","AB15","AC14","AC15","AD14","AD15",
                "AE14","AE15","AF14","AF15","AA16","AA17","AB16","AB17",
                "AC16","AC17","AD16","AD17","AE16","AE17","AF16","AF17",
                "AA18","AA19","AB18","AB19","AC18","AC19","AD18","AD19",
                "AE18","AE19","AF18","AF19","AA20","AA21","AB20","AB21",
                "AC20","AC21","AD20","AD21","AE20","AE21","AF20","AF21",
                "AA22","AA23"]
    symbol_pins(b33_pins)

    b33_hl_x = u4_x + 18
    for i in range(50):
        y = u4_y - 66.04 + 63.5 + 2.54 - i * 2.54
        if i == 49:
            y = u4_y - 66.04 - 63.5 + 2.54
        wire(u4_x + 10.16, y, b33_hl_x, y)
        pair_idx = i // 2
        suffix = "P" if i % 2 == 0 else "N"
        if i < 48:
            hier_label(f"AD9361_B33_L{pair_idx}{suffix}", b33_hl_x, y, "bidirectional")
        else:
            hier_label(f"AD9361_B33_L24{'P' if i==48 else 'N'}", b33_hl_x, y, "bidirectional")

    # Unit 5: Bank 34 HP - AD9361 overflow/ctrl
    text_note("PL BANK 34 HP - AD9361 DATA/CTRL (Unit 5)", 170, 340, 2.0)
    u5_x, u5_y = 205, 420
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u5_x, u5_y, unit=5)
    b34_pins = ["AA24","AA25","AB24","AB25","AC24","AC25","AD24","AD25",
                "AE24","AE25","AF24","AF25","AA26","AA27","AB26","AB27",
                "AC26","AC27","AD26","AD27","AE26","AE27","AF26","AF27",
                "AA28","AA29","AB28","AB29","AC28","AC29","AD28","AD29",
                "AE28","AE29","AF28","AF29","AA30","AB30","AC30","AD30",
                "AE30","AF30","Y14","Y15","Y16","Y17","Y18","Y19",
                "Y20","Y21"]
    symbol_pins(b34_pins)

    b34_hl_x = u5_x + 18
    for i in range(50):
        y = u5_y - 66.04 + 63.5 + 2.54 - i * 2.54
        if i == 49:
            y = u5_y - 66.04 - 63.5 + 2.54
        wire(u5_x + 10.16, y, b34_hl_x, y)
        pair_idx = i // 2
        suffix = "P" if i % 2 == 0 else "N"
        if i < 48:
            hier_label(f"AD9361_B34_L{pair_idx}{suffix}", b34_hl_x, y, "bidirectional")
        else:
            hier_label(f"AD9361_B34_L24{'P' if i==48 else 'N'}", b34_hl_x, y, "bidirectional")

    # Unit 6: Bank 13 HR - AD9361 SPI, control
    text_note("PL BANK 13 HR - AD9361 SPI/CTRL (Unit 6)", 30, 510, 2.0)
    u6_x, u6_y = 65, 590
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u6_x, u6_y, unit=6)
    b13_pins = ["A14","B14","C14","D14","E14","F14","A15","B15",
                "C15","D15","E15","F15","A16","B16","C16","D16",
                "E16","F16","A17","B17","C17","D17","E17","F17",
                "A18","B18","C18","D18","E18","F18","A19","B19",
                "C19","D19","E19","F19","A20","B20","C20","D20",
                "E20","F20","A21","B21","C21","D21","E21","F21",
                "A22","B22"]
    symbol_pins(b13_pins)

    b13_hl_x = u6_x + 18
    for i in range(50):
        y = u6_y - 66.04 + 63.5 + 2.54 - i * 2.54
        if i == 49:
            y = u6_y - 66.04 - 63.5 + 2.54
        wire(u6_x + 10.16, y, b13_hl_x, y)
        hier_label(f"AD9361_B13_IO{i}", b13_hl_x, y, "bidirectional")

    # Unit 7: Bank 12 HR - GPIO, LEDs, buttons
    text_note("PL BANK 12 HR - GPIO/LEDS/1PPS (Unit 7)", 170, 510, 2.0)
    u7_x, u7_y = 205, 590
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u7_x, u7_y, unit=7)
    b12_pins = ["A23","B23","C23","D23","E23","F23","A24","B24",
                "C24","D24","E24","F24","A25","B25","C25","D25",
                "E25","F25","A26","B26","C26","D26","E26","F26",
                "A27","B27","C27","D27","E27","F27","A28","B28",
                "C28","D28","E28","F28","A29","B29","C29","D29",
                "E29","F29","A30","B30","C30","D30","G14","G15",
                "G16","G17"]
    symbol_pins(b12_pins)

    b12_hl_x = u7_x + 18
    for i in range(50):
        y = u7_y - 66.04 + 63.5 + 2.54 - i * 2.54
        if i == 49:
            y = u7_y - 66.04 - 63.5 + 2.54
        wire(u7_x + 10.16, y, b12_hl_x, y)
        hier_label(f"GPIO_B12_IO{i}", b12_hl_x, y, "bidirectional")

    # Unit 8: Spare (just place, no labels needed for now)
    text_note("PL SPARE (Unit 8)", 30, 680, 2.0)
    u8_x, u8_y = 65, 760
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u8_x, u8_y, unit=8)
    spare_pins = ["H14","H15","H16","H17","J14","J15","J16","J17",
                  "K14","K15","K16","K17","L14","L15","L16","L17",
                  "M14","M15","M16","M17","N14","N15","N16","N17",
                  "P14","P15","P16","P17","R14","R15","R16","R17",
                  "T14","T15","T16","T17","U14","U15","U16","U17",
                  "V14","V15","V16","V17","W14","W15","W16","W17",
                  "Y6","Y7"]
    symbol_pins(spare_pins)

    # ================================================================
    # SECTION 6: Zynq Unit 9 - Power with decoupling
    # ================================================================
    text_note("ZYNQ POWER (Unit 9) + DECOUPLING", 30, 860, 2.0)

    u9_x, u9_y = 80, 920
    symbol_instance("cirradio:XC7Z045", "U1", "XC7Z045-2FFG900I", u9_x, u9_y, unit=9)
    # Power unit pin numbers
    pwr_unit_pins = (
        ["G18","G19","G20","G21","G22","G23","G24","G25","G26","G27",
         "H18","H19","H20","H21","H22"] +  # VCCINT
        ["H23","H24","H25","H26"] +  # VCCAUX
        ["H27","H28"] +  # VCCBRAM
        ["J18","J19"] +  # VCCO_33
        ["J20","J21"] +  # VCCO_34
        ["J22","J23"] +  # VCCO_13
        ["J24","J25"] +  # VCCO_12
        ["J26","J27","J28","K18"] +  # VCCPINT
        ["K19","K20"] +  # VCCPAUX
        ["K21","K22"] +  # VCCPLL
        ["K23","K24","K25","K26","K27","K28","L18","L19","L20","L21","L22","L23",
         "L24","L25","L26","L27","L28","M18","M19","M20","M21","M22","M23","M24",
         "M25","M26","M27","M28","N18","N19","N20"]  # GND
    )
    symbol_pins(pwr_unit_pins)

    # Connect power pins to global labels
    # VCCINT
    global_label("+1V0", u9_x - 22, u9_y - 55.88 + 53.34, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 53.34, u9_x - 22, u9_y - 55.88 + 53.34)
    # VCCAUX
    global_label("+1V5", u9_x - 22, u9_y - 55.88 + 48.26, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 48.26, u9_x - 22, u9_y - 55.88 + 48.26)
    # VCCBRAM
    global_label("+1V0", u9_x - 22, u9_y - 55.88 + 43.18, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 43.18, u9_x - 22, u9_y - 55.88 + 43.18)
    # VCCO_33
    global_label("+1V8", u9_x - 22, u9_y - 55.88 + 38.1, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 38.1, u9_x - 22, u9_y - 55.88 + 38.1)
    # VCCO_34
    global_label("+1V8", u9_x - 22, u9_y - 55.88 + 35.56, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 35.56, u9_x - 22, u9_y - 55.88 + 35.56)
    # VCCO_13
    global_label("+3V3", u9_x - 22, u9_y - 55.88 + 33.02, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 33.02, u9_x - 22, u9_y - 55.88 + 33.02)
    # VCCO_12
    global_label("+3V3", u9_x - 22, u9_y - 55.88 + 30.48, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 30.48, u9_x - 22, u9_y - 55.88 + 30.48)
    # VCCPINT
    global_label("+1V0", u9_x - 22, u9_y - 55.88 + 25.4, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 25.4, u9_x - 22, u9_y - 55.88 + 25.4)
    # VCCPAUX
    global_label("+1V8", u9_x - 22, u9_y - 55.88 + 20.32, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 20.32, u9_x - 22, u9_y - 55.88 + 20.32)
    # VCCPLL
    global_label("+1V8", u9_x - 22, u9_y - 55.88 + 15.24, "passive", 180)
    wire(u9_x - 15.24, u9_y - 55.88 + 15.24, u9_x - 22, u9_y - 55.88 + 15.24)
    # GND
    power_symbol("GND", u9_x + 22, u9_y - 55.88 + 53.34)
    wire(u9_x + 15.24, u9_y - 55.88 + 53.34, u9_x + 22, u9_y - 55.88 + 53.34)

    # ================================================================
    # SECTION 7: Decoupling capacitors
    # ================================================================
    text_note("DECOUPLING CAPACITORS (per Xilinx UG483)", 30, 1000, 2.0)

    # VCCINT: 20x 100nF + 4x 10uF
    decoupling_group("+1V0", 30, 1020, 20, 4, "VCCINT")

    # VCCAUX: 8x 100nF + 2x 10uF
    decoupling_group("+1V5", 30, 1060, 8, 2, "VCCAUX")

    # VCCO_33: 4x 100nF + 1x 10uF
    decoupling_group("+1V8", 30, 1100, 4, 1, "VCCO Bank 33")

    # VCCO_34: 4x 100nF + 1x 10uF
    decoupling_group("+1V8", 30, 1140, 4, 1, "VCCO Bank 34")

    # VCCO_13: 4x 100nF + 1x 10uF
    decoupling_group("+3V3", 30, 1180, 4, 1, "VCCO Bank 13")

    # VCCO_12: 4x 100nF + 1x 10uF
    decoupling_group("+3V3", 30, 1220, 4, 1, "VCCO Bank 12")

    # VCCO_MIO (Bank 500/501): 4x 100nF + 1x 10uF each
    decoupling_group("+1V8", 170, 1100, 4, 1, "VCCO Bank 500")
    decoupling_group("+1V8", 170, 1140, 4, 1, "VCCO Bank 501")

    # VCCPINT: 8x 100nF + 2x 10uF
    decoupling_group("+1V0", 170, 1020, 8, 2, "VCCPINT")

    # VCCPAUX: 4x 100nF + 1x 10uF
    decoupling_group("+1V8", 170, 1060, 4, 1, "VCCPAUX")

    # VCCBRAM: 4x 100nF + 1x 10uF
    decoupling_group("+1V0", 30, 1260, 4, 1, "VCCBRAM")

    # VCCPLL: 4x 100nF + 1x 10uF (filtered)
    decoupling_group("+1V8", 170, 1180, 4, 1, "VCCPLL")

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
        # Try to find where the imbalance is
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

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/zynq.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"Component counts:")
    print(f"  Zynq units placed: 9 (all as U1)")
    print(f"  Oscillator: 1 (Y1)")
    print(f"  JTAG header: 1 (J2)")
    print(f"  DIP switch: 1 (SW1)")
    print(f"  Reset button: 1 (SW2)")
    print(f"  DONE LED: 1 (D3)")
    print(f"  Capacitors: {counts['capacitors']}")
    print(f"  Resistors: {counts['resistors']}")
    print(f"  Power symbols: {counts['symbols'] - 9 - 4}")  # subtract major ICs
    print(f"  Wires: {counts['wires']}")
    print(f"  Global labels: {counts['gl_labels']}")
    print(f"  Hierarchical labels: {counts['hier_labels']}")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")

if __name__ == "__main__":
    main()
