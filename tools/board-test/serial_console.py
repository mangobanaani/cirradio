#!/usr/bin/env python3
# tools/board-test/serial_console.py
"""Serial console board test: verify U-Boot and Linux boot via UART."""
import argparse
import time
from pathlib import Path
from board_ssh import write_result

UBOOT_PROMPT  = "ZynqMP>"
LINUX_PROMPT  = "login:"
BOOT_TIMEOUT  = 120  # seconds

def run_dry():
    write_result("serial_console", True, {
        "log": "dry-run: U-Boot and Linux boot simulated",
        "uboot_seen": True,
        "linux_seen": True,
    })


def run_live(port: str, baud: int):
    import serial
    result = {"uboot_seen": False, "linux_seen": False, "log": ""}
    passed = False
    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            deadline = time.monotonic() + BOOT_TIMEOUT
            buf = ""
            while time.monotonic() < deadline:
                chunk = ser.read(256).decode("utf-8", errors="replace")
                buf += chunk
                if UBOOT_PROMPT in buf:
                    result["uboot_seen"] = True
                if LINUX_PROMPT in buf:
                    result["linux_seen"] = True
                    break
            result["log"] = buf[-500:]  # last 500 chars
            passed = result["uboot_seen"] and result["linux_seen"]
    except Exception as e:
        result["log"] = str(e)
    write_result("serial_console", passed, result)
    return passed


def main():
    parser = argparse.ArgumentParser(description="Serial console boot verification")
    parser.add_argument("--port",    default="/dev/ttyUSB0")
    parser.add_argument("--baud",    type=int, default=115200)
    parser.add_argument("--dry-run", action="store_true")
    # Absorb common args passed by run_all.py
    parser.add_argument("--host",    default=None)
    parser.add_argument("--key",     default=None)
    args = parser.parse_args()

    if args.dry_run:
        run_dry()
        return
    ok = run_live(args.port, args.baud)
    raise SystemExit(0 if ok else 1)

if __name__ == "__main__":
    main()
