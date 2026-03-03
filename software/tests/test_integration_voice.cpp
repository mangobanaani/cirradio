#include <catch2/catch_test_macros.hpp>
#include "node/RadioNode.h"
#include "hal/SimChannel.h"
#include <memory>
#include <vector>
#include <cmath>

using namespace cirradio;

namespace {

// Generate a sine wave at the given frequency and sample rate
std::vector<int16_t> generate_sine(double freq_hz, double sample_rate, size_t num_samples) {
    std::vector<int16_t> samples(num_samples);
    for (size_t i = 0; i < num_samples; ++i) {
        samples[i] = static_cast<int16_t>(
            16000.0 * std::sin(2.0 * M_PI * freq_hz * static_cast<double>(i) / sample_rate));
    }
    return samples;
}

// Compute RMS energy of audio samples
double rms_energy(const std::vector<int16_t>& samples) {
    if (samples.empty()) return 0.0;
    double sum_sq = 0.0;
    for (auto s : samples) {
        sum_sq += static_cast<double>(s) * static_cast<double>(s);
    }
    return std::sqrt(sum_sq / static_cast<double>(samples.size()));
}

}  // namespace

TEST_CASE("Encrypted voice from node A to node B", "[integration][voice]") {
    auto channel = std::make_shared<hal::SimChannel>();
    node::RadioNode node_a(1, channel);
    node::RadioNode node_b(2, channel);

    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    node_a.provision_keys(tek, fhek);
    node_b.provision_keys(tek, fhek);

    node_a.start();
    node_b.start();

    // Allow discovery
    for (int frame = 0; frame < 10; ++frame) {
        node_a.tick();
        node_b.tick();
    }

    REQUIRE(node_a.peers().size() == 1);

    // Generate test audio: 1kHz sine at 8kHz sample rate
    // VoiceCodec (Codec2_1200) expects num_samples_per_frame() samples
    // Codec2 1200 bps uses 320 samples per frame
    auto test_audio = generate_sine(1000.0, 8000.0, 320);

    // Transmit voice from A to B
    node_a.voice_tx(2, test_audio);

    // Tick to process
    node_a.tick();
    node_b.tick();

    auto rx_audio = node_b.voice_rx();
    REQUIRE(rx_audio.has_value());
    REQUIRE(rx_audio->audio.size() == 320);
    // Verify audio has energy (lossy codec, can't compare exactly)
    REQUIRE(rms_energy(rx_audio->audio) > 100.0);
}
