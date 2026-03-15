// fpga/src/fhss_engine/fhss_engine.sv
`timescale 1ns/1ps
module fhss_engine (
    input  logic        clk,
    input  logic        rst_n,
    // Key and configuration (from axi_regs)
    input  logic [255:0] fhek_i,
    input  logic [31:0]  blacklist_i [0:19],
    input  logic [31:0]  slot_bitmap_i,
    // GPS 1PPS synchronization
    input  logic         pps_i,
    // Frequency query interface
    input  logic [4:0]   slot_req,
    input  logic [31:0]  frame_req,
    // Outputs
    output logic [31:0]  freq_khz_o,
    output logic         freq_valid_o,
    output logic         hop_lock_o,
    output logic         gps_holdover_o
);

    // AES core signals
    logic        aes_init, aes_next;
    logic [127:0] aes_block;
    logic [127:0] aes_result;
    logic         aes_ready, aes_result_valid;

    aes_core aes_inst (
        .clk         (clk),
        .reset_n     (rst_n),
        .encdec      (1'b1),         // encrypt
        .init        (aes_init),
        .next        (aes_next),
        .keylen      (1'b1),         // AES-256
        .key         (fhek_i),
        .block       (aes_block),
        .ready       (aes_ready),
        .result      (aes_result),
        .result_valid(aes_result_valid)
    );

    // GPS holdover detection
    // Missing PPS after GPS_HOLDOVER_CYCLES → assert gps_holdover_o
    localparam int GPS_HOLDOVER_CYCLES = 15_000_000;
    logic [24:0] pps_watchdog;
    logic        pps_prev;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pps_watchdog   <= 0;
            pps_prev       <= 0;
            hop_lock_o     <= 0;
            gps_holdover_o <= 1;
        end else begin
            pps_prev <= pps_i;
            // Rising edge of PPS
            if (pps_i && !pps_prev) begin
                pps_watchdog   <= 0;
                hop_lock_o     <= 1;
                gps_holdover_o <= 0;
            end else if (pps_watchdog < GPS_HOLDOVER_CYCLES[24:0]) begin
                pps_watchdog <= pps_watchdog + 1;
            end else begin
                gps_holdover_o <= 1;
            end
        end
    end

    // FSM states
    typedef enum logic [2:0] {
        S_IDLE,
        S_INIT_KEY,
        S_WAIT_READY,
        S_ENCRYPT,
        S_WAIT_RESULT,
        S_CHECK_BLACKLIST,
        S_DONE
    } state_t;

    state_t state;
    logic [7:0]  attempt_reg;
    logic [4:0]  slot_reg;
    logic [31:0] frame_reg;
    logic [63:0] cipher_lo;
    logic [31:0] channel_idx;
    logic [31:0] candidate_freq;
    logic        blacklisted;

    // Check if candidate_freq is blacklisted
    always_comb begin
        blacklisted = 1'b0;
        for (int i = 0; i < 20; i++) begin
            if (blacklist_i[i] != 0 && blacklist_i[i] == candidate_freq)
                blacklisted = 1'b1;
        end
    end

    assign aes_block = {slot_reg, 24'h0, frame_reg, 56'h0, attempt_reg};

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= S_IDLE;
            aes_init     <= 0;
            aes_next     <= 0;
            freq_khz_o   <= 0;
            freq_valid_o <= 0;
            attempt_reg  <= 0;
        end else begin
            aes_init     <= 0;
            aes_next     <= 0;
            freq_valid_o <= 0;

            case (state)
                S_IDLE: begin
                    // Accept new request when in IDLE
                    slot_reg    <= slot_req;
                    frame_reg   <= frame_req;
                    attempt_reg <= 0;
                    aes_init    <= 1;   // load key
                    state       <= S_INIT_KEY;
                end

                S_INIT_KEY: begin
                    // Wait for AES core to be ready (key schedule done)
                    if (aes_ready) begin
                        aes_next <= 1;
                        state    <= S_WAIT_RESULT;
                    end
                end

                S_WAIT_RESULT: begin
                    if (aes_result_valid) begin
                        cipher_lo <= aes_result[63:0];
                        state     <= S_CHECK_BLACKLIST;
                    end
                end

                S_CHECK_BLACKLIST: begin
                    // channel_index = ciphertext[63:0] % 287
                    // 287 channels: 225000..511000 kHz (1 MHz steps)
                    channel_idx    = cipher_lo % 287;
                    candidate_freq = 225_000 + channel_idx * 1_000;

                    if (!blacklisted || attempt_reg >= 9) begin
                        freq_khz_o   <= candidate_freq;
                        freq_valid_o <= 1;
                        state        <= S_DONE;
                    end else begin
                        // Try next attempt
                        attempt_reg <= attempt_reg + 1;
                        aes_next    <= 1;   // encrypt with new attempt
                        state       <= S_WAIT_RESULT;
                    end
                end

                S_DONE: begin
                    // Hold output; on next cycle return to IDLE for next request
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
