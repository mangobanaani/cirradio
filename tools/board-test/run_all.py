# tools/board-test/run_all.py
"""Sequenced board test suite. Emits TAP output."""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    ("flash_fpga",  ["flash_fpga.py"]),
    ("rf_loopback", ["rf_loopback.py"]),
    ("gps_lock",    ["gps_lock.py"]),
    ("fhss_onair",  ["fhss_onair.py"]),
]

HERE = Path(__file__).parent


def run_script(script_path, extra_args, common_args):
    cmd = [sys.executable, str(script_path)] + common_args + extra_args
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run all board tests")
    parser.add_argument("--host", default="192.168.1.100")
    parser.add_argument("--key", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bitstream", default="/tmp/cirradio.bit")
    args = parser.parse_args()

    common = ["--host", args.host]
    if args.key:
        common += ["--key", args.key]
    if args.dry_run:
        common.append("--dry-run")

    print(f"TAP version 13")
    print(f"1..{len(SCRIPTS)}")

    all_passed = True
    for i, (name, script_args) in enumerate(SCRIPTS, 1):
        extra = []
        if name == "flash_fpga":
            extra = ["--bitstream", args.bitstream]
        script = HERE / script_args[0]
        ok = run_script(script, extra, common)
        if not ok:
            all_passed = False

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
