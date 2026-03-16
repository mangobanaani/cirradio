// software/src/security/TamperMonitor.h
#pragma once
#include <atomic>
#include <thread>
#include <cstdint>
#include <functional>

namespace cirradio::security {

class TamperMonitor {
public:
    using TamperCallback = std::function<void(int channel)>;

    explicit TamperMonitor(TamperCallback cb,
                           const char* gpiochip = "/dev/gpiochip0");

    // Test constructor: injects a pre-opened line fd (e.g., a pipe write end).
    TamperMonitor(TamperCallback cb, int injected_fd);

    ~TamperMonitor();

    TamperMonitor(const TamperMonitor&) = delete;
    TamperMonitor& operator=(const TamperMonitor&) = delete;

    void start();
    void stop();

private:
    TamperCallback cb_;
    std::atomic<bool> running_{false};
    std::thread thread_;
    int line_fd_ = -1;
    int stop_fd_ = -1;
    bool owns_fd_ = false;

    void run_loop();
};

}  // namespace cirradio::security
