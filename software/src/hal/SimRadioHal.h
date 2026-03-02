#pragma once
#include "IRadioHal.h"
#include "SimChannel.h"
#include <memory>

namespace cirradio::hal {

class SimRadioHal : public IRadioHal {
public:
    explicit SimRadioHal(std::shared_ptr<SimChannel> channel);
    ~SimRadioHal() override;

    bool configure(const RadioConfig& config) override;
    bool tune(Frequency freq) override;
    bool set_tx_power(PowerLevel power_dbm) override;
    bool transmit(ConstSampleBuffer samples) override;
    size_t receive(SampleBuffer buffer) override;
    bool set_tx_enabled(bool enabled) override;
    RadioConfig current_config() const override;

private:
    std::shared_ptr<SimChannel> channel_;
    uint32_t radio_id_;
    RadioConfig config_{};
    bool tx_enabled_ = false;
};

}  // namespace cirradio::hal
