# Board Bring-up Test Suite

Scripts for automated bring-up testing of the CIRRADIO dev board.
All scripts support `--dry-run` for local verification without hardware.

## Prerequisites

```
pip install -r requirements.txt
```

`paramiko` is required for SSH connectivity. `pyserial` is used for
serial console access (not yet implemented in these scripts).

## Scripts

### board_ssh.py
Shared SSH helpers used by all test scripts. Provides `BoardSSH` (paramiko
wrapper with dry-run mode) and `write_result()` (TAP + JSON output).

### flash_fpga.py
Flash the FPGA bitstream via JTAG using `xsct` (Vivado SDK) or `xc3sprog`,
then verify `/dev/uio0` is present on the target.

```
python3 flash_fpga.py --host 192.168.1.100 --bitstream cirradio.bit [--tool xsct|xc3sprog]
python3 flash_fpga.py --bitstream /tmp/test.bit --dry-run
```

### rf_loopback.py
Enable AD9361 internal loopback at 300 MHz, transmit QPSK symbols, and
measure EVM. Pass threshold: EVM < 5%.

```
python3 rf_loopback.py --host 192.168.1.100
python3 rf_loopback.py --dry-run
```

### gps_lock.py
Wait for gpsd to report a 3D fix (mode >= 3) and verify PPS jitter is
below 1000 ns.

```
python3 gps_lock.py --host 192.168.1.100 [--timeout 300]
python3 gps_lock.py --dry-run
```

### fhss_onair.py
Collect FHSS hop logs from two boards and verify 100% hop correlation.
Requires the `cirradio-cli` application running on the target.

```
python3 fhss_onair.py --host 192.168.1.100 --host2 192.168.1.101
python3 fhss_onair.py --dry-run
```

### run_all.py
Runs all scripts in sequence and emits TAP-format output.

```
python3 run_all.py --host 192.168.1.100 --bitstream cirradio.bit
python3 run_all.py --dry-run
```

## Results

Each script writes a JSON result file to `results/<script_name>.json`.
Fields: `script`, `passed`, `timestamp`, plus script-specific details.
