"""Natural caves by type and by geography, plus a light overlay.

Ideas from the Dungeoneer's Survival Guide (TSR, 1986; pp. 70-73, 114-121: how rock, what lies above, the
water table, heat and humidity shape a cave) and the Castle Keeper's Guide (Troll Lord Games; pp. 128-130:
cave types each with their own shape, light radius with a band of shadow). Code and word lists are our own.

typed_cave() draws the grid for one cave type. annotate() reads a finished grid and a geography and returns
sections tagged with clearance band, ceiling, climb surface, flooded and slick shares and collapse zones,
plus per-cell overlays. No numbers here come from the books; they are plain defaults you may change.
"""
import math

CAVE_TYPES = ("solution", "lava", "sea", "canyon", "crevice", "talus", "glacial")
ROCKS = ("limestone", "basalt", "sandstone", "granite", "shale", "ice")
ABOVE = ("open", "soil", "forest", "mountain", "lake", "sea", "city", "ruins")
HEAT = ("cold", "temperate", "hot", "volcanic")
HUMIDITY = ("dry", "damp", "wet")
# per type: default rock, wall chance inside the type mask, smoothing passes, base ceiling in metres
TYPE_INFO = {
    "solution": ("limestone", 0.30, 3, 4.0),
    "lava": ("basalt", 0.12, 3, 5.0),
    "sea": ("sandstone", 0.38, 4, 6.0),
    "canyon": ("sandstone", 0.25, 3, 15.0),
    "crevice": ("granite", 0.0, 0, 8.0),
    "talus": ("granite", 0.30, 2, 2.0),
    "glacial": ("ice", 0.36, 6, 5.0),
}
WEAK = dict(limestone=1, basalt=1, sandstone=2, granite=0, shale=3, ice=2)
LOAD = dict(open=0, soil=0, forest=0, mountain=1, lake=2, sea=2, city=2, ruins=1)
BANDS = ((1, "crawl"), (2, "stoop"), (4, "walk"), (10 ** 9, "hall"))
WALL, FLOOR = "#", "."


def _mask(ctype, w, h, rng):
    """Cells where the cave may open, by type."""
    m = [[False] * w for _ in range(h)]

    def dab(x, y, r):
        for yy in range(int(y - r), int(y + r) + 1):
            for xx in range(int(x - r), int(x + r) + 1):
                if 0 <= xx < w and 0 <= yy < h and (xx - x) ** 2 + (yy - y) ** 2 <= r * r + 0.25:
                    m[yy][xx] = True

    def line(x0, y0, x1, y1, r):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / float(n)
            dab(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r)
    if ctype == "solution":       # joint-guided network: passages along two crack directions, a few chambers
        for i in range(5 + w * h // 500):
            x, y = rng.uniform(3, w - 4), rng.uniform(3, h - 4)
            ang = (0.35 if i % 2 else 1.9) + rng.uniform(-0.2, 0.2)
            ln = rng.uniform(0.25, 0.55) * w
            line(x, y, x + math.cos(ang) * ln, y + math.sin(ang) * ln, rng.uniform(1.3, 2.2))
        for _ in range(3):
            dab(rng.uniform(5, w - 6), rng.uniform(5, h - 6), rng.uniform(2.5, 3.5))
    elif ctype == "lava":         # one long sinuous tube, end to end
        ph, amp, r = rng.uniform(0, 6.28), rng.uniform(0.15, 0.3) * h, rng.uniform(1.8, 2.4)
        prev = None
        for x in range(2, w - 2):
            y = h / 2.0 + amp * math.sin(ph + x * 2 * math.pi / (w * 0.8))
            if prev:
                line(prev[0], prev[1], x, y, r)
            prev = (x, y)
    elif ctype == "sea":          # a mouth on the west side, chambers shrinking inland
        cy = rng.uniform(0.35, 0.65) * h
        for x in range(1, w - 2):
            r = max(1.2, (h * 0.3) * (1 - x / float(w)) + 1.0)
            dab(x, cy + math.sin(x * 0.2) * 0.2 * h, r)
        for _ in range(3):
            dab(rng.uniform(w * 0.1, w * 0.5), rng.uniform(4, h - 5), rng.uniform(2, 3.5))
    elif ctype == "canyon":       # straight deep trench
        y0, y1 = rng.uniform(0.3, 0.7) * h, rng.uniform(0.3, 0.7) * h
        line(2, y0, w - 3, y1, rng.uniform(2.5, 3.5))
    elif ctype == "crevice":      # thin cracks crossing
        line(2, rng.uniform(2, h - 3), w - 3, rng.uniform(2, h - 3), 0.6)
        x0 = rng.uniform(0.3, 0.7) * w
        line(x0, 2, x0 + rng.uniform(-6, 6), h - 3, 0.6)
    elif ctype == "talus":        # piled blocks: many small pockets
        for _ in range(w * h // 28):
            dab(rng.uniform(2, w - 3), rng.uniform(2, h - 3), rng.uniform(1.6, 2.8))
    elif ctype == "glacial":      # broad smooth melt hall along the flow
        cy = rng.uniform(0.4, 0.6) * h
        for x in range(2, w - 2):
            dab(x, cy + 2 * math.sin(x * 0.15), 0.28 * h)
    else:
        raise ValueError("unknown cave type %r (%s)" % (ctype, ", ".join(CAVE_TYPES)))
    return m


def typed_cave(w, h, rng, ctype, stats=None):
    """A cave drawn for one type: the type mask, noise inside it, smoothing, the largest region kept."""
    import mpw_places as P
    if ctype not in TYPE_INFO:
        raise ValueError("unknown cave type %r (%s)" % (ctype, ", ".join(CAVE_TYPES)))
    fill, passes = TYPE_INFO[ctype][1], TYPE_INFO[ctype][2]
    m = _mask(ctype, w, h, rng)
    g = [[FLOOR if (0 < x < w - 1 and 0 < y < h - 1 and m[y][x] and rng.random() >= fill) else WALL
          for x in range(w)] for y in range(h)]
    for _ in range(passes):
        ng = [r[:] for r in g]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if not m[y][x]:
                    continue
                n = sum(g[y + dy][x + dx] == WALL for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
                ng[y][x] = WALL if n >= (4 if g[y][x] == WALL else 6) else FLOOR
        g = ng
    regions = P.flood_regions(g, w, h)
    if not regions:
        raise ValueError("cave came out solid; try another seed")
    big = set(max(regions, key=len))
    if stats is not None:
        stats["largest_region_share"] = len(big) / float(sum(len(r) for r in regions))
        stats["cave_type"] = ctype
    for y in range(h):
        for x in range(w):
            if g[y][x] == FLOOR and (x, y) not in big:
                g[y][x] = WALL
    return g, []


def geo_defaults(ctype=None, geo=None):
    """Fill a geography dict with defaults and check each value."""
    out = dict(rock=TYPE_INFO[ctype or "solution"][0], above="soil", water_table=0.2, heat="temperate",
               humidity="damp", built=False)
    out.update({k: v for k, v in (geo or {}).items() if v is not None})
    for k, allowed in (("rock", ROCKS), ("above", ABOVE), ("heat", HEAT), ("humidity", HUMIDITY)):
        if out[k] not in allowed:
            raise ValueError("--%s must be one of %s" % (k, ", ".join(allowed)))
    wt = float(out["water_table"])
    if not 0 <= wt <= 1:
        raise ValueError("--water-table must be 0 to 1 (share of the floor below the water table)")
    out["water_table"] = wt
    out["built"] = bool(out["built"])
    return out


def _wall_dist(g, w, h):
    """Steps from each cell to the nearest wall (8-neighbour BFS)."""
    q = [(x, y) for y in range(h) for x in range(w) if g[y][x] == WALL]
    d = dict.fromkeys(q, 0)
    i = 0
    while i < len(q):
        x, y = q[i]
        i += 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if 0 <= n[0] < w and 0 <= n[1] < h and n not in d:
                    d[n] = d[(x, y)] + 1
                    q.append(n)
    return d


def _depth(seed, x, y):
    """Smooth 0..1 floor-depth field: bilinear value noise on a 6-cell lattice."""
    import mpw_gen as G

    def v(i, j):
        return (G.h64(seed, 77, i, j) >> 11) / 9007199254740992.0
    fx, fy = x / 6.0, y / 6.0
    i, j = int(fx), int(fy)
    tx, ty = fx - i, fy - j
    a = v(i, j) * (1 - tx) + v(i + 1, j) * tx
    b = v(i, j + 1) * (1 - tx) + v(i + 1, j + 1) * tx
    return a * (1 - ty) + b * ty


def light_overlay(g, w, h, lights, radius=None):
    """Per cell: 'L' lit (walking distance within the light's range), 's' shadow band (out to twice the
    range), ' ' dark, '#' rock. Distance runs through floor, so light does not pass walls."""
    best = {}
    for L in lights:
        x0, y0 = int(L["x"]), int(L["y"])
        if not (0 <= x0 < w and 0 <= y0 < h) or g[y0][x0] == WALL:
            continue
        r = float(radius if radius is not None else L["range"])
        d = {(x0, y0): 0}
        q = [(x0, y0)]
        i = 0
        while i < len(q):
            x, y = q[i]
            i += 1
            if d[(x, y)] >= 2 * r:
                continue
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= n[0] < w and 0 <= n[1] < h and n not in d and g[n[1]][n[0]] != WALL:
                    d[n] = d[(x, y)] + 1
                    q.append(n)
        for p, v in d.items():
            best[p] = max(best.get(p, 0), 2 if v <= r else 1)
    sym = {0: " ", 1: "s", 2: "L"}
    return ["".join("#" if g[y][x] == WALL else sym[best.get((x, y), 0)] for x in range(w)) for y in range(h)]


def _band(span):
    return next(b for lim, b in BANDS if span <= lim)


def annotate(g, w, h, seed, ctype=None, geo=None, lights=(), chunk=6):
    """Floor sections tagged by geography, and the cell overlays."""
    geo = geo_defaults(ctype, geo)
    wd = _wall_dist(g, w, h)
    base = 2.5 if geo["built"] else TYPE_INFO[ctype or "solution"][3]
    frozen = geo["heat"] == "cold" or geo["rock"] == "ice"
    risk = WEAK[geo["rock"]] + LOAD[geo["above"]] + (geo["heat"] == "volcanic") + geo["built"]
    cells = []
    for y in range(h):
        row = []
        for x in range(w):
            if g[y][x] == WALL:
                row.append("#")
                continue
            dp = _depth(seed, x, y)
            if dp < geo["water_table"]:
                row.append("~")
            elif not geo["built"] and (frozen or geo["humidity"] == "wet" or
                                       (geo["humidity"] == "damp" and dp < geo["water_table"] + 0.1)):
                row.append("s")
            else:
                row.append(".")
        cells.append(row)
    sections = []
    seen = set()
    for cy in range(0, h, chunk):
        for cx in range(0, w, chunk):
            for y in range(cy, min(h, cy + chunk)):
                for x in range(cx, min(w, cx + chunk)):
                    if g[y][x] == WALL or (x, y) in seen:
                        continue
                    comp, i = [(x, y)], 0
                    seen.add((x, y))
                    while i < len(comp):
                        px, py = comp[i]
                        i += 1
                        for n in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                            if cx <= n[0] < min(w, cx + chunk) and cy <= n[1] < min(h, cy + chunk) \
                                    and n not in seen and g[n[1]][n[0]] != WALL:
                                seen.add(n)
                                comp.append(n)
                    span = max(wd[p] for p in comp)          # steps to rock from the section's widest cell
                    band = _band(span)
                    ceil = 1.0 if band == "crawl" else round(base * (0.5 + 0.25 * min(span, 4)), 1)
                    fl = sum(cells[py][px] == "~" for px, py in comp) / float(len(comp))
                    sl = sum(cells[py][px] == "s" for px, py in comp) / float(len(comp))
                    if geo["built"]:
                        climb = "worked stone"
                    elif frozen:
                        climb = "ice"
                    elif ctype == "talus":
                        climb = "scree"
                    elif geo["rock"] == "basalt":
                        climb = "glassy rock"
                    elif fl > 0.5 or geo["humidity"] == "wet":
                        climb = "wet rock"
                    else:
                        climb = "dry rock"
                    collapse = (risk >= 4 and band != "crawl") or (risk == 3 and band == "hall")
                    mx = sum(p[0] for p in comp) / float(len(comp))
                    my = sum(p[1] for p in comp) / float(len(comp))
                    sections.append(dict(id=len(sections), cells=len(comp), at=[round(mx, 1), round(my, 1)],
                                         clearance=band, ceiling_m=ceil, climb=climb, flooded=round(fl, 2),
                                         slick=round(sl, 2), collapse=collapse))
                    if collapse:
                        for px, py in comp:
                            if cells[py][px] == ".":
                                cells[py][px] = "x"
    out = dict(type=ctype, geo=geo, collapse_risk=int(risk), sections=sections, cells=["".join(r) for r in cells],
               cell_key={"#": "rock", ".": "dry floor", "~": "flooded", "s": "slick", "x": "collapse zone"})
    if lights:
        out["light"] = light_overlay(g, w, h, lights)
        out["light_key"] = {"L": "lit", "s": "shadow band", " ": "dark", "#": "rock"}
    return out
