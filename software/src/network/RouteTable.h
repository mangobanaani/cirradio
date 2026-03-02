#pragma once
#include "LinkState.h"
#include <map>
#include <optional>
#include <vector>

namespace cirradio::network {

class RouteTable {
public:
    explicit RouteTable(uint32_t local_id);

    // Update a link between two nodes. Bidirectional: adds both directions.
    void update_link(uint32_t from, uint32_t to, float quality);

    // Remove a node and all its links.
    void remove_node(uint32_t node_id);

    // Recompute shortest paths using Dijkstra over link quality.
    // Quality metric: path quality = product of link qualities.
    // Best path = highest quality product.
    void recompute();

    // Get the route to a destination (after recompute).
    std::optional<RouteEntry> next_hop(uint32_t destination) const;

    // Get all known routes.
    std::vector<RouteEntry> all_routes() const;

    // Get all known node IDs.
    std::vector<uint32_t> known_nodes() const;

private:
    uint32_t local_id_;
    // Adjacency: node -> [(neighbor, quality)]
    std::map<uint32_t, std::vector<std::pair<uint32_t, float>>> adjacency_;
    // Computed routes: destination -> RouteEntry
    std::map<uint32_t, RouteEntry> routes_;
};

}  // namespace cirradio::network
