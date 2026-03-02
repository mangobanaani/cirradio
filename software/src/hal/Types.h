#pragma once
#include <cstdint>
#include <complex>
#include <vector>
#include <span>
#include <chrono>
#include <optional>

namespace cirradio::hal {

using Sample = std::complex<float>;
using SampleBuffer = std::span<Sample>;
using ConstSampleBuffer = std::span<const Sample>;
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
    Frequency center_freq;
    uint32_t sample_rate;
    uint32_t bandwidth;
    PowerLevel tx_power;
};

}  // namespace cirradio::hal
