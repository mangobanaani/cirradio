// fpga/sim/axi_regs_tb.sv
// Run on Linux with:
//   vivado -mode batch -source fpga/scripts/run_sim.tcl -tclargs axi_regs_tb
// Expected output: axi_regs_tb: ALL TESTS PASSED
`timescale 1ns/1ps
`include "sim_helpers.svh"
`include "regs.svh"

module axi_regs_tb;
    // Clock/reset
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;  // 100 MHz

    // DUT signals
    logic [11:0] awaddr; logic awvalid, awready;
    logic [31:0] wdata;  logic [3:0] wstrb; logic wvalid, wready;
    logic [1:0]  bresp;  logic bvalid, bready;
    logic [11:0] araddr; logic arvalid, arready;
    logic [31:0] rdata;  logic [1:0] rresp; logic rvalid, rready;
    logic [255:0] fhek_o;
    logic [31:0]  blacklist_o[0:19];
    logic [31:0]  slot_bitmap_o;
    logic signed [31:0] tx_power_o;
    logic [31:0]  status_i  = 32'h2; // GPS holdover
    logic signed [31:0] rssi_i = 32'hFFFF8300;
    logic [31:0]  hop_counter_i = 32'h0;
    logic [31:0]  err_count_i[0:19];
    initial foreach (err_count_i[i]) err_count_i[i] = 0;

    axi_regs dut (.*);

    // AXI write task
    task automatic axi_write(input [11:0] addr, input [31:0] data);
        awaddr = addr; awvalid = 1; wdata = data; wstrb = 4'hF; wvalid = 1;
        bready = 1;
        @(posedge clk iff (awready && wready));
        @(posedge clk); awvalid = 0; wvalid = 0;
        @(posedge clk iff bvalid);
        `CHECK_EQ(bresp, 2'b00, "write response OKAY");
        @(posedge clk); bready = 0;
    endtask

    // AXI read task
    task automatic axi_read(input [11:0] addr, output [31:0] data);
        araddr = addr; arvalid = 1; rready = 1;
        @(posedge clk iff arready);
        @(posedge clk); arvalid = 0;
        @(posedge clk iff rvalid);
        `CHECK_EQ(rresp, 2'b00, "read response OKAY");
        data = rdata;
        @(posedge clk); rready = 0;
    endtask

    logic [31:0] rd;

    initial begin
        // Reset
        awvalid=0; wvalid=0; bready=0; arvalid=0; rready=0;
        rst_n = 0; `WAIT_CYCLES(4); rst_n = 1; `WAIT_CYCLES(2);

        // --- Test 1: Reset defaults ---
        axi_read(REG_STATUS, rd);
        `CHECK_EQ(rd, REG_STATUS_RESET, "STATUS reset default");
        axi_read(REG_TX_POWER, rd);
        `CHECK_EQ(rd, REG_TX_POWER_RESET, "TX_POWER reset default");
        axi_read(REG_SLOT_BITMAP, rd);
        `CHECK_EQ(rd, REG_SLOT_BITMAP_RESET, "SLOT_BITMAP reset default");

        // --- Test 2: Write and read back FHEK registers ---
        axi_write(REG_FHEK_0, 32'hDEADBEEF);
        axi_write(REG_FHEK_7, 32'hCAFEBABE);
        axi_read(REG_FHEK_0, rd);
        `CHECK_EQ(rd, 32'hDEADBEEF, "FHEK_0 write-readback");
        axi_read(REG_FHEK_7, rd);
        `CHECK_EQ(rd, 32'hCAFEBABE, "FHEK_7 write-readback");

        // --- Test 3: FHEK output propagates ---
        `CHECK_EQ(fhek_o[31:0],   32'hDEADBEEF, "fhek_o[31:0]");
        `CHECK_EQ(fhek_o[255:224], 32'hCAFEBABE, "fhek_o[255:224]");

        // --- Test 4: Blacklist write-readback ---
        axi_write(REG_BLACKLIST_BASE,            32'd225_000);  // entry 0
        axi_write(REG_BLACKLIST_BASE + 12'h04,   32'd300_000);  // entry 1
        axi_write(REG_BLACKLIST_BASE + 12'h4C,   32'd512_000);  // entry 19
        axi_read(REG_BLACKLIST_BASE, rd);
        `CHECK_EQ(rd, 32'd225_000, "blacklist[0] readback");
        axi_read(REG_BLACKLIST_BASE + 12'h4C, rd);
        `CHECK_EQ(rd, 32'd512_000, "blacklist[19] readback");

        // --- Test 5: Slot bitmap ---
        axi_write(REG_SLOT_BITMAP, 32'h000F_0001);
        `CHECK_EQ(slot_bitmap_o, 32'h000F_0001, "slot_bitmap_o propagates");

        // --- Test 6: TX power ---
        axi_write(REG_TX_POWER, 32'd3700);
        `CHECK_EQ(tx_power_o, 32'd3700, "tx_power_o propagates");

        // --- Test 7: Read-only registers reflect inputs ---
        status_i = 32'h1; rssi_i = -5000; hop_counter_i = 32'h00000064;
        `WAIT_CYCLES(2);
        axi_read(REG_STATUS, rd);       `CHECK_EQ(rd, 32'h1, "STATUS from PL");
        axi_read(REG_RSSI, rd);         `CHECK_EQ(rd, 32'hFFFF_EC78, "RSSI from PL");
        axi_read(REG_HOP_COUNTER, rd);  `CHECK_EQ(rd, 32'h64, "HOP_COUNTER from PL");

        // --- Test 8: Per-slot error counts ---
        err_count_i[0]  = 32'd7;
        err_count_i[19] = 32'd42;
        `WAIT_CYCLES(2);
        axi_read(REG_ERR_BASE, rd);             `CHECK_EQ(rd, 32'd7,  "err_count[0]");
        axi_read(REG_ERR_BASE + 12'h4C, rd);    `CHECK_EQ(rd, 32'd42, "err_count[19]");

        $display("axi_regs_tb: ALL TESTS PASSED");
        $finish;
    end

    // Timeout watchdog
    initial begin #50000; $error("TIMEOUT"); $fatal(1); end
endmodule
