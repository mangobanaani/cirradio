// software/embedded/drivers/gps_hal.cpp
#include "gps_hal.hpp"
#include <cstring>
#include <chrono>

namespace cirradio::drivers {

GpsHal::GpsHal() {
    if (gps_open("localhost", DEFAULT_GPSD_PORT, &gps_data_) == 0) {
        gps_stream(&gps_data_, WATCH_ENABLE | WATCH_JSON | WATCH_PPS, nullptr);
        connected_ = true;
    }
}

GpsHal::~GpsHal() {
    if (connected_) {
        gps_stream(&gps_data_, WATCH_DISABLE, nullptr);
        gps_close(&gps_data_);
    }
}

std::optional<hal::GpsPosition> GpsHal::get_position() {
    if (!connected_) return std::nullopt;
    if (gps_read(&gps_data_, nullptr, 0) < 0) return std::nullopt;
    if ((gps_data_.set & LATLON_SET) == 0) return std::nullopt;
    hal::GpsPosition pos{};
    pos.latitude  = gps_data_.fix.latitude;
    pos.longitude = gps_data_.fix.longitude;
    pos.altitude  = gps_data_.fix.altMSL;
    pos.valid     = true;
    pos.time      = hal::Timestamp{};
    return pos;
}

std::optional<hal::Timestamp> GpsHal::get_time() {
    if (!connected_) return std::nullopt;
    if (gps_read(&gps_data_, nullptr, 0) < 0) return std::nullopt;
    if ((gps_data_.set & TIME_SET) == 0) return std::nullopt;
    auto dur = std::chrono::seconds(gps_data_.fix.time.tv_sec)
             + std::chrono::nanoseconds(gps_data_.fix.time.tv_nsec);
    return hal::Timestamp(std::chrono::duration_cast<hal::Timestamp::duration>(dur));
}

std::optional<hal::Timestamp> GpsHal::get_pps_timestamp() {
    if (!connected_) return std::nullopt;
    if ((gps_data_.set & PPSTIME_IS) == 0) return std::nullopt;
    auto dur = std::chrono::seconds(gps_data_.pps.tv_sec)
             + std::chrono::nanoseconds(gps_data_.pps.tv_nsec);
    return hal::Timestamp(std::chrono::duration_cast<hal::Timestamp::duration>(dur));
}

} // namespace cirradio::drivers
