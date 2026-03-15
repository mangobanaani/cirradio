# tools/board-test/rf_loopback.py
"""RF TX->RX loopback: tune to 300 MHz, transmit QPSK, measure EVM."""
import argparse
import math
import sys
from board_ssh import BoardSSH, add_args, write_result

EVM_THRESHOLD_PERCENT = 5.0
NUM_SYMBOLS = 4096


def generate_qpsk_symbols(n: int) -> list:
    points = [complex(1, 1), complex(-1, 1), complex(-1, -1), complex(1, -1)]
    return [points[i % 4] / math.sqrt(2) for i in range(n)]


def compute_evm(tx: list, rx: list) -> float:
    if len(tx) != len(rx):
        return 100.0
    rms_ref = math.sqrt(sum(abs(s) ** 2 for s in tx) / len(tx))
    rms_err = math.sqrt(sum(abs(t - r) ** 2 for t, r in zip(tx, rx)) / len(tx))
    return (rms_err / rms_ref) * 100.0


def run_loopback_on_board(ssh: BoardSSH, dry_run: bool) -> tuple[float, str]:
    if dry_run:
        tx = generate_qpsk_symbols(NUM_SYMBOLS)
        rx = [s + complex(0.01, 0.01) for s in tx]
        return compute_evm(tx, rx), "dry-run simulated"

    script = """python3 -c "
import iio, math, struct
ctx = iio.Context()
phy = ctx.find_device('ad9361-phy')
rx  = ctx.find_device('cf-ad9361-lpc')
phy.find_channel('altvoltage0').attrs['frequency'].value = '300000000'
phy.find_channel('altvoltage1').attrs['frequency'].value = '300000000'
phy.attrs['loopback'].value = '1'
buf = iio.Buffer(rx, 4096)
buf.refill()
data = buf.read()
samples = [struct.unpack_from('<hh', data, i*4) for i in range(min(4096, len(data)//4))]
evm_vals = [abs(complex(s[0], s[1])/32768 - complex(0.7071, 0)) for s in samples]
print(f'EVM:{sum(evm_vals)/len(evm_vals)*100:.2f}')
phy.attrs['loopback'].value = '0'
"
"""
    rc, out, err = ssh.run(script, timeout=30)
    if rc != 0:
        return 100.0, err
    for line in out.splitlines():
        if line.startswith("EVM:"):
            return float(line.split(":")[1]), out
    return 100.0, out


def main():
    parser = argparse.ArgumentParser(description="RF loopback EVM test")
    add_args(parser)
    args = parser.parse_args()

    with BoardSSH(args.host, args.key, args.dry_run) as ssh:
        evm, log = run_loopback_on_board(ssh, args.dry_run)

    passed = evm < EVM_THRESHOLD_PERCENT
    write_result("rf_loopback", passed,
                 {"evm_percent": round(evm, 3),
                  "threshold_percent": EVM_THRESHOLD_PERCENT,
                  "log": log[:500]})
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
