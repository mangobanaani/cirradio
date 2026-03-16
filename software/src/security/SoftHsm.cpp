// software/src/security/SoftHsm.cpp
#include "security/SoftHsm.h"
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <cstring>
#include <cstdlib>
#include <unistd.h>
#include <mutex>
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/kdf.h>
#include <openssl/params.h>
#include <openssl/crypto.h>

namespace cirradio::security {

// ── Per-process singleton: initialize SoftHSM2 once ─────────────────────────
namespace {
struct SharedLib {
    void*              lib     = nullptr;
    CK_FUNCTION_LIST*  fn      = nullptr;
    CK_SLOT_ID         slot_id = 0;
    std::string        tmp_dir;

    static SharedLib& instance() {
        static SharedLib inst;
        return inst;
    }
};
} // namespace

static SharedLib& init_shared_lib() {
    SharedLib& sl = SharedLib::instance();
    if (sl.fn) return sl;  // already initialized

    static constexpr const char* kLibPath = SOFTHSM2_LIB_PATH;
    static constexpr const char* kPin = "1234";

    // 1. Create temp directory
    char tmp_template[] = "/tmp/softhsm2-XXXXXX";
    const char* tmp = mkdtemp(tmp_template);
    if (!tmp) throw std::runtime_error("mkdtemp failed");
    sl.tmp_dir = tmp;

    // 2. Create token storage subdirectory
    std::filesystem::create_directory(sl.tmp_dir + "/tokens");

    // 3. Write softhsm2.conf
    std::string conf_path = sl.tmp_dir + "/softhsm2.conf";
    {
        std::ofstream f(conf_path);
        f << "directories.tokendir = " << sl.tmp_dir << "/tokens/\n"
          << "objectstore.backend = file\n"
          << "log.level = ERROR\n";
    }

    // 4. Point SoftHSM2 at our config BEFORE dlopen
    setenv("SOFTHSM2_CONF", conf_path.c_str(), 1);

    // 5. dlopen SoftHSM2
    sl.lib = dlopen(kLibPath, RTLD_NOW | RTLD_LOCAL);
    if (!sl.lib) throw std::runtime_error(
        std::string("dlopen softhsm2 failed: ") + dlerror());

    auto get_fn = reinterpret_cast<CK_C_GetFunctionList_t>(
        dlsym(sl.lib, "C_GetFunctionList"));
    if (!get_fn) throw std::runtime_error("C_GetFunctionList not found");

    CK_RV rv = get_fn(&sl.fn);
    if (rv != CKR_OK) throw std::runtime_error("C_GetFunctionList failed");

    // 6. Initialize Cryptoki
    rv = reinterpret_cast<CK_RV(*)(void*)>(sl.fn->C_Initialize)(nullptr);
    if (rv != CKR_OK && rv != CKR_CRYPTOKI_ALREADY_INITIALIZED)
        throw std::runtime_error("C_Initialize rv=" + std::to_string(rv));

    // 7. Find first uninitialized slot
    CK_SLOT_ID slots[16]; CK_ULONG slot_count = 16;
    rv = reinterpret_cast<CK_RV(*)(CK_BBOOL,CK_SLOT_ID*,CK_ULONG*)>(
        sl.fn->C_GetSlotList)(CK_FALSE, slots, &slot_count);
    if (rv != CKR_OK || slot_count == 0)
        throw std::runtime_error("No slots found");

    // 8. Initialize token
    rv = reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_UTF8CHAR_PTR,CK_ULONG,CK_UTF8CHAR_PTR)>(
        sl.fn->C_InitToken)(slots[0],
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>("CIRRADIO")));
    if (rv != CKR_OK) throw std::runtime_error("C_InitToken rv=" + std::to_string(rv));

    // Find the initialized slot
    slot_count = 16;
    rv = reinterpret_cast<CK_RV(*)(CK_BBOOL,CK_SLOT_ID*,CK_ULONG*)>(
        sl.fn->C_GetSlotList)(CK_TRUE, slots, &slot_count);
    if (rv != CKR_OK || slot_count == 0)
        throw std::runtime_error("No initialized slots");
    sl.slot_id = slots[0];

    // 9. SO session: set user PIN
    CK_SESSION_HANDLE so_sess;
    rv = reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_FLAGS,void*,void*,CK_SESSION_HANDLE*)>(
        sl.fn->C_OpenSession)(sl.slot_id, CKF_SERIAL_SESSION | CKF_RW_SESSION,
                              nullptr, nullptr, &so_sess);
    if (rv != CKR_OK) throw std::runtime_error("C_OpenSession SO rv=" + std::to_string(rv));

    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_USER_TYPE,CK_UTF8CHAR_PTR,CK_ULONG)>(
        sl.fn->C_Login)(so_sess, CKU_SO,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4);

    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_UTF8CHAR_PTR,CK_ULONG)>(
        sl.fn->C_InitPIN)(so_sess,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4);

    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE)>(sl.fn->C_Logout)(so_sess);
    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE)>(sl.fn->C_CloseSession)(so_sess);

    return sl;
}

// Open a fresh user session on the shared token
static CK_SESSION_HANDLE open_user_session(SharedLib& sl) {
    static constexpr const char* kPin = "1234";
    CK_SESSION_HANDLE session;
    CK_RV rv = reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_FLAGS,void*,void*,CK_SESSION_HANDLE*)>(
        sl.fn->C_OpenSession)(sl.slot_id, CKF_SERIAL_SESSION | CKF_RW_SESSION,
                              nullptr, nullptr, &session);
    if (rv != CKR_OK) throw std::runtime_error("C_OpenSession user rv=" + std::to_string(rv));

    rv = reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_USER_TYPE,CK_UTF8CHAR_PTR,CK_ULONG)>(
        sl.fn->C_Login)(session, CKU_USER,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4);
    if (rv != CKR_OK && rv != CKR_USER_ALREADY_LOGGED_IN)
        throw std::runtime_error("C_Login user rv=" + std::to_string(rv));

    return session;
}

static SoftHsm::CtorArgs make_ctor_args() {
    SharedLib& sl = init_shared_lib();
    CK_SESSION_HANDLE session = open_user_session(sl);
    return {sl.lib, sl.fn, session, sl.slot_id};
}

SoftHsm::SoftHsm()
    : SoftHsm(make_ctor_args())
{}

SoftHsm::SoftHsm(CtorArgs&& a)
    : Pkcs11Hsm(a.lib, a.fn, a.session, a.slot)
{}

void SoftHsm::shutdown() {
    if (soft_finalized_) return;
    soft_finalized_ = true;
    ec_keys_.clear();
    // Close PKCS#11 session (idempotent)
    if (fn_ && session_) {
        ck_logout(session_);
        ck_close_session(session_);
        session_ = 0;
    }
}

SoftHsm::~SoftHsm() {
    shutdown();
    // Prevent base class destructor from acting on already-closed session.
    fn_  = nullptr;
    lib_ = nullptr;
}

// ── generate_key: non-sensitive session key for test use ─────────────────────
HsmKeyHandle SoftHsm::generate_key(KeyType /*type*/, const KeyLabel& /*label*/) {
    CK_MECHANISM mech{CKM_AES_KEY_GEN, nullptr, 0};
    CK_KEY_TYPE key_type = CKK_AES;
    CK_ULONG key_len     = 32;
    CK_BBOOL ck_true     = CK_TRUE;
    CK_BBOOL ck_false    = CK_FALSE;
    CK_ATTRIBUTE templ[] = {
        {CKA_KEY_TYPE,   &key_type, sizeof(key_type)},
        {CKA_VALUE_LEN,  &key_len,  sizeof(key_len)},
        {CKA_TOKEN,      &ck_false, sizeof(ck_false)},
        {CKA_SENSITIVE,  &ck_false, sizeof(ck_false)},   // extractable for tests
        {CKA_EXTRACTABLE,&ck_true,  sizeof(ck_true)},
        {CKA_ENCRYPT,    &ck_true,  sizeof(ck_true)},
        {CKA_DECRYPT,    &ck_true,  sizeof(ck_true)},
        {CKA_WRAP,       &ck_true,  sizeof(ck_true)},
        {CKA_UNWRAP,     &ck_true,  sizeof(ck_true)},
    };
    CK_OBJECT_HANDLE kh = CK_INVALID_HANDLE;
    CK_RV rv = ck_generate_key(&mech, templ, 9, &kh);
    if (rv != CKR_OK)
        throw std::runtime_error("SoftHsm::generate_key rv=" + std::to_string(rv));
    return HsmKeyHandle(*this, static_cast<CkHandle>(kh));
}

// ── unwrap_key: non-sensitive result for test use ────────────────────────────
std::optional<HsmKeyHandle> SoftHsm::unwrap_key(
    CkHandle wrapping_key, std::span<const uint8_t> wrapped)
{
    CK_MECHANISM mech{CKM_AES_KEY_WRAP, nullptr, 0};
    CK_OBJECT_CLASS obj_class = CKO_SECRET_KEY;
    CK_KEY_TYPE key_type      = CKK_AES;
    CK_ULONG key_len          = 32;
    CK_BBOOL ck_true          = CK_TRUE;
    CK_BBOOL ck_false         = CK_FALSE;
    CK_ATTRIBUTE templ[] = {
        {CKA_CLASS,      &obj_class, sizeof(obj_class)},
        {CKA_KEY_TYPE,   &key_type,  sizeof(key_type)},
        {CKA_TOKEN,      &ck_false,  sizeof(ck_false)},
        {CKA_SENSITIVE,  &ck_false,  sizeof(ck_false)},   // allow export_raw
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

// ── export_raw: C_GetAttributeValue(CKA_VALUE) ───────────────────────────────
std::optional<std::vector<uint8_t>> SoftHsm::export_raw(CkHandle kh) {
    // First call: get value length
    CK_ATTRIBUTE attr{CKA_VALUE, nullptr, 0};
    CK_RV rv = ck_get_attribute(static_cast<CK_OBJECT_HANDLE>(kh), &attr, 1);
    if (rv != CKR_OK) return std::nullopt;

    std::vector<uint8_t> key_bytes(attr.ulValueLen);
    attr.pValue = key_bytes.data();
    rv = ck_get_attribute(static_cast<CK_OBJECT_HANDLE>(kh), &attr, 1);
    if (rv != CKR_OK) return std::nullopt;
    return key_bytes;
}

// ── import_raw: C_CreateObject with CKA_VALUE ────────────────────────────────
std::optional<HsmKeyHandle> SoftHsm::import_raw(
    std::span<const uint8_t> key_bytes, const KeyLabel& /*label*/)
{
    if (key_bytes.size() != 32) return std::nullopt;

    CK_OBJECT_CLASS obj_class = CKO_SECRET_KEY;
    CK_KEY_TYPE key_type      = CKK_AES;
    CK_ULONG key_len          = static_cast<CK_ULONG>(key_bytes.size());
    CK_BBOOL ck_true          = CK_TRUE;
    CK_BBOOL ck_false         = CK_FALSE;
    void* key_data = const_cast<uint8_t*>(key_bytes.data());

    CK_ATTRIBUTE templ[] = {
        {CKA_CLASS,      &obj_class, sizeof(obj_class)},
        {CKA_KEY_TYPE,   &key_type,  sizeof(key_type)},
        {CKA_VALUE,      key_data,   key_len},
        {CKA_TOKEN,      &ck_false,  sizeof(ck_false)},
        {CKA_SENSITIVE,  &ck_false,  sizeof(ck_false)},
        {CKA_EXTRACTABLE,&ck_true,   sizeof(ck_true)},
        {CKA_ENCRYPT,    &ck_true,   sizeof(ck_true)},
        {CKA_DECRYPT,    &ck_true,   sizeof(ck_true)},
        {CKA_WRAP,       &ck_true,   sizeof(ck_true)},
        {CKA_UNWRAP,     &ck_true,   sizeof(ck_true)},
    };
    CK_OBJECT_HANDLE obj = CK_INVALID_HANDLE;
    CK_RV rv = ck_create_object(templ, 10, &obj);
    if (rv != CKR_OK) return std::nullopt;
    return HsmKeyHandle(*this, static_cast<CkHandle>(obj));
}

// ── import_ec_key_der: store DER private key in memory ───────────────────────
CkHandle SoftHsm::import_ec_key_der(std::span<const uint8_t> der_priv) {
    std::vector<uint8_t> key_bytes(der_priv.begin(), der_priv.end());
    CkHandle h = next_ec_handle_++;
    ec_keys_[h] = std::move(key_bytes);
    return h;
}

// ── ecies_decrypt: ECDH P-384 + HKDF-SHA-384 + AES-256-GCM ─────────────────
std::optional<std::vector<uint8_t>> SoftHsm::ecies_decrypt(
    CkHandle ik_handle, std::span<const uint8_t> payload)
{
    // Payload: ephemeral_pub(97) | IV(12) | ciphertext | GCM_tag(16)
    constexpr size_t kPubLen = 97;  // P-384 uncompressed point
    constexpr size_t kIvLen  = 12;
    constexpr size_t kTagLen = 16;
    if (payload.size() < kPubLen + kIvLen + kTagLen) return std::nullopt;

    auto it = ec_keys_.find(ik_handle);
    if (it == ec_keys_.end()) return std::nullopt;

    // 1. Load device private key from DER
    const uint8_t* p = it->second.data();
    EVP_PKEY* dev_priv = d2i_PrivateKey(EVP_PKEY_EC, nullptr, &p,
                                        static_cast<long>(it->second.size()));
    if (!dev_priv) return std::nullopt;

    // 2. Load ephemeral public key from uncompressed point bytes
    EVP_PKEY* ephem_pub = nullptr;
    {
        EC_GROUP* grp = EC_GROUP_new_by_curve_name(NID_secp384r1);
        EC_POINT* pt  = EC_POINT_new(grp);
        BN_CTX* ctx   = BN_CTX_new();
        EC_POINT_oct2point(grp, pt, payload.data(), kPubLen, ctx);
        EC_KEY* ec_key = EC_KEY_new();
        EC_KEY_set_group(ec_key, grp);
        EC_KEY_set_public_key(ec_key, pt);
        ephem_pub = EVP_PKEY_new();
        EVP_PKEY_set1_EC_KEY(ephem_pub, ec_key);
        EC_KEY_free(ec_key);
        BN_CTX_free(ctx);
        EC_POINT_free(pt);
        EC_GROUP_free(grp);
    }
    if (!ephem_pub) { EVP_PKEY_free(dev_priv); return std::nullopt; }

    // 3. ECDH: derive shared secret
    EVP_PKEY_CTX* dh_ctx = EVP_PKEY_CTX_new(dev_priv, nullptr);
    EVP_PKEY_derive_init(dh_ctx);
    EVP_PKEY_derive_set_peer(dh_ctx, ephem_pub);
    size_t secret_len = 0;
    EVP_PKEY_derive(dh_ctx, nullptr, &secret_len);
    std::vector<uint8_t> shared(secret_len);
    EVP_PKEY_derive(dh_ctx, shared.data(), &secret_len);
    shared.resize(secret_len);
    EVP_PKEY_CTX_free(dh_ctx);
    EVP_PKEY_free(ephem_pub);
    EVP_PKEY_free(dev_priv);

    // 4. HKDF-SHA-384: shared_secret → 32-byte AES key
    std::vector<uint8_t> aes_key(32);
    {
        EVP_PKEY_CTX* hkdf_ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
        EVP_PKEY_derive_init(hkdf_ctx);
        EVP_PKEY_CTX_set_hkdf_md(hkdf_ctx, EVP_sha384());
        EVP_PKEY_CTX_set1_hkdf_key(hkdf_ctx, shared.data(),
                                   static_cast<int>(shared.size()));
        EVP_PKEY_CTX_set1_hkdf_salt(hkdf_ctx, nullptr, 0);
        static const uint8_t kInfo[] = "cirradio-keyfill";
        EVP_PKEY_CTX_add1_hkdf_info(hkdf_ctx, kInfo, sizeof(kInfo) - 1);
        size_t key_len = 32;
        EVP_PKEY_derive(hkdf_ctx, aes_key.data(), &key_len);
        EVP_PKEY_CTX_free(hkdf_ctx);
    }
    OPENSSL_cleanse(shared.data(), shared.size());

    // 5. AES-256-GCM decrypt
    auto iv   = payload.subspan(kPubLen, kIvLen);
    auto body = payload.subspan(kPubLen + kIvLen);  // ciphertext + tag
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
    int final_ok = EVP_DecryptFinal_ex(cctx, plaintext.data() + out_len, &out_len);
    EVP_CIPHER_CTX_free(cctx);
    OPENSSL_cleanse(aes_key.data(), aes_key.size());

    if (final_ok != 1) return std::nullopt;
    return plaintext;
}

}  // namespace cirradio::security
