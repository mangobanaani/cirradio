# fpga/constraints/pinout.xdc
# Stub: pin assignments added per module. See Phase 2 schematic for full pinout.

# AD9361 LVDS interface — pin assignments (replace TBD with values from Phase 2 KiCad schematic)
set_property PACKAGE_PIN TBD [get_ports data_clk_p]
set_property IOSTANDARD LVDS_25 [get_ports data_clk_p]
set_property DIFF_TERM TRUE [get_ports data_clk_p]
set_property PACKAGE_PIN TBD [get_ports rx_frame_p]
set_property IOSTANDARD LVDS_25 [get_ports rx_frame_p]
set_property DIFF_TERM TRUE [get_ports rx_frame_p]
# p0_d_p[5:0], tx_frame_p, p0_tx_p[5:0], fb_clk_p: repeat pattern above with Phase 2 pin numbers
