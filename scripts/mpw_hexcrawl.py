"""mapwright hexcrawl: a seeded fantasy wilderness hex map and its sandbox kit, plus the check bars and the
sandbox.json lint.

- grid: flat-topped hexes in columns (odd-q, the sector's layout), hex IDs column+row as four digits (0101 top left).
- terrain: seeded region growing from scattered seeds, so terrain comes in coherent patches. Every connected patch of
  one terrain two or more hexes big is a feature, lettered once on the map and listed A-Z in the geography.
- keys: about a third of the land hexes keyed on purpose (--keyed), the rest left for the GM to fill.
- per terrain: a hazard rolled per hex entered (chance in 10) and a top predator as a soft level gate.
- landmarks: keyed sites seen from afar carry a sight radius in hexes.
- sandbox.json: overview, geography, rumor slots (true, false, half-true), encounter slots (home hex, purpose,
  one clash result) and keyed hexes. Format idea from Points of Light (Goodman Games); every word list is our own.
"""
import os
import time
from xml.sax.saxutils import escape

import mpw_names
import mpw_places as P
import mpw_space as S

HEX_VERSION = "hexcrawl-1"
LAND = ("grassland", "forest", "hills", "mountains", "marsh", "heath")
TERRAIN = {
    # weight, fill, feature noun, hazard (text, chance in 10 per hex entered), top predator (name, level from)
    "grassland": (5, "#c9d98a", "Fields", ("grass fire on the wind", 1), ("lion pack", 2)),
    "forest": (4, "#5f9a5a", "Wood", ("lost the trail under the canopy", 2), ("great bear", 4)),
    "hills": (3, "#b9a46a", "Downs", ("loose scree and a turned ankle", 1), ("hill giant band", 7)),
    "mountains": (2, "#8a7f78", "Peaks", ("rockfall on the pass", 2), ("roc pair", 9)),
    "marsh": (2, "#7fa79a", "Fen", ("sucking mire swallows a pack", 2), ("swamp hydra", 6)),
    "heath": (2, "#c2a7b8", "Moor", ("cold fog, no landmark in sight", 1), ("barrow wight", 5)),
    "lake": (1, "#7fb3d8", "Water", ("sudden squall on open water", 2), ("lake serpent", 8)),
}
KINDS = {
    # kind, weight per terrain group, landmark?
    "village": (("grassland", "forest", "hills", "heath"), 3, False),
    "ruin": (LAND, 3, False),
    "lair": (LAND, 3, False),
    "camp": (("grassland", "forest", "hills", "heath", "marsh"), 2, False),
    "shrine": (LAND, 2, False),
    "cave": (("hills", "mountains", "forest"), 2, False),
    "tower": (LAND, 1, True),
    "standing stones": (("grassland", "hills", "heath"), 1, True),
    "lone peak": (("mountains", "hills"), 1, True),
}
SIGHT = {"mountains": 4, "hills": 3}          # landmark sight in hexes; other terrain 2, a tower one more
PURPOSES = ("hunting", "raiding", "scouting", "foraging", "trading", "on pilgrimage", "escorting captives",
            "fleeing pursuit")
SOFT = ("escorting captives", "fleeing pursuit")
HOMES = ("lair", "camp", "village", "cave")


def hex_id(c, rw):
    return "%02d%02d" % (c + 1, rw + 1)


def parse_hex(h):
    s = str(h)
    if len(s) != 4 or not s.isdigit():
        raise ValueError("hex %r: use four digits, column then row, such as 0307" % (h,))
    return int(s[:2]) - 1, int(s[2:]) - 1


def neighbours(c, rw, cols, rows):
    odd = c & 1
    steps = ((0, -1), (0, 1), (-1, -1 + odd), (-1, odd), (1, -1 + odd), (1, odd))
    for dc, dr in steps:
        x, y = c + dc, rw + dr
        if 0 <= x < cols and 0 <= y < rows:
            yield x, y


def letter(i):
    s = ""
    i += 1
    while i:
        i, k = divmod(i - 1, 26)
        s = chr(65 + k) + s
    return s


def grow_terrain(r, cols, rows):
    """Region growing: seeds with weighted terrain, then a random frontier claims one neighbour at a time."""
    n = cols * rows
    names = sorted(TERRAIN)
    total = sum(TERRAIN[t][0] for t in names)
    grid = {}
    front = []
    for _ in range(max(6, n // 8)):
        c, rw = r.randint(0, cols - 1), r.randint(0, rows - 1)
        if (c, rw) in grid:
            continue
        x, acc = r.random() * total, 0
        for t in names:
            acc += TERRAIN[t][0]
            if x < acc:
                break
        grid[(c, rw)] = t
        front.append((c, rw))
    while front:
        i = r.randint(0, len(front) - 1)
        c, rw = front[i]
        free = [q for q in neighbours(c, rw, cols, rows) if q not in grid]
        if not free:
            front[i] = front[-1]
            front.pop()
            continue
        q = free[r.randint(0, len(free) - 1)]
        grid[q] = grid[(c, rw)]
        front.append(q)
    return grid


def features(grid, cols, rows):
    """Connected patches of one terrain, two or more hexes, lettered A-Z in hex ID order of their first hex."""
    seen, out = set(), []
    for c in range(cols):
        for rw in range(rows):
            if (c, rw) in seen:
                continue
            t, comp, todo = grid[(c, rw)], [], [(c, rw)]
            seen.add((c, rw))
            while todo:
                q = todo.pop()
                comp.append(q)
                for nb in neighbours(q[0], q[1], cols, rows):
                    if nb not in seen and grid[nb] == t:
                        seen.add(nb)
                        todo.append(nb)
            if len(comp) >= 2:
                out.append((t, sorted(comp)))
    return out


def centre_hex(cells):
    mx = sum(c for c, _ in cells) / len(cells)
    my = sum(rw for _, rw in cells) / len(cells)
    return min(cells, key=lambda q: ((q[0] - mx) ** 2 + (q[1] - my) ** 2, q))


def _pick_kind(r, terrain):
    opts = [(k, v[1]) for k, v in sorted(KINDS.items()) if terrain in v[0]]
    x, acc = r.random() * sum(w for _, w in opts), 0
    for k, w in opts:
        acc += w
        if x < acc:
            return k
    return opts[-1][0]


def gen_hexcrawl(seed, out, cols=20, rows=16, keyed=0.33, miles=6, version="0.36.0", name_style=None):
    t0 = time.perf_counter()
    if not (6 <= cols <= 60 and 6 <= rows <= 60):
        raise ValueError("--cols and --rows are 6 to 60 hexes")
    if not 0.05 <= keyed <= 0.9:
        raise ValueError("--keyed is a share of land hexes, 0.05 to 0.9")
    if not 1 <= miles <= 50:
        raise ValueError("--miles is 1 to 50 per hex")
    r = P.Rng(seed, 401)
    lang = mpw_names.make_language(seed, name_style)
    namer = mpw_names.Namer(lang)
    grid = grow_terrain(r, cols, rows)
    feats = features(grid, cols, rows)
    letter_of, geo = {}, []
    for i, (t, cells) in enumerate(feats):
        lt = letter(i)
        for q in cells:
            letter_of[q] = lt
        ch = centre_hex(cells)
        geo.append(dict(letter=lt, name="%s %s" % (namer.name("feature", (i,)), TERRAIN[t][2]), terrain=t,
                        hexes=[hex_id(*q) for q in cells], label_hex=hex_id(*ch)))
    land = [q for q in sorted(grid) if grid[q] != "lake"]
    want = max(1, int(round(keyed * len(land))))
    pool = list(land)
    for i in range(len(pool) - 1, 0, -1):
        j = r.randint(0, i)
        pool[i], pool[j] = pool[j], pool[i]
    keys = []
    for q in sorted(pool[:want]):
        t = grid[q]
        kind = _pick_kind(r, t)
        k = dict(hex=hex_id(*q), kind=kind, title="%s %s" % (namer.name("site", q), kind), terrain=t,
                 feature=letter_of.get(q), text="")
        if KINDS[kind][2]:
            k["landmark"] = True
            k["sight"] = SIGHT.get(t, 2) + (1 if kind == "tower" else 0)
        keys.append(k)
    if not any(k.get("landmark") for k in keys):
        k = keys[0]
        k.update(kind="tower", title="%s tower" % k["title"].rsplit(" ", 1)[0], landmark=True,
                 sight=SIGHT.get(k["terrain"], 2) + 1)
    keyed_ids = [k["hex"] for k in keys]
    homes = [k["hex"] for k in keys if k["kind"] in HOMES] or keyed_ids
    enc = [dict(roll=1, kind="clash", text="results 2 and 3 meet and fight each other")]
    for n in range(2, 11):
        p = PURPOSES[r.randint(0, len(PURPOSES) - 1)]
        e = dict(roll=n, kind="group", group="", home=homes[r.randint(0, len(homes) - 1)], purpose=p, roster="")
        if p in SOFT:
            e["complication_pct"] = 20
        enc.append(e)
    truth = ["true"] * 4 + ["false"] * 3 + ["half"]
    for i in range(len(truth) - 1, 0, -1):
        j = r.randint(0, i)
        truth[i], truth[j] = truth[j], truth[i]
    unkeyed = [hex_id(*q) for q in land if hex_id(*q) not in keyed_ids] or keyed_ids
    rumors = []
    for i, tv in enumerate(truth):
        tgt = (keyed_ids if tv != "false" else unkeyed)[r.randint(0, len(keyed_ids if tv != "false" else unkeyed) - 1)]
        rumors.append(dict(roll=i + 1, truth=tv, hex=tgt, text=""))
    used = sorted({grid[q] for q in grid})
    terrain = {t: dict(hazard=TERRAIN[t][3][0], hazard_in_10=TERRAIN[t][3][1], predator=TERRAIN[t][4][0],
                       predator_level=TERRAIN[t][4][1]) for t in used}
    name = "%s Reach" % namer.name("land", (seed,))
    overview = dict(name=name, grid=dict(cols=cols, rows=rows, ids="column+row, four digits, 0101 top left",
                                         layout="flat-top columns, odd columns half a hex lower"),
                    miles_per_hex=miles, hexes=len(grid), land_hexes=len(land), keyed=len(keys),
                    keyed_share=round(len(keys) / float(len(land)), 4), text="")
    sandbox = dict(overview=overview, terrain=terrain, geography=geo, rumors=rumors, encounters=enc, keys=keys)
    hexes = [dict(hex=hex_id(c, rw), terrain=grid[(c, rw)], feature=letter_of.get((c, rw)))
             for c in range(cols) for rw in range(rows)]
    params = dict(cols=cols, rows=rows, keyed=keyed, miles=miles, name_style=name_style)
    recipe = dict(kind="hexcrawl", seed=int(seed), tool_version=version, hex_version=HEX_VERSION, params=params,
                  language=lang)
    t1 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    P.dump(os.path.join(out, "hexcrawl.json"), dict(name=name, grid=overview["grid"], hexes=hexes))
    P.dump(os.path.join(out, "sandbox.json"), sandbox)
    names = [dict(kind="feature", id=g["letter"], name=g["name"]) for g in geo]
    names += [dict(kind="site", id=k["hex"], name=k["title"]) for k in keys]
    P.dump(os.path.join(out, "names.json"), {"seed": int(seed), "language": lang, "names": names})
    P.dump(os.path.join(out, "sources.json"), {"files": [], "note": "generated; nothing fetched. Kit format after "
                                               "Points of Light (Goodman Games); no content from it"})
    P.dump(os.path.join(out, "recipe.json"), recipe)
    S._write(out, "map.svg", render_svg(sandbox, hexes))
    return dict(out=out, kind="hexcrawl", name=name, hexes=len(grid), features=len(geo), keyed=len(keys),
                landmarks=sum(1 for k in keys if k.get("landmark")),
                times=dict(generate=round(t1 - t0, 3), total=round(time.perf_counter() - t0, 3)))


ST = dict(bg="#f4ecd8", ink="#2b2118", grid="#6b5a44", key="#8a1f1f", font="Georgia, serif", halo="#f4ecd8")


def render_svg(sb, hexes, st=ST):
    g = sb["overview"]["grid"]
    cols, rows = g["cols"], g["rows"]
    rad, m, top, side = 22.0, 20.0, 44.0, 230.0
    mw = 1.5 * rad * cols + 0.5 * rad
    w = int(mw + 2 * m + side)
    h = int(max(S.SQ3 * rad * (rows + 0.5), 14 * (len(sb["geography"]) + 4)) + top + m + 24)
    o = S._svg_head(w, h, st["bg"])
    o.append('<text x="%d" y="28" font-family="%s" font-size="18" fill="%s">%s</text>'
             % (m, st["font"], st["ink"], escape(sb["overview"]["name"])))

    def ctr(c, rw):
        x, y = S.hex_center(c, rw, rad)
        return x + m + rad, y + top + S.SQ3 * rad / 2

    def poly(cx, cy):
        return "M" + "L".join("%.1f,%.1f" % (cx + rad * S.math.cos(S.math.pi / 3 * i),
                                            cy + rad * S.math.sin(S.math.pi / 3 * i)) for i in range(6)) + "Z"
    for hx in hexes:
        c, rw = parse_hex(hx["hex"])
        cx, cy = ctr(c, rw)
        o.append('<path class="hex %s" d="%s" fill="%s" stroke="%s" stroke-width="0.6"/>'
                 % (hx["terrain"], poly(cx, cy), TERRAIN[hx["terrain"]][1], st["grid"]))
        o.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="6" fill="%s" text-anchor="middle">%s</text>'
                 % (cx, cy - rad * 0.55, st["font"], st["grid"], hx["hex"]))
    o.append('<g class="features" font-family="%s" font-size="13" font-weight="bold" fill="%s">' % (st["font"], st["ink"]))
    for f in sb["geography"]:
        cx, cy = ctr(*parse_hex(f["label_hex"]))
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (cx, cy + rad * 0.7, f["letter"]))
    o.append("</g>")
    for k in sb["keys"]:
        cx, cy = ctr(*parse_hex(k["hex"]))
        if k.get("landmark"):
            o.append('<path class="landmark" d="M%.1f,%.1fL%.1f,%.1fL%.1f,%.1fZ" fill="%s"/>'
                     % (cx, cy - 5, cx - 4.5, cy + 3.5, cx + 4.5, cy + 3.5, st["key"]))
        else:
            o.append('<circle class="key" cx="%.1f" cy="%.1f" r="3.2" fill="%s"/>' % (cx, cy, st["key"]))
    x0, y = m + mw + 18, top + 8
    o.append('<g class="legend" font-family="%s" font-size="10" fill="%s">' % (st["font"], st["ink"]))
    o.append('<text x="%.1f" y="%.1f" font-weight="bold">Geography</text>' % (x0, y))
    for f in sb["geography"]:
        y += 14
        o.append('<text x="%.1f" y="%.1f">%s  %s</text>' % (x0, y, f["letter"], escape(f["name"])))
    y += 22
    o.append('<text x="%.1f" y="%.1f">dot: keyed hex; triangle: landmark</text>' % (x0, y))
    o.append("</g>")
    bar = 3 * 1.5 * rad
    by = h - 14
    o.append('<path d="M%.1f,%.1fh%.1f" stroke="%s" stroke-width="2"/>' % (m, by, bar, st["ink"]))
    o.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="10" fill="%s">3 hexes, %d miles (1 hex = %d '
             'miles)</text>' % (m + bar + 8, by + 4, st["font"], st["ink"], 3 * sb["overview"]["miles_per_hex"],
                                sb["overview"]["miles_per_hex"]))
    o.append(P.labels_svg([], st))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def regenerate(d, tmp):
    rc = P.load(d, "recipe.json")
    p = rc["params"]
    gen_hexcrawl(rc["seed"], tmp, p["cols"], p["rows"], p["keyed"], p["miles"], rc["tool_version"], p["name_style"])


def sandbox_issues(sb):
    """Problems with a sandbox.json kit: every hex inside the map, one key per hex, homes and true rumors on keyed
    hexes, a clash result, landmarks with a sight radius, terrain with hazard and predator. Returns [text]."""
    w = []
    g = (sb.get("overview") or {}).get("grid") or {}
    cols, rows = g.get("cols"), g.get("rows")
    if not cols or not rows:
        return ["overview.grid has no cols and rows: the map size is unknown"]

    def inside(h, what):
        try:
            c, rw = parse_hex(h)
        except ValueError as e:
            w.append("%s: %s" % (what, e))
            return False
        if not (0 <= c < cols and 0 <= rw < rows):
            w.append("%s hex %s is outside the %dx%d map" % (what, h, cols, rows))
            return False
        return True
    keys = sb.get("keys") or []
    ids = [k.get("hex") for k in keys]
    for k in keys:
        inside(k.get("hex"), "key %s" % k.get("title", ""))
        if k.get("landmark") and not k.get("sight"):
            w.append("landmark %s has no sight radius in hexes" % k.get("hex"))
    for h in sorted({x for x in ids if ids.count(x) > 1}):
        w.append("hex %s is keyed more than once" % h)
    keyed = set(ids)
    for f in sb.get("geography") or []:
        for h in f.get("hexes") or []:
            inside(h, "feature %s" % f.get("letter"))
    letters = [f.get("letter") for f in sb.get("geography") or []]
    if letters != sorted(letters, key=lambda s: (len(s or ""), s or "")):
        w.append("geography is not listed A-Z")
    for e in sb.get("encounters") or []:
        if e.get("home") is not None and inside(e["home"], "encounter %s home" % e.get("roll")) \
                and e["home"] not in keyed:
            w.append("encounter %s home hex %s is not keyed" % (e.get("roll"), e["home"]))
    if sb.get("encounters") and not any(e.get("kind") == "clash" for e in sb["encounters"]):
        w.append("encounter chart has no clash result (two groups meet)")
    rum = sb.get("rumors") or []
    for x in rum:
        if x.get("hex") is not None and inside(x["hex"], "rumor %s" % x.get("roll")) \
                and x.get("truth") in ("true", "half") and x["hex"] not in keyed:
            w.append("true rumor %s points at unkeyed hex %s" % (x.get("roll"), x["hex"]))
    if rum and not ({"true", "false"} <= {x.get("truth") for x in rum}):
        w.append("rumor chart needs both true and false entries")
    for t, v in (sb.get("terrain") or {}).items():
        if not v.get("hazard") or not v.get("predator"):
            w.append("terrain %s has no hazard or no top predator" % t)
    if keys and not any(k.get("landmark") for k in keys):
        w.append("no landmark with a sight radius")
    return w


def bars(d):
    sb = P.load(d, "sandbox.json")
    hc = P.load(d, "hexcrawl.json")
    g = sb["overview"]["grid"]
    cols, rows = g["cols"], g["rows"]
    out = [("hexcrawl: sandbox kit lints clean", not sandbox_issues(sb), "; ".join(sandbox_issues(sb)[:3]) or "ok")]
    grid = {parse_hex(x["hex"]): x["terrain"] for x in hc["hexes"]}
    out.append(("hexcrawl: every hex has one terrain", len(grid) == cols * rows == len(hc["hexes"]),
                "%d of %d hexes" % (len(grid), cols * rows)))
    bad = 0
    for f in sb["geography"]:
        cells = {parse_hex(x) for x in f["hexes"]}
        start = next(iter(cells))
        seen, todo = {start}, [start]
        while todo:
            q = todo.pop()
            for nb in neighbours(q[0], q[1], cols, rows):
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    todo.append(nb)
        if seen != cells or any(grid[q] != f["terrain"] for q in cells) or len(cells) < 2:
            bad += 1
    out.append(("hexcrawl: each feature is one connected patch of one terrain", bad == 0,
                "%d features, %d broken" % (len(sb["geography"]), bad)))
    with open(os.path.join(d, "map.svg"), encoding="utf-8") as fh:
        svg = fh.read()
    seg = svg.split('<g class="features"', 1)[1].split("</g>", 1)[0]
    shown = [s.split(">", 1)[1].split("<", 1)[0] for s in seg.split("<text")[1:]]
    out.append(("hexcrawl: each feature lettered once on the map", sorted(shown) == sorted(f["letter"] for f in sb["geography"]),
                "%d letters drawn for %d features" % (len(shown), len(sb["geography"]))))
    rc = P.load(d, "recipe.json")
    want = rc["params"]["keyed"]
    share = sb["overview"]["keyed_share"]
    land = sb["overview"]["land_hexes"]
    out.append(("hexcrawl: keyed share within one hex of the target", abs(share - want) * land <= 1.0 + 1e-9,
                "%.3f keyed vs %.3f wanted" % (share, want)))
    return out
