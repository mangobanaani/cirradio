#!/usr/bin/env python3
"""Generate connectors and debug schematic sheet for CIRRADIO dev board."""

import uuid
import sys

def uid():
    return str(uuid.uuid4())

# Reference designator counters - start at 200 to avoid conflicts with
# power sheet (1-99) and zynq sheet (100-199)
cap_idx = [200]
res_idx = [200]
pwr_idx = [200]
led_idx = [1]
btn_idx = [1]
tp_idx = [1]
conn_idx = [10]  # J10+ to avoid conflicts with J1 (Barrel), J2 (JTAG), etc.

counts = {"capacitors": 0, "resistors": 0, "symbols": 0, "wires": 0,
           "labels": 0, "gl_labels": 0, "hier_labels": 0, "leds": 0,
           "buttons": 0, "test_points": 0}

lines = []
def emit(s):
    lines.append(s)

def next_cap():
    c = cap_idx[0]; cap_idx[0] += 1; return f"C{c}"

def next_res():
    r = res_idx[0]; res_idx[0] += 1; return f"R{r}"

def next_pwr():
    p = pwr_idx[0]; pwr_idx[0] += 1; return f"#PWR{p:04d}"

def next_led():
    d = led_idx[0]; led_idx[0] += 1; return f"D{d}"

def next_btn():
    b = btn_idx[0]; btn_idx[0] += 1; return f"SW{b}"

def next_tp():
    t = tp_idx[0]; tp_idx[0] += 1; return f"TP{t}"

def next_conn():
    j = conn_idx[0]; conn_idx[0] += 1; return f"J{j}"


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

def net_label(name, x, y, angle=0):
    counts["labels"] += 1
    emit(f'    (label "{name}" (at {x} {y} {angle}) (effects (font (size 1.27 1.27))) (uuid "{uid()}"))')

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
    symbol_instance("Device:R", ref, value, x, y, angle=angle, footprint="Resistor_SMD:R_0402_1005Metric")
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

    # Switch:SW_Push (tactile button)
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

    # Connector_Generic:Conn_02x20_Odd_Even (GPIO header)
    emit('''    (symbol "Connector_Generic:Conn_02x20_Odd_Even"
      (pin_names (offset 1.016) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 1.27 26.67 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_02x20_Odd_Even" (at 1.27 -26.67 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "Conn_02x20_Odd_Even_1_1"
        (rectangle (start -1.27 25.4) (end 3.81 -25.4) (stroke (width 0.254) (type default)) (fill (type background)))''')
    for i in range(20):
        odd = i * 2 + 1
        even = i * 2 + 2
        y = 24.13 - i * 2.54
        emit(f'        (pin passive line (at -3.81 {y} 0) (length 2.54) (name "Pin_{odd}" (effects (font (size 1.27 1.27)))) (number "{odd}" (effects (font (size 1.27 1.27)))))')
        emit(f'        (pin passive line (at 6.35 {y} 180) (length 2.54) (name "Pin_{even}" (effects (font (size 1.27 1.27)))) (number "{even}" (effects (font (size 1.27 1.27)))))')
    emit('''      )
    )''')

    # Connector:TestPoint
    emit('''    (symbol "Connector:TestPoint"
      (pin_names (offset 0.762) hide) (exclude_from_sim no) (in_bom no) (on_board yes)
      (property "Reference" "TP" (at 0 5.842 0) (effects (font (size 1.27 1.27))))
      (property "Value" "TestPoint" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 5.08 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 5.08 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "TestPoint_0_1"
        (circle (center 0 1.778) (radius 0.762) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "TestPoint_1_1"
        (pin passive line (at 0 0 90) (length 1.016) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      )
    )''')

    # Power symbols
    for net in ["+12V", "+5V", "+3V3", "+1V8", "+1V35", "+1V0", "+1V5", "VTT", "GND"]:
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
        elif net == "VTT":
            # VTT is not a standard KiCad power symbol, define custom
            emit(f'''    (symbol "power:VTT"
      (power) (pin_names (offset 0)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) hide))
      (property "Value" "VTT" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "VTT_0_1"
        (polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "VTT_1_1"
        (pin power_in line (at 0 0 90) (length 0) (name "VTT" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
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


def test_point(name, x, y, fp="TestPoint:TestPoint_Pad_1.5x1.5mm"):
    """Place a test point."""
    counts["test_points"] += 1
    ref = next_tp()
    symbol_instance("Connector:TestPoint", ref, name, x, y, footprint=fp)
    symbol_pins(["1"])


def main():
    # ================================================================
    # Header
    # ================================================================
    emit('(kicad_sch')
    emit('  (version 20231120)')
    emit('  (generator "cirradio_gen_connectors")')
    emit('  (generator_version "9.0")')
    emit(f'  (uuid "{uid()}")')
    emit('  (paper "A3")')
    emit('  (title_block')
    emit('    (title "CIRRADIO Dev Board - Connectors & Debug")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (company "")')
    emit('    (comment 1 "GPIO header, status LEDs, user buttons, test points")')
    emit('    (comment 2 "Matches Zynq PL Bank 12 hierarchical labels")')
    emit('  )')
    emit('')

    # Library symbols
    emit_lib_symbols()
    emit('')

    # ================================================================
    # SECTION 1: GPIO Header (2x20, 0.1" pitch)
    # ================================================================
    text_note("GPIO HEADER (2x20, 0.1 inch pitch)", 30, 20, 2.0)
    text_note("PL Bank 12 I/O with 33R series protection", 30, 25, 1.27)

    # Place the 2x20 connector
    hdr_ref = next_conn()
    hdr_x, hdr_y = 180, 90
    symbol_instance("Connector_Generic:Conn_02x20_Odd_Even", hdr_ref,
                    "GPIO_2x20", hdr_x, hdr_y,
                    footprint="Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical")
    pin_nums = [str(i) for i in range(1, 41)]
    symbol_pins(pin_nums)

    # GPIO header pinout (Raspberry Pi-style numbering):
    # Pin 1: +3V3    Pin 2: +5V
    # Pin 3: PL_IO0  Pin 4: +5V
    # Pin 5: PL_IO1  Pin 6: GND
    # Pin 7: PL_IO2  Pin 8: PS_UART0_TX
    # Pin 9: GND     Pin 10: PS_UART0_RX
    # Pin 11: PL_IO3 Pin 12: PL_IO4
    # Pin 13: PL_IO5 Pin 14: GND
    # Pin 15: PL_IO6 Pin 16: PL_IO7
    # Pin 17: +3V3   Pin 18: PL_IO8
    # Pin 19: PL_IO9 Pin 20: GND
    # Pin 21: PL_IO10 Pin 22: PL_IO11
    # Pin 23: PL_IO12 Pin 24: PL_IO13
    # Pin 25: GND     Pin 26: PL_IO14
    # Pin 27: PS_I2C_SDA Pin 28: PS_I2C_SCL
    # Pin 29: PL_IO15 Pin 30: GND
    # Pin 31: PL_IO16 Pin 32: PL_IO17
    # Pin 33: PL_IO18 Pin 34: GND
    # Pin 35: PL_IO19 Pin 36: PS_SPI_CE0
    # Pin 37: PS_SPI_MISO Pin 38: PS_SPI_MOSI
    # Pin 39: GND     Pin 40: PS_SPI_SCLK

    # Define pin assignments: (pin_number, net_name, type)
    # type: "power", "gnd", "pl_io", "ps_sig"
    pin_assignments = [
        (1,  "+3V3",        "power"),
        (2,  "+5V",         "power"),
        (3,  "PL_IO0",      "pl_io"),
        (4,  "+5V",         "power"),
        (5,  "PL_IO1",      "pl_io"),
        (6,  "GND",         "gnd"),
        (7,  "PL_IO2",      "pl_io"),
        (8,  "PS_UART0_TX", "ps_sig"),
        (9,  "GND",         "gnd"),
        (10, "PS_UART0_RX", "ps_sig"),
        (11, "PL_IO3",      "pl_io"),
        (12, "PL_IO4",      "pl_io"),
        (13, "PL_IO5",      "pl_io"),
        (14, "GND",         "gnd"),
        (15, "PL_IO6",      "pl_io"),
        (16, "PL_IO7",      "pl_io"),
        (17, "+3V3",        "power"),
        (18, "PL_IO8",      "pl_io"),
        (19, "PL_IO9",      "pl_io"),
        (20, "GND",         "gnd"),
        (21, "PL_IO10",     "pl_io"),
        (22, "PL_IO11",     "pl_io"),
        (23, "PL_IO12",     "pl_io"),
        (24, "PL_IO13",     "pl_io"),
        (25, "GND",         "gnd"),
        (26, "PL_IO14",     "pl_io"),
        (27, "PS_I2C_SDA",  "ps_sig"),
        (28, "PS_I2C_SCL",  "ps_sig"),
        (29, "PL_IO15",     "pl_io"),
        (30, "GND",         "gnd"),
        (31, "PL_IO16",     "pl_io"),
        (32, "PL_IO17",     "pl_io"),
        (33, "PL_IO18",     "pl_io"),
        (34, "GND",         "gnd"),
        (35, "PL_IO19",     "pl_io"),
        (36, "PS_SPI_CE0",  "ps_sig"),
        (37, "PS_SPI_MISO", "ps_sig"),
        (38, "PS_SPI_MOSI", "ps_sig"),
        (39, "GND",         "gnd"),
        (40, "PS_SPI_SCLK", "ps_sig"),
    ]

    # Place series 33R resistors on PL I/O lines, and connect all header pins
    # Odd pins are on the left side (hdr_x - 3.81), even on the right (hdr_x + 6.35)
    # Place labels to the left of odd pins, to the right of even pins

    pl_io_resistor_x = 120  # X position for series resistors (left of header)
    pl_io_label_x = 100     # X position for hierarchical labels

    for pin_num, net_name, pin_type in pin_assignments:
        row = (pin_num - 1) // 2
        y = hdr_y - 25.4 + 24.13 - row * 2.54
        is_odd = (pin_num % 2 == 1)

        if is_odd:
            pin_x = hdr_x - 3.81
        else:
            pin_x = hdr_x + 6.35

        if pin_type == "power":
            if is_odd:
                power_symbol(net_name, pin_x - 8, y, angle=90)
                wire(pin_x - 8, y, pin_x, y)
            else:
                power_symbol(net_name, pin_x + 8, y, angle=270)
                wire(pin_x, y, pin_x + 8, y)

        elif pin_type == "gnd":
            if is_odd:
                power_symbol("GND", pin_x - 8, y, angle=90)
                wire(pin_x - 8, y, pin_x, y)
            else:
                power_symbol("GND", pin_x + 8, y, angle=270)
                wire(pin_x, y, pin_x + 8, y)

        elif pin_type == "pl_io":
            # PL I/O: series 33R resistor then hierarchical label to Bank 12
            # Extract the IO index for the hierarchical label
            io_idx = int(net_name.replace("PL_IO", ""))
            bank12_net = f"GPIO_B12_IO{io_idx}"

            if is_odd:
                # Wire from header pin left to resistor
                wire(pin_x, y, pl_io_resistor_x + 3.81, y)
                resistor("33R", pl_io_resistor_x, y, angle=90)
                wire(pl_io_resistor_x - 3.81, y, pl_io_label_x, y)
                # Hierarchical label matching Zynq Bank 12
                hier_label(bank12_net, pl_io_label_x, y, "bidirectional", 180)
            else:
                # For even pins with PL I/O, route right to resistor and label
                right_res_x = hdr_x + 6.35 + 18
                right_label_x = right_res_x + 18
                wire(pin_x, y, right_res_x - 3.81, y)
                resistor("33R", right_res_x, y, angle=90)
                wire(right_res_x + 3.81, y, right_label_x, y)
                hier_label(bank12_net, right_label_x, y, "bidirectional")

        elif pin_type == "ps_sig":
            # PS signals: global label (connects to other sheets)
            if is_odd:
                global_label(net_name, pin_x - 10, y, "bidirectional", 0)
                wire(pin_x - 10, y, pin_x, y)
            else:
                global_label(net_name, pin_x + 10, y, "bidirectional", 180)
                wire(pin_x, y, pin_x + 10, y)

    # ================================================================
    # SECTION 2: Status LEDs (4x 0603)
    # ================================================================
    text_note("STATUS LEDs", 30, 160, 2.0)
    text_note("Active-high, 0603 package", 30, 165, 1.27)

    # LED layout: +rail -> R -> LED(A->K) -> GND
    # For power LED: +3V3 -> 4.7K -> LED -> GND (always on)
    # For signal LEDs: PL_signal -> 330R -> LED -> GND

    led_configs = [
        ("PWR",   "Green", "+3V3",      "4.7K",  None,          "Power (always on)"),
        ("HB",    "Green", "PL_LED_HB", "330R",  "GPIO_B12_IO40", "Heartbeat"),
        ("TX",    "Red",   "PL_LED_TX", "330R",  "GPIO_B12_IO41", "TX activity"),
        ("RX",    "Green", "PL_LED_RX", "330R",  "GPIO_B12_IO42", "RX activity"),
    ]

    led_base_x = 60
    led_base_y = 185
    led_spacing = 20

    for idx, (name, color, source, res_val, bank12_net, desc) in enumerate(led_configs):
        x = led_base_x + idx * led_spacing
        y = led_base_y

        text_note(f"{name} ({color})", x - 2, y - 10, 1.0)

        counts["leds"] += 1
        led_ref = next_led()

        if source == "+3V3":
            # Power LED: +3V3 at top
            power_symbol("+3V3", x, y - 8)
            wire(x, y - 8, x, y - 5)
        else:
            # Signal LED: hierarchical label from Bank 12
            hier_label(bank12_net, x - 12, y - 5, "bidirectional", 0)
            wire(x - 12, y - 5, x, y - 5)

        # Series resistor (vertical)
        resistor(res_val, x, y, angle=0)
        wire(x, y - 5, x, y - 3.81)

        # LED below resistor
        symbol_instance("Device:LED", led_ref, f"{color}", x, y + 8,
                        footprint="LED_SMD:LED_0603_1608Metric", angle=90)
        symbol_pins(["1", "2"])
        wire(x, y + 3.81, x, y + 4.19)

        # GND below LED
        power_symbol("GND", x, y + 16)
        wire(x, y + 11.81, x, y + 16)

    # ================================================================
    # SECTION 3: User Buttons (2x tactile, active-low)
    # ================================================================
    text_note("USER BUTTONS (active-low, 10K pull-up, 100nF debounce)", 30, 225, 2.0)

    btn_configs = [
        ("BTN0", "GPIO_B12_IO44"),
        ("BTN1", "GPIO_B12_IO45"),
    ]

    btn_base_x = 70
    btn_base_y = 255
    btn_spacing = 50

    for idx, (name, bank12_net) in enumerate(btn_configs):
        bx = btn_base_x + idx * btn_spacing
        by = btn_base_y

        text_note(name, bx - 3, by - 15, 1.27)

        counts["buttons"] += 1
        btn_ref = next_btn()

        # Pull-up: +3V3 -> 10K -> node
        power_symbol("+3V3", bx, by - 18)
        wire(bx, by - 18, bx, by - 15)
        resistor("10K", bx, by - 11, angle=0)
        wire(bx, by - 15, bx, by - 14.81)

        # Node where button, pull-up, debounce cap, and signal meet
        node_y = by - 5
        wire(bx, by - 7.19, bx, node_y)

        # Button: node -> switch -> GND
        symbol_instance("Switch:SW_Push", btn_ref, name, bx, by,
                        footprint="Button_Switch_SMD:SW_Push_1P1T_NO_6x6mm_H9.5mm")
        symbol_pins(["1", "2"])
        wire(bx, node_y, bx - 5.08, by)
        wire(bx + 5.08, by, bx + 10, by)
        power_symbol("GND", bx + 10, by)

        # Debounce cap: node -> 100nF -> GND
        cap_x = bx + 8
        wire(bx, node_y, cap_x, node_y)
        cap("100n", cap_x, node_y + 5, "Capacitor_SMD:C_0402_1005Metric")
        power_symbol("GND", cap_x, node_y + 12)
        wire(cap_x, node_y + 8.81, cap_x, node_y + 12)
        wire(cap_x, node_y, cap_x, node_y + 1.19)

        # Hierarchical label to Bank 12
        hier_label(bank12_net, bx - 15, node_y, "bidirectional", 180)
        wire(bx - 15, node_y, bx, node_y)

    # ================================================================
    # SECTION 4: Test Points (SMD pads)
    # ================================================================
    text_note("TEST POINTS (SMD pads)", 30, 300, 2.0)
    text_note("All power rails + key signals", 30, 305, 1.27)

    tp_rails = [
        ("+12V",  "power"),
        ("+5V",   "power"),
        ("+3V3",  "power"),
        ("+1V8",  "power"),
        ("+1V35", "power"),
        ("+1V0",  "power"),
        ("+1V5",  "power"),
        ("VTT",   "power"),
        ("GND",   "gnd"),
    ]

    tp_signals = [
        ("GPS_1PPS", "signal"),
        ("PS_CLK",   "signal"),
    ]

    tp_base_x = 40
    tp_base_y = 325
    tp_spacing_x = 25
    tp_spacing_y = 30

    # Power rail test points (top row)
    for idx, (net, tp_type) in enumerate(tp_rails):
        tx = tp_base_x + idx * tp_spacing_x
        ty = tp_base_y

        test_point(net, tx, ty, "TestPoint:TestPoint_Pad_1.5x1.5mm")

        if tp_type == "gnd":
            power_symbol("GND", tx, ty - 5)
            wire(tx, ty, tx, ty - 5)
        else:
            power_symbol(net, tx, ty - 5)
            wire(tx, ty, tx, ty - 5)

    # Signal test points (bottom row)
    for idx, (net, tp_type) in enumerate(tp_signals):
        tx = tp_base_x + idx * tp_spacing_x
        ty = tp_base_y + tp_spacing_y

        test_point(net, tx, ty, "TestPoint:TestPoint_Pad_1.5x1.5mm")

        global_label(net, tx, ty - 5, "passive")
        wire(tx, ty, tx, ty - 5)

    # ================================================================
    # SECTION 5: Board ID silkscreen
    # ================================================================
    text_note("CIRRADIO DevBoard v1.0", 30, 390, 3.0)

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

    outpath = "/Users/pekka/Documents/cirradio/hardware/cirradio-devboard/connectors.kicad_sch"
    with open(outpath, 'w') as f:
        f.write(output)

    print(f"Generated: {outpath}")
    print(f"Component counts:")
    print(f"  GPIO header: 1 ({hdr_ref})")
    print(f"  LEDs: {counts['leds']}")
    print(f"  Buttons: {counts['buttons']}")
    print(f"  Test points: {counts['test_points']}")
    print(f"  Resistors: {counts['resistors']}")
    print(f"  Capacitors: {counts['capacitors']}")
    print(f"  Power symbols: {pwr_idx[0] - 200}")
    print(f"  Wires: {counts['wires']}")
    print(f"  Global labels: {counts['gl_labels']}")
    print(f"  Hierarchical labels: {counts['hier_labels']}")
    print(f"  Parentheses balanced: {opens} opens, {closes} closes")


if __name__ == "__main__":
    main()
