#include "security/SoftCryptoHal.h"
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/x509.h>
#include <memory>

namespace cirradio::security {

namespace {

struct EvpPkeyDeleter {
    void operator()(EVP_PKEY* p) const { EVP_PKEY_free(p); }
};
using EvpPkeyPtr = std::unique_ptr<EVP_PKEY, EvpPkeyDeleter>;

struct EvpMdCtxDeleter {
    void operator()(EVP_MD_CTX* ctx) const { EVP_MD_CTX_free(ctx); }
};
using EvpMdCtxPtr = std::unique_ptr<EVP_MD_CTX, EvpMdCtxDeleter>;

// Deserialize a DER-encoded key into EVP_PKEY (private key)
EvpPkeyPtr load_private_key_der(std::span<const uint8_t> der) {
    const unsigned char* p = der.data();
    EVP_PKEY* pkey = d2i_PrivateKey(EVP_PKEY_EC, nullptr, &p,
                                     static_cast<long>(der.size()));
    return EvpPkeyPtr(pkey);
}

// Deserialize a DER-encoded public key into EVP_PKEY
EvpPkeyPtr load_public_key_der(std::span<const uint8_t> der) {
    const unsigned char* p = der.data();
    EVP_PKEY* pkey = d2i_PUBKEY(nullptr, &p,
                                 static_cast<long>(der.size()));
    return EvpPkeyPtr(pkey);
}

}  // namespace

std::optional<std::vector<uint8_t>> SoftCryptoHal::encrypt(
    std::span<const uint8_t> key,
    std::span<const uint8_t> plaintext) {
    return engine_.encrypt(key, plaintext);
}

std::optional<std::vector<uint8_t>> SoftCryptoHal::decrypt(
    std::span<const uint8_t> key,
    std::span<const uint8_t> ciphertext) {
    return engine_.decrypt(key, ciphertext);
}

std::optional<std::vector<uint8_t>> SoftCryptoHal::wrap_key(
    std::span<const uint8_t> kek,
    std::span<const uint8_t> key_to_wrap) {
    return engine_.wrap_key(kek, key_to_wrap);
}

std::optional<std::vector<uint8_t>> SoftCryptoHal::unwrap_key(
    std::span<const uint8_t> kek,
    std::span<const uint8_t> wrapped_key) {
    return engine_.unwrap_key(kek, wrapped_key);
}

std::optional<std::vector<uint8_t>> SoftCryptoHal::sign(
    std::span<const uint8_t> private_key,
    std::span<const uint8_t> data) {

    auto pkey = load_private_key_der(private_key);
    if (!pkey) {
        return std::nullopt;
    }

    EvpMdCtxPtr ctx(EVP_MD_CTX_new());
    if (!ctx) {
        return std::nullopt;
    }

    if (EVP_DigestSignInit(ctx.get(), nullptr, EVP_sha384(), nullptr,
                           pkey.get()) != 1) {
        return std::nullopt;
    }

    if (EVP_DigestSignUpdate(ctx.get(), data.data(), data.size()) != 1) {
        return std::nullopt;
    }

    // Determine signature length
    size_t sig_len = 0;
    if (EVP_DigestSignFinal(ctx.get(), nullptr, &sig_len) != 1) {
        return std::nullopt;
    }

    std::vector<uint8_t> signature(sig_len);
    if (EVP_DigestSignFinal(ctx.get(), signature.data(), &sig_len) != 1) {
        return std::nullopt;
    }
    signature.resize(sig_len);

    return signature;
}

bool SoftCryptoHal::verify(
    std::span<const uint8_t> public_key,
    std::span<const uint8_t> data,
    std::span<const uint8_t> signature) {

    auto pkey = load_public_key_der(public_key);
    if (!pkey) {
        return false;
    }

    EvpMdCtxPtr ctx(EVP_MD_CTX_new());
    if (!ctx) {
        return false;
    }

    if (EVP_DigestVerifyInit(ctx.get(), nullptr, EVP_sha384(), nullptr,
                             pkey.get()) != 1) {
        return false;
    }

    if (EVP_DigestVerifyUpdate(ctx.get(), data.data(), data.size()) != 1) {
        return false;
    }

    return EVP_DigestVerifyFinal(ctx.get(), signature.data(),
                                  signature.size()) == 1;
}

}  // namespace cirradio::security
