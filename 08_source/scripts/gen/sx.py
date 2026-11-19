"""S-expression tối giản cho file KiCad: parse / dump.

- list  -> list Python
- chuỗi có nháy -> đối tượng Q (giữ nguyên nháy khi ghi lại)
- atom  -> str
"""


class Q(str):
    """Chuỗi được đặt trong dấu nháy kép khi ghi ra file."""
    __slots__ = ()


def parse(text):
    pos = 0
    n = len(text)
    stack = [[]]
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
            pos += 1
        elif c == ")":
            stack.pop()
            pos += 1
        elif c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    buf.append(text[pos:pos + 2])
                    pos += 2
                else:
                    buf.append(text[pos])
                    pos += 1
            pos += 1
            stack[-1].append(Q("".join(buf)))
        else:
            start = pos
            while pos < n and text[pos] not in " \t\r\n()":
                pos += 1
            stack[-1].append(text[start:pos])
    return stack[0][0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a + '"'
    if isinstance(a, float):
        s = ("%.4f" % a).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dump(node, indent=0):
    """Ghi S-expression; list ngắn không chứa list con được viết trên một dòng."""
    if not isinstance(node, list):
        return _atom(node)
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(_atom(x) for x in node) + ")"
    pad = "\t" * (indent + 1)
    out = ["(" + _atom(node[0])]
    i = 1
    while i < len(node) and not isinstance(node[i], list):
        out[0] += " " + _atom(node[i])
        i += 1
    for child in node[i:]:
        out.append(pad + dump(child, indent + 1))
    out.append("\t" * indent + ")")
    return "\n".join(out)


def find(node, key):
    """Trả về list con đầu tiên có phần tử đầu == key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def esc(s):
    """Thoát ký tự cho chuỗi đặt trong nháy."""
    return Q(str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))
