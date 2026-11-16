"""mapwright world generator: `gen world`, `gen region` / `zoom`, and `check`.

Standard library only. Pipeline (design.md section 4, realistic-land.md):
world-keyed jittered grid -> Delaunay as its dual -> domain-warped Voronoi plates
with distance-to-boundary convergent / divergent / transform uplift -> fBm with
domain warp -> implicit stream-power erosion (Braun-Willett, n = 1) ->
Priority-Flood with epsilon -> single steepest receiver -> accumulation ->
rivers, lakes with one outlet -> latitude + wind + rain-shadow climate ->
Whittaker-style biomes -> recipe folder + map.svg.

Map units: the world is a WORLD x WORLD km square, x east, y south (SVG order).
GeoJSON and the world file use a local metre CRS with y north (see recipe.json).
"""
import base64
import hashlib
import heapq
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import time
import zlib

GEN_VERSION = "gen-1"
WORLD = 1000.0          # km
ELEV_LAND = 3000.0      # metres per height unit above sea level
ELEV_SEA = 4000.0       # metres per height unit below sea level
PNG_OFFSET = 10000      # heights.png value = metres + PNG_OFFSET
EPS_FLOOD = 1e-5
LAKE_MIN = 2e-3         # height units (6 m): shallower raised flats are not lakes
LAPSE = 6.5             # deg C per km

M64 = (1 << 64) - 1


# ------------------------------------------------------------------ hashing / noise
def h64(*k):
    x = 0x9E3779B97F4A7C15
    for v in k:
        x = (x ^ (v & M64)) * 0xBF58476D1CE4E5B9 & M64
        x ^= x >> 31
        x = x * 0x94D049BB133111EB & M64
        x ^= x >> 29
    return x


def u01(*k):
    return (h64(*k) >> 11) / 9007199254740992.0


_LAT = {}


def _lat(seed, ix, iy):
    k = (seed, ix, iy)
    v = _LAT.get(k)
    if v is None:
        v = _LAT[k] = u01(seed, ix, iy)
    return v


def vnoise(seed, x, y):
    ix = math.floor(x)
    iy = math.floor(y)
    fx = x - ix
    fy = y - iy
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = _lat(seed, ix, iy)
    b = _lat(seed, ix + 1, iy)
    c = _lat(seed, ix, iy + 1)
    d = _lat(seed, ix + 1, iy + 1)
    top = a + (b - a) * fx
    return top + (c + (d - c) * fx - top) * fy


def fbm(seed, x, y, f, octaves=4):
    s = 0.0
    a = 1.0
    t = 0.0
    for o in range(octaves):
        s += a * vnoise(seed + o * 7919, x * f, y * f)
        t += a
        a *= 0.5
        f *= 2.0
    return s / t - 0.5


# ------------------------------------------------------------------ mesh
def build_mesh(seed, x0, y0, x1, y1, sp, jit=0.4):
    """World-keyed jittered grid; same world point + spacing -> same mesh point."""
    gx0 = math.ceil(x0 / sp)
    gy0 = math.ceil(y0 / sp)
    nx = max(2, int(math.floor(x1 / sp)) - gx0 + 1)
    ny = max(2, int(math.floor(y1 / sp)) - gy0 + 1)
    lvl = int(round(math.log2(WORLD / sp) * 64))
    X = []
    Y = []
    for j in range(ny):
        for i in range(nx):
            gi = gx0 + i
            gj = gy0 + j
            X.append((gi + (u01(seed, 1, lvl, gi, gj) - 0.5) * 2 * jit) * sp)
            Y.append((gj + (u01(seed, 2, lvl, gi, gj) - 0.5) * 2 * jit) * sp)
    nb = [[] for _ in range(nx * ny)]
    tris = []

    def incircle(a, b, c, d):
        ax, ay = X[a] - X[d], Y[a] - Y[d]
        bx, by = X[b] - X[d], Y[b] - Y[d]
        cx, cy = X[c] - X[d], Y[c] - Y[d]
        return (ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay) \
            + (cx * cx + cy * cy) * (ax * by - bx * ay) > 0
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            b = a + 1
            c = a + nx + 1
            d = a + nx
            if incircle(a, b, c, d):
                tris += [(a, b, d), (b, c, d)]
                diag = (b, d)
            else:
                tris += [(a, b, c), (a, c, d)]
                diag = (a, c)
            for p, q in ((a, b), (a, d), diag):
                nb[p].append(q)
                nb[q].append(p)
    for j in range(ny - 1):
        a = j * nx + nx - 1
        nb[a].append(a + nx)
        nb[a + nx].append(a)
    for i in range(nx - 1):
        a = (ny - 1) * nx + i
        nb[a].append(a + 1)
        nb[a + 1].append(a)
    border = [j == 0 or i == 0 or j == ny - 1 or i == nx - 1 for j in range(ny) for i in range(nx)]
    return dict(X=X, Y=Y, nx=nx, ny=ny, nb=nb, tris=tris, sp=sp, border=border, gx0=gx0, gy0=gy0)


# ------------------------------------------------------------------ land
def plate_uplift(seed, X, Y, nplates):
    """Distance-to-boundary tectonics on domain-warped Voronoi plates.

    Returns base height and uplift rate per cell. Rules (realistic-land.md s.2):
    convergent continent-continent: broad high belt; ocean-continent: trench on the
    ocean side, arc range inland on the continent; ocean-ocean: island arc;
    divergent: rift valley on continents, mid-ocean ridge at sea; transform: low ridge.
    """
    P = [(u01(seed, 10, k) * WORLD, u01(seed, 11, k) * WORLD) for k in range(nplates)]
    cont = [u01(seed, 12, k) < 0.45 for k in range(nplates)]
    cont[int(u01(seed, 15) * nplates)] = True     # at least one continent
    vel = []
    for k in range(nplates):
        ang = u01(seed, 13, k) * 2 * math.pi
        vel.append((math.cos(ang), math.sin(ang)))
    n = len(X)
    base = [0.0] * n
    upl = [0.0] * n
    plate = [0] * n
    kind = [0] * n   # 0 interior, 1 convergent, 2 divergent, 3 transform (nearest boundary)
    for c in range(n):
        x = X[c] + 90 * fbm(seed + 50, X[c], Y[c], 0.003, 3)
        y = Y[c] + 90 * fbm(seed + 60, X[c], Y[c], 0.003, 3)
        b1 = b2 = 1e30
        k1 = k2 = 0
        for k in range(nplates):
            px, py = P[k]
            dd = (x - px) ** 2 + (y - py) ** 2
            if dd < b1:
                b2, k2 = b1, k1
                b1, k1 = dd, k
            elif dd < b2:
                b2, k2 = dd, k
        plate[c] = k1
        nx_, ny_ = P[k2][0] - P[k1][0], P[k2][1] - P[k1][1]
        L = math.hypot(nx_, ny_) or 1.0
        nx_ /= L
        ny_ /= L
        d = (b2 - b1) / (2 * L)                     # distance to the bisector (km)
        rvx = vel[k1][0] - vel[k2][0]
        rvy = vel[k1][1] - vel[k2][1]
        conv = rvx * nx_ + rvy * ny_                # > 0: plates approach
        shear = abs(rvx * ny_ - rvy * nx_)
        c1, c2 = cont[k1], cont[k2]
        # continental margins are blended across the boundary over ~80 km
        mine = 0.14 if c1 else -0.45
        other = 0.14 if c2 else -0.45
        w = 0.5 + 0.5 * min(1.0, d / 80.0)
        base[c] = mine * w + other * (1 - w)

        def g(dist, width):
            return math.exp(-(dist / width) ** 2)
        u = 0.0
        if conv > 0.25:
            kind[c] = 1
            if c1 and c2:
                u = 0.9 * conv * g(d, 70.0)
            elif c1 and not c2:
                u = 0.85 * conv * g(d - 45.0, 35.0)
            elif c2 and not c1:
                u = -0.35 * conv * g(d, 18.0)
            else:
                u = (0.55 * conv * g(d - 25.0, 18.0)) if k1 < k2 else -0.2 * conv * g(d, 15.0)
        elif conv < -0.25:
            kind[c] = 2
            u = (-0.25 * -conv * g(d, 22.0)) if c1 else (0.22 * -conv * g(d, 35.0))
        else:
            kind[c] = 3
            u = 0.12 * shear * g(d, 12.0)
        upl[c] = u
    return base, upl, plate, kind, dict(points=P, continental=cont, velocity=vel)


def land_heights(seed, M, nplates):
    X, Y = M["X"], M["Y"]
    base, upl, plate, kind, pinfo = plate_uplift(seed, X, Y, nplates)
    n = len(X)
    H = [0.0] * n
    for c in range(n):
        x, y = X[c], Y[c]
        qx = fbm(seed + 70, x, y, 0.004, 3)
        qy = fbm(seed + 80, x, y, 0.004, 3)
        detail = fbm(seed + 90, x + 120 * qx, y + 120 * qy, 0.005, 5)
        e = min(x, y, WORLD - x, WORLD - y) / WORLD + 0.25 * fbm(seed + 95, x, y, 0.004, 3)
        fall = min(1.0, max(0.0, (e - 0.03) / 0.12))
        h = base[c] + upl[c] * (1.0 + 2.5 * detail) + 0.75 * detail
        H[c] = h * fall - (1 - fall) * 0.6
        if M["border"][c]:
            H[c] = min(H[c], -0.2)
    return H, upl, plate, kind, pinfo


def priority_flood(H, nb, ocean, eps=EPS_FLOOD, outlets=()):
    """Barnes et al. Priority-Flood with epsilon; returns filled F and push parents.

    outlets: land cells on a window edge that drain out of the map (seeded like sea)."""
    n = len(H)
    F = H[:]
    closed = [False] * n
    parent = [-1] * n
    pq = []
    for c in sorted(outlets):
        closed[c] = True
        heapq.heappush(pq, (F[c], c))
    for c in range(n):
        if ocean[c]:
            closed[c] = True
            for q in nb[c]:
                if not ocean[q]:
                    heapq.heappush(pq, (F[c], c))
                    break
    while pq:
        h, c = heapq.heappop(pq)
        for q in nb[c]:
            if not closed[q]:
                closed[q] = True
                parent[q] = c
                if F[q] <= h + eps:
                    F[q] = h + eps
                heapq.heappush(pq, (F[q], q))
    return F, parent


def receivers(F, nb, ocean, outlets=()):
    n = len(F)
    rcv = [-1] * n
    for c in range(n):
        if ocean[c] or c in outlets:
            continue
        best = F[c]
        b = -1
        for q in nb[c]:
            if F[q] < best:
                best = F[q]
                b = q
        rcv[c] = b
    return rcv


def accumulate(F, rcv, weight=None):
    n = len(F)
    acc = [1.0] * n if weight is None else weight[:]
    order = sorted(range(n), key=F.__getitem__, reverse=True)
    for c in order:
        r = rcv[c]
        if r >= 0:
            acc[r] += acc[c]
    return acc, order


def erode(H, upl, M, steps, kdt=0.0045, udt=0.004):
    """Implicit stream-power erosion (Braun & Willett 2013), n = 1, m = 0.5.

    Each step: route on the Priority-Flood-filled surface, accumulate, then update
    heights from the outlet upstream: h = (h + dt(U + F h_r)) / (1 + dt F), with
    F = K sqrt(A) / (distance / spacing). Pits (receiver higher) only uplift.
    """
    X, Y, nb, sp = M["X"], M["Y"], M["nb"], M["sp"]
    n = len(H)
    H = H[:]
    U = [max(0.0, u) * udt for u in upl]
    for _ in range(steps):
        ocean = [h < 0 for h in H]
        F, _p = priority_flood(H, nb, ocean)
        rcv = receivers(F, nb, ocean)
        acc, order = accumulate(F, rcv)
        for c in reversed(order):           # ascending filled height: outlet first
            r = rcv[c]
            if r < 0:
                continue
            if H[r] < H[c]:
                d = math.hypot(X[c] - X[r], Y[c] - Y[r]) / sp
                f = kdt * math.sqrt(acc[c]) / d
                H[c] = (H[c] + U[c] + f * H[r]) / (1 + f)
            else:
                H[c] += U[c]
    return H


def hydrology(H, nb, thr, inflow=None, outlets=()):
    """Final water routing: filled heights, receivers, accumulation, lakes, rivers.

    outlets: window-edge cells that drain out of the map; used only when the map
    holds no sea, so water has somewhere to go (L-009)."""
    n = len(H)
    ocean = [h < 0 for h in H]
    outlets = set(outlets) if not any(ocean) else set()
    F, parent = priority_flood(H, nb, ocean, outlets=outlets)
    raised = [(not ocean[c]) and F[c] > H[c] + 1e-12 for c in range(n)]
    rcv = receivers(F, nb, ocean, outlets)
    for c in range(n):
        if raised[c]:
            rcv[c] = parent[c]   # inside a filled flat, follow the flood tree to the spill
    # lakes: connected raised components deeper than LAKE_MIN somewhere
    lake = [-1] * n
    lakes = []
    for s in range(n):
        if not raised[s] or lake[s] != -1:
            continue
        comp = [s]
        lake[s] = -2
        i = 0
        while i < len(comp):
            c = comp[i]
            i += 1
            for q in nb[c]:
                if raised[q] and lake[q] == -1:
                    lake[q] = -2
                    comp.append(q)
        if max(F[c] - H[c] for c in comp) >= LAKE_MIN:
            lid = len(lakes)
            for c in comp:
                lake[c] = lid
            lakes.append(sorted(comp))
        else:
            for c in comp:
                lake[c] = -3
    for c in range(n):
        if lake[c] < 0:
            lake[c] = -1
    # one outlet per lake: re-tree any lake entered from more than one spill
    fixed = 0
    for lid, comp in enumerate(lakes):
        outs = [c for c in comp if lake[rcv[c]] != lid]
        if len(outs) > 1:
            fixed += 1
            o = min(outs, key=lambda c: (F[rcv[c]], c))
            seen = {o}
            frontier = [o]
            depth = {o: 0}
            while frontier:
                nxt = []
                for c in frontier:
                    for q in nb[c]:
                        if lake[q] == lid and q not in seen:
                            seen.add(q)
                            rcv[q] = c
                            depth[q] = depth[c] + 1
                            nxt.append(q)
                frontier = nxt
    # lift: walk the receiver tree up from the sea so every step is strictly downhill
    # by at least 1e-7 (survives the 9-decimal rounding in mesh.json)
    up = [[] for _ in range(n)]
    for c in range(n):
        if rcv[c] >= 0:
            up[rcv[c]].append(c)
    stack = [c for c in range(n) if ocean[c] or c in outlets]
    while stack:
        c = stack.pop()
        for q in up[c]:
            if F[q] < F[c] + 1e-7:
                F[q] = F[c] + 1e-7
            stack.append(q)
    acc, _ = accumulate(F, rcv, inflow)
    river = [(not ocean[c]) and acc[c] >= thr for c in range(n)]
    return dict(ocean=ocean, F=F, rcv=rcv, acc=acc, lake=lake, lakes=lakes, river=river, lakes_retreed=fixed,
                outlets=sorted(outlets))


# ------------------------------------------------------------------ climate
BIOMES = [  # name, fill colour
    ("ocean", "#9cc3dc"), ("lake", "#7fb2d6"), ("ice", "#f4f6f8"), ("tundra", "#c9c7a7"),
    ("boreal forest", "#5f7f5a"), ("temperate grassland", "#c8c58a"), ("cold desert", "#d8cfae"),
    ("temperate seasonal forest", "#7fa26a"), ("temperate rainforest", "#4f8a63"),
    ("subtropical desert", "#e6d29a"), ("savanna", "#cfc077"), ("tropical seasonal forest", "#8fae5a"),
    ("tropical rainforest", "#3f7f4a"), ("alpine", "#b9b2a6"),
]
BIOME_ID = {b[0]: i for i, b in enumerate(BIOMES)}


def whittaker(t, p):
    """Whittaker-style lookup: mean annual temperature (C), precipitation (cm/yr)."""
    if t < -10:
        return "ice"
    if t < -3:
        return "tundra"
    if t < 5:
        return "boreal forest" if p >= 40 else "tundra"
    if t < 18:
        if p < 25:
            return "cold desert"
        if p < 60:
            return "temperate grassland"
        if p < 200:
            return "temperate seasonal forest"
        return "temperate rainforest"
    if p < 35:
        return "subtropical desert"
    if p < 110:
        return "savanna"
    if p < 250:
        return "tropical seasonal forest"
    return "tropical rainforest"


def lat_of(y, lat_top, lat_bottom):
    return lat_top + (lat_bottom - lat_top) * y / WORLD


def wind_dir(lat):
    """Prevailing surface wind as +1 (blowing east) or -1 (blowing west)."""
    a = abs(lat)
    return 1 if 30 <= a < 60 else -1


def lat_wetness(lat):
    """Zonal precipitation factor: wet ITCZ, dry subtropics, wet mid-latitudes, dry poles."""
    a = abs(lat)
    return 0.35 + 1.0 * math.exp(-(a / 12.0) ** 2) + 0.55 * math.exp(-((a - 52) / 12.0) ** 2) \
        - 0.25 * math.exp(-((a - 27) / 7.0) ** 2) - 0.2 * max(0.0, (a - 70) / 20.0)


def sea_level_temp(lat):
    return 29.0 - 0.52 * abs(lat)


def climate(seed, M, H, hyd, lat_top, lat_bottom):
    X, Y, nx, ny = M["X"], M["Y"], M["nx"], M["ny"]
    n = len(X)
    temp = [0.0] * n
    prec = [0.0] * n
    for j in range(ny):
        row = [j * nx + i for i in range(nx)]
        lat = lat_of(sum(Y[c] for c in row) / nx, lat_top, lat_bottom)
        wd = wind_dir(lat)
        if wd < 0:
            row.reverse()
        moist = 1.0
        prev_h = 0.0
        for c in row:
            h = max(0.0, H[c])
            if hyd["ocean"][c] or hyd["lake"][c] >= 0:
                moist = min(1.0, moist + 0.25)
                prev_h = 0.0
                prec[c] = 0.0
                continue
            oro = max(0.0, h - prev_h) * 10.0
            rain = moist * (0.035 + oro)
            rain = min(rain, moist)
            moist = max(0.0, moist - rain) + 0.004   # a little recycled moisture
            prev_h = h
            prec[c] = rain
    for c in range(n):
        lat = lat_of(Y[c], lat_top, lat_bottom)
        elev_km = max(0.0, H[c]) * ELEV_LAND / 1000.0
        temp[c] = sea_level_temp(lat) - LAPSE * elev_km + 3.0 * fbm(seed + 300, X[c], Y[c], 0.01, 2)
        prec[c] = 3200.0 * prec[c] * lat_wetness(lat) + 25.0 * lat_wetness(lat)   # cm / yr
    biome = [0] * n
    for c in range(n):
        if hyd["ocean"][c]:
            biome[c] = BIOME_ID["ocean"]
        elif hyd["lake"][c] >= 0:
            biome[c] = BIOME_ID["lake"]
        elif H[c] * ELEV_LAND > 2600 and temp[c] < 2:
            biome[c] = BIOME_ID["alpine"]
        else:
            biome[c] = BIOME_ID[whittaker(temp[c], prec[c])]
    return temp, prec, biome


# ------------------------------------------------------------------ geometry
def coast_lines(X, Y, H, tris, level=0.0):
    """Marching triangles on H = level, chained into polylines by shared edges."""
    seg = {}
    for t in tris:
        es = []
        for p, q in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (H[p] < level) != (H[q] < level):
                es.append((p, q) if p < q else (q, p))
        if len(es) == 2:
            a, b = es
            seg.setdefault(a, []).append(b)
            seg.setdefault(b, []).append(a)

    def pt(e):
        p, q = e
        s = (H[p] - level) / (H[p] - H[q])
        return (X[p] + (X[q] - X[p]) * s, Y[p] + (Y[q] - Y[p]) * s)
    used = set()
    lines = []
    starts = sorted(seg, key=lambda e: (len(seg[e]) != 1, e))
    for s in starts:
        for nxt in seg[s]:
            key = (s, nxt) if s < nxt else (nxt, s)
            if key in used:
                continue
            line = [s]
            prev, cur = s, nxt
            used.add(key)
            while True:
                line.append(cur)
                cand = [e for e in seg[cur] if ((cur, e) if cur < e else (e, cur)) not in used]
                if not cand:
                    break
                e = cand[0]
                used.add((cur, e) if cur < e else (e, cur))
                prev, cur = cur, e
            lines.append([pt(e) for e in line])
    return lines


def river_lines(X, Y, hyd, min_len=2):
    """River polylines from sources down to the sea, a lake, or a confluence."""
    river, rcv, lake, ocean, acc = hyd["river"], hyd["rcv"], hyd["lake"], hyd["ocean"], hyd["acc"]
    n = len(X)
    has_up = [False] * n
    for c in range(n):
        if river[c] and rcv[c] >= 0 and lake[c] < 0:
            has_up[rcv[c]] = True
    done = [False] * n
    lines = []
    srcs = sorted((c for c in range(n) if river[c] and lake[c] < 0 and not has_up[c]),
                  key=lambda c: (-acc[c], c))
    # longest first: walk every source, stop at a cell already drawn
    for s in srcs:
        cur = s
        pts = [cur]
        while True:
            done[cur] = True
            r = rcv[cur]
            if r < 0:
                break
            pts.append(r)
            if ocean[r] or lake[r] >= 0 or done[r]:
                break
            cur = r
        if len(pts) >= min_len:
            lines.append(dict(cells=pts, acc=acc[pts[-2]]))
    # cells on lake outflows that start at the lake outlet
    for c in range(n):
        if river[c] and not done[c] and lake[c] < 0:
            cur = c
            pts = [cur]
            while True:
                done[cur] = True
                r = rcv[cur]
                if r < 0:
                    break
                pts.append(r)
                if ocean[r] or lake[r] >= 0 or done[r]:
                    break
                cur = r
            lines.append(dict(cells=pts, acc=acc[pts[-2]] if len(pts) > 1 else acc[c]))
    return lines


def lake_rings(X, Y, tris, lake, lid_count):
    """Outline of each lake from the triangles whose three corners are in the lake."""
    edges = [dict() for _ in range(lid_count)]
    for t in tris:
        lid = lake[t[0]]
        if lid < 0 or lake[t[1]] != lid or lake[t[2]] != lid:
            continue
        for p, q in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (p, q) if p < q else (q, p)
            edges[lid][k] = edges[lid].get(k, 0) + 1
    rings = []
    for lid in range(lid_count):
        adj = {}
        for (p, q), k in sorted(edges[lid].items()):
            if k == 1:
                adj.setdefault(p, []).append(q)
                adj.setdefault(q, []).append(p)
        used = set()
        rs = []
        for s in sorted(adj):
            for nxt in adj[s]:
                key = (s, nxt) if s < nxt else (nxt, s)
                if key in used:
                    continue
                used.add(key)
                ring = [s]
                cur = nxt
                while cur != s:
                    ring.append(cur)
                    cand = [e for e in adj[cur] if ((cur, e) if cur < e else (e, cur)) not in used]
                    if not cand:
                        break
                    e = cand[0]
                    used.add((cur, e) if cur < e else (e, cur))
                    cur = e
                if len(ring) >= 3:
                    rs.append([(X[c], Y[c]) for c in ring + [s]])
        rings.append(rs)
    return rings


# ------------------------------------------------------------------ raster / files
def raster(M, H, biome, x0, y0, x1, y1, R):
    """Barycentric heights and nearest-corner biome per pixel over the window."""
    X, Y, tris = M["X"], M["Y"], M["tris"]
    W = R
    Hh = max(1, int(round(R * (y1 - y0) / (x1 - x0))))
    px = (x1 - x0) / W
    Z = [[-0.3] * W for _ in range(Hh)]
    B = [[0] * W for _ in range(Hh)]
    for a, b, c in tris:
        ax, ay, bx, by, cx, cy = X[a], Y[a], X[b], Y[b], X[c], Y[c]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if det == 0:
            continue
        c0 = max(0, int(math.floor((min(ax, bx, cx) - x0) / px - 0.5)) + 0)
        c1 = min(W - 1, int(math.ceil((max(ax, bx, cx) - x0) / px - 0.5)))
        r0 = max(0, int(math.floor((min(ay, by, cy) - y0) / px - 0.5)))
        r1 = min(Hh - 1, int(math.ceil((max(ay, by, cy) - y0) / px - 0.5)))
        ha, hb, hc = H[a], H[b], H[c]
        for r in range(r0, r1 + 1):
            wy = y0 + (r + 0.5) * px
            zr = Z[r]
            br = B[r]
            for col in range(c0, c1 + 1):
                wx = x0 + (col + 0.5) * px
                l1 = ((by - cy) * (wx - cx) + (cx - bx) * (wy - cy)) / det
                if l1 < -1e-9:
                    continue
                l2 = ((cy - ay) * (wx - cx) + (ax - cx) * (wy - cy)) / det
                if l2 < -1e-9:
                    continue
                l3 = 1 - l1 - l2
                if l3 < -1e-9:
                    continue
                zr[col] = l1 * ha + l2 * hb + l3 * hc
                br[col] = biome[a] if l1 >= l2 and l1 >= l3 else (biome[b] if l2 >= l3 else biome[c])
    return Z, B, px


def elev_m(h):
    return h * ELEV_LAND if h >= 0 else h * ELEV_SEA


def png_bytes(w, h, rows, depth, ctype):
    if depth == 16:
        raw = b"".join(b"\0" + struct.pack(">%dH" % w, *r) for r in rows)
    else:
        raw = b"".join(b"\0" + bytes(r) for r in rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def hex_rgb(s):
    return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)


def shaded_rgb(Z, B, px):
    """Biome colour times a Horn hillshade (NW light), as RGB rows."""
    Hh, W = len(Z), len(Z[0])
    pal = [hex_rgb(b[1]) for b in BIOMES]
    zf = ELEV_LAND / 1000.0 * 6.0
    zen = math.radians(45)
    az = math.radians(135)
    rows = []
    for r in range(Hh):
        r0 = Z[max(r - 1, 0)]
        r1 = Z[r]
        r2 = Z[min(r + 1, Hh - 1)]
        out = bytearray()
        for c in range(W):
            cl = max(c - 1, 0)
            cr = min(c + 1, W - 1)
            col = pal[B[r][c]]
            if r1[c] < 0:
                out += bytes(col)
                continue
            dzdx = ((r0[cr] + 2 * r1[cr] + r2[cr]) - (r0[cl] + 2 * r1[cl] + r2[cl])) / (8 * px) * zf
            dzdy = ((r2[cl] + 2 * r2[c] + r2[cr]) - (r0[cl] + 2 * r0[c] + r0[cr])) / (8 * px) * zf
            slope = math.atan(math.hypot(dzdx, dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            v = math.cos(zen) * math.cos(slope) + math.sin(zen) * math.sin(slope) * math.cos(az - aspect)
            k = 0.55 + 0.6 * max(0.0, v)
            out += bytes(min(255, int(ch * k)) for ch in col)
        rows.append(out)
    return rows


def rnd(v, k=6):
    return round(v, k)


def to_geo(x, y):
    """Map km (y south) -> local metres (y north)."""
    return [round(x * 1000.0, 2), round((WORLD - y) * 1000.0, 2)]


def dump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, separators=(",", ":"), sort_keys=False)
        f.write("\n")


def write_folder(out, recipe, M, H, hyd, temp, prec, biome, window, R, deltas=(), parent_ctx=None):
    import mpw_human
    os.makedirs(out, exist_ok=True)
    X, Y, tris = M["X"], M["Y"], M["tris"]
    x0, y0, x1, y1 = window
    n = len(X)
    mesh = dict(nx=M["nx"], ny=M["ny"], sp=M["sp"], gx0=M["gx0"], gy0=M["gy0"],
                x=[rnd(v) for v in X], y=[rnd(v) for v in Y], h=[rnd(v, 7) for v in H],
                f=[rnd(v, 9) for v in hyd["F"]], rcv=hyd["rcv"], acc=[rnd(v, 3) for v in hyd["acc"]],
                river=[1 if v else 0 for v in hyd["river"]], ocean=[1 if v else 0 for v in hyd["ocean"]],
                lake=hyd["lake"], temp=[rnd(v, 3) for v in temp], prec=[rnd(v, 2) for v in prec],
                biome=biome, deltas=list(deltas))
    if hyd.get("outlets"):
        mesh["outlets"] = hyd["outlets"]
    # human layer and names work on the stored (rounded) mesh, so files alone rebuild them
    thr = recipe["params"]["river_threshold"]
    if parent_ctx:
        hum = mpw_human.human_child(mesh, thr, parent_ctx, window)
    else:
        hum = mpw_human.human_world(mesh, thr)
    # ports only on open coast (row 21): a settlement touching a lake or enclosed sea is never a port
    popen = None
    if parent_ctx and parent_ctx.get("open_sea"):
        popen = lambda: (parent_ctx["mesh"], parent_ctx["open_sea"]())   # noqa: E731
    sea = open_sea(mesh, hum["nb"], popen)
    for s in hum["sets"]:
        s["port"] = any(sea[q] for q in hum["nb"][s["cell"]])
    recipe["ports"] = [s["id"] for s in hum["sets"] if s["port"]]
    labels, entries, stem, stem_names, lake_names = mpw_human.name_features(mesh, hum, recipe["language"],
                                                                            parent_ctx)
    # features
    feats = []
    for line in coast_lines(X, Y, H, tris):
        feats.append({"type": "Feature", "properties": {"kind": "coast"},
                      "geometry": {"type": "LineString", "coordinates": [to_geo(*p) for p in line]}})
    rl = river_lines(X, Y, hyd)
    for i, rv in enumerate(rl):
        sid = stem[rv["cells"][0]]
        feats.append({"type": "Feature", "properties": {"kind": "river", "id": i, "acc": rnd(rv["acc"], 3),
                                                        "stem": sid, "name": stem_names.get(sid),
                                                        "cells": rv["cells"]},
                      "geometry": {"type": "LineString",
                                   "coordinates": [to_geo(X[c], Y[c]) for c in rv["cells"]]}})
    rings = lake_rings(X, Y, tris, hyd["lake"], len(hyd["lakes"]))
    for lid, comp in enumerate(hyd["lakes"]):
        outs = [c for c in comp if hyd["lake"][hyd["rcv"][c]] != lid]
        geom = {"type": "MultiPolygon", "coordinates": [[[to_geo(*p) for p in r]] for r in rings[lid]]}
        feats.append({"type": "Feature", "properties": {"kind": "lake", "id": lid, "name": lake_names.get(lid),
                                                        "cells": len(comp),
                                                        "outlets": outs,
                                                        "level_m": rnd(elev_m(hyd["F"][comp[0]]), 1)},
                      "geometry": geom})
    human = mpw_human.features(mesh, hum, stem, stem_names)
    feats += labels + human
    dump(os.path.join(out, "features.geojson"), {"type": "FeatureCollection", "features": feats})
    dump(os.path.join(out, "mesh.json"), mesh)
    # heights.png + world file
    Z, B, px = raster(M, H, biome, x0, y0, x1, y1, R)
    rows = [[max(0, min(65535, int(round(elev_m(z) + PNG_OFFSET)))) for z in zr] for zr in Z]
    with open(os.path.join(out, "heights.png"), "wb") as f:
        f.write(png_bytes(len(rows[0]), len(rows), rows, 16, 0))
    pm = px * 1000.0
    tl = to_geo(x0 + px / 2, y0 + px / 2)
    with open(os.path.join(out, "heights.pgw"), "w", newline="\n") as f:
        f.write("%.6f\n0.0\n0.0\n%.6f\n%.6f\n%.6f\n" % (pm, -pm, tl[0], tl[1]))
    dump(os.path.join(out, "names.json"), {"seed": recipe["seed"], "language": recipe["language"],
                                           "names": entries})
    dump(os.path.join(out, "sources.json"), {"files": [], "note": "generated; nothing fetched"})
    dump(os.path.join(out, "recipe.json"), recipe)
    # svg
    rgb = shaded_rgb(Z, B, px)
    write_svg(os.path.join(out, "map.svg"), recipe, X, Y, H, tris, hyd, rl, rings, window, rgb, human)
    return dict(rivers=len(rl), lakes=len(hyd["lakes"]), settlements=len(hum["sets"]), roads=len(hum["roads"]),
                names=len(entries))


def write_svg(path, recipe, X, Y, H, tris, hyd, rl, rings, window, rgb, human=()):
    x0, y0, x1, y1 = window
    W = 1000.0
    s = W / (x1 - x0)
    Hs = (y1 - y0) * s

    def P(x, y):
        return "%.1f %.1f" % ((x - x0) * s, (y - y0) * s)
    img = base64.b64encode(png_bytes(len(rgb[0]) // 3, len(rgb), rgb, 8, 2)).decode()
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
         % (W, Hs, W, Hs),
         '<rect width="100%%" height="100%%" fill="%s"/>' % BIOMES[0][1],
         '<image href="data:image/png;base64,%s" width="%d" height="%d"/>' % (img, W, Hs)]
    d = []
    for lid, rs in enumerate(rings):
        for r in rs:
            d.append("M" + "L".join(P(*p) for p in r) + "Z")
    if d:
        o.append('<path fill="%s" stroke="#2f6fa8" stroke-width="0.6" d="%s"/>' % (BIOMES[1][1], "".join(d)))
    thr = recipe["params"]["river_threshold"]
    o.append('<g fill="none" stroke="#2f6fa8" stroke-linecap="round" stroke-linejoin="round">')
    for rv in rl:
        w = min(3.5, 0.5 + 0.35 * math.sqrt(rv["acc"] / thr))
        o.append('<path stroke-width="%.2f" d="M%s"/>' % (w, "L".join(P(X[c], Y[c]) for c in rv["cells"])))
    o.append("</g>")
    cd = ["M" + "L".join(P(*p) for p in line) for line in coast_lines(X, Y, H, tris)]
    o.append('<path fill="none" stroke="#24343c" stroke-width="1.1" d="%s"/>' % "".join(cd))
    style = {"major": ("#7a3b1d", 1.6, ""), "minor": ("#8a5a3a", 1.0, ""), "track": ("#8a5a3a", 0.7, "3 2")}
    for f in human:
        pr = f["properties"]
        if pr["kind"] in ("road", "track"):
            col, w, dash = style.get(pr["rank"], style["minor"])
            o.append('<path fill="none" stroke="%s" stroke-width="%.1f"%s d="M%s"/>'
                     % (col, w, ' stroke-dasharray="%s"' % dash if dash else "",
                        "L".join(P(X[c], Y[c]) for c in pr["cells"])))
    size = {"city": (4.5, 15), "town": (3.2, 12), "village": (2.0, 9)}
    for f in human:
        pr = f["properties"]
        if pr["kind"] == "settlement":
            r, fs = size[pr["rank"]]
            c = pr["cell"]
            sx, sy = (X[c] - x0) * s, (Y[c] - y0) * s
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#222" stroke="#fff" stroke-width="0.8"/>'
                     % (sx, sy, r))
            o.append('<text x="%.1f" y="%.1f" font-family="Georgia,serif" font-size="%d" fill="#222" '
                     'stroke="#fff" stroke-width="2.5" paint-order="stroke">%s</text>'
                     % (sx + r + 2, sy + fs * 0.35, fs, pr["name"]))
    o.append('<text x="20" y="34" font-family="Georgia,serif" font-size="22" fill="#222" stroke="#fff" '
             'stroke-width="3" paint-order="stroke">%s seed %d</text>' % (recipe["kind"], recipe["seed"]))
    o.append("</svg>")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o) + "\n")


# ------------------------------------------------------------------ commands
def gen_world(seed, cells, out, plates=12, erosion=15, lat_top=60.0, lat_bottom=0.0, raster_px=512,
              version="0.2.0", style=None, pattern=None, language=None):
    import mpw_names
    _LAT.clear()
    lang = language or mpw_names.make_language(seed, style, pattern)
    t = {}
    t0 = time.perf_counter()
    side = max(4, int(round(math.sqrt(cells))))
    sp = WORLD / side
    M = build_mesh(seed, 0.0, 0.0, WORLD - 1e-9, WORLD - 1e-9, sp)
    t["mesh"] = time.perf_counter() - t0
    t1 = time.perf_counter()
    H, upl, plate, kind, pinfo = land_heights(seed, M, plates)
    t["plates_noise"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    H = erode(H, upl, M, erosion)
    t["erosion"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    n = len(H)
    thr = max(20, n // 400)
    hyd = hydrology(H, M["nb"], thr)
    t["hydrology"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    temp, prec, biome = climate(seed, M, H, hyd, lat_top, lat_bottom)
    t["climate"] = time.perf_counter() - t1
    recipe = dict(kind="world", seed=seed, generator=GEN_VERSION, tool="mapwright", tool_version=version,
                  params=dict(cells=cells, cells_actual=n, spacing_km=sp, plates=plates, erosion_steps=erosion,
                              lat_top=lat_top, lat_bottom=lat_bottom, river_threshold=thr, raster_px=raster_px,
                              eps_flood=EPS_FLOOD, lake_min=LAKE_MIN),
                  projection=dict(kind="local", units="m", axes="x east, y north",
                                  extent_m=[0, 0, WORLD * 1000, WORLD * 1000],
                                  latitude="linear in y: %s at the north edge, %s at the south edge"
                                           % (lat_top, lat_bottom)),
                  heights=dict(file="heights.png", value="metres + %d" % PNG_OFFSET,
                               land_m_per_unit=ELEV_LAND, sea_m_per_unit=ELEV_SEA),
                  extent=[0, 0, WORLD, WORLD], parent=None, deltas=[],
                  plates=dict(continental=pinfo["continental"]), language=lang)
    t1 = time.perf_counter()
    info = write_folder(out, recipe, M, H, hyd, temp, prec, biome, (0.0, 0.0, WORLD, WORLD), raster_px)
    t["write_render"] = time.perf_counter() - t1
    t["total"] = time.perf_counter() - t0
    land = sum(1 for o in hyd["ocean"] if not o)
    return dict(out=out, cells=n, land_fraction=round(land / n, 3), rivers=info["rivers"], lakes=info["lakes"],
                settlements=info["settlements"], roads=info["roads"], names=info["names"], style=lang["style"],
                lakes_retreed=hyd["lakes_retreed"], times={k: round(v, 3) for k, v in t.items()})


def load(d, name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return json.load(f)


class Grid:
    """Bucket index of points for nearest-k lookups."""

    def __init__(self, X, Y, size):
        self.X, self.Y, self.s = X, Y, size
        self.b = {}
        for i in range(len(X)):
            self.b.setdefault((int(X[i] // size), int(Y[i] // size)), []).append(i)

    def near(self, x, y, k, rmax=6):
        gi, gj = int(x // self.s), int(y // self.s)
        found = []
        for r in range(rmax + 1):
            for dj in range(-r, r + 1):
                for di in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    for p in self.b.get((gi + di, gj + dj), ()):
                        found.append(((self.X[p] - x) ** 2 + (self.Y[p] - y) ** 2, p))
            if len(found) >= k and r >= 1:
                found.sort()
                if found[k - 1][0] <= (r * self.s) ** 2:
                    return found[:k]
        found.sort()
        return found[:k]


def pick_window(pm, frac=0.25):
    """Quarter-width tile of the parent with the most coast (prototype rule)."""
    X, Y, h, nx = pm["x"], pm["y"], pm["h"], pm["nx"]
    best = None
    size = WORLD * frac
    k = int(round(1 / frac))
    for wy in range(k):
        for wx in range(k):
            ax, ay = wx * size, wy * size
            cnt = 0
            for c in range(len(X)):
                if ax <= X[c] < ax + size and ay <= Y[c] < ay + size:
                    i = c % nx
                    if i + 1 < nx and (h[c] < 0) != (h[c + 1] < 0):
                        cnt += 1
            if best is None or cnt > best[0]:
                best = (cnt, ax, ay)
    _, ax, ay = best
    return (ax, ay, ax + size, ay + size)


def parent_dir(child, rc):
    """Parent folder of a child recipe: relative to the child folder (old recipes stored it absolute)."""
    p = rc["parent"]["path"]
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(child, p))


def parent_ref(parent, out):
    """Parent path as stored in the child recipe: relative to the child folder, '/' separators."""
    try:
        return os.path.relpath(os.path.abspath(parent), os.path.abspath(out)).replace("\\", "/")
    except ValueError:    # another drive on Windows
        return os.path.abspath(parent).replace("\\", "/")


def _clip_exit(ax, ay, bx, by, x0, y0, x1, y1):
    """Point where segment a(inside)->b(outside) leaves the rectangle."""
    t = 1.0
    for v, d, lo, hi in ((ax, bx - ax, x0, x1), (ay, by - ay, y0, y1)):
        if d > 0:
            t = min(t, (hi - v) / d)
        elif d < 0:
            t = min(t, (lo - v) / d)
    return ax + (bx - ax) * t, ay + (by - ay) * t


def edge_outlets(M, H, PX, PY, prcv, pacc, pocean, window):
    """Border cells where the parent's flow leaves the window (L-009).

    Every parent flow edge from a cell inside the window to one outside marks the
    child border cell nearest its exit point; hydrology drains through them when the
    window holds no sea. The biggest exit always counts; smaller ones need a tenth of
    its area, so a few real outlets carry the water instead of every border cell."""
    x0, y0, x1, y1 = window
    border = M["border"]
    X, Y = M["X"], M["Y"]
    bcells = [c for c in range(len(X)) if border[c]]
    exits = []
    for p in range(len(PX)):
        r = prcv[p]
        if r < 0 or pocean[p]:
            continue
        if not (x0 <= PX[p] <= x1 and y0 <= PY[p] <= y1) or (x0 <= PX[r] <= x1 and y0 <= PY[r] <= y1):
            continue
        ex, ey = _clip_exit(PX[p], PY[p], PX[r], PY[r], x0, y0, x1, y1)
        c = min(bcells, key=lambda q: ((X[q] - ex) ** 2 + (Y[q] - ey) ** 2, q))
        exits.append((pacc[p], c))
    if not exits:
        return [min(bcells, key=lambda q: (H[q], q))] if bcells else []   # lowest edge cell
    top = max(a for a, _ in exits)
    return sorted({c for a, c in exits if a >= 0.1 * top})


def gen_region(parent, window, cells, out, detail=0.03, raster_px=512, version="0.2.0", ref=None):
    import mpw_names
    _LAT.clear()
    t0 = time.perf_counter()
    prec_ = load(parent, "recipe.json")
    pm = load(parent, "mesh.json")
    seed = prec_["seed"]
    if window is None:
        window = pick_window(pm)
    x0, y0, x1, y1 = window
    if not (0 <= x0 < x1 <= WORLD and 0 <= y0 < y1 <= WORLD):
        raise ValueError("window must lie inside 0..%g" % WORLD)
    psp = pm["sp"]
    sp = math.sqrt((x1 - x0) * (y1 - y0) / cells)
    if sp >= psp:
        raise ValueError("child spacing %.3f km is not finer than the parent's %.3f km; raise --cells" % (sp, psp))
    M = build_mesh(seed, x0, y0, x1, y1, sp)
    X, Y = M["X"], M["Y"]
    PX, PY, PH, PF = pm["x"], pm["y"], pm["h"], pm["f"]
    g = Grid(PX, PY, psp)
    n = len(X)
    H = [0.0] * n
    damp = detail * psp / (WORLD / 126.0)   # amplitude scales with parent spacing (0.03 at 16k)
    ptris = _tris(pm)
    inc = {}
    for t in ptris:
        for v in t:
            inc.setdefault(v, []).append(t)
    pcoast = SegGrid(_coast_segs(PX, PY, PH, ptris), psp)
    band = max(0.0, 0.8 * psp - 1.2 * sp)   # coast may wander this far; a child edge adds up to ~1.2 sp
    for c in range(n):
        x, y = X[c], Y[c]
        s = 0.0
        ws = 0.0
        nn = g.near(x, y, 3)
        for d, p in nn:
            w = 1.0 / (d + 1e-9)
            s += w * PH[p]
            ws += w
        h = s / ws + damp * fbm(seed + 900, x, y, 0.05, 3)
        # the side of the coast comes from the parent's own linear surface (its
        # coast line), so the child coast can only move inside a band around it
        side = None
        for _, p in nn:
            for t in inc.get(p, ()):
                a_, b_, c_ = t
                det = (PY[b_] - PY[c_]) * (PX[a_] - PX[c_]) + (PX[c_] - PX[b_]) * (PY[a_] - PY[c_])
                if det == 0:
                    continue
                l1 = ((PY[b_] - PY[c_]) * (x - PX[c_]) + (PX[c_] - PX[b_]) * (y - PY[c_])) / det
                l2 = ((PY[c_] - PY[a_]) * (x - PX[c_]) + (PX[a_] - PX[c_]) * (y - PY[c_])) / det
                if l1 >= -1e-9 and l2 >= -1e-9 and 1 - l1 - l2 >= -1e-9:
                    side = (l1 * PH[a_] + l2 * PH[b_] + (1 - l1 - l2) * PH[c_]) < 0
                    break
            if side is not None:
                break
        if side is None:
            side = nn[0][1] is not None and PH[nn[0][1]] < 0
        if (h < 0) != side and pcoast.dist(x, y, 3) > band:
            h = -1e-4 if side else 1e-4
        H[c] = h
    # burn parent rivers into the child: sample each parent river segment in the window
    cg = Grid(X, Y, sp)
    pr, prcv, pacc, pocean = pm["river"], pm["rcv"], pm["acc"], pm["ocean"]
    inflow = [1.0] * n
    ratio = (sp / psp) ** 2
    forced = set()
    psegs = []
    for p in range(len(PX)):
        r = prcv[p]
        if not pr[p] or r < 0:
            continue
        ax, ay, bx, by = PX[p], PY[p], PX[r], PY[r]
        if max(ax, bx) < x0 or min(ax, bx) > x1 or max(ay, by) < y0 or min(ay, by) > y1:
            continue
        psegs.append((ax, ay, bx, by))
        L = math.hypot(bx - ax, by - ay)
        k = max(2, int(L / (sp * 0.5)) + 1)
        for i in range(k + 1):
            t = i / k
            x = ax + (bx - ax) * t
            y = ay + (by - ay) * t
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            hit = cg.near(x, y, 1)
            if not hit:
                continue
            c = hit[0][1]
            lvl = PF[p] + (PF[r] - PF[p]) * t
            if pocean[r] and t > 0.5:
                continue
            target = lvl - 0.004
            if PH[p] >= 0:
                target = max(target, 2e-4 * (1 - t))
            if H[c] > target and not M["border"][c]:
                H[c] = target
            forced.add(c)
    # inflow: parent rivers entering through the window edge carry their upstream area
    for p in range(len(PX)):
        r = prcv[p]
        if not pr[p] or r < 0:
            continue
        inside_p = x0 <= PX[p] <= x1 and y0 <= PY[p] <= y1
        inside_r = x0 <= PX[r] <= x1 and y0 <= PY[r] <= y1
        if inside_r and not inside_p:
            hit = cg.near(PX[r], PY[r], 1)
            if hit:
                inflow[hit[0][1]] += pacc[p] / ratio
    outlets = edge_outlets(M, H, PX, PY, prcv, pacc, pocean, (x0, y0, x1, y1))
    pthr = prec_["params"]["river_threshold"]
    thr = max(8.0, pthr / ratio / 4.0)     # smaller rivers than the parent shows
    # the parent's settlements and roads stood on dry land: where the finer child
    # surface puts them in the sea, lift them to just above sea level; where it floods
    # them into a new lake, lift them just above the lake level (a causeway or island)
    pfe = load(parent, "features.geojson")["features"]
    keep = set()
    for f in pfe:
        pr = f["properties"]
        if pr.get("kind") == "settlement":
            pts = [(PX[pr["cell"]], PY[pr["cell"]])]
        elif pr.get("kind") in ("road", "track"):
            pts = []
            cs = pr["cells"]
            for a, b in zip(cs, cs[1:]):
                L = math.hypot(PX[b] - PX[a], PY[b] - PY[a])
                k = max(1, int(L / (sp * 0.5)) + 1)
                pts += [(PX[a] + (PX[b] - PX[a]) * i / k, PY[a] + (PY[b] - PY[a]) * i / k) for i in range(k + 1)]
        else:
            continue
        for x, y in pts:
            if x0 <= x <= x1 and y0 <= y <= y1:
                hit = cg.near(x, y, 1)
                if hit:
                    keep.add(hit[0][1])
    for c in sorted(keep):
        if H[c] < 1e-4:
            H[c] = 1e-4
    hyd = hydrology(H, M["nb"], thr, inflow, outlets)
    for _ in range(3):
        wet = [c for c in sorted(keep) if hyd["lake"][c] >= 0]
        if not wet:
            break
        for c in wet:
            H[c] = hyd["F"][c] + 1e-4
        hyd = hydrology(H, M["nb"], thr, inflow, outlets)
    # parent river paths are rivers in the child, down to the sea, a lake or an edge outlet
    for c in sorted(forced):
        cur = c
        guard = 0
        while cur >= 0 and not hyd["ocean"][cur] and guard < n:
            hyd["river"][cur] = True
            cur = hyd["rcv"][cur]
            guard += 1
    pp = prec_["params"]
    temp, prc, biome = climate(seed, M, H, hyd, pp["lat_top"], pp["lat_bottom"])
    recipe = dict(kind="region", seed=seed, generator=GEN_VERSION, tool="mapwright", tool_version=version,
                  params=dict(cells=cells, cells_actual=n, spacing_km=sp, parent_spacing_km=psp, detail=detail,
                              lat_top=pp["lat_top"], lat_bottom=pp["lat_bottom"], river_threshold=thr,
                              raster_px=raster_px, eps_flood=EPS_FLOOD, lake_min=LAKE_MIN),
                  projection=prec_["projection"], heights=prec_["heights"],
                  extent=[x0, y0, x1, y1],
                  parent=dict(path=ref if ref is not None else parent_ref(parent, out), window=[x0, y0, x1, y1]),
                  deltas=[], language=prec_.get("language") or mpw_names.make_language(seed))
    pnames = load(parent, "names.json").get("names") or []
    ctx = dict(mesh=pm, features=pfe, names=pnames, sp=psp, open_sea=lambda: open_sea_dir(parent))
    info = write_folder(out, recipe, M, H, hyd, temp, prc, biome, (x0, y0, x1, y1), raster_px, parent_ctx=ctx)
    return dict(out=out, cells=n, window=[x0, y0, x1, y1], rivers=info["rivers"], lakes=info["lakes"],
                settlements=info["settlements"], roads=info["roads"], names=info["names"],
                parent_river_segments=len(psegs), times=dict(total=round(time.perf_counter() - t0, 3)))


# ------------------------------------------------------------------ check
def _dseg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy or 1e-12
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


class SegGrid:
    def __init__(self, segs, size):
        self.s = size
        self.b = {}
        self.segs = segs
        for i, (ax, ay, bx, by) in enumerate(segs):
            for gi in range(int(min(ax, bx) // size), int(max(ax, bx) // size) + 1):
                for gj in range(int(min(ay, by) // size), int(max(ay, by) // size) + 1):
                    self.b.setdefault((gi, gj), []).append(i)

    def dist(self, x, y, rmax=12):
        gi, gj = int(x // self.s), int(y // self.s)
        best = 1e30
        for r in range(rmax + 1):
            for dj in range(-r, r + 1):
                for di in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    for i in self.b.get((gi + di, gj + dj), ()):
                        best = min(best, _dseg(x, y, *self.segs[i]))
            if best <= r * self.s:
                break
        return best


def _coast_segs(X, Y, H, tris):
    out = []
    for line in coast_lines(X, Y, H, tris):
        for a, b in zip(line, line[1:]):
            out.append((a[0], a[1], b[0], b[1]))
    return out


def _tris(m):
    """Rebuild the Delaunay triangles from the stored mesh (same rule as build_mesh)."""
    X, Y, nx, ny = m["x"], m["y"], m["nx"], m["ny"]
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            b, c, d = a + 1, a + nx + 1, a + nx
            ax, ay = X[a] - X[d], Y[a] - Y[d]
            bx, by = X[b] - X[d], Y[b] - Y[d]
            cx, cy = X[c] - X[d], Y[c] - Y[d]
            if (ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay) \
                    + (cx * cx + cy * cy) * (ax * by - bx * ay) > 0:
                tris += [(a, b, d), (b, c, d)]
            else:
                tris += [(a, b, c), (a, c, d)]
    return tris


def _neighbours(m):
    nb = [set() for _ in range(len(m["x"]))]
    for a, b, c in _tris(m):
        for p, q in ((a, b), (b, c), (c, a)):
            nb[p].add(q)
            nb[q].add(p)
    nx, ny = m["nx"], m["ny"]
    for j in range(ny - 1):
        a = j * nx + nx - 1
        nb[a].add(a + nx)
        nb[a + nx].add(a)
    for i in range(nx - 1):
        a = (ny - 1) * nx + i
        nb[a].add(a + 1)
        nb[a + 1].add(a)
    return nb


def open_sea(m, nb, parent=None):
    """Open-sea mask: sea cells reached by flooding inward from the map border through sea cells.

    Enclosed sea below the waterline that the flood never reaches is not open sea, and lakes never are.
    A child window with no sea on its border takes its seeds from the parent: parent() returns
    (parent mesh, parent open-sea mask), and a child sea cell whose nearest parent cell is open sea seeds the flood.
    """
    ocean = m["ocean"]
    n = len(ocean)
    nx, ny = m["nx"], m["ny"]
    if nx * ny == n:
        edge = [j * nx + i for j in range(ny) for i in range(nx) if i in (0, nx - 1) or j in (0, ny - 1)]
    else:
        edge = [c for c in range(n) if len(nb[c]) < 6]
    seeds = [c for c in edge if ocean[c]]
    if not seeds and parent is not None and any(ocean):
        pm, pmask = parent()
        g = Grid(pm["x"], pm["y"], pm["sp"])
        X, Y = m["x"], m["y"]
        for c in range(n):
            if ocean[c]:
                hit = g.near(X[c], Y[c], 1)
                if hit and pmask[hit[0][1]]:
                    seeds.append(c)
    out = [0] * n
    stack = []
    for c in seeds:
        if not out[c]:
            out[c] = 1
            stack.append(c)
    while stack:
        c = stack.pop()
        for q in nb[c]:
            if ocean[q] and not out[q]:
                out[q] = 1
                stack.append(q)
    return out


def open_sea_dir(d):
    """open_sea for a written folder; a child asks its parent folder only when it needs to."""
    rc = load(d, "recipe.json")
    m = load(d, "mesh.json")
    parent = None
    if rc.get("parent"):
        pd = parent_dir(d, rc)
        parent = lambda: (load(pd, "mesh.json"), open_sea_dir(pd))   # noqa: E731
    return open_sea(m, _neighbours(m), parent)


def regenerate(d, tmp):
    rc = load(d, "recipe.json")
    p = rc["params"]
    if rc["kind"] == "world":
        gen_world(rc["seed"], p["cells"], tmp, p["plates"], p["erosion_steps"], p["lat_top"], p["lat_bottom"],
                  p["raster_px"], rc["tool_version"], language=rc.get("language"))
    else:
        gen_region(parent_dir(d, rc), tuple(rc["parent"]["window"]), p["cells"], tmp, p["detail"],
                   p["raster_px"], rc["tool_version"], ref=rc["parent"]["path"])


FILES = ("recipe.json", "features.geojson", "heights.png", "heights.pgw", "mesh.json", "names.json",
         "sources.json", "map.svg")


SHADOW_MIN_WET = 50   # cm/yr windward mean below which bar 7 does not judge the rain shadow


def check(d, determinism=True):
    """Land proof bars. Returns list of (number, name, ok, detail)."""
    rc = load(d, "recipe.json")
    m = load(d, "mesh.json")
    X, Y, F, rcv, river, ocean, lake = m["x"], m["y"], m["f"], m["rcv"], m["river"], m["ocean"], m["lake"]
    n = len(X)
    nb = _neighbours(m)
    bars = []
    # 1 downhill (a landlocked window drains through its edge outlets, L-009)
    outl = set(m.get("outlets", []))
    bad = 0
    for c in range(n):
        if not river[c]:
            continue
        cur = c
        steps = 0
        while not ocean[cur] and cur not in outl:
            r = rcv[cur]
            if r < 0 or r not in nb[cur] or not F[r] < F[cur] or steps > n:
                bad += 1
                break
            cur = r
            steps += 1
    nriv = sum(river)
    bars.append((1, "every river runs downhill to the sea or through a lake to it", bad == 0,
                 "%d river cells, %d failures%s" % (nriv, bad, ", %d edge outlets" % len(outl) if outl else "")))
    # 2 no split outside a marked delta
    deltas = set(m.get("deltas", []))
    split = 0
    gaps = 0
    for c in range(n):
        if river[c] and not ocean[c]:
            r = rcv[c]
            if not isinstance(r, int):
                split += 1
            elif r >= 0 and not (river[r] or ocean[r] or lake[r] >= 0) and c not in deltas:
                gaps += 1
    feats = load(d, "features.geojson")["features"]
    seen_next = {}
    for f in feats:
        if f["properties"]["kind"] == "river":
            cells = f["properties"]["cells"]
            for a, b in zip(cells, cells[1:]):
                if seen_next.setdefault(a, b) != b and a not in deltas:
                    split += 1
    bars.append((2, "no river splits outside a marked delta", split == 0 and gaps == 0,
                 "%d splits, %d rivers that stop on land, %d marked deltas" % (split, gaps, len(deltas))))
    # 3 lakes
    nl = max(lake) + 1 if lake else 0
    multi = 0
    worst = 0
    for lid in range(nl):
        outs = sum(1 for c in range(n) if lake[c] == lid and lake[rcv[c]] != lid)
        worst = max(worst, outs)
        if outs > 1:
            multi += 1
    bars.append((3, "each lake has at most one outlet", multi == 0,
                 "%d lakes, max outlets %d" % (nl, worst)))
    # 4 determinism
    if determinism:
        tmp = tempfile.mkdtemp(prefix="mpw-check-")
        diff = ["(not run)"]
        try:
            regenerate(d, tmp)
            diff = []
            for fn in FILES:
                with open(os.path.join(d, fn), "rb") as a, open(os.path.join(tmp, fn), "rb") as b:
                    if hashlib.sha256(a.read()).digest() != hashlib.sha256(b.read()).digest():
                        diff.append(fn)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        bars.append((4, "same recipe gives byte-identical files", not diff,
                     "all %d files identical" % len(FILES) if not diff else "differ: " + ", ".join(diff)))
    else:
        diff = None
        bars.append((4, "same recipe gives byte-identical files", True, "skipped (--no-regen)"))
    # 5, 6 child vs parent
    if rc.get("parent"):
        pd = parent_dir(d, rc)
        pm = load(pd, "mesh.json")
        psp = pm["sp"]
        x0, y0, x1, y1 = rc["parent"]["window"]
        pseg = SegGrid(_coast_segs(pm["x"], pm["y"], pm["h"], _tris(pm)), psp)
        csegs = _coast_segs(X, Y, m["h"], _tris(m))
        ds = [pseg.dist((a + c) / 2, (b + e) / 2) / psp for a, b, c, e in csegs]
        mx = max(ds) if ds else 0.0
        bars.append((5, "child coast within 1 parent spacing of the parent coast", mx <= 1.0,
                     "%d child coast segments, max %.3f, mean %.3f parent spacings"
                     % (len(ds), mx, (sum(ds) / len(ds)) if ds else 0.0)))
        cr = []
        for c in range(n):
            r = rcv[c]
            if river[c] and r >= 0:
                cr.append((X[c], Y[c], X[r], Y[r]))
        cgrid = SegGrid(cr, psp) if cr else None
        dr = []
        PX, PY, prv, prc, poc = pm["x"], pm["y"], pm["river"], pm["rcv"], pm["ocean"]
        for p in range(len(PX)):
            r = prc[p]
            if not prv[p] or r < 0:
                continue
            for t in (0.0, 0.5):
                x = PX[p] + (PX[r] - PX[p]) * t
                y = PY[p] + (PY[r] - PY[p]) * t
                if x0 + psp <= x <= x1 - psp and y0 + psp <= y <= y1 - psp:
                    dr.append((cgrid.dist(x, y) if cgrid else 1e9) / psp)
        mr = max(dr) if dr else 0.0
        bars.append((6, "parent rivers present in the child within 1 parent spacing", mr <= 1.0,
                     "%d parent river points, max %.3f parent spacings" % (len(dr), mr)))
    else:
        bars.append((5, "child coast within 1 parent spacing of the parent coast", True, "n/a (not a child map)"))
        bars.append((6, "parent rivers present in the child within 1 parent spacing", True, "n/a (not a child map)"))
    # 7 climate
    temp, prec, h = m["temp"], m["prec"], m["h"]
    lt, lb = rc["params"]["lat_top"], rc["params"]["lat_bottom"]
    bands = {}
    for c in range(n):
        if ocean[c]:
            continue
        lat = abs(lat_of(Y[c], lt, lb))
        sl = temp[c] + LAPSE * max(0.0, h[c]) * ELEV_LAND / 1000.0
        bands.setdefault(int(lat // 10), []).append(sl)
    keys = sorted(k for k in bands if len(bands[k]) >= 5)
    means = [sum(bands[k]) / len(bands[k]) for k in keys]
    mono = all(a > b for a, b in zip(means, means[1:]))
    # rain shadow: land cells just downwind of high ground are drier than just upwind
    nx = m["nx"]
    wind_up, wind_dn = [], []
    for c in range(n):
        if ocean[c] or h[c] * ELEV_LAND < 1200:
            continue
        lat = lat_of(Y[c], lt, lb)
        wd = wind_dir(lat)
        i = c % nx
        for k, lst in ((-3 * wd, wind_up), (3 * wd, wind_dn)):
            j = i + k
            q = c + k
            if 0 <= j < nx and not ocean[q] and lake[q] < 0 and h[q] * ELEV_LAND < 800:
                lst.append(prec[q])
    up = sum(wind_up) / len(wind_up) if wind_up else 0.0
    dn = sum(wind_dn) / len(wind_dn) if wind_dn else 0.0
    few = len(wind_up) < 20 or len(wind_dn) < 20
    arid = not few and up < SHADOW_MIN_WET   # nothing to shadow: judged on noise (L-009, T-20261116-8)
    shadow = few or arid or up > dn
    bars.append((7, "climate: temperature falls poleward; lee of mountains drier", mono and shadow,
                 "sea-level temp by 10-deg band %s; windward %.0f vs leeward %.0f cm/yr%s"
                 % ("/".join("%.1f" % v for v in means), up, dn, " (too few samples, shadow not judged)" if few else
                    " (windward under %d cm/yr, too arid to judge)" % SHADOW_MIN_WET if arid else "")))
    bars += human_bars(d, rc, m, nb, feats, diff)
    return bars


def human_bars(d, rc, m, nb, feats, diff):
    """Bars 8-13: settlements, roads, names, determinism of names and features, child keeps parent."""
    import mpw_human
    X, Y, ocean, lake = m["x"], m["y"], m["ocean"], m["lake"]
    n = len(X)
    nbs = [set(v) for v in nb]
    out = []
    sets = [f["properties"] for f in feats if f["properties"]["kind"] == "settlement"]
    roads = [f["properties"] for f in feats if f["properties"]["kind"] in ("road", "track")]
    bad = [s["id"] for s in sets if not (0 <= s["cell"] < n) or ocean[s["cell"]] or lake[s["cell"]] >= 0]
    out.append((8, "every settlement on land and not in a lake", not bad,
                "%d settlements, %d in water" % (len(sets), len(bad))))
    land, _ = mpw_human.components(n, nb, mpw_human.passable(m))
    uf = mpw_human.UF()
    for r in roads:
        for a, b in zip(r["cells"], r["cells"][1:]):
            uf.union(a, b)
    groups = {}
    for s in sets:
        groups.setdefault(land[s["cell"]], set()).add(uf.find(s["cell"]))
    split = sorted(k for k, v in groups.items() if len(v) > 1)
    out.append((9, "all settlements of one landmass connected by roads", not split,
                "%d landmasses with settlements, %d split" % (len(groups), len(split))))
    wet = jump = 0
    for r in roads:
        cs = r["cells"]
        wet += sum(1 for c in cs if ocean[c] or lake[c] >= 0)
        jump += sum(1 for a, b in zip(cs, cs[1:]) if b not in nbs[a])
    out.append((10, "roads never run through sea or lake cells (no ferries) and step cell to cell",
                wet == 0 and jump == 0,
                "%d roads, %d road cells, %d in water, %d jumps" % (len(roads), sum(len(r["cells"]) for r in roads),
                                                                   wet, jump)))
    nj = load(d, "names.json")
    ents = nj.get("names") or []
    named = {"settlement", "lake", "sea", "ocean", "range", "land"}
    missing = 0
    fnames = []
    for f in feats:
        pr = f["properties"]
        if pr["kind"] in named or pr["kind"] == "river":
            if not pr.get("name"):
                missing += 1
            elif pr["kind"] != "river":
                fnames.append(pr["name"])
    low = [e["name"].lower() for e in ents]
    dup = len(low) - len(set(low))
    lost = len(set(fnames) - {e["name"] for e in ents})
    rivers_named = {f["properties"]["name"] for f in feats if f["properties"]["kind"] == "river"}
    lost += len(rivers_named - {e["name"] for e in ents} - {None})
    out.append((11, "names unique and present for every named feature", missing == 0 and dup == 0 and lost == 0,
                "%d names, %d duplicates, %d features unnamed, %d feature names missing from names.json"
                % (len(ents), dup, missing, lost)))
    if diff is None:
        out.append((12, "same seed gives byte-identical names.json and features.geojson", True,
                    "skipped (--no-regen)"))
    else:
        bad12 = [fn for fn in ("names.json", "features.geojson") if fn in diff]
        out.append((12, "same seed gives byte-identical names.json and features.geojson", not bad12,
                    "identical" if not bad12 else "differ: " + ", ".join(bad12)))
    if rc.get("parent"):
        pd = parent_dir(d, rc)
        pm = load(pd, "mesh.json")
        psp = pm["sp"]
        tol = mpw_human.TOL_PARENT * psp + m["sp"]
        x0, y0, x1, y1 = rc["parent"]["window"]
        pfe = load(pd, "features.geojson")["features"]
        byp = {s["parent_id"]: s for s in sets if "parent_id" in s}
        worst_s = 0.0
        miss = 0
        cnt = 0
        for f in pfe:
            pr = f["properties"]
            if pr["kind"] != "settlement":
                continue
            px, py = pm["x"][pr["cell"]], pm["y"][pr["cell"]]
            if not (x0 <= px <= x1 and y0 <= py <= y1):
                continue
            cnt += 1
            s = byp.get(pr["id"])
            if s is None or s["name"] != pr["name"]:
                miss += 1
                continue
            worst_s = max(worst_s, math.hypot(X[s["cell"]] - px, Y[s["cell"]] - py))
        segs = [(X[a], Y[a], X[b], Y[b]) for r in roads for a, b in zip(r["cells"], r["cells"][1:])]
        sg = SegGrid(segs, psp) if segs else None
        worst_r = 0.0
        pts = 0
        for f in pfe:
            pr = f["properties"]
            if pr["kind"] not in ("road", "track"):
                continue
            for c in pr["cells"]:
                px, py = pm["x"][c], pm["y"][c]
                if x0 + psp <= px <= x1 - psp and y0 + psp <= py <= y1 - psp:
                    pts += 1
                    worst_r = max(worst_r, sg.dist(px, py) if sg else 1e9)
        ok = miss == 0 and worst_s <= tol and worst_r <= tol
        out.append((13, "child keeps parent settlements and roads within 1 parent + 1 child spacing", ok,
                    "%d parent settlements in window, %d missing or renamed, max shift %.2f km; %d parent road "
                    "points, max %.2f km; tolerance %.2f km" % (cnt, miss, worst_s, pts, worst_r, tol)))
    else:
        out.append((13, "child keeps parent settlements and roads within 1 parent + 1 child spacing", True,
                    "n/a (not a child map)"))
    # 14 ports only on open coast
    sea = open_sea_dir(d)
    ports = [s for s in sets if s.get("port")]
    bad = [s["id"] for s in ports if not (0 <= s["cell"] < n) or not any(sea[q] for q in nb[s["cell"]])]
    listed = sorted(rc.get("ports", []))
    same = listed == sorted(s["id"] for s in ports)
    out.append((14, "every port touches open sea (a lakeshore town is never a port)", not bad and same,
                "%d ports, %d off open sea%s" % (len(ports), len(bad), "" if same else "; recipe ports differ")))
    return out
