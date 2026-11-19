#!/usr/bin/env python3
"""Dựng PCB giai đoạn 1: viền bo, stackup 6 lớp, nạp footprint + net từ schematic, BỐ TRÍ linh kiện.

Chưa đi dây (đúng phạm vi giai đoạn 1). Chạy:  python3 scripts/gen/board.py
Toạ độ trong file này là toạ độ BO (mm): gốc = góc sau-trái, +X sang phải, +Y về phía mặt trước.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "..", "hardware"))
PROJECT = "cm4-gateway"
PCB = os.path.join(HW, PROJECT + ".kicad_pcb")
SCH = os.path.join(HW, PROJECT + ".kicad_sch")
KFP = "/usr/share/kicad/footprints"

W, H = 150.0, 105.0            # kích thước bo
OX, OY = 40.0, 30.0            # vị trí gốc bo trên trang vẽ
R_CORNER = 3.0
MM = pcbnew.FromMM
TM = pcbnew.ToMM

# vị trí tâm (theo X) của các cổng mặt trước, trái -> phải khi nhìn từ trên xuống, mặt trước ở dưới
X_LAN = {4: 17.0, 3: 35.2, 2: 53.4, 1: 71.6}      # bước 18.2 mm (tai vỏ hai jack kề nhau không chạm)
X_USBA, X_DBG, X_USBC, X_WAN = 90.0, 104.5, 116.0, 133.0
RJ45_OVERHANG = 2.0            # mặt trước RJ45 và USB-A nhô khỏi mép bo
Y_NIC = 76.0
CLK_R = 13.0                   # tâm hàng Rs clock, tính từ tâm switch (mm)
SW_POS = {"SW1": (60.0, 50.0), "SW2": (23.6, 50.0)}    # SW2 = SW1 dịch -36.4 (giống hệt vị trí tương đối với 2 NIC)
CM4_ORG = (114.5, 9.5)         # gốc footprint CM4 (lỗ vít số 1), xoay 180 độ


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


# --------------------------------------------------------------------------- netlist
def load_netlist():
    out = os.path.join(tempfile.gettempdir(), "cm4gw_netlist.xml")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                   check=True, capture_output=True)
    root = ET.parse(out).getroot()
    comps = {}
    for c in root.iter("comp"):
        fields = {f.get("name"): (f.text or "") for f in c.iter("field")}
        sp = c.find("sheetpath")
        comps[c.get("ref")] = dict(
            ref=c.get("ref"), value=c.findtext("value") or "", footprint=c.findtext("footprint") or "",
            fields=fields, sheet=sp.get("names").strip("/"), sheet_ts=sp.get("tstamps"),
            ts=(c.findtext("tstamps") or "").split()[0], group=fields.get("Group", ""),
            dnp=c.find("property[@name='dnp']") is not None)
    nets = {}
    for n in root.iter("net"):
        nets[n.get("name")] = [(x.get("ref"), x.get("pin")) for x in n.iter("node")]
    return comps, nets


def natural(ref):
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


# --------------------------------------------------------------------------- board helpers
class Builder:
    def __init__(self):
        self.board = pcbnew.BOARD()
        self.comps, self.nets = load_netlist()
        self.fps = {}
        self.placed = {}
        self.problems = []

    # ---- khởi tạo
    def setup_layers(self):
        b = self.board
        b.SetCopperLayerCount(6)
        names = {pcbnew.F_Cu: "F.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu",
                 pcbnew.In3_Cu: "In3.Cu", pcbnew.In4_Cu: "In4.Cu", pcbnew.B_Cu: "B.Cu"}
        for lid, t in ((pcbnew.In1_Cu, pcbnew.LT_POWER), (pcbnew.In2_Cu, pcbnew.LT_SIGNAL),
                       (pcbnew.In3_Cu, pcbnew.LT_POWER), (pcbnew.In4_Cu, pcbnew.LT_POWER)):
            b.SetLayerType(lid, t)
        ds = b.GetDesignSettings()
        ds.SetBoardThickness(MM(1.6))

    def load_footprints(self):
        b = self.board
        netinfo = {}
        for name in self.nets:
            ni = pcbnew.NETINFO_ITEM(b, name)
            b.Add(ni)
            netinfo[name] = ni
        pin_net = {}
        for name, nodes in self.nets.items():
            for ref, pin in nodes:
                pin_net[(ref, pin)] = netinfo[name]
        for ref in sorted(self.comps, key=natural):
            c = self.comps[ref]
            lib, name = c["footprint"].split(":")
            path = os.path.join(HW, "lib", "cm4-gateway.pretty") if lib == "cm4-gateway" \
                else os.path.join(KFP, lib + ".pretty")
            fp = pcbnew.FootprintLoad(path, name)
            if fp is None:
                raise SystemExit("Khong nap duoc footprint %s cho %s" % (c["footprint"], ref))
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            fp.SetReference(ref)
            fp.SetValue(c["value"])
            fp.SetPath(pcbnew.KIID_PATH(c["sheet_ts"] + c["ts"]))
            fp.SetSheetname("/" + c["sheet"] + "/")
            for k in ("LCSC", "MPN", "Group"):
                if k in c["fields"]:
                    fp.SetField(k, c["fields"][k])
            for f in fp.GetFields():
                if f.GetName() not in ("Reference", "Value"):
                    f.SetVisible(False)
            # silkscreen: chỉ giữ tham chiếu cho linh kiện lớn; R/C/FB/TP xem trên lớp Fab (bản vẽ lắp ráp)
            prefix = natural(ref)[0]
            rf = fp.Reference()
            rf.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
            rf.SetTextThickness(MM(0.12))
            if (prefix in ("R", "C", "FB", "TP", "H") and "CP_Elec" not in name) or \
                    name.startswith(("RJ45_", "USB_")):
                rf.SetVisible(False)
            fp.SetField("Datasheet", c["fields"].get("Datasheet", "~") or "~")
            fp.SetField("Description", c["fields"].get("Description", ""))
            for f in fp.GetFields():
                if f.GetName() not in ("Reference", "Value"):
                    f.SetVisible(False)
            if prefix in ("TP", "H"):
                fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
            fix_models(fp, c["footprint"])
            for pad in fp.Pads():
                ni = pin_net.get((ref, pad.GetNumber()))
                if ni is not None:
                    pad.SetNet(ni)
            fp.SetPosition(P(-30, -30))
            b.Add(fp)
            self.fps[ref] = fp
        self.netinfo = netinfo

    # ---- hình học
    def crtyd(self, ref):
        """Hộp bao courtyard hiện tại (toạ độ bo, mm): (x0, y0, x1, y1)."""
        fp = self.fps[ref]
        xs, ys = [], []
        for g in fp.GraphicalItems():
            if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                bb = g.GetBoundingBox()
                xs += [bb.GetLeft(), bb.GetRight()]
                ys += [bb.GetTop(), bb.GetBottom()]
        if not xs:
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                xs += [bb.GetLeft(), bb.GetRight()]
                ys += [bb.GetTop(), bb.GetBottom()]
        return (TM(min(xs)) - OX, TM(min(ys)) - OY, TM(max(xs)) - OX, TM(max(ys)) - OY)

    def orient(self, ref, rot=0, side="F"):
        fp = self.fps[ref]
        if side == "B" and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)

    def place(self, ref, x, y, rot=0, side="F"):
        """Đặt GỐC footprint tại (x, y)."""
        self.orient(ref, rot, side)
        self.fps[ref].SetPosition(P(x, y))
        self.placed[ref] = side

    def place_center(self, ref, x, y, rot=0, side="F"):
        """Đặt sao cho TÂM courtyard nằm tại (x, y)."""
        self.orient(ref, rot, side)
        fp = self.fps[ref]
        fp.SetPosition(P(x, y))
        x0, y0, x1, y1 = self.crtyd(ref)
        fp.Move(pcbnew.VECTOR2I(MM(x - (x0 + x1) / 2), MM(y - (y0 + y1) / 2)))
        self.placed[ref] = side

    def group(self, sheet, *groups):
        refs = [r for r, c in self.comps.items() if c["sheet"] == sheet and c["group"] in groups
                and r not in self.placed]
        return sorted(refs, key=lambda r: (groups.index(self.comps[r]["group"]), natural(r)))

    def pack(self, refs, x0, y0, x1, y1, side="F", rot=0, gap=0.15, exclude=(), rots=None, big_first=True,
             name="", bottom_up=False):
        """Xếp kiểu kệ (shelf) các footprint vào vùng chữ nhật; trả về danh sách không vừa."""
        rots = rots or {}
        items = []
        for r in refs:
            self.orient(r, rots.get(r, rots.get(natural(r)[0], rot)), side)
            self.fps[r].SetPosition(P(0, 0))
            a, b_, c, d = self.crtyd(r)
            items.append((r, c - a, d - b_))
        if big_first:
            items.sort(key=lambda it: -round(it[2], 1))
        cx, cy, rowh = x0, y0, 0.0
        left = []
        for r, w, h in items:
            while True:
                if cx + w > x1 + 1e-6:
                    cx, cy, rowh = x0, cy + rowh + gap, 0.0
                if cy + h > y1 + 1e-6:
                    left.append(r)
                    break
                ty = (y1 - (cy - y0) - h) if bottom_up else cy      # bottom_up: xếp từ mép gần đầu nối trở lên
                hit = [e for e in exclude if not (cx + w <= e[0] - gap or cx >= e[2] + gap or
                                                  ty + h <= e[1] - gap or ty >= e[3] + gap)]
                if hit:
                    cx = max(e[2] for e in hit) + gap
                    continue
                fp = self.fps[r]
                a, b_, c, d = self.crtyd(r)
                fp.Move(pcbnew.VECTOR2I(MM(cx - a), MM(ty - b_)))
                self.placed[r] = side
                cx += w + gap
                rowh = max(rowh, h)
                break
        if left:
            self.problems.append("Vung %s (%.1f,%.1f)-(%.1f,%.1f) khong du cho: %s" % (name, x0, y0, x1, y1, left))
        return left

    # ---- đặt theo vị trí chân (decoupling, điện trở tham chiếu)
    def pad_xy(self, ref, num):
        return [(TM(p.GetPosition().x) - OX, TM(p.GetPosition().y) - OY)
                for p in self.fps[ref].Pads() if p.GetNumber() == str(num)]

    def _is_tht(self, ref):
        return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in self.fps[ref].Pads())

    def place_near(self, items, side="B", exclude=(), gap=0.12, step=0.2, rmax=10.0, name=""):
        """items: [(ref, tx, ty, rot)] — đặt tâm courtyard gần (tx, ty) nhất mà không chồng linh kiện khác."""
        import math
        occ = [self.crtyd(r) for r in self.placed if self.placed[r] == side or self._is_tht(r)]
        occ += list(exclude)
        for ref, tx, ty, rot in items:
            self.orient(ref, rot, side)
            fp = self.fps[ref]
            fp.SetPosition(P(0, 0))
            a, b_, c, d = self.crtyd(ref)
            w, h = c - a, d - b_
            best = None
            r = 0.0
            while r <= rmax and best is None:
                n = max(1, int(2 * math.pi * r / step))
                for i in range(n):
                    ang = 2 * math.pi * i / n
                    x, y = tx + r * math.cos(ang), ty + r * math.sin(ang)
                    box = (x - w / 2 - gap, y - h / 2 - gap, x + w / 2 + gap, y + h / 2 + gap)
                    if box[0] < 0.4 or box[1] < 0.4 or box[2] > W - 0.4 or box[3] > H - 0.4:
                        continue
                    if any(not (box[2] <= o[0] or box[0] >= o[2] or box[3] <= o[1] or box[1] >= o[3]) for o in occ):
                        continue
                    best = (x, y)
                    break
                r += step
            if best is None:
                self.problems.append("%s: khong tim duoc cho gan (%.1f, %.1f) cho %s" % (name, tx, ty, ref))
                continue
            fp.Move(pcbnew.VECTOR2I(MM(best[0] - (a + c) / 2), MM(best[1] - (b_ + d) / 2)))
            self.placed[ref] = side
            occ.append(self.crtyd(ref))

    def decouple(self, ic, refs, f, side="B", exclude=(), name=""):
        """Đặt tụ/ferrite của một IC ở mặt đối diện, mỗi tụ 100 nF ngay dưới một chân nguồn cùng net.
        f: hệ số co vị trí chân về tâm IC (<1: vào trong thân; >1: ra ngoài hàng pad)."""
        fp = self.fps[ic]
        cx, cy = TM(fp.GetPosition().x) - OX, TM(fp.GetPosition().y) - OY
        ic_pins = {}
        for net, nodes in self.nets.items():
            for r, pin in nodes:
                if r == ic and net != "GND":
                    for xy in self.pad_xy(ic, pin):
                        ic_pins.setdefault(net, []).append(xy)
        free = {n: list(v) for n, v in ic_pins.items()}
        items = []

        def target(xy, ff):
            return cx + (xy[0] - cx) * ff, cy + (xy[1] - cy) * ff

        def cap_net(r):
            ns = {p.GetNetname() for p in self.fps[r].Pads()} - {"GND"}
            local = [n for n in ns if n.startswith("/") and n in ic_pins]
            if local:
                return local[0]
            ns = [n for n in ns if n in ic_pins]
            return ns[0] if ns else None

        small = [r for r in refs if "0402" in self.comps[r]["footprint"]]
        large = [r for r in refs if r not in small]
        for r in small:
            net = cap_net(r)
            if net and free.get(net):
                xy = free[net].pop(0)
            elif net:
                pts = ic_pins[net]
                xy = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
            else:
                xy = (cx, cy)
            tx, ty = target(xy, f)
            rot = 0 if abs(xy[0] - cx) >= abs(xy[1] - cy) else 90
            items.append((r, tx, ty, rot))
        for r in large:
            net = cap_net(r)
            pts = ic_pins.get(net) or [(cx, cy)]
            # tụ khối / ferrite: gần chân xa tâm nhất của nhóm chân cùng net, lùi vào trong hơn một chút
            xy = max(pts, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))
            tx, ty = target(xy, f * (0.72 if f < 1 else 1.35))
            rot = 0 if abs(xy[0] - cx) >= abs(xy[1] - cy) else 90
            items.append((r, tx, ty, rot))
        self.place_near(items, side=side, exclude=exclude, name=name)

    # ---- viền bo, chữ, zone
    def outline(self):
        b = self.board
        r = R_CORNER

        def seg(x1, y1, x2, y2):
            s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
            b.Add(s)

        def arc(cx, cy, a0):
            import math
            s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_ARC)
            pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                   for a in (a0, a0 + 45, a0 + 90)]
            s.SetArcGeometry(P(*pts[0]), P(*pts[1]), P(*pts[2]))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
            b.Add(s)

        seg(r, 0, W - r, 0); seg(W, r, W, H - r); seg(W - r, H, r, H); seg(0, H - r, 0, r)
        arc(r, r, 180); arc(W - r, r, 270); arc(W - r, H - r, 0); arc(r, H - r, 90)

    def text(self, s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0, thick=None, justify=None):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(thick or size * 0.15))
        if rot:
            t.SetTextAngleDegrees(rot)
        if layer in (pcbnew.B_SilkS, pcbnew.B_Fab):
            t.SetMirrored(True)
        self.board.Add(t)
        return t

    def rect_zone(self, layer, net, x0, y0, x1, y1, name, prio=0):
        z = pcbnew.ZONE(self.board)
        z.SetLayer(layer)
        z.SetNetCode(self.netinfo[net].GetNetCode())
        z.SetZoneName(name)
        z.SetAssignedPriority(prio)
        z.SetMinThickness(MM(0.2))
        z.SetLocalClearance(MM(0.25))
        o = z.Outline()
        o.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(MM(OX + x), MM(OY + y))
        self.board.Add(z)
        return z

    def drawing(self, layer, x0, y0, x1, y1, label=None, width=0.12):
        """Khung chữ nhật trên lớp vẽ phụ (dùng cho ảnh floorplan)."""
        b = self.board
        for a, b_, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(a, b_)); s.SetEnd(P(c, d)); s.SetLayer(layer); s.SetWidth(MM(width))
            b.Add(s)
        if label:
            self.text(label, (x0 + x1) / 2, y0 + 1.2, 1.2, layer)


def fix_models(fp, fpname):
    """Thay mô hình 3D cho footprint mà bản cài KiCad không kèm file model đúng tên."""
    sub = {
        "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm":
            ("${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm.step",
             (0, 0, 0), (0, 0, 0), (1, 1, 1)),
        # Kailh/Cherry MX: model thật (thư viện kiswitch), gốc model ở tâm trục; footprint KiCad gốc ở chân 1
        "Button_Switch_Keyboard:SW_Cherry_MX_1.00u_PCB":
            ("${KIPRJMOD}/lib/3dmodels/SW_Cherry_MX_PCB.stp", (-2.54, -5.08, 0), (0, 0, 0), (1, 1, 1)),
    }
    if fpname in sub:
        path, off, rot, sc = sub[fpname]
        fp.Models().clear()
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset = pcbnew.VECTOR3D(*off)
        m.m_Rotation = pcbnew.VECTOR3D(*rot)
        m.m_Scale = pcbnew.VECTOR3D(*sc)
        fp.Models().push_back(m)


# --------------------------------------------------------------------------- bố trí
def place_all(B):
    g = B.group
    yf = H                                   # mép trước

    # ---- lỗ bắt vít M3 (4 góc)
    for ref, (x, y) in zip(g("CM4", "holes"), ((4.5, 4.5), (W - 4.5, 4.5), (4.5, H - 4.5), (W - 4.5, H - 4.5))):
        B.place(ref, x, y)

    # ---- CM4 (xoay 180: đầu chân 1/101 hướng về mặt trước; đầu nối chân 101-200 nằm bên trái)
    B.place("U201", CM4_ORG[0], CM4_ORG[1], rot=180)

    # ---- cổng mặt trước
    for k, x in X_LAN.items():
        B.place("J%d01" % (5 + k), x, yf + RJ45_OVERHANG, rot=180)        # LAN1..4 = sheet số 6..9
    B.place("J301", X_WAN, yf + RJ45_OVERHANG, rot=180)                    # WAN
    B.place("J1001", X_USBA - 3.5, yf + RJ45_OVERHANG - 13.04)             # USB-A (thân dài tới y=13.04)
    B.place("J1003", X_DBG, yf - 2.67)                                     # micro-USB: mép bo tại y=+2.67
    B.place("J1002", X_USBC, yf - 3.68)                                    # USB-C: mép bo tại y=+3.68

    # ---- jack DC mặt sau (miệng jack hướng ra sau, nhô 0.5 mm)
    B.place("J101", 16.0, 13.25, rot=270)

    # ---- nguồn
    B.pack(g("Power", "in"), 22.5, 3.0, 62.0, 17.0, name="in", rots={"C": 0})
    B.pack(g("Power", "tp"), 63.0, 2.6, 77.0, 7.4, name="tp", gap=0.1)
    B.pack(g("Power", "led", "seq"), 63.0, 7.6, 76.5, 12.0, name="led/seq")
    # U101: vòng nóng Cin - VIN/GND - SW - D104 đặt sát nhau (review S3)
    B.place_center("U101", 35.0, 24.0)
    # rev B: pad +12V của C104/C105/C106 quay lên cùng hàng với chân VIN -> một dải đồng 1 mm thẳng tới chân 2
    B.place_center("C106", 30.25, 23.85, rot=270)      # 100 nF/50 V ngay tại chân VIN, GND quay xuống
    B.place_center("C104", 27.6, 24.0, rot=270)        # 10 µF/50 V
    B.place_center("C105", 25.0, 24.0, rot=270)
    B.place_center("C109", 35.0, 20.2)                 # tụ boot giữa BOOT (chân 1) và SW (chân 8)
    B.place_center("L101", 46.6, 22.6)                 # cuộn cảm ngay cạnh chân SW
    B.place_center("D104", 37.25, 31.3, rot=180)       # diode nằm ngang dưới U101: K phải (nút SW), A trái sát GND tụ vào (review M2)
    for i, r in enumerate(("C110", "C111", "C112", "C113")):
        B.place_center(r, 56.2 + i * 2.6, 22.6, rot=90)
    B.pack(g("Power", "b5"), 44.6, 30.2, 72.0, 36.5, name="b5")
    # rev B: hai buck TPS563201 bố trí cố định — cuộn cảm quay chân SW về phía IC, tụ boot ngay trên chân VBST,
    # tụ vào sát chân VIN, tụ ra sát chân ra của cuộn cảm (review rev A R4)
    for u, l, cb, cin, couts, y, chf in (("U102", "L102", "C117", "C115", ("C119", "C118"), 20.0, "C116"),
                                          ("U103", "L103", "C123", "C121", ("C124", "C125"), 41.5, "C122")):
        B.place_center(chf, 12.3, y + 3.3, rot=270)          # 100 nF sát tụ vào, cạnh chân VIN (review rev B M1)
        B.place_center(u, 11.5, y)
        B.place_center(l, 6.2, y, rot=180)
        B.place_center(cb, 12.3, y - 2.4, rot=180)
        B.place_center(cin, 10.2, y + 3.6, rot=270)
        for i, c in enumerate(couts):
            B.place_center(c, 4.4 + 2.3 * i, y + 4.1, rot=270)
    fixed_b = ("U102", "L102", "C117", "C115", "C119", "C118", "C116",
               "U103", "L103", "C123", "C121", "C124", "C125", "C122")
    bk = [B.crtyd(r) for r in fixed_b]
    B.pack([r for r in g("Power", "b3V3") if r not in fixed_b], 3.0, 17.5, 21.5, 37.0, name="b3V3", exclude=bk)
    B.pack([r for r in g("Power", "b1V0") if r not in fixed_b], 3.0, 39.0, 14.4, 66.0, name="b1V0", exclude=bk)

    # ---- hai PCIe switch (xoay 270: cạnh có các làn PCIe quay sang phải, cạnh clock quay về mặt trước)
    for name, n in (("SW1", 4), ("SW2", 5)):
        cx, cy = SW_POS[name]
        B.place("U%d01" % n, cx, cy, rot=270)
        ep = (cx - 3.6, cy - 3.6, cx + 3.6, cy + 3.6)                      # chừa vùng via tản nhiệt dưới đế
        # --- tụ AC và điện trở clock: xếp theo TỪNG CẶP, đúng thứ tự chân, thuận chiều cặp vi sai (giai đoạn 2)
        pc = B.place_center
        xa, xb = cx + 11.5, cx + 13.9
        for top, bot, x, dy, rot in (
                ("C%d01", "C%d02", xa, -5.0, 0),      # UP TX (chân 124 P ở trên)
                ("C%d07", "C%d08", xb, -2.0, 0),      # DN3 TX (118 P ở trên)
                ("C%d10", "C%d09", xa, 0.8, 180),     # clock tự vòng vào REFCLKP/N (111 N ở trên); pad 2 quay về chip
                ("C%d06", "C%d05", xb, 2.3, 0),       # DN2 TX (107 N ở trên)
                ("C%d04", "C%d03", xa, 5.4, 0)):      # DN1 TX (101 N ở trên)
            pc(top % n, x, cy + dy - 0.56, rot=rot)
            pc(bot % n, x, cy + dy + 0.56, rot=rot)
        # 4 ngõ ra clock: Rs (33R) thành cặp đứng ngay dưới hàng chân; cặp clock đổi lớp bằng via ngay sau Rs,
        # Rp (49.9R xuống GND) nằm MẶT DƯỚI hai bên cặp via đó.
        for k0, xc in ((16, -4.0), (12, -1.6), (8, 0.8), (4, 3.2)):
            r = CLK_R
            pc("R%d%02d" % (n, k0), cx + xc + 0.56, cy + r, rot=270)        # Rs_P (chân P bên phải)
            pc("R%d%02d" % (n, k0 + 2), cx + xc - 0.56, cy + r, rot=270)    # Rs_N
            pc("R%d%02d" % (n, k0 + 1), cx + xc + 1.75, cy + r + 1.45, rot=0, side="B")    # Rp_P (hàng trên)
            pc("R%d%02d" % (n, k0 + 3), cx + xc - 1.75, cy + r + 3.35, rot=180, side="B")     # Rp_N (hàng dưới)
        if name == "SW1":
            # phân cực clock CM4 -> REFCLKI: mặt dưới, hai bên cặp via nằm DƯỚI THÂN chip (clock vào chân 73/74 từ phía trong)
            for r_, dx, dy, ro in (("R209", -1.0, 3.2, 180), ("R210", -1.0, 4.4, 0), ("R211", -4.6, 3.2, 0),
                                   ("R212", -4.6, 4.4, 180)):
                pc(r_, cx + dx, cy + dy, rot=ro, side="B")
        refin_keep = (cx - 5.6, cy + 2.6, cx + 0.0, cy + 7.2)
        tms_keep = (cx + 3.8, cy + 8.5, cx + 5.4, cy + 11.2)     # via thoát chân 92
        # điện trở tham chiếu ngay dưới chân tương ứng (mặt dưới): REXT (116), IREF (86), CLKBUF_PD (60)
        ref_r = g(name, "ref")
        items = []
        for r, pin in zip(ref_r, ("116", "86", "60")):
            px, py = B.pad_xy("U%d01" % n, pin)[0]
            items.append((r, cx + (px - cx) * 0.74, cy + (py - cy) * 0.74, 0 if abs(px - cx) > abs(py - cy) else 90))
        B.place_near(items, side="B", exclude=[ep, refin_keep, tms_keep], name=name + " ref")
        # decoupling: mỗi tụ 100 nF dưới đúng một chân nguồn (review S4)
        B.decouple("U%d01" % n, g(name, "v10", "avdd", "v33", "cvdd", "avddh"), 0.74, side="B",
                   exclude=[ep, refin_keep, tms_keep],
                   name=name + " decoupling")
        # strap của chân ở hàng dưới / hai cạnh bên: đặt mặt dưới ngay dưới chân (không kéo dây vòng qua chip)
        u = "U%d01" % n
        for r in list(g(name, "strap")):
            pins = [pin for net, nodes in B.nets.items() if (r, "1") in nodes or (r, "2") in nodes
                    for ref, pin in nodes if ref == u]
            if not pins:
                continue
            px, py = B.pad_xy(u, pins[0])[0]
            if py < cy - 5:
                continue                                  # hàng trên: giữ ở cụm phía trên
            tx, ty = cx + (px - cx) * 1.28, cy + (py - cy) * 1.28
            B.place_near([(r, tx, ty, 0 if abs(py - cy) > abs(px - cx) else 90)], side="B",
                         exclude=[ep, refin_keep, tms_keep], name=name + " strap duoi")
        B.place_center("TP%d01" % n, cx + 10.0, cy - 11.75)          # điểm đo AVDD_1V0
        B.pack(g(name, "strap"), cx - 9.0, cy - 13.0, cx + 8.8, cy - 10.5, big_first=False, gap=0.12,
               name=name + " strap")

    # ---- 4 NIC + linh kiện quanh
    for k, x in X_LAN.items():
        sh = "LAN%d" % k
        n = 5 + k
        B.place("U%d01" % n, x, Y_NIC, rot=90)             # MDI quay về jack, PCIe quay về phía switch
        ep = (x - 2.5, Y_NIC - 2.5, x + 2.5, Y_NIC + 2.5)     # vùng dưới chip dành cho fanout + via tản nhiệt
        # vùng via thoát chân của NIC (xem NIC_ESC trong route.py): không đặt linh kiện mặt dưới ở đây
        keep = [(x - 1.6, Y_NIC + 2.6, x + 3.0, Y_NIC + 5.6), (x - 4.9, Y_NIC - 6.0, x + 0.2, Y_NIC - 4.8),
                (x - 4.9, Y_NIC - 2.6, x - 2.4, Y_NIC + 2.4), (x + 4.1, Y_NIC - 0.4, x + 5.9, Y_NIC + 1.5),
                (x + 3.1, Y_NIC - 3.4, x + 4.7, Y_NIC - 1.8)]
        B.decouple("U%d01" % n, g(sh, "v10", "v33"), 1.75, side="B", exclude=[ep] + keep, name=sh + " decoupling")
        # điện trở RSET (2.49 k) ngay cạnh chân 31; cụm thạch anh lùi sang trái để cạnh trái NIC còn 2.8 mm thoát chân
        rset = [r for r in g(sh, "strap") if B.comps[r]["value"].startswith("2.49k")]
        for r in rset:
            B.place_center(r, x - 3.9, Y_NIC + 2.7, rot=90)
        B.pack(g(sh, "xtal"), x - 10.25, Y_NIC - 4.5, x - 5.15, Y_NIC + 4.0, name=sh + " xtal", rots={"C": 90})
        B.pack(g(sh, "strap"), x + 5.8, Y_NIC - 4.4, x + 7.95, Y_NIC + 5.2, name=sh + " strap", big_first=False)
        # tụ AC của HSO: 2 tụ đứng cạnh nhau ngay trên chân 17 (P, bên phải) / 18 (N); pad 1 quay về NIC
        B.place_center("C%d01" % n, x + 1.76, Y_NIC - 5.3, rot=90)
        B.place_center("C%d02" % n, x + 0.64, Y_NIC - 5.3, rot=90)
        B.pack([r for r in g(sh, "jack")], x - 8.4, 80.9, x - 4.4, 84.6, name=sh + " led/ct")

    # ---- WAN
    B.pack(g("WAN", "jack"), X_WAN - 8.4, 82.6, X_WAN - 4.4, 84.95, name="WAN led/ct", gap=0.1)
    B.pack(g("WAN", "chs"), 142.2, 85.5, 148.8, 96.5, rot=90, name="CHASSIS-GND")

    # ---- linh kiện phụ của CM4
    B.pack(g("CM4", "dec"), 110.5, 19.0, 119.5, 30.0, side="B", rot=90, name="CM4 decoupling (mat duoi)")
    B.pack(g("CM4", "pcieglue"), 73.2, 31.0, 77.4, 35.5, big_first=False, name="PCIe glue")
    B.pack(g("CM4", "ctl"), 79.0, 62.3, 97.8, 69.3, name="CM4 ctl")
    B.pack(g("CM4", "jmp"), 98.5, 62.5, 120.5, 69.0, name="CM4 jumper", rots={"JP": 90, "J": 90})
    B.pack(g("CM4", "fan"), 121.5, 2.5, 140.5, 10.0, name="fan", rots={"J": 90})

    # ---- USB / debug
    # (giai đoạn 2) đặt tường minh để chừa hành lang cho các cặp USB: mux quay cổng ra phía đông,
    # cặp USB-A đi xuống theo hành lang x = 91.5..96.5, cặp USB-C chui lớp trong sang đông.
    B.place_center("U1001", 88.0, 76.0)
    B.place_center("C1001", 88.0, 73.4)
    B.place_center("SW1001", 104.5, 74.2)                # công tắc BOOT (bên trong vỏ)
    B.place_center("U1002", X_USBA, 89.3)                # IC ESD ngay sau chân đầu nối (review N7)
    B.place_center("U1005", X_DBG, 96.6)
    B.place_center("U1004", X_USBC, 93.0)
    esd = [B.crtyd(r) for r in ("U1002", "U1004", "U1005")]
    B.pack(g("USB_Debug", "usba"), 80.7, 76.5, 85.9, 91.0, name="USB-A", big_first=False, bottom_up=True,
           exclude=esd)
    B.pack(g("USB_Debug", "dbg"), 99.5, 78.0, 110.0, 97.8, name="debug UART", rots={"U1006": 90}, big_first=False,
           bottom_up=True, exclude=esd)
    B.pack(g("USB_Debug", "usbc"), 110.8, 84.0, 121.2, 90.6, name="USB-C", big_first=False, bottom_up=True,
           exclude=esd)

    # ---- bảo mật (cột bên phải CM4)
    B.place_center("BT1101", 134.5, 22.5)
    B.place_center("SW1101", 134.5, 46.5)
    B.pack(g("Security", "tpm"), 121.8, 55.0, 147.5, 63.5, name="TPM")
    B.place_center("U1102", 128.6, 67.3)
    B.place_center("Y1101", 123.3, 66.3, rot=90)       # thạch anh 32.768 kHz sát chân OSCI/OSCO (review S6)
    B.pack(g("Security", "rtc", "keep"), 121.8, 64.0, 147.5, 70.6, name="RTC/V_KEEP", big_first=False,
           exclude=[B.crtyd("U1102"), B.crtyd("Y1101")])
    # giãn cách 0.45 mm để còn chỗ đặt via giữa các linh kiện (vùng này có cặp MDI của WAN chạy ở lớp trong)
    B.pack([r for r in g("Security", "tamper") if r != "R1111"], 121.8, 71.0, 147.5, 83.0, name="tamper/SRAM",
           rots={"J": 90}, gap=0.45, exclude=[(X_WAN - 8.6, 82.4, X_WAN - 4.2, 85.0)])
    tp = B.crtyd("TP1103")
    B.place_near([("R1111", (tp[0] + tp[2]) / 2, tp[1] - 1.2, 90)], side="F", gap=0.3, name="R1111")   # 1 k -> TAMPER_OPEN

    missing = [r for r in B.comps if r not in B.placed]
    if missing:
        B.problems.append("Chua dat: %s" % sorted(missing, key=natural))


def silk(B):
    t = B.text
    for k, x in X_LAN.items():
        t("LAN%d" % k, x, 84.5, 1.0)
    t("WAN", X_WAN, 84.6, 1.0)
    t("USB", X_USBA, 90.5, 0.9)
    t("DEBUG", X_DBG, 98.8, 0.8)
    t("FLASH", X_USBC, 95.6, 0.8)
    t("12V DC  tam (+)", 16.0, 16.2, 0.8)
    t("CM4 SECURITY GATEWAY  Rev ${REVISION}  ${ISSUE_DATE}", 100.0, 80.6, 1.2)
    t("SW1", 50.0, 57.0, 0.9); t("SW2", 13.6, 57.0, 0.9)
    t("TAMPER", 134.5, 54.3, 0.9)
    t("CR2032 (+) tren", 134.5, 34.6, 0.8)
    t("CM4", 98.0, 64.0 - 60.5, 1.2)


def planes(B):
    """Mặt phẳng GND trên L2 (In1) và L4 (In3) phủ toàn bo — theo stackup trong docs/specs."""
    for layer, nm in ((pcbnew.In1_Cu, "GND_L2"), (pcbnew.In3_Cu, "GND_L4")):
        B.rect_zone(layer, "GND", 0.3, 0.3, W - 0.3, H - 0.3, nm)


STACKUP = '''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01524) (material "Solder mask") (epsilon_r 3.8) (loss_tangent 0))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "prepreg") (thickness 0.0994) (material "3313 RC57%") (epsilon_r 4.1) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 2" (type "core") (thickness 0.55) (material "FR4 core") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 3" (type "prepreg") (thickness 0.1088) (material "2116 RC54%") (epsilon_r 4.16) (loss_tangent 0.02))
			(layer "In3.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 4" (type "core") (thickness 0.55) (material "FR4 core") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In4.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 5" (type "prepreg") (thickness 0.0994) (material "3313 RC57%") (epsilon_r 4.1) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01524) (material "Solder mask") (epsilon_r 3.8) (loss_tangent 0))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "ENIG")
			(dielectric_constraints yes)
		)
'''


def inject_stackup(path):
    t = open(path, encoding="utf-8").read()
    if "(stackup" in t:
        a = t.index("\t\t(stackup")
        depth, i = 0, a + 2
        while True:
            if t[i] == "(":
                depth += 1
            elif t[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        t = t[:a] + STACKUP + t[i + 2:]
    else:
        m = re.search(r"\n\t\(setup\n", t)
        t = t[:m.end()] + STACKUP + t[m.end():]
    open(path, "w", encoding="utf-8").write(t)


def check_overlaps(B):
    """Tự kiểm tra chồng courtyard và linh kiện ra ngoài bo (bổ sung cho DRC của KiCad)."""
    boxes = {r: B.crtyd(r) for r in B.placed}
    tht = {r for r, fp in B.fps.items() if any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
                                               for p in fp.Pads())}
    refs = sorted(boxes)
    bad = []
    for i, a in enumerate(refs):
        ax0, ay0, ax1, ay1 = boxes[a]
        for b in refs[i + 1:]:
            if B.placed[a] != B.placed[b] and a not in tht and b not in tht:
                continue
            if a == "U201" or b == "U201":
                other = b if a == "U201" else a
                if B.placed[other] == "B" and other not in tht:
                    continue
            bx0, by0, bx1, by1 = boxes[b]
            ov = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
            if ov[0] > 0.02 and ov[1] > 0.02:
                bad.append("%s x %s (%.2f x %.2f mm)" % (a, b, ov[0], ov[1]))
    edge_ok = {"J101", "J301", "J601", "J701", "J801", "J901", "J1001", "J1002", "J1003"}
    for r, (x0, y0, x1, y1) in boxes.items():
        if r not in edge_ok and (x0 < 0.3 or y0 < 0.3 or x1 > W - 0.3 or y1 > H - 0.3):
            bad.append("%s ra ngoai/sat mep bo (%.1f,%.1f)-(%.1f,%.1f)" % (r, x0, y0, x1, y1))
    return bad


def write_project():
    def nc(name, track, clr, dpw, dpg, via=0.5, drill=0.25, prio=0):
        return {"bus_width": 12, "clearance": clr, "diff_pair_gap": dpg, "diff_pair_via_gap": 0.25,
                "diff_pair_width": dpw, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": prio,
                "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": track, "tuning_profile": "",
                "via_diameter": via, "via_drill": drill, "wire_width": 6}
    classes = [
        nc("Default", 0.15, 0.1, 0.15, 0.15, via=0.45, drill=0.2, prio=2147483647),
        nc("PCIE_90R", 0.15, 0.12, 0.15, 0.15, via=0.45, drill=0.2, prio=0),
        nc("USB_90R", 0.15, 0.12, 0.15, 0.15, via=0.45, drill=0.2, prio=1),
        nc("MDI_100R", 0.125, 0.12, 0.125, 0.18, via=0.45, drill=0.2, prio=2),
        nc("USB_FS", 0.15, 0.12, 0.15, 0.15, via=0.45, drill=0.2, prio=5),
        nc("PWR", 0.3, 0.1, 0.2, 0.2, via=0.6, drill=0.3, prio=3),
        nc("PWR_HV", 1.0, 0.1, 0.2, 0.2, via=0.8, drill=0.4, prio=4),
    ]
    pats = []
    for p in ("PCIE_TX_*", "PCIE_RX_*", "PCIE_CLK_*", "P?_SW2NIC_*", "P?_NIC2SW_*", "P?_CLK_*", "X_SW*",
              "SW2_CLK_*", "/SW?/*TXC_*", "/SW?/CLKO*", "/SW?/SELF*", "/LAN?/HSO_*", "/SW?/DN3_*",
              "/SW?/CLK3_*"):
        pats.append({"netclass": "PCIE_90R", "pattern": p})
    for p in ("USB_D?", "/USB_Debug/USB*_D?", "/USB_Debug/USB*_CON_D?"):
        pats.append({"netclass": "USB_90R", "pattern": p})
    for p in ("/USB_Debug/DBG_*D?",):          # USB full-speed của CH340: không cần khớp độ dài
        pats.append({"netclass": "USB_FS", "pattern": p})
    for p in ("WAN_MDI*", "/LAN?/MDI*"):
        pats.append({"netclass": "MDI_100R", "pattern": p})
    for p in ("+5V", "+3V3", "+3V3_SW", "+1V0", "/SW?/AVDD*", "/SW?/CVDD*", "/LAN?/V1P0",
              "/USB_Debug/USBA_VBUS", "/Power/SW_3V3", "/Power/SW_1V0"):
        pats.append({"netclass": "PWR", "pattern": p})
    for p in ("+12V", "+12V_JACK", "/Power/VIN_FUSED", "/Power/SW_5V"):
        pats.append({"netclass": "PWR_HV", "pattern": p})
    pro = {
        "board": {"design_settings": {"rules": {
            "max_error": 0.005, "min_clearance": 0.1, "min_connection": 0.0,
            "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.19, "min_hole_to_hole": 0.25,
            "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 2,
            "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.08,
            "min_through_hole_diameter": 0.2, "min_track_width": 0.09, "min_via_annular_width": 0.1,
            "min_via_diameter": 0.4, "solder_mask_to_copper_clearance": 0.0,
            "use_height_for_length_calcs": True}}},
        "boards": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": PROJECT + ".kicad_pro", "version": 3},
        "net_settings": {"classes": classes, "meta": {"version": 5}, "net_colors": {},
                         "netclass_assignments": {}, "netclass_patterns": pats},
        "text_variables": {"REVISION": "B", "ISSUE_DATE": "2026-11-18"},
    }
    with open(os.path.join(HW, PROJECT + ".kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)


DRU = '''(version 1)
# Luật theo năng lực JLCPCB 6 lớp (cần đối chiếu lại bảng năng lực hiện hành ở giai đoạn 2).
# QUY ƯỚC DỰ ÁN: không viết luật theo Reference của linh kiện.

(rule "jlc_pth_hole_clearance_outer"
  (layer outer)
  (condition "A.Pad_Type == 'Through-hole' || B.Pad_Type == 'Through-hole'")
  (constraint hole_clearance (min 0.28mm)))

(rule "nguon_dong_lon_rong_toi_thieu"
  (condition "A.NetClass == 'PWR_HV' && A.NetName != '/Power/SW_5V'")
  (constraint track_width (min 0.6mm)))

# SW_5V: nhánh chính chân SW -> cuộn cảm do script đặt sẵn rộng 1.0-1.5 mm; nhánh tụ bootstrap (C109) chỉ nạp dòng cổng.
(rule "nut_sw_5v_rong_toi_thieu"
  (condition "A.NetName == '/Power/SW_5V'")
  (constraint track_width (min 0.3mm)))

(rule "nut_sw_buck_rong_toi_thieu"
  (condition "A.NetName == '/Power/SW_3V3' || A.NetName == '/Power/SW_1V0'")
  (constraint track_width (min 0.5mm)))

(rule "jlc_pth_hole_clearance_inner"
  (layer inner)
  (condition "A.Pad_Type == 'Through-hole' || B.Pad_Type == 'Through-hole'")
  (constraint hole_clearance (min 0.30mm)))

# Lệch độ dài chỉ xét TRONG từng cặp vi sai.
(rule "pcie_90R_do_lech_trong_cap"
  (condition "A.NetClass == 'PCIE_90R'")
  (constraint skew (max 0.1mm) (within_diff_pairs)))

(rule "usb_90R_do_lech_trong_cap"
  (condition "A.NetClass == 'USB_90R'")
  (constraint skew (max 1.0mm) (within_diff_pairs)))

# MDI: hai hàng chân so le của jack HR911130A lệch nhau 2.54 mm nên lệch trong cặp tới ~2.5 mm là cố hữu
# (≈17 ps, không đáng kể so với chu kỳ ký hiệu 8 ns của 1000BASE-T). USB 2.0 HS: 1 mm ≈ 7 ps so với UI 2083 ps.
(rule "mdi_100R_do_lech_trong_cap"
  (condition "A.NetClass == 'MDI_100R'")
  (constraint skew (max 3.0mm) (within_diff_pairs)))

# Net class của cặp vi sai khai báo khe hở 0.12 mm để hai dây trong cặp (khe danh định 0.15/0.18 mm) không bị báo
# ở các góc vát; với MỌI net khác, cặp vi sai phải cách tối thiểu 0.11 mm (bộ đi dây giữ 0.15 mm khi còn chỗ).
(rule "cap_vi_sai_cach_net_khac"
  (condition "(A.NetClass == 'PCIE_90R' || A.NetClass == 'USB_90R' || A.NetClass == 'MDI_100R' || A.NetClass == 'USB_FS') && !A.isCoupledDiffPair()")
  (constraint clearance (min 0.11mm)))
'''


def main():
    B = Builder()
    B.setup_layers()
    B.load_footprints()
    B.outline()
    place_all(B)
    silk(B)
    # (giai đoạn 2) mọi vùng đồng do scripts/gen/route.py tạo
    bad = check_overlaps(B)
    pcbnew.ZONE_FILLER(B.board).Fill(B.board.Zones())
    B.board.GetTitleBlock().SetTitle("CM4 Security Gateway - Carrier Board")
    B.board.GetTitleBlock().SetRevision("B")
    B.board.GetTitleBlock().SetDate("2026-11-11")
    pcbnew.SaveBoard(PCB, B.board)
    inject_stackup(PCB)
    write_project()
    with open(os.path.join(HW, PROJECT + ".kicad_dru"), "w", encoding="utf-8") as f:
        f.write(DRU)
    dump = {"board": {"w": W, "h": H, "r": R_CORNER}, "parts": []}
    for r in sorted(B.placed, key=natural):
        x0, y0, x1, y1 = B.crtyd(r)
        dump["parts"].append(dict(ref=r, side=B.placed[r], sheet=B.comps[r]["sheet"], group=B.comps[r]["group"],
                                  value=B.comps[r]["value"], box=[round(v, 3) for v in (x0, y0, x1, y1)]))
    netpads = {}
    for r, fp in B.fps.items():
        for pad in fp.Pads():
            nm = pad.GetNetname()
            if nm and not nm.startswith("unconnected-"):
                netpads.setdefault(nm, []).append([round(TM(pad.GetPosition().x) - OX, 2),
                                                   round(TM(pad.GetPosition().y) - OY, 2), r])
    dump["nets"] = netpads
    dump["front_x"] = dict(LAN=X_LAN, USBA=X_USBA, DEBUG=X_DBG, FLASH=X_USBC, WAN=X_WAN)
    with open(os.path.join(HW, "placement.json"), "w") as f:
        json.dump(dump, f, indent=0)
    print("Footprint: %d, da dat: %d" % (len(B.fps), len(B.placed)))
    for p in B.problems:
        print("VAN DE:", p)
    print("Chong courtyard / sat mep: %d" % len(bad))
    for x in bad[:60]:
        print("   ", x)
    return 1 if (B.problems or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
