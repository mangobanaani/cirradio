#!/usr/bin/env python3
"""Generate copper zone fills for ground and power planes.

Reads the existing cirradio-devboard.kicad_pcb and adds zone fills for:
- 3 solid GND planes on In1.Cu, In3.Cu, In7.Cu
- Split power plane on In5.Cu (+1V0, +1V35, +1V5, +1V8, +3V3, +5V)
- GND flood fills on F.Cu and B.Cu

Board: 160x100mm, 10-layer stackup.
"""

import os
import re
import uuid
import sys


def gen_uuid():
    return str(uuid.uuid4())


def zone_sexpr(net_num, net_name, layer, zone_name, polygons,
               priority=0, clearance=0.2,
               thermal_gap=0.3, thermal_bridge_width=0.3,
               min_thickness=0.2):
    """Generate a KiCad zone S-expression.

    Args:
        net_num: Net number from the netlist
        net_name: Net name string (e.g. "GND")
        layer: Copper layer name (e.g. "In1.Cu")
        zone_name: Human-readable zone name
        polygons: List of polygon point lists, each is [(x1,y1), (x2,y2), ...]
        priority: Zone fill priority (higher = fills first)
        clearance: Pad-to-zone clearance in mm
        thermal_gap: Thermal relief gap in mm
        thermal_bridge_width: Thermal relief spoke width in mm
        min_thickness: Minimum copper thickness in mm

    Returns:
        String with the zone S-expression.
    """
    zones = []
    for pts in polygons:
        uid = gen_uuid()
        pts_str = " ".join(f"(xy {x} {y})" for x, y in pts)

        priority_line = ""
        if priority > 0:
            priority_line = f"\n    (priority {priority})"

        zone = f"""  (zone
    (net {net_num})
    (net_name "{net_name}")
    (layer "{layer}")
    (uuid "{uid}")
    (name "{zone_name}"){priority_line}
    (hatch edge 0.5)
    (connect_pads
      (clearance {clearance})
    )
    (min_thickness {min_thickness})
    (filled_areas_thickness no)
    (fill yes
      (thermal_gap {thermal_gap})
      (thermal_bridge_width {thermal_bridge_width})
    )
    (polygon
      (pts
        {pts_str}
      )
    )
  )"""
        zones.append(zone)
    return "\n".join(zones)


# Board extents
BW = 160.0  # board width mm
BH = 100.0  # board height mm

# Full board polygon (with small margin for edge clearance)
FULL_BOARD = [(0, 0), (BW, 0), (BW, BH), (0, BH)]


def generate_all_zones():
    """Generate all zone definitions and return as a string."""
    sections = []

    sections.append("\n  ;; ===== GROUND PLANES =====")

    # --- Solid GND planes on inner layers ---
    for layer, name in [("In1.Cu", "GND1"), ("In3.Cu", "GND2"), ("In7.Cu", "GND3")]:
        sections.append(zone_sexpr(
            net_num=1, net_name="GND", layer=layer,
            zone_name=name, polygons=[FULL_BOARD],
            priority=0, clearance=0.2
        ))

    sections.append("\n  ;; ===== POWER PLANE (In5.Cu) - SPLIT REGIONS =====")

    # --- Power plane splits on In5.Cu ---
    # +1V0: Zynq VCCINT, center area
    sections.append(zone_sexpr(
        net_num=3, net_name="+1V0", layer="In5.Cu",
        zone_name="PWR_1V0",
        polygons=[[(30, 30), (130, 30), (130, 70), (30, 70)]],
        priority=1, clearance=0.15
    ))

    # +1V35: DDR3L area
    sections.append(zone_sexpr(
        net_num=6, net_name="+1V35", layer="In5.Cu",
        zone_name="PWR_1V35",
        polygons=[[(100, 20), (145, 20), (145, 60), (100, 60)]],
        priority=1, clearance=0.15
    ))

    # +1V5: Near Zynq VCCAUX
    sections.append(zone_sexpr(
        net_num=10, net_name="+1V5", layer="In5.Cu",
        zone_name="PWR_1V5",
        polygons=[[(55, 30), (75, 30), (75, 50), (55, 50)]],
        priority=1, clearance=0.15
    ))

    # +1V8: AD9361 area and general (two polygons)
    sections.append(zone_sexpr(
        net_num=13, net_name="+1V8", layer="In5.Cu",
        zone_name="PWR_1V8",
        polygons=[
            [(60, 0), (100, 0), (100, 35), (60, 35)],
            [(40, 30), (60, 30), (60, 60), (40, 60)],
        ],
        priority=1, clearance=0.15
    ))

    # +3V3: Peripherals area + top-right (two polygons)
    sections.append(zone_sexpr(
        net_num=16, net_name="+3V3", layer="In5.Cu",
        zone_name="PWR_3V3",
        polygons=[
            [(100, 60), (160, 60), (160, 100), (100, 100)],
            [(135, 0), (160, 0), (160, 30), (135, 30)],
        ],
        priority=1, clearance=0.15
    ))

    # +5V: PA area only
    sections.append(zone_sexpr(
        net_num=20, net_name="+5V", layer="In5.Cu",
        zone_name="PWR_5V",
        polygons=[[(0, 15), (25, 15), (25, 35), (0, 35)]],
        priority=1, clearance=0.15
    ))

    sections.append("\n  ;; ===== GROUND FLOOD FILLS (F.Cu and B.Cu) =====")

    # --- Ground flood fills on outer layers ---
    sections.append(zone_sexpr(
        net_num=1, net_name="GND", layer="F.Cu",
        zone_name="GND_TOP",
        polygons=[FULL_BOARD],
        priority=0, clearance=0.2
    ))

    sections.append(zone_sexpr(
        net_num=1, net_name="GND", layer="B.Cu",
        zone_name="GND_BOT",
        polygons=[FULL_BOARD],
        priority=0, clearance=0.2
    ))

    return "\n".join(sections) + "\n"


def main():
    pcb_dir = os.path.dirname(os.path.abspath(__file__))
    pcb_path = os.path.join(pcb_dir, "cirradio-devboard.kicad_pcb")

    if not os.path.exists(pcb_path):
        print(f"ERROR: PCB file not found: {pcb_path}", file=sys.stderr)
        sys.exit(1)

    with open(pcb_path, "r") as f:
        content = f.read()

    # Check if zones already exist
    if "(zone" in content:
        print("WARNING: Zones already present in PCB file. Removing existing zones first.")
        # Remove existing zone blocks (greedy match each zone block)
        content = re.sub(
            r'\n  ;; ===== GROUND PLANES =====.*?;; ===== GROUND FLOOD FILLS \(F\.Cu and B\.Cu\) =====.*?\n  \)\n',
            '\n',
            content,
            flags=re.DOTALL
        )
        # Also try individual zone removal as fallback
        content = re.sub(r'\s*\(zone\s.*?\n  \)', '', content, flags=re.DOTALL)

    # Find insertion point: before the first (footprint line
    match = re.search(r'^  \(footprint ', content, re.MULTILINE)
    if match:
        insert_pos = match.start()
        # Find the preceding comment block for mounting holes
        # Look for the comment lines before footprints
        preceding = content[:insert_pos]
        # Insert zones before the mounting holes comment
        mh_comment = preceding.rfind(";; Mounting holes")
        if mh_comment >= 0:
            insert_pos = mh_comment
            # Back up to the newline before the comment
            while insert_pos > 0 and content[insert_pos - 1] in ('\n', '\r'):
                insert_pos -= 1
            insert_pos += 1  # keep one newline
        zones_text = generate_all_zones()
        new_content = content[:insert_pos] + "\n" + zones_text + "\n" + content[insert_pos:]
    else:
        # No footprints found; insert before the final closing paren
        last_paren = content.rfind(")")
        zones_text = generate_all_zones()
        new_content = content[:last_paren] + "\n" + zones_text + "\n" + content[last_paren:]

    with open(pcb_path, "w") as f:
        f.write(new_content)

    # Count zones added
    zone_count = new_content.count("(zone")
    print(f"Successfully added {zone_count} copper zones to {pcb_path}")
    print("Zones added:")
    print("  - In1.Cu: GND1 (solid ground plane)")
    print("  - In3.Cu: GND2 (solid ground plane)")
    print("  - In7.Cu: GND3 (solid ground plane)")
    print("  - In5.Cu: +1V0 (Zynq VCCINT)")
    print("  - In5.Cu: +1V35 (DDR3L)")
    print("  - In5.Cu: +1V5 (Zynq VCCAUX)")
    print("  - In5.Cu: +1V8 (AD9361, 2 polygons)")
    print("  - In5.Cu: +3V3 (Peripherals, 2 polygons)")
    print("  - In5.Cu: +5V (PA area)")
    print("  - F.Cu: GND_TOP (ground flood fill)")
    print("  - B.Cu: GND_BOT (ground flood fill)")


if __name__ == "__main__":
    main()
