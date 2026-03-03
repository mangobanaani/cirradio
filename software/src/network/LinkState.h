#pragma once
#include <cstdint>
#include <vector>
#include <chrono>

namespace cirradio::network {

struct LinkInfo {
    uint32_t neighbor_id;
    float quality;  // 0.0 to 1.0, higher is better (based on RSSI/SNR)
};

struct LinkStateAdvertisement {
    uint32_t node_id;
    std::vector<LinkInfo> neighbors;
    uint32_t sequence;  // monotonically increasing per node
    std::chrono::steady_clock::time_point timestamp;
};

struct RouteEntry {
    uint32_t destination;
    uint32_t next_hop;
    uint32_t hop_count;
    float path_quality;  // product of link qualities along path
};

}  // namespace cirradio::network
