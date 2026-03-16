// software/src/transec/EmconManager.cpp
#include "transec/EmconManager.h"
#include <chrono>

namespace cirradio::transec {

EmconManager::EmconManager(security::IAxiRegs& regs, TransecConfig& cfg)
    : regs_(regs), cfg_(cfg) {
    apply_level(2); // ensure hardware matches default
}

bool EmconManager::set_level(int level, bool unlock) {
    if (level < 0 || level > 2) return false;
    bool is_downgrade = level > level_; // 0 is most restricted; 2 is normal
    // "downgrade" in EMCON terms means less restricted: 0→1, 0→2, 1→2
    if (is_downgrade && !unlock) return false;
    if (is_downgrade && unlock) {
        regs_.write_emcon_unlock();
    }
    apply_level(level);
    return true;
}

void EmconManager::force_emcon0() {
    level_ = 0;
    regs_.set_emcon_ctrl(0x4u); // level=0, lock=1 (tamper-locked silence)
    regs_.set_tx_power(0);      // 0 dBm (no TX anyway — PA killed by EMCON gate)
}

void EmconManager::on_beacon_rssi(uint32_t peer, float rssi_dbm) {
    auto now_ms = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
    cfg_.update_peer_rssi(peer, rssi_dbm, now_ms);
}

void EmconManager::apply_level(int level) {
    level_ = level;
    // Set lock bit when moving to restricted level (0 or 1)
    uint32_t ctrl = static_cast<uint32_t>(level) | (level < 2 ? 0x4u : 0x0u);
    regs_.set_emcon_ctrl(ctrl);
    if (level == 0) {
        regs_.set_tx_power(0);
    } else if (level == 1) {
        regs_.set_tx_power(kNormalPowerDbmX100 - 2000); // −20 dB
    } else {
        regs_.set_tx_power(kNormalPowerDbmX100);
    }
}

} // namespace cirradio::transec
