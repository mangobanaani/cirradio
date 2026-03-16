// fpga/src/tdma_mac/tdma_mac.sv
`timescale 1ns/1ps
module tdma_mac (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] slot_bitmap_i,
    input  logic [4:0]  current_slot_i,
    // EMCON controls
    input  logic [1:0]  emcon_level_i,
    input  logic        emcon_ctrl_wr_i,
    input  logic        emcon_unlock_wr_i,
    input  logic [31:0] axi_wdata_i,
    // PA ramp
    input  logic [31:0] pa_ramp_steps_i,
    // Outputs
    output logic        txnrx_o,
    output logic        pa_enable_o,
    output logic        tr_switch_o,
    output logic        preamble_tx_o,
    output logic        slot_lock_o,
    output logic [15:0] pa_atten_x100_o
);
    // tx_slot: 1 if this node owns the current slot
    logic tx_slot;
    assign tx_slot = slot_bitmap_i[current_slot_i];

    // =========================================================================
    // EMCON unlock latch and level register
    // =========================================================================
    logic        unlock_pending_q;
    logic [1:0]  emcon_level_q;
    logic        lock_q;

    localparam logic [31:0] EMCON_UNLOCK_MAGIC = 32'hA5C3_3C5A;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            unlock_pending_q <= 1'b0;
            emcon_level_q    <= 2'b10;
            lock_q           <= 1'b0;
        end else begin
            if (emcon_unlock_wr_i && axi_wdata_i == EMCON_UNLOCK_MAGIC)
                unlock_pending_q <= 1'b1;

            if (emcon_ctrl_wr_i) begin
                unlock_pending_q <= 1'b0;
                lock_q           <= axi_wdata_i[2];
                if (emcon_level_i > emcon_level_q) begin
                    if (!lock_q || unlock_pending_q)
                        emcon_level_q <= emcon_level_i;
                end else begin
                    emcon_level_q <= emcon_level_i;
                end
            end
        end
    end

    // =========================================================================
    // EMCON-gated PA enable
    // Level 0: transmit inhibited
    // Level 1: transmit only on slot 0 (beacon/emergency)
    // Level 2: normal operation
    // =========================================================================
    always_comb begin
        case (emcon_level_q)
            2'b00: pa_enable_o = 1'b0;
            2'b01: pa_enable_o = tx_slot & (current_slot_i == 5'd0);
            2'b10: pa_enable_o = tx_slot;
            default: pa_enable_o = 1'b0;
        endcase
    end

    // TX/RX control follows pa_enable_o
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            txnrx_o     <= '0;
            tr_switch_o <= '0;
        end else begin
            txnrx_o     <= pa_enable_o;
            tr_switch_o <= pa_enable_o;
        end
    end

    // =========================================================================
    // PA ramp
    // pa_atten_x100_o: attenuation in hundredths of a dB
    //   0x0FA0 = 4000 → −40 dB (fully attenuated)
    //   0x0000 →   0 dB (full power)
    // pa_ramp_steps_i: attenuation units decremented/incremented each cycle.
    // Default 4 → ramp takes 4000/4 = 1000 cycles = 10 µs at 100 MHz.
    // =========================================================================
    logic tx_slot_prev;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pa_atten_x100_o <= 16'h0FA0;  // start at −40 dB × 100
            tx_slot_prev    <= 1'b0;
        end else begin
            tx_slot_prev <= pa_enable_o;

            if (pa_enable_o) begin
                // Ramp up: decrement attenuation each cycle
                if (pa_atten_x100_o >= pa_ramp_steps_i[15:0])
                    pa_atten_x100_o <= pa_atten_x100_o - pa_ramp_steps_i[15:0];
                else
                    pa_atten_x100_o <= 16'd0;
            end else begin
                // Ramp down: increment attenuation each cycle
                if (pa_atten_x100_o + pa_ramp_steps_i[15:0] <= 16'h0FA0)
                    pa_atten_x100_o <= pa_atten_x100_o + pa_ramp_steps_i[15:0];
                else
                    pa_atten_x100_o <= 16'h0FA0;
            end
        end
    end


    // =========================================================================
    // Preamble: assert for first 3000 cycles of owned TX slot (30 ms at 100 MHz)
    // =========================================================================
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
