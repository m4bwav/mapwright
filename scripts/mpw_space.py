"""mapwright space: seeded sectors, star systems, planet textures and deck plans as recipe folders, their proof
bars and exports. Standard library only.

Methods follow references/scifi-maps.md:
- sector: flat-topped hex grid in columns (a 32x40 sector of sixteen 8x10 subsectors, or one subsector), one
  world per occupied hex, routes as the relative neighbourhood graph (RNG) of the hex centres joined with the
  Euclidean minimum spanning tree, so the graph is always connected (section 4.2); routes within the jump range
  are jump routes, longer ones are marked long. Written as JSON and as a T5 tab-delimited sector file (3.2).
  With --real, the nearby stars bundled in data/near-stars.csv placed from RA, Dec and parallax (section 1).
- system: one main-sequence star (mass, luminosity, radius), planets on roughly geometric spacing kept at least
  12 mutual Hill radii apart, kinds by habitable zone and snow line, moons inside the Hill sphere (sections 6, 7).
  Drawn as a schematic (equal spacing, not to scale) and to scale (linear AU, body markers not to scale).
- planet: equirectangular 2:1 texture from 3D value noise sampled at each pixel's point on the unit sphere, so
  there is no seam and no pole pinch (section 8). Kinds: rocky, ice, ocean, gas, moon (power-law craters), locked
  (tidally locked, substellar point at the centre of the texture).
- deck: square grid of 1.5 m squares inside a ship or station hull, a spine corridor, rooms on both sides each
  with a door, an airlock with an inner and an outer door, lifts at the same square on every deck (section 9).
"""
import csv
import io
import json
import math
import os
import shutil
import struct
import tempfile
import time
import zlib
from xml.sax.saxutils import escape

import mpw_gen as G
import mpw_names
import mpw_places as P

SPACE_VERSION = "space-1"
KINDS = ("sector", "system", "planet", "deck")
PLANET_KINDS = ("rocky", "ice", "ocean", "gas", "moon", "locked")
HERE = os.path.dirname(os.path.abspath(__file__))
NEAR_STARS = os.path.join(HERE, "data", "near-stars.csv")
SQ3 = math.sqrt(3.0)
EHEX = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"

# tolerances, measured on the sweep in TESTS.md (T-20261115-3)
SEAM_FACTOR = 2.5      # seam column difference vs the 90th percentile adjacent-column difference
POLE_FACTOR = 0.5      # std of the top or bottom row vs the std of the whole texture (width 512 or more)
CRATER_SLOPE_TOL = 0.35
HILL_MIN = 10.0        # rule of thumb from references/scifi-maps.md section 6; generator keeps 12
DIST_TOL_PC = 1e-6


def _r(v, n=4):
    return round(v, n)


def _svg_head(w, h, bg):
    return ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (w, h, w, h),
            '<rect width="%d" height="%d" fill="%s"/>' % (w, h, bg)]


SST = dict(bg="#0b1020", ink="#dfe8ff", grid="#2a3558", route="#6f8fd8", long="#c9a14a", star="#fff4d6",
           water="#5fa8ff", dry="#d9a35b", font="Verdana, Arial, sans-serif", halo="#0b1020", mono=False,
           hz="#1f4d2e", orbit="#45557f")


# ================================================================== sector
def hex_center(col, row, r):
    """Flat-topped hexes in columns; 0-based odd columns sit half a hex lower (odd-q)."""
    return 1.5 * r * col, SQ3 * r * (row + 0.5 * (col & 1))


def hex_dist(a, b):
    def cube(c, rw):
        q = c
        z = rw - (c - (c & 1)) // 2
        return q, -q - z, z
    x1, y1, z1 = cube(*a)
    x2, y2, z2 = cube(*b)
    return max(abs(x1 - x2), abs(y1 - y2), abs(z1 - z2))


def _d(p, q):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p, q)))


def emst(pts):
    """Prim's algorithm, O(n^2): the edges of the Euclidean minimum spanning tree."""
    n = len(pts)
    if n < 2:
        return []
    best = [float("inf")] * n
    frm = [-1] * n
    used = [False] * n
    best[0] = 0.0
    out = []
    for _ in range(n):
        i = min((k for k in range(n) if not used[k]), key=lambda k: (best[k], k))
        used[i] = True
        if frm[i] >= 0:
            out.append((min(i, frm[i]), max(i, frm[i])))
        for k in range(n):
            if not used[k]:
                dk = _d(pts[i], pts[k])
                if dk < best[k]:
                    best[k] = dk
                    frm[k] = i
    return out


def rng_graph(pts, radius=None):
    """Relative neighbourhood graph edges (i < j). With a radius, only pairs within it are tested (witnesses of
    a pair lie within d(p, q) of p, so they are inside the same radius); the EMST is added so the graph stays
    connected whatever the radius."""
    n = len(pts)
    if radius is None:
        nb = [list(range(n)) for _ in range(n)]
    else:
        cell = radius
        buckets = {}
        for i, p in enumerate(pts):
            buckets.setdefault((int(p[0] // cell), int(p[1] // cell)), []).append(i)
        nb = []
        for i, p in enumerate(pts):
            bx, by = int(p[0] // cell), int(p[1] // cell)
            lst = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for k in buckets.get((bx + dx, by + dy), ()):
                        if k != i and _d(p, pts[k]) <= radius:
                            lst.append(k)
            nb.append(sorted(lst))
    edges = set()
    for i in range(n):
        for j in nb[i]:
            if j <= i:
                continue
            dij = _d(pts[i], pts[j])
            if not any(max(_d(pts[i], pts[k]), _d(pts[j], pts[k])) < dij for k in nb[i] if k != j):
                edges.add((i, j))
    edges.update(emst(pts))
    return sorted(edges)


def components(n, edges):
    par = list(range(n))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for a, b in edges:
        par[f(a)] = f(b)
    return len({f(i) for i in range(n)})


def bridges(n, edges):
    adj = [[] for _ in range(n)]
    for k, (a, b) in enumerate(edges):
        adj[a].append((b, k))
        adj[b].append((a, k))
    disc = [-1] * n
    low = [0] * n
    t = [0]
    out = 0
    for s in range(n):
        if disc[s] >= 0:
            continue
        disc[s] = low[s] = t[0]
        t[0] += 1
        stack = [(s, -1, iter(adj[s]))]
        while stack:
            v, pe, it = stack[-1]
            for w, k in it:
                if k == pe:
                    continue
                if disc[w] < 0:
                    disc[w] = low[w] = t[0]
                    t[0] += 1
                    stack.append((w, k, iter(adj[w])))
                    break
                low[v] = min(low[v], disc[w])
            else:
                stack.pop()
                if stack:
                    u = stack[-1][0]
                    low[u] = min(low[u], low[v])
                    if low[v] > disc[u]:
                        out += 1
    return out


def _d6(r, n=2):
    return sum(r.randint(1, 6) for _ in range(n))


def _clamp(v, a, b):
    return max(a, min(b, v))


STARS = [("M2 V", 30), ("M5 V", 20), ("K5 V", 14), ("K0 V", 10), ("G2 V", 10), ("G8 V", 6), ("F5 V", 6),
         ("A2 V", 2), ("M0 III", 2)]


def _weighted(r, table):
    tot = sum(w for _, w in table)
    x = r.random() * tot
    for v, w in table:
        x -= w
        if x < 0:
            return v
    return table[-1][0]


def world_code(r):
    """A random UWP-shaped code to fill the T5 columns (not any setting's data)."""
    size = _d6(r) - 2
    atm = 0 if size == 0 else _clamp(_d6(r) - 7 + size, 0, 15)
    hyd = 0 if size <= 1 else _clamp(_d6(r) - 7 + atm, 0, 10)
    pop = _d6(r) - 2
    gov = 0 if pop == 0 else _clamp(_d6(r) - 7 + pop, 0, 15)
    law = 0 if pop == 0 else _clamp(_d6(r) - 7 + gov, 0, 9)
    s = _d6(r)
    port = "X" if s <= 2 else "E" if s <= 4 else "D" if s <= 6 else "C" if s <= 8 else "B" if s <= 10 else "A"
    tech = _clamp(r.randint(1, 6) + {"A": 6, "B": 4, "C": 2, "X": -4}.get(port, 0) + (1 if size <= 4 else 0)
                  + (2 if pop >= 9 else 0), 0, 15)
    if pop == 0:
        tech = 0
    uwp = "%s%s%s%s%s%s%s-%s" % (port, EHEX[size], EHEX[atm], EHEX[hyd], EHEX[pop], EHEX[gov], EHEX[law], EHEX[tech])
    belts = max(0, r.randint(-2, 2))
    giants = max(0, r.randint(-1, 4))
    pbg = "%d%d%d" % (0 if pop == 0 else r.randint(1, 9), belts, giants)
    return dict(uwp=uwp, hyd=hyd, pop=pop, pbg=pbg, worlds=1 + belts + giants + r.randint(0, 8))


T5_COLS = ["Hex", "Name", "UWP", "Bases", "Remarks", "Zone", "PBG", "Allegiance", "Stars", "{Ix}", "(Ex)", "[Cx]",
           "Nobility", "W"]


def t5_tab(worlds):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n")
    w.writerow(T5_COLS)
    for wd in worlds:
        w.writerow([wd["hex"], wd["name"], wd["uwp"], "", "", "", wd["pbg"], "Na", wd["star"], "", "", "", "",
                    wd["w"]])
    return buf.getvalue()


def read_t5_tab(text):
    """Reads any T5 tab-delimited file by its header (field order is not fixed)."""
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    if not rows:
        raise ValueError("empty sector file")
    head = rows[0]
    for need in ("Hex", "Name", "UWP"):
        if need not in head:
            raise ValueError("T5 tab file lacks a %s column" % need)
    return [dict(zip(head, r)) for r in rows[1:] if r]


def load_near_stars(path=NEAR_STARS):
    out = []
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
    for row in csv.DictReader(lines):
        ra, dec, plx = float(row["ra_deg"]), float(row["dec_deg"]), float(row["parallax_mas"])
        d = 1000.0 / plx
        rr, dd = math.radians(ra), math.radians(dec)
        out.append(dict(name=row["name"], ra=ra, dec=dec, plx=plx, star=row["spectral"],
                        xyz=[d * math.cos(dd) * math.cos(rr), d * math.cos(dd) * math.sin(rr), d * math.sin(dd)]))
    return out


def gen_sector(seed, out, size="subsector", density=0.5, jump=2, real=False, radius_pc=6.0, version="0.6.0",
               name_style=None):
    t0 = time.perf_counter()
    r = P.Rng(seed, 101)
    lang = mpw_names.make_language(seed, name_style)
    namer = mpw_names.Namer(lang)
    params = dict(size=size, density=density, jump=jump, real=bool(real), radius_pc=radius_pc, name_style=name_style)
    if real:
        stars = [s for s in load_near_stars() if 1000.0 / s["plx"] <= radius_pc]
        sol = dict(name="Sol", ra=0.0, dec=0.0, plx=None, star="G2 V", xyz=[0.0, 0.0, 0.0])
        stars = [sol] + sorted(stars, key=lambda s: 1000.0 / s["plx"])
        pts = [s["xyz"] for s in stars]
        edges = rng_graph(pts)
        worlds = [dict(id=i, name=s["name"], star=s["star"], ra=s["ra"], dec=s["dec"], parallax_mas=s["plx"],
                       dist_pc=_r(0.0 if s["plx"] is None else 1000.0 / s["plx"], 9),
                       xyz=[_r(v, 9) for v in s["xyz"]]) for i, s in enumerate(stars)]
        routes = [dict(a=a, b=b, pc=_r(_d(pts[a], pts[b]), 4), kind="jump" if _d(pts[a], pts[b]) <= jump else "long")
                  for a, b in edges]
        grid = None
    else:
        cols, rows = (8, 10) if size == "subsector" else (32, 40)
        if size not in ("subsector", "sector"):
            raise ValueError("--size is subsector or sector")
        if not 0.05 <= density <= 1.0:
            raise ValueError("--density must be in 0.05..1")
        worlds = []
        for c in range(cols):
            for rw in range(rows):
                if r.random() < density:
                    wc = world_code(r)
                    st = _weighted(r, STARS)
                    worlds.append(dict(id=len(worlds), col=c, row=rw, hex="%02d%02d" % (c + 1, rw + 1),
                                       name=namer.name("world", (c, rw)), uwp=wc["uwp"], hyd=wc["hyd"], pop=wc["pop"],
                                       pbg=wc["pbg"], star=st, w=wc["worlds"]))
                else:
                    # keep the draw count fixed per hex so one change never shifts later hexes
                    for _ in range(20):
                        r.random()
        if len(worlds) < 2:
            raise ValueError("fewer than two worlds; raise --density")
        pts = [hex_center(w["col"], w["row"], 1.0) for w in worlds]
        edges = rng_graph(pts, radius=SQ3 * max(jump, 3) + 1e-9)
        routes = []
        for a, b in edges:
            hd = hex_dist((worlds[a]["col"], worlds[a]["row"]), (worlds[b]["col"], worlds[b]["row"]))
            routes.append(dict(a=a, b=b, hexes=hd, kind="jump" if hd <= jump else "long"))
        grid = dict(cols=cols, rows=rows, layout="flat-top columns, 0-based odd columns half a hex lower (odd-q)",
                    subsectors="ABCDEFGHIJKLMNOP" if size == "sector" else "A")
    name = namer.name("sector", (seed,)) if not real else "Near stars within %.1f pc" % radius_pc
    sec = dict(name=name, grid=grid, worlds=worlds, routes=routes)
    recipe = dict(kind="sector", seed=int(seed), tool_version=version, space_version=SPACE_VERSION, params=params,
                  language=lang)
    t1 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    P.dump(os.path.join(out, "sector.json"), sec)
    if not real:
        with open(os.path.join(out, "sector.tab"), "w", encoding="utf-8", newline="\n") as f:
            f.write(t5_tab(worlds))
        names = [dict(kind="world", id=w["id"], name=w["name"]) for w in worlds]
        srcs = {"files": [], "note": "generated; nothing fetched"}
    else:
        names = [dict(kind="star", id=w["id"], name=w["name"]) for w in worlds]
        srcs = {"files": ["scripts/data/near-stars.csv"], "credit": _near_credit(),
                "note": "positions and parallaxes are measured facts; see the header of near-stars.csv"}
    P.dump(os.path.join(out, "names.json"), {"seed": int(seed), "language": lang, "names": names})
    P.dump(os.path.join(out, "sources.json"), srcs)
    P.dump(os.path.join(out, "recipe.json"), recipe)
    _write(out, "map.svg", render_sector_svg(recipe, sec))
    t = dict(generate=_r(t1 - t0, 3), total=_r(time.perf_counter() - t0, 3))
    return dict(out=out, kind="sector", name=name, worlds=len(worlds), routes=len(routes),
                long=sum(1 for x in routes if x["kind"] == "long"), times=t)


def _near_credit():
    with open(NEAR_STARS, encoding="utf-8") as f:
        return " ".join(ln[1:].strip() for ln in f if ln.startswith("#"))


def _write(out, name, text):
    with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_sector_svg(rc, sec, st=SST):
    if sec["grid"] is None:
        return _render_real_svg(sec, st)
    cols, rows = sec["grid"]["cols"], sec["grid"]["rows"]
    rad = 28.0 if cols <= 8 else 14.0
    m = 20.0
    top = 40.0
    w = int(1.5 * rad * cols + 0.5 * rad + 2 * m)
    h = int(SQ3 * rad * (rows + 0.5) + top + m + 10)
    o = _svg_head(w, h, st["bg"])
    o.append('<text x="%d" y="26" font-family="%s" font-size="16" fill="%s">%s</text>'
             % (m, st["font"], st["ink"], escape(sec["name"])))

    def ctr(c, rw):
        x, y = hex_center(c, rw, rad)
        return x + m + rad, y + top + SQ3 * rad / 2
    if cols > 8:
        for k in range(16):
            sx, sy = k % 4, k // 4
            x0, _ = ctr(sx * 8, 0)
            x1, _ = ctr(sx * 8 + 7, 0)
            _, y0 = ctr(0, sy * 10)
            _, y1 = ctr(0, sy * 10 + 9)
            o.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="60" fill="%s" opacity="0.18" '
                     'text-anchor="middle">%s</text>' % ((x0 + x1) / 2, (y0 + y1) / 2 + 20, st["font"], st["grid"],
                                                          "ABCDEFGHIJKLMNOP"[k]))
    path = []
    for c in range(cols):
        for rw in range(rows):
            cx, cy = ctr(c, rw)
            pts = [(cx + rad * math.cos(math.pi / 3 * i), cy + rad * math.sin(math.pi / 3 * i)) for i in range(6)]
            path.append("M" + "L".join("%.1f,%.1f" % p for p in pts) + "Z")
    o.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.8"/>' % ("".join(path), st["grid"]))
    W = sec["worlds"]
    for e in sec["routes"]:
        a, b = W[e["a"]], W[e["b"]]
        (x1, y1), (x2, y2) = ctr(a["col"], a["row"]), ctr(b["col"], b["row"])
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s/>'
                 % (x1, y1, x2, y2, st["route"] if e["kind"] == "jump" else st["long"], "1.6" if cols <= 8 else "1",
                    "" if e["kind"] == "jump" else ' stroke-dasharray="4 3"'))
    cands = []
    for wd in W:
        cx, cy = ctr(wd["col"], wd["row"])
        o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>'
                 % (cx, cy, 5 if cols <= 8 else 3, st["water"] if wd["hyd"] > 0 else st["dry"]))
        if cols <= 8:
            o.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="7" fill="%s" text-anchor="middle">%s</text>'
                     % (cx, cy - rad * 0.55, st["font"], st["grid"], wd["hex"]))
        cands.append((wd["name"], cx, cy + (rad * 0.62 if cols <= 8 else rad * 0.9), 9.0 if cols <= 8 else 6.0))
    labs, _ = P.place_labels(cands, w, h, False)
    o.append(P.labels_svg(labs, st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def _render_real_svg(sec, st):
    W = sec["worlds"]
    w = h = 760
    ext = max(max(abs(p["xyz"][0]), abs(p["xyz"][1])) for p in W) or 1.0
    s = (w / 2 - 70) / ext
    cx, cy = w / 2, h / 2 + 10

    def xy(p):
        return cx + p["xyz"][0] * s, cy - p["xyz"][1] * s
    o = _svg_head(w, h, st["bg"])
    o.append('<text x="20" y="26" font-family="%s" font-size="16" fill="%s">%s (equatorial x right, y up; '
             'z in brackets)</text>' % (st["font"], st["ink"], escape(sec["name"])))
    for k in range(1, int(ext) + 1):
        o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="0.6"/>'
                 % (cx, cy, k * s, st["grid"]))
    for e in sec["routes"]:
        (x1, y1), (x2, y2) = xy(W[e["a"]]), xy(W[e["b"]])
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2"%s/>'
                 % (x1, y1, x2, y2, st["route"] if e["kind"] == "jump" else st["long"],
                    "" if e["kind"] == "jump" else ' stroke-dasharray="4 3"'))
    cands = []
    for p in W:
        x, y = xy(p)
        o.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x, y, st["star"]))
        cands.append(("%s %.2f pc [%+.1f]" % (p["name"], p["dist_pc"], p["xyz"][2]), x, y + 14, 9.0))
    o.append('<text x="20" y="%d" font-family="%s" font-size="10" fill="%s">rings every 1 pc; routes: relative '
             'neighbourhood graph in 3D</text>' % (h - 14, st["font"], st["grid"]))
    labs, _ = P.place_labels(cands, w, h, False)
    o.append(P.labels_svg(labs, st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def _sector_bars(d):
    rc = P.load(d, "recipe.json")
    sec = P.load(d, "sector.json")
    W, R = sec["worlds"], sec["routes"]
    edges = [(e["a"], e["b"]) for e in R]
    nc = components(len(W), edges)
    bars = [("sector: route graph connected", nc == 1 and len(W) > 1,
             "%d worlds, %d routes, %d component(s), %d bridges (chokepoints listed, not failed)"
             % (len(W), len(R), nc, bridges(len(W), edges)))]
    jump = rc["params"]["jump"]
    if sec["grid"] is not None:
        bad = 0
        for e in R:
            hd = hex_dist((W[e["a"]]["col"], W[e["a"]]["row"]), (W[e["b"]]["col"], W[e["b"]]["row"]))
            if hd != e["hexes"] or (e["kind"] == "jump") != (hd <= jump):
                bad += 1
        bars.append(("sector: jump routes within jump %d, longer ones marked long" % jump, bad == 0,
                     "%d jump, %d long, %d mislabelled" % (sum(e["kind"] == "jump" for e in R),
                                                           sum(e["kind"] == "long" for e in R), bad)))
        cols, rows = sec["grid"]["cols"], sec["grid"]["rows"]
        cells = [(w["col"], w["row"]) for w in W]
        outside = sum(1 for c, rw in cells if not (0 <= c < cols and 0 <= rw < rows))
        bars.append(("sector: worlds inside the grid, one per hex", outside == 0 and len(set(cells)) == len(cells),
                     "%d worlds, %d outside, %d sharing a hex" % (len(W), outside, len(cells) - len(set(cells)))))
        with open(os.path.join(d, "sector.tab"), encoding="utf-8") as f:
            try:
                back = read_t5_tab(f.read())
                ok = [(b["Hex"], b["Name"], b["UWP"]) for b in back] == [(w["hex"], w["name"], w["uwp"]) for w in W]
                det = "%d rows read back by header, hex, name and UWP match: %s" % (len(back), ok)
            except ValueError as e:
                ok, det = False, str(e)
        bars.append(("sector: T5 tab file reads back", ok, det))
    else:
        cat = {s["name"]: s for s in load_near_stars()}
        worst = 0.0
        miss = 0
        for w in W:
            if w["parallax_mas"] is None:
                continue
            c = cat.get(w["name"])
            if c is None:
                miss += 1
                continue
            pub = 1000.0 / c["plx"]
            dxyz = math.sqrt(sum(v * v for v in w["xyz"]))
            ra = math.degrees(math.atan2(w["xyz"][1], w["xyz"][0])) % 360.0
            dec = math.degrees(math.asin(w["xyz"][2] / dxyz))
            worst = max(worst, abs(dxyz - pub), abs(w["dist_pc"] - pub))
            if abs((ra - c["ra"] + 180) % 360 - 180) > 1e-6 or abs(dec - c["dec"]) > 1e-6:
                miss += 1
        bars.append(("sector: catalogue stars at their published distances", miss == 0 and worst <= DIST_TOL_PC,
                     "%d stars, worst |xyz| vs 1000/parallax %.2e pc (tolerance %.0e), %d off in RA/Dec or missing"
                     % (len(W) - 1, worst, DIST_TOL_PC, miss)))
        long_ = [e for e in R if (e["kind"] == "jump") != (e["pc"] <= jump)]
        bars.append(("sector: routes within %.1f pc marked jump, longer ones long" % jump, not long_,
                     "%d mislabelled" % len(long_)))
    return bars


# ================================================================== system
MS = {"M": (0.35, "#ff9b5e"), "K": (0.75, "#ffc98a"), "G": (1.0, "#fff1c4"), "F": (1.3, "#f6f6ff")}
ME = 3.003e-6          # Earth mass in solar masses
RE_AU = 4.2635e-5      # Earth radius in AU
RSUN_AU = 0.00465047
BODY_COL = {"rocky": "#b08a64", "ocean": "#4f8fd6", "gas": "#d9b07a", "ice-giant": "#8fd3e0", "ice": "#e6eef5",
            "dwarf": "#9a9a9a", "moon": "#c8c8c8"}


def gen_system(seed, out, star=None, planets=None, version="0.6.0", name_style=None):
    t0 = time.perf_counter()
    r = P.Rng(seed, 202)
    lang = mpw_names.make_language(seed, name_style)
    namer = mpw_names.Namer(lang)
    cls = star or _weighted(r, [("M", 40), ("K", 25), ("G", 20), ("F", 15)])
    if cls not in MS:
        raise ValueError("--star is one of M, K, G, F")
    mass = MS[cls][0] * r.uniform(0.9, 1.1)
    lum = mass ** 4 if mass > 0.43 else 0.23 * mass ** 2.3
    srad = mass ** 0.8 * RSUN_AU
    hz = (0.95 * math.sqrt(lum), 1.67 * math.sqrt(lum))
    snow = 2.7 * math.sqrt(lum)
    n = planets or r.randint(4, 9)
    sname = namer.name("star", (seed,))
    bodies = []
    a = max(r.uniform(0.2, 0.45) * math.sqrt(lum), 20 * srad)
    giant_done = False

    def body(a, u, gd):
        """Kind and mass at distance a from two pre-drawn numbers, so a pushed orbit can be re-judged."""
        if a < hz[0]:
            return "rocky", 0.05 + 1.45 * u[1]
        if a <= hz[1]:
            return ("ocean" if u[0] < 0.4 else "rocky"), 0.3 + 1.7 * u[1]
        if a < snow:
            return "rocky", 0.05 + 0.75 * u[1]
        if not gd or (a < 3 * snow and u[0] < 0.5):
            return "gas", 60 + 340 * u[1]
        if a < 8 * snow:
            return "ice-giant", 10 + 15 * u[1]
        return "dwarf", 0.002 + 0.048 * u[1]

    draws = [(r.random(), r.random()) for _ in range(n)]
    for i in range(n):
        kind, m = body(a, draws[i], giant_done)
        if kind == "gas":
            giant_done = True
        rad_e = m ** 0.27
        if kind == "gas":
            rad_e = min(11.2, max(6.0, m ** 0.5))
        if kind == "ice-giant":
            rad_e = 3.5 + m / 25.0
        hill = a * (m * ME / (3 * mass)) ** (1 / 3.0)
        moons = []
        nm = r.randint(1, 5) if kind in ("gas", "ice-giant") else (1 if r.random() < 0.3 else 0)
        lo, hi = 3 * rad_e * RE_AU, 0.4 * hill
        if hi > lo * 1.5:
            ma = lo * r.uniform(1.1, 1.6)
            for k in range(nm):
                if ma > hi:
                    break
                moons.append(dict(name="%s %s" % ("", ["I", "II", "III", "IV", "V", "VI"][k]), a_au=_r(ma, 7),
                                  a_planet_radii=_r(ma / (rad_e * RE_AU), 2), kind="moon",
                                  texture="moon" if kind != "ocean" else "ice"))
                ma *= r.uniform(1.5, 2.4)
        letter = "bcdefghijk"[i]
        nm_ = "%s %s" % (sname, letter)
        for mo in moons:
            mo["name"] = nm_ + mo["name"]
        tex = {"rocky": "rocky", "ocean": "ocean", "gas": "gas", "ice-giant": "gas", "dwarf": "ice"}[kind]
        if kind == "rocky" and a < hz[0] * 0.5 and cls in ("M", "K"):
            tex = "locked"
        bodies.append(dict(name=nm_, kind=kind, a_au=_r(a, 6), mass_earth=_r(m, 4), radius_earth=_r(rad_e, 3),
                           hill_au=_r(hill, 7), zone="inner" if a < hz[0] else "habitable" if a <= hz[1] else
                           "outer" if a < snow else "beyond snow line", texture=tex, moons=moons))
        # next orbit: geometric step, then pushed out to at least 12 mutual Hill radii
        nxt = a * r.uniform(1.4, 2.0)
        if i + 1 < n:
            for _ in range(12):
                m_next = body(nxt, draws[i + 1], giant_done)[1]
                rh = ((m + m_next) * ME / (3 * mass)) ** (1 / 3.0) * (a + nxt) / 2
                if nxt - a >= 12.5 * rh:
                    break
                nxt = a + 13.0 * rh
        a = nxt
    sysd = dict(star=dict(name=sname, cls=cls, spectral="%s%d V" % (cls, r.randint(0, 9)), mass_sun=_r(mass, 4),
                          luminosity_sun=_r(lum, 5), radius_au=_r(srad, 7)),
                habitable_zone_au=[_r(hz[0], 4), _r(hz[1], 4)], snow_line_au=_r(snow, 4), bodies=bodies,
                notes="schematic: equal spacing, not to scale; orbits.svg: orbits to scale, body markers not")
    recipe = dict(kind="system", seed=int(seed), tool_version=version, space_version=SPACE_VERSION,
                  params=dict(star=star, planets=planets, name_style=name_style), language=lang)
    t1 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    P.dump(os.path.join(out, "system.json"), sysd)
    names = [dict(kind="star", id=0, name=sname)] + [dict(kind="planet", id=i + 1, name=b["name"])
                                                     for i, b in enumerate(bodies)]
    P.dump(os.path.join(out, "names.json"), {"seed": int(seed), "language": lang, "names": names})
    P.dump(os.path.join(out, "sources.json"), {"files": [], "note": "generated; nothing fetched"})
    P.dump(os.path.join(out, "recipe.json"), recipe)
    _write(out, "map.svg", render_system_svg(sysd, "schematic"))
    _write(out, "orbits.svg", render_system_svg(sysd, "scale"))
    t = dict(generate=_r(t1 - t0, 3), total=_r(time.perf_counter() - t0, 3))
    return dict(out=out, kind="system", name=sname, star=sysd["star"]["spectral"], planets=len(bodies),
                moons=sum(len(b["moons"]) for b in bodies), times=t)


def _body_px(b):
    return {"gas": 16, "ice-giant": 11, "ocean": 7, "rocky": 6, "dwarf": 3.5}[b["kind"]]


def render_system_svg(sysd, view="schematic", st=SST):
    B = sysd["bodies"]
    star = sysd["star"]
    scol = MS[star["cls"]][1]
    if view == "scale":
        w = h = 820
        cx, cy = w / 2, h / 2 + 10
        amax = max(b["a_au"] for b in B)
        s = (w / 2 - 50) / amax
        o = _svg_head(w, h, st["bg"])
        o.append('<text x="16" y="26" font-family="%s" font-size="15" fill="%s">%s: orbits to scale (1 AU = %.1f px); '
                 'body markers not to scale</text>' % (st["font"], st["ink"], escape(star["name"]), s))
        hz = sysd["habitable_zone_au"]
        o.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="none" stroke="%s" stroke-width="%.2f" opacity="0.6"/>'
                 % (cx, cy, (hz[0] + hz[1]) / 2 * s, st["hz"], max(0.5, (hz[1] - hz[0]) * s)))
        o.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="none" stroke="%s" stroke-dasharray="2 4" stroke-width="0.8"/>'
                 % (cx, cy, sysd["snow_line_au"] * s, st["grid"]))
        o.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (cx, cy, scol))
        cands = []
        for i, b in enumerate(B):
            ang = (i * 2.399963) % (2 * math.pi)
            x, y = cx + b["a_au"] * s * math.cos(ang), cy + b["a_au"] * s * math.sin(ang)
            o.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="none" stroke="%s" stroke-width="0.8"/>'
                     % (cx, cy, b["a_au"] * s, st["orbit"]))
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (x, y, max(2.5, _body_px(b) / 3), BODY_COL[b["kind"]]))
            cands.append(("%s %.2f AU" % (b["name"].split()[-1], b["a_au"]), x, y - 8, 9.0))
        o.append('<text x="16" y="%d" font-family="%s" font-size="10" fill="%s">green band: habitable zone %.2f-%.2f AU;'
                 ' dashed: snow line %.2f AU</text>' % (h - 14, st["font"], st["grid"], hz[0], hz[1], sysd["snow_line_au"]))
    else:
        step = 110
        w = int(140 + step * len(B))
        h = 360
        y0 = 150
        o = _svg_head(w, h, st["bg"])
        o.append('<text x="16" y="26" font-family="%s" font-size="15" fill="%s">%s (%s): schematic, equal spacing, '
                 'not to scale</text>' % (st["font"], st["ink"], escape(star["name"]), star["spectral"]))
        o.append('<circle cx="0" cy="%d" r="70" fill="%s"/>' % (y0, scol))
        hz = sysd["habitable_zone_au"]
        xs = [110 + step * i for i in range(len(B))]
        inz = [x for x, b in zip(xs, B) if b["zone"] == "habitable"]
        if inz:
            o.append('<rect x="%d" y="50" width="%d" height="200" fill="%s" opacity="0.6"/>'
                     % (min(inz) - step // 2, max(inz) - min(inz) + step, st["hz"]))
        o.append('<line x1="70" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>' % (y0, w - 20, y0, st["orbit"]))
        cands = []
        for x, b in zip(xs, B):
            o.append('<circle cx="%d" cy="%d" r="%.1f" fill="%s"/>' % (x, y0, _body_px(b), BODY_COL[b["kind"]]))
            for k, mo in enumerate(b["moons"]):
                o.append('<circle cx="%d" cy="%d" r="2.5" fill="%s"/>' % (x, y0 + 30 + 12 * k, BODY_COL["moon"]))
            cands.append((b["name"].split()[-1] + " " + b["kind"], x, y0 - 30, 10.0))
            cands.append(("%.2f AU" % b["a_au"], x, y0 + 105, 9.0))
        o.append('<text x="16" y="%d" font-family="%s" font-size="10" fill="%s">green: habitable zone %.2f-%.2f AU; '
                 'dots below a planet: moons</text>' % (h - 14, st["font"], st["grid"], hz[0], hz[1]))
    labs, _ = P.place_labels(cands, w, h, False)
    o.append(P.labels_svg(labs, st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def _system_bars(d):
    s = P.load(d, "system.json")
    st = s["star"]
    B = s["bodies"]
    inside = [b["name"] for b in B if b["a_au"] <= st["radius_au"] * 2]
    bars = [("system: every orbit outside the star", not inside and bool(B), "%d planets, %d too close; star radius "
             "%.5f AU" % (len(B), len(inside), st["radius_au"]))]
    asc = all(B[i]["a_au"] < B[i + 1]["a_au"] for i in range(len(B) - 1))
    worst = float("inf")
    for b1, b2 in zip(B, B[1:]):
        rh = ((b1["mass_earth"] + b2["mass_earth"]) * ME / (3 * st["mass_sun"])) ** (1 / 3.0) * (b1["a_au"] + b2["a_au"]) / 2
        worst = min(worst, (b2["a_au"] - b1["a_au"]) / rh)
    bars.append(("system: neighbours at least %d mutual Hill radii apart" % HILL_MIN, asc and worst >= HILL_MIN,
                 "orbits ascending %s, closest pair %.1f mutual Hill radii" % (asc, worst if B[1:] else float("nan"))))
    bad = 0
    nmo = 0
    for b in B:
        hill = b["a_au"] * (b["mass_earth"] * ME / (3 * st["mass_sun"])) ** (1 / 3.0)
        for mo in b["moons"]:
            nmo += 1
            if not (b["radius_earth"] * RE_AU < mo["a_au"] < hill):
                bad += 1
    bars.append(("system: moons inside their planet's Hill sphere and outside the planet", bad == 0,
                 "%d moons, %d outside the bounds" % (nmo, bad)))
    hz = s["habitable_zone_au"]
    lum = st["luminosity_sun"]
    ok = abs(hz[0] - 0.95 * math.sqrt(lum)) < 1e-3 and abs(hz[1] - 1.67 * math.sqrt(lum)) < 1e-3
    zbad = sum(1 for b in B if (b["zone"] == "habitable") != (hz[0] <= b["a_au"] <= hz[1]))
    bars.append(("system: habitable zone scales with sqrt(L) and zones match it", ok and zbad == 0,
                 "%.3f-%.3f AU for L = %.4f, %d bodies in the wrong zone" % (hz[0], hz[1], lum, zbad)))
    return bars


# ================================================================== planet
class Noise3:
    """3D value noise on a seeded permutation table, smoothstep-interpolated."""

    def __init__(self, seed, stream=0):
        r = P.Rng(seed, 7000 + stream)
        p = list(range(256))
        for i in range(255, 0, -1):
            j = int(r.random() * (i + 1))
            p[i], p[j] = p[j], p[i]
        self.p = p + p
        self.v = [r.random() * 2 - 1 for _ in range(256)]

    def __call__(self, x, y, z):
        fx, fy, fz = math.floor(x), math.floor(y), math.floor(z)
        xi, yi, zi = int(fx) & 255, int(fy) & 255, int(fz) & 255
        tx, ty, tz = x - fx, y - fy, z - fz
        sx, sy, sz = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty), tz * tz * (3 - 2 * tz)
        p, v = self.p, self.v
        a = p[xi] + yi
        b = p[xi + 1] + yi
        aa, ab, ba, bb = p[a] + zi, p[a + 1] + zi, p[b] + zi, p[b + 1] + zi
        x00 = v[p[aa]] + sx * (v[p[ba]] - v[p[aa]])
        x10 = v[p[ab]] + sx * (v[p[bb]] - v[p[ab]])
        x01 = v[p[aa + 1]] + sx * (v[p[ba + 1]] - v[p[aa + 1]])
        x11 = v[p[ab + 1]] + sx * (v[p[bb + 1]] - v[p[ab + 1]])
        y0 = x00 + sy * (x10 - x00)
        y1 = x01 + sy * (x11 - x01)
        return y0 + sz * (y1 - y0)


def fbm(n, x, y, z, octaves=5, freq=2.0):
    s = 0.0
    amp = 1.0
    tot = 0.0
    for k in range(octaves):
        s += amp * n(x * freq + 31.7 * k, y * freq + 17.3 * k, z * freq + 7.1 * k)
        tot += amp
        amp *= 0.5
        freq *= 2.0
    return s / tot


def _ramp(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(c0[i] + (c1[i] - c0[i]) * f for i in range(3))
    return stops[-1][1]


def _hx(s):
    return G.hex_rgb(s)


def gen_planet(seed, out, kind="rocky", width=1024, version="0.6.0", sampling="sphere"):
    """sampling='uv' is a deliberately wrong 2D sampling used only by tests to prove the bars fail."""
    t0 = time.perf_counter()
    if kind not in PLANET_KINDS:
        raise ValueError("--kind is one of: " + ", ".join(PLANET_KINDS))
    if width < 512 or width % 2:
        raise ValueError("--width must be an even number of pixels, 512 or more (the pole bar needs it)")
    W, H = width, width // 2
    r = P.Rng(seed, 303)
    n1, n2 = Noise3(seed, 1), Noise3(seed, 2)
    craters = []
    if kind in ("moon", "rocky"):
        b = 2.0
        dmin, dmax = 0.012, 0.3
        cnt = 600 if kind == "moon" else 40
        for _ in range(cnt):
            u = r.random()
            dd = dmin * (1 - u * (1 - (dmin / dmax) ** b)) ** (-1.0 / b)
            z = r.uniform(-1, 1)
            lon = r.uniform(-math.pi, math.pi)
            q = math.sqrt(1 - z * z)
            craters.append((q * math.cos(lon), q * math.sin(lon), z, dd / 2))
        craters.sort(key=lambda c: -c[3])
    ovals = []
    if kind == "gas":
        for _ in range(r.randint(1, 4)):
            ovals.append((r.uniform(-0.8, 0.8), r.uniform(-math.pi, math.pi), r.uniform(0.08, 0.25), r.uniform(0.04, 0.09)))
    tint = r.uniform(-12, 12)
    bands = r.randint(7, 11)
    pal = _palette(kind, r)
    heights = [[0.0] * W for _ in range(H)]
    pts = [[None] * W for _ in range(H)]
    for j in range(H):
        lat = math.pi / 2 - (j + 0.5) / H * math.pi
        cl, sl = math.cos(lat), math.sin(lat)
        for i in range(W):
            lon = (i + 0.5) / W * 2 * math.pi - math.pi
            if sampling == "uv":
                x, y, z = (i + 0.5) / W * 4, (j + 0.5) / H * 2, 0.5
            else:
                x, y, z = cl * math.cos(lon), cl * math.sin(lon), sl
            pts[j][i] = (x, y, z, lat, lon)
            heights[j][i] = fbm(n1, x, y, z, 5, 1.6)
    for cx, cy, cz, rad in craters:
        clat = math.asin(cz)
        reach = rad * 1.5
        j0 = max(0, int((math.pi / 2 - (clat + reach)) / math.pi * H) - 1)
        j1 = min(H - 1, int((math.pi / 2 - (clat - reach)) / math.pi * H) + 1)
        depth = 0.25 + 1.2 * rad
        for j in range(j0, j1 + 1):
            for i in range(W):
                x, y, z = pts[j][i][:3]
                dot = x * cx + y * cy + z * cz
                if dot < math.cos(reach):
                    continue
                t = math.acos(min(1.0, dot)) / rad
                if t < 1:
                    heights[j][i] += depth * (t * t - 1)
                elif t < 1.5:
                    heights[j][i] += depth * 0.35 * (1 - (t - 1) / 0.5)
    rows = []
    for j in range(H):
        row = bytearray()
        for i in range(W):
            x, y, z, lat, lon = pts[j][i]
            h = heights[j][i]
            c = _shade(kind, pal, h, x, y, z, lat, lon, n2, bands, ovals)
            row += bytes(_clamp(int(round(v + tint * 0.3)), 0, 255) for v in c)
        rows.append(row)
    png = G.png_bytes(W, H, rows, 8, 2)
    meta = dict(kind=kind, width=W, height=H, layout="equirectangular 2:1, column 0 starts at longitude -180, row 0 "
                "at latitude +90, pixel centres", sampling="3D value noise at each pixel's point on the unit sphere"
                if sampling == "sphere" else "2D (u, v), test only", craters=len(craters),
                crater_power_law=dict(b=2.0, d_min=0.012, d_max=0.3) if craters else None,
                crater_diameters=[_r(c[3] * 2, 6) for c in craters], storms=len(ovals),
                substellar_point=[0.0, 0.0] if kind == "locked" else None)
    recipe = dict(kind="planet", seed=int(seed), tool_version=version, space_version=SPACE_VERSION,
                  params=dict(kind=kind, width=W, sampling=sampling), language=None)
    t1 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "texture.png"), "wb") as f:
        f.write(png)
    P.dump(os.path.join(out, "planet.json"), meta)
    P.dump(os.path.join(out, "sources.json"), {"files": [], "note": "generated; nothing fetched"})
    P.dump(os.path.join(out, "recipe.json"), recipe)
    _write(out, "map.svg", render_planet_svg(recipe, png, W, H))
    t = dict(generate=_r(t1 - t0, 3), total=_r(time.perf_counter() - t0, 3))
    return dict(out=out, kind="planet", planet=kind, width=W, height=H, craters=len(craters), times=t)


def _palette(kind, r):
    if kind == "rocky":
        return [(-1, _hx("#3d2f26")), (-0.2, _hx("#6e5340")), (0.15, _hx("#a77e5a")), (0.5, _hx("#d8b48a")), (1, _hx("#efe0c8"))]
    if kind == "moon":
        return [(-1.5, _hx("#2e2e30")), (-0.3, _hx("#5f5f63")), (0.2, _hx("#9a9a9c")), (1, _hx("#d6d6d2"))]
    if kind == "ice":
        return [(-1, _hx("#9fb9cc")), (0, _hx("#d5e4ee")), (1, _hx("#f7fbff"))]
    if kind == "ocean":
        return [(-1, _hx("#0b2a55")), (0.15, _hx("#1f5d9e")), (0.3, _hx("#3f86c4")), (0.31, _hx("#c9b57d")),
                (0.45, _hx("#5e8a4a")), (1, _hx("#8a7a5c"))]
    if kind == "gas":
        a = [_hx("#e9d4ae"), _hx("#c98d55"), _hx("#f4e7cf"), _hx("#a8673e"), _hx("#d9b98a")]
        k = r.randint(0, len(a) - 1)
        return a[k:] + a[:k]
    return [(-1, _hx("#101828")), (-0.2, _hx("#e8f0f8")), (0.1, _hx("#7a8a5a")), (0.45, _hx("#3f6b3a")),
            (0.75, _hx("#c7a46a")), (1, _hx("#2a6fb0"))]


def _shade(kind, pal, h, x, y, z, lat, lon, n2, bands, ovals):
    if kind in ("rocky", "moon"):
        return _ramp(pal, h * (2.2 if kind == "rocky" else 1.6))
    if kind == "ice":
        c = _ramp(pal, h * 2.0)
        ridge = 1 - abs(fbm(n2, x, y, z, 2, 2.0))
        if ridge > 0.85:
            f = ((ridge - 0.85) / 0.15) ** 2
            c = tuple(c[i] + (_hx("#8a4b2f")[i] - c[i]) * f * 0.8 for i in range(3))
        return c
    if kind == "ocean":
        c = _ramp(pal, h * 1.8 - 0.1)
        if abs(z) + 0.08 * h > 0.86:
            c = _hx("#f2f6fa")
        return c
    if kind == "gas":
        t = z * bands * 0.5 + 0.35 * fbm(n2, x * 2.5, y * 2.5, z * 9.0, 4, 1.0)
        k = int(math.floor(t)) % len(pal)
        f = t - math.floor(t)
        f = f * f * (3 - 2 * f)
        c0, c1 = pal[k], pal[(k + 1) % len(pal)]
        c = tuple(c0[i] + (c1[i] - c0[i]) * f for i in range(3))
        for olat, olon, a, b in ovals:
            dl = (lon - olon + math.pi) % (2 * math.pi) - math.pi
            dd = (dl * math.cos(olat) / a) ** 2 + ((lat - olat) / b) ** 2
            if dd < 1:
                c = tuple(c[i] + (_hx("#b5482f")[i] - c[i]) * (1 - dd) for i in range(3))
        return c
    # locked: mu = cosine of the angle to the substellar point (lon 0, lat 0)
    mu = x + 0.12 * h
    return _ramp(pal, mu)


def render_planet_svg(rc, png, W, H, st=SST):
    sw, sh = 1024, 512
    w, h = sw + 40, sh + 70
    o = _svg_head(w, h, st["bg"])
    o.append('<text x="20" y="28" font-family="%s" font-size="15" fill="%s">%s planet, seed %d: equirectangular '
             'texture, graticule every 30 degrees</text>' % (st["font"], st["ink"], rc["params"]["kind"], rc["seed"]))
    o.append('<image x="20" y="45" width="%d" height="%d" preserveAspectRatio="none" href="data:image/png;base64,%s"/>'
             % (sw, sh, __import__("base64").b64encode(png).decode("ascii")))
    g = []
    for k in range(1, 12):
        x = 20 + sw * k / 12
        g.append("M%.1f,45V%.1f" % (x, 45 + sh))
    for k in range(1, 6):
        y = 45 + sh * k / 6
        g.append("M20,%.1fH%.1f" % (y, 20 + sw))
    o.append('<path d="%s" stroke="#ffffff" stroke-opacity="0.25" stroke-width="0.7" fill="none"/>' % "".join(g))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def decode_png(data):
    """8-bit grey, RGB or RGBA non-interlaced PNG to rows of pixel tuples (all five filters)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos = 8
    idat = b""
    w = h = ct = None
    while pos < len(data):
        ln, = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ct, _, _, il = struct.unpack(">IIBBBBB", body)
            if depth != 8 or il or ct not in (0, 2, 6):
                raise ValueError("only 8-bit grey, RGB or RGBA non-interlaced PNGs")
        elif typ == b"IDAT":
            idat += body
        pos += 12 + ln
    bpp = {0: 1, 2: 3, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    rows = []
    k = 0
    for _ in range(h):
        ft = raw[k]
        cur = bytearray(raw[k + 1:k + 1 + stride])
        k += 1 + stride
        for i in range(stride):
            a = cur[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                cur[i] = (cur[i] + a) & 255
            elif ft == 2:
                cur[i] = (cur[i] + b) & 255
            elif ft == 3:
                cur[i] = (cur[i] + (a + b) // 2) & 255
            elif ft == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                cur[i] = (cur[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(cur[i * bpp:i * bpp + 3]) if bpp >= 3 else (cur[i],) * 3 for i in range(w)])
        prev = cur
    return w, h, rows


def texture_bars(png):
    w, h, rows = decode_png(png)
    L = [[0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in row] for row in rows]
    seam = sum(abs(r[0] - r[-1]) for r in L) / h
    pair = sorted(sum(abs(r[c] - r[c + 1]) for r in L) / h for c in range(w - 1))
    med = pair[int(len(pair) * 0.9)]
    allv = [v for r in L for v in r]
    mean = sum(allv) / len(allv)
    sd = math.sqrt(sum((v - mean) ** 2 for v in allv) / len(allv))

    def rsd(r):
        m = sum(r) / len(r)
        return math.sqrt(sum((v - m) ** 2 for v in r) / len(r))
    top, bot = rsd(L[0]), rsd(L[-1])
    pole_ok = sd < 1e-9 or max(top, bot) <= POLE_FACTOR * sd
    return [("planet: texture is 2:1", w == 2 * h, "%dx%d" % (w, h)),
            ("planet: no seam where the edges meet", seam <= SEAM_FACTOR * med + 0.5,
             "mean |col 0 - col %d| %.2f vs 90th percentile adjacent-column %.2f (limit x%.1f + 0.5 grey level)"
             % (w - 1, seam, med, SEAM_FACTOR)),
            ("planet: no pinch at the poles (pole rows uniform)", pole_ok,
             "std of top row %.2f, bottom row %.2f vs whole texture %.2f (limit x%.2f)" % (top, bot, sd, POLE_FACTOR))]


def _planet_bars(d):
    with open(os.path.join(d, "texture.png"), "rb") as f:
        bars = texture_bars(f.read())
    meta = P.load(d, "planet.json")
    pl = meta.get("crater_power_law")
    if pl and len(meta["crater_diameters"]) >= 300:
        ds = sorted(meta["crater_diameters"], reverse=True)
        lo, hi = pl["d_min"], pl["d_max"] / 4
        xs, ys = [], []
        for k in range(8):
            dd = lo * (hi / lo) ** (k / 7.0)
            n = sum(1 for v in ds if v >= dd)
            if n >= 20:
                xs.append(math.log(dd))
                ys.append(math.log(n))
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
        bars.append(("planet: crater sizes follow N(>D) ~ D^-%.1f" % pl["b"], abs(-slope - pl["b"]) <= CRATER_SLOPE_TOL,
                     "%d craters, fitted log-log slope %.2f (limit +-%.2f)" % (len(ds), slope, CRATER_SLOPE_TOL)))
    return bars


# ================================================================== deck
ROOM_NAMES = ["quarters", "galley", "medbay", "cargo", "lab", "stores", "lounge", "sensors", "life support",
              "armoury", "workshop", "hydroponics", "brig", "comms"]
PASSABLE = ".+L"


def _hull(W, H, hull):
    cy = H // 2
    K = (H - 5) // 2  # one wall row and one row of space each side
    ks = []
    for x in range(W):
        if x < 2 or x > W - 3:
            ks.append(-1)
            continue
        t = (x - 2) / max(1, W - 5)
        if hull == "ship":
            prof = min(0.85 + 0.15 * t / 0.4 if t < 0.4 else 1.0, (1 - t) / 0.3 if t > 0.7 else 1.0)
            prof = max(prof, 0.0)
        else:
            prof = min(1.0, 0.45 + t / 0.25, 0.45 + (1 - t) / 0.25)
        ks.append(int(round(K * prof)))
    return cy, ks


def gen_deck(seed, out, w=40, h=21, decks=2, hull="ship", pps=16, version="0.6.0", name_style=None):
    t0 = time.perf_counter()
    if hull not in ("ship", "station"):
        raise ValueError("--hull is ship or station")
    if w < 16 or h < 11 or not 1 <= decks <= 6:
        raise ValueError("deck needs --w 16+, --h 11+, --decks 1..6")
    lang = mpw_names.make_language(seed, name_style)
    namer = mpw_names.Namer(lang)
    cy, ks = _hull(w, h, hull)
    xs = [x for x in range(w) if ks[x] >= 0]
    lift_x = (xs[0] + xs[-1]) // 2
    plans = []
    rooms = []
    for dk in range(decks):
        r = P.Rng(seed, 400 + dk)
        g = [[" "] * w for _ in range(h)]
        inside = [[ks[x] >= 0 and abs(y - cy) <= ks[x] for x in range(w)] for y in range(h)]
        for y in range(h):
            for x in range(w):
                if inside[y][x]:
                    g[y][x] = "."
        for y in range(h):
            for x in range(w):
                if not inside[y][x] and any(0 <= y + dy < h and 0 <= x + dx < w and inside[y + dy][x + dx]
                                            for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                    g[y][x] = "#"
        for x in xs:
            for yy in (cy - 1, cy + 1):
                if inside[yy][x]:
                    g[yy][x] = "#"
        drooms = []
        for side in (-1, 1):
            run = [x for x in xs if ks[x] >= 2]
            # split runs of consecutive columns into rooms 3..6 wide, one wall column between
            runs, cur = [], []
            for x in run:
                if cur and x != cur[-1] + 1:
                    runs.append(cur)
                    cur = []
                cur.append(x)
            if cur:
                runs.append(cur)
            for rn in runs:
                i = 0
                spans = []
                while i < len(rn):
                    wd = r.randint(3, 6)
                    if len(rn) - i - wd < 3:
                        wd = len(rn) - i
                    spans.append(rn[i:i + wd])
                    i += wd + 1
                    if i - 1 < len(rn) and i - 1 >= 0 and i <= len(rn):
                        sep = rn[i - 1]
                        for y in range(h):
                            if inside[y][sep] and (y - cy) * side >= 2:
                                g[y][sep] = "#"
                for sp in spans:
                    cells = [(x, y) for x in sp for y in range(h) if inside[y][x] and (y - cy) * side >= 2
                             and g[y][x] == "."]
                    if not cells:
                        continue
                    dx = sp[r.randint(0, len(sp) - 1)]
                    g[cy + side][dx] = "+"
                    drooms.append(dict(id=len(rooms) + len(drooms), deck=dk, side=side, x0=sp[0], x1=sp[-1],
                                       cells=sorted([[x, y] for x, y in cells], key=lambda c: (c[1], c[0])),
                                       door=[dx, cy + side]))
        g[cy][lift_x] = "L"
        drooms.sort(key=lambda rm: (rm["x0"], rm["side"]))
        for k, rm in enumerate(drooms):
            rm["id"] = len(rooms) + k
        if dk == 0:
            # airlock: an upper room near the middle whose hull wall opens to space
            cand = sorted([rm for rm in drooms if rm["side"] == -1], key=lambda rm: abs((rm["x0"] + rm["x1"]) / 2 - lift_x))
            for rm in cand:
                ok = None
                for x in range(rm["x0"], rm["x1"] + 1):
                    top = cy - ks[x]
                    if top - 2 >= 0 and g[top - 1][x] == "#" and g[top - 2][x] == " " and g[top][x] == ".":
                        ok = x
                        break
                if ok is not None:
                    g[cy - ks[ok] - 1][ok] = "A"
                    rm["name"] = "airlock"
                    rm["outer"] = [ok, cy - ks[ok] - 1]
                    break
            fr = max(drooms, key=lambda rm: (rm["x1"], -rm["side"]))
            fr.setdefault("name", "bridge")
        back = [rm for rm in sorted(drooms, key=lambda rm: rm["x0"]) if "name" not in rm][:2]
        for rm, nm in zip(back, ("engineering", "drive")):
            rm["name"] = nm
        for rm in drooms:
            if "name" not in rm:
                rm["name"] = ROOM_NAMES[r.randint(0, len(ROOM_NAMES) - 1)]
        rooms += drooms
        plans.append(["".join(row) for row in g])
    if not any(rm.get("outer") for rm in rooms):
        raise ValueError("no room touches the hull for an airlock; try another seed or a larger --h")
    ship = namer.name("ship", (seed,))
    dj = dict(name=ship, hull=hull, w=w, h=h, square_m=1.5, decks=plans, lift=[lift_x, cy], rooms=rooms,
              legend={" ": "outside", "#": "wall", ".": "floor", "+": "door", "L": "lift (same square on every deck)",
                      "A": "airlock outer door"})
    recipe = dict(kind="deck", seed=int(seed), tool_version=version, space_version=SPACE_VERSION,
                  params=dict(w=w, h=h, decks=decks, hull=hull, pps=pps, name_style=name_style), language=lang)
    t1 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    P.dump(os.path.join(out, "deck.json"), dj)
    P.dump(os.path.join(out, "names.json"), {"seed": int(seed), "language": lang,
                                             "names": [dict(kind="ship", id=0, name=ship)]})
    P.dump(os.path.join(out, "sources.json"), {"files": [], "note": "generated; nothing fetched"})
    P.dump(os.path.join(out, "recipe.json"), recipe)
    _write(out, "map.svg", render_deck_svg(dj, pps))
    t = dict(generate=_r(t1 - t0, 3), total=_r(time.perf_counter() - t0, 3))
    return dict(out=out, kind="deck", name=ship, decks=decks, rooms=len(rooms), times=t)


DST = dict(P.PSTYLES["blueprint"])


def render_deck_svg(dj, pps, st=DST):
    w, h = dj["w"], dj["h"]
    pw = w * pps
    ph = h * pps
    m = 20
    top = 40
    gap = 34
    W = pw + 2 * m
    H = top + len(dj["decks"]) * (ph + gap) + 30
    o = _svg_head(W, H, st["bg"])
    o.append('<text x="%d" y="26" font-family="%s" font-size="15" fill="%s">%s: %s, %d deck(s), 1 square = 1.5 m</text>'
             % (m, st["font"], st["ink"], escape(dj["name"]), dj["hull"], len(dj["decks"]), ))
    cands = []
    col = {"#": st["wall"], ".": st["floor"], "+": st["door"], "L": "#7fe0a0", "A": "#ff8a6a"}
    for dk, rows in enumerate(dj["decks"]):
        oy = top + dk * (ph + gap) + 14
        o.append('<text x="%d" y="%d" font-family="%s" font-size="11" fill="%s">Deck %d</text>'
                 % (m, oy - 4, st["font"], st["grid"], dk + 1))
        for y, row in enumerate(rows):
            for x, c in enumerate(row):
                if c != " ":
                    o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                             % (m + x * pps, oy + y * pps, pps, pps, col[c]))
        for rm in [q for q in dj["rooms"] if q["deck"] == dk]:
            cx = sum(c[0] for c in rm["cells"]) / len(rm["cells"])
            cyy = sum(c[1] for c in rm["cells"]) / len(rm["cells"])
            cands.append((rm["name"], m + (cx + 0.5) * pps, oy + (cyy + 0.5) * pps + 3, 8.0))
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2"/>'
             % (m, H - 14, m + pps * 4, H - 14, st["ink"]))
    o.append('<text x="%d" y="%d" font-family="%s" font-size="10" fill="%s">6 m</text>'
             % (m + pps * 4 + 6, H - 10, st["font"], st["ink"]))
    labs, _ = P.place_labels(cands, W, H, True)
    o.append(P.labels_svg(labs, st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def _deck_bars(d):
    dj = P.load(d, "deck.json")
    D = dj["decks"]
    nd = len(D)
    h, w = len(D[0]), len(D[0][0])
    airlocks = [rm for rm in dj["rooms"] if rm.get("outer")]
    bars = []
    if not airlocks:
        return [("deck: an airlock exists", False, "no room has an outer door")]
    al = airlocks[0]
    start = (al["deck"], al["cells"][0][0], al["cells"][0][1])
    seen = {start}
    st = [start]
    while st:
        k, x, y = st.pop()
        nxt = [(k, x + 1, y), (k, x - 1, y), (k, x, y + 1), (k, x, y - 1)]
        if D[k][y][x] == "L":
            nxt += [(k - 1, x, y), (k + 1, x, y)]
        for kk, xx, yy in nxt:
            if 0 <= kk < nd and 0 <= xx < w and 0 <= yy < h and (kk, xx, yy) not in seen and D[kk][yy][xx] in PASSABLE:
                if kk != k and not (D[k][y][x] == "L" and D[kk][yy][xx] == "L"):
                    continue
                seen.add((kk, xx, yy))
                st.append((kk, xx, yy))
    floor = [(k, x, y) for k in range(nd) for y in range(h) for x in range(w) if D[k][y][x] in PASSABLE]
    unr = [rm["name"] for rm in dj["rooms"] if not any((rm["deck"], c[0], c[1]) in seen for c in rm["cells"])]
    bars.append(("deck: every room reached from the airlock", not unr,
                 "%d rooms on %d deck(s), %d unreached%s" % (len(dj["rooms"]), nd, len(unr),
                                                             (": " + ", ".join(unr[:4])) if unr else "")))
    bars.append(("deck: every floor square reached", len(seen) == len(floor), "%d of %d reached" % (len(seen), len(floor))))
    bad = 0
    nd_ = 0
    for k in range(nd):
        for y in range(h):
            for x in range(w):
                if D[k][y][x] == "+":
                    nd_ += 1
                    ns = 0 < y < h - 1 and D[k][y - 1][x] in PASSABLE and D[k][y + 1][x] in PASSABLE
                    ew = 0 < x < w - 1 and D[k][y][x - 1] in PASSABLE and D[k][y][x + 1] in PASSABLE
                    if not (ns or ew):
                        bad += 1
    bars.append(("deck: every door joins two floors", bad == 0, "%d doors, %d bad" % (nd_, bad)))
    ox, oy = al["outer"]
    Ad = D[al["deck"]]
    outer_ok = Ad[oy][ox] == "A" and any(0 <= oy + dy < h and Ad[oy + dy][ox] == " " for dy in (-1, 1)) and \
        any([ox, oy + dy] in al["cells"] for dy in (-1, 1))
    inner = al["door"] and Ad[al["door"][1]][al["door"][0]] == "+"
    bars.append(("deck: airlock has an inner door and an outer door to space", bool(outer_ok and inner),
                 "outer at %s opens to space: %s; inner door: %s" % (al["outer"], bool(outer_ok), bool(inner))))
    lifts = [sorted((x, y) for y in range(h) for x in range(w) if D[k][y][x] == "L") for k in range(nd)]
    bars.append(("deck: lifts line up on every deck", all(lf == lifts[0] and lf for lf in lifts),
                 "lift squares per deck: %s" % [len(lf) for lf in lifts]))
    return bars


# ================================================================== folder-level: render, check, export
def render_svg(d, view=None):
    rc = P.load(d, "recipe.json")
    k = rc["kind"]
    if k == "sector":
        return render_sector_svg(rc, P.load(d, "sector.json"))
    if k == "system":
        return render_system_svg(P.load(d, "system.json"), view or "schematic")
    if k == "planet":
        with open(os.path.join(d, "texture.png"), "rb") as f:
            png = f.read()
        w, h = P.png_size(png)
        return render_planet_svg(rc, png, w, h)
    return render_deck_svg(P.load(d, "deck.json"), rc["params"]["pps"])


def regenerate(d, tmp):
    rc = P.load(d, "recipe.json")
    p = rc["params"]
    v = rc["tool_version"]
    k = rc["kind"]
    if k == "sector":
        gen_sector(rc["seed"], tmp, p["size"], p["density"], p["jump"], p["real"], p["radius_pc"], v, p["name_style"])
    elif k == "system":
        gen_system(rc["seed"], tmp, p["star"], p["planets"], v, p["name_style"])
    elif k == "planet":
        gen_planet(rc["seed"], tmp, p["kind"], p["width"], v, p.get("sampling", "sphere"))
    else:
        gen_deck(rc["seed"], tmp, p["w"], p["h"], p["decks"], p["hull"], p["pps"], v, p["name_style"])


def _bytes(path):
    with open(path, "rb") as f:
        return f.read()


def check(d, determinism=True, labels=True):
    rc = P.load(d, "recipe.json")
    k = rc["kind"]
    bars = {"sector": _sector_bars, "system": _system_bars, "planet": _planet_bars, "deck": _deck_bars}[k](d)
    if determinism:
        tmp = tempfile.mkdtemp(prefix="mpw-space-")
        try:
            regenerate(d, tmp)
            a, b = sorted(os.listdir(d)), sorted(os.listdir(tmp))
            # Files the gen writes must exist and match; extra files (a render the
            # user saved into the folder) are not the gen's and are ignored.
            diff = sorted(set(b) - set(a)) + [n for n in b if n in a and _bytes(os.path.join(d, n)) != _bytes(os.path.join(tmp, n))]
            a = b
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        bars.append(("same seed gives byte-identical files", not diff,
                     "differs: %s" % ", ".join(diff) if diff else "%d files identical" % len(a)))
    if labels:
        import mpw_render as R
        for name in ("map.svg", "orbits.svg"):
            pth = os.path.join(d, name)
            if os.path.exists(pth):
                with open(pth, encoding="utf-8") as f:
                    bars += [(n + ("" if name == "map.svg" else " (" + name + ")"), ok, det)
                             for n, ok, det in R.label_bars(f.read())]
    return [(i + 1, n, ok, det) for i, (n, ok, det) in enumerate(bars)]


SPHERE_NOTE = (
    "Equirectangular sphere texture (2:1). Column 0 is longitude -180 and the last column +180; row 0 is latitude "
    "+90. Pixel centres sit half a pixel in from every edge, so the left and right edges meet without a seam and the "
    "pole rows are uniform (mapwright check proves both). three.js (threewright): new THREE.TextureLoader().load(png),"
    " set texture.colorSpace = THREE.SRGBColorSpace and use it as the map of a MeshStandardMaterial on a "
    "SphereGeometry; SphereGeometry's UVs are equirectangular. Rotate the mesh about Y if longitude 0 should face "
    "the camera. Blender (polywright): a UV Sphere's default UVs are equirectangular; or use an Environment-style "
    "spherical projection on an Image Texture node. Check orientation once on first import.")


def export(d, out):
    rc = P.load(d, "recipe.json")
    k = rc["kind"]
    if k == "planet":
        if not out.lower().endswith(".png"):
            raise ValueError("a planet exports as a .png sphere texture")
        shutil.copyfile(os.path.join(d, "texture.png"), out)
        note = os.path.splitext(out)[0] + ".sphere.json"
        meta = P.load(d, "planet.json")
        P.dump(note, dict(texture=os.path.basename(out), kind=meta["kind"], width=meta["width"], height=meta["height"],
                          layout=meta["layout"], handoff=SPHERE_NOTE,
                          plugins=dict(threewright="sphere material from this PNG",
                                       polywright="UV sphere in Blender, or a printed globe")))
        with open(out, "rb") as f:
            bars = texture_bars(f.read())
        return bars, [out, note]
    if k == "sector":
        sec = P.load(d, "sector.json")
        if sec["grid"] is None:
            raise ValueError("a real-star chart has no hex grid; export works on generated sectors")
        if not out.lower().endswith((".tab", ".tsv", ".txt")):
            raise ValueError("a sector exports as a T5 tab-delimited file (.tab)")
        shutil.copyfile(os.path.join(d, "sector.tab"), out)
        with open(out, encoding="utf-8") as f:
            back = read_t5_tab(f.read())
        return [("T5 tab: reads back by header", len(back) == len(sec["worlds"]),
                 "%d of %d worlds" % (len(back), len(sec["worlds"])))], [out]
    raise ValueError("export for a %s recipe: render it to SVG/PNG/PDF instead" % k)
