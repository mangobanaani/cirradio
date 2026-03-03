#include <catch2/catch_test_macros.hpp>
#include <memory>

#include "hal/SimChannel.h"
#include "node/RadioNode.h"

using namespace cirradio::node;
using namespace cirradio::hal;

TEST_CASE("RadioNode initializes all subsystems", "[node]") {
    auto channel = std::make_shared<SimChannel>();
    RadioNode node(/*id=*/1, channel);

    REQUIRE(node.state() == NodeState::Idle);
    node.start();
    REQUIRE(node.state() == NodeState::Listening);
}

TEST_CASE("RadioNode tick advances discovery", "[node]") {
    auto channel = std::make_shared<SimChannel>();
    RadioNode node1(1, channel);
    RadioNode node2(2, channel);

    node1.start();
    node2.start();

    // Tick both nodes several times so they discover each other
    for (int i = 0; i < 3; ++i) {
        node1.tick();
        node2.tick();
    }

    auto peers1 = node1.peers();
    auto peers2 = node2.peers();

    REQUIRE(std::find(peers1.begin(), peers1.end(), 2) != peers1.end());
    REQUIRE(std::find(peers2.begin(), peers2.end(), 1) != peers2.end());
}

TEST_CASE("RadioNode provision_keys sets shared keys", "[node]") {
    auto channel = std::make_shared<SimChannel>();

    std::vector<uint8_t> shared_tek(32, 0xAA);
    std::vector<uint8_t> shared_fhek(32, 0xBB);

    RadioNode node(1, channel);
    node.provision_keys(shared_tek, shared_fhek);
    node.start();

    REQUIRE(node.state() == NodeState::Listening);
}

TEST_CASE("RadioNode cli_execute delegates to CLIShell", "[node]") {
    auto channel = std::make_shared<SimChannel>();
    RadioNode node(1, channel);
    node.start();

    auto result = node.cli_execute("status");
    REQUIRE(result.success);
    REQUIRE(result.output.find("Node ID") != std::string::npos);
}
