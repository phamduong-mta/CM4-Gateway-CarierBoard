#!/usr/bin/env python3
"""Lõi bộ đi dây cho giai đoạn 2 (không phụ thuộc phần mềm ngoài).

- Bo mạch được raster hoá ở bước G = 0.05 mm trên 3 lớp tín hiệu: F.Cu, In2.Cu, B.Cu.
  Mỗi ô lưu mã net của phần đồng chiếm ô đó (0 = trống, KEEP = cấm mọi net).
- Khoảng cách an toàn được tính bằng biến đổi khoảng cách Euclid (EDT) trên cửa sổ quanh net đang đi.
- A* 8 hướng có trạng thái hướng (chỉ rẽ 45°), đổi lớp bằng via; cặp vi sai được đi như MỘT đường "béo"
  theo tim cặp rồi dựng hai đường song song, sau đó bù lệch độ dài bằng các gờ nhỏ trên đường ngắn hơn.

Toạ độ: mm theo hệ BO (gốc = góc sau-trái), giống scripts/gen/board.py.
"""
import ctypes
import heapq
import math
import os

import numpy as np
from scipy import ndimage

G = 0.05
KEEP = 32000
F, I2, B = 0, 1, 2
LNAME = ["F.Cu", "In2.Cu", "B.Cu"]
DX = (1, 1, 0, -1, -1, -1, 0, 1)
DY = (0, 1, 1, 1, 0, -1, -1, -1)
MARGIN = 0.035          # dự phòng sai số raster


_LIB = None


def _lib():
    global _LIB
    if _LIB is None:
        here = os.path.dirname(os.path.abspath(__file__))
        so, src = os.path.join(here, "astar.so"), os.path.join(here, "astar.c")
        if not os.path.exists(so) or os.path.getmtime(so) < os.path.getmtime(src):
            import subprocess
            subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", so, src], check=True)
        _LIB = ctypes.CDLL(so)
        _LIB.astar.restype = ctypes.c_long
    return _LIB


def cell(v):
    return int(round(v / G))


class Fail(Exception):
    pass


class RT:
    def __init__(self, w, h, corner_r=3.0, edge=0.25):
        self.W, self.H = w, h
        self.nx, self.ny = cell(w) + 1, cell(h) + 1
        self.cu = [np.zeros((self.ny, self.nx), np.int16) for _ in range(3)]
        self.smd = np.zeros((self.ny, self.nx), bool)       # pad SMD (mọi net) trên F hoặc B: cấm via chồng lên
        self.hole = np.zeros((self.ny, self.nx), bool)      # lỗ khoan (pad xuyên lỗ, via)
        self.thtcu = np.zeros((self.ny, self.nx), bool)     # đồng của pad xuyên lỗ
        self.novia = np.zeros((self.ny, self.nx), bool)
        self.pairkeep = np.zeros((self.ny, self.nx), bool)  # cấm cặp vi sai đi lớp F dưới thân IC     # vùng cấm đặt via (hành lang thoát chân IC bước nhỏ)
        self.tracks = []    # [net, layer, x1, y1, x2, y2, w]
        self.vias = []      # [net, x, y, dia, drill]
        self.pads = {}      # net -> list dict(x, y, layers, ref, num, tht, poly)
        self.log = []
        self.fpsize = {}
        # viền bo: cấm đồng sát mép (kể cả góc bo tròn)
        yy, xx = np.mgrid[0:self.ny, 0:self.nx]
        x, y = xx * G, yy * G
        dx = np.maximum(np.maximum(corner_r - x, x - (w - corner_r)), 0)
        dy = np.maximum(np.maximum(corner_r - y, y - (h - corner_r)), 0)
        inside = np.minimum(np.minimum(x, w - x), np.minimum(y, h - y))
        dist_in = np.where((dx > 0) & (dy > 0), corner_r - np.hypot(dx, dy), inside)
        frame = dist_in < edge
        for a in self.cu:
            a[frame] = KEEP
        self.frame = frame
        self._dsmd = None

    # ------------------------------------------------------------------ raster
    def _box(self, x0, y0, x1, y1):
        return (max(0, cell(x0) - 1), max(0, cell(y0) - 1), min(self.nx, cell(x1) + 2), min(self.ny, cell(y1) + 2))

    def stamp_seg(self, arr, x1, y1, x2, y2, r, val):
        bx0, by0, bx1, by1 = self._box(min(x1, x2) - r, min(y1, y2) - r, max(x1, x2) + r, max(y1, y2) + r)
        if bx1 <= bx0 or by1 <= by0:
            return
        yy, xx = np.mgrid[by0:by1, bx0:bx1]
        px, py = xx * G - x1, yy * G - y1
        vx, vy = x2 - x1, y2 - y1
        l2 = vx * vx + vy * vy
        t = np.clip((px * vx + py * vy) / l2, 0, 1) if l2 > 0 else 0
        d = np.hypot(px - t * vx, py - t * vy)
        arr[by0:by1, bx0:bx1][d <= r] = val

    def stamp_poly(self, arr, pts, val):
        from PIL import Image, ImageDraw
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bx0, by0, bx1, by1 = self._box(min(xs), min(ys), max(xs), max(ys))
        if bx1 <= bx0 or by1 <= by0:
            return
        im = Image.new("L", (bx1 - bx0, by1 - by0), 0)
        ImageDraw.Draw(im).polygon([((x / G - bx0), (y / G - by0)) for x, y in pts], fill=1, outline=1)
        m = np.array(im, bool)
        arr[by0:by1, bx0:bx1][m] = val

    def _stamp_poly_win(self, arr, pts, x0, y0):
        from PIL import Image, ImageDraw
        h, w = arr.shape
        im = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im).polygon([((x / G - x0), (y / G - y0)) for x, y in pts], fill=1, outline=1)
        arr |= np.array(im, bool)

    def add_pad(self, net, name, x, y, polys, layers, ref, num, tht, drill=None, size=(0, 0), keep_extra=0.0):
        """polys: list các đa giác (mm). layers: tập chỉ số lớp (0..2). drill: (x1,y1,x2,y2,r) hoặc None."""
        code = net if net > 0 else KEEP
        for L in layers:
            for pts in polys:
                self.stamp_poly(self.cu[L], pts, code)
        if not tht:
            for pts in polys:
                self.stamp_poly(self.smd, pts, True)
        else:
            for pts in polys:
                self.stamp_poly(self.thtcu, pts, True)
        if drill:
            self.stamp_seg(self.hole, *drill, True)
            if net <= 0:
                for L in range(3):
                    self.stamp_seg(self.cu[L], drill[0], drill[1], drill[2], drill[3], drill[4] + keep_extra, KEEP)
        if net > 0:
            self.pads.setdefault(net, []).append(dict(x=x, y=y, layers=tuple(layers), ref=ref, num=num, tht=tht,
                                                      polys=polys, size=size, name=name))
        self._dsmd = None

    minw = {}       # net -> độ rộng tối thiểu (dòng lớn); mọi bước nối/cứu đều không được đi hẹp hơn

    def _minw(self, net, w, clr, via):
        m = self.minw.get(net)
        if m and w < m:
            return m, max(clr, 0.2), (max(via[0], 0.6), max(via[1], 0.3)) + tuple(via[2:])
        return w, clr, via

    def add_track(self, net, L, x1, y1, x2, y2, w):
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
            return
        self.tracks.append([net, L, x1, y1, x2, y2, w])
        self.stamp_seg(self.cu[L], x1, y1, x2, y2, w / 2, net)

    def add_via(self, net, x, y, dia=0.45, drill=0.2):
        self.vias.append([net, x, y, dia, drill])
        for L in range(3):
            self.stamp_seg(self.cu[L], x, y, x, y, dia / 2, net)
        self.stamp_seg(self.hole, x, y, x, y, drill / 2, True)

    def dsmd(self):
        if self._dsmd is None:
            self._dsmd = (ndimage.distance_transform_edt(~self.smd) * G).astype(np.float32)
        return self._dsmd

    # ------------------------------------------------------------------ mặt nạ
    def window(self, pts, margin):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (max(0, cell(min(xs) - margin)), max(0, cell(min(ys) - margin)),
                min(self.nx, cell(max(xs) + margin) + 1), min(self.ny, cell(max(ys) + margin) + 1))

    def dist_other(self, L, nets, win, pad):
        """Khoảng cách (mm) tới đồng của net khác trên lớp L, trong cửa sổ win (đã cắt)."""
        x0, y0, x1, y1 = win
        px0, py0, px1, py1 = max(0, x0 - pad), max(0, y0 - pad), min(self.nx, x1 + pad), min(self.ny, y1 + pad)
        sub = self.cu[L][py0:py1, px0:px1]
        other = sub != 0
        for n in nets:
            other &= sub != n
        if not other.any():
            return np.full((y1 - y0, x1 - x0), 99.0, np.float32)
        d = ndimage.distance_transform_edt(~other) * G
        return d[y0 - py0:y0 - py0 + (y1 - y0), x0 - px0:x0 - px0 + (x1 - x0)]

    def dist_hole(self, win, pad):
        x0, y0, x1, y1 = win
        px0, py0, px1, py1 = max(0, x0 - pad), max(0, y0 - pad), min(self.nx, x1 + pad), min(self.ny, y1 + pad)
        sub = self.hole[py0:py1, px0:px1]
        if not sub.any():
            return np.full((y1 - y0, x1 - x0), 99.0, np.float32)
        d = ndimage.distance_transform_edt(~sub) * G
        return d[y0 - py0:y0 - py0 + (y1 - y0), x0 - px0:x0 - px0 + (x1 - x0)]

    def masks(self, nets, win, r_trk, layers, via=None, extra_via_r=0.0):
        """Trả về (blk[3], viablk): blk[L] = None nếu lớp không được dùng.
        via = (dia, drill, clr) hoặc None."""
        pad = int(2.0 / G)
        blk = [None, None, None]
        dist = [None, None, None]
        for L in range(3):
            if L in layers or via:
                dist[L] = self.dist_other(L, nets, win, pad)
            if L in layers:
                blk[L] = dist[L] < r_trk
        vb = None
        if via:
            dia, drill, clr = via
            rv = dia / 2 + clr + MARGIN + extra_via_r
            x0, y0, x1, y1 = win
            vb = (dist[0] < rv) | (dist[1] < rv) | (dist[2] < rv)
            vb |= self.dist_hole(win, pad) < (dia / 2 + 0.31 + MARGIN + extra_via_r)   # đồng của via cách lỗ khoan >= 0.30 mm (luật JLC)
            vb |= self.dsmd()[y0:y1, x0:x1] < (dia / 2 + 0.06 + extra_via_r)
            vb |= self.novia[y0:y1, x0:x1]
            # luật JLC (kicad_dru): lỗ via cách đồng của pad xuyên lỗ >= 0.30 mm
            px0, py0 = max(0, x0 - pad), max(0, y0 - pad)
            sub = self.thtcu[py0:min(self.ny, y1 + pad), px0:min(self.nx, x1 + pad)]
            if sub.any():
                dt = ndimage.distance_transform_edt(~sub) * G
                vb |= dt[y0 - py0:y0 - py0 + (y1 - y0), x0 - px0:x0 - px0 + (x1 - x0)] < (drill / 2 + 0.31 + MARGIN + extra_via_r)
        return blk, vb

    # ------------------------------------------------------------------ A*
    @staticmethod
    def astar(nxw, nyw, blk, goal, hfield, starts, step=2, lw=(1.0, 1.3, 1.0), via_cost=1500, viablk=None,
              gdir=None, pairvia=0, turn=30, hw=1.4, maxexp=20000000, layers=(0, 1, 2), minrun=1):
        """blk/goal: list 3 phần tử bytes/bytearray (hoặc None). hfield: mảng float32 (theo ô, đơn vị ô).
        starts: list (li, x, y, dir) — dir 8 = tự do. Trả về list nút [(li, x, y)] từ đầu tới đích, hoặc None.
        Lõi tìm đường viết bằng C (astar.c)."""
        lib = _lib()
        cb = [None if (b is None or i not in layers) else (ctypes.c_ubyte * len(b)).from_buffer_copy(bytes(b))
              for i, b in enumerate(blk)]
        cg = [None if g is None else (ctypes.c_ubyte * len(g)).from_buffer_copy(bytes(g)) for g in goal]
        h = np.ascontiguousarray(hfield, np.float32)
        st = (ctypes.c_int * (4 * len(starts)))(*[v for s_ in starts for v in s_])
        lwc = (ctypes.c_float * 3)(*lw)
        vb = None if viablk is None else (ctypes.c_ubyte * len(viablk)).from_buffer_copy(bytes(viablk))
        cap = 200000
        out = (ctypes.c_int * (3 * cap))()
        n = lib.astar(nxw, nyw, cb[0], cb[1], cb[2], cg[0], cg[1], cg[2], h.ctypes.data_as(ctypes.c_void_p),
                      st, len(starts), step, lwc, ctypes.c_float(via_cost), vb, -1 if gdir is None else gdir,
                      pairvia, ctypes.c_float(turn), ctypes.c_float(hw), ctypes.c_long(maxexp), minrun, out, cap)
        if n < 0:
            return None
        nodes = [(out[3 * i], out[3 * i + 1], out[3 * i + 2]) for i in range(n)]
        nodes.reverse()
        return nodes

    # ------------------------------------------------------------------ đi dây net đơn
    def _hfield(self, goalmask):
        return np.ascontiguousarray(ndimage.distance_transform_edt(~goalmask), np.float32).ravel()

    def connect(self, net, starts_mm, goal_masks_full, w, clr, layers=(0, 1, 2), via=(0.45, 0.2, 0.13), margin=4.0,
                extra_pts=(), step=2, lw=(1.0, 1.3, 1.0), via_cost=1500, nets_own=None, maxexp=1500000):
        """Đi 1 đoạn từ các điểm starts_mm [(L, x, y)] tới vùng đích goal_masks_full (list 3 mảng bool toàn bo hoặc None).
        Trả về danh sách điểm [(L, x, y)] theo mm (đã phát track + via vào self)."""
        w, clr, via = self._minw(net, w, clr, via)
        own = nets_own or (net,)
        gpts = []
        for L in range(3):
            gm = goal_masks_full[L]
            if gm is not None:
                ys, xs = np.nonzero(gm)
                if len(xs):
                    gpts += [(xs.min() * G, ys.min() * G), (xs.max() * G, ys.max() * G)]
        if not gpts:
            raise Fail("khong co dich")
        pts = [(x, y) for _, x, y in starts_mm] + list(extra_pts)
        # cửa sổ: quanh điểm đầu (đích nằm ngoài cửa sổ thì báo lỗi để nơi gọi nới cửa sổ)
        win = self.window(pts, margin)
        x0, y0, x1, y1 = win
        nxw, nyw = x1 - x0, y1 - y0
        r = w / 2 + clr + MARGIN
        blk, vb = self.masks(own, win, r, layers, via)
        gm_any = np.zeros((nyw, nxw), bool)
        goal = [None, None, None]
        for L in range(3):
            if goal_masks_full[L] is not None and blk[L] is not None:
                g = goal_masks_full[L][y0:y1, x0:x1]
                goal[L] = g.tobytes()
                gm_any |= g
        if not gm_any.any():
            raise Fail("dich ngoai cua so")
        h = self._hfield(gm_any)
        starts = []
        for L, x, y in starts_mm:
            cx, cy = cell(x) - x0, cell(y) - y0
            if blk[L] is None:
                continue
            # ô xuất phát luôn được coi là trống (nằm trong pad của chính net)
            starts.append((L, cx, cy, 8))
        bb = [None if b is None else bytearray(b.tobytes()) for b in blk]
        for L, cx, cy, _ in starts:
            bb[L][cy * nxw + cx] = 0
        nodes = self.astar(nxw, nyw, bb, goal, h, starts, step=step, lw=lw, via_cost=via_cost,
                           viablk=None if vb is None else vb.tobytes(), layers=layers, maxexp=maxexp,
                           minrun=2 if step == 2 else 3)
        if nodes is None:
            raise Fail("khong tim duoc duong")
        path = [(L, (x + x0) * G, (y + y0) * G) for L, x, y in nodes]
        self.emit_path(net, path, w, via)
        return path

    def emit_path(self, net, path, w, via):
        """path: [(L, x, y)] — nút liên tiếp cùng (x, y) khác L = via."""
        i = 0
        n = len(path)
        while i < n - 1:
            L, x, y = path[i]
            L2, x2, y2 = path[i + 1]
            if L2 != L:
                self.add_via(net, x, y, via[0], via[1])
                i += 1
                continue
            # gộp các nút thẳng hàng
            j = i + 1
            dx, dy = x2 - x, y2 - y
            while j + 1 < n and path[j + 1][0] == L:
                ex, ey = path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]
                if abs(dx * ey - dy * ex) > 1e-9 or (dx * ex + dy * ey) <= 0:
                    break
                j += 1
            self.add_track(net, L, x, y, path[j][1], path[j][2], w)
            i = j

    def pad_goal(self, pads, shrink=0.0):
        """Mặt nạ đích (3 lớp) phủ phần đồng của các pad đã cho."""
        gm = [np.zeros((self.ny, self.nx), bool) for _ in range(3)]
        for p in pads:
            for L in p["layers"]:
                for pts in p["polys"]:
                    self.stamp_poly(gm[L], pts, True)
        return gm

    def route_net(self, net, w, clr, layers=(0, 1, 2), via=(0.45, 0.2, 0.13), order=None, lw=(1.0, 1.3, 1.0),
                  via_cost=1500, margins=(3.0, 10.0, 40.0, 160.0), done=None, step=2, widths=None):
        """Nối toàn bộ pad của 1 net thành cây. done: mặt nạ 3 lớp của phần đã nối (nếu net đã có sẵn đường)."""
        pads = self.pads.get(net, [])
        if len(pads) < 2 and done is None:
            return True
        tree = done
        rest = list(pads)
        if tree is None:
            # bắt đầu từ pad gần trọng tâm nhất
            cx = sum(p["x"] for p in pads) / len(pads)
            cy = sum(p["y"] for p in pads) / len(pads)
            # hạt giống: pad của linh kiện ít chân nhất (tụ, điểm đo — dễ tiếp cận), gần trọng tâm
            rest.sort(key=lambda p: (min(self.fpsize.get(p["ref"], 2), 8), (p["x"] - cx) ** 2 + (p["y"] - cy) ** 2))
            first = rest.pop(0)
            tree = self.pad_goal([first])
            tpts = [(first["x"], first["y"])]
        else:
            tpts = []
            for L in range(3):
                ys, xs = np.nonzero(tree[L])
                tpts += list(zip((xs[::40] * G).tolist(), (ys[::40] * G).tolist()))
            # pad đã nằm trong cây thì bỏ qua
            rest = [p for p in rest if not any(tree[L][cell(p["y"]), cell(p["x"])] for L in p["layers"])]
        ok = True
        self.last_failed = []
        retry = {}
        while rest:
            rest.sort(key=lambda p: min((p["x"] - a) ** 2 + (p["y"] - b) ** 2 for a, b in tpts))
            p = rest.pop(0)
            near = min(tpts, key=lambda t: (p["x"] - t[0]) ** 2 + (p["y"] - t[1]) ** 2)
            starts = [(L, p["x"], p["y"]) for L in p["layers"] if L in layers or p["tht"]]
            path = None
            dist = math.sqrt((p["x"] - near[0]) ** 2 + (p["y"] - near[1]) ** 2)
            for ww in (widths or (w,)):
                tiers = [m for m in margins if m >= dist + 2.5][:2] or [margins[-1]]
                if dist < 2.0:
                    tiers = list(margins[:2])
                for m in tiers:
                    try:
                        path = self.connect(net, starts, tree, ww, clr, layers=layers, via=via, margin=m, lw=lw,
                                            via_cost=via_cost, step=step,
                                            maxexp=5000000 if m <= 10 else (30000000 if m <= 40 else 60000000))
                        break
                    except Fail:
                        continue
                if path is not None:
                    break
            if path is None:
                # thử lại sau khi cây đã lớn hơn (tối đa 2 lần)
                k = (p["ref"], p["num"])
                retry[k] = retry.get(k, 0) + 1
                if retry[k] <= 2 and rest:
                    rest.append(p)
                    if all(retry.get((q["ref"], q["num"]), 0) >= retry[k] for q in rest):
                        if retry[k] >= 2:
                            for q in rest:
                                self.log.append("KHONG NOI DUOC net %d pad %s.%s" % (net, q["ref"], q["num"]))
                            self.last_failed += rest
                            return False
                    else:
                        continue
                    continue
                self.log.append("KHONG NOI DUOC net %d pad %s.%s" % (net, p["ref"], p["num"]))
                self.last_failed.append(p)
                ok = False
                continue
            # cập nhật cây: pad mới + đường vừa đi
            for L in p["layers"]:
                for pts in p["polys"]:
                    self.stamp_poly(tree[L], pts, True)
            for i in range(len(path) - 1):
                L, x, y = path[i]
                L2, x2, y2 = path[i + 1]
                if L == L2:
                    self.stamp_seg(tree[L], x, y, x2, y2, 0.06, True)
                else:
                    for k in range(3):
                        self.stamp_seg(tree[k], x, y, x, y, 0.1, True)
            tpts.append((p["x"], p["y"]))
            tpts += [(x, y) for _, x, y in path[::20]]
        return ok

    def fanout_pad(self, net, pad, zone, w=0.25, clr=0.13, via=(0.45, 0.2, 0.13), n=1, margins=(2.0, 5.0)):
        """Nối 1 pad SMD xuống mặt phẳng: đi một đoạn ngắn trên lớp của pad tới chỗ đặt được via (trong vùng `zone`
        của net trên lớp nguồn; zone=None = mọi nơi). Trả về số via đã đặt."""
        w, clr, via = self._minw(net, w, clr, via)
        L = pad["layers"][0]
        made = 0
        for _ in range(n):
            ok = False
            for m in margins:
                win = self.window([(pad["x"], pad["y"])], m)
                x0, y0, x1, y1 = win
                nxw, nyw = x1 - x0, y1 - y0
                blk, vb = self.masks((net,), win, w / 2 + clr + MARGIN, (L,), via)
                goalm = ~vb & ~blk[L]
                if zone is not None:
                    goalm &= zone[y0:y1, x0:x1]
                if not goalm.any():
                    continue
                goal = [None, None, None]
                goal[L] = goalm.tobytes()
                h = self._hfield(goalm)
                bb = [None, None, None]
                bb[L] = bytearray(blk[L].tobytes())
                cx, cy = cell(pad["x"]) - x0, cell(pad["y"]) - y0
                # xuất phát từ mọi ô của pad (pad lớn: via có thể nằm sát mép pad)
                pm = np.zeros((nyw, nxw), bool)
                for pts in pad["polys"]:
                    self._stamp_poly_win(pm, pts, x0, y0)
                ys, xs = np.nonzero(pm)
                starts = [(L, int(x), int(y), 8) for x, y in list(zip(xs.tolist(), ys.tolist()))[::3]] or [(L, cx, cy, 8)]
                for _, sx, sy, _ in starts:
                    bb[L][sy * nxw + sx] = 0
                nodes = self.astar(nxw, nyw, bb, goal, h, starts, step=1, lw=(1, 1, 1), viablk=None, layers=(L,),
                                   minrun=2)
                if nodes is None:
                    continue
                path = [(l, (x + x0) * G, (y + y0) * G) for l, x, y in nodes]
                self.emit_path(net, path, w, via)
                self.add_via(net, path[-1][1], path[-1][2], via[0], via[1])
                ok = True
                made += 1
                break
            if not ok:
                break
        return made

    def rip(self, net):
        """Gỡ toàn bộ đường + via của 1 net khỏi kết quả và khỏi raster (giữ lại pad)."""
        fx = getattr(self, "fixed", set())
        keep = [t for t in self.tracks if t[0] == net and tuple(t) in fx]      # đồng nguồn cố định: không gỡ
        self.tracks = [t for t in self.tracks if t[0] != net] + keep
        had_via = any(v[0] == net for v in self.vias)
        self.vias = [v for v in self.vias if v[0] != net]
        for L in range(3):
            self.cu[L][self.cu[L] == net] = 0
        for p in self.pads.get(net, []):
            for L in p["layers"]:
                for pts in p["polys"]:
                    self.stamp_poly(self.cu[L], pts, net)
        for t in keep:
            self.stamp_seg(self.cu[t[1]], t[2], t[3], t[4], t[5], t[6] / 2, net)
        if had_via:
            self.hole = self.hole_base.copy()
            for v in self.vias:
                self.stamp_seg(self.hole, v[1], v[2], v[1], v[2], v[4] / 2, True)

    def nets_near(self, x, y, r):
        win = self.window([(x, y)], r)
        out = set()
        for L in range(3):
            out |= set(np.unique(self.cu[L][win[1]:win[3], win[0]:win[2]]).tolist())
        out.discard(0)
        out.discard(KEEP)
        return out

    def components(self, net, margin=1.0):
        """Phân nhóm liên thông của 1 net bằng raster (đường + pad trên từng lớp, nối lớp qua via / pad xuyên lỗ).
        Trả về (win, lab[3], root(L, nhãn) -> id nhóm, {id nhóm: [pad]})."""
        pads = self.pads.get(net, [])
        pts = [(p["x"], p["y"]) for p in pads] + [(t[2], t[3]) for t in self.tracks if t[0] == net] + \
              [(t[4], t[5]) for t in self.tracks if t[0] == net] + [(v[1], v[2]) for v in self.vias if v[0] == net]
        win = self.window(pts, margin)
        x0, y0, x1, y1 = win
        lab = [ndimage.label(self.cu[L][y0:y1, x0:x1] == net, structure=np.ones((3, 3)))[0] for L in range(3)]
        parent = {}

        def find(a):
            while parent.get(a, a) != a:
                parent[a] = parent.get(parent[a], parent[a])
                a = parent[a]
            return a

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[a] = b
        thru = [(v[1], v[2]) for v in self.vias if v[0] == net] + [(p["x"], p["y"]) for p in pads if p["tht"]]
        for x, y in thru:
            ids = [(L, int(lab[L][cell(y) - y0, cell(x) - x0])) for L in range(3)]
            ids = [i for i in ids if i[1]]
            for a_ in ids[1:]:
                union(ids[0], a_)
        groups = {}
        for p in pads:
            L = p["layers"][0]
            groups.setdefault(find((L, int(lab[L][cell(p["y"]) - y0, cell(p["x"]) - x0]))), []).append(p)
        return win, lab, find, groups

    def route_net_strict(self, net, w, clr, layers=(0, 1, 2), via=(0.45, 0.2, 0.13), widths=None, lw=(1.0, 1.3, 1.0),
                         via_cost=1500, margins=(3.0, 10.0, 40.0, 160.0), step=2):
        """Nối mọi pad của 1 net thành MỘT khối liên thông thật sự (kiểm bằng raster sau mỗi lần nối)."""
        self.last_failed = []
        dead = set()
        for _it in range(4 * len(self.pads.get(net, [])) + 4):
            win, lab, find, groups = self.components(net)
            if len(groups) <= 1:
                return True
            x0, y0, x1, y1 = win
            main = max(groups, key=lambda g: (len(groups[g]), -min(p["x"] + p["y"] for p in groups[g])))
            mpts = [(p["x"], p["y"]) for p in groups[main]]
            # mặt nạ đích: mọi ô đồng thuộc nhóm chính
            goal = []
            for L in range(3):
                ids = [l for l in range(1, int(lab[L].max()) + 1) if find((L, l)) == main]
                gm = np.zeros((self.ny, self.nx), bool)
                if ids:
                    gm[y0:y1, x0:x1] = np.isin(lab[L], ids)
                goal.append(gm)
                if ids:
                    ys, xs = np.nonzero(gm[y0:y1:8, x0:x1:8])
                    mpts += [((x * 8 + x0) * G, (y * 8 + y0) * G) for x, y in zip(xs.tolist()[::5], ys.tolist()[::5])]
            cand = []
            for g, pl in groups.items():
                if g == main:
                    continue
                for p in pl:
                    if (p["ref"], p["num"]) in dead:
                        continue
                    dd = min((p["x"] - a) ** 2 + (p["y"] - b) ** 2 for a, b in mpts)
                    cand.append((dd, p["ref"], p["num"], p))
            if not cand:
                return False
            cand.sort(key=lambda c: c[:3])
            dist, _, _, p = cand[0]
            dist = math.sqrt(dist)
            starts = [(L, p["x"], p["y"]) for L in p["layers"]]
            path = None
            for ww in (widths or (w,)):
                tiers = [m for m in margins if m >= dist + 2.5][:2] or [margins[-1]]
                if dist < 2.0:
                    tiers = list(margins[:2])
                for m in tiers:
                    try:
                        path = self.connect(net, starts, goal, ww, clr, layers=layers, via=via, margin=m, lw=lw,
                                            via_cost=via_cost, step=step,
                                            maxexp=5000000 if m <= 10 else (30000000 if m <= 40 else 60000000))
                        break
                    except Fail:
                        continue
                if path is not None:
                    break
            if path is None:
                dead.add((p["ref"], p["num"]))
                self.last_failed.append(p)
                self.log.append("KHONG NOI DUOC net %d pad %s.%s" % (net, p["ref"], p["num"]))
        return False

    def tree_of(self, net):
        """Mặt nạ cây hiện có của net: đường + via đã phát (không gồm pad chưa nối)."""
        tree = [np.zeros((self.ny, self.nx), bool) for _ in range(3)]
        anyt = False
        for n, L, x1, y1, x2, y2, w in self.tracks:
            if n == net:
                self.stamp_seg(tree[L], x1, y1, x2, y2, 0.06, True)
                anyt = True
        for n, x, y, dia, dr in self.vias:
            if n == net:
                for k in range(3):
                    self.stamp_seg(tree[k], x, y, x, y, 0.1, True)
                anyt = True
        return tree if anyt else None

    # ------------------------------------------------------------------ cặp vi sai
    def pair_path(self, nets, ta, tb, w, s, clr, layers=(0, 1), margin=5.0, via=(0.45, 0.2, 0.15), vp=0.7,
                  lv=0.6, lw=(1.0, 1.1, 3.0), via_cost=2500, extra=0.02, maxexp=2500000, extra_pts=(), keep=None,
                  avoid=(), run0=8, minrun=6, keep_all=None):
        """Tìm tim cặp từ đầu ta tới đầu tb. Đầu = dict(T=(x, y), e=(ex, ey) hướng thoát ra, L=lớp).
        Trả về list đỉnh [(L, x, y, kind)] với kind: 'n' thường, 'v' via."""
        half = w + s / 2
        r = half + clr + MARGIN + extra
        win = self.window([ta["T"], tb["T"]] + list(extra_pts), margin)
        x0, y0, x1, y1 = win
        nxw, nyw = x1 - x0, y1 - y0
        blk, vb = self.masks(nets, win, r, layers, via, extra_via_r=vp / 2)
        if avoid:
            # pad của chính 2 net trong cặp nhưng KHÔNG phải đầu cặp (vd. điện trở kéo): coi là vật cản
            for L in range(3):
                am = np.zeros((nyw, nxw), bool)
                hit = False
                for p in avoid:
                    if L in p["layers"]:
                        for pts in p["polys"]:
                            tmp = np.zeros((self.ny, self.nx), bool) if False else None
                            self._stamp_poly_win(am, pts, x0, y0)
                            hit = True
                if hit:
                    d = ndimage.distance_transform_edt(~am) * G
                    if blk[L] is not None:
                        blk[L] = blk[L] | (d < r)
                    vb = vb | (d < via[0] / 2 + clr + MARGIN + vp / 2)
        if keep_all is not None:
            ka = keep_all[y0:y1, x0:x1]
            for L in range(3):
                if blk[L] is not None:
                    blk[L] = blk[L] | ka
            vb = vb | ka
        if keep is not None and blk[0] is not None:
            blk[0] = blk[0] | keep[y0:y1, x0:x1]
        da = _dir_index(ta["e"])
        db = _dir_index((-tb["e"][0], -tb["e"][1]))
        ax, ay = cell(ta["T"][0]) - x0, cell(ta["T"][1]) - y0
        bx, by = cell(tb["T"][0]) - x0, cell(tb["T"][1]) - y0
        gm = np.zeros((nyw, nxw), bool)
        gm[by, bx] = True
        goal = [None, None, None]
        goal[tb["L"]] = gm.tobytes()
        h = self._hfield(gm)
        bb = [None if b is None else bytearray(b.tobytes()) for b in blk]
        # mở lối ra/vào dọc hướng thoát (đoạn này nằm giữa các pad lân cận, đã được kiểm tra hình học riêng)
        for (cx, cy, d, L) in ((ax, ay, da, ta["L"]), (bx, by, (db + 4) & 7, tb["L"])):
            for k in range(0, int(0.45 / G) + 1):
                xx, yy = cx + DX[d] * k, cy + DY[d] * k
                if 0 <= xx < nxw and 0 <= yy < nyw and bb[L] is not None:
                    bb[L][yy * nxw + xx] = 0
        sx, sy = ax + DX[da] * run0, ay + DY[da] * run0
        for k in range(run0 + 1):
            if bb[ta["L"]] is not None and bb[ta["L"]][(ay + DY[da] * k) * nxw + ax + DX[da] * k]:
                raise Fail("cap vi sai: loi ra bi chan")
        nodes = self.astar(nxw, nyw, bb, goal, h, [(ta["L"], sx, sy, da)], step=1, lw=lw, via_cost=via_cost,
                           viablk=vb.tobytes(), gdir=db, pairvia=int(round(lv / G)), turn=60, layers=layers,
                           maxexp=maxexp, minrun=minrun)
        if nodes is None:
            raise Fail("cap vi sai: khong tim duoc duong")
        nodes = [(ta["L"], ax, ay)] + nodes
        # nén thành đỉnh; phát hiện via (đổi lớp giữa 2 nút cách nhau 2*lv)
        verts = []
        for i, (L, x, y) in enumerate(nodes):
            X, Y = (x + x0) * G, (y + y0) * G
            if i and nodes[i - 1][0] != L:
                pl, px, py = nodes[i - 1]
                PX, PY = (px + x0) * G, (py + y0) * G
                verts.append((pl, (PX + X) / 2, (PY + Y) / 2, "v"))
                verts.append((L, (PX + X) / 2, (PY + Y) / 2, "w"))
            verts.append((L, X, Y, "n"))
        return verts

    def pair_emit(self, np_, nn, verts, ta, tb, w, s, via=(0.45, 0.2), vp=0.7):
        """Dựng 2 đường song song từ tim cặp. Trả về (polyP, polyN) dạng [(L, x, y)]."""
        # gộp đỉnh thẳng hàng (giữ đỉnh via)
        pts = []
        for v in verts:
            if pts and v[3] == "n" and pts[-1][3] == "n" and pts[-1][0] == v[0] and \
                    abs(pts[-1][1] - v[1]) < 1e-6 and abs(pts[-1][2] - v[2]) < 1e-6:
                continue
            if len(pts) >= 2 and v[3] == "n" and pts[-1][3] == "n" and pts[-2][3] == "n" and pts[-2][0] == pts[-1][0] == v[0]:
                ax, ay = pts[-1][1] - pts[-2][1], pts[-1][2] - pts[-2][2]
                bx, by = v[1] - pts[-1][1], v[2] - pts[-1][2]
                if abs(ax * by - ay * bx) < 1e-9 and ax * bx + ay * by > 0:
                    pts[-1] = v
                    continue
            pts.append(v)
        e = ta["e"]
        nx_, ny_ = -e[1], e[0]
        side_p = 1 if ((ta["P"][0] - ta["T"][0]) * nx_ + (ta["P"][1] - ta["T"][1]) * ny_) > 0 else -1
        out = {}
        for sign, net in ((side_p, np_), (-side_p, nn)):
            poly = []
            n = len(pts)
            for i, (L, x, y, kind) in enumerate(pts):
                # hướng đoạn trước / sau
                def seg_dir(a, b):
                    dx, dy = b[1] - a[1], b[2] - a[2]
                    l = math.hypot(dx, dy)
                    return (dx / l, dy / l) if l > 1e-9 else None
                dprev = seg_dir(pts[i - 1], pts[i]) if i > 0 else None
                dnext = seg_dir(pts[i], pts[i + 1]) if i < n - 1 else None
                if dprev is None:
                    dprev = dnext
                if dnext is None:
                    dnext = dprev
                if kind in ("v", "w"):
                    hs = vp / 2
                    poly.append((L, x + sign * hs * (-dprev[1]), y + sign * hs * dprev[0]))
                    continue
                hs = s / 2 + w / 2
                n1 = (-dprev[1], dprev[0])
                n2 = (-dnext[1], dnext[0])
                den = 1 + n1[0] * n2[0] + n1[1] * n2[1]
                ox, oy = (n1[0] + n2[0]) / den, (n1[1] + n2[1]) / den
                poly.append((L, x + sign * hs * ox, y + sign * hs * oy))
            out[net] = poly
        return out[np_], out[nn], side_p

    # ------------------------------------------------------------------ kiểm tra đoạn thẳng
    def seg_free(self, nets, L, x1, y1, x2, y2, r):
        win = self.window([(x1, y1), (x2, y2)], r + 0.2)
        d = self.dist_other(L, nets, win, int(1.0 / G))
        x0, y0 = win[0], win[1]
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / (G / 2)) + 1)
        for k in range(n + 1):
            t = k / n
            cx, cy = cell(x1 + (x2 - x1) * t) - x0, cell(y1 + (y2 - y1) * t) - y0
            if d[cy, cx] < r:
                return False
        return True

    def net_length(self, net):
        return sum(math.hypot(t[4] - t[2], t[5] - t[3]) for t in self.tracks if t[0] == net)

    def tune(self, short, other, target_extra, w, clr, hmax=0.3, flat=0.3, min_len=0.9):
        """Thêm gờ (bump) vào đường của net `short` để dài thêm target_extra mm. Gờ lồi ra phía xa net `other`."""
        if target_extra < 0.02:
            return 0.0
        per_max = 2 * hmax * (math.sqrt(2) - 1)
        segs = [t for t in self.tracks if t[0] == short and math.hypot(t[4] - t[2], t[5] - t[3]) >= min_len]
        segs.sort(key=lambda t: -math.hypot(t[4] - t[2], t[5] - t[3]))
        others = [t for t in self.tracks if t[0] == other]
        remaining = target_extra
        for t in segs:
            if remaining < 0.02:
                break
            net, L, x1, y1, x2, y2, tw = t
            ln = math.hypot(x2 - x1, y2 - y1)
            ux, uy = (x2 - x1) / ln, (y2 - y1) / ln
            # phía xa đối tác: dựa trên đoạn của net kia gần trung điểm nhất
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            best = None
            for o in others:
                if o[1] != L:
                    continue
                ox, oy = (o[2] + o[4]) / 2, (o[3] + o[5]) / 2
                # khoảng cách từ trung điểm tới đoạn o
                vx, vy = o[4] - o[2], o[5] - o[3]
                l2 = vx * vx + vy * vy
                tt = max(0, min(1, ((mx - o[2]) * vx + (my - o[3]) * vy) / l2)) if l2 else 0
                qx, qy = o[2] + tt * vx, o[3] + tt * vy
                dd = math.hypot(mx - qx, my - qy)
                if best is None or dd < best[0]:
                    best = (dd, qx, qy)
            nxo, nyo = -uy, ux
            sides = [(nxo, nyo), (-nxo, -nyo)]
            if best is not None and best[0] <= 1.0:
                if (best[1] - mx) * nxo + (best[2] - my) * nyo > 0:
                    sides = [(-nxo, -nyo)]
                else:
                    sides = [(nxo, nyo)]
            nb_max = int((ln - 0.3) / (2 * hmax + 2 * flat))
            if nb_max < 1:
                continue
            nb = min(nb_max, int(math.ceil(remaining / per_max)))
            hgt = min(hmax, (remaining / nb) / (2 * (math.sqrt(2) - 1)))
            pitch = 2 * hgt + 2 * flat
            start = (ln - nb * pitch) / 2
            r = tw / 2 + clr + MARGIN
            okside = None
            for nxo, nyo in sides:
                a0 = (x1 + ux * start + nxo * hgt, y1 + uy * start + nyo * hgt)
                a1 = (x1 + ux * (start + nb * pitch) + nxo * hgt, y1 + uy * (start + nb * pitch) + nyo * hgt)
                if self.seg_free((short,), L, a0[0], a0[1], a1[0], a1[1], r + (0.1 if len(sides) == 2 else 0)):
                    okside = (nxo, nyo)
                    break
            if okside is None:
                continue
            nxo, nyo = okside
            pts = [(x1, y1)]
            for k in range(nb):
                b0 = start + k * pitch + flat / 2
                for dd, hh in ((0, 0), (hgt, hgt), (hgt + flat, hgt), (2 * hgt + flat, 0)):
                    pts.append((x1 + ux * (b0 + dd) + nxo * hh, y1 + uy * (b0 + dd) + nyo * hh))
            pts.append((x2, y2))
            self.tracks.remove(t)
            for a, b in zip(pts, pts[1:]):
                self.add_track(net, L, a[0], a[1], b[0], b[1], tw)
            remaining -= nb * 2 * hgt * (math.sqrt(2) - 1)
        return target_extra - remaining

    # ------------------------------------------------------------------ ảnh gỡ lỗi
    def png(self, path, box=None, scale=1):
        from PIL import Image
        x0, y0, x1, y1 = (0, 0, self.nx, self.ny) if box is None else self.window([box[:2], box[2:]], 0)
        img = np.zeros((y1 - y0, x1 - x0, 3), np.uint8) + 18
        for L, col in ((2, (60, 90, 255)), (1, (60, 200, 90)), (0, (235, 70, 60))):
            m = self.cu[L][y0:y1, x0:x1]
            img[(m != 0) & (m != KEEP)] = col
        img[self.smd[y0:y1, x0:x1] & (self.cu[0][y0:y1, x0:x1] != 0)] = (150, 40, 40)
        img[self.hole[y0:y1, x0:x1]] = (255, 255, 255)
        img[self.frame[y0:y1, x0:x1]] = (90, 90, 0)
        im = Image.fromarray(img)
        if scale != 1:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.NEAREST)
        im.save(path)


def _dir_index(e):
    ang = math.atan2(e[1], e[0])
    return int(round(ang / (math.pi / 4))) & 7
