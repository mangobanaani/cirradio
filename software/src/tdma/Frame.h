#pragma once
#include <cstdint>
#include <array>
#include <stdexcept>

namespace cirradio::tdma {

enum class SlotType : uint8_t {
    Beacon,     // Slot 0: rotating net control
    Traffic,    // Slots 1-14: voice + data
    DataOnly,   // Slots 15-17: bulk data
    KeyMgmt,    // Slot 18: OTAR / rekey
    Discovery   // Slot 19: join, fixed rendezvous freq
};

struct SlotInfo {
    SlotType type;
    uint32_t owner_id{0};   // 0 = unclaimed
    bool active{false};     // true if slot is in use this frame
};

class Frame {
public:
    static constexpr uint8_t kSlotCount = 20;
    static constexpr uint32_t kFrameDurationMs = 1000;
    static constexpr uint32_t kSlotDurationMs = 50;
    static constexpr uint32_t kGuardTimeMs = 2;
    static constexpr uint32_t kPreambleMs = 3;
    static constexpr uint32_t kDataTimeMs = 42;

    explicit Frame(uint32_t frame_number)
        : frame_number_(frame_number) {
        for (uint8_t i = 0; i < kSlotCount; ++i) {
            slots_[i].type = type_for_slot(i);
            slots_[i].owner_id = 0;
            slots_[i].active = false;
        }
    }

    uint8_t slot_count() const { return kSlotCount; }
    uint32_t frame_number() const { return frame_number_; }

    SlotType slot_type(uint8_t slot_index) const {
        if (slot_index >= kSlotCount) {
            throw std::out_of_range("slot_index out of range");
        }
        return slots_[slot_index].type;
    }

    const SlotInfo& slot(uint8_t slot_index) const {
        if (slot_index >= kSlotCount) {
            throw std::out_of_range("slot_index out of range");
        }
        return slots_[slot_index];
    }

    SlotInfo& slot(uint8_t slot_index) {
        if (slot_index >= kSlotCount) {
            throw std::out_of_range("slot_index out of range");
        }
        return slots_[slot_index];
    }

private:
    uint32_t frame_number_;
    std::array<SlotInfo, kSlotCount> slots_;

    static SlotType type_for_slot(uint8_t index) {
        if (index == 0) return SlotType::Beacon;
        if (index <= 14) return SlotType::Traffic;
        if (index <= 17) return SlotType::DataOnly;
        if (index == 18) return SlotType::KeyMgmt;
        return SlotType::Discovery;
    }
};

}  // namespace cirradio::tdma
