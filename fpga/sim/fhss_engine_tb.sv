// fpga/sim/fhss_engine_tb.sv
`timescale 1ns/1ps
`include "sim_helpers.svh"
`include "regs.svh"
module fhss_engine_tb;
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;  // 100 MHz

    logic [255:0] fhek_i;
    logic [31:0]  blacklist_i [0:19];
    logic [31:0]  slot_bitmap_i;
    logic         pps_i = 0;
    logic [4:0]   slot_req;
    logic [31:0]  frame_req;
    logic [31:0]  freq_khz_o;
    logic         freq_valid_o;
    logic         hop_lock_o;
    logic         gps_holdover_o;

    fhss_engine dut (.*);

    // Test vectors (AES-256 of {slot, frame, attempt} with FHEK=0xAA*32)
    localparam int TV_SLOT0_FRAME0_FREQ_KHZ   = 342000;
    localparam int TV_SLOT0_FRAME100_FREQ_KHZ = 326000;
    localparam int TV_SLOT1_FRAME0_FREQ_KHZ   = 225000;

    initial fhek_i = {32{8'hAA}};
    initial foreach (blacklist_i[i]) blacklist_i[i] = 0;
    initial slot_bitmap_i = 0;

    task automatic request_freq(
        input [4:0] slot, input [31:0] frame,
        output [31:0] freq_khz
    );
        slot_req = slot; frame_req = frame;
        @(posedge clk iff freq_valid_o);
        freq_khz = freq_khz_o;
    endtask

    logic [31:0] freq;
    initial begin
        rst_n = 0; `WAIT_CYCLES(4); rst_n = 1; `WAIT_CYCLES(2);

        // Test 1: Known AES-256 test vectors
        request_freq(0, 0,   freq);
        `CHECK_EQ(freq, TV_SLOT0_FRAME0_FREQ_KHZ,   "slot=0 frame=0 freq");
        request_freq(0, 100, freq);
        `CHECK_EQ(freq, TV_SLOT0_FRAME100_FREQ_KHZ, "slot=0 frame=100 freq");
        request_freq(1, 0,   freq);
        `CHECK_EQ(freq, TV_SLOT1_FRAME0_FREQ_KHZ,   "slot=1 frame=0 freq");

        // Test 2: Frequency within band (225-512 MHz)
        for (int s = 0; s < 20; s++) begin
            for (int f = 0; f < 10; f++) begin
                request_freq(s, f, freq);
                `CHECK(freq >= 225_000 && freq <= 512_000, "freq in band");
            end
        end

        // Test 3: Blacklist skip
        request_freq(0, 0, freq);
        blacklist_i[0] = freq;
        `WAIT_CYCLES(2);
        request_freq(0, 0, freq);
        `CHECK(freq != blacklist_i[0], "blacklisted freq skipped");
        blacklist_i[0] = 0;

        // Test 4: GPS 1PPS resets frame counter, hop_lock asserts
        @(posedge clk); pps_i = 1; @(posedge clk); pps_i = 0;
        repeat(50) @(posedge clk);
        `CHECK(hop_lock_o, "hop_lock after GPS 1PPS");

        // Test 5: GPS holdover when PPS stops
        repeat(200) @(posedge clk);
        `CHECK(gps_holdover_o, "gps_holdover when PPS missing");

        $display("fhss_engine_tb: ALL TESTS PASSED"); $finish;
    end
    initial begin #5000000; $error("TIMEOUT"); $fatal(1); end
endmodule
