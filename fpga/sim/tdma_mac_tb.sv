// fpga/sim/tdma_mac_tb.sv
`timescale 1ns/1ps
`include "sim_helpers.svh"
module tdma_mac_tb;
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    logic [31:0] slot_bitmap_i;
    logic [4:0]  current_slot_i;
    logic        txnrx_o;
    logic        pa_enable_o;
    logic        tr_switch_o;
    logic        preamble_tx_o;
    logic        slot_lock_o;

    tdma_mac dut (.*);

    task automatic next_slot(input [4:0] slot);
        current_slot_i = slot;
        @(posedge clk);
    endtask

    initial begin
        slot_bitmap_i = 32'h0000_0001;  // own slot 0
        current_slot_i = 0; rst_n = 0;
        `WAIT_CYCLES(4); rst_n = 1; `WAIT_CYCLES(2);

        // --- Test 1: TX slot — owned slot 0 ---
        next_slot(0);
        `WAIT_CYCLES(5);
        `CHECK(txnrx_o,    "txnrx=1 on owned TX slot");
        `CHECK(pa_enable_o, "PA enabled on TX slot");
        `CHECK(tr_switch_o, "T/R switch=TX on owned slot");

        // --- Test 2: RX slot — unowned slot 1 ---
        next_slot(1);
        `WAIT_CYCLES(5);
        `CHECK(!txnrx_o,    "txnrx=0 on RX slot");
        `CHECK(!pa_enable_o, "PA off on RX slot");
        `CHECK(!tr_switch_o, "T/R switch=RX on unowned slot");

        // --- Test 3: TX->RX transition within 1 us (100 cycles at 100 MHz) ---
        next_slot(0); `WAIT_CYCLES(2);
        next_slot(1);
        begin
            int cycles = 0;
            while (txnrx_o && cycles < 200) begin @(posedge clk); cycles++; end
            `CHECK(cycles < 100, "T/R switch transition < 1 us");
        end

        // --- Test 4: Preamble output on TX slot ---
        next_slot(0); `WAIT_CYCLES(2);
        `CHECK(preamble_tx_o, "preamble asserted at start of TX slot");

        // --- Test 5: No false slot_lock on empty channel ---
        next_slot(5); `WAIT_CYCLES(50);
        `CHECK(!slot_lock_o, "no false slot_lock on noise-free RX");

        $display("tdma_mac_tb: ALL TESTS PASSED"); $finish;
    end
    initial begin #1000000; $error("TIMEOUT"); $fatal(1); end
endmodule
