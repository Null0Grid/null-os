"""Null mark geometry: a ring crossed by two parallel slashes.

Single source of truth for the mark. Used by patch-font.py (font glyph)
and tools/make-branding.py (SVG/PNG logo, wallpaper, splash).
All coordinates are in font units: 600-wide cell, baseline at y=0.
"""
import math

CELL_W = 600
CX, CY = 300, 360          # ring centre
R_OUT, R_IN = 255, 200     # ring outer/inner radius (55 thick)
SLASH_ANGLE = 58           # degrees from horizontal, rising left to right
SLASH_HALF_LEN = 330       # half-length of each slash from its centre
SLASH_HALF_W = 27          # half-thickness of each slash
SLASH_OFFSET = 62          # perpendicular distance of each slash from centre
CODEPOINT = 0xE900         # private-use code point in Null Mono
GLYPH_NAME = "nullmark"

K = 0.5522847498           # cubic bezier circle constant


def circle(cx, cy, r, clockwise):
    """Four cubic segments approximating a circle. Returns list of ops."""
    k = K * r
    pts = [(cx + r, cy), (cx, cy - r), (cx - r, cy), (cx, cy + r)]  # E,S,W,N
    ctrl = [
        ((cx + r, cy - k), (cx + k, cy - r)),
        ((cx - k, cy - r), (cx - r, cy - k)),
        ((cx - r, cy + k), (cx - k, cy + r)),
        ((cx + k, cy + r), (cx + r, cy + k)),
    ]
    ops = [("move", pts[0])]
    order = range(4)
    if not clockwise:
        # Reverse direction: E -> N -> W -> S -> E
        pts_r = [pts[0], pts[3], pts[2], pts[1]]
        ctrl_r = [(c[1], c[0]) for c in reversed(ctrl)]
        for i in order:
            ops.append(("curve", ctrl_r[i][0], ctrl_r[i][1], pts_r[(i + 1) % 4]))
        return ops
    for i in order:
        ops.append(("curve", ctrl[i][0], ctrl[i][1], pts[(i + 1) % 4]))
    return ops


def slash(offset):
    """Parallelogram (rectangle rotated by SLASH_ANGLE), clockwise."""
    a = math.radians(SLASH_ANGLE)
    ux, uy = math.cos(a), math.sin(a)          # along the slash
    nx, ny = -uy, ux                           # perpendicular
    mx, my = CX + nx * offset, CY + ny * offset
    L, W = SLASH_HALF_LEN, SLASH_HALF_W
    # Clockwise in y-up coordinates
    corners = [
        (mx - ux * L + nx * W, my - uy * L + ny * W),
        (mx + ux * L + nx * W, my + uy * L + ny * W),
        (mx + ux * L - nx * W, my + uy * L - ny * W),
        (mx - ux * L - nx * W, my - uy * L - ny * W),
    ]
    ops = [("move", corners[0])] + [("line", c) for c in corners[1:]]
    return ops


def contours():
    """All contours, wound for the nonzero fill rule (y-up)."""
    return [
        circle(CX, CY, R_OUT, clockwise=True),
        circle(CX, CY, R_IN, clockwise=False),
        slash(-SLASH_OFFSET),
        slash(+SLASH_OFFSET),
    ]


def draw(pen):
    for c in contours():
        for op in c:
            if op[0] == "move":
                pen.moveTo(op[1])
            elif op[0] == "line":
                pen.lineTo(op[1])
            else:
                pen.curveTo(op[1], op[2], op[3])
        pen.closePath()


def svg_path(flip_height=None):
    """SVG path data. If flip_height is given, flip y (SVG is y-down)."""
    def p(pt):
        x, y = pt
        if flip_height is not None:
            y = flip_height - y
        return f"{x:.1f},{y:.1f}"
    out = []
    for c in contours():
        for op in c:
            if op[0] == "move":
                out.append("M" + p(op[1]))
            elif op[0] == "line":
                out.append("L" + p(op[1]))
            else:
                out.append("C" + " ".join(p(q) for q in op[1:]))
        out.append("Z")
    return " ".join(out)
