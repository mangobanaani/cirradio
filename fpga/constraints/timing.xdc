# fpga/constraints/timing.xdc
# Primary clocks - defined here; module-specific constraints added per-task
create_clock -period 30.000 -name PS_CLK [get_ports PS_CLK]
# DATA_CLK from AD9361 is defined after ad9361_if instantiation
# set_false_path between fabric and DATA_CLK domains (async FIFO handles CDC)
