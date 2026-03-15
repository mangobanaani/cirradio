// fpga/sim/channelizer_tb.sv
`timescale 1ns/1ps
`include "sim_helpers.svh"
module channelizer_tb;
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    logic [31:0] s_axis_tdata;
    logic        s_axis_tvalid;
    logic        s_axis_tready;
    logic [31:0] m_axis_tdata;
    logic        m_axis_tvalid;
    logic        m_axis_tready = 1;
    logic [5:0]  decim_rate;

    channelizer dut (.*);

    int tx_count = 0, rx_count = 0;

    always @(posedge clk) begin
        if (s_axis_tvalid && s_axis_tready) tx_count++;
    end
    always @(posedge clk) begin
        if (m_axis_tvalid && m_axis_tready) rx_count++;
    end

    initial begin
        rst_n = 0; decim_rate = 4; `WAIT_CYCLES(4); rst_n = 1;

        // Feed 4000 input samples at full rate
        s_axis_tvalid = 1;
        s_axis_tdata = 32'h0FFF_0FFF;
        repeat(4000) @(posedge clk iff s_axis_tready);
        s_axis_tvalid = 0;
        `WAIT_CYCLES(100);

        // At 4x decimation, expect ~1000 output samples
        `CHECK(rx_count >= 950 && rx_count <= 1050,
               "DDC output rate = input/4 within 5%");

        $display("channelizer_tb: PASSED (in=%0d out=%0d decim=4)", tx_count, rx_count);
        $finish;
    end
    initial begin #500000; $error("TIMEOUT"); $fatal(1); end
endmodule
