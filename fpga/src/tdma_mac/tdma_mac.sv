// fpga/src/tdma_mac/tdma_mac.sv
`timescale 1ns/1ps
module tdma_mac (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] slot_bitmap_i,
    input  logic [4:0]  current_slot_i,
    output logic        txnrx_o,
    output logic        pa_enable_o,
    output logic        tr_switch_o,
    output logic        preamble_tx_o,
    output logic        slot_lock_o
);
    // tx_slot: 1 if this node owns the current slot
    logic tx_slot;
    assign tx_slot = slot_bitmap_i[current_slot_i];

    // TX/RX control registers
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            txnrx_o     <= '0;
            pa_enable_o <= '0;
            tr_switch_o <= '0;
        end else begin
            txnrx_o     <= tx_slot;
            pa_enable_o <= tx_slot;
            tr_switch_o <= tx_slot;
        end
    end

    // Preamble: assert for first 3000 cycles of owned TX slot (30 ms at 100 MHz)
    localparam int PREAMBLE_CYCLES = 3000;
    logic [11:0] preamble_cnt;
    logic        prev_tx_slot;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            preamble_cnt  <= '0;
            preamble_tx_o <= '0;
            prev_tx_slot  <= '0;
        end else begin
            prev_tx_slot <= tx_slot;
            if (tx_slot && !prev_tx_slot) begin
                // Rising edge of tx_slot: start preamble
                preamble_cnt  <= 12'(PREAMBLE_CYCLES - 1);
                preamble_tx_o <= 1'b1;
            end else if (preamble_cnt > 0) begin
                preamble_cnt  <= preamble_cnt - 1'b1;
                preamble_tx_o <= 1'b1;
            end else begin
                preamble_tx_o <= 1'b0;
            end
        end
    end

    // slot_lock: preamble detector — asserts when preamble_in signal
    // detected during RX slot. In simulation, driven via external force.
    // For hardware: correlation energy threshold on RX baseband.
    assign slot_lock_o = 1'b0;  // hardware-dependent; cleared in sim tests

endmodule
