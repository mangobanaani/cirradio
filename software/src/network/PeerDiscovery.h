#pragma once
#include "Messages.h"
#include <vector>
#include <map>
#include <chrono>
#include <cstdint>

namespace cirradio::network {

class PeerDiscovery {
public:
    explicit PeerDiscovery(uint32_t node_id, uint32_t net_id = 0);

    // Generate a discovery beacon to broadcast
    DiscoveryBeacon generate_beacon(uint8_t current_node_count) const;

    // Process a received discovery beacon
    // Returns true if this is a new (previously unknown) node
    bool process_beacon(const DiscoveryBeacon& beacon);

    // Get list of discovered node IDs
    std::vector<uint32_t> discovered_nodes() const;

    // Remove nodes that haven't beaconed within timeout
    void expire_stale(std::chrono::steady_clock::duration timeout);

    uint32_t node_id() const { return node_id_; }

private:
    uint32_t node_id_;
    uint32_t net_id_;
    std::map<uint32_t, std::chrono::steady_clock::time_point> discovered_;
};

}  // namespace cirradio::network
