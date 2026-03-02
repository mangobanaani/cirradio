#pragma once
#include "RouteTable.h"
#include "LinkState.h"
#include <map>

namespace cirradio::network {

class MeshRouter {
public:
    explicit MeshRouter(uint32_t local_id);

    // Process a received link-state advertisement.
    // Returns true if the advertisement was new (caused a table update).
    bool process_advertisement(const LinkStateAdvertisement& lsa);

    // Generate our own link-state advertisement.
    LinkStateAdvertisement generate_advertisement() const;

    // Add/update a direct neighbor link (from local measurements).
    void update_neighbor(uint32_t neighbor_id, float quality);

    // Remove a neighbor (e.g., heartbeat timeout).
    void remove_neighbor(uint32_t neighbor_id);

    // Get route to destination.
    std::optional<RouteEntry> route_to(uint32_t destination) const;

    // Get list of direct neighbors.
    std::vector<uint32_t> neighbors() const;

    // Get all known nodes in the mesh.
    std::vector<uint32_t> known_nodes() const;

    uint32_t local_id() const { return local_id_; }

private:
    uint32_t local_id_;
    uint32_t sequence_ = 0;
    RouteTable table_;
    std::map<uint32_t, float> direct_neighbors_;  // neighbor_id -> quality
    std::map<uint32_t, uint32_t> last_sequence_;   // node_id -> last seen sequence
};

}  // namespace cirradio::network
