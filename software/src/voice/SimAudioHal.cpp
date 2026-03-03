#include "voice/SimAudioHal.h"
#include <algorithm>

namespace cirradio::voice {

std::vector<int16_t> SimAudioHal::capture(size_t num_samples) {
    size_t available = std::min(num_samples, capture_buffer_.size());
    std::vector<int16_t> result(available);
    for (size_t i = 0; i < available; ++i) {
        result[i] = capture_buffer_.front();
        capture_buffer_.pop_front();
    }
    // If fewer samples available than requested, pad with silence
    result.resize(num_samples, 0);
    return result;
}

bool SimAudioHal::playback(std::span<const int16_t> samples) {
    played_buffer_.insert(played_buffer_.end(), samples.begin(), samples.end());
    return true;
}

bool SimAudioHal::set_volume(float level) {
    if (level < 0.0f || level > 1.0f) {
        return false;
    }
    volume_ = level;
    return true;
}

void SimAudioHal::inject_capture_data(const std::vector<int16_t>& samples) {
    capture_buffer_.insert(capture_buffer_.end(), samples.begin(), samples.end());
}

std::vector<int16_t> SimAudioHal::get_played_data() {
    auto data = std::move(played_buffer_);
    played_buffer_.clear();
    return data;
}

}  // namespace cirradio::voice
