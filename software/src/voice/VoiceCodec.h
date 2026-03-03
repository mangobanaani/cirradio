#pragma once
#include <vector>
#include <cstdint>

namespace cirradio::voice {

enum class CodecMode {
    Codec2_3200,  // 3200 bps - best quality
    Codec2_2400,  // 2400 bps
    Codec2_1600,  // 1600 bps
    Codec2_1200,  // 1200 bps - lowest bandwidth, tactical
    Codec2_700C   // 700 bps - ultra low bandwidth
};

class VoiceCodec {
public:
    explicit VoiceCodec(CodecMode mode = CodecMode::Codec2_1200);
    ~VoiceCodec();

    // Encode one frame of audio (num_samples_per_frame() int16_t samples at 8kHz)
    // Returns compressed bytes
    std::vector<uint8_t> encode(const std::vector<int16_t>& samples);

    // Decode compressed bytes back to audio samples
    std::vector<int16_t> decode(const std::vector<uint8_t>& data);

    // Get frame parameters
    int num_samples_per_frame() const;  // e.g., 320 for codec2 1200
    int bytes_per_frame() const;        // compressed bytes per frame

    VoiceCodec(const VoiceCodec&) = delete;
    VoiceCodec& operator=(const VoiceCodec&) = delete;

private:
    void* codec2_ = nullptr;
    CodecMode mode_;
};

}  // namespace cirradio::voice
