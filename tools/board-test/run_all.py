# tools/board-test/run_all.py
"""Sequenced board test suite. Emits valid TAP-13 output."""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    ("serial_console", ["serial_console.py"]),
    ("flash_fpga",     ["flash_fpga.py"]),
    ("rf_loopback",    ["rf_loopback.py"]),
    ("gps_lock",       ["gps_lock.py"]),
    ("fhss_onair",     ["fhss_onair.py"]),
]

HERE = Path(__file__).parent


def run_script(script_path, extra_args, common_args):
    cmd = [sys.executable, str(script_path)] + common_args + extra_args
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run all board tests")
    parser.add_argument("--host",      default="192.168.1.100")
    parser.add_argument("--key",       default=None)
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--bitstream", default="/tmp/cirradio.bit")
    parser.add_argument("--port",      default="/dev/ttyUSB0")
    args = parser.parse_args()

    common = ["--host", args.host]
    if args.key:
        common += ["--key", args.key]
    if args.dry_run:
        common.append("--dry-run")

    print("TAP version 13")
    print(f"1..{len(SCRIPTS)}")

    all_passed = True
    for i, (name, script_args) in enumerate(SCRIPTS, 1):
        extra = []
        if name == "flash_fpga":
            extra = ["--bitstream", args.bitstream]
        if name == "serial_console":
            extra = ["--port", args.port]
        script = HERE / script_args[0]
        ok = run_script(script, extra, common)
        status = "ok" if ok else "not ok"
        print(f"{status} {i} - {name}")
        if not ok:
            all_passed = False

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
