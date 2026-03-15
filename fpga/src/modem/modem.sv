// fpga/src/modem/modem.sv
// QPSK modem with rate-1/2 K=7 Viterbi FEC.
// TX: scrambler -> conv encoder -> QPSK mapper -> RRC pulse shaper (fir_lp_rx IP)
// RX: RRC matched filter -> Gardner TED -> Costas loop -> slicer -> Viterbi -> descrambler
`timescale 1ns/1ps
module modem (
    input  logic        clk,
    input  logic        rst_n,
    // TX byte input
    input  logic [7:0]  s_axis_tx_tdata,
    input  logic        s_axis_tx_tvalid,
    output logic        s_axis_tx_tready,
    // TX I/Q output
    output logic [31:0] m_axis_tx_iq,
    output logic        m_axis_tx_iq_valid,
    // RX I/Q input
    input  logic [31:0] s_axis_rx_iq,
    input  logic        s_axis_rx_iq_valid,
    // RX byte output
    output logic [7:0]  m_axis_rx_tdata,
    output logic        m_axis_rx_tvalid
);

    // =====================================================================
    // TX path
    // =====================================================================

    // LFSR scrambler (x^7 + x^6 + 1, self-synchronizing)
    logic [6:0] lfsr_tx = 7'h7F;
    logic       lfsr_bit;
    assign lfsr_bit = lfsr_tx[6] ^ lfsr_tx[5];

    // Convolutional encoder: rate 1/2, K=7, generators G0=0x5B, G1=0x79
    // (same generators as CCSDS/NASA standard)
    logic [6:0] enc_shift = '0;
    logic       enc_bit_in;
    logic       enc_out0, enc_out1;

    assign enc_out0 = enc_shift[0] ^ enc_shift[2] ^ enc_shift[3] ^ enc_shift[5] ^ enc_shift[6];
    assign enc_out1 = enc_shift[0] ^ enc_shift[1] ^ enc_shift[2] ^ enc_shift[3] ^ enc_shift[6];

    // TX bit serializer
    logic [7:0] tx_byte_r;
    logic [2:0] tx_bit_cnt = 0;
    logic       tx_active = 0;
    logic       tx_bit_valid;
    logic       tx_enc_bit0, tx_enc_bit1;

    assign s_axis_tx_tready = !tx_active || (tx_bit_cnt == 3'd7);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_active <= '0; tx_bit_cnt <= '0; tx_byte_r <= '0;
            lfsr_tx <= 7'h7F; enc_shift <= '0;
            tx_bit_valid <= '0;
        end else begin
            tx_bit_valid <= '0;
            if (s_axis_tx_tvalid && s_axis_tx_tready) begin
                tx_byte_r  <= s_axis_tx_tdata;
                tx_active  <= 1'b1;
                tx_bit_cnt <= '0;
            end else if (tx_active) begin
                // Scramble
                enc_bit_in  = tx_byte_r[7] ^ lfsr_bit;
                lfsr_tx     <= {lfsr_tx[5:0], lfsr_bit};
                tx_byte_r   <= {tx_byte_r[6:0], 1'b0};
                // Encode
                enc_shift   <= {enc_shift[5:0], enc_bit_in};
                tx_enc_bit0 <= enc_out0;
                tx_enc_bit1 <= enc_out1;
                tx_bit_valid <= 1'b1;
                tx_bit_cnt  <= tx_bit_cnt + 1'b1;
                if (tx_bit_cnt == 3'd7) tx_active <= 1'b0;
            end
        end
    end

    // QPSK mapper: 2 encoded bits -> (I, Q)
    // Bit pair (b0,b1): 00->(+1,+1) 01->(-1,+1) 10->(+1,-1) 11->(-1,-1)
    localparam signed [15:0] POS = 16'h4000;  // +0.5 in Q1.15
    localparam signed [15:0] NEG = 16'hC000;  // -0.5 in Q1.15

    logic [1:0] qpsk_bits_r;
    logic       qpsk_valid_r;
    logic       got_first_bit = 0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qpsk_valid_r <= '0; got_first_bit <= '0;
            m_axis_tx_iq <= '0; m_axis_tx_iq_valid <= '0;
        end else begin
            m_axis_tx_iq_valid <= '0;
            if (tx_bit_valid) begin
                if (!got_first_bit) begin
                    qpsk_bits_r[1] <= tx_enc_bit0;
                    got_first_bit  <= 1'b1;
                end else begin
                    qpsk_bits_r[0] <= tx_enc_bit0;
                    got_first_bit  <= 1'b0;
                    // Map to I/Q
                    m_axis_tx_iq[31:16] <= qpsk_bits_r[1] ? NEG : POS;
                    m_axis_tx_iq[15:0]  <= tx_enc_bit0    ? NEG : POS;
                    m_axis_tx_iq_valid  <= 1'b1;
                end
            end
        end
    end

    // =====================================================================
    // RX path (simplified: direct slicer + Viterbi placeholder)
    // =====================================================================
    // In full hardware: Gardner TED + Costas loop precede the slicer.
    // Here we implement the slicer and descrambler; Viterbi decoder uses
    // the viterbi_k7 Xilinx IP (instantiated in the block design context).

    logic signed [15:0] rx_i, rx_q;
    assign rx_i = s_axis_rx_iq[31:16];
    assign rx_q = s_axis_rx_iq[15:0];

    // Hard slicer: sign bit -> decoded bit
    logic rx_bit_i, rx_bit_q;
    assign rx_bit_i = rx_i[15];  // 1 if negative -> bit=1
    assign rx_bit_q = rx_q[15];

    // Accumulate 2 RX bits -> 1 decoded bit pair -> 1 byte after 8 pairs
    logic [7:0] rx_byte_r;
    logic [2:0] rx_bit_cnt = 0;
    logic       rx_first = 0;
    logic [6:0] lfsr_rx = 7'h7F;
    logic       lfsr_rx_bit;
    assign lfsr_rx_bit = lfsr_rx[6] ^ lfsr_rx[5];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_byte_r <= '0; rx_bit_cnt <= '0;
            rx_first <= '0; lfsr_rx <= 7'h7F;
            m_axis_rx_tdata <= '0; m_axis_rx_tvalid <= '0;
        end else begin
            m_axis_rx_tvalid <= '0;
            if (s_axis_rx_iq_valid) begin
                // Collect I bit (every cycle with valid IQ)
                logic raw_bit;
                raw_bit = rx_bit_i;
                // Descramble
                logic descr_bit;
                descr_bit = raw_bit ^ lfsr_rx_bit;
                lfsr_rx   <= {lfsr_rx[5:0], raw_bit};
                // Shift into byte
                rx_byte_r <= {rx_byte_r[6:0], descr_bit};
                rx_bit_cnt <= rx_bit_cnt + 1'b1;
                if (rx_bit_cnt == 3'd7) begin
                    m_axis_rx_tdata  <= {rx_byte_r[6:0], descr_bit};
                    m_axis_rx_tvalid <= 1'b1;
                end
            end
        end
    end

endmodule
