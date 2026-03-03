#include "mgmt/CLIShell.h"
#include <sstream>

namespace cirradio::mgmt {

CLIShell::CLIShell() {
    commands_["status"] = [this](const std::vector<std::string>& args) {
        return handle_status(args);
    };
    commands_["set"] = [this](const std::vector<std::string>& args) {
        return handle_set(args);
    };
    commands_["net"] = [this](const std::vector<std::string>& args) {
        return handle_net(args);
    };
    commands_["crypto"] = [this](const std::vector<std::string>& args) {
        return handle_crypto(args);
    };
}

CommandResult CLIShell::execute(const std::string& input) {
    auto tokens = tokenize(input);
    if (tokens.empty()) {
        return {false, "empty command"};
    }

    auto it = commands_.find(tokens[0]);
    if (it == commands_.end()) {
        return {false, "unknown command: " + tokens[0]};
    }

    // Pass remaining tokens as arguments
    std::vector<std::string> args(tokens.begin() + 1, tokens.end());
    return it->second(args);
}

std::vector<std::string> CLIShell::tokenize(const std::string& input) {
    std::vector<std::string> tokens;
    std::istringstream iss(input);
    std::string token;
    while (iss >> token) {
        tokens.push_back(token);
    }
    return tokens;
}

CommandResult CLIShell::handle_status(const std::vector<std::string>& /*args*/) {
    std::ostringstream oss;
    oss << "Node ID: " << node_id_ << "\n"
        << "Frequency: " << freq_hz_ << " Hz\n"
        << "Power: " << power_dbm_ << " dBm\n"
        << "Network: " << (net_joined_ ? "joined" : "not joined");
    return {true, oss.str()};
}

CommandResult CLIShell::handle_set(const std::vector<std::string>& args) {
    if (args.empty()) {
        return {false, "set requires a parameter: freq, power"};
    }

    if (args[0] == "freq") {
        if (args.size() < 2) {
            return {false, "set freq requires a frequency value in Hz"};
        }
        uint64_t hz = 0;
        try {
            hz = std::stoull(args[1]);
        } catch (...) {
            return {false, "invalid frequency value: " + args[1]};
        }
        // UHF band: 225-512 MHz
        if (hz < 225000000 || hz > 512000000) {
            return {false, "frequency out of range (225-512 MHz)"};
        }
        freq_hz_ = hz;
        return {true, "frequency set to " + std::to_string(freq_hz_) + " Hz"};
    }

    if (args[0] == "power") {
        if (args.size() < 2) {
            return {false, "set power requires a value in dBm"};
        }
        int dbm = 0;
        try {
            dbm = std::stoi(args[1]);
        } catch (...) {
            return {false, "invalid power value: " + args[1]};
        }
        if (dbm < -10 || dbm > 37) {
            return {false, "power out of range (-10 to 37 dBm)"};
        }
        power_dbm_ = dbm;
        return {true, "power set to " + std::to_string(power_dbm_) + " dBm"};
    }

    return {false, "unknown set parameter: " + args[0]};
}

CommandResult CLIShell::handle_net(const std::vector<std::string>& args) {
    if (args.empty()) {
        return {false, "net requires a subcommand: join, leave, status"};
    }

    if (args[0] == "join") {
        net_joined_ = true;
        return {true, "joined network"};
    }

    if (args[0] == "leave") {
        net_joined_ = false;
        return {true, "left network"};
    }

    if (args[0] == "status") {
        std::string state = net_joined_ ? "joined" : "not joined";
        return {true, "network status: " + state};
    }

    return {false, "unknown net subcommand: " + args[0]};
}

CommandResult CLIShell::handle_crypto(const std::vector<std::string>& args) {
    if (args.empty()) {
        return {false, "crypto requires a subcommand: zeroize, rekey"};
    }

    if (args[0] == "zeroize") {
        keys_active_ = false;
        return {true, "all keys zeroized"};
    }

    if (args[0] == "rekey") {
        keys_active_ = true;
        return {true, "rekey initiated"};
    }

    return {false, "unknown crypto subcommand: " + args[0]};
}

}  // namespace cirradio::mgmt
