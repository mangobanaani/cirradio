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

    // TX path: stub (full TX path via OSERDESE2 after hardware bring-up)
    assign s_axis_tx_tready = 1'b1;
    assign tx_frame_p = 1'b0; assign tx_frame_n = 1'b1;
    assign p0_tx_p    = 6'b0; assign p0_tx_n    = 6'b111111;
    assign fb_clk_p   = 1'b0; assign fb_clk_n   = 1'b1;

endmodule
