// fpga/sim/sim_helpers.svh
`ifndef SIM_HELPERS_SVH
`define SIM_HELPERS_SVH

// Fail simulation with message and location
`define CHECK(cond, msg) \
  if (!(cond)) begin \
    $error("%s:%0d CHECK FAILED: %s", `__FILE__, `__LINE__, msg); \
    $fatal(1); \
  end

// Check register value
`define CHECK_EQ(actual, expected, msg) \
  if ((actual) !== (expected)) begin \
    $error("%s:%0d MISMATCH: %s  actual=0x%08X expected=0x%08X", \
           `__FILE__, `__LINE__, msg, actual, expected); \
    $fatal(1); \
  end

// Wait N rising edges of clk
`define WAIT_CYCLES(n) repeat(n) @(posedge clk)

`endif
