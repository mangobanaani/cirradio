#!/usr/bin/env python3
"""Generate PCB netlist import for CIRRADIO dev board.

Parses all 7 sub-schematic files to extract:
- All component instances (reference, value, footprint)
- All net names (from global labels, hierarchical labels, local labels, power symbols)

Generates an updated cirradio-devboard.kicad_pcb with:
- All nets declared
- Net class assignments (Power, Power_Wide, RF_50ohm, LVDS, DDR3, DDR3_DiffPair)
- 4x M3 mounting holes at board corners
- Component summary in comments
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


def uid():
    return str(uuid.uuid4())


def parse_schematic(filepath):
    """Parse a KiCad schematic file and extract components and net names."""
    with open(filepath, "r") as f:
        content = f.read()

    components = []
    nets = set()

    # Extract component instances (symbol with lib_id, not inside lib_symbols)
    # We need to find symbols that are instances, not library definitions.
    # Instance symbols appear after the lib_symbols section and have properties
    # like Reference, Value, Footprint with actual values.

    # Find where lib_symbols ends
    lib_sym_depth = 0
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

    # Work with content after lib_symbols
    body = content[lib_sym_end:] if lib_sym_end > 0 else content

    # Extract symbol instances with lib_id
    # Pattern: (symbol (lib_id "...") ... (property "Reference" "R1" ...) (property "Value" "10k" ...) (property "Footprint" "..." ...) ...)
    sym_pattern = re.compile(
        r'\(symbol\s+\(lib_id\s+"([^"]+)"\)\s+\(at\s+[\d.\-e ]+ \d+\)'
    )

    for m in sym_pattern.finditer(body):
        lib_id = m.group(1)
        start = m.start()

        # Find the matching closing paren for this symbol
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

        # Extract properties
        ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', sym_block)
        val_m = re.search(r'\(property\s+"Value"\s+"([^"]+)"', sym_block)
        fp_m = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', sym_block)

        ref = ref_m.group(1) if ref_m else ""
        val = val_m.group(1) if val_m else ""
        fp = fp_m.group(1) if fp_m else ""

        # Skip power symbols and PWR_FLAG (they are virtual, no footprint)
        if lib_id.startswith("power:"):
            # But extract power net names from their Value
            if val and val != "PWR_FLAG":
                nets.add(val)
            continue

        # Skip symbols with # prefix references (power symbols, flags)
        if ref.startswith("#"):
            continue

        components.append({
            "reference": ref,
            "value": val,
            "footprint": fp,
            "lib_id": lib_id,
        })

    # Extract global labels -> nets
    for m in re.finditer(r'\(global_label\s+"([^"]+)"', body):
        nets.add(m.group(1))

    # Extract hierarchical labels -> nets
    for m in re.finditer(r'\(hierarchical_label\s+"([^"]+)"', body):
        nets.add(m.group(1))

    # Extract local net labels -> nets
    for m in re.finditer(r'\(label\s+"([^"]+)"', body):
        nets.add(m.group(1))

    return components, nets


def classify_net(name):
    """Classify a net into a net class."""
    # Power_Wide: main input power
    if name in ("+12V", "+12V_IN"):
        return "Power_Wide"

    # Power nets
    power_nets = {
        "+5V", "+3V3", "+3V3A", "+1V8", "+1V5", "+1V35", "+1V0",
        "VTT", "VTTREF", "+5V_PA", "+1V3_AD",
    }
    if name in power_nets:
        return "Power"

    # DDR3 differential pairs (CK and DQS pairs)
    if re.match(r"DDR_(CK|DQS)\d*[_]?[PN]?$", name):
        return "DDR3_DiffPair"

    # DDR3 signals
    if re.match(r"DDR_(DQ|A|BA|CK|DM|DQS|RAS|CAS|WE|CS|CKE|ODT|RESET)", name):
        return "DDR3"

    # LVDS pairs (AD9361 digital interface)
    lvds_prefixes = (
        "P0_D", "P1_D",
        "DATA_CLK_P", "DATA_CLK_N",
        "FB_CLK_P", "FB_CLK_N",
        "RX_FRAME_P", "RX_FRAME_N",
        "TX_FRAME_P", "TX_FRAME_N",
    )
    for prefix in lvds_prefixes:
        if name.startswith(prefix):
            return "LVDS"

    # RF traces (between AD9361 and RF front-end)
    rf_nets = {
        "AD_RX1A_P", "AD_RX1A_N", "AD_TX1A",
        "AD_RX1B_P", "AD_RX1B_N", "AD_TX1B",
        "AD_RX2A_P", "AD_RX2A_N", "AD_TX2A",
    }
    if name in rf_nets:
        return "RF_50ohm"

    return "Default"


def generate_mounting_hole(ref, x, y):
    """Generate a full M3 mounting hole footprint definition."""
    fp_uuid = uid()
    pad_uuid = uid()
    crtyd_uuid = uid()
    fab_uuid = uid()
    silk_uuid = uid()
    ref_uuid = uid()
    val_uuid = uid()

    return f"""  (footprint "MountingHole:MountingHole_3.2mm_M3_Pad"
    (layer "F.Cu")
    (uuid "{fp_uuid}")
    (at {x} {y})
    (property "Reference" "{ref}" (at 0 -4.2 0) (layer "F.SilkS") (uuid "{ref_uuid}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (property "Value" "MountingHole_3.2mm_M3_Pad" (at 0 4.2 0) (layer "F.Fab") (uuid "{val_uuid}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr exclude_from_pos_files)
    (fp_circle
      (center 0 0) (end 3.2 0)
      (stroke (width 0.15) (type solid)) (fill none) (layer "F.CrtYd") (uuid "{crtyd_uuid}")
    )
    (fp_circle
      (center 0 0) (end 3.0 0)
      (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab") (uuid "{fab_uuid}")
    )
    (pad "1" thru_hole circle
      (at 0 0) (size 6.0 6.0) (drill 3.2)
      (layers "*.Cu" "*.Mask")
      (uuid "{pad_uuid}")
    )
  )"""


def generate_pcb(all_components, all_nets):
    """Generate the complete .kicad_pcb file."""

    # Sort nets alphabetically, GND first
    net_names = sorted(all_nets - {"GND"})
    net_names = ["GND"] + net_names

    # Assign net numbers (0 = unconnected, 1+ = real nets)
    net_map = {}
    for i, name in enumerate(net_names):
        net_map[name] = i + 1  # net 0 is "" (unconnected)

    # Classify nets
    net_classes = defaultdict(list)
    for name in net_names:
        cls = classify_net(name)
        if cls != "Default":
            net_classes[cls].append(name)

    # Component statistics
    comp_by_type = defaultdict(int)
    for c in all_components:
        ref = c["reference"]
        # Extract prefix (letter part)
        prefix = re.match(r"([A-Za-z]+)", ref)
        if prefix:
            comp_by_type[prefix.group(1)] += 1

    # Count by category
    ic_count = comp_by_type.get("U", 0)
    cap_count = comp_by_type.get("C", 0)
    res_count = comp_by_type.get("R", 0)
    ind_count = comp_by_type.get("L", 0)
    diode_count = comp_by_type.get("D", 0)
    led_count = 0  # LEDs use D prefix too in our schematic; count by value
    conn_count = comp_by_type.get("J", 0)
    xtal_count = comp_by_type.get("Y", 0)
    fb_count = comp_by_type.get("FB", 0)
    tp_count = comp_by_type.get("TP", 0)
    sw_count = comp_by_type.get("SW", 0)

    # Count LEDs from diodes with LED in lib_id or value
    for c in all_components:
        if "LED" in c.get("lib_id", "") or "LED" in c.get("value", ""):
            led_count += 1

    total_components = len(all_components)
    total_nets = len(net_names)

    lines = []
    def emit(s):
        lines.append(s)

    emit("(kicad_pcb")
    emit('  (version 20231014)')
    emit('  (generator "gen_pcb_netlist")')
    emit('  (generator_version "9.0")')
    emit("  (general")
    emit("    (thickness 1.6)")
    emit("    (legacy_teardrops no)")
    emit("  )")
    emit('  (paper "A3")')
    emit("  (title_block")
    emit('    (title "CIRRADIO Dev Board")')
    emit('    (date "2026-03-03")')
    emit('    (rev "1.0")')
    emit('    (comment 1 "Tactical SDR Development Board")')
    emit('    (comment 2 "Zynq-7045 + AD9361")')
    emit(f'    (comment 3 "{total_components} components, {total_nets} nets")')
    emit("  )")

    # Layers
    emit("  (layers")
    emit('    (0 "F.Cu" signal)')
    emit('    (1 "In1.Cu" signal "GND1")')
    emit('    (2 "In2.Cu" signal "SIG1")')
    emit('    (3 "In3.Cu" signal "GND2")')
    emit('    (4 "In4.Cu" signal "SIG2")')
    emit('    (5 "In5.Cu" signal "PWR")')
    emit('    (6 "In6.Cu" signal "SIG3")')
    emit('    (7 "In7.Cu" signal "GND3")')
    emit('    (8 "In8.Cu" signal "SIG4")')
    emit('    (31 "B.Cu" signal)')
    emit('    (32 "B.Adhes" user "B.Adhesive")')
    emit('    (33 "F.Adhes" user "F.Adhesive")')
    emit('    (34 "B.Paste" user)')
    emit('    (35 "F.Paste" user)')
    emit('    (36 "B.SilkS" user "B.Silkscreen")')
    emit('    (37 "F.SilkS" user "F.Silkscreen")')
    emit('    (38 "B.Mask" user "B.Mask")')
    emit('    (39 "F.Mask" user "F.Mask")')
    emit('    (40 "Dwgs.User" user "User.Drawings")')
    emit('    (41 "Cmts.User" user "User.Comments")')
    emit('    (42 "Eco1.User" user "User.Eco1")')
    emit('    (43 "Eco2.User" user "User.Eco2")')
    emit('    (44 "Edge.Cuts" user)')
    emit('    (45 "Margin" user)')
    emit('    (46 "B.CrtYd" user "B.Courtyard")')
    emit('    (47 "F.CrtYd" user "F.Courtyard")')
    emit('    (48 "B.Fab" user "B.Fab")')
    emit('    (49 "F.Fab" user "F.Fab")')
    emit("  )")

    # Setup (preserved from original)
    emit("  (setup")
    emit("    (pad_to_mask_clearance 0)")
    emit("    (allow_soldermask_bridges_in_footprints no)")
    emit("    (stackup")
    emit('      (layer "F.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 1" (type "prepreg") (thickness 0.1) (epsilon_r 4.2))')
    emit('      (layer "In1.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 2" (type "core") (thickness 0.2) (epsilon_r 4.5))')
    emit('      (layer "In2.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 3" (type "prepreg") (thickness 0.1) (epsilon_r 4.2))')
    emit('      (layer "In3.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 4" (type "core") (thickness 0.2) (epsilon_r 4.5))')
    emit('      (layer "In4.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 5" (type "prepreg") (thickness 0.1) (epsilon_r 4.2))')
    emit('      (layer "In5.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 6" (type "core") (thickness 0.2) (epsilon_r 4.5))')
    emit('      (layer "In6.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 7" (type "prepreg") (thickness 0.1) (epsilon_r 4.2))')
    emit('      (layer "In7.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 8" (type "core") (thickness 0.2) (epsilon_r 4.5))')
    emit('      (layer "In8.Cu" (type "copper") (thickness 0.035))')
    emit('      (layer "dielectric 9" (type "prepreg") (thickness 0.1) (epsilon_r 4.2))')
    emit('      (layer "B.Cu" (type "copper") (thickness 0.035))')
    emit('      (copper_finish "ENIG")')
    emit("      (dielectric_constraints yes)")
    emit("    )")
    emit("    (pcbplotparams")
    emit("      (layerselection 0x00010fc_ffffffff)")
    emit("      (plot_on_all_layers_selection 0x0000000_00000000)")
    emit("      (disableapertmacros no)")
    emit("      (usegerberextensions yes)")
    emit("      (usegerberattributes yes)")
    emit("      (usegerberadvancedattributes yes)")
    emit("      (creategerberjobfile yes)")
    emit("      (dashed_line_dash_ratio 12.000000)")
    emit("      (dashed_line_gap_ratio 3.000000)")
    emit("      (svgprecision 4)")
    emit("      (plotframeref no)")
    emit("      (viasonmask no)")
    emit("      (mode 1)")
    emit("      (useauxorigin no)")
    emit("      (hpglpennumber 1)")
    emit("      (hpglpenspeed 20)")
    emit("      (hpglpendiameter 15.000000)")
    emit("      (pdf_front_fp_property_popups yes)")
    emit("      (pdf_back_fp_property_popups yes)")
    emit("      (dxf_units_format 0)")
    emit("      (dxf_use_pcbnew_font yes)")
    emit("      (psnegative no)")
    emit("      (psa4output no)")
    emit("      (plotreference yes)")
    emit("      (plotvalue yes)")
    emit("      (plotfptext yes)")
    emit("      (plotinvisibletext no)")
    emit("      (sketchpadsonfab no)")
    emit("      (subtractmaskfromsilk no)")
    emit("      (outputformat 1)")
    emit("      (mirror no)")
    emit("      (drillshape 0)")
    emit("      (scaleselection 1)")
    emit('      (outputdirectory "fab/gerbers/")')
    emit("    )")
    emit("  )")

    # Net declarations
    emit('  (net 0 "")')
    for name in net_names:
        emit(f'  (net {net_map[name]} "{name}")')

    emit("")

    # Net classes (definitions)
    emit('  (net_class "Default" ""')
    emit("    (clearance 0.1)")
    emit("    (trace_width 0.15)")
    emit("    (via_dia 0.55)")
    emit("    (via_drill 0.3)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("  )")
    emit('  (net_class "Power" ""')
    emit("    (clearance 0.2)")
    emit("    (trace_width 0.4)")
    emit("    (via_dia 0.7)")
    emit("    (via_drill 0.4)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("  )")
    emit('  (net_class "Power_Wide" ""')
    emit("    (clearance 0.2)")
    emit("    (trace_width 0.8)")
    emit("    (via_dia 0.7)")
    emit("    (via_drill 0.4)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("  )")
    emit('  (net_class "RF_50ohm" ""')
    emit("    (clearance 0.2)")
    emit("    (trace_width 0.28)")
    emit("    (via_dia 0.55)")
    emit("    (via_drill 0.3)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("  )")
    emit('  (net_class "LVDS" ""')
    emit("    (clearance 0.12)")
    emit("    (trace_width 0.12)")
    emit("    (via_dia 0.45)")
    emit("    (via_drill 0.2)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("    (diff_pair_width 0.12)")
    emit("    (diff_pair_gap 0.2)")
    emit("  )")
    emit('  (net_class "DDR3" ""')
    emit("    (clearance 0.1)")
    emit("    (trace_width 0.1)")
    emit("    (via_dia 0.45)")
    emit("    (via_drill 0.2)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("  )")
    emit('  (net_class "DDR3_DiffPair" ""')
    emit("    (clearance 0.1)")
    emit("    (trace_width 0.1)")
    emit("    (via_dia 0.45)")
    emit("    (via_drill 0.2)")
    emit("    (uvia_dia 0.3)")
    emit("    (uvia_drill 0.1)")
    emit("    (diff_pair_width 0.1)")
    emit("    (diff_pair_gap 0.15)")
    emit("  )")

    emit("")

    # Net class memberships - assign nets to non-default classes
    # KiCad 9 uses net_class_memberships or inline in net_class with (add_net ...)
    # We use the (add_net) syntax inside net_class blocks - but that's KiCad 5 style.
    # For KiCad 7+/9, net class assignments go in the Design Rules as
    # (net_class_assignments ...) or we can use the older compatible format.
    # Actually in KiCad 9.x the cleanest way is to keep net_class definitions
    # and then assign nets via DRC rules or schematic net classes.
    # For PCB file compatibility, we just add the nets inline.
    # But wait - the format above is already the standard.
    # Let me use the supported approach: after net_class definitions,
    # we can add (net_class_memberships) or simply put the assignments
    # inline in the net_class blocks using (add_net "name").
    # KiCad 9 actually supports both. Let's emit a dedicated section.

    # Actually, looking at real KiCad 9 files, net class assignments are done
    # differently - they live in the board setup as custom rules or in the
    # net_class blocks with (add_net). Let me use the add_net approach.
    # But that requires modifying the net_class blocks above.
    # Instead, let's just regenerate with add_net inside.

    # We need to re-emit net_class blocks with add_net entries.
    # Let's rebuild:
    lines_nc = []
    # Find and remove the previously emitted net_class blocks
    # and re-emit with assignments
    # Actually, let's just clear and re-emit the net_class section properly.

    # Remove the net_class lines we already emitted
    # Find the first net_class line
    nc_start = None
    nc_end = None
    for idx, line in enumerate(lines):
        if '(net_class "Default"' in line and nc_start is None:
            nc_start = idx
        if nc_start is not None and line.strip() == ")" and '(net_class' not in line:
            # Check if next non-empty line is another net_class or empty
            pass
    # This is getting messy. Let's just not do the double-emit approach.
    # Instead, rebuild the net_class section from scratch with add_net.

    # Clear everything from the first net_class to the end of the last one
    new_lines = []
    skip = False
    in_net_class = False
    for line in lines:
        if '(net_class "' in line:
            skip = True
            in_net_class = True
            continue
        if skip and line.strip() == ")":
            skip = False
            in_net_class = False
            continue
        if skip:
            continue
        new_lines.append(line)

    lines = new_lines

    # Now re-emit net classes with add_net entries
    def emit_net_class(name, desc, params, nets_list):
        lines.append(f'  (net_class "{name}" "{desc}"')
        for k, v in params:
            lines.append(f"    ({k} {v})")
        for n in sorted(nets_list):
            lines.append(f'    (add_net "{n}")')
        lines.append("  )")

    # Gather nets per class
    power_nets_list = net_classes.get("Power", [])
    power_wide_list = net_classes.get("Power_Wide", [])
    rf_list = net_classes.get("RF_50ohm", [])
    lvds_list = net_classes.get("LVDS", [])
    ddr3_list = net_classes.get("DDR3", [])
    ddr3dp_list = net_classes.get("DDR3_DiffPair", [])

    # Move DDR3_DiffPair nets out of DDR3 (they might match both patterns)
    ddr3_list = [n for n in ddr3_list if n not in set(ddr3dp_list)]

    emit_net_class("Default", "", [
        ("clearance", "0.1"),
        ("trace_width", "0.15"),
        ("via_dia", "0.55"),
        ("via_drill", "0.3"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
    ], [])

    emit_net_class("Power", "", [
        ("clearance", "0.2"),
        ("trace_width", "0.4"),
        ("via_dia", "0.7"),
        ("via_drill", "0.4"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
    ], power_nets_list)

    emit_net_class("Power_Wide", "", [
        ("clearance", "0.2"),
        ("trace_width", "0.8"),
        ("via_dia", "0.7"),
        ("via_drill", "0.4"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
    ], power_wide_list)

    emit_net_class("RF_50ohm", "", [
        ("clearance", "0.2"),
        ("trace_width", "0.28"),
        ("via_dia", "0.55"),
        ("via_drill", "0.3"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
    ], rf_list)

    emit_net_class("LVDS", "", [
        ("clearance", "0.12"),
        ("trace_width", "0.12"),
        ("via_dia", "0.45"),
        ("via_drill", "0.2"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
        ("diff_pair_width", "0.12"),
        ("diff_pair_gap", "0.2"),
    ], lvds_list)

    emit_net_class("DDR3", "", [
        ("clearance", "0.1"),
        ("trace_width", "0.1"),
        ("via_dia", "0.45"),
        ("via_drill", "0.2"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
    ], ddr3_list)

    emit_net_class("DDR3_DiffPair", "", [
        ("clearance", "0.1"),
        ("trace_width", "0.1"),
        ("via_dia", "0.45"),
        ("via_drill", "0.2"),
        ("uvia_dia", "0.3"),
        ("uvia_drill", "0.1"),
        ("diff_pair_width", "0.1"),
        ("diff_pair_gap", "0.15"),
    ], ddr3dp_list)

    emit("")

    # Board outline (160x100mm)
    emit('  (gr_rect (start 0 0) (end 160 100) (stroke (width 0.1) (type solid)) (fill none) (layer "Edge.Cuts") (uuid "a1b2c3d4-e5f6-7890-abcd-ef0123456789"))')
    emit("")

    # Impedance notes
    emit(r'  (gr_text "IMPEDANCE TARGETS:\n50\u03A9 microstrip (F.Cu): 0.28mm w, ref GND1\n100\u03A9 diff stripline (In2.Cu): 0.12mm w, 0.20mm gap\n50\u03A9 stripline (In2/In4.Cu): 0.18mm w"')
    emit('    (at 80 -5) (layer "Cmts.User") (uuid "b2c3d4e5-f6a7-8901-bcde-f01234567890")')
    emit("    (effects (font (size 1.5 1.5) (thickness 0.15)))")
    emit("  )")
    emit("")

    # Component summary note
    summary = (
        f"NETLIST IMPORT SUMMARY:\\n"
        f"Total components: {total_components}\\n"
        f"Total nets: {total_nets}\\n"
        f"ICs: {ic_count}, Caps: {cap_count}, Res: {res_count}, "
        f"Ind: {ind_count}, Diodes: {diode_count}, LEDs: {led_count}\\n"
        f"Connectors: {conn_count}, Crystals: {xtal_count}\\n"
        f"Note: Run Update PCB from Schematic to import component footprints"
    )
    emit(f'  (gr_text "{summary}"')
    emit(f'    (at 80 108) (layer "Cmts.User") (uuid "{uid()}")')
    emit("    (effects (font (size 1.2 1.2) (thickness 0.12)))")
    emit("  )")
    emit("")

    # Mounting holes at 4 corners (5mm inset from board edge)
    emit("  ;; Mounting holes - M3, 3.2mm drill, 6mm pad")
    emit(generate_mounting_hole("MH1", 5, 5))
    emit(generate_mounting_hole("MH2", 155, 5))
    emit(generate_mounting_hole("MH3", 5, 95))
    emit(generate_mounting_hole("MH4", 155, 95))
    emit("")

    emit(")")

    return "\n".join(lines), total_components, total_nets, comp_by_type, net_classes


def main():
    all_components = []
    all_nets = set()
    all_nets.add("GND")  # Always present

    print("Parsing schematic files...")
    for sch_file in SCHEMATIC_FILES:
        filepath = os.path.join(SCRIPT_DIR, sch_file)
        if not os.path.exists(filepath):
            print(f"  WARNING: {sch_file} not found, skipping")
            continue
        components, nets = parse_schematic(filepath)
        all_components.extend(components)
        all_nets.update(nets)
        print(f"  {sch_file}: {len(components)} components, {len(nets)} nets")

    # Deduplicate components by reference (same ref from different sheets is same part)
    seen_refs = set()
    unique_components = []
    for c in all_components:
        if c["reference"] not in seen_refs:
            seen_refs.add(c["reference"])
            unique_components.append(c)

    print(f"\nTotal unique components: {len(unique_components)}")
    print(f"Total unique nets: {len(all_nets)}")

    pcb_content, total_comp, total_nets, comp_types, net_classes = generate_pcb(
        unique_components, all_nets
    )

    # Write PCB file
    pcb_path = os.path.join(SCRIPT_DIR, "cirradio-devboard.kicad_pcb")
    with open(pcb_path, "w") as f:
        f.write(pcb_content)
        f.write("\n")
    print(f"\nWrote {pcb_path}")

    # Print summary
    print("\n=== COMPONENT SUMMARY ===")
    for prefix in sorted(comp_types.keys()):
        print(f"  {prefix}: {comp_types[prefix]}")

    print("\n=== NET CLASS ASSIGNMENTS ===")
    for cls in sorted(net_classes.keys()):
        nets = net_classes[cls]
        print(f"  {cls}: {len(nets)} nets")
        for n in sorted(nets)[:10]:
            print(f"    {n}")
        if len(nets) > 10:
            print(f"    ... and {len(nets) - 10} more")

    print(f"\n=== TOTALS ===")
    print(f"  Components: {total_comp}")
    print(f"  Nets: {total_nets}")
    print(f"  Mounting holes: 4 (MH1-MH4)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
