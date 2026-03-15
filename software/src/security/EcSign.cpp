// software/src/security/EcSign.cpp
#include "security/EcSign.h"
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/x509.h>
#include <memory>

namespace cirradio::security {

namespace {
struct EvpKeyDeleter { void operator()(EVP_PKEY* p) { EVP_PKEY_free(p); } };
struct EvpMdCtxDeleter { void operator()(EVP_MD_CTX* p) { EVP_MD_CTX_free(p); } };
using EvpKeyPtr   = std::unique_ptr<EVP_PKEY, EvpKeyDeleter>;
using EvpMdCtxPtr = std::unique_ptr<EVP_MD_CTX, EvpMdCtxDeleter>;
}

std::optional<std::vector<uint8_t>> ec_sign(
    std::span<const uint8_t> der_private_key,
    std::span<const uint8_t> data)
{
    const unsigned char* p = der_private_key.data();
    EvpKeyPtr pkey(d2i_PrivateKey(EVP_PKEY_EC, nullptr, &p,
                                  static_cast<long>(der_private_key.size())));
    if (!pkey) return std::nullopt;

    EvpMdCtxPtr ctx(EVP_MD_CTX_new());
    if (!ctx) return std::nullopt;
    if (EVP_DigestSignInit(ctx.get(), nullptr, EVP_sha384(), nullptr, pkey.get()) != 1)
        return std::nullopt;

    size_t sig_len = 0;
    if (EVP_DigestSign(ctx.get(), nullptr, &sig_len,
                       data.data(), data.size()) != 1) return std::nullopt;
    std::vector<uint8_t> sig(sig_len);
    if (EVP_DigestSign(ctx.get(), sig.data(), &sig_len,
                       data.data(), data.size()) != 1) return std::nullopt;
    sig.resize(sig_len);
    return sig;
}

bool ec_verify(
    std::span<const uint8_t> der_public_key,
    std::span<const uint8_t> data,
    std::span<const uint8_t> signature)
{
    const unsigned char* p = der_public_key.data();
    EvpKeyPtr pkey(d2i_PUBKEY(nullptr, &p,
                               static_cast<long>(der_public_key.size())));
    if (!pkey) return false;

    EvpMdCtxPtr ctx(EVP_MD_CTX_new());
    if (!ctx) return false;
    if (EVP_DigestVerifyInit(ctx.get(), nullptr, EVP_sha384(), nullptr, pkey.get()) != 1)
        return false;
    return EVP_DigestVerify(ctx.get(),
                            signature.data(), signature.size(),
                            data.data(), data.size()) == 1;
}

}  // namespace cirradio::security
