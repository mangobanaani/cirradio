#!/usr/bin/env python3
"""Generate PCB component placement for CIRRADIO dev board.

Parses all 7 sub-schematic files, assigns components to physical zones,
and generates footprint entries in the .kicad_pcb file with correct
placement coordinates.

Zone plan (160x100mm board):
  Top-left     (0-60, 0-40):     RF front-end (shielded)
  Top-center   (60-100, 0-32):   AD9361 + OCXO
  Center       (40-120, 32-80):  Zynq-7045
  Center-right (100-140, 25-55): DDR3L memory
  Bottom-left  (0-60, 60-100):   Power supply
  Bottom-right (100-160, 60-100): Connectors, peripherals
  Right edge   (155-160, 30-50): SMA antenna
  Top-right    (140-160, 0-30):  GPS module + U.FL
"""

import re
import os
import uuid
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCHEMATIC_FILES = [
    "power.kicad_sch",
    "zynq.kicad_sch",
    "ddr3l.kicad_sch",
    "ad9361.kicad_sch",
    "rf-frontend.kicad_sch",
    "peripherals.kicad_sch",
    "connectors.kicad_sch",
]

SCHEMATIC_ZONE = {
    "power.kicad_sch": "power",
    "zynq.kicad_sch": "zynq",
    "ddr3l.kicad_sch": "ddr3l",
    "ad9361.kicad_sch": "ad9361",
    "rf-frontend.kicad_sch": "rf",
    "peripherals.kicad_sch": "peripherals",
    "connectors.kicad_sch": "connectors",
}


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Schematic parsing (reused from gen_pcb_netlist.py)
# ---------------------------------------------------------------------------

def parse_schematic(filepath):
    """Parse a KiCad schematic file and extract component instances."""
    with open(filepath, "r") as f:
        content = f.read()

    components = []

    # Find where lib_symbols ends
    lib_sym_end = 0
    lib_sym_start = content.find("(lib_symbols")
    if lib_sym_start >= 0:
        depth = 0
        i = lib_sym_start
        while i < len(content):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    lib_sym_end = i + 1
                    break
            i += 1

    body = content[lib_sym_end:] if lib_sym_end > 0 else content

    sym_pattern = re.compile(
        r'\(symbol\s+\(lib_id\s+"([^"]+)"\)\s+\(at\s+[\d.\-e ]+ \d+\)'
    )

    for m in sym_pattern.finditer(body):
        lib_id = m.group(1)
        start = m.start()

        depth = 0
        i = start
        while i < len(body):
            if body[i] == '(':
                depth += 1
            elif body[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        sym_block = body[start:i+1]

        ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', sym_block)
        val_m = re.search(r'\(property\s+"Value"\s+"([^"]+)"', sym_block)
        fp_m = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', sym_block)

        ref = ref_m.group(1) if ref_m else ""
        val = val_m.group(1) if val_m else ""
        fp = fp_m.group(1) if fp_m else ""

        if lib_id.startswith("power:"):
            continue
        if ref.startswith("#"):
            continue

        components.append({
            "reference": ref,
            "value": val,
            "footprint": fp,
            "lib_id": lib_id,
        })

    return components


# ---------------------------------------------------------------------------
# Zone-based placement
# ---------------------------------------------------------------------------

class Zone:
    """Grid-based auto-placer within a rectangular zone."""

    def __init__(self, name, x_min, y_min, x_max, y_max):
        self.name = name
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        self.cursor_x = x_min + 1.0
        self.cursor_y = y_min + 1.0
        self.row_height = 0.0

    def place(self, ref, fp_name, w, h):
        """Place a component, return (x, y, rotation, layer) or None."""
        margin = 0.5
        needed_w = w + margin
        needed_h = h + margin

        if self.cursor_x + needed_w > self.x_max:
            self.cursor_x = self.x_min + 1.0
            self.cursor_y += self.row_height + margin
            self.row_height = 0.0

        if self.cursor_y + needed_h > self.y_max:
            return None

        x = self.cursor_x + w / 2.0
        y = self.cursor_y + h / 2.0
        self.cursor_x += needed_w
        self.row_height = max(self.row_height, needed_h)
        return (x, y, 0, "F.Cu")


def estimate_footprint_size(fp_name):
    """Estimate (width, height) in mm from footprint name."""
    fp = fp_name or ""
    if "0402" in fp:
        return (1.0, 0.5)
    if "0603" in fp:
        return (1.6, 0.8)
    if "0805" in fp:
        return (2.0, 1.25)
    if "1206" in fp or "1210" in fp:
        return (3.2, 1.6)
    if "BGA-900" in fp or "FFG900" in fp:
        return (31.0, 31.0)
    if "BGA-144" in fp:
        return (10.0, 10.0)
    if "BGA-96" in fp:
        return (8.0, 13.0)
    if "BGA-153" in fp:
        return (12.0, 16.0)
    if "QFN-48" in fp:
        return (7.0, 7.0)
    if "QFN-32" in fp:
        return (5.0, 5.0)
    if "QFN-24" in fp or "QFN-16" in fp:
        return (3.0, 3.0)
    if "SOIC-8" in fp:
        return (5.0, 4.0)
    if "SOT-23-5" in fp:
        return (3.0, 3.0)
    if "SOT-23" in fp:
        return (3.0, 2.5)
    if "WSON-8_2x2" in fp:
        return (2.0, 2.0)
    if "WSON-8-1EP_6x5" in fp:
        return (6.0, 5.0)
    if "DIP-14" in fp:
        return (8.0, 20.0)
    if "PinHeader_2x20_P2.54" in fp:
        return (5.1, 50.8)
    if "PinHeader_2x07_P1.27" in fp:
        return (2.5, 8.9)
    if "SMA_Amphenol" in fp:
        return (5.0, 5.0)
    if "BarrelJack" in fp:
        return (9.0, 11.0)
    if "USB_A" in fp:
        return (12.0, 14.0)
    if "USB_Micro" in fp:
        return (8.0, 6.0)
    if "RJ45" in fp:
        return (16.0, 14.0)
    if "microSD" in fp:
        return (14.0, 15.0)
    if "U.FL" in fp:
        return (3.0, 3.0)
    if "LCC-16" in fp:
        return (12.0, 16.0)
    if "TGA2594" in fp:
        return (5.0, 5.0)
    if "TestPoint" in fp:
        return (1.5, 1.5)
    if "CP_Radial" in fp:
        return (8.0, 8.0)
    if "Crystal" in fp or "VDFN" in fp:
        return (3.2, 1.5)
    if "SW_DIP" in fp:
        return (10.0, 5.0)
    if "SW_Push" in fp or "SW_SPST" in fp:
        return (4.0, 3.0)
    if "D_SMA" in fp or "LED_0603" in fp:
        return (1.6, 0.8)
    if "FerriteBead" in fp:
        return (1.0, 0.5)
    return (2.0, 1.0)


def is_passive(comp):
    ref = comp["reference"]
    return ref[0] in ("R", "C", "L") and ref[1:].isdigit()


def build_placement_plan(components_by_zone):
    """Assign (x, y, rotation, layer) to every component."""
    placements = {}

    # Overflow zones for passives that don't fit
    zone_rf = Zone("RF Passives", 2, 2, 58, 38)
    zone_ad = Zone("AD9361 Passives", 62, 2, 98, 30)
    zone_zynq = Zone("Zynq Passives", 42, 34, 98, 78)
    zone_ddr = Zone("DDR3L Passives", 102, 27, 138, 53)
    zone_power = Zone("Power Passives", 2, 62, 58, 98)
    zone_conn = Zone("Conn Passives", 102, 62, 158, 98)

    # -------------------------------------------------------------------
    # 1. Zynq-7045 at board center
    # -------------------------------------------------------------------
    zynq_comps = components_by_zone.get("zynq", [])
    for comp in zynq_comps:
        ref = comp["reference"]
        if ref == "U1":
            placements[ref] = (80.0, 50.0, 0, "F.Cu")
        elif is_passive(comp):
            # Decoupling caps under Zynq on B.Cu
            w, h = estimate_footprint_size(comp["footprint"])
            if zone_zynq.cursor_y + h < 78:
                result = zone_zynq.place(ref, comp["footprint"], w, h)
                if result:
                    x, y, rot, _ = result
                    placements[ref] = (x, y, rot, "B.Cu")
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_zynq.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result

    # -------------------------------------------------------------------
    # 2. DDR3L memories (center-right)
    # -------------------------------------------------------------------
    ddr_comps = components_by_zone.get("ddr3l", [])
    for comp in ddr_comps:
        ref = comp["reference"]
        if ref == "U2":
            placements[ref] = (112.0, 35.0, 0, "F.Cu")
        elif ref == "U3":
            placements[ref] = (128.0, 35.0, 0, "F.Cu")
        elif is_passive(comp):
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_ddr.place(ref, comp["footprint"], w, h)
            if result:
                x, y, rot, _ = result
                placements[ref] = (x, y, rot, "B.Cu")
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_ddr.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result

    # -------------------------------------------------------------------
    # 3. AD9361 (top-center)
    # -------------------------------------------------------------------
    ad_comps = components_by_zone.get("ad9361", [])
    for comp in ad_comps:
        ref = comp["reference"]
        if ref == "U9":
            placements[ref] = (80.0, 16.0, 0, "F.Cu")
        elif ref in ("Y1", "Y2"):
            placements[ref] = (92.0, 10.0 if ref == "Y1" else 22.0, 0, "F.Cu")
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_ad.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result

    # -------------------------------------------------------------------
    # 4. RF front-end (top-left)
    # -------------------------------------------------------------------
    rf_comps = components_by_zone.get("rf", [])
    rf_ic_positions = {
        "U16": (15.0, 10.0, 0),   # PE42525 T/R switch
        "U17": (30.0, 10.0, 0),   # ADL5523 LNA
        "FL1": (42.0, 10.0, 0),   # SAW filter
        "U18": (30.0, 25.0, 0),   # ADL5606 driver amp
        "U19": (15.0, 25.0, 0),   # TGA2594 PA
        "J1":  (5.0, 18.0, 0),    # SMA input (if from RF sheet)
    }
    for comp in rf_comps:
        ref = comp["reference"]
        if ref in rf_ic_positions:
            x, y, rot = rf_ic_positions[ref]
            placements[ref] = (x, y, rot, "F.Cu")
        elif "BPF" in comp["value"] or "Harmonic" in comp["value"]:
            if ref not in placements:
                w, h = estimate_footprint_size(comp["footprint"])
                result = zone_rf.place(ref, comp["footprint"], w, h)
                if result:
                    placements[ref] = result
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_rf.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result

    # -------------------------------------------------------------------
    # 5. Power supply (bottom-left)
    # -------------------------------------------------------------------
    power_comps = components_by_zone.get("power", [])
    power_ic_positions = {
        "U4":  (10.0, 72.0, 0),   # TPS54360B #1 (5V)
        "U5":  (10.0, 82.0, 0),   # TPS54360B #2 (3.3V)
        "U6":  (28.0, 68.0, 0),   # TPS62913 #1 (1.8V)
        "U7":  (28.0, 76.0, 0),   # TPS62913 #2 (1.35V)
        "U8":  (28.0, 84.0, 0),   # TPS62913 #3 (1.0V)
        "U20": (44.0, 68.0, 0),   # TPS62913 #4 (1.5V)
        "U21": (44.0, 78.0, 0),   # TPS51200 (VTT)
        "U22": (44.0, 88.0, 0),   # TPS3808 (supervisor)
    }
    for comp in power_comps:
        ref = comp["reference"]
        if ref in placements:
            continue
        if ref in power_ic_positions:
            x, y, rot = power_ic_positions[ref]
            placements[ref] = (x, y, rot, "F.Cu")
        elif ref == "J2":
            placements[ref] = (8.0, 94.0, 0, "F.Cu")
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_power.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result

    # -------------------------------------------------------------------
    # 6. Peripherals (split: GPS top-right, others bottom-right)
    # -------------------------------------------------------------------
    periph_comps = components_by_zone.get("peripherals", [])
    periph_ic_positions = {
        "U10": (148.0, 10.0, 0),   # MAX-M10S GPS
        "U11": (138.0, 22.0, 0),   # OCXO
        "U12": (110.0, 80.0, 0),   # USB3320C USB PHY
        "U13": (130.0, 80.0, 0),   # KSZ9031 ETH PHY
        "U14": (110.0, 90.0, 0),   # FT232RQ USB-UART
        "U15": (148.0, 80.0, 0),   # S25FL256 QSPI flash
        "U23": (130.0, 90.0, 0),   # eMMC
        "Y3":  (140.0, 86.0, 0),   # PS clock oscillator
    }
    periph_passive_zone = Zone("Periph Passives", 102, 62, 158, 68)
    for comp in periph_comps:
        ref = comp["reference"]
        if ref in placements:
            continue
        if ref in periph_ic_positions:
            x, y, rot = periph_ic_positions[ref]
            placements[ref] = (x, y, rot, "F.Cu")
        elif ref.startswith("J") and "U.FL" in comp["footprint"]:
            placements[ref] = (155.0, 10.0, 0, "F.Cu")
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = periph_passive_zone.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result
            else:
                result = zone_conn.place(ref, comp["footprint"], w, h)
                if result:
                    placements[ref] = result

    # -------------------------------------------------------------------
    # 7. Connectors (bottom-right and board edges)
    # -------------------------------------------------------------------
    conn_comps = components_by_zone.get("connectors", [])
    conn_positions = {
        "J3":  (156.0, 40.0, 90),  # SMA antenna (right edge)
        "J4":  (150.0, 94.0, 0),   # RJ-45 Ethernet
        "J5":  (120.0, 96.0, 0),   # USB-A
        "J6":  (108.0, 96.0, 0),   # USB Micro-B
        "J7":  (135.0, 70.0, 0),   # GPIO 2x20 header
        "J8":  (115.0, 70.0, 0),   # JTAG 2x7 header
        "J9":  (125.0, 96.0, 0),   # microSD slot
    }
    for comp in conn_comps:
        ref = comp["reference"]
        if ref in placements:
            continue
        if ref in conn_positions:
            x, y, rot = conn_positions[ref]
            placements[ref] = (x, y, rot, "F.Cu")
        elif ref.startswith("TP"):
            tp_match = re.search(r"\d+", ref)
            if tp_match:
                tp_num = int(tp_match.group())
                placements[ref] = (62.0 + tp_num * 4.0, 96.0, 0, "F.Cu")
        elif ref.startswith("LED"):
            led_match = re.search(r"\d+", ref)
            if led_match:
                led_num = int(led_match.group())
                placements[ref] = (102.0 + led_num * 3.0, 60.0, 0, "F.Cu")
        elif ref.startswith("SW"):
            sw_match = re.search(r"\d+", ref)
            if sw_match:
                sw_num = int(sw_match.group())
                placements[ref] = (102.0 + sw_num * 8.0, 56.0, 0, "F.Cu")
        else:
            w, h = estimate_footprint_size(comp["footprint"])
            result = zone_conn.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result

    return placements


# ---------------------------------------------------------------------------
# Footprint generation
# ---------------------------------------------------------------------------

def get_pad_info(fp_name, ref):
    """Return list of (pad_num, pad_type, shape, x, y, sx, sy, drill, layers)."""
    pads = []
    fp = fp_name or ""

    if any(p in fp for p in ["R_0402", "C_0402", "L_0402", "FerriteBead_0402"]):
        pads = [
            ("1", "smd", "roundrect", -0.48, 0, 0.56, 0.62, None, "F.Cu"),
            ("2", "smd", "roundrect", 0.48, 0, 0.56, 0.62, None, "F.Cu"),
        ]
    elif any(p in fp for p in ["R_0603", "C_0603", "LED_0603"]):
        pads = [
            ("1", "smd", "roundrect", -0.75, 0, 0.8, 0.95, None, "F.Cu"),
            ("2", "smd", "roundrect", 0.75, 0, 0.8, 0.95, None, "F.Cu"),
        ]
    elif any(p in fp for p in ["R_0805", "C_0805", "L_0805"]):
        pads = [
            ("1", "smd", "roundrect", -0.9, 0, 1.0, 1.45, None, "F.Cu"),
            ("2", "smd", "roundrect", 0.9, 0, 1.0, 1.45, None, "F.Cu"),
        ]
    elif any(p in fp for p in ["C_1206", "L_1210"]):
        pads = [
            ("1", "smd", "roundrect", -1.4, 0, 1.3, 1.8, None, "F.Cu"),
            ("2", "smd", "roundrect", 1.4, 0, 1.3, 1.8, None, "F.Cu"),
        ]
    elif "D_SMA" in fp:
        pads = [
            ("1", "smd", "rect", -2.0, 0, 1.5, 1.8, None, "F.Cu"),
            ("2", "smd", "rect", 2.0, 0, 1.5, 1.8, None, "F.Cu"),
        ]
    elif "TestPoint" in fp:
        pads = [("1", "smd", "rect", 0, 0, 1.5, 1.5, None, "F.Cu")]
    elif "BarrelJack" in fp:
        pads = [
            ("1", "thru_hole", "rect", 0, 0, 3.5, 3.5, 1.2, "*.Cu"),
            ("2", "thru_hole", "oval", 6.0, 0, 3.5, 3.5, 1.2, "*.Cu"),
            ("3", "thru_hole", "oval", 3.0, 4.7, 3.5, 3.5, 1.2, "*.Cu"),
        ]
    elif "SMA_Amphenol" in fp:
        pads = [
            ("1", "smd", "rect", 0, 0, 1.5, 1.5, None, "F.Cu"),
            ("2", "thru_hole", "circle", -2.5, -2.5, 2.0, 2.0, 1.0, "*.Cu"),
            ("2", "thru_hole", "circle", 2.5, -2.5, 2.0, 2.0, 1.0, "*.Cu"),
            ("2", "thru_hole", "circle", -2.5, 2.5, 2.0, 2.0, 1.0, "*.Cu"),
            ("2", "thru_hole", "circle", 2.5, 2.5, 2.0, 2.0, 1.0, "*.Cu"),
        ]
    elif "CP_Radial" in fp:
        pads = [
            ("1", "thru_hole", "rect", 0, 0, 1.8, 1.8, 0.8, "*.Cu"),
            ("2", "thru_hole", "circle", 3.5, 0, 1.8, 1.8, 0.8, "*.Cu"),
        ]
    elif "SOIC-8" in fp:
        for i in range(4):
            pads.append((str(i+1), "smd", "rect", -2.7, -1.905 + i * 1.27, 1.55, 0.6, None, "F.Cu"))
        for i in range(4):
            pads.append((str(8-i), "smd", "rect", 2.7, -1.905 + i * 1.27, 1.55, 0.6, None, "F.Cu"))
    elif "WSON-8_2x2" in fp:
        for i in range(4):
            pads.append((str(i+1), "smd", "rect", -0.9, -0.75 + i * 0.5, 0.65, 0.3, None, "F.Cu"))
        for i in range(4):
            pads.append((str(8-i), "smd", "rect", 0.9, -0.75 + i * 0.5, 0.65, 0.3, None, "F.Cu"))
        pads.append(("9", "smd", "rect", 0, 0, 0.84, 0.84, None, "F.Cu"))
    elif "SOT-23-5" in fp:
        pads = [
            ("1", "smd", "rect", -1.1, 0.95, 1.0, 0.6, None, "F.Cu"),
            ("2", "smd", "rect", -1.1, 0, 1.0, 0.6, None, "F.Cu"),
            ("3", "smd", "rect", -1.1, -0.95, 1.0, 0.6, None, "F.Cu"),
            ("4", "smd", "rect", 1.1, -0.95, 1.0, 0.6, None, "F.Cu"),
            ("5", "smd", "rect", 1.1, 0.95, 1.0, 0.6, None, "F.Cu"),
        ]
    elif "SOT-23" in fp:
        pads = [
            ("1", "smd", "rect", -1.1, 0.95, 1.0, 0.6, None, "F.Cu"),
            ("2", "smd", "rect", -1.1, -0.95, 1.0, 0.6, None, "F.Cu"),
            ("3", "smd", "rect", 1.1, 0, 1.0, 0.6, None, "F.Cu"),
        ]
    elif "QFN-16" in fp and "3x3" in fp:
        for i in range(4):
            pads.append((str(i+1), "smd", "rect", -1.45, -0.75 + i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+5), "smd", "rect", -0.75 + i * 0.5, 1.45, 0.3, 0.8, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+9), "smd", "rect", 1.45, 0.75 - i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+13), "smd", "rect", 0.75 - i * 0.5, -1.45, 0.3, 0.8, None, "F.Cu"))
        pads.append(("17", "smd", "rect", 0, 0, 1.75, 1.75, None, "F.Cu"))
    elif "QFN-24" in fp and "4x4" in fp:
        for i in range(6):
            pads.append((str(i+1), "smd", "rect", -1.95, -1.25 + i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(6):
            pads.append((str(i+7), "smd", "rect", -1.25 + i * 0.5, 1.95, 0.3, 0.8, None, "F.Cu"))
        for i in range(6):
            pads.append((str(i+13), "smd", "rect", 1.95, 1.25 - i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(6):
            pads.append((str(i+19), "smd", "rect", 1.25 - i * 0.5, -1.95, 0.3, 0.8, None, "F.Cu"))
        pads.append(("25", "smd", "rect", 0, 0, 2.65, 2.65, None, "F.Cu"))
    elif "QFN-32" in fp and "5x5" in fp:
        for i in range(8):
            pads.append((str(i+1), "smd", "rect", -2.45, -1.75 + i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(8):
            pads.append((str(i+9), "smd", "rect", -1.75 + i * 0.5, 2.45, 0.3, 0.8, None, "F.Cu"))
        for i in range(8):
            pads.append((str(i+17), "smd", "rect", 2.45, 1.75 - i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(8):
            pads.append((str(i+25), "smd", "rect", 1.75 - i * 0.5, -2.45, 0.3, 0.8, None, "F.Cu"))
        pads.append(("33", "smd", "rect", 0, 0, 3.1, 3.1, None, "F.Cu"))
    elif "QFN-48" in fp and "7x7" in fp:
        for i in range(12):
            pads.append((str(i+1), "smd", "rect", -3.45, -2.75 + i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(12):
            pads.append((str(i+13), "smd", "rect", -2.75 + i * 0.5, 3.45, 0.3, 0.8, None, "F.Cu"))
        for i in range(12):
            pads.append((str(i+25), "smd", "rect", 3.45, 2.75 - i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(12):
            pads.append((str(i+37), "smd", "rect", 2.75 - i * 0.5, -3.45, 0.3, 0.8, None, "F.Cu"))
        pads.append(("49", "smd", "rect", 0, 0, 5.15, 5.15, None, "F.Cu"))
    elif "WSON-8-1EP_6x5" in fp:
        for i in range(4):
            pads.append((str(i+1), "smd", "rect", -2.75, -1.905 + i * 1.27, 1.2, 0.6, None, "F.Cu"))
        for i in range(4):
            pads.append((str(8-i), "smd", "rect", 2.75, -1.905 + i * 1.27, 1.2, 0.6, None, "F.Cu"))
        pads.append(("9", "smd", "rect", 0, 0, 3.4, 4.0, None, "F.Cu"))
    elif "BGA-96" in fp:
        cols = "ABCDEFGHJ"
        for row in range(14):
            for ci, col in enumerate(cols):
                px = (ci - 4) * 0.8
                py = (row - 6.5) * 0.8
                pads.append((f"{col}{row+1}", "smd", "circle", px, py, 0.4, 0.4, None, "F.Cu"))
    elif "BGA-144" in fp:
        cols = "ABCDEFGHJKLM"
        for row in range(12):
            for ci, col in enumerate(cols):
                px = (ci - 5.5) * 0.8
                py = (row - 5.5) * 0.8
                pads.append((f"{col}{row+1}", "smd", "circle", px, py, 0.4, 0.4, None, "F.Cu"))
    elif "BGA-153" in fp:
        cols = "ABCDEFGHJKL"
        for row in range(14):
            for ci, col in enumerate(cols):
                px = (ci - 5) * 0.8
                py = (row - 6.5) * 0.8
                pads.append((f"{col}{row+1}", "smd", "circle", px, py, 0.45, 0.45, None, "F.Cu"))
    elif "VDFN-4" in fp:
        pads = [
            ("1", "smd", "rect", -0.55, -0.325, 0.85, 0.42, None, "F.Cu"),
            ("2", "smd", "rect", 0.55, -0.325, 0.85, 0.42, None, "F.Cu"),
            ("3", "smd", "rect", 0.55, 0.325, 0.85, 0.42, None, "F.Cu"),
            ("4", "smd", "rect", -0.55, 0.325, 0.85, 0.42, None, "F.Cu"),
        ]
    elif "Crystal_SMD_3215" in fp:
        pads = [
            ("1", "smd", "rect", -1.2, 0, 1.0, 1.3, None, "F.Cu"),
            ("2", "smd", "rect", 1.2, 0, 1.0, 1.3, None, "F.Cu"),
        ]
    elif "DIP-14" in fp:
        for i in range(7):
            pads.append((str(i+1), "thru_hole", "rect" if i == 0 else "oval",
                        -3.81, -7.62 + i * 2.54, 1.6, 1.6, 0.8, "*.Cu"))
            pads.append((str(14-i), "thru_hole", "oval",
                        3.81, -7.62 + i * 2.54, 1.6, 1.6, 0.8, "*.Cu"))
    elif "PinHeader_2x07_P1.27" in fp:
        for row in range(7):
            for col in range(2):
                pin = row * 2 + col + 1
                pads.append((str(pin), "thru_hole", "rect" if pin == 1 else "oval",
                            col * 1.27, row * 1.27, 0.85, 0.85, 0.5, "*.Cu"))
    elif "PinHeader_2x20_P2.54" in fp:
        for row in range(20):
            for col in range(2):
                pin = row * 2 + col + 1
                pads.append((str(pin), "thru_hole", "rect" if pin == 1 else "oval",
                            col * 2.54, row * 2.54, 1.7, 1.7, 1.0, "*.Cu"))
    elif "USB_A" in fp:
        pads = [
            ("1", "thru_hole", "rect", 0, 0, 1.5, 1.5, 0.8, "*.Cu"),
            ("2", "thru_hole", "oval", 2.5, 0, 1.5, 1.5, 0.8, "*.Cu"),
            ("3", "thru_hole", "oval", 5.0, 0, 1.5, 1.5, 0.8, "*.Cu"),
            ("4", "thru_hole", "oval", 7.5, 0, 1.5, 1.5, 0.8, "*.Cu"),
            ("S1", "thru_hole", "oval", -1.25, 3.5, 2.5, 2.5, 1.4, "*.Cu"),
            ("S2", "thru_hole", "oval", 8.75, 3.5, 2.5, 2.5, 1.4, "*.Cu"),
        ]
    elif "USB_Micro" in fp:
        for i in range(5):
            pads.append((str(i+1), "smd", "rect", -1.3 + i * 0.65, 0, 0.4, 1.35, None, "F.Cu"))
        pads.append(("S1", "smd", "rect", -3.1, 1.8, 1.6, 1.5, None, "F.Cu"))
        pads.append(("S2", "smd", "rect", 3.1, 1.8, 1.6, 1.5, None, "F.Cu"))
    elif "RJ45" in fp:
        for i in range(8):
            pads.append((str(i+1), "thru_hole", "oval",
                        -4.445 + i * 1.27, 0, 1.1, 1.1, 0.65, "*.Cu"))
        pads.append(("S1", "thru_hole", "oval", -6.35, 6.35, 2.3, 2.3, 1.6, "*.Cu"))
        pads.append(("S2", "thru_hole", "oval", 6.35, 6.35, 2.3, 2.3, 1.6, "*.Cu"))
    elif "U.FL" in fp:
        pads = [
            ("1", "smd", "rect", 0, 0, 1.0, 1.0, None, "F.Cu"),
            ("2", "smd", "rect", -1.3, 0, 0.9, 2.0, None, "F.Cu"),
            ("2", "smd", "rect", 1.3, 0, 0.9, 2.0, None, "F.Cu"),
        ]
    elif "microSD" in fp:
        for i in range(8):
            pads.append((str(i+1), "smd", "rect", -3.85 + i * 1.1, 0, 0.7, 1.6, None, "F.Cu"))
        pads.append(("S1", "smd", "rect", -6.85, 5.5, 1.2, 2.5, None, "F.Cu"))
        pads.append(("S2", "smd", "rect", 6.85, 5.5, 1.2, 2.5, None, "F.Cu"))
    elif "LCC-16" in fp:
        for i in range(4):
            pads.append((str(i+1), "smd", "rect", -5.5, -2.25 + i * 1.5, 1.0, 0.8, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+5), "smd", "rect", -2.25 + i * 1.5, 7.5, 0.8, 1.0, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+9), "smd", "rect", 5.5, 2.25 - i * 1.5, 1.0, 0.8, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+13), "smd", "rect", 2.25 - i * 1.5, -7.5, 0.8, 1.0, None, "F.Cu"))
    elif "TGA2594" in fp:
        for i in range(4):
            pads.append((str(i+1), "smd", "rect", -2.25, -0.75 + i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+5), "smd", "rect", -0.75 + i * 0.5, 2.25, 0.3, 0.8, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+9), "smd", "rect", 2.25, 0.75 - i * 0.5, 0.8, 0.3, None, "F.Cu"))
        for i in range(4):
            pads.append((str(i+13), "smd", "rect", 0.75 - i * 0.5, -2.25, 0.3, 0.8, None, "F.Cu"))
        pads.append(("17", "smd", "rect", 0, 0, 2.5, 2.5, None, "F.Cu"))
    elif "SW_SPST" in fp or "SW_Push" in fp:
        pads = [
            ("1", "smd", "rect", -1.7, 0, 0.8, 1.0, None, "F.Cu"),
            ("2", "smd", "rect", 1.7, 0, 0.8, 1.0, None, "F.Cu"),
        ]
    elif "SW_DIP" in fp:
        for i in range(2):
            pads.append((str(i+1), "thru_hole", "rect" if i == 0 else "oval",
                        0, i * 2.54, 1.6, 1.6, 0.8, "*.Cu"))
            pads.append((str(4-i), "thru_hole", "oval",
                        7.62, i * 2.54, 1.6, 1.6, 0.8, "*.Cu"))
    else:
        # Zynq BGA-900 or SAW filter or generic
        if ref == "U1":
            for row in range(30):
                for col in range(30):
                    px = (col - 14.5) * 1.0
                    py = (row - 14.5) * 1.0
                    pads.append((str(row * 30 + col + 1), "smd", "circle",
                                px, py, 0.5, 0.5, None, "F.Cu"))
        elif ref and ref.startswith("FL"):
            pads = [
                ("1", "smd", "rect", -2.0, 0, 1.0, 1.5, None, "F.Cu"),
                ("2", "smd", "rect", 2.0, 0, 1.0, 1.5, None, "F.Cu"),
                ("3", "smd", "rect", 0, -1.5, 3.0, 1.0, None, "F.Cu"),
            ]
        else:
            pads = [
                ("1", "smd", "rect", -0.5, 0, 0.6, 0.6, None, "F.Cu"),
                ("2", "smd", "rect", 0.5, 0, 0.6, 0.6, None, "F.Cu"),
            ]

    return pads


def generate_footprint(comp, x, y, rotation, layer):
    """Generate a KiCad PCB footprint S-expression."""
    ref = comp["reference"]
    val = comp["value"]
    fp = comp["footprint"]
    fp_uuid = uid()

    fp_lib_name = fp if fp else f"cirradio:{ref}"
    rot_str = f" {rotation}" if rotation else ""
    at_str = f"(at {x:.2f} {y:.2f}{rot_str})"

    if layer == "B.Cu":
        silk_layer = "B.SilkS"
        fab_layer = "B.Fab"
        crtyd_layer = "B.CrtYd"
    else:
        silk_layer = "F.SilkS"
        fab_layer = "F.Fab"
        crtyd_layer = "F.CrtYd"

    lines = []
    lines.append(f'  (footprint "{fp_lib_name}"')
    lines.append(f'    (layer "{layer}")')
    lines.append(f'    (uuid "{fp_uuid}")')
    lines.append(f'    {at_str}')

    ref_uuid = uid()
    lines.append(f'    (property "Reference" "{ref}" (at 0 -2 0) (layer "{silk_layer}") (uuid "{ref_uuid}")')
    lines.append(f'      (effects (font (size 0.8 0.8) (thickness 0.12)))')
    lines.append(f'    )')

    val_uuid = uid()
    lines.append(f'    (property "Value" "{val}" (at 0 2 0) (layer "{fab_layer}") (uuid "{val_uuid}")')
    lines.append(f'      (effects (font (size 0.8 0.8) (thickness 0.12)))')
    lines.append(f'    )')

    # Courtyard
    cw, ch = estimate_footprint_size(fp)
    cx = cw / 2.0 + 0.25
    cy = ch / 2.0 + 0.25
    lines.append(f'    (fp_rect')
    lines.append(f'      (start {-cx:.3f} {-cy:.3f}) (end {cx:.3f} {cy:.3f})')
    lines.append(f'      (stroke (width 0.05) (type solid)) (fill none) (layer "{crtyd_layer}") (uuid "{uid()}")')
    lines.append(f'    )')

    # Fab outline
    fx = cw / 2.0
    fy = ch / 2.0
    lines.append(f'    (fp_rect')
    lines.append(f'      (start {-fx:.3f} {-fy:.3f}) (end {fx:.3f} {fy:.3f})')
    lines.append(f'      (stroke (width 0.1) (type solid)) (fill none) (layer "{fab_layer}") (uuid "{uid()}")')
    lines.append(f'    )')

    # Pads
    pad_infos = get_pad_info(fp, ref)
    for pad_num, pad_type, shape, px, py, sx, sy, drill, pad_layers in pad_infos:
        pad_uuid = uid()
        if pad_type == "thru_hole":
            drill_str = f" (drill {drill})" if drill else ""
            lines.append(f'    (pad "{pad_num}" {pad_type} {shape}')
            lines.append(f'      (at {px:.3f} {py:.3f}) (size {sx:.3f} {sy:.3f}){drill_str}')
            lines.append(f'      (layers "{pad_layers}" "*.Mask")')
            lines.append(f'      (uuid "{pad_uuid}")')
            lines.append(f'    )')
        else:
            paste = layer.replace("Cu", "Paste")
            mask = layer.replace("Cu", "Mask")
            lines.append(f'    (pad "{pad_num}" smd {shape}')
            lines.append(f'      (at {px:.3f} {py:.3f}) (size {sx:.3f} {sy:.3f})')
            lines.append(f'      (layers "{layer}" "{paste}" "{mask}")')
            lines.append(f'      (uuid "{pad_uuid}")')
            lines.append(f'    )')

    lines.append(f'  )')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("CIRRADIO Dev Board - Component Placement Generator")
    print("=" * 55)

    components_by_zone = defaultdict(list)
    all_components = {}

    print("\nParsing schematic files...")
    for sch_file in SCHEMATIC_FILES:
        filepath = os.path.join(SCRIPT_DIR, sch_file)
        if not os.path.exists(filepath):
            print(f"  WARNING: {sch_file} not found, skipping")
            continue
        components = parse_schematic(filepath)
        zone = SCHEMATIC_ZONE[sch_file]
        print(f"  {sch_file}: {len(components)} components -> zone '{zone}'")
        for comp in components:
            ref = comp["reference"]
            if ref not in all_components:
                all_components[ref] = comp
                components_by_zone[zone].append(comp)

    total = len(all_components)
    print(f"\nTotal unique components: {total}")

    print("\nCalculating placement positions...")
    placements = build_placement_plan(components_by_zone)
    placed = len(placements)
    print(f"  Placed: {placed}/{total} components")

    # Handle unplaced components with overflow zone
    overflow_zone = Zone("Overflow", 2, 42, 40, 60)
    for ref, comp in all_components.items():
        if ref not in placements:
            w, h = estimate_footprint_size(comp["footprint"])
            result = overflow_zone.place(ref, comp["footprint"], w, h)
            if result:
                placements[ref] = result
            else:
                placements[ref] = (5.0, 50.0, 0, "F.Cu")

    # Read existing PCB file
    pcb_path = os.path.join(SCRIPT_DIR, "cirradio-devboard.kicad_pcb")
    print(f"\nReading {pcb_path}...")
    with open(pcb_path, "r") as f:
        pcb_content = f.read()

    # Strip existing component footprints (keep mounting holes)
    pcb_lines = pcb_content.split("\n")
    output_lines = []
    in_footprint = False
    fp_depth = 0
    fp_buf = []
    mounting_hole_fps = []

    i = 0
    while i < len(pcb_lines):
        line = pcb_lines[i]
        stripped = line.strip()

        if stripped.startswith('(footprint ') and not in_footprint:
            in_footprint = True
            fp_buf = [line]
            fp_depth = line.count('(') - line.count(')')
            i += 1
            continue

        if in_footprint:
            fp_buf.append(line)
            fp_depth += line.count('(') - line.count(')')
            if fp_depth <= 0:
                fp_text = "\n".join(fp_buf)
                if "MountingHole" in fp_text:
                    mounting_hole_fps.append(fp_text)
                in_footprint = False
                fp_buf = []
            i += 1
            continue

        output_lines.append(line)
        i += 1

    # Remove trailing closing paren and blanks
    while output_lines and output_lines[-1].strip() in ("", ")"):
        last = output_lines.pop()
        if last.strip() == ")":
            break

    # Re-add mounting holes
    output_lines.append("")
    output_lines.append("  ;; ===== MOUNTING HOLES =====")
    for mh_fp in mounting_hole_fps:
        output_lines.append(mh_fp)

    # Add component footprints grouped by zone
    output_lines.append("")
    output_lines.append("  ;; ===== COMPONENT PLACEMENT =====")
    output_lines.append(f"  ;; Generated by gen_pcb_placement.py")
    output_lines.append(f"  ;; {len(placements)} components placed")
    output_lines.append("")

    # Group by zone for readable output
    zone_assignments = defaultdict(list)
    for ref in sorted(placements.keys()):
        x, y, rot, layer = placements[ref]
        if x < 60 and y < 40:
            z = "RF Front-End"
        elif 60 <= x < 100 and y < 32:
            z = "AD9361"
        elif 40 <= x < 100 and 32 <= y < 80:
            z = "Zynq"
        elif 100 <= x and y < 62:
            z = "DDR3L / Peripherals-Top"
        elif x < 60 and y >= 60:
            z = "Power"
        elif x >= 140 and y < 30:
            z = "GPS"
        else:
            z = "Connectors / Peripherals"
        zone_assignments[z].append(ref)

    zone_order = [
        "RF Front-End", "AD9361", "Zynq", "DDR3L / Peripherals-Top",
        "Power", "GPS", "Connectors / Peripherals"
    ]

    for zone_name in zone_order:
        refs = zone_assignments.get(zone_name, [])
        if not refs:
            continue
        output_lines.append(f"  ;; --- {zone_name} ({len(refs)} components) ---")
        for ref in sorted(refs):
            comp = all_components[ref]
            x, y, rot, layer = placements[ref]
            fp_text = generate_footprint(comp, x, y, rot, layer)
            output_lines.append(fp_text)
        output_lines.append("")

    output_lines.append(")")
    output_lines.append("")

    pcb_output = "\n".join(output_lines)
    with open(pcb_path, "w") as f:
        f.write(pcb_output)

    print(f"Wrote {pcb_path}")
    print(f"  Total footprints: {len(placements)} + {len(mounting_hole_fps)} mounting holes")

    # Summary
    print("\n=== PLACEMENT SUMMARY ===")
    for zone_name in zone_order:
        refs = zone_assignments.get(zone_name, [])
        if refs:
            ics = [r for r in refs if all_components[r]["reference"].startswith("U")]
            passives = [r for r in refs if is_passive(all_components[r])]
            others = [r for r in refs if r not in ics and r not in passives]
            print(f"  {zone_name}: {len(refs)} total "
                  f"({len(ics)} ICs, {len(passives)} passives, {len(others)} other)")

    fcu = sum(1 for _, _, _, l in placements.values() if l == "F.Cu")
    bcu = sum(1 for _, _, _, l in placements.values() if l == "B.Cu")
    print(f"\n  F.Cu components: {fcu}")
    print(f"  B.Cu components: {bcu}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
