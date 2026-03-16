// software/src/security/KeyFillPort.h
#pragma once
#include "security/IHsmEngine.h"
#include "security/KeyManager.h"
#include <cstdint>
#include <vector>
#include <optional>
#include <span>
#include <atomic>

namespace cirradio::security {

enum class FillMsgType : uint8_t {
    HELLO       = 0x01,
    NONCE       = 0x02,
    IDENTITY    = 0x03,
    DEV_ATTEST  = 0x04,
    GUN_ATTEST  = 0x05,
    KEY_BLOCK   = 0x06,
    ACK         = 0x07,
    NAK         = 0x08,
};

enum class FillState : uint8_t {
    IDLE,
    HELLO_RCVD,
    NONCE_SENT,
    IDENTITY_VERIFIED,
    DEV_ATTEST_SENT,
    GUN_ATTEST_VERIFIED,
    KEYS_RECEIVED,
    ACK,
};

struct FillFrame {
    FillMsgType type;
    std::vector<uint8_t> payload;
};

class KeyFillPort {
public:
    // Production: uart_fd = -1 opens /dev/ttyPS1 internally.
    // Test injection: pass a socketpair fd.
    KeyFillPort(KeyManager& km, IHsmEngine& hsm, CkHandle ik_handle,
                int uart_fd = -1);
    ~KeyFillPort();

    KeyFillPort(const KeyFillPort&) = delete;
    KeyFillPort& operator=(const KeyFillPort&) = delete;

    // Run one fill session (blocking, 30 s timeout).
    bool run_session();

    // Scrub session state (called by ZeroizeEngine step 3).
    void clear_session() noexcept;

    void add_trusted_gun_pubkey(std::vector<uint8_t> der_pub);

private:
    KeyManager&  km_;
    IHsmEngine&  hsm_;
    CkHandle     ik_handle_;
    int          fd_ = -1;
    bool         owns_fd_ = false;

    FillState state_ = FillState::IDLE;
    std::vector<uint8_t> device_nonce_{};
    std::vector<uint8_t> gun_nonce_{};
    std::vector<std::vector<uint8_t>> trusted_gun_pubkeys_;

    bool send_frame(FillMsgType type, std::span<const uint8_t> payload);
    std::optional<FillFrame> recv_frame(int timeout_ms = 30000);
    bool verify_gun_cert(std::span<const uint8_t> cert_der);
    bool verify_ecdsa_p384(std::span<const uint8_t> pubkey_der,
                           std::span<const uint8_t> msg,
                           std::span<const uint8_t> sig);
    std::vector<uint8_t> sign_with_ik(std::span<const uint8_t> msg);
    void send_nak();
    void reset_state() noexcept;
};

}  // namespace cirradio::security
