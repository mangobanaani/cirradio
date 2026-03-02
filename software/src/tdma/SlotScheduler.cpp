#include "tdma/SlotScheduler.h"
#include <stdexcept>

namespace cirradio::tdma {

SlotScheduler::SlotScheduler(uint32_t node_id)
    : node_id_(node_id), frame_(0) {}

bool SlotScheduler::claim_slot(uint8_t slot_index) {
    if (slot_index >= Frame::kSlotCount) {
        return false;
    }

    auto& s = frame_.slot(slot_index);

    // Only Traffic and DataOnly slots can be claimed
    if (s.type != SlotType::Traffic && s.type != SlotType::DataOnly) {
        return false;
    }

    // Already claimed
    if (s.owner_id != 0) {
        return false;
    }

    s.owner_id = node_id_;
    s.active = true;
    return true;
}

void SlotScheduler::release_slot(uint8_t slot_index) {
    if (slot_index >= Frame::kSlotCount) {
        return;
    }

    auto& s = frame_.slot(slot_index);
    s.owner_id = 0;
    s.active = false;
}

uint32_t SlotScheduler::owner_of(uint8_t slot_index) const {
    if (slot_index >= Frame::kSlotCount) {
        throw std::out_of_range("slot_index out of range");
    }
    return frame_.slot(slot_index).owner_id;
}

uint32_t SlotScheduler::beacon_controller(
    uint32_t frame_number,
    const std::vector<uint32_t>& node_list) const {
    if (node_list.empty()) {
        return 0;
    }
    return node_list[frame_number % node_list.size()];
}

std::optional<uint8_t> SlotScheduler::my_voice_slot() const {
    // Return the first traffic slot owned by this node (lowest index)
    for (uint8_t i = 1; i <= 14; ++i) {
        if (frame_.slot(i).owner_id == node_id_) {
            return i;
        }
    }
    return std::nullopt;
}

void SlotScheduler::apply_slot_map(const Frame& frame) {
    for (uint8_t i = 0; i < Frame::kSlotCount; ++i) {
        auto& dst = frame_.slot(i);
        const auto& src = frame.slot(i);
        dst.owner_id = src.owner_id;
        dst.active = src.active;
    }
}

const Frame& SlotScheduler::current_frame() const {
    return frame_;
}

void SlotScheduler::advance_frame() {
    frame_ = Frame(frame_.frame_number() + 1);
}

}  // namespace cirradio::tdma
