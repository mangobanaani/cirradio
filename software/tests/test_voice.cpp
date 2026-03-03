#include <catch2/catch_test_macros.hpp>
#include <cmath>
#include "voice/VoiceCodec.h"
#include "voice/JitterBuffer.h"
#include "voice/SimAudioHal.h"

TEST_CASE("Codec2 encode/decode roundtrip", "[voice]") {
    cirradio::voice::VoiceCodec codec(cirradio::voice::CodecMode::Codec2_1200);
    int n = codec.num_samples_per_frame();
    std::vector<int16_t> input(n);
    // Generate 1kHz sine wave at 8kHz sample rate
    for (int i = 0; i < n; ++i)
        input[i] = static_cast<int16_t>(16000.0 * std::sin(2.0 * M_PI * 1000.0 * i / 8000.0));

    auto encoded = codec.encode(input);
    REQUIRE(encoded.size() == static_cast<size_t>(codec.bytes_per_frame()));
    REQUIRE(encoded.size() < input.size() * 2);  // must compress

    auto decoded = codec.decode(encoded);
    REQUIRE(decoded.size() == static_cast<size_t>(n));
    // Lossy codec - check it has signal energy
    double energy = 0;
    for (auto s : decoded) energy += static_cast<double>(s) * s;
    REQUIRE(energy > 0);
}

TEST_CASE("VoiceCodec different modes have different bitrates", "[voice]") {
    cirradio::voice::VoiceCodec c1200(cirradio::voice::CodecMode::Codec2_1200);
    cirradio::voice::VoiceCodec c3200(cirradio::voice::CodecMode::Codec2_3200);
    REQUIRE(c3200.bytes_per_frame() > c1200.bytes_per_frame());
}

TEST_CASE("JitterBuffer reorders out-of-order packets", "[voice]") {
    cirradio::voice::JitterBuffer jbuf(5);
    std::vector<int16_t> frame_a(160, 100);
    std::vector<int16_t> frame_b(160, 200);
    std::vector<int16_t> frame_c(160, 300);

    jbuf.push(2, frame_c);
    jbuf.push(0, frame_a);
    jbuf.push(1, frame_b);

    auto out0 = jbuf.pop();
    REQUIRE(out0.has_value());
    REQUIRE((*out0)[0] == 100);

    auto out1 = jbuf.pop();
    REQUIRE(out1.has_value());
    REQUIRE((*out1)[0] == 200);

    auto out2 = jbuf.pop();
    REQUIRE(out2.has_value());
    REQUIRE((*out2)[0] == 300);
}

TEST_CASE("JitterBuffer returns nullopt for missing frame", "[voice]") {
    cirradio::voice::JitterBuffer jbuf(5);
    jbuf.push(0, std::vector<int16_t>(160, 100));
    jbuf.pop();  // gets frame 0
    // Frame 1 is missing, frame 2 is available
    jbuf.push(2, std::vector<int16_t>(160, 300));
    auto out = jbuf.pop();
    REQUIRE_FALSE(out.has_value());  // waiting for frame 1
}

TEST_CASE("SimAudioHal capture and playback", "[voice]") {
    cirradio::voice::SimAudioHal audio;
    std::vector<int16_t> test_data = {100, 200, 300, 400};
    audio.inject_capture_data(test_data);
    auto captured = audio.capture(4);
    REQUIRE(captured == test_data);

    audio.playback(captured);
    auto played = audio.get_played_data();
    REQUIRE(played == test_data);
}
