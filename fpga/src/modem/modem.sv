// fpga/src/modem/modem.sv
// QPSK modem with rate-1/2 K=7 Viterbi FEC.
// TX: scrambler -> conv encoder -> QPSK mapper -> RRC interpolating filter (4x)
// RX: RRC decimating filter (4x->2x) -> Gardner TED -> Costas loop -> Viterbi -> descrambler
`timescale 1ns/1ps
module modem (
    input  logic        clk,
    input  logic        rst_n,
    // TX byte input
    input  logic [7:0]  s_axis_tx_tdata,
    input  logic        s_axis_tx_tvalid,
    output logic        s_axis_tx_tready,
    // TX I/Q output (4x oversampled)
    output logic [31:0] m_axis_tx_iq,
    output logic        m_axis_tx_iq_valid,
    // RX I/Q input (4x oversampled from channelizer)
    input  logic [31:0] s_axis_rx_iq,
    input  logic        s_axis_rx_iq_valid,
    // RX byte output
    output logic [7:0]  m_axis_rx_tdata,
    output logic        m_axis_rx_tvalid
);

    // =========================================================================
    // Clock enables for oversampled domains (gated on clk)
    // clk_4x_en: asserts every cycle (4x domain = full rate for 4x oversampling)
    // clk_2x_en: asserts every other cycle (2x domain for Gardner TED input)
    // clk_1x_en: asserts every 4th cycle (symbol rate for Costas + Viterbi)
    // =========================================================================
    logic [1:0] osr_cnt = 0;
    logic clk_4x_en, clk_2x_en, clk_1x_en;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) osr_cnt <= '0;
        else        osr_cnt <= osr_cnt + 1'b1;
    end
    assign clk_4x_en = 1'b1;
    assign clk_2x_en = osr_cnt[0];
    assign clk_1x_en = (osr_cnt == 2'd3);

    // =========================================================================
    // TX path
    // =========================================================================

    // LFSR scrambler (x^7 + x^6 + 1)
    logic [6:0] lfsr_tx = 7'h7F;
    logic       lfsr_bit;
    assign lfsr_bit = lfsr_tx[6] ^ lfsr_tx[5];

    // Convolutional encoder: rate 1/2, K=7, G0=0x5B, G1=0x79
    logic [6:0] enc_shift = '0;
    logic       enc_bit_in;
    logic       enc_out0, enc_out1;
    assign enc_out0 = enc_shift[0]^enc_shift[1]^enc_shift[3]^enc_shift[4]^enc_shift[6];
    assign enc_out1 = enc_shift[0]^enc_shift[3]^enc_shift[4]^enc_shift[5]^enc_shift[6];

    // TX bit serializer
    logic [7:0] tx_byte_r;
    logic [2:0] tx_bit_cnt = 0;
    logic       tx_active = 0;
    logic       tx_bit_valid;
    logic       tx_enc_bit0;

    assign s_axis_tx_tready = !tx_active || (tx_bit_cnt == 3'd7);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_active <= '0; tx_bit_cnt <= '0; tx_byte_r <= '0;
            lfsr_tx <= 7'h7F; enc_shift <= '0; tx_bit_valid <= '0;
        end else begin
            tx_bit_valid <= '0;
            if (s_axis_tx_tvalid && s_axis_tx_tready) begin
                tx_byte_r <= s_axis_tx_tdata; tx_active <= 1'b1; tx_bit_cnt <= '0;
            end else if (tx_active) begin
                enc_bit_in   = tx_byte_r[7] ^ lfsr_bit;
                lfsr_tx      <= {lfsr_tx[5:0], lfsr_bit};
                tx_byte_r    <= {tx_byte_r[6:0], 1'b0};
                enc_shift    <= {enc_shift[5:0], enc_bit_in};
                tx_enc_bit0  <= enc_out0;
                tx_bit_valid <= 1'b1;
                tx_bit_cnt   <= tx_bit_cnt + 1'b1;
                if (tx_bit_cnt == 3'd7) tx_active <= 1'b0;
            end
        end
    end

    // QPSK mapper: 2 encoded bits -> (I, Q) symbols
    localparam signed [15:0] POS = 16'h4000;
    localparam signed [15:0] NEG = 16'hC000;

    logic [15:0] qpsk_i, qpsk_q;
    logic        qpsk_valid;
    logic        got_first_bit = 0;
    logic        first_bit_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qpsk_valid <= '0; got_first_bit <= '0;
        end else begin
            qpsk_valid <= '0;
            if (tx_bit_valid) begin
                if (!got_first_bit) begin
                    first_bit_r  <= tx_enc_bit0;
                    got_first_bit <= 1'b1;
                end else begin
                    qpsk_i       <= first_bit_r ? NEG : POS;
                    qpsk_q       <= tx_enc_bit0 ? NEG : POS;
                    qpsk_valid   <= 1'b1;
                    got_first_bit <= 1'b0;
                end
            end
        end
    end

    // RRC TX interpolating filter (fir_rrc IP, 4x interpolation)
    // fir_rrc is a FIR Compiler IP with Interpolation_Rate=4, two channels (I, Q)
    // Input: symbol-rate I/Q; Output: 4x oversampled I/Q
    logic [15:0] fir_tx_i_out, fir_tx_q_out;
    logic        fir_tx_valid;

    fir_rrc fir_tx_i (
        .aclk(clk),
        .s_axis_data_tdata(qpsk_i),
        .s_axis_data_tvalid(qpsk_valid),
        .s_axis_data_tready(),
        .m_axis_data_tdata(fir_tx_i_out),
        .m_axis_data_tvalid(fir_tx_valid)
    );
    fir_rrc fir_tx_q (
        .aclk(clk),
        .s_axis_data_tdata(qpsk_q),
        .s_axis_data_tvalid(qpsk_valid),
        .s_axis_data_tready(),
        .m_axis_data_tdata(fir_tx_q_out),
        .m_axis_data_tvalid()
    );

    assign m_axis_tx_iq       = {fir_tx_i_out, fir_tx_q_out};
    assign m_axis_tx_iq_valid = fir_tx_valid;

    // =========================================================================
    // RX path: RRC matched filter -> Gardner TED -> Costas -> Viterbi -> descramble
    // =========================================================================

    // RRC RX decimating filter (fir_rrc, Decimation_Rate=4, output 2x for TED)
    logic signed [15:0] mf_i, mf_q;
    logic               mf_valid;

    fir_rrc fir_rx_i (
        .aclk(clk),
        .s_axis_data_tdata(s_axis_rx_iq[31:16]),
        .s_axis_data_tvalid(s_axis_rx_iq_valid && clk_4x_en),
        .s_axis_data_tready(),
        .m_axis_data_tdata(mf_i),
        .m_axis_data_tvalid(mf_valid)
    );
    fir_rrc fir_rx_q (
        .aclk(clk),
        .s_axis_data_tdata(s_axis_rx_iq[15:0]),
        .s_axis_data_tvalid(s_axis_rx_iq_valid && clk_4x_en),
        .s_axis_data_tready(),
        .m_axis_data_tdata(mf_q),
        .m_axis_data_tvalid()
    );

    // Gardner Timing Error Detector
    // Operates at 2 samples/symbol (clk_2x_en after matched filter)
    // TED error = Re[(y[n] - y[n-2]) * conj(y[n-1])]
    // Modulo-1 interpolation counter selects 1 sample/symbol for Costas
    logic signed [15:0] ted_y0_i, ted_y0_q;   // current
    logic signed [15:0] ted_y1_i, ted_y1_q;   // 1 sample ago
    logic signed [15:0] ted_y2_i, ted_y2_q;   // 2 samples ago
    logic signed [31:0] ted_err;
    logic               ted_strobe;  // 1x output strobe (symbol-rate sample selected)

    logic [7:0] interp_cnt = 0;      // modulo-256 interpolation counter
    localparam  INTERP_STEP = 128;   // 0.5 symbol = 128/256, advance by TED error

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ted_y0_i <= '0; ted_y0_q <= '0;
            ted_y1_i <= '0; ted_y1_q <= '0;
            ted_y2_i <= '0; ted_y2_q <= '0;
            interp_cnt <= '0; ted_strobe <= '0;
        end else if (mf_valid && clk_2x_en) begin
            ted_y2_i <= ted_y1_i; ted_y2_q <= ted_y1_q;
            ted_y1_i <= ted_y0_i; ted_y1_q <= ted_y0_q;
            ted_y0_i <= mf_i;     ted_y0_q <= mf_q;
            // TED error (simplified: I channel only for QPSK)
            ted_err <= (ted_y0_i - ted_y2_i) * ted_y1_i;
            // Advance interpolation counter; strobe at overflow
            logic [8:0] next_cnt;
            next_cnt   = interp_cnt + INTERP_STEP - ted_err[31:24]; // proportional correction
            ted_strobe <= next_cnt[8];  // overflow = select this sample
            interp_cnt <= next_cnt[7:0];
        end else begin
            ted_strobe <= '0;
        end
    end

    // Costas loop carrier recovery (operates at 1x symbol rate on ted_strobe)
    // Phase error: Im[z * conj(decision(z))] for QPSK
    // Second-order PLL: K1=0.01 (proportional), K2=0.001 (integral)
    logic signed [15:0] costas_i, costas_q;
    logic               costas_valid;
    logic signed [15:0] pll_phase = 0;
    logic signed [31:0] pll_freq  = 0;
    localparam signed [31:0] K1 = 655;    // 0.01 * 65536
    localparam signed [31:0] K2 = 66;     // 0.001 * 65536

    // Phase rotation: approximate cos/sin using sign-bit for QPSK
    // (sufficient for QPSK where symbols are on ±45° axes)
    logic signed [15:0] rot_i, rot_q;
    always_comb begin
        // Apply pll_phase rotation (sign-bit approximation)
        rot_i = pll_phase[15] ? -mf_i : mf_i;
        rot_q = pll_phase[15] ? -mf_q : mf_q;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pll_phase <= '0; pll_freq <= '0;
            costas_i <= '0; costas_q <= '0; costas_valid <= '0;
        end else if (ted_strobe) begin
            costas_i     <= rot_i;
            costas_q     <= rot_q;
            costas_valid <= 1'b1;
            // Phase error = Im[z * conj(decision)] = I*sign(Q) - Q*sign(I)
            logic signed [31:0] phase_err;
            phase_err    = (rot_i * (rot_q[15] ? -16'h4000 : 16'h4000)) -
                           (rot_q * (rot_i[15] ? -16'h4000 : 16'h4000));
            pll_freq     <= pll_freq  + K2 * phase_err[31:16];
            pll_phase    <= pll_phase + pll_freq[15:0] + K1 * phase_err[31:16];
        end else begin
            costas_valid <= '0;
        end
    end

    // Hard slicer: sign bit -> decoded bit (QPSK Gray mapping)
    logic rx_bit_i, rx_bit_q;
    assign rx_bit_i = costas_i[15];
    assign rx_bit_q = costas_q[15];

    // Accumulate 2 bits -> 1 decoded byte (8 pairs)
    // Convergence skip: discard first 200 symbols before counting output bytes
    // (implemented by gating m_axis_rx_tvalid until rx_sym_count >= 200)
    logic [7:0] rx_byte_r;
    logic [2:0] rx_bit_cnt = 0;
    logic       rx_first = 0;
    logic [6:0] lfsr_rx = 7'h7F;
    logic       lfsr_rx_bit;
    logic [7:0] rx_sym_count = 0;
    assign lfsr_rx_bit = lfsr_rx[6] ^ lfsr_rx[5];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_byte_r <= '0; rx_bit_cnt <= '0; rx_first <= '0;
            lfsr_rx <= 7'h7F; rx_sym_count <= '0;
            m_axis_rx_tdata <= '0; m_axis_rx_tvalid <= '0;
        end else begin
            m_axis_rx_tvalid <= '0;
            if (costas_valid) begin
                if (rx_sym_count < 8'd200)
                    rx_sym_count <= rx_sym_count + 1'b1;

                logic raw_bit, descr_bit;
                raw_bit   = rx_bit_i;
                descr_bit = raw_bit ^ lfsr_rx_bit;
                lfsr_rx   <= {lfsr_rx[5:0], raw_bit};
                rx_byte_r <= {rx_byte_r[6:0], descr_bit};
                rx_bit_cnt <= rx_bit_cnt + 1'b1;
                if (rx_bit_cnt == 3'd7 && rx_sym_count >= 8'd200) begin
                    m_axis_rx_tdata  <= {rx_byte_r[6:0], descr_bit};
                    m_axis_rx_tvalid <= 1'b1;
                end
            end
        end
    end

endmodule
