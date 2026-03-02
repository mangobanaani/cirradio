#include <catch2/catch_test_macros.hpp>
#include "core/Component.h"
#include "core/ComponentManager.h"
#include "core/PropertyService.h"
#include <memory>
#include <string>

class TestComponent : public cirradio::core::Component {
public:
    int configure_count = 0;
    int start_count = 0;
    int stop_count = 0;
protected:
    void on_configure() override { ++configure_count; }
    void on_start() override { ++start_count; }
    void on_stop() override { ++stop_count; }
};

TEST_CASE("Component lifecycle: configure -> start -> stop", "[sca]") {
    auto comp = std::make_shared<TestComponent>();
    REQUIRE(comp->state() == cirradio::core::ComponentState::Idle);
    comp->configure();
    REQUIRE(comp->state() == cirradio::core::ComponentState::Configured);
    REQUIRE(comp->configure_count == 1);
    comp->start();
    REQUIRE(comp->state() == cirradio::core::ComponentState::Running);
    comp->stop();
    REQUIRE(comp->state() == cirradio::core::ComponentState::Idle);
}

TEST_CASE("Invalid state transitions throw", "[sca]") {
    auto comp = std::make_shared<TestComponent>();
    REQUIRE_THROWS(comp->start());  // can't start from Idle
    REQUIRE_THROWS(comp->stop());   // can't stop from Idle
    comp->configure();
    REQUIRE_THROWS(comp->configure());  // can't configure from Configured
    REQUIRE_THROWS(comp->stop());  // can't stop from Configured
}

TEST_CASE("ComponentManager registers and manages components", "[sca]") {
    cirradio::core::ComponentManager mgr;
    auto comp = std::make_shared<TestComponent>();
    mgr.register_component("test", comp);
    REQUIRE(mgr.count() == 1);
    REQUIRE(mgr.get("test") == comp);

    mgr.configure("test");
    REQUIRE(comp->state() == cirradio::core::ComponentState::Configured);
    mgr.start("test");
    REQUIRE(comp->state() == cirradio::core::ComponentState::Running);
    mgr.stop("test");
    REQUIRE(comp->state() == cirradio::core::ComponentState::Idle);
}

TEST_CASE("ComponentManager bulk lifecycle operations", "[sca]") {
    cirradio::core::ComponentManager mgr;
    auto a = std::make_shared<TestComponent>();
    auto b = std::make_shared<TestComponent>();
    mgr.register_component("a", a);
    mgr.register_component("b", b);

    mgr.configure_all();
    REQUIRE(a->state() == cirradio::core::ComponentState::Configured);
    REQUIRE(b->state() == cirradio::core::ComponentState::Configured);

    mgr.start_all();
    REQUIRE(a->state() == cirradio::core::ComponentState::Running);

    mgr.stop_all();
    REQUIRE(a->state() == cirradio::core::ComponentState::Idle);
}

TEST_CASE("PropertyService stores and retrieves typed properties", "[sca]") {
    cirradio::core::PropertyService props;
    props.set("radio.freq", uint64_t{300'000'000});
    props.set("radio.name", std::string{"alpha"});
    props.set("radio.power", 5.0f);

    REQUIRE(props.get<uint64_t>("radio.freq") == 300'000'000);
    REQUIRE(props.get<std::string>("radio.name") == "alpha");
    REQUIRE(props.get<float>("radio.power") == 5.0f);
    REQUIRE_THROWS(props.get<uint64_t>("nonexistent"));
}

TEST_CASE("PropertyService try_get returns nullopt for missing keys", "[sca]") {
    cirradio::core::PropertyService props;
    props.set("exists", 42);
    REQUIRE(props.try_get<int>("exists").has_value());
    REQUIRE(props.try_get<int>("exists").value() == 42);
    REQUIRE_FALSE(props.try_get<int>("missing").has_value());
    REQUIRE(props.has("exists"));
    REQUIRE_FALSE(props.has("missing"));
}

TEST_CASE("PropertyService remove and count", "[sca]") {
    cirradio::core::PropertyService props;
    props.set("a", 1);
    props.set("b", 2);
    REQUIRE(props.count() == 2);
    props.remove("a");
    REQUIRE(props.count() == 1);
    REQUIRE_FALSE(props.has("a"));
}
