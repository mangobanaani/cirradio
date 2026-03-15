// software/src/security/SoftHsm.h
#pragma once
#include "security/Pkcs11Hsm.h"
#include <string>

namespace cirradio::security {

// SoftHSM2-backed test shim.
// Creates a fresh token in a temp dir on construction; cleans up on destruction.
// Inherits all PKCS#11 operations from Pkcs11Hsm.
// Overrides export_raw / import_raw for simulation key provisioning.
class SoftHsm : public Pkcs11Hsm {
public:
    SoftHsm();
    ~SoftHsm() override;

    SoftHsm(const SoftHsm&) = delete;
    SoftHsm& operator=(const SoftHsm&) = delete;

    // Export raw key bytes via C_GetAttributeValue (works because test keys
    // are created with CKA_EXTRACTABLE=TRUE).
    std::optional<std::vector<uint8_t>> export_raw(CkHandle kh) override;

    // Import raw key bytes as a session key object via C_CreateObject.
    std::optional<HsmKeyHandle> import_raw(
        std::span<const uint8_t> key_bytes, const KeyLabel& label) override;

private:
    struct Init {
        void*             lib;
        CK_FUNCTION_LIST* fn;
        CK_SESSION_HANDLE session;
        CK_SLOT_ID        slot;
        std::string       tmp_dir;
    };
    static Init setup();

    explicit SoftHsm(Init&& i);

    std::string tmp_dir_;

    static constexpr const char* kLibPath =
        "/opt/homebrew/lib/softhsm/libsofthsm2.so";
    static constexpr const char* kPin = "1234";
};

}  // namespace cirradio::security
