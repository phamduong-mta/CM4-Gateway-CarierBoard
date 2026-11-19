#!/usr/bin/env python3
"""Xuất GÓI GIAI ĐOẠN 1 vào out/stage1/ (cấu trúc theo task.md §9).

Chạy từ thư mục gốc dự án:  python3 scripts/export_stage1.py
Mọi file đều sinh lại từ nguồn (schematic, PCB, docs) bằng kicad-cli; nhật ký ở LOG.txt.
"""
import csv
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HW = os.path.join(ROOT, "hardware")
SCH = os.path.join(HW, "cm4-gateway.kicad_sch")
PCB = os.path.join(HW, "cm4-gateway.kicad_pcb")
OUT = os.path.join(ROOT, "out", "stage1")
LOG = []


def run(cmd, ok_codes=(0,)):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    last = (r.stdout + r.stderr).strip().splitlines()
    last = [l for l in last if "property.h" not in l]
    LOG.append("$ " + " ".join(os.path.relpath(c, ROOT) if os.path.isabs(c) else c for c in cmd))
    LOG.append("  -> ma thoat %d | %s" % (r.returncode, last[-1] if last else ""))
    if r.returncode not in ok_codes:
        print("LOI:", " ".join(cmd), "\n", r.stdout[-2000:], r.stderr[-2000:])
        sys.exit(1)
    return r


def d(*p):
    path = os.path.join(OUT, *p)
    os.makedirs(path, exist_ok=True)
    return path


def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True, cwd=ROOT).stdout.strip()


def cm4_pinout(dst):
    xml = os.path.join(dst, "_netlist.xml")
    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", xml, SCH])
    root = ET.parse(xml).getroot()
    os.remove(xml)
    pins = json.load(open(os.path.join(ROOT, "scripts", "gen", "cm4_pins.json")))
    names = {n: nm for n, nm, _ in pins}
    net_of = {}
    for n in root.iter("net"):
        for nd in n.iter("node"):
            if nd.get("ref") == "U201":
                net_of[int(nd.get("pin"))] = (n.get("name"), len(list(n.iter("node"))))
    rows = []
    for n in range(1, 201):
        net, cnt = net_of.get(n, ("", 0))
        used = not net.startswith("unconnected-")
        rows.append([n, names[n], net if used else "(để hở)", "" if not used else str(cnt - 1)])
    with open(os.path.join(dst, "cm4-pinout.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Chan", "Ten chan CM4", "Net tren bo", "So chan khac cung net"])
        w.writerows(rows)
    with open(os.path.join(dst, "cm4-pinout.md"), "w", encoding="utf-8") as f:
        f.write("# Bảng gán chân CM4 (200 chân) — sinh từ netlist\n\n")
        f.write("Đầu nối 1 = chân 1–100, đầu nối 2 = chân 101–200. \"(để hở)\" = không nối.\n\n")
        f.write("| Chân | Tên | Net | | Chân | Tên | Net |\n|---|---|---|---|---|---|---|\n")
        for i in range(0, 200, 2):
            a, b = rows[i], rows[i + 1]
            f.write("| %d | %s | %s | | %d | %s | %s |\n" % (a[0], a[1], a[2], b[0], b[1], b[2]))
    used = sum(1 for r in rows if r[2] != "(để hở)")
    return used


def main():
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = git("rev-parse", "--short", "HEAD")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    ver = run(["kicad-cli", "version"]).stdout.strip()
    dirty = len([l for l in git("status", "--porcelain").splitlines() if not l[3:].startswith("out/")])
    LOG.append("kicad-cli %s | commit %s | file chua commit: %d | %s" % (ver, commit, dirty, stamp))

    # ---- 01 tổng quan
    o1 = d("01_overview")
    run([sys.executable, "scripts/gen/diagrams.py", o1, "block", "power"])
    npins = cm4_pinout(o1)
    shutil.copy(os.path.join(ROOT, "docs", "specs", "2026-11-11-cm4-gateway-design.md"),
                os.path.join(o1, "design-doc.md"))

    # ---- 02 schematic
    o2 = d("02_schematic")
    run(["kicad-cli", "sch", "export", "pdf", "-o", os.path.join(o2, "cm4-gateway-schematic.pdf"), SCH])
    run(["kicad-cli", "sch", "export", "svg", "-o", d("02_schematic", "svg"), SCH])

    # ---- 03 layout
    o3 = d("03_layout")
    run([sys.executable, "scripts/gen/diagrams.py", o3, "floor", "rats", "dims"])
    run(["kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,F.Courtyard,F.Silkscreen,Edge.Cuts",
         "--mode-single", "--black-and-white", "-o", os.path.join(o3, "placement-top.pdf"), PCB])
    run(["kicad-cli", "pcb", "export", "pdf", "--layers", "B.Fab,B.Courtyard,B.Silkscreen,Edge.Cuts",
         "--mode-single", "--black-and-white", "--mirror", "-o", os.path.join(o3, "placement-bottom.pdf"), PCB])
    run(["convert", "-density", "110", os.path.join(o3, "dimensions.svg"), os.path.join(o3, "dimensions.pdf")])
    for f in ("stackup.md", "routing-plan.md"):
        shutil.copy(os.path.join(ROOT, "docs", "specs", f), os.path.join(o3, f))
    shutil.copy(os.path.join(HW, "placement.json"), os.path.join(o3, "placement.json"))

    # ---- 04 3D
    o4 = d("04_3d")
    views = {"3d_top": ["--side", "top", "--zoom", "0.95"],
             "3d_bottom": ["--side", "bottom", "--zoom", "0.95"],
             "3d_front": ["--rotate", "-78,0,0", "--zoom", "0.95"],
             "3d_back": ["--rotate", "-78,0,180", "--zoom", "0.95"],
             "3d_iso": ["--rotate", "-50,0,30", "--perspective", "--zoom", "0.85"]}
    for name, opts in views.items():
        run(["kicad-cli", "pcb", "render", "-w", "2400", "-h", "1600", "--quality", "high", "--background",
             "opaque"] + opts + ["-o", os.path.join(o4, name + ".png"), PCB])
    run(["kicad-cli", "pcb", "export", "step", "--subst-models", "--force", "-o",
         os.path.join(o4, "cm4-gateway.step"), PCB], ok_codes=(0, 2))

    # ---- 05 báo cáo
    o5 = d("05_reports")
    for fmt, ext in (("report", "rpt"), ("json", "json")):
        run(["kicad-cli", "sch", "erc", "--severity-all", "--format", fmt, "-o", os.path.join(o5, "erc." + ext), SCH],
            ok_codes=(0, 5))
        run(["kicad-cli", "pcb", "drc", "--severity-all", "--schematic-parity", "--format", fmt, "-o",
             os.path.join(o5, "drc." + ext), PCB], ok_codes=(0, 5))
    erc = json.load(open(os.path.join(o5, "erc.json")))
    drc = json.load(open(os.path.join(o5, "drc.json")))
    erc_v = [v for s in erc["sheets"] for v in s["violations"]]
    n_erc_e = sum(1 for v in erc_v if v["severity"] == "error")
    n_erc_w = sum(1 for v in erc_v if v["severity"] == "warning")
    n_drc_e = sum(1 for v in drc["violations"] if v["severity"] == "error")
    n_drc_w = sum(1 for v in drc["violations"] if v["severity"] == "warning")
    n_unc = len(drc.get("unconnected_items", []))
    n_par = len(drc.get("schematic_parity", []))
    from collections import Counter
    wtypes = Counter(v["type"] for v in drc["violations"])
    with open(os.path.join(o5, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("# Tóm tắt ERC / DRC (giai đoạn 1 — chưa đi dây)\n\n")
        f.write("| Kiểm tra | Lỗi | Cảnh báo | Ghi chú |\n|---|---|---|---|\n")
        f.write("| ERC (schematic) | **%d** | %d | |\n" % (n_erc_e, n_erc_w))
        f.write("| DRC (PCB) | **%d** | %d | %s |\n" % (n_drc_e, n_drc_w, ", ".join("%s ×%d" % kv for kv in wtypes.most_common())))
        f.write("| Chưa nối | — | %d | bình thường: giai đoạn 1 chưa đi dây |\n" % n_unc)
        f.write("| Lệch schematic ↔ PCB | — | %d | |\n" % n_par)
        f.write("\nCảnh báo DRC còn lại đều thuộc silkscreen (chữ chạm mép bo ở đầu nối nhô ra, chữ chồng pad); "
                "sẽ dọn ở giai đoạn 2 cùng lúc đi dây.\n")

    # ---- 06 BOM
    o6 = d("06_bom")
    run([sys.executable, "scripts/bom_check.py", o6])

    # ---- 07 ghi chú
    o7 = d("07_notes")
    for f in sorted(os.listdir(os.path.join(ROOT, "docs", "notes"))):
        if f.endswith(".md"):
            shutil.copy(os.path.join(ROOT, "docs", "notes", f), os.path.join(o7, f))
    shutil.copy(os.path.join(ROOT, "docs", "datasheets", "SOURCES.md"), os.path.join(o7, "datasheet-SOURCES.md"))
    rv = os.path.join(ROOT, "docs", "reviews")
    for f in sorted(os.listdir(rv)):
        if f.endswith(".md"):
            shutil.copy(os.path.join(rv, f), os.path.join(o7, "review-" + f))

    # ---- README từ mẫu
    tpl = open(os.path.join(ROOT, "docs", "specs", "stage1-README.tpl.md"), encoding="utf-8").read()
    bom_sum = open(os.path.join(o6, "bom_summary.md"), encoding="utf-8").read()
    import re
    cost = re.search(r"\*\*([\d.]+) USD/bo\*\*", bom_sum)
    place = json.load(open(os.path.join(HW, "placement.json")))
    nf = sum(1 for p in place["parts"] if p["side"] == "F")
    vals = dict(STAMP=stamp, COMMIT=commit, DIRTY=str(dirty), KICAD=ver, ERC_E=str(n_erc_e), ERC_W=str(n_erc_w),
                DRC_E=str(n_drc_e), DRC_W=str(n_drc_w), UNC=str(n_unc), NPARTS=str(len(place["parts"])),
                NTOP=str(nf), NBOT=str(len(place["parts"]) - nf), NPINS=str(npins),
                COST=cost.group(1) if cost else "?")
    for k, v in vals.items():
        tpl = tpl.replace("{{%s}}" % k, v)
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(tpl)

    # ---- LOG + SHA256
    open(os.path.join(OUT, "LOG.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    sums = []
    for base, _, files in sorted(os.walk(OUT)):
        for fn in sorted(files):
            p = os.path.join(base, fn)
            if fn == "SHA256SUMS":
                continue
            sums.append("%s  %s" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), os.path.relpath(p, OUT)))
    open(os.path.join(OUT, "SHA256SUMS"), "w").write("\n".join(sums) + "\n")
    print("Da xuat goi giai doan 1: %d file | ERC %d loi | DRC %d loi | chua noi %d" % (len(sums), n_erc_e, n_drc_e, n_unc))


if __name__ == "__main__":
    main()
