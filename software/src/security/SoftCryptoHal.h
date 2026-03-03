#pragma once
#include "hal/ICryptoHal.h"
#include "security/CryptoEngine.h"

namespace cirradio::security {

class SoftCryptoHal : public hal::ICryptoHal {
public:
    std::optional<std::vector<uint8_t>> encrypt(
        std::span<const uint8_t> key,
        std::span<const uint8_t> plaintext) override;
    std::optional<std::vector<uint8_t>> decrypt(
        std::span<const uint8_t> key,
        std::span<const uint8_t> ciphertext) override;
    std::optional<std::vector<uint8_t>> wrap_key(
        std::span<const uint8_t> kek,
        std::span<const uint8_t> key_to_wrap) override;
    std::optional<std::vector<uint8_t>> unwrap_key(
        std::span<const uint8_t> kek,
        std::span<const uint8_t> wrapped_key) override;
    std::optional<std::vector<uint8_t>> sign(
        std::span<const uint8_t> private_key,
        std::span<const uint8_t> data) override;
    bool verify(
        std::span<const uint8_t> public_key,
        std::span<const uint8_t> data,
        std::span<const uint8_t> signature) override;

private:
    CryptoEngine engine_;
};

}  // namespace cirradio::security
