#include "network/MeshRouter.h"

namespace cirradio::network {

MeshRouter::MeshRouter(uint32_t local_id)
    : local_id_(local_id), table_(local_id) {}

bool MeshRouter::process_advertisement(const LinkStateAdvertisement& lsa) {
    // Reject advertisements from ourselves
    if (lsa.node_id == local_id_) {
        return false;
    }

    // Reject stale advertisements (sequence <= last seen)
    auto it = last_sequence_.find(lsa.node_id);
    if (it != last_sequence_.end() && lsa.sequence <= it->second) {
        return false;
    }

    last_sequence_[lsa.node_id] = lsa.sequence;

    // Update the route table with the advertised links
    for (const auto& link : lsa.neighbors) {
        table_.update_link(lsa.node_id, link.neighbor_id, link.quality);
    }

    table_.recompute();
    return true;
}

LinkStateAdvertisement MeshRouter::generate_advertisement() const {
    LinkStateAdvertisement lsa;
    lsa.node_id = local_id_;
    lsa.sequence = sequence_;
    lsa.timestamp = std::chrono::steady_clock::now();

    for (const auto& [neighbor_id, quality] : direct_neighbors_) {
        lsa.neighbors.push_back({neighbor_id, quality});
    }

    return lsa;
}

void MeshRouter::update_neighbor(uint32_t neighbor_id, float quality) {
    direct_neighbors_[neighbor_id] = quality;
    table_.update_link(local_id_, neighbor_id, quality);
    table_.recompute();
}

void MeshRouter::remove_neighbor(uint32_t neighbor_id) {
    direct_neighbors_.erase(neighbor_id);
    table_.remove_node(neighbor_id);
    table_.recompute();
}

std::optional<RouteEntry> MeshRouter::route_to(uint32_t destination) const {
    return table_.next_hop(destination);
}

std::vector<uint32_t> MeshRouter::neighbors() const {
    std::vector<uint32_t> result;
    result.reserve(direct_neighbors_.size());
    for (const auto& [id, _] : direct_neighbors_) {
        result.push_back(id);
    }
    return result;
}

std::vector<uint32_t> MeshRouter::known_nodes() const {
    return table_.known_nodes();
}

}  // namespace cirradio::network
