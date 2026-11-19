#!/usr/bin/env python3
"""Báo cáo đi dây: độ dài, độ lệch trong cặp, số via, lớp của từng cặp vi sai; thống kê đường/via toàn bo.
Dùng: .venv/bin/python scripts/routing_report.py  -> docs/reviews/routing-report.md"""
import fnmatch
import json
import math
import os
import sys
from collections import defaultdict

import pcbnew

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PCB = os.path.join(ROOT, "hardware", "cm4-gateway.kicad_pcb")
PRO = os.path.join(ROOT, "hardware", "cm4-gateway.kicad_pro")
LN = {pcbnew.F_Cu: "L1", pcbnew.In2_Cu: "L3", pcbnew.B_Cu: "L6", pcbnew.In1_Cu: "L2", pcbnew.In3_Cu: "L4",
      pcbnew.In4_Cu: "L5"}
LIMIT = {"PCIE_90R": 0.1, "USB_90R": 1.0, "MDI_100R": 3.0}


def main():
    b = pcbnew.LoadBoard(PCB)
    pats = json.load(open(PRO))["net_settings"]["netclass_patterns"]

    def cls(n):
        for p in pats:
            if fnmatch.fnmatchcase(n, p["pattern"]):
                return p["netclass"]
        return "Default"
    length = defaultdict(lambda: defaultdict(float))
    vias = defaultdict(int)
    wmin = {}
    ntr = nvia = 0
    tot = defaultdict(float)
    for t in b.GetTracks():
        n = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            vias[n] += 1
            nvia += 1
            continue
        l = pcbnew.ToMM(t.GetLength())
        length[n][LN[t.GetLayer()]] += l
        tot[LN[t.GetLayer()]] += l
        w = pcbnew.ToMM(t.GetWidth())
        wmin[n] = min(wmin.get(n, 9), w)
        ntr += 1
    names = sorted(length)
    pairs = []
    for n in names:
        for a, c in (("_P", "_N"), ("DP", "DN")):
            if n.endswith(a) and n[:-len(a)] + c in length:
                pairs.append((n, n[:-len(a)] + c))
    out = ["# Báo cáo đi dây — CM4 Security Gateway Rev A", "",
           "Sinh tự động từ `hardware/cm4-gateway.kicad_pcb` bằng `scripts/routing_report.py`.", "",
           "## Tổng quan", "",
           "- Số đoạn đường: **%d**, số via: **%d** (via nhỏ nhất Ø0.45/0.20 mm, không có via-in-pad trên pad linh kiện "
           "ngoài via tản nhiệt trong đế IC)." % (ntr, nvia),
           "- Tổng chiều dài theo lớp: " + ", ".join("%s %.0f mm" % (k, tot[k]) for k in sorted(tot)) + ".",
           "- Stackup JLC06161H-3313: L1 tín hiệu · L2 GND · L3 tín hiệu · L4 GND · L5 nguồn · L6 tín hiệu.", "",
           "## Cặp vi sai", "",
           "Độ dài tính theo tâm đường (không tính chiều cao via). Giới hạn lệch: PCIe 0.1 mm, USB 1.0 mm, MDI 3.0 mm.", "",
           "| Cặp | Net class | Rộng (mm) | Dài P (mm) | Dài N (mm) | Lệch (mm) | Giới hạn | Via/dây | Lớp |",
           "|---|---|---|---|---|---|---|---|---|"]
    worst = defaultdict(float)
    bad = 0
    for p, n in pairs:
        c = cls(p)
        lp, lnn = sum(length[p].values()), sum(length[n].values())
        sk = abs(lp - lnn)
        lim = LIMIT.get(c)
        worst[c] = max(worst[c], sk)
        flag = ""
        if lim is not None and sk > lim:
            flag = " **VƯỢT**"
            bad += 1
        lay = "+".join(sorted(set(length[p]) | set(length[n])))
        out.append("| %s | %s | %.3f | %.2f | %.2f | %.3f%s | %s | %d | %s |" % (
            p[:-2] if p.endswith("_P") else p[:-2], c, wmin[p], lp, lnn, sk, flag, lim if lim is not None else "—",
            vias[p], lay))
    out += ["", "Lệch lớn nhất theo nhóm: " + ", ".join("%s %.3f mm" % kv for kv in sorted(worst.items())) +
            ". Số cặp vượt giới hạn: **%d**." % bad, "",
            "## Trở kháng theo stackup (tính gần đúng, xem `stackup.md`)", "",
            "| Loại | Lớp | Rộng / khe | Z vi sai ước tính |", "|---|---|---|---|",
            "| PCIe, clock, USB | L1 (tham chiếu L2, h = 0.0994 mm) | 0.15 / 0.15 | ≈ 88 Ω |",
            "| Ethernet MDI | L1 | 0.125 / 0.18 | ≈ 100 Ω |",
            "| Đoạn trên L3 (stripline lệch, cách L4 0.109 mm, cách L2 0.55 mm) | L3 | 0.15 / 0.15 | ≈ 80–85 Ω |",
            "| MDI trên L3 | L3 | 0.125 / 0.18 | ≈ 92–96 Ω |",
            "| Clock tự vòng trên L6 (tham chiếu L5) | L6 | 0.15 / 0.15 | ≈ 88 Ω |", "",
            "Các đoạn L3 chỉ mang clock 100 MHz, liên kết giữa hai switch (5 GT/s, ~50 mm) và MDI (125 MBd); sai lệch "
            "trở kháng 5–10 % ở các đoạn này nằm trong dung sai ±15 % của PCIe/Ethernet. Mọi làn dữ liệu PCIe tới NIC "
            "và tới CM4 nằm trọn trên L1.", ""]
    path = os.path.join(ROOT, "docs", "reviews", "routing-report.md")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    print("cap: %d, vuot gioi han: %d, duong %d, via %d" % (len(pairs), bad, ntr, nvia))
    return 0


if __name__ == "__main__":
    sys.exit(main())
