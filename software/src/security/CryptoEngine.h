// software/src/security/CryptoEngine.h
#pragma once
#include "security/IHsmEngine.h"
#include <vector>
#include <optional>
#include <span>
#include <cstdint>

namespace cirradio::security {

// Convenience wrapper that binds an IHsmEngine to a specific key handle.
// encrypt/decrypt/wrap_key/unwrap_key delegate to the HSM.
class CryptoEngine {
public:
    CryptoEngine(IHsmEngine& hsm, CkHandle kh) : hsm_(hsm), kh_(kh) {}

    // AES-256-GCM encrypt (IV+ciphertext+tag wire format).
    std::optional<std::vector<uint8_t>> encrypt(
        std::span<const uint8_t> plaintext) {
        return hsm_.encrypt(kh_, plaintext);
    }

    // AES-256-GCM decrypt. Returns nullopt on auth failure.
    std::optional<std::vector<uint8_t>> decrypt(
        std::span<const uint8_t> ciphertext) {
        return hsm_.decrypt(kh_, ciphertext);
    }

    // Wrap another key (kh_ acts as KEK).
    std::optional<std::vector<uint8_t>> wrap_key(CkHandle key_to_wrap) {
        return hsm_.wrap_key(kh_, key_to_wrap);
    }

    // Unwrap bytes (kh_ acts as KEK). Returns handle to new key.
    std::optional<HsmKeyHandle> unwrap_key(
        std::span<const uint8_t> wrapped) {
        return hsm_.unwrap_key(kh_, wrapped);
    }

private:
    IHsmEngine& hsm_;
    CkHandle    kh_;
};

}  // namespace cirradio::security
