#include "voice/JitterBuffer.h"

namespace cirradio::voice {

JitterBuffer::JitterBuffer(size_t depth) : depth_(depth) {}

void JitterBuffer::push(uint32_t sequence, const std::vector<int16_t>& frame) {
    buffer_[sequence] = frame;

    // Before any pop, track the lowest sequence in the buffer
    if (first_push_) {
        next_seq_ = buffer_.begin()->first;
    }

    // Drop oldest frames if buffer exceeds depth
    while (buffer_.size() > depth_) {
        auto it = buffer_.begin();
        // If we're dropping frames we haven't played yet, advance next_seq_
        if (it->first == next_seq_) {
            ++next_seq_;
        }
        buffer_.erase(it);
    }
}

std::optional<std::vector<int16_t>> JitterBuffer::pop() {
    first_push_ = false;  // lock next_seq_ after first pop attempt

    auto it = buffer_.find(next_seq_);
    if (it == buffer_.end()) {
        return std::nullopt;
    }

    auto frame = std::move(it->second);
    buffer_.erase(it);
    ++next_seq_;
    return frame;
}

size_t JitterBuffer::size() const {
    return buffer_.size();
}

void JitterBuffer::reset() {
    buffer_.clear();
    next_seq_ = 0;
    first_push_ = true;
}

}  // namespace cirradio::voice
