# fpga/scripts/run_sim.tcl
# Usage: vivado -mode batch -source fpga/scripts/run_sim.tcl -tclargs <tb_module>
# Example: vivado -mode batch -source fpga/scripts/run_sim.tcl -tclargs axi_regs_tb

set tb_name [lindex $argv 0]
if {$tb_name eq ""} {
    puts "ERROR: No testbench specified. Usage: -tclargs <tb_module>"
    exit 1
}

set script_dir [file dirname [file normalize [info script]]]
set proj_dir   "$script_dir/../vivado/cirradio.xpr"

open_project $proj_dir
set_property top $tb_name [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {0ns} -objects [get_filesets sim_1]
launch_simulation
run all
set failed [expr {[get_value -radix unsigned /tb_done] == 0}]
close_sim
if {$failed} {
    puts "SIMULATION FAILED: $tb_name"
    exit 1
}
puts "SIMULATION PASSED: $tb_name"
exit 0
