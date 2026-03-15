# fpga/scripts/create_project.tcl
# Usage: vivado -mode batch -source fpga/scripts/create_project.tcl

set script_dir [file dirname [file normalize [info script]]]
set root_dir   [file normalize "$script_dir/../.."]
set proj_dir   "$root_dir/fpga/vivado"

# Remove old project if it exists
file delete -force $proj_dir

create_project cirradio $proj_dir -part xc7z045ffg900-2
set_property target_language SystemVerilog [current_project]
set_property simulator_language Mixed [current_project]

# Add RTL sources (fpga/src/ is one level deep: src/<module>/*.sv)
# Note: Tcl 8.6 glob does not support **, use single wildcard
set sv_files [glob -nocomplain "$root_dir/fpga/src/*/*.sv"]
if {[llength $sv_files] > 0} {
    add_files -norecurse $sv_files
}
set_property file_type SystemVerilog [get_files *.sv]

# Add include files
set svh_files [glob -nocomplain "$root_dir/fpga/src/*/*.svh" \
                                "$root_dir/fpga/sim/*.svh"]
if {[llength $svh_files] > 0} {
    add_files -norecurse $svh_files
}

# Add simulation files
set sim_files [glob -nocomplain "$root_dir/fpga/sim/*_tb.sv"]
if {[llength $sim_files] > 0} {
    add_files -fileset sim_1 -norecurse $sim_files
}

# Add constraints
add_files -fileset constrs_1 -norecurse \
    "$root_dir/fpga/constraints/pinout.xdc" \
    "$root_dir/fpga/constraints/timing.xdc"

# ---- Xilinx IP Instances ----

# XPM libraries (built-in, no separate IP needed)
set_property -name {xpm_libraries} -value {XPM_FIFO XPM_MEMORY XPM_CDC} \
    -objects [current_project]

# FIR Compiler for RX low-pass (DDC)
create_ip -name fir_compiler -vendor xilinx.com -library ip \
          -version 7.2 -module_name fir_lp_rx
set_property -dict [list \
    CONFIG.CoefficientVector {0.001 0.005 0.015 0.035 0.070 0.120 0.175 0.215 0.230 0.215 0.175 0.120 0.070 0.035 0.015 0.005 0.001} \
    CONFIG.Decimation_Rate {4} \
    CONFIG.Filter_Type {Decimation} \
    CONFIG.Number_of_Channels {1} \
    CONFIG.Output_Rounding_Mode {Convergent_Rounding_to_Even} \
    CONFIG.Output_Width {24} \
] [get_ips fir_lp_rx]

# Viterbi Decoder (rate 1/2, K=7, soft-decision)
create_ip -name viterbi_v8_0 -vendor xilinx.com -library ip \
          -version 8.0 -module_name viterbi_k7
set_property -dict [list \
    CONFIG.Code_Rate {1/2} \
    CONFIG.Constraint_Length {7} \
    CONFIG.Soft_Input {true} \
    CONFIG.Decision_Type {Traceback} \
    CONFIG.Traceback_Depth {35} \
] [get_ips viterbi_k7]

# AXI DMA
create_ip -name axi_dma -vendor xilinx.com -library ip \
          -version 7.1 -module_name axi_dma_iq
set_property -dict [list \
    CONFIG.c_include_sg {0} \
    CONFIG.c_sg_length_width {26} \
    CONFIG.c_m_axi_mm2s_data_width {64} \
    CONFIG.c_m_axi_s2mm_data_width {64} \
] [get_ips axi_dma_iq]

# AXI GPIO (T/R switch, PA enable, LEDs)
create_ip -name axi_gpio -vendor xilinx.com -library ip \
          -version 2.0 -module_name axi_gpio_rf
set_property -dict [list \
    CONFIG.C_GPIO_WIDTH {8} \
    CONFIG.C_ALL_OUTPUTS {1} \
] [get_ips axi_gpio_rf]

# AXI Timer (slot timing)
create_ip -name axi_timer -vendor xilinx.com -library ip \
          -version 2.0 -module_name axi_timer_slot

# AXI Interconnect
create_ip -name axi_interconnect -vendor xilinx.com -library ip \
          -version 1.7 -module_name axi_ic
set_property -dict [list \
    CONFIG.NUM_SI {1} \
    CONFIG.NUM_MI {4} \
] [get_ips axi_ic]

# AXI VIP (for simulation -- PS master model)
create_ip -name axi_vip -vendor xilinx.com -library ip \
          -version 1.1 -module_name axi_vip_mst
set_property -dict [list \
    CONFIG.INTERFACE_MODE {MASTER} \
    CONFIG.PROTOCOL {AXI4LITE} \
] [get_ips axi_vip_mst]
set_property used_in_synthesis false [get_files axi_vip_mst.xci]

# TODO (Task 6, fhss_engine): Add Xilinx Security AES-256 IP here.
# Requires a Vivado Encryption license (not included in WebPACK/Standard).
# Verify license availability before attempting fhss_engine tasks.
# If unlicensed, substitute an open-source AES-256-ECB core (e.g. secworks/aes).

# Generate all IP output products
generate_target all [get_ips]
export_ip_user_files -of_objects [get_ips] -no_script -sync -force

puts "Project created at $proj_dir"
puts "Next: open in Vivado GUI to create block design, then run run_sim.tcl"
