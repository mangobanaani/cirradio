# tools/board-test/board_ssh.py
"""Shared SSH helpers and dry-run mock for board bring-up scripts."""
import json
import os
import time
from pathlib import Path
from typing import Optional

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


class BoardSSH:
    """Paramiko SSH wrapper with dry-run mode."""

    def __init__(self, host: str, key_path: Optional[str] = None,
                 dry_run: bool = False):
        self.host = host
        self.key_path = key_path
        self.dry_run = dry_run
        self._client = None
        if not dry_run:
            import paramiko
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs = {"hostname": host, "username": "root", "timeout": 30}
            if key_path:
                kwargs["key_filename"] = key_path
            self._client.connect(**kwargs)

    def run(self, cmd: str, timeout: int = 60) -> tuple[int, str, str]:
        if self.dry_run:
            return self._dry_run_cmd(cmd)
        stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        rc = stdout.channel.recv_exit_status()
        return rc, stdout.read().decode(), stderr.read().decode()

    def _dry_run_cmd(self, cmd: str) -> tuple[int, str, str]:
        mocks = {
            "ls /dev/uio0": (0, "/dev/uio0\n", ""),
            "gpspipe -w -n": (0, '{"class":"TPV","mode":3,"lat":60.1,"lon":24.9}\n', ""),
            "cat /sys/class/pps/pps0/assert": (0, "1710000000.000000001#1\n1710000001.000000002#2\n", ""),
        }
        for pattern, result in mocks.items():
            if pattern in cmd:
                return result
        return 0, f"[dry-run] {cmd}\n", ""

    def close(self):
        if self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def write_result(script_name: str, passed: bool, details: dict) -> Path:
    result = {"script": script_name, "passed": passed,
              "timestamp": time.time(), **details}
    out = RESULTS_DIR / f"{script_name}.json"
    out.write_text(json.dumps(result, indent=2))
    tap_line = f"{'ok' if passed else 'not ok'} - {script_name}"
    print(tap_line)
    return out


def add_args(parser):
    parser.add_argument("--host", default="192.168.1.100")
    parser.add_argument("--key", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser
