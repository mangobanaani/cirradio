#include <catch2/catch_test_macros.hpp>
#include <chrono>

#include "network/LinkState.h"
#include "network/RouteTable.h"
#include "network/MeshRouter.h"

TEST_CASE("RouteTable computes shortest path", "[network]") {
    cirradio::network::RouteTable table(1);
    // 1 -- 0.9 -- 2 -- 0.8 -- 3
    // 1 -- 0.5 -- 3 (direct but worse)
    table.update_link(1, 2, 0.9f);
    table.update_link(1, 3, 0.5f);
    table.update_link(2, 3, 0.8f);
    table.recompute();

    auto r2 = table.next_hop(2);
    REQUIRE(r2.has_value());
    REQUIRE(r2->next_hop == 2);
    REQUIRE(r2->hop_count == 1);

    auto r3 = table.next_hop(3);
    REQUIRE(r3.has_value());
    // 1->2->3 quality = 0.9*0.8 = 0.72 > 0.5 (direct)
    REQUIRE(r3->next_hop == 2);
    REQUIRE(r3->hop_count == 2);
    REQUIRE(r3->path_quality > 0.7f);
}

TEST_CASE("RouteTable handles node disappearance", "[network]") {
    cirradio::network::RouteTable table(1);
    table.update_link(1, 2, 0.9f);
    table.update_link(2, 3, 0.8f);
    table.recompute();
    REQUIRE(table.next_hop(3).has_value());

    table.remove_node(2);
    table.recompute();
    REQUIRE_FALSE(table.next_hop(3).has_value());
}

TEST_CASE("RouteTable has no route entry for self", "[network]") {
    cirradio::network::RouteTable table(1);
    table.update_link(1, 2, 0.9f);
    table.recompute();
    REQUIRE_FALSE(table.next_hop(1).has_value());
}

TEST_CASE("MeshRouter processes link-state advertisements", "[network]") {
    cirradio::network::MeshRouter router(1);
    router.update_neighbor(2, 0.9f);

    // Receive advertisement from node 2 saying it can reach node 3
    cirradio::network::LinkStateAdvertisement lsa;
    lsa.node_id = 2;
    lsa.neighbors = {{3, 0.8f}};
    lsa.sequence = 1;
    lsa.timestamp = std::chrono::steady_clock::now();

    REQUIRE(router.process_advertisement(lsa));
    auto route = router.route_to(3);
    REQUIRE(route.has_value());
    REQUIRE(route->next_hop == 2);
}

TEST_CASE("MeshRouter rejects stale advertisements", "[network]") {
    cirradio::network::MeshRouter router(1);
    router.update_neighbor(2, 0.9f);

    cirradio::network::LinkStateAdvertisement lsa;
    lsa.node_id = 2;
    lsa.neighbors = {{3, 0.8f}};
    lsa.sequence = 5;
    lsa.timestamp = std::chrono::steady_clock::now();
    REQUIRE(router.process_advertisement(lsa));

    lsa.sequence = 3;  // older sequence
    REQUIRE_FALSE(router.process_advertisement(lsa));
}

TEST_CASE("MeshRouter generates advertisement", "[network]") {
    cirradio::network::MeshRouter router(1);
    router.update_neighbor(2, 0.9f);
    router.update_neighbor(3, 0.5f);

    auto lsa = router.generate_advertisement();
    REQUIRE(lsa.node_id == 1);
    REQUIRE(lsa.neighbors.size() == 2);
}

TEST_CASE("MeshRouter remove_neighbor updates routing", "[network]") {
    cirradio::network::MeshRouter router(1);
    router.update_neighbor(2, 0.9f);
    REQUIRE(router.route_to(2).has_value());

    router.remove_neighbor(2);
    REQUIRE_FALSE(router.route_to(2).has_value());
}

TEST_CASE("Four-node mesh finds optimal routes", "[network]") {
    cirradio::network::MeshRouter router(1);
    router.update_neighbor(2, 0.9f);
    router.update_neighbor(4, 0.3f);

    // Node 2 sees node 3
    cirradio::network::LinkStateAdvertisement lsa2;
    lsa2.node_id = 2;
    lsa2.neighbors = {{1, 0.9f}, {3, 0.9f}};
    lsa2.sequence = 1;
    lsa2.timestamp = std::chrono::steady_clock::now();
    router.process_advertisement(lsa2);

    // Node 4 also sees node 3
    cirradio::network::LinkStateAdvertisement lsa4;
    lsa4.node_id = 4;
    lsa4.neighbors = {{1, 0.3f}, {3, 0.9f}};
    lsa4.sequence = 1;
    lsa4.timestamp = std::chrono::steady_clock::now();
    router.process_advertisement(lsa4);

    auto route_to_3 = router.route_to(3);
    REQUIRE(route_to_3.has_value());
    // 1->2->3 (0.9*0.9=0.81) should beat 1->4->3 (0.3*0.9=0.27)
    REQUIRE(route_to_3->next_hop == 2);
}
