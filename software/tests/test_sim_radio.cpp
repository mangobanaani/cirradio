#include <catch2/catch_test_macros.hpp>
#include <memory>
#include <vector>
#include "hal/SimChannel.h"
#include "hal/SimRadioHal.h"

using namespace cirradio::hal;

static constexpr Frequency FREQ_300MHZ = 300'000'000;
static constexpr Frequency FREQ_400MHZ = 400'000'000;

static std::vector<Sample> make_test_samples(size_t count) {
    std::vector<Sample> samples(count);
    for (size_t i = 0; i < count; ++i) {
        samples[i] = Sample{static_cast<float>(i) * 0.1f, static_cast<float>(i) * -0.1f};
    }
    return samples;
}

TEST_CASE("Two radios on same freq can communicate", "[hal][sim]") {
    auto channel = std::make_shared<SimChannel>();
    SimRadioHal radio_a(channel);
    SimRadioHal radio_b(channel);

    radio_a.tune(FREQ_300MHZ);
    radio_a.set_tx_enabled(true);
    radio_b.tune(FREQ_300MHZ);

    auto tx_samples = make_test_samples(32);
    REQUIRE(radio_a.transmit(tx_samples));

    std::vector<Sample> rx_buf(64);
    size_t received = radio_b.receive(rx_buf);
    REQUIRE(received == 32);
    for (size_t i = 0; i < received; ++i) {
        REQUIRE(rx_buf[i].real() == tx_samples[i].real());
        REQUIRE(rx_buf[i].imag() == tx_samples[i].imag());
    }
}

TEST_CASE("Frequency isolation", "[hal][sim]") {
    auto channel = std::make_shared<SimChannel>();
    SimRadioHal radio_a(channel);
    SimRadioHal radio_b(channel);

    radio_a.tune(FREQ_300MHZ);
    radio_a.set_tx_enabled(true);
    radio_b.tune(FREQ_400MHZ);

    auto tx_samples = make_test_samples(16);
    REQUIRE(radio_a.transmit(tx_samples));

    std::vector<Sample> rx_buf(64);
    size_t received = radio_b.receive(rx_buf);
    REQUIRE(received == 0);
}

TEST_CASE("TX disabled blocks transmission", "[hal][sim]") {
    auto channel = std::make_shared<SimChannel>();
    SimRadioHal radio_a(channel);
    SimRadioHal radio_b(channel);

    radio_a.tune(FREQ_300MHZ);
    // tx_enabled defaults to false, do not enable it
    radio_b.tune(FREQ_300MHZ);

    auto tx_samples = make_test_samples(16);
    REQUIRE_FALSE(radio_a.transmit(tx_samples));

    std::vector<Sample> rx_buf(64);
    size_t received = radio_b.receive(rx_buf);
    REQUIRE(received == 0);
}

TEST_CASE("Multiple receivers", "[hal][sim]") {
    auto channel = std::make_shared<SimChannel>();
    SimRadioHal radio_a(channel);
    SimRadioHal radio_b(channel);
    SimRadioHal radio_c(channel);

    radio_a.tune(FREQ_300MHZ);
    radio_a.set_tx_enabled(true);
    radio_b.tune(FREQ_300MHZ);
    radio_c.tune(FREQ_300MHZ);

    auto tx_samples = make_test_samples(8);
    REQUIRE(radio_a.transmit(tx_samples));

    std::vector<Sample> rx_buf_b(64);
    size_t received_b = radio_b.receive(rx_buf_b);
    REQUIRE(received_b == 8);

    std::vector<Sample> rx_buf_c(64);
    size_t received_c = radio_c.receive(rx_buf_c);
    REQUIRE(received_c == 8);

    for (size_t i = 0; i < 8; ++i) {
        REQUIRE(rx_buf_b[i].real() == tx_samples[i].real());
        REQUIRE(rx_buf_b[i].imag() == tx_samples[i].imag());
        REQUIRE(rx_buf_c[i].real() == tx_samples[i].real());
        REQUIRE(rx_buf_c[i].imag() == tx_samples[i].imag());
    }
}

TEST_CASE("Tune changes receive frequency", "[hal][sim]") {
    auto channel = std::make_shared<SimChannel>();
    SimRadioHal radio_a(channel);
    SimRadioHal radio_b(channel);

    radio_a.tune(FREQ_400MHZ);
    radio_a.set_tx_enabled(true);

    // Radio B starts on 300 MHz - nothing to receive there
    radio_b.tune(FREQ_300MHZ);

    std::vector<Sample> rx_buf(64);
    size_t received = radio_b.receive(rx_buf);
    REQUIRE(received == 0);

    // Retune radio B to 400 MHz to match radio A
    radio_b.tune(FREQ_400MHZ);

    // Transmit after retune
    auto tx_samples = make_test_samples(16);
    REQUIRE(radio_a.transmit(tx_samples));

    received = radio_b.receive(rx_buf);
    REQUIRE(received == 16);
    for (size_t i = 0; i < received; ++i) {
        REQUIRE(rx_buf[i].real() == tx_samples[i].real());
        REQUIRE(rx_buf[i].imag() == tx_samples[i].imag());
    }
}
