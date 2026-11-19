#!/usr/bin/env python3
"""Rev B: nối nốt nhánh +5V vào cụm VIN của U102 (C115/C116) với bề rộng 0.5 mm — finish.py chọn cặp điểm khác nên
không tìm ra; nối từ đầu dải VIN tới via +5V gần nhất bằng A* (bề rộng tối thiểu theo MINW_LOCAL).

Dùng: CM4GW_PCB=<bo> CM4GW_PLACED=<bố trí> python patch_rev_b.py
"""
import shutil
import sys

import pcbnew

import finish as F
import route as R


def main():
    work = R.PCB + ".work.kicad_pcb"
    shutil.copy(R.PCB, work)
    if R.PLACED:
        shutil.copy(R.PLACED, R.PCB)
    else:                                   # như finish.py: sinh lại bản bố trí
        import os, subprocess
        subprocess.run([sys.executable, os.path.join(R.HERE, "board.py")], check=True, capture_output=True)
    board = pcbnew.LoadBoard(R.PCB)
    rt = F.load_routed(board, work)
    n = rt.netcode["+5V"]
    a = dict(net="+5V", x=50.37 - R.OX, y=52.82 - R.OY, L=0, kind="x")         # đầu dải VIN U102 -> C115
    b = dict(net="+5V", x=64.3 - R.OX, y=59.9 - R.OY, L=None, kind="via")      # via +5V của nhánh cấp
    if not (F.link(rt, n, a, b) or F.link(rt, n, b, a)):
        shutil.copy(work, R.PCB)
        sys.exit("khong noi duoc +5V cho U102")
    R.prune_dead(rt)
    R.save(board, rt)
    __import__("os").remove(work)
    print("da noi +5V -> U102 (0.5 mm)")


if __name__ == "__main__":
    main()
