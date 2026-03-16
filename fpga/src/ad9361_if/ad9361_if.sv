// fpga/src/ad9361_if/ad9361_if.sv
`timescale 1ns/1ps
module ad9361_if (
    input  logic        fabric_clk,
    input  logic        fabric_rst_n,
    input  logic        data_clk_p, data_clk_n,
    input  logic        rx_frame_p, rx_frame_n,
    input  logic [5:0]  p0_d_p,    p0_d_n,
    output logic        tx_frame_p, tx_frame_n,
    output logic [5:0]  p0_tx_p,   p0_tx_n,
    output logic        fb_clk_p,  fb_clk_n,
    output logic [31:0] m_axis_rx_tdata,
    output logic        m_axis_rx_tvalid,
    input  logic        m_axis_rx_tready,
    input  logic [31:0] s_axis_tx_tdata,
    input  logic        s_axis_tx_tvalid,
    output logic        s_axis_tx_tready,
    input  logic        iserdes_clk,
    input  logic        iserdes_clk_div
);
    // RX: IBUFDS -> ISERDESE2 for DATA_CLK
    logic data_clk_int;
    IBUFDS #(.DIFF_TERM("TRUE"), .IOSTANDARD("LVDS_25"))
        ibuf_clk (.O(data_clk_int), .I(data_clk_p), .IB(data_clk_n));

    logic rx_frame_ser;
    IBUFDS #(.DIFF_TERM("TRUE"), .IOSTANDARD("LVDS_25"))
        ibuf_rxf (.O(rx_frame_ser), .I(rx_frame_p), .IB(rx_frame_n));

    // ISERDESE2 for each data bit: DDR -> 2 parallel bits per clk
    logic [5:0] p0_d_rise, p0_d_fall;
    genvar b;
    generate
        for (b = 0; b < 6; b++) begin : gen_iserdes
            logic p0_d_int;
            IBUFDS #(.DIFF_TERM("TRUE"), .IOSTANDARD("LVDS_25"))
                ibuf_d (.O(p0_d_int), .I(p0_d_p[b]), .IB(p0_d_n[b]));
            ISERDESE2 #(
                .DATA_RATE("DDR"), .DATA_WIDTH(4),
                .INTERFACE_TYPE("NETWORKING"),
                .IOBDELAY("NONE"), .NUM_CE(1)
            ) iserdes_inst (
                .O(),
                .Q1(p0_d_rise[b]), .Q2(p0_d_fall[b]),
                .Q3(), .Q4(), .Q5(), .Q6(), .Q7(), .Q8(),
                .SHIFTOUT1(), .SHIFTOUT2(),
                .D(p0_d_int), .DDLY(),
                .CLK(iserdes_clk), .CLKB(~iserdes_clk),
                .CLKDIV(iserdes_clk_div),
                .OCLK(), .OCLKB(),
                .RST(!fabric_rst_n), .CE1(1'b1), .CE2(1'b0),
                .BITSLIP(1'b0),
                .DYNCLKDIVSEL(1'b0), .DYNCLKSEL(1'b0),
                .OFB(), .SHIFTIN1(1'b0), .SHIFTIN2(1'b0)
            );
        end
    endgenerate

    // RX_FRAME ISERDESE2
    logic rx_frame_rise, rx_frame_fall;
    ISERDESE2 #(
        .DATA_RATE("DDR"), .DATA_WIDTH(4),
        .INTERFACE_TYPE("NETWORKING"),
        .IOBDELAY("NONE"), .NUM_CE(1)
    ) iserdes_rxf (
        .O(),
        .Q1(rx_frame_rise), .Q2(rx_frame_fall),
        .Q3(), .Q4(), .Q5(), .Q6(), .Q7(), .Q8(),
        .SHIFTOUT1(), .SHIFTOUT2(),
        .D(rx_frame_ser), .DDLY(),
        .CLK(iserdes_clk), .CLKB(~iserdes_clk),
        .CLKDIV(iserdes_clk_div),
        .OCLK(), .OCLKB(),
        .RST(!fabric_rst_n), .CE1(1'b1), .CE2(1'b0),
        .BITSLIP(1'b0),
        .DYNCLKDIVSEL(1'b0), .DYNCLKSEL(1'b0),
        .OFB(), .SHIFTIN1(1'b0), .SHIFTIN2(1'b0)
    );

    // Reconstruct 12-bit I/Q: {rise[5:0], fall[5:0]}
    logic [11:0] raw_sample;
    assign raw_sample = {p0_d_rise, p0_d_fall};

    // I/Q demux using RX_FRAME
    logic [11:0] i_sample_r, q_sample_r;
    logic        sample_valid_r;
    always_ff @(posedge iserdes_clk_div or negedge fabric_rst_n) begin
        if (!fabric_rst_n) begin
            i_sample_r <= '0; q_sample_r <= '0; sample_valid_r <= '0;
        end else begin
            sample_valid_r <= '0;
            if (rx_frame_rise) begin
                i_sample_r <= raw_sample;
            end else begin
                q_sample_r     <= raw_sample;
                sample_valid_r <= 1'b1;
            end
        end
    end

    // XPM FIFO: DATA_CLK domain -> fabric clock domain
    logic fifo_empty;
    xpm_fifo_async #(
        .FIFO_WRITE_DEPTH(16), .WRITE_DATA_WIDTH(32),
        .READ_DATA_WIDTH(32),  .READ_MODE("FWFT"),
        .FIFO_MEMORY_TYPE("BRAM")
    ) fifo_rx (
        .wr_clk(iserdes_clk_div),
        .wr_en(sample_valid_r),
        .din({i_sample_r, q_sample_r}),
        .rd_clk(fabric_clk),
        .rd_en(m_axis_rx_tready && m_axis_rx_tvalid),
        .dout(m_axis_rx_tdata),
        .empty(fifo_empty),
        .full(),
        .rd_data_count(), .wr_data_count(),
        .prog_empty_thresh('0), .prog_full_thresh('0),
        .injectsbiterr('0), .injectdbiterr('0),
        .rst(!fabric_rst_n), .rd_rst_busy(), .wr_rst_busy(),
        .sbiterr(), .dbiterr()
    );
    assign m_axis_rx_tvalid = !fifo_empty;

    // =========================================================================
    // TX path: fabric clock domain -> DATA_CLK domain -> OSERDESE2 -> OBUFDS
    // =========================================================================
    // XPM FIFO: fabric clock domain -> DATA_CLK (iserdes_clk_div) domain
    logic [31:0] tx_fifo_dout;
    logic        tx_fifo_empty, tx_fifo_rd_en;
    logic        tx_fifo_valid_r;

    xpm_fifo_async #(
        .FIFO_WRITE_DEPTH(16), .WRITE_DATA_WIDTH(32),
        .READ_DATA_WIDTH(32),  .READ_MODE("FWFT"),
        .FIFO_MEMORY_TYPE("BRAM")
    ) fifo_tx (
        .wr_clk(fabric_clk),
        .wr_en(s_axis_tx_tvalid && s_axis_tx_tready),
        .din(s_axis_tx_tdata),
        .rd_clk(iserdes_clk_div),
        .rd_en(tx_fifo_rd_en),
        .dout(tx_fifo_dout),
        .empty(tx_fifo_empty),
        .full(),
        .rd_data_count(), .wr_data_count(),
        .prog_empty_thresh('0), .prog_full_thresh('0),
        .injectsbiterr('0), .injectdbiterr('0),
        .rst(!fabric_rst_n), .rd_rst_busy(), .wr_rst_busy(),
        .sbiterr(), .dbiterr()
    );
    assign s_axis_tx_tready = 1'b1;  // fabric side always accepts

    // TX serialiser state machine (DATA_CLK domain, iserdes_clk_div)
    // Each IQ sample (32 bits = 16b I + 16b Q) is sent as:
    //   Phase 0: I[11:6]  tx_frame=1  (I word, upper 6 bits)
    //   Phase 1: I[5:0]   tx_frame=1  (I word, lower 6 bits)
    //   Phase 2: Q[11:6]  tx_frame=0  (Q word, upper 6 bits)
    //   Phase 3: Q[5:0]   tx_frame=0  (Q word, lower 6 bits)
    logic [1:0] tx_phase = 0;
    logic [11:0] tx_i_reg, tx_q_reg;
    logic [5:0]  tx_data_ser;
    logic        tx_frame_ser;
    logic        tx_sample_active = 0;

    assign tx_fifo_rd_en = !tx_fifo_empty && (tx_phase == 2'd0) && !tx_sample_active;

    always_ff @(posedge iserdes_clk_div or negedge fabric_rst_n) begin
        if (!fabric_rst_n) begin
            tx_phase         <= '0;
            tx_i_reg         <= '0; tx_q_reg <= '0;
            tx_data_ser      <= '0; tx_frame_ser <= '0;
            tx_sample_active <= '0;
        end else begin
            case (tx_phase)
                2'd0: begin
                    if (!tx_fifo_empty) begin
                        tx_i_reg         <= tx_fifo_dout[31:20];  // upper 12 bits = I
                        tx_q_reg         <= tx_fifo_dout[15:4];   // lower 12 bits = Q
                        tx_data_ser      <= tx_fifo_dout[31:26];  // I[11:6]
                        tx_frame_ser     <= 1'b1;
                        tx_sample_active <= 1'b1;
                        tx_phase         <= 2'd1;
                    end
                end
                2'd1: begin
                    tx_data_ser  <= tx_i_reg[5:0];
                    tx_frame_ser <= 1'b1;
                    tx_phase     <= 2'd2;
                end
                2'd2: begin
                    tx_data_ser  <= tx_q_reg[11:6];
                    tx_frame_ser <= 1'b0;
                    tx_phase     <= 2'd3;
                end
                2'd3: begin
                    tx_data_ser      <= tx_q_reg[5:0];
                    tx_frame_ser     <= 1'b0;
                    tx_sample_active <= 1'b0;
                    tx_phase         <= 2'd0;
                end
            endcase
        end
    end

    // OSERDESE2: single-rate (SDR) output per iserdes_clk_div tick
    // AD9361 DDR LVDS: each DATA_CLK edge carries 6 data bits.
    // We output 6 bits per iserdes_clk_div cycle (SDR at half DATA_CLK rate).
    genvar t;
    generate
        for (t = 0; t < 6; t++) begin : gen_oserdes
            logic tx_bit_p, tx_bit_n;
            OSERDESE2 #(
                .DATA_RATE_OQ("SDR"), .DATA_RATE_TQ("SDR"),
                .DATA_WIDTH(4), .SERDES_MODE("MASTER"),
                .TRISTATE_WIDTH(1)
            ) oserdes_inst (
                .OQ(tx_bit_p),
                .D1(tx_data_ser[t]), .D2(1'b0), .D3(1'b0), .D4(1'b0),
                .D5(1'b0), .D6(1'b0), .D7(1'b0), .D8(1'b0),
                .T1(1'b0), .T2(1'b0), .T3(1'b0), .T4(1'b0),
                .TCE(1'b0), .OCE(1'b1),
                .CLK(iserdes_clk), .CLKDIV(iserdes_clk_div),
                .RST(!fabric_rst_n),
                .SHIFTIN1(1'b0), .SHIFTIN2(1'b0),
                .SHIFTOUT1(), .SHIFTOUT2(),
                .OFB(), .TFB(), .TQ()
            );
            OBUFDS #(.IOSTANDARD("LVDS_25"))
                obuf_d (.O(p0_tx_p[t]), .OB(p0_tx_n[t]), .I(tx_bit_p));
        end
    endgenerate

    // TX_FRAME OSERDESE2 + OBUFDS
    logic tx_frame_out;
    OSERDESE2 #(
        .DATA_RATE_OQ("SDR"), .DATA_RATE_TQ("SDR"),
        .DATA_WIDTH(4), .SERDES_MODE("MASTER"),
        .TRISTATE_WIDTH(1)
    ) oserdes_frame (
        .OQ(tx_frame_out),
        .D1(tx_frame_ser), .D2(1'b0), .D3(1'b0), .D4(1'b0),
        .D5(1'b0), .D6(1'b0), .D7(1'b0), .D8(1'b0),
        .T1(1'b0), .T2(1'b0), .T3(1'b0), .T4(1'b0),
        .TCE(1'b0), .OCE(1'b1),
        .CLK(iserdes_clk), .CLKDIV(iserdes_clk_div),
        .RST(!fabric_rst_n),
        .SHIFTIN1(1'b0), .SHIFTIN2(1'b0),
        .SHIFTOUT1(), .SHIFTOUT2(),
        .OFB(), .TFB(), .TQ()
    );
    OBUFDS #(.IOSTANDARD("LVDS_25"))
        obuf_txf (.O(tx_frame_p), .OB(tx_frame_n), .I(tx_frame_out));

    // FB_CLK: loopback of DATA_CLK to AD9361 for TX timing alignment
    logic fb_clk_out;
    ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0))
        oddr_fb (.Q(fb_clk_out), .C(iserdes_clk_div),
                 .CE(1'b1), .D1(1'b1), .D2(1'b0), .R(1'b0), .S(1'b0));
    OBUFDS #(.IOSTANDARD("LVDS_25"))
        obuf_fb (.O(fb_clk_p), .OB(fb_clk_n), .I(fb_clk_out));

endmodule
