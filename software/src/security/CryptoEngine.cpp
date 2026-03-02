#include "security/CryptoEngine.h"
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <memory>

namespace cirradio::security {

namespace {

struct EvpCipherCtxDeleter {
    void operator()(EVP_CIPHER_CTX* ctx) const {
        EVP_CIPHER_CTX_free(ctx);
    }
};
using EvpCipherCtxPtr = std::unique_ptr<EVP_CIPHER_CTX, EvpCipherCtxDeleter>;

}  // namespace

std::optional<std::vector<uint8_t>> CryptoEngine::encrypt(
    std::span<const uint8_t> key,
    std::span<const uint8_t> plaintext) {

    if (key.size() != kKeySize) {
        return std::nullopt;
    }

    // Generate random IV
    std::vector<uint8_t> iv(kIvSize);
    if (RAND_bytes(iv.data(), static_cast<int>(kIvSize)) != 1) {
        return std::nullopt;
    }

    EvpCipherCtxPtr ctx(EVP_CIPHER_CTX_new());
    if (!ctx) {
        return std::nullopt;
    }

    if (EVP_EncryptInit_ex(ctx.get(), EVP_aes_256_gcm(), nullptr,
                           nullptr, nullptr) != 1) {
        return std::nullopt;
    }

    // Set IV length
    if (EVP_CIPHER_CTX_ctrl(ctx.get(), EVP_CTRL_GCM_SET_IVLEN,
                            static_cast<int>(kIvSize), nullptr) != 1) {
        return std::nullopt;
    }

    // Set key and IV
    if (EVP_EncryptInit_ex(ctx.get(), nullptr, nullptr,
                           key.data(), iv.data()) != 1) {
        return std::nullopt;
    }

    // Encrypt
    std::vector<uint8_t> ciphertext(plaintext.size());
    int out_len = 0;

    if (!plaintext.empty()) {
        if (EVP_EncryptUpdate(ctx.get(), ciphertext.data(), &out_len,
                              plaintext.data(),
                              static_cast<int>(plaintext.size())) != 1) {
            return std::nullopt;
        }
    }

    int final_len = 0;
    if (EVP_EncryptFinal_ex(ctx.get(), ciphertext.data() + out_len,
                            &final_len) != 1) {
        return std::nullopt;
    }
    ciphertext.resize(static_cast<size_t>(out_len + final_len));

    // Get GCM tag
    std::vector<uint8_t> tag(kTagSize);
    if (EVP_CIPHER_CTX_ctrl(ctx.get(), EVP_CTRL_GCM_GET_TAG,
                            static_cast<int>(kTagSize), tag.data()) != 1) {
        return std::nullopt;
    }

    // Wire format: IV + ciphertext + tag
    std::vector<uint8_t> result;
    result.reserve(kIvSize + ciphertext.size() + kTagSize);
    result.insert(result.end(), iv.begin(), iv.end());
    result.insert(result.end(), ciphertext.begin(), ciphertext.end());
    result.insert(result.end(), tag.begin(), tag.end());

    return result;
}

std::optional<std::vector<uint8_t>> CryptoEngine::decrypt(
    std::span<const uint8_t> key,
    std::span<const uint8_t> ciphertext) {

    if (key.size() != kKeySize) {
        return std::nullopt;
    }

    // Minimum size: IV + tag (ciphertext can be empty)
    if (ciphertext.size() < kIvSize + kTagSize) {
        return std::nullopt;
    }

    // Parse wire format
    auto iv = ciphertext.subspan(0, kIvSize);
    auto encrypted = ciphertext.subspan(kIvSize,
                                        ciphertext.size() - kIvSize - kTagSize);
    auto tag = ciphertext.subspan(ciphertext.size() - kTagSize, kTagSize);

    EvpCipherCtxPtr ctx(EVP_CIPHER_CTX_new());
    if (!ctx) {
        return std::nullopt;
    }

    if (EVP_DecryptInit_ex(ctx.get(), EVP_aes_256_gcm(), nullptr,
                           nullptr, nullptr) != 1) {
        return std::nullopt;
    }

    if (EVP_CIPHER_CTX_ctrl(ctx.get(), EVP_CTRL_GCM_SET_IVLEN,
                            static_cast<int>(kIvSize), nullptr) != 1) {
        return std::nullopt;
    }

    if (EVP_DecryptInit_ex(ctx.get(), nullptr, nullptr,
                           key.data(), iv.data()) != 1) {
        return std::nullopt;
    }

    // Set expected tag
    if (EVP_CIPHER_CTX_ctrl(ctx.get(), EVP_CTRL_GCM_SET_TAG,
                            static_cast<int>(kTagSize),
                            const_cast<uint8_t*>(tag.data())) != 1) {
        return std::nullopt;
    }

    // Decrypt
    std::vector<uint8_t> plaintext(encrypted.size());
    int out_len = 0;

    if (!encrypted.empty()) {
        if (EVP_DecryptUpdate(ctx.get(), plaintext.data(), &out_len,
                              encrypted.data(),
                              static_cast<int>(encrypted.size())) != 1) {
            return std::nullopt;
        }
    }

    // Verify tag
    int final_len = 0;
    if (EVP_DecryptFinal_ex(ctx.get(), plaintext.data() + out_len,
                            &final_len) != 1) {
        return std::nullopt;  // Authentication failed
    }
    plaintext.resize(static_cast<size_t>(out_len + final_len));

    return plaintext;
}

std::optional<std::vector<uint8_t>> CryptoEngine::wrap_key(
    std::span<const uint8_t> kek,
    std::span<const uint8_t> key_to_wrap) {
    return encrypt(kek, key_to_wrap);
}

std::optional<std::vector<uint8_t>> CryptoEngine::unwrap_key(
    std::span<const uint8_t> kek,
    std::span<const uint8_t> wrapped_key) {
    return decrypt(kek, wrapped_key);
}

}  // namespace cirradio::security
