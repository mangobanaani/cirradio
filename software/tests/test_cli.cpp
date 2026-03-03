#include <catch2/catch_test_macros.hpp>
#include <string>

#include "mgmt/CLIShell.h"

using namespace cirradio::mgmt;

TEST_CASE("CLI parses status command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("status");
    REQUIRE(result.success);
    REQUIRE(result.output.find("Node ID") != std::string::npos);
}

TEST_CASE("CLI parses set frequency command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("set freq 300000000");
    REQUIRE(result.success);
}

TEST_CASE("CLI rejects unknown command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("nonexistent");
    REQUIRE_FALSE(result.success);
}

TEST_CASE("CLI parses set power command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("set power 20");
    REQUIRE(result.success);
    REQUIRE(result.output.find("20") != std::string::npos);
}

TEST_CASE("CLI parses net join command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("net join");
    REQUIRE(result.success);
}

TEST_CASE("CLI parses net leave command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("net leave");
    REQUIRE(result.success);
}

TEST_CASE("CLI parses net status command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("net status");
    REQUIRE(result.success);
}

TEST_CASE("CLI parses crypto zeroize command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("crypto zeroize");
    REQUIRE(result.success);
}

TEST_CASE("CLI parses crypto rekey command", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("crypto rekey");
    REQUIRE(result.success);
}

TEST_CASE("CLI handles empty input", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("");
    REQUIRE_FALSE(result.success);
}

TEST_CASE("CLI handles whitespace-only input", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("   ");
    REQUIRE_FALSE(result.success);
}

TEST_CASE("CLI set freq rejects missing argument", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("set freq");
    REQUIRE_FALSE(result.success);
}

TEST_CASE("CLI set freq rejects out-of-range frequency", "[mgmt]") {
    CLIShell cli;
    // Below 225 MHz
    auto result = cli.execute("set freq 100000000");
    REQUIRE_FALSE(result.success);
    // Above 512 MHz
    result = cli.execute("set freq 600000000");
    REQUIRE_FALSE(result.success);
}

TEST_CASE("CLI set power rejects missing argument", "[mgmt]") {
    CLIShell cli;
    auto result = cli.execute("set power");
    REQUIRE_FALSE(result.success);
}
