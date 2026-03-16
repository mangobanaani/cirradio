// software/embedded/drivers/iio_radio.cpp
#include "iio_radio.hpp"
#include <algorithm>
#include <stdexcept>
#include <cstring>
#include <string>

namespace cirradio::drivers {

IioRadio::IioRadio() {
    ctx_ = iio_create_local_context();
    if (!ctx_) throw std::runtime_error("iio_create_local_context failed");

    phy_ = iio_context_find_device(ctx_, "ad9361-phy");
    dds_ = iio_context_find_device(ctx_, "cf-ad9361-dds-core-lpc");
    adc_ = iio_context_find_device(ctx_, "cf-ad9361-lpc");
    if (!phy_ || !dds_ || !adc_)
        throw std::runtime_error("AD9361 IIO devices not found");

    if (!init_buffers())
        throw std::runtime_error("Failed to create IIO buffers");
}

IioRadio::~IioRadio() {
    if (tx_buf_) iio_buffer_destroy(tx_buf_);
    if (rx_buf_) iio_buffer_destroy(rx_buf_);
    if (ctx_)    iio_context_destroy(ctx_);
}

bool IioRadio::tune(hal::Frequency freq) {
    auto* ch = iio_device_find_channel(phy_, "altvoltage0", true);
    if (!ch) return false;
    std::string freq_str = std::to_string(freq);
    return iio_channel_attr_write(ch, "frequency", freq_str.c_str()) >= 0;
}

bool IioRadio::transmit(hal::ConstSampleBuffer samples) {
    if (!tx_buf_) return false;
    auto* buf_ptr = static_cast<int16_t*>(iio_buffer_first(tx_buf_,
        iio_device_find_channel(dds_, "voltage0", true)));
    size_t n = std::min(samples.size(), static_cast<size_t>(BUF_SAMPLES));
    for (size_t i = 0; i < n; i++) {
        buf_ptr[i * 2]     = static_cast<int16_t>(samples[i].real() * 32767.0f);
        buf_ptr[i * 2 + 1] = static_cast<int16_t>(samples[i].imag() * 32767.0f);
    }
    return iio_buffer_push(tx_buf_) > 0;
}

size_t IioRadio::receive(hal::SampleBuffer buffer) {
    if (!rx_buf_) return 0;
    ssize_t nbytes = iio_buffer_refill(rx_buf_);
    if (nbytes < 0) return 0;
    auto* buf_ptr = static_cast<const int16_t*>(iio_buffer_first(rx_buf_,
        iio_device_find_channel(adc_, "voltage0", false)));
    size_t n = std::min(buffer.size(),
                        static_cast<size_t>(nbytes / (2 * sizeof(int16_t))));
    for (size_t i = 0; i < n; i++)
        buffer[i] = {buf_ptr[i * 2] / 32768.0f, buf_ptr[i * 2 + 1] / 32768.0f};
    return n;
}

bool IioRadio::init_buffers() {
    auto* tx_ch = iio_device_find_channel(dds_, "voltage0", true);
    auto* rx_ch = iio_device_find_channel(adc_, "voltage0", false);
    if (!tx_ch || !rx_ch) return false;
    iio_channel_enable(tx_ch);
    iio_channel_enable(rx_ch);
    tx_buf_ = iio_device_create_buffer(dds_, BUF_SAMPLES, false);
    rx_buf_ = iio_device_create_buffer(adc_, BUF_SAMPLES, false);
    return tx_buf_ && rx_buf_;
}

bool IioRadio::configure(const hal::RadioConfig& cfg) { config_ = cfg; return tune(cfg.center_freq); }

bool IioRadio::set_tx_power(hal::PowerLevel power_dbm) {
    // AD9361 TX attenuation: 0–89.75 dBm in 0.25 dB steps, as millidB integer.
    // IIO attribute "hardwaregain" on TX voltage0 channel, signed dB.
    auto* ch = iio_device_find_channel(phy_, "voltage0", true); // TX direction
    if (!ch) return false;
    // Clamp to AD9361 range: −89.75 to 0 dBm TX gain
    float clamped = std::clamp(static_cast<float>(power_dbm), -89.75f, 0.0f);
    std::string val = std::to_string(clamped);
    return iio_channel_attr_write(ch, "hardwaregain", val.c_str()) >= 0;
}

bool IioRadio::set_tx_enabled(bool) { return true; }
hal::RadioConfig IioRadio::current_config() const { return config_; }

} // namespace cirradio::drivers
