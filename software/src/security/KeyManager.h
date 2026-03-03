#pragma once
#include "CryptoEngine.h"
#include <vector>
#include <cstdint>
#include <optional>
#include <stdexcept>

namespace cirradio::security {

struct OtarMessage {
    uint32_t key_epoch;                 // monotonic counter identifying key generation
    std::vector<uint8_t> wrapped_tek;   // TEK encrypted under KEK
    std::vector<uint8_t> wrapped_fhek;  // FHEK encrypted under KEK
};

class KeyManager {
public:
    KeyManager();

    // Initialize the KEK (Key Encryption Key). Generates a random 32-byte key.
    void initialize_kek();

    // Set KEK from external source (e.g., key fill device)
    void set_kek(const std::vector<uint8_t>& kek);

    // Generate a new random TEK (Traffic Encryption Key)
    std::vector<uint8_t> generate_tek();

    // Generate a new random FHEK (Frequency Hop Encryption Key)
    std::vector<uint8_t> generate_fhek();

    // Rotate TEK: generates new TEK, increments epoch, returns new key
    std::vector<uint8_t> rotate_tek();

    // Get current keys (throws if not initialized)
    std::vector<uint8_t> current_tek() const;
    std::vector<uint8_t> current_fhek() const;

    // Set keys directly (e.g., received via net join)
    void set_tek(const std::vector<uint8_t>& tek);
    void set_fhek(const std::vector<uint8_t>& fhek);

    // Get current key epoch
    uint32_t key_epoch() const;

    // Generate OTAR message for distribution to other nodes
    // The TEK and FHEK are wrapped under the KEK
    OtarMessage generate_otar_message();

    // Process received OTAR message: unwrap and install new keys
    bool process_otar_message(const OtarMessage& msg);

    // Emergency zeroization: wipe all keys from memory
    void zeroize();

    // Check if keys are available
    bool is_initialized() const;

private:
    CryptoEngine engine_;
    std::vector<uint8_t> kek_;    // 32 bytes
    std::vector<uint8_t> tek_;    // 32 bytes
    std::vector<uint8_t> fhek_;   // 32 bytes
    uint32_t key_epoch_ = 0;
    bool initialized_ = false;

    // Securely zero a vector's memory
    static void secure_zero(std::vector<uint8_t>& v);

    // Generate a random 32-byte key
    static std::vector<uint8_t> generate_random_key();
};

}  // namespace cirradio::security
