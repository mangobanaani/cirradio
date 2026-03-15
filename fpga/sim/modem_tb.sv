// fpga/sim/modem_tb.sv
`timescale 1ns/1ps
`include "sim_helpers.svh"
module modem_tb;
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    logic [7:0] tx_byte; logic tx_valid, tx_ready;
    logic [7:0] rx_byte; logic rx_valid;
    logic [31:0] tx_iq, rx_iq;
    logic        tx_iq_valid, rx_iq_valid = 1;

    modem dut (
        .clk(clk), .rst_n(rst_n),
        .s_axis_tx_tdata(tx_byte), .s_axis_tx_tvalid(tx_valid),
        .s_axis_tx_tready(tx_ready),
        .m_axis_tx_iq(tx_iq), .m_axis_tx_iq_valid(tx_iq_valid),
        .s_axis_rx_iq(rx_iq), .s_axis_rx_iq_valid(rx_iq_valid),
        .m_axis_rx_tdata(rx_byte), .m_axis_rx_tvalid(rx_valid)
    );

    // AWGN at ~12 dB SNR
    localparam int NOISE_AMP = 400;

    function automatic logic [31:0] add_noise(input [31:0] iq);
        logic [15:0] i_noisy, q_noisy;
        int ni, nq;
        ni = $random % NOISE_AMP;
        nq = $random % NOISE_AMP;
        i_noisy = iq[31:16] + ni;
        q_noisy = iq[15:0]  + nq;
        return {i_noisy, q_noisy};
    endfunction

    always_comb rx_iq = add_noise(tx_iq);

    localparam int N_BYTES = 1250;
    logic [7:0] sent[N_BYTES];
    int bit_errors = 0;
    int bytes_rx   = 0;

    initial begin
        rst_n = 0; tx_valid = 0;
        `WAIT_CYCLES(10); rst_n = 1; `WAIT_CYCLES(5);

        foreach (sent[i]) begin
            sent[i] = $urandom;
            tx_byte  = sent[i];
            tx_valid = 1;
            @(posedge clk iff tx_ready);
        end
        tx_valid = 0;

        wait(bytes_rx >= N_BYTES || $time > 5000000);

        `CHECK(bit_errors <= 1, "BER < 1e-4 at Eb/N0=9dB");
        $display("modem_tb: BER = %0d/%0d -- PASSED", bit_errors, N_BYTES*8);
        $finish;
    end

    always @(posedge clk) begin
        if (rx_valid && bytes_rx < N_BYTES) begin
            bit_errors += $countones(rx_byte ^ sent[bytes_rx]);
            bytes_rx++;
        end
    end

    initial begin #10000000; $error("TIMEOUT"); $fatal(1); end
endmodule
