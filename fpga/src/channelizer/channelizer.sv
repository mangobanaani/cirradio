// fpga/src/channelizer/channelizer.sv
// DDC/DUC top: wraps Xilinx FIR Compiler fir_lp_rx IP for decimation.
// decim_rate is passed to FIR Compiler configuration (hardcoded at 4x in IP).
`timescale 1ns/1ps
module channelizer (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] s_axis_tdata,
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    output logic [31:0] m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    input  logic [5:0]  decim_rate      // informational; FIR IP is fixed at 4x
);
    // Instantiate Xilinx FIR Compiler IP (fir_lp_rx): Decimation mode, 4x
    // AXI4-Stream slave (input) -> AXI4-Stream master (decimated output)
    fir_lp_rx fir_inst (
        .aclk               (clk),
        .s_axis_data_tvalid (s_axis_tvalid),
        .s_axis_data_tready (s_axis_tready),
        .s_axis_data_tdata  (s_axis_tdata),
        .m_axis_data_tvalid (m_axis_tvalid),
        .m_axis_data_tready (m_axis_tready),
        .m_axis_data_tdata  (m_axis_tdata)
    );
endmodule
