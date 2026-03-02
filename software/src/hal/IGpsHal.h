#pragma once
#include "Types.h"
#include <optional>

namespace cirradio::hal {

class IGpsHal {
public:
    virtual ~IGpsHal() = default;
    virtual std::optional<GpsPosition> get_position() = 0;
    virtual std::optional<Timestamp> get_time() = 0;
    virtual std::optional<Timestamp> get_pps_timestamp() = 0;
};

}  // namespace cirradio::hal
