#!/usr/bin/env python3
"""Basic design rule check for the CIRRADIO dev board PCB."""

import re
import sys
import os

PCB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "cirradio-devboard.kicad_pcb")


def read_pcb(path):
    with open(path, "r") as f:
        return f.read()


def check_parens(text):
    """Verify S-expression parenthesis balance."""
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return False, depth
    return depth == 0, depth


def collect_nets(text):
    """Return set of declared net numbers."""
    return set(int(m) for m in re.findall(r'^\s*\(net\s+(\d+)\s+"', text, re.MULTILINE))


def count_pattern(text, pattern):
    return len(re.findall(pattern, text, re.MULTILINE))


def extract_net_refs(text, pattern):
    """Extract net numbers referenced in segments or vias."""
    return [int(m) for m in re.findall(pattern, text)]


def check_board_dimensions(text):
    """Check Edge.Cuts for 160x100mm board outline."""
    # gr_rect form
    m = re.search(
        r'\(gr_rect\s+\(start\s+([\d.]+)\s+([\d.]+)\)\s+\(end\s+([\d.]+)\s+([\d.]+)\).*?"Edge\.Cuts"',
        text,
    )
    if m:
        x1, y1, x2, y2 = float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        return w, h

    # Fallback: 4 gr_line segments on Edge.Cuts
    lines = re.findall(
        r'\(gr_line\s+\(start\s+([\d.]+)\s+([\d.]+)\)\s+\(end\s+([\d.]+)\s+([\d.]+)\).*?"Edge\.Cuts"',
        text,
    )
    if len(lines) >= 4:
        xs = set()
        ys = set()
        for x1, y1, x2, y2 in lines:
            xs.update([float(x1), float(x2)])
            ys.update([float(y1), float(y2)])
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        return w, h

    return None, None


def main():
    if not os.path.exists(PCB_FILE):
        print(f"ERROR: PCB file not found: {PCB_FILE}")
        sys.exit(1)

    text = read_pcb(PCB_FILE)
    issues = []

    # 1. S-expression balance
    balanced, depth = check_parens(text)
    if not balanced:
        issues.append(f"S-expression unbalanced (depth={depth})")

    # 2. Count elements
    nets = collect_nets(text)
    n_footprints = count_pattern(text, r'^\s*\(footprint\s+"')
    n_segments = count_pattern(text, r'^\s*\(segment\s+')
    n_vias = count_pattern(text, r'^\s*\(via\s+')
    n_zones = count_pattern(text, r'^\s*\(zone\s+')

    # 3. Verify net references in segments and vias
    seg_nets = extract_net_refs(text, r'\(segment\s[^)]*\(net\s+(\d+)\)')
    via_nets = extract_net_refs(text, r'\(via\s[^)]*\(net\s+(\d+)\)')
    all_refs = set(seg_nets + via_nets)
    invalid_nets = all_refs - nets
    if invalid_nets:
        issues.append(f"Invalid net references: {sorted(invalid_nets)}")

    # 4. Board dimensions
    w, h = check_board_dimensions(text)
    if w is None:
        issues.append("Could not determine board dimensions from Edge.Cuts")
    else:
        if abs(w - 160.0) > 0.5 or abs(h - 100.0) > 0.5:
            issues.append(f"Board dimensions {w}x{h}mm, expected 160x100mm")

    # Report
    print("=" * 50)
    print("CIRRADIO Dev Board DRC Report")
    print("=" * 50)
    print(f"Nets defined:   {len(nets)}")
    print(f"Components:     {n_footprints}")
    print(f"Segments:       {n_segments}")
    print(f"Vias:           {n_vias}")
    print(f"Zones:          {n_zones}")
    if w is not None:
        print(f"Board size:     {w:.0f} x {h:.0f} mm")
    print(f"Parens balanced: {'Yes' if balanced else 'No'}")
    print(f"Net refs valid:  {'Yes' if not invalid_nets else 'No'}")
    print("-" * 50)

    if issues:
        print("ISSUES FOUND:")
        for i in issues:
            print(f"  - {i}")
        print("Result: FAIL")
        sys.exit(1)
    else:
        print("Result: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
