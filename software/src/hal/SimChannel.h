#pragma once
#include "Types.h"
#include <mutex>
#include <map>
#include <vector>
#include <deque>
#include <cstdint>

namespace cirradio::hal {

class SimChannel {
public:
    // Register a radio, returns an ID
    uint32_t register_radio();
    void unregister_radio(uint32_t radio_id);

    // Transmit samples on a frequency. All other radios tuned to that freq will receive them.
    void transmit(uint32_t sender_id, Frequency freq, const std::vector<Sample>& samples);

    // Receive samples for a specific radio on a frequency. Returns samples available (may be empty).
    std::vector<Sample> receive(uint32_t radio_id, Frequency freq, size_t max_samples);

    // Enable/disable partition mode: when active, 50% of frames are dropped.
    void set_partition_active(bool active);

private:
    std::mutex mutex_;
    uint32_t next_id_ = 1;
    bool partition_active_ = false;
    uint32_t transmit_count_ = 0;
    // Per-radio, per-frequency receive buffers
    // map<radio_id, map<frequency, deque<Sample>>>
    std::map<uint32_t, std::map<Frequency, std::deque<Sample>>> rx_buffers_;
    std::vector<uint32_t> registered_radios_;
};

}  // namespace cirradio::hal
