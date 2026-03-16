# Security

## Cryptographic Posture

CIRRADIO final version will use following algorithms throughout:

| Purpose              | Algorithm                  | Key size |
|----------------------|----------------------------|----------|
| Traffic encryption   | AES-256-GCM                | 256-bit  |
| FHSS hop sequencing  | AES-256-ECB                | 256-bit  |
| Node authentication  | ECDSA P-384                | 384-bit  |
| Key derivation       | HKDF-SHA-384               | —        |

## Key Storage

The current build uses **SoftHSM2** (a software-only PKCS#11 token) as the
HSM backend. Keys managed by SoftHSM2 are stored on disk in a temporary
directory and are **not hardware-protected**. This is the development/CI
configuration.

The hardware integration point is fully defined:

- **`IHsmEngine`** — abstract interface for all key operations (generate,
  sign, verify, encrypt, decrypt)
- **`Pkcs11Hsm`** — dlopen-based PKCS#11 2.40 loader; any compliant HSM
  library (Thales Luna, Utimaco, YubiHSM2, AWS CloudHSM, etc.) drops in
  by setting `SOFTHSM2_LIB_PATH` at CMake configure time to point to the
  HSM's PKCS#11 shared library
- **`SoftHsm`** — subclass of `Pkcs11Hsm` for SoftHSM2; used in CI and
  all 97 software tests

## Certification Status

CIRRADIO is a **research and development platform**. It is not certified
to any standard:

- Not NSA Type 1 certified
- Not FIPS 140-3 validated
- Not evaluated under Common Criteria
- Not approved for operational use with classified material

## What Is Not Included

- Operational frequency plans or hop keys
- Classified waveform parameters
- Production HSM provisioning procedures
- COMSEC material of any kind

Do not commit classified material, operational key material, or sensitive
frequency plans to this repository.

## Responsible Disclosure

To report a security vulnerability, contact: **[add email before public release]**

Please allow reasonable time for a fix before public disclosure.
