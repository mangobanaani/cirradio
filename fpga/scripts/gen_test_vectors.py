#!/usr/bin/env python3
# fpga/scripts/gen_test_vectors.py
# Generates AES-256-ECB test vectors matching Phase 1 HopSequencer plaintext format.
# Output used by fhss_engine_tb.sv.
# Requires: pip install cryptography

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import struct, json

def compute_channel_index(fhek: bytes, slot: int, frame: int,
                           attempt: int, num_channels: int) -> int:
    """Mirrors HopSequencer::compute_channel_index() exactly."""
    # [slot(1)][pad(3)][frame LE(4)][zeros(7)][attempt(1)] = 16 bytes
    plaintext = bytes([slot, 0, 0, 0]) + struct.pack('<I', frame) + \
                bytes(7) + bytes([attempt])
    cipher = Cipher(algorithms.AES(fhek), modes.ECB(), backend=default_backend())
    enc = cipher.encryptor()
    ct = enc.update(plaintext) + enc.finalize()
    raw = struct.unpack('<Q', ct[:8])[0]
    return raw % num_channels

# CIRRADIO band: 225-512 MHz, 1 MHz spacing = 287 channels
NUM_CHANNELS = 287

vectors = []
# Vector set 1: FHEK = 32 x 0xAA
fhek_aa = bytes([0xAA] * 32)
for slot, frame in [(0,0),(0,1),(0,100),(1,0),(5,50),(19,999)]:
    ch = compute_channel_index(fhek_aa, slot, frame, 0, NUM_CHANNELS)
    freq_khz = 225_000 + ch * 1_000
    vectors.append({
        "fhek": "AA"*32, "slot": slot, "frame": frame, "attempt": 0,
        "channel_index": ch, "freq_khz": freq_khz
    })

# Vector set 2: blacklist test — attempt=1 with FHEK=0xCC
fhek_cc = bytes([0xCC] * 32)
ch0 = compute_channel_index(fhek_cc, 0, 0, 0, NUM_CHANNELS)
ch1 = compute_channel_index(fhek_cc, 0, 0, 1, NUM_CHANNELS)
vectors.append({"fhek": "CC"*32, "slot": 0, "frame": 0, "attempt": 0,
                "channel_index": ch0, "freq_khz": 225_000 + ch0*1_000})
vectors.append({"fhek": "CC"*32, "slot": 0, "frame": 0, "attempt": 1,
                "channel_index": ch1, "freq_khz": 225_000 + ch1*1_000})

print(json.dumps(vectors, indent=2))

# Also emit SystemVerilog parameter format for direct inclusion in testbench
print("\n// Paste into fhss_engine_tb.sv:")
for v in vectors:
    print(f"// slot={v['slot']} frame={v['frame']} attempt={v['attempt']}"
          f" -> ch={v['channel_index']} freq={v['freq_khz']} kHz")
