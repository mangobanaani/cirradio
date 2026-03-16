// software/src/security/ZeroizeEngine.h
#pragma once
#include "security/IAxiRegs.h"
#include "security/IHsmEngine.h"
#include "security/KeyManager.h"
#include <cstdint>
#include <string>

namespace cirradio::security {

class KeyFillPort;

struct ZeroizeResult {
    bool step1_fpga_ok   = false;
    bool step2_hsm_ok    = false;
    bool step3_ram_ok    = false;
    bool step4_audit_ok  = false;
};

class ZeroizeEngine {
public:
    ZeroizeEngine(KeyManager& km, IHsmEngine& hsm, IAxiRegs& axi,
                  CkHandle ik_handle);
    ~ZeroizeEngine() = default;

    ZeroizeEngine(const ZeroizeEngine&) = delete;
    ZeroizeEngine& operator=(const ZeroizeEngine&) = delete;

    void set_keyfill_port(KeyFillPort* kfp) noexcept { kfp_ = kfp; }

    // Execute all 5 steps synchronously. noexcept.
    // On non-Linux builds, step 5 logs and returns instead of calling reboot().
    ZeroizeResult run() noexcept;

    bool triggered() const noexcept { return triggered_; }

private:
    KeyManager&   km_;
    IHsmEngine&   hsm_;
    IAxiRegs&     axi_;
    CkHandle      ik_handle_;
    KeyFillPort*  kfp_ = nullptr;
    bool          triggered_ = false;

    void log_step(int step, const std::string& msg, bool ok) noexcept;
};

}  // namespace cirradio::security
