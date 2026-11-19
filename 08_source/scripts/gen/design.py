#!/usr/bin/env python3
"""Sinh toàn bộ schematic CM4 Security Gateway Rev A.

Chạy:  python3 scripts/gen/design.py      (ghi vào hardware/)
Nguồn sự thật của mạch nguyên lý là file này; các file .kicad_sch được sinh ra từ đây.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parts                                   # noqa: E402
import symdefs                                 # noqa: E402
from kisch import G, Design, stock             # noqa: E402

HW = os.path.normpath(os.path.join(HERE, "..", "..", "hardware"))
PROJECT = "cm4-gateway"
REV = "B"
DATE = "2026-11-18"

POWER_NETS = {"GND", "CHASSIS", "+12V_JACK", "+12V", "+5V", "+3V3", "+3V3_SW", "+1V0"}

FP = dict(
    CM4="cm4-gateway:Raspberry-Pi-4-Compute-Module",
    SWITCH="cm4-gateway:LQFP-128-1EP_14x14mm_P0.4mm_EP5.5x5.5mm",
    NIC="Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm",
    MAGJACK="cm4-gateway:RJ45_Hanrun_HR911130A_Horizontal",
    TPM="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm",
    SO8="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    SOT236="Package_TO_SOT_SMD:SOT-23-6",
    TSOT236="Package_TO_SOT_SMD:TSOT-23-6",
    HSOP8="Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm_ThermalVias",
    MSOP10="Package_SO:MSOP-10_3x3mm_P0.5mm",
    SOIC16="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
    DCJACK="cm4-gateway:BarrelJack_XKB_DC-005-5A",
    USBA="Connector_USB:USB_A_Molex_67643_Horizontal",
    USBC="Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
    MICROUSB="Connector_USB:USB_Micro-B_Molex_47346-0001",
)


def XY(cx, cy):
    return (cx * G, cy * G)


class Ctx:
    """Trợ giúp theo sheet: đánh số tham chiếu, đặt linh kiện thụ động theo danh sách dọc."""

    def __init__(self, sheet, base):
        self.sh = sheet
        self.base = base            # "1".."11" hoặc "{n}" cho sheet đa thể hiện
        self.cnt = {}
        self.cx = self.cy = 0
        self.pitch = 3
        self.grp = ""               # thẻ nhóm bố trí PCB (trường "Group")

    def g(self, name):
        self.grp = name
        return self

    def ref(self, prefix):
        self.cnt[prefix] = self.cnt.get(prefix, 0) + 1
        return "%s%s%02d" % (prefix, self.base, self.cnt[prefix])

    def at(self, cx, cy, pitch=3):
        self.cx, self.cy, self.pitch = cx, cy, pitch
        return self

    def _next(self):
        pos = XY(self.cx, self.cy)
        self.cy += self.pitch
        return pos

    def R(self, val, a, b, dnp=False):
        lcsc, mpn = parts.R[val]
        x, y = self._next()
        return self.sh.part2("Device:R", self.ref("R"), val, x, y, a, b, fp=parts.FP_R0402,
                             lcsc=lcsc, mpn=mpn, dnp=dnp, Group=self.grp)

    def C(self, val, pkg, a, b, dnp=False):
        lcsc, mpn, fp, desc = parts.C[(val, pkg)]
        x, y = self._next()
        return self.sh.part2("Device:C", self.ref("C"), val, x, y, a, b, fp=fp, lcsc=lcsc, mpn=mpn,
                             desc=desc, dnp=dnp, Group=self.grp)

    def P2(self, key, value, a, b, prefix=None, **nets):
        """Linh kiện 2 chân trong parts.P (a -> chân 1, b -> chân 2)."""
        p = parts.P[key]
        sym = stock(p["sym"])
        x, y = self._next()
        return self.sh.part2(sym, self.ref(prefix or sym.ref_prefix), value, x, y, a, b,
                             fp=p["fp"], lcsc=p["lcsc"], mpn=p["mpn"], Group=self.grp)

    def diode(self, key, value, k, a):
        """Diode/LED/Zener nằm ngang: K bên trái, A bên phải."""
        p = parts.P[key]
        x, y = self._next()
        inst = self.sh.add(p["sym"], self.ref("D"), value, (x, y), fp=p["fp"], lcsc=p["lcsc"], mpn=p["mpn"],
                           Group=self.grp)
        inst.net({"K": k, "A": a})
        return inst

    def part(self, key, value, cx, cy, nets, prefix=None, rot=0):
        p = parts.P[key]
        sym = stock(p["sym"])
        inst = self.sh.add(sym, self.ref(prefix or sym.ref_prefix), value, XY(cx, cy), rot=rot,
                           fp=p["fp"], lcsc=p["lcsc"], mpn=p["mpn"], Group=self.grp)
        inst.net(nets)
        return inst

    def ic(self, sym, value, cx, cy, fp, lcsc, mpn, unit=1, ref=None, prefix=None):
        if isinstance(sym, str):
            sym = stock(sym)
        ref = ref or self.ref(prefix or sym.ref_prefix)
        return self.sh.add(sym, ref, value, XY(cx, cy), unit=unit, fp=fp, lcsc=lcsc, mpn=mpn, Group=self.grp)

    def tp(self, net, cx, cy):
        p = parts.P["TP"]
        inst = self.sh.add(p["sym"], self.ref("TP"), net.lstrip(".^"), XY(cx, cy), rot=90, fp=p["fp"],
                           Group=self.grp, _nobom=True)
        inst.net({"1": net})
        return inst

    def flag(self, net, cx, cy):
        self.cnt["#FLG"] = self.cnt.get("#FLG", 0) + 1
        inst = self.sh.add("power:PWR_FLAG", "#FLG%s%02d" % (self.base, self.cnt["#FLG"]), "PWR_FLAG",
                           XY(cx, cy))
        inst.net({"1": net}, stub=G)
        return inst


def check_all_pins(design):
    bad = []
    seen = {}
    for sh in design.sheets:
        for inst in sh.insts:
            key = (sh.filename, inst.ref, inst.unit)
            for p in inst.unassigned():
                bad.append("%s %s unit %d: chan %s (%s) chua gan net" % (sh.filename, inst.ref, inst.unit,
                                                                        p["number"], p["name"]))
            seen.setdefault((sh.filename, inst.ref), set()).add(inst.unit)
            if len(inst.sym.units) > 1:
                pass
    # mọi unit của symbol đa unit phải được đặt
    for sh in design.sheets:
        by_ref = {}
        for inst in sh.insts:
            by_ref.setdefault(inst.ref, (inst.sym, set()))[1].add(inst.unit)
        for ref, (sym, units) in by_ref.items():
            if units != sym.units:
                bad.append("%s %s: thieu unit %s" % (sh.filename, ref, sorted(sym.units - units)))
    if bad:
        raise SystemExit("LOI GAN CHAN:\n  " + "\n  ".join(bad))


# =========================================================================== POWER
def sheet_power(d):
    sh = d.new_sheet("Power", "power.kicad_sch", "Nguồn: vào 12V, bảo vệ, 5V / 3V3_SW / 1V0")
    c = Ctx(sh, "1")

    # ---- đầu vào + bảo vệ
    sh.frame(10 * G, 8 * G, 95 * G, 36 * G, "1. Đầu vào 12 V (9–24 V) và bảo vệ")
    c.g("in")
    j = c.ic(symdefs.dc_jack(), "DC-005-5A-2.0", 22, 18, FP["DCJACK"], "C381116", "DC-005-5A-2.0", prefix="J")
    j.net({"1": "+12V_JACK", "2": "GND", "3": "GND"})
    q = c.ic(symdefs.pmos_so8(), "AO4407A", 60, 18, FP["SO8"], "C16072", "AO4407A", prefix="Q")
    q.net(D=".VIN_FUSED", S="+12V", G=".RP_GATE")
    c.at(22, 25)
    c.P2("FUSE4A", "4A 32V", "+12V_JACK", ".VIN_FUSED", prefix="F")
    c.R("100k", ".RP_GATE", "GND")
    c.diode("BZT52C12", "BZT52C12", "+12V", ".RP_GATE")
    c.at(60, 25)
    c.diode("SMBJ24A", "SMBJ24A", "+12V", "GND")
    x, y = c._next()
    p = parts.P["CE100u"]
    sh.part2(p["sym"], c.ref("C"), "100uF/35V", x, y, "+12V", "GND", fp=p["fp"], lcsc=p["lcsc"], mpn=p["mpn"],
             Group="in")
    c.C("10uF/50V", "1206", "+12V", "GND")
    sh.text("Q101: P-MOSFET chống cắm ngược cực (dẫn khi cực đúng).\n"
            "D101: Zener 12 V bảo vệ cực cổng. D102: TVS 24 V kẹp xung.\n"
            "F101: cầu chì 4 A. Dải vào 9–24 V; danh định adapter 12 V/3 A.", 12 * G, 35.5 * G, size=1.2)

    # ---- chỉ báo / sequencing / test point / cờ nguồn
    sh.frame(98 * G, 8 * G, 160 * G, 36 * G, "2. LED nguồn, PERIPH_EN, điểm đo, cờ ERC")
    c.g("led").at(108, 15)
    c.R("2.2k", "+5V", ".LED_PWR")
    c.diode("LED_R", "PWR (đỏ)", "GND", ".LED_PWR")
    c.g("seq")
    c.R("10k", "+3V3", "PERIPH_EN")
    c.R("100k", "PERIPH_EN", "GND")
    c.C("100nF", "0402", "PERIPH_EN", "GND")
    c.g("tp")
    for i, net in enumerate(["+12V", "+5V", "+3V3", "+3V3_SW"]):
        c.tp(net, 130, 14 + i * 3)
    for i, net in enumerate(["+1V0", "GND", "GND", "PERIPH_EN"]):
        c.tp(net, 146, 14 + i * 3)
    for i, net in enumerate(["+12V_JACK", "+12V", "+5V", "+3V3_SW", "+1V0"]):
        c.flag(net, 122 + i * 8, 31)
    sh.text("PERIPH_EN: +3V3 của CM4 bật hai buck ngoại vi\n→ không chân nào của CM4 có điện trước CM4.",
            100 * G, 35.5 * G, size=1.2)

    # ---- buck 5V
    sh.frame(10 * G, 38 * G, 160 * G, 68 * G, "3. Buck 12 V → +5V / 5 A  (TPS54560B, 400 kHz)")
    c.g("b5")
    u = c.ic("Regulator_Switching:TPS54560BDDA", "TPS54560BDDAR", 75, 52, FP["HSOP8"], "C1850354",
             "TPS54560BDDAR")
    u.net({"VIN": "+12V", "EN": ".EN_5V", "RT/CLK": ".RT_5V", "COMP": ".COMP_5V", "FB": ".FB_5V",
           "BOOT": ".BOOT_5V", "SW": ".SW_5V", "GND": "GND"})
    c.at(26, 44)
    c.C("10uF/50V", "1206", "+12V", "GND")
    c.C("10uF/50V", "1206", "+12V", "GND")
    c.C("100nF/50V", "0402", "+12V", "GND")
    c.R("300k", "+12V", ".EN_5V")
    c.R("51k", ".EN_5V", "GND")
    c.R("243k", ".RT_5V", "GND")
    c.R("13k", ".COMP_5V", ".COMP_RC")
    c.C("4.7nF", "0402", ".COMP_RC", "GND")
    c.at(50, 62)
    c.C("47pF", "0402", ".COMP_5V", "GND")
    c.at(110, 44)
    c.C("100nF", "0402", ".BOOT_5V", ".SW_5V")
    c.diode("B560C", "B560C", ".SW_5V", "GND")
    c.P2("10uH", "10uH 7.8A", ".SW_5V", "+5V")
    c.R("53.6k", "+5V", ".FB_5V")
    c.R("10.2k", ".FB_5V", "GND")
    c.at(138, 44)
    for _ in range(4):
        c.C("47uF", "1206", "+5V", "GND")
    c.C("100nF", "0402", "+5V", "GND")
    sh.text("UVLO: bật ~7.9 V, tắt ~6.9 V (300k/51k).  Vout = 0.8 V × (1 + 53.6k/10.2k) = 5.00 V.\n"
            "Bù: 13k + 4.7 nF // 47 pF (tần số cắt ~19 kHz).  Diode bắt B560C 60 V/5 A.",
            60 * G, 67.5 * G, size=1.2)

    # ---- buck 3V3_SW và 1V0
    def small_buck(cx, cy, tag, rail, rtop, title):
        sh.frame((cx - 30) * G, (cy - 11) * G, (cx + 30) * G, (cy + 23) * G, title)
        c.g("b" + tag)
        u = c.ic("Regulator_Switching:TPS563201", "TPS563201DDCR", cx, cy, FP["TSOT236"], "C116592",
                 "TPS563201DDCR")
        u.net({"VIN": "+5V", "EN": "PERIPH_EN", "SW": ".SW_" + tag, "VBST": ".BST_" + tag,
               "VFB": ".FB_" + tag, "GND": "GND"})
        c.at(cx - 16, cy + 7)
        c.C("22uF", "0805", "+5V", "GND")
        c.C("100nF", "0402", "+5V", "GND")
        c.C("100nF", "0402", ".BST_" + tag, ".SW_" + tag)
        c.P2("2.2uH", "2.2uH 4.5A", ".SW_" + tag, rail)
        c.at(cx + 16, cy + 7)
        c.R(rtop, rail, ".FB_" + tag)
        c.R("10k", ".FB_" + tag, "GND")
        c.C("22uF", "0805", rail, "GND")
        c.C("22uF", "0805", rail, "GND")
        c.C("100nF", "0402", rail, "GND")

    small_buck(40, 80, "3V3", "+3V3_SW", "33.2k", "4. Buck +5V → +3V3_SW / 3 A (NIC + switch)")
    small_buck(104, 80, "1V0", "+1V0", "3.4k", "5. Buck +5V → +1V0 / 3 A (lõi PCIe switch)")
    sh.text("Vout = 0.768 V × (1 + Rtop/10k):\n33.2k → 3.32 V;  3.4k → 1.03 V.", 56 * G, 75 * G, size=1.2)

    return sh


# =========================================================================== CM4
def sheet_cm4(d):
    sh = d.new_sheet("CM4", "cm4.kicad_sch", "Raspberry Pi CM4 và mạch phụ trợ", paper="A2")
    c = Ctx(sh, "2")
    cm4 = symdefs.cm4()
    ref = c.ref("U")

    # ------------------------------------------------ unit A: chân 1..100
    a = sh.add(cm4, ref, "CM4 (eMMC, không WiFi)", XY(40, 48), unit=1, fp=FP["CM4"], lcsc="C3642394",
               mpn="DF40C-100DS-0.4V(58)", Group="cm4")
    gnd_a = [1, 2, 7, 8, 13, 14, 22, 23, 32, 33, 42, 43, 52, 53, 59, 60, 65, 66, 71, 74, 98]
    netsA = {n: "GND" for n in gnd_a}
    netsA.update({
        3: "WAN_MDI3_P", 5: "WAN_MDI3_N", 4: "WAN_MDI1_P", 6: "WAN_MDI1_N",
        11: "WAN_MDI2_P", 9: "WAN_MDI2_N", 12: "WAN_MDI0_P", 10: "WAN_MDI0_N",
        15: "WAN_LED_G", 17: "WAN_LED_Y", 19: "NC", 16: "NC", 18: "NC",
        20: "EEPROM_nWP", 21: "LED_nACT",
        24: "NC", 25: "NC", 26: "NC", 27: "NC", 28: "NC", 29: "NC", 30: "NC", 31: "NC",   # GPIO26,21,19,20,13,16,6,12
        34: "NC", 35: "NC", 36: "NC",                                                      # GPIO5, ID_SC, ID_SD
        37: "TPM_CS_N", 38: "SPI_SCLK", 39: "SRAM_CS_N", 40: "SPI_MISO", 41: "NC",        # GPIO7,11,8,9,25
        44: "SPI_MOSI", 45: "TPM_PIRQ_N", 46: "NC", 47: "TAMPER_OPEN", 48: "NC",          # GPIO10,24,22,23,27
        49: "FAN_PWM", 50: "LED_STATUS", 51: "UART_RXD", 54: "NC", 55: "UART_TXD",        # GPIO18,17,15,4,14
        56: "NC", 58: "NC",                                                                 # GPIO3, GPIO2
        57: "NC", 61: "NC", 62: "NC", 63: "NC", 64: "NC", 67: "NC", 68: "NC", 69: "NC", 70: "NC", 72: "NC",
        73: "NC", 75: "NC", 76: "NC",
        77: "+5V", 79: "+5V", 81: "+5V", 83: "+5V", 85: "+5V", 87: "+5V",
        78: "+3V3", 84: "+3V3", 86: "+3V3", 88: "NC", 90: "NC",
        80: "RTC_SCL", 82: "RTC_SDA",
        89: "NC", 91: "NC", 92: "RUN_PG", 93: "nRPIBOOT", 94: "NC", 95: "NC", 96: "NC", 97: "NC",
        99: "GLOBAL_EN", 100: "nEXTRST",
    })
    a.net(netsA)

    # ------------------------------------------------ unit B: chân 101..200
    b = sh.add(cm4, ref, "CM4 (eMMC, không WiFi)", XY(108, 48), unit=2, fp=FP["CM4"], lcsc="C3642394",
               mpn="DF40C-100DS-0.4V(58)", Group="cm4")
    gnd_b = [107, 108, 113, 114, 119, 120, 125, 126, 131, 132, 137, 138, 144, 150, 155, 156, 161, 162,
             167, 168, 173, 174, 179, 180, 185, 186, 191, 192, 197, 198]
    netsB = {n: "GND" for n in gnd_b}
    netsB.update({101: "GND",                      # USB_OTG_ID: vai trò cố định -> nối GND (datasheet 2.4)
                  102: ".PCIE_CLKREQ_N", 103: "USB_DN", 105: "USB_DP", 104: "NC", 106: "NC",
                  109: "PCIE_RST_N", 110: "PCIE_CLK_P", 112: "PCIE_CLK_N", 111: "NC",
                  116: "PCIE_RX_N", 118: "PCIE_RX_P", 122: "PCIE_TX_P", 124: "PCIE_TX_N"})
    for n in range(101, 201):
        netsB.setdefault(n, "NC")                  # CSI/DSI/HDMI không dùng
    b.net(netsB)

    # ------------------------------------------------ mạch phụ trợ
    X0 = 152
    X1 = 192
    sh.frame((X0 - 4) * G, 8 * G, (X0 + 34) * G, 44 * G, "Điều khiển & LED")
    c.g("ctl").at(X0 + 8, 16)
    c.R("470R", "+3V3", ".LED_ACT_A")
    c.diode("LED_G", "ACT (xanh)", "LED_nACT", ".LED_ACT_A")
    c.R("470R", "LED_STATUS", ".LED_STA_A")
    c.diode("LED_G", "STATUS (xanh)", "GND", ".LED_STA_A")
    c.g("pcieglue")
    c.R("10k", "+3V3", "nRPIBOOT")
    c.R("0R", ".PCIE_CLKREQ_N", "GND")
    c.R("100k", "PCIE_RST_N", "GND")
    c.g("ctl")
    c.R("220R", "RUN_PG", ".RST_BTN")
    c.part("TACT", "RESET", X0 + 8, 41, {"1": ".RST_BTN", "2": "GND"}, prefix="SW")

    sh.frame((X0 - 4) * G, 47 * G, (X0 + 34) * G, 72 * G, "Jumper / header")
    c.g("jmp")
    c.part("HDR2", "EEPROM_WP (đóng = khóa ghi)", X0 + 8, 54, {"1": "EEPROM_nWP", "2": "GND"}, prefix="JP")
    c.part("HDR2", "PWR_BTN (GLOBAL_EN)", X0 + 8, 62, {"1": "GLOBAL_EN", "2": "GND"}, prefix="J")
    c.tp("RUN_PG", X0 + 22, 68)
    c.tp("PCIE_RST_N", X0 + 8, 68)

    sh.frame((X0 - 4) * G, 75 * G, (X0 + 34) * G, 104 * G, "Quạt 5 V (tùy chọn, PWM GPIO18)")
    c.g("fan")
    c.part("HDR2", "FAN 5V", X0 + 8, 82, {"1": "+5V", "2": ".FAN_N"}, prefix="J")
    qf = c.part("AO3400A", "AO3400A", X0 + 20, 82, {"G": ".FAN_G", "D": ".FAN_N", "S": "GND"})
    c.at(X0 + 8, 92)
    c.R("100R", "FAN_PWM", ".FAN_G")
    c.R("10k", ".FAN_G", "GND")
    c.diode("1N4148WS", "1N4148WS", "+5V", ".FAN_N")

    sh.frame((X1 - 4) * G, 75 * G, (X1 + 36) * G, 104 * G,
             "Phân cực lại clock PCIe → REFCLKI SW1")
    c.g("clkbias").at(X1 + 10, 84)
    c.R("10k", "+3V3_SW", "PCIE_CLK_P")
    c.R("1.37k", "PCIE_CLK_P", "GND")
    c.R("10k", "+3V3_SW", "PCIE_CLK_N")
    c.R("1.37k", "PCIE_CLK_N", "GND")
    sh.text("Vcm = 3.3 V × 1.37k/(10k+1.37k) = 0.40 V\n(datasheet PI7C9X2G404SL bảng 8-1, ghi chú 4).",
            (X1 - 2) * G, 101 * G, size=1.2)

    sh.frame((X1 - 4) * G, 47 * G, (X1 + 36) * G, 72 * G, "Decoupling tại đầu nối CM4")
    c.g("dec").at(X1 + 10, 55)
    c.C("47uF", "1206", "+5V", "GND")
    c.C("100nF", "0402", "+5V", "GND")
    c.C("10uF", "0603", "+3V3", "GND")
    c.C("100nF", "0402", "+3V3", "GND")

    # lỗ bắt vít bo (M3) nối CHASSIS
    sh.frame((X1 - 4) * G, 8 * G, (X1 + 36) * G, 44 * G, "Lỗ bắt vít M3")
    for i in range(4):
        p = parts.P["HOLE"]
        h = sh.add(p["sym"], c.ref("H"), "M3", XY(X1 + 10, 16 + i * 7), fp=p["fp"], Group="holes", _nobom=True)
        h.net({"1": "CHASSIS"})

    sh.text("Chân không dùng (HDMI, CSI, DSI, SD, GPIO dư, WL/BT) để hở theo khuyến nghị datasheet CM4.\n"
            "USB_OTG_ID nối GND: vai trò USB cố định (host khi chạy, device khi rpiboot).\n"
            "PCIe_CLK_nREQ kéo GND qua 0R: CM4 luôn phát clock 100 MHz.",
            20 * G, 92 * G, size=1.5)
    return sh


# =========================================================================== WAN
def magjack_block(sh, c, cx, cy, mdi, led_g_k, led_y_k, led_rail, ct_net):
    """Đặt 1 cổng HR911130A + tụ điểm giữa + điện trở LED. mdi: 8 net theo thứ tự chân."""
    c.g("jack")
    j = c.ic(symdefs.magjack(), "HR911130A", cx, cy, FP["MAGJACK"], "C54408", "HR911130A", prefix="J")
    names = ["MDI0+", "MDI0-", "MDI1+", "MDI1-", "MDI2+", "MDI2-", "MDI3+", "MDI3-"]
    nets = dict(zip(names, mdi))
    nets.update({"CT": ct_net, "LED_G_A": ".LED_G_A", "LED_G_K": led_g_k,
                 "LED_Y_A": ".LED_Y_A", "LED_Y_K": led_y_k, "CHS_GND": "CHASSIS", "SHIELD": "CHASSIS"})
    j.net(nets)
    c.at(cx + 28, cy - 4)
    c.R("470R", led_rail, ".LED_G_A")
    c.R("470R", led_rail, ".LED_Y_A")
    c.C("100nF", "0402", ct_net, "GND")
    return j


def sheet_wan(d):
    sh = d.new_sheet("WAN", "wan.kicad_sch", "Cổng WAN (PHY Gigabit trên CM4) + nối đất vỏ", paper="A4")
    c = Ctx(sh, "3")
    sh.frame(10 * G, 10 * G, 82 * G, 40 * G, "RJ45 WAN — HR911130A")
    mdi = ["WAN_MDI0_P", "WAN_MDI0_N", "WAN_MDI1_P", "WAN_MDI1_N",
           "WAN_MDI2_P", "WAN_MDI2_N", "WAN_MDI3_P", "WAN_MDI3_N"]
    magjack_block(sh, c, 36, 24, mdi, "WAN_LED_G", "WAN_LED_Y", "+3V3", ".WAN_CT")
    sh.text("LED tích cực thấp do PHY của CM4 kéo (nLED3/activity = xanh, nLED2/speed = vàng).\n"
            "Điểm giữa biến áp (chân 1) nối GND qua 100 nF (PHY kiểu điện áp).", 12 * G, 39 * G, size=1.3)
    sh.frame(10 * G, 44 * G, 82 * G, 62 * G, "CHASSIS ↔ GND (vỏ RJ45/USB, lỗ vít)")
    c.g("chs").at(30, 51)
    c.R("1M", "CHASSIS", "GND")
    c.C("4.7nF/2kV", "1206", "CHASSIS", "GND")
    c.flag("CHASSIS", 56, 56)
    return sh


# =========================================================================== PCIe switch (x2)
def sheet_switch(d):
    sh = d.new_sheet("PCIeSwitch", "pcie_switch.kicad_sch",
                     "PCIe switch PI7C9X2G404SL (dùng 2 lần: SW1, SW2)", paper="A2",
                     instance_numbers=[("SW1", 4), ("SW2", 5)])
    c = Ctx(sh, "{n}")
    sym = symdefs.pcie_switch()
    ref = c.ref("U")
    kw = dict(fp=FP["SWITCH"], lcsc="C500767", mpn="PI7C9X2G404SLBFDEX")

    # ------------------------------------------------ unit 1: PCIe
    sh.frame(8 * G, 8 * G, 150 * G, 80 * G, "A. Làn PCIe, clock, reset")
    kw["Group"] = "ic"
    u1 = sh.add(sym, ref, "PI7C9X2G404SL", XY(50, 34), unit=1, **kw)
    # ĐẢO CỰC CÓ CHỦ ĐÍCH (giai đoạn 2): mọi đầu THU PCIe (PERPx/PERNx) nối chéo P<->N.
    # Thứ tự chân của IC làm mọi làn TX->RX bị bắt chéo nếu nối thẳng; PCIe bắt buộc đầu thu tự nhận đảo cực
    # (Lane Polarity Inversion). Clock KHÔNG đảo cực. Xem docs/notes/decisions.md.
    u1.net({"PERP0": "^UP_RX_N", "PERN0": "^UP_RX_P", "PETP0": ".UP_TXC_P", "PETN0": ".UP_TXC_N",
            "REFCLKP": ".SELFCLK_P", "REFCLKN": ".SELFCLK_N",
            "REFCLKI_P": "^CLKIN_P", "REFCLKI_N": "^CLKIN_N", "PERST_L": "^PERST_N",
            "REXT": ".REXT", "REXT_GND": ".REXT_GND", "IREF": ".IREF", "CLKBUF_PD": ".CLKBUF_PD",
            "PETP1": ".DN1_TXC_P", "PETN1": ".DN1_TXC_N", "PERP1": "^DN1_RX_N", "PERN1": "^DN1_RX_P",
            "PETP2": ".DN2_TXC_P", "PETN2": ".DN2_TXC_N", "PERP2": "^DN2_RX_N", "PERN2": "^DN2_RX_P",
            "PETP3": ".DN3_TXC_P", "PETN3": ".DN3_TXC_N", "PERP3": "^DN3_RX_N", "PERN3": "^DN3_RX_P",
            "REFCLKO_P0": ".CLKO0_P", "REFCLKO_N0": ".CLKO0_N", "REFCLKO_P1": ".CLKO1_P", "REFCLKO_N1": ".CLKO1_N",
            "REFCLKO_P2": ".CLKO2_P", "REFCLKO_N2": ".CLKO2_N", "REFCLKO_P3": ".CLKO3_P", "REFCLKO_N3": ".CLKO3_N",
            "DWNRST_L1": "^DNRST1_N", "DWNRST_L2": "^DNRST2_N", "DWNRST_L3": "^DNRST3_N"})
    # tụ ghép AC phía phát (TX) của switch
    c.g("txc").at(96, 14)
    for a_, b_ in ((".UP_TXC_P", "^UP_TX_P"), (".UP_TXC_N", "^UP_TX_N"),
                   (".DN1_TXC_P", "^DN1_TX_P"), (".DN1_TXC_N", "^DN1_TX_N"),
                   (".DN2_TXC_P", "^DN2_TX_P"), (".DN2_TXC_N", "^DN2_TX_N"),
                   (".DN3_TXC_P", "^DN3_TX_P"), (".DN3_TXC_N", "^DN3_TX_N")):
        c.C("100nF", "0402", a_, b_)
    # tham chiếu / strap của khối PCIe
    c.g("ref").at(96, 40)
    c.R("1.43k", ".REXT", ".REXT_GND")
    c.R("475R", ".IREF", "GND")
    c.R("330R", ".CLKBUF_PD", "GND")
    # clock: REFCLKO0 quay về REFCLKP/N của chính chip (ghép AC), REFCLKO1..3 ra ngoài
    c.g("clk").at(124, 14)
    for i, (op, on) in enumerate(((".SELFT_P", ".SELFT_N"), ("^CLK1_P", "^CLK1_N"),
                                  ("^CLK2_P", "^CLK2_N"), ("^CLK3_P", "^CLK3_N"))):
        c.R("33R", ".CLKO%d_P" % i, op)
        c.R("49.9R", op, "GND")
        c.R("33R", ".CLKO%d_N" % i, on)
        c.R("49.9R", on, "GND")
    c.g("selfc").at(96, 52)
    c.C("100nF", "0402", ".SELFT_P", ".SELFCLK_P")
    c.C("100nF", "0402", ".SELFT_N", ".SELFCLK_N")
    sh.text("Clock: CLKIN (100 MHz) → bộ đệm tích hợp → REFCLKO0..3 (HCSL, Rs 33 Ω + Rp 49.9 Ω).\n"
            "REFCLKO0 quay về REFCLKP/N của chính switch qua tụ 100 nF; REFCLKO1..3 cấp cho thiết bị phía dưới.\n"
            "Tụ AC 100 nF đặt sát chân phát (PETx). Phía thu của switch nhận tụ AC đặt ở thiết bị phát đối diện.",
            10 * G, 78 * G, size=1.4)

    # ------------------------------------------------ unit 2: cấu hình
    sh.frame(8 * G, 84 * G, 150 * G, 150 * G, "B. Strap, test, JTAG, GPIO")
    u2 = sh.add(sym, ref, "PI7C9X2G404SL", XY(50, 116), unit=2, **kw)
    u2.net({"SLOTCLK": ".SLOTCLK", "PWR_SAV": ".PWR_SAV",
            "TEST1": ".TEST1", "TEST2": ".TEST2", "TEST3": ".TEST3", "TEST4": ".TEST4",
            "TEST5": ".TEST5", "TEST6": ".TEST6",
            "SMBCLK": ".SMBCLK", "SMBDATA": ".SMBDATA", "EEPD": ".EEPD",
            "TMS": ".TMS", "TRST_L": ".TRST"})
    u2.nc("VC1_EN", "RXPOLINV_DIS", "PL_512B", "PRSNT1", "PRSNT2", "PRSNT3",
          "SLOT_IMP1", "SLOT_IMP2", "SLOT_IMP3", "EECLK", "SCAN_EN",
          "GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO6", "GPIO7",
          "PORTSTATUS0", "PORTSTATUS1", "PORTSTATUS2", "TCK", "TDO", "TDI", "NC")
    c.g("strap").at(100, 92)
    c.R("5.1k", "+3V3_SW", ".SLOTCLK")
    c.R("330R", ".PWR_SAV", "GND")
    c.R("5.1k", "+3V3_SW", ".TEST1")
    c.R("5.1k", "+3V3_SW", ".TEST2")
    c.R("330R", ".TEST3", "GND")
    c.R("330R", ".TEST4", "GND")
    c.R("330R", ".TEST5", "GND")
    c.R("330R", ".TEST6", "GND")
    c.at(128, 92)
    c.R("5.1k", "+3V3_SW", ".SMBCLK")
    c.R("5.1k", "+3V3_SW", ".SMBDATA")
    c.R("5.1k", "+3V3_SW", ".EEPD")
    c.R("330R", ".TMS", "GND")
    c.R("330R", ".TRST", "GND")
    sh.text("Các chân strap có điện trở kéo xuống nội (VC1_EN, RXPOLINV_DIS, PL_512B, PRSNTx, SLOT_IMPx) để hở:\n"
            "mặc định = VC1 tắt, payload 256 B, thiết bị \"có mặt\", nối chip-chip. SLOTCLK kéo lên: dùng chung clock nền.\n"
            "Không dùng EEPROM/SMBus/JTAG ở Rev A (kéo theo đúng mục 3.3–3.4 datasheet).",
            10 * G, 148 * G, size=1.4)

    # ------------------------------------------------ unit 3: nguồn
    sh.frame(154 * G, 8 * G, 226 * G, 150 * G, "C. Nguồn và decoupling")
    u3 = sh.add(sym, ref, "PI7C9X2G404SL", XY(176, 34), unit=3, **kw)
    u3.net({"VDDC": "+1V0", "VDDCAUX": "+1V0", "AVDD": ".AVDD_1V0", "VDDR": "+3V3_SW", "VAUX": "+3V3_SW",
            "CVDDR": ".CVDD_3V3", "AVDDH": ".AVDDH_3V3", "VSS": "GND", "CGND": "GND"})
    c.g("avdd").at(166, 66)
    c.P2("FB120", "120R@100MHz 2A", "+1V0", ".AVDD_1V0")
    c.C("10uF", "0603", ".AVDD_1V0", "GND")
    for _ in range(5):
        c.C("100nF", "0402", ".AVDD_1V0", "GND")
    c.g("cvdd")
    c.P2("FB120", "120R@100MHz 2A", "+3V3_SW", ".CVDD_3V3")
    c.C("4.7uF", "0603", ".CVDD_3V3", "GND")
    for _ in range(3):
        c.C("100nF", "0402", ".CVDD_3V3", "GND")
    c.g("avddh")
    c.P2("FB120", "120R@100MHz 2A", "+3V3_SW", ".AVDDH_3V3")
    c.C("1uF", "0402", ".AVDDH_3V3", "GND")
    c.C("100nF", "0402", ".AVDDH_3V3", "GND")
    c.g("v10").at(194, 66)
    c.C("10uF", "0603", "+1V0", "GND")
    c.C("10uF", "0603", "+1V0", "GND")
    for _ in range(11):
        c.C("100nF", "0402", "+1V0", "GND")
    c.g("v33").at(214, 66)
    c.C("10uF", "0603", "+3V3_SW", "GND")
    for _ in range(6):
        c.C("100nF", "0402", "+3V3_SW", "GND")
    c.g("strap")
    c.tp(".AVDD_1V0", 200, 140)
    c.flag(".AVDD_1V0", 162, 144)
    c.flag(".CVDD_3V3", 174, 144)
    c.flag(".AVDDH_3V3", 186, 144)
    return sh


# =========================================================================== LAN NIC (x4)
def sheet_nic(d):
    sh = d.new_sheet("LAN_NIC", "lan_nic.kicad_sch", "Cổng LAN: RTL8111H + RJ45 (dùng 4 lần)", paper="A3",
                     instance_numbers=[("LAN1", 6), ("LAN2", 7), ("LAN3", 8), ("LAN4", 9)])
    c = Ctx(sh, "{n}")
    sh.frame(8 * G, 8 * G, 100 * G, 70 * G, "A. RTL8111H — PCIe ↔ Gigabit Ethernet")
    c.g("ic")
    u = c.ic(symdefs.rtl8111h(), "RTL8111H-CG", 50, 30, FP["NIC"], "C2761340", "RTL8111H-CG")
    mdi = [".MDI0_P", ".MDI0_N", ".MDI1_P", ".MDI1_N", ".MDI2_P", ".MDI2_N", ".MDI3_P", ".MDI3_N"]
    u.net({"HSIP": "^RX_N", "HSIN": "^RX_P", "HSOP": ".HSO_P", "HSON": ".HSO_N",
           "REFCLK_P": "^CLK_P", "REFCLK_N": "^CLK_N", "PERSTB": "^PERST_N",
           "CLKREQB": ".CLKREQ_N", "ISOLATEB": ".ISOLATE_N", "LANWAKEB": ".LANWAKE_N",
           "CKXTAL1": ".XTAL1", "CKXTAL2": ".XTAL2", "RSET": ".RSET",
           "VDDREG": "+3V3_SW", "AVDD33": "+3V3_SW",
           "MDIP0": mdi[0], "MDIN0": mdi[1], "MDIP1": mdi[2], "MDIN1": mdi[3],
           "MDIP2": mdi[4], "MDIN2": mdi[5], "MDIP3": mdi[6], "MDIN3": mdi[7],
           "LED0": "NC", "LED1": ".LED_Y_K", "LED2": ".LED_G_K",
           "REGOUT": ".V1P0", "DVDD10": ".V1P0", "AVDD10": ".V1P0", "GND": "GND"})
    c.g("txc").at(18, 46)
    c.C("100nF", "0402", ".HSO_P", "^TX_P")
    c.C("100nF", "0402", ".HSO_N", "^TX_N")
    c.g("strap")
    c.R("10k", "+3V3_SW", ".CLKREQ_N")
    c.R("10k", "+3V3_SW", ".LANWAKE_N")
    c.R("1k", "+3V3_SW", ".ISOLATE_N")
    c.R("15k", ".ISOLATE_N", "GND")
    c.R("2.49k", ".RSET", "GND")
    c.g("xtal")
    y = c.part("XTAL25M", "25MHz 12pF", 50, 54, {"1": ".XTAL1", "3": ".XTAL2", "G": "GND"}, prefix="Y")
    c.at(46, 60)
    c.C("18pF", "0402", ".XTAL1", "GND")
    c.C("18pF", "0402", ".XTAL2", "GND")
    c.g("v10").at(80, 44)
    c.C("4.7uF", "0603", ".V1P0", "GND")
    for _ in range(4):
        c.C("100nF", "0402", ".V1P0", "GND")
    c.g("v33").at(80, 14, pitch=3)
    c.C("4.7uF", "0603", "+3V3_SW", "GND")
    for _ in range(3):
        c.C("100nF", "0402", "+3V3_SW", "GND")
    c.g("strap")
    c.tp(".V1P0", 80, 62)
    c.flag(".V1P0", 92, 66)
    sh.text("LED mặc định (tích cực thấp): LED2 = link/act 1000M → LED xanh; LED1 = link/act 100M → LED vàng.\n"
            "ISOLATEB kéo lên 3V3 (1k/15k): chip luôn nối bus. CLKREQB/LANWAKEB chỉ kéo lên (không dùng).\n"
            "RTL8111H dùng LDO nội 1.0 V (REGOUT) — không cấp rail này cho linh kiện khác.",
            10 * G, 69 * G, size=1.3)

    sh.frame(104 * G, 8 * G, 160 * G, 70 * G, "B. RJ45 — HR911130A")
    magjack_block(sh, c, 122, 24, mdi, ".LED_G_K", ".LED_Y_K", "+3V3_SW", ".CT")
    return sh


# =========================================================================== USB + debug
def sheet_usb(d):
    sh = d.new_sheet("USB_Debug", "usb_debug.kicad_sch", "USB host, cổng nạp eMMC, console UART", paper="A3")
    c = Ctx(sh, "10")

    sh.frame(8 * G, 8 * G, 78 * G, 56 * G, "A. USB mux + công tắc BOOT")
    c.g("mux")
    u = c.ic("Interface_USB:FSUSB42MUX", "FSUSB42MUX", 34, 24, FP["MSOP10"], "C11355", "FSUSB42MUX")
    u.net({"VCC": "+3V3", "GND": "GND", "SEL": "nRPIBOOT", "~{OE}": "GND",
           "D+": "USB_DP", "D-": "USB_DN",
           "HSD1+": ".USBC_DP", "HSD1-": ".USBC_DN", "HSD2+": ".USBA_DP", "HSD2-": ".USBA_DN"})
    sw = c.part("SLIDE", "BOOT (PCM12)", 34, 44, {"B": "nRPIBOOT", "A": "GND", "C": "NC"}, prefix="SW")
    c.at(60, 40)
    c.C("100nF", "0402", "+3V3", "GND")
    sh.text("SEL = nRPIBOOT:\n  cao (bình thường) → HSD2 = USB-A (host)\n  thấp (BOOT) → HSD1 = USB-C (rpiboot)\n"
            "Công tắc BOOT nằm bên trong vỏ.", 10 * G, 54 * G, size=1.3)

    sh.frame(82 * G, 8 * G, 160 * G, 56 * G, "B. USB-A host (VBUS giới hạn ~1.2 A)")
    c.g("usba")
    ja = c.ic("Connector:USB_A", "USB-A 67643-2910", 96, 22, FP["USBA"], "C564920", "67643-2910", prefix="J")
    ja.net({"VBUS": ".USBA_VBUS", "D+": ".USBA_CON_DP", "D-": ".USBA_CON_DN", "GND": "GND", "Shield": "CHASSIS"})
    e1 = c.ic("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", 126, 22, FP["SOT236"], "C7519", "USBLC6-2SC6")
    e1.net({"3": ".USBA_CON_DP", "4": ".USBA_DP", "1": ".USBA_CON_DN", "6": ".USBA_DN",   # kênh chọn để cặp không bắt chéo
            "VBUS": ".USBA_VBUS", "GND": "GND"})
    ps = c.ic(symdefs.tps2553(), "TPS2553DBVR", 110, 42, FP["SOT236"], "C55266", "TPS2553DBVR")
    ps.net({"IN": "+5V", "EN": ".USBA_EN", "ILIM": ".USBA_ILIM", "OUT": ".USBA_VBUS", "~{FAULT}": "NC", "GND": "GND"})
    c.at(140, 34)
    c.R("10k", "+3V3", ".USBA_EN")
    c.R("22k", ".USBA_ILIM", "GND")
    c.C("100nF", "0402", "+5V", "GND")
    c.C("47uF", "1206", ".USBA_VBUS", "GND")
    c.C("47uF", "1206", ".USBA_VBUS", "GND")
    c.C("100nF", "0402", ".USBA_VBUS", "GND")
    c.flag(".USBA_VBUS", 150, 52)

    sh.frame(8 * G, 60 * G, 78 * G, 112 * G, "C. USB-C (chỉ dữ liệu, dùng nạp eMMC bằng rpiboot)")
    c.g("usbc")
    jc = c.ic("Connector:USB_C_Receptacle_USB2.0_16P", "USB4105-GF-A", 24, 86, FP["USBC"], "C3020560",
              "USB4105-GF-A", prefix="J")
    jc.net({"GND": "GND", "SHIELD": "CHASSIS", "VBUS": ".USBC_VBUS", "CC1": ".USBC_CC1", "CC2": ".USBC_CC2",
            "D+": ".USBC_CON_DP", "D-": ".USBC_CON_DN", "SBU1": "NC", "SBU2": "NC"})
    e2 = c.ic("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", 58, 72, FP["SOT236"], "C7519", "USBLC6-2SC6")
    e2.net({"3": ".USBC_CON_DP", "4": ".USBC_DP", "1": ".USBC_CON_DN", "6": ".USBC_DN",
            "VBUS": ".USBC_VBUS", "GND": "GND"})
    c.at(56, 86)
    c.R("5.1k", ".USBC_CC1", "GND")
    c.R("5.1k", ".USBC_CC2", "GND")
    c.R("100k", ".USBC_VBUS", "GND")
    c.C("100nF", "0402", ".USBC_VBUS", "GND")
    c.tp(".USBC_VBUS", 56, 100)
    sh.text("VBUS của USB-C KHÔNG nối vào rail +5V của bo (tránh máy tính cấp ngược).\n"
            "Khi nạp eMMC, bo vẫn cấp nguồn bằng jack 12 V.", 10 * G, 110 * G, size=1.3)

    sh.frame(82 * G, 60 * G, 160 * G, 112 * G, "D. Console UART — micro-USB → CH340C → GPIO14/15")
    c.g("dbg")
    jm = c.ic("Connector:USB_B_Micro", "micro-USB 47346-0001", 94, 78, FP["MICROUSB"], "C132560",
              "47346-0001", prefix="J")
    jm.net({"VBUS": ".DBG_VBUS", "D+": ".DBG_CON_DP", "D-": ".DBG_CON_DN", "ID": "NC", "GND": "GND",
            "Shield": "CHASSIS"})
    e3 = c.ic("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", 114, 68, FP["SOT236"], "C7519", "USBLC6-2SC6")
    e3.net({"1": ".DBG_CON_DP", "6": ".DBG_DP", "3": ".DBG_CON_DN", "4": ".DBG_DN",
            "VBUS": ".DBG_VBUS", "GND": "GND"})
    ch = c.ic("Interface_USB:CH340C", "CH340C", 128, 90, FP["SOIC16"], "C84681", "CH340C")
    ch.net({"VCC": "+3V3", "V3": "+3V3", "GND": "GND", "UD+": ".DBG_DP", "UD-": ".DBG_DN",
            "TXD": ".CH_TXD", "RXD": ".CH_RXD", "R232": "NC",
            "~{CTS}": "NC", "~{DSR}": "NC", "~{RI}": "NC", "~{DCD}": "NC", "~{DTR}": "NC", "~{RTS}": "NC"})
    ch.nc("7", "8")
    c.at(96, 93)
    c.R("470R", ".CH_TXD", "UART_RXD")
    c.R("470R", "UART_TXD", ".CH_RXD")
    c.R("100k", ".DBG_VBUS", "GND")
    c.C("100nF", "0402", "+3V3", "GND")
    c.C("100nF", "0402", ".DBG_VBUS", "GND")
    sh.text("CH340C lấy nguồn +3V3 của CM4 (V3 nối VCC):\nkhông cấp ngược vào CM4 khi bo tắt.\n"
            "VBUS micro-USB không nối vào rail nào.", 84 * G, 66 * G, size=1.2, justify="left top")
    return sh


# =========================================================================== Security
def sheet_security(d):
    sh = d.new_sheet("Security", "security.kicad_sch", "TPM, RTC, pin, SRAM chống mở vỏ", paper="A3")
    c = Ctx(sh, "11")

    sh.frame(8 * G, 8 * G, 78 * G, 60 * G, "A. TPM 2.0 — SLB9670 (SPI0, CE1)")
    c.g("tpm")
    t = c.ic(symdefs.slb9670(), "SLB9670VQ2.0", 32, 34, FP["TPM"], "C1012863", "SLB9670VQ20FW785XTMA1")
    t.net({"CS#": "TPM_CS_N", "SCLK": "SPI_SCLK", "MOSI": "SPI_MOSI", "MISO": "SPI_MISO",
           "RST#": "nEXTRST", "PIRQ#": "TPM_PIRQ_N", "GPIO": "NC", "PP": "NC",
           "VDD": "+3V3", "GND": "GND", "NC": "NC", "NCI": "NC"})
    c.at(62, 16)
    c.R("10k", "+3V3", "TPM_CS_N")
    c.R("10k", "+3V3", "TPM_PIRQ_N")
    c.C("100nF", "0402", "+3V3", "GND")
    c.C("100nF", "0402", "+3V3", "GND")
    c.C("1uF", "0402", "+3V3", "GND")
    sh.text("overlay: dtoverlay=tpm-slb9670 (SPI0, CE1 = GPIO7).\nRST# nối nEXTRST của CM4.", 10 * G, 58 * G, size=1.3)

    sh.frame(82 * G, 8 * G, 160 * G, 60 * G, "B. RTC PCF85063A + pin CR2032 (rail V_KEEP)")
    c.g("rtc")
    r = c.ic(symdefs.rtc(), "PCF85063AT", 106, 22, FP["SO8"], "C5151540", "PCF85063AT/AY")
    r.net({"OSCI": ".RTC_XI", "OSCO": ".RTC_XO", "SCL": "RTC_SCL", "SDA": "RTC_SDA",
           "VDD": ".V_KEEP", "~{INT}": "NC", "CLKOUT": "NC", "VSS": "GND"})
    p = parts.P["XTAL32K"]
    sh.part2(p["sym"], c.ref("Y"), "32.768kHz 7pF", 92 * G, 36 * G, ".RTC_XI", ".RTC_XO", fp=p["fp"],
             lcsc=p["lcsc"], mpn=p["mpn"], Group="rtc")
    p = parts.P["BATT"]
    bt = sh.add(p["sym"], c.ref("BT"), "CR2032", XY(134, 22), fp=p["fp"], lcsc=p["lcsc"], mpn=p["mpn"], Group="batt")
    bt.net({"+": ".VBAT", "-": "GND"})
    c.g("keep")
    dd = c.part("BAT54C", "BAT54C", 120, 42, {"1": "+3V3", "2": ".VBAT_R", "K": ".V_KEEP"}, prefix="D")
    c.at(146, 34)
    c.R("1k", ".VBAT", ".VBAT_R")
    c.C("100nF", "0402", ".V_KEEP", "GND")
    c.flag(".V_KEEP", 150, 46)
    c.flag(".VBAT", 140, 46)
    c.tp(".V_KEEP", 100, 52)
    sh.text("V_KEEP = OR(+3V3, pin): nuôi RTC và nhánh tamper. Khi CM4 có điện, pin không bị tiêu hao.\n"
            "overlay: dtoverlay=i2c-rtc,pcf85063a,i2c_csi_dsi (SDA0/SCL0 = GPIO44/45).", 84 * G, 58.5 * G, size=1.3)

    sh.frame(8 * G, 64 * G, 160 * G, 112 * G, "C. Chống mở vỏ: MX switch → cắt nguồn + kẹp GND SRAM 23LCV1024")
    c.g("mx")
    mx = c.part("MX", "MX Red (vỏ đậy = đóng)", 22, 74, {"1": ".V_KEEP", "2": ".TAMP_LOOP"}, prefix="SW")
    c.g("tamper")
    jt = c.part("HDR2", "TAMPER_EXT (jumper)", 44, 74, {"1": ".TAMP_LOOP", "2": ".TAMP_J"}, prefix="J")
    q1 = c.part("BSS138", "BSS138", 66, 76, {"G": ".V_SW", "D": ".VCC_GATE", "S": "GND"})
    q2 = c.part("AO3401A", "AO3401A", 84, 76, {"G": ".VCC_GATE", "S": "+3V3", "D": ".SRAM_VCC"}, rot=0)
    q3 = c.part("2N7002", "2N7002", 102, 76, {"G": ".VCC_GATE", "D": ".CLAMP", "S": "GND"})
    q4 = c.part("BSS138", "BSS138", 120, 76, {"G": ".V_SW", "D": ".TAMP_D", "S": "GND"})
    s = c.ic(symdefs.sram(), "23LCV1024-I/SN", 142, 76, FP["SO8"], "C615097", "23LCV1024-I/SN")
    s.net({"~{CS}": ".SRAM_CS", "SCK": ".SRAM_SCK", "SI": ".SRAM_SI", "SO": ".SRAM_SO",
           "VCC": ".SRAM_VCC", "VBAT": ".VBAT_SRAM", "NC": "NC", "VSS": "GND"})
    c.at(22, 86)
    c.R("1k", ".TAMP_J", ".V_SW")
    c.R("4.7M", ".V_SW", "GND")
    c.C("1nF", "0402", ".V_SW", "GND")
    c.diode("1N4148WS", "1N4148WS", ".VBAT_SRAM", ".V_SW")
    c.R("10M", ".VBAT_SRAM", "GND")
    c.at(56, 86)
    c.R("10k", "+3V3", ".VCC_GATE")
    c.R("10R", ".SRAM_VCC", ".CLAMP")
    c.C("100nF", "0402", ".SRAM_VCC", "GND")
    c.R("100k", ".SRAM_VCC", ".SRAM_CS")
    c.at(88, 86)
    c.R("10k", "+3V3", ".TAMP_D")
    c.R("1k", ".TAMP_D", "TAMPER_OPEN")
    c.at(118, 86)
    c.R("10k", "SRAM_CS_N", ".SRAM_CS")
    c.R("1k", "SPI_SCLK", ".SRAM_SCK")
    c.R("1k", "SPI_MOSI", ".SRAM_SI")
    c.R("1k", ".SRAM_SO", "SPI_MISO")
    c.flag(".SRAM_VCC", 146, 88)
    c.tp(".SRAM_VCC", 146, 94)
    c.tp("TAMPER_OPEN", 100, 94)
    sh.text("Vỏ đậy: MX đóng → V_SW ≈ V_KEEP → Q1101 dẫn → VCC_GATE thấp → Q1102 cấp +3V3 cho SRAM; D1102 nạp chân VBAT (giữ dữ liệu khi mất điện).\n"
            "Mở vỏ / đứt dây / rút jumper: V_SW xả qua 4.7 MΩ (τ ≈ 5 ms) → Q1101 tắt → VCC_GATE lên +3V3 (10 k) → Q1102 ngắt, Q1103 kẹp SRAM_VCC qua 10 Ω;\n"
            "VBAT_SRAM mất nguồn (D1102 chặn dòng rò ngược về V_SW, xả qua 10 MΩ + dòng VBAT). Q1104 tạo TAMPER_OPEN riêng → mạch xóa KHÔNG phụ thuộc trạng thái GPIO23.\n"
            "Điện trở nối tiếp trên CS/SCK/SI/SO chặn dòng ký sinh từ bus SPI vào SRAM đã bị ngắt.",
            10 * G, 111 * G, size=1.25)
    return sh


# =========================================================================== ROOT
def build():
    d = Design(PROJECT, "CM4 Security Gateway — Carrier Board", REV, DATE, "cm4-gateway", HW)
    d.power_nets |= POWER_NETS

    sp = sheet_power(d)
    sheet_cm4(d)
    sheet_wan(d)
    ssw = sheet_switch(d)
    snic = sheet_nic(d)
    sheet_usb(d)
    sheet_security(d)

    r = d.root
    r.text("CM4 SECURITY GATEWAY — Rev %s" % REV, 20 * G, 14 * G, size=5, bold=True)
    r.text("1 WAN (PHY CM4) + 4 LAN (PCIe → 2× PI7C9X2G404SL → 4× RTL8111H) · TPM 2.0 · RTC · SRAM chống mở vỏ",
           20 * G, 19 * G, size=2.2)

    by_name = {s.name: s for s in d.sheets}
    d.place_sheet(by_name["Power"], "Power", 14 * G, 28 * G, 26 * G, 10 * G)
    d.place_sheet(by_name["CM4"], "CM4", 14 * G, 43 * G, 26 * G, 10 * G)
    d.place_sheet(by_name["WAN"], "WAN", 14 * G, 58 * G, 26 * G, 10 * G)
    d.place_sheet(by_name["USB_Debug"], "USB_Debug", 14 * G, 73 * G, 26 * G, 10 * G)
    d.place_sheet(by_name["Security"], "Security", 14 * G, 88 * G, 26 * G, 10 * G)

    def sw_pins(up_rx, up_tx, dn, clkin, clks, perst, rsts):
        pins = [("UP_RX_P", "L", up_rx + "_P"), ("UP_RX_N", "L", up_rx + "_N"),
                ("UP_TX_P", "L", up_tx + "_P"), ("UP_TX_N", "L", up_tx + "_N"),
                ("CLKIN_P", "L", clkin + "_P"), ("CLKIN_N", "L", clkin + "_N"),
                ("PERST_N", "L", perst)]
        for i, (tx, rx) in enumerate(dn, start=1):
            pins += [("DN%d_TX_P" % i, "R", tx and tx + "_P"), ("DN%d_TX_N" % i, "R", tx and tx + "_N"),
                     ("DN%d_RX_P" % i, "R", rx and rx + "_P"), ("DN%d_RX_N" % i, "R", rx and rx + "_N")]
        for i, ck in enumerate(clks, start=1):
            pins += [("CLK%d_P" % i, "R", ck and ck + "_P"), ("CLK%d_N" % i, "R", ck and ck + "_N")]
        for i, rs in enumerate(rsts, start=1):
            pins.append(("DNRST%d_N" % i, "R", rs))
        return pins

    d.place_sheet(ssw, "SW1", 66 * G, 28 * G, 30 * G, 24 * G, sw_pins(
        "PCIE_TX", "PCIE_RX",
        # cổng xuôi 1 (chân sát góc dưới) -> NIC ở phía tây (LAN2), cổng 2 -> NIC ngay dưới (LAN1): hai nhóm làn không cắt nhau
        [("P2_SW2NIC", "P2_NIC2SW"), ("P1_SW2NIC", "P1_NIC2SW"), ("X_SW1TO2", "X_SW2TO1")],
        "PCIE_CLK", ["P1_CLK", "P2_CLK", "SW2_CLK"], "PCIE_RST_N", ["P2_RST_N", "P1_RST_N", "SW2_RST_N"]))
    d.place_sheet(ssw, "SW2", 66 * G, 60 * G, 30 * G, 24 * G, sw_pins(
        "X_SW1TO2", "X_SW2TO1",
        [("P4_SW2NIC", "P4_NIC2SW"), ("P3_SW2NIC", "P3_NIC2SW"), (None, None)],
        "SW2_CLK", ["P3_CLK", "P4_CLK", None], "SW2_RST_N", ["P4_RST_N", "P3_RST_N", None]))
    for i in range(4):
        k = i + 1
        d.place_sheet(snic, "LAN%d" % k, 128 * G, (28 + i * 14) * G, 24 * G, 10 * G, [
            ("RX_P", "L", "P%d_SW2NIC_P" % k), ("RX_N", "L", "P%d_SW2NIC_N" % k),
            ("TX_P", "L", "P%d_NIC2SW_P" % k), ("TX_N", "L", "P%d_NIC2SW_N" % k),
            ("CLK_P", "L", "P%d_CLK_P" % k), ("CLK_N", "L", "P%d_CLK_N" % k),
            ("PERST_N", "L", "P%d_RST_N" % k)])
    r.text("Cây PCIe:  CM4 → SW1 → {LAN1, LAN2, SW2};  SW2 → {LAN3, LAN4, cổng 3 dự phòng (để hở)}",
           14 * G, 104 * G, size=1.8)
    r.text("ĐẢO CỰC: mọi đầu thu PCIe (switch PERP/PERN, NIC HSIP/HSIN, CM4 PCIe_RX) nối chéo P<->N có chủ đích (clock không đảo)\n"
           "để cặp vi sai không phải bắt chéo trên PCB (PCIe tự nhận đảo cực ở đầu thu).\n"
           "Quy ước tên net:  Pk_SW2NIC = switch phát → NIC thu;  Pk_NIC2SW = NIC phát → switch thu;\n"
           "X_SW1TO2 / X_SW2TO1 = liên kết giữa hai switch.  Tụ AC luôn nằm ở phía phát.",
           14 * G, 109 * G, size=1.5)
    return d, sp


def main():
    d, sp = build()
    check_all_pins(d)
    d.write()
    os.makedirs(os.path.join(HW, "lib"), exist_ok=True)
    d.write_symbol_lib(os.path.join(HW, "lib", "cm4-gateway.kicad_sym"))
    n = sum(len(s.insts) for s in d.sheets)
    print("Da ghi %d sheet, %d the hien linh kien (chua nhan so lan dung sheet)" % (len(d.sheets), n))


if __name__ == "__main__":
    main()
