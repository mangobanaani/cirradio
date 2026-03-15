// software/embedded/hal/zynq7045_hal.cpp
#include "zynq7045_hal.hpp"

namespace cirradio::hal {

Zynq7045HAL::Zynq7045HAL()
    : regs_("/dev/uio0"), radio_(), gps_() {}

IRadioHal&        Zynq7045HAL::radio() { return radio_; }
IGpsHal&          Zynq7045HAL::gps()   { return gps_; }
drivers::AxiRegs& Zynq7045HAL::regs()  { return regs_; }

} // namespace cirradio::hal
