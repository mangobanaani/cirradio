// software/src/transec/TransecConfig.h
#pragma once
#include <cstdint>
#include <unordered_map>
#include <algorithm>

namespace cirradio::transec {

struct PeerLink {
    uint32_t peer;
    float    rssi_dbm;
    float    required_power_dbm;
    uint64_t last_beacon_ms;
};

class TransecConfig {
public:
    static constexpr int   kMaxPeers       = 256;
    static constexpr int   kEntryExpiryMs  = 300'000;
    static constexpr float kDefaultRssiDbm = -90.0f;

    TransecConfig() = default;

    void  update_peer_rssi(uint32_t peer, float rssi_dbm, uint64_t now_ms = 0);
    float required_power_dbm(uint32_t peer) const;
    void  evict_stale_peers(uint64_t now_ms);
    size_t peer_count() const { return peers_.size(); }

    int   interleaver_depth() const     { return interleaver_depth_; }
    void  set_interleaver_depth(int d)  { interleaver_depth_ = std::clamp(d, 1, 32); }
    int   hop_rate() const              { return hop_rate_; }
    void  set_hop_rate(int r)           { hop_rate_ = std::clamp(r, 1, 1000); }
    float link_margin_db() const        { return link_margin_db_; }
    void  set_link_margin_db(float m)   { link_margin_db_ = m; }

private:
    std::unordered_map<uint32_t, PeerLink> peers_;
    int   interleaver_depth_ = 10;
    int   hop_rate_          = 100;
    float link_margin_db_    = 10.0f;
};

} // namespace cirradio::transec
