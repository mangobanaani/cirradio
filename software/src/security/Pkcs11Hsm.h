// software/src/security/Pkcs11Hsm.h
#pragma once
#include "security/IHsmEngine.h"
#include "security/pkcs11_types.h"
#include <string>

namespace cirradio::security {

// PKCS#11 implementation via dlopen. Supports any vendor HSM.
// Set PKCS11_MODULE_PATH env to the .so/.dylib path before construction.
class Pkcs11Hsm : public IHsmEngine {
public:
    explicit Pkcs11Hsm(const std::string& module_path);
    ~Pkcs11Hsm() override;

    Pkcs11Hsm(const Pkcs11Hsm&) = delete;
    Pkcs11Hsm& operator=(const Pkcs11Hsm&) = delete;

    HsmKeyHandle generate_key(KeyType type, const KeyLabel& label) override;
    std::optional<std::vector<uint8_t>> encrypt(
        CkHandle kh, std::span<const uint8_t> plaintext) override;
    std::optional<std::vector<uint8_t>> decrypt(
        CkHandle kh, std::span<const uint8_t> ciphertext) override;
    std::optional<std::vector<uint8_t>> wrap_key(
        CkHandle wrapping_key, CkHandle key_to_wrap) override;
    std::optional<HsmKeyHandle> unwrap_key(
        CkHandle wrapping_key, std::span<const uint8_t> wrapped) override;
    // Returns nullopt on production HSM — key extraction not permitted.
    std::optional<std::vector<uint8_t>> export_raw(CkHandle kh) override;
    // Returns nullopt on production HSM — raw import not permitted.
    std::optional<HsmKeyHandle> import_raw(
        std::span<const uint8_t> key_bytes, const KeyLabel& label) override;
    bool destroy_key(CkHandle kh) override;\
    CkHandle import_ec_key_der(std::span<const uint8_t> der_priv) override;\
    std::optional<std::vector<uint8_t>> ecies_decrypt(\
        CkHandle ik_handle, std::span<const uint8_t> payload) override;\
    void shutdown() override;

protected:
    // Protected constructor for SoftHsm to pass a pre-opened session.
    Pkcs11Hsm(void* lib, CK_FUNCTION_LIST* fn,
              CK_SESSION_HANDLE session, CK_SLOT_ID slot) noexcept;

    void*              lib_     = nullptr;
    CK_FUNCTION_LIST*  fn_      = nullptr;
    CK_SESSION_HANDLE  session_ = 0;
    CK_SLOT_ID         slot_id_ = 0;

    // Exposed to SoftHsm for export_raw / import_raw / generate_key / unwrap_key.
    CK_RV ck_get_attribute(CK_OBJECT_HANDLE obj,
                           CK_ATTRIBUTE* templ, CK_ULONG count);
    CK_RV ck_create_object(CK_ATTRIBUTE* templ, CK_ULONG count,
                           CK_OBJECT_HANDLE* obj);
    CK_RV ck_generate_key(CK_MECHANISM* mech,
                          CK_ATTRIBUTE* templ, CK_ULONG count,
                          CK_OBJECT_HANDLE* key);
    CK_RV ck_unwrap_key(CK_MECHANISM* mech, CK_OBJECT_HANDLE wrapping,
                        CK_BYTE_PTR in, CK_ULONG in_len,
                        CK_ATTRIBUTE* templ, CK_ULONG count,
                        CK_OBJECT_HANDLE* new_key);
    CK_RV ck_logout(CK_SESSION_HANDLE s);
    CK_RV ck_close_session(CK_SESSION_HANDLE s);

private:
    static constexpr size_t kIvLen  = 12;
    bool finalized_ = false;
    static constexpr size_t kTagLen = 16;
    static constexpr size_t kKeyLen = 32;

    // Convenience call helpers (avoid repeated reinterpret_casts).
    CK_RV ck_init(void* args);
    CK_RV ck_get_slot_list(CK_BBOOL token_present,
                           CK_SLOT_ID* slots, CK_ULONG* count);
    CK_RV ck_open_session(CK_SLOT_ID slot, CK_FLAGS flags,
                          CK_SESSION_HANDLE* phSession);
    CK_RV ck_login(CK_SESSION_HANDLE s, CK_USER_TYPE user,
                   CK_UTF8CHAR_PTR pin, CK_ULONG len);
    CK_RV ck_finalize(void* args);
    CK_RV ck_destroy_object(CK_OBJECT_HANDLE obj);
    CK_RV ck_encrypt_init(CK_MECHANISM* mech, CK_OBJECT_HANDLE key);
    CK_RV ck_encrypt(CK_BYTE_PTR in, CK_ULONG in_len,
                     CK_BYTE_PTR out, CK_ULONG* out_len);
    CK_RV ck_decrypt_init(CK_MECHANISM* mech, CK_OBJECT_HANDLE key);
    CK_RV ck_decrypt(CK_BYTE_PTR in, CK_ULONG in_len,
                     CK_BYTE_PTR out, CK_ULONG* out_len);
    CK_RV ck_wrap_key(CK_MECHANISM* mech, CK_OBJECT_HANDLE wrapping,
                      CK_OBJECT_HANDLE to_wrap,
                      CK_BYTE_PTR out, CK_ULONG* out_len);
};

}  // namespace cirradio::security
