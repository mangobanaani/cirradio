#!/usr/bin/env python3
"""Generate PCB routing traces, via stitching, and silkscreen for CIRRADIO dev board.

Adds representative routing for:
- DDR3L byte lanes and address/command bus (In2.Cu / In4.Cu)
- AD9361 LVDS differential pairs (In2.Cu)
- 50-ohm RF microstrip (F.Cu)
- Power distribution (In5.Cu)
- General I/O: SPI, UART, I2C, JTAG (In6.Cu / In8.Cu)
- Ground via stitching along board perimeter and RF section
- Silkscreen board title
"""

import re
import uuid
import math

PCB_FILE = "hardware/cirradio-devboard/cirradio-devboard.kicad_pcb"

# Component reference positions (mm) from placement generator
ZYNQ_XY = (80.0, 50.0)
AD9361_XY = (80.0, 16.0)
DDR0_XY = (112.0, 35.0)   # U2 - DDR3L chip 0
DDR1_XY = (128.0, 35.0)   # U3 - DDR3L chip 1

# RF chain positions (approximate, from placement)
SMA_RX_XY = (10.0, 10.0)
BPF_XY = (22.0, 10.0)
TR_SW_XY = (34.0, 10.0)
LNA_XY = (46.0, 12.0)
SAW_XY = (58.0, 14.0)
AD9361_RF_XY = (80.0, 16.0)
PA_XY = (46.0, 8.0)
SMA_TX_XY = (10.0, 20.0)

# Board dimensions
BOARD_W = 160.0
BOARD_H = 100.0
BOARD_MARGIN = 3.0  # edge clearance


def uid():
    return str(uuid.uuid4())


def parse_nets(pcb_text):
    """Extract net number -> net name mapping."""
    nets = {}
    for m in re.finditer(r'\(net\s+(\d+)\s+"([^"]*)"\)', pcb_text):
        nets[m.group(2)] = int(m.group(1))
    return nets


def segment(x1, y1, x2, y2, width, layer, net_num):
    return (f'  (segment (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) '
            f'(width {width}) (layer "{layer}") (net {net_num}) (uuid "{uid()}"))')


def via(x, y, net_num, size=0.55, drill=0.3, layers=("F.Cu", "B.Cu")):
    return (f'  (via (at {x:.3f} {y:.3f}) (size {size}) (drill {drill}) '
            f'(layers "{layers[0]}" "{layers[1]}") (net {net_num}) (uuid "{uid()}"))')


def gr_text(text, x, y, layer="F.SilkS", size=2.0, thickness=0.3):
    return (f'  (gr_text "{text}" (at {x:.3f} {y:.3f}) (layer "{layer}") (uuid "{uid()}")\n'
            f'    (effects (font (size {size} {size}) (thickness {thickness})))\n'
            f'  )')


def route_point_to_point(x1, y1, x2, y2, width, layer, net_num, max_seg=5.0):
    """Route between two points with intermediate segments for long runs."""
    segs = []
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    n = max(1, int(dist / max_seg))
    for i in range(n):
        sx = x1 + dx * i / n
        sy = y1 + dy * i / n
        ex = x1 + dx * (i + 1) / n
        ey = y1 + dy * (i + 1) / n
        segs.append(segment(sx, sy, ex, ey, width, layer, net_num))
    return segs


def gen_ddr3l_routing(nets):
    """Generate DDR3L byte-lane and address/command routing."""
    entries = []
    entries.append("  ; DDR3L byte lane routing (In2.Cu / In4.Cu)")

    # Byte lane 0: DQ0-DQ7 from Zynq to DDR0
    dq_width = 0.1
    for byte_lane in range(4):
        layer = "In2.Cu" if byte_lane < 2 else "In4.Cu"
        y_offset = byte_lane * 1.5
        target_xy = DDR0_XY if byte_lane < 2 else DDR1_XY

        for bit in range(8):
            dq_idx = byte_lane * 8 + bit
            net_name = f"DDR_DQ{dq_idx}"
            net_num = nets.get(net_name, 0)
            if net_num == 0:
                continue
            x_spread = bit * 0.4
            src_x = ZYNQ_XY[0] + 10 + x_spread
            src_y = ZYNQ_XY[1] - 5 + y_offset
            dst_x = target_xy[0] - 4 + x_spread
            dst_y = target_xy[1] + y_offset
            entries.extend(route_point_to_point(
                src_x, src_y, dst_x, dst_y, dq_width, layer, net_num))

        # DQS differential pair for this byte lane
        dqs_p_name = f"DDR_DQS_P{byte_lane}"
        dqs_n_name = f"DDR_DQS_N{byte_lane}"
        dqs_p = nets.get(dqs_p_name, 0)
        dqs_n = nets.get(dqs_n_name, 0)
        if dqs_p and dqs_n:
            gap = 0.15
            cx = (ZYNQ_XY[0] + 10 + target_xy[0] - 4) / 2
            src_y_base = ZYNQ_XY[1] - 5 + y_offset + 0.5
            dst_y_base = target_xy[1] + y_offset + 0.5
            # P trace
            entries.extend(route_point_to_point(
                ZYNQ_XY[0] + 12, src_y_base - gap / 2,
                target_xy[0] - 2, dst_y_base - gap / 2,
                dq_width, layer, dqs_p))
            # N trace
            entries.extend(route_point_to_point(
                ZYNQ_XY[0] + 12, src_y_base + gap / 2,
                target_xy[0] - 2, dst_y_base + gap / 2,
                dq_width, layer, dqs_n))

        # DM for this byte lane
        dm_name = f"DDR_DM{byte_lane}"
        dm_net = nets.get(dm_name, 0)
        if dm_net:
            entries.extend(route_point_to_point(
                ZYNQ_XY[0] + 13, ZYNQ_XY[1] - 4 + y_offset,
                target_xy[0] - 1, target_xy[1] + 1 + y_offset,
                dq_width, layer, dm_net))

    # Address / command bus -- fly-by topology: Zynq -> DDR0 -> DDR1
    entries.append("  ; DDR3L address/command fly-by topology (In4.Cu)")
    addr_layer = "In4.Cu"
    addr_width = 0.1
    addr_nets = []
    for i in range(15):
        addr_nets.append(f"DDR_A{i}")
    addr_nets.extend(["DDR_BA0", "DDR_BA1", "DDR_BA2",
                       "DDR_CAS_B", "DDR_RAS_B", "DDR_WE_B",
                       "DDR_CKE", "DDR_CS_B", "DDR_ODT", "DDR_RESET_B"])
    for idx, net_name in enumerate(addr_nets):
        net_num = nets.get(net_name, 0)
        if net_num == 0:
            continue
        y_off = 8 + idx * 0.35
        # Zynq -> DDR0
        entries.extend(route_point_to_point(
            ZYNQ_XY[0] + 14, ZYNQ_XY[1] + y_off,
            DDR0_XY[0], DDR0_XY[1] + 10 + idx * 0.35,
            addr_width, addr_layer, net_num))
        # DDR0 -> DDR1 (fly-by continuation)
        entries.extend(route_point_to_point(
            DDR0_XY[0] + 2, DDR0_XY[1] + 10 + idx * 0.35,
            DDR1_XY[0], DDR1_XY[1] + 10 + idx * 0.35,
            addr_width, addr_layer, net_num))

    # DDR clock differential pair
    entries.append("  ; DDR3L clock differential pair")
    ck_p = nets.get("DDR_CK_P", 0)
    ck_n = nets.get("DDR_CK_N", 0)
    if ck_p and ck_n:
        for ck_net, offset in [(ck_p, -0.075), (ck_n, 0.075)]:
            entries.extend(route_point_to_point(
                ZYNQ_XY[0] + 14, ZYNQ_XY[1] + 6 + offset,
                DDR0_XY[0], DDR0_XY[1] + 8 + offset,
                addr_width, addr_layer, ck_net))
            entries.extend(route_point_to_point(
                DDR0_XY[0] + 2, DDR0_XY[1] + 8 + offset,
                DDR1_XY[0], DDR1_XY[1] + 8 + offset,
                addr_width, addr_layer, ck_net))

    return entries


def gen_lvds_routing(nets):
    """Generate AD9361 LVDS differential pair routing on In2.Cu."""
    entries = []
    entries.append("  ; AD9361 LVDS differential pairs (In2.Cu)")
    lvds_layer = "In2.Cu"
    lvds_width = 0.12
    gap = 0.20

    # 12 data pairs P0_D0..P0_D11
    for i in range(12):
        p_name = f"P0_D{i}_P"
        n_name = f"P0_D{i}_N"
        p_net = nets.get(p_name, 0)
        n_net = nets.get(n_name, 0)
        if not (p_net and n_net):
            continue
        x_spread = i * 1.2
        src_x = AD9361_XY[0] - 8 + x_spread
        src_y = AD9361_XY[1] + 4
        dst_x = ZYNQ_XY[0] - 8 + x_spread
        dst_y = ZYNQ_XY[1] - 12
        # P trace
        entries.extend(route_point_to_point(
            src_x, src_y, dst_x, dst_y,
            lvds_width, lvds_layer, p_net))
        # N trace (offset by gap)
        entries.extend(route_point_to_point(
            src_x + gap, src_y, dst_x + gap, dst_y,
            lvds_width, lvds_layer, n_net))

    # Frame and clock pairs
    for base in ["RX_FRAME", "TX_FRAME", "DATA_CLK", "FB_CLK"]:
        p_net = nets.get(f"{base}_P", 0)
        n_net = nets.get(f"{base}_N", 0)
        if not (p_net and n_net):
            continue
        x_base = AD9361_XY[0] + 8
        entries.extend(route_point_to_point(
            x_base, AD9361_XY[1] + 5, x_base, ZYNQ_XY[1] - 10,
            lvds_width, lvds_layer, p_net))
        entries.extend(route_point_to_point(
            x_base + gap, AD9361_XY[1] + 5, x_base + gap, ZYNQ_XY[1] - 10,
            lvds_width, lvds_layer, n_net))
        x_base += 1.5

    return entries


def gen_rf_routing(nets):
    """Generate 50-ohm RF microstrip routing on F.Cu with ground via stitching."""
    entries = []
    entries.append("  ; RF 50-ohm microstrip routing (F.Cu)")
    rf_width = 0.28
    rf_layer = "F.Cu"
    gnd_net = nets.get("GND", 1)

    # RX path: SMA_RX -> BPF -> T/R switch -> LNA -> SAW -> AD9361
    rx_net = nets.get("AD_RX1A_P", 0) or 178
    rx_path = [SMA_RX_XY, BPF_XY, TR_SW_XY, LNA_XY, SAW_XY, AD9361_RF_XY]
    for i in range(len(rx_path) - 1):
        entries.extend(route_point_to_point(
            rx_path[i][0], rx_path[i][1],
            rx_path[i + 1][0], rx_path[i + 1][1],
            rf_width, rf_layer, rx_net, max_seg=3.0))

    # TX path: AD9361 -> PA -> T/R switch -> SMA_TX
    tx_net = nets.get("AD_TX1A", 0) or 180
    tx_path = [AD9361_RF_XY, (58.0, 8.0), PA_XY, TR_SW_XY, (22.0, 16.0), SMA_TX_XY]
    entries.append("  ; RF TX path")
    for i in range(len(tx_path) - 1):
        entries.extend(route_point_to_point(
            tx_path[i][0], tx_path[i][1],
            tx_path[i + 1][0], tx_path[i + 1][1],
            rf_width, rf_layer, tx_net, max_seg=3.0))

    # Ground via stitching along RX RF trace (every 1mm, offset 1mm from trace)
    entries.append("  ; RF ground via stitching")
    all_rf_points = rx_path + tx_path[1:]  # combined path points
    for i in range(len(rx_path) - 1):
        x1, y1 = rx_path[i]
        x2, y2 = rx_path[i + 1]
        dist = math.hypot(x2 - x1, y2 - y1)
        n_vias = max(1, int(dist / 1.0))
        dx = (x2 - x1) / n_vias
        dy = (y2 - y1) / n_vias
        # perpendicular offset for via stitching
        length = math.hypot(dx, dy)
        if length > 0:
            px = -dy / length * 1.0
            py = dx / length * 1.0
        else:
            px, py = 0, 1.0
        for j in range(n_vias + 1):
            vx = x1 + dx * j + px
            vy = y1 + dy * j + py
            entries.append(via(vx, vy, gnd_net))
            # mirror side
            entries.append(via(vx - 2 * px, vy - 2 * py, gnd_net))

    return entries


def gen_power_routing(nets):
    """Generate power distribution traces on In5.Cu (wide traces from regulators)."""
    entries = []
    entries.append("  ; Power distribution routing (In5.Cu)")
    pwr_layer = "In5.Cu"
    pwr_width = 0.8

    # Regulator area: bottom-right of board (120-150, 70-90)
    reg_area_x = 135.0
    reg_area_y = 80.0

    power_rails = [
        ("+1V0", ZYNQ_XY, 3),
        ("+1V35", ((DDR0_XY[0] + DDR1_XY[0]) / 2, DDR0_XY[1]), 6),
        ("+1V8", (ZYNQ_XY[0], ZYNQ_XY[1] + 10), 13),
        ("+3V3", (80.0, 75.0), 16),
        ("+5V", (80.0, 85.0), 20),
        ("+1V3_AD", AD9361_XY, 9),
        ("+3V3A", (AD9361_XY[0] + 10, AD9361_XY[1]), 17),
    ]

    for rail_name, dest_xy, fallback_net in power_rails:
        net_num = nets.get(rail_name, fallback_net)
        entries.extend(route_point_to_point(
            reg_area_x, reg_area_y,
            dest_xy[0], dest_xy[1],
            pwr_width, pwr_layer, net_num, max_seg=10.0))

    # +12V input from barrel jack (top-right corner area)
    v12_net = nets.get("+12V", 2)
    entries.extend(route_point_to_point(
        150.0, 10.0, reg_area_x, reg_area_y,
        1.0, pwr_layer, v12_net, max_seg=10.0))

    return entries


def gen_general_io_routing(nets):
    """Generate SPI, UART, I2C, JTAG routing on In6.Cu / In8.Cu."""
    entries = []
    io_width = 0.15

    # SPI to AD9361 (Zynq PS SPI -> AD9361)
    entries.append("  ; SPI routing to AD9361 (In6.Cu)")
    spi_layer = "In6.Cu"
    spi_signals = [
        ("AD_SCLK", 179), ("AD_MOSI", 176), ("AD_MISO", 175), ("AD_CS_N", 174)
    ]
    for idx, (name, fallback) in enumerate(spi_signals):
        net_num = nets.get(name, fallback)
        y_off = idx * 0.5
        entries.extend(route_point_to_point(
            ZYNQ_XY[0] - 5, ZYNQ_XY[1] - 8 + y_off,
            AD9361_XY[0] - 5, AD9361_XY[1] + 8 + y_off,
            io_width, spi_layer, net_num))

    # UART (In8.Cu) -- Zynq to connector area (bottom edge)
    entries.append("  ; UART routing (In8.Cu)")
    uart_layer = "In8.Cu"
    uart_signals = [
        ("PS_UART0_RX", 392), ("PS_UART0_TX", 393),
        ("UART0_MIO46", 416), ("UART0_MIO47", 417),
    ]
    for idx, (name, fallback) in enumerate(uart_signals):
        net_num = nets.get(name, fallback)
        entries.extend(route_point_to_point(
            ZYNQ_XY[0] - 10 + idx * 1.0, ZYNQ_XY[1] + 15,
            20.0 + idx * 2.0, BOARD_H - 8,
            io_width, uart_layer, net_num))

    # I2C (In6.Cu)
    entries.append("  ; I2C routing (In6.Cu)")
    i2c_signals = [("PS_I2C_SCL", 385), ("PS_I2C_SDA", 386)]
    for idx, (name, fallback) in enumerate(i2c_signals):
        net_num = nets.get(name, fallback)
        entries.extend(route_point_to_point(
            ZYNQ_XY[0] + 5, ZYNQ_XY[1] + 12 + idx * 0.5,
            40.0 + idx * 2.0, BOARD_H - 8,
            io_width, spi_layer, net_num))

    # JTAG (In8.Cu) -- Zynq to JTAG header (bottom-left)
    entries.append("  ; JTAG routing (In8.Cu)")
    jtag_signals = [
        ("MIO10", 349), ("MIO11", 350), ("MIO12", 351), ("MIO13", 352),
    ]
    for idx, (name, fallback) in enumerate(jtag_signals):
        net_num = nets.get(name, fallback)
        entries.extend(route_point_to_point(
            ZYNQ_XY[0] - 12, ZYNQ_XY[1] + 10 + idx * 0.5,
            10.0 + idx * 2.0, BOARD_H - 8,
            io_width, uart_layer, net_num))

    return entries


def gen_perimeter_via_stitching(nets):
    """Generate ground via stitching around board perimeter every 2mm."""
    entries = []
    entries.append("  ; Board perimeter ground via stitching (every 2mm)")
    gnd_net = nets.get("GND", 1)
    spacing = 2.0
    inset = BOARD_MARGIN + 1.0  # 4mm from edge

    # Top edge
    x = inset
    while x <= BOARD_W - inset:
        entries.append(via(x, inset, gnd_net))
        x += spacing
    # Bottom edge
    x = inset
    while x <= BOARD_W - inset:
        entries.append(via(x, BOARD_H - inset, gnd_net))
        x += spacing
    # Left edge
    y = inset + spacing
    while y <= BOARD_H - inset - spacing:
        entries.append(via(inset, y, gnd_net))
        y += spacing
    # Right edge
    y = inset + spacing
    while y <= BOARD_H - inset - spacing:
        entries.append(via(BOARD_W - inset, y, gnd_net))
        y += spacing

    return entries


def gen_silkscreen():
    """Generate silkscreen text labels."""
    entries = []
    entries.append("  ; Silkscreen labels")
    entries.append(gr_text("CIRRADIO DevBoard v1.0", BOARD_W / 2, BOARD_H - 6,
                           "F.SilkS", 2.0, 0.3))
    entries.append(gr_text("Zynq-7045 + AD9361", BOARD_W / 2, BOARD_H - 3,
                           "F.SilkS", 1.2, 0.2))
    # Section labels
    entries.append(gr_text("RF", 40.0, 5.0, "F.SilkS", 1.5, 0.25))
    entries.append(gr_text("FPGA", ZYNQ_XY[0], ZYNQ_XY[1] - 18, "F.SilkS", 1.5, 0.25))
    entries.append(gr_text("DDR3L", (DDR0_XY[0] + DDR1_XY[0]) / 2, DDR0_XY[1] - 8,
                           "F.SilkS", 1.5, 0.25))
    entries.append(gr_text("POWER", 135.0, 72.0, "F.SilkS", 1.2, 0.2))

    return entries


def main():
    with open(PCB_FILE, "r") as f:
        pcb_text = f.read()

    nets = parse_nets(pcb_text)
    print(f"Parsed {len(nets)} nets from PCB file")

    all_entries = []

    # Generate all routing sections
    all_entries.append("\n  ; ========== ROUTING AND VIA STITCHING ==========")

    ddr = gen_ddr3l_routing(nets)
    all_entries.extend(ddr)
    print(f"  DDR3L routing: {len(ddr)} entries")

    lvds = gen_lvds_routing(nets)
    all_entries.extend(lvds)
    print(f"  LVDS routing: {len(lvds)} entries")

    rf = gen_rf_routing(nets)
    all_entries.extend(rf)
    print(f"  RF routing: {len(rf)} entries")

    pwr = gen_power_routing(nets)
    all_entries.extend(pwr)
    print(f"  Power routing: {len(pwr)} entries")

    io = gen_general_io_routing(nets)
    all_entries.extend(io)
    print(f"  General I/O routing: {len(io)} entries")

    perim = gen_perimeter_via_stitching(nets)
    all_entries.extend(perim)
    print(f"  Perimeter via stitching: {len(perim)} entries")

    silk = gen_silkscreen()
    all_entries.extend(silk)
    print(f"  Silkscreen: {len(silk)} entries")

    total = sum(1 for e in all_entries if e.strip().startswith("("))
    print(f"\nTotal generated entries: {total}")

    # Insert before the final closing paren
    insertion = "\n".join(all_entries) + "\n"
    # Find the last ')' which closes the kicad_pcb
    idx = pcb_text.rfind(")")
    new_pcb = pcb_text[:idx] + "\n" + insertion + "\n" + pcb_text[idx:]

    with open(PCB_FILE, "w") as f:
        f.write(new_pcb)

    print(f"Updated {PCB_FILE}")


if __name__ == "__main__":
    main()
