#pragma once
#include "Types.h"

namespace cirradio::hal {

class IRadioHal {
public:
    virtual ~IRadioHal() = default;
    virtual bool configure(const RadioConfig& config) = 0;
    virtual bool tune(Frequency freq) = 0;
    virtual bool set_tx_power(PowerLevel power_dbm) = 0;
    virtual bool transmit(ConstSampleBuffer samples) = 0;
    virtual size_t receive(SampleBuffer buffer) = 0;
    virtual bool set_tx_enabled(bool enabled) = 0;
    virtual RadioConfig current_config() const = 0;
};

}  // namespace cirradio::hal
