#include <catch2/catch_test_macros.hpp>
#include <memory>
#include <vector>
#include <cstdint>
#include <thread>
#include <chrono>

#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/x509.h>

#include "network/NetJoin.h"
#include "network/PeerDiscovery.h"
#include "security/SoftCryptoHal.h"

using namespace cirradio::network;
using namespace cirradio::security;

namespace {

// Helper: serialize EVP_PKEY private key to DER
std::vector<uint8_t> private_key_to_der(EVP_PKEY* pkey) {
    int len = i2d_PrivateKey(pkey, nullptr);
    if (len <= 0) return {};
    std::vector<uint8_t> der(static_cast<size_t>(len));
    unsigned char* p = der.data();
    i2d_PrivateKey(pkey, &p);
    return der;
}

// Helper: serialize EVP_PKEY public key to DER
std::vector<uint8_t> public_key_to_der(EVP_PKEY* pkey) {
    int len = i2d_PUBKEY(pkey, nullptr);
    if (len <= 0) return {};
    std::vector<uint8_t> der(static_cast<size_t>(len));
    unsigned char* p = der.data();
    i2d_PUBKEY(pkey, &p);
    return der;
}

// RAII wrapper for EC P-384 key pair generation
struct EcKeyPair {
    EVP_PKEY* pkey = nullptr;
    std::vector<uint8_t> private_der;
    std::vector<uint8_t> public_der;

    EcKeyPair() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
        REQUIRE(ctx != nullptr);
        REQUIRE(EVP_PKEY_keygen_init(ctx) == 1);
        REQUIRE(EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_secp384r1) == 1);
        REQUIRE(EVP_PKEY_keygen(ctx, &pkey) == 1);
        EVP_PKEY_CTX_free(ctx);

        private_der = private_key_to_der(pkey);
        public_der = public_key_to_der(pkey);
        REQUIRE(!private_der.empty());
        REQUIRE(!public_der.empty());
    }

    ~EcKeyPair() {
        EVP_PKEY_free(pkey);
    }

    EcKeyPair(const EcKeyPair&) = delete;
    EcKeyPair& operator=(const EcKeyPair&) = delete;
};

}  // namespace

TEST_CASE("Net join: challenge-response authentication succeeds", "[network]") {
    EcKeyPair responder_keys;
    EcKeyPair joiner_keys;

    auto crypto = std::make_shared<SoftCryptoHal>();

    NetJoin responder(1, crypto, responder_keys.private_der, responder_keys.public_der);
    NetJoin joiner(2, crypto, joiner_keys.private_der, joiner_keys.public_der);

    // Responder trusts the joiner
    responder.add_trusted_node(2, joiner_keys.public_der);

    // Step 1: Joiner creates join request
    auto join_request = joiner.create_join_request();
    REQUIRE(join_request.node_id == 2);
    REQUIRE(join_request.public_key == joiner_keys.public_der);

    // Step 2: Responder creates challenge
    auto challenge = responder.create_challenge(join_request);
    REQUIRE(challenge.challenger_id == 1);
    REQUIRE(challenge.joiner_id == 2);
    REQUIRE(challenge.nonce.size() == 32);

    // Step 3: Joiner signs challenge
    auto response = joiner.sign_challenge(challenge);
    REQUIRE(response.joiner_id == 2);
    REQUIRE(response.nonce == challenge.nonce);
    REQUIRE(!response.signature.empty());

    // Step 4: Responder verifies and accepts
    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    auto result = responder.verify_and_accept(response, tek, fhek);

    REQUIRE(result.accepted == true);
    REQUIRE(!result.encrypted_tek.empty());
    REQUIRE(!result.encrypted_fhek.empty());
}

TEST_CASE("Net join: rejects unknown node", "[network]") {
    EcKeyPair responder_keys;
    EcKeyPair joiner_keys;

    auto crypto = std::make_shared<SoftCryptoHal>();

    NetJoin responder(1, crypto, responder_keys.private_der, responder_keys.public_der);
    NetJoin joiner(2, crypto, joiner_keys.private_der, joiner_keys.public_der);

    // Responder does NOT add joiner's key to trusted list

    auto join_request = joiner.create_join_request();
    auto challenge = responder.create_challenge(join_request);
    auto response = joiner.sign_challenge(challenge);

    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    auto result = responder.verify_and_accept(response, tek, fhek);

    REQUIRE(result.accepted == false);
}

TEST_CASE("Net join: rejects tampered signature", "[network]") {
    EcKeyPair responder_keys;
    EcKeyPair joiner_keys;

    auto crypto = std::make_shared<SoftCryptoHal>();

    NetJoin responder(1, crypto, responder_keys.private_der, responder_keys.public_der);
    NetJoin joiner(2, crypto, joiner_keys.private_der, joiner_keys.public_der);

    responder.add_trusted_node(2, joiner_keys.public_der);

    auto join_request = joiner.create_join_request();
    auto challenge = responder.create_challenge(join_request);
    auto response = joiner.sign_challenge(challenge);

    // Tamper with the signature
    REQUIRE(!response.signature.empty());
    response.signature[0] ^= 0xFF;

    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    auto result = responder.verify_and_accept(response, tek, fhek);

    REQUIRE(result.accepted == false);
}

TEST_CASE("PeerDiscovery: generates beacon", "[network]") {
    PeerDiscovery discovery(42, 100);

    auto beacon = discovery.generate_beacon(5);

    REQUIRE(beacon.node_id == 42);
    REQUIRE(beacon.net_id == 100);
    REQUIRE(beacon.num_nodes == 5);
    REQUIRE(beacon.timestamp.time_since_epoch().count() > 0);
}

TEST_CASE("PeerDiscovery: discovers new nodes", "[network]") {
    PeerDiscovery discovery(1);

    DiscoveryBeacon beacon;
    beacon.node_id = 2;
    beacon.net_id = 0;
    beacon.num_nodes = 1;
    beacon.timestamp = std::chrono::steady_clock::now();

    // First time seeing node 2 - should return true
    REQUIRE(discovery.process_beacon(beacon) == true);

    // Second time seeing node 2 - should return false (already known)
    REQUIRE(discovery.process_beacon(beacon) == false);

    auto nodes = discovery.discovered_nodes();
    REQUIRE(nodes.size() == 1);
    REQUIRE(nodes[0] == 2);
}

TEST_CASE("PeerDiscovery: expires stale nodes", "[network]") {
    PeerDiscovery discovery(1);

    DiscoveryBeacon beacon;
    beacon.node_id = 2;
    beacon.net_id = 0;
    beacon.num_nodes = 1;
    beacon.timestamp = std::chrono::steady_clock::now();

    REQUIRE(discovery.process_beacon(beacon) == true);
    REQUIRE(discovery.discovered_nodes().size() == 1);

    // Expire with zero timeout - everything should be stale
    discovery.expire_stale(std::chrono::steady_clock::duration::zero());

    REQUIRE(discovery.discovered_nodes().empty());
}
