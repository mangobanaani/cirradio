// software/src/security/SecurityManager.h
#pragma once
#include "security/IAxiRegs.h"
#include "security/IHsmEngine.h"
#include "security/KeyManager.h"
#include "security/ZeroizeEngine.h"
#include "security/TamperMonitor.h"
#include "security/KeyFillPort.h"
#include <memory>
#include <atomic>
#include <functional>

namespace cirradio::security {

class SecurityManager {
public:
    SecurityManager(KeyManager& km, IHsmEngine& hsm,
                    IAxiRegs& axi, CkHandle ik_handle);
    ~SecurityManager();

    SecurityManager(const SecurityManager&) = delete;
    SecurityManager& operator=(const SecurityManager&) = delete;

    // Synchronous zeroize. Called by TamperMonitor or externally. noexcept.
    void zeroize_immediate() noexcept;

    // Start tamper monitoring thread.
    void start();

    KeyFillPort& keyfill_port() noexcept { return *kfp_; }

    bool is_zeroized() const noexcept { return zeroized_.load(); }

    void set_post_zeroize_hook(std::function<void()> hook) { post_zeroize_hook_ = std::move(hook); }

private:
    ZeroizeEngine                  zeroize_engine_;
    std::unique_ptr<KeyFillPort>   kfp_;
    std::unique_ptr<TamperMonitor> tamper_;
    std::atomic<bool>              zeroized_{false};
    std::function<void()>          post_zeroize_hook_;
};

}  // namespace cirradio::security
