# CIRRADIO: Secure Tactical Software-Defined Radio

## Design Document

Date: 2026-03-02

## Overview

CIRRADIO is a secure tactical software-defined radio system for government team communications. It provides encrypted voice and data over ad-hoc peer-to-peer mesh networks with frequency-hopping spread spectrum (FHSS) in the UHF 225-512 MHz band.

The project encompasses custom PCB hardware, FPGA DSP firmware, and a C++ software stack built on the Software Communications Architecture (SCA).

## Requirements

- Frequency range: UHF 225-512 MHz
- TX power: Software-configurable, milliwatts to 5W
- Security: Type 1 / NSA-grade crypto infrastructure (AES-256-GCM placeholder for dev phase)
- Waveforms: SCA-compliant, supporting SINCGARS, HAVEQUICK, and custom FHSS
- Networking: Ad-hoc P2P mesh, no master node, up to 30 nodes
- Frequency hopping: GPS-synchronized, 20 hops/sec, adaptive anti-jam
- Form factor: Development board first, miniaturize for production later
- EDA: KiCad for PCB design

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CIRRADIO Dev Board                        │
│                                                             │
│  ┌──────────┐    ┌──────────────────────────┐              │
│  │ RF Front │    │     Xilinx Zynq-7045     │              │
│  │   End    │    │  ┌────────┐ ┌─────────┐  │  ┌────────┐ │
│  │          │SPI │  │ FPGA   │ │ ARM A9  │  │  │ HSM /  │ │
│  │ AD9361   │◄──►│  │Fabric  │ │ Core 0  │  │  │ Crypto │ │
│  │          │    │  │(DSP/   │ │ (SCA    │  │  │Module  │ │
│  │ LNA      │    │  │Wavefrm)│ │ Middle- │  │  └───┬────┘ │
│  │ PA (5W)  │    │  │        │ │ ware)   │  │      │SPI   │
│  │ Filters  │    │  │        │ │         │  │      │      │
│  │ T/R SW   │    │  │        │ │ Core 1  │  │  ┌───┴────┐ │
│  │          │    │  │        │ │ (Linux/ │  │  │  GPS   │ │
│  └────┬─────┘    │  └────────┘ │ Control)│  │  │ Module │ │
│       │          │             └─────────┘  │  └────────┘ │
│    SMA Conn      └──────────────────────────┘              │
│                        │    │    │                          │
│                      DDR3  USB  ETH                        │
│                      1GB  Debug  GigE                      │
└─────────────────────────────────────────────────────────────┘
```

Core components:

- **AD9361**: Wideband transceiver, 70 MHz - 6 GHz, 2x2 MIMO capable, 56 MHz instantaneous bandwidth. Connected to Zynq via LVDS data interface + SPI control.
- **Zynq-7045 (XC7Z045)**: 350K logic cells FPGA + dual Cortex-A9 @ 1 GHz. FPGA handles real-time DSP (channelization, FHSS hopping engine, modulation/demod). ARM runs PetaLinux + SCA middleware (REDHAWK).
- **HSM**: Dedicated crypto module for Type 1 encryption. Physically isolated, communicates over authenticated SPI. Anti-tamper mesh and zeroization on intrusion.
- **GPS**: u-blox M10 for timing (FHSS synchronization) and position reporting.
- **Memory**: 1 GB DDR3L for ARM, QSPI flash for FPGA bitstream and boot.

## RF Front-End

```
        ANT
         │
    ┌────┴────┐
    │ SMA     │
    │ Conn    │
    └────┬────┘
         │
    ┌────┴────┐
    │ Band-   │  225-512 MHz bandpass (SAW or cavity)
    │ pass    │
    │ Filter  │
    └────┬────┘
         │
    ┌────┴────┐
    │ T/R     │  PE42525, <0.5 dB loss, >50 dB isolation
    │ Switch  │  ~300 ns switching
    └──┬───┬──┘
       │   │
    TX │   │ RX
       │   │
       │   ▼
       │  LNA (ADL5523, NF ~1 dB, gain ~20 dB)
       │   │
       │   ▼
       │  SAW Filter (second stage, out-of-band rejection)
       │   │
       ▼   ▼
    ┌──────────────┐
    │   AD9361     │
    │  TX1  RX1    │  Internal AGC for RX
    └──────────────┘
       │
       ▼ TX path
    Driver Amp (ADL5606, ~20 dB gain)
       │
       ▼
    PA Module (Qorvo/MACOM, 225-512 MHz, 37 dBm / 5W max)
       │
       ▼
    LPF / Harmonic Filter
       │
       ▼
    To T/R Switch
```

Design points:

- Fast T/R switching (<1 us) for FHSS compatibility.
- System noise figure ~2 dB, sensitivity approximately -120 dBm.
- TX power control: AD9361 internal attenuation (~40 dB) + driver gain control + PA bias adjustment gives continuous mW-to-5W software control.
- PA dissipates ~10W at full power; heat sink required.
- Separate analog and digital ground planes. RF section shielded from digital.

## FPGA & DSP Architecture

### FPGA Fabric (PL)

- **AD9361 Interface**: LVDS 12-bit I/Q data path.
- **Channelizer**: DDC/DUC with polyphase filter bank.
- **FHSS Engine**: Hop sequencer generates pseudo-random frequency sequences from shared key/seed. Configurable 100-1000+ hops/sec. AD9361 retunes in ~50 us.
- **Modem**: QPSK/OFDM modulation/demodulation with LDPC FEC.
- **TDMA MAC Engine**: Slot allocation, preamble detection.
- **Sync & Timing**: GPS-disciplined, 1PPS aligned.

### ARM Processors (PS) - PetaLinux

- **REDHAWK SCA Core**: Waveform loader, component manager, domain manager.
- **Mesh Networking**: OLSR routing, peer discovery, TDMA scheduler.
- **Crypto Interface**: HSM driver, key management, zeroization.
- **Voice Pipeline**: Audio capture, MELPe/Codec2 codec, jitter buffer.
- **Situational Awareness**: GPS service, PLI tracker.
- **Management**: CLI shell, REST API, config/diagnostics.

## Security & Crypto Architecture

### Key Hierarchy

- **KEK (Key Encryption Key)**: Stored in HSM, never leaves hardware. Wraps/unwraps all other keys.
- **TEK (Traffic Encryption Key)**: Per-net session key, rotated hourly. Encrypts all voice + data. Distributed via OTAR.
- **FHEK (Freq Hop Encryption Key)**: Separate key for hop sequence generation. Compromising TEK does not reveal hop pattern.
- **IK (Identity Key)**: Per-device ECDSA P-384 keypair. Authenticates node during net join. Provisioned at manufacturing.

### Encryption

AES-256-GCM authenticated encryption. All crypto operations performed inside HSM hardware. Plaintext keys never exist in main RAM.

Data flow (TX): Plaintext -> Compress (LZ4) -> Encrypt (AES-256-GCM in HSM) -> FEC (LDPC) -> Modulate

### Anti-Tamper

Physical:
- Tamper-detect mesh over HSM + key storage
- Intrusion triggers instant zeroization (<10 ms)
- Battery-backed tamper circuit (always-on)

Logical:
- Secure boot chain: Zynq eFuse -> FSBL -> U-Boot -> Linux -> Application
- FPGA bitstream encrypted + authenticated
- Runtime integrity checks on code regions
- Failed auth attempts trigger key zeroization

### Net Join Protocol

1. New node transmits on rendezvous frequency (slot 19, fixed freq)
2. Existing node challenges with nonce
3. New node signs nonce with IK (ECDSA)
4. Existing node verifies against trusted node list
5. TEK + FHEK sent encrypted under new node's public key
6. New node ACKs, begins hopping with net

Target join time: < 2 seconds.

## FHSS & Ad-Hoc Mesh Protocol

### FHSS Timing Structure

- Frame duration: 1 second, GPS 1PPS aligned
- 20 slots per frame, 50 ms each
- Each slot: 2 ms guard | 3 ms preamble | 42 ms data | 3 ms guard
- Each slot hops to a different frequency: freq = AES(FHEK, slot_index || frame_count)
- Guard time absorbs GPS timing drift between nodes

### Slot Allocation (TDMA)

| Slots | Purpose |
|-------|---------|
| 0 | Beacon / Net Control (rotating responsibility, no single master) |
| 1-14 | Traffic slots (voice + data), dynamically claimed |
| 15-17 | Data-only slots (bulk transfer, PLI, preemptable) |
| 18 | OTAR / Key management (TEK rotation, emergency rekey) |
| 19 | Discovery / Join (fixed rendezvous frequency, not hopping) |

### Ad-Hoc Mesh Routing (Adapted OLSR)

- Each node broadcasts link-state in beacon slot (neighbor list, RSSI/SNR, hop count).
- All nodes compute shortest path via Dijkstra over link quality metric. Updated every frame or on topology change.
- Multi-hop relay: intermediate nodes automatically relay in their TX slot. +1 frame (~1s) latency per hop.
- Net merge/split: subnets auto-merge when in range; splits detected by missing heartbeats; each fragment operates independently.
- Max network size: 30 nodes. Max relay hops: 4 (voice latency < 500 ms).

### Voice Latency Budget

Audio capture (20 ms) + codec (5 ms) + wait for slot (25 ms avg) + propagation + decode = ~80 ms single hop.

### Anti-Jam

Nodes detect high error rate on specific hop frequencies and blacklist them. Hop sequencer adaptively skips jammed frequencies, reducing capacity slightly but maintaining communication.

## Software Architecture (C++)

### Technology

- C++17 minimum (C++20 where cross-compiler supports)
- CMake build system with cross-compilation for Zynq ARM
- Native host builds for unit testing

### Project Structure

```
cirradio/
├── hardware/                  # KiCad PCB project
│   ├── cirradio.kicad_pro
│   ├── schematic/
│   └── layout/
├── fpga/                      # Vivado FPGA project
│   ├── src/
│   │   ├── fhss_engine/
│   │   ├── channelizer/
│   │   ├── modem/
│   │   └── tdma_mac/
│   ├── constraints/
│   └── ip/
├── software/                  # C++ application
│   ├── CMakeLists.txt
│   ├── src/
│   │   ├── core/              # SCA framework
│   │   ├── waveforms/         # Loadable .so waveform plugins
│   │   ├── network/           # Mesh networking
│   │   ├── security/          # Crypto & key management
│   │   ├── voice/             # Voice pipeline
│   │   ├── sa/                # Situational awareness
│   │   ├── hal/               # Hardware abstraction layer
│   │   └── mgmt/              # Management interface
│   ├── include/
│   ├── drivers/               # Linux kernel modules
│   ├── tests/
│   └── third_party/
├── firmware/                  # Boot firmware, device tree
├── docs/
│   └── plans/
└── tools/                     # Build scripts, flashing tools
```

### Key Design Decisions

- **Plugin architecture**: Waveforms compile to .so shared libraries, loaded at runtime.
- **HAL layer**: All hardware access through abstraction. Enables full software stack testing on desktop Linux with simulated RF.
- **Zero-copy data path**: FPGA DMA writes I/Q into shared memory. Waveform chain uses mmap'd ring buffers.
- **Real-time voice**: Dedicated SCHED_FIFO thread. JitterBuffer maintains <150 ms end-to-end latency.

### Dependencies

- Boost.Asio (async networking/timers)
- protobuf or FlatBuffers (message serialization)
- spdlog (logging)
- Catch2 (testing)
- libiio (AD9361 control)

## Development Phases

### Phase 1: Software on Desktop (No Hardware)

- SCA framework core in C++
- Simulated RF HAL (loopback I/Q over shared memory)
- Mesh networking stack with simulated nodes
- FHSS hop sequence generator (pure math, testable standalone)
- TDMA scheduler and slot allocation
- Mesh routing (OLSR adaptation) with simulated multi-node test harness
- Peer discovery and net join protocol
- Crypto engine interface with software AES-256-GCM placeholder
- Voice pipeline with Codec2 (open-source MELPe alternative for dev phase)
- CLI management shell
- Multi-node integration test (N simulated radios in one process)

### Phase 2: FPGA Development (Eval Board)

- ADRV9361-Z7035 SOM + carrier board
- Port FHSS engine, channelizer, modem to VHDL/Verilog
- AD9361 bring-up and RF loopback testing
- Integrate FPGA DSP with ARM software stack
- Two-radio bench test

### Phase 3: Custom Dev Board (KiCad)

- Schematic capture
- RF front-end (LNA, PA, filters, T/R switch)
- HSM integration + anti-tamper circuitry
- GPS module integration
- 8-layer stackup, controlled impedance RF traces
- Proto board fab + assembly
- Bring-up, RF characterization, EMC pre-scan

### Phase 4: Integration & Multi-Node Testing

- 4+ board mesh network field testing
- FHSS performance validation
- Voice quality testing
- Crypto integration with HSM hardware
- Security audit and penetration testing

### Phase 5: Miniaturization & Production Design

- Shrink to target form factor
- TEMPEST compliance design
- Environmental testing (temp, vibration, humidity)
- Type 1 certification process
- Production tooling

## Dev Board BOM Estimate

| Component | Approx Cost |
|-----------|-------------|
| ADRV9361-Z7035 SOM (eval, Phase 2) | $2,500 |
| Carrier board (eval, Phase 2) | $500 |
| Custom dev board PCB, 5 pcs (Phase 3) | $3,000 |
| AD9361 per board | $200 |
| Zynq-7045 per board | $500 |
| PA module + RF components per board | $300 |
| HSM module per board | $150 |
| GPS module per board | $30 |
| Passives, connectors, misc per board | $200 |
| **Per custom board total** | **~$1,400** |
