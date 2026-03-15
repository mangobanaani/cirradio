// software/src/security/KeyManager.cpp
#include "security/KeyManager.h"
#include <stdexcept>

namespace cirradio::security {

KeyManager::KeyManager(IHsmEngine& hsm) : hsm_(hsm) {}

HsmKeyHandle KeyManager::import_raw_or_throw(
    const std::vector<uint8_t>& key, const std::string& label)
{
    auto h = hsm_.import_raw(key, label);
    if (!h) throw std::runtime_error(
        "HSM does not support import_raw (production HSM path)");
    return std::move(*h);
}

void KeyManager::initialize_kek() {
    kek_ = hsm_.generate_key(KeyType::AES256, "kek");
}

void KeyManager::set_kek_raw(const std::vector<uint8_t>& kek) {
    kek_ = import_raw_or_throw(kek, "kek");
}

void KeyManager::generate_tek() {
    tek_ = hsm_.generate_key(KeyType::AES256, "tek");
}

void KeyManager::generate_fhek() {
    fhek_ = hsm_.generate_key(KeyType::AES256, "fhek");
}

void KeyManager::rotate_tek() {
    tek_ = hsm_.generate_key(KeyType::AES256, "tek");
    ++key_epoch_;
}

void KeyManager::set_tek_raw(const std::vector<uint8_t>& tek) {
    tek_ = import_raw_or_throw(tek, "tek");
}

void KeyManager::set_fhek_raw(const std::vector<uint8_t>& fhek) {
    fhek_ = import_raw_or_throw(fhek, "fhek");
}

std::optional<std::vector<uint8_t>> KeyManager::encrypt_with_tek(
    std::span<const uint8_t> plaintext)
{
    if (!tek_) throw std::runtime_error("TEK not initialized");
    return hsm_.encrypt(tek_->get(), plaintext);
}

std::optional<std::vector<uint8_t>> KeyManager::decrypt_with_tek(
    std::span<const uint8_t> ciphertext)
{
    if (!tek_) throw std::runtime_error("TEK not initialized");
    return hsm_.decrypt(tek_->get(), ciphertext);
}

std::vector<uint8_t> KeyManager::export_fhek_for_fpga() {
    if (!fhek_) throw std::runtime_error("FHEK not initialized");
    auto raw = hsm_.export_raw(fhek_->get());
    if (!raw) throw std::runtime_error("HSM declined FHEK export");
    return *raw;
}

std::vector<uint8_t> KeyManager::export_tek_for_distribution() {
    if (!tek_) throw std::runtime_error("TEK not initialized");
    auto raw = hsm_.export_raw(tek_->get());
    if (!raw) throw std::runtime_error("HSM declined TEK export");
    return *raw;
}

OtarMessage KeyManager::generate_otar_message() {
    if (!kek_ || !tek_ || !fhek_)
        throw std::runtime_error("Keys not initialized");
    auto wt = hsm_.wrap_key(kek_->get(), tek_->get());
    auto wf = hsm_.wrap_key(kek_->get(), fhek_->get());
    if (!wt || !wf) throw std::runtime_error("Key wrap failed");
    ++key_epoch_;
    return OtarMessage{key_epoch_, std::move(*wt), std::move(*wf)};
}

bool KeyManager::process_otar_message(const OtarMessage& msg) {
    if (!kek_) return false;
    if (msg.key_epoch <= key_epoch_) return false;
    auto tek  = hsm_.unwrap_key(kek_->get(), msg.wrapped_tek);
    auto fhek = hsm_.unwrap_key(kek_->get(), msg.wrapped_fhek);
    if (!tek || !fhek) return false;
    tek_  = std::move(*tek);
    fhek_ = std::move(*fhek);
    key_epoch_ = msg.key_epoch;
    return true;
}

void KeyManager::zeroize() {
    kek_.reset(); tek_.reset(); fhek_.reset();
    key_epoch_ = 0;
}

bool KeyManager::is_initialized() const {
    return kek_.has_value() && tek_.has_value() && fhek_.has_value();
}

uint32_t KeyManager::key_epoch() const { return key_epoch_; }

}  // namespace cirradio::security
