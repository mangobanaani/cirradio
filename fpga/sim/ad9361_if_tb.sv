// fpga/sim/ad9361_if_tb.sv
`timescale 1ps/1ps
`include "sim_helpers.svh"
module ad9361_if_tb;
    logic fab_clk = 0, fab_rst_n = 0;
    always #5000 fab_clk = ~fab_clk;    // 100 MHz

    logic data_clk = 0;
    always #4069 data_clk = ~data_clk;  // ~122.88 MHz

    logic iserdes_clk = 0, iserdes_clk_div = 0;
    always #2034 iserdes_clk = ~iserdes_clk;
    always #4069 iserdes_clk_div = ~iserdes_clk_div;

    logic data_clk_p, data_clk_n;
    assign data_clk_p = data_clk; assign data_clk_n = ~data_clk;

    logic rx_frame_p, rx_frame_n;
    logic [5:0] p0_d_p, p0_d_n;

    logic [31:0] rx_tdata; logic rx_tvalid, rx_tready = 1;
    logic [31:0] tx_tdata = 0; logic tx_tvalid = 0, tx_tready;
    logic tx_fp, tx_fn; logic [5:0] tx_p, tx_n; logic fb_p, fb_n;

    ad9361_if dut (
        .fabric_clk(fab_clk), .fabric_rst_n(fab_rst_n),
        .data_clk_p(data_clk_p), .data_clk_n(data_clk_n),
        .rx_frame_p(rx_frame_p), .rx_frame_n(rx_frame_n),
        .p0_d_p(p0_d_p), .p0_d_n(p0_d_n),
        .tx_frame_p(tx_fp), .tx_frame_n(tx_fn),
        .p0_tx_p(tx_p), .p0_tx_n(tx_n),
        .fb_clk_p(fb_p), .fb_clk_n(fb_n),
        .m_axis_rx_tdata(rx_tdata), .m_axis_rx_tvalid(rx_tvalid),
        .m_axis_rx_tready(rx_tready),
        .s_axis_tx_tdata(tx_tdata), .s_axis_tx_tvalid(tx_tvalid),
        .s_axis_tx_tready(tx_tready),
        .iserdes_clk(iserdes_clk), .iserdes_clk_div(iserdes_clk_div)
    );

    localparam I_SAMP = 12'hABC;
    localparam Q_SAMP = 12'h123;
    int sample_phase = 0;

    always @(posedge data_clk) begin
        case (sample_phase % 4)
            0: begin p0_d_p <= I_SAMP[11:6]; rx_frame_p <= 1; end
            1: begin p0_d_p <= I_SAMP[5:0];  rx_frame_p <= 1; end
            2: begin p0_d_p <= Q_SAMP[11:6]; rx_frame_p <= 0; end
            3: begin p0_d_p <= Q_SAMP[5:0];  rx_frame_p <= 0; end
        endcase
        sample_phase++;
    end
    always_comb p0_d_n = ~p0_d_p;
    always_comb rx_frame_n = ~rx_frame_p;

    int rx_count = 0;
    always @(posedge fab_clk) begin
        if (rx_tvalid && rx_tready) begin
            `CHECK_EQ(rx_tdata[31:16], 16'(signed'(I_SAMP)), "I sample value");
            `CHECK_EQ(rx_tdata[15:0],  16'(signed'(Q_SAMP)), "Q sample value");
            rx_count++;
        end
    end

    initial begin
        fab_rst_n = 0; #50000; fab_rst_n = 1;
        wait(rx_count >= 100);
        $display("ad9361_if_tb: RX verified %0d samples — PASSED", rx_count);
        $finish;
    end
    initial begin #2000000; $error("TIMEOUT — no RX samples"); $fatal(1); end
endmodule
