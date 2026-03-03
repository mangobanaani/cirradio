#pragma once
#include <string>
#include <functional>
#include <map>
#include <vector>

namespace cirradio::mgmt {

struct CommandResult {
    bool success;
    std::string output;
};

class CLIShell {
public:
    CLIShell();

    // Execute a command string and return the result.
    CommandResult execute(const std::string& input);

private:
    using Handler = std::function<CommandResult(const std::vector<std::string>& args)>;

    // Top-level command dispatch table
    std::map<std::string, Handler> commands_;

    // Parse input into tokens
    static std::vector<std::string> tokenize(const std::string& input);

    // Command handlers
    CommandResult handle_status(const std::vector<std::string>& args);
    CommandResult handle_set(const std::vector<std::string>& args);
    CommandResult handle_net(const std::vector<std::string>& args);
    CommandResult handle_crypto(const std::vector<std::string>& args);

    // State (stub values for standalone operation; wired to subsystems in Task 13)
    uint32_t node_id_ = 1;
    uint64_t freq_hz_ = 300000000;
    int power_dbm_ = 10;
    bool net_joined_ = false;
    bool keys_active_ = true;
};

}  // namespace cirradio::mgmt
