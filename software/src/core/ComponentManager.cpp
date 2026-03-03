#include "core/ComponentManager.h"
#include <stdexcept>

namespace cirradio::core {

void ComponentManager::register_component(const std::string& name,
                                          std::shared_ptr<Component> component) {
    if (components_.count(name))
        throw std::runtime_error("Component already registered: " + name);
    components_[name] = std::move(component);
}

void ComponentManager::unregister_component(const std::string& name) {
    auto it = components_.find(name);
    if (it == components_.end())
        throw std::runtime_error("Component not found: " + name);
    components_.erase(it);
}

void ComponentManager::configure(const std::string& name) {
    get(name)->configure();
}

void ComponentManager::start(const std::string& name) {
    get(name)->start();
}

void ComponentManager::stop(const std::string& name) {
    get(name)->stop();
}

void ComponentManager::configure_all() {
    for (auto& [name, comp] : components_)
        comp->configure();
}

void ComponentManager::start_all() {
    for (auto& [name, comp] : components_)
        comp->start();
}

void ComponentManager::stop_all() {
    for (auto& [name, comp] : components_)
        comp->stop();
}

std::shared_ptr<Component> ComponentManager::get(const std::string& name) const {
    auto it = components_.find(name);
    if (it == components_.end())
        throw std::runtime_error("Component not found: " + name);
    return it->second;
}

std::vector<std::string> ComponentManager::list() const {
    std::vector<std::string> names;
    names.reserve(components_.size());
    for (const auto& [name, comp] : components_)
        names.push_back(name);
    return names;
}

size_t ComponentManager::count() const {
    return components_.size();
}

}  // namespace cirradio::core
