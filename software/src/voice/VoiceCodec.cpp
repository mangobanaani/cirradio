#include "voice/VoiceCodec.h"
#include <codec2/codec2.h>
#include <stdexcept>
#include <cstring>

namespace cirradio::voice {

namespace {

int to_codec2_mode(CodecMode mode) {
    switch (mode) {
        case CodecMode::Codec2_3200: return CODEC2_MODE_3200;
        case CodecMode::Codec2_2400: return CODEC2_MODE_2400;
        case CodecMode::Codec2_1600: return CODEC2_MODE_1600;
        case CodecMode::Codec2_1200: return CODEC2_MODE_1200;
        case CodecMode::Codec2_700C: return CODEC2_MODE_700C;
        default: throw std::invalid_argument("Unknown codec mode");
    }
}

}  // namespace

VoiceCodec::VoiceCodec(CodecMode mode) : mode_(mode) {
    codec2_ = codec2_create(to_codec2_mode(mode));
    if (!codec2_) {
        throw std::runtime_error("Failed to create codec2 instance");
    }
}

VoiceCodec::~VoiceCodec() {
    if (codec2_) {
        codec2_destroy(static_cast<CODEC2*>(codec2_));
    }
}

std::vector<uint8_t> VoiceCodec::encode(const std::vector<int16_t>& samples) {
    auto* c2 = static_cast<CODEC2*>(codec2_);
    int expected_samples = codec2_samples_per_frame(c2);
    if (static_cast<int>(samples.size()) != expected_samples) {
        throw std::invalid_argument("Input sample count does not match frame size");
    }

    int nbytes = codec2_bytes_per_frame(c2);
    std::vector<uint8_t> encoded(nbytes);

    // codec2_encode takes non-const short* for speech_in
    std::vector<short> speech(samples.begin(), samples.end());
    codec2_encode(c2, encoded.data(), speech.data());

    return encoded;
}

std::vector<int16_t> VoiceCodec::decode(const std::vector<uint8_t>& data) {
    auto* c2 = static_cast<CODEC2*>(codec2_);
    int nbytes = codec2_bytes_per_frame(c2);
    if (static_cast<int>(data.size()) != nbytes) {
        throw std::invalid_argument("Input data size does not match expected frame bytes");
    }

    int nsamples = codec2_samples_per_frame(c2);
    std::vector<short> speech(nsamples);
    codec2_decode(c2, speech.data(), data.data());

    return std::vector<int16_t>(speech.begin(), speech.end());
}

int VoiceCodec::num_samples_per_frame() const {
    return codec2_samples_per_frame(static_cast<CODEC2*>(codec2_));
}

int VoiceCodec::bytes_per_frame() const {
    return codec2_bytes_per_frame(static_cast<CODEC2*>(codec2_));
}

}  // namespace cirradio::voice
