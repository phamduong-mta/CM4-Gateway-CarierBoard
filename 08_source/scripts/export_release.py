#!/usr/bin/env python3
"""Xuất GÓI FINAL giai đoạn 2 vào out/release/rev-b/ (cấu trúc theo task.md §11).

Chạy từ thư mục gốc dự án:  python3 scripts/export_release.py [--no-jlc]
Mọi file sinh lại từ nguồn bằng kicad-cli; nhật ký ở LOG.txt. --no-jlc: bỏ bước tra tồn kho JLC (không cần mạng).
"""
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, OrderedDict

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HW = os.path.join(ROOT, "hardware")
NAME = "cm4-gateway"
SCH = os.path.join(HW, NAME + ".kicad_sch")
PCB = os.path.join(HW, NAME + ".kicad_pcb")
OUT = os.path.join(ROOT, "out", "release", "rev-b")
OX, OY = 40.0, 30.0
LOG = []

# Hiệu chỉnh góc xoay cho CPL của JLCPCB (góc JLC = góc KiCad + hiệu chỉnh), theo bảng dùng phổ biến của cộng đồng
# (JLCKicadTools). JLC vẫn hiển thị vị trí/chiều linh kiện trước khi sản xuất — PHẢI xem lại ở bước đặt hàng.
ROT_FIX = [
    (r"^SOT-23", 180), (r"^TSOT-23", 180), (r"^SOT-223", 180), (r"^SOIC-", 270), (r"^SOP-", 270), (r"^HSOP-", 270), (r"^MSOP-", 270),
    (r"^TSSOP-", 270), (r"^LQFP-", 270), (r"^QFN-", 270), (r"^VQFN-", 270), (r"^CP_Elec_", 180),
    (r"^D_SOD-123", 0), (r"^D_SMB", 0), (r"^D_SMC", 0), (r"^LED_", 0), (r"^Crystal_SMD_3215", 0),
]


def run(cmd, ok_codes=(0,)):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if "property.h" not in l and "swig" not in l]
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


def natural(ref):
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


def netlist_comps(dst_xml):
    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", dst_xml, SCH])
    comps = OrderedDict()
    for c in ET.parse(dst_xml).getroot().iter("comp"):
        f = {x.get("name"): (x.text or "") for x in c.iter("field")}
        comps[c.get("ref")] = dict(ref=c.get("ref"), value=c.findtext("value") or "",
                                   fp=(c.findtext("footprint") or ""), lcsc=f.get("LCSC", ""), mpn=f.get("MPN", ""))
    return comps


def board_parts():
    """Đọc vị trí linh kiện trực tiếp từ PCB (tâm footprint theo hệ toạ độ bo, mm)."""
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    out = {}
    for fp in b.GetFootprints():
        tht = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads())
        smd = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in fp.Pads())
        bb = fp.GetBoundingBox(False)       # thân + pad, không tính chữ
        pads = [p for p in fp.Pads() if p.IsOnCopperLayer()]
        if pads:
            cx = (min(p.GetPosition().x for p in pads) + max(p.GetPosition().x for p in pads)) / 2
            cy = (min(p.GetPosition().y for p in pads) + max(p.GetPosition().y for p in pads)) / 2
        else:
            cx, cy = bb.Centre().x, bb.Centre().y
        out[fp.GetReference()] = dict(
            x=pcbnew.ToMM(cx) - OX, y=pcbnew.ToMM(cy) - OY, rot=fp.GetOrientationDegrees() % 360,
            side="Bottom" if fp.IsFlipped() else "Top",
            # THT theo thuộc tính footprint (pad PTH của via tản nhiệt / chân giữ vỏ USB không tính là THT)
            tht=bool(fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE), mixed=False,
            fpname=str(fp.GetFPID().GetLibItemName()),
            nobom=bool(fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM))
    return out, b


def main():
    no_jlc = "--no-jlc" in sys.argv
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = git("rev-parse", "--short", "HEAD")
    dirty = len([l for l in git("status", "--porcelain").splitlines() if not l[3:].startswith("out/")])
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    ver = run(["kicad-cli", "version"]).stdout.strip()
    LOG.append("kicad-cli %s | commit %s | file chua commit: %d | %s" % (ver, commit, dirty, stamp))

    # ---- 01 schematic
    o1 = d("01_schematic")
    run(["kicad-cli", "sch", "export", "pdf", "-o", os.path.join(o1, NAME + "-schematic.pdf"), SCH])
    run(["kicad-cli", "sch", "export", "svg", "-o", d("01_schematic", "svg"), SCH])

    # ---- 02 bản vẽ PCB
    o2 = d("02_pcb_drawings")
    copper = [("F.Cu", "L1_F_Cu"), ("In1.Cu", "L2_In1_GND"), ("In2.Cu", "L3_In2_tin_hieu"), ("In3.Cu", "L4_In3_GND"),
              ("In4.Cu", "L5_In4_nguon"), ("B.Cu", "L6_B_Cu")]
    for layer, nm in copper:
        run(["kicad-cli", "pcb", "export", "pdf", "--layers", layer + ",Edge.Cuts", "--mode-single",
             "-o", os.path.join(o2, "copper_%s.pdf" % nm), PCB])
    run(["kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,F.Silkscreen,F.Courtyard,Edge.Cuts", "--mode-single",
         "--black-and-white", "-o", os.path.join(o2, "assembly-top.pdf"), PCB])
    run(["kicad-cli", "pcb", "export", "pdf", "--layers", "B.Fab,B.Silkscreen,B.Courtyard,Edge.Cuts", "--mode-single",
         "--black-and-white", "--mirror", "-o", os.path.join(o2, "assembly-bottom.pdf"), PCB])
    run([sys.executable, "scripts/gen/diagrams.py", o2, "dims", "floor"])
    run(["convert", "-density", "110", os.path.join(o2, "dimensions.svg"), os.path.join(o2, "dimensions.pdf")])

    # ---- 03 ảnh
    o3 = d("03_images")
    views = {"3d_top": ["--side", "top", "--zoom", "0.95"],
             "3d_bottom": ["--side", "bottom", "--zoom", "0.95"],
             "3d_front": ["--rotate", "-78,0,0", "--zoom", "0.95"],
             "3d_back": ["--rotate", "-78,0,180", "--zoom", "0.95"],
             "3d_iso": ["--rotate", "-50,0,30", "--perspective", "--zoom", "0.85"]}
    for name, opts in views.items():
        run(["kicad-cli", "pcb", "render", "-w", "2400", "-h", "1600", "--quality", "high", "--background",
             "opaque"] + opts + ["-o", os.path.join(o3, name + ".png"), PCB])
    for layer, nm in copper:
        svg = os.path.join(o3, "copper_%s.svg" % nm)
        run(["kicad-cli", "pcb", "export", "svg", "--layers", layer + ",Edge.Cuts", "--mode-single",
             "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", svg, PCB])
        run(["convert", "-density", "300", "-background", "black", "-flatten", svg, svg[:-4] + ".png"])
        os.remove(svg)
    run([sys.executable, "scripts/gen/diagrams.py", o3, "block", "power"])

    # ---- 04 3D
    o4 = d("04_3d")
    run(["kicad-cli", "pcb", "export", "step", "--subst-models", "--force", "-o",
         os.path.join(o4, NAME + ".step"), PCB], ok_codes=(0, 2))

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
    wtypes = Counter(v["type"] for v in drc["violations"])
    rep = os.path.join(ROOT, "docs", "reviews", "routing-report.md")
    if os.path.exists(rep):
        shutil.copy(rep, os.path.join(o5, "routing-report.md"))
    with open(os.path.join(o5, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("# Tóm tắt ERC / DRC (bản final Rev B)\n\n")
        f.write("| Kiểm tra | Lỗi | Cảnh báo | Ghi chú |\n|---|---|---|---|\n")
        f.write("| ERC (schematic) | **%d** | %d | |\n" % (n_erc_e, n_erc_w))
        f.write("| DRC (PCB) | **%d** | %d | %s |\n" % (n_drc_e, n_drc_w,
                                                     ", ".join("%s ×%d" % kv for kv in wtypes.most_common()) or "—"))
        f.write("| Chưa nối | **%d** | — | |\n" % n_unc)
        f.write("| Lệch schematic ↔ PCB | **%d** | — | |\n" % n_par)
        f.write("\nLuật DRC: `hardware/cm4-gateway.kicad_dru` + net class trong `.kicad_pro` (không có luật theo Reference).\n")
        f.write("Báo cáo độ dài / lệch từng cặp vi sai: `routing-report.md`.\n")

    # ---- 07 BOM / netlist / vị trí  (làm trước 06 để dùng chung dữ liệu)
    o7 = d("07_bom_netlist")
    comps = netlist_comps(os.path.join(o7, NAME + ".net.xml"))
    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", os.path.join(o7, NAME + ".net"), SCH])
    run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "-o", os.path.join(o7, "positions_all.csv"), PCB])
    if no_jlc:
        LOG.append("(bo qua tra ton kho JLC)")
    else:
        run([sys.executable, "scripts/bom_check.py", o7])
    parts, board = board_parts()

    # ---- 06 sản xuất
    o6 = d("06_fabrication")
    gdir = d("06_fabrication", "gerber")
    layers = "F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "--no-x2",
         "--use-drill-file-origin", "-o", gdir, PCB])
    run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--drill-origin",
         "plot", "--excellon-units", "mm", "--generate-map", "--map-format", "pdf", "-o", gdir + os.sep, PCB])
    with zipfile.ZipFile(os.path.join(o6, "gerber.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(gdir)):
            if not fn.endswith(".pdf"):
                z.write(os.path.join(gdir, fn), fn)
    # BOM / CPL cho JLC: chỉ linh kiện có mã LCSC; U201 (CM4) = 2 đầu nối DF40 tách thành U201A/U201B
    groups = OrderedDict()
    cpl = []
    not_fitted = []
    for ref in sorted(comps, key=natural):
        c = comps[ref]
        p = parts.get(ref)
        if p is None:
            continue
        fpn = c["fp"].split(":")[-1]
        if not c["lcsc"]:
            not_fitted.append((ref, c["value"], "không có mã LCSC (điểm đo / lỗ vít / pin)"))
            continue
        fix = next((a for pat, a in ROT_FIX if re.match(pat, fpn)), 0)
        if ref == "U201":
            # hai đầu nối DF40C-100DS: toạ độ lấy từ 2 nhóm pad (chân 1-100 và 101-200)
            import pcbnew
            fp = board.FindFootprintByReference("U201")
            for suffix, lo in (("A", 1), ("B", 101)):
                pads = [q for q in fp.Pads() if q.GetNumber().isdigit() and lo <= int(q.GetNumber()) < lo + 100]
                x = (min(q.GetPosition().x for q in pads) + max(q.GetPosition().x for q in pads)) / 2
                y = (min(q.GetPosition().y for q in pads) + max(q.GetPosition().y for q in pads)) / 2
                cpl.append(["U201" + suffix, pcbnew.ToMM(x) - OX, pcbnew.ToMM(y) - OY, "Top", (p["rot"] + 90) % 360])
            groups.setdefault(("DF40C-100DS-0.4V (CM4)", "DF40C-100DS-0.4V", c["lcsc"]), []).extend(["U201A", "U201B"])
            continue
        groups.setdefault((c["value"], fpn, c["lcsc"]), []).append(ref)
        rot = (p["rot"] + fix) % 360        # mặt dưới chỉ có R/C/ferrite không cực tính
        cpl.append([ref, p["x"], p["y"], p["side"], rot])
    with open(os.path.join(o6, "bom_jlc.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fpn, lcsc), refs in groups.items():
            w.writerow([val, ",".join(refs), fpn, lcsc])
    with open(os.path.join(o6, "cpl_jlc.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, x, y, side, rot in cpl:
            # gốc toạ độ CPL = gốc file gerber (góc trên-trái của trang vẽ KiCad); trục Y của JLC hướng lên
            w.writerow([ref, "%.4fmm" % (x + OX), "%.4fmm" % (-(y + OY)), side, "%.1f" % rot])
    with open(os.path.join(o6, "lcsc_map.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Footprint", "LCSC", "MPN", "Qty", "Refs", "THT"])
        for (val, fpn, lcsc), refs in groups.items():
            r0 = refs[0].rstrip("AB") if refs[0].startswith("U201") else refs[0]
            tht = "THT" if parts[r0]["tht"] else ("SMD+THT" if parts[r0]["mixed"] else "SMD")
            w.writerow([val, fpn, lcsc, comps[r0]["mpn"], len(refs), " ".join(refs), tht])
    n_bom = sum(len(v) for v in groups.values())
    tht_refs = sorted([r for r in comps if comps[r]["lcsc"] and parts.get(r) and (parts[r]["tht"] or parts[r]["mixed"])],
                      key=natural)
    # kiểm tra chéo
    n_sch = len(comps)
    n_sch_lcsc = sum(1 for c in comps.values() if c["lcsc"])
    cross = dict(schematic=n_sch, pcb=len(parts), co_lcsc=n_sch_lcsc, bom_jlc=n_bom, cpl_jlc=len(cpl),
                 khong_lap=len(not_fitted))
    ok_cross = (n_sch == len(parts)) and (n_bom == len(cpl) == n_sch_lcsc + 1)     # +1: U201 tách thành 2 đầu nối
    cross["dat"] = ok_cross
    json.dump(cross, open(os.path.join(o6, "crosscheck.json"), "w"), indent=1)
    tpl = open(os.path.join(ROOT, "docs", "specs", "ORDERING.tpl.md"), encoding="utf-8").read()
    bom_sum = ""
    bs = os.path.join(o7, "bom_summary.md")
    if os.path.exists(bs):
        bom_sum = open(bs, encoding="utf-8").read()
    cost = re.search(r"\*\*([\d.]+) USD/bo\*\*", bom_sum)
    ext = re.search(r"\*\*(\d+)\*\* mã extended", bom_sum)
    vals = dict(NBOM=str(n_bom), NLINES=str(len(groups)), NCPL=str(len(cpl)), NSCH=str(n_sch),
                NTOP=str(sum(1 for r in cpl if r[3] == "Top")), NBOT=str(sum(1 for r in cpl if r[3] == "Bottom")),
                THT=", ".join(tht_refs), NTHT=str(len(tht_refs)),
                NOTFIT="\n".join("| %s | %s | %s |" % t for t in not_fitted),
                COST=cost.group(1) if cost else "?", NEXT=ext.group(1) if ext else "?",
                CROSS="ĐẠT" if ok_cross else "KHÔNG ĐẠT")
    for k, v in vals.items():
        tpl = tpl.replace("{{%s}}" % k, v)
    open(os.path.join(o6, "ORDERING.md"), "w", encoding="utf-8").write(tpl)

    # ---- 08 nguồn
    o8 = d("08_source")
    shutil.copytree(HW, os.path.join(o8, "hardware"),
                    ignore=shutil.ignore_patterns("*-backups", "*.kicad_prl", "fp-info-cache", "ref", "*.lck", "~*"))
    shutil.copytree(os.path.join(ROOT, "scripts"), os.path.join(o8, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.pyc"))

    # ---- 09 tài liệu
    o9 = d("09_docs")
    shutil.copy(os.path.join(ROOT, "docs", "specs", "2026-11-11-cm4-gateway-design.md"), os.path.join(o9, "design-doc.md"))
    for f in ("stackup.md", "routing-plan.md"):
        shutil.copy(os.path.join(ROOT, "docs", "specs", f), os.path.join(o9, f))
    for f in ("BRINGUP.md", "SOFTWARE.md"):
        shutil.copy(os.path.join(ROOT, "docs", f), os.path.join(o9, f))
    for f in sorted(os.listdir(os.path.join(ROOT, "docs", "notes"))):
        if f.endswith(".md"):
            shutil.copy(os.path.join(ROOT, "docs", "notes", f), os.path.join(o9, f))
    shutil.copy(os.path.join(ROOT, "docs", "datasheets", "SOURCES.md"), os.path.join(o9, "datasheet-SOURCES.md"))
    for f in sorted(os.listdir(os.path.join(ROOT, "docs", "reviews"))):
        if f.endswith(".md"):
            shutil.copy(os.path.join(ROOT, "docs", "reviews", f), os.path.join(o9, "review-" + f))
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import export_stage1
    export_stage1.LOG = LOG
    npins = export_stage1.cm4_pinout(o9)

    # ---- README
    tpl = open(os.path.join(ROOT, "docs", "specs", "release-README.tpl.md"), encoding="utf-8").read()
    vals = dict(STAMP=stamp, COMMIT=commit, DIRTY=str(dirty), KICAD=ver, ERC_E=str(n_erc_e), ERC_W=str(n_erc_w),
                DRC_E=str(n_drc_e), DRC_W=str(n_drc_w), UNC=str(n_unc), PAR=str(n_par), NPARTS=str(len(parts)),
                NPINS=str(npins), NBOM=str(n_bom), NCPL=str(len(cpl)), COST=cost.group(1) if cost else "?",
                CROSS="đạt" if ok_cross else "KHÔNG ĐẠT")
    for k, v in vals.items():
        tpl = tpl.replace("{{%s}}" % k, v)
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(tpl)

    open(os.path.join(OUT, "LOG.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    sums = []
    for base, _, files in sorted(os.walk(OUT)):
        for fn in sorted(files):
            p = os.path.join(base, fn)
            if fn == "SHA256SUMS":
                continue
            sums.append("%s  %s" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), os.path.relpath(p, OUT)))
    open(os.path.join(OUT, "SHA256SUMS"), "w").write("\n".join(sums) + "\n")
    print("Da xuat goi final: %d file | ERC %d loi | DRC %d loi | chua noi %d | lech sch-pcb %d | BOM %d = CPL %d (%s)"
          % (len(sums), n_erc_e, n_drc_e, n_unc, n_par, n_bom, len(cpl), "dat" if ok_cross else "KHONG DAT"))
    return 0 if (n_erc_e == 0 and n_drc_e == 0 and n_unc == 0 and n_par == 0 and ok_cross) else 2


if __name__ == "__main__":
    sys.exit(main())
