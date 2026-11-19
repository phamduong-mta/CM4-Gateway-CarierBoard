"""Bộ sinh schematic KiCad 10 (.kicad_sch) theo kiểu "nhãn net".

Mỗi chân linh kiện được nối một đoạn dây ngắn và gắn nhãn net (hoặc ký hiệu nguồn).
UUID sinh tất định (uuid5) để sinh lại file không làm đổi liên kết schematic <-> PCB.
"""
import math
import os
import re
import uuid

from sx import Q, dump, esc, find, findall, parse

KICAD_SYM_DIR = "/usr/share/kicad/symbols"
NS = uuid.UUID("5f1c7a50-3c4e-4b7e-9d53-c0a4c3a7e001")
SCH_VERSION = "20260306"
G = 2.54          # lưới 100 mil
FONT = ["effects", ["font", ["size", 1.27, 1.27]]]


def uid(*key):
    return Q(str(uuid.uuid5(NS, "/".join(str(k) for k in key))))


def effects(size=1.27, justify=None, hide=False, bold=False):
    font = ["font", ["size", size, size]]
    if bold:
        font.append(["bold", "yes"])
    e = ["effects", font]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


# --------------------------------------------------------------------------- symbols
class LibSym:
    def __init__(self, lib_id, sexpr, ref_prefix="U"):
        self.lib_id = lib_id
        self.sexpr = sexpr
        self.ref_prefix = ref_prefix
        self.pins = []          # dict(number,name,x,y,angle,unit,etype)
        self.props = {}         # tên -> (x, y, angle)
        self.bbox = {}          # unit -> (x1,y1,x2,y2) toạ độ thư viện
        self._scan()

    def _scan(self):
        base = self.lib_id.split(":")[1]
        for p in findall(self.sexpr, "property"):
            at = find(p, "at")
            self.props[str(p[1])] = (float(at[1]), float(at[2]), float(at[3]))
            if p[1] == "Reference":
                self.ref_prefix = str(p[2])
        self.units = set()
        for sub in findall(self.sexpr, "symbol"):
            m = re.match(re.escape(base) + r"_(\d+)_(\d+)$", str(sub[1]))
            unit = int(m.group(1)) if m else 0
            if unit:
                self.units.add(unit)
            for pin in findall(sub, "pin"):
                at = find(pin, "at")
                self.pins.append(dict(
                    number=str(find(pin, "number")[1]), name=str(find(pin, "name")[1]),
                    x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                    unit=unit, etype=str(pin[1]),
                    hidden=find(pin, "hide") is not None))
        if not self.units:
            self.units = {1}

    def unit_pins(self, unit):
        return [p for p in self.pins if p["unit"] in (0, unit)]


_stock_cache = {}


def _slice_symbol(text, name):
    key = '\n\t(symbol "%s"\n' % name
    i = text.find(key)
    if i < 0:
        raise KeyError(name)
    i += 2
    depth = 0
    j = i
    in_str = False
    while True:
        c = text[j]
        if in_str:
            if c == "\\":
                j += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return text[i:j + 1]


_lib_text = {}


def stock(lib_id):
    """Lấy symbol từ thư viện KiCad cài sẵn, đã gộp 'extends', đổi tên thành Lib:Name."""
    if lib_id in _stock_cache:
        return _stock_cache[lib_id]
    lib, name = lib_id.split(":")
    if lib not in _lib_text:
        with open(os.path.join(KICAD_SYM_DIR, lib + ".kicad_sym"), encoding="utf-8") as f:
            _lib_text[lib] = f.read()
    sym = parse(_slice_symbol(_lib_text[lib], name))
    ext = find(sym, "extends")
    if ext is not None:
        parent_name = str(ext[1])
        parent = parse(_slice_symbol(_lib_text[lib], parent_name))
        child_props = {str(p[1]): p for p in findall(sym, "property")}
        merged = []
        for item in parent:
            if isinstance(item, list) and item[0] == "property":
                merged.append(child_props.pop(str(item[1]), item))
            elif isinstance(item, list) and item[0] == "symbol":
                item[1] = Q(str(item[1]).replace(parent_name + "_", name + "_", 1))
                merged.append(item)
            else:
                merged.append(item)
        # thuộc tính chỉ có ở con: chèn trước các symbol con
        idx = next(i for i, it in enumerate(merged) if isinstance(it, list) and it[0] == "symbol")
        for p in child_props.values():
            merged.insert(idx, p)
            idx += 1
        sym = merged
    sym[1] = Q(lib_id)
    ls = LibSym(lib_id, sym)
    _stock_cache[lib_id] = ls
    return ls


def _prop(name, value, x, y, hide=False, justify=None, angle=0):
    return ["property", Q(name), esc(value), ["at", x, y, angle], effects(hide=hide, justify=justify)]


LIB = "cm4gw"
custom_symbols = {}     # name -> LibSym (ghi ra hardware/lib/cm4-gateway.kicad_sym)


def box(name, units, ref="U", desc="", pin_len=2.54, min_width=10.16):
    """Tạo symbol hình hộp. units = [dict(left=[...], right=[...]), ...]
    Mỗi chân: (số, tên, kiểu điện) hoặc None để chừa một khoảng trống."""
    if name in custom_symbols:
        return custom_symbols[name]
    sym = ["symbol", Q("%s:%s" % (LIB, name)),
           ["pin_names", ["offset", 1.016]],
           ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"]]
    subs = []
    first_bbox = None
    for ui, u in enumerate(units, start=1):
        left = u.get("left", [])
        right = u.get("right", [])
        rows = max(len(left), len(right), 1)
        lw = max([len(p[1]) for p in left if p] + [0])
        rw = max([len(p[1]) for p in right if p] + [0])
        width = max(min_width, math.ceil(((lw + rw) * 1.1 + 6) / 5.08) * 5.08)
        hw = width / 2
        height = (rows + 1) * G
        top = math.floor(height / 2 / G) * G
        bot = top - height
        sub = ["symbol", Q("%s_%d_1" % (name, ui)),
               ["rectangle", ["start", -hw, top], ["end", hw, bot],
                ["stroke", ["width", 0.254], ["type", "default"]],
                ["fill", ["type", "background"]]]]
        for side, pins in (("L", left), ("R", right)):
            for i, p in enumerate(pins):
                if p is None:
                    continue
                num, pname, etype = p
                y = top - (i + 1) * G
                if side == "L":
                    at = ["at", -hw - pin_len, y, 0]
                else:
                    at = ["at", hw + pin_len, y, 180]
                sub.append(["pin", etype, "line", at, ["length", pin_len],
                            ["name", esc(pname), FONT], ["number", Q(str(num)), FONT]])
        subs.append(sub)
        if first_bbox is None:
            first_bbox = (-hw, top, hw, bot)
        if ui == 1:
            sym += [
                _prop("Reference", ref, -hw, top + 1.27, justify="left bottom"),
                _prop("Value", name, -hw, bot - 1.27, justify="left top"),
                _prop("Footprint", "", 0, 0, hide=True),
                _prop("Datasheet", "", 0, 0, hide=True),
                _prop("Description", desc, 0, 0, hide=True),
            ]
    sym += subs
    ls = LibSym("%s:%s" % (LIB, name), sym, ref)
    for ui, u in enumerate(units, start=1):
        sub = subs[ui - 1]
        r = find(sub, "rectangle")
        ls.bbox[ui] = (float(find(r, "start")[1]), float(find(r, "start")[2]),
                       float(find(r, "end")[1]), float(find(r, "end")[2]))
    custom_symbols[name] = ls
    return ls


def power_symbol(net):
    """Ký hiệu nguồn riêng cho từng rail (net toàn cục = giá trị Value)."""
    name = "PWR_" + re.sub(r"[^A-Za-z0-9_+]", "_", net)
    if name in custom_symbols:
        return custom_symbols[name]
    gnd = net.startswith("GND") or net == "CHASSIS"
    st = ["stroke", ["width", 0], ["type", "default"]]
    nofill = ["fill", ["type", "none"]]
    if net == "CHASSIS":
        gfx = [["polyline", ["pts", ["xy", 0, 0], ["xy", 0, -1.27]], st, nofill],
               ["polyline", ["pts", ["xy", -1.27, -1.27], ["xy", 1.27, -1.27]], st, nofill],
               ["polyline", ["pts", ["xy", -1.27, -1.27], ["xy", -1.905, -2.54]], st, nofill],
               ["polyline", ["pts", ["xy", 0, -1.27], ["xy", -0.635, -2.54]], st, nofill],
               ["polyline", ["pts", ["xy", 1.27, -1.27], ["xy", 0.635, -2.54]], st, nofill]]
        vy, pin_angle = -4.2, 270
    elif gnd:
        gfx = [["polyline", ["pts", ["xy", 0, 0], ["xy", 0, -1.27], ["xy", 1.27, -1.27],
                             ["xy", 0, -2.54], ["xy", -1.27, -1.27], ["xy", 0, -1.27]], st, nofill]]
        vy, pin_angle = -4.2, 270
    else:
        gfx = [["polyline", ["pts", ["xy", 0, 0], ["xy", 0, 1.27]], st, nofill],
               ["polyline", ["pts", ["xy", -1.27, 1.27], ["xy", 1.27, 1.27]],
                ["stroke", ["width", 0.3], ["type", "default"]], nofill]]
        vy, pin_angle = 2.6, 90
    sym = ["symbol", Q("%s:%s" % (LIB, name)), ["power", "global"],
           ["pin_numbers", ["hide", "yes"]], ["pin_names", ["offset", 0], ["hide", "yes"]],
           ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
           _prop("Reference", "#PWR", 0, 0, hide=True),
           _prop("Value", net, 0, vy),
           _prop("Footprint", "", 0, 0, hide=True),
           _prop("Datasheet", "", 0, 0, hide=True),
           _prop("Description", "Ky hieu nguon: net toan cuc \"%s\"" % net, 0, 0, hide=True),
           ["symbol", Q(name + "_0_1")] + gfx,
           ["symbol", Q(name + "_1_1"),
            ["pin", "power_in", "line", ["at", 0, 0, pin_angle], ["length", 0],
             ["name", Q(""), FONT], ["number", Q("1"), FONT]]]]
    ls = LibSym("%s:%s" % (LIB, name), sym, "#PWR")
    ls.is_gnd = gnd
    ls.value_y = vy
    custom_symbols[name] = ls
    return ls


def rot_point(px, py, rot):
    """Điểm thư viện (trục y hướng lên) -> độ lệch trên bản vẽ (trục y hướng xuống)."""
    r = int(rot) % 360
    if r == 0:
        return px, -py
    if r == 90:
        return -py, -px
    if r == 180:
        return -px, py
    return py, px


def rot_dir(angle, rot):
    """Hướng từ điểm nối của chân đi RA NGOÀI thân linh kiện, trên bản vẽ."""
    a = math.radians(angle)
    ox, oy = -round(math.cos(a)), -round(math.sin(a))
    return rot_point(ox, oy, rot)


# --------------------------------------------------------------------------- sheet
class Inst:
    def __init__(self, sheet, sym, ref, value, at, rot, unit, fields, dnp):
        self.sheet, self.sym, self.ref, self.value = sheet, sym, ref, value
        self.at, self.rot, self.unit = at, rot, unit
        self.fields, self.dnp = fields, dnp
        self.done = set()

    def _find(self, key):
        key = str(key)
        pins = self.sym.unit_pins(self.unit)
        m = [p for p in pins if p["number"] == key]
        if not m:
            m = [p for p in pins if p["name"] == key]
        if not m:
            raise KeyError("%s: khong co chan %r (unit %d)" % (self.ref, key, self.unit))
        return m

    def pinpos(self, pin):
        dx, dy = rot_point(pin["x"], pin["y"], self.rot)
        ox, oy = rot_dir(pin["angle"], self.rot)
        return self.at[0] + dx, self.at[1] + dy, ox, oy

    def net(self, mapping=None, stub=G, **kw):
        """Gán net cho chân. Khoá: số chân hoặc tên chân (tên trùng -> mọi chân cùng tên)."""
        mapping = dict(mapping or {})
        mapping.update(kw)
        for key, net in mapping.items():
            for pin in self._find(key):
                x, y, ox, oy = self.pinpos(pin)
                self.done.add(pin["number"])
                if net is None or net == "NC":
                    self.sheet.no_connect(x, y)
                else:
                    self.sheet.attach(x, y, ox, oy, net, stub)
        return self

    def nc(self, *keys):
        return self.net({k: "NC" for k in keys})

    def unassigned(self):
        return [p for p in self.sym.unit_pins(self.unit) if p["number"] not in self.done]


class Sheet:
    def __init__(self, design, name, filename, title, paper="A3", instances=None):
        self.design, self.name, self.filename, self.title, self.paper = design, name, filename, title, paper
        self.uuid = uid("sheetfile", filename)
        # instances: list[(sheet_symbol_uuid, n)]; root không có
        self.instances = instances or []
        self.items = []
        self.insts = []
        self.used = {}
        self.pwr_count = 0
        self.seq = 0
        self.hier_pins = {}     # tên -> shape (cho sheet đa thể hiện)

    # ---- phần tử cơ bản
    def _id(self, kind):
        self.seq += 1
        return uid(self.filename, kind, self.seq)

    def wire(self, x1, y1, x2, y2):
        self.items.append(["wire", ["pts", ["xy", x1, y1], ["xy", x2, y2]],
                           ["stroke", ["width", 0], ["type", "default"]], ["uuid", self._id("w")]])

    def no_connect(self, x, y):
        self.items.append(["no_connect", ["at", x, y], ["uuid", self._id("nc")]])

    def junction(self, x, y):
        self.items.append(["junction", ["at", x, y], ["diameter", 0], ["color", 0, 0, 0, 0],
                           ["uuid", self._id("j")]])

    def text(self, s, x, y, size=1.8, bold=False, justify="left bottom"):
        self.items.append(["text", esc(s), ["exclude_from_sim", "no"], ["at", x, y, 0],
                           effects(size, justify, bold=bold), ["uuid", self._id("t")]])

    def frame(self, x1, y1, x2, y2, title=None):
        self.items.append(["rectangle", ["start", x1, y1], ["end", x2, y2],
                           ["stroke", ["width", 0.15], ["type", "dash"]],
                           ["fill", ["type", "none"]], ["uuid", self._id("r")]])
        if title:
            self.text(title, x1 + 1.5, y1 + 4.2, size=2.2, bold=True)

    def label(self, x, y, ox, oy, net):
        """Đặt nhãn/ ký hiệu nguồn tại (x,y), hướng ra ngoài (ox,oy)."""
        d = self.design
        if net in d.power_nets:
            ps = power_symbol(net)
            if ps.is_gnd:
                rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[(ox, oy)]
            else:
                rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[(ox, oy)]
            self.pwr_count += 1
            self._emit_symbol(ps, "#PWR{n}%03d" % self.pwr_count, net, (x, y), rot, 1, {}, False, power=True)
            return
        ang, just = {(1, 0): (0, "left"), (-1, 0): (180, "right"),
                     (0, -1): (90, "left"), (0, 1): (270, "right")}[(ox, oy)]
        if net.startswith("."):          # nhãn cục bộ trong sheet
            self.items.append(["label", esc(net[1:]), ["at", x, y, ang],
                               effects(justify=just + " bottom"), ["uuid", self._id("l")]])
        elif net.startswith("^"):        # nhãn phân cấp (sheet đa thể hiện)
            nm = net[1:]
            self.hier_pins.setdefault(nm, "passive")
            self.items.append(["hierarchical_label", esc(nm), ["shape", "passive"], ["at", x, y, ang],
                               effects(justify=just), ["uuid", self._id("h")]])
        else:
            d.global_nets.add(net)
            self.items.append(["global_label", esc(net), ["shape", "passive"], ["at", x, y, ang],
                               effects(justify=just), ["uuid", self._id("g")]])

    def attach(self, x, y, ox, oy, net, stub=G):
        x2, y2 = x + ox * stub, y + oy * stub
        if stub:
            self.wire(x, y, x2, y2)
        self.label(x2, y2, ox, oy, net)

    # ---- linh kiện
    def add(self, sym, ref, value, at, rot=0, unit=1, fp="", lcsc="", mpn="", desc=None,
            dnp=False, **extra):
        if isinstance(sym, str):
            sym = stock(sym)
        fields = dict(Footprint=fp, LCSC=lcsc, MPN=mpn)
        if desc:
            fields["Description"] = desc
        fields.update(extra)
        inst = Inst(self, sym, ref, value, at, rot, unit, fields, dnp)
        self.insts.append(inst)
        self._emit_symbol(sym, ref, value, at, rot, unit, fields, dnp)
        return inst

    def _emit_symbol(self, sym, ref, value, at, rot, unit, fields, dnp, power=False):
        self.used[sym.lib_id] = sym
        x, y = at
        key = ("sym", ref, unit, x, y)
        s = ["symbol", ["lib_id", Q(sym.lib_id)], ["at", x, y, rot], ["unit", unit],
             ["exclude_from_sim", "no"],
             ["in_bom", "no" if (power or fields.get("_nobom")) else "yes"], ["on_board", "yes"],
             ["dnp", "yes" if dnp else "no"],
             ["uuid", uid(self.filename, *key)]]
        ref0 = self._ref(ref, self.instances[0][1] if self.instances else 0)
        # vị trí Reference / Value
        if power:
            vy = sym.value_y
            dx, dy = rot_point(0, vy, rot)
            just = None
            if rot in (90, 270):          # ký hiệu nằm ngang: đẩy chữ ra xa theo độ dài, canh giữa
                sgn = 1 if dx > 0 else -1
                dx = sgn * (abs(dx) + 0.42 * len(value))
            s.append(["property", Q("Reference"), Q(ref0), ["at", x, y, 0], effects(hide=True)])
            s.append(["property", Q("Value"), esc(value), ["at", x + dx, y + dy, 90 if rot in (90, 270) else 0],
                      effects(1.0, just)])
        else:
            rx, ry, vx, vy, rj, vj = self._field_pos(sym, unit, x, y, rot)
            fa = 90 if rot in (90, 270) else 0      # bù góc xoay của symbol để chữ luôn nằm ngang
            s.append(["property", Q("Reference"), Q(ref0), ["at", rx, ry, fa], effects(justify=rj)])
            s.append(["property", Q("Value"), esc(value), ["at", vx, vy, fa], effects(justify=vj)])
        for name in ("Footprint", "Datasheet", "Description", "LCSC", "MPN"):
            val = fields.get(name, "")
            if name in ("Datasheet",) and not val:
                val = "~"
            if name == "Description" and not val:
                d = find([p for p in findall(sym.sexpr, "property") if p[1] == "Description"] or [[]], "x")
                dp = [p for p in findall(sym.sexpr, "property") if p[1] == "Description"]
                val = str(dp[0][2]) if dp else ""
            s.append(["property", Q(name), esc(val) if not isinstance(val, Q) else val,
                      ["at", x, y, 0], effects(hide=True)])
        for name, val in fields.items():
            if name not in ("Footprint", "Datasheet", "Description", "LCSC", "MPN", "_nobom"):
                s.append(["property", Q(name), esc(val), ["at", x, y, 0], effects(hide=True)])
        inst = ["instances", ["project", Q(self.design.project)]]
        for path, n in self._paths():
            inst[1].append(["path", Q(path), ["reference", Q(self._ref(ref, n))], ["unit", unit]])
        s.append(inst)
        self.items.append(s)

    def _field_pos(self, sym, unit, x, y, rot):
        if unit in sym.bbox:
            x1, y1, x2, y2 = sym.bbox[unit]
            return x + x1, y - y1 - 1.0, x + x1, y - y2 + 1.0, "left bottom", "left top"
        pins = sym.unit_pins(unit)
        if rot == 0 and len(pins) > 3 and "Reference" in sym.props:
            # symbol thư viện đặt thẳng: dùng vị trí trường do thư viện định sẵn
            (ax, ay, _), (bx, by, _) = sym.props["Reference"], sym.props["Value"]
            return x + ax, y - ay, x + bx, y - by, "left", "left"
        if len(pins) == 2 and abs(pins[0]["x"] - pins[1]["x"]) + abs(pins[0]["y"] - pins[1]["y"]) > 5:
            # linh kiện 2 chân: xét hướng sau khi xoay
            (ax, ay), (bx, by) = [rot_point(p["x"], p["y"], rot) for p in pins]
            if abs(ax - bx) > abs(ay - by):      # nằm ngang
                return x, y - 2.3, x, y + 2.3, "bottom", "top"
            return x + 2.0, y - 1.0, x + 2.0, y + 1.0, "left bottom", "left top"
        ys = [rot_point(p["x"], p["y"], rot)[1] for p in pins] or [0]
        xs = [rot_point(p["x"], p["y"], rot)[0] for p in pins] or [0]
        return x + max(xs) + 1.0, y + min(ys) - 0.5, x + max(xs) + 1.0, y + min(ys) + 2.0, "left bottom", "left top"

    def _ref(self, ref, n):
        return ref.replace("{n}", str(n))

    def _paths(self):
        root = "/" + self.design.root_uuid
        if not self.instances:
            return [(root, 0)]
        return [(root + "/" + su, n) for su, n in self.instances]

    def part2(self, sym, ref, value, x, y, a, b, fp="", lcsc="", mpn="", dnp=False, rot=None, stub=G, **kw):
        """Linh kiện 2 chân đặt nằm ngang: chân 1 bên trái (net a), chân 2 bên phải (net b)."""
        if isinstance(sym, str):
            sym = stock(sym)
        pins = sym.unit_pins(1)
        if rot is None:
            p1 = next(p for p in pins if p["number"] == "1")
            rot = 90 if abs(p1["y"]) > abs(p1["x"]) else 0
            if rot_point(p1["x"], p1["y"], rot)[0] > 0:
                rot += 180
        inst = self.add(sym, ref, value, (x, y), rot=rot, fp=fp, lcsc=lcsc, mpn=mpn, dnp=dnp, **kw)
        inst.net({"1": a, "2": b}, stub=stub)
        return inst

    # ---- ghi file
    def render(self):
        d = self.design
        root = ["kicad_sch", ["version", SCH_VERSION], ["generator", Q("cm4gw_gen")],
                ["generator_version", Q("10.0")], ["uuid", self.uuid], ["paper", Q(self.paper)],
                ["title_block", ["title", esc(self.title)], ["date", Q(d.date)], ["rev", Q(d.rev)],
                 ["company", esc(d.company)], ["comment", 1, esc(d.project_title)]]]
        libs = ["lib_symbols"]
        for lib_id in sorted(self.used):
            libs.append(self.used[lib_id].sexpr)
        root.append(libs)
        root += self.items
        if self is d.root:
            root.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
        root.append(["embedded_fonts", "no"])
        return dump(root) + "\n"


class Design:
    def __init__(self, project, title, rev, date, company, outdir):
        self.project, self.project_title, self.rev, self.date, self.company = project, title, rev, date, company
        self.outdir = outdir
        self.power_nets = set()
        self.global_nets = set()
        self.sheets = []
        self.root = Sheet(self, "root", project + ".kicad_sch", title, paper="A3")
        self.root_uuid = str(self.root.uuid)
        self.sheets.append(self.root)
        self.page = 1

    def sheet_symbol_uuid(self, name):
        return str(uid("sheetsym", name))

    def new_sheet(self, name, filename, title, paper="A3", instance_numbers=None):
        """instance_numbers: None -> 1 thể hiện (tên = name); list[(tên thể hiện, n)] -> đa thể hiện."""
        if instance_numbers is None:
            inst = [(self.sheet_symbol_uuid(name), 0)]
        else:
            inst = [(self.sheet_symbol_uuid(nm), n) for nm, n in instance_numbers]
        sh = Sheet(self, name, filename, title, paper, inst)
        self.sheets.append(sh)
        return sh

    def place_sheet(self, sheet, inst_name, x, y, w, h, pins=None):
        """Đặt ký hiệu sheet trên trang gốc. pins: list[(tên, cạnh 'L'/'R', net toàn cục)]."""
        self.page += 1
        su = Q(self.sheet_symbol_uuid(inst_name))
        s = ["sheet", ["at", x, y], ["size", w, h], ["exclude_from_sim", "no"], ["in_bom", "yes"],
             ["on_board", "yes"], ["dnp", "no"],
             ["stroke", ["width", 0.1524], ["type", "solid"]],
             ["fill", ["color", 255, 255, 194, 1.0]],
             ["uuid", su],
             ["property", Q("Sheetname"), esc(inst_name), ["at", x, y - 0.7, 0],
              effects(1.5, "left bottom")],
             ["property", Q("Sheetfile"), Q(sheet.filename), ["at", x, y + h + 0.7, 0],
              effects(1.0, "left top")]]
        nl = nr = 0
        for nm, side, net in (pins or []):
            if side == "L":
                nl += 1
                px, py, ang, just, ox = x, y + nl * G, 180, "left", -1
            else:
                nr += 1
                px, py, ang, just, ox = x + w, y + nr * G, 0, "right", 1
            s.append(["pin", esc(nm), "passive", ["at", px, py, ang],
                      ["uuid", uid("sheetpin", inst_name, nm)], effects(justify=just)])
            if net is None:
                self.root.no_connect(px, py)
            else:
                self.root.attach(px, py, ox, 0, net, G)
        s.append(["instances", ["project", Q(self.project),
                                ["path", Q("/" + self.root_uuid), ["page", Q(str(self.page))]]]])
        self.root.items.append(s)

    def write(self):
        for sh in self.sheets:
            with open(os.path.join(self.outdir, sh.filename), "w", encoding="utf-8") as f:
                f.write(sh.render())

    def write_symbol_lib(self, path):
        lib = ["kicad_symbol_lib", ["version", "20251024"], ["generator", Q("cm4gw_gen")],
               ["generator_version", Q("10.0")]]
        for name in sorted(custom_symbols):
            sym = parse(dump(custom_symbols[name].sexpr))   # bản sao
            sym[1] = Q(name)
            lib.append(sym)
        with open(path, "w", encoding="utf-8") as f:
            f.write(dump(lib) + "\n")
