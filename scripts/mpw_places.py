"""mapwright places: seeded cities, dungeons and battle maps as recipe folders, their proof bars and the
Universal VTT export. Standard library only.

Methods follow references/cities-and-dungeons.md:
- city: ring-and-spoke street growth (wards between gate roads, the Watabou-style medieval plan in section 3,
  reimplemented), blocks as the faces between rings and spokes, lots by recursive cuts across the long axis
  (OBB subdivision, section 2), a wall on one ring with gates only where the main roads cross it, districts.
- dungeon: BSP rooms with L corridors plus extra loops (5.1), or cellular-automaton caves keeping the largest
  region (5.2); doors at one-wide room openings; square grid.
- battle: square or hex grid, ruined buildings with doors, rocks, trees, torches; enclosed pockets filled.
"""
import base64
import json
import math
import os
import shutil
import struct
import tempfile
import time
from xml.sax.saxutils import escape

import mpw_gen as G
import mpw_names

PLACES_VERSION = "places-1"
KINDS = ("city", "dungeon", "battle")
FILES = ("recipe.json", "features.geojson", "names.json", "sources.json", "grid.json", "map.png", "map.svg")


# ------------------------------------------------------------------ stable random numbers
class Rng:
    """Counter-based generator on mpw_gen.h64: same seed, same numbers on every Python version."""

    def __init__(self, seed, stream=0):
        self.s = int(seed) & G.M64
        self.st = stream
        self.i = 0

    def random(self):
        self.i += 1
        return (G.h64(self.s, self.st, self.i) >> 11) / 9007199254740992.0

    def randint(self, a, b):
        return a + int(self.random() * (b - a + 1)) if b > a else a

    def uniform(self, a, b):
        return a + (b - a) * self.random()

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]


def dump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, separators=(",", ":"))
        f.write("\n")


def load(d, name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return json.load(f)


def r2(v):
    return round(v, 2)


# ------------------------------------------------------------------ geometry
def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def centroid(poly):
    a = area(poly)
    if abs(a) < 1e-12:
        return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
    cx = cy = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        k = x0 * y1 - x1 * y0
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    return (cx / (6 * a), cy / (6 * a))


def clip_half(poly, px, py, nx, ny):
    """Keep the part of a polygon where (p - P).n >= 0 (Sutherland-Hodgman, one plane)."""
    out = []
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        da = (a[0] - px) * nx + (a[1] - py) * ny
        db = (b[0] - px) * nx + (b[1] - py) * ny
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def seg_cross(a, b, c, d):
    """Proper crossing only: touching at an end or running along is not a crossing."""
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def on_boundary(p, poly, tol=1e-6):
    return any(seg_dist(p[0], p[1], *poly[i], *poly[(i + 1) % len(poly)]) <= tol for i in range(len(poly)))


def simple(poly):
    n = len(poly)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if seg_cross(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return False
    return True


def frontage(poly, block, tol=1e-6, minlen=1.0):
    """True when some edge of poly lies on the block boundary (both ends on it) and is longer than minlen."""
    n = len(poly)
    return any(math.dist(poly[i], poly[(i + 1) % n]) > minlen and on_boundary(poly[i], block, tol)
               and on_boundary(poly[(i + 1) % n], block, tol) and on_boundary(
                   ((poly[i][0] + poly[(i + 1) % n][0]) / 2, (poly[i][1] + poly[(i + 1) % n][1]) / 2), block, tol)
               for i in range(n))


def split_lots(poly, target, rng, block=None, depth=0):
    """Recursive cuts across the long axis near the middle (OBB subdivision) until under the target area.
    A cut is kept only when both halves still front the block boundary (a street); else the other axis is
    tried, and if neither keeps frontage the piece stays whole."""
    block = block or poly
    a = abs(area(poly))
    if a <= target or depth > 14 or len(poly) < 3:
        return [poly]
    best = 0
    for i in range(len(poly)):
        L = math.dist(poly[i], poly[(i + 1) % len(poly)])
        if L > best:
            best, k = L, i
    ax, ay = poly[k]
    bx, by = poly[(k + 1) % len(poly)]
    ux, uy = (bx - ax) / best, (by - ay) / best
    j = rng.uniform(0.42, 0.58)
    for vx, vy in ((ux, uy), (-uy, ux)):
        proj = [(p[0] - ax) * vx + (p[1] - ay) * vy for p in poly]
        lo, hi = min(proj), max(proj)
        t = lo + (hi - lo) * j
        px, py = ax + vx * t, ay + vy * t
        left = clip_half(poly, px, py, -vx, -vy)
        right = clip_half(poly, px, py, vx, vy)
        if len(left) < 3 or len(right) < 3 or not frontage(left, block) or not frontage(right, block):
            continue
        return split_lots(left, target, rng, block, depth + 1) + split_lots(right, target, rng, block, depth + 1)
    return [poly]


# ------------------------------------------------------------------ PNG
def png_rgb(w, h, rows):
    return G.png_bytes(w, h, rows, 8, 2)


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


# ------------------------------------------------------------------ styles for places
PSTYLES = {
    "ink-and-parchment": dict(bg="#efe2c2", ink="#3b2f22", block="#d9c49a", lot="#c9ad7d", water="#9db8c9",
                              wall="#3b2f22", floor="#f3e8cf", rock="#5a4a3a", grid="#b9a37c", door="#8a5a2b",
                              tree="#5e7a45", font="'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif",
                              halo="#efe2c2", mono=False),
    "blueprint": dict(bg="#1d4e89", ink="#e8f1ff", block="#2c66aa", lot="#3a78bf", water="#163c6b",
                      wall="#e8f1ff", floor="#2a5f9e", rock="#0f2f57", grid="#5c8fcf", door="#ffd27a",
                      tree="#6fa8dc", font="'Courier New', Courier, monospace", halo="#1d4e89", mono=True),
}
DEFAULT_PSTYLE = {"city": "ink-and-parchment", "dungeon": "blueprint", "battle": "ink-and-parchment"}


def pstyle(name, kind):
    name = name or DEFAULT_PSTYLE[kind]
    if name not in PSTYLES:
        raise ValueError("style %r is not drawn for a %s; use one of: %s" % (name, kind, ", ".join(sorted(PSTYLES))))
    return name, PSTYLES[name]


def _rgb(h):
    return bytes(G.hex_rgb(h))


def place_labels(cands, w, h, mono, reserved=()):
    """Greedy: cands = [(text, x, y, size)] in priority order; drop any that overlap or leave the frame."""
    import mpw_render as R
    boxes = list(reserved)
    out, dropped = [], []
    for text, x, y, size in cands:
        b = R.text_box(x, y, size, text, "middle", 0.0, 0.0, 2.0, mono)
        if b[0] < 2 or b[1] < 2 or b[2] > w - 2 or b[3] > h - 2 or any(R.overlap(b, o) for o in boxes):
            dropped.append(text)
            continue
        boxes.append(b)
        out.append((text, x, y, size))
    return out, dropped


def labels_svg(labels, st):
    o = ['<g class="labels" font-family="%s" fill="%s" stroke="%s" stroke-width="2.5" paint-order="stroke">'
         % (escape(st["font"], {'"': "&quot;"}), st["ink"], st["halo"])]
    for text, x, y, size in labels:
        o.append('<text x="%.1f" y="%.1f" font-size="%.1f" text-anchor="middle">%s</text>' % (x, y, size, escape(text)))
    o.append("</g>")
    return "".join(o)


# ================================================================== city
def _parent_context(parent, settlement):
    """Name, sea direction and river direction for a city sited on a world settlement."""
    rc = load(parent, "recipe.json")
    fc = load(parent, "features.geojson")
    sets = [f for f in fc["features"] if f["properties"].get("kind") == "settlement"]
    if not sets:
        raise ValueError("parent %s has no settlements" % parent)
    if settlement is None:
        s = sorted(sets, key=lambda f: (-f["properties"].get("score", 0), f["properties"]["id"]))[0]
    else:
        m = [f for f in sets if f["properties"]["id"] == settlement]
        if not m:
            raise ValueError("no settlement %s in %s (ids: %s)" % (settlement, parent,
                             ", ".join(str(f["properties"]["id"]) for f in sets[:20])))
        s = m[0]
    sx, sy = s["geometry"]["coordinates"]
    near = rc["params"].get("spacing_km", 8.0) * 1000.0 * 1.5

    def nearest(kind):
        best = None
        for f in fc["features"]:
            if f["properties"].get("kind") != kind:
                continue
            c = f["geometry"]["coordinates"]
            for i in range(len(c) - 1):
                d = seg_dist(sx, sy, c[i][0], c[i][1], c[i + 1][0], c[i + 1][1])
                if best is None or d < best[0]:
                    best = (d, c[i], c[i + 1])
        return best if best and best[0] <= near else None
    ctx = dict(parent=None, settlement=s["properties"]["id"], name=s["properties"].get("name"), language=rc.get("language"),
               used=[e["name"] for e in load(parent, "names.json").get("names", [])], sea=None, river=None)
    c = nearest("coast")
    if c:
        a, b = c[1], c[2]
        t = max(0.0, min(1.0, ((sx - a[0]) * (b[0] - a[0]) + (sy - a[1]) * (b[1] - a[1]))
                         / max(1e-9, (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)))
        qx, qy = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
        # world y is north-up; city y is south-down, so flip the y component
        ctx["sea"] = round(math.atan2(-(qy - sy), qx - sx), 6)
    rv = nearest("river")
    if rv:
        ctx["river"] = round(math.atan2(-(rv[2][1] - rv[1][1]), rv[2][0] - rv[1][0]), 6)
    return ctx


DISTRICTS_IN = ["craftsmen", "merchants", "temple", "nobles", "docks", "slums", "guildhall", "garrison"]
DISTRICTS_OUT = ["farms", "suburb", "orchards", "tanneries"]


def gen_city(seed, out, bands=6, wall=4, spokes=None, ring_m=55.0, lot_m2=300.0, parent=None, settlement=None,
             sea=None, river=None, style=None, version="0.5.0", name_style=None, ref=None):
    t0 = time.perf_counter()
    rng = Rng(seed, 1)
    ctx = _parent_context(parent, settlement) if parent else None
    if ctx:
        ctx["parent"] = ref or os.path.relpath(os.path.abspath(parent), os.path.abspath(out)).replace("\\", "/")
    if ctx:
        sea = ctx["sea"] if sea is None else sea
        river = ctx["river"] if river is None else river
        lang = ctx["language"] or mpw_names.make_language(seed, name_style)
    else:
        lang = mpw_names.make_language(seed, name_style)
    if wall is not None and not 1 <= wall < bands:
        raise ValueError("--wall must be a ring between 1 and bands-1")
    n0 = rng.randint(5, 7)          # always drawn, so a stored --spokes replays the same stream
    n0 = spokes or n0
    # spokes per band: (angle, id, main)
    base = [(2 * math.pi * j / n0 + rng.uniform(-0.25, 0.25) * 2 * math.pi / n0) % (2 * math.pi) for j in range(n0)]
    sp_band = {1: [(a, j, True) for j, a in enumerate(sorted(base))]}
    nid = n0
    for k in range(2, bands + 1):
        prev = sp_band[k - 1]
        if wall is not None and k == wall + 1:
            sp_band[k] = [s for s in prev if s[2]]       # only gate roads leave the wall
            continue
        cur = []
        pr = 0.75 if (wall is None or k <= wall) else 0.45
        for i, s in enumerate(prev):
            cur.append(s)
            nxt = prev[(i + 1) % len(prev)]
            gap = (nxt[0] - s[0]) % (2 * math.pi)
            if gap * ring_m * k > 2.2 * ring_m and rng.random() < pr:
                cur.append(((s[0] + gap * rng.uniform(0.4, 0.6)) % (2 * math.pi), nid, False))
                nid += 1
        sp_band[k] = sorted(cur)
    radius = {}
    pos = {}

    def node(k, s):
        key = (k, s[1])
        if key not in pos:
            r0 = 0.7 * ring_m if k == 0 else ring_m * (0.7 + k)
            r = r0 * (1 + 0.07 * (G.u01(seed, 77, k, s[1]) - 0.5))
            pos[key] = (r * math.cos(s[0]), r * math.sin(s[0]))
            radius[key] = r
        return key
    ring_sp = {}
    for k in range(0, bands + 1):
        u = {}
        for b in (k, k + 1):
            for s in sp_band.get(b, []):
                u[s[1]] = s
        ring_sp[k] = sorted(u.values())
        for s in ring_sp[k]:
            node(k, s)

    def in_arc(x, a, b):
        return (x - a) % (2 * math.pi) <= (b - a) % (2 * math.pi) + 1e-12

    def arc_order(lst, a):
        return sorted(lst, key=lambda s: (s[0] - a) % (2 * math.pi))
    # sea and river tests in metres, city centre at 0,0, y south
    shore = None
    if sea is not None:
        shore = (math.cos(sea), math.sin(sea), ring_m * (0.7 + bands * rng.uniform(0.55, 0.75)))

    def wet(p):
        return shore is not None and p[0] * shore[0] + p[1] * shore[1] > shore[2]
    rline = None
    if river is not None:
        off = rng.uniform(-0.25, 0.25) * ring_m * 2
        ux, uy = math.cos(river), math.sin(river)
        rline = ((-uy * off, ux * off), (ux, uy), 12.0)
    R = ring_m * (0.7 + bands + 1.5)

    def river_d(p):
        (ox, oy), (ux, uy), _ = rline
        return abs((p[0] - ox) * -uy + (p[1] - oy) * ux)
    def ring_path(k, s, t):
        """Points along ring k from spoke s to spoke t (forward), one every 7.5 degrees: curved streets."""
        gap = (t[0] - s[0]) % (2 * math.pi) or 2 * math.pi
        n = max(1, int(math.ceil(gap / (math.pi / 24))))
        r0, r1 = radius[(k, s[1])], radius[(k, t[1])]
        mid = [((r0 + (r1 - r0) * m / n) * math.cos(s[0] + gap * m / n), (r0 + (r1 - r0) * m / n) * math.sin(s[0] + gap * m / n))
               for m in range(1, n)]
        return [pos[(k, s[1])]] + mid + [pos[(k, t[1])]]
    # streets: (from node, to node, rank, points)
    edges = []
    for k in range(0, bands + 1):
        sl = ring_sp[k]
        for i, s in enumerate(sl):
            t = sl[(i + 1) % len(sl)]
            edges.append(((k, s[1]), (k, t[1]), "wall-street" if wall is not None and k == wall else
                          ("plaza" if k == 0 else "street"), ring_path(k, s, t)))
    for k in range(1, bands + 1):
        for s in sp_band[k]:
            edges.append(((k - 1, s[1]), (k, s[1]), "main" if s[2] else "street", [pos[(k - 1, s[1])], pos[(k, s[1])]]))
    edges = [e for e in edges if not any(wet(q) for q in e[3])]
    # blocks
    blocks = []
    for k in range(1, bands + 1):
        sl = sp_band[k]
        for i, a in enumerate(sl):
            b = sl[(i + 1) % len(sl)]
            outer = [s for s in arc_order(ring_sp[k], a[0]) if in_arc(s[0], a[0], b[0])]
            inner = [s for s in arc_order(ring_sp[k - 1], a[0]) if in_arc(s[0], a[0], b[0])]
            poly = []
            for j in range(len(outer) - 1):
                poly += ring_path(k, outer[j], outer[j + 1])[:-1]
            poly.append(pos[(k, outer[-1][1])])
            back = []
            for j in range(len(inner) - 1):
                back += ring_path(k - 1, inner[j], inner[j + 1])[:-1]
            back.append(pos[(k - 1, inner[-1][1])])
            poly += list(reversed(back))
            if any(wet(p) for p in poly):
                continue
            blocks.append(dict(band=k, a=a, poly=poly))
    # districts: one per (sector between gate roads, inner/outer half inside the wall, or outside)
    mains = sp_band[1]
    namer = mpw_names.Namer(lang, used=(ctx["used"] if ctx else ()))
    city_name = (ctx and ctx["name"]) or namer.name("city", (seed,))
    dist = {}
    for bl in blocks:
        ang = math.atan2(*reversed(centroid(bl["poly"]))) % (2 * math.pi)
        base0 = mains[0][0]
        sec = max(i for i, m in enumerate(mains) if (m[0] - base0) % (2 * math.pi) <= (ang - base0) % (2 * math.pi))
        inside = wall is None or bl["band"] <= wall
        ring = 0 if (inside and bl["band"] <= max(1, (wall or bands) // 2)) else (1 if inside else 2)
        key = (sec, ring)
        if key not in dist:
            pool = DISTRICTS_IN if inside else DISTRICTS_OUT
            dist[key] = dict(id=len(dist), sector=sec, ring=ring, inside=inside,
                             type=pool[G.h64(seed, 91, sec, ring) % len(pool)],
                             name=namer.name("district", (sec, ring)), blocks=[])
        dist[key]["blocks"].append(bl)
        bl["district"] = dist[key]["id"]
    # lots and buildings
    lots = []
    for bi, bl in enumerate(blocks):
        bl["id"] = bi
        inside = wall is None or bl["band"] <= wall
        tgt = lot_m2 * (0.8 + 0.15 * bl["band"]) if inside else lot_m2 * 4
        lr = Rng(seed, 1000 + bi)
        for li, lp in enumerate(split_lots(bl["poly"], tgt, lr)):
            if rline and (river_d(centroid(lp)) < rline[2] / 2 + 6 or any(river_d(p) < rline[2] / 2 for p in lp)):
                continue
            front = frontage(lp, bl["poly"])
            lots.append(dict(block=bi, id=len(lots), poly=lp, front=front, inside=inside))
    # wall polyline(s) and gates
    wall_lines, gates = [], []
    if wall is not None:
        wl = ring_sp[wall]
        seq = []
        for j in range(len(wl)):
            seq += ring_path(wall, wl[j], wl[(j + 1) % len(wl)])[:-1]
        dry = [not wet(p) for p in seq]
        if all(dry):
            wall_lines.append(seq + [seq[0]])
        else:
            i0 = dry.index(False)
            cur = []
            for j in range(1, len(seq) + 1):
                i = (i0 + j) % len(seq)
                if dry[i]:
                    cur.append(seq[i])
                else:
                    if len(cur) > 1:
                        wall_lines.append(cur)
                    cur = []
            if len(cur) > 1:
                wall_lines.append(cur)
        for s in sp_band.get(wall + 1, []):
            if not wet(pos[(wall, s[1])]) and not wet(pos[(wall + 1, s[1])]):
                gates.append(dict(id=len(gates), spoke=s[1], at=pos[(wall, s[1])]))
    bridges = []
    if rline:
        (ox, oy), (ux, uy), _ = rline
        a = (ox - ux * R, oy - uy * R)
        b = (ox + ux * R, oy + uy * R)
        for ei, e in enumerate(edges):
            if any(seg_cross(a, b, e[3][j], e[3][j + 1]) for j in range(len(e[3]) - 1)):
                bridges.append(ei)
    # features (metres, x east, y south; geojson stores y north)
    F = []

    def P(p):
        return [r2(p[0]), r2(-p[1])]
    for i, (a, b, kind, pts) in enumerate(edges):
        pr = dict(kind="street", id=i, rank=kind)
        if i in bridges:
            pr["bridge"] = True
        F.append({"type": "Feature", "properties": pr,
                  "geometry": {"type": "LineString", "coordinates": [P(q) for q in pts]}})
    plaza = []
    for j in range(len(ring_sp[0])):
        plaza += ring_path(0, ring_sp[0][j], ring_sp[0][(j + 1) % len(ring_sp[0])])[:-1]
    F.append({"type": "Feature", "properties": dict(kind="plaza", name="Market"),
              "geometry": {"type": "Polygon", "coordinates": [[P(p) for p in plaza + plaza[:1]]]}})
    for bl in blocks:
        F.append({"type": "Feature", "properties": dict(kind="block", id=bl["id"], band=bl["band"],
                                                         district=bl["district"]),
                  "geometry": {"type": "Polygon", "coordinates": [[P(p) for p in bl["poly"] + bl["poly"][:1]]]}})
    for lt in lots:
        F.append({"type": "Feature", "properties": dict(kind="lot", id=lt["id"], block=lt["block"],
                                                         frontage=lt["front"]),
                  "geometry": {"type": "Polygon", "coordinates": [[P(p) for p in lt["poly"] + lt["poly"][:1]]]}})
        if lt["front"]:
            c = centroid(lt["poly"])
            k = 0.72 if lt["inside"] else 0.45
            bp = [(c[0] + (p[0] - c[0]) * k, c[1] + (p[1] - c[1]) * k) for p in lt["poly"]]
            F.append({"type": "Feature", "properties": dict(kind="building", lot=lt["id"]),
                      "geometry": {"type": "Polygon", "coordinates": [[P(p) for p in bp + bp[:1]]]}})
    for wl in wall_lines:
        F.append({"type": "Feature", "properties": dict(kind="wall"),
                  "geometry": {"type": "LineString", "coordinates": [P(p) for p in wl]}})
    for g in gates:
        F.append({"type": "Feature", "properties": dict(kind="gate", id=g["id"]),
                  "geometry": {"type": "Point", "coordinates": P(g["at"])}})
    for d in sorted(dist.values(), key=lambda d: d["id"]):
        pts = [centroid(b["poly"]) for b in d["blocks"]]
        ws = [abs(area(b["poly"])) for b in d["blocks"]]
        c = (sum(p[0] * w for p, w in zip(pts, ws)) / sum(ws), sum(p[1] * w for p, w in zip(pts, ws)) / sum(ws))
        F.append({"type": "Feature", "properties": dict(kind="district", id=d["id"], name=d["name"], type=d["type"],
                                                         inside=d["inside"], blocks=[b["id"] for b in d["blocks"]]),
                  "geometry": {"type": "Point", "coordinates": P(c)}})
    if shore:
        nx, ny, dd = shore
        F.append({"type": "Feature", "properties": dict(kind="coast"),
                  "geometry": {"type": "LineString", "coordinates": [P((nx * dd - ny * R, ny * dd + nx * R)),
                                                                      P((nx * dd + ny * R, ny * dd - nx * R))]}})
    if rline:
        (ox, oy), (ux, uy), wd = rline
        F.append({"type": "Feature", "properties": dict(kind="river", width_m=wd),
                  "geometry": {"type": "LineString", "coordinates": [P((ox - ux * R, oy - uy * R)),
                                                                      P((ox + ux * R, oy + uy * R))]}})
    names = [dict(kind="city", id=0, name=city_name)] + [dict(kind="district", id=d["id"], name=d["name"])
                                                          for d in sorted(dist.values(), key=lambda d: d["id"])]
    recipe = dict(kind="city", seed=seed, generator=PLACES_VERSION, tool="mapwright", tool_version=version,
                  name=city_name,
                  params=dict(bands=bands, wall=wall, spokes=n0, ring_m=ring_m, lot_m2=lot_m2, sea=sea, river=river,
                              style=style, name_style=name_style),
                  projection=dict(kind="local", units="m", axes="x east, y north, origin at the market"),
                  extent=[-R, -R, R, R], parent=({"path": ctx["parent"], "settlement": ctx["settlement"]}
                                                  if ctx else None),
                  language=lang)
    t1 = time.perf_counter()
    write_place(out, recipe, F, names, None, None)
    t = dict(generate=round(t1 - t0, 3), write_render=round(time.perf_counter() - t1, 3),
             total=round(time.perf_counter() - t0, 3))
    return dict(out=out, kind="city", name=city_name, streets=len(edges), blocks=len(blocks), lots=len(lots),
                districts=len(dist), gates=len(gates), bridges=len(bridges), times=t)


def render_city_svg(rc, F, st):
    e = rc["extent"]
    W = 1000.0
    s = W / (e[2] - e[0])
    Hs = (e[3] - e[1]) * s

    def X(c):
        return "%.1f,%.1f" % ((c[0] - e[0]) * s, (-c[1] - e[1]) * s)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, Hs, W, Hs),
         '<rect width="100%%" height="100%%" fill="%s"/>' % st["bg"]]
    by = {}
    for f in F:
        by.setdefault(f["properties"]["kind"], []).append(f)
    for f in by.get("block", []):
        o.append('<polygon points="%s" fill="%s"/>' % (" ".join(X(c) for c in f["geometry"]["coordinates"][0]),
                                                       st["block"]))
    for f in by.get("building", []):
        o.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.4"/>'
                 % (" ".join(X(c) for c in f["geometry"]["coordinates"][0]), st["lot"], st["ink"]))
    for f in by.get("plaza", []):
        o.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.8"/>'
                 % (" ".join(X(c) for c in f["geometry"]["coordinates"][0]), st["floor"], st["ink"]))
    for f in by.get("river", []):
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f"/>'
                 % (" ".join(X(c) for c in f["geometry"]["coordinates"]), st["water"], f["properties"]["width_m"] * s))
    for f in by.get("coast", []):
        a, b = f["geometry"]["coordinates"]
        # sea: big polygon on the far side of the coast line
        dx, dy = b[0] - a[0], b[1] - a[1]
        nx, ny = dy, -dx
        L = math.hypot(nx, ny) or 1
        k = 4 * (e[2] - e[0]) / L
        if nx * a[0] + ny * a[1] < 0:
            nx, ny = -nx, -ny
        poly = [a, b, [b[0] + nx * k, b[1] + ny * k], [a[0] + nx * k, a[1] + ny * k]]
        o.append('<polygon points="%s" fill="%s"/>' % (" ".join(X(c) for c in poly), st["water"]))
    for f in by.get("street", []):
        rk = f["properties"]["rank"]
        wd = {"main": 2.4, "wall-street": 1.6, "plaza": 1.2}.get(rk, 1.0)
        dash = ""
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f"%s/>'
                 % (" ".join(X(c) for c in f["geometry"]["coordinates"]), st["ink"], wd, dash))
    for f in by.get("wall", []):
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="4"/>'
                 % (" ".join(X(c) for c in f["geometry"]["coordinates"]), st["wall"]))
    for f in by.get("gate", []):
        c = f["geometry"]["coordinates"]
        o.append('<circle cx="%s" cy="%s" r="4" fill="%s" stroke="%s" stroke-width="1.5"/>'
                 % (*X(c).split(","), st["bg"], st["wall"]))
    cands = [(rc["name"], W / 2, 34.0, 26.0)]
    for f in sorted(by.get("district", []), key=lambda f: (not f["properties"]["inside"], f["properties"]["id"])):
        x, y = X(f["geometry"]["coordinates"]).split(",")
        cands.append((f["properties"]["name"], float(x), float(y), 12.0))
    labs, _ = place_labels(cands, W, Hs, st["mono"])
    o.append(labels_svg(labs, st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ================================================================== grids (dungeon and battle)
WALLC, FLOOR, DOOR, TREE = "#", ".", "+", "T"
PASS = (FLOOR, DOOR)


def carve_l(g, a, b, rng):
    (x0, y0), (x1, y1) = a, b
    if rng.random() < 0.5:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            g[y0][x] = FLOOR
        for y in range(min(y0, y1), max(y0, y1) + 1):
            g[y][x1] = FLOOR
    else:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            g[y][x0] = FLOOR
        for x in range(min(x0, x1), max(x0, x1) + 1):
            g[y1][x] = FLOOR


def bsp_dungeon(w, h, rng, leaf=9, loops=0.12):
    g = [[WALLC] * w for _ in range(h)]
    rooms = []

    def split(x, y, ww, hh, depth):
        horiz = hh > ww if abs(ww - hh) > 2 else rng.random() < 0.5
        size = hh if horiz else ww
        if size < 2 * leaf or depth > 8:
            rw = rng.randint(max(3, ww // 2), max(3, ww - 2))
            rh = rng.randint(max(3, hh // 2), max(3, hh - 2))
            rx = x + rng.randint(1, max(1, ww - rw - 1))
            ry = y + rng.randint(1, max(1, hh - rh - 1))
            rw = min(rw, x + ww - 1 - rx)
            rh = min(rh, y + hh - 1 - ry)
            rooms.append([rx, ry, rw, rh])
            return [len(rooms) - 1]
        cut = int(size * rng.uniform(0.35, 0.65))
        if horiz:
            a = split(x, y, ww, cut, depth + 1)
            b = split(x, y + cut, ww, hh - cut, depth + 1)
        else:
            a = split(x, y, cut, hh, depth + 1)
            b = split(x + cut, y, ww - cut, hh, depth + 1)
        ra, rb = rooms[rng.choice(a)], rooms[rng.choice(b)]
        links.append((ra, rb))
        return a + b
    links = []
    split(0, 0, w, h, 0)
    for rx, ry, rw, rh in rooms:
        for yy in range(ry, ry + rh):
            for xx in range(rx, rx + rw):
                g[yy][xx] = FLOOR

    def ctr(r):
        return (r[0] + r[2] // 2, r[1] + r[3] // 2)
    for ra, rb in links:
        carve_l(g, ctr(ra), ctr(rb), rng)
    n = len(rooms)
    extra = max(1, int(round(n * loops)))
    pairs = sorted(((math.dist(ctr(rooms[i]), ctr(rooms[j])), i, j) for i in range(n) for j in range(i + 1, n)))
    linked = set((id(a), id(b)) for a, b in links) | set((id(b), id(a)) for a, b in links)
    added = 0
    for _, i, j in pairs:
        if added >= extra:
            break
        if (id(rooms[i]), id(rooms[j])) in linked or rng.random() < 0.5:
            continue
        carve_l(g, ctr(rooms[i]), ctr(rooms[j]), rng)
        added += 1
    for yy in range(h):
        g[yy][0] = g[yy][w - 1] = WALLC
    for xx in range(w):
        g[0][xx] = g[h - 1][xx] = WALLC
    # doors: one-wide openings just outside a room
    inroom = set()
    for rx, ry, rw, rh in rooms:
        for yy in range(ry, ry + rh):
            for xx in range(rx, rx + rw):
                inroom.add((xx, yy))
    for rx, ry, rw, rh in rooms:
        ring = [(xx, ry - 1, 0) for xx in range(rx, rx + rw)] + [(xx, ry + rh, 0) for xx in range(rx, rx + rw)] + \
               [(rx - 1, yy, 1) for yy in range(ry, ry + rh)] + [(rx + rw, yy, 1) for yy in range(ry, ry + rh)]
        for xx, yy, vert in ring:
            if not (0 < xx < w - 1 and 0 < yy < h - 1) or (xx, yy) in inroom or g[yy][xx] != FLOOR:
                continue
            if vert == 0 and g[yy][xx - 1] == WALLC and g[yy][xx + 1] == WALLC:
                g[yy][xx] = DOOR
            elif vert == 1 and g[yy - 1][xx] == WALLC and g[yy + 1][xx] == WALLC:
                g[yy][xx] = DOOR
    return g, rooms


def cave_dungeon(w, h, rng, fill=0.45, passes=5):
    g = [[WALLC if (x in (0, w - 1) or y in (0, h - 1) or rng.random() < fill) else FLOOR for x in range(w)]
         for y in range(h)]
    for _ in range(passes):
        ng = [row[:] for row in g]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                n = sum(g[y + dy][x + dx] == WALLC for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
                ng[y][x] = WALLC if n >= 5 else (FLOOR if n <= 3 else g[y][x])
        g = ng
    regions = flood_regions(g, w, h)
    if not regions:
        raise ValueError("cave came out solid; try another seed or a lower fill")
    keep = set(max(regions, key=len))
    for y in range(h):
        for x in range(w):
            if g[y][x] == FLOOR and (x, y) not in keep:
                g[y][x] = WALLC
    return g, []


def nbrs4(x, y):
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def nbrs_hex(x, y):
    """odd-r offset neighbours."""
    if y % 2:
        d = ((1, 0), (-1, 0), (0, -1), (1, -1), (0, 1), (1, 1))
    else:
        d = ((1, 0), (-1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1))
    return tuple((x + a, y + b) for a, b in d)


def flood_regions(g, w, h, passable=PASS, nb=nbrs4):
    seen = set()
    regions = []
    for y in range(h):
        for x in range(w):
            if g[y][x] in passable and (x, y) not in seen:
                comp = [(x, y)]
                seen.add((x, y))
                i = 0
                while i < len(comp):
                    cx, cy = comp[i]
                    i += 1
                    for nx, ny in nb(cx, cy):
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and g[ny][nx] in passable:
                            seen.add((nx, ny))
                            comp.append((nx, ny))
                regions.append(comp)
    return regions


def battle_square(w, h, rng):
    g = [[FLOOR] * w for _ in range(h)]
    lights = []
    occ = set()
    nb = rng.randint(2, 4)
    for _ in range(nb * 6):
        if nb <= 0:
            break
        bw, bh = rng.randint(5, 9), rng.randint(4, 7)
        x0, y0 = rng.randint(2, w - bw - 3), rng.randint(2, h - bh - 3)
        cells = {(x, y) for x in range(x0 - 1, x0 + bw + 1) for y in range(y0 - 1, y0 + bh + 1)}
        if cells & occ:
            continue
        occ |= cells
        nb -= 1
        for y in range(y0, y0 + bh):
            for x in range(x0, x0 + bw):
                edge = x in (x0, x0 + bw - 1) or y in (y0, y0 + bh - 1)
                g[y][x] = WALLC if edge else FLOOR
        # ruin gaps and doors (never on a corner)
        sides = [[(x, y0) for x in range(x0 + 1, x0 + bw - 1)], [(x, y0 + bh - 1) for x in range(x0 + 1, x0 + bw - 1)],
                 [(x0, y) for y in range(y0 + 1, y0 + bh - 1)], [(x0 + bw - 1, y) for y in range(y0 + 1, y0 + bh - 1)]]
        for si in range(rng.randint(1, 2)):
            side = sides[rng.randint(0, 3)]
            dx, dy = side[len(side) // 2]
            g[dy][dx] = DOOR
            lights.append(dict(x=dx + 0.5, y=dy + 0.5, range=6, color="ffeccd8b"))
        if rng.random() < 0.6:
            side = sides[rng.randint(0, 3)]
            dx, dy = side[rng.randint(0, len(side) - 1)]
            if g[dy][dx] == WALLC and DOOR not in (g[dy][dx - 1], g[dy][dx + 1], g[dy - 1][dx], g[dy + 1][dx]):
                g[dy][dx] = FLOOR
    for _ in range(rng.randint(3, 6)):        # rocks
        cx, cy = rng.randint(1, w - 2), rng.randint(1, h - 2)
        r = rng.uniform(0.8, 2.2)
        for y in range(max(0, int(cy - r - 1)), min(h, int(cy + r + 2))):
            for x in range(max(0, int(cx - r - 1)), min(w, int(cx + r + 2))):
                if (x, y) not in occ and math.hypot(x - cx, y - cy) <= r:
                    g[y][x] = WALLC
    for _ in range(int(w * h * 0.03)):         # trees
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        if g[y][x] == FLOOR and (x, y) not in occ:
            g[y][x] = TREE
    fx, fy = rng.randint(w // 3, 2 * w // 3), rng.randint(h // 3, 2 * h // 3)
    if g[fy][fx] == FLOOR:
        lights.append(dict(x=fx + 0.5, y=fy + 0.5, range=8, color="ffffb060"))
    return g, lights


def battle_hex(w, h, rng):
    g = [[FLOOR] * w for _ in range(h)]
    for _ in range(rng.randint(3, 6)):
        cx, cy = rng.randint(1, w - 2), rng.randint(1, h - 2)
        blob = [(cx, cy)]
        g[cy][cx] = WALLC
        for _ in range(rng.randint(2, 8)):
            bx, by = rng.choice(blob)
            nx, ny = rng.choice(nbrs_hex(bx, by))
            if 0 <= nx < w and 0 <= ny < h:
                g[ny][nx] = WALLC
                blob.append((nx, ny))
    for _ in range(int(w * h * 0.04)):
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        if g[y][x] == FLOOR:
            g[y][x] = TREE
    return g, []


def fill_pockets(g, w, h, nb, edge):
    """Battle maps: keep the largest open region that touches the map edge; every other pocket becomes rock
    (a rock line can cut the map in two, so touching the edge is not enough). Returns the kept region."""
    regs = flood_regions(g, w, h, PASS, nb)
    touch = [c for c in regs if any(p in edge for p in c)] or regs
    keep = max(touch, key=lambda c: (len(c), min(c)))
    for comp in regs:
        if comp is not keep:
            for x, y in comp:
                g[y][x] = WALLC
    return keep


def wall_segments(g, w, h, border_walls=True):
    """Grid-unit wall segments between open cells (floor, door, tree) and walls, merged along rows and columns.
    Outside the grid counts as wall when border_walls is true (dungeons), as open ground otherwise (battle maps)."""
    def solid(x, y):
        if not (0 <= x < w and 0 <= y < h):
            return border_walls
        return g[y][x] == WALLC

    def opened(x, y):
        return 0 <= x < w and 0 <= y < h and g[y][x] != WALLC

    def edge(p, q):
        return (opened(*p) and solid(*q)) or (opened(*q) and solid(*p))
    segs = []
    for y in range(h + 1):
        run = None
        for x in range(w + 1):
            e = x < w and edge((x, y - 1), (x, y))
            if e and run is None:
                run = x
            elif not e and run is not None:
                segs.append(((run, y), (x, y)))
                run = None
    for x in range(w + 1):
        run = None
        for y in range(h + 1):
            e = y < h and edge((x - 1, y), (x, y))
            if e and run is None:
                run = y
            elif not e and run is not None:
                segs.append(((x, run), (x, y)))
                run = None
    return segs


def door_portals(g, w, h):
    out = []
    for y in range(h):
        for x in range(w):
            if g[y][x] != DOOR:
                continue
            lw = x - 1 >= 0 and g[y][x - 1] == WALLC
            rw = x + 1 < w and g[y][x + 1] == WALLC
            if lw and rw:     # walls left and right: passage runs north-south, door spans east-west
                out.append(dict(x=x, y=y, bounds=[[x, y + 0.5], [x + 1, y + 0.5]], rotation=0.0))
            else:
                out.append(dict(x=x, y=y, bounds=[[x + 0.5, y], [x + 0.5, y + 1]], rotation=round(math.pi / 2, 6)))
    return out


def grid_png(g, w, h, pps, st):
    """Square grid picture: cell colours, a 1 px grid line on every multiple of pps."""
    col = {WALLC: _rgb(st["rock"]), FLOOR: _rgb(st["floor"]), DOOR: _rgb(st["door"]), TREE: _rgb(st["tree"])}
    gl = _rgb(st["grid"])
    rows = []
    for y in range(h):
        body = bytearray()
        line = bytearray()
        for x in range(w):
            c = col[g[y][x]]
            body += gl + c * (pps - 1)
            line += gl * pps
        body = bytes(body)
        line = bytes(line)
        rows.append(line)
        rows.extend([body] * (pps - 1))
    return png_rgb(w * pps, h * pps, rows)


def hex_geometry(w, h, pps):
    """Pointy-top odd-r hexes, pps = hex width in px (even). Returns centre(x, y) and rounded vertices."""
    size = pps / math.sqrt(3)
    rowh = 1.5 * size

    def centre(x, y):
        return (pps * (x + 0.5 * (y % 2)) + pps / 2, rowh * y + size)

    def verts(x, y):
        cx, cy = centre(x, y)
        return [(round(cx + size * math.cos(math.radians(60 * i - 30))), round(cy + size * math.sin(math.radians(60 * i - 30))))
                for i in range(6)], [(cx + size * math.cos(math.radians(60 * i - 30)), cy + size * math.sin(math.radians(60 * i - 30)))
                                     for i in range(6)]
    W = int(pps * w + pps / 2)
    H = int(math.ceil(rowh * (h - 1) + 2 * size))
    return centre, verts, W, H


def render_grid_svg(rc, gj, st):
    w, h, pps = gj["w"], gj["h"], rc["params"]["pps"]
    g = gj["cells"]
    col = {WALLC: st["rock"], FLOOR: st["floor"], DOOR: st["door"], TREE: st["tree"]}
    if gj["grid"] == "hex":
        centre, verts, W, H = hex_geometry(w, h, pps)
        o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
             '<rect width="100%%" height="100%%" fill="%s"/>' % st["bg"], '<g class="grid" stroke="%s" stroke-width="1">'
             % st["grid"]]
        for y in range(h):
            for x in range(w):
                v, _ = verts(x, y)
                o.append('<polygon points="%s" fill="%s"/>' % (" ".join("%d,%d" % p for p in v), col[g[y][x]]))
        o.append("</g>")
        cands = [(rc["name"], W / 2, 30.0, 22.0)]
    else:
        W, H = w * pps, h * pps
        o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
             '<rect width="100%%" height="100%%" fill="%s"/>' % st["rock"]]
        for y in range(h):
            x = 0
            while x < w:
                c = g[y][x]
                x1 = x
                while x1 < w and g[y][x1] == c:
                    x1 += 1
                if c != WALLC:
                    o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                             % (x * pps, y * pps, (x1 - x) * pps, pps, col[c]))
                x = x1
        o.append('<g class="grid" stroke="%s" stroke-width="1">' % st["grid"])
        for x in range(w + 1):
            o.append('<line x1="%d" y1="0" x2="%d" y2="%d"/>' % (x * pps, x * pps, H))
        for y in range(h + 1):
            o.append('<line x1="0" y1="%d" x2="%d" y2="%d"/>' % (y * pps, W, y * pps))
        o.append("</g>")
        o.append('<g class="walls" stroke="%s" stroke-width="%d" stroke-linecap="square">' % (st["wall"], max(2, pps // 12)))
        for (a, b) in gj["walls"]:
            o.append('<line x1="%d" y1="%d" x2="%d" y2="%d"/>' % (a[0] * pps, a[1] * pps, b[0] * pps, b[1] * pps))
        o.append("</g>")
        cands = []
        for r in gj.get("rooms", []):
            cands.append((str(r["id"] + 1), (r["x"] + r["w"] / 2) * pps, (r["y"] + r["h"] / 2) * pps + pps * 0.3,
                          max(10.0, pps * 0.55)))
        cands.insert(0, (rc["name"], W / 2, pps * 0.75, max(14.0, pps * 0.6)))
    labs, _ = place_labels(cands, W, H, st["mono"])
    o.append(labels_svg(labs, st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def gen_grid(kind, seed, out, w, h, method="bsp", grid="square", pps=None, style=None, version="0.5.0",
             name_style=None):
    t0 = time.perf_counter()
    rng = Rng(seed, 2 if kind == "dungeon" else 3)
    lang = mpw_names.make_language(seed, name_style)
    namer = mpw_names.Namer(lang)
    pps = int(pps or (70 if kind == "dungeon" else 100))
    if pps < 8:
        raise ValueError("--pps must be at least 8")
    if grid == "hex" and pps % 2:
        raise ValueError("hex grids need an even --pps so hex centres land on whole pixels")
    if w < 12 or h < 10:
        raise ValueError("a %s needs at least 12x10 squares" % kind)
    rooms = []
    lights = []
    if kind == "dungeon":
        if method == "bsp":
            g, rr = bsp_dungeon(w, h, rng)
            rooms = [dict(id=i, x=r[0], y=r[1], w=r[2], h=r[3]) for i, r in enumerate(rr)]
        elif method == "cave":
            g, _ = cave_dungeon(w, h, rng)
        else:
            raise ValueError("unknown dungeon method %r (bsp, cave)" % method)
        for r in rooms:
            lights.append(dict(x=r["x"] + r["w"] / 2, y=r["y"] + r["h"] / 2, range=max(r["w"], r["h"]),
                               color="ffeccd8b"))
        if not rooms:
            fl = [(x, y) for y in range(h) for x in range(w) if g[y][x] == FLOOR]
            for i in range(max(1, len(fl) // 120)):
                x, y = fl[G.h64(seed, 55, i) % len(fl)]
                lights.append(dict(x=x + 0.5, y=y + 0.5, range=5, color="ff9fd3ff"))
        fl = [(x, y) for y in range(h) for x in range(w) if g[y][x] in PASS]
        if rooms:
            r0 = rooms[0]
            entrance = [r0["x"] + r0["w"] // 2, r0["y"] + r0["h"] // 2]
        else:
            entrance = list(min(fl))
        nb = nbrs4
    else:
        method = None
        if grid == "hex":
            g, lights = battle_hex(w, h, rng)
            nb = nbrs_hex
        else:
            g, lights = battle_square(w, h, rng)
            nb = nbrs4
        edge = {(x, y) for y in range(h) for x in range(w) if x in (0, w - 1) or y in (0, h - 1)}
        keep = set(fill_pockets(g, w, h, nb, edge))
        entrance = list(min(p for p in edge if p in keep))
    cells = ["".join(r) for r in g]
    walls = wall_segments(g, w, h, border_walls=(kind == "dungeon")) if grid == "square" else []
    trees = [[x, y] for y in range(h) for x in range(w) if g[y][x] == TREE]
    portals = door_portals(g, w, h) if grid == "square" else []
    name = namer.name(kind, (seed,))
    gj = dict(w=w, h=h, grid=grid, cells=cells, rooms=rooms, entrance=entrance,
              walls=[[list(a), list(b)] for a, b in walls], portals=portals, lights=lights, trees=trees)
    feats = []
    for r in rooms:
        x, y, rw, rh = r["x"], r["y"], r["w"], r["h"]
        feats.append({"type": "Feature", "properties": dict(kind="room", id=r["id"], number=r["id"] + 1),
                      "geometry": {"type": "Polygon", "coordinates": [[[x, y], [x + rw, y], [x + rw, y + rh],
                                                                        [x, y + rh], [x, y]]]}})
    for p in portals:
        feats.append({"type": "Feature", "properties": dict(kind="door"),
                      "geometry": {"type": "LineString", "coordinates": p["bounds"]}})
    for a, b in walls:
        feats.append({"type": "Feature", "properties": dict(kind="wall"),
                      "geometry": {"type": "LineString", "coordinates": [list(a), list(b)]}})
    for L in lights:
        feats.append({"type": "Feature", "properties": dict(kind="light", range=L["range"], color=L["color"]),
                      "geometry": {"type": "Point", "coordinates": [L["x"], L["y"]]}})
    feats.append({"type": "Feature", "properties": dict(kind="entrance"),
                  "geometry": {"type": "Point", "coordinates": [entrance[0] + 0.5, entrance[1] + 0.5]}})
    recipe = dict(kind=kind, seed=seed, generator=PLACES_VERSION, tool="mapwright", tool_version=version, name=name,
                  params=dict(w=w, h=h, method=method, grid=grid, pps=pps, style=style, name_style=name_style),
                  projection=dict(kind="grid", units="square", axes="x east, y south, origin top-left"),
                  extent=[0, 0, w, h], parent=None, language=lang)
    t1 = time.perf_counter()
    write_place(out, recipe, feats, [dict(kind=kind, id=0, name=name)], gj, None)
    t = dict(generate=round(t1 - t0, 3), write_render=round(time.perf_counter() - t1, 3),
             total=round(time.perf_counter() - t0, 3))
    return dict(out=out, kind=kind, name=name, w=w, h=h, grid=grid, pps=pps, rooms=len(rooms), doors=len(portals),
                walls=len(walls), lights=len(lights), floor=sum(c in PASS for r in cells for c in r), times=t)


# ------------------------------------------------------------------ folder, render
def write_place(out, recipe, feats, names, gj, _):
    os.makedirs(out, exist_ok=True)
    dump(os.path.join(out, "features.geojson"), {"type": "FeatureCollection", "features": feats})
    dump(os.path.join(out, "names.json"), {"seed": recipe["seed"], "language": recipe["language"], "names": names})
    dump(os.path.join(out, "sources.json"), {"files": [], "note": "generated; nothing fetched"})
    dump(os.path.join(out, "recipe.json"), recipe)
    sname, st = pstyle(recipe["params"].get("style"), recipe["kind"])
    if gj is not None:
        dump(os.path.join(out, "grid.json"), gj)
        if gj["grid"] == "square":
            with open(os.path.join(out, "map.png"), "wb") as f:
                f.write(grid_png([list(r) for r in gj["cells"]], gj["w"], gj["h"], recipe["params"]["pps"], st))
    svg = render_svg(out, sname)
    with open(os.path.join(out, "map.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)


def render_svg(d, style_name=None):
    rc = load(d, "recipe.json")
    _, st = pstyle(style_name, rc["kind"])
    if rc["kind"] == "city":
        return render_city_svg(rc, load(d, "features.geojson")["features"], st)
    return render_grid_svg(rc, load(d, "grid.json"), st)


# ------------------------------------------------------------------ Universal VTT
def uvtt(d):
    rc = load(d, "recipe.json")
    if rc["kind"] not in ("dungeon", "battle"):
        raise ValueError("Universal VTT export is for dungeon and battle recipes, not %s" % rc["kind"])
    gj = load(d, "grid.json")
    if gj["grid"] != "square":
        raise ValueError("Universal VTT is square-grid only; a hex battle map exports as map.svg")
    with open(os.path.join(d, "map.png"), "rb") as f:
        img = f.read()
    return {
        "format": 0.3,
        "resolution": {"map_origin": {"x": 0, "y": 0}, "map_size": {"x": gj["w"], "y": gj["h"]},
                       "pixels_per_grid": int(rc["params"]["pps"])},
        "line_of_sight": [[{"x": a[0], "y": a[1]}, {"x": b[0], "y": b[1]}] for a, b in gj["walls"]],
        "objects_line_of_sight": [[{"x": x, "y": y}, {"x": x + 1, "y": y}, {"x": x + 1, "y": y + 1},
                                   {"x": x, "y": y + 1}, {"x": x, "y": y}] for x, y in gj.get("trees", [])],
        "portals": [{"position": {"x": p["x"] + 0.5, "y": p["y"] + 0.5},
                     "bounds": [{"x": b[0], "y": b[1]} for b in p["bounds"]],
                     "rotation": p["rotation"], "closed": True, "freestanding": False} for p in gj["portals"]],
        "environment": {"baked_lighting": False, "ambient_light": "ffffffff"},
        "lights": [{"position": {"x": L["x"], "y": L["y"]}, "range": L["range"], "intensity": 1,
                    "color": L["color"], "shadows": True} for L in gj["lights"]],
        "image": base64.b64encode(img).decode("ascii"),
    }


def write_uvtt(d, out):
    data = uvtt(d)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, separators=(",", ":"))
    return data


def uvtt_bars(text):
    """Load a Universal VTT file back and test it: keys, integer ppg, walls inside, portals on walls, image size."""
    bars = []
    try:
        u = json.loads(text)
        res = u["resolution"]
        mx, my = res["map_size"]["x"], res["map_size"]["y"]
        ppg = res["pixels_per_grid"]
        los = u["line_of_sight"]
        ok = isinstance(ppg, int) and ppg > 0
        bars.append(("uvtt: loads, pixels_per_grid a whole number", ok, "ppg %r, %d walls, %d portals, %d lights"
                     % (ppg, len(los), len(u["portals"]), len(u["lights"]))))
        out = [p for line in los + u.get("objects_line_of_sight", []) for p in line
               if not (0 <= p["x"] <= mx and 0 <= p["y"] <= my)]
        bars.append(("uvtt: walls inside the image", bool(los) and not out, "%d walls, %d points outside %dx%d"
                     % (len(los), len(out), mx, my)))
        segs = [((l[i]["x"], l[i]["y"]), (l[i + 1]["x"], l[i + 1]["y"])) for l in los for i in range(len(l) - 1)]
        off = 0
        for p in u["portals"]:
            for b in p["bounds"]:
                if not any(seg_dist(b["x"], b["y"], *a, *c) <= 1e-6 for a, c in segs):
                    off += 1
        bars.append(("uvtt: every door ends on a wall", off == 0, "%d door ends off a wall" % off))
        img = base64.b64decode(u["image"])
        iw, ih = png_size(img)
        bars.append(("uvtt: image matches the grid", (iw, ih) == (mx * ppg, my * ppg),
                     "%dx%d px for %dx%d squares at %d" % (iw, ih, mx, my, ppg)))
        # colours are AARRGGBB (the Foundry importer drops the first two characters); a portal with closed false
        # imports as a window; a wall under a portal doubles the door wall the importer builds from its bounds
        cols = [u["environment"]["ambient_light"]] + [L["color"] for L in u["lights"]]
        badc = [c for c in cols if not (isinstance(c, str) and len(c) == 8 and c[:2].lower() == "ff"
                                        and all(ch in "0123456789abcdefABCDEF" for ch in c))]
        opened = sum(1 for p in u["portals"] if p.get("closed") is not True)
        over = 0
        for p in u["portals"]:
            b0, b1 = p["bounds"][0], p["bounds"][-1]
            mid = ((b0["x"] + b1["x"]) / 2.0, (b0["y"] + b1["y"]) / 2.0)
            if any(seg_dist(mid[0], mid[1], *a, *c) <= 1e-6 for a, c in segs):
                over += 1
        bars.append(("uvtt: colours alpha first, doors closed, no wall over a door", not badc and not opened and not over,
                     "%d colours not ffRRGGBB, %d portals not closed, %d doors under a wall" % (len(badc), opened, over)))
    except (ValueError, KeyError, TypeError) as e:
        bars.append(("uvtt: loads", False, str(e)))
    return bars


# ------------------------------------------------------------------ check
def regenerate(d, tmp):
    rc = load(d, "recipe.json")
    p = rc["params"]
    if rc["kind"] == "city":
        par = rc.get("parent")
        ppath = None
        if par:
            ppath = par["path"] if os.path.isabs(par["path"]) else os.path.normpath(os.path.join(d, par["path"]))
        gen_city(rc["seed"], tmp, p["bands"], p["wall"], p["spokes"], p["ring_m"], p["lot_m2"], ppath,
                 par and par["settlement"], p["sea"], p["river"], p["style"], rc["tool_version"], p["name_style"],
                 ref=par and par["path"])
    else:
        gen_grid(rc["kind"], rc["seed"], tmp, p["w"], p["h"], p["method"] or "bsp", p["grid"], p["pps"], p["style"],
                 rc["tool_version"], p["name_style"])


def _city_bars(d):
    fc = load(d, "features.geojson")["features"]
    by = {}
    for f in fc:
        by.setdefault(f["properties"]["kind"], []).append(f)
    key = lambda c: (round(c[0], 2), round(c[1], 2))  # noqa: E731
    adj = {}
    for f in by.get("street", []):
        c = f["geometry"]["coordinates"]
        for i in range(len(c) - 1):
            a, b = key(c[i]), key(c[i + 1])
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    plaza = by["plaza"][0]["geometry"]["coordinates"][0]
    start = key(plaza[0])
    seen = {start}
    st = [start]
    while st:
        n = st.pop()
        for m in adj.get(n, ()):
            if m not in seen:
                seen.add(m)
                st.append(m)
    bars = [("city: every street reachable from the market", len(seen) == len(adj),
             "%d of %d street nodes reached" % (len(seen), len(adj)))]
    blocks = {f["properties"]["id"]: [tuple(c) for c in f["geometry"]["coordinates"][0][:-1]] for f in by.get("block", [])}
    bad = [i for i, poly in blocks.items() if sum(key(p) in seen for p in poly) < 2]
    bars.append(("city: every block fronts a reached street", not bad and bool(blocks),
                 "%d blocks, %d without a reached street edge" % (len(blocks), len(bad))))
    nolot = bad_shape = 0
    lots = by.get("lot", [])
    for f in lots:
        poly = [tuple(c) for c in f["geometry"]["coordinates"][0][:-1]]
        bp = blocks[f["properties"]["block"]]
        if area(poly) == 0 or not simple(poly) or not all(on_boundary(p, bp, 0.02) or _inside(p, bp) for p in poly):
            bad_shape += 1
        if not frontage(poly, bp, 0.02):
            nolot += 1
    built = {f["properties"]["lot"] for f in by.get("building", [])}
    builtbad = sum(1 for f in lots if f["properties"]["id"] in built and not f["properties"]["frontage"])
    bars.append(("city: lots simple, positive and inside their block", bad_shape == 0, "%d lots, %d bad"
                 % (len(lots), bad_shape)))
    bars.append(("city: every built lot has street frontage", builtbad == 0,
                 "%d lots, %d without frontage (left as yards, never built on), %d built without frontage"
                 % (len(lots), nolot, builtbad)))
    walls = by.get("wall", [])
    if walls:
        wsegs = [(w["geometry"]["coordinates"][i], w["geometry"]["coordinates"][i + 1]) for w in walls
                 for i in range(len(w["geometry"]["coordinates"]) - 1)]
        gates = [tuple(g["geometry"]["coordinates"]) for g in by.get("gate", [])]
        offg = sum(1 for g in gates if not any(seg_dist(*g, *a, *b) <= 1e-6 for a, b in wsegs))
        # every street crossing or touching the wall line from outside does so at a gate
        cross = 0
        gk = {key(g) for g in gates}
        for f in by.get("street", []):
            if f["properties"]["rank"] == "wall-street":
                continue
            c = f["geometry"]["coordinates"]
            for j in range(len(c) - 1):
                for wa, wb in wsegs:
                    if seg_cross(c[j], c[j + 1], wa, wb):
                        cross += 1
        closed = all(w["geometry"]["coordinates"][0] == w["geometry"]["coordinates"][-1] for w in walls)
        outward = _outward_without_gate(by, wsegs, gk, key)
        bars.append(("city: gates on the wall, streets cross it only at gates", offg == 0 and cross == 0 and outward == 0,
                     "%d gates (%d off the wall), %d streets cut the wall, %d leave it without a gate; wall %s"
                     % (len(gates), offg, cross, outward, "closed" if closed else "open to the sea")))
    return bars


def _inside(p, poly):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def _outward_without_gate(by, wsegs, gk, key):
    """Radial streets from a wall node that point away from the centre must start at a gate."""
    on = set()
    for f in by.get("street", []):
        for c in f["geometry"]["coordinates"]:
            if any(seg_dist(c[0], c[1], *wa, *wb) <= 1e-6 for wa, wb in wsegs):
                on.add(key(c))
    bad = 0
    for f in by.get("street", []):
        if f["properties"]["rank"] in ("wall-street",) or len(f["geometry"]["coordinates"]) != 2:
            continue
        a, b = [key(c) for c in f["geometry"]["coordinates"]]
        for p, q in ((a, b), (b, a)):
            if p in on and q not in on and math.hypot(*q) > math.hypot(*p) and p not in gk:
                bad += 1
    return bad


def _grid_bars(d):
    rc = load(d, "recipe.json")
    gj = load(d, "grid.json")
    w, h, pps = gj["w"], gj["h"], rc["params"]["pps"]
    g = gj["cells"]
    nb = nbrs_hex if gj["grid"] == "hex" else nbrs4
    ex, ey = gj["entrance"]
    seen = {(ex, ey)}
    st = [(ex, ey)]
    while st:
        x, y = st.pop()
        for nx, ny in nb(x, y):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and g[ny][nx] in PASS:
                seen.add((nx, ny))
                st.append((nx, ny))
    floor = [(x, y) for y in range(h) for x in range(w) if g[y][x] in PASS]
    bars = [("%s: every floor square reachable from the entrance" % rc["kind"],
             g[ey][ex] in PASS and len(seen) == len(floor), "%d of %d passable squares reached" % (len(seen), len(floor)))]
    rooms = gj.get("rooms", [])
    if rooms:
        unr = [r["id"] for r in rooms if not any((x, y) in seen for x in range(r["x"], r["x"] + r["w"])
                                                 for y in range(r["y"], r["y"] + r["h"]))]
        ov = 0
        for i in range(len(rooms)):
            for j in range(i + 1, len(rooms)):
                a, b = rooms[i], rooms[j]
                if a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]:
                    ov += 1
        bars.append(("dungeon: every room reached, none overlap", not unr and ov == 0,
                     "%d rooms, %d unreached, %d overlapping pairs" % (len(rooms), len(unr), ov)))
    doors = [(x, y) for y in range(h) for x in range(w) if g[y][x] == DOOR]
    if doors or rooms:
        bad = 0
        for x, y in doors:
            ns = (x - 1 >= 0 and g[y][x - 1] in PASS and x + 1 < w and g[y][x + 1] in PASS) or \
                 (y - 1 >= 0 and g[y - 1][x] in PASS and y + 1 < h and g[y + 1][x] in PASS)
            if (x, y) not in seen or not ns:
                bad += 1
        bars.append(("%s: every door reached and joins two floors" % rc["kind"], bad == 0,
                     "%d doors, %d bad" % (len(doors), bad)))
    if gj["grid"] == "square":
        deg = {}
        for a, b in gj["walls"]:
            for p in (tuple(a), tuple(b)):
                deg[p] = deg.get(p, 0) + 1
        # a vertex on the open map edge of a battle map may end a wall
        loose = [p for p, k in deg.items() if k % 2 and not (rc["kind"] == "battle" and (p[0] in (0, w) or p[1] in (0, h)))]
        bars.append(("%s: walls closed (every wall end meets another)" % rc["kind"], not loose,
                     "%d wall runs, %d loose ends" % (len(gj["walls"]), len(loose))))
        with open(os.path.join(d, "map.png"), "rb") as f:
            iw, ih = png_size(f.read(32))
        bars.append(("%s: grid on whole pixels" % rc["kind"], isinstance(pps, int) and (iw, ih) == (w * pps, h * pps),
                     "map.png %dx%d = %dx%d squares x %d px" % (iw, ih, w, h, pps)))
        bars += uvtt_bars(json.dumps(uvtt(d)))
    else:
        _, verts, _, _ = hex_geometry(w, h, pps)
        drift = 0.0
        for y in range(h):
            for x in range(w):
                v, exact = verts(x, y)
                drift = max(drift, max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(v, exact)))
        bars.append(("battle: hex grid on whole pixels", pps % 2 == 0 and drift <= 0.71,
                     "pps %d (even: centres on whole px across), vertices rounded to whole px, max drift %.2f px"
                     % (pps, drift)))
    return bars


def _bytes(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def check(d, determinism=True, labels=True):
    rc = load(d, "recipe.json")
    bars = _city_bars(d) if rc["kind"] == "city" else _grid_bars(d)
    if determinism:
        tmp = tempfile.mkdtemp(prefix="mpw-")
        try:
            regenerate(d, tmp)
            diff = [n for n in FILES if _bytes(os.path.join(d, n)) != _bytes(os.path.join(tmp, n))]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        bars.append(("same seed gives byte-identical files", not diff, "differs: %s" % ", ".join(diff) if diff
                     else "%d files identical" % sum(os.path.exists(os.path.join(d, n)) for n in FILES)))
    if labels:
        import mpw_render as R
        with open(os.path.join(d, "map.svg"), encoding="utf-8") as f:
            bars += list(R.label_bars(f.read()))
    return [(i + 1, n, ok, det) for i, (n, ok, det) in enumerate(bars)]
