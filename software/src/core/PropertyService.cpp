#include "core/PropertyService.h"

namespace cirradio::core {

bool PropertyService::has(const std::string& key) const {
    return properties_.find(key) != properties_.end();
}

void PropertyService::remove(const std::string& key) {
    properties_.erase(key);
}

size_t PropertyService::count() const {
    return properties_.size();
}

std::vector<std::string> PropertyService::keys() const {
    std::vector<std::string> result;
    result.reserve(properties_.size());
    for (const auto& [key, val] : properties_)
        result.push_back(key);
    return result;
}

}  // namespace cirradio::core
