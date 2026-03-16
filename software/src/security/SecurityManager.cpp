// software/src/security/SecurityManager.cpp
#include "security/SecurityManager.h"
#include "security/KeyFillPort.h"
#include <spdlog/spdlog.h>

namespace cirradio::security {

SecurityManager::SecurityManager(KeyManager& km, IHsmEngine& hsm,
                                 IAxiRegs& axi, CkHandle ik_handle)
    : zeroize_engine_(km, hsm, axi, ik_handle)
{
    kfp_ = std::make_unique<KeyFillPort>(km, hsm, ik_handle);
    zeroize_engine_.set_keyfill_port(kfp_.get());

    tamper_ = std::make_unique<TamperMonitor>(
        [this](int /*ch*/) { zeroize_immediate(); });
}

SecurityManager::~SecurityManager() {
    tamper_->stop();
}

void SecurityManager::zeroize_immediate() noexcept {
    bool expected = false;
    if (!zeroized_.compare_exchange_strong(expected, true)) return;
    spdlog::critical("[SECURITY] zeroize_immediate triggered");
    zeroize_engine_.run();
    if (post_zeroize_hook_) {
        try { post_zeroize_hook_(); } catch (...) {}
    }
}

void SecurityManager::start() {
    tamper_->start();
}

}  // namespace cirradio::security
