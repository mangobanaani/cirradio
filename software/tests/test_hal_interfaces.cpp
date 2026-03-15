#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <memory>
#include "hal/IRadioHal.h"
#include "hal/IGpsHal.h"
#include "hal/IAudioHal.h"

using namespace cirradio::hal;

// --- Mock implementations ---

class MockRadioHal : public IRadioHal {
public:
    bool configure(const RadioConfig& config) override {
        config_ = config;
        return true;
    }
    bool tune(Frequency freq) override {
        config_.center_freq = freq;
        return true;
    }
    bool set_tx_power(PowerLevel power_dbm) override {
        config_.tx_power = power_dbm;
        return true;
    }
    bool transmit(ConstSampleBuffer samples) override {
        return samples.size() > 0;
    }
    size_t receive(SampleBuffer buffer) override {
        return 0;
    }
    bool set_tx_enabled(bool enabled) override {
        tx_enabled_ = enabled;
        return true;
    }
    RadioConfig current_config() const override {
        return config_;
    }

private:
    RadioConfig config_{};
    bool tx_enabled_ = false;
};

class MockGpsHal : public IGpsHal {
public:
    std::optional<GpsPosition> get_position() override {
        return GpsPosition{60.1699, 24.9384, 10.0,
                           std::chrono::steady_clock::now(), true};
    }
    std::optional<Timestamp> get_time() override {
        return std::chrono::steady_clock::now();
    }
    std::optional<Timestamp> get_pps_timestamp() override {
        return std::chrono::steady_clock::now();
    }
};

class MockAudioHal : public IAudioHal {
public:
    std::vector<int16_t> capture(size_t num_samples) override {
        return std::vector<int16_t>(num_samples, 0);
    }
    bool playback(std::span<const int16_t> samples) override {
        return samples.size() > 0;
    }
    bool set_volume(float level) override {
        volume_ = level;
        return true;
    }

private:
    float volume_ = 1.0f;
};

// --- Tests ---

TEST_CASE("IRadioHal mock can be instantiated and used", "[hal]") {
    std::unique_ptr<IRadioHal> radio = std::make_unique<MockRadioHal>();

    RadioConfig cfg{};
    cfg.center_freq = 145'000'000;
    cfg.sample_rate = 48000;
    cfg.bandwidth = 25000;
    cfg.tx_power = 5.0f;

    REQUIRE(radio->configure(cfg));
    REQUIRE(radio->tune(146'000'000));
    REQUIRE(radio->set_tx_power(10.0f));
    REQUIRE(radio->set_tx_enabled(true));

    auto current = radio->current_config();
    REQUIRE(current.center_freq == 146'000'000);
    REQUIRE(current.tx_power == 10.0f);

    std::vector<Sample> tx_samples(64, Sample{1.0f, 0.0f});
    REQUIRE(radio->transmit(tx_samples));

    std::vector<Sample> rx_buf(64);
    REQUIRE(radio->receive(rx_buf) == 0);
}

TEST_CASE("IGpsHal mock can be instantiated and used", "[hal]") {
    std::unique_ptr<IGpsHal> gps = std::make_unique<MockGpsHal>();

    auto pos = gps->get_position();
    REQUIRE(pos.has_value());
    REQUIRE(pos->valid);
    REQUIRE(pos->latitude == Catch::Approx(60.1699));
    REQUIRE(pos->longitude == Catch::Approx(24.9384));

    auto time = gps->get_time();
    REQUIRE(time.has_value());

    auto pps = gps->get_pps_timestamp();
    REQUIRE(pps.has_value());
}

TEST_CASE("IAudioHal mock can be instantiated and used", "[hal]") {
    std::unique_ptr<IAudioHal> audio = std::make_unique<MockAudioHal>();

    auto samples = audio->capture(128);
    REQUIRE(samples.size() == 128);

    REQUIRE(audio->playback(samples));
    REQUIRE(audio->set_volume(0.5f));
}
