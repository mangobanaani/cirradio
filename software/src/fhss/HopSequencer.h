#pragma once
#include "hal/Types.h"
#include <vector>
#include <cstdint>
#include <set>
#include <span>

namespace cirradio::fhss {

class HopSequencer {
public:
    // fhek: 32-byte frequency hop encryption key
    // min_freq/max_freq: band edges in Hz
    // channel_spacing: channel grid spacing in Hz
    HopSequencer(std::span<const uint8_t> fhek,
                 hal::Frequency min_freq,
                 hal::Frequency max_freq,
                 hal::Frequency channel_spacing);

    // Get the hop frequency for a given slot and frame number.
    // Deterministic: same inputs always produce same output.
    hal::Frequency get_hop_frequency(uint8_t slot, uint32_t frame) const;

    // Blacklist a frequency (for anti-jam). Blacklisted freqs are skipped.
    void blacklist_frequency(hal::Frequency freq);

    // Clear all blacklisted frequencies.
    void clear_blacklist();

    // Get total number of available channels.
    uint64_t num_channels() const;

private:
    std::vector<uint8_t> fhek_;  // 32 bytes
    hal::Frequency min_freq_;
    hal::Frequency max_freq_;
    hal::Frequency channel_spacing_;
    uint64_t num_channels_;
    std::set<hal::Frequency> blacklist_;

    // Internal: compute raw channel index from slot+frame using AES
    uint64_t compute_channel_index(uint8_t slot, uint32_t frame,
                                   uint8_t attempt = 0) const;
};

}  // namespace cirradio::fhss
