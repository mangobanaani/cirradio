# Phase 1: Desktop Software Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete CIRRADIO C++ software stack running on desktop Linux with simulated RF, enabling multi-node mesh networking, FHSS, encrypted voice/data, and full SCA framework -- all without hardware.

**Architecture:** HAL abstraction layer with simulated backends allows the entire stack to run on desktop. Simulated RF uses shared-memory ring buffers for I/Q loopback between virtual nodes. All components are testable independently via Catch2.

**Tech Stack:** C++17, CMake 3.20+, Catch2 (testing), spdlog (logging), Boost.Asio (async I/O), OpenSSL (AES-256-GCM placeholder), Codec2 (voice), FlatBuffers (serialization)

---

### Task 1: Project Scaffold & Build System

**Files:**
- Create: `software/CMakeLists.txt`
- Create: `software/src/main.cpp`
- Create: `software/tests/CMakeLists.txt`
- Create: `software/tests/test_main.cpp`
- Create: `software/cmake/toolchain-zynq.cmake`
- Create: `.gitignore`

**Step 1: Create root CMakeLists.txt**

```cmake
cmake_minimum_required(VERSION 3.20)
project(cirradio VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(CIRRADIO_BUILD_TESTS "Build tests" ON)
option(CIRRADIO_SIMULATE "Build with simulated HAL" ON)

find_package(Threads REQUIRED)
find_package(spdlog REQUIRED)
find_package(Boost REQUIRED COMPONENTS system)
find_package(OpenSSL REQUIRED)

add_subdirectory(src)

if(CIRRADIO_BUILD_TESTS)
    enable_testing()
    find_package(Catch2 3 REQUIRED)
    add_subdirectory(tests)
endif()
```

**Step 2: Create minimal main.cpp**

```cpp
#include <spdlog/spdlog.h>

int main(int argc, char* argv[]) {
    spdlog::info("CIRRADIO v0.1.0 starting");
    return 0;
}
```

**Step 3: Create test scaffold with a smoke test**

`software/tests/test_main.cpp`:
```cpp
#include <catch2/catch_test_macros.hpp>

TEST_CASE("smoke test", "[core]") {
    REQUIRE(1 + 1 == 2);
}
```

`software/tests/CMakeLists.txt`:
```cmake
add_executable(cirradio_tests test_main.cpp)
target_link_libraries(cirradio_tests PRIVATE Catch2::Catch2WithMain)
include(Catch2::Catch)
catch_discover_tests(cirradio_tests)
```

**Step 4: Create .gitignore and cross-compilation toolchain stub**

**Step 5: Build and run smoke test**

Run: `cd software && mkdir -p build && cd build && cmake .. && make -j$(nproc) && ctest --output-on-failure`
Expected: All tests pass.

**Step 6: Commit**

```
git add software/ .gitignore
git commit -m "scaffold cmake project with catch2 test harness"
```

---

### Task 2: HAL Interfaces

**Files:**
- Create: `software/src/hal/IRadioHal.h`
- Create: `software/src/hal/ICryptoHal.h`
- Create: `software/src/hal/IGpsHal.h`
- Create: `software/src/hal/IAudioHal.h`
- Create: `software/src/hal/Types.h`

**Step 1: Define common types**

`software/src/hal/Types.h`:
```cpp
#pragma once
#include <cstdint>
#include <complex>
#include <vector>
#include <span>
#include <chrono>

namespace cirradio::hal {

using Sample = std::complex<float>;  // I/Q sample
using SampleBuffer = std::span<Sample>;
using Frequency = uint64_t;  // Hz
using PowerLevel = float;    // dBm
using Timestamp = std::chrono::steady_clock::time_point;

struct GpsPosition {
    double latitude;
    double longitude;
    double altitude;
    Timestamp time;
    bool valid;
};

struct RadioConfig {
    Frequency center_freq;   // Hz
    uint32_t sample_rate;    // Hz
    uint32_t bandwidth;      // Hz
    PowerLevel tx_power;     // dBm
};

}  // namespace cirradio::hal
```

**Step 2: Define IRadioHal interface**

```cpp
#pragma once
#include "Types.h"
#include <functional>

namespace cirradio::hal {

class IRadioHal {
public:
    virtual ~IRadioHal() = default;
    virtual bool configure(const RadioConfig& config) = 0;
    virtual bool tune(Frequency freq) = 0;
    virtual bool set_tx_power(PowerLevel power_dbm) = 0;
    virtual bool transmit(SampleBuffer samples) = 0;
    virtual size_t receive(SampleBuffer buffer) = 0;
    virtual bool set_tx_enabled(bool enabled) = 0;
    virtual RadioConfig current_config() const = 0;
};

}  // namespace cirradio::hal
```

**Step 3: Define ICryptoHal, IGpsHal, IAudioHal** (similar pure virtual interfaces)

**Step 4: Write tests that verify mock implementations compile against interfaces**

`software/tests/test_hal_interfaces.cpp`:
```cpp
#include <catch2/catch_test_macros.hpp>
#include "hal/IRadioHal.h"
#include "hal/ICryptoHal.h"
#include "hal/IGpsHal.h"
#include "hal/IAudioHal.h"

// Minimal mock to verify interface compiles
class MockRadioHal : public cirradio::hal::IRadioHal {
public:
    bool configure(const cirradio::hal::RadioConfig&) override { return true; }
    bool tune(cirradio::hal::Frequency) override { return true; }
    bool set_tx_power(cirradio::hal::PowerLevel) override { return true; }
    bool transmit(cirradio::hal::SampleBuffer) override { return true; }
    size_t receive(cirradio::hal::SampleBuffer buf) override { return 0; }
    bool set_tx_enabled(bool) override { return true; }
    cirradio::hal::RadioConfig current_config() const override { return {}; }
};

TEST_CASE("HAL interfaces are implementable", "[hal]") {
    MockRadioHal radio;
    REQUIRE(radio.configure({}) == true);
}
```

**Step 5: Build and test**

Run: `cmake --build build && ctest --output-on-failure`
Expected: PASS

**Step 6: Commit**

```
git commit -m "add HAL interfaces for radio, crypto, gps, audio"
```

---

### Task 3: Simulated Radio HAL

**Files:**
- Create: `software/src/hal/SimRadioHal.h`
- Create: `software/src/hal/SimRadioHal.cpp`
- Create: `software/src/hal/SimChannel.h`
- Create: `software/src/hal/SimChannel.cpp`
- Create: `software/tests/test_sim_radio.cpp`

**Step 1: Write failing test for SimChannel (shared medium)**

SimChannel models a shared RF medium. Multiple SimRadioHal instances connect to it. When one transmits, others on the same frequency receive.

```cpp
TEST_CASE("SimChannel delivers samples between two radios", "[hal][sim]") {
    auto channel = std::make_shared<cirradio::hal::SimChannel>();
    cirradio::hal::SimRadioHal radio_a(channel, 1);
    cirradio::hal::SimRadioHal radio_b(channel, 2);

    cirradio::hal::RadioConfig cfg{};
    cfg.center_freq = 300'000'000;  // 300 MHz
    cfg.sample_rate = 1'000'000;
    cfg.bandwidth = 1'000'000;
    radio_a.configure(cfg);
    radio_b.configure(cfg);

    std::vector<cirradio::hal::Sample> tx_buf(100, {1.0f, 0.5f});
    radio_a.set_tx_enabled(true);
    radio_a.transmit(tx_buf);

    std::vector<cirradio::hal::Sample> rx_buf(100);
    size_t n = radio_b.receive(rx_buf);
    REQUIRE(n == 100);
    REQUIRE(rx_buf[0].real() == Catch::Approx(1.0f));
}
```

**Step 2: Run test, verify it fails (classes don't exist yet)**

**Step 3: Implement SimChannel** (thread-safe ring buffer per frequency, mutex-protected) and SimRadioHal (stores config, routes TX to channel, reads RX from channel).

**Step 4: Run test, verify pass**

**Step 5: Add test for frequency isolation** (radio on different freq should not receive)

**Step 6: Commit**

```
git commit -m "add simulated radio HAL with shared channel medium"
```

---

### Task 4: Crypto Engine (Software AES-256-GCM)

**Files:**
- Create: `software/src/security/CryptoEngine.h`
- Create: `software/src/security/CryptoEngine.cpp`
- Create: `software/src/security/SoftCryptoHal.h`
- Create: `software/src/security/SoftCryptoHal.cpp`
- Create: `software/tests/test_crypto.cpp`

**Step 1: Write failing test for encrypt/decrypt roundtrip**

```cpp
TEST_CASE("AES-256-GCM encrypt then decrypt roundtrip", "[security]") {
    cirradio::security::CryptoEngine engine;
    std::vector<uint8_t> key(32, 0xAB);  // 256-bit key
    std::vector<uint8_t> plaintext = {'H','e','l','l','o'};

    auto encrypted = engine.encrypt(key, plaintext);
    REQUIRE(encrypted.has_value());
    REQUIRE(encrypted->size() > plaintext.size());  // IV + ciphertext + tag

    auto decrypted = engine.decrypt(key, *encrypted);
    REQUIRE(decrypted.has_value());
    REQUIRE(*decrypted == plaintext);
}

TEST_CASE("AES-256-GCM detects tampered ciphertext", "[security]") {
    cirradio::security::CryptoEngine engine;
    std::vector<uint8_t> key(32, 0xAB);
    std::vector<uint8_t> plaintext = {'T','e','s','t'};

    auto encrypted = engine.encrypt(key, plaintext);
    REQUIRE(encrypted.has_value());

    (*encrypted)[20] ^= 0xFF;  // flip a byte

    auto decrypted = engine.decrypt(key, *encrypted);
    REQUIRE_FALSE(decrypted.has_value());  // must fail authentication
}
```

**Step 2: Run test, verify fails**

**Step 3: Implement CryptoEngine** using OpenSSL EVP API for AES-256-GCM. Format: 12-byte IV || ciphertext || 16-byte GCM tag.

**Step 4: Run tests, verify pass**

**Step 5: Add test for key hierarchy** (KEK wrapping a TEK)

```cpp
TEST_CASE("KEK wraps and unwraps TEK", "[security]") {
    cirradio::security::CryptoEngine engine;
    std::vector<uint8_t> kek(32, 0x11);
    std::vector<uint8_t> tek(32, 0x22);

    auto wrapped = engine.wrap_key(kek, tek);
    REQUIRE(wrapped.has_value());

    auto unwrapped = engine.unwrap_key(kek, *wrapped);
    REQUIRE(unwrapped.has_value());
    REQUIRE(*unwrapped == tek);
}
```

**Step 6: Implement wrap_key / unwrap_key (AES key wrap or just encrypt with GCM)**

**Step 7: Commit**

```
git commit -m "add crypto engine with AES-256-GCM encrypt/decrypt and key wrap"
```

---

### Task 5: FHSS Hop Sequence Generator

**Files:**
- Create: `software/src/fhss/HopSequencer.h`
- Create: `software/src/fhss/HopSequencer.cpp`
- Create: `software/tests/test_hop_sequencer.cpp`

**Step 1: Write failing test for deterministic hop sequence**

```cpp
TEST_CASE("Hop sequence is deterministic given same key and frame", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xAA);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);
    // args: key, min_freq, max_freq, channel_spacing

    auto freq_a = seq.get_hop_frequency(/*slot=*/0, /*frame=*/100);
    auto freq_b = seq.get_hop_frequency(/*slot=*/0, /*frame=*/100);
    REQUIRE(freq_a == freq_b);  // same input = same output

    auto freq_c = seq.get_hop_frequency(/*slot=*/1, /*frame=*/100);
    REQUIRE(freq_a != freq_c);  // different slot = different freq
}

TEST_CASE("Hop frequencies stay within band", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xBB);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);

    for (uint32_t frame = 0; frame < 1000; ++frame) {
        for (uint8_t slot = 0; slot < 20; ++slot) {
            auto freq = seq.get_hop_frequency(slot, frame);
            REQUIRE(freq >= 225'000'000);
            REQUIRE(freq <= 512'000'000);
        }
    }
}

TEST_CASE("Different keys produce different sequences", "[fhss]") {
    std::vector<uint8_t> key_a(32, 0xAA);
    std::vector<uint8_t> key_b(32, 0xBB);
    cirradio::fhss::HopSequencer seq_a(key_a, 225'000'000, 512'000'000, 1'000'000);
    cirradio::fhss::HopSequencer seq_b(key_b, 225'000'000, 512'000'000, 1'000'000);

    bool any_different = false;
    for (uint32_t f = 0; f < 100; ++f) {
        if (seq_a.get_hop_frequency(0, f) != seq_b.get_hop_frequency(0, f)) {
            any_different = true;
            break;
        }
    }
    REQUIRE(any_different);
}
```

**Step 2: Run test, verify fails**

**Step 3: Implement HopSequencer**

Core algorithm: `AES-256-ECB(FHEK, slot_index || frame_count)` -> take first 8 bytes as uint64 -> modulo into channel grid -> add to min_freq.

```cpp
Frequency HopSequencer::get_hop_frequency(uint8_t slot, uint32_t frame) const {
    uint8_t input[16] = {};
    std::memcpy(input, &slot, 1);
    std::memcpy(input + 4, &frame, 4);

    uint8_t output[16];
    // AES-256-ECB encrypt single block
    aes_ecb_encrypt(fhek_.data(), input, output);

    uint64_t raw;
    std::memcpy(&raw, output, 8);

    uint64_t num_channels = (max_freq_ - min_freq_) / channel_spacing_;
    uint64_t channel = raw % num_channels;
    return min_freq_ + channel * channel_spacing_;
}
```

**Step 4: Run tests, verify pass**

**Step 5: Add test for adaptive blacklisting**

```cpp
TEST_CASE("Blacklisted frequencies are skipped", "[fhss]") {
    std::vector<uint8_t> fhek(32, 0xCC);
    cirradio::fhss::HopSequencer seq(fhek, 225'000'000, 512'000'000, 1'000'000);

    auto original = seq.get_hop_frequency(0, 0);
    seq.blacklist_frequency(original);
    auto replacement = seq.get_hop_frequency(0, 0);
    REQUIRE(replacement != original);
    REQUIRE(replacement >= 225'000'000);
    REQUIRE(replacement <= 512'000'000);
}
```

**Step 6: Implement blacklisting (skip + rehash to next channel)**

**Step 7: Commit**

```
git commit -m "add FHSS hop sequence generator with blacklisting"
```

---

### Task 6: TDMA Frame & Slot Scheduler

**Files:**
- Create: `software/src/tdma/Frame.h`
- Create: `software/src/tdma/SlotScheduler.h`
- Create: `software/src/tdma/SlotScheduler.cpp`
- Create: `software/tests/test_tdma.cpp`

**Step 1: Write failing test for frame structure**

```cpp
TEST_CASE("Frame has 20 slots with correct types", "[tdma]") {
    cirradio::tdma::Frame frame(/*frame_number=*/0);
    REQUIRE(frame.slot_count() == 20);
    REQUIRE(frame.slot_type(0) == cirradio::tdma::SlotType::Beacon);
    REQUIRE(frame.slot_type(1) == cirradio::tdma::SlotType::Traffic);
    REQUIRE(frame.slot_type(15) == cirradio::tdma::SlotType::DataOnly);
    REQUIRE(frame.slot_type(18) == cirradio::tdma::SlotType::KeyMgmt);
    REQUIRE(frame.slot_type(19) == cirradio::tdma::SlotType::Discovery);
}
```

**Step 2: Run, verify fails**

**Step 3: Implement Frame struct** with slot type enum matching the design (0=Beacon, 1-14=Traffic, 15-17=DataOnly, 18=KeyMgmt, 19=Discovery).

**Step 4: Run, verify pass**

**Step 5: Write failing test for slot claiming**

```cpp
TEST_CASE("Node can claim and release traffic slots", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler(/*node_id=*/1);
    REQUIRE(scheduler.claim_slot(5));    // claim slot 5
    REQUIRE(scheduler.owner_of(5) == 1);
    REQUIRE_FALSE(scheduler.claim_slot(0));  // can't claim beacon
    REQUIRE_FALSE(scheduler.claim_slot(19)); // can't claim discovery

    scheduler.release_slot(5);
    REQUIRE(scheduler.owner_of(5) == 0);  // 0 = unclaimed
}

TEST_CASE("Beacon controller rotates", "[tdma]") {
    cirradio::tdma::SlotScheduler scheduler(/*node_id=*/1);
    std::vector<uint8_t> node_list = {1, 2, 3};
    REQUIRE(scheduler.beacon_controller(/*frame=*/0, node_list) == 1);
    REQUIRE(scheduler.beacon_controller(/*frame=*/1, node_list) == 2);
    REQUIRE(scheduler.beacon_controller(/*frame=*/2, node_list) == 3);
    REQUIRE(scheduler.beacon_controller(/*frame=*/3, node_list) == 1);
}
```

**Step 6: Implement SlotScheduler**

**Step 7: Run, verify pass**

**Step 8: Commit**

```
git commit -m "add TDMA frame structure and slot scheduler"
```

---

### Task 7: SCA Core Framework

**Files:**
- Create: `software/src/core/Component.h`
- Create: `software/src/core/ComponentManager.h`
- Create: `software/src/core/ComponentManager.cpp`
- Create: `software/src/core/WaveformLoader.h`
- Create: `software/src/core/WaveformLoader.cpp`
- Create: `software/src/core/PropertyService.h`
- Create: `software/tests/test_sca_core.cpp`

**Step 1: Write failing test for component lifecycle**

```cpp
TEST_CASE("Component lifecycle: configure -> start -> stop -> release", "[sca]") {
    auto comp = std::make_shared<TestComponent>();
    cirradio::core::ComponentManager mgr;

    mgr.register_component("test", comp);
    REQUIRE(comp->state() == cirradio::core::ComponentState::Idle);

    mgr.configure("test");
    REQUIRE(comp->state() == cirradio::core::ComponentState::Configured);

    mgr.start("test");
    REQUIRE(comp->state() == cirradio::core::ComponentState::Running);

    mgr.stop("test");
    REQUIRE(comp->state() == cirradio::core::ComponentState::Idle);
}
```

Where TestComponent inherits from Component base class with virtual `on_configure()`, `on_start()`, `on_stop()`.

**Step 2: Run, verify fails**

**Step 3: Implement Component base class and ComponentManager**

**Step 4: Run, verify pass**

**Step 5: Write failing test for property service**

```cpp
TEST_CASE("PropertyService stores and retrieves typed properties", "[sca]") {
    cirradio::core::PropertyService props;
    props.set("radio.freq", uint64_t{300'000'000});
    props.set("radio.name", std::string{"alpha"});

    REQUIRE(props.get<uint64_t>("radio.freq") == 300'000'000);
    REQUIRE(props.get<std::string>("radio.name") == "alpha");
    REQUIRE_THROWS(props.get<uint64_t>("nonexistent"));
}
```

**Step 6: Implement PropertyService (map<string, variant>)**

**Step 7: Run, verify pass**

**Step 8: Commit**

```
git commit -m "add SCA core framework with component manager and property service"
```

---

### Task 8: Mesh Router (OLSR Adaptation)

**Files:**
- Create: `software/src/network/LinkState.h`
- Create: `software/src/network/RouteTable.h`
- Create: `software/src/network/RouteTable.cpp`
- Create: `software/src/network/MeshRouter.h`
- Create: `software/src/network/MeshRouter.cpp`
- Create: `software/tests/test_mesh_router.cpp`

**Step 1: Write failing test for route computation (Dijkstra)**

```cpp
TEST_CASE("RouteTable computes shortest path", "[network]") {
    cirradio::network::RouteTable table(/*local_id=*/1);

    // Node 1 can reach Node 2 (quality 0.9) and Node 3 (quality 0.5)
    // Node 2 can reach Node 3 (quality 0.8)
    table.update_link(1, 2, 0.9f);
    table.update_link(1, 3, 0.5f);
    table.update_link(2, 3, 0.8f);

    table.recompute();

    auto route_to_2 = table.next_hop(/*destination=*/2);
    REQUIRE(route_to_2.has_value());
    REQUIRE(route_to_2->next_hop == 2);
    REQUIRE(route_to_2->hop_count == 1);

    auto route_to_3 = table.next_hop(/*destination=*/3);
    REQUIRE(route_to_3.has_value());
    // Should prefer 1->2->3 (0.9*0.8=0.72) over 1->3 (0.5)
    REQUIRE(route_to_3->next_hop == 2);
    REQUIRE(route_to_3->hop_count == 2);
}

TEST_CASE("RouteTable handles node disappearance", "[network]") {
    cirradio::network::RouteTable table(/*local_id=*/1);
    table.update_link(1, 2, 0.9f);
    table.update_link(2, 3, 0.8f);
    table.recompute();
    REQUIRE(table.next_hop(3).has_value());

    table.remove_node(2);
    table.recompute();
    REQUIRE_FALSE(table.next_hop(3).has_value());
}
```

**Step 2: Run, verify fails**

**Step 3: Implement RouteTable** with Dijkstra over link quality metric (higher is better, multiply along path).

**Step 4: Run, verify pass**

**Step 5: Write failing test for MeshRouter** (processes link-state advertisements, updates table)

**Step 6: Implement MeshRouter**

**Step 7: Run, verify pass**

**Step 8: Commit**

```
git commit -m "add mesh router with OLSR-style link state routing"
```

---

### Task 9: Peer Discovery & Net Join Protocol

**Files:**
- Create: `software/src/network/PeerDiscovery.h`
- Create: `software/src/network/PeerDiscovery.cpp`
- Create: `software/src/network/NetJoin.h`
- Create: `software/src/network/NetJoin.cpp`
- Create: `software/src/network/Messages.h`
- Create: `software/tests/test_net_join.cpp`

**Step 1: Write failing test for challenge-response join**

```cpp
TEST_CASE("Net join: challenge-response authentication", "[network]") {
    // Existing node (responder)
    cirradio::network::NetJoin responder(/*node_id=*/1, trusted_keys);
    // New node (joiner)
    cirradio::network::NetJoin joiner(/*node_id=*/2, own_identity_key);

    // Step 1: joiner sends join request
    auto join_req = joiner.create_join_request();

    // Step 2: responder creates challenge
    auto challenge = responder.create_challenge(join_req);
    REQUIRE(challenge.nonce.size() == 32);

    // Step 3: joiner signs challenge
    auto response = joiner.sign_challenge(challenge);

    // Step 4: responder verifies and provides keys
    auto result = responder.verify_and_accept(response);
    REQUIRE(result.accepted);
    REQUIRE(result.tek.size() == 32);
    REQUIRE(result.fhek.size() == 32);
}

TEST_CASE("Net join rejects unknown node", "[network]") {
    cirradio::network::NetJoin responder(/*node_id=*/1, trusted_keys);
    // Untrusted node
    auto join_req = untrusted_joiner.create_join_request();
    auto challenge = responder.create_challenge(join_req);
    auto response = untrusted_joiner.sign_challenge(challenge);
    auto result = responder.verify_and_accept(response);
    REQUIRE_FALSE(result.accepted);
}
```

**Step 2: Run, verify fails**

**Step 3: Implement Messages.h** (FlatBuffers or plain structs for JoinRequest, Challenge, ChallengeResponse, JoinAccept)

**Step 4: Implement NetJoin** with ECDSA P-384 signing via OpenSSL

**Step 5: Run, verify pass**

**Step 6: Write test for PeerDiscovery** (beacon broadcasting on rendezvous slot, timeout handling)

**Step 7: Implement PeerDiscovery**

**Step 8: Commit**

```
git commit -m "add peer discovery and authenticated net join protocol"
```

---

### Task 10: Voice Pipeline

**Files:**
- Create: `software/src/voice/AudioCapture.h`
- Create: `software/src/voice/AudioCapture.cpp`
- Create: `software/src/voice/VoiceCodec.h`
- Create: `software/src/voice/VoiceCodec.cpp`
- Create: `software/src/voice/JitterBuffer.h`
- Create: `software/src/voice/JitterBuffer.cpp`
- Create: `software/src/voice/VoicePipeline.h`
- Create: `software/src/voice/VoicePipeline.cpp`
- Create: `software/tests/test_voice.cpp`

**Step 1: Write failing test for Codec2 encode/decode roundtrip**

```cpp
TEST_CASE("Codec2 encode/decode roundtrip preserves audio", "[voice]") {
    cirradio::voice::VoiceCodec codec(cirradio::voice::CodecMode::Codec2_1200);

    // 20ms of 8kHz audio = 160 samples
    std::vector<int16_t> input(160);
    // Fill with a 1kHz sine wave
    for (int i = 0; i < 160; ++i) {
        input[i] = static_cast<int16_t>(16000.0 * std::sin(2.0 * M_PI * 1000.0 * i / 8000.0));
    }

    auto encoded = codec.encode(input);
    REQUIRE(encoded.size() > 0);
    REQUIRE(encoded.size() < input.size() * 2);  // must compress

    auto decoded = codec.decode(encoded);
    REQUIRE(decoded.size() == 160);
    // Lossy codec, so just check not all zeros
    bool has_signal = false;
    for (auto s : decoded) {
        if (std::abs(s) > 100) { has_signal = true; break; }
    }
    REQUIRE(has_signal);
}
```

**Step 2: Run, verify fails**

**Step 3: Implement VoiceCodec** wrapping libcodec2 (Codec2 at 1200 bps for low bandwidth tactical voice).

**Step 4: Run, verify pass**

**Step 5: Write failing test for JitterBuffer**

```cpp
TEST_CASE("JitterBuffer reorders out-of-order packets", "[voice]") {
    cirradio::voice::JitterBuffer jbuf(/*depth_ms=*/100, /*frame_ms=*/20);

    std::vector<int16_t> frame_a(160, 100);
    std::vector<int16_t> frame_b(160, 200);
    std::vector<int16_t> frame_c(160, 300);

    jbuf.push(/*seq=*/2, frame_c);
    jbuf.push(/*seq=*/0, frame_a);
    jbuf.push(/*seq=*/1, frame_b);

    auto out0 = jbuf.pop();
    REQUIRE(out0.has_value());
    REQUIRE((*out0)[0] == 100);  // frame_a first

    auto out1 = jbuf.pop();
    REQUIRE((*out1)[0] == 200);  // frame_b second
}
```

**Step 6: Implement JitterBuffer**

**Step 7: Run, verify pass**

**Step 8: Commit**

```
git commit -m "add voice pipeline with codec2 and jitter buffer"
```

---

### Task 11: Key Management & OTAR

**Files:**
- Create: `software/src/security/KeyManager.h`
- Create: `software/src/security/KeyManager.cpp`
- Create: `software/src/security/KeyStore.h`
- Create: `software/src/security/KeyStore.cpp`
- Create: `software/tests/test_key_manager.cpp`

**Step 1: Write failing test for key hierarchy**

```cpp
TEST_CASE("KeyManager manages key hierarchy", "[security]") {
    cirradio::security::KeyManager km;
    km.initialize_kek();  // generate random KEK

    auto tek = km.generate_tek();
    REQUIRE(tek.size() == 32);

    auto fhek = km.generate_fhek();
    REQUIRE(fhek.size() == 32);

    // Keys should be retrievable
    REQUIRE(km.current_tek() == tek);
    REQUIRE(km.current_fhek() == fhek);
}

TEST_CASE("TEK rotation produces new key", "[security]") {
    cirradio::security::KeyManager km;
    km.initialize_kek();
    auto tek1 = km.generate_tek();
    auto tek2 = km.rotate_tek();
    REQUIRE(tek1 != tek2);
    REQUIRE(km.current_tek() == tek2);
}

TEST_CASE("Zeroization clears all keys", "[security]") {
    cirradio::security::KeyManager km;
    km.initialize_kek();
    km.generate_tek();
    km.generate_fhek();

    km.zeroize();

    REQUIRE_THROWS(km.current_tek());
    REQUIRE_THROWS(km.current_fhek());
}
```

**Step 2: Run, verify fails**

**Step 3: Implement KeyManager and KeyStore** (in-memory for sim, wraps keys under KEK)

**Step 4: Run, verify pass**

**Step 5: Write test for OTAR message generation** (wrapped TEK for distribution)

**Step 6: Implement OTAR message create/parse**

**Step 7: Commit**

```
git commit -m "add key manager with key hierarchy, rotation, and zeroization"
```

---

### Task 12: CLI Management Shell

**Files:**
- Create: `software/src/mgmt/CLIShell.h`
- Create: `software/src/mgmt/CLIShell.cpp`
- Create: `software/tests/test_cli.cpp`

**Step 1: Write failing test for command parsing**

```cpp
TEST_CASE("CLI parses status command", "[mgmt]") {
    cirradio::mgmt::CLIShell cli;
    auto result = cli.execute("status");
    REQUIRE(result.success);
    REQUIRE(result.output.find("Node ID") != std::string::npos);
}

TEST_CASE("CLI parses set frequency command", "[mgmt]") {
    cirradio::mgmt::CLIShell cli;
    auto result = cli.execute("set freq 300000000");
    REQUIRE(result.success);
}

TEST_CASE("CLI rejects unknown command", "[mgmt]") {
    cirradio::mgmt::CLIShell cli;
    auto result = cli.execute("nonexistent");
    REQUIRE_FALSE(result.success);
}
```

**Step 2: Run, verify fails**

**Step 3: Implement CLIShell** with command map: `status`, `set freq <hz>`, `set power <dbm>`, `net join`, `net leave`, `net status`, `crypto zeroize`, `crypto rekey`.

**Step 4: Run, verify pass**

**Step 5: Commit**

```
git commit -m "add CLI management shell with command parser"
```

---

### Task 13: Node Integration (Single Virtual Radio)

**Files:**
- Create: `software/src/node/RadioNode.h`
- Create: `software/src/node/RadioNode.cpp`
- Create: `software/tests/test_radio_node.cpp`

**Step 1: Write failing test for RadioNode assembly**

RadioNode composes all subsystems: HAL, crypto, FHSS, TDMA, mesh router, voice, net join.

```cpp
TEST_CASE("RadioNode initializes all subsystems", "[node]") {
    auto channel = std::make_shared<cirradio::hal::SimChannel>();
    cirradio::node::RadioNode node(/*id=*/1, channel);

    REQUIRE(node.state() == cirradio::node::NodeState::Idle);
    node.start();
    REQUIRE(node.state() == cirradio::node::NodeState::Listening);
}
```

**Step 2: Run, verify fails**

**Step 3: Implement RadioNode** as the top-level composition that wires HAL, crypto, FHSS, TDMA, router, voice, and CLI together.

**Step 4: Run, verify pass**

**Step 5: Commit**

```
git commit -m "add RadioNode composing all subsystems"
```

---

### Task 14: Multi-Node Integration Test

**Files:**
- Create: `software/tests/test_integration_multinode.cpp`

**Step 1: Write test for two-node P2P communication**

```cpp
TEST_CASE("Two nodes discover each other and exchange data", "[integration]") {
    auto channel = std::make_shared<cirradio::hal::SimChannel>();
    cirradio::node::RadioNode node_a(1, channel);
    cirradio::node::RadioNode node_b(2, channel);

    // Pre-provision both with same TEK/FHEK for simplicity
    auto shared_tek = cirradio::security::generate_random_key(32);
    auto shared_fhek = cirradio::security::generate_random_key(32);
    node_a.provision_keys(shared_tek, shared_fhek);
    node_b.provision_keys(shared_tek, shared_fhek);

    node_a.start();
    node_b.start();

    // Simulate several frames to allow discovery
    for (int frame = 0; frame < 10; ++frame) {
        node_a.tick();
        node_b.tick();
    }

    REQUIRE(node_a.peers().size() == 1);
    REQUIRE(node_a.peers()[0] == 2);

    // Send data
    std::vector<uint8_t> message = {'P','I','N','G'};
    node_a.send_data(/*dest=*/2, message);

    // Tick to process
    node_a.tick();
    node_b.tick();

    auto received = node_b.receive_data();
    REQUIRE(received.has_value());
    REQUIRE(received->payload == message);
    REQUIRE(received->source == 1);
}
```

**Step 2: Run, verify fails (depends on all prior tasks)**

**Step 3: Fix integration issues** (this test exercises the full stack)

**Step 4: Run, verify pass**

**Step 5: Write test for mesh relay (3 nodes, A can't reach C directly)**

```cpp
TEST_CASE("Three-node mesh relay", "[integration]") {
    auto channel = std::make_shared<cirradio::hal::SimChannel>();
    // Node A and C are far apart, B is in the middle
    cirradio::node::RadioNode node_a(1, channel, /*range_limit=*/100);
    cirradio::node::RadioNode node_b(2, channel, /*range_limit=*/100);
    cirradio::node::RadioNode node_c(3, channel, /*range_limit=*/100);

    // Position: A at 0m, B at 80m, C at 160m
    // A<->B in range, B<->C in range, A<->C out of range
    node_a.set_position(0);
    node_b.set_position(80);
    node_c.set_position(160);

    provision_all({node_a, node_b, node_c});
    start_all({node_a, node_b, node_c});
    run_frames(30, {node_a, node_b, node_c});

    // A sends to C, should relay through B
    node_a.send_data(3, {'H','I'});
    run_frames(5, {node_a, node_b, node_c});

    auto received = node_c.receive_data();
    REQUIRE(received.has_value());
    REQUIRE(received->source == 1);
}
```

**Step 6: Fix relay routing in MeshRouter if needed**

**Step 7: Run, verify pass**

**Step 8: Commit**

```
git commit -m "add multi-node integration tests for p2p and mesh relay"
```

---

### Task 15: Voice Integration Test

**Files:**
- Create: `software/tests/test_integration_voice.cpp`

**Step 1: Write test for end-to-end encrypted voice**

```cpp
TEST_CASE("Encrypted voice from node A to node B", "[integration][voice]") {
    auto channel = std::make_shared<cirradio::hal::SimChannel>();
    cirradio::node::RadioNode node_a(1, channel);
    cirradio::node::RadioNode node_b(2, channel);

    provision_and_start({node_a, node_b});
    run_frames(10, {node_a, node_b});

    // Generate 20ms of test audio (1kHz sine)
    auto test_audio = generate_sine(1000, 8000, 160);

    node_a.voice_tx(/*dest=*/2, test_audio);
    run_frames(5, {node_a, node_b});

    auto rx_audio = node_b.voice_rx();
    REQUIRE(rx_audio.has_value());
    REQUIRE(rx_audio->size() == 160);
    // Verify audio has energy (lossy codec, can't compare exactly)
    REQUIRE(rms_energy(*rx_audio) > 100.0f);
}
```

**Step 2: Run, verify fails or passes (depends on pipeline wiring)**

**Step 3: Fix integration issues**

**Step 4: Commit**

```
git commit -m "add voice integration test for encrypted voice path"
```

---

## Task Dependency Order

```
Task 1 (scaffold)
  └─► Task 2 (HAL interfaces)
        ├─► Task 3 (sim radio HAL)
        └─► Task 4 (crypto engine)
              ├─► Task 5 (FHSS)
              ├─► Task 9 (net join)
              └─► Task 11 (key mgmt)
        Task 6 (TDMA) ──────────────┐
        Task 7 (SCA core)           │
        Task 8 (mesh router) ───────┤
        Task 10 (voice) ────────────┤
        Task 12 (CLI) ──────────────┤
                                    ▼
                            Task 13 (RadioNode)
                                    │
                              ┌─────┴─────┐
                              ▼           ▼
                        Task 14      Task 15
                     (multi-node)   (voice integ)
```

Tasks 5-12 can be parallelized after Tasks 1-4 are complete.
