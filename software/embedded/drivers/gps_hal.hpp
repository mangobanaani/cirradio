// software/embedded/drivers/gps_hal.hpp
#pragma once
#include "hal/IGpsHal.h"
#include <gps.h>

namespace cirradio::drivers {

class GpsHal final : public hal::IGpsHal {
public:
    GpsHal();
    ~GpsHal() override;
    std::optional<hal::GpsPosition> get_position() override;
    std::optional<hal::Timestamp>   get_time() override;
    std::optional<hal::Timestamp>   get_pps_timestamp() override;

private:
    struct gps_data_t gps_data_;
    bool connected_ = false;
};

} // namespace cirradio::drivers
