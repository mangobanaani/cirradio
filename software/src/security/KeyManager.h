// software/src/security/KeyManager.h
#pragma once
#include "security/IHsmEngine.h"
#include <vector>
#include <cstdint>
#include <optional>
#include <stdexcept>

namespace cirradio::security {

struct OtarMessage {
    uint32_t             key_epoch;
    std::vector<uint8_t> wrapped_tek;
    std::vector<uint8_t> wrapped_fhek;
};

class KeyManager {
public:
    explicit KeyManager(IHsmEngine& hsm);

    void initialize_kek();
    void set_kek_raw(const std::vector<uint8_t>& kek);
    void generate_tek();
    void generate_fhek();
    void rotate_tek();
    void set_tek_raw(const std::vector<uint8_t>& tek);
    void set_fhek_raw(const std::vector<uint8_t>& fhek);

    std::optional<std::vector<uint8_t>> encrypt_with_tek(
        std::span<const uint8_t> plaintext);
    std::optional<std::vector<uint8_t>> decrypt_with_tek(
        std::span<const uint8_t> ciphertext);

    std::vector<uint8_t> export_fhek_for_fpga();
    std::vector<uint8_t> export_tek_for_distribution();

    OtarMessage generate_otar_message();
    bool process_otar_message(const OtarMessage& msg);
    void zeroize();

    bool is_initialized() const;
    uint32_t key_epoch() const;

private:
    IHsmEngine& hsm_;
    std::optional<HsmKeyHandle> kek_, tek_, fhek_;
    uint32_t key_epoch_ = 0;

    HsmKeyHandle import_raw_or_throw(const std::vector<uint8_t>& key,
                                     const std::string& label);
};

}  // namespace cirradio::security
