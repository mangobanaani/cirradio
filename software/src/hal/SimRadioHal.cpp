#include "hal/SimRadioHal.h"
#include <algorithm>

namespace cirradio::hal {

SimRadioHal::SimRadioHal(std::shared_ptr<SimChannel> channel)
    : channel_(std::move(channel)) {
    radio_id_ = channel_->register_radio();
}

SimRadioHal::~SimRadioHal() {
    channel_->unregister_radio(radio_id_);
}

bool SimRadioHal::configure(const RadioConfig& config) {
    config_ = config;
    return true;
}

bool SimRadioHal::tune(Frequency freq) {
    config_.center_freq = freq;
    return true;
}

bool SimRadioHal::set_tx_power(PowerLevel power_dbm) {
    config_.tx_power = power_dbm;
    return true;
}

bool SimRadioHal::transmit(ConstSampleBuffer samples) {
    if (!tx_enabled_) {
        return false;
    }
    std::vector<Sample> vec(samples.begin(), samples.end());
    channel_->transmit(radio_id_, config_.center_freq, vec);
    return true;
}

size_t SimRadioHal::receive(SampleBuffer buffer) {
    auto samples = channel_->receive(radio_id_, config_.center_freq, buffer.size());
    std::copy(samples.begin(), samples.end(), buffer.begin());
    return samples.size();
}

bool SimRadioHal::set_tx_enabled(bool enabled) {
    tx_enabled_ = enabled;
    return true;
}

RadioConfig SimRadioHal::current_config() const {
    return config_;
}

}  // namespace cirradio::hal
