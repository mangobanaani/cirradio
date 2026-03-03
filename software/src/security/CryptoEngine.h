#pragma once
#include <vector>
#include <cstdint>
#include <optional>
#include <span>

namespace cirradio::security {

class CryptoEngine {
public:
    // Encrypt plaintext with AES-256-GCM. Returns IV + ciphertext + tag.
    std::optional<std::vector<uint8_t>> encrypt(
        std::span<const uint8_t> key,
        std::span<const uint8_t> plaintext);

    // Decrypt AES-256-GCM ciphertext. Input is IV + ciphertext + tag.
    // Returns nullopt if authentication fails.
    std::optional<std::vector<uint8_t>> decrypt(
        std::span<const uint8_t> key,
        std::span<const uint8_t> ciphertext);

    // Wrap a key under a KEK (uses AES-256-GCM internally)
    std::optional<std::vector<uint8_t>> wrap_key(
        std::span<const uint8_t> kek,
        std::span<const uint8_t> key_to_wrap);

    // Unwrap a key using KEK
    std::optional<std::vector<uint8_t>> unwrap_key(
        std::span<const uint8_t> kek,
        std::span<const uint8_t> wrapped_key);

private:
    static constexpr size_t kKeySize = 32;   // AES-256
    static constexpr size_t kIvSize = 12;    // GCM recommended IV
    static constexpr size_t kTagSize = 16;   // GCM tag
};

}  // namespace cirradio::security
