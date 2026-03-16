// software/src/security/IHsmEngine.h
#pragma once
#include <cstdint>
#include <vector>
#include <optional>
#include <span>
#include <string>

namespace cirradio::security {

using CkHandle = uint64_t;  // opaque PKCS#11 CK_OBJECT_HANDLE

class IHsmEngine;

// RAII wrapper: calls engine.destroy_key(handle) on scope exit.
class HsmKeyHandle {
public:
    HsmKeyHandle() noexcept = default;
    HsmKeyHandle(IHsmEngine& engine, CkHandle handle) noexcept
        : engine_(&engine), handle_(handle) {}
    ~HsmKeyHandle() { reset(); }
    HsmKeyHandle(HsmKeyHandle&& o) noexcept
        : engine_(o.engine_), handle_(o.handle_)
    { o.engine_ = nullptr; o.handle_ = 0; }
    HsmKeyHandle& operator=(HsmKeyHandle&& o) noexcept {
        if (this != &o) { reset(); engine_ = o.engine_; handle_ = o.handle_;
                          o.engine_ = nullptr; o.handle_ = 0; }
        return *this;
    }
    HsmKeyHandle(const HsmKeyHandle&) = delete;
    HsmKeyHandle& operator=(const HsmKeyHandle&) = delete;
    CkHandle get() const noexcept { return handle_; }
    bool valid() const noexcept { return engine_ != nullptr; }
private:
    void reset();
    IHsmEngine* engine_ = nullptr;
    CkHandle    handle_ = 0;
};

enum class KeyType { AES256 };
using KeyLabel = std::string;

class IHsmEngine {
public:
    virtual ~IHsmEngine() = default;

    // Generate a new key; handle is owned by returned HsmKeyHandle.
    virtual HsmKeyHandle generate_key(KeyType type, const KeyLabel& label) = 0;

    // AES-256-GCM encrypt. Returns IV(12)+ciphertext+tag(16).
    virtual std::optional<std::vector<uint8_t>> encrypt(
        CkHandle kh, std::span<const uint8_t> plaintext) = 0;

    // AES-256-GCM decrypt. Input is IV(12)+ciphertext+tag(16). Returns nullopt on auth failure.
    virtual std::optional<std::vector<uint8_t>> decrypt(
        CkHandle kh, std::span<const uint8_t> ciphertext) = 0;

    // Wrap key_to_wrap under wrapping_key (CKM_AES_KEY_WRAP / RFC 3394).
    virtual std::optional<std::vector<uint8_t>> wrap_key(
        CkHandle wrapping_key, CkHandle key_to_wrap) = 0;

    // Unwrap wrapped bytes under wrapping_key; return handle to new key object.
    virtual std::optional<HsmKeyHandle> unwrap_key(
        CkHandle wrapping_key, std::span<const uint8_t> wrapped_key_bytes) = 0;

    // Export raw key bytes. Returns nullopt on production HSM (key extraction prohibited).
    // Returns actual bytes on SoftHsm for test/simulation use.
    virtual std::optional<std::vector<uint8_t>> export_raw(CkHandle kh) = 0;

    // Import raw key bytes as a new key object. Returns nullopt on production HSM.
    // SoftHsm implements this for simulation key provisioning.
    virtual std::optional<HsmKeyHandle> import_raw(
        std::span<const uint8_t> key_bytes, const KeyLabel& label) = 0;

    // Destroy key object; called by HsmKeyHandle destructor.
    virtual bool destroy_key(CkHandle kh) = 0;

    // Store DER-encoded EC P-384 private key; returns opaque handle.
    // SoftHsm: stores in memory. Pkcs11Hsm: C_CreateObject(CKO_PRIVATE_KEY).
    virtual CkHandle import_ec_key_der(std::span<const uint8_t> der_priv) = 0;

    // ECIES decrypt using device identity key.
    // Payload format: ephemeral_pub(97B P-384 uncompressed) | IV(12B) | ciphertext | GCM_tag(16B)
    // Derives shared secret via ECDH P-384, applies HKDF-SHA-384("cirradio-keyfill"),
    // decrypts with AES-256-GCM. Returns plaintext or nullopt on any failure.
    virtual std::optional<std::vector<uint8_t>>
        ecies_decrypt(CkHandle ik_handle,
                      std::span<const uint8_t> ecies_payload) = 0;

    // Idempotent teardown: C_Logout + C_CloseSession + C_Finalize.
    // Safe to call from both ZeroizeEngine and destructor.
    virtual void shutdown() = 0;
};

// HsmKeyHandle::reset() defined here to avoid circular header dependency.
inline void HsmKeyHandle::reset() {
    if (engine_ && handle_ != 0) {
        engine_->destroy_key(handle_);
        engine_ = nullptr;
        handle_ = 0;
    }
}

}  // namespace cirradio::security
