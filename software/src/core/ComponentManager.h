#pragma once
#include "Component.h"
#include <memory>
#include <string>
#include <map>
#include <vector>

namespace cirradio::core {

class ComponentManager {
public:
    void register_component(const std::string& name, std::shared_ptr<Component> component);
    void unregister_component(const std::string& name);

    void configure(const std::string& name);
    void start(const std::string& name);
    void stop(const std::string& name);

    // Lifecycle operations on all components
    void configure_all();
    void start_all();
    void stop_all();

    std::shared_ptr<Component> get(const std::string& name) const;
    std::vector<std::string> list() const;
    size_t count() const;

private:
    std::map<std::string, std::shared_ptr<Component>> components_;
};

}  // namespace cirradio::core
