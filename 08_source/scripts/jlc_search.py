#!/usr/bin/env python3
"""Tra cứu linh kiện trên thư viện PCBA của JLCPCB (API công khai của trang đặt hàng).
Dùng: jlc_search.py <từ khoá> [từ khoá...]   -> in mã LCSC, kho, giá, loại basic/extended."""
import sys, json, urllib.request

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

def search(keyword, n=8):
    body = json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": n}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    info = (d.get("data") or {}).get("componentPageInfo") or {}
    return info.get("list") or []

def fmt(c):
    prices = c.get("componentPrices") or []
    p1 = prices[0]["productPrice"] if prices else None
    return "%-10s | %-28s | %-22s | %-8s | stock %-7s | $%s | %s" % (
        c.get("componentCode"), (c.get("componentModelEn") or "")[:28],
        (c.get("componentSpecificationEn") or "")[:22],
        c.get("componentLibraryType"), c.get("stockCount"), p1,
        (c.get("componentBrandEn") or "")[:18])

if __name__ == "__main__":
    for kw in sys.argv[1:]:
        print("==", kw)
        try:
            for c in search(kw):
                print("  " + fmt(c))
        except Exception as e:
            print("  ERR", e)
