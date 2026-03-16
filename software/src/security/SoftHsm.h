// software/src/security/SoftHsm.h
#pragma once
#include "security/Pkcs11Hsm.h"
#include <string>
#include <unordered_map>
#include <cstdint>

namespace cirradio::security {

// SoftHSM2-backed test shim.
// Uses a process-wide singleton SoftHSM2 session pool; each instance opens
// its own session on the shared token. The library is never finalized to
// avoid SoftHSM2's no-reinit restriction.
class SoftHsm : public Pkcs11Hsm {
public:
    struct CtorArgs {
        void*              lib;
        CK_FUNCTION_LIST*  fn;
        CK_SESSION_HANDLE  session;
        CK_SLOT_ID         slot;
    };

    SoftHsm();
    explicit SoftHsm(CtorArgs&& a);
    ~SoftHsm() override;

    SoftHsm(const SoftHsm&) = delete;
    SoftHsm& operator=(const SoftHsm&) = delete;

    // Export raw key bytes via C_GetAttributeValue (works because test keys
    // are created with CKA_EXTRACTABLE=TRUE, CKA_SENSITIVE=FALSE).
    std::optional<std::vector<uint8_t>> export_raw(CkHandle kh) override;

    // Import raw key bytes as a session key object via C_CreateObject.
    std::optional<HsmKeyHandle> import_raw(
        std::span<const uint8_t> key_bytes, const KeyLabel& label) override;

    // Override to generate non-sensitive (extractable) keys for test use.
    HsmKeyHandle generate_key(KeyType type, const KeyLabel& label) override;

    // Override to unwrap into non-sensitive (extractable) keys for test use.
    std::optional<HsmKeyHandle> unwrap_key(
        CkHandle wrapping_key, std::span<const uint8_t> wrapped) override;

    // Store DER-encoded EC P-384 private key in memory; returns opaque handle.
    CkHandle import_ec_key_der(std::span<const uint8_t> der_priv) override;

    // ECIES decrypt using stored EC identity key (pure OpenSSL, no PKCS#11).
    std::optional<std::vector<uint8_t>> ecies_decrypt(
        CkHandle ik_handle, std::span<const uint8_t> payload) override;

    // Idempotent teardown: clear EC keys, close PKCS#11 session.
    void shutdown() override;

private:
    // EC identity key store: handle → DER-encoded private key bytes
    // Handle space starts at 0xEC000000 to avoid collision with PKCS#11 handles.
    std::unordered_map<CkHandle, std::vector<uint8_t>> ec_keys_;
    CkHandle next_ec_handle_ = 0xEC000000ULL;
    bool soft_finalized_ = false;
};

}  // namespace cirradio::security
