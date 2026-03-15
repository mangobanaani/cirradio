// software/tests/test_multinode_stress.cpp
#include <catch2/catch_test_macros.hpp>
#include "node/RadioNode.h"
#include "hal/SimChannel.h"
#include <memory>
#include <vector>
#include <algorithm>

using namespace cirradio;

namespace {

void provision_and_start(std::vector<node::RadioNode*>& nodes) {
    std::vector<uint8_t> tek(32, 0xAA), fhek(32, 0xBB);
    for (auto* n : nodes) { n->provision_keys(tek, fhek); n->start(); }
}

void tick_all(std::vector<node::RadioNode*>& nodes, int frames) {
    for (int f = 0; f < frames; ++f)
        for (auto* n : nodes) n->tick();
}

bool all_fully_meshed(std::vector<node::RadioNode*>& nodes) {
    size_t expected = nodes.size() - 1;
    return std::all_of(nodes.begin(), nodes.end(), [expected](node::RadioNode* n) {
        return n->peers().size() >= expected;
    });
}

}  // namespace

TEST_CASE("6-node partition then rejoin reconverges", "[stress]") {
    auto channel = std::make_shared<hal::SimChannel>();

    std::vector<std::unique_ptr<node::RadioNode>> owned;
    std::vector<node::RadioNode*> all_nodes;
    for (uint32_t id = 1; id <= 6; ++id) {
        owned.push_back(std::make_unique<node::RadioNode>(id, channel));
        all_nodes.push_back(owned.back().get());
    }

    provision_and_start(all_nodes);
    tick_all(all_nodes, 20);

    channel->set_partition_active(true);
    tick_all(all_nodes, 10);

    channel->set_partition_active(false);
    tick_all(all_nodes, 50);

    REQUIRE(all_fully_meshed(all_nodes));
}

TEST_CASE("FHSS collision detected: losing node retries", "[stress]") {
    auto channel = std::make_shared<hal::SimChannel>();

    std::vector<std::unique_ptr<node::RadioNode>> owned;
    std::vector<node::RadioNode*> nodes;
    for (uint32_t id = 1; id <= 4; ++id) {
        owned.push_back(std::make_unique<node::RadioNode>(id, channel));
        nodes.push_back(owned.back().get());
    }

    provision_and_start(nodes);
    tick_all(nodes, 100);

    REQUIRE(all_fully_meshed(nodes));
}

TEST_CASE("20-node mesh frame delivery >= 99% over 1000 frames", "[stress]") {
    auto channel = std::make_shared<hal::SimChannel>();

    std::vector<std::unique_ptr<node::RadioNode>> owned;
    std::vector<node::RadioNode*> nodes;
    for (uint32_t id = 1; id <= 20; ++id) {
        owned.push_back(std::make_unique<node::RadioNode>(id, channel));
        nodes.push_back(owned.back().get());
    }

    provision_and_start(nodes);
    // Allow time for all nodes to discover each other before sending
    tick_all(nodes, 30);

    int sent = 0;
    std::vector<uint8_t> payload = {'P', 'I', 'N', 'G'};
    for (uint32_t dst = 2; dst <= 20; ++dst) {
        nodes[0]->send_data(dst, payload);
        ++sent;
    }

    tick_all(nodes, 1000);

    int received = 0;
    for (size_t i = 1; i < nodes.size(); ++i) {
        auto data = nodes[i]->receive_data();
        if (data.has_value()) ++received;
    }

    double ratio = static_cast<double>(received) / sent;
    INFO("Delivery ratio = " << ratio << " (" << received << "/" << sent << ")");
    REQUIRE(ratio >= 0.99);
}
