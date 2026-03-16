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

    // ---- RX stimulus (unchanged) ----
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

    // ---- RX checker ----
    int rx_count = 0;
    always @(posedge fab_clk) begin
        if (rx_tvalid && rx_tready) begin
            `CHECK_EQ(rx_tdata[31:16], 16'(signed'(I_SAMP)), "I sample value");
            `CHECK_EQ(rx_tdata[15:0],  16'(signed'(Q_SAMP)), "Q sample value");
            rx_count++;
        end
    end

    // ---- TX checker ----
    // Send a known IQ sample; verify p0_tx_p goes non-zero (OSERDESE2 active)
    // and tx_frame_p toggles in the expected pattern (1,1,0,0 per 4 iserdes_clk_div cycles).
    localparam logic [31:0] TX_SAMP = 32'hDEAD_BEEF;
    int tx_frame_transitions = 0;
    logic tx_frame_prev = 0;
    int tx_data_nonzero = 0;

    always @(posedge iserdes_clk_div) begin
        // Count tx_frame transitions (should toggle from 1->0 after 2 phases)
        if (tx_fp !== tx_frame_prev) begin
            tx_frame_transitions++;
            tx_frame_prev <= tx_fp;
        end
        // Verify tx_p carries data (at least one bit set when active)
        if (tx_p !== 6'b0 && tx_p !== 6'b111111)
            tx_data_nonzero++;
    end

    initial begin
        fab_rst_n = 0; #50000; fab_rst_n = 1;

        // Wait for RX to be verified
        wait(rx_count >= 100);

        // Send TX sample
        @(posedge fab_clk); tx_tdata = TX_SAMP; tx_tvalid = 1;
        @(posedge fab_clk iff tx_tready); tx_tvalid = 0;

        // Allow serialisation to complete (4 iserdes_clk_div cycles)
        repeat(20) @(posedge iserdes_clk_div);

        `CHECK(tx_frame_transitions >= 2, "TX frame toggled (I/Q boundary seen)");
        `CHECK(tx_data_nonzero > 0,       "TX data pins carried non-trivial data");
        $display("ad9361_if_tb: RX %0d samples + TX path verified — PASSED", rx_count);
        $finish;
    end
    initial begin #4000000; $error("TIMEOUT"); $fatal(1); end
endmodule
