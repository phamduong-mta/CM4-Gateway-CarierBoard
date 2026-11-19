"""Symbol tự định nghĩa (hình hộp) cho các IC/đầu nối không dùng symbol có sẵn.
Số chân lấy từ datasheet (xem docs/notes/parts-check.md, docs/datasheets/SOURCES.md)."""
import json
import os

from kisch import box

HERE = os.path.dirname(os.path.abspath(__file__))


def cm4():
    """Raspberry Pi CM4: 2 unit (1-100 / 101-200); chân lẻ bên trái, chân chẵn bên phải.
    Tên + kiểu chân lấy từ symbol chính thức trong CM4IO.kicad_sym."""
    pins = {n: (name, et) for n, name, et in json.load(open(os.path.join(HERE, "cm4_pins.json")))}
    # tránh xung đột ERC: mỗi rail ra chỉ một chân power_out
    for n in (86, 90):
        pins[n] = (pins[n][0], "passive")
    # 88 (+1.8V) để hở; 84/86 (+3.3V) để passive vì CH340C có chân V3 kiểu power_out nối cùng rail
    pins[84] = (pins[84][0], "passive")
    pins[88] = (pins[88][0], "power_out")
    units = []
    for base in (0, 100):
        left = [(n, pins[n][0], pins[n][1]) for n in range(base + 1, base + 101, 2)]
        right = [(n, pins[n][0], pins[n][1]) for n in range(base + 2, base + 101, 2)]
        units.append(dict(left=left, right=right))
    return box("RPi_CM4", units, ref="U", desc="Raspberry Pi Compute Module 4 (2x Hirose DF40C-100DS-0.4V)")


def pcie_switch():
    """Diodes PI7C9X2G404SL, LQFP-128-EP 14x14 (DS40068 Rev 5-2, muc 3 + 4.1)."""
    I, O, B, P, PW, NC = "input", "output", "bidirectional", "passive", "power_in", "no_connect"
    u1 = dict(
        left=[(128, "PERP0", I), (127, "PERN0", I), (124, "PETP0", O), (123, "PETN0", O), None,
              (110, "REFCLKP", I), (111, "REFCLKN", I), None,
              (74, "REFCLKI_P", I), (73, "REFCLKI_N", I), None,
              (10, "PERST_L", I), None,
              (116, "REXT", P), (115, "REXT_GND", P), (86, "IREF", P), (60, "CLKBUF_PD", I)],
        right=[(100, "PETP1", O), (101, "PETN1", O), (97, "PERP1", I), (98, "PERN1", I), None,
               (106, "PETP2", O), (107, "PETN2", O), (102, "PERP2", I), (103, "PERN2", I), None,
               (118, "PETP3", O), (117, "PETN3", O), (122, "PERP3", I), (121, "PERN3", I), None,
               (85, "REFCLKO_P0", O), (83, "REFCLKO_N0", O), (81, "REFCLKO_P1", O), (80, "REFCLKO_N1", O),
               (78, "REFCLKO_P2", O), (77, "REFCLKO_N2", O), (76, "REFCLKO_P3", O), (75, "REFCLKO_N3", O), None,
               (5, "DWNRST_L1", O), (6, "DWNRST_L2", O), (7, "DWNRST_L3", O)])
    u2 = dict(
        left=[(18, "VC1_EN", I), (24, "RXPOLINV_DIS", I), (53, "PL_512B", I), (33, "SLOTCLK", I),
              (28, "PWR_SAV", I), None,
              (19, "PRSNT1", I), (20, "PRSNT2", I), (21, "PRSNT3", I), None,
              (45, "SLOT_IMP1", I), (46, "SLOT_IMP2", I), (47, "SLOT_IMP3", I), None,
              (9, "TEST1", I), (16, "TEST2", I), (17, "TEST3", I), (22, "TEST4", I),
              (25, "TEST5", I), (51, "TEST6", I), None,
              (26, "SMBCLK", I), (27, "SMBDATA", B), (70, "EECLK", O), (71, "EEPD", B), (72, "SCAN_EN", B)],
        right=[(36, "GPIO0", B), (35, "GPIO1", B), (37, "GPIO2", B), (38, "GPIO3", B),
               (39, "GPIO4", B), (42, "GPIO5", B), (43, "GPIO6", B), (44, "GPIO7", B), None,
               (67, "PORTSTATUS0", O), (68, "PORTSTATUS1", O), (69, "PORTSTATUS2", O), None,
               (89, "TCK", I), (92, "TMS", I), (88, "TDO", O), (93, "TDI", I), (94, "TRST_L", I), None,
               (48, "NC", NC), (52, "NC", NC), (54, "NC", NC), (57, "NC", NC),
               (58, "NC", NC), (59, "NC", NC), (114, "NC", NC)])
    vss = [2, 4, 11, 12, 30, 32, 34, 41, 50, 56, 61, 63, 66, 87, 90, 95, 104, 120, 126, 129]
    u3 = dict(
        left=[(n, "VDDC", PW) for n in (3, 23, 29, 31, 40, 55, 62, 65, 91)] + [None] +
             [(n, "VDDCAUX", PW) for n in (13, 14)] + [None] +
             [(n, "AVDD", PW) for n in (99, 105, 108, 119, 125)] + [None] +
             [(n, "VDDR", PW) for n in (1, 8, 49, 64, 96)] + [(15, "VAUX", PW)] + [None] +
             [(n, "CVDDR", PW) for n in (79, 82, 84)] + [(113, "AVDDH", PW)],
        right=[(n, "VSS", PW) for n in vss] + [None] + [(n, "CGND", PW) for n in (109, 112)])
    s = box("PI7C9X2G404SL", [u1, u2, u3], ref="U",
            desc="PCIe Gen2 packet switch, 4 cong x 1 lan (1 len + 3 xuong), LQFP-128-EP")
    assert len({p["number"] for p in s.pins}) == 129, len({p["number"] for p in s.pins})
    return s


def rtl8111h():
    """Realtek RTL8111H-CG, QFN-32 4x4 (datasheet rev 1.2, muc 5-6)."""
    I, O, B, P, PW = "input", "output", "bidirectional", "passive", "power_in"
    u = dict(
        left=[(13, "HSIP", I), (14, "HSIN", I), (17, "HSOP", O), (18, "HSON", O), None,
              (15, "REFCLK_P", I), (16, "REFCLK_N", I), None,
              (19, "PERSTB", I), (12, "CLKREQB", B), (20, "ISOLATEB", I), (21, "LANWAKEB", B), None,
              (28, "CKXTAL1", I), (29, "CKXTAL2", P), (31, "RSET", P), None,
              (23, "VDDREG", PW), (11, "AVDD33", PW), (32, "AVDD33", PW)],
        right=[(1, "MDIP0", B), (2, "MDIN0", B), (4, "MDIP1", B), (5, "MDIN1", B),
               (6, "MDIP2", B), (7, "MDIN2", B), (9, "MDIP3", B), (10, "MDIN3", B), None,
               (27, "LED0", O), (26, "LED1", O), (25, "LED2", O), None,
               (24, "REGOUT", P), (22, "DVDD10", P), (3, "AVDD10", P), (8, "AVDD10", P), (30, "AVDD10", P),
               None, (33, "GND", PW)])
    s = box("RTL8111H", [u], ref="U", desc="PCIe -> Gigabit Ethernet (MAC+PHY), LDO 1.0V noi, QFN-32")
    assert len(s.pins) == 33
    return s


def magjack():
    """HanRun HR911130A: RJ45 1000Base-T co bien ap + 2 LED (ban ve HR911130A Rev A)."""
    P = "passive"
    u = dict(
        left=[(2, "MDI0+", P), (3, "MDI0-", P), (4, "MDI1+", P), (7, "MDI1-", P),
              (5, "MDI2+", P), (6, "MDI2-", P), (8, "MDI3+", P), (9, "MDI3-", P), None, (1, "CT", P)],
        right=[(11, "LED_G_A", P), (12, "LED_G_K", P), None, (14, "LED_Y_A", P), (13, "LED_Y_K", P),
               None, (10, "CHS_GND", P), ("SH", "SHIELD", P)])
    return box("HR911130A", [u], ref="J", desc="RJ45 Gigabit co bien ap va LED")


def slb9670():
    """Infineon SLB9670VQ2.0, VQFN-32 5x5 (data sheet muc 3)."""
    I, O, P, PW, NC = "input", "output", "passive", "power_in", "no_connect"
    nci = [1, 3, 4, 5, 10, 11, 12, 13, 14, 15, 16, 25, 26, 27, 28, 31]
    u = dict(
        left=[(20, "CS#", I), (19, "SCLK", I), (21, "MOSI", I), (24, "MISO", O), None,
              (17, "RST#", I), (18, "PIRQ#", "open_collector"), None, (6, "GPIO", P), (7, "PP", P)],
        right=[(8, "VDD", PW), (22, "VDD", PW), None,
               (2, "GND", PW), (9, "GND", PW), (23, "GND", PW), (32, "GND", PW), (33, "GND", PW), None,
               (29, "NC", NC), (30, "NC", NC)] + [(n, "NCI", NC) for n in nci])
    s = box("SLB9670VQ2.0", [u], ref="U", desc="TPM 2.0, SPI, VQFN-32")
    assert len(s.pins) == 33
    return s


def sram():
    """Microchip 23LCV1024, SOIC-8 (DS25156A)."""
    u = dict(left=[(1, "~{CS}", "input"), (6, "SCK", "input"), (5, "SI", "input"), (2, "SO", "output")],
             right=[(8, "VCC", "power_in"), (7, "VBAT", "passive"), (3, "NC", "no_connect"), (4, "VSS", "power_in")])
    return box("23LCV1024", [u], ref="U", desc="SPI SRAM 1 Mbit co chan VBAT")


def rtc():
    """NXP PCF85063AT, SO-8."""
    u = dict(left=[(1, "OSCI", "input"), (2, "OSCO", "output"), None, (6, "SCL", "input"), (5, "SDA", "bidirectional")],
             right=[(8, "VDD", "power_in"), (3, "~{INT}", "open_collector"), (7, "CLKOUT", "output"), None,
                    (4, "VSS", "power_in")])
    return box("PCF85063AT", [u], ref="U", desc="RTC I2C, SO-8")


def pmos_so8():
    """AO4407A, SOIC-8: S=1,2,3  G=4  D=5..8."""
    P = "passive"
    u = dict(left=[(5, "D", P), (6, "D", P), (7, "D", P), (8, "D", P)],
             right=[(1, "S", P), (2, "S", P), (3, "S", P), (4, "G", "input")])
    return box("AO4407A", [u], ref="Q", desc="P-MOSFET 30V 12A SOIC-8 (chong nguoc cuc)")


def dc_jack():
    P = "passive"
    u = dict(right=[(1, "TIP(+)", P), (2, "SLEEVE(-)", P), (3, "SWITCH", P)])
    return box("DC_JACK_5.5x2.1", [u], ref="J", desc="Jack DC 5.5x2.1 mm, tam duong")


def tps2553():
    """TI TPS2553DBV (SOT-23-6): 1 IN, 2 GND, 3 EN, 4 FAULT#, 5 ILIM, 6 OUT."""
    u = dict(left=[(1, "IN", "power_in"), (3, "EN", "input"), (5, "ILIM", "passive")],
             right=[(6, "OUT", "passive"), (4, "~{FAULT}", "open_collector"), (2, "GND", "power_in")])
    return box("TPS2553", [u], ref="U", desc="Cong tac nguon USB co gioi han dong, EN tich cuc cao")
