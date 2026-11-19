#!/usr/bin/env python3
"""Vẽ hình minh hoạ giai đoạn 1 (SVG + PNG): sơ đồ khối, cây nguồn, floorplan.

Floorplan lấy toạ độ thật từ hardware/placement.json (do board.py ghi ra).
Chạy: python3 scripts/gen/diagrams.py <thư mục ra>
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "..", "hardware"))
FONT = "DejaVu Sans"


class Svg:
    def __init__(self, w, h, bg="#ffffff"):
        self.w, self.h = w, h
        self.e = ['<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (w, h, bg)]

    def rect(self, x, y, w, h, fill="#fff", stroke="#234", sw=2, rx=8, op=1.0, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.e.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.1f" fill="%s" stroke="%s" '
                      'stroke-width="%.2f" fill-opacity="%.2f"%s/>' % (x, y, w, h, rx, fill, stroke, sw, op, d))

    def text(self, x, y, s, size=16, anchor="middle", weight="normal", fill="#111", rot=None):
        s = s.replace("&", "&amp;").replace("<", "&lt;")
        tr = ' transform="rotate(%d %.1f %.1f)"' % (rot, x, y) if rot else ""
        self.e.append('<text x="%.2f" y="%.2f" font-family="%s" font-size="%.1f" text-anchor="%s" '
                      'font-weight="%s" fill="%s"%s>%s</text>' % (x, y, FONT, size, anchor, weight, fill, tr, s))

    def box(self, x, y, w, h, title, lines=(), fill="#eef3ff", stroke="#234", tsize=17):
        self.rect(x, y, w, h, fill, stroke)
        n = len(lines)
        ty = y + h / 2 - (n * 17) / 2 + 6
        self.text(x + w / 2, ty, title, tsize, weight="bold")
        for i, ln in enumerate(lines):
            self.text(x + w / 2, ty + 19 * (i + 1), ln, 13, fill="#333")

    def line(self, pts, stroke="#234", sw=2.5, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.e.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f"%s/>' % (
            " ".join("%.1f,%.1f" % p for p in pts), stroke, sw, d))

    def arrow(self, pts, label=None, stroke="#234", sw=2.5, both=False, lpos=0.5, dy=-7, dash=None, lsize=12.5):
        import math
        self.line(pts, stroke, sw, dash)

        def head(p, q):
            a = math.atan2(q[1] - p[1], q[0] - p[0])
            s = 10
            pts2 = [q, (q[0] - s * math.cos(a - 0.4), q[1] - s * math.sin(a - 0.4)),
                    (q[0] - s * math.cos(a + 0.4), q[1] - s * math.sin(a + 0.4))]
            self.e.append('<polygon points="%s" fill="%s"/>' % (" ".join("%.1f,%.1f" % p for p in pts2), stroke))
        head(pts[-2], pts[-1])
        if both:
            head(pts[1], pts[0])
        if label:
            i = min(int(lpos * (len(pts) - 1)), len(pts) - 2)
            mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
            self.text(mx, my + dy, label, lsize, fill=stroke)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n%s\n</svg>\n'
                    % (self.w, self.h, self.w, self.h, "\n".join(self.e)))
        png = os.path.splitext(path)[0] + ".png"
        subprocess.run(["convert", "-density", "110", path, png], check=True)
        print("da ve", os.path.basename(path), "+ png")


C_PWR, C_CM4, C_PCIE, C_NIC, C_USB, C_SEC, C_CON = "#ffe9c7", "#d9f2d9", "#e3ddff", "#d6ecff", "#fde0ec", "#fff5b8", "#e9e9e9"
HS = "#7a2fd0"        # màu đường tốc độ cao


def block_diagram(out):
    s = Svg(1500, 980)
    s.text(750, 38, "CM4 Security Gateway Rev A — Sơ đồ khối", 26, weight="bold")
    s.text(750, 62, "1 WAN + 4 LAN · USB host · cổng nạp eMMC · console UART · TPM 2.0 · RTC · SRAM chống mở vỏ", 14,
           fill="#444")
    # nguồn
    s.box(40, 100, 200, 70, "Jack DC 12 V", ["mặt sau · 5.5×2.1 · tâm (+)"], C_CON)
    s.box(280, 100, 220, 70, "Bảo vệ đầu vào", ["cầu chì 4 A · P-FET · TVS"], C_PWR)
    s.box(540, 100, 220, 70, "Buck +5V / 5 A", ["TPS54560B"], C_PWR)
    s.box(800, 85, 200, 46, "Buck +3V3_SW / 3 A", [], C_PWR, tsize=14)
    s.box(800, 139, 200, 46, "Buck +1V0 / 3 A", [], C_PWR, tsize=14)
    s.arrow([(240, 135), (280, 135)]); s.arrow([(500, 135), (540, 135)])
    s.arrow([(760, 122), (800, 108)]); s.arrow([(760, 148), (800, 162)])
    s.text(1020, 112, "→ 4× NIC, 2× switch (I/O)", 12.5, "start", fill="#444")
    s.text(1020, 166, "→ lõi 2× switch", 12.5, "start", fill="#444")
    s.text(1250, 139, "bật bởi +3V3 của CM4 (PERIPH_EN)", 12.5, fill="#a33")
    # CM4
    s.box(560, 300, 330, 300, "", [], C_CM4)
    s.text(725, 335, "Raspberry Pi CM4", 22, weight="bold")
    s.text(725, 358, "eMMC · không WiFi · 2× DF40 100 chân", 13, fill="#333")
    for i, t in enumerate(["PHY GbE (MDI)", "PCIe Gen2 ×1", "USB 2.0", "UART0 (GPIO14/15)", "SPI0 (CE0, CE1)",
                           "I2C SDA0/SCL0", "GPIO23 · GPIO17 · GPIO18", "+5V vào · +3V3 ra 600 mA"]):
        s.text(725, 395 + i * 25, t, 14, fill="#123")
    s.arrow([(650, 170), (650, 300)], "+5V", C_PWR.replace("ffe9c7", "c77700"), lpos=0.5, dy=0)
    # WAN
    s.box(1010, 250, 210, 60, "RJ45 WAN", ["HR911130A (có biến áp)"], C_CON)
    s.arrow([(890, 330), (950, 330), (950, 280), (1010, 280)], "MDI 100 Ω", HS, both=True, lpos=0.1)
    # PCIe
    s.box(180, 300, 250, 110, "PCIe switch SW1", ["PI7C9X2G404SL", "1 lên + 3 xuống · đệm clock"], C_PCIE)
    s.box(180, 470, 250, 110, "PCIe switch SW2", ["PI7C9X2G404SL", "cổng 3 dự phòng"], C_PCIE)
    s.arrow([(560, 355), (430, 355)], "PCIe ×1 + REFCLK + RST", HS, both=True)
    s.arrow([(305, 410), (305, 470)], "làn 3", HS, both=True, dy=0)
    for i in range(4):
        x = 40 + i * 185
        s.box(x, 660, 165, 70, "NIC %d" % (i + 1), ["RTL8111H"], C_NIC)
        s.box(x, 790, 165, 60, "RJ45 LAN%d" % (i + 1), ["HR911130A"], C_CON)
        s.arrow([(x + 82, 730), (x + 82, 790)], "MDI", HS, both=True, dy=0)
    s.arrow([(215, 410), (215, 440), (122, 440), (122, 660)], None, HS, both=True)
    s.arrow([(260, 410), (260, 450), (140, 450), (140, 620), (307, 620), (307, 660)], None, HS, both=True)
    s.arrow([(330, 580), (330, 610), (492, 610), (492, 660)], None, HS, both=True)
    s.arrow([(390, 580), (390, 600), (677, 600), (677, 660)], None, HS, both=True)
    s.text(60, 630, "PCIe ×1 mỗi NIC (Gen1) + REFCLK + PERST#", 12.5, "start", fill=HS)
    # USB
    s.box(1010, 370, 150, 60, "USB mux", ["FSUSB42"], C_USB)
    s.box(1230, 340, 220, 50, "USB-A host", ["TPS2553 ~1.2 A · ESD"], C_CON, tsize=14)
    s.box(1230, 410, 220, 50, "USB-C “FLASH”", ["rpiboot · chỉ dữ liệu"], C_CON, tsize=14)
    s.arrow([(890, 400), (1010, 400)], "USB 2.0 · 90 Ω", HS, both=True)
    s.arrow([(1160, 388), (1230, 365)], None, HS, both=True)
    s.arrow([(1160, 412), (1230, 435)], None, HS, both=True)
    s.box(1010, 450, 150, 44, "Công tắc BOOT", [], C_USB, tsize=13)
    s.arrow([(1085, 450), (1085, 430)], None, "#a33")
    s.arrow([(1010, 480), (890, 470)], "nRPIBOOT", "#a33", dy=14)
    # UART
    s.box(1010, 520, 150, 60, "CH340C", ["USB-UART"], C_USB)
    s.box(1230, 525, 220, 50, "micro-USB “DEBUG”", [], C_CON, tsize=14)
    s.arrow([(890, 545), (1010, 550)], "UART0", "#234", both=True)
    s.arrow([(1160, 550), (1230, 550)], None, "#234", both=True)
    # bảo mật
    s.box(980, 640, 150, 60, "TPM 2.0", ["SLB9670 · SPI0 CE1"], C_SEC)
    s.box(1150, 640, 150, 60, "SRAM", ["23LCV1024 · CE0"], C_SEC)
    s.box(1320, 640, 150, 60, "RTC", ["PCF85063A · I2C"], C_SEC)
    s.box(1150, 760, 150, 60, "Mạch tamper", ["cắt + kẹp nguồn SRAM"], C_SEC)
    s.box(980, 760, 150, 60, "MX switch", ["vỏ đậy = đóng"], C_CON)
    s.box(1320, 760, 150, 60, "Pin CR2032", ["rail V_KEEP"], C_CON)
    s.arrow([(800, 600), (800, 670), (980, 670)], "SPI", "#234", both=True, lpos=0.9)
    s.arrow([(860, 600), (860, 622), (1225, 622), (1225, 640)], None, "#234", both=True)
    s.arrow([(880, 600), (880, 612), (1395, 612), (1395, 640)], "I2C", "#234", both=True, lpos=0.6)
    s.arrow([(1130, 790), (1150, 790)], None, "#a33")
    s.arrow([(1225, 760), (1225, 700)], None, "#a33")
    s.arrow([(1320, 790), (1300, 790)], None, "#c77700")
    s.arrow([(1395, 760), (1395, 700)], None, "#c77700")
    s.arrow([(1190, 820), (1190, 860), (840, 860), (840, 600)], "TAMPER_OPEN → GPIO23", "#a33", lpos=0.4, dy=-6)
    # chú giải
    s.rect(40, 880, 620, 80, "#fafafa", "#999", 1)
    s.line([(60, 905), (120, 905)], HS, 3); s.text(130, 910, "cặp vi sai tốc độ cao (PCIe 90 Ω, USB 90 Ω, MDI 100 Ω)", 13, "start")
    s.line([(60, 930), (120, 930)], "#a33", 3); s.text(130, 935, "tín hiệu điều khiển / bảo mật", 13, "start")
    s.line([(60, 950), (120, 950)], "#c77700", 3); s.text(130, 955, "nguồn", 13, "start")
    s.save(os.path.join(out, "block-diagram.svg"))


def power_tree(out):
    s = Svg(1500, 820)
    s.text(750, 38, "Cây nguồn — CM4 Security Gateway Rev A", 26, weight="bold")
    A = "#c77700"
    s.box(30, 330, 170, 80, "Adapter 12 V", ["khuyến nghị 12 V / 3 A", "dải vào 9–24 V"], C_CON)
    s.box(240, 330, 190, 80, "Bảo vệ", ["F101 4 A · Q101 P-FET", "D102 TVS 24 V"], C_PWR)
    s.box(480, 330, 200, 80, "U101 TPS54560B", ["12 V → +5V", "5 A · 400 kHz · η≈90 %"], C_PWR)
    s.arrow([(200, 370), (240, 370)], "+12V_JACK", A); s.arrow([(430, 370), (480, 370)], "+12V", A)
    s.text(580, 430, "tải tối đa ước tính 4.3 A", 12.5, fill="#a33")
    # nhánh +5V
    ys = [110, 250, 390, 530, 670]
    s.line([(680, 370), (730, 370)], A, 3); s.line([(730, ys[0] + 35), (730, ys[-1] + 35)], A, 3)
    s.text(705, 360, "+5V", 13, fill=A)
    items = [("CM4 (+5V vào)", ["điển hình 1.4 A", "tối đa ~1.8 A"], C_CM4),
             ("U1003 TPS2553", ["USB-A VBUS", "giới hạn ~1.2 A"], C_USB),
             ("U102 TPS563201", ["+5V → +3V3_SW", "3 A · EN = PERIPH_EN"], C_PWR),
             ("U103 TPS563201", ["+5V → +1V0", "3 A · EN = PERIPH_EN"], C_PWR),
             ("Quạt 5 V (tùy chọn)", ["≤ 0.2 A · PWM GPIO18"], C_CON)]
    for y, (t, l, c) in zip(ys, items):
        s.box(780, y, 210, 70, t, l, c)
        s.arrow([(730, y + 35), (780, y + 35)], None, A)
    # nhánh CM4 3V3
    s.box(1060, 60, 400, 150, "", [], "#f3fbf3")
    s.text(1260, 85, "+3V3 do CM4 cấp ra (≤ 600 mA)", 15, weight="bold")
    for i, t in enumerate(["TPM SLB9670 (~25 mA) · CH340C (~10 mA)", "FSUSB42 · LED · điện trở kéo",
                           "SRAM 23LCV1024 (VCC qua Q1102)", "PERIPH_EN → bật U102, U103",
                           "V_KEEP = OR(+3V3, pin) → RTC, nhánh tamper"]):
        s.text(1260, 110 + i * 21, t, 13, fill="#222")
    s.arrow([(990, 135), (1060, 135)], "+3V3", "#2a7a2a")
    # 3V3_SW
    s.box(1060, 370, 400, 100, "", [], "#f5f9ff")
    s.text(1260, 395, "+3V3_SW (tải tối đa ~1.3 A)", 15, weight="bold")
    s.text(1260, 418, "4× RTL8111H: ~0.25 A mỗi chip (LDO nội → 1.0 V)", 13)
    s.text(1260, 439, "2× PI7C9X2G404SL: VDDR/CVDDR/AVDDH ~0.12 A mỗi chip", 13)
    s.text(1260, 460, "LED RJ45 LAN", 13)
    s.arrow([(990, 425), (1060, 425)], None, A)
    s.box(1060, 520, 400, 90, "", [], "#f7f3ff")
    s.text(1260, 545, "+1V0 (tải tối đa ~1.35 A)", 15, weight="bold")
    s.text(1260, 568, "2× PI7C9X2G404SL: VDDC + AVDD + VDDCAUX", 13)
    s.text(1260, 589, "điển hình 0.27 A, tối đa 0.68 A mỗi chip", 13)
    s.arrow([(990, 565), (1060, 565)], None, A)
    # pin
    s.box(1060, 680, 190, 70, "Pin CR2032", ["≈ 2 µA khi rút điện", "> 10 năm"], C_CON)
    s.box(1290, 680, 170, 70, "RTC + SRAM VBAT", ["rail V_KEEP / V_SW"], C_SEC)
    s.arrow([(1250, 715), (1290, 715)], None, A)
    # trình tự
    s.rect(30, 560, 650, 220, "#fafafa", "#999", 1)
    s.text(50, 588, "Trình tự cấp nguồn", 16, "start", "bold")
    for i, t in enumerate(["1. Cắm 12 V → U101 khởi động khi Vin > 7.9 V (UVLO) → +5V",
                           "2. CM4 tự khởi động: +3V3 → +1V8 → RUN_PG",
                           "3. +3V3 của CM4 kéo PERIPH_EN → U102 (+3V3_SW) và U103 (+1V0) cùng lên",
                           "4. CM4 nhả PCIe_nRST khi kernel khởi tạo PCIe (>100 ms sau khi nguồn ổn định)",
                           "5. SW1 nhả DWNRST# → NIC1, NIC2, SW2 → SW2 nhả reset cho NIC3, NIC4",
                           "Khi CM4 tắt (GLOBAL_EN thấp): +3V3 mất → toàn bộ rail ngoại vi tắt theo",
                           "⇒ không chân nào của CM4 bị cấp điện trước +5V (yêu cầu datasheet CM4 §5.1)"]):
        s.text(50, 615 + i * 23, t, 13.5, "start", fill="#a33" if i == 6 else "#222")
    s.text(40, 110, "Ngân sách phía 12 V", 16, "start", "bold")
    for i, t in enumerate(["Tải +5V tối đa: 1.8 + 1.2 + 0.95 + 0.32 + 0.2 ≈ 4.5 A", "→ 22.5 W / 0.90 ≈ 25 W ≈ 2.1 A @ 12 V",
                           "Điển hình (không USB, không quạt): ~12 W ≈ 1.0 A", "Adapter: tối thiểu 12 V/2 A, khuyến nghị 12 V/3 A"]):
        s.text(40, 136 + i * 22, t, 13.5, "start")
    s.save(os.path.join(out, "power-tree.svg"))


BLOCKS = [  # (tên, màu, hàm chọn)
    ("Nguồn", "#f4a742", lambda p: p["sheet"] == "Power"),
    ("CM4 + phụ trợ", "#59b359", lambda p: p["sheet"] == "CM4"),
    ("PCIe switch", "#8a6fe0", lambda p: p["sheet"].startswith("SW")),
    ("NIC + RJ45 LAN", "#4a9fe0", lambda p: p["sheet"].startswith("LAN")),
    ("WAN", "#1f6fb5", lambda p: p["sheet"] == "WAN"),
    ("USB / debug", "#e0608f", lambda p: p["sheet"] == "USB_Debug"),
    ("Bảo mật (TPM, RTC, tamper)", "#d9c400", lambda p: p["sheet"] == "Security"),
]


def floorplan(out):
    d = json.load(open(os.path.join(HW, "placement.json")))
    W, H = d["board"]["w"], d["board"]["h"]
    k = 8.0                          # px / mm
    mx, my = 60, 110
    pw = W * k + 2 * mx
    s = Svg(int(2 * pw + 40), int(H * k + my + 330))

    def panel(ox, side, title):
        s.text(ox + mx + W * k / 2, 70, title, 22, weight="bold")
        s.rect(ox + mx, my, W * k, H * k, "#1f3d2b" if side == "F" else "#243a52", "#000", 2, rx=3 * k)
        for p in d["parts"]:
            x0, y0, x1, y1 = p["box"]
            if side == "B":
                x0, x1 = W - x1, W - x0            # nhìn từ mặt dưới: lật trái-phải
            tht = p["ref"].startswith(("J", "SW11", "BT", "H", "JP")) and p["side"] == "F"
            if p["side"] != side:
                continue
            col = next((c for n, c, f in BLOCKS if f(p)), "#ccc")
            s.rect(ox + mx + x0 * k, my + y0 * k, (x1 - x0) * k, (y1 - y0) * k, col, "#111", 0.6, rx=1, op=0.92)
            w, h = (x1 - x0) * k, (y1 - y0) * k
            big = w * h > 2600
            if big:
                lab = {"U201": "CM4", "U401": "SW1", "U501": "SW2", "BT1101": "CR2032", "SW1101": "MX tamper",
                       "J101": "DC 12V", "J301": "WAN", "J1001": "USB-A", "L101": "L 10µH",
                       "J601": "LAN1", "J701": "LAN2", "J801": "LAN3", "J901": "LAN4"}.get(p["ref"], p["ref"])
                s.text(ox + mx + (x0 + x1) / 2 * k, my + (y0 + y1) / 2 * k + 5, lab, 15 if w > 90 else 11,
                       weight="bold")
        s.text(ox + mx + W * k / 2, my + H * k + 26, "MẶT TRƯỚC (các cổng)" if side == "F" else "mặt trước", 14,
               fill="#333")
        s.text(ox + mx + W * k / 2, my - 10, "MẶT SAU (jack nguồn)" if side == "F" else "mặt sau", 14, fill="#333")

    panel(0, "F", "Mặt trên (Top) — %d × %d mm" % (W, H))
    panel(pw + 40, "B", "Mặt dưới (Bottom) — nhìn từ dưới lên")
    # nhãn cổng mặt trước
    for ref, lab in (("J1003", "DEBUG"), ("J1002", "FLASH")):
        p = next(q for q in d["parts"] if q["ref"] == ref)
        s.text(mx + (p["box"][0] + p["box"][2]) / 2 * k, my + p["box"][1] * k - 6, lab, 11, weight="bold", fill="#fff")
    # chú giải
    y0 = my + H * k + 60
    s.text(mx, y0, "Chú giải theo khối chức năng (mỗi ô = courtyard thật của 1 linh kiện)", 16, "start", "bold")
    for i, (n, c, f) in enumerate(BLOCKS):
        x = mx + (i % 4) * 300
        y = y0 + 22 + (i // 4) * 34
        cnt = sum(1 for p in d["parts"] if f(p))
        s.rect(x, y, 26, 20, c, "#111", 1, rx=2)
        s.text(x + 36, y + 16, "%s (%d)" % (n, cnt), 14, "start")
    nt = sum(1 for p in d["parts"] if p["side"] == "F")
    nb = len(d["parts"]) - nt
    s.text(mx, y0 + 110, "Tổng %d linh kiện: %d mặt trên, %d mặt dưới (tụ decoupling dưới PCIe switch, NIC và CM4)."
           % (len(d["parts"]), nt, nb), 14, "start")
    s.text(mx, y0 + 134, "Không đặt linh kiện mặt trên bên dưới module CM4 (khe hở 0 mm với đầu nối DF40C cao 1.5 mm).",
           14, "start")
    s.text(mx, y0 + 158, "Thứ tự cổng mặt trước (trái → phải): LAN4, LAN3, LAN2, LAN1, USB-A, DEBUG (micro-USB), FLASH (USB-C), WAN.",
           14, "start")
    s.save(os.path.join(out, "floorplan.svg"))


def _board_base(s, d, k, mx, my, labels=True):
    W, H = d["board"]["w"], d["board"]["h"]
    s.rect(mx, my, W * k, H * k, "#f4f7f4", "#000", 2, rx=3 * k)
    for p in d["parts"]:
        x0, y0, x1, y1 = p["box"]
        col = next((c for n, c, f in BLOCKS if f(p)), "#ccc")
        s.rect(mx + x0 * k, my + y0 * k, (x1 - x0) * k, (y1 - y0) * k, col, "#555", 0.5, rx=1,
               op=0.55 if p["side"] == "F" else 0.25)


def ratsnest(out):
    """Đường nối chưa đi dây (cây khung nhỏ nhất theo từng net), bỏ qua GND/CHASSIS và các rail nguồn."""
    d = json.load(open(os.path.join(HW, "placement.json")))
    W, H = d["board"]["w"], d["board"]["h"]
    k, mx, my = 11.0, 50, 90
    s = Svg(int(W * k + 2 * mx), int(H * k + my + 130))
    s.text(mx + W * k / 2, 45, "Bố trí + đường nối chưa đi dây (ratsnest)", 24, weight="bold")
    _board_base(s, d, k, mx, my)
    skip = {"GND", "CHASSIS", "+5V", "+3V3", "+3V3_SW", "+1V0", "+12V", "+12V_JACK"}
    total = 0.0
    longest = []
    for net, pads in d["nets"].items():
        if net in skip or len(pads) < 2:
            continue
        hs = any(t in net for t in ("PCIE", "SW2NIC", "NIC2SW", "X_SW", "_CLK", "MDI", "USB", "TXC", "CLKO",
                                    "SELF", "HSO", "DBG_"))
        pw = any(t in net for t in ("AVDD", "CVDD", "V1P0", "VBUS", "SW_", "VIN_"))
        col = "#7a2fd0" if hs else ("#c77700" if pw else "#2b6fb3")
        pts = [(p[0], p[1]) for p in pads]
        used, rest, length = [pts[0]], pts[1:], 0.0
        while rest:
            best = None
            for a in used:
                for b in rest:
                    dd = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
                    if best is None or dd < best[0]:
                        best = (dd, a, b)
            _, a, b = best
            s.line([(mx + a[0] * k, my + a[1] * k), (mx + b[0] * k, my + b[1] * k)], col, 1.3 if hs else 0.7)
            length += best[0] ** 0.5
            used.append(b)
            rest.remove(b)
        total += length
        longest.append((length, net))
    longest.sort(reverse=True)
    y = my + H * k + 30
    s.line([(mx, y), (mx + 50, y)], "#7a2fd0", 3); s.text(mx + 60, y + 5, "cặp vi sai / tốc độ cao", 14, "start")
    s.line([(mx + 300, y), (mx + 350, y)], "#2b6fb3", 3); s.text(mx + 360, y + 5, "tín hiệu thường", 14, "start")
    s.line([(mx + 560, y), (mx + 610, y)], "#c77700", 3); s.text(mx + 620, y + 5, "nguồn cục bộ", 14, "start")
    s.text(mx, y + 34, "Tổng chiều dài ước lượng (không tính GND và các rail chính): %.0f mm. Net dài nhất: %s."
           % (total, ", ".join("%s %.0f mm" % (n, l) for l, n in longest[:4])), 13.5, "start")
    s.text(mx, y + 58, "Linh kiện mặt dưới vẽ mờ. GND và các rail +5V/+3V3/+3V3_SW/+1V0 đi bằng mặt phẳng nên không vẽ.",
           13.5, "start")
    s.save(os.path.join(out, "ratsnest.svg"))


def dimensions(out):
    d = json.load(open(os.path.join(HW, "placement.json")))
    W, H = d["board"]["w"], d["board"]["h"]
    k, mx, my = 9.0, 130, 150
    s = Svg(int(W * k + 2 * mx), int(H * k + my + 300))
    s.text(mx + W * k / 2, 45, "Bản vẽ kích thước — nhìn từ trên (đơn vị mm)", 24, weight="bold")
    s.rect(mx, my, W * k, H * k, "#fbfbf6", "#000", 2.5, rx=3 * k)
    parts = {p["ref"]: p for p in d["parts"]}

    def dim_h(x0, x1, y, txt, up=True):
        s.line([(mx + x0 * k, y), (mx + x1 * k, y)], "#a33", 1.2)
        for x in (x0, x1):
            s.line([(mx + x * k, y - 6), (mx + x * k, y + 6)], "#a33", 1.2)
        s.text(mx + (x0 + x1) / 2 * k, y - 6 if up else y + 16, txt, 12.5, fill="#a33")

    def dim_v(y0, y1, x, txt):
        s.line([(x, my + y0 * k), (x, my + y1 * k)], "#a33", 1.2)
        for y in (y0, y1):
            s.line([(x - 6, my + y * k), (x + 6, my + y * k)], "#a33", 1.2)
        s.text(x - 10, my + (y0 + y1) / 2 * k + 4, txt, 12.5, "end", fill="#a33")

    big = ["U201", "J101", "J301", "J601", "J701", "J801", "J901", "J1001", "J1002", "J1003", "BT1101", "SW1101",
           "U401", "U501", "H201", "H202", "H203", "H204"]
    names = {"U201": "CM4 40×55", "J101": "DC", "J301": "WAN", "J601": "LAN1", "J701": "LAN2", "J801": "LAN3",
             "J901": "LAN4", "J1001": "USB-A", "J1002": "FLASH", "J1003": "DEBUG", "BT1101": "CR2032",
             "SW1101": "MX", "U401": "SW1", "U501": "SW2"}
    for r in big:
        x0, y0, x1, y1 = parts[r]["box"]
        if r.startswith("H"):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            s.e.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#fff" stroke="#000" stroke-width="1.5"/>'
                       % (mx + cx * k, my + cy * k, 1.6 * k))
            continue
        s.rect(mx + x0 * k, my + y0 * k, (x1 - x0) * k, (y1 - y0) * k, "#e6ecf5", "#345", 1.2, rx=2)
        s.text(mx + (x0 + x1) / 2 * k, my + (y0 + y1) / 2 * k + 5, names.get(r, r), 13, weight="bold")
    # kích thước bao
    dim_h(0, W, my - 80, "%.0f" % W)
    dim_v(0, H, mx - 90, "%.0f" % H)
    # lỗ vít
    dim_h(0, 4.5, my - 40, "4.5"); dim_h(4.5, W - 4.5, my - 40, "%.0f (lỗ M3 Ø3.2)" % (W - 9)); dim_h(W - 4.5, W, my - 40, "4.5")
    dim_v(0, 4.5, mx - 45, "4.5"); dim_v(4.5, H - 4.5, mx - 45, "%.0f" % (H - 9)); dim_v(H - 4.5, H, mx - 45, "4.5")
    # tâm cổng mặt trước
    fx = d["front_x"]
    xs = sorted([(v, "LAN%s" % kk) for kk, v in fx["LAN"].items()] + [(fx["USBA"], "USB-A"), (fx["DEBUG"], "DEBUG"),
                                                                      (fx["FLASH"], "FLASH"), (fx["WAN"], "WAN")])
    yb = my + H * k + 60
    for i, (x, n) in enumerate(xs):
        s.line([(mx + x * k, my + H * k - 10), (mx + x * k, yb + 16)], "#a33", 0.8, dash="4 3")
        s.text(mx + x * k, yb + 34, "%.1f" % x, 12.5, fill="#a33")
        s.text(mx + x * k, yb + 52, n, 12, fill="#333")
    s.text(mx - 10, yb + 34, "X tâm cổng →", 12.5, "end", fill="#a33")
    s.line([(mx, my + H * k), (mx, yb + 16)], "#a33", 0.8, dash="4 3")
    # jack DC
    jx = (parts["J101"]["box"][0] + parts["J101"]["box"][2]) / 2
    dim_h(0, 16.0, my - 12, "16.0 (tâm jack DC)")
    y = yb + 90
    for i, t in enumerate([
            "Bo 150 × 105 mm, dày 1.6 mm, góc bo R3. Bốn lỗ M3 (Ø3.2, vành đồng Ø6.4) cách mép 4.5 mm.",
            "RJ45 (HR911130A, rộng 16.1, cao 13.5) và USB-A nhô khỏi mép trước 2.0 mm; USB-C ≈ 0.1 mm; micro-USB ≈ 0.7 mm.",
            "Jack DC nhô khỏi mép sau 0.5 mm. Bước giữa các cổng LAN: 18.2 mm.",
            "Module CM4 gắn bằng 4 trụ M2.5 cao 1.5 mm (khoảng lỗ 33 × 48 mm); không có linh kiện mặt trên dưới module.",
            "Linh kiện cao nhất: MX switch ≈ 15 mm (kể cả trục), RJ45 13.5 mm, tụ hóa 7.7 mm, cuộn cảm 4 mm.",
            "Mặt dưới chỉ có linh kiện 0402/0603 (cao ≤ 1 mm) — trụ đỡ bo nên cao ≥ 3 mm."]):
        s.text(mx - 100, y + i * 22, t, 13.5, "start")
    s.save(os.path.join(out, "dimensions.svg"))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    which = sys.argv[2:] or ["block", "power", "floor", "rats", "dims"]
    if "block" in which:
        block_diagram(out)
    if "power" in which:
        power_tree(out)
    if "floor" in which:
        floorplan(out)
    if "rats" in which:
        ratsnest(out)
    if "dims" in which:
        dimensions(out)
