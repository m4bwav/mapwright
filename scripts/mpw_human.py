"""mapwright human layer: settlements, roads and names on a generated mesh.

Works on the stored mesh dict (mesh.json values), so a check or a child map
can rebuild everything from files alone. Standard library only.
"""
import heapq
import math

import mpw_names

WORLD = 1000.0
ELEV_LAND = 3000.0
AREA_WORLD = 5000.0      # km2 of land per world settlement
SPACING_WORLD = 35.0     # km minimum between world settlements
RANGE_M = 1500.0         # a mountain range is land above this, connected
MIN_BODY = 6             # cells: smaller seas and landmasses get no name
MIN_RANGE = 8
TOL_PARENT = 1.0        # child keeps parent settlements and roads within 1 parent + 1 child spacing
REUSE = 0.35             # cost factor on cells that already carry a road

HAB = {"ice": 0.0, "tundra": 0.15, "boreal forest": 0.4, "temperate grassland": 1.0, "cold desert": 0.2,
       "temperate seasonal forest": 1.0, "temperate rainforest": 0.8, "subtropical desert": 0.15,
       "savanna": 0.8, "tropical seasonal forest": 0.8, "tropical rainforest": 0.55, "alpine": 0.05}
TERRAIN = {"temperate grassland": 1.0, "savanna": 1.0, "temperate seasonal forest": 1.3, "boreal forest": 1.4,
           "temperate rainforest": 1.6, "tropical seasonal forest": 1.4, "tropical rainforest": 1.8,
           "cold desert": 1.2, "subtropical desert": 1.3, "tundra": 1.3, "ice": 2.5, "alpine": 2.2}


def _bnames():
    import mpw_gen
    return [b[0] for b in mpw_gen.BIOMES]


def neighbours(m):
    import mpw_gen
    return [sorted(s) for s in mpw_gen._neighbours(m)]


def to_geo(x, y):
    return [round(x * 1000.0, 2), round((WORLD - y) * 1000.0, 2)]


def qkey(x, y):
    """World-keyed integer key (0.1 km) for names."""
    return (int(round(x * 10)), int(round(y * 10)))


# ------------------------------------------------------------------ components
def components(n, nb, member):
    """Connected components of cells where member[c]; returns (comp id per cell or -1, list of cell lists)."""
    cid = [-1] * n
    comps = []
    for s in range(n):
        if not member[s] or cid[s] != -1:
            continue
        k = len(comps)
        cid[s] = k
        comp = [s]
        i = 0
        while i < len(comp):
            c = comp[i]
            i += 1
            for q in nb[c]:
                if member[q] and cid[q] == -1:
                    cid[q] = k
                    comp.append(q)
        comps.append(comp)
    return cid, comps


def passable(m):
    return [(not m["ocean"][c]) and m["lake"][c] < 0 for c in range(len(m["x"]))]


def far_cell(comp, nb, inside):
    """Cell of comp farthest (in steps) from its edge; ties by id."""
    cs = set(comp)
    depth = {}
    frontier = [c for c in comp if any(q not in cs for q in nb[c])] or [comp[0]]
    for c in frontier:
        depth[c] = 0
    while frontier:
        nxt = []
        for c in frontier:
            for q in nb[c]:
                if q in cs and q not in depth:
                    depth[q] = depth[c] + 1
                    nxt.append(q)
        frontier = nxt
    return max(comp, key=lambda c: (depth.get(c, 0), -c))


# ------------------------------------------------------------------ settlements
def site_scores(m, nb, thr, ok):
    X, Y, h, acc, rcv, river, ocean, lake, biome = (m["x"], m["y"], m["h"], m["acc"], m["rcv"], m["river"],
                                                    m["ocean"], m["lake"], m["biome"])
    names = _bnames()
    n = len(X)
    up = [0] * n
    for c in range(n):
        r = rcv[c]
        if r >= 0 and river[c]:
            up[r] += 1
    sc = [None] * n
    for c in range(n):
        if not ok[c]:
            continue
        s = HAB.get(names[biome[c]], 0.5)
        if river[c]:
            s += 0.6 + 0.25 * math.log2(max(1.0, acc[c] / thr))
            if up[c] >= 2:
                s += 0.8                                    # confluence
            if rcv[c] >= 0 and ocean[rcv[c]]:
                s += 1.2                                    # river mouth
        coast = shore = False
        g = 0.0
        for q in nb[c]:
            if ocean[q]:
                coast = True
            elif lake[q] >= 0:
                shore = True
            d = math.hypot(X[q] - X[c], Y[q] - Y[c]) * 1000.0 or 1.0
            g = max(g, abs(max(0.0, h[q]) - max(0.0, h[c])) * ELEV_LAND / d)
        if coast:
            s += 0.6
        if shore:
            s += 0.5
        s -= min(2.0, 6.0 * g)                              # flat land
        s -= 0.3 * max(0.0, h[c]) * 3.0                     # high ground
        sc[c] = s
    return sc


def pick_sites(m, sc, spacing, count, taken=(), floor=0.2):
    """Greedy best-first with a minimum spacing; ties break by cell id."""
    X, Y = m["x"], m["y"]
    b = {}

    def free(x, y):
        gi, gj = int(x // spacing), int(y // spacing)
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                for (px, py) in b.get((gi + di, gj + dj), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < spacing * spacing:
                        return False
        return True

    def add(x, y):
        b.setdefault((int(x // spacing), int(y // spacing)), []).append((x, y))
    for x, y in taken:
        add(x, y)
    cand = sorted((c for c in range(len(X)) if sc[c] is not None and sc[c] >= floor), key=lambda c: (-sc[c], c))
    out = []
    for c in cand:
        if len(out) >= count:
            break
        if free(X[c], Y[c]):
            add(X[c], Y[c])
            out.append(c)
    return out


# ------------------------------------------------------------------ paths
class Router:
    def __init__(self, m, nb, thr):
        self.m, self.nb, self.thr = m, nb, thr
        self.ok = passable(m)
        names = _bnames()
        self.tf = [TERRAIN.get(names[b], 1.0) for b in m["biome"]]
        self.road = set()

    def step(self, a, b):
        m = self.m
        d = math.hypot(m["x"][b] - m["x"][a], m["y"][b] - m["y"][a])
        g = abs(max(0.0, m["h"][b]) - max(0.0, m["h"][a])) * ELEV_LAND / (d * 1000.0 or 1.0)
        cost = d * (1.0 + 60.0 * g * g) * self.tf[b]
        if m["river"][b] and not m["river"][a] and b not in self.road:
            cost += d * min(6.0, 1.0 + 0.2 * m["acc"][b] / self.thr)   # bridge
        if b in self.road:
            cost *= REUSE
        return cost

    def path(self, src, targets, allowed=None, goal_xy=None):
        """A* (goal_xy given) or Dijkstra to any cell in targets. Returns cell list or None."""
        m = self.m
        X, Y = m["x"], m["y"]
        if src in targets:
            return [src]
        gx, gy = goal_xy if goal_xy else (None, None)
        dist = {src: 0.0}
        prev = {}
        pq = [(0.0, 0.0, src)]
        while pq:
            f, gcost, c = heapq.heappop(pq)
            if gcost > dist.get(c, 1e300):
                continue
            if c in targets:
                out = [c]
                while c in prev:
                    c = prev[c]
                    out.append(c)
                return out[::-1]
            for q in self.nb[c]:
                if not self.ok[q] or (allowed is not None and not allowed(q)):
                    continue
                nd = gcost + self.step(c, q)
                if nd < dist.get(q, 1e300):
                    dist[q] = nd
                    prev[q] = c
                    hh = REUSE * math.hypot(X[q] - gx, Y[q] - gy) if goal_xy else 0.0
                    heapq.heappush(pq, (nd + hh, nd, q))
        return None


def rng_edges(pts):
    """Relative neighbourhood graph over points (contains the Euclidean MST, so connected)."""
    k = len(pts)
    d = [[math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]) for j in range(k)] for i in range(k)]
    out = []
    for i in range(k):
        for j in range(i + 1, k):
            dij = d[i][j]
            if not any(max(d[i][t], d[j][t]) < dij for t in range(k) if t != i and t != j):
                out.append((dij, i, j))
    out.sort()
    return out


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        p = self.p
        p.setdefault(a, a)
        while p[a] != a:
            p[a] = p[p[a]]
            a = p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def connect_all(router, sets, land, roads, kind="road"):
    """Join every landmass's settlements into one road component (cheapest link first)."""
    uf = UF()
    for r in roads:
        for a, b in zip(r["cells"], r["cells"][1:]):
            uf.union(a, b)
    by_land = {}
    for s in sets:
        uf.find(s["cell"])
        by_land.setdefault(land[s["cell"]], []).append(s)
    for lid in sorted(by_land):
        ss = by_land[lid]
        while True:
            roots = sorted({uf.find(s["cell"]) for s in ss})
            if len(roots) <= 1:
                break
            main = roots[0]
            netcells = {c for c in uf.p if uf.find(c) == main and land[c] == lid}
            other = next(s for s in ss if uf.find(s["cell"]) != main)
            p = router.path(other["cell"], netcells)
            if p is None:
                break
            roads.append(dict(cells=p, kind=kind, rank="minor", a=other["id"], b=None, link=True))
            router.road.update(p)
            for a, b in zip(p, p[1:]):
                uf.union(a, b)
    return roads


def rank_of(i, count):
    if i < max(1, int(math.ceil(0.1 * count))):
        return "city"
    if i < max(1, int(math.ceil(0.35 * count))):
        return "town"
    return "village"


# ------------------------------------------------------------------ world and child
def human_world(m, thr):
    n = len(m["x"])
    nb = neighbours(m)
    ok = passable(m)
    land, lands = components(n, nb, ok)
    big = [len(lands[land[c]]) >= 3 if land[c] >= 0 else False for c in range(n)]
    sc = site_scores(m, nb, thr, big)
    sp = m["sp"]
    land_km2 = sum(1 for c in range(n) if ok[c]) * sp * sp
    count = max(1, int(round(land_km2 / AREA_WORLD)))
    spacing = max(SPACING_WORLD, 3.0 * sp)
    cells = pick_sites(m, sc, spacing, count)
    sets = [dict(id=i, cell=c, rank=rank_of(i, len(cells)), score=round(sc[c], 3)) for i, c in enumerate(cells)]
    router = Router(m, nb, thr)
    roads = []
    by_land = {}
    for s in sets:
        by_land.setdefault(land[s["cell"]], []).append(s)
    for lid in sorted(by_land):
        ss = by_land[lid]
        pts = [(m["x"][s["cell"]], m["y"][s["cell"]]) for s in ss]
        edges = rng_edges(pts)
        big_first = sorted(edges, key=lambda e: (ss[e[1]]["rank"] == "village" or ss[e[2]]["rank"] == "village",
                                                 e[0], e[1], e[2]))
        for _, i, j in big_first:
            a, b = ss[i], ss[j]
            bc = b["cell"]
            p = router.path(a["cell"], {bc}, goal_xy=(m["x"][bc], m["y"][bc]))
            if p is None:
                continue
            major = a["rank"] != "village" and b["rank"] != "village"
            roads.append(dict(cells=p, kind="road", rank="major" if major else "minor", a=a["id"], b=b["id"]))
            router.road.update(p)
    connect_all(router, sets, land, roads)
    return dict(nb=nb, land=land, lands=lands, sets=sets, roads=roads)


def _snap(m, ok, grid, x, y, reach, taken=()):
    """Nearest passable child cell within reach km (a child lake can swallow a parent shore)."""
    k = 24
    while True:
        hits = grid.near(x, y, k, rmax=int(reach / grid.s) + 2)
        for d2, c in hits:
            if d2 > reach * reach:
                return None
            if ok[c] and c not in taken:
                return c
        if len(hits) < k:
            return None
        k *= 4


def human_child(m, thr, parent, window):
    """parent: dict(mesh, features, sp). Keeps parent settlements and roads, adds villages and tracks."""
    import mpw_gen
    n = len(m["x"])
    X, Y = m["x"], m["y"]
    nb = neighbours(m)
    ok = passable(m)
    land, lands = components(n, nb, ok)
    sp, psp = m["sp"], parent["sp"]
    x0, y0, x1, y1 = window
    grid = mpw_gen.Grid(X, Y, sp)
    pm = parent["mesh"]
    PX, PY = pm["x"], pm["y"]
    reach = TOL_PARENT * psp + sp
    inside = lambda x, y: x0 <= x <= x1 and y0 <= y <= y1   # noqa: E731
    sets = []
    pmap = {}
    for f in parent["features"]:
        pr = f["properties"]
        if pr.get("kind") != "settlement":
            continue
        pc = pr["cell"]
        if not inside(PX[pc], PY[pc]):
            continue
        c = _snap(m, ok, grid, PX[pc], PY[pc], reach, {s["cell"] for s in sets})
        if c is None:
            continue
        s = dict(id=len(sets), cell=c, rank=pr["rank"], score=pr.get("score", 0), parent_id=pr["id"],
                 name=pr.get("name"))
        sets.append(s)
        pmap[pr["id"]] = s
    router = Router(m, nb, thr)
    roads = []
    for f in parent["features"]:
        pr = f["properties"]
        if pr.get("kind") not in ("road", "track"):
            continue
        runs, cur = [], []
        for pc in pr["cells"]:
            if inside(PX[pc], PY[pc]):
                cur.append(pc)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        for run in runs:
            if len(run) < 2:
                continue
            cells = []
            for pc in run:
                c = _snap(m, ok, grid, PX[pc], PY[pc], reach)
                if c is not None and (not cells or cells[-1] != c):
                    cells.append(c)
            # corridor: within one parent spacing of the parent polyline near this vertex pair
            pieces = []
            path = cells[:1]
            for ca, cb in zip(cells, cells[1:]):
                def corr(q, ca=ca, cb=cb):
                    return min(mpw_gen._dseg(X[q], Y[q], X[ca], Y[ca], X[cb], Y[cb]), 1e9) <= psp
                p = None
                if land[ca] == land[cb]:
                    p = router.path(ca, {cb}, allowed=corr, goal_xy=(X[cb], Y[cb]))
                    if p is None:
                        p = router.path(ca, {cb}, goal_xy=(X[cb], Y[cb]))
                if p is None:          # the child split the land here (new lake or inlet): start a new piece
                    pieces.append(path)
                    path = [cb]
                    continue
                path += p[1:]
            pieces.append(path)
            for path in pieces:
                if len(path) >= 2:
                    roads.append(dict(cells=path, kind=pr["kind"], rank=pr["rank"], a=None, b=None,
                                      parent_id=pr["id"]))
                    router.road.update(path)
    connect_all(router, sets, land, roads)
    # new villages and tracks
    big = [len(lands[land[c]]) >= 3 if land[c] >= 0 else False for c in range(n)]
    sc = site_scores(m, nb, thr, big)
    land_km2 = sum(1 for c in range(n) if ok[c]) * sp * sp
    count = max(0, int(round(land_km2 / (AREA_WORLD * sp / psp))))
    spacing = max(3.0 * sp, SPACING_WORLD * sp / psp)
    taken = [(X[s["cell"]], Y[s["cell"]]) for s in sets]
    for c in pick_sites(m, sc, spacing, count, taken):
        sets.append(dict(id=len(sets), cell=c, rank="village", score=round(sc[c], 3)))
    net = {}
    for r in roads:
        for c in r["cells"]:
            net.setdefault(land[c], set()).add(c)
    for s in sets:
        if "parent_id" in s:
            net.setdefault(land[s["cell"]], set()).add(s["cell"])
    for s in sets:
        if "parent_id" in s:
            continue
        lid = land[s["cell"]]
        tg = net.setdefault(lid, set())
        if tg:
            p = router.path(s["cell"], tg)
            if p is not None and len(p) >= 2:
                roads.append(dict(cells=p, kind="track", rank="track", a=s["id"], b=None))
                router.road.update(p)
                tg.update(p)
        tg.add(s["cell"])
    connect_all(router, sets, land, roads, kind="track")
    return dict(nb=nb, land=land, lands=lands, sets=sets, roads=roads)


# ------------------------------------------------------------------ names
def river_stems(m, nb):
    """Main stem per river cell: upstream follows the biggest tributary. Returns stem id per cell, mouths."""
    n = len(m["x"])
    river, rcv, acc, ocean, lake = m["river"], m["rcv"], m["acc"], m["ocean"], m["lake"]
    ups = [[] for _ in range(n)]
    for c in range(n):
        if river[c] and lake[c] < 0 and rcv[c] >= 0:
            ups[rcv[c]].append(c)
    stem = [-1] * n
    mouths = [c for c in range(n) if river[c] and lake[c] < 0 and not ocean[c]
              and (rcv[c] < 0 or not river[rcv[c]] or ocean[rcv[c]] or lake[rcv[c]] >= 0)]
    heads = [(c, None) for c in mouths]
    k = 0
    while heads:
        nxt = []
        for c, _ in heads:
            sid = k
            k += 1
            cur = c
            while True:
                stem[cur] = sid
                up = sorted((q for q in ups[cur] if stem[q] == -1), key=lambda q: (-acc[q], q))
                if not up:
                    break
                for q in up[1:]:
                    nxt.append((q, sid))
                cur = up[0]
        heads = nxt
    return stem, mouths


def name_features(m, hum, lang, parent=None):
    """Names for settlements, rivers, lakes, seas, ranges and landmasses.

    Returns (feature list of label points, names list, river stem names per cell stem id, lake names).
    """
    import mpw_gen
    X, Y = m["x"], m["y"]
    n = len(X)
    nb = hum["nb"]
    used = [e["name"] for e in parent["names"]] if parent else []
    namer = mpw_names.Namer(lang, used)
    entries = []
    pgrid = None
    if parent:
        pm = parent["mesh"]
        pgrid = mpw_gen.Grid(pm["x"], pm["y"], parent["sp"])
        pnb = neighbours(pm)
        pnames = {}
        for e in parent["names"]:
            pnames[(e["kind"], e["id"])] = e
        pref = parent_layers(pm, pnb, parent["features"])

    def nearest_parent(c):
        return pgrid.near(X[c], Y[c], 1)[0][1]

    def inherit(kind_set, cells, layer):
        """Majority parent component id among cells (needs at least half matched)."""
        votes = {}
        for c in cells:
            v = pref[layer][nearest_parent(c)]
            if v >= 0:
                votes[v] = votes.get(v, 0) + 1
        if not votes:
            return None
        best = min(votes, key=lambda v: (-votes[v], v))
        if votes[best] * 2 < len(cells):
            return None
        for kd in kind_set:
            e = pnames.get((kd, best))
            if e:
                return e
        return None
    claimed = set()

    def assign(kind_set, kind, fid, cells, anchor, layer):
        e = inherit(kind_set, cells, layer) if parent else None
        if e and (e["kind"], e["id"]) not in claimed:
            claimed.add((e["kind"], e["id"]))
            nm, kd, pid = e["name"], e["kind"], e["id"]
        else:
            nm, kd, pid = namer.name(kind, qkey(X[anchor], Y[anchor])), kind, None
        ent = dict(kind=kd, id=fid, name=nm)
        if pid is not None:
            ent["parent_id"] = pid
        entries.append(ent)
        return ent
    feats = []
    # settlements (inherited ones keep the parent name)
    for s in hum["sets"]:
        if s.get("name"):
            namer.used.add(s["name"].lower())
            nm = s["name"]
        else:
            nm = namer.name("settlement", qkey(X[s["cell"]], Y[s["cell"]]))
        s["name"] = nm
        ent = dict(kind="settlement", id=s["id"], name=nm)
        if "parent_id" in s:
            ent["parent_id"] = s["parent_id"]
        entries.append(ent)
    # seas and oceans
    sea, seas = components(n, nb, m["ocean"])
    order = sorted(range(len(seas)), key=lambda k: (-len(seas[k]), seas[k][0]))
    for k in order:
        comp = seas[k]
        if len(comp) < MIN_BODY:
            continue
        kind = "ocean" if len(comp) >= 0.2 * n else "sea"
        a = far_cell(comp, nb, None)
        ent = assign(("ocean", "sea"), kind, k, comp, a, "sea")
        feats.append(_label(ent, a, X, Y, len(comp)))
    # landmasses
    land, lands = hum["land"], hum["lands"]
    for k in sorted(range(len(lands)), key=lambda k: (-len(lands[k]), lands[k][0])):
        comp = lands[k]
        if len(comp) < MIN_BODY:
            continue
        a = far_cell(comp, nb, None)
        ent = assign(("land",), "land", k, comp, a, "land")
        feats.append(_label(ent, a, X, Y, len(comp)))
    # mountain ranges
    rid, ranges = range_components(m, nb)
    for k in sorted(range(len(ranges)), key=lambda k: (-len(ranges[k]), ranges[k][0])):
        comp = ranges[k]
        a = max(comp, key=lambda c: (m["h"][c], -c))
        ent = assign(("range",), "range", k, comp, a, "range")
        feats.append(_label(ent, a, X, Y, len(comp)))
    # lakes
    lake_names = {}
    nl = (max(m["lake"]) + 1) if m["lake"] else 0
    lcells = [[] for _ in range(nl)]
    for c in range(n):
        if m["lake"][c] >= 0:
            lcells[m["lake"][c]].append(c)
    for lid in range(nl):
        if lcells[lid]:
            lake_names[lid] = assign(("lake",), "lake", lid, lcells[lid], lcells[lid][0], "lake")["name"]
    # rivers: one name per main stem
    stem, mouths = river_stems(m, nb)
    scells = {}
    for c in range(n):
        if stem[c] >= 0:
            scells.setdefault(stem[c], []).append(c)
    stem_names = {}
    for sid in sorted(scells, key=lambda s: (-len(scells[s]), s)):
        cells = scells[sid]
        mouth = max(cells, key=lambda c: (m["acc"][c], -c))
        stem_names[sid] = assign(("river",), "river", sid, cells, mouth, "river")["name"]
    entries.sort(key=lambda e: (e["kind"], e["id"]))
    return feats, entries, stem, stem_names, lake_names


def range_components(m, nb):
    n = len(m["x"])
    hi = [(not m["ocean"][i]) and m["lake"][i] < 0 and m["h"][i] * ELEV_LAND >= RANGE_M for i in range(n)]
    rid, comps = components(n, nb, hi)
    keep = [c for c in comps if len(c) >= MIN_RANGE]
    rid = [-1] * n
    for k, comp in enumerate(keep):
        for c in comp:
            rid[c] = k
    return rid, keep


def parent_layers(pm, pnb, pfeats):
    """Per parent cell: sea, land, range, lake and river stem ids, rebuilt the way the parent named them."""
    n = len(pm["x"])
    sea, _ = components(n, pnb, pm["ocean"])
    land, _ = components(n, pnb, passable(pm))
    rid, _ = range_components(pm, pnb)
    stem, _ = river_stems(pm, pnb)
    return dict(sea=sea, land=land, range=rid, lake=list(pm["lake"]), river=stem)


def _label(ent, c, X, Y, size):
    return {"type": "Feature", "properties": {"kind": ent["kind"], "id": ent["id"], "name": ent["name"],
                                              "cells": size, "anchor": c},
            "geometry": {"type": "Point", "coordinates": to_geo(X[c], Y[c])}}


def features(m, hum, stem, stem_names):
    """GeoJSON features for settlements and roads."""
    X, Y = m["x"], m["y"]
    out = []
    for s in hum["sets"]:
        pr = {"kind": "settlement", "id": s["id"], "rank": s["rank"], "name": s["name"], "cell": s["cell"],
              "score": s["score"]}
        if "parent_id" in s:
            pr["parent_id"] = s["parent_id"]
        out.append({"type": "Feature", "properties": pr,
                    "geometry": {"type": "Point", "coordinates": to_geo(X[s["cell"]], Y[s["cell"]])}})
    for i, r in enumerate(hum["roads"]):
        pr = {"kind": r["kind"], "id": i, "rank": r["rank"], "cells": r["cells"]}
        if r.get("a") is not None:
            pr["from"] = r["a"]
        if r.get("b") is not None:
            pr["to"] = r["b"]
        if "parent_id" in r:
            pr["parent_id"] = r["parent_id"]
        out.append({"type": "Feature", "properties": pr,
                    "geometry": {"type": "LineString", "coordinates": [to_geo(X[c], Y[c]) for c in r["cells"]]}})
    return out
