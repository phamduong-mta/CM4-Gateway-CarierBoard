#!/usr/bin/env python3
"""Bước hoàn thiện sau route.py: đọc danh sách "chưa nối" do DRC của KiCad báo, nối từng cặp điểm còn rời bằng đường
0.10 mm / via Ø0.40 (trong năng lực JLC 6 lớp), gỡ-đi-lại các net nhỏ lân cận nếu cần (có hoàn tác).
Lặp tới khi KiCad báo 0 chưa nối (tối đa 4 vòng). Chạy:  .venv/bin/python scripts/gen/finish.py"""
import copy
import fnmatch
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route as R
import rt_core as rc
from rt_core import Fail

T = pcbnew.ToMM
LAYER = {"F.Cu": 0, "In2.Cu": 1, "B.Cu": 2}
VIA = (0.4, 0.2, 0.1)


def load_routed(board, routed_path):
    rt = R.load(board)
    rt.minw = {rt.netcode[n]: w for n, w in list(R.MINW.items()) + list(R.MINW_LOCAL.items()) if n in rt.netcode}
    rb = pcbnew.LoadBoard(routed_path)
    for t in rb.GetTracks():
        n = board.FindNet(t.GetNetname()).GetNetCode()
        if t.GetClass() == "PCB_VIA":
            rt.add_via(n, T(t.GetPosition().x) - R.OX, T(t.GetPosition().y) - R.OY, T(t.GetWidth(pcbnew.F_Cu)),
                       T(t.GetDrill()))
        else:
            L = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}[t.GetLayer()]
            rt.add_track(n, L, T(t.GetStart().x) - R.OX, T(t.GetStart().y) - R.OY, T(t.GetEnd().x) - R.OX,
                         T(t.GetEnd().y) - R.OY, T(t.GetWidth()))
    mw = {rt.netcode[n] for n in R.MINW if n in rt.netcode}
    rt.fixed = {tuple(t) for t in rt.tracks if t[0] in mw}       # không gỡ đồng nguồn dòng lớn
    pats = json.load(open(os.path.join(R.HW, "cm4-gateway.kicad_pro")))["net_settings"]["netclass_patterns"]
    rt.locked = {n for n, nm in rt.netname.items()
                 if R.netclass_of(nm, pats) in ("PCIE_90R", "USB_90R", "MDI_100R")}
    rt.hole_base = np.zeros_like(rt.hole)
    for net, pads in rt.pads.items():
        pass
    return rt


def drc_unconnected(pcb):
    out = pcb + ".drc1.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, pcb], capture_output=True)
    d = json.load(open(out))
    res = []
    for v in d.get("unconnected_items", []):
        pts = []
        for it in v["items"]:
            desc = it["description"]
            m = re.search(r"\[(.*?)\]", desc)
            lay = re.search(r" on (\S+\.Cu)", desc)
            kind = "zone" if desc.startswith("Zone") else ("via" if desc.startswith("Via") else "x")
            pts.append(dict(net=m.group(1) if m else None, x=it["pos"]["x"] - R.OX, y=it["pos"]["y"] - R.OY,
                            L=LAYER.get(lay.group(1)) if lay else None, kind=kind))
        res.append(pts)
    return res


def disc(rt, x, y, layers, r=0.12):
    g = [None, None, None]
    for L in layers:
        g[L] = np.zeros((rt.ny, rt.nx), bool)
        rt.stamp_seg(g[L], x, y, x, y, r, True)
    return g


def link(rt, net, a, b):
    """Nối điểm a tới điểm b (dict x, y, L) bằng A* với luật nhỏ nhất."""
    la = (0, 1, 2) if a["L"] is None or a["kind"] == "via" else (a["L"],)
    lb = (0, 1, 2) if b["L"] is None or b["kind"] == "via" else (b["L"],)
    goal = disc(rt, b["x"], b["y"], lb)
    dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    for w in (0.12, 0.1):
        for m in (2.5, 6.0, dist / 2 + 4.0):
            try:
                rt.connect(net, [(L, a["x"], a["y"]) for L in la], goal, w, 0.1, via=VIA, margin=m,
                           maxexp=40000000, extra_pts=[(b["x"], b["y"])])
                return True
            except Fail:
                continue
    return False


def plane_link(rt, net, a):
    """Điểm a thuộc net mặt phẳng nhưng bị cô lập: thêm via xuống mặt phẳng ngay cạnh."""
    name = rt.netname[net]
    zone = R.plane_masks(rt)[name]
    p = dict(x=a["x"], y=a["y"], layers=(a["L"] if a["L"] is not None else 0,),
             polys=[[(a["x"] - 0.05, a["y"] - 0.05), (a["x"] + 0.05, a["y"] - 0.05), (a["x"] + 0.05, a["y"] + 0.05),
                     (a["x"] - 0.05, a["y"] + 0.05)]])
    return rt.fanout_pad(net, p, zone, w=0.12, clr=0.1, via=VIA, margins=(2.0, 5.0, 9.0)) > 0


def fix_pair(rt, pair):
    a, b = pair
    net = rt.netcode.get(a["net"] or b["net"])
    if net is None:
        return False
    if a["kind"] == "zone":
        a, b = b, a
    zone = b["kind"] == "zone"
    if zone and plane_link(rt, net, a):
        return True
    if not zone and rt.netname[net] in R.PLANE_W:
        # hai pad của net mặt phẳng: pad nào chưa có via thì thêm via cho pad đó
        for q in (b, a):
            if q["kind"] == "x" and plane_link(rt, net, q):
                return True
    if (zone or rt.netname[net] in R.PLANE_W) and a["L"] is not None:
        # pad bị kẹt: nối sang pad cùng net gần nhất trên cùng lớp bằng đường gãy ngang–chéo 45°–ngang
        # (vd. chân GND 42 sang chân GND 43 ở cột đối diện của đầu nối CM4)
        r = 0.06 + 0.1 + 0.03
        for p in sorted(rt.pads[net], key=lambda p: math.hypot(p["x"] - a["x"], p["y"] - a["y"])):
            d = math.hypot(p["x"] - a["x"], p["y"] - a["y"])
            if not (0.05 < d < 4.0 and a["L"] in p["layers"]):
                continue
            dy = p["y"] - a["y"]
            sx = 1 if p["x"] > a["x"] else -1
            span = abs(p["x"] - a["x"]) - abs(dy)
            for k in range(0, 41):
                x1 = a["x"] + sx * span * k / 40.0
                pts = [(a["x"], a["y"]), (x1, a["y"]), (x1 + sx * abs(dy), p["y"]), (p["x"], p["y"])]
                if span >= 0 and all(rt.seg_free((net,), a["L"], *pts[i], *pts[i + 1], r) for i in range(3)
                                     if math.hypot(pts[i][0] - pts[i + 1][0], pts[i][1] - pts[i + 1][1]) > 1e-6):
                    for i in range(3):
                        rt.add_track(net, a["L"], *pts[i], *pts[i + 1], 0.12)
                    return True
    if not zone and (link(rt, net, a, b) or link(rt, net, b, a)):
        return True
    planes = {rt.netcode[n] for n in R.PLANE_W}
    if not zone and wan_detour(rt, net, a, b):
        return True
    for rad in (2.0, 3.5, 5.5):
        snap = (copy.deepcopy(rt.tracks), copy.deepcopy(rt.vias), [x.copy() for x in rt.cu], rt.hole.copy())
        victims = (rt.nets_near(a["x"], a["y"], rad) | (set() if zone else rt.nets_near(b["x"], b["y"], rad))) - {net}
        victims = {v for v in victims if v not in rt.locked and v not in planes and v in rt.netname
                   and 2 <= len(rt.pads.get(v, [])) <= (8 if rad < 3 else 40)}
        for v in victims:
            rt.rip(v)
        ok = (plane_link(rt, net, a) if zone else link(rt, net, a, b)) and all(
            rt.route_net_strict(v, 0.12, 0.115, via=VIA) or rt.route_net_strict(v, 0.1, 0.1, via=VIA)
            for v in sorted(victims, key=lambda v: len(rt.pads[v])))
        if ok:
            return True
        rt.tracks, rt.vias, rt.cu, rt.hole = snap
    return False


def wan_detour(rt, net, a, b):
    """Cặp MDI của WAN chạy qua vùng bảo mật: gỡ cả 4 cặp + net nhỏ lân cận, nối net kẹt trước, rồi đi lại các net
    vừa gỡ và 4 cặp WAN theo đúng kế hoạch cũ (có hoàn tác nếu bất kỳ bước nào hỏng)."""
    wan = [rt.netcode["WAN_MDI%d%s" % (k, s_)] for k in range(4) for s_ in ("_P", "_N")]
    planes = {rt.netcode[n] for n in R.PLANE_W}
    snap = (copy.deepcopy(rt.tracks), copy.deepcopy(rt.vias), [x.copy() for x in rt.cu], rt.hole.copy())
    victims = (rt.nets_near(a["x"], a["y"], 2.5) | rt.nets_near(b["x"], b["y"], 2.5)) - {net} - set(wan)
    victims = {v for v in victims if v not in rt.locked and v not in planes and v in rt.netname
               and 2 <= len(rt.pads.get(v, [])) <= 40}
    for v in list(victims) + wan:
        rt.rip(v)
    rt.pairs = []
    ok = link(rt, net, a, b)
    if ok:
        for base, nodes in R.WAN_PLAN():
            if R.route_pair(rt, base, nodes, verbose=False, avoid_rects=R.WAN_AVOID, **R.MDI) is None:
                ok = False
                break
    if ok:
        ok = all(rt.route_net_strict(v, 0.12, 0.115, via=VIA) or rt.route_net_strict(v, 0.1, 0.1, via=VIA)
                 for v in sorted(victims, key=lambda v: len(rt.pads[v])))
    if not ok:
        rt.tracks, rt.vias, rt.cu, rt.hole = snap
    return ok


def drc_bad_nets(pcb):
    """Net của đường/via đang vi phạm khe hở / lỗ (không tính pad)."""
    out = pcb + ".drc2.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, pcb], capture_output=True)
    d = json.load(open(out))
    nets = set()
    for v in d["violations"]:
        if v["severity"] != "error":
            continue
        for it in v["items"]:
            if it["description"].startswith(("Track", "Via")):
                m = re.search(r"\[(.*?)\]", it["description"])
                if m:
                    nets.add(m.group(1))
    return nets


def score(pcb):
    return len(drc_unconnected(pcb)) + 2 * len(drc_bad_nets(pcb))


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    tag = os.environ.get("CM4GW_VARIANT", "")
    work = os.path.join(tempfile.gettempdir(), "cm4gw_routed%s.kicad_pcb" % tag)
    best = os.path.join(tempfile.gettempdir(), "cm4gw_best%s.kicad_pcb" % tag)
    shutil.copy(R.PCB, best)
    best_score = score(R.PCB)
    for it in range(rounds):
        pairs = drc_unconnected(R.PCB)
        nbad = drc_bad_nets(R.PCB)
        print("vong %d: chua noi %d, net vi pham %s (diem %d)" % (it + 1, len(pairs), sorted(nbad), best_score),
              flush=True)
        if not pairs and not nbad:
            break
        shutil.copy(R.PCB, work)
        if R.PLACED:
            shutil.copy(R.PLACED, R.PCB)
        else:
            subprocess.run([sys.executable, os.path.join(R.HERE, "board.py")], check=True, capture_output=True)
        board = pcbnew.LoadBoard(R.PCB)
        rt = load_routed(board, work)
        bad = []
        for nm in nbad:
            net = rt.netcode.get(nm)
            if net is None or net in rt.locked or nm in R.PLANE_W or net in rt.minw:
                continue
            snap = (copy.deepcopy(rt.tracks), copy.deepcopy(rt.vias), [x.copy() for x in rt.cu], rt.hole.copy())
            rt.rip(net)
            if not (rt.route_net_strict(net, 0.12, 0.115, via=VIA) or rt.route_net_strict(net, 0.1, 0.1, via=VIA)):
                rt.tracks, rt.vias, rt.cu, rt.hole = snap
                bad.append((nm, "di lai sau loi DRC"))
        for pr in pairs:
            if not fix_pair(rt, pr):
                bad.append((pr[0]["net"], round(pr[0]["x"], 1), round(pr[0]["y"], 1)))
        print("   khong sua duoc:", bad, flush=True)
        R.prune_dead(rt)
        R.save(board, rt)
        sc = score(R.PCB)
        if sc < best_score:
            best_score = sc
            shutil.copy(R.PCB, best)
        else:
            shutil.copy(best, R.PCB)            # không tốt hơn: giữ bản tốt nhất
    print("ket qua (diem = chua noi + 2 x net vi pham):", best_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
