"""Hoàn thiện rev B trên bo đã đi dây (chạy sau patch_rev_a.py). Không đổi linh kiện / nối mạch.

1) Dọn đoạn dây & via treo (dựa trên DRC của KiCad, hoàn tác nếu làm hở mạch).
2) Lụa: cắt nét lụa của footprint đè lên pad / quá sát mép bo; dời (hoặc thu nhỏ, cuối cùng ẩn) chữ
   Reference / chữ trên bo đang đè lên pad, lụa khác hoặc mép bo.
3) Nhãn vị trí cho công tắc gạt BOOT; revision B.

Dùng: python3 scripts/gen/polish_rev_b.py hardware/cm4-gateway.kicad_pcb
"""
import json, math, os, shutil, subprocess, sys, tempfile
import pcbnew

PCB = sys.argv[1]
M = lambda v: int(round(v * 1e6))
mm = lambda v: v / 1e6
REV, DATE = "B", "2026-11-18"
CLR = 0.15          # khe hở lụa – pad / lụa – lụa
EDGE = 0.35         # lụa – mép bo


def drc(path):
    out = path + ".drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--refill-zones", "--format", "json", "-o", out, path],
                   capture_output=True)
    d = json.load(open(out))
    os.unlink(out)
    return d


def refill_save(b, path):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)


# ---------------------------------------------------------------- 1) dây / via treo
def _score(d):
    return (len(d["unconnected_items"]), sum(1 for q in d["violations"] if q["severity"] == "error"))


def _find(alltr, it0):
    x, y = it0["pos"]["x"], it0["pos"]["y"]
    net = it0["description"].split("[", 1)[1].split("]", 1)[0]
    isvia = it0["description"].startswith("Via")
    out = []
    for i, t in enumerate(alltr):
        if t.GetNetname() != net or (t.Type() == pcbnew.PCB_VIA_T) != isvia:
            continue
        s, e = t.GetStart(), t.GetEnd()
        pts = [(s.x, s.y), (e.x, e.y), ((s.x + e.x) / 2, (s.y + e.y) / 2)]
        if any(abs(mm(px) - x) < 0.006 and abs(mm(py) - y) < 0.006 for px, py in pts):
            out.append(i)
    return out


def dangling_pass(path):
    """Xóa từng đoạn/via treo; nếu xóa via làm hở mạch thì thay via bằng đoạn nối trên lớp còn lại."""
    tmp = path.replace(".kicad_pcb", "_try.kicad_pcb")
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copy(path.replace(".kicad_pcb", ext), tmp.replace(".kicad_pcb", ext))
    d = drc(path)
    base = _score(d)
    skip = set()
    while True:
        dang = [v["items"][0] for v in d["violations"] if v["type"] in ("track_dangling", "via_dangling")]
        dang = [i for i in dang if (i["description"], i["pos"]["x"], i["pos"]["y"]) not in skip]
        if not dang:
            break
        it0 = dang[0]
        key = (it0["description"], it0["pos"]["x"], it0["pos"]["y"])
        ok = False
        b0 = pcbnew.LoadBoard(path)
        cands = _find(list(b0.GetTracks()), it0)
        del b0
        trials = [("xoa", i) for i in cands] + [("cau", i) for i in cands]
        for mode, idx in trials:
            b = pcbnew.LoadBoard(path)
            alltr = list(b.GetTracks())
            t = alltr[idx]
            if mode == "cau":
                if t.Type() != pcbnew.PCB_VIA_T:
                    continue
                c = t.GetPosition(); r = t.GetWidth(pcbnew.F_Cu) // 2
                for o in alltr:
                    if o is t or o.Type() == pcbnew.PCB_VIA_T or o.GetNetname() != t.GetNetname():
                        continue
                    for q in (o.GetStart(), o.GetEnd()):
                        if 0 < math.hypot(q.x - c.x, q.y - c.y) <= r:
                            n = pcbnew.PCB_TRACK(b); n.SetStart(c); n.SetEnd(pcbnew.VECTOR2I(q.x, q.y))
                            n.SetWidth(o.GetWidth()); n.SetLayer(o.GetLayer()); n.SetNet(o.GetNet()); b.Add(n)
            b.Delete(t)
            refill_save(b, tmp)
            d2 = drc(tmp)
            if _score(d2) <= base:
                os.replace(tmp, path); d = d2; ok = True
                print("treo: %s %s" % (mode, key[0][:40]))
                break
        if not ok:
            skip.add(key); print("treo: giu %s" % key[0][:40])
    for ext in (".kicad_pro", ".kicad_dru"):
        os.unlink(tmp.replace(".kicad_pcb", ext))
    if os.path.exists(tmp):
        os.unlink(tmp)


# ---------------------------------------------------------------- 2) lụa
def box(bb, m=0.0):
    return (mm(bb.GetLeft()) - m, mm(bb.GetTop()) - m, mm(bb.GetRight()) + m, mm(bb.GetBottom()) + m)


def hit(a, c):
    return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]


def polish_silk(b):
    eb = box(b.GetBoardEdgesBoundingBox())
    inner = (eb[0] + EDGE, eb[1] + EDGE, eb[2] - EDGE, eb[3] - EDGE)
    sides = {pcbnew.F_SilkS: pcbnew.F_Cu, pcbnew.B_SilkS: pcbnew.B_Cu}
    pads = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            for sl, cu in sides.items():
                if p.IsOnLayer(cu):
                    pads[sl].append(box(p.GetBoundingBox(), CLR))
    # vias không phủ mask? (via mặc định tented) -> bỏ qua

    def free_pt(sl, x, y, w):
        if not (inner[0] <= x <= inner[2] and inner[1] <= y <= inner[3]):
            return False
        r = (x - w / 2, y - w / 2, x + w / 2, y + w / 2)
        return not any(hit(r, pb) for pb in pads[sl])

    # 2a) nét lụa >= 0.15 mm, chữ nét >= 0.15 mm (năng lực JLC), rồi cắt nét lụa footprint
    W = M(0.15)
    for fp in b.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetLayer() in sides and g.GetClass() == "PCB_SHAPE" and g.GetWidth() < W:
                g.SetWidth(W)
        for t in (fp.Reference(), fp.Value()):
            if t.GetLayer() in sides and t.GetTextThickness() < W:
                t.SetTextThickness(W)
    for d in b.GetDrawings():
        if d.GetLayer() in sides:
            if d.GetClass() == "PCB_TEXT" and d.GetTextThickness() < W:
                d.SetTextThickness(W)
            elif d.GetClass() == "PCB_SHAPE" and d.GetWidth() < W:
                d.SetWidth(W)
    cut = 0
    work = [(fp, list(fp.GraphicalItems())) for fp in b.GetFootprints()]
    for fp, items in work:
        for g in items:
            sl = g.GetLayer()
            if sl not in sides or g.GetClass() != "PCB_SHAPE" or g.GetShape() != pcbnew.SHAPE_T_SEGMENT:
                continue
            s, e, w = g.GetStart(), g.GetEnd(), mm(g.GetWidth())
            x1, y1, x2, y2 = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
            L = math.hypot(x2 - x1, y2 - y1)
            n = max(2, int(L / 0.05))
            ok = [free_pt(sl, x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n, w) for i in range(n + 1)]
            if all(ok):
                continue
            runs, st = [], None
            for i, f in enumerate(ok + [False]):
                if f and st is None:
                    st = i
                elif not f and st is not None:
                    if i - 1 - st >= max(2, int(0.25 / (L / n))):
                        runs.append((st, i - 1))
                    st = None
            for a, c in runs:
                ng = pcbnew.PCB_SHAPE(fp)
                ng.SetShape(pcbnew.SHAPE_T_SEGMENT); ng.SetLayer(sl); ng.SetWidth(g.GetWidth())
                ng.SetStart(pcbnew.VECTOR2I(M(x1 + (x2 - x1) * a / n), M(y1 + (y2 - y1) * a / n)))
                ng.SetEnd(pcbnew.VECTOR2I(M(x1 + (x2 - x1) * c / n), M(y1 + (y2 - y1) * c / n)))
                fp.Add(ng)
            fp.Delete(g); cut += 1
    print("lua: cat %d net" % cut)

    # 2b) chữ: Reference + chữ trên bo
    def shapes_of(sl, skip=None):
        out = []
        for fp in b.GetFootprints():
            for g in fp.GraphicalItems():
                if g is not skip and g.GetLayer() == sl and g.GetClass() == "PCB_SHAPE":
                    out.append(box(g.GetBoundingBox(), CLR))
        for d in b.GetDrawings():
            if d is not skip and d.GetLayer() == sl and d.GetClass() == "PCB_SHAPE":
                out.append(box(d.GetBoundingBox(), CLR))
        return out

    texts = []
    for fp in b.GetFootprints():
        r = fp.Reference()
        if r.IsVisible() and r.GetLayer() in sides:
            texts.append((r, fp))
    for d in b.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() in sides:
            texts.append((d, None))
    fixed = moved = hidden = 0
    placed = {sl: [] for sl in sides}
    bad = []
    for t, fp in texts:
        sl = t.GetLayer()
        bb = box(t.GetBoundingBox())
        others = shapes_of(sl) + pads[sl]
        if fp is not None:
            others += [box(o.GetBoundingBox(), CLR) for o, f2 in texts if o is not t and o.GetLayer() == sl]
        else:
            others += [box(o.GetBoundingBox(), CLR) for o, f2 in texts if o is not t and o.GetLayer() == sl]
        inside = bb[0] >= inner[0] and bb[1] >= inner[1] and bb[2] <= inner[2] and bb[3] <= inner[3]
        if inside and not any(hit(bb, o) for o in others):
            placed[sl].append(bb)
            continue
        bad.append((t, fp))
    for t, fp in bad:
        sl = t.GetLayer()
        p0 = t.GetPosition()
        h0 = t.GetTextHeight()
        ok = False
        if fp is not None:
            fb = box(fp.GetBoundingBox(False, False))
            cx, cy = (fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2
            cand = []
            for k in range(0, 12):
                dd = 0.2 * k
                cand += [(cx, fb[1] - 0.6 - dd), (cx, fb[3] + 0.6 + dd), (fb[0] - 1.2 - dd, cy), (fb[2] + 1.2 + dd, cy),
                         (fb[0] - 0.8 - dd, fb[1] - 0.6), (fb[2] + 0.8 + dd, fb[1] - 0.6),
                         (fb[0] - 0.8 - dd, fb[3] + 0.6), (fb[2] + 0.8 + dd, fb[3] + 0.6)]
        else:
            x0, y0 = mm(p0.x), mm(p0.y)
            cand = [(x0 + dx * 0.25, y0 + dy * 0.25) for r in range(0, 40) for dx in range(-r, r + 1)
                    for dy in (-r, r) if abs(dx) <= r] + \
                   [(x0 + dx * 0.25, y0 + dy * 0.25) for r in range(0, 40) for dy in range(-r + 1, r) for dx in (-r, r)]
            cand.sort(key=lambda c: math.hypot(c[0] - x0, c[1] - y0))
        others = shapes_of(sl) + pads[sl] + [box(o.GetBoundingBox(), CLR) for o, _ in texts
                                             if o is not t and o.GetLayer() == sl and o.IsVisible()]
        for scale in (1.0, 0.9, 0.8):
            hgt = M(max(0.8, mm(h0) * scale))
            t.SetTextSize(pcbnew.VECTOR2I(hgt, hgt)); t.SetTextThickness(M(0.15))
            for x, y in cand:
                t.SetPosition(pcbnew.VECTOR2I(M(x), M(y)))
                bb = box(t.GetBoundingBox())
                if bb[0] >= inner[0] and bb[1] >= inner[1] and bb[2] <= inner[2] and bb[3] <= inner[3] \
                        and not any(hit(bb, o) for o in others):
                    ok = True; break
            if ok:
                break
        if ok:
            moved += 1
        else:
            t.SetPosition(p0); t.SetTextSize(pcbnew.VECTOR2I(h0, h0))
            if fp is not None:
                t.SetVisible(False); hidden += 1
            else:
                print("  khong dat duoc chu:", t.GetText())
    print("lua: doi %d chu, an %d reference" % (moved, hidden))


def boot_labels(b):
    fp = b.FindFootprintByReference("SW1001")
    pads = {p.GetNumber(): p.GetPosition() for p in fp.Pads() if p.GetNumber()}
    y = mm(fp.GetPosition().y) + 2.6
    for txt, x in (("BOOT", mm(pads["1"].x)), ("eMMC", mm(pads["3"].x) + 0.6)):
        t = pcbnew.PCB_TEXT(b)
        t.SetText(txt); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(M(0.8), M(0.8))); t.SetTextThickness(M(0.15))
        t.SetPosition(pcbnew.VECTOR2I(M(x), M(y)))
        b.Add(t)


LABELS = {"J201": "PWR BTN", "JP201": "EEPROM WP", "J1101": "TAMPER EXT", "SW201": "RESET", "J202": "FAN 5V"}


def func_labels(b):
    for ref, txt in LABELS.items():
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            continue
        bb = fp.GetBoundingBox(False, False)
        t = pcbnew.PCB_TEXT(b)
        t.SetText(txt); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(M(0.8), M(0.8))); t.SetTextThickness(M(0.15))
        t.SetPosition(pcbnew.VECTOR2I((bb.GetLeft() + bb.GetRight()) // 2, bb.GetBottom() + M(0.9)))
        b.Add(t)


def stitch_islands(b):
    """Mảng đồng GND (lớp ngoài) có pad GND nhưng không via nào: thêm via 0.45/0.2 xuống mặt phẳng GND."""
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    M = pcbnew.FromMM
    gvias = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA" and v.GetNetname() == "GND"]
    gpads = [p for p in b.GetPads() if p.GetNetname() == "GND"]
    other = [t for t in b.GetTracks() if t.GetNetname() != "GND"] + [p for p in b.GetPads() if p.GetNetname() != "GND"]
    holes = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA"] + \
            [p.GetPosition() for p in b.GetPads() if p.HasHole()]
    sig = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    added = 0
    for z in list(b.Zones()):
        if z.GetNetname() != "GND":
            continue
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.IsOnLayer(L):
                continue
            fp = z.GetFilledPolysList(L)
            for i in range(fp.OutlineCount()):
                if any(fp.Contains(v.GetPosition(), i) for v in gvias):
                    continue
                if not any(p.IsOnLayer(L) and fp.Contains(p.GetPosition(), i) for p in gpads):
                    continue
                bb = fp.Outline(i).BBox()
                done = False
                for gx in range(bb.GetX(), bb.GetRight(), M(0.05)):
                    for gy in range(bb.GetY(), bb.GetBottom(), M(0.05)):
                        c = pcbnew.VECTOR2I(gx, gy)
                        ring = [pcbnew.VECTOR2I(gx + int(M(0.26) * math.cos(a * math.pi / 4)),
                                                gy + int(M(0.26) * math.sin(a * math.pi / 4))) for a in range(8)]
                        if not all(fp.Contains(q, i) for q in [c] + ring):
                            continue
                        if any(math.hypot(h.x - gx, h.y - gy) < M(0.55) for h in holes):
                            continue
                        if any(it.HitTest(c, M(0.225 + 0.13)) for it in other
                               if any(it.IsOnLayer(l) for l in sig)):
                            continue
                        v = pcbnew.PCB_VIA(b)
                        v.SetPosition(c); v.SetViaType(pcbnew.VIATYPE_THROUGH)
                        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                        v.SetWidth(pcbnew.F_Cu, M(0.45)); v.SetDrill(M(0.2))
                        v.SetNet(b.FindNet("GND")); b.Add(v)
                        gvias.append(v); holes.append(c); added += 1
                        done = True
                        print("  via GND khau dao %s (%.2f, %.2f)" % (b.GetLayerName(L), gx / 1e6, gy / 1e6))
                        break
                    if done:
                        break
                if not done:
                    print("  !! khong dat duoc via cho dao GND tai", bb.GetX() / 1e6, bb.GetY() / 1e6)
    return added


def via_clusters(b, nets=("+12V", "+12V_JACK", "/Power/VIN_FUSED"), extra=2):
    """Review W3: mỗi via đổi lớp của đường vào 12 V thêm tối đa `extra` via song song (0.6/0.3), nối bằng dải 0.6 mm
    trên cả F.Cu và B.Cu, chỉ đặt ở chỗ cách đồng net khác đủ khe hở."""
    M = pcbnew.FromMM
    sig = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    added = 0
    for net in nets:
        ni = b.FindNet(net)
        if ni is None:
            continue
        vs = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == net]
        for v0 in vs:
            c0 = v0.GetPosition()
            other = [t for t in b.GetTracks() if t.GetNetname() != net] + \
                    [p for p in b.GetPads() if p.GetNetname() != net]
            holes = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA"] + \
                    [p.GetPosition() for p in b.GetPads() if p.HasHole()]
            got = 0
            for k in range(16):
                if got >= extra:
                    break
                a = k * math.pi / 8
                c = pcbnew.VECTOR2I(c0.x + int(M(1.0) * math.cos(a)), c0.y + int(M(1.0) * math.sin(a)))
                if any(math.hypot(h.x - c.x, h.y - c.y) < M(0.95) for h in holes):
                    continue
                pts = [pcbnew.VECTOR2I(c0.x + int((c.x - c0.x) * f), c0.y + int((c.y - c0.y) * f))
                       for f in (0.35, 0.7, 1.0)]
                ok = True
                for it in other:
                    for q in pts:
                        lay_ok = [l for l in sig if it.IsOnLayer(l)]
                        if lay_ok and it.HitTest(q, M(0.3 + 0.2 + 0.05)):
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    continue
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(c); v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetWidth(pcbnew.F_Cu, M(0.6)); v.SetDrill(M(0.3)); v.SetNet(ni); b.Add(v)
                for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(c0); t.SetEnd(c); t.SetWidth(M(0.6)); t.SetLayer(L); t.SetNet(ni); b.Add(t)
                holes.append(c); got += 1; added += 1
            print("  via %s (%.2f, %.2f): +%d via song song" % (net, c0.x / 1e6, c0.y / 1e6, got))
    return added


def widen_buck(b, path, w=0.4):
    """Review M1: đoạn +5V/+3V3_SW/+1V0 còn mảnh (< 0.3 mm) trong khu buck phía tây -> nới lên `w`; đoạn nào gây lỗi
    khe hở (DRC) thì trả về bề rộng cũ."""
    M = pcbnew.FromMM
    boxes = ((40, 44, 61, 66.5), (40, 68, 53.5, 79.5))         # = route.BUCK_BOX (toạ độ trang)
    ch = {}
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" or t.GetNetname() not in ("+5V", "+3V3_SW", "+1V0") or t.GetWidth() >= M(0.3):
            continue
        if all(any(a <= q.x / 1e6 <= c and y0 <= q.y / 1e6 <= y1 for a, y0, c, y1 in boxes)
               for q in (t.GetStart(), t.GetEnd())):
            ch[(t.GetNetname(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)] = t.GetWidth()
            t.SetWidth(M(w))
    refill_save(b, path)
    d = drc(path)
    bad = set()
    for v in d["violations"]:
        if v["severity"] == "error":
            for it in v["items"]:
                bad.add((round(it["pos"]["x"], 3), round(it["pos"]["y"], 3)))
    back = 0
    for t in list(b.GetTracks()):
        k = (t.GetNetname(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)
        if k in ch:
            pts = [t.GetStart(), t.GetEnd(), (t.GetStart() + t.GetEnd()) / 2]
            if any(min(abs(q.x / 1e6 - x) + abs(q.y / 1e6 - y) for q in pts) < 0.01 or
                   t.HitTest(pcbnew.VECTOR2I(M(x), M(y)), 0) for x, y in bad):
                t.SetWidth(ch[k]); back += 1
    print("  noi rong %d doan nguon khu buck (tra lai %d doan vuong khe ho)" % (len(ch) - back, back))


def main():
    dangling_pass(PCB)
    b = pcbnew.LoadBoard(PCB)
    tb = b.GetTitleBlock(); tb.SetRevision(REV); tb.SetDate(DATE)
    stitch_islands(b)
    via_clusters(b)
    widen_buck(b, PCB)
    widen_buck(b, PCB, w=0.25)
    boot_labels(b)
    func_labels(b)
    polish_silk(b)
    refill_save(b, PCB)
    pro = PCB.replace(".kicad_pcb", ".kicad_pro")
    j = json.load(open(pro))
    j.setdefault("text_variables", {}).update({"REVISION": REV, "ISSUE_DATE": DATE})
    # footprint do script sinh và đã cắt lụa -> khác thư viện là chủ ý
    sev = j.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rule_severities", {})
    sev.update({"lib_footprint_mismatch": "ignore", "lib_footprint_issues": "ignore"})
    json.dump(j, open(pro, "w"), indent=2)
    d = drc(PCB)
    from collections import Counter
    print("DRC loi:", sum(1 for v in d["violations"] if v["severity"] == "error"),
          "chua noi:", len(d["unconnected_items"]),
          "canh bao:", dict(Counter(v["type"] for v in d["violations"] if v["severity"] == "warning")))


if __name__ == "__main__":
    main()
