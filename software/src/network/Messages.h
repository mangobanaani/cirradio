#pragma once
#include <cstdint>
#include <vector>
#include <chrono>

namespace cirradio::network {

struct JoinRequest {
    uint32_t node_id;
    std::vector<uint8_t> public_key;  // DER-encoded EC P-384 public key
};

struct Challenge {
    uint32_t challenger_id;
    uint32_t joiner_id;
    std::vector<uint8_t> nonce;  // 32 random bytes
};

struct ChallengeResponse {
    uint32_t joiner_id;
    std::vector<uint8_t> nonce;      // echo back
    std::vector<uint8_t> signature;  // ECDSA signature of nonce
};

struct JoinAccept {
    bool accepted;
    std::vector<uint8_t> encrypted_tek;   // TEK wrapped under joiner's public key
    std::vector<uint8_t> encrypted_fhek;  // FHEK wrapped under joiner's public key
};

struct DiscoveryBeacon {
    uint32_t node_id;
    uint32_t net_id;          // network identifier
    uint8_t num_nodes;        // current node count
    std::chrono::steady_clock::time_point timestamp;
};

}  // namespace cirradio::network
