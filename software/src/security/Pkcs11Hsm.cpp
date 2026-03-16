// software/src/security/Pkcs11Hsm.cpp
#include "security/Pkcs11Hsm.h"
#include <dlfcn.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/kdf.h>
#include <spdlog/spdlog.h>
#include <stdexcept>
#include <cstring>

namespace cirradio::security {

// ── Public constructor: dlopen + find token + open user session ──────────────
Pkcs11Hsm::Pkcs11Hsm(const std::string& module_path) {
    lib_ = dlopen(module_path.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!lib_) {
        throw std::runtime_error("dlopen " + module_path + " failed: " + dlerror());
    }
    auto get_fn = reinterpret_cast<CK_C_GetFunctionList_t>(
        dlsym(lib_, "C_GetFunctionList"));
    if (!get_fn) throw std::runtime_error("C_GetFunctionList not found");

    CK_RV rv = get_fn(&fn_);
    if (rv != CKR_OK) throw std::runtime_error("C_GetFunctionList rv=" + std::to_string(rv));

    rv = ck_init(nullptr);
    if (rv != CKR_OK && rv != CKR_CRYPTOKI_ALREADY_INITIALIZED)
        throw std::runtime_error("C_Initialize rv=" + std::to_string(rv));

    CK_SLOT_ID slots[16]; CK_ULONG slot_count = 16;
    rv = ck_get_slot_list(CK_TRUE, slots, &slot_count);
    if (rv != CKR_OK || slot_count == 0)
        throw std::runtime_error("No tokens found");
    slot_id_ = slots[0];

    rv = ck_open_session(slot_id_,
                         CKF_SERIAL_SESSION | CKF_RW_SESSION, &session_);
    if (rv != CKR_OK)
        throw std::runtime_error("C_OpenSession rv=" + std::to_string(rv));

    const char* pin = "1234";
    rv = ck_login(session_, CKU_USER,
                  reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(pin)), 4);
    if (rv != CKR_OK && rv != CKR_USER_ALREADY_LOGGED_IN)
        throw std::runtime_error("C_Login rv=" + std::to_string(rv));
}

// ── Protected constructor: SoftHsm passes pre-opened session ─────────────────
Pkcs11Hsm::Pkcs11Hsm(void* lib, CK_FUNCTION_LIST* fn,
                     CK_SESSION_HANDLE session, CK_SLOT_ID slot) noexcept
    : lib_(lib), fn_(fn), session_(session), slot_id_(slot) {}

Pkcs11Hsm::~Pkcs11Hsm() {\
    shutdown();\
    if (lib_) { dlclose(lib_); lib_ = nullptr; }\
}

// ── IHsmEngine methods ────────────────────────────────────────────────────────
HsmKeyHandle Pkcs11Hsm::generate_key(KeyType /*type*/, const KeyLabel& /*label*/) {
    CK_MECHANISM mech{CKM_AES_KEY_GEN, nullptr, 0};
    CK_OBJECT_CLASS obj_class = CKO_SECRET_KEY;
    CK_KEY_TYPE key_type      = CKK_AES;
    CK_ULONG key_len          = static_cast<CK_ULONG>(kKeyLen);
    CK_BBOOL ck_true          = CK_TRUE;
    CK_BBOOL ck_false         = CK_FALSE;
    CK_ATTRIBUTE templ[] = {
        {CKA_KEY_TYPE,  &key_type,  sizeof(key_type)},
        {CKA_VALUE_LEN, &key_len,   sizeof(key_len)},
        {CKA_TOKEN,     &ck_false,  sizeof(ck_false)},  // session object
        {CKA_SENSITIVE, &ck_true,   sizeof(ck_true)},
        {CKA_EXTRACTABLE,&ck_true,  sizeof(ck_true)},   // needed for C_WrapKey
        {CKA_ENCRYPT,   &ck_true,   sizeof(ck_true)},
        {CKA_DECRYPT,   &ck_true,   sizeof(ck_true)},
        {CKA_WRAP,      &ck_true,   sizeof(ck_true)},
        {CKA_UNWRAP,    &ck_true,   sizeof(ck_true)},
    };
    CK_OBJECT_HANDLE kh = CK_INVALID_HANDLE;
    CK_RV rv = ck_generate_key(&mech, templ, 9, &kh);
    if (rv != CKR_OK)
        throw std::runtime_error("C_GenerateKey rv=" + std::to_string(rv));
    return HsmKeyHandle(*this, static_cast<CkHandle>(kh));
}

std::optional<std::vector<uint8_t>> Pkcs11Hsm::encrypt(
    CkHandle kh, std::span<const uint8_t> plaintext)
{
    // Generate random IV
    std::vector<uint8_t> iv(kIvLen);
    if (RAND_bytes(iv.data(), static_cast<int>(kIvLen)) != 1) return std::nullopt;

    CK_GCM_PARAMS gcm{iv.data(), kIvLen, kIvLen * 8, nullptr, 0, kTagLen * 8};
    CK_MECHANISM mech{CKM_AES_GCM, &gcm, sizeof(gcm)};

    CK_RV rv = ck_encrypt_init(&mech, static_cast<CK_OBJECT_HANDLE>(kh));
    if (rv != CKR_OK) return std::nullopt;

    // First call: get output size (plaintext_len + tag_len)
    CK_ULONG out_len = static_cast<CK_ULONG>(plaintext.size() + kTagLen);

    std::vector<uint8_t> ct(out_len);
    rv = ck_encrypt(
        const_cast<CK_BYTE_PTR>(plaintext.data()),
        static_cast<CK_ULONG>(plaintext.size()),
        ct.data(), &out_len);
    if (rv != CKR_OK) return std::nullopt;
    ct.resize(out_len);

    // Wire format: IV(12) + C_Encrypt output (ciphertext + tag)
    std::vector<uint8_t> result;
    result.reserve(kIvLen + ct.size());
    result.insert(result.end(), iv.begin(), iv.end());
    result.insert(result.end(), ct.begin(), ct.end());
    return result;
}

std::optional<std::vector<uint8_t>> Pkcs11Hsm::decrypt(
    CkHandle kh, std::span<const uint8_t> ciphertext)
{
    if (ciphertext.size() < kIvLen + kTagLen) return std::nullopt;

    auto iv      = ciphertext.subspan(0, kIvLen);
    auto ct_tag  = ciphertext.subspan(kIvLen);  // ciphertext + tag

    CK_GCM_PARAMS gcm{
        const_cast<CK_BYTE_PTR>(iv.data()), kIvLen, kIvLen * 8,
        nullptr, 0, kTagLen * 8};
    CK_MECHANISM mech{CKM_AES_GCM, &gcm, sizeof(gcm)};

    CK_RV rv = ck_decrypt_init(&mech, static_cast<CK_OBJECT_HANDLE>(kh));
    if (rv != CKR_OK) return std::nullopt;

    CK_ULONG out_len = static_cast<CK_ULONG>(ct_tag.size());  // upper bound
    std::vector<uint8_t> plaintext(out_len);
    rv = ck_decrypt(
        const_cast<CK_BYTE_PTR>(ct_tag.data()),
        static_cast<CK_ULONG>(ct_tag.size()),
        plaintext.data(), &out_len);
    if (rv != CKR_OK) return std::nullopt;  // auth failure
    plaintext.resize(out_len);
    return plaintext;
}

std::optional<std::vector<uint8_t>> Pkcs11Hsm::wrap_key(
    CkHandle wrapping_key, CkHandle key_to_wrap)
{
    CK_MECHANISM mech{CKM_AES_KEY_WRAP, nullptr, 0};
    CK_ULONG wrapped_len = 0;
    // First call: get required buffer size
    CK_RV rv = ck_wrap_key(&mech,
        static_cast<CK_OBJECT_HANDLE>(wrapping_key),
        static_cast<CK_OBJECT_HANDLE>(key_to_wrap),
        nullptr, &wrapped_len);
    if (rv != CKR_OK) return std::nullopt;

    std::vector<uint8_t> wrapped(wrapped_len);
    rv = ck_wrap_key(&mech,
        static_cast<CK_OBJECT_HANDLE>(wrapping_key),
        static_cast<CK_OBJECT_HANDLE>(key_to_wrap),
        wrapped.data(), &wrapped_len);
    if (rv != CKR_OK) return std::nullopt;
    wrapped.resize(wrapped_len);
    return wrapped;
}

std::optional<HsmKeyHandle> Pkcs11Hsm::unwrap_key(
    CkHandle wrapping_key, std::span<const uint8_t> wrapped)
{
    CK_MECHANISM mech{CKM_AES_KEY_WRAP, nullptr, 0};
    CK_OBJECT_CLASS obj_class = CKO_SECRET_KEY;
    CK_KEY_TYPE key_type      = CKK_AES;
    CK_ULONG key_len          = static_cast<CK_ULONG>(kKeyLen);
    CK_BBOOL ck_true          = CK_TRUE;
    CK_BBOOL ck_false         = CK_FALSE;
    CK_ATTRIBUTE templ[] = {
        {CKA_CLASS,      &obj_class, sizeof(obj_class)},
        {CKA_KEY_TYPE,   &key_type,  sizeof(key_type)},
        {CKA_TOKEN,      &ck_false,  sizeof(ck_false)},
        {CKA_SENSITIVE,  &ck_true,   sizeof(ck_true)},
        {CKA_EXTRACTABLE,&ck_true,   sizeof(ck_true)},
        {CKA_ENCRYPT,    &ck_true,   sizeof(ck_true)},
        {CKA_DECRYPT,    &ck_true,   sizeof(ck_true)},
        {CKA_WRAP,       &ck_true,   sizeof(ck_true)},
        {CKA_UNWRAP,     &ck_true,   sizeof(ck_true)},
    };
    CK_OBJECT_HANDLE new_key = CK_INVALID_HANDLE;
    CK_RV rv = ck_unwrap_key(&mech,
        static_cast<CK_OBJECT_HANDLE>(wrapping_key),
        const_cast<CK_BYTE_PTR>(wrapped.data()),
        static_cast<CK_ULONG>(wrapped.size()),
        templ, 9, &new_key);
    if (rv != CKR_OK) return std::nullopt;
    return HsmKeyHandle(*this, static_cast<CkHandle>(new_key));
}

// Production HSM: key extraction not permitted.
std::optional<std::vector<uint8_t>> Pkcs11Hsm::export_raw(CkHandle /*kh*/) {
    return std::nullopt;
}

// Production HSM: raw import not permitted.
std::optional<HsmKeyHandle> Pkcs11Hsm::import_raw(
    std::span<const uint8_t> /*key_bytes*/, const KeyLabel& /*label*/) {
    return std::nullopt;
}

bool Pkcs11Hsm::destroy_key(CkHandle kh) {\
    if (finalized_ || !fn_) return false;
    CK_RV rv = ck_destroy_object(static_cast<CK_OBJECT_HANDLE>(kh));
    return rv == CKR_OK;
}


void Pkcs11Hsm::shutdown() {
    if (finalized_) return;
    finalized_ = true;
    if (fn_ && session_) {
        ck_logout(session_);
        ck_close_session(session_);
        session_ = 0;
    }
    if (fn_) {
        ck_finalize(nullptr);
        fn_ = nullptr;
    }
}

CkHandle Pkcs11Hsm::import_ec_key_der(std::span<const uint8_t> der_priv) {
    if (finalized_) return 0;
    const uint8_t* p = der_priv.data();
    EVP_PKEY* pkey = d2i_PrivateKey(EVP_PKEY_EC, nullptr, &p,
                                    static_cast<long>(der_priv.size()));
    if (!pkey) return 0;
    const EC_KEY* ec = EVP_PKEY_get0_EC_KEY(pkey);
    const BIGNUM* priv_bn = EC_KEY_get0_private_key(ec);
    std::vector<uint8_t> priv_bytes(48, 0);
    BN_bn2binpad(priv_bn, priv_bytes.data(), 48);
    EVP_PKEY_free(pkey);
    static const uint8_t kP384Oid[] = {
        0x06, 0x05, 0x2b, 0x81, 0x04, 0x00, 0x22
    };
    CK_OBJECT_CLASS  cls   = CKO_PRIVATE_KEY;
    CK_KEY_TYPE      ktype = CKK_EC;
    CK_BBOOL         ck_true  = CK_TRUE;
    CK_BBOOL         ck_false = CK_FALSE;
    CK_ATTRIBUTE templ[] = {
        {CKA_CLASS,       &cls,              sizeof(cls)},
        {CKA_KEY_TYPE,    &ktype,            sizeof(ktype)},
        {CKA_TOKEN,       &ck_false,         sizeof(ck_false)},
        {CKA_SENSITIVE,   &ck_true,          sizeof(ck_true)},
        {CKA_EXTRACTABLE, &ck_false,         sizeof(ck_false)},
        {CKA_SIGN,        &ck_true,          sizeof(ck_true)},
        {CKA_DERIVE,      &ck_true,          sizeof(ck_true)},
        {CKA_EC_PARAMS,   const_cast<uint8_t*>(kP384Oid), sizeof(kP384Oid)},
        {CKA_VALUE,       priv_bytes.data(), 48},
    };
    CK_OBJECT_HANDLE obj = CK_INVALID_HANDLE;
    CK_RV rv = ck_create_object(templ, 9, &obj);
    OPENSSL_cleanse(priv_bytes.data(), priv_bytes.size());
    if (rv != CKR_OK) return 0;
    return static_cast<CkHandle>(obj);
}

std::optional<std::vector<uint8_t>> Pkcs11Hsm::ecies_decrypt(
    CkHandle ik_handle, std::span<const uint8_t> payload)
{
    if (finalized_) return std::nullopt;
    constexpr size_t kPubLen = 97;
    constexpr size_t kIvLen  = 12;
    constexpr size_t kTagLen = 16;
    if (payload.size() < kPubLen + kIvLen + kTagLen) return std::nullopt;
    CK_ECDH1_DERIVE_PARAMS params{};
    params.kdf             = CKD_NULL;
    params.ulSharedDataLen = 0;
    params.pSharedData     = nullptr;
    params.ulPublicDataLen = static_cast<CK_ULONG>(kPubLen);
    params.pPublicData     = const_cast<uint8_t*>(payload.data());
    CK_MECHANISM mech{CKM_ECDH1_DERIVE, &params, sizeof(params)};
    CK_OBJECT_CLASS  cls    = CKO_SECRET_KEY;
    CK_KEY_TYPE      ktype  = CKK_GENERIC_SECRET;
    CK_ULONG         klen   = 48;
    CK_BBOOL         ck_true  = CK_TRUE;
    CK_BBOOL         ck_false = CK_FALSE;
    CK_ATTRIBUTE templ[] = {
        {CKA_CLASS,       &cls,      sizeof(cls)},
        {CKA_KEY_TYPE,    &ktype,    sizeof(ktype)},
        {CKA_VALUE_LEN,   &klen,     sizeof(klen)},
        {CKA_TOKEN,       &ck_false, sizeof(ck_false)},
        {CKA_SENSITIVE,   &ck_false, sizeof(ck_false)},
        {CKA_EXTRACTABLE, &ck_true,  sizeof(ck_true)},
    };
    CK_OBJECT_HANDLE derived_h = CK_INVALID_HANDLE;
    CK_RV rv = reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_MECHANISM*,CK_OBJECT_HANDLE,CK_ATTRIBUTE*,CK_ULONG,CK_OBJECT_HANDLE*)>(fn_->C_DeriveKey)(session_, &mech,
                                 static_cast<CK_OBJECT_HANDLE>(ik_handle),
                                 templ, 6, &derived_h);
    if (rv != CKR_OK) return std::nullopt;
    std::vector<uint8_t> shared(48);
    CK_ATTRIBUTE val_attr{CKA_VALUE, shared.data(), 48};
    rv = ck_get_attribute(derived_h, &val_attr, 1);
    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_OBJECT_HANDLE)>(fn_->C_DestroyObject)(session_, derived_h);
    if (rv != CKR_OK) return std::nullopt;
    std::vector<uint8_t> aes_key(32);
    {
        EVP_PKEY_CTX* hctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
        EVP_PKEY_derive_init(hctx);
        EVP_PKEY_CTX_set_hkdf_md(hctx, EVP_sha384());
        EVP_PKEY_CTX_set1_hkdf_key(hctx, shared.data(),
                                   static_cast<int>(shared.size()));
        EVP_PKEY_CTX_set1_hkdf_salt(hctx, nullptr, 0);
        static const uint8_t kInfo[] = "cirradio-keyfill";
        EVP_PKEY_CTX_add1_hkdf_info(hctx, kInfo, sizeof(kInfo) - 1);
        size_t kl = 32;
        EVP_PKEY_derive(hctx, aes_key.data(), &kl);
        EVP_PKEY_CTX_free(hctx);
    }
    OPENSSL_cleanse(shared.data(), shared.size());
    auto iv   = payload.subspan(kPubLen, kIvLen);
    auto body = payload.subspan(kPubLen + kIvLen);
    if (body.size() < kTagLen) return std::nullopt;
    auto ct  = body.subspan(0, body.size() - kTagLen);
    auto tag = body.subspan(body.size() - kTagLen);
    std::vector<uint8_t> plaintext(ct.size());
    EVP_CIPHER_CTX* cctx = EVP_CIPHER_CTX_new();
    EVP_DecryptInit_ex(cctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(cctx, EVP_CTRL_GCM_SET_IVLEN, static_cast<int>(kIvLen), nullptr);
    EVP_DecryptInit_ex(cctx, nullptr, nullptr, aes_key.data(), iv.data());
    int out_len = 0;
    EVP_DecryptUpdate(cctx, plaintext.data(), &out_len,
                      ct.data(), static_cast<int>(ct.size()));
    EVP_CIPHER_CTX_ctrl(cctx, EVP_CTRL_GCM_SET_TAG, static_cast<int>(kTagLen),
                        const_cast<uint8_t*>(tag.data()));
    int ok = EVP_DecryptFinal_ex(cctx, plaintext.data() + out_len, &out_len);
    EVP_CIPHER_CTX_free(cctx);
    OPENSSL_cleanse(aes_key.data(), aes_key.size());
    if (ok != 1) return std::nullopt;
    return plaintext;
}
// ── Call helpers (reinterpret_cast boilerplate) ────────────────────────────
CK_RV Pkcs11Hsm::ck_init(void* a) {
    return reinterpret_cast<CK_RV(*)(void*)>(fn_->C_Initialize)(a);
}
CK_RV Pkcs11Hsm::ck_finalize(void* a) {
    return reinterpret_cast<CK_RV(*)(void*)>(fn_->C_Finalize)(a);
}
CK_RV Pkcs11Hsm::ck_get_slot_list(CK_BBOOL tp, CK_SLOT_ID* s, CK_ULONG* c) {
    return reinterpret_cast<CK_RV(*)(CK_BBOOL,CK_SLOT_ID*,CK_ULONG*)>(
        fn_->C_GetSlotList)(tp, s, c);
}
CK_RV Pkcs11Hsm::ck_open_session(CK_SLOT_ID slot, CK_FLAGS f, CK_SESSION_HANDLE* ph) {
    return reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_FLAGS,void*,void*,CK_SESSION_HANDLE*)>(
        fn_->C_OpenSession)(slot, f, nullptr, nullptr, ph);
}
CK_RV Pkcs11Hsm::ck_close_session(CK_SESSION_HANDLE s) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE)>(fn_->C_CloseSession)(s);
}
CK_RV Pkcs11Hsm::ck_login(CK_SESSION_HANDLE s, CK_USER_TYPE u,
                           CK_UTF8CHAR_PTR p, CK_ULONG l) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_USER_TYPE,
                                     CK_UTF8CHAR_PTR,CK_ULONG)>(
        fn_->C_Login)(s, u, p, l);
}
CK_RV Pkcs11Hsm::ck_logout(CK_SESSION_HANDLE s) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE)>(fn_->C_Logout)(s);
}
CK_RV Pkcs11Hsm::ck_generate_key(CK_MECHANISM* m, CK_ATTRIBUTE* t,
                                   CK_ULONG c, CK_OBJECT_HANDLE* k) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_MECHANISM*,
                                     CK_ATTRIBUTE*,CK_ULONG,CK_OBJECT_HANDLE*)>(
        fn_->C_GenerateKey)(session_, m, t, c, k);
}
CK_RV Pkcs11Hsm::ck_destroy_object(CK_OBJECT_HANDLE obj) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_OBJECT_HANDLE)>(
        fn_->C_DestroyObject)(session_, obj);
}
CK_RV Pkcs11Hsm::ck_encrypt_init(CK_MECHANISM* m, CK_OBJECT_HANDLE k) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_MECHANISM*,CK_OBJECT_HANDLE)>(
        fn_->C_EncryptInit)(session_, m, k);
}
CK_RV Pkcs11Hsm::ck_encrypt(CK_BYTE_PTR in, CK_ULONG il,
                              CK_BYTE_PTR out, CK_ULONG* ol) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_BYTE_PTR,CK_ULONG,
                                     CK_BYTE_PTR,CK_ULONG*)>(
        fn_->C_Encrypt)(session_, in, il, out, ol);
}
CK_RV Pkcs11Hsm::ck_decrypt_init(CK_MECHANISM* m, CK_OBJECT_HANDLE k) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_MECHANISM*,CK_OBJECT_HANDLE)>(
        fn_->C_DecryptInit)(session_, m, k);
}
CK_RV Pkcs11Hsm::ck_decrypt(CK_BYTE_PTR in, CK_ULONG il,
                              CK_BYTE_PTR out, CK_ULONG* ol) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_BYTE_PTR,CK_ULONG,
                                     CK_BYTE_PTR,CK_ULONG*)>(
        fn_->C_Decrypt)(session_, in, il, out, ol);
}
CK_RV Pkcs11Hsm::ck_wrap_key(CK_MECHANISM* m, CK_OBJECT_HANDLE wrap,
                               CK_OBJECT_HANDLE key,
                               CK_BYTE_PTR out, CK_ULONG* ol) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_MECHANISM*,
                                     CK_OBJECT_HANDLE,CK_OBJECT_HANDLE,
                                     CK_BYTE_PTR,CK_ULONG*)>(
        fn_->C_WrapKey)(session_, m, wrap, key, out, ol);
}
CK_RV Pkcs11Hsm::ck_unwrap_key(CK_MECHANISM* m, CK_OBJECT_HANDLE wrap,
                                 CK_BYTE_PTR in, CK_ULONG il,
                                 CK_ATTRIBUTE* t, CK_ULONG c,
                                 CK_OBJECT_HANDLE* k) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_MECHANISM*,
                                     CK_OBJECT_HANDLE,CK_BYTE_PTR,CK_ULONG,
                                     CK_ATTRIBUTE*,CK_ULONG,CK_OBJECT_HANDLE*)>(
        fn_->C_UnwrapKey)(session_, m, wrap, in, il, t, c, k);
}
CK_RV Pkcs11Hsm::ck_get_attribute(CK_OBJECT_HANDLE obj,
                                    CK_ATTRIBUTE* t, CK_ULONG c) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_OBJECT_HANDLE,
                                     CK_ATTRIBUTE*,CK_ULONG)>(
        fn_->C_GetAttributeValue)(session_, obj, t, c);
}
CK_RV Pkcs11Hsm::ck_create_object(CK_ATTRIBUTE* t, CK_ULONG c,
                                    CK_OBJECT_HANDLE* obj) {
    return reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_ATTRIBUTE*,
                                     CK_ULONG,CK_OBJECT_HANDLE*)>(
        fn_->C_CreateObject)(session_, t, c, obj);
}

}  // namespace cirradio::security
