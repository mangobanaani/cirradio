#include "fhss/HopSequencer.h"
#include <openssl/evp.h>
#include <cstring>
#include <memory>
#include <stdexcept>

namespace cirradio::fhss {

namespace {

struct EvpCipherCtxDeleter {
    void operator()(EVP_CIPHER_CTX* ctx) const {
        EVP_CIPHER_CTX_free(ctx);
    }
};
using EvpCipherCtxPtr = std::unique_ptr<EVP_CIPHER_CTX, EvpCipherCtxDeleter>;

static constexpr size_t kKeySize = 32;   // AES-256
static constexpr size_t kBlockSize = 16; // AES block size
static constexpr int kMaxBlacklistAttempts = 10;

}  // namespace

HopSequencer::HopSequencer(std::span<const uint8_t> fhek,
                           hal::Frequency min_freq,
                           hal::Frequency max_freq,
                           hal::Frequency channel_spacing)
    : fhek_(fhek.begin(), fhek.end()),
      min_freq_(min_freq),
      max_freq_(max_freq),
      channel_spacing_(channel_spacing) {

    if (fhek_.size() != kKeySize) {
        throw std::invalid_argument("FHEK must be 32 bytes");
    }
    if (min_freq >= max_freq) {
        throw std::invalid_argument("min_freq must be less than max_freq");
    }
    if (channel_spacing == 0) {
        throw std::invalid_argument("channel_spacing must be non-zero");
    }

    num_channels_ = (max_freq - min_freq) / channel_spacing;
    if (num_channels_ == 0) {
        throw std::invalid_argument("Band too narrow for given channel spacing");
    }
}

uint64_t HopSequencer::compute_channel_index(uint8_t slot, uint32_t frame,
                                              uint8_t attempt) const {
    // Build 16-byte input block:
    // [slot (1 byte)][padding (3 bytes)][frame (4 bytes LE)][zeros (7 bytes)][attempt (1 byte)]
    uint8_t input[kBlockSize] = {};
    input[0] = slot;
    // bytes 1-3: padding (already zero)
    // bytes 4-7: frame number in little-endian
    std::memcpy(&input[4], &frame, sizeof(frame));
    // bytes 8-14: zeros (already zero)
    // byte 15: attempt number (0 for first try, 1+ for blacklist rehash)
    input[15] = attempt;

    // AES-256-ECB encrypt single block
    uint8_t output[kBlockSize] = {};

    EvpCipherCtxPtr ctx(EVP_CIPHER_CTX_new());
    if (!ctx) {
        throw std::runtime_error("Failed to create EVP_CIPHER_CTX");
    }

    if (EVP_EncryptInit_ex(ctx.get(), EVP_aes_256_ecb(), nullptr,
                           fhek_.data(), nullptr) != 1) {
        throw std::runtime_error("EVP_EncryptInit_ex failed");
    }

    // Disable padding since we're encrypting exactly one block
    EVP_CIPHER_CTX_set_padding(ctx.get(), 0);

    int out_len = 0;
    if (EVP_EncryptUpdate(ctx.get(), output, &out_len,
                          input, kBlockSize) != 1) {
        throw std::runtime_error("EVP_EncryptUpdate failed");
    }

    int final_len = 0;
    if (EVP_EncryptFinal_ex(ctx.get(), output + out_len, &final_len) != 1) {
        throw std::runtime_error("EVP_EncryptFinal_ex failed");
    }

    // Take first 8 bytes as uint64_t (little-endian)
    uint64_t raw_value = 0;
    std::memcpy(&raw_value, output, sizeof(raw_value));

    return raw_value % num_channels_;
}

hal::Frequency HopSequencer::get_hop_frequency(uint8_t slot,
                                                uint32_t frame) const {
    // First attempt with attempt=0
    uint64_t channel_idx = compute_channel_index(slot, frame, 0);
    hal::Frequency freq = min_freq_ + channel_idx * channel_spacing_;

    if (blacklist_.empty()) {
        return freq;
    }

    // Check blacklist and rehash if needed
    for (int attempt = 1; attempt <= kMaxBlacklistAttempts; ++attempt) {
        if (blacklist_.find(freq) == blacklist_.end()) {
            return freq;  // Not blacklisted
        }
        // Rehash with incremented attempt number
        channel_idx = compute_channel_index(slot, frame,
                                            static_cast<uint8_t>(attempt));
        freq = min_freq_ + channel_idx * channel_spacing_;
    }

    // After max attempts, return whatever we have
    return freq;
}

void HopSequencer::blacklist_frequency(hal::Frequency freq) {
    blacklist_.insert(freq);
}

void HopSequencer::clear_blacklist() {
    blacklist_.clear();
}

uint64_t HopSequencer::num_channels() const {
    return num_channels_;
}

}  // namespace cirradio::fhss
