#include "network/NetJoin.h"
#include <openssl/rand.h>
#include <algorithm>

namespace cirradio::network {

static constexpr size_t kNonceSize = 32;

NetJoin::NetJoin(uint32_t node_id,
                 std::shared_ptr<hal::ICryptoHal> crypto,
                 std::vector<uint8_t> identity_private_key,
                 std::vector<uint8_t> identity_public_key)
    : node_id_(node_id),
      crypto_(std::move(crypto)),
      private_key_(std::move(identity_private_key)),
      public_key_(std::move(identity_public_key)) {}

// -- Joiner side --

JoinRequest NetJoin::create_join_request() const {
    return JoinRequest{node_id_, public_key_};
}

ChallengeResponse NetJoin::sign_challenge(const Challenge& challenge) const {
    auto signature = crypto_->sign(private_key_, challenge.nonce);

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
    bool valid = crypto_->verify(key_it->second, response.nonce, response.signature);
    if (!valid) {
        pending_challenges_.erase(challenge_it);
        return result;
    }

    // Wrap TEK and FHEK for the joiner using the nonce as a symmetric wrapping key.
    // In a production system this would use ECIES or a proper key agreement protocol.
    // Here we use the 32-byte nonce as a symmetric key for AES-256-GCM wrapping.
    auto wrapped_tek = crypto_->encrypt(expected_nonce, tek);
    auto wrapped_fhek = crypto_->encrypt(expected_nonce, fhek);

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
