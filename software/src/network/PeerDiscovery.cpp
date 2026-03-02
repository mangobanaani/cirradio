#include "network/PeerDiscovery.h"
#include <algorithm>

namespace cirradio::network {

PeerDiscovery::PeerDiscovery(uint32_t node_id, uint32_t net_id)
    : node_id_(node_id), net_id_(net_id) {}

DiscoveryBeacon PeerDiscovery::generate_beacon(uint8_t current_node_count) const {
    DiscoveryBeacon beacon;
    beacon.node_id = node_id_;
    beacon.net_id = net_id_;
    beacon.num_nodes = current_node_count;
    beacon.timestamp = std::chrono::steady_clock::now();
    return beacon;
}

bool PeerDiscovery::process_beacon(const DiscoveryBeacon& beacon) {
    // Ignore beacons from ourselves
    if (beacon.node_id == node_id_) {
        return false;
    }

    auto [it, inserted] = discovered_.emplace(beacon.node_id, beacon.timestamp);
    if (!inserted) {
        // Already known - update timestamp
        it->second = beacon.timestamp;
        return false;
    }
    return true;
}

std::vector<uint32_t> PeerDiscovery::discovered_nodes() const {
    std::vector<uint32_t> result;
    result.reserve(discovered_.size());
    for (const auto& [id, _] : discovered_) {
        result.push_back(id);
    }
    return result;
}

void PeerDiscovery::expire_stale(std::chrono::steady_clock::duration timeout) {
    auto now = std::chrono::steady_clock::now();
    for (auto it = discovered_.begin(); it != discovered_.end(); ) {
        if ((now - it->second) > timeout) {
            it = discovered_.erase(it);
        } else {
            ++it;
        }
    }
}

}  // namespace cirradio::network
