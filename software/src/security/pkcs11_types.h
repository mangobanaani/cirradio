// software/src/security/pkcs11_types.h
// Minimal PKCS#11 2.40 type definitions for dlopen usage.
// No external dependencies — matches the standard ABI exactly.
#pragma once
#include <cstdint>

extern "C" {

typedef unsigned long   CK_ULONG;
typedef unsigned char   CK_BYTE;
typedef CK_BYTE         CK_UTF8CHAR;
typedef CK_UTF8CHAR*    CK_UTF8CHAR_PTR;
typedef CK_BYTE*        CK_BYTE_PTR;
typedef CK_ULONG        CK_FLAGS;
typedef CK_ULONG        CK_SLOT_ID;
typedef CK_ULONG        CK_SESSION_HANDLE;
typedef CK_ULONG        CK_OBJECT_HANDLE;
typedef CK_ULONG        CK_MECHANISM_TYPE;
typedef CK_ULONG        CK_OBJECT_CLASS;
typedef CK_ULONG        CK_KEY_TYPE;
typedef CK_ULONG        CK_RV;
typedef CK_ULONG        CK_BBOOL;
typedef CK_ULONG        CK_USER_TYPE;

struct CK_VERSION { CK_BYTE major; CK_BYTE minor; };

struct CK_MECHANISM {
    CK_MECHANISM_TYPE mechanism;
    void*             pParameter;
    CK_ULONG          ulParameterLen;
};

// PKCS#11 2.40 GCM params (includes ulIvBits)
struct CK_GCM_PARAMS {
    CK_BYTE_PTR pIv;
    CK_ULONG    ulIvLen;
    CK_ULONG    ulIvBits;
    CK_BYTE_PTR pAAD;
    CK_ULONG    ulAADLen;
    CK_ULONG    ulTagBits;
};

struct CK_ATTRIBUTE {
    CK_ULONG type;
    void*    pValue;
    CK_ULONG ulValueLen;
};

// CK_FUNCTION_LIST: 68 function pointers in PKCS#11 2.40 standard order.
// We store unused slots as void* to preserve exact struct layout.
struct CK_FUNCTION_LIST {
    CK_VERSION version;
    void* C_Initialize;
    void* C_Finalize;
    void* C_GetInfo;
    void* C_GetFunctionList;
    void* C_GetSlotList;
    void* C_GetSlotInfo;
    void* C_GetTokenInfo;
    void* C_GetMechanismList;
    void* C_GetMechanismInfo;
    void* C_InitToken;
    void* C_InitPIN;
    void* C_SetPIN;
    void* C_OpenSession;
    void* C_CloseSession;
    void* C_CloseAllSessions;
    void* C_GetSessionInfo;
    void* C_GetOperationState;
    void* C_SetOperationState;
    void* C_Login;
    void* C_Logout;
    void* C_CreateObject;
    void* C_CopyObject;
    void* C_DestroyObject;
    void* C_GetObjectSize;
    void* C_GetAttributeValue;
    void* C_SetAttributeValue;
    void* C_FindObjectsInit;
    void* C_FindObjects;
    void* C_FindObjectsFinal;
    void* C_EncryptInit;
    void* C_Encrypt;
    void* C_EncryptUpdate;
    void* C_EncryptFinal;
    void* C_DecryptInit;
    void* C_Decrypt;
    void* C_DecryptUpdate;
    void* C_DecryptFinal;
    void* C_DigestInit;
    void* C_Digest;
    void* C_DigestUpdate;
    void* C_DigestKey;
    void* C_DigestFinal;
    void* C_SignInit;
    void* C_Sign;
    void* C_SignUpdate;
    void* C_SignFinal;
    void* C_SignRecoverInit;
    void* C_SignRecover;
    void* C_VerifyInit;
    void* C_Verify;
    void* C_VerifyUpdate;
    void* C_VerifyFinal;
    void* C_VerifyRecoverInit;
    void* C_VerifyRecover;
    void* C_DigestEncryptUpdate;
    void* C_DecryptDigestUpdate;
    void* C_SignEncryptUpdate;
    void* C_DecryptVerifyUpdate;
    void* C_GenerateKey;
    void* C_GenerateKeyPair;
    void* C_WrapKey;
    void* C_UnwrapKey;
    void* C_DeriveKey;
    void* C_SeedRandom;
    void* C_GenerateRandom;
    void* C_GetFunctionStatus;
    void* C_CancelFunction;
    void* C_WaitForSlotEvent;
};

typedef CK_RV (*CK_C_GetFunctionList_t)(CK_FUNCTION_LIST**);

// Return codes
static constexpr CK_RV CKR_OK                            = 0x00000000UL;
static constexpr CK_RV CKR_CRYPTOKI_ALREADY_INITIALIZED  = 0x00000191UL;
static constexpr CK_RV CKR_USER_ALREADY_LOGGED_IN        = 0x00000100UL;

// Session flags
static constexpr CK_FLAGS CKF_SERIAL_SESSION = 0x00000004UL;
static constexpr CK_FLAGS CKF_RW_SESSION     = 0x00000002UL;
static constexpr CK_FLAGS CKF_TOKEN_PRESENT  = 0x00000001UL;

// User types
static constexpr CK_USER_TYPE CKU_SO   = 0x00000000UL;
static constexpr CK_USER_TYPE CKU_USER = 0x00000001UL;

// Mechanisms
static constexpr CK_MECHANISM_TYPE CKM_AES_KEY_GEN  = 0x00001080UL;
static constexpr CK_MECHANISM_TYPE CKM_AES_GCM      = 0x00001087UL;
static constexpr CK_MECHANISM_TYPE CKM_AES_KEY_WRAP = 0x00002109UL;

// Object classes
static constexpr CK_OBJECT_CLASS CKO_SECRET_KEY = 0x00000003UL;

// Key types
static constexpr CK_KEY_TYPE CKK_AES = 0x0000001FUL;

// Attribute types
static constexpr CK_ULONG CKA_CLASS       = 0x00000000UL;
static constexpr CK_ULONG CKA_TOKEN       = 0x00000001UL;
static constexpr CK_ULONG CKA_KEY_TYPE    = 0x00000100UL;
static constexpr CK_ULONG CKA_SENSITIVE   = 0x00000103UL;
static constexpr CK_ULONG CKA_ENCRYPT     = 0x00000104UL;
static constexpr CK_ULONG CKA_DECRYPT     = 0x00000105UL;
static constexpr CK_ULONG CKA_WRAP        = 0x00000106UL;
static constexpr CK_ULONG CKA_UNWRAP      = 0x00000107UL;
static constexpr CK_ULONG CKA_EXTRACTABLE = 0x00000162UL;
static constexpr CK_ULONG CKA_VALUE       = 0x00000011UL;
static constexpr CK_ULONG CKA_VALUE_LEN   = 0x00000161UL;

static constexpr CK_BBOOL CK_TRUE  = 1;
static constexpr CK_BBOOL CK_FALSE = 0;
static constexpr CK_OBJECT_HANDLE CK_INVALID_HANDLE = 0;

}  // extern "C"
