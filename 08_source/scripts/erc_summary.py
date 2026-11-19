#!/usr/bin/env python3
"""Chạy ERC bằng kicad-cli và in tóm tắt theo loại vi phạm."""
import json, subprocess, sys, tempfile, os
from collections import Counter
sch = sys.argv[1] if len(sys.argv) > 1 else "hardware/cm4-gateway.kicad_sch"
out = os.path.join(tempfile.gettempdir(), "cm4gw_erc.json")
r = subprocess.run(["kicad-cli", "sch", "erc", "--severity-all", "--format", "json", "-o", out, sch],
                   capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-2:] if r.stdout else r.stderr)
d = json.load(open(out))
c = Counter(); ex = {}
for sh in d["sheets"]:
    for v in sh["violations"]:
        k = (v["severity"], v["type"]); c[k] += 1
        ex.setdefault(k, []).append((sh["path"], v["description"], [i["description"] for i in v["items"]]))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
for k, cnt in c.most_common():
    print(cnt, k)
    for e in ex[k][:n]:
        print("     ", e)
print("TONG: %d loi, %d canh bao" % (sum(v for k, v in c.items() if k[0] == "error"),
                                      sum(v for k, v in c.items() if k[0] == "warning")))
