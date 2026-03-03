#include <catch2/catch_test_macros.hpp>
#include "node/RadioNode.h"
#include "hal/SimChannel.h"
#include <memory>
#include <vector>

using namespace cirradio;

TEST_CASE("Two nodes discover each other and exchange data", "[integration]") {
    auto channel = std::make_shared<hal::SimChannel>();
    node::RadioNode node_a(1, channel);
    node::RadioNode node_b(2, channel);

    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    node_a.provision_keys(tek, fhek);
    node_b.provision_keys(tek, fhek);

    node_a.start();
    node_b.start();

    // Simulate several frames to allow discovery
    for (int frame = 0; frame < 10; ++frame) {
        node_a.tick();
        node_b.tick();
    }

    REQUIRE(node_a.peers().size() == 1);
    REQUIRE(node_a.peers()[0] == 2);
    REQUIRE(node_b.peers().size() == 1);
    REQUIRE(node_b.peers()[0] == 1);

    // Send data from A to B
    std::vector<uint8_t> message = {'P', 'I', 'N', 'G'};
    node_a.send_data(2, message);

    // Tick to process the transmission
    node_a.tick();
    node_b.tick();

    auto received = node_b.receive_data();
    REQUIRE(received.has_value());
    REQUIRE(received->payload == message);
    REQUIRE(received->source == 1);
}

TEST_CASE("Three nodes discover each other", "[integration]") {
    auto channel = std::make_shared<hal::SimChannel>();
    node::RadioNode node_a(1, channel);
    node::RadioNode node_b(2, channel);
    node::RadioNode node_c(3, channel);

    std::vector<uint8_t> tek(32, 0xAA);
    std::vector<uint8_t> fhek(32, 0xBB);
    node_a.provision_keys(tek, fhek);
    node_b.provision_keys(tek, fhek);
    node_c.provision_keys(tek, fhek);

    node_a.start();
    node_b.start();
    node_c.start();

    for (int frame = 0; frame < 10; ++frame) {
        node_a.tick();
        node_b.tick();
        node_c.tick();
    }

    REQUIRE(node_a.peers().size() == 2);
    REQUIRE(node_b.peers().size() == 2);
    REQUIRE(node_c.peers().size() == 2);
}

TEST_CASE("Data exchange across three nodes", "[integration]") {
    auto channel = std::make_shared<hal::SimChannel>();
    node::RadioNode node_a(1, channel);
    node::RadioNode node_b(2, channel);
    node::RadioNode node_c(3, channel);

    std::vector<uint8_t> tek(32, 0xCC);
    std::vector<uint8_t> fhek(32, 0xDD);
    node_a.provision_keys(tek, fhek);
    node_b.provision_keys(tek, fhek);
    node_c.provision_keys(tek, fhek);

    node_a.start();
    node_b.start();
    node_c.start();

    for (int frame = 0; frame < 10; ++frame) {
        node_a.tick();
        node_b.tick();
        node_c.tick();
    }

    // Node 1 sends to node 3
    std::vector<uint8_t> message = {'H', 'E', 'L', 'L', 'O'};
    node_a.send_data(3, message);

    node_a.tick();
    node_b.tick();
    node_c.tick();

    auto received = node_c.receive_data();
    REQUIRE(received.has_value());
    REQUIRE(received->payload == message);
    REQUIRE(received->source == 1);
}
