// software/embedded/drivers/axi_regs.cpp
#include "axi_regs.hpp"
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdexcept>
#include <cstring>

namespace cirradio::drivers {

AxiRegs::AxiRegs(const char* uio_dev) {
    fd_ = open(uio_dev, O_RDWR);
    if (fd_ < 0)
        throw std::runtime_error(std::string("Cannot open ") + uio_dev);

    base_ = static_cast<volatile uint32_t*>(
        mmap(nullptr, PAGE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd_, 0));
    if (base_ == MAP_FAILED) {
        close(fd_);
        throw std::runtime_error("mmap failed for axi_regs");
    }
}

AxiRegs::~AxiRegs() {
    if (base_ != MAP_FAILED) munmap(const_cast<uint32_t*>(base_), PAGE_SIZE);
    if (fd_ >= 0) close(fd_);
}

void AxiRegs::write_reg(uint32_t offset, uint32_t value) {
    base_[offset / 4] = value;
}

uint32_t AxiRegs::read_reg(uint32_t offset) const {
    return base_[offset / 4];
}

void AxiRegs::set_fhek(std::span<const uint8_t> fhek) {
    if (fhek.size() != 32)
        throw std::invalid_argument("FHEK must be 32 bytes");
    for (int i = 0; i < 8; i++) {
        uint32_t word;
        std::memcpy(&word, fhek.data() + i * 4, 4);
        write_reg(REG_FHEK_0 + i * 4, word);
    }
}

void AxiRegs::set_blacklist(std::span<const uint32_t> freqs_khz) {
    for (size_t i = 0; i < std::min(freqs_khz.size(), static_cast<size_t>(REG_BLACKLIST_COUNT)); i++)
        write_reg(REG_BLACKLIST_BASE + i * 4, freqs_khz[i]);
}

void AxiRegs::set_slot_bitmap(uint32_t bitmap) { write_reg(REG_SLOT_BITMAP, bitmap); }
void AxiRegs::set_tx_power(int32_t dBm_x100) { write_reg(REG_TX_POWER, static_cast<uint32_t>(dBm_x100)); }

uint32_t AxiRegs::status() const { return read_reg(REG_STATUS); }
bool AxiRegs::hop_locked() const { return (status() & STATUS_HOP_LOCK) != 0; }
bool AxiRegs::gps_holdover() const { return (status() & STATUS_GPS_HOLDOVER) != 0; }
int32_t  AxiRegs::rssi_dBm_x100() const { return static_cast<int32_t>(read_reg(REG_RSSI)); }
uint32_t AxiRegs::hop_counter() const { return read_reg(REG_HOP_COUNTER); }

void AxiRegs::zeroize_fhek() {
    for (uint32_t i = 0; i < 8; ++i)
        write_reg(REG_FHEK_0 + i * 4, 0u);
    write_reg(REG_CONTROL, CTRL_FHEK_ZEROIZE);
}
void AxiRegs::halt_fpga_clocks() {
    write_reg(REG_CONTROL, CTRL_CLOCK_HALT);
}

void AxiRegs::set_hop_rate(uint32_t hops_per_sec) {
    write_reg(REG_HOP_RATE, hops_per_sec);
}
void AxiRegs::set_blacklist_size(uint32_t count) {
    write_reg(REG_BLACKLIST_SIZE, count);
}
void AxiRegs::set_interleaver_depth(uint32_t depth) {
    write_reg(REG_INTERLEAVER_DEPTH, depth);
}
void AxiRegs::set_pa_ramp_steps(uint32_t cycles) {
    write_reg(REG_PA_RAMP_STEPS, cycles);
}
void AxiRegs::set_emcon_ctrl(uint32_t value) {
    write_reg(REG_EMCON_CTRL, value);
}
void AxiRegs::write_emcon_unlock() {
    write_reg(REG_EMCON_UNLOCK, 0xA5C3'3C5Au);
}
uint32_t AxiRegs::emcon_level() const {
    return read_reg(REG_EMCON_CTRL) & 0x3u;
}
} // namespace cirradio::drivers
