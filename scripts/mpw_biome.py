"""Biome presets for battle maps: noise-banded ground terrain and declarative scatter rules.

A biome is data. Ground terrain comes from one seeded value-noise field cut into bands (the lowest band
might be water, the next marsh, the rest grass). Scatter rules say what to place, not how:
  feature      name written to features.geojson
  per10k       [lo, hi] count per 10 000 cells; the target is drawn once from that range and scaled to the map
  min_spacing  no two of the same feature closer than this (cells, Euclidean between centres)
  edge_margin  keep this many cells clear of the map edge
  avoid        terrain names the feature may not stand on
  cell         "rock" or "tree" to also block the cell, or null for a marker only
Standard library only. Draws only from its own streams so the base battle map is untouched.
"""
import json
import math
import random

TERRAIN_STREAM = 4100
SCATTER_STREAM = 4200

# terrain name -> (one-letter code, colour)
TERRAIN = {
    "grass": ("g", "#c9d6a3"), "soil": ("s", "#cdb68f"), "rich": ("r", "#a99467"), "moss": ("m", "#a7bf8a"),
    "marsh": ("h", "#9fb59a"), "water": ("w", "#9cc3d9"), "sand": ("d", "#e6d3a3"), "gravel": ("v", "#c2bcb0"),
    "snow": ("n", "#f1f3f4"), "ice": ("i", "#d4e7f0"),
}

# bands: [(upper cut, terrain)], read in order; the last cut should be 1.0
BIOMES = {
    "temperate": dict(freq=0.09, bands=[(0.14, "water"), (0.24, "marsh"), (0.78, "grass"), (1.0, "rich")], scatter=[
        dict(feature="tree", per10k=[180, 260], min_spacing=1.5, edge_margin=1, avoid=["water", "marsh"], cell="tree"),
        dict(feature="bush", per10k=[120, 180], min_spacing=1.0, edge_margin=0, avoid=["water"], cell=None),
        dict(feature="boulder", per10k=[20, 40], min_spacing=4, edge_margin=2, avoid=["water", "marsh"], cell="rock")]),
    "boreal": dict(freq=0.08, bands=[(0.12, "water"), (0.30, "moss"), (1.0, "soil")], scatter=[
        dict(feature="tree", per10k=[300, 400], min_spacing=1.4, edge_margin=1, avoid=["water"], cell="tree"),
        dict(feature="boulder", per10k=[30, 50], min_spacing=4, edge_margin=2, avoid=["water"], cell="rock")]),
    "tundra": dict(freq=0.07, bands=[(0.10, "ice"), (0.55, "snow"), (0.85, "moss"), (1.0, "gravel")], scatter=[
        dict(feature="shrub", per10k=[60, 100], min_spacing=2, edge_margin=0, avoid=["ice"], cell=None),
        dict(feature="boulder", per10k=[40, 60], min_spacing=5, edge_margin=2, avoid=["ice"], cell="rock")]),
    "desert": dict(freq=0.06, bands=[(0.70, "sand"), (0.92, "gravel"), (1.0, "soil")], scatter=[
        dict(feature="cactus", per10k=[30, 60], min_spacing=3, edge_margin=1, avoid=[], cell="tree"),
        dict(feature="boulder", per10k=[30, 50], min_spacing=5, edge_margin=2, avoid=[], cell="rock"),
        dict(feature="spring", per10k=[2, 6], min_spacing=12, edge_margin=4, avoid=["gravel"], cell=None)]),
    "swamp": dict(freq=0.11, bands=[(0.38, "water"), (0.72, "marsh"), (1.0, "moss")], scatter=[
        dict(feature="tree", per10k=[120, 180], min_spacing=1.5, edge_margin=1, avoid=["water"], cell="tree"),
        dict(feature="reeds", per10k=[150, 220], min_spacing=1.0, edge_margin=0, avoid=["moss"], cell=None)]),
}

RULE_KEYS = ("feature", "per10k", "min_spacing", "edge_margin", "avoid", "cell")


def _lattice(seed, stream, gx, gy):
    return random.Random("%d:%d:%d:%d" % (seed, stream, gx, gy)).random()


def value_noise(seed, w, h, freq, octaves=3):
    """Seeded value noise in [0, 1): smoothstep-interpolated lattice values, summed octaves, then rank-normalised
    so a band cut of 0.3 covers about 30% of the cells whatever the frequency."""
    raw = [[0.0] * w for _ in range(h)]
    amp, f, tot = 1.0, freq, 0.0
    for o in range(octaves):
        for y in range(h):
            for x in range(w):
                fx, fy = x * f, y * f
                x0, y0 = int(math.floor(fx)), int(math.floor(fy))
                tx, ty = fx - x0, fy - y0
                sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
                a = _lattice(seed, TERRAIN_STREAM + o, x0, y0)
                b = _lattice(seed, TERRAIN_STREAM + o, x0 + 1, y0)
                c = _lattice(seed, TERRAIN_STREAM + o, x0, y0 + 1)
                d = _lattice(seed, TERRAIN_STREAM + o, x0 + 1, y0 + 1)
                raw[y][x] += amp * ((a + (b - a) * sx) * (1 - sy) + (c + (d - c) * sx) * sy)
        tot += amp
        amp *= 0.5
        f *= 2.0
    order = sorted((raw[y][x], y, x) for y in range(h) for x in range(w))
    n = float(len(order))
    out = [[0.0] * w for _ in range(h)]
    for i, (_, y, x) in enumerate(order):
        out[y][x] = i / n
    return out


def terrain_grid(seed, w, h, biome):
    field = value_noise(seed, w, h, biome["freq"])
    rows = []
    for y in range(h):
        r = []
        for x in range(w):
            v = field[y][x]
            for cut, name in biome["bands"]:
                if v < cut:
                    break
            r.append(name)
        rows.append(r)
    return rows


def validate_rules(rules):
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list of scatter rules")
    for r in rules:
        miss = [k for k in ("feature", "per10k") if k not in r]
        if miss:
            raise ValueError("scatter rule needs %s" % ", ".join(miss))
        extra = [k for k in r if k not in RULE_KEYS]
        if extra:
            raise ValueError("unknown scatter rule key %s (allowed: %s)" % (", ".join(extra), ", ".join(RULE_KEYS)))
        lo, hi = r["per10k"]
        if not 0 <= lo <= hi:
            raise ValueError("per10k must be [lo, hi] with 0 <= lo <= hi")
        if r.get("cell") not in (None, "rock", "tree"):
            raise ValueError("cell must be rock, tree or null")
        for t in r.get("avoid", []):
            if t not in TERRAIN:
                raise ValueError("unknown terrain %r in avoid (known: %s)" % (t, ", ".join(sorted(TERRAIN))))
    return [dict(feature=r["feature"], per10k=[float(r["per10k"][0]), float(r["per10k"][1])],
                 min_spacing=float(r.get("min_spacing", 0)), edge_margin=int(r.get("edge_margin", 0)),
                 avoid=list(r.get("avoid", [])), cell=r.get("cell")) for r in rules]


def load_rules(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return validate_rules(data.get("scatter", data) if isinstance(data, dict) else data)


def scatter(g, terrain, w, h, rules, seed, mult, free, blocks_ok, cellmap):
    """Place each rule's items on cells where free(x, y) holds. blocks_ok(x, y) says a blocking item may go there.
    Returns [{feature, target, placed, points}] in rule order. Deterministic per seed."""
    n = w * h
    out = []
    taken = set()
    for i, r in enumerate(rules):
        rng = random.Random("%d:%d:%d" % (seed, SCATTER_STREAM, i))
        lo, hi = r["per10k"]
        target = int(round(rng.uniform(lo, hi) * mult * n / 10000.0))
        m = r["edge_margin"]
        cands = [(x, y) for y in range(m, h - m) for x in range(m, w - m)
                 if (x, y) not in taken and terrain[y][x] not in r["avoid"] and free(x, y)]
        rng.shuffle(cands)
        pts = []
        sp2 = r["min_spacing"] ** 2
        for x, y in cands:
            if len(pts) >= target:
                break
            if (x, y) in taken or not free(x, y):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < sp2 for px, py in pts):
                continue
            if r["cell"] and not blocks_ok(x, y):
                continue
            pts.append((x, y))
            taken.add((x, y))
            if r["cell"]:
                g[y][x] = cellmap[r["cell"]]
        out.append(dict(feature=r["feature"], target=target, placed=len(pts), points=[list(p) for p in pts]))
    return out
