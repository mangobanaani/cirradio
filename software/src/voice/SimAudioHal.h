#pragma once
#include "hal/IAudioHal.h"
#include <vector>
#include <deque>
#include <cstdint>

namespace cirradio::voice {

class SimAudioHal : public hal::IAudioHal {
public:
    std::vector<int16_t> capture(size_t num_samples) override;
    bool playback(std::span<const int16_t> samples) override;
    bool set_volume(float level) override;

    // Test helpers: inject audio for capture, read back played audio
    void inject_capture_data(const std::vector<int16_t>& samples);
    std::vector<int16_t> get_played_data();

private:
    std::deque<int16_t> capture_buffer_;
    std::vector<int16_t> played_buffer_;
    float volume_ = 1.0f;
};

}  // namespace cirradio::voice
