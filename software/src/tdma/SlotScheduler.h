#pragma once
#include "Frame.h"
#include <vector>
#include <cstdint>
#include <optional>

namespace cirradio::tdma {

class SlotScheduler {
public:
    explicit SlotScheduler(uint32_t node_id);

    // Try to claim a traffic slot (1-14) or data-only slot (15-17).
    // Returns false if slot is already claimed or is a reserved type (Beacon/KeyMgmt/Discovery).
    bool claim_slot(uint8_t slot_index);

    // Release a previously claimed slot.
    void release_slot(uint8_t slot_index);

    // Get the owner of a slot (0 = unclaimed).
    uint32_t owner_of(uint8_t slot_index) const;

    // Determine who should be beacon controller for a given frame.
    // Rotates round-robin through the node list.
    uint32_t beacon_controller(uint32_t frame_number,
                               const std::vector<uint32_t>& node_list) const;

    // Get the slot index assigned to this node for voice TX (first claimed traffic slot).
    std::optional<uint8_t> my_voice_slot() const;

    // Apply a slot map received from beacon (overwrites local state).
    void apply_slot_map(const Frame& frame);

    // Get current frame state.
    const Frame& current_frame() const;

    // Advance to next frame.
    void advance_frame();

private:
    uint32_t node_id_;
    Frame frame_;
};

}  // namespace cirradio::tdma
