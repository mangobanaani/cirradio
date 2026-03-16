// fpga/src/axi_regs/axi_regs.sv
`timescale 1ns/1ps
`include "regs.svh"
module axi_regs #(
    parameter ADDR_WIDTH = 12,
    parameter DATA_WIDTH = 32
)(
    input  logic                  clk,
    input  logic                  rst_n,
    input  logic [ADDR_WIDTH-1:0] s_axi_awaddr,
    input  logic                  s_axi_awvalid,
    output logic                  s_axi_awready,
    input  logic [DATA_WIDTH-1:0] s_axi_wdata,
    input  logic [3:0]            s_axi_wstrb,
    input  logic                  s_axi_wvalid,
    output logic                  s_axi_wready,
    output logic [1:0]            s_axi_bresp,
    output logic                  s_axi_bvalid,
    input  logic                  s_axi_bready,
    input  logic [ADDR_WIDTH-1:0] s_axi_araddr,
    input  logic                  s_axi_arvalid,
    output logic                  s_axi_arready,
    output logic [DATA_WIDTH-1:0] s_axi_rdata,
    output logic [1:0]            s_axi_rresp,
    output logic                  s_axi_rvalid,
    input  logic                  s_axi_rready,
    output logic [255:0]          fhek_o,
    output logic [31:0]           blacklist_o [0:19],
    output logic [31:0]           slot_bitmap_o,
    output logic signed [31:0]    tx_power_o,
    output logic [31:0]           ctrl_o,
    output logic [31:0]           hop_period_o,
    output logic [31:0]           blacklist_size_o,
    output logic [5:0]            interleaver_depth_o,
    output logic [31:0]           pa_ramp_steps_o,
    output logic [31:0]           emcon_ctrl_o,
    output logic                  emcon_ctrl_wr_o,
    output logic                  emcon_unlock_wr_o,
    output logic [31:0]           axi_wdata_o,
    input  logic [31:0]           status_i,
    input  logic signed [31:0]    rssi_i,
    input  logic [31:0]           hop_counter_i,
    input  logic [31:0]           err_count_i [0:19]
);
    // Write register storage
    logic [31:0] fhek_r   [0:7];
    logic [31:0] bl_r     [0:19];
    logic [31:0] slotmap_r;
    logic [31:0] txpow_r;
    logic [31:0] ctrl_r;

    // TRANSEC register storage
    logic [31:0] hop_period_r;
    logic [31:0] bl_size_r;
    logic [31:0] il_depth_r;
    logic [31:0] pa_step_r;
    logic [31:0] emcon_ctrl_r;
    logic        emcon_ctrl_wr_r;
    logic        emcon_unlock_wr_r;

    // Output assignments
    genvar k;
    generate
        for (k = 0; k < 8; k++)
            assign fhek_o[k*32 +: 32] = fhek_r[k];
        for (k = 0; k < 20; k++)
            assign blacklist_o[k] = bl_r[k];
    endgenerate
    assign slot_bitmap_o = slotmap_r;
    assign tx_power_o    = txpow_r;
    assign ctrl_o    = ctrl_r;

    // AXI write state machine (single-cycle accept)
    assign s_axi_awready = 1'b1;
    assign s_axi_wready  = 1'b1;
    assign s_axi_bresp   = 2'b00; // OKAY

    logic aw_fire, w_fire;
    assign aw_fire = s_axi_awvalid & s_axi_awready;
    assign w_fire  = s_axi_wvalid  & s_axi_wready;

    logic        wr_pending;
    logic [11:0] wr_addr_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axi_bvalid      <= '0;
            wr_pending        <= '0;
            foreach (fhek_r[i])  fhek_r[i]  <= '0;
            foreach (bl_r[i])    bl_r[i]    <= '0;
            slotmap_r         <= REG_SLOT_BITMAP_RESET;
            txpow_r           <= REG_TX_POWER_RESET;
            ctrl_r            <= '0;
            hop_period_r      <= 32'd1_000_000;
            bl_size_r         <= 32'd20;
            il_depth_r        <= 32'd10;
            pa_step_r         <= 32'd4;
            emcon_ctrl_r      <= 32'd2;
            emcon_ctrl_wr_r   <= '0;
            emcon_unlock_wr_r <= '0;
        end else begin
            // Latch write address
            if (aw_fire) wr_addr_r <= s_axi_awaddr;
            if (aw_fire) wr_pending <= 1'b1;

            // Apply write data
            if (w_fire && (wr_pending || aw_fire)) begin
                logic [11:0] wa;
                wa = aw_fire ? s_axi_awaddr : wr_addr_r;
                // FHEK
                if (wa >= REG_FHEK_0 && wa <= REG_FHEK_7)
                    fhek_r[(wa - REG_FHEK_0) >> 2] <= s_axi_wdata;
                // Blacklist
                else if (wa >= REG_BLACKLIST_BASE &&
                         wa < REG_BLACKLIST_BASE + 20*4)
                    bl_r[(wa - REG_BLACKLIST_BASE) >> 2] <= s_axi_wdata;
                // Slot bitmap
                else if (wa == REG_SLOT_BITMAP) slotmap_r <= s_axi_wdata;
                // TX power
                else if (wa == REG_TX_POWER)   txpow_r   <= s_axi_wdata;
                // Control (write-only: zeroize / halt)
                else if (wa == REG_CONTROL) ctrl_r <= s_axi_wdata;
                // TRANSEC registers
                else if (wa == REG_HOP_RATE)          hop_period_r      <= s_axi_wdata;
                else if (wa == REG_BLACKLIST_SIZE)    bl_size_r         <= s_axi_wdata;
                else if (wa == REG_INTERLEAVER_DEPTH) il_depth_r        <= s_axi_wdata;
                else if (wa == REG_PA_RAMP_STEPS)      pa_step_r         <= s_axi_wdata;
                else if (wa == REG_EMCON_CTRL)  begin emcon_ctrl_r      <= s_axi_wdata;
                                                      emcon_ctrl_wr_r   <= 1'b1; end
                else if (wa == REG_EMCON_UNLOCK)      emcon_unlock_wr_r <= 1'b1;
                wr_pending <= 1'b0;
                s_axi_bvalid <= 1'b1;
            end else begin emcon_ctrl_wr_r <= '0; emcon_unlock_wr_r <= '0; end

            if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 1'b0;
        end
    end

    // AXI read state machine
    assign s_axi_arready = 1'b1;
    assign s_axi_rresp   = 2'b00;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axi_rvalid <= '0;
            s_axi_rdata  <= '0;
        end else begin
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1'b1;
                case (s_axi_araddr)
                    REG_SLOT_BITMAP:  s_axi_rdata <= slotmap_r;
                    REG_TX_POWER:     s_axi_rdata <= txpow_r;
                    REG_STATUS:       s_axi_rdata <= status_i;
                    REG_RSSI:         s_axi_rdata <= rssi_i;
                    REG_HOP_COUNTER:  s_axi_rdata <= hop_counter_i;
                    REG_EMCON_CTRL:   s_axi_rdata <= emcon_ctrl_r;
                    default: begin
                        if (s_axi_araddr >= REG_FHEK_0 &&
                            s_axi_araddr <= REG_FHEK_7)
                            s_axi_rdata <=
                                fhek_r[(s_axi_araddr - REG_FHEK_0) >> 2];
                        else if (s_axi_araddr >= REG_BLACKLIST_BASE &&
                                 s_axi_araddr < REG_BLACKLIST_BASE + 20*4)
                            s_axi_rdata <=
                                bl_r[(s_axi_araddr - REG_BLACKLIST_BASE) >> 2];
                        else if (s_axi_araddr >= REG_ERR_BASE &&
                                 s_axi_araddr < REG_ERR_BASE + 20*4)
                            s_axi_rdata <=
                                err_count_i[(s_axi_araddr - REG_ERR_BASE) >> 2];
                        else
                            s_axi_rdata <= '0;
                    end
                endcase
            end else if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
            end
        end
    end

    // TRANSEC output assignments
    assign hop_period_o        = hop_period_r;
    assign blacklist_size_o    = bl_size_r;
    assign interleaver_depth_o = il_depth_r[5:0];
    assign pa_ramp_steps_o      = pa_step_r;
    assign emcon_ctrl_o        = emcon_ctrl_r;
    assign emcon_ctrl_wr_o     = emcon_ctrl_wr_r;
    assign emcon_unlock_wr_o   = emcon_unlock_wr_r;
    assign axi_wdata_o         = s_axi_wdata;
endmodule
