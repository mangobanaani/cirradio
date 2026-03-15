#include "hal/SimChannel.h"
#include <algorithm>

namespace cirradio::hal {

uint32_t SimChannel::register_radio() {
    std::lock_guard<std::mutex> lock(mutex_);
    uint32_t id = next_id_++;
    registered_radios_.push_back(id);
    rx_buffers_[id] = {};
    return id;
}

void SimChannel::unregister_radio(uint32_t radio_id) {
    std::lock_guard<std::mutex> lock(mutex_);
    registered_radios_.erase(
        std::remove(registered_radios_.begin(), registered_radios_.end(), radio_id),
        registered_radios_.end());
    rx_buffers_.erase(radio_id);
}

void SimChannel::set_partition_active(bool active) {
    std::lock_guard<std::mutex> lock(mutex_);
    partition_active_ = active;
    transmit_count_ = 0;
}

void SimChannel::transmit(uint32_t sender_id, Frequency freq, const std::vector<Sample>& samples) {
    std::lock_guard<std::mutex> lock(mutex_);
    // When partition is active, drop every other frame (toggle on transmit count).
    if (partition_active_) {
        ++transmit_count_;
        if (transmit_count_ % 2 == 0) {
            return;  // drop this frame
        }
    }
    for (uint32_t radio_id : registered_radios_) {
        if (radio_id == sender_id) {
            continue;
        }
        auto& buf = rx_buffers_[radio_id][freq];
        buf.insert(buf.end(), samples.begin(), samples.end());
    }
}

std::vector<Sample> SimChannel::receive(uint32_t radio_id, Frequency freq, size_t max_samples) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto radio_it = rx_buffers_.find(radio_id);
    if (radio_it == rx_buffers_.end()) {
        return {};
    }
    auto freq_it = radio_it->second.find(freq);
    if (freq_it == radio_it->second.end()) {
        return {};
    }
    auto& buf = freq_it->second;
    size_t count = std::min(max_samples, buf.size());
    std::vector<Sample> result(buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(count));
    buf.erase(buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(count));
    return result;
}

}  // namespace cirradio::hal
