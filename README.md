# CIRRADIO

> Full-stack SDR — UHF FHSS ad-hoc mesh radio with AES-256
> frequency hopping, PKCS#11 HSM crypto, TDMA MAC, and QPSK+Viterbi modem.
> SystemVerilog RTL (Zynq-7045 PL) through embedded Linux (PetaLinux/Yocto)
> to a C++20 comms stack, validated in simulation end-to-end.


---

## What It Is

CIRRADIO is a tactical UHF frequency-hopping spread-spectrum (FHSS) mesh radio
designed to NSA/MIL-STD-inspired requirements. It covers the 225–512 MHz
military UHF band with 287 hop channels, AES-256 frequency-hop sequencing,
TDMA slot MAC, and a PKCS#11-abstracted HSM crypto layer. The target hardware
is a custom Zynq-7045 + AD9361 board designed in Phase 2; the full software
stack runs and passes tests today on any Linux or macOS machine without hardware.

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
| RF Front-End        | Custom KiCad board (Phase 2)        | LNA, PA, bandpass filter, T/R switch       | Board designed  |
| RF Transceiver      | AD9361                              | 70 MHz–6 GHz direct-conversion SDR         | RTL complete    |
| FPGA DSP            | SystemVerilog, Zynq-7045 PL         | Channelizer, modem, FHSS engine, TDMA MAC  | XSim verified   |
| Embedded Linux      | PetaLinux 2024.2 / Yocto            | BSP, device tree, Yocto app layer          | Config complete |
| Hardware HAL        | libiio, UIO mmap, gpsd              | IRadioHal + IGpsHal for Zynq ARM           | Code complete   |
| Comms Stack         | C++20, CMake, Boost, OpenSSL        | Full SCA-inspired radio stack              | 97 tests pass   |
| Crypto / HSM        | OpenSSL, PKCS#11, SoftHSM2          | AES-256-GCM, ECDSA P-384, key management  | Tests pass      |
| Mesh Networking     | Custom OLSR adaptation              | Ad-hoc peer discovery, net join            | Tests pass      |
| Voice               | Codec2 (3200 bps)                   | Open voice codec; MELPe placeholder        | Tests pass      |

---

## What Makes It Milspec-Capable

- **287-channel UHF FHSS** (225–512 MHz, 1 MHz spacing) — AES-256-ECB hop sequencer;
  hop key (FHEK) is cryptographically separate from traffic key (TEK) so TEK compromise
  does not reveal the hop pattern
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
# Expected: 100% tests passed, 0 tests failed out of 97
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
