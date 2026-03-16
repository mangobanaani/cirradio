# CIRRADIO

> Full-stack SDR — UHF FHSS ad-hoc mesh radio with AES-256 frequency hopping,
> PKCS#11 HSM crypto, TDMA MAC, QPSK+Viterbi modem, and TRANSEC (11,480-channel
> anti-jam FHSS, EMCON 0/1/2 emission control, adaptive per-link power control).
> SystemVerilog RTL (Zynq-7045 PL) through embedded Linux (PetaLinux/Yocto)
> to a C++20 comms stack, validated in simulation end-to-end.

![License](https://img.shields.io/github/license/mangobanaani/cirradio)
![C++](https://img.shields.io/badge/C%2B%2B-20-blue)
![SystemVerilog](https://img.shields.io/badge/RTL-SystemVerilog-orange)
![CMake](https://img.shields.io/badge/CMake-3.20%2B-064F8C)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey)
![Tests](https://img.shields.io/badge/tests-128%20passing-brightgreen)

---

## What It Is

CIRRADIO is a tactical UHF frequency-hopping spread-spectrum (FHSS) mesh radio
designed to NSA/MIL-STD-inspired requirements. It covers the 225–512 MHz
military UHF band with 11,480 hop channels at 25 kHz spacing, GPS-locked 100
hops/sec AES-256-ECB sequencing, TDMA slot MAC, and a PKCS#11-abstracted HSM
crypto layer. The TRANSEC subsystem adds three-tier emission control (EMCON
0/1/2), FEC block interleaving, burst-mode PA ramping, and adaptive per-link
power control. The target hardware is a custom Zynq-7045 + AD9361 board; the
full software stack runs and passes tests today on any Linux or macOS machine
without hardware.

---

## Architecture

```
RF Front-End  (LNA · PA · bandpass filter · T/R switch)
      │ SMA
  AD9361  Transceiver  (70 MHz – 6 GHz direct-conversion SDR)
      │ LVDS 6-bit DDR  (ad9361_if.sv — IBUFDS/ISERDESE2 RX, OSERDESE2 TX)
  ┌───────────────────────── Zynq-7045 PL ──────────────────────────┐
  │  Channelizer     CIC + RRC FIR DDC/DUC  (4× oversample)        │
  │  QPSK Modem      RRC MF · Gardner TED · Costas · Viterbi K=7   │
  │  FHSS Engine     AES-256-ECB hop seq · blacklist · GPS 1PPS     │
  │  TDMA MAC        Slot engine · TXNRX control · preamble         │
  │  AXI Regs        4 KB AXI4-Lite slave  (PS ↔ PL control plane) │
  └────────────────────────── AXI / DMA ───────────────────────────┘
      │ AXI4-Lite + AXI DMA
  ┌───────────────────────── Zynq-7045 PS ──────────────────────────┐
  │  PetaLinux 2024.2 / Yocto BSP  (device tree · meta-cirradio)   │
  │  Zynq7045HAL  →  libiio (AD9361) · UIO mmap (AXI regs) · gpsd  │
  │  ┌─────────────────── C++20 Comms Stack ──────────────────────┐ │
  │  │  SCA Core · FHSS scheduler · TDMA scheduler                │ │
  │  │  Mesh Router (OLSR) · Peer Discovery · Net Join (ECDSA)    │ │
  │  │  CryptoEngine (AES-256-GCM) · KeyManager (PKCS#11 HSM)    │ │
  │  │  Voice Pipeline (Codec2 3200 bps) · CLI Management Shell   │ │
  │  └────────────────────────────────────────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Stack

| Layer               | Technology                          | Purpose                                    | Status          |
|---------------------|-------------------------------------|--------------------------------------------|-----------------|
| RF Front-End        | Custom KiCad board (Zynq-7045)      | LNA, PA, bandpass filter, T/R switch       | Board designed  |
| RF Transceiver      | AD9361                              | 70 MHz–6 GHz direct-conversion SDR         | RTL complete    |
| FPGA DSP            | SystemVerilog, Zynq-7045 PL         | Channelizer, modem, FHSS engine, TDMA MAC  | XSim verified   |
| Embedded Linux      | PetaLinux 2024.2 / Yocto            | BSP, device tree, Yocto app layer          | Config complete |
| Hardware HAL        | libiio, UIO mmap, gpsd              | IRadioHal + IGpsHal for Zynq ARM           | Code complete   |
| Comms Stack         | C++20, CMake, Boost, OpenSSL        | Full SCA-inspired radio stack              | 128 tests pass  |
| TRANSEC             | C++20 + SystemVerilog               | Anti-jam FHSS, EMCON, adaptive power       | Complete        |
| Crypto / HSM        | OpenSSL, PKCS#11, SoftHSM2          | AES-256-GCM, ECDSA P-384, key management  | Tests pass      |
| Mesh Networking     | Custom OLSR adaptation              | Ad-hoc peer discovery, net join            | Tests pass      |
| Voice               | Codec2 (3200 bps)                   | Open voice codec; MELPe placeholder        | Tests pass      |

---

## What Makes It Milspec-Capable

- **11,480-channel UHF FHSS** (225–512 MHz, 25 kHz spacing) — GPS-locked 100 hops/sec
  AES-256-ECB hop sequencer with `hop_index` field for deterministic intra-second
  sequences; FHEK cryptographically separate from TEK so TEK compromise does not
  reveal the hop pattern
- **TRANSEC subsystem** — three-tier EMCON (0=silence, 1=beacon-only −20 dB,
  2=normal), hardware-enforced lock bit with one-time unlock token, tamper→EMCON-0
  callback; FEC block interleaver (N×512 BRAM, depth 1–32, default 10 = 100 ms
  jammer dwell); burst-mode PA ramp (configurable attenuation step, 10 µs default);
  adaptive per-link power control from beacon RSSI table (max 256 peers, 300 s expiry)
- **PKCS#11 HSM abstraction** — `IHsmEngine` interface + `Pkcs11Hsm` dlopen loader
  accepts any PKCS#11-compliant HSM module (Thales, Utimaco, YubiHSM, etc.) without
  code changes; SoftHSM2 used for development/CI
- **TDMA slot engine** with GPS 1PPS synchronisation and AXI Timer holdover on GPS loss;
  slot bitmap register lets each node own multiple traffic slots
- **QPSK modem** with rate-1/2 K=7 Viterbi FEC (CCSDS generators), Gardner timing
  error detector, and Costas loop carrier recovery — full closed-loop demodulation
- **ECDSA P-384 net join** — challenge-response authentication against a trusted node
  list; new node signs nonce, TEK+FHEK delivered encrypted under its public key;
  join target < 2 seconds
- **OTAR key distribution** architecture — over-the-air rekeying; TEK rotated hourly
- **Three-key hierarchy** — KEK (HSM-bound, wraps all other keys), TEK
  (per-session AES-256-GCM traffic key), FHEK (hop sequence key)
- **Secure boot chain design** — Zynq eFuse → FSBL → U-Boot → Linux → application;
  FPGA bitstream encrypted and authenticated in production configuration

---

## Build & Run (Software Stack — no hardware required)

The C++20 comms stack builds and runs on any Linux or macOS machine today.

**Dependencies (macOS):**
```bash
brew install cmake boost openssl spdlog softhsm codec2 catch2
```

**Dependencies (Ubuntu 24.04):**
```bash
sudo apt-get install -y cmake libboost-dev libssl-dev libspdlog-dev \
    libcodec2-dev softhsm2 pkg-config
# Catch2 v3 from source:
git clone --depth 1 --branch v3.5.4 https://github.com/catchorg/Catch2.git
cmake -S Catch2 -B Catch2/build -DBUILD_TESTING=OFF
sudo cmake --build Catch2/build --target install -j
```

**Build:**
```bash
cmake -S software -B software/build
cmake --build software/build -j$(nproc)
```

**Test:**
```bash
ctest --test-dir software/build --output-on-failure
# Expected: 100% tests passed, 0 tests failed out of 128
```

---

## Repository Layout

```
fpga/               FPGA RTL (SystemVerilog) + XSim testbenches
  src/              Six RTL modules: axi_regs, ad9361_if, channelizer,
                    fhss_engine, modem, tdma_mac
  sim/              Testbenches (*_tb.sv) — all pass XSim simulation
  scripts/          Vivado project TCL, simulation runner, check_regmap.py
  constraints/      Pin assignments (pinout.xdc) and timing (timing.xdc)

hardware/           KiCad dev board (Zynq-7045 + AD9361, 8-layer PCB)
  cirradio-devboard/  Python generators produce .kicad_sch and .kicad_pcb
  fab/              Fabrication notes

software/           C++20 comms stack (builds on desktop today)
  src/              HAL, FHSS, TDMA, network, security, voice, CLI
  tests/            Catch2 test suite (97 tests)
  embedded/         Cross-compile HAL for Zynq ARM (libiio, UIO, gpsd)

firmware/           Embedded Linux stack
  device-tree/      PetaLinux device tree overlays (pl.dtsi, system-user.dtsi)
  petalinux/        meta-cirradio Yocto layer with app recipe + systemd service

tools/
  board-test/       Board bring-up scripts (SSH + serial, all support --dry-run)

docs/               Architecture deep-dive, design specs, implementation plans
```

---

## See Also

- [`fpga/README.md`](fpga/README.md) — RTL module details and Vivado instructions
- [`hardware/README.md`](hardware/README.md) — Dev board overview and KiCad generation
- [`docs/architecture.md`](docs/architecture.md) — Key hierarchy, FHSS math, net join
  protocol, TDMA structure, AXI register map
- [`SECURITY.md`](SECURITY.md) — Crypto posture and responsible disclosure
