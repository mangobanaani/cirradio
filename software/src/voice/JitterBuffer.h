#pragma once
#include <vector>
#include <cstdint>
#include <optional>
#include <map>

namespace cirradio::voice {

class JitterBuffer {
public:
    // depth: max number of frames to buffer
    explicit JitterBuffer(size_t depth = 5);

    // Push a frame with its sequence number
    void push(uint32_t sequence, const std::vector<int16_t>& frame);

    // Pop the next frame in sequence order
    // Returns nullopt if next expected frame hasn't arrived yet
    std::optional<std::vector<int16_t>> pop();

    // Number of frames currently buffered
    size_t size() const;

    // Reset the buffer
    void reset();

private:
    size_t depth_;
    uint32_t next_seq_ = 0;
    bool first_push_ = true;
    std::map<uint32_t, std::vector<int16_t>> buffer_;
};

}  // namespace cirradio::voice
