// software/src/transec/EmconManager.h
#pragma once
#include "transec/TransecConfig.h"
#include "security/IAxiRegs.h"

namespace cirradio::transec {

class EmconManager {
public:
    explicit EmconManager(security::IAxiRegs& regs, TransecConfig& cfg);

    // Set EMCON level. Returns true on success.
    // EMCON levels: 0=silence (most restricted), 1=reduced, 2=normal (least restricted)
    // Decreasing restriction (0→1, 0→2, 1→2) requires unlock=true or is rejected.
    bool set_level(int level, bool unlock = false);

    // Force to EMCON 0 unconditionally (called by TamperMonitor after zeroize).
    void force_emcon0();

    int current_level() const { return level_; }

    // Called by PeerDiscovery on each received beacon.
    void on_beacon_rssi(uint32_t peer, float rssi_dbm);

private:
    security::IAxiRegs& regs_;
    TransecConfig&      cfg_;
    int                 level_{2};

    void apply_level(int level);
    static constexpr int32_t kNormalPowerDbmX100 = 3700; // 37.0 dBm default
};

} // namespace cirradio::transec
