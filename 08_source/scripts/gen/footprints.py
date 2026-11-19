#!/usr/bin/env python3
"""Dựng các footprint riêng của dự án vào hardware/lib/cm4-gateway.pretty.

- Raspberry-Pi-4-Compute-Module : lấy từ CM4 IO Board (Raspberry Pi), thêm courtyard = viền module
- LQFP-128-1EP_14x14mm_P0.4mm_EP5.5x5.5mm : LQFP-128 chuẩn KiCad + đế tản nhiệt (chân 129)
- RJ45_Hanrun_HR911130A_Horizontal : dựng theo bản vẽ HR911130A Rev A trang 2
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "..", "hardware"))
OUT = os.path.join(HW, "lib", "cm4-gateway.pretty")
KFP = "/usr/share/kicad/footprints"
MM = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def line(fp, layer, x1, y1, x2, y2, w=0.12):
    s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2)); s.SetLayer(layer); s.SetWidth(MM(w))
    fp.Add(s)


def rect(fp, layer, x1, y1, x2, y2, w=0.05):
    for a, b, c, d in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)):
        line(fp, layer, a, b, c, d, w)


def set_model(fp, path, offset=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), clear=True):
    if clear:
        fp.Models().clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(*offset)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(*scale)
    fp.Models().push_back(m)


def save(fp, name):
    fp.SetFPID(pcbnew.LIB_ID("cm4-gateway", name))
    path = os.path.join(OUT, name + ".kicad_mod")
    if os.path.exists(path):
        os.remove(path)
    if not os.path.isdir(OUT) or not os.listdir(OUT):
        os.makedirs(OUT, exist_ok=True)
    io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    io.FootprintSave(OUT, fp)
    print("da ghi", name, "| pad:", len(fp.Pads()))


def cm4():
    fp = pcbnew.FootprintLoad(os.path.join(HW, "ref", "cm4io", "CM4IO.pretty"), "Raspberry-Pi-4-Compute-Module")
    # mô hình 3D: 2 đầu nối DF40 (giữ nguyên offset/rotation của Raspberry Pi) + tấm module minh họa
    fp.Models().clear()
    for ox in (-0.46, 33.46):           # offset/rotation đúng như footprint gốc của Raspberry Pi
        set_model(fp, "${KIPRJMOD}/lib/3dmodels/DF40C-100DS.stp", (ox, 15.38, 0), (-90, 0, 0), clear=False)
    set_model(fp, "${KIPRJMOD}/lib/3dmodels/CM4_module_outline.wrl", (16.5, 24.0, 2.1), clear=False)
    # courtyard = viền module 40 x 55 mm (lỗ vít lùi 3.5 mm): cấm đặt linh kiện mặt trên dưới module
    rect(fp, pcbnew.F_CrtYd, -3.5, -51.5, 36.5, 3.5)
    fp.SetAttributes(pcbnew.FP_SMD)
    fp.SetLibDescription("Raspberry Pi CM4: 2x Hirose DF40C-100DS-0.4V + 4 lo M2.5 (tu CM4 IO Board)")
    save(fp, "Raspberry-Pi-4-Compute-Module")


def lqfp128_ep():
    fp = pcbnew.FootprintLoad(os.path.join(KFP, "Package_QFP.pretty"), "LQFP-128_14x14mm_P0.4mm")
    assert len(fp.Pads()) == 128
    ep = 5.5        # D2/E2 = 5.10..5.99 mm (PD-2072)
    pad = pcbnew.PAD(fp)
    pad.SetNumber("129")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT)
    pad.SetSize(pcbnew.VECTOR2I(MM(ep), MM(ep)))
    pad.SetPosition(V(0, 0))
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
    pad.SetLayerSet(ls)
    fp.Add(pad)
    # kem hàn chia 3x3 ô (phủ ~55%) để tránh nổi chip
    n, cell = 3, 1.25
    pitch = ep / n
    for i in range(n):
        for j in range(n):
            p = pcbnew.PAD(fp)
            p.SetNumber("")
            p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
            p.SetRoundRectRadiusRatio(0.2)
            p.SetSize(pcbnew.VECTOR2I(MM(cell), MM(cell)))
            p.SetPosition(V(-ep / 2 + pitch * (i + 0.5), -ep / 2 + pitch * (j + 0.5)))
            l2 = pcbnew.LSET(); l2.AddLayer(pcbnew.F_Paste)
            p.SetLayerSet(l2)
            fp.Add(p)
    fp.SetLibDescription("LQFP-128 14x14 mm, buoc 0.4 mm, de tan nhiet 5.5x5.5 mm (Diodes FD128, PI7C9X2G404SL)")
    save(fp, "LQFP-128-1EP_14x14mm_P0.4mm_EP5.5x5.5mm")


def hr911130a():
    """Gốc toạ độ = tâm mặt trước của jack; +Y đi vào trong bo; thân dài 21.3, rộng 16.1 mm."""
    fp = pcbnew.FOOTPRINT(None)
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.Reference().SetPosition(V(0, 23.0)); fp.Reference().SetLayer(pcbnew.F_SilkS)
    fp.Value().SetText("HR911130A"); fp.Value().SetPosition(V(0, 12)); fp.Value().SetLayer(pcbnew.F_Fab)
    for t in (fp.Reference(), fp.Value()):
        t.SetTextSize(pcbnew.VECTOR2I(MM(1), MM(1))); t.SetTextThickness(MM(0.15))

    def th(num, x, y, drill, size, shape=pcbnew.PAD_SHAPE_CIRCLE):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(num)); p.SetAttribute(pcbnew.PAD_ATTRIB_PTH); p.SetShape(shape)
        p.SetSize(pcbnew.VECTOR2I(MM(size), MM(size))); p.SetDrillSize(pcbnew.VECTOR2I(MM(drill), MM(drill)))
        p.SetPosition(V(x, y)); p.SetLayerSet(pcbnew.PAD.PTHMask())
        fp.Add(p)

    def npth(x, y, drill):
        p = pcbnew.PAD(fp)
        p.SetNumber(""); p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(pcbnew.VECTOR2I(MM(drill), MM(drill))); p.SetDrillSize(pcbnew.VECTOR2I(MM(drill), MM(drill)))
        p.SetPosition(V(x, y)); p.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
        fp.Add(p)

    y_post = 10.92                      # trụ định vị cách mặt trước 10.92
    y_even, y_odd = y_post + 6.35, y_post + 8.89
    # chân tín hiệu Ø0.89 -> khoan 0.95, pad 1.5
    odd = {9: -4.445, 7: -1.905, 5: 0.635, 3: 3.175, 1: 5.715}
    even = {10: -5.715, 8: -3.175, 6: -0.635, 4: 1.905, 2: 4.445}
    for n, x in odd.items():
        th(n, x, y_odd, 0.95, 1.5, pcbnew.PAD_SHAPE_RECT if n == 1 else pcbnew.PAD_SHAPE_CIRCLE)
    for n, x in even.items():
        th(n, x, y_even, 0.95, 1.5)
    # chân LED Ø1.02 -> khoan 1.1, pad 1.7; hàng LED cách trụ 4.90 về phía trước
    y_led = y_post - 4.90
    for n, x in {14: -6.625, 13: -4.085, 12: 4.085, 11: 6.625}.items():
        th(n, x, y_led, 1.1, 1.7)
    # tai vỏ Ø1.63 -> khoan 1.75, pad 2.6
    for x in (-7.745, 7.745):
        th("SH", x, y_post + 3.05, 1.75, 2.3)
    # trụ nhựa Ø3.25 (không mạ)
    for x in (-5.715, 5.715):
        npth(x, y_post, 3.3)

    w, d = 16.1, 21.3
    rect(fp, pcbnew.F_Fab, -w / 2, 0, w / 2, d, 0.1)
    rect(fp, pcbnew.F_CrtYd, -w / 2 - 0.4, -0.25, w / 2 + 0.4, d + 0.4, 0.05)
    for x in (-w / 2 - 0.12, w / 2 + 0.12):
        line(fp, pcbnew.F_SilkS, x, 0.3, x, y_post + 1.2)
        line(fp, pcbnew.F_SilkS, x, y_post + 4.9, x, d + 0.12)
    line(fp, pcbnew.F_SilkS, -w / 2 - 0.12, d + 0.12, w / 2 + 0.12, d + 0.12)
    line(fp, pcbnew.F_SilkS, 6.6, d + 0.5, 7.6, d + 0.5)          # dấu chân 1
    fp.SetLibDescription("RJ45 HanRun HR911130A, 1000Base-T co bien ap va LED, nam ngang (ban ve Rev A)")
    fp.SetKeywords("RJ45 magjack gigabit")
    # mô hình 3D: dùng model magjack cổng đơn cùng kích thước bao (16 x 21.3 x 13.5 mm) của CM4 IO Board
    set_model(fp, "${KIPRJMOD}/lib/3dmodels/RJ45_magjack_16x21.stp", (0, -21.37, 6.8), (-90, 0, 180))
    save(fp, "RJ45_Hanrun_HR911130A_Horizontal")


def dc_jack():
    """Jack DC XKB DC-005-5A-2.0: lấy footprint BarrelJack_Horizontal của KiCad, chỉnh theo bản vẽ
    X-DC-005-5A-2.0: khe khoan 1.0 x 3.5 mm, chân 2 cách chân 1 là 5.9 mm."""
    fp = pcbnew.FootprintLoad(os.path.join(KFP, "Connector_BarrelJack.pretty"), "BarrelJack_Horizontal")
    geo = {"1": ((0.0, 0.0), (3.2, 4.3), (1.0, 3.5)),
           "2": ((-5.9, 0.0), (2.8, 4.3), (1.0, 3.5)),
           "3": ((-3.0, 4.7), (4.3, 2.8), (3.5, 1.0))}
    for pad in fp.Pads():
        pos, size, drill = geo[pad.GetNumber()]
        pad.SetPosition(V(*pos))
        pad.SetSize(pcbnew.VECTOR2I(MM(size[0]), MM(size[1])))
        pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(drill[0]), MM(drill[1])))
    fp.SetLibDescription("Jack DC 5.5x2.0/2.1 mm XKB DC-005-5A-2.0 (5 A), nam ngang, khe 1.0x3.5 mm")
    save(fp, "BarrelJack_XKB_DC-005-5A")


def cm4_wrl():
    """Tấm minh họa module CM4 (40 x 55 x 1.2 mm) cho ảnh render."""
    hx, hy, hz = 20 / 2.54, 27.5 / 2.54, 0.6 / 2.54      # đơn vị VRML của KiCad = 0.1 inch
    txt = """#VRML V2.0 utf8
Shape { appearance Appearance { material Material { diffuseColor 0.05 0.35 0.15 specularColor 0.2 0.2 0.2 shininess 0.3 transparency 0.25 } }
  geometry Box { size %.4f %.4f %.4f } }
Transform { translation 0 %.4f %.4f children [ Shape { appearance Appearance { material Material { diffuseColor 0.75 0.75 0.78 } }
  geometry Box { size %.4f %.4f %.4f } } ] }
""" % (2 * hx, 2 * hy, 2 * hz, 2.0 / 2.54, (0.6 + 1.2) / 2.54, 15 / 2.54, 15 / 2.54, 2.4 / 2.54)
    with open(os.path.join(HW, "lib", "3dmodels", "CM4_module_outline.wrl"), "w") as f:
        f.write(txt)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cm4_wrl()
    cm4()
    lqfp128_ep()
    hr911130a()
    dc_jack()
