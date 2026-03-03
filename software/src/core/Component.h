#pragma once
#include <string>
#include <stdexcept>

namespace cirradio::core {

enum class ComponentState {
    Idle,
    Configured,
    Running
};

class Component {
public:
    virtual ~Component() = default;

    ComponentState state() const { return state_; }

    void configure() {
        if (state_ != ComponentState::Idle)
            throw std::runtime_error("Component must be Idle to configure");
        on_configure();
        state_ = ComponentState::Configured;
    }

    void start() {
        if (state_ != ComponentState::Configured)
            throw std::runtime_error("Component must be Configured to start");
        on_start();
        state_ = ComponentState::Running;
    }

    void stop() {
        if (state_ != ComponentState::Running)
            throw std::runtime_error("Component must be Running to stop");
        on_stop();
        state_ = ComponentState::Idle;
    }

protected:
    virtual void on_configure() {}
    virtual void on_start() {}
    virtual void on_stop() {}

private:
    ComponentState state_ = ComponentState::Idle;
};

}  // namespace cirradio::core
