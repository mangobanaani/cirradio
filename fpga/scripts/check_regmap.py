#!/usr/bin/env python3
# fpga/scripts/check_regmap.py
# Validates that regs.svh and axi_regs.hpp define identical register offsets.
# Run: python3 fpga/scripts/check_regmap.py
# Exits 0 on success, 1 on mismatch.

import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SVH  = ROOT / "fpga/src/axi_regs/regs.svh"
HPP  = ROOT / "software/embedded/drivers/axi_regs.hpp"

def parse_svh(path):
    """Extract localparam name -> hex value from .svh"""
    result = {}
    for m in re.finditer(
        r"localparam\s+(\w+)\s*=\s*(12'h|32'h|5'd)?([0-9A-Fa-f_]+)",
        path.read_text()
    ):
        name, prefix, val = m.group(1), m.group(2), m.group(3).replace("_","")
        if prefix in ("12'h", "32'h"):
            result[name] = int(val, 16)
        elif prefix == "5'd":
            result[name] = int(val, 10)
    return result

def parse_hpp(path):
    """Extract constexpr name -> hex value from .hpp"""
    result = {}
    for m in re.finditer(
        r"constexpr\s+\w+\s+(\w+)\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+)u?",
        path.read_text()
    ):
        name, val = m.group(1), m.group(2)
        result[name] = int(val, 16) if val.startswith("0x") else int(val)
    return result

svh = parse_svh(SVH)
hpp = parse_hpp(HPP)

errors = []
for name, svh_val in svh.items():
    if name.startswith("STATUS_") and name.endswith("_BIT"):
        continue  # bit-index params not mirrored directly
    if name in hpp:
        if svh_val != hpp[name]:
            errors.append(f"MISMATCH {name}: svh=0x{svh_val:08X} hpp=0x{hpp[name]:08X}")
    else:
        errors.append(f"MISSING in hpp: {name}")

HPP_ONLY_ALLOWED = {"PAGE_SIZE"}
for name in hpp:
    if name not in svh and not name.startswith("STATUS_HOP") \
            and not name.startswith("STATUS_GPS") \
            and name not in HPP_ONLY_ALLOWED:
        errors.append(f"EXTRA in hpp (not in svh): {name}")

if errors:
    print("REGMAP CHECK FAILED:")
    for e in errors: print(f"  {e}")
    sys.exit(1)
print(f"REGMAP CHECK PASSED: {len(svh)} registers match between svh and hpp")
