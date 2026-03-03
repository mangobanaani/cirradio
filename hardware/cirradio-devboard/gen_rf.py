#!/usr/bin/env python3
"""Generate RF front-end schematic sheet for CIRRADIO dev board."""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

# Reference designator counters (RF sheet: start at 300 to avoid conflicts)
cap_idx = [300]
ind_idx = [300]
res_idx = [300]
pwr_idx = [300]
u_idx = [10]  # ICs start at U10

def next_cap():
    c = cap_idx[0]; cap_idx[0] += 1; return f"C{c}"

def next_ind():
    i = ind_idx[0]; ind_idx[0] += 1; return f"L{i}"

def next_res():
    r = res_idx[0]; res_idx[0] += 1; return f"R{r}"

def next_pwr():
    p = pwr_idx[0]; pwr_idx[0] += 1; return f"#PWR{p:04d}"

def next_u():
    u = u_idx[0]; u_idx[0] += 1; return f"U{u}"

# Track component counts
counts = {"capacitors": 0, "inductors": 0, "resistors": 0, "symbols": 0,
           "wires": 0, "labels": 0, "gl_labels": 0, "hier_labels": 0}

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

def cap(value, x, y, angle=0, fp="Capacitor_SMD:C_0402_1005Metric"):
    """Place a capacitor."""
    counts["capacitors"] += 1
    ref = next_cap()
    symbol_instance("Device:C", ref, value, x, y, angle=angle, footprint=fp)
    symbol_pins(["1", "2"])

def inductor(value, x, y, angle=0, fp="Inductor_SMD:L_0402_1005Metric"):
    """Place an inductor."""
    counts["inductors"] += 1
    ref = next_ind()
    symbol_instance("Device:L", ref, value, x, y, angle=angle, footprint=fp)
    symbol_pins(["1", "2"])

def resistor(value, x, y, angle=0):
    counts["resistors"] += 1
    ref = next_res()
    symbol_instance("Device:R", ref, value, x, y, angle=angle)
    symbol_pins(["1", "2"])


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

    # Device:L
    emit('''    (symbol "Device:L"
      (pin_names (offset 0) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "L" (at 1.524 0 0) (effects (font (size 1.27 1.27)) (justify left)))
      (property "Value" "L" (at -1.524 0 0) (effects (font (size 1.27 1.27)) (justify right)))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "L_0_1"
        (arc (start 0 -2.54) (mid 0.635 -1.905) (end 0 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))
        (arc (start 0 -1.27) (mid 0.635 -0.635) (end 0 0) (stroke (width 0.254) (type default)) (fill (type none)))
        (arc (start 0 0) (mid 0.635 0.635) (end 0 1.27) (stroke (width 0.254) (type default)) (fill (type none)))
        (arc (start 0 1.27) (mid 0.635 1.905) (end 0 2.54) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "L_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Connector:Conn_Coaxial (SMA)
    emit('''    (symbol "Connector:Conn_Coaxial"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0.254 3.048 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_Coaxial" (at 2.286 -2.286 0) (effects (font (size 1.27 1.27)) (justify left)))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "Conn_Coaxial_0_1"
        (arc (start -1.778 -0.508) (mid 0.7584 -2.044) (end 1.778 0) (stroke (width 0.254) (type default)) (fill (type none)))
        (arc (start -1.778 0.508) (mid -0.7584 2.044) (end 1.778 0) (stroke (width 0.254) (type default)) (fill (type none)))
      )
      (symbol "Conn_Coaxial_1_1"
        (pin passive line (at -3.81 0 0) (length 2.54) (name "In" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 2.54) (name "Ext" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Device:C_Polarized (generic BPF representation)
    # We use a simple box symbol for generic "BPF" filter
    emit('''    (symbol "Device:BPF"
      (pin_names (offset 0.254)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "FL" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
      (property "Value" "BPF" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "BPF_0_1"
        (rectangle (start -5.08 2.54) (end 5.08 -2.54) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "BPF_1_1"
        (pin passive line (at -7.62 0 0) (length 2.54) (name "IN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 7.62 0 180) (length 2.54) (name "OUT" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -5.08 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # PE42525 T/R switch (from cirradio lib)
    emit('''    (symbol "cirradio:PE42525"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
      (property "Value" "PE42525" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "PE42525_0_1"
        (rectangle (start -7.62 8.89) (end 7.62 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "PE42525_1_1"
        (pin bidirectional line (at -10.16 5.08 0) (length 2.54) (name "RFC" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 10.16 2.54 180) (length 2.54) (name "RF2" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin bidirectional line (at 10.16 5.08 180) (length 2.54) (name "RF1" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
        (pin input line (at -10.16 0 0) (length 2.54) (name "V2" (effects (font (size 1.27 1.27)))) (number "15" (effects (font (size 1.27 1.27)))))
        (pin input line (at -10.16 2.54 0) (length 2.54) (name "V1" (effects (font (size 1.27 1.27)))) (number "16" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "17" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ADL5523ACPZ LNA (from cirradio lib)
    emit('''    (symbol "cirradio:ADL5523ACPZ"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 11.43 0) (effects (font (size 1.27 1.27))))
      (property "Value" "ADL5523ACPZ" (at 0 -11.43 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "ADL5523ACPZ_0_1"
        (rectangle (start -7.62 10.16) (end 7.62 -10.16) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "ADL5523ACPZ_1_1"
        (pin input line (at -10.16 7.62 0) (length 2.54) (name "RFIN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin output line (at 10.16 7.62 180) (length 2.54) (name "RFOUT" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 12.7 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 10.16 2.54 180) (length 2.54) (name "DECL" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 12.7 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "15" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -10.16 2.54 0) (length 2.54) (name "VPDC" (effects (font (size 1.27 1.27)))) (number "16" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -12.7 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "17" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # ADL5606ACPZ TX driver (from cirradio lib)
    emit('''    (symbol "cirradio:ADL5606ACPZ"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 15.24 0) (effects (font (size 1.27 1.27))))
      (property "Value" "ADL5606ACPZ" (at 0 -15.24 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "ADL5606ACPZ_0_1"
        (rectangle (start -7.62 13.97) (end 7.62 -13.97) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "ADL5606ACPZ_1_1"
        (pin input line (at -10.16 10.16 0) (length 2.54) (name "INP" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin input line (at -10.16 7.62 0) (length 2.54) (name "INM" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin output line (at 10.16 10.16 180) (length 2.54) (name "OUTP" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 16.51 270) (length 2.54) (name "VCC2" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin output line (at 10.16 7.62 180) (length 2.54) (name "OUTM" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "12" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "13" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 16.51 270) (length 2.54) (name "VCC3" (effects (font (size 1.27 1.27)))) (number "14" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "15" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "16" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "17" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "18" (effects (font (size 1.27 1.27)))))
        (pin input line (at -10.16 2.54 0) (length 2.54) (name "PWDN" (effects (font (size 1.27 1.27)))) (number "19" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 16.51 270) (length 2.54) (name "VCC1" (effects (font (size 1.27 1.27)))) (number "20" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "21" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "22" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "23" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "24" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -16.51 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "25" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # TGA2594-SM PA (from cirradio lib)
    emit('''    (symbol "cirradio:TGA2594-SM"
      (pin_names (offset 0.254))
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
      (property "Value" "TGA2594-SM" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "TGA2594-SM_0_1"
        (rectangle (start -7.62 8.89) (end 7.62 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))
      )
      (symbol "TGA2594-SM_1_1"
        (pin input line (at -10.16 5.08 0) (length 2.54) (name "RF_IN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 11.43 270) (length 2.54) (name "VDD1" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 11.43 270) (length 2.54) (name "VDD2" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
        (pin output line (at 10.16 5.08 180) (length 2.54) (name "RF_OUT" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 11.43 270) (length 2.54) (name "VDD3" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -11.43 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
        (pin no_connect line (at 10.16 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Power symbols
    for net, arrow_up in [("+3V3", True), ("+3V3A", True), ("+5V_PA", True), ("GND", False)]:
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
    emit('  (generator "cirradio_gen_rf")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board - RF Front-End")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "225-512 MHz UHF: SMA, BPF, T/R switch, LNA, SAW, TX driver, PA, harmonic LPF")')
    emit('    (comment 2 "PE42525 + ADL5523 + ADL5606 + TGA2594-SM")')
    emit('  )')
    emit('')

    # Library symbols
    emit_lib_symbols()
    emit('')

    # ================================================================
    # SECTION 1: ANTENNA / SMA CONNECTOR (far left)
    # ================================================================
    text_note("ANTENNA / SMA CONNECTOR", 30, 20, 2.0)
    text_note("50 ohm SMA edge-launch connector", 30, 24, 1.27)

    # SMA connector J1
    sma_x, sma_y = 40, 45
    symbol_instance("Connector:Conn_Coaxial", "J1", "SMA 50ohm", sma_x, sma_y,
                    footprint="Connector_Coaxial:SMA_Amphenol_132289_EdgeMount")
    symbol_pins(["1", "2"])
    # GND on shield
    wire(sma_x, sma_y + 3.81, sma_x, sma_y + 7)
    power_symbol("GND", sma_x, sma_y + 7)

    # Wire from SMA signal pin to BPF input area
    wire(sma_x + 3.81, sma_y, sma_x + 10, sma_y)

    # ================================================================
    # SECTION 2: INPUT BANDPASS FILTER (225-512 MHz, 3-section LC)
    # ================================================================
    text_note("INPUT BPF 225-512 MHz", 60, 20, 2.0)
    text_note("3-section LC: 47nH series, 22pF shunt, 0402 RF-grade", 60, 24, 1.27)

    bpf_x = 55  # start X of BPF network
    bpf_y = 45  # signal path Y

    # Section 1: L1 series -> C1 shunt
    wire(sma_x + 10, bpf_y, bpf_x, bpf_y)
    inductor("47n", bpf_x + 5, bpf_y, angle=90, fp="Inductor_SMD:L_0402_1005Metric")
    wire(bpf_x + 5 + 3.81, bpf_y, bpf_x + 15, bpf_y)
    # Shunt cap to GND
    wire(bpf_x + 15, bpf_y, bpf_x + 15, bpf_y + 3)
    cap("22p", bpf_x + 15, bpf_y + 7)
    wire(bpf_x + 15, bpf_y + 10.81, bpf_x + 15, bpf_y + 13)
    power_symbol("GND", bpf_x + 15, bpf_y + 13)

    # Section 2: L2 series -> C2 shunt
    wire(bpf_x + 15, bpf_y, bpf_x + 20, bpf_y)
    inductor("47n", bpf_x + 25, bpf_y, angle=90, fp="Inductor_SMD:L_0402_1005Metric")
    wire(bpf_x + 25 + 3.81, bpf_y, bpf_x + 35, bpf_y)
    wire(bpf_x + 35, bpf_y, bpf_x + 35, bpf_y + 3)
    cap("22p", bpf_x + 35, bpf_y + 7)
    wire(bpf_x + 35, bpf_y + 10.81, bpf_x + 35, bpf_y + 13)
    power_symbol("GND", bpf_x + 35, bpf_y + 13)

    # Section 3: L3 series -> C3 shunt
    wire(bpf_x + 35, bpf_y, bpf_x + 40, bpf_y)
    inductor("47n", bpf_x + 45, bpf_y, angle=90, fp="Inductor_SMD:L_0402_1005Metric")
    wire(bpf_x + 45 + 3.81, bpf_y, bpf_x + 55, bpf_y)
    wire(bpf_x + 55, bpf_y, bpf_x + 55, bpf_y + 3)
    cap("22p", bpf_x + 55, bpf_y + 7)
    wire(bpf_x + 55, bpf_y + 10.81, bpf_x + 55, bpf_y + 13)
    power_symbol("GND", bpf_x + 55, bpf_y + 13)

    # Wire from BPF output to T/R switch
    wire(bpf_x + 55, bpf_y, bpf_x + 65, bpf_y)

    # ================================================================
    # SECTION 3: T/R SWITCH PE42525
    # ================================================================
    text_note("T/R SWITCH PE42525", 130, 20, 2.0)
    text_note("RFC=antenna, RF1=RX, RF2=TX", 130, 24, 1.27)

    sw_x, sw_y = 135, 45
    sw_ref = next_u()
    symbol_instance("cirradio:PE42525", sw_ref, "PE42525", sw_x, sw_y,
                    footprint="Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm")
    symbol_pins([str(i) for i in range(1, 18)])

    # GND
    wire(sw_x, sw_y + 11.43, sw_x, sw_y + 15)
    power_symbol("GND", sw_x, sw_y + 15)

    # VDD = +3V3 via 100nF decoupling
    # Power label above
    global_label("+3V3", sw_x - 15, sw_y - 10, "passive")
    wire(sw_x - 15, sw_y - 10, sw_x - 15, sw_y - 5)
    cap("100n", sw_x - 15, sw_y - 1)
    wire(sw_x - 15, sw_y + 2.81, sw_x - 15, sw_y + 5)
    power_symbol("GND", sw_x - 15, sw_y + 5)

    # Wire from BPF to RFC (pin 1, left side at y+5.08)
    wire(bpf_x + 65, bpf_y, sw_x - 10.16, sw_y + 5.08)

    # Control: V1, V2 from Zynq PL
    hier_label("TR_V1", sw_x - 18, sw_y + 2.54, "input", 0)
    wire(sw_x - 18, sw_y + 2.54, sw_x - 10.16, sw_y + 2.54)
    hier_label("TR_V2", sw_x - 18, sw_y, "input", 0)
    wire(sw_x - 18, sw_y, sw_x - 10.16, sw_y)

    # RF1 (pin 12, right at y+5.08) = RX path
    rx_path_x = sw_x + 10.16
    wire(rx_path_x, sw_y + 5.08, rx_path_x + 10, sw_y + 5.08)

    # RF2 (pin 4, right at y+2.54) = TX path
    tx_path_x = sw_x + 10.16
    wire(tx_path_x, sw_y + 2.54, tx_path_x + 5, sw_y + 2.54)
    # Route TX path down to TX section
    wire(tx_path_x + 5, sw_y + 2.54, tx_path_x + 5, sw_y + 60)

    # ================================================================
    # SECTION 4: RX PATH - LNA ADL5523
    # ================================================================
    text_note("RX PATH - LNA ADL5523", 170, 20, 2.0)
    text_note("Low-noise amplifier, Gain ~20 dB, NF ~1.2 dB", 170, 24, 1.27)

    lna_x, lna_y = 185, 45
    lna_ref = next_u()
    symbol_instance("cirradio:ADL5523ACPZ", lna_ref, "ADL5523ACPZ", lna_x, lna_y,
                    footprint="Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.65mm_EP1.75x1.75mm")
    symbol_pins([str(i) for i in range(1, 18)])

    # GND
    wire(lna_x, lna_y + 12.7, lna_x, lna_y + 16)
    power_symbol("GND", lna_x, lna_y + 16)

    # VCC = +3V3A via 100nH bias inductor + 100nF + 10nF decoupling
    # VCC at pin 10/13 (top, y-12.7)
    vcc_lna_x = lna_x
    vcc_lna_y = lna_y - 12.7
    wire(vcc_lna_x, vcc_lna_y, vcc_lna_x, vcc_lna_y - 5)
    inductor("100n", vcc_lna_x, vcc_lna_y - 9, fp="Inductor_SMD:L_0402_1005Metric")
    wire(vcc_lna_x, vcc_lna_y - 12.81, vcc_lna_x, vcc_lna_y - 15)
    global_label("+3V3A", vcc_lna_x, vcc_lna_y - 15, "passive")

    # Decoupling 100nF near VCC
    wire(vcc_lna_x + 5, vcc_lna_y - 5, vcc_lna_x + 5, vcc_lna_y - 2)
    cap("100n", vcc_lna_x + 5, vcc_lna_y + 2)
    wire(vcc_lna_x + 5, vcc_lna_y + 5.81, vcc_lna_x + 5, vcc_lna_y + 8)
    power_symbol("GND", vcc_lna_x + 5, vcc_lna_y + 8)
    wire(vcc_lna_x, vcc_lna_y - 5, vcc_lna_x + 5, vcc_lna_y - 5)

    # Decoupling 10nF
    wire(vcc_lna_x + 10, vcc_lna_y - 5, vcc_lna_x + 10, vcc_lna_y - 2)
    cap("10n", vcc_lna_x + 10, vcc_lna_y + 2)
    wire(vcc_lna_x + 10, vcc_lna_y + 5.81, vcc_lna_x + 10, vcc_lna_y + 8)
    power_symbol("GND", vcc_lna_x + 10, vcc_lna_y + 8)
    wire(vcc_lna_x + 5, vcc_lna_y - 5, vcc_lna_x + 10, vcc_lna_y - 5)

    # VPDC (pin 16) - bias decoupling via cap to GND
    wire(lna_x - 10.16, lna_y + 2.54, lna_x - 15, lna_y + 2.54)
    cap("100n", lna_x - 19, lna_y + 2.54, angle=90)
    wire(lna_x - 22.81, lna_y + 2.54, lna_x - 25, lna_y + 2.54)
    power_symbol("GND", lna_x - 25, lna_y + 2.54)

    # DECL pin 11 (right at y+2.54) - 100pF decoupling to GND
    wire(lna_x + 10.16, lna_y + 2.54, lna_x + 15, lna_y + 2.54)
    cap("100p", lna_x + 19, lna_y + 2.54, angle=90)
    wire(lna_x + 22.81, lna_y + 2.54, lna_x + 25, lna_y + 2.54)
    power_symbol("GND", lna_x + 25, lna_y + 2.54)

    # Input matching: wire from T/R switch RF1
    wire(rx_path_x + 10, sw_y + 5.08, lna_x - 15, lna_y + 7.62)
    wire(lna_x - 15, lna_y + 7.62, lna_x - 10.16, lna_y + 7.62)

    # Output matching: RFOUT (pin 9, right at y+7.62)
    wire(lna_x + 10.16, lna_y + 7.62, lna_x + 30, lna_y + 7.62)

    # ================================================================
    # SECTION 5: RX SAW FILTER (generic bandpass)
    # ================================================================
    text_note("RX SAW FILTER", 230, 20, 2.0)
    text_note("225-512 MHz SAW bandpass filter", 230, 24, 1.27)

    saw_x, saw_y = 235, 45 + 7.62
    counts["symbols"] += 1
    u_saw = uid()
    saw_ref = "FL1"
    emit(f'    (symbol (lib_id "Device:BPF") (at {saw_x} {saw_y} 0)')
    emit(f'      (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)')
    emit(f'      (uuid "{u_saw}")')
    emit(f'      (property "Reference" "{saw_ref}" (at {saw_x} {saw_y - 2} 0) (effects (font (size 1.27 1.27))))')
    emit(f'      (property "Value" "SAW 225-512MHz" (at {saw_x} {saw_y + 2} 0) (effects (font (size 1.27 1.27))))')
    emit(f'      (property "Footprint" "" (at {saw_x} {saw_y} 0) (effects (font (size 1.27 1.27)) hide))')
    emit(f'      (property "Datasheet" "" (at {saw_x} {saw_y} 0) (effects (font (size 1.27 1.27)) hide))')
    symbol_pins(["1", "2", "3"])

    # GND on SAW
    wire(saw_x, saw_y + 5.08, saw_x, saw_y + 9)
    power_symbol("GND", saw_x, saw_y + 9)

    # Wire LNA output to SAW input
    wire(lna_x + 30, lna_y + 7.62, saw_x - 7.62, saw_y)

    # SAW output
    wire(saw_x + 7.62, saw_y, saw_x + 20, saw_y)

    # ================================================================
    # SECTION 6: RX TO AD9361 - AC COUPLING
    # ================================================================
    text_note("RX TO AD9361", 265, 20, 2.0)
    text_note("AC coupled 100pF differential", 265, 24, 1.27)

    rx_ac_x = saw_x + 20
    rx_ac_y = saw_y

    # AC coupling cap 100pF for RX1A_P
    cap("100p", rx_ac_x + 5, rx_ac_y, angle=90)
    wire(rx_ac_x + 5 + 3.81, rx_ac_y, rx_ac_x + 15, rx_ac_y)
    hier_label("AD_RX1A_P", rx_ac_x + 15, rx_ac_y, "output", 0)

    # RX1A_N path (offset below)
    rx_n_y = rx_ac_y + 8
    wire(rx_ac_x, rx_ac_y, rx_ac_x, rx_n_y)
    wire(rx_ac_x, rx_n_y, rx_ac_x + 1.19, rx_n_y)
    cap("100p", rx_ac_x + 5, rx_n_y, angle=90)
    wire(rx_ac_x + 5 + 3.81, rx_n_y, rx_ac_x + 15, rx_n_y)
    hier_label("AD_RX1A_N", rx_ac_x + 15, rx_n_y, "output", 0)

    # ================================================================
    # SECTION 7: TX FROM AD9361 - AC COUPLING
    # ================================================================
    text_note("TX FROM AD9361", 130, 90, 2.0)
    text_note("AC coupled 100pF, single-ended drive to TX driver", 130, 94, 1.27)

    tx_ac_x = 135
    tx_ac_y = 107

    hier_label("AD_TX1A", tx_ac_x - 15, tx_ac_y, "input", 0)
    wire(tx_ac_x - 15, tx_ac_y, tx_ac_x - 5, tx_ac_y)
    cap("100p", tx_ac_x, tx_ac_y, angle=90)
    wire(tx_ac_x + 3.81, tx_ac_y, tx_ac_x + 15, tx_ac_y)

    # ================================================================
    # SECTION 8: TX DRIVER ADL5606
    # ================================================================
    text_note("TX DRIVER ADL5606", 175, 90, 2.0)
    text_note("Differential driver, Gain ~20 dB, single-ended input via INP", 175, 94, 1.27)

    drv_x, drv_y = 195, 107
    drv_ref = next_u()
    symbol_instance("cirradio:ADL5606ACPZ", drv_ref, "ADL5606ACPZ", drv_x, drv_y,
                    footprint="Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.65x2.65mm")
    symbol_pins([str(i) for i in range(1, 26)])

    # GND
    wire(drv_x, drv_y + 16.51, drv_x, drv_y + 20)
    power_symbol("GND", drv_x, drv_y + 20)

    # VCC = +5V_PA
    wire(drv_x, drv_y - 16.51, drv_x, drv_y - 20)
    global_label("+5V_PA", drv_x, drv_y - 20, "passive")

    # Decoupling: 100nF + 10nF near VCC
    wire(drv_x + 8, drv_y - 20, drv_x + 8, drv_y - 17)
    cap("100n", drv_x + 8, drv_y - 13)
    wire(drv_x + 8, drv_y - 9.19, drv_x + 8, drv_y - 7)
    power_symbol("GND", drv_x + 8, drv_y - 7)
    wire(drv_x, drv_y - 20, drv_x + 8, drv_y - 20)

    wire(drv_x + 14, drv_y - 20, drv_x + 14, drv_y - 17)
    cap("10n", drv_x + 14, drv_y - 13)
    wire(drv_x + 14, drv_y - 9.19, drv_x + 14, drv_y - 7)
    power_symbol("GND", drv_x + 14, drv_y - 7)
    wire(drv_x + 8, drv_y - 20, drv_x + 14, drv_y - 20)

    # INP (pin 1) from AC coupling
    wire(tx_ac_x + 15, tx_ac_y, drv_x - 10.16, drv_y + 10.16)

    # INM (pin 3) - AC ground via cap
    wire(drv_x - 10.16, drv_y + 7.62, drv_x - 15, drv_y + 7.62)
    cap("100n", drv_x - 19, drv_y + 7.62, angle=90)
    wire(drv_x - 22.81, drv_y + 7.62, drv_x - 25, drv_y + 7.62)
    power_symbol("GND", drv_x - 25, drv_y + 7.62)

    # PWDN (pin 19) - hierarchical label to Zynq PL
    hier_label("TX_DRV_PWDN", drv_x - 18, drv_y + 2.54, "input", 0)
    wire(drv_x - 18, drv_y + 2.54, drv_x - 10.16, drv_y + 2.54)

    # OUTP (pin 7) -> to PA
    wire(drv_x + 10.16, drv_y + 10.16, drv_x + 25, drv_y + 10.16)

    # OUTM (pin 9) - terminate with 50 ohm to GND (not used single-ended)
    wire(drv_x + 10.16, drv_y + 7.62, drv_x + 15, drv_y + 7.62)
    resistor("49.9", drv_x + 19, drv_y + 7.62, angle=90)
    wire(drv_x + 22.81, drv_y + 7.62, drv_x + 25, drv_y + 7.62)
    power_symbol("GND", drv_x + 25, drv_y + 7.62)

    # ================================================================
    # SECTION 9: TX PA TGA2594-SM
    # ================================================================
    text_note("TX PA TGA2594-SM (+37 dBm / 5W)", 245, 90, 2.0)
    text_note("GaAs pHEMT power amplifier, VDD=+5V_PA", 245, 94, 1.27)

    pa_x, pa_y = 260, 107
    pa_ref = next_u()
    symbol_instance("cirradio:TGA2594-SM", pa_ref, "TGA2594-SM", pa_x, pa_y,
                    footprint="cirradio:TGA2594-SM")
    symbol_pins([str(i) for i in range(1, 11)])

    # GND
    wire(pa_x, pa_y + 11.43, pa_x, pa_y + 15)
    power_symbol("GND", pa_x, pa_y + 15)

    # VDD = +5V_PA (heavy decoupling: 10uF + 100nF + 10nF)
    pa_vdd_y = pa_y - 11.43
    wire(pa_x, pa_vdd_y, pa_x, pa_vdd_y - 3)
    global_label("+5V_PA", pa_x, pa_vdd_y - 3, "passive")

    # 10uF bulk cap
    wire(pa_x + 8, pa_vdd_y - 3, pa_x + 8, pa_vdd_y)
    cap("10u", pa_x + 8, pa_vdd_y + 4, fp="Capacitor_SMD:C_0805_2012Metric")
    wire(pa_x + 8, pa_vdd_y + 7.81, pa_x + 8, pa_vdd_y + 10)
    power_symbol("GND", pa_x + 8, pa_vdd_y + 10)
    wire(pa_x, pa_vdd_y - 3, pa_x + 8, pa_vdd_y - 3)

    # 100nF
    wire(pa_x + 14, pa_vdd_y - 3, pa_x + 14, pa_vdd_y)
    cap("100n", pa_x + 14, pa_vdd_y + 4)
    wire(pa_x + 14, pa_vdd_y + 7.81, pa_x + 14, pa_vdd_y + 10)
    power_symbol("GND", pa_x + 14, pa_vdd_y + 10)
    wire(pa_x + 8, pa_vdd_y - 3, pa_x + 14, pa_vdd_y - 3)

    # 10nF
    wire(pa_x + 20, pa_vdd_y - 3, pa_x + 20, pa_vdd_y)
    cap("10n", pa_x + 20, pa_vdd_y + 4)
    wire(pa_x + 20, pa_vdd_y + 7.81, pa_x + 20, pa_vdd_y + 10)
    power_symbol("GND", pa_x + 20, pa_vdd_y + 10)
    wire(pa_x + 14, pa_vdd_y - 3, pa_x + 20, pa_vdd_y - 3)

    # RF_IN from driver OUTP
    wire(drv_x + 25, drv_y + 10.16, pa_x - 15, pa_y + 5.08)
    wire(pa_x - 15, pa_y + 5.08, pa_x - 10.16, pa_y + 5.08)

    # RF_OUT to harmonic LPF
    wire(pa_x + 10.16, pa_y + 5.08, pa_x + 20, pa_y + 5.08)

    # ================================================================
    # SECTION 10: HARMONIC LPF (3-element Chebyshev: 33pF-27nH-33pF)
    # ================================================================
    text_note("HARMONIC LPF (Chebyshev)", 300, 90, 2.0)
    text_note("3-element: 33pF shunt - 27nH series - 33pF shunt", 300, 94, 1.27)

    lpf_x = pa_x + 20
    lpf_y = pa_y + 5.08

    # Shunt C1 to GND
    wire(lpf_x, lpf_y, lpf_x, lpf_y + 3)
    cap("33p", lpf_x, lpf_y + 7)
    wire(lpf_x, lpf_y + 10.81, lpf_x, lpf_y + 13)
    power_symbol("GND", lpf_x, lpf_y + 13)

    # Series inductor
    wire(lpf_x, lpf_y, lpf_x + 5, lpf_y)
    inductor("27n", lpf_x + 10, lpf_y, angle=90, fp="Inductor_SMD:L_0402_1005Metric")
    wire(lpf_x + 10 + 3.81, lpf_y, lpf_x + 20, lpf_y)

    # Shunt C2 to GND
    wire(lpf_x + 20, lpf_y, lpf_x + 20, lpf_y + 3)
    cap("33p", lpf_x + 20, lpf_y + 7)
    wire(lpf_x + 20, lpf_y + 10.81, lpf_x + 20, lpf_y + 13)
    power_symbol("GND", lpf_x + 20, lpf_y + 13)

    # Output of LPF back to T/R switch TX path
    wire(lpf_x + 20, lpf_y, lpf_x + 30, lpf_y)
    # Connect back to the T/R switch RF2 line (routed down earlier)
    wire(lpf_x + 30, lpf_y, lpf_x + 30, sw_y + 60)
    wire(lpf_x + 30, sw_y + 60, tx_path_x + 5, sw_y + 60)

    # ================================================================
    # SECTION 11: RF ROUTING NOTES
    # ================================================================
    text_note("RF ROUTING NOTES", 30, 150, 2.0)
    text_note("- All RF traces: 50 ohm controlled impedance (microstrip or CPWG)", 30, 155, 1.27)
    text_note("- Keep RF traces short, minimize vias in signal path", 30, 159, 1.27)
    text_note("- Ground plane continuous under all RF sections", 30, 163, 1.27)
    text_note("- T/R switch PE42525: place close to antenna SMA", 30, 167, 1.27)
    text_note("- LNA input: minimize trace length from T/R switch for NF", 30, 171, 1.27)
    text_note("- PA output: wide traces, thermal relief on VDD", 30, 175, 1.27)
    text_note("- BPF/LPF components: tight placement, minimize parasitic inductance", 30, 179, 1.27)
    text_note("- RX/TX isolation: physical separation, guard traces with via fencing", 30, 183, 1.27)
    text_note("- Decoupling caps: place as close to IC power pins as possible", 30, 187, 1.27)
    text_note("- AD9361 interface: matched-length differential pairs", 30, 191, 1.27)

    # ================================================================
    # Close the schematic
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

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/rf-frontend.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"Component counts:")
    print(f"  SMA connector: 1 (J1)")
    print(f"  T/R switch PE42525: 1 ({sw_ref})")
    print(f"  LNA ADL5523: 1 ({lna_ref})")
    print(f"  SAW filter: 1 ({saw_ref})")
    print(f"  TX driver ADL5606: 1 ({drv_ref})")
    print(f"  PA TGA2594-SM: 1 ({pa_ref})")
    print(f"  Capacitors: {counts['capacitors']}")
    print(f"  Inductors: {counts['inductors']}")
    print(f"  Resistors: {counts['resistors']}")
    print(f"  Power symbols: {pwr_idx[0] - 300}")
    print(f"  Wires: {counts['wires']}")
    print(f"  Global labels: {counts['gl_labels']}")
    print(f"  Hierarchical labels: {counts['hier_labels']}")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")

if __name__ == "__main__":
    main()
