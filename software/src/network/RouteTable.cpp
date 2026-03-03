#include "network/RouteTable.h"
#include <algorithm>
#include <queue>

namespace cirradio::network {

RouteTable::RouteTable(uint32_t local_id)
    : local_id_(local_id) {}

void RouteTable::update_link(uint32_t from, uint32_t to, float quality) {
    auto update_adj = [&](uint32_t a, uint32_t b, float q) {
        auto& neighbors = adjacency_[a];
        auto it = std::find_if(neighbors.begin(), neighbors.end(),
            [b](const auto& p) { return p.first == b; });
        if (it != neighbors.end()) {
            it->second = q;
        } else {
            neighbors.emplace_back(b, q);
        }
    };

    update_adj(from, to, quality);
    update_adj(to, from, quality);
}

void RouteTable::remove_node(uint32_t node_id) {
    adjacency_.erase(node_id);

    // Remove all links pointing to this node
    for (auto& [id, neighbors] : adjacency_) {
        neighbors.erase(
            std::remove_if(neighbors.begin(), neighbors.end(),
                [node_id](const auto& p) { return p.first == node_id; }),
            neighbors.end());
    }
}

void RouteTable::recompute() {
    routes_.clear();

    // Dijkstra maximizing path quality (product of link qualities)
    // quality[node] = best known path quality from local_id_ to node
    std::map<uint32_t, float> quality;
    std::map<uint32_t, uint32_t> predecessor;

    // Priority queue: (quality, node_id), highest quality first
    using Entry = std::pair<float, uint32_t>;
    std::priority_queue<Entry> pq;

    quality[local_id_] = 1.0f;
    pq.push({1.0f, local_id_});

    while (!pq.empty()) {
        auto [q, u] = pq.top();
        pq.pop();

        // Skip if we already found a better path
        if (q < quality[u]) {
            continue;
        }

        auto adj_it = adjacency_.find(u);
        if (adj_it == adjacency_.end()) {
            continue;
        }

        for (const auto& [v, link_q] : adj_it->second) {
            float new_quality = q * link_q;
            auto it = quality.find(v);
            if (it == quality.end() || new_quality > it->second) {
                quality[v] = new_quality;
                predecessor[v] = u;
                pq.push({new_quality, v});
            }
        }
    }

    // Build route entries from predecessor chain
    for (const auto& [dest, q] : quality) {
        if (dest == local_id_) {
            continue;  // no route to self
        }

        // Trace back from destination to find next_hop and hop_count
        uint32_t current = dest;
        uint32_t hops = 0;
        while (predecessor.count(current) && predecessor[current] != local_id_) {
            current = predecessor[current];
            ++hops;
        }
        ++hops;  // count the final hop to the first neighbor

        RouteEntry entry;
        entry.destination = dest;
        entry.next_hop = current;  // first hop from local_id_
        entry.hop_count = hops;
        entry.path_quality = q;
        routes_[dest] = entry;
    }
}

std::optional<RouteEntry> RouteTable::next_hop(uint32_t destination) const {
    auto it = routes_.find(destination);
    if (it == routes_.end()) {
        return std::nullopt;
    }
    return it->second;
}

std::vector<RouteEntry> RouteTable::all_routes() const {
    std::vector<RouteEntry> result;
    result.reserve(routes_.size());
    for (const auto& [id, entry] : routes_) {
        result.push_back(entry);
    }
    return result;
}

std::vector<uint32_t> RouteTable::known_nodes() const {
    std::vector<uint32_t> nodes;
    for (const auto& [id, _] : adjacency_) {
        nodes.push_back(id);
    }
    return nodes;
}

}  // namespace cirradio::network
