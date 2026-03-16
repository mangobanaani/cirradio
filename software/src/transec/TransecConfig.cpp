// software/src/transec/TransecConfig.cpp
#include "transec/TransecConfig.h"

namespace cirradio::transec {

void TransecConfig::update_peer_rssi(uint32_t peer, float rssi_dbm,
                                     uint64_t now_ms) {
    if (peers_.size() >= kMaxPeers && peers_.find(peer) == peers_.end())
        return; // table full; ignore new peer
    auto& entry = peers_[peer];
    entry.peer               = peer;
    entry.rssi_dbm           = rssi_dbm;
    entry.required_power_dbm = rssi_dbm + link_margin_db_;
    entry.last_beacon_ms     = now_ms;
}

float TransecConfig::required_power_dbm(uint32_t peer) const {
    auto it = peers_.find(peer);
    if (it == peers_.end())
        return kDefaultRssiDbm + link_margin_db_;
    return it->second.required_power_dbm;
}

void TransecConfig::evict_stale_peers(uint64_t now_ms) {
    for (auto it = peers_.begin(); it != peers_.end(); ) {
        if (now_ms > it->second.last_beacon_ms &&
            now_ms - it->second.last_beacon_ms > kEntryExpiryMs)
            it = peers_.erase(it);
        else
            ++it;
    }
}

} // namespace cirradio::transec
