#pragma once
#include <string>
#include <functional>
#include <map>
#include <vector>
#include "transec/EmconManager.h"
#include "transec/TransecConfig.h"
#include "security/IAxiRegs.h"

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

    void set_emcon_manager(transec::EmconManager* em) { emcon_mgr_ = em; }
    void set_transec_config(transec::TransecConfig* cfg) { transec_cfg_ = cfg; }
    void set_axi_regs(security::IAxiRegs* regs) { axi_regs_ = regs; }

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
    CommandResult handle_emcon(const std::vector<std::string>& args);
    CommandResult handle_transec(const std::vector<std::string>& args);

    // State (wired to subsystems via RadioNode constructor injection)
    uint32_t node_id_ = 1;
    uint64_t freq_hz_ = 300000000;
    int power_dbm_ = 10;
    bool net_joined_ = false;
    bool keys_active_ = true;

    transec::EmconManager*  emcon_mgr_   = nullptr;
    transec::TransecConfig* transec_cfg_ = nullptr;
    security::IAxiRegs*     axi_regs_    = nullptr;
};

}  // namespace cirradio::mgmt
