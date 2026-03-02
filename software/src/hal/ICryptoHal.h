#pragma once
#include <vector>
#include <cstdint>
#include <optional>
#include <span>

namespace cirradio::hal {

class ICryptoHal {
public:
    virtual ~ICryptoHal() = default;
    virtual std::optional<std::vector<uint8_t>> encrypt(
        std::span<const uint8_t> key,
        std::span<const uint8_t> plaintext) = 0;
    virtual std::optional<std::vector<uint8_t>> decrypt(
        std::span<const uint8_t> key,
        std::span<const uint8_t> ciphertext) = 0;
    virtual std::optional<std::vector<uint8_t>> wrap_key(
        std::span<const uint8_t> kek,
        std::span<const uint8_t> key_to_wrap) = 0;
    virtual std::optional<std::vector<uint8_t>> unwrap_key(
        std::span<const uint8_t> kek,
        std::span<const uint8_t> wrapped_key) = 0;
    virtual std::optional<std::vector<uint8_t>> sign(
        std::span<const uint8_t> private_key,
        std::span<const uint8_t> data) = 0;
    virtual bool verify(
        std::span<const uint8_t> public_key,
        std::span<const uint8_t> data,
        std::span<const uint8_t> signature) = 0;
};

}  // namespace cirradio::hal
