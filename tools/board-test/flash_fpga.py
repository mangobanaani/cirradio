# tools/board-test/flash_fpga.py
"""Flash FPGA bitstream via xsct (Vivado SDK) or xc3sprog."""
import argparse
import subprocess
import sys
from board_ssh import BoardSSH, add_args, write_result


def flash_with_xsct(bitstream_path: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "[dry-run] xsct flash simulated"
    tcl = (
        f"connect; targets -set -filter {{name =~ \"arm*\"}}; "
        f"fpga {bitstream_path}; disconnect; exit"
    )
    result = subprocess.run(
        ["xsct", "-eval", tcl],
        capture_output=True, text=True, timeout=120
    )
    return result.returncode == 0, result.stdout + result.stderr


def flash_with_xc3sprog(bitstream_path: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "[dry-run] xc3sprog flash simulated"
    result = subprocess.run(
        ["xc3sprog", "-c", "jtaghs1_fast", bitstream_path],
        capture_output=True, text=True, timeout=120
    )
    return result.returncode == 0, result.stdout + result.stderr


def verify_uio0(ssh: BoardSSH) -> bool:
    rc, out, _ = ssh.run("ls /dev/uio0")
    return rc == 0 and "/dev/uio0" in out


def main():
    parser = argparse.ArgumentParser(description="Flash FPGA via JTAG")
    add_args(parser)
    parser.add_argument("--bitstream", required=True)
    parser.add_argument("--tool", choices=["xsct", "xc3sprog"], default="xsct")
    args = parser.parse_args()

    if args.tool == "xsct":
        ok, log = flash_with_xsct(args.bitstream, args.dry_run)
    else:
        ok, log = flash_with_xc3sprog(args.bitstream, args.dry_run)

    if not ok:
        write_result("flash_fpga", False, {"error": log})
        sys.exit(1)

    with BoardSSH(args.host, args.key, args.dry_run) as ssh:
        uio_ok = verify_uio0(ssh)

    passed = ok and uio_ok
    write_result("flash_fpga", passed,
                 {"tool": args.tool, "uio0_present": uio_ok, "log": log[:500]})
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
