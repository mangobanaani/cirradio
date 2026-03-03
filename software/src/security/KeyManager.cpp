#include "security/KeyManager.h"
#include <openssl/rand.h>
#include <openssl/crypto.h>
#include <stdexcept>

namespace cirradio::security {

namespace {
constexpr size_t kKeySize = 32;
}

KeyManager::KeyManager() = default;

void KeyManager::initialize_kek() {
    kek_ = generate_random_key();
    initialized_ = true;
}

void KeyManager::set_kek(const std::vector<uint8_t>& kek) {
    if (kek.size() != kKeySize) {
        throw std::invalid_argument("KEK must be 32 bytes");
    }
    kek_ = kek;
    initialized_ = true;
}

std::vector<uint8_t> KeyManager::generate_tek() {
    tek_ = generate_random_key();
    return tek_;
}

std::vector<uint8_t> KeyManager::generate_fhek() {
    fhek_ = generate_random_key();
    return fhek_;
}

std::vector<uint8_t> KeyManager::rotate_tek() {
    tek_ = generate_random_key();
    ++key_epoch_;
    return tek_;
}

std::vector<uint8_t> KeyManager::current_tek() const {
    if (tek_.empty()) {
        throw std::runtime_error("TEK not available");
    }
    return tek_;
}

std::vector<uint8_t> KeyManager::current_fhek() const {
    if (fhek_.empty()) {
        throw std::runtime_error("FHEK not available");
    }
    return fhek_;
}

void KeyManager::set_tek(const std::vector<uint8_t>& tek) {
    if (tek.size() != kKeySize) {
        throw std::invalid_argument("TEK must be 32 bytes");
    }
    tek_ = tek;
}

void KeyManager::set_fhek(const std::vector<uint8_t>& fhek) {
    if (fhek.size() != kKeySize) {
        throw std::invalid_argument("FHEK must be 32 bytes");
    }
    fhek_ = fhek;
}

uint32_t KeyManager::key_epoch() const {
    return key_epoch_;
}

OtarMessage KeyManager::generate_otar_message() {
    if (kek_.empty() || tek_.empty() || fhek_.empty()) {
        throw std::runtime_error("Cannot generate OTAR message: keys not initialized");
    }

    auto wrapped_tek = engine_.wrap_key(kek_, tek_);
    if (!wrapped_tek) {
        throw std::runtime_error("Failed to wrap TEK");
    }

    auto wrapped_fhek = engine_.wrap_key(kek_, fhek_);
    if (!wrapped_fhek) {
        throw std::runtime_error("Failed to wrap FHEK");
    }

    ++key_epoch_;

    OtarMessage msg;
    msg.key_epoch = key_epoch_;
    msg.wrapped_tek = std::move(*wrapped_tek);
    msg.wrapped_fhek = std::move(*wrapped_fhek);
    return msg;
}

bool KeyManager::process_otar_message(const OtarMessage& msg) {
    if (kek_.empty()) {
        return false;
    }

    // Reject stale or replayed messages
    if (msg.key_epoch <= key_epoch_) {
        return false;
    }

    auto tek = engine_.unwrap_key(kek_, msg.wrapped_tek);
    if (!tek) {
        return false;
    }

    auto fhek = engine_.unwrap_key(kek_, msg.wrapped_fhek);
    if (!fhek) {
        return false;
    }

    tek_ = std::move(*tek);
    fhek_ = std::move(*fhek);
    key_epoch_ = msg.key_epoch;
    initialized_ = true;
    return true;
}

void KeyManager::zeroize() {
    secure_zero(kek_);
    secure_zero(tek_);
    secure_zero(fhek_);
    kek_.clear();
    tek_.clear();
    fhek_.clear();
    key_epoch_ = 0;
    initialized_ = false;
}

bool KeyManager::is_initialized() const {
    return initialized_;
}

void KeyManager::secure_zero(std::vector<uint8_t>& v) {
    if (!v.empty()) {
        OPENSSL_cleanse(v.data(), v.size());
    }
}

std::vector<uint8_t> KeyManager::generate_random_key() {
    std::vector<uint8_t> key(kKeySize);
    if (RAND_bytes(key.data(), static_cast<int>(kKeySize)) != 1) {
        throw std::runtime_error("Failed to generate random key");
    }
    return key;
}

}  // namespace cirradio::security
