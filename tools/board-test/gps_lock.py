# tools/board-test/gps_lock.py
"""Wait for gpsd 3D fix and PPS signal on the board."""
import argparse
import json
import sys
import time
from board_ssh import BoardSSH, add_args, write_result

FIX_TIMEOUT_SECONDS = 300
PPS_JITTER_THRESHOLD_NS = 1000


def wait_for_fix(ssh: BoardSSH, timeout: int, dry_run: bool) -> tuple[bool, dict]:
    if dry_run:
        return True, {"mode": 3, "lat": 60.1, "lon": 24.9, "fix_time_s": 2}
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out, _ = ssh.run("gpspipe -w -n 10 2>/dev/null | grep TPV | head -1", timeout=15)
        if rc == 0 and out.strip():
            try:
                tpv = json.loads(out.strip())
                if tpv.get("mode", 0) >= 3:
                    return True, tpv
            except json.JSONDecodeError:
                pass
        time.sleep(5)
    return False, {}


def check_pps_jitter(ssh: BoardSSH, dry_run: bool) -> tuple[bool, float]:
    if dry_run:
        return True, 100.0
    rc, out, _ = ssh.run("cat /sys/class/pps/pps0/assert 2>/dev/null | tail -5")
    if rc != 0 or not out.strip():
        return False, -1.0
    timestamps = []
    for line in out.strip().splitlines():
        try:
            ts = float(line.split("#")[0])
            timestamps.append(ts)
        except (ValueError, IndexError):
            pass
    if len(timestamps) < 2:
        return False, -1.0
    intervals = [abs((timestamps[i+1] - timestamps[i]) - 1.0) * 1e9
                 for i in range(len(timestamps) - 1)]
    jitter_ns = max(intervals)
    return jitter_ns < PPS_JITTER_THRESHOLD_NS, jitter_ns


def main():
    parser = argparse.ArgumentParser(description="GPS 3D fix + PPS jitter test")
    add_args(parser)
    parser.add_argument("--timeout", type=int, default=FIX_TIMEOUT_SECONDS)
    args = parser.parse_args()
    with BoardSSH(args.host, args.key, args.dry_run) as ssh:
        fix_ok, tpv = wait_for_fix(ssh, args.timeout, args.dry_run)
        pps_ok, jitter_ns = check_pps_jitter(ssh, args.dry_run)
    passed = fix_ok and pps_ok
    write_result("gps_lock", passed, {
        "fix_achieved": fix_ok, "tpv": tpv,
        "pps_jitter_ns": jitter_ns, "pps_threshold_ns": PPS_JITTER_THRESHOLD_NS,
    })
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
