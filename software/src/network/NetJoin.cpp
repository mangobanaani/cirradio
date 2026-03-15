#include "network/NetJoin.h"
#include "security/EcSign.h"
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <algorithm>

namespace cirradio::network {

static constexpr size_t kNonceSize = 32;
static constexpr size_t kIvSize  = 12;
static constexpr size_t kTagSize = 16;

// AES-256-GCM encrypt using a 32-byte raw key (for wrapping TEK/FHEK in JoinAccept)
static std::optional<std::vector<uint8_t>> aes_gcm_encrypt(
    const std::vector<uint8_t>& key, const std::vector<uint8_t>& plaintext)
{
    if (key.size() != 32) return std::nullopt;
    std::vector<uint8_t> iv(kIvSize);
    if (RAND_bytes(iv.data(), static_cast<int>(kIvSize)) != 1) return std::nullopt;

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return std::nullopt;

    bool ok = true;
    ok = ok && EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1;
    ok = ok && EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, static_cast<int>(kIvSize), nullptr) == 1;
    ok = ok && EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), iv.data()) == 1;

    std::vector<uint8_t> ciphertext(plaintext.size());
    int out_len = 0;
    if (ok && !plaintext.empty())
        ok = EVP_EncryptUpdate(ctx, ciphertext.data(), &out_len,
                               plaintext.data(), static_cast<int>(plaintext.size())) == 1;

    int final_len = 0;
    if (ok) ok = EVP_EncryptFinal_ex(ctx, ciphertext.data() + out_len, &final_len) == 1;
    ciphertext.resize(static_cast<size_t>(out_len + final_len));

    std::vector<uint8_t> tag(kTagSize);
    if (ok) ok = EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, static_cast<int>(kTagSize), tag.data()) == 1;
    EVP_CIPHER_CTX_free(ctx);

    if (!ok) return std::nullopt;

    std::vector<uint8_t> result;
    result.reserve(kIvSize + ciphertext.size() + kTagSize);
    result.insert(result.end(), iv.begin(), iv.end());
    result.insert(result.end(), ciphertext.begin(), ciphertext.end());
    result.insert(result.end(), tag.begin(), tag.end());
    return result;
}

NetJoin::NetJoin(uint32_t node_id,
                 std::vector<uint8_t> identity_private_key,
                 std::vector<uint8_t> identity_public_key)
    : node_id_(node_id),
      private_key_(std::move(identity_private_key)),
      public_key_(std::move(identity_public_key)) {}

// -- Joiner side --

JoinRequest NetJoin::create_join_request() const {
    return JoinRequest{node_id_, public_key_};
}

ChallengeResponse NetJoin::sign_challenge(const Challenge& challenge) const {
    auto signature = cirradio::security::ec_sign(private_key_, challenge.nonce);

    ChallengeResponse response;
    response.joiner_id = node_id_;
    response.nonce = challenge.nonce;
    response.signature = signature.value_or(std::vector<uint8_t>{});
    return response;
}

// -- Responder side --

void NetJoin::add_trusted_node(uint32_t node_id, std::vector<uint8_t> public_key) {
    trusted_keys_[node_id] = std::move(public_key);
}

Challenge NetJoin::create_challenge(const JoinRequest& request) {
    Challenge challenge;
    challenge.challenger_id = node_id_;
    challenge.joiner_id = request.node_id;
    challenge.nonce.resize(kNonceSize);
    RAND_bytes(challenge.nonce.data(), static_cast<int>(kNonceSize));

    pending_challenges_[request.node_id] = challenge;
    return challenge;
}

JoinAccept NetJoin::verify_and_accept(const ChallengeResponse& response,
                                       const std::vector<uint8_t>& tek,
                                       const std::vector<uint8_t>& fhek) {
    JoinAccept result;
    result.accepted = false;

    // Look up pending challenge for this joiner
    auto challenge_it = pending_challenges_.find(response.joiner_id);
    if (challenge_it == pending_challenges_.end()) {
        return result;
    }

    const auto& expected_nonce = challenge_it->second.nonce;

    // Verify the echoed nonce matches
    if (response.nonce != expected_nonce) {
        pending_challenges_.erase(challenge_it);
        return result;
    }

    // Look up trusted public key for this joiner
    auto key_it = trusted_keys_.find(response.joiner_id);
    if (key_it == trusted_keys_.end()) {
        pending_challenges_.erase(challenge_it);
        return result;
    }

    // Verify ECDSA signature of the nonce
    bool valid = cirradio::security::ec_verify(key_it->second, response.nonce, response.signature);
    if (!valid) {
        pending_challenges_.erase(challenge_it);
        return result;
    }

    // Wrap TEK and FHEK using the 32-byte nonce as a symmetric key.
    auto wrapped_tek  = aes_gcm_encrypt(expected_nonce, tek);
    auto wrapped_fhek = aes_gcm_encrypt(expected_nonce, fhek);

    if (!wrapped_tek || !wrapped_fhek) {
        pending_challenges_.erase(challenge_it);
        return result;
    }

    result.accepted = true;
    result.encrypted_tek = std::move(*wrapped_tek);
    result.encrypted_fhek = std::move(*wrapped_fhek);

    pending_challenges_.erase(challenge_it);
    return result;
}

}  // namespace cirradio::network
