// software/embedded/hal/zynq7045_hal.hpp
#pragma once
#include "drivers/iio_radio.hpp"
#include "drivers/axi_regs.hpp"
#include "drivers/gps_hal.hpp"

namespace cirradio::hal {

class Zynq7045HAL {
public:
    Zynq7045HAL();
    IRadioHal&          radio();
    IGpsHal&            gps();
    drivers::AxiRegs&   regs();

private:
    drivers::AxiRegs   regs_;
    drivers::IioRadio  radio_;
    drivers::GpsHal    gps_;
};

} // namespace cirradio::hal
