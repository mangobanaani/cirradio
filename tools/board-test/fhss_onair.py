# tools/board-test/fhss_onair.py
"""Two-board FHSS hop correlation test."""
import argparse
import json
import sys
from board_ssh import BoardSSH, add_args, write_result

NUM_HOPS = 100
REQUIRED_CORRELATION = 1.0


def collect_hop_log(ssh: BoardSSH, num_hops: int, dry_run: bool) -> list:
    if dry_run:
        return [225000 + (i * 1000 + 17000) % 287000 for i in range(num_hops)]
    cmd = f"cirradio-cli fhss log --hops {num_hops} --json 2>/dev/null"
    rc, out, _ = ssh.run(cmd, timeout=30)
    if rc != 0:
        return []
    try:
        return json.loads(out).get("hops", [])
    except json.JSONDecodeError:
        return []


def main():
    parser = argparse.ArgumentParser(description="Two-board FHSS hop correlation")
    add_args(parser)
    parser.add_argument("--host2", default=None)
    args = parser.parse_args()
    host2 = args.host2 or args.host
    with BoardSSH(args.host, args.key, args.dry_run) as ssh1, \
         BoardSSH(host2, args.key, args.dry_run) as ssh2:
        hops1 = collect_hop_log(ssh1, NUM_HOPS, args.dry_run)
        hops2 = collect_hop_log(ssh2, NUM_HOPS, args.dry_run)
    if not hops1 or not hops2 or len(hops1) != len(hops2):
        write_result("fhss_onair", False, {"error": f"hop counts: {len(hops1)} vs {len(hops2)}"})
        sys.exit(1)
    matches = sum(1 for a, b in zip(hops1, hops2) if a == b)
    correlation = matches / NUM_HOPS
    passed = correlation >= REQUIRED_CORRELATION
    write_result("fhss_onair", passed, {
        "hops_checked": NUM_HOPS, "matches": matches, "correlation": correlation,
    })
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
