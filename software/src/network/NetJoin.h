#pragma once
#include "Messages.h"
#include "hal/ICryptoHal.h"
#include <map>
#include <memory>
#include <vector>
#include <optional>
#include <functional>

namespace cirradio::network {

class NetJoin {
public:
    // node_id: our node ID
    // crypto: crypto HAL for signing/verifying
    // identity_private_key: our DER-encoded EC P-384 private key
    // identity_public_key: our DER-encoded EC P-384 public key
    NetJoin(uint32_t node_id,
            std::shared_ptr<hal::ICryptoHal> crypto,
            std::vector<uint8_t> identity_private_key,
            std::vector<uint8_t> identity_public_key);

    // -- Joiner side --
    JoinRequest create_join_request() const;
    ChallengeResponse sign_challenge(const Challenge& challenge) const;

    // -- Responder side --

    // Add a trusted node's public key
    void add_trusted_node(uint32_t node_id, std::vector<uint8_t> public_key);

    // Create challenge for a joiner
    Challenge create_challenge(const JoinRequest& request);

    // Verify challenge response and accept/reject
    // tek and fhek are the current net keys to distribute
    JoinAccept verify_and_accept(const ChallengeResponse& response,
                                  const std::vector<uint8_t>& tek,
                                  const std::vector<uint8_t>& fhek);

private:
    uint32_t node_id_;
    std::shared_ptr<hal::ICryptoHal> crypto_;
    std::vector<uint8_t> private_key_;
    std::vector<uint8_t> public_key_;
    std::map<uint32_t, std::vector<uint8_t>> trusted_keys_;  // node_id -> public_key
    std::map<uint32_t, Challenge> pending_challenges_;  // joiner_id -> challenge
};

}  // namespace cirradio::network
