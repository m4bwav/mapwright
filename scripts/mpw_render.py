"""mapwright render: recipe folder to a print map (SVG, then PNG or PDF through a headless browser).

Standard library only. Labels are placed with collision avoidance using a shipped,
deliberately wide width table (or a TTF's hmtx table with --font). Same recipe and
style give byte-identical SVG.
"""
import base64
import http.server
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import mpw_gen as G

W = 1000.0          # SVG width in px
MARGIN = 10.0
SVGNS = "{http://www.w3.org/2000/svg}"

# ------------------------------------------------------------------ styles
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Helvetica Neue', Arial, sans-serif"
OLD = "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif"
MONO = "'Courier New', Courier, monospace"

STYLES = {
    "topographic": dict(desc="hypsometric tints, hillshade, depth-tinted sea", land="hypso", sea=("#d4ebf7", "#7fb0d4"),
                        shade=0.6, coast="#3a5a70", river="#3d7cc0", lake="#a8d0ea", roads=("#b03a2e", "#c0703a", "#8a5a3a"),
                        dot="#222222", ink="#1e1e1e", halo="#ffffff", font=SANS, paper="#ffffff"),
    "atlas": dict(desc="biome colours, soft hillshade, flat sea, serif labels", land="biome", sea=("#b6d6ec", "#b6d6ec"),
                  shade=0.45, coast="#24343c", river="#2f6fa8", lake="#9cc6e4", roads=("#7a3b1d", "#8a5a3a", "#8a5a3a"),
                  dot="#222222", ink="#222222", halo="#ffffff", font=SERIF, paper="#ffffff"),
    "satellite": dict(desc="dark natural colour with strong relief, white labels", land="sat", sea=("#24507a", "#0e2740"),
                      shade=0.85, coast="#0e2232", river="#2a5d8a", lake="#1f4a70", roads=("#d8c8a8", "#c8b898", "#a89878"),
                      dot="#ffffff", ink="#ffffff", halo="#101820", font=SANS, paper="#0e2740"),
    "ink-and-parchment": dict(desc="parchment land, ink lines, old serif", land="flat", landc="#ecdcb0", sea=("#d9c896", "#cbb680"),
                              shade=0.35, coast="#3b2a1a", river="#3b2a1a", lake="#d9c896", roads=("#5a3b22", "#5a3b22", "#7a5a3a"),
                              dot="#3b2a1a", ink="#2b1d10", halo="#ecdcb0", font=OLD, paper="#e2d0a0"),
    "blueprint": dict(desc="white line work on blueprint blue, monospace", land="flat", landc="#2c66aa", sea=("#1d4e89", "#1d4e89"),
                      shade=0.15, coast="#e8f1fb", river="#cfe2f8", lake="#1d4e89", roads=("#ffffff", "#e0ecfa", "#c0d4ee"),
                      dot="#ffffff", ink="#ffffff", halo="#1d4e89", font=MONO, mono=True, grid="#5d8cc4", paper="#1d4e89"),
    "star-chart": dict(desc="night palette with a star field (palette only for now)", land="flat", landc="#1b2348", sea=("#0b1026", "#0b1026"),
                       shade=0.25, coast="#c9d4ff", river="#8fa2e8", lake="#0b1026", roads=("#c9d4ff", "#a8b6ee", "#8090c8"),
                       dot="#ffe9a8", ink="#e9ecff", halo="#0b1026", font=SANS, stars=True, paper="#0b1026"),
}
DEFAULT_STYLE = "topographic"

HYPSO = [(0, "#8fbf7f"), (200, "#b5d38f"), (500, "#e3e2a0"), (1000, "#d9b77a"), (2000, "#b88a5a"),
         (3000, "#a07860"), (4500, "#f2f0ee")]
SAT = {"ocean": "#24507a", "lake": "#1f4a70", "ice": "#e8eef2", "tundra": "#7d7a68", "boreal forest": "#2f4a32",
       "temperate forest": "#36572f", "temperate rainforest": "#2b4d2c", "grassland": "#7d8a4c",
       "shrubland": "#8a7f56", "desert": "#b8a27a", "savanna": "#8f8a4e", "tropical forest": "#2e5228",
       "tropical rainforest": "#24461f"}


def style(name):
    if name not in STYLES:
        raise ValueError("unknown style %r; styles: %s" % (name, ", ".join(sorted(STYLES))))
    return STYLES[name]


# ------------------------------------------------------------------ text metrics
# Advance widths in em. Deliberately on the wide side of common serif and sans faces,
# so a label measured here is never shorter than it draws. Not copied from any font.
_NARROW = set("il.,;:'|!`")
_SEMI = set("fjrtI()[]-\" ")
_WIDE = set("mwMW@")
_CAPS_WIDE = set("ABCDGHKNOQRUVXY&")


def em_width(ch):
    if ch in _NARROW:
        return 0.37
    if ch in _SEMI:
        return 0.48
    if ch in _WIDE:
        return 1.0
    if ch.isupper():
        return 0.84 if ch in _CAPS_WIDE else 0.74
    if ch.isdigit():
        return 0.64
    return 0.64


class TTFMetrics:
    """Advance widths from a TrueType file's cmap (format 4) and hmtx tables."""

    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        num = struct.unpack(">H", data[4:6])[0]
        tabs = {}
        for i in range(num):
            tag, _, off, ln = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
            tabs[tag.decode("latin-1")] = (off, ln)
        for t in ("head", "hhea", "hmtx", "cmap"):
            if t not in tabs:
                raise ValueError("%s: no %s table (not a TrueType font?)" % (path, t))
        self.upem = struct.unpack(">H", data[tabs["head"][0] + 18:tabs["head"][0] + 20])[0]
        nh = struct.unpack(">H", data[tabs["hhea"][0] + 34:tabs["hhea"][0] + 36])[0]
        ho = tabs["hmtx"][0]
        self.adv = [struct.unpack(">H", data[ho + 4 * i:ho + 4 * i + 2])[0] for i in range(nh)]
        co = tabs["cmap"][0]
        sub = None
        for i in range(struct.unpack(">H", data[co + 2:co + 4])[0]):
            pid, eid, off = struct.unpack(">HHI", data[co + 4 + 8 * i:co + 12 + 8 * i])
            if pid == 3 and eid in (1, 0) and struct.unpack(">H", data[co + off:co + off + 2])[0] == 4:
                sub = co + off
                break
        if sub is None:
            raise ValueError("%s: no Windows Unicode cmap format 4" % path)
        segx2 = struct.unpack(">H", data[sub + 6:sub + 8])[0]
        n = segx2 // 2
        ends = struct.unpack(">%dH" % n, data[sub + 14:sub + 14 + segx2])
        p = sub + 16 + segx2
        starts = struct.unpack(">%dH" % n, data[p:p + segx2])
        deltas = struct.unpack(">%dh" % n, data[p + segx2:p + 2 * segx2])
        ro = p + 2 * segx2
        ranges = struct.unpack(">%dH" % n, data[ro:ro + segx2])
        self.cmap = {}
        for k in range(n):
            for c in range(starts[k], min(ends[k], 0x2FF) + 1):
                if ranges[k] == 0:
                    g = (c + deltas[k]) & 0xFFFF
                else:
                    a = ro + 2 * k + ranges[k] + 2 * (c - starts[k])
                    g = struct.unpack(">H", data[a:a + 2])[0]
                    if g:
                        g = (g + deltas[k]) & 0xFFFF
                self.cmap[c] = g

    def em(self, ch):
        g = self.cmap.get(ord(ch), 0)
        return self.adv[min(g, len(self.adv) - 1)] / self.upem


def text_width(text, size, ls=0.0, mono=False, metrics=None):
    if mono:
        em = 0.62 * len(text)
    elif metrics is not None:
        em = sum(metrics.em(c) for c in text)
    else:
        em = sum(em_width(c) for c in text)
    return em * size + ls * max(0, len(text) - 1)


ASC, DESC = 0.80, 0.26   # of font size, above and below the baseline


def text_box(x, y, size, text, anchor="start", angle=0.0, ls=0.0, pad=0.0, mono=False, metrics=None):
    """Axis-aligned box (x0, y0, x1, y1) of a label, rotated about (x, y) when angle != 0."""
    w = text_width(text, size, ls, mono, metrics)
    dx0 = {"start": 0.0, "middle": -w / 2, "end": -w}[anchor]
    pts = [(dx0 - pad, -ASC * size - pad), (dx0 + w + pad, -ASC * size - pad),
           (dx0 + w + pad, DESC * size + pad), (dx0 - pad, DESC * size + pad)]
    if angle:
        ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        pts = [(px * ca - py * sa, px * sa + py * ca) for px, py in pts]
    xs = [x + p[0] for p in pts]
    ys = [y + p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


# ------------------------------------------------------------------ loading
def load(d):
    rc = G.load(d, "recipe.json")
    m = G.load(d, "mesh.json")
    fc = G.load(d, "features.geojson")
    return rc, m, fc["features"]


def _frame(rc):
    x0, y0, x1, y1 = rc["extent"]
    s = W / (x1 - x0)
    return x0, y0, s, (y1 - y0) * s


def _to_px(c, x0, y0, s):
    return ((c[0] / 1000.0 - x0) * s, (G.WORLD - c[1] / 1000.0 - y0) * s)


# ------------------------------------------------------------------ land raster
def _ramp(stops, v):
    if v <= stops[0][0]:
        return G.hex_rgb(stops[0][1])
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            p, q = G.hex_rgb(ca), G.hex_rgb(cb)
            return tuple(int(round(p[i] + (q[i] - p[i]) * t)) for i in range(3))
    return G.hex_rgb(stops[-1][1])


def land_rows(rc, m, st):
    """RGB rows of the land and sea raster for a style, with Horn hillshade."""
    x0, y0, x1, y1 = rc["extent"]
    M = dict(X=m["x"], Y=m["y"], tris=G._tris(m))
    R = int(rc["params"].get("raster_px", 512))
    Z, B, px = G.raster(M, m["h"], m["biome"], x0, y0, x1, y1, R)
    Hh, Wd = len(Z), len(Z[0])
    biome_rgb = [G.hex_rgb(b[1]) for b in G.BIOMES]
    sat_rgb = [G.hex_rgb(SAT.get(b[0], b[1])) for b in G.BIOMES]
    sea_hi, sea_lo = st["sea"]
    flat = G.hex_rgb(st.get("landc", "#cccccc"))
    shade = st["shade"]
    zf = G.ELEV_LAND / 1000.0 * 6.0
    zen, az = math.radians(45), math.radians(135)
    hyp = {}
    rows = []
    for r in range(Hh):
        r0, r1, r2 = Z[max(r - 1, 0)], Z[r], Z[min(r + 1, Hh - 1)]
        out = bytearray()
        for c in range(Wd):
            z = r1[c]
            if z < 0:
                out += bytes(_ramp([(-1.0, sea_lo), (0.0, sea_hi)], max(-1.0, z * 1.5)))
                continue
            mode = st["land"]
            if mode == "hypso":
                k = int(G.elev_m(z) // 25)
                col = hyp.get(k)
                if col is None:
                    col = hyp[k] = _ramp(HYPSO, k * 25)
            elif mode == "biome":
                col = biome_rgb[B[r][c]]
            elif mode == "sat":
                col = sat_rgb[B[r][c]]
            else:
                col = flat
            cl, cr = max(c - 1, 0), min(c + 1, Wd - 1)
            dzdx = ((r0[cr] + 2 * r1[cr] + r2[cr]) - (r0[cl] + 2 * r1[cl] + r2[cl])) / (8 * px) * zf
            dzdy = ((r2[cl] + 2 * r2[c] + r2[cr]) - (r0[cl] + 2 * r0[c] + r0[cr])) / (8 * px) * zf
            slope = math.atan(math.hypot(dzdx, dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            v = math.cos(zen) * math.cos(slope) + math.sin(zen) * math.sin(slope) * math.cos(az - aspect)
            k = 1.0 - shade + shade * (0.45 + 0.75 * max(0.0, v))
            out += bytes(max(0, min(255, int(ch * k))) for ch in col)
        rows.append(out)
    return rows


# ------------------------------------------------------------------ labels
LABEL_SPEC = {  # kind: size, letter-spacing, upper, italic, priority
    "ocean": (22, 4.0, False, True, 1), "sea": (16, 2.0, False, True, 3), "land": (20, 4.0, True, False, 2),
    "range": (12, 2.5, True, False, 5), "city": (15, 0.0, False, False, 0), "town": (12, 0.0, False, False, 4),
    "village": (9.5, 0.0, False, False, 7), "river": (10.5, 0.5, False, True, 6),
}
DOT = {"city": 4.5, "town": 3.2, "village": 2.0}


def _river_spots(pts, need, maxdev=3.5):
    """Straight-enough stretches of a polyline at least `need` px long, middle first."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        for j in range(i + 1, n):
            ax, ay = pts[i]
            bx, by = pts[j]
            L = math.hypot(bx - ax, by - ay)
            if L < need:
                continue
            dev = 0.0
            for k in range(i + 1, j):
                px, py = pts[k]
                dev = max(dev, abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / L)
            if dev <= maxdev:
                out.append((abs((i + j) / 2 - (n - 1) / 2), i, j))
            break
    out.sort()
    return [(pts[i], pts[j]) for _, i, j in out]


def place_labels(features, frame, st, reserved=(), metrics=None):
    """Greedy placement in priority order. Returns (placed, dropped).

    Each placed label: dict(text, x, y, size, anchor, angle, ls, italic, box, kind).
    """
    x0, y0, s, Hs = frame
    mono = st.get("mono", False)
    pad = 1.5
    lim = (MARGIN, MARGIN, W - MARGIN, Hs - MARGIN)
    obstacles = list(reserved)
    cands = []
    rivers = {}
    for f in features:
        pr = f["properties"]
        k = pr["kind"]
        if k == "settlement":
            p = _to_px(f["geometry"]["coordinates"], x0, y0, s)
            r = DOT[pr["rank"]]
            obstacles.append((p[0] - r - 1, p[1] - r - 1, p[0] + r + 1, p[1] + r + 1))
            cands.append((LABEL_SPEC[pr["rank"]][4], -pr.get("score", 0), pr["name"], pr["rank"], p, r))
        elif k in ("ocean", "sea", "land", "range") and pr.get("name"):
            cands.append((LABEL_SPEC[k][4], 0, pr["name"], k, _to_px(f["geometry"]["coordinates"], x0, y0, s), 0))
        elif k == "river" and pr.get("name"):
            pts = [_to_px(c, x0, y0, s) for c in f["geometry"]["coordinates"]]
            L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
            if L > rivers.get(pr["name"], (0,))[0]:
                rivers[pr["name"]] = (L, pts)
    for name in sorted(rivers):
        cands.append((LABEL_SPEC["river"][4], -rivers[name][0], name, "river", rivers[name][1], 0))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    placed, dropped = [], []

    def free(box):
        if box[0] < lim[0] or box[1] < lim[1] or box[2] > lim[2] or box[3] > lim[3]:
            return False
        for b in obstacles:
            if overlap(box, b):
                return False
        return True

    for _, _, name, kind, p, r in cands:
        size, ls, upper, italic, _ = LABEL_SPEC[kind]
        text = name.upper() if upper else name
        opts = []
        if kind in DOT:
            g = r + 2.5
            cy = size * (ASC - DESC) / 2
            opts = [(p[0] + g, p[1] + cy, "start", 0), (p[0] - g, p[1] + cy, "end", 0),
                    (p[0], p[1] - g - DESC * size, "middle", 0), (p[0], p[1] + g + ASC * size, "middle", 0),
                    (p[0] + g * 0.8, p[1] - g * 0.8, "start", 0), (p[0] - g * 0.8, p[1] - g * 0.8, "end", 0),
                    (p[0] + g * 0.8, p[1] + g * 0.8 + ASC * size, "start", 0),
                    (p[0] - g * 0.8, p[1] + g * 0.8 + ASC * size, "end", 0)]
        elif kind == "river":
            need = text_width(text, size, ls, mono, metrics) + 12
            for a, b in _river_spots(p, need)[:12]:
                ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
                if ang > 90:
                    ang -= 180
                elif ang < -90:
                    ang += 180
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nxp, nyp = math.sin(math.radians(ang)), -math.cos(math.radians(ang))
                off = size * 0.45
                opts.append((mx + nxp * off, my + nyp * off, "middle", round(ang, 1)))
        else:
            hgt = size * 1.6
            ww = text_width(text, size, ls, mono, metrics)
            base = (p[0], p[1] + size * 0.3)
            opts = [base] + [(base[0] + dx * ww * 0.35, base[1] + dy * hgt)
                             for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1),
                                            (0, -2), (0, 2))]
            opts = [(o[0], o[1], "middle", 0) for o in opts]
        for x, y, anchor, ang in opts:
            x, y = round(x, 1), round(y, 1)
            box = text_box(x, y, size, text, anchor, ang, ls, pad, mono, metrics)
            if free(box):
                obstacles.append(box)
                placed.append(dict(text=text, x=x, y=y, size=size, anchor=anchor, angle=ang, ls=ls, italic=italic,
                                   box=box, kind=kind))
                break
        else:
            dropped.append(dict(text=text, kind=kind))
    return placed, dropped


# ------------------------------------------------------------------ furniture
def _nice(target):
    e = 10 ** math.floor(math.log10(target))
    for k in (5, 2, 1):
        if k * e <= target:
            return k * e
    return e


def scale_bar(frame, rc, st):
    x0, y0, s, Hs = frame
    kmpx = 1.0 / s
    km = _nice(180 * kmpx)
    L = km * s
    bx, by = W - MARGIN - 12 - L, Hs - MARGIN - 16
    box = (bx - 8, by - 22, W - MARGIN, Hs - MARGIN)
    ink, halo = st["ink"], st["halo"]
    o = ['<g class="scalebar" font-family="%s" font-size="11" fill="%s">' % (escape(st["font"], {"'": "&apos;"}), ink),
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.75"/>'
         % (box[0], box[1], box[2] - box[0], box[3] - box[1], halo)]
    for i in range(4):
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="5" fill="%s" stroke="%s" stroke-width="0.8"/>'
                 % (bx + i * L / 4, by, L / 4, ink if i % 2 == 0 else halo, ink))
    o.append('<text x="%.1f" y="%.1f">0</text>' % (bx - 3, by - 4))
    o.append('<text x="%.1f" y="%.1f" text-anchor="end">%g km</text>' % (bx + L + 6, by - 4, km))
    o.append("</g>")
    return o, box, km


def north_arrow(frame, st):
    x = W - MARGIN - 18
    y = MARGIN + 10
    box = (x - 14, y - 4, x + 14, y + 44)
    o = ['<g class="north">',
         '<rect x="%.1f" y="%.1f" width="28" height="48" fill="%s" fill-opacity="0.75"/>' % (box[0], box[1], st["halo"]),
         '<path d="M%.1f %.1fL%.1f %.1fL%.1f %.1fZ" fill="%s"/>' % (x, y + 14, x - 7, y + 38, x, y + 32, st["ink"]),
         '<path d="M%.1f %.1fL%.1f %.1fL%.1f %.1fZ" fill="none" stroke="%s" stroke-width="0.8"/>'
         % (x, y + 14, x + 7, y + 38, x, y + 32, st["ink"]),
         '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="%s" font-size="12" font-weight="bold" fill="%s">N</text>'
         % (x, y + 10, escape(st["font"], {"'": "&apos;"}), st["ink"]),
         "</g>"]
    return o, box


def legend_entries(features, m, st, rc):
    """The symbols actually drawn on this map, in drawing order."""
    kinds = {}
    for f in features:
        pr = f["properties"]
        k = pr["kind"]
        if k in ("road", "track"):
            kinds.setdefault("road:" + pr.get("rank", "minor"), True)
        elif k == "settlement":
            kinds.setdefault("settlement:" + pr["rank"], True)
        elif k == "lake" and f["geometry"]["coordinates"]:
            kinds["lake"] = True
        elif k in ("river", "coast"):
            kinds[k] = True
    ent = []
    if st["land"] in ("biome", "sat"):
        land = [h for h, o in zip(m["h"], m["ocean"]) if not o]
        seen = sorted(set(b for b, o, l in zip(m["biome"], m["ocean"], m["lake"]) if not o and l < 0))
        pal = SAT if st["land"] == "sat" else {}
        for b in seen:
            nm, col = G.BIOMES[b]
            ent.append(dict(kind="swatch", label=nm, fill=pal.get(nm, col)))
    elif st["land"] == "hypso":
        top = max([G.elev_m(h) for h, o in zip(m["h"], m["ocean"]) if not o] or [0])
        for (a, c), nxt in zip(HYPSO, HYPSO[1:] + [(None, None)]):
            if a <= top:
                ent.append(dict(kind="swatch", label="%d m+" % a if nxt[0] is None or nxt[0] > top
                                else "%d-%d m" % (a, nxt[0]), fill=c))
    else:
        ent.append(dict(kind="swatch", label="land", fill=st["landc"]))
    ent.append(dict(kind="swatch", label="sea", fill=st["sea"][0]))
    if kinds.get("coast"):
        ent.append(dict(kind="line", label="coast", stroke=st["coast"], width=1.1))
    if kinds.get("river"):
        ent.append(dict(kind="line", label="river", stroke=st["river"], width=1.6))
    if kinds.get("lake"):
        ent.append(dict(kind="swatch", label="lake", fill=st["lake"], stroke=st["river"]))
    for rank, i, lab in (("major", 0, "major road"), ("minor", 1, "minor road"), ("track", 2, "track")):
        if kinds.get("road:" + rank):
            ent.append(dict(kind="line", label=lab, stroke=st["roads"][i], width=(1.6, 1.0, 0.7)[i],
                            dash="3 2" if rank == "track" else ""))
    for rank in ("city", "town", "village"):
        if kinds.get("settlement:" + rank):
            ent.append(dict(kind="dot", label=rank, r=DOT[rank], fill=st["dot"]))
    return ent


def legend_svg(entries, frame, st):
    x0, y0, s, Hs = frame
    row = 15
    h = 22 + row * len(entries)
    w = 12 + 30 + max([text_width(e["label"], 10.5, 0, st.get("mono")) for e in entries] or [0]) + 10
    bx, by = MARGIN, Hs - MARGIN - h
    box = (bx, by, bx + w, by + h)
    f = escape(st["font"], {"'": "&apos;"})
    o = ['<g class="legend" font-family="%s" font-size="10.5" fill="%s">' % (f, st["ink"]),
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.85" stroke="%s" stroke-width="0.6"/>'
         % (bx, by, w, h, st["halo"], st["ink"]),
         '<text x="%.1f" y="%.1f" font-weight="bold">Legend</text>' % (bx + 8, by + 14)]
    for i, e in enumerate(entries):
        y = by + 22 + i * row
        sx = bx + 10
        if e["kind"] == "swatch":
            o.append('<rect x="%.1f" y="%.1f" width="22" height="10" fill="%s" stroke="%s" stroke-width="0.5"/>'
                     % (sx, y, e["fill"], e.get("stroke", st["ink"])))
        elif e["kind"] == "line":
            o.append('<path d="M%.1f %.1fh22" stroke="%s" stroke-width="%.1f" fill="none"%s/>'
                     % (sx, y + 5, e["stroke"], e["width"], ' stroke-dasharray="%s"' % e["dash"] if e.get("dash") else ""))
        else:
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="0.8"/>'
                     % (sx + 11, y + 5, e["r"], e["fill"], st["halo"]))
        o.append('<text x="%.1f" y="%.1f">%s</text>' % (sx + 30, y + 9, escape(e["label"])))
    o.append("</g>")
    return o, box


# ------------------------------------------------------------------ render
def _P(c, x0, y0, s):
    p = _to_px(c, x0, y0, s)
    return "%.1f %.1f" % p


def render_svg(d, style_name=DEFAULT_STYLE, font=None, title=None):
    """Return (svg_text, info). info: placed, dropped, legend, times, style."""
    t0 = time.perf_counter()
    st = style(style_name)
    rc, m, feats = load(d)
    metrics = TTFMetrics(font) if font else None
    frame = _frame(rc)
    x0, y0, s, Hs = frame
    times = {}
    rows = land_rows(rc, m, st)
    times["raster"] = time.perf_counter() - t0
    img = base64.b64encode(G.png_bytes(len(rows[0]) // 3, len(rows), rows, 8, 2)).decode()
    fam = escape(st["font"], {"'": "&apos;"})
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, Hs, W, Hs),
         '<rect width="100%%" height="100%%" fill="%s"/>' % st["sea"][1],
         '<image href="data:image/png;base64,%s" width="%d" height="%d" preserveAspectRatio="none"/>' % (img, W, Hs)]
    if st.get("stars"):
        o.append('<g fill="#ffffff">')
        for i in range(400):
            sx, sy = G.u01(rc["seed"], 911, i) * W, G.u01(rc["seed"], 912, i) * Hs
            o.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill-opacity="%.2f"/>'
                     % (sx, sy, 0.3 + 0.9 * G.u01(rc["seed"], 913, i) ** 3, 0.3 + 0.6 * G.u01(rc["seed"], 914, i)))
        o.append("</g>")
    if st.get("grid"):
        gd = "".join("M%d 0V%.1f" % (x, Hs) for x in range(50, int(W), 50))
        gd += "".join("M0 %dH%d" % (y, W) for y in range(50, int(Hs), 50))
        o.append('<path d="%s" stroke="%s" stroke-width="0.4" fill="none" stroke-opacity="0.6"/>' % (gd, st["grid"]))
    lakes, rivers, coast, roads, sets = [], [], [], [], []
    for f in feats:
        k = f["properties"]["kind"]
        {"lake": lakes, "river": rivers, "coast": coast, "road": roads, "track": roads,
         "settlement": sets}.get(k, []).append(f)
    d_l = []
    for f in lakes:
        for poly in f["geometry"]["coordinates"]:
            for ring in poly:
                d_l.append("M" + "L".join(_P(c, x0, y0, s) for c in ring) + "Z")
    if d_l:
        o.append('<path class="lakes" fill="%s" stroke="%s" stroke-width="0.6" d="%s"/>' % (st["lake"], st["river"], "".join(d_l)))
    thr = rc["params"]["river_threshold"]
    o.append('<g class="rivers" fill="none" stroke="%s" stroke-linecap="round" stroke-linejoin="round">' % st["river"])
    for f in rivers:
        w = min(3.5, 0.5 + 0.35 * math.sqrt(f["properties"]["acc"] / thr))
        o.append('<path stroke-width="%.2f" d="M%s"/>' % (w, "L".join(_P(c, x0, y0, s) for c in f["geometry"]["coordinates"])))
    o.append("</g>")
    cd = ["M" + "L".join(_P(c, x0, y0, s) for c in f["geometry"]["coordinates"]) for f in coast]
    o.append('<path class="coast" fill="none" stroke="%s" stroke-width="1.1" d="%s"/>' % (st["coast"], "".join(cd)))
    rk = {"major": (0, 1.6, ""), "minor": (1, 1.0, ""), "track": (2, 0.7, "3 2")}
    for f in roads:
        i, w, dash = rk.get(f["properties"].get("rank"), rk["minor"])
        o.append('<path fill="none" stroke="%s" stroke-width="%.1f"%s d="M%s"/>'
                 % (st["roads"][i], w, ' stroke-dasharray="%s"' % dash if dash else "",
                    "L".join(_P(c, x0, y0, s) for c in f["geometry"]["coordinates"])))
    for f in sets:
        p = _to_px(f["geometry"]["coordinates"], x0, y0, s)
        o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="0.8"/>'
                 % (p[0], p[1], DOT[f["properties"]["rank"]], st["dot"], st["halo"]))
    times["features"] = time.perf_counter() - t0 - times["raster"]
    # furniture first, so labels keep clear of it
    title = title if title is not None else "%s seed %d" % (rc["kind"], rc["seed"])
    tb = text_box(MARGIN + 6, MARGIN + 24, 20, title, pad=4, mono=st.get("mono"), metrics=metrics)
    sb, sbox, km = scale_bar(frame, rc, st)
    na, nbox = north_arrow(frame, st)
    ents = legend_entries(feats, m, st, rc)
    lg, lbox = legend_svg(ents, frame, st)
    placed, dropped = place_labels(feats, frame, st, reserved=[tb, sbox, nbox, lbox], metrics=metrics)
    times["labels"] = time.perf_counter() - t0 - times["raster"] - times["features"]
    o.append('<g class="labels" font-family="%s" fill="%s" stroke="%s" stroke-width="2.5" paint-order="stroke" '
             'stroke-linejoin="round">' % (fam, st["ink"], st["halo"]))
    for lb in placed:
        attrs = ['class="lbl"', 'x="%.1f"' % lb["x"], 'y="%.1f"' % lb["y"], 'font-size="%g"' % lb["size"]]
        if lb["anchor"] != "start":
            attrs.append('text-anchor="%s"' % lb["anchor"])
        if lb["ls"]:
            attrs.append('letter-spacing="%g"' % lb["ls"])
        if lb["italic"]:
            attrs.append('font-style="italic"')
        if lb["angle"]:
            attrs.append('transform="rotate(%g %.1f %.1f)"' % (lb["angle"], lb["x"], lb["y"]))
        o.append("<text %s>%s</text>" % (" ".join(attrs), escape(lb["text"])))
    o.append("</g>")
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.75"/>'
             % (tb[0], tb[1], tb[2] - tb[0], tb[3] - tb[1], st["halo"]))
    o.append('<text class="title" x="%.1f" y="%.1f" font-family="%s" font-size="20" fill="%s">%s</text>'
             % (MARGIN + 6, MARGIN + 24, fam, st["ink"], escape(title)))
    o += lg + sb + na
    o.append('<rect width="%d" height="%.1f" fill="none" stroke="%s" stroke-width="2"/>' % (W, Hs, st["ink"]))
    o.append("</svg>")
    times["total"] = time.perf_counter() - t0
    info = dict(style=style_name, placed=len(placed), dropped=[x["text"] for x in dropped],
                legend=[e["label"] for e in ents], scale_km=km, width=int(W), height=round(Hs, 1), times=times,
                labels=placed)
    return "\n".join(o) + "\n", info


# ------------------------------------------------------------------ browser export
def find_browser():
    import mpw
    return mpw.find_browser()


def svg_to(svg_path, out, browser=None, timeout=120):
    """SVG to PNG or PDF with headless Chrome or Edge."""
    browser = browser or find_browser()
    if not browser:
        raise RuntimeError("PNG and PDF need Chrome or Edge (headless); none found. Install one, or write .svg")
    with open(svg_path, encoding="utf-8") as f:
        svg = f.read()
    root = ET.fromstring(svg.encode("utf-8"))
    w = int(float(root.get("width")))
    h = int(math.ceil(float(root.get("height"))))
    tmp = tempfile.mkdtemp(prefix="mpw-")
    try:
        html = os.path.join(tmp, "page.html")
        with open(html, "w", encoding="utf-8", newline="\n") as f:
            f.write('<!doctype html><html><head><meta charset="utf-8"><style>@page{size:%dpx %dpx;margin:0}'
                    'html,body{margin:0;padding:0;overflow:hidden}svg{display:block}</style></head><body>%s</body></html>'
                    % (w, h, svg))
        url = "file:///" + html.replace("\\", "/").lstrip("/")
        out_abs = os.path.abspath(out)
        args = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                "--no-default-browser-check", "--user-data-dir=" + os.path.join(tmp, "prof")]
        if out.lower().endswith(".pdf"):
            args += ["--no-pdf-header-footer", "--print-to-pdf=" + out_abs, url]
        else:
            args += ["--window-size=%d,%d" % (w, h), "--screenshot=" + out_abs, url]
        if os.path.exists(out_abs):
            os.remove(out_abs)
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        if not os.path.isfile(out_abs):
            raise RuntimeError("browser did not write " + out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def write_out(svg, out):
    ext = os.path.splitext(out)[1].lower()
    if ext not in (".svg", ".png", ".pdf"):
        raise ValueError("-o wants .svg, .png or .pdf")
    if ext == ".svg":
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        return out
    tmp = tempfile.mkdtemp(prefix="mpw-")
    try:
        p = os.path.join(tmp, "map.svg")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        return svg_to(p, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ label bars
def labels_from_svg(svg, metrics=None):
    """Label boxes measured back from a rendered SVG's attributes (independent of the placer's state)."""
    root = ET.fromstring(svg.encode("utf-8"))
    w = float(root.get("width"))
    h = float(root.get("height"))
    fam = ""
    out = []
    for g in root.iter(SVGNS + "g"):
        if g.get("class") != "labels":
            continue
        fam = g.get("font-family", "")
        for t in g.iter(SVGNS + "text"):
            ang = 0.0
            tr = t.get("transform")
            if tr and tr.startswith("rotate("):
                ang = float(tr[7:-1].split()[0])
            box = text_box(float(t.get("x")), float(t.get("y")), float(t.get("font-size")), t.text or "",
                           t.get("text-anchor", "start"), ang, float(t.get("letter-spacing", 0)), 0.0,
                           "monospace" in fam, metrics)
            out.append((t.text or "", box))
    return out, w, h


def label_bars(svg, png_path=None):
    """Label proof bars: overlaps, edge cuts, OCR read-back. Returns [(name, ok, detail)] with ok None = skipped."""
    labs, w, h = labels_from_svg(svg)
    over = 0
    pairs = []
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            if overlap(labs[i][1], labs[j][1]):
                over += 1
                if len(pairs) < 3:
                    pairs.append("%s/%s" % (labs[i][0], labs[j][0]))
    cut = [t for t, b in labs if b[0] < 0 or b[1] < 0 or b[2] > w or b[3] > h]
    bars = [("labels: none overlap", over == 0, "%d labels, %d overlapping pairs%s"
             % (len(labs), over, (" e.g. " + ", ".join(pairs)) if pairs else "")),
            ("labels: none cut by the edge", not cut, "%d cut%s" % (len(cut), (": " + ", ".join(cut[:3])) if cut else ""))]
    tess = shutil.which("tesseract")
    if not tess:
        bars.append(("labels: read back by OCR", None, "skipped: tesseract not found (install it to run this bar)"))
    elif not png_path:
        bars.append(("labels: read back by OCR", None, "skipped: no PNG (needs Chrome or Edge to rasterise)"))
    else:
        r = subprocess.run([tess, png_path, "stdout"], capture_output=True, text=True, timeout=300)
        txt = "".join(ch for ch in r.stdout.lower() if ch.isalnum())
        words = [t for t, _ in labs]
        hit = [t for t in words if "".join(ch for ch in t.lower() if ch.isalnum()) in txt]
        bars.append(("labels: read back by OCR", len(hit) == len(words),
                     "%d of %d labels read back (bar unmeasured: every label must be read)" % (len(hit), len(words))))
    return bars


def check_labels(d, style_name=DEFAULT_STYLE):
    svg, info = render_svg(d, style_name)
    png = None
    if shutil.which("tesseract") and find_browser():
        tmp = tempfile.mkdtemp(prefix="mpw-")
        png = write_out(svg, os.path.join(tmp, "map.png"))
    return label_bars(svg, png)


# ------------------------------------------------------------------ serve
PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>%s</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%%;background:#222;overflow:hidden}#m{width:100%%;height:100%%;cursor:grab}
#m svg{width:100%%;height:100%%}#h{position:fixed;left:8px;bottom:8px;color:#ddd;font:12px sans-serif}</style></head>
<body><div id="m">%s</div><div id="h">drag to pan, wheel to zoom, double-click to reset</div><script>
const s=document.querySelector('#m svg');s.removeAttribute('width');s.removeAttribute('height');
const v0=s.getAttribute('viewBox').split(' ').map(Number);let v=v0.slice();
function set(){s.setAttribute('viewBox',v.join(' '))}
s.addEventListener('wheel',e=>{e.preventDefault();const r=s.getBoundingClientRect();
const k=e.deltaY>0?1.2:1/1.2;const sc=Math.max(v[2]/r.width,v[3]/r.height);
const ox=v[0]+(e.clientX-r.left-(r.width-v[2]/sc)/2)*sc,oy=v[1]+(e.clientY-r.top-(r.height-v[3]/sc)/2)*sc;
v=[ox-(ox-v[0])*k,oy-(oy-v[1])*k,v[2]*k,v[3]*k];set()},{passive:false});
let d=null;s.addEventListener('mousedown',e=>{d=[e.clientX,e.clientY,v[0],v[1]]});
addEventListener('mouseup',()=>d=null);addEventListener('mousemove',e=>{if(!d)return;const r=s.getBoundingClientRect();
const sc=Math.max(v[2]/r.width,v[3]/r.height);v[0]=d[2]-(e.clientX-d[0])*sc;v[1]=d[3]-(e.clientY-d[1])*sc;set()});
s.addEventListener('dblclick',()=>{v=v0.slice();set()});
</script></body></html>
"""
LOOPBACK = "127.0.0.1"


def make_server(svg, title="mapwright", port=0):
    """HTTP server for the pan/zoom page, bound to 127.0.0.1 only."""
    body = (PAGE % (escape(title), svg)).encode("utf-8")

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] not in ("/", "/index.html", "/map.svg"):
                self.send_error(404)
                return
            data = svg.encode("utf-8") if self.path.startswith("/map.svg") else body
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml" if self.path.startswith("/map.svg")
                             else "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass
    return http.server.ThreadingHTTPServer((LOOPBACK, port), H)


# ------------------------------------------------------------------ sheet
def sheet_svg(items, cols=None, cell=480.0):
    """items: [(caption, svg_text)]. Nests each map in one SVG grid."""
    n = len(items)
    cols = cols or min(n, 3)
    rows_n = int(math.ceil(n / float(cols)))
    parts = []
    hs = []
    for cap, svg in items:
        root_open = svg.index(">", svg.index("<svg")) + 1
        close = svg.rindex("</svg>")
        tag = svg[:root_open]
        vb = tag.split('viewBox="')[1].split('"')[0].split()
        hs.append(float(vb[3]) / float(vb[2]) * cell)
        parts.append((cap, vb, svg[root_open:close]))
    ch = max(hs) + 28
    gap = 12
    tw = cols * cell + (cols + 1) * gap
    th = rows_n * ch + (rows_n + 1) * gap
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (tw, th, tw, th),
         '<rect width="100%" height="100%" fill="#f4f4f2"/>']
    for i, (cap, vb, inner) in enumerate(parts):
        cx = gap + (i % cols) * (cell + gap)
        cy = gap + (i // cols) * (ch + gap)
        o.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="15" fill="#222">%s</text>'
                 % (cx, cy + 16, SANS.replace("'", "&apos;"), escape(cap)))
        o.append('<svg x="%.1f" y="%.1f" width="%.1f" height="%.1f" viewBox="%s">' % (cx, cy + 24, cell, hs[i], " ".join(vb)))
        o.append(inner)
        o.append("</svg>")
    o.append("</svg>")
    return "\n".join(o) + "\n"
