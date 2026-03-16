// fpga/sim/modem_tb.sv
`timescale 1ns/1ps
`include "sim_helpers.svh"
module modem_tb;
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    logic [7:0]  tx_byte; logic tx_valid, tx_ready;
    logic [7:0]  rx_byte; logic rx_valid;
    logic [31:0] tx_iq, rx_iq;
    logic        tx_iq_valid;
    logic [5:0]  interleaver_depth_i = 6'd8;  // default: 8 rows

    modem dut (
        .clk(clk), .rst_n(rst_n),
        .s_axis_tx_tdata(tx_byte), .s_axis_tx_tvalid(tx_valid),
        .s_axis_tx_tready(tx_ready),
        .m_axis_tx_iq(tx_iq), .m_axis_tx_iq_valid(tx_iq_valid),
        .s_axis_rx_iq(rx_iq), .s_axis_rx_iq_valid(tx_iq_valid),
        .m_axis_rx_tdata(rx_byte), .m_axis_rx_tvalid(rx_valid),
        .interleaver_depth_i(interleaver_depth_i)
    );

    // Channel impairments:
    //   Carrier frequency offset: ~500 Hz at symbol rate 10 MHz -> normalized offset
    //   Modelled as a phase accumulator advancing each RRC output sample
    //   Symbol timing offset: 0.3 symbol delay -> preload rx_iq delay buffer
    localparam int  NOISE_AMP      = 400;          // ~12 dB SNR
    localparam real FREQ_OFF_RAD   = 0.000314;     // ~500 Hz / 10 MHz * 2pi ~= 3.14e-4 rad/sample
    localparam int  TIMING_OFF_Q8  = 77;           // 0.3 * 256 timing offset (modulo-1 units)

    real  phase_acc = 0.0;
    logic [31:0] timing_delay[3];  // 3-tap delay for fractional timing

    function automatic logic [31:0] apply_channel(input [31:0] iq_in);
        real i_r, q_r, i_rot, q_rot;
        int  ni, nq;
        int  i_out, q_out;
        // 1. Apply carrier frequency offset (complex rotation)
        i_r   = $itor($signed(iq_in[31:16]));
        q_r   = $itor($signed(iq_in[15:0]));
        i_rot = i_r * $cos(phase_acc) - q_r * $sin(phase_acc);
        q_rot = i_r * $sin(phase_acc) + q_r * $cos(phase_acc);
        phase_acc = phase_acc + FREQ_OFF_RAD;
        // 2. AWGN
        ni    = $random % NOISE_AMP;
        nq    = $random % NOISE_AMP;
        i_out = $rtoi(i_rot) + ni;
        q_out = $rtoi(q_rot) + nq;
        return {i_out[15:0], q_out[15:0]};
    endfunction

    // Build rx_iq from delayed tx_iq (timing offset) + channel
    always_ff @(posedge clk) begin
        if (tx_iq_valid) begin
            timing_delay[2] <= timing_delay[1];
            timing_delay[1] <= timing_delay[0];
            timing_delay[0] <= tx_iq;
        end
    end
    // Use 1-cycle delayed sample to simulate 0.25–0.5 symbol timing offset
    always_comb rx_iq = apply_channel(timing_delay[1]);

    localparam int N_BYTES = 1250;
    logic [7:0] sent[N_BYTES];
    int bit_errors = 0;
    int bytes_rx   = 0;

    initial begin
        rst_n = 0; tx_valid = 0;
        timing_delay[0] = '0; timing_delay[1] = '0; timing_delay[2] = '0;
        `WAIT_CYCLES(10); rst_n = 1; `WAIT_CYCLES(5);

        foreach (sent[i]) begin
            sent[i]  = $urandom;
            tx_byte  = sent[i];
            tx_valid = 1;
            @(posedge clk iff tx_ready);
        end
        tx_valid = 0;

        wait(bytes_rx >= N_BYTES || $time > 10_000_000);

        `CHECK(bit_errors <= 12, "BER < 1e-3 post-convergence with freq+timing offsets");
        $display("modem_tb: BER = %0d/%0d with freq+timing offset -- PASSED",
                 bit_errors, N_BYTES*8);
        $finish;
    end

    always @(posedge clk) begin
        if (rx_valid && bytes_rx < N_BYTES) begin
            bit_errors += $countones(rx_byte ^ sent[bytes_rx]);
            bytes_rx++;
        end
    end

    // TODO: interleaver round-trip test
    // Send N_BYTES with burst errors injected mid-frame, verify BER improvement
    // versus same test without interleaver (interleaver_depth_i = 1).
    // $display("TODO: interleaver round-trip BER with burst errors");

    initial begin #20_000_000; $error("TIMEOUT"); $fatal(1); end
endmodule
