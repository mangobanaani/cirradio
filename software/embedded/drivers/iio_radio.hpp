// software/embedded/drivers/iio_radio.hpp
#pragma once
#include "hal/IRadioHal.h"
#include <iio.h>
#include <memory>

namespace cirradio::drivers {

class IioRadio final : public hal::IRadioHal {
public:
    explicit IioRadio();
    ~IioRadio() override;

    bool configure(const hal::RadioConfig& config) override;
    bool tune(hal::Frequency freq) override;
    bool set_tx_power(hal::PowerLevel power_dbm) override;
    bool transmit(hal::ConstSampleBuffer samples) override;
    size_t receive(hal::SampleBuffer buffer) override;
    bool set_tx_enabled(bool enabled) override;
    hal::RadioConfig current_config() const override;

private:
    struct iio_context* ctx_    = nullptr;
    struct iio_device*  phy_    = nullptr;
    struct iio_device*  dds_    = nullptr;
    struct iio_device*  adc_    = nullptr;
    struct iio_buffer*  tx_buf_ = nullptr;
    struct iio_buffer*  rx_buf_ = nullptr;
    hal::RadioConfig    config_;
    static constexpr size_t BUF_SAMPLES = 4096;

    bool init_buffers();
};

} // namespace cirradio::drivers
