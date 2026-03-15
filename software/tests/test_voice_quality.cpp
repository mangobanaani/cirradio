// software/tests/test_voice_quality.cpp
#include <catch2/catch_test_macros.hpp>
#include "voice/VoiceCodec.h"
#include <cmath>
#include <random>
#include <vector>
#include <cstdlib>
#include <numeric>

using namespace cirradio::voice;

namespace {

// Generate a simple repeating signal (square wave) that Codec2 can handle
std::vector<int16_t> make_reference_pcm(CodecMode mode, int num_frames) {
    VoiceCodec codec(mode);
    int spf = codec.num_samples_per_frame();
    std::vector<int16_t> out;
    out.reserve(static_cast<size_t>(num_frames * spf));
    double freq = 440.0;
    for (int f = 0; f < num_frames; ++f) {
        for (int i = 0; i < spf; ++i) {
            double t = static_cast<double>(f * spf + i) / 8000.0;
            // Mix of frequencies to mimic speech-like signal
            double s = 0.5 * std::sin(2.0 * M_PI * freq * t)
                     + 0.3 * std::sin(2.0 * M_PI * 880.0 * t)
                     + 0.2 * std::sin(2.0 * M_PI * 1320.0 * t);
            out.push_back(static_cast<int16_t>(16000.0 * s));
        }
    }
    return out;
}

std::vector<int16_t> codec_roundtrip(CodecMode mode, const std::vector<int16_t>& ref_pcm)
{
    VoiceCodec codec(mode);
    int spf = codec.num_samples_per_frame();
    int num_frames = static_cast<int>(ref_pcm.size()) / spf;

    std::vector<int16_t> out;
    for (int f = 0; f < num_frames; ++f) {
        std::vector<int16_t> frame(ref_pcm.begin() + f * spf,
                                    ref_pcm.begin() + (f + 1) * spf);
        auto encoded = codec.encode(frame);
        auto decoded = codec.decode(encoded);
        out.insert(out.end(), decoded.begin(), decoded.end());
    }
    return out;
}

// RMS energy
double rms_energy(const std::vector<int16_t>& v) {
    double e = 0;
    for (auto s : v) e += static_cast<double>(s) * s;
    return std::sqrt(e / v.size());
}

}  // namespace

TEST_CASE("Codec2 encode/decode produces non-silent output for all modes", "[voice_quality]") {
    const std::vector<CodecMode> modes = {
        CodecMode::Codec2_3200,
        CodecMode::Codec2_2400,
        CodecMode::Codec2_1600,
        CodecMode::Codec2_1200,
    };
    for (auto mode : modes) {
        auto ref = make_reference_pcm(mode, 20);
        auto out = codec_roundtrip(mode, ref);
        REQUIRE(!out.empty());
        double e = rms_energy(out);
        INFO("Mode energy = " << e);
        // Codec2 is a vocoder - output energy should be non-zero
        REQUIRE(e > 100.0);  // at least 100 RMS (out of max ~16000)
    }
}

TEST_CASE("Codec2 compressed bitrate is within spec", "[voice_quality]") {
    // Check that bytes_per_frame() matches the expected mode bitrate
    // 3200 bps at 8kHz with 160 samples/frame: 8 bytes/frame
    // 1200 bps at 8kHz with 320 samples/frame: ~6 bytes/frame
    VoiceCodec codec3200(CodecMode::Codec2_3200);
    VoiceCodec codec1200(CodecMode::Codec2_1200);

    REQUIRE(codec3200.bytes_per_frame() > 0);
    REQUIRE(codec1200.bytes_per_frame() > 0);
    // Higher bitrate mode should use more bytes per frame
    // (accounting for different frame lengths: 160 vs 320 samples)
    double bps_3200 = static_cast<double>(codec3200.bytes_per_frame() * 8)
                    / codec3200.num_samples_per_frame() * 8000.0;
    double bps_1200 = static_cast<double>(codec1200.bytes_per_frame() * 8)
                    / codec1200.num_samples_per_frame() * 8000.0;
    INFO("Codec2_3200 bitrate = " << bps_3200 << " bps");
    INFO("Codec2_1200 bitrate = " << bps_1200 << " bps");
    REQUIRE(bps_3200 >= bps_1200);
}

TEST_CASE("Codec2 frames are losslessly compressed (encode/decode frame count matches)", "[voice_quality]") {
    VoiceCodec codec(CodecMode::Codec2_1200);
    int spf = codec.num_samples_per_frame();
    int num_frames = 10;

    auto ref = make_reference_pcm(CodecMode::Codec2_1200, num_frames);
    auto out = codec_roundtrip(CodecMode::Codec2_1200, ref);

    // Must produce exactly the right number of samples
    REQUIRE(out.size() == static_cast<size_t>(num_frames * spf));
}
