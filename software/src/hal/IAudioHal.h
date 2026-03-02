#pragma once
#include <vector>
#include <cstdint>
#include <span>

namespace cirradio::hal {

class IAudioHal {
public:
    virtual ~IAudioHal() = default;
    virtual std::vector<int16_t> capture(size_t num_samples) = 0;
    virtual bool playback(std::span<const int16_t> samples) = 0;
    virtual bool set_volume(float level) = 0;  // 0.0 to 1.0
};

}  // namespace cirradio::hal
