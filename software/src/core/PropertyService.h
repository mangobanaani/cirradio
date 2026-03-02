#pragma once
#include <string>
#include <any>
#include <map>
#include <stdexcept>
#include <optional>
#include <vector>

namespace cirradio::core {

class PropertyService {
public:
    template<typename T>
    void set(const std::string& key, T value) {
        properties_[key] = std::move(value);
    }

    template<typename T>
    T get(const std::string& key) const {
        auto it = properties_.find(key);
        if (it == properties_.end())
            throw std::runtime_error("Property not found: " + key);
        return std::any_cast<T>(it->second);
    }

    template<typename T>
    std::optional<T> try_get(const std::string& key) const {
        auto it = properties_.find(key);
        if (it == properties_.end()) return std::nullopt;
        try {
            return std::any_cast<T>(it->second);
        } catch (...) {
            return std::nullopt;
        }
    }

    bool has(const std::string& key) const;
    void remove(const std::string& key);
    size_t count() const;
    std::vector<std::string> keys() const;

private:
    std::map<std::string, std::any> properties_;
};

}  // namespace cirradio::core
