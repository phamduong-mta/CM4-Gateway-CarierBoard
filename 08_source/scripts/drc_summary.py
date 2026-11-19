#!/usr/bin/env python3
"""Chạy DRC bằng kicad-cli và in tóm tắt theo loại vi phạm."""
import json, subprocess, sys, tempfile, os
from collections import Counter
pcb = sys.argv[1] if len(sys.argv) > 1 else "hardware/cm4-gateway.kicad_pcb"
out = os.path.join(tempfile.gettempdir(), "cm4gw_drc.json")
r = subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "--schematic-parity", "--format", "json", "-o", out, pcb],
                   capture_output=True, text=True)
print((r.stdout or r.stderr).strip().splitlines()[-3:])
d = json.load(open(out))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
for key in ("violations", "schematic_parity"):
    c = Counter(); ex = {}
    for v in d.get(key, []):
        k = (v["severity"], v["type"]); c[k] += 1
        ex.setdefault(k, []).append((v["description"], [i["description"] for i in v["items"]]))
    print("==", key, sum(c.values()))
    for k, cnt in c.most_common():
        print(cnt, k)
        for e in ex[k][:n]:
            print("     ", e)
print("== unconnected_items", len(d.get("unconnected_items", [])))
