// software/src/security/EcSign.h
#pragma once
#include <vector>
#include <optional>
#include <span>
#include <cstdint>

namespace cirradio::security {

// EC P-384 / SHA-384 sign using DER-encoded private key.
std::optional<std::vector<uint8_t>> ec_sign(
    std::span<const uint8_t> der_private_key,
    std::span<const uint8_t> data);

// EC P-384 / SHA-384 verify using DER-encoded public key.
bool ec_verify(
    std::span<const uint8_t> der_public_key,
    std::span<const uint8_t> data,
    std::span<const uint8_t> signature);

}  // namespace cirradio::security
