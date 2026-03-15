// software/src/security/SoftHsm.cpp
#include "security/SoftHsm.h"
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <cstring>
#include <cstdlib>
#include <unistd.h>

namespace cirradio::security {

// ── Static setup: prepare temp dir + SoftHSM2 token ─────────────────────────
SoftHsm::Init SoftHsm::setup() {
    // 1. Create temp directory
    char tmp_template[] = "/tmp/softhsm2-XXXXXX";
    const char* tmp = mkdtemp(tmp_template);
    if (!tmp) throw std::runtime_error("mkdtemp failed");
    std::string tmp_dir(tmp);

    // 2. Create token storage subdirectory
    std::filesystem::create_directory(tmp_dir + "/tokens");

    // 3. Write softhsm2.conf
    std::string conf_path = tmp_dir + "/softhsm2.conf";
    {
        std::ofstream f(conf_path);
        f << "directories.tokendir = " << tmp_dir << "/tokens/\n"
          << "objectstore.backend = file\n"
          << "log.level = ERROR\n";
    }

    // 4. Point SoftHSM2 at our config
    setenv("SOFTHSM2_CONF", conf_path.c_str(), 1);

    // 5. dlopen SoftHSM2
    void* lib = dlopen(kLibPath, RTLD_NOW | RTLD_LOCAL);
    if (!lib) throw std::runtime_error(
        std::string("dlopen softhsm2 failed: ") + dlerror());

    auto get_fn = reinterpret_cast<CK_C_GetFunctionList_t>(
        dlsym(lib, "C_GetFunctionList"));
    if (!get_fn) throw std::runtime_error("C_GetFunctionList not found");

    CK_FUNCTION_LIST* fn = nullptr;
    CK_RV rv = get_fn(&fn);
    if (rv != CKR_OK) throw std::runtime_error("C_GetFunctionList failed");

    // 6. Initialize Cryptoki
    rv = reinterpret_cast<CK_RV(*)(void*)>(fn->C_Initialize)(nullptr);
    if (rv != CKR_OK && rv != CKR_CRYPTOKI_ALREADY_INITIALIZED)
        throw std::runtime_error("C_Initialize rv=" + std::to_string(rv));

    // 7. Find first (uninitialized) slot
    CK_SLOT_ID slots[16]; CK_ULONG slot_count = 16;
    rv = reinterpret_cast<CK_RV(*)(CK_BBOOL,CK_SLOT_ID*,CK_ULONG*)>(
        fn->C_GetSlotList)(CK_FALSE, slots, &slot_count);
    if (rv != CKR_OK || slot_count == 0)
        throw std::runtime_error("No slots found");

    // 8. Initialize token on slot 0
    rv = reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_UTF8CHAR_PTR,CK_ULONG,CK_UTF8CHAR_PTR)>(
        fn->C_InitToken)(slots[0],
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>("CIRRADIO")));
    if (rv != CKR_OK) throw std::runtime_error("C_InitToken rv=" + std::to_string(rv));

    // After C_InitToken, SoftHSM2 reassigns token to a new slot index.
    slot_count = 16;
    rv = reinterpret_cast<CK_RV(*)(CK_BBOOL,CK_SLOT_ID*,CK_ULONG*)>(
        fn->C_GetSlotList)(CK_TRUE, slots, &slot_count);
    if (rv != CKR_OK || slot_count == 0)
        throw std::runtime_error("No initialized slots");
    CK_SLOT_ID token_slot = slots[0];

    // 9. SO session: set user PIN
    CK_SESSION_HANDLE so_sess;
    rv = reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_FLAGS,void*,void*,CK_SESSION_HANDLE*)>(
        fn->C_OpenSession)(token_slot, CKF_SERIAL_SESSION | CKF_RW_SESSION,
                           nullptr, nullptr, &so_sess);
    if (rv != CKR_OK) throw std::runtime_error("C_OpenSession SO rv=" + std::to_string(rv));

    rv = reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_USER_TYPE,CK_UTF8CHAR_PTR,CK_ULONG)>(
        fn->C_Login)(so_sess, CKU_SO,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4);
    if (rv != CKR_OK) throw std::runtime_error("C_Login SO rv=" + std::to_string(rv));

    rv = reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_UTF8CHAR_PTR,CK_ULONG)>(
        fn->C_InitPIN)(so_sess,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4);
    if (rv != CKR_OK) throw std::runtime_error("C_InitPIN rv=" + std::to_string(rv));

    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE)>(fn->C_Logout)(so_sess);
    reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE)>(fn->C_CloseSession)(so_sess);

    // 10. Open normal user session
    CK_SESSION_HANDLE session;
    rv = reinterpret_cast<CK_RV(*)(CK_SLOT_ID,CK_FLAGS,void*,void*,CK_SESSION_HANDLE*)>(
        fn->C_OpenSession)(token_slot, CKF_SERIAL_SESSION | CKF_RW_SESSION,
                           nullptr, nullptr, &session);
    if (rv != CKR_OK) throw std::runtime_error("C_OpenSession user rv=" + std::to_string(rv));

    rv = reinterpret_cast<CK_RV(*)(CK_SESSION_HANDLE,CK_USER_TYPE,CK_UTF8CHAR_PTR,CK_ULONG)>(
        fn->C_Login)(session, CKU_USER,
            reinterpret_cast<CK_UTF8CHAR_PTR>(const_cast<char*>(kPin)), 4);
    if (rv != CKR_OK) throw std::runtime_error("C_Login user rv=" + std::to_string(rv));

    return Init{lib, fn, session, token_slot, tmp_dir};
}

SoftHsm::SoftHsm(Init&& i)
    : Pkcs11Hsm(i.lib, i.fn, i.session, i.slot)
    , tmp_dir_(std::move(i.tmp_dir))
{}

SoftHsm::SoftHsm() : SoftHsm(setup()) {}

SoftHsm::~SoftHsm() {
    // Base class destructor handles C_Logout/C_CloseSession/C_Finalize/dlclose.
    // We only clean up the temp directory here.
    if (!tmp_dir_.empty()) {
        std::filesystem::remove_all(tmp_dir_);
    }
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

}  // namespace cirradio::security
