// software/src/security/ZeroizeEngine.cpp
#include "security/ZeroizeEngine.h"
#include "security/KeyFillPort.h"
#include <spdlog/spdlog.h>
#include <cstring>
#include <ctime>

#ifdef __linux__
#include <unistd.h>
#include <sys/reboot.h>
#endif

namespace cirradio::security {

ZeroizeEngine::ZeroizeEngine(KeyManager& km, IHsmEngine& hsm,
                             IAxiRegs& axi, CkHandle ik_handle)
    : km_(km), hsm_(hsm), axi_(axi), ik_handle_(ik_handle)
{}

void ZeroizeEngine::log_step(int step, const std::string& msg, bool ok) noexcept {
    try {
        spdlog::critical("[ZEROIZE] step={} {} status={}", step, msg,
                         ok ? "OK" : "FAIL");
    } catch (...) {}
}

ZeroizeResult ZeroizeEngine::run() noexcept {
    triggered_ = true;
    ZeroizeResult result;

    // Step 1: FPGA registers
    try {
        axi_.zeroize_fhek();
        result.step1_fpga_ok = true;
    } catch (...) {}
    log_step(1, "FPGA FHEK scrub", result.step1_fpga_ok);

    // Step 2: HSM key destruction
    try {
        km_.zeroize();
        if (ik_handle_ != 0) {
            hsm_.destroy_key(ik_handle_);
            ik_handle_ = 0;
        }
        hsm_.shutdown();
        result.step2_hsm_ok = true;
    } catch (...) {}
    log_step(2, "HSM key destruction", result.step2_hsm_ok);

    // Step 3: RAM scrub
    try {
        if (kfp_) kfp_->clear_session();
        result.step3_ram_ok = true;
    } catch (...) {}
    log_step(3, "RAM scrub", result.step3_ram_ok);

    // Step 4: Audit log
    try {
        struct timespec ts{};
        clock_gettime(CLOCK_REALTIME, &ts);
        spdlog::critical("[AUDIT] zeroize ts={} fpga={} hsm={} ram={}",
                         ts.tv_sec,
                         result.step1_fpga_ok, result.step2_hsm_ok,
                         result.step3_ram_ok);
        result.step4_audit_ok = true;
    } catch (...) {}
    log_step(4, "audit log", result.step4_audit_ok);

    // Step 5: Halt
    log_step(5, "system halt", true);
    try { axi_.halt_fpga_clocks(); } catch (...) {}

#ifdef __linux__
    sync();
    reboot(LINUX_REBOOT_CMD_POWER_OFF);
#endif

    return result;
}

}  // namespace cirradio::security
