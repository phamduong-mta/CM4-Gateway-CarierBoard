#!/usr/bin/env python3
"""Rev B: giữ lại toàn bộ dây của bản đã đi sạch (rev A) ở những chỗ không đổi, chỉ đi lại khu nguồn.

Cách làm: nạp bản bố trí mới (CM4GW_PLACED), đặt đồng nguồn rộng cố định (pre_power), rồi chép từng đoạn dây / via
của bản cũ sang nếu nó không đè lên đồng của net khác (pad đã dời, đồng nguồn mới). Net dòng lớn (MINW) bỏ hẳn để đi
lại với bề rộng tối thiểu. Phần còn hở do finish.py nối nốt.

Dùng: CM4GW_PCB=<ra> CM4GW_PLACED=<bố trí> python reuse_route.py <bo_cu.kicad_pcb>
"""
import shutil
import sys

import numpy as np
import pcbnew

import route as R

CLR = 0.1


def main():
    old = pcbnew.LoadBoard(sys.argv[1])
    if R.PLACED:                                      # không có: R.PCB đang là bản board.py vừa sinh
        shutil.copy(R.PLACED, R.PCB)
    board = pcbnew.LoadBoard(R.PCB)
    rt = R.load(board)
    rt.pairs = []
    rt.minw = {rt.netcode[n]: w for n, w in R.MINW.items() if n in rt.netcode}
    n0 = len(rt.tracks)
    R.pre_power(rt)
    rt.fixed = {tuple(t) for t in rt.tracks[n0:]}
    T = lambda v: v / 1e6
    kept = drop = 0
    inbox = lambda x, y: any(a <= x <= c and b <= y <= d for a, b, c, d in R.BUCK_BOX)
    items = list(old.GetTracks())
    for t in items:                                   # via trước, rồi đường
        if t.GetClass() != "PCB_VIA":
            continue
        nm = t.GetNetname()
        if nm in R.MINW or nm not in rt.netcode:
            drop += 1
            continue
        n = rt.netcode[nm]
        x, y, d = T(t.GetPosition().x) - R.OX, T(t.GetPosition().y) - R.OY, T(t.GetWidth(pcbnew.F_Cu))
        if nm in R.MINW_LOCAL and inbox(x, y):
            drop += 1
            continue
        if all(rt.seg_free((n,), L, x, y, x, y, d / 2 + CLR) for L in range(3)):
            rt.add_via(n, x, y, d, T(t.GetDrill()))
            kept += 1
        else:
            drop += 1
    for t in items:
        if t.GetClass() == "PCB_VIA":
            continue
        nm = t.GetNetname()
        if nm in R.MINW or nm not in rt.netcode:
            drop += 1
            continue
        n = rt.netcode[nm]
        L = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}[t.GetLayer()]
        x1, y1 = T(t.GetStart().x) - R.OX, T(t.GetStart().y) - R.OY
        x2, y2 = T(t.GetEnd().x) - R.OX, T(t.GetEnd().y) - R.OY
        w = T(t.GetWidth())
        if nm in R.MINW_LOCAL and (inbox(x1, y1) or inbox(x2, y2)) and w < R.MINW_LOCAL[nm]:
            drop += 1
            continue
        if rt.seg_free((n,), L, x1, y1, x2, y2, w / 2 + CLR):
            rt.add_track(n, L, x1, y1, x2, y2, w)
            kept += 1
        else:
            drop += 1
    rt.hole_base = np.zeros_like(rt.hole)
    R.prune_dead(rt)
    R.save(board, rt)
    print("giu %d, bo %d" % (kept, drop))


if __name__ == "__main__":
    main()
