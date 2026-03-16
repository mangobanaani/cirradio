// software/src/security/TamperMonitor.cpp
#include "security/TamperMonitor.h"
#include <spdlog/spdlog.h>
#include <cstring>

#ifdef __linux__
#include <fcntl.h>
#include <unistd.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <linux/gpio.h>
#include <pthread.h>
#include <sched.h>
#endif

namespace cirradio::security {

TamperMonitor::TamperMonitor(TamperCallback cb, const char* gpiochip)
    : cb_(std::move(cb)), owns_fd_(true)
{
#ifdef __linux__
    int chip_fd = open(gpiochip, O_RDONLY | O_CLOEXEC);
    if (chip_fd < 0) {
        spdlog::warn("TamperMonitor: cannot open {}: {}", gpiochip, strerror(errno));
        return;
    }

    struct gpio_v2_line_request req{};
    req.offsets[0] = 0;
    req.offsets[1] = 1;
    req.offsets[2] = 2;
    req.num_lines  = 3;
    req.config.flags = GPIO_V2_LINE_FLAG_EDGE_FALLING |
                       GPIO_V2_LINE_FLAG_ACTIVE_LOW   |
                       GPIO_V2_LINE_FLAG_INPUT;

    if (ioctl(chip_fd, GPIO_V2_GET_LINE_IOCTL, &req) < 0) {
        spdlog::warn("TamperMonitor: GPIO_V2_GET_LINE_IOCTL failed: {}", strerror(errno));
        close(chip_fd);
        return;
    }
    close(chip_fd);
    line_fd_ = req.fd;
    stop_fd_ = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
#endif
}

TamperMonitor::TamperMonitor(TamperCallback cb, int injected_fd)
    : cb_(std::move(cb)), line_fd_(injected_fd), owns_fd_(false)
{
#ifdef __linux__
    stop_fd_ = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
#endif
}

TamperMonitor::~TamperMonitor() {
    stop();
#ifdef __linux__
    if (owns_fd_ && line_fd_ >= 0) close(line_fd_);
    if (stop_fd_ >= 0) close(stop_fd_);
#endif
}

void TamperMonitor::start() {
    if (line_fd_ < 0) return;
    running_.store(true, std::memory_order_relaxed);
    thread_ = std::thread([this]{ run_loop(); });
#ifdef __linux__
    sched_param sp{};
    sp.sched_priority = 99;
    pthread_setschedparam(thread_.native_handle(), SCHED_FIFO, &sp);
#endif
}

void TamperMonitor::stop() {
    running_.store(false, std::memory_order_relaxed);
#ifdef __linux__
    if (stop_fd_ >= 0) {
        uint64_t one = 1;
        write(stop_fd_, &one, sizeof(one));
    }
#endif
    if (thread_.joinable()) thread_.join();
}

void TamperMonitor::run_loop() {
#ifdef __linux__
    int ep = epoll_create1(EPOLL_CLOEXEC);
    {
        epoll_event ev{};
        ev.events  = EPOLLIN;
        ev.data.fd = line_fd_;
        epoll_ctl(ep, EPOLL_CTL_ADD, line_fd_, &ev);
    }
    if (stop_fd_ >= 0) {
        epoll_event ev{};
        ev.events  = EPOLLIN;
        ev.data.fd = stop_fd_;
        epoll_ctl(ep, EPOLL_CTL_ADD, stop_fd_, &ev);
    }

    while (running_.load(std::memory_order_relaxed)) {
        epoll_event events[2];
        int n = epoll_wait(ep, events, 2, -1);
        if (n < 0) break;
        for (int i = 0; i < n; ++i) {
            if (events[i].data.fd == stop_fd_) goto done;
            if (events[i].data.fd == line_fd_) {
                gpio_v2_line_event evt{};
                if (read(line_fd_, &evt, sizeof(evt)) == sizeof(evt)) {
                    int channel = static_cast<int>(evt.offset);
                    spdlog::critical("[TAMPER] channel={} asserted", channel);
                    if (cb_) cb_(channel);
                }
            }
        }
    }
done:
    close(ep);
#endif
}

}  // namespace cirradio::security
