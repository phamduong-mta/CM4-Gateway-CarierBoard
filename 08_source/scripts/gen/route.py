#!/usr/bin/env python3
"""Giai đoạn 2 — đi dây toàn bộ bo. Chạy sau board.py:  .venv/bin/python scripts/gen/route.py [buoc...]

Đọc hardware/cm4-gateway.kicad_pcb (đã bố trí), xoá mọi đường/via/vùng đồng cũ, đi dây lại từ đầu và ghi đè file.
Kết quả tất định: chạy lại cho cùng một bản đi dây.
"""
import fnmatch
import json
import math
import os
import pickle
import sys
import time

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rt_core as rc
from rt_core import RT, Fail, G, F, I2, B

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "..", "hardware"))
PCB = os.environ.get("CM4GW_PCB", os.path.join(HW, "cm4-gateway.kicad_pcb"))
PLACED = os.environ.get("CM4GW_PLACED")          # bản bố trí (chưa đi dây) dùng chung khi chạy nhiều phương án song song
# Phương án thứ tự đi dây (chạy song song nhiều phương án, giữ bản tốt nhất):
#   S = đi bus SPI vùng bảo mật trước cặp WAN, B = đi toàn bộ net vùng bảo mật trước, K = cấm cặp WAN đi qua vùng bảo mật
VARIANT = os.environ.get("CM4GW_VARIANT", "S")
W, H, OX, OY = 150.0, 105.0, 40.0, 30.0
MM, TM = pcbnew.FromMM, pcbnew.ToMM
KL = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]


def load(board):
    rt = RT(W, H)
    rt.netname = {}
    rt.netcode = {}
    rt.fp = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        plist = []
        for pad in fp.Pads():
            npth0 = pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            if not pad.IsOnCopperLayer() and not npth0:
                continue
            if npth0:
                # lỗ không mạ: vùng cấm đồng = lỗ + khoảng hở (lỗ vít của CM4 có khoảng hở riêng 1.7 mm)
                hs = pad.GetEffectiveHoleShape()
                sg = hs.GetSeg()
                keep = 1.75 if ref == "U201" else 0.35
                for L in range(3):
                    rt.stamp_seg(rt.cu[L], TM(sg.A.x) - OX, TM(sg.A.y) - OY, TM(sg.B.x) - OX, TM(sg.B.y) - OY,
                                 TM(hs.GetWidth()) / 2 + keep, rc.KEEP)
                rt.stamp_seg(rt.hole, TM(sg.A.x) - OX, TM(sg.A.y) - OY, TM(sg.B.x) - OX, TM(sg.B.y) - OY,
                             TM(hs.GetWidth()) / 2, True)
                continue
            tht = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            if tht:
                layers = (0, 1, 2)
                kl = pcbnew.F_Cu
            elif pad.IsOnLayer(pcbnew.F_Cu):
                layers, kl = (0,), pcbnew.F_Cu
            else:
                layers, kl = (2,), pcbnew.B_Cu
            ps = pad.GetEffectivePolygon(kl, pcbnew.ERROR_OUTSIDE)
            polys = []
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                polys.append([(TM(o.CPoint(k).x) - OX, TM(o.CPoint(k).y) - OY) for k in range(o.PointCount())])
            x, y = TM(pad.GetPosition().x) - OX, TM(pad.GetPosition().y) - OY
            drill = None
            if tht and pad.GetDrillSize().x > 0:
                hs = pad.GetEffectiveHoleShape()
                sg = hs.GetSeg()
                drill = (TM(sg.A.x) - OX, TM(sg.A.y) - OY, TM(sg.B.x) - OX, TM(sg.B.y) - OY, TM(hs.GetWidth()) / 2)
            net = pad.GetNetCode()
            name = pad.GetNetname()
            if net > 0:
                rt.netname[net] = name
                rt.netcode[name] = net
            npth = pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            rt.add_pad(net, name, x, y, polys, layers, ref, pad.GetNumber(), tht, drill,
                       keep_extra=0.25 if (npth or net <= 0) else 0.0)
            plist.append((pad.GetNumber(), x, y, net))
        for z in fp.Zones():
            if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
                ol = z.Outline()
                for i in range(ol.OutlineCount()):
                    o = ol.Outline(i)
                    pts = [(TM(o.CPoint(k).x) - OX, TM(o.CPoint(k).y) - OY) for k in range(o.PointCount())]
                    for L, kl in enumerate(KL):
                        if z.IsOnLayer(kl):
                            if z.GetDoNotAllowTracks():
                                rt.stamp_poly(rt.cu[L], pts, rc.KEEP)
                            if z.GetDoNotAllowVias():
                                rt.stamp_poly(rt.novia, pts, True)
        if len(plist) >= 16 and ref != "U201":
            xs = [q[1] for q in plist]
            ys = [q[2] for q in plist]
            rt.pairkeep[rc.cell(min(ys)):rc.cell(max(ys)) + 1, rc.cell(min(xs)):rc.cell(max(xs)) + 1] = True
        rt.fpsize[ref] = len(plist)
        rt.fp[ref] = dict(pads=plist, x=TM(fp.GetPosition().x) - OX, y=TM(fp.GetPosition().y) - OY,
                          side="F" if fp.GetLayer() == pcbnew.F_Cu else "B")
    return rt


def netclass_of(name, pats):
    for p in pats:
        if fnmatch.fnmatchcase(name, p["pattern"]):
            return p["netclass"]
    return "Default"


# --------------------------------------------------------------------------- cặp vi sai
def pair_names(rt):
    """Trả về list (nameP, nameN) theo hậu tố _P/_N hoặc DP/DN."""
    out = []
    for nm in sorted(rt.netcode):
        if nm.endswith("_P") and nm[:-2] + "_N" in rt.netcode:
            out.append((nm, nm[:-2] + "_N"))
        elif nm.endswith("DP") and nm[:-2] + "DN" in rt.netcode:
            out.append((nm, nm[:-2] + "DN"))
    return out


def snap8(vx, vy):
    a = round(math.atan2(vy, vx) / (math.pi / 4)) * (math.pi / 4)
    return (round(math.cos(a), 6), round(math.sin(a), 6))


def snap4(vx, vy):
    return (1.0 if vx > 0 else -1.0, 0.0) if abs(vx) >= abs(vy) else (0.0, 1.0 if vy > 0 else -1.0)


def group_centroid(rt, pad, other=None):
    fp = rt.fp[pad["ref"]]
    pl = fp["pads"]
    if pad["ref"] == "U201":
        hi = int(pad["num"]) > 100
        pl = [p for p in pl if p[0].isdigit() and (int(p[0]) > 100) == hi]
    if len(pl) <= 2 and other is not None and other["ref"] != pad["ref"]:
        pl = pl + rt.fp[other["ref"]]["pads"]
    return sum(p[1] for p in pl) / len(pl), sum(p[2] for p in pl) / len(pl)


def pad_ext(pad, e):
    return max((x - pad["x"]) * e[0] + (y - pad["y"]) * e[1] for pts in pad["polys"] for x, y in pts)


def terminal(rt, pP, pN, pitch):
    mx, my = (pP["x"] + pN["x"]) / 2, (pP["y"] + pN["y"]) / 2
    sx, sy = pN["x"] - pP["x"], pN["y"] - pP["y"]
    sep = math.hypot(sx, sy)
    cx, cy = group_centroid(rt, pP, pN)
    tht = pP["tht"] or pN["tht"]
    if tht:
        e = snap4(mx - cx, my - cy)
        d = 2.2
    else:
        px, py = snap4(-sy, sx)
        if px * (mx - cx) + py * (my - cy) < 0:
            px, py = -px, -py
        e = (px, py)
        big = len(rt.fp[pP["ref"]]["pads"]) >= 16
        d = max(pad_ext(pP, e), pad_ext(pN, e)) + max(0.6 if big else 0.2, (sep - pitch) / 2)
    T = (round((mx + e[0] * d) / G) * G, round((my + e[1] * d) / G) * G)
    # dịch T theo phương ngang để nằm đúng trục giữa 2 pad (giữ đối xứng), làm tròn về lưới
    return dict(T=T, e=e, L=pP["layers"][0] if not tht else 0, P=(pP["x"], pP["y"]), N=(pN["x"], pN["y"]), tht=tht,
                pP=pP, pN=pN, sep=sep, free=0.3)


def find_terminals(rt, nP, nN, pitch):
    """Ghép pad của net P với pad của net N thành các đầu cặp."""
    PP = list(rt.pads[nP])
    NN = list(rt.pads[nN])
    terms = []
    for p in PP:
        best = None
        for q in NN:
            dd = math.hypot(p["x"] - q["x"], p["y"] - q["y"])
            lim = 3.2 if p["tht"] else 2.0
            if dd < lim and p["layers"] == q["layers"] and (best is None or dd < best[0]):
                best = (dd, q)
        if best:
            NN.remove(best[1])
            terms.append(terminal(rt, p, best[1], pitch))
    return terms


def _terminal_by_ref(rt, terms, ref, opt, pitch):
    for t in terms:
        if ref in (t["pP"]["ref"], t["pN"]["ref"]):
            if opt and "e" in opt:
                e = opt["e"]
                d = max(pad_ext(t["pP"], e), pad_ext(t["pN"], e)) + opt.get("d", 0.6)
                mx, my = (t["P"][0] + t["N"][0]) / 2, (t["P"][1] + t["N"][1]) / 2
                t = dict(t, e=e, T=(round((mx + e[0] * d) / G) * G, round((my + e[1] * d) / G) * G))
            return t
    raise KeyError("khong co dau cap tai %s" % ref)


LV = 0.6


def route_pair(rt, base, nodes=None, w=0.15, s=0.15, clr=0.15, layers=(0, 1), tol=0.08, verbose=True, sfx=("_P", "_N"),
               under_ic=False, tails=False, avoid_rects=None):
    """Đi 1 cặp vi sai. nodes = danh sách mốc:
       ("T", ref[, {e: (ex, ey)}])            đầu cặp tại linh kiện ref
       ("W", x, y, (dx, dy), L)               đi qua điểm (x, y) theo hướng (dx, dy) trên lớp L
       ("V", x, y, (dx, dy), L1, L2)          cặp via tại (x, y), đang đi theo hướng (dx, dy), đổi lớp L1 -> L2
       ("A",)                                 chặng kế tiếp được tự đổi lớp (A* tự đặt via)
    Không có nodes: nối 2 đầu xa nhau nhất, tự đổi lớp nếu cần."""
    nameP, nameN = base + sfx[0], base + sfx[1]
    nP, nN = rt.netcode[nameP], rt.netcode[nameN]
    terms = find_terminals(rt, nP, nN, w + s)
    if nodes is None:
        if len(terms) < 2:
            rt.log.append("CAP %s: chi co %d dau" % (base, len(terms)))
            return None
        best = None
        for i in range(len(terms)):
            for j in range(i + 1, len(terms)):
                dd = math.hypot(terms[i]["T"][0] - terms[j]["T"][0], terms[i]["T"][1] - terms[j]["T"][1])
                if best is None or dd > best[0]:
                    best = (dd, i, j)
        ta, tb = terms[best[1]], terms[best[2]]
        seq = [("t", ta), ("A",), ("t", tb)]
    else:
        seq = []
        for nd in nodes:
            if nd[0] == "T":
                seq.append(("t", _terminal_by_ref(rt, terms, nd[1], nd[2] if len(nd) > 2 else None, w + s)))
            else:
                seq.append(nd)
        ta = seq[0][1]
        tb = seq[-1][1] if seq[-1][0] == "t" else None
    avoid = [p for p in rt.pads[nP] + rt.pads[nN] if not p["tht"]]      # tim cặp không được đè lên pad nào
    verts = []
    cur = dict(T=ta["T"], e=ta["e"], L=ta["L"], free=0.3)
    auto = False
    try:
        for nd in seq[1:]:
            if nd[0] == "A":
                auto = True
                continue
            if nd[0] == "t":
                goal = dict(T=nd[1]["T"], e=nd[1]["e"], L=nd[1]["L"])
                nxt = None
                extra = []
            elif nd[0] in ("W", "E"):
                _, x, y, d, L = nd[:5]
                goal = dict(T=(x, y), e=(-d[0], -d[1]), L=L)
                nxt = dict(T=(x, y), e=d, L=L, free=0.3)
                extra = []
            else:
                _, x, y, d, L1, L2 = nd
                goal = dict(T=(x - d[0] * LV, y - d[1] * LV), e=(-d[0], -d[1]), L=L1)
                nxt = dict(T=(x + d[0] * LV, y + d[1] * LV), e=d, L=L2, free=0.3)
                extra = [(L1, x, y, "v"), (L2, x, y, "w")]
            lay = tuple(sorted(set(layers))) if auto else tuple(sorted({cur["L"], goal["L"]}))
            short = math.hypot(cur["T"][0] - goal["T"][0], cur["T"][1] - goal["T"][1]) < 3.0
            leg = None
            for m, mx in ((4.0, 3000000), (12.0, 20000000), (30.0, 80000000)):
                try:
                    leg = rt.pair_path((nP, nN), cur, goal, w, s, clr, layers=lay, margin=m, maxexp=mx,
                                       keep=None if under_ic else rt.pairkeep, avoid=avoid,
                                       run0=2 if short else 8, minrun=3 if short else 6,
                                       keep_all=None if not avoid_rects else rect_mask(rt, avoid_rects, inset=0.0))
                    break
                except Fail:
                    continue
            if leg is None:
                raise Fail("chang toi %s" % (str(nd[:3]) if nd[0] != "t" else nd[1]["pP"]["ref"]))
            verts += leg if not verts else leg[1:]
            verts += extra
            if nxt:
                if extra:
                    verts.append((nxt["L"], nxt["T"][0], nxt["T"][1], "n"))
                cur = nxt
            auto = False
    except Fail as ex:
        rt.log.append("CAP %s: KHONG TIM DUOC DUONG (%s)" % (base, ex))
        return None
    polyP, polyN, side = rt.pair_emit(nP, nN, verts, ta, tb, w, s)
    twisted = False
    if tb is not None:
        eb = tb["e"]
        tb_dir = (-eb[0], -eb[1])
        nb = (-tb_dir[1], tb_dir[0])
        side_b = 1 if ((tb["P"][0] - tb["T"][0]) * nb[0] + (tb["P"][1] - tb["T"][1]) * nb[1]) > 0 else -1
        twisted = side_b != side
    if twisted:
        rt.log.append("CAP %s: DAO CUC o dau %s" % (base, tb["pP"]["ref"]))
    for net, poly, key in ((nP, polyP, "pP"), (nN, polyN, "pN")):
        other = nN if net == nP else nP
        rt.emit_path(net, poly, w, (0.45, 0.2))
        for t, end in ((ta, poly[0]), (tb, poly[-1])):
            if t is None:
                continue
            pad = t[key]
            L = end[0]
            direct = (not t["tht"]) and L in pad["layers"] and \
                rt.seg_free((net, other), L, pad["x"], pad["y"], end[1], end[2], w / 2 + 0.13 + 0.02)
            if direct:
                rt.add_track(net, L, pad["x"], pad["y"], end[1], end[2], w)
            else:
                rt.log.append("  (cap %s: pad %s.%s noi vong, khong di thang duoc)" % (base, pad["ref"], pad["num"]))
                gm = [np.zeros((rt.ny, rt.nx), bool) for _ in range(3)]
                rt.stamp_seg(gm[L], end[1], end[2], end[1], end[2], 0.03, True)
                try:
                    rt.connect(net, [(l, pad["x"], pad["y"]) for l in pad["layers"]], gm, w, 0.11,
                               layers=(L,), margin=2.5, step=1, via=None)
                except Fail:
                    rt.log.append("CAP %s: khong noi duoc pad %s.%s vao cap" % (base, pad["ref"], pad["num"]))
    if tb is None or tails:
        # đầu cặp kết thúc tại điểm mốc: nối từng dây vào các pad còn lại của net (được đổi lớp nếu cần)
        for net in (nP, nN):
            if not rt.route_net(net, w, 0.13, done=rt.tree_of(net), step=1, margins=(3.0, 8.0)):
                rt.log.append("CAP %s: khong noi duoc duoi vao pad" % base)
    lp, ln = rt.net_length(nP), rt.net_length(nN)
    if abs(lp - ln) > tol:
        short, other = (nP, nN) if lp < ln else (nN, nP)
        rt.tune(short, other, abs(lp - ln), w, 0.13)
    lp2, ln2 = rt.net_length(nP), rt.net_length(nN)
    nv = sum(1 for v in verts if v[3] == "v")
    if verbose:
        print("  %-22s dai %.2f / %.2f  (truoc bu: lech %.2f)  sau bu: lech %.3f  via %d%s" % (
            base, lp2, ln2, abs(lp - ln), abs(lp2 - ln2), nv, "  DAO-CUC" if twisted else ""), flush=True)
    rt.pairs.append(dict(base=base, P=nameP, N=nameN, lp=lp2, ln=ln2, vias=nv, twisted=twisted, w=w, s=s,
                         layers=sorted({v[0] for v in verts})))
    return rt.pairs[-1]


# --------------------------------------------------------------------------- kế hoạch PCIe
N_, S_, E_, W_ = (0, -1), (0, 1), (1, 0), (-1, 0)
SW_, NE_ = (-1, 1), (1, -1)
CY, YN, CLK_R, VIA_DY = 50.0, 76.0, 13.0, 2.4


def plan_switch_local(rt, n, cx, lan_e, lan_w):
    """Các cặp ngắn quanh 1 switch: chân -> tụ AC, chân -> Rs, NIC -> tụ HSO."""
    sw = "/SW%d/" % (n - 3)
    for k in ("UP_TXC", "DN1_TXC", "DN2_TXC", "DN3_TXC", "SELFCLK", "CLKO3", "CLKO0", "CLKO2", "CLKO1"):
        route_pair(rt, sw + k)
    for lan in (lan_e, lan_w):
        route_pair(rt, "/LAN%d/HSO" % lan)


def plan_switch_clocks(rt, n, cx, lan_e, lan_w):
    sw = "/SW%d/" % (n - 3)
    vy = CY + CLK_R + VIA_DY
    for xc, lan in ((0.8, lan_e), (-1.6, lan_w)):
        xn = (cx + 11.6) if lan == lan_e else (cx - 6.6)
        rs = "R%d%02d" % (n, 8 if lan == lan_e else 12)
        mid = [("W", xn - 4.6, YN - 6.6, E_, I2), ("W", xn + 3.9, YN - 4.6, S_, I2)] if lan == lan_e else []
        route_pair(rt, "P%d_CLK" % lan, [("T", rs), ("V", cx + xc, vy, S_, F, I2)] + mid +
                   [("V", xn + 3.9, YN - 2.6, S_, I2, F), ("T", "U%d01" % (5 + lan))])
    # clock tự vòng: Rs -> via xuống mặt dưới -> vòng qua góc dưới-phải -> via lên -> tụ AC -> REFCLKP/N
    route_pair(rt, sw + "SELFT", [("T", "R%d04" % n), ("V", cx + 3.2, vy, S_, F, B),
                                  ("V", cx + 15.7, CY + 0.8, W_, B, F), ("T", "C%d09" % n)], layers=(0, 2))


def pad_of(rt, ref, num):
    for net, pads in rt.pads.items():
        for p in pads:
            if p["ref"] == ref and p["num"] == num:
                return net, p
    raise KeyError(ref + "." + num)


def plan_clock_shunts(rt, n, cx):
    """Nối Rp (mặt dưới) vào cặp via ngay sau Rs bằng hai đoạn đối xứng; cổng không dùng (SW2 CLKO3) được thêm via."""
    vy = CY + CLK_R + VIA_DY
    for k0, xc in ((16, -4.0), (12, -1.6), (8, 0.8), (4, 3.2)):
        for sgn, dk in ((1, 1), (-1, 3)):
            net, pad = pad_of(rt, "R%d%02d" % (n, k0 + dk), "1")
            vx = cx + xc + sgn * 0.35
            if not any(v[0] == net and abs(v[1] - vx) < 0.01 and abs(v[2] - vy) < 0.01 for v in rt.vias):
                _, rs = pad_of(rt, "R%d%02d" % (n, k0 + dk - 1), "2")
                rt.add_track(net, F, rs["x"], rs["y"], vx, vy, 0.15)
                rt.add_via(net, vx, vy, 0.45, 0.2)
            rt.add_track(net, B, vx, vy, pad["x"], pad["y"], 0.15)


def plan_clock_bias(rt, cx):
    """Điện trở phân cực clock CM4 (mặt dưới) nối đối xứng vào cặp via dưới thân SW1."""
    for sgn, ra, rb in ((1, ("R210", "1"), ("R209", "2")), (-1, ("R212", "1"), ("R211", "2"))):
        net, pa = pad_of(rt, *ra)
        _, pb = pad_of(rt, *rb)
        vx, vy = cx - 2.8 + sgn * 0.35, CY + 5.0
        rt.add_track(net, B, vx, vy, pa["x"], pa["y"], 0.15)
        rt.add_track(net, B, pa["x"], pa["y"], pb["x"], pb["y"], 0.15)


def plan_switch_lanes(rt, n, cx, lan_e, lan_w):
    u = "U%d01" % n
    ne, nw = "U%d01" % (5 + lan_e), "U%d01" % (5 + lan_w)
    route_pair(rt, "P%d_SW2NIC" % lan_e, [("T", "C%d05" % n), ("W", cx + 16.5, CY + 12.0, S_, F), ("T", ne)])
    route_pair(rt, "P%d_NIC2SW" % lan_e, [("T", "C%d01" % (5 + lan_e)), ("W", cx + 14.9, CY + 14.0, N_, F),
                                          ("W", cx + 14.9, CY + 6.4, N_, F), ("T", u)])
    route_pair(rt, "P%d_NIC2SW" % lan_w, [("T", "C%d01" % (5 + lan_w)), ("W", cx + 3.0, CY + 17.8, E_, F),
                                          ("W", cx + 11.8, CY + 8.8, (-1, -1), F), ("T", u)])
    route_pair(rt, "P%d_SW2NIC" % lan_w, [("T", "C%d03" % n), ("W", cx + 13.4, CY + 9.6, S_, F),
                                          ("W", cx + 1.5, CY + 18.9, W_, F), ("W", cx - 1.7, CY + 21.0, S_, F),
                                          ("T", nw)])


def plan_pcie(rt):
    c1, c2 = 60.0, 23.6
    # 1) làn lên CM4
    route_pair(rt, "PCIE_TX", [("T", "U201"), ("W", 75.5, 36.6, W_, F), ("T", "U401")])
    plan_switch_local(rt, 4, c1, 1, 2)
    plan_switch_local(rt, 5, c2, 3, 4)
    route_pair(rt, "PCIE_RX", [("T", "C401"), ("W", 75.5, 37.8, E_, F), ("T", "U201")])
    # 2) liên kết giữa hai switch (lớp trong, vòng phía bắc SW1 rồi quay lại cạnh phải SW1)
    route_pair(rt, "X_SW2TO1", [("T", "C501"), ("V", c2 + 15.8, CY - 5.0, E_, F, I2),
                                ("W", c1 + 0.0, CY - 14.4, E_, I2),
                                ("V", c1 + 18.1, CY - 3.6, W_, I2, F), ("T", "U401")])
    route_pair(rt, "X_SW1TO2", [("T", "C407"), ("V", c1 + 16.1, CY - 2.0, E_, F, I2),
                                ("W", c1 + 0.0, CY - 15.3, W_, I2),
                                ("V", c2 + 17.7, CY - 6.3, W_, I2, F), ("T", "U501")])
    # 3) clock vào REFCLKI (từ phía trong thân chip)
    route_pair(rt, "PCIE_CLK", [("T", "U201"), ("A",),
                                ("V", c1 - 2.8, CY + 5.0, S_, I2, F), ("T", "U401", {"e": N_})], under_ic=True)
    route_pair(rt, "SW2_CLK", [("T", "R416"), ("V", c1 - 4.0, CY + CLK_R + VIA_DY, S_, F, I2),
                               ("W", c2 + 10.0, CY + 10.4, W_, I2),
                               ("V", c2 - 2.8, CY + 5.0, S_, I2, F), ("T", "U501", {"e": N_})], under_ic=True)
    plan_switch_clocks(rt, 4, c1, 1, 2)
    plan_switch_clocks(rt, 5, c2, 3, 4)
    plan_clock_shunts(rt, 4, c1)
    plan_clock_shunts(rt, 5, c2)
    plan_clock_bias(rt, c1)
    # 4) làn dữ liệu switch <-> NIC (toàn bộ trên lớp trên)
    plan_switch_lanes(rt, 4, c1, 1, 2)
    plan_switch_lanes(rt, 5, c2, 3, 4)


X_LAN = {4: 17.0, 3: 35.2, 2: 53.4, 1: 71.6}
X_WAN = 133.0
MDI = dict(w=0.125, s=0.18, clr=0.15, tol=0.3)
DPDN = ("DP", "DN")


def plan_mdi(rt):
    for k, x in X_LAN.items():
        u, b = "U%d01" % (5 + k), "/LAN%d/MDI" % k
        route_pair(rt, b + "1", [("T", u), ("V", x, YN + 5.0, S_, F, I2), ("E", x, 85.4, S_, I2)], **MDI)
        route_pair(rt, b + "0", [("T", u), ("E", x - 3.8, 85.6, S_, F)], **MDI)
        route_pair(rt, b + "2", [("T", u), ("E", x, 85.6, S_, F)], **MDI)
        route_pair(rt, b + "3", [("T", u), ("E", x + 3.8, 85.6, S_, F)], **MDI)
    for base, nodes in WAN_PLAN():
        route_pair(rt, base, nodes, avoid_rects=WAN_AVOID if "K" in VARIANT else None, **MDI)


# Vùng bảo mật (TPM, RTC, SRAM/tamper): cấm cặp MDI của WAN đi xuyên qua để còn chỗ đặt via cho các net chậm.
WAN_AVOID = [(121.3, 50.0, 147.7, 83.3)]


def WAN_PLAN():
    x = X_WAN
    return [("WAN_MDI3", [("T", "U201", {"sel": 3}), ("V", 119.7, 40.2, E_, F, I2), ("W", 123.5, 40.2, E_, I2),
                          ("E", x + 3.8, 85.6, S_, I2)]),
            ("WAN_MDI2", [("T", "U201"), ("W", 121.6, 41.5, S_, F), ("V", 121.6, 43.0, S_, F, I2),
                          ("V", x + 0.6, 84.2, E_, I2, F), ("E", x, 85.9, S_, F)]),
            ("WAN_MDI1", [("T", "U201"), ("V", 110.2, 40.2, W_, F, I2), ("E", x - 0.3, 85.2, S_, I2)]),
            ("WAN_MDI0", [("T", "U201"), ("V", 111.6, 39.0, W_, F, I2), ("E", x - 3.8, 85.6, S_, I2)])]


def plan_usb(rt):
    U = "/USB_Debug/"
    route_pair(rt, "USB_", sfx=DPDN)
    route_pair(rt, U + "USBA_", [("T", "U1001"), ("W", 94.2, 75.73, E_, F), ("W", 95.2, 78.5, S_, F), ("T", "U1002")], sfx=DPDN)
    route_pair(rt, U + "USBC_", [("T", "U1001"), ("V", 92.5, 76.73, E_, F, I2), ("A",), ("T", "U1004")], sfx=DPDN)
    route_pair(rt, U + "USBA_CON_", [("T", "U1002"), ("E", 90.0, 92.0, S_, F)], sfx=DPDN, tol=0.3)
    route_pair(rt, U + "USBC_CON_", [("T", "U1004"), ("E", 116.0, 95.3, S_, F)], sfx=DPDN, tol=0.3)


# --------------------------------------------------------------------------- nguồn, mass, tín hiệu thường
# Chia vùng lớp nguồn In4 (L5). Ưu tiên cao đè lên ưu tiên thấp.  (x0, y0, x1, y1)
Z_1V0 = [(2.5, 40.0, 15.0, 64.0), (15.0, 39.5, 32.4, 58.8), (32.4, 46.5, 51.2, 53.5), (51.2, 39.5, 68.8, 58.8)]
Z_5V = [(22.5, 0.3, 149.7, 30.5), (79.5, 30.5, 149.7, 104.7)]
Z_3V3SW = [(0.3, 0.3, 149.7, 104.7)]
P_1V0 = [(2.5, 40.0), (15.0, 40.0), (15.0, 39.5), (32.4, 39.5), (32.4, 46.5), (51.2, 46.5), (51.2, 39.5), (68.8, 39.5),
         (68.8, 58.8), (51.2, 58.8), (51.2, 53.5), (32.4, 53.5), (32.4, 58.8), (15.0, 58.8), (15.0, 64.0), (2.5, 64.0)]
P_5V = [(22.5, 0.3), (149.7, 0.3), (149.7, 104.7), (79.5, 104.7), (79.5, 30.5), (22.5, 30.5)]
PLANE_W = {"GND": 0.25, "+5V": 0.3, "+3V3_SW": 0.25, "+1V0": 0.25}


def rect_mask(rt, rects, inset=0.6):
    m = np.zeros((rt.ny, rt.nx), bool)
    for x0, y0, x1, y1 in rects:
        m[max(0, rc.cell(y0 + inset)):rc.cell(y1 - inset) + 1, max(0, rc.cell(x0 + inset)):rc.cell(x1 - inset) + 1] = True
    return m


# Khe +3V3_SW trong đảo +1V0 cho chân VDDR (8, 15) ở hàng trên của mỗi switch.
N_3V3 = [(x - 0.75, 40.6, x + 0.75, 44.4) for x in (63.4, 60.6, 27.0, 24.2)]


def plane_masks(rt):
    notch = rect_mask(rt, N_3V3, inset=0.3)
    m10 = rect_mask(rt, Z_1V0) & ~rect_mask(rt, N_3V3, inset=-0.6)
    not10 = ~(rect_mask(rt, Z_1V0, inset=-0.6) & ~notch)
    m5 = rect_mask(rt, Z_5V) & not10
    not5 = ~rect_mask(rt, Z_5V, inset=-0.6)
    m33 = rect_mask(rt, Z_3V3SW) & not10 & not5
    return {"GND": None, "+5V": m5, "+3V3_SW": m33, "+1V0": m10}


def pad_area(p):
    a = 0.0
    for pts in p["polys"]:
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
    return abs(a) / 2


def ep_vias(rt, ref, nx, ny, pitch, dia=0.5, drill=0.25):
    """Via tản nhiệt trong đế (EP) của IC; bỏ vị trí nào vướng đường lớp trong / linh kiện mặt dưới."""
    f = rt.fp[ref]
    ep = max((p for p in rt.pads[rt.netcode["GND"]] if p["ref"] == ref), key=pad_area)
    gnd = rt.netcode["GND"]
    n = 0
    for i in range(nx):
        for j in range(ny):
            x = ep["x"] + (i - (nx - 1) / 2) * pitch
            y = ep["y"] + (j - (ny - 1) / 2) * pitch
            win = rt.window([(x, y)], 1.0)
            ok = True
            for L in (1, 2):
                d = rt.dist_other(L, (gnd,), win, 20)
                if d[rc.cell(y) - win[1], rc.cell(x) - win[0]] < dia / 2 + 0.2:
                    ok = False
            dh = rt.dist_hole(win, 20)
            if dh[rc.cell(y) - win[1], rc.cell(x) - win[0]] < drill / 2 + 0.3:
                ok = False
            if ok:
                rt.add_via(gnd, x, y, dia, drill)
                n += 1
    return n


def fanout_planes(rt, order=("+1V0", "+3V3_SW", "+5V", "GND")):
    zm = plane_masks(rt)
    stat = {}
    for name in order:
        net = rt.netcode[name]
        done = fail = 0
        pads = [p for p in rt.pads[net] if not p["tht"]]
        # IC nhiều chân trước (khó thoát nhất), rồi tới tụ
        pads.sort(key=lambda p: (-len(rt.fp[p["ref"]]["pads"]), p["ref"], p["num"]))
        for p in pads:
            a = pad_area(p)
            if a > 20:
                continue                                  # đế tản nhiệt: đã có via riêng
            zone = zm[name]
            n = 4 if a > 6 else (2 if a > 1.2 else 1)
            big = a > 1.2
            got = rt.fanout_pad(net, p, zone, w=min(PLANE_W[name], 0.2) if a < 0.2 else (0.4 if big else PLANE_W[name]),
                                via=(0.6, 0.3, 0.13) if big else (0.45, 0.2, 0.13), n=n)
            if got:
                done += 1
            else:
                fail += 1
        stat[name] = (done, fail)
    return stat


def net_width(name, cls):
    if name in ("+5V",):
        return (0.8, 0.4, 0.25)
    if name in ("+3V3_SW", "+1V0"):
        return (0.4, 0.25, 0.15)
    if name in ("+3V3", "CHASSIS"):
        return (0.3, 0.2, 0.15)
    if name == "GND":
        return (0.25, 0.15)
    if cls == "PWR_HV":
        return (1.0, 0.8, 0.6)
    if name in ("/Power/SW_3V3", "/Power/SW_1V0"):
        return (0.6, 0.5)
    if cls == "PWR":
        return (0.3, 0.2, 0.15)
    return (0.15,)


def prepare_fanout(rt):
    """Vùng cấm via quanh IC chân nhỏ: dải 1.0 mm ngay ngoài hàng pad (hành lang thoát chân) — via nguồn/mass
    phải đặt xa hơn hoặc dưới thân chip, để các chân tín hiệu kề bên còn lối ra."""
    for ref, f in rt.fp.items():
        pl = [q for q in f["pads"] if q[3] > 0]
        if len(f["pads"]) < 24 or ref == "U201":
            continue
        xs = [q[1] for q in f["pads"]]
        ys = [q[2] for q in f["pads"]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        o, i = 1.35, 0.75          # tính từ tâm hàng pad: cấm từ -0.75 (mép trong pad) tới +1.35 mm
        outer = np.zeros((rt.ny, rt.nx), bool)
        outer[rc.cell(y0 - o):rc.cell(y1 + o) + 1, rc.cell(x0 - o):rc.cell(x1 + o) + 1] = True
        outer[rc.cell(y0 + i):rc.cell(y1 - i) + 1, rc.cell(x0 + i):rc.cell(x1 - i) + 1] = False
        rt.novia |= outer


# Sơ đồ thoát chân cố định cho RTL8111H (QFN-32, bước 0.4 mm), toạ độ tương đối so với tâm NIC (x sang phải, y về mặt trước).
# Mỗi chân: danh sách điểm của đoạn đường trên lớp trên; True = đặt via ở điểm cuối.
NIC_ESC = {
    "3": ([(-0.6, 3.5), (-1.0, 3.9), (-1.0, 4.25)], True),          # V1P0 giữa MDI0 và MDI1
    "8": ([(1.4, 3.3), (2.1, 4.0), (2.4, 4.0)], True),              # V1P0 giữa MDI2 và MDI3
    "11": ([(4.3, 0.6), (4.6, 0.9)], True),                         # +3V3_SW
    "12": ([(5.35, 0.2)], True),                                    # CLKREQ#
    "19": ([(0.6, -2.45), (-0.3, -5.4)], True),                      # PERST#
    "20": ([(0.2, -2.45), (-1.1, -5.4)], True),                     # ISOLATE#
    "21": ([(-0.2, -2.45), (-1.9, -5.4)], True),                    # LANWAKE#
    "22": ([(-0.6, -2.45), (-2.7, -5.4)], True),                    # V1P0
    "23": ([(-1.0, -2.45), (-3.5, -5.4)], True),                    # +3V3_SW
    "24": ([(-1.4, -2.45), (-4.3, -5.4)], True),                    # V1P0
    "25": ([(-2.7, -1.4), (-3.3, -2.0)], True),                     # LED xanh
    "26": ([(-3.6, -1.0), (-4.2, -1.6)], True),                     # LED vàng
    "28": ([(-4.6, -0.2)], False),                                  # XTAL1 -> thạch anh bên trái
    "29": ([(-4.6, 0.2)], False),                                   # XTAL2
    "30": ([(-4.2, 0.6), (-4.4, 0.8)], True),                       # V1P0
    "31": ([(-3.5, 1.0), (-3.9, 1.4)], False),                      # RSET -> điện trở 2.49 k ngay bên dưới
    "32": ([(-2.5, 1.4), (-2.9, 1.8)], True),                       # +3V3_SW
}

MINW = {"+12V": 0.6, "+12V_JACK": 0.6, "/Power/VIN_FUSED": 0.6, "/Power/SW_5V": 0.6,
        "/Power/SW_3V3": 0.5, "/Power/SW_1V0": 0.5}
# Rev B (review M1): khu buck phía tây — dây cũ của 3 net này trong hộp (toạ độ bo) bị bỏ và nối lại rộng ≥ 0.5 mm
MINW_LOCAL = {"+5V": 0.5, "+3V3_SW": 0.5, "+1V0": 0.5}
BUCK_BOX = ((0.0, 14.0, 21.0, 36.5), (0.0, 38.0, 13.5, 49.5))     # buck 3V3 / buck 1V0 (tránh U501)


def pre_power(rt):
    """Rev B (review rev A R1/R3/R4): đồng nguồn dòng lớn của 3 bộ buck đi TRƯỚC, bằng dải rộng cố định."""
    rt.minw = {rt.netcode[n]: w for n, w in MINW.items() if n in rt.netcode}
    P = lambda ref, num: pad_of(rt, ref, num)
    # U101 (12 V -> 5 V): VIN — dải 1 mm qua pad +12V của C105, C104, C106 tới chân 2 (cổ 0.6 mm giữa hai chân kề)
    n, v = P("U101", "2")
    _, c105 = P("C105", "1")
    rt.add_track(n, 0, v["x"], v["y"], v["x"] - 1.45, v["y"], 0.6)
    rt.add_track(n, 0, v["x"] - 1.45, v["y"] - 0.47, c105["x"], v["y"] - 0.47, 1.0)
    # SW: chân 8 -> L101.1 (dải 1 mm) -> D104 (catốt) dải 1.5 mm
    n, sw = P("U101", "8")
    _, l1 = P("L101", "1")
    _, dk = P("D104", "1")
    _, cb = P("C109", "2")
    rt.add_track(n, 0, sw["x"] + 0.55, sw["y"] - 0.14, l1["x"], sw["y"] - 0.14, 1.0)
    rt.add_track(n, 0, dk["x"] + 0.9, l1["y"], dk["x"] + 0.9, dk["y"], 1.5)
    # GND vòng nóng: anốt D104 -> GND tụ vào C106/C104 trên F.Cu (1.0 mm), không phụ thuộc mảng đồng đổ
    g, da = P("D104", "2")
    _, g106 = P("C106", "2")
    _, g104 = P("C104", "2")
    rt.add_track(g, 0, da["x"], da["y"], g106["x"], da["y"] - (da["x"] - g106["x"]), 1.0)
    rt.add_track(g, 0, g106["x"], da["y"] - (da["x"] - g106["x"]), g106["x"], g106["y"] + 0.15, 1.0)
    rt.add_track(g, 0, g106["x"], g104["y"], g104["x"], g104["y"], 0.8)
    rt.add_track(n, 0, cb["x"], cb["y"], sw["x"] - 0.45, cb["y"], 0.3)
    rt.add_track(n, 0, sw["x"] - 0.45, cb["y"], sw["x"], cb["y"] + 0.45, 0.3)
    rt.add_track(n, 0, sw["x"], cb["y"] + 0.45, sw["x"], sw["y"], 0.3)
    # +5V: L101.2 -> C110..C113 dải 1.5 mm
    n, l2 = P("L101", "2")
    _, c113 = P("C113", "1")
    rt.add_track(n, 0, l2["x"], c113["y"] - 0.15, c113["x"], c113["y"] - 0.15, 1.5)
    # U102/U103: SW chân 2 -> cuộn cảm (0.6 mm), tụ boot -> VBST và -> nút SW (0.5 mm)
    for u, l, c in (("U102", "L102", "C117"), ("U103", "L103", "C123")):
        n, sp = P(u, "2")
        _, lp = P(l, "1")
        _, bst = P(u, "6")
        _, c1 = P(c, "1")
        _, c2 = P(c, "2")
        rt.add_track(n, 0, sp["x"], sp["y"], lp["x"], sp["y"], 0.6)
        rt.add_track(pad_of(rt, c, "1")[0], 0, c1["x"], c1["y"], bst["x"], bst["y"], 0.3)
        rt.add_track(n, 0, c2["x"], c2["y"], lp["x"] + 0.4, c2["y"], 0.5)
        rt.add_track(n, 0, lp["x"] + 0.4, c2["y"], lp["x"], c2["y"] + 0.4, 0.5)
        rt.add_track(n, 0, lp["x"], c2["y"] + 0.4, lp["x"], sp["y"], 0.5)
    # VIN chân 3 -> tụ vào (0.6 mm); ra cuộn cảm pad 2 -> 2 tụ ra (0.6 mm)
    for u, l, cin, couts in (("U102", "L102", "C115", ("C119", "C118")), ("U103", "L103", "C121", ("C124", "C125"))):
        n, vi = P(u, "3")
        _, ci = P(cin, "1")
        rt.add_track(n, 0, vi["x"], vi["y"], ci["x"], vi["y"] + 0.35, 0.6)
        rt.add_track(n, 0, ci["x"], vi["y"] + 0.35, ci["x"], ci["y"], 0.6)
        n, lo = P(l, "2")
        _, o1 = P(couts[0], "1")
        _, o2 = P(couts[1], "1")
        rt.add_track(n, 0, lo["x"], lo["y"], o1["x"], o1["y"], 0.6)
        rt.add_track(n, 0, o1["x"], o1["y"], o2["x"], o2["y"], 0.6)


def pre_escape(rt):
    """Kéo sẵn mọi chân không thuộc cặp vi sai của 4 NIC ra via / điểm thoát theo sơ đồ cố định, TRƯỚC khi đi cặp
    (chân bước 0.4 mm nếu để bộ đi dây tự xử lý lần lượt sẽ bị các đường bên cạnh bịt lối ra)."""
    for k, x in X_LAN.items():
        ref = "U%d01" % (5 + k)
        for num, (pts, via) in NIC_ESC.items():
            net, p = pad_of(rt, ref, num)
            if not rt.netname.get(net, "").strip() or rt.netname[net].startswith("unconnected-"):
                continue
            prev = (p["x"], p["y"])
            for dx, dy in pts:
                rt.add_track(net, F, prev[0], prev[1], x + dx, YN + dy, 0.15)
                prev = (x + dx, YN + dy)
            if via:
                rt.add_via(net, prev[0], prev[1], 0.45, 0.2)
    # AVDDH (chân 113, cạnh phải switch): via ngay ngoài chân; mặt dưới đi giữa 2 pad GND của C421/C422 tới pad 1 của
    # hai tụ, và đi thẳng lên hạt ferrite
    for n, cx in ((4, 60.0), (5, 23.6)):
        net, p = pad_of(rt, "U%d01" % n, "113")
        _, c1 = pad_of(rt, "C%d21" % n, "1")
        _, c2 = pad_of(rt, "C%d22" % n, "1")
        _, fb = pad_of(rt, "FB%d03" % n, "2")
        ym = (c1["y"] + c2["y"]) / 2
        vx = cx + 8.95
        xm = (c1["x"] + c2["x"]) / 2
        rt.add_track(net, F, p["x"], p["y"], vx, ym, 0.15)
        rt.add_via(net, vx, ym, 0.4, 0.2)
        rt.add_track(net, B, vx, ym, xm, ym, 0.15)
        rt.add_track(net, B, xm, ym, c1["x"], c1["y"], 0.15)
        rt.add_track(net, B, xm, ym, c2["x"], c2["y"], 0.15)
        rt.add_track(net, B, vx, ym, fb["x"], fb["y"], 0.15)
    # hai switch: mọi chân có nối ở hàng trên (chân 1-32) thoát thẳng ra ngoài tới via so le 2 hàng; chân 92 (TMS) tương tự
    for ref, cx in (("U401", 60.0), ("U501", 23.6)):
        for num, x, y, net in rt.fp[ref]["pads"]:
            if not num.isdigit() or net <= 0 or rt.netname[net].startswith("unconnected-"):
                continue
            n = int(num)
            if rt.netname[net] == "+3V3_SW":
                continue                      # hàng via này nằm trong đảo +1V0 của lớp nguồn
            if 1 <= n <= 32:
                vy = CY - (9.1 if n % 2 else 9.9)
            elif n == 92:
                vy = CY + 10.3
            else:
                continue
            rt.add_track(net, F, x, y, x, vy, 0.15)
            rt.add_via(net, x, vy, 0.4, 0.2)


def pre_stubs(rt, length=0.7, w=0.15):
    """Dành sẵn lối thoát cho từng chân của IC chân nhỏ: một đoạn thẳng ngắn từ pad ra ngoài (vuông góc hàng pad).
    Nhờ vậy đường của net đi trước không cắt ngang ngay trước mặt các chân bên cạnh."""
    n = 0
    rt.stubs = []
    routed = {t[0] for t in rt.tracks}
    for net, pads in rt.pads.items():
        if len(pads) < 2 or net in routed:
            continue
        for p in pads:
            if p["tht"] or rt.fpsize.get(p["ref"], 0) < 16:
                continue
            xs = [abs(x - p["x"]) for pts in p["polys"] for x, y in pts]
            ys = [abs(y - p["y"]) for pts in p["polys"] for x, y in pts]
            ex, ey = max(xs), max(ys)
            if max(ex, ey) > 1.2 or abs(ex - ey) < 0.05:
                continue                      # đế tản nhiệt / pad vuông: không có hướng thoát rõ ràng
            cx, cy = group_centroid(rt, p)
            if ex > ey:
                e = (1.0 if p["x"] > cx else -1.0, 0.0)
                l = ex + length
            else:
                e = (0.0, 1.0 if p["y"] > cy else -1.0)
                l = ey + length
            x2, y2 = p["x"] + e[0] * l, p["y"] + e[1] * l
            L = p["layers"][0]
            if rt.seg_free((net,), L, p["x"], p["y"], x2, y2, w / 2 + 0.13 + 0.02):
                rt.add_track(net, L, p["x"], p["y"], x2, y2, w)
                rt.stubs.append(rt.tracks[-1])
                # không cho via của net khác chắn ngay trước đầu lối thoát
                rt.stamp_seg(rt.novia, x2, y2, x2 + e[0] * 1.3, y2 + e[1] * 1.3, 0.38, True)
                n += 1
    return n


def plane_tree(rt, name):
    """Đích cho net mặt phẳng: chỉ các via / chân xuyên lỗ nằm TRONG vùng của net trên lớp nguồn (GND: mọi nơi)."""
    net = rt.netcode[name]
    zone = plane_masks(rt)[name]
    tree = [np.zeros((rt.ny, rt.nx), bool) for _ in range(3)]
    pts = [(v[1], v[2]) for v in rt.vias if v[0] == net] + [(p["x"], p["y"]) for p in rt.pads[net] if p["tht"]]
    for x, y in pts:
        if zone is None or zone[rc.cell(y), rc.cell(x)]:
            for k in range(3):
                rt.stamp_seg(tree[k], x, y, x, y, 0.1, True)
    return tree


def route_plane_net(rt, name, ws, via, clr=0.13):
    """Nối các pad của net mặt phẳng chưa tới được via hợp lệ nào."""
    net = rt.netcode[name]
    bad = []
    for p in plane_orphans(rt, net):
        goal = plane_tree(rt, name)
        ok = False
        for w in ws:
            for m in (4.0, 12.0, 45.0):
                try:
                    rt.connect(net, [(L, p["x"], p["y"]) for L in p["layers"]], goal, w, clr, via=via, margin=m,
                               maxexp=30000000)
                    ok = True
                    break
                except Fail:
                    continue
            if ok:
                break
        if not ok:
            bad.append(p)
    rt.last_failed = bad
    return not bad


# Net hay bị các net khác bịt lối (pad nằm giữa nhiều đường): đi trước.
PRIORITY = ("SPI_MOSI", "RTC_SDA", "RTC_SCL", "/Security/SRAM_SI", "/SW1/TMS", "/SW2/TMS", "/SW1/TEST1", "/SW2/TEST1",
            "/SW1/SMBCLK", "/SW2/SMBCLK", "/SW1/PWR_SAV", "/SW2/PWR_SAV", "+12V", "+3V3", "/Power/EN_5V",
            "/Power/RT_5V", "/Power/COMP_5V", "TPM_CS_N", "TPM_PIRQ_N", "PCIE_RST_N")


def route_one(rt, name, pats):
    net = rt.netcode[name]
    cls = netclass_of(name, pats)
    ws = net_width(name, cls)
    via = (0.6, 0.3, 0.13) if ws[0] >= 0.4 else (0.45, 0.2, 0.13)
    clr = 0.2 if cls == "PWR_HV" else 0.13
    if cls in ("PCIE_90R", "USB_90R", "MDI_100R", "USB_FS"):
        clr = 0.15
    t1 = time.time()
    if name in PLANE_W:
        ok = route_plane_net(rt, name, ws, via)
    else:
        lay = (0, 2) if cls == "PWR_HV" else (0, 1, 2)      # dòng lớn: chỉ lớp ngoài 1 oz
        ok = rt.route_net_strict(net, ws[0], clr, layers=lay, via=via, widths=ws)
    if time.time() - t1 > 8:
        print("   (%s: %.0fs)" % (name, time.time() - t1), flush=True)
    return ok, list(rt.last_failed)


def route_singles(rt, pats, skip=(), only=(), rounds=0):
    """Đi mọi net còn lại (net ngắn trước); net nào kẹt thì gỡ các net lân cận quanh pad bị kẹt rồi đi lại
    (rip-up & reroute). Trả về danh sách net chưa nối xong."""
    span = {}
    todo = []
    for net, pads in rt.pads.items():
        name = rt.netname[net]
        if len(pads) < 2:
            continue
        xs = [p["x"] for p in pads]
        ys = [p["y"] for p in pads]
        span[name] = (max(xs) - min(xs)) + (max(ys) - min(ys))
        if name in skip or (only and not any(fnmatch.fnmatchcase(name, o) for o in only)):
            continue
        todo.append(name)
    todo.sort(key=lambda n: (0 if n in PRIORITY else 1, span[n], n))
    failed = {}
    for name in todo:
        ok, fp = route_one(rt, name, pats)
        if not ok:
            failed[name] = fp
    print("   luot 1: %d net kẹt" % len(failed), sorted(failed)[:40], flush=True)
    planes = {rt.netcode[n] for n in PLANE_W}
    for rnd in range(rounds):
        if not failed:
            break
        nxt = {}
        for name in sorted(failed, key=lambda n: (span[n], n)):
            net = rt.netcode[name]
            victims = set()
            for p in failed[name]:
                victims |= rt.nets_near(p["x"], p["y"], 1.6 + 0.6 * rnd)
            victims = {v for v in victims if v != net and v not in rt.locked and v not in planes
                       and v in rt.netname and 2 <= len(rt.pads.get(v, [])) <= 6}
            for v in victims:
                rt.rip(v)
            rt.rip(net)
            ok, fp = route_one(rt, name, pats)
            if not ok:
                nxt[name] = fp
            for v in sorted(victims, key=lambda v: (span.get(rt.netname[v], 0), v)):
                vn = rt.netname[v]
                ok2, fp2 = route_one(rt, vn, pats)
                if not ok2:
                    nxt[vn] = fp2
                elif vn in nxt:
                    del nxt[vn]
        failed = nxt
        print("   luot gỡ-đi-lại %d: còn %d net kẹt" % (rnd + 1, len(failed)), sorted(failed)[:40], flush=True)
    return sorted(failed)


def plane_orphans(rt, net):
    """Pad của net mặt phẳng chưa có đường tới via / chân xuyên lỗ nào."""
    win, lab, find, groups = rt.components(net)
    x0, y0 = win[0], win[1]
    ok = set()
    zone = plane_masks(rt)[rt.netname[net]]
    thru = [(v[1], v[2]) for v in rt.vias if v[0] == net] + [(p["x"], p["y"]) for p in rt.pads[net] if p["tht"]]
    for x, y in thru:
        if zone is not None and not zone[rc.cell(y), rc.cell(x)]:
            continue
        for L in range(3):
            l = int(lab[L][rc.cell(y) - y0, rc.cell(x) - x0])
            if l:
                ok.add(find((L, l)))
    return [p for g, pl in groups.items() if g not in ok for p in pl]


def rescue(rt, pats):
    """Lượt cứu: các pad còn kẹt được nối bằng đường 0.12 mm, khe hở 0.10 mm, via Ø0.40/0.20 (vẫn trong năng lực JLC),
    và được phép đặt via trong dải sát hàng chân IC."""
    rt.novia[:] = False
    zm = plane_masks(rt)
    left = []
    via = (0.4, 0.2, 0.115)
    for name in PLANE_W:
        net = rt.netcode[name]
        for p in plane_orphans(rt, net):
            if rt.fanout_pad(net, p, zm[name], w=0.15, clr=0.115, via=via, margins=(2.0, 5.0, 9.0)):
                continue
            goal = plane_tree(rt, name)
            done = False
            for m in (4.0, 12.0, 45.0):
                try:
                    rt.connect(net, [(L, p["x"], p["y"]) for L in p["layers"]], goal, 0.12, 0.115, via=via, margin=m,
                               maxexp=30000000)
                    done = True
                    break
                except Fail:
                    continue
            if not done:
                left.append("%s %s.%s" % (name, p["ref"], p["num"]))
    for net, pads in sorted(rt.pads.items()):
        name = rt.netname[net]
        if len(pads) < 2 or name in PLANE_W:
            continue
        if not rt.route_net_strict(net, 0.12, 0.115, via=via):
            left += [(name, p) for p in rt.last_failed]
    # Gỡ-đi-lại có hoàn tác: gỡ các net nhỏ quanh net còn kẹt, đi net kẹt trước rồi đi lại các net vừa gỡ;
    # chỉ giữ kết quả nếu TẤT CẢ đều nối xong, nếu không thì khôi phục nguyên trạng.
    import copy
    planes = {rt.netcode[n] for n in PLANE_W}
    out = [x for x in left if isinstance(x, str)]
    stuck = []
    for x in left:
        if not isinstance(x, str) and x[0] not in stuck:
            stuck.append(x[0])
    for name in stuck:
        net = rt.netcode[name]
        solved = False
        for rad in (1.2, 2.0, 3.0):
            snap = (copy.deepcopy(rt.tracks), copy.deepcopy(rt.vias), [a_.copy() for a_ in rt.cu], rt.hole.copy())
            victims = set()
            for p in rt.pads[net]:
                victims |= rt.nets_near(p["x"], p["y"], rad)
            victims = {v for v in victims if v != net and v not in rt.locked and v not in planes
                       and v in rt.netname and 2 <= len(rt.pads.get(v, [])) <= 8}
            for v in victims:
                rt.rip(v)
            rt.rip(net)
            ok = rt.route_net_strict(net, 0.12, 0.115, via=via) or rt.route_net_strict(net, 0.1, 0.1, via=via)
            if ok:
                for v in sorted(victims, key=lambda v: len(rt.pads[v])):
                    if not (rt.route_net_strict(v, 0.12, 0.115, via=via) or rt.route_net_strict(v, 0.1, 0.1, via=via)):
                        ok = False
                        break
            if ok:
                solved = True
                break
            rt.tracks, rt.vias, rt.cu, rt.hole = snap[0], snap[1], snap[2], snap[3]
        if not solved:
            out.append(name)
    return out


def unconnected_report(rt):
    """Kiểm tra lại bằng raster: mỗi net phải là 1 khối liền (qua đường, via, pad; net mặt phẳng coi via là đã nối)."""
    from scipy import ndimage
    out = []
    planes = {rt.netcode[n] for n in PLANE_W}
    for net, pads in rt.pads.items():
        if len(pads) < 2:
            continue
        lab = []
        for L in range(3):
            lab.append(ndimage.label(rt.cu[L] == net)[0])
        # hợp nhất nhãn qua via / pad xuyên lỗ bằng union-find
        parent = {}

        def find(a):
            while parent.get(a, a) != a:
                a = parent[a]
            return a

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[a] = b
        thru = [(v[1], v[2]) for v in rt.vias if v[0] == net] + [(p["x"], p["y"]) for p in pads if p["tht"]]
        plane_node = ("plane",)
        for x, y in thru:
            ids = [(L, lab[L][rc.cell(y), rc.cell(x)]) for L in range(3)]
            for a in ids[1:]:
                union(ids[0], a)
            if net in planes:
                union(ids[0], plane_node)
        roots = set()
        for p in pads:
            L = p["layers"][0]
            roots.add(find((L, lab[L][rc.cell(p["y"]), rc.cell(p["x"])])))
        if len(roots) > 1:
            out.append((rt.netname[net], len(roots)))
    return out


def add_zone(board, layer, netcode, pts, name, prio, clearance=0.2, solid=True, minw=0.2):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(netcode)
    z.SetZoneName(name)
    z.SetAssignedPriority(prio)
    z.SetMinThickness(MM(minw))
    z.SetLocalClearance(MM(clearance))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(MM(0.2))
    z.SetThermalReliefSpokeWidth(MM(0.3))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(MM(OX + x), MM(OY + y))
    board.Add(z)
    return z


def rect_pts(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def build_zones(board, rt):
    full = (0.3, 0.3, W - 0.3, H - 0.3)
    gnd = rt.netcode["GND"]
    add_zone(board, pcbnew.In1_Cu, gnd, rect_pts(full), "GND_L2", 0)
    add_zone(board, pcbnew.In3_Cu, gnd, rect_pts(full), "GND_L4", 0)
    for i, r in enumerate(Z_3V3SW):
        add_zone(board, pcbnew.In4_Cu, rt.netcode["+3V3_SW"], rect_pts(r), "3V3SW_L5_%d" % i, 1)
    add_zone(board, pcbnew.In4_Cu, rt.netcode["+5V"], P_5V, "5V_L5", 2)
    add_zone(board, pcbnew.In4_Cu, rt.netcode["+1V0"], P_1V0, "1V0_L5", 3)
    for i, r in enumerate(N_3V3):
        add_zone(board, pcbnew.In4_Cu, rt.netcode["+3V3_SW"], rect_pts(r), "3V3SW_khe_%d" % i, 4)
    # đổ GND các lớp tín hiệu (nối pad bằng nan tản nhiệt để dễ hàn)
    for layer, nm in ((pcbnew.F_Cu, "GND_L1"), (pcbnew.In2_Cu, "GND_L3"), (pcbnew.B_Cu, "GND_L6")):
        add_zone(board, layer, gnd, rect_pts(full), nm, 0, clearance=0.25, solid=False, minw=0.25)


def trim_dangling(rt):
    """Cắt phần thừa của các đoạn 'lối thoát chân IC' (pre_stubs): giữ từ pad tới điểm nối xa nhất, bỏ phần còn lại."""
    n = 0
    for st in list(getattr(rt, "stubs", [])):
        t = next((q for q in rt.tracks if q is st), None)
        if t is None:
            continue
        net, L = t[0], t[1]
        b, a = (t[2], t[3]), (t[4], t[5])              # b = tâm pad, a = đầu ngoài
        ln = math.hypot(a[0] - b[0], a[1] - b[1])
        far = 0.0
        for o in rt.tracks:
            if o is t or o[0] != net or o[1] != L:
                continue
            for q in ((o[2], o[3]), (o[4], o[5])):
                if _pt_seg(q[0], q[1], t) <= t[6] / 2 + 0.03:
                    far = max(far, math.hypot(q[0] - b[0], q[1] - b[1]))
            # đường khác cắt ngang / chạm vào đoạn thoát (không có đầu mút nằm trên nó)
            for k in range(0, 41):
                px, py = b[0] + (a[0] - b[0]) * k / 40.0, b[1] + (a[1] - b[1]) * k / 40.0
                if _pt_seg(px, py, o) <= (o[6] + t[6]) / 2:
                    far = max(far, ln * k / 40.0)
        for v in rt.vias:
            if v[0] == net and _pt_seg(v[1], v[2], t) <= t[6] / 2 + 0.03:
                far = max(far, math.hypot(v[1] - b[0], v[2] - b[1]))
        if far >= ln - 0.02 or tuple(t) in getattr(rt, "fixed", ()):
            continue
        rt.tracks = [q for q in rt.tracks if q is not t]
        if far > 0.05:
            k = far / ln
            rt.tracks.append([net, L, b[0], b[1], b[0] + (a[0] - b[0]) * k, b[1] + (a[1] - b[1]) * k, t[6]])
        n += 1
    return n


def bridge(rt, net, pa, pb, w=0.12, clr=0.1, via=(0.4, 0.2, 0.1), rmax=1.6):
    """Nối 2 pad gần nhau ở hai mặt (hoặc cùng mặt) bằng 1 via: pad A -> via -> pad B, hai đoạn thẳng."""
    mx, my = (pa["x"] + pb["x"]) / 2, (pa["y"] + pb["y"]) / 2
    win = rt.window([(mx, my)], rmax + 1.0)
    x0, y0 = win[0], win[1]
    _, vb = rt.masks((net,), win, w / 2 + clr + rc.MARGIN, (), via)
    best = None
    r = w / 2 + clr + 0.02
    for k in range(0, int(rmax / G) + 1):
        for j in range(max(1, 8 * k)):
            ang = 2 * math.pi * j / max(1, 8 * k)
            x, y = mx + k * G * math.cos(ang), my + k * G * math.sin(ang)
            cx, cy = rc.cell(x) - x0, rc.cell(y) - y0
            if not (0 <= cy < vb.shape[0] and 0 <= cx < vb.shape[1]) or vb[cy, cx]:
                continue
            La, Lb = pa["layers"][0], pb["layers"][0]
            if rt.seg_free((net,), La, pa["x"], pa["y"], x, y, r) and rt.seg_free((net,), Lb, x, y, pb["x"], pb["y"], r):
                ln = math.hypot(pa["x"] - x, pa["y"] - y) + math.hypot(pb["x"] - x, pb["y"] - y)
                if best is None or ln < best[0]:
                    best = (ln, x, y, La, Lb)
        if best is not None and k * G > 0.3:
            break
    if best is None:
        return False
    _, x, y, La, Lb = best
    rt.add_track(net, La, pa["x"], pa["y"], x, y, w)
    rt.add_via(net, x, y, via[0], via[1])
    rt.add_track(net, Lb, x, y, pb["x"], pb["y"], w)
    return True


def final_fix(rt, pats):
    """Lượt cuối cho các net còn rời: nối cặp pad gần nhau bằng 1 via; còn lại gỡ-đi-lại bán kính lớn."""
    via = (0.4, 0.2, 0.1)
    planes = {rt.netcode[n] for n in PLANE_W}
    left = []
    for name, cnt in unconnected_report(rt):
        net = rt.netcode[name]
        for _ in range(cnt + 2):
            win, lab, find, groups = rt.components(net)
            if net in planes:
                orph = plane_orphans(rt, net)
                if not orph:
                    break
                zone = plane_masks(rt)[name]
                p = orph[0]
                if not rt.fanout_pad(net, p, zone, w=0.12, clr=0.1, via=via, margins=(2.0, 5.0, 9.0)):
                    left.append(name)
                    break
                continue
            if len(groups) <= 1:
                break
            gl = list(groups.values())
            best = None
            for i in range(len(gl)):
                for j in range(i + 1, len(gl)):
                    for a in gl[i]:
                        for b in gl[j]:
                            dd = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                            if best is None or dd < best[0]:
                                best = (dd, a, b)
            if best[0] < 3.5 and (bridge(rt, net, best[1], best[2]) or
                                  bridge(rt, net, best[1], best[2], w=0.1, rmax=2.6)):
                continue
            if rt.route_net_strict(net, 0.1, 0.1, via=via):
                break
            left.append(name)
            break
    # gỡ-đi-lại bán kính lớn (có hoàn tác) cho phần còn lại
    import copy
    out = []
    for name in left:
        net = rt.netcode[name]
        ok = False
        for rad in (3.0, 5.0):
            snap = (copy.deepcopy(rt.tracks), copy.deepcopy(rt.vias), [a_.copy() for a_ in rt.cu], rt.hole.copy())
            victims = set()
            for p in rt.pads[net]:
                victims |= rt.nets_near(p["x"], p["y"], rad)
            victims = {v for v in victims if v != net and v not in rt.locked and v not in planes
                       and v in rt.netname and 2 <= len(rt.pads.get(v, [])) <= 8}
            for v in victims:
                rt.rip(v)
            rt.rip(net)
            ok = rt.route_net_strict(net, 0.1, 0.1, via=via) and all(
                rt.route_net_strict(v, 0.12, 0.115, via=via) or rt.route_net_strict(v, 0.1, 0.1, via=via)
                for v in sorted(victims, key=lambda v: len(rt.pads[v])))
            if ok:
                break
            rt.tracks, rt.vias, rt.cu, rt.hole = snap
        if not ok:
            out.append(name)
    return out


def prune_dead(rt):
    """Xoá đoạn cụt (một đầu không nối gì) và via cụt (≤1 đường, không nằm trong pad) của net không phải mặt phẳng."""
    planes = {rt.netcode[n] for n in PLANE_W}
    removed = 0
    while True:
        ch = 0
        fx = getattr(rt, "fixed", ())
        for t in list(rt.tracks):
            net = t[0]
            if tuple(t) in fx:
                continue
            for a, b in (((t[2], t[3]), (t[4], t[5])), ((t[4], t[5]), (t[2], t[3]))):
                if _anchored(rt, net, t, a):
                    continue
                # đầu a tự do: giữ phần từ b tới điểm nối xa nhất trên đoạn
                ln = math.hypot(a[0] - b[0], a[1] - b[1])
                far = 0.0
                for o in rt.tracks:
                    if o is t or o[0] != net or o[1] != t[1]:
                        continue
                    for q in ((o[2], o[3]), (o[4], o[5])):
                        if _pt_seg(q[0], q[1], t) <= t[6] / 2 + 0.02:
                            far = max(far, math.hypot(q[0] - b[0], q[1] - b[1]))
                for v in rt.vias:
                    if v[0] == net and _pt_seg(v[1], v[2], t) <= t[6] / 2 + 0.02:
                        far = max(far, math.hypot(v[1] - b[0], v[2] - b[1]))
                if far >= ln - 0.02:
                    continue                    # điểm nối nằm ngay đầu a: không cắt (tránh lặp vô hạn)
                rt.tracks = [q for q in rt.tracks if q is not t]
                if far > 0.03:
                    k = far / ln
                    rt.tracks.append([net, t[1], b[0], b[1], b[0] + (a[0] - b[0]) * k, b[1] + (a[1] - b[1]) * k, t[6]])
                ch += 1
                break
        for v in list(rt.vias):
            net = v[0]
            if net in planes:
                continue
            n = sum(1 for t in rt.tracks if t[0] == net and _pt_seg(v[1], v[2], t) <= t[6] / 2 + v[3] / 2 + 0.05)
            inpad = any(_near_poly(p, v[1], v[2], v[3] / 2 + 0.02) for p in rt.pads.get(net, []))
            if n <= 1 and not inpad:
                rt.vias = [q for q in rt.vias if q is not v]
                ch += 1
        removed += ch
        if not ch:
            return removed


def _near_poly(p, x, y, tol=0.1):
    if _in_polys(p, x, y):
        return True
    for pts in p["polys"]:
        for i in range(len(pts)):
            q = [0, 0, pts[i][0], pts[i][1], pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]]
            if _pt_seg(x, y, q) <= tol:
                return True
    return False


def _anchored(rt, net, t, a):
    # dung sai 0.1 mm: điểm cuối do A* đặt theo lưới 0.05 mm nên có thể nằm sát mép pad / đường
    if any(_near_poly(p, a[0], a[1]) for p in rt.pads.get(net, []) if t[1] in p["layers"]):
        return True
    if any(v[0] == net and math.hypot(v[1] - a[0], v[2] - a[1]) <= v[3] / 2 + 0.05 for v in rt.vias):
        return True
    for o in rt.tracks:
        if o is not t and o[0] == net and o[1] == t[1] and _pt_seg(a[0], a[1], o) <= o[6] / 2 + 0.06:
            return True
    return False


def _pt_seg(px, py, t):
    x1, y1, x2, y2 = t[2], t[3], t[4], t[5]
    vx, vy = x2 - x1, y2 - y1
    l2 = vx * vx + vy * vy
    k = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / l2)) if l2 else 0.0
    return math.hypot(px - x1 - k * vx, py - y1 - k * vy)


def _in_polys(p, x, y):
    for pts in p["polys"]:
        inside = False
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
        if inside:
            return True
    return False


def save(board, rt, path=PCB):
    assert len(board.GetTracks()) == 0, "route.py phai chay tren bo vua sinh tu board.py"
    for net, L, x1, y1, x2, y2, w in rt.tracks:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(MM(OX + x1), MM(OY + y1)))
        t.SetEnd(pcbnew.VECTOR2I(MM(OX + x2), MM(OY + y2)))
        t.SetWidth(MM(w))
        t.SetLayer(KL[L])
        t.SetNet(board.FindNet(net))
        board.Add(t)
    for net, x, y, dia, drill in rt.vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(MM(OX + x), MM(OY + y)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        try:
            v.SetWidth(pcbnew.F_Cu, MM(dia))
        except TypeError:
            v.SetWidth(MM(dia))
        v.SetDrill(MM(drill))
        v.SetNet(board.FindNet(net))
        board.Add(v)
    build_zones(board, rt)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)


CACHE = PCB + ".cache.pkl"
SCR = "/tmp/claude-1000/-home-gradien-Workspace-KiCAD/bfa28602-f054-4d22-a6bf-4b5e802d89c0/scratchpad/"


def main():
    """route.py [--cache]  : --cache = dùng lại kết quả cặp vi sai + via mặt phẳng đã lưu (chỉ để gỡ lỗi nhanh)."""
    t0 = time.time()
    import subprocess
    if PLACED:
        import shutil
        shutil.copy(PLACED, PCB)
    else:
        subprocess.run([sys.executable, os.path.join(HERE, "board.py")], check=True, capture_output=True)
    board = pcbnew.LoadBoard(PCB)
    pro = json.load(open(os.path.join(HW, "cm4-gateway.kicad_pro")))
    pats = pro["net_settings"]["netclass_patterns"]
    if "--cache" in sys.argv and os.path.exists(CACHE):
        rt = pickle.load(open(CACHE, "rb"))
        print("dung cache", flush=True)
    else:
        rt = load(board)
        print("nap bo: %.1fs, %d net co pad" % (time.time() - t0, len(rt.pads)))
        rt.pairs = []
        prepare_fanout(rt)
        n0 = len(rt.tracks)
        pre_power(rt)
        rt.fixed = {tuple(t) for t in rt.tracks[n0:]}
        pre_escape(rt)
        plan_pcie(rt)
        # bus SPI của vùng bảo mật đi TRƯỚC các cặp MDI của WAN (các cặp này chạy xuyên vùng bảo mật và sẽ né theo)
        if "B" in VARIANT:
            route_singles(rt, pats, only=("SPI_*", "SRAM_CS_N", "TPM_*", "/Security/*", "TAMPER_OPEN", "RTC_*",
                                          "nEXTRST"))
        elif "S" in VARIANT:
            route_singles(rt, pats, only=("SPI_*", "SRAM_CS_N", "TPM_CS_N", "/Security/SRAM_*"))
        plan_mdi(rt)
        plan_usb(rt)
        print("cap vi sai: %.0fs" % (time.time() - t0), flush=True)
        n = sum(ep_vias(rt, r, 4, 4, 1.2) for r in ("U401", "U501")) + \
            sum(ep_vias(rt, "U%d01" % k, 2, 2, 1.3) for k in (6, 7, 8, 9))
        print("via tan nhiet:", n, flush=True)
        rt.locked = {t[0] for t in rt.tracks} | {v[0] for v in rt.vias}      # cặp vi sai + lối thoát đặt tay: không gỡ
        rt.hole_base = rt.hole.copy()
        for v in rt.vias:
            pass
        print("loi thoat chan IC:", pre_stubs(rt), flush=True)
        rt._dsmd = None
        pickle.dump(rt, open(CACHE, "wb"), protocol=4)
    if "--stop-fanout" not in sys.argv:
        only = [a[7:] for a in sys.argv if a.startswith("--only=")]
        # 1) tín hiệu và rail cục bộ trước (để chân IC còn lối thoát), 2) via xuống mặt phẳng, 3) phần còn lại của net mặt phẳng
        if not only:
            print("fanout mat phang (xong, loi):", fanout_planes(rt), "%.0fs" % (time.time() - t0), flush=True)
        bad = route_singles(rt, pats, only=only, skip=tuple(PLANE_W))
        print("net tin hieu: %d chua xong  %.0fs" % (len(bad), time.time() - t0), flush=True)
        if not only:
            bad2 = route_singles(rt, pats, only=tuple(PLANE_W))
            print("net mat phang: %d chua xong  %.0fs" % (len(bad2), time.time() - t0), flush=True)
    if "--stop-fanout" not in sys.argv and not [a for a in sys.argv if a.startswith("--only=")]:
        left = rescue(rt, pats)
        print("luot cuu: con %d pad" % len(left), left, "%.0fs" % (time.time() - t0), flush=True)
    print("cat dau thua:", trim_dangling(rt), "| don via/duong cut:", prune_dead(rt), flush=True)
    if "--stop-fanout" not in sys.argv and not [a for a in sys.argv if a.startswith("--only=")]:
        print("luot cuoi: con", final_fix(rt, pats), flush=True)
        print("don lan 2:", prune_dead(rt), flush=True)
    rep = unconnected_report(rt)
    print("kiem tra raster: %d net chua lien" % len(rep), rep[:60], flush=True)
    save(board, rt)
    for l in rt.log:
        if not l.startswith("  ("):
            print(l)
    print("tong %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
