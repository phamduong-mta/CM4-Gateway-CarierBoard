#!/usr/bin/env python3
"""Sinh BOM từ schematic và đối chiếu từng mã LCSC với thư viện PCBA JLCPCB (tồn kho, giá, tên linh kiện).

Dùng: bom_check.py <thư mục ra>   -> bom.csv, bom_summary.md
"""
import csv, os, re, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jlc_search import search

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCH = os.path.join(ROOT, "hardware", "cm4-gateway.kicad_sch")
BOARDS = 5      # số bo ước tính cho 1 lần đặt


def natural(ref):
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


def main(out):
    os.makedirs(out, exist_ok=True)
    xml = os.path.join(tempfile.gettempdir(), "cm4gw_bom.xml")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", xml, SCH],
                   check=True, capture_output=True)
    groups = {}
    for c in ET.parse(xml).getroot().iter("comp"):
        f = {x.get("name"): (x.text or "") for x in c.iter("field")}
        key = (c.findtext("value"), c.findtext("footprint"), f.get("LCSC", ""), f.get("MPN", ""))
        groups.setdefault(key, []).append(c.get("ref"))
    rows, total, problems = [], 0.0, []
    for (value, fp, lcsc, mpn), refs in sorted(groups.items(), key=lambda kv: natural(sorted(kv[1], key=natural)[0])):
        refs = sorted(refs, key=natural)
        qty = len(refs)
        info = dict(stock="", price="", lib="", model="", note="")
        if lcsc:
            # U201: 1 footprint = 2 đầu nối DF40
            q = qty * 2 if lcsc == "C3642394" else qty
            try:
                res = [x for x in search(lcsc, 5) if x.get("componentCode") == lcsc]
                time.sleep(0.15)
            except Exception as e:
                res = []
                info["note"] = "loi tra cuu: %s" % e
            if res:
                r = res[0]
                prices = r.get("componentPrices") or []
                need = q * BOARDS
                price = None
                for p in prices:
                    if p["startNumber"] <= need and (p["endNumber"] == -1 or need <= p["endNumber"]):
                        price = p["productPrice"]
                if price is None and prices:
                    price = prices[0]["productPrice"]
                info.update(stock=r.get("stockCount"), price=price, lib=r.get("componentLibraryType"),
                            model=r.get("componentModelEn") or "")
                total += (price or 0) * q
                if (r.get("stockCount") or 0) < need:
                    problems.append("%s (%s): kho %s < cần %d" % (lcsc, mpn, r.get("stockCount"), need))
                key = re.sub(r"[^A-Za-z0-9]", "", mpn.split()[0]).upper()[:10]
                if key and key not in re.sub(r"[^A-Za-z0-9]", "", info["model"]).upper():
                    info["note"] = "TEN KHAC: JLC ghi '%s'" % info["model"]
                    problems.append("%s: MPN '%s' khác tên JLC '%s'" % (lcsc, mpn, info["model"]))
            elif not info["note"]:
                info["note"] = "KHONG TIM THAY"
                problems.append("%s (%s): không tìm thấy trên JLC" % (lcsc, mpn))
            qty_note = "%d (=%d đầu nối)" % (qty, q) if lcsc == "C3642394" else str(qty)
        else:
            qty_note = str(qty)
            info["note"] = "khong lap (diem do / lo vit)"
        rows.append([", ".join(refs), qty_note, value, fp, mpn, lcsc, info["lib"], info["stock"], info["price"],
                     info["note"]])
    with open(os.path.join(out, "bom.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Tham chieu", "SL/bo", "Gia tri", "Footprint", "MPN", "LCSC", "Loai JLC", "Ton kho JLC",
                    "Don gia USD", "Ghi chu"])
        w.writerows(rows)
    nparts = sum(len(v) for v in groups.values())
    ext = len({r[5] for r in rows if r[6] == "expand"})
    base = len({r[5] for r in rows if r[6] == "base"})
    with open(os.path.join(out, "bom_summary.md"), "w", encoding="utf-8") as f:
        f.write("# Tóm tắt BOM (sinh tự động bởi scripts/bom_check.py)\n\n")
        f.write("- Số linh kiện trên schematic: **%d**, số dòng BOM: **%d**\n" % (nparts, len(rows)))
        f.write("- Loại linh kiện JLC: **%d** mã basic, **%d** mã extended (mỗi mã extended tính phí nạp ~3 USD/lần đặt)\n"
                % (base, ext))
        f.write("- Tiền linh kiện ước tính: **%.1f USD/bo** (giá tại mức %d bo, chưa gồm CM4, PCB, công lắp, phí extended)\n"
                % (total, BOARDS))
        f.write("\n## Vấn đề cần xem\n\n")
        f.write("\n".join("- " + p for p in problems) if problems else "- Không có: mọi mã LCSC đều tìm thấy, đủ kho, đúng tên.")
        f.write("\n")
    print("dong BOM:", len(rows), "| linh kien:", nparts, "| uoc tinh %.1f USD/bo" % total, "| basic", base, "extended", ext)
    for p in problems:
        print("  !", p)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
