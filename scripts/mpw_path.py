"""Pathfinding on recipe folders: A* paths, Dijkstra fields, Tobler travel time, chokepoints and fairness.

Graphs come from the recipe itself:
- dungeon and square battle maps: 8-way moves (or 4 with --moves 4), diagonals cost sqrt(2), no corner cutting,
  no diagonal step into or out of a door, one-way doors of cyclic dungeons entered only from their source side
  (`path` honours locks by default with lock_search over (square, keys held); fields, --ignore-locks and the
  check commands treat locks as open: the walker holds every key);
- hex battle maps: odd-r neighbours, every step costs 1;
- decks: 8-way squares of 1.5 m in metres, a lift square joins the same square on the deck above and below (3 m);
- world and region meshes: the road router's step cost (distance x slope x terrain, bridge to enter a river);
  water cells are impassable. That cost is directed (terrain and bridges are paid on the cell entered).
Standard library only.
"""
import heapq
import json
import math
import os

import mpw_human
import mpw_places as P

SQ2 = math.sqrt(2.0)
DECK_SQ_M = 1.5
LIFT_M = 3.0
DECK_PASS = ".+L"
TOBLER_FLAT = 6.0 * math.exp(-3.5 * 0.05)   # 5.036742 km/h
MODES = {"walk": 1.0, "offpath": 0.6, "horse": 1.25}


def tobler_kmh(slope, mode="walk"):
    """Tobler's hiking function: 6 exp(-3.5 |S + 0.05|) km/h, S = rise over run, positive uphill."""
    return 6.0 * math.exp(-3.5 * abs(slope + 0.05)) * MODES[mode]


def _load(d, name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return json.load(f)


class Graph:
    """nodes: sorted list; out(n) -> [(m, cost)]; est(n, goals) admissible and consistent; xy(n) output coords;
    sxy(n) map.svg pixel coords."""
    directed = False
    units = "steps"

    def out(self, n):
        c = self._cache.get(n)
        if c is None:
            c = self._cache[n] = self._out(n)
        return c

    def reverse(self):
        rev = {n: [] for n in self.nodes}
        for n in self.nodes:
            for m, c in self.out(n):
                rev[m].append((n, c))
        return rev

    def undirected_adj(self):
        adj = {n: set() for n in self.nodes}
        for n in self.nodes:
            for m, _ in self.out(n):
                adj[n].add(m)
                adj[m].add(n)
        return {n: sorted(v) for n, v in adj.items()}


class SquareGraph(Graph):
    def __init__(self, gj, pps, moves=8, passable=P.PASS):
        self.kind = "square"
        self.w, self.h, self.g, self.pps = gj["w"], gj["h"], gj["cells"], pps
        self.moves = moves
        self.passable = passable
        self.nodes = [(x, y) for y in range(self.h) for x in range(self.w) if self.g[y][x] in passable]
        self.ok = set(self.nodes)
        self.doors = {n for n in self.nodes if self.g[n[1]][n[0]] == P.DOOR}
        self.rule = {}
        gr = gj.get("graph")
        for e in (gr or {}).get("edges", []):
            if "oneway" in e:
                dx, dy = e["door"]
                sx, sy = gr["cells"][e["oneway"][0]]
                cx, cy = sx * P.CELL + P.CELL // 2, sy * P.CELL + P.CELL // 2
                self.rule[(dx, dy)] = ((cx > dx) - (cx < dx), (cy > dy) - (cy < dy))
        self.directed = bool(self.rule)
        self.locks = sum(1 for e in (gr or {}).get("edges", []) if "lock" in e)
        self.lockdoor = {tuple(e["door"]): e["lock"] for e in (gr or {}).get("edges", []) if "lock" in e}
        self.keycell = {}
        for k in (gr or {}).get("keys", []):
            cx, cy = gr["cells"][k["node"]]
            self.keycell[(cx * P.CELL + P.CELL // 2, cy * P.CELL + P.CELL // 2)] = k["id"]
        self._cache = {}

    def _out(self, n):
        x, y = n
        res = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m = (x + dx, y + dy)
            if m in self.ok:
                r = self.rule.get(m)
                if r is not None and (-dx, -dy) != r:
                    continue
                res.append((m, 1.0))
        if self.moves == 8 and n not in self.doors:
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                m = (x + dx, y + dy)
                if m in self.ok and m not in self.doors and (x + dx, y) in self.ok and (x, y + dy) in self.ok:
                    res.append((m, SQ2))
        return res

    def est(self, n, goals):
        best = 1e300
        for gx, gy in goals:
            dx, dy = abs(n[0] - gx), abs(n[1] - gy)
            v = dx + dy if self.moves == 4 else max(dx, dy) + (SQ2 - 1.0) * min(dx, dy)
            best = min(best, v)
        return best

    def node(self, v):
        if len(v) != 2:
            raise ValueError("square maps take X,Y (column, row from the top-left, 0-based)")
        n = (int(v[0]), int(v[1]))
        if n not in self.ok:
            if getattr(self, "agent", 1) > 1:
                raise ValueError("%d,%d has no room for a %d-square body anchored at its top-left" % (n + (self.agent,)))
            raise ValueError("%d,%d is not a floor square" % n)
        return n

    def xy(self, n):
        return [n[0] + 0.5, n[1] + 0.5]

    def sxy(self, n):
        return ((n[0] + 0.5) * self.pps, (n[1] + 0.5) * self.pps)


def _cube(x, y):
    q = x - (y - (y & 1)) // 2
    return q, y, -q - y


class HexGraph(Graph):
    def __init__(self, gj, pps):
        self.kind = "hex"
        self.w, self.h, self.g, self.pps = gj["w"], gj["h"], gj["cells"], pps
        self.nodes = [(x, y) for y in range(self.h) for x in range(self.w) if self.g[y][x] in P.PASS]
        self.ok = set(self.nodes)
        self.centre = P.hex_geometry(self.w, self.h, pps)[0]
        self._cache = {}

    def _out(self, n):
        return [(m, 1.0) for m in P.nbrs_hex(*n) if m in self.ok]

    def est(self, n, goals):
        a = _cube(*n)
        best = 1e300
        for g in goals:
            b = _cube(*g)
            best = min(best, max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])))
        return float(best)

    def node(self, v):
        if len(v) != 2:
            raise ValueError("hex maps take X,Y (odd-r column, row)")
        n = (int(v[0]), int(v[1]))
        if n not in self.ok:
            raise ValueError("%d,%d is not an open hex" % n)
        return n

    def xy(self, n):
        return [n[0], n[1]]

    def sxy(self, n):
        return self.centre(*n)


class DeckGraph(Graph):
    units = "m"

    def __init__(self, dj, pps):
        self.kind = "deck"
        self.D = dj["decks"]
        self.nd, self.h, self.w = len(self.D), len(self.D[0]), len(self.D[0][0])
        self.pps = pps
        self.nodes = [(k, x, y) for k in range(self.nd) for y in range(self.h) for x in range(self.w)
                      if self.D[k][y][x] in DECK_PASS]
        self.ok = set(self.nodes)
        self._cache = {}

    def c(self, n):
        return self.D[n[0]][n[2]][n[1]]

    def _out(self, n):
        k, x, y = n
        res = []
        door = self.c(n) == "+"
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m = (k, x + dx, y + dy)
            if m in self.ok:
                res.append((m, DECK_SQ_M))
        if not door:
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                m = (k, x + dx, y + dy)
                if m in self.ok and self.c(m) != "+" and (k, x + dx, y) in self.ok and (k, x, y + dy) in self.ok:
                    res.append((m, DECK_SQ_M * SQ2))
        if self.c(n) == "L":
            for kk in (k - 1, k + 1):
                m = (kk, x, y)
                if m in self.ok and self.c(m) == "L":
                    res.append((m, LIFT_M))
        return res

    def est(self, n, goals):
        best = 1e300
        for g in goals:
            dx, dy = abs(n[1] - g[1]), abs(n[2] - g[2])
            best = min(best, DECK_SQ_M * (max(dx, dy) + (SQ2 - 1.0) * min(dx, dy)))
        return best

    def node(self, v):
        if len(v) == 2:
            v = (1,) + tuple(v)
        if len(v) != 3:
            raise ValueError("decks take X,Y (deck 1) or DECK,X,Y with DECK from 1")
        n = (int(v[0]) - 1, int(v[1]), int(v[2]))
        if n not in self.ok:
            raise ValueError("deck %d square %d,%d is not floor" % (n[0] + 1, n[1], n[2]))
        return n

    def xy(self, n):
        return [n[0] + 1, n[1] + 0.5, n[2] + 0.5]

    def sxy(self, n):
        ph = self.h * self.pps
        oy = 40 + n[0] * (ph + 34) + 14
        return (20 + (n[1] + 0.5) * self.pps, oy + (n[2] + 0.5) * self.pps)


class MeshGraph(Graph):
    """World or region mesh. cost='road' reuses the road router's step; cost='walk'/'offpath'/'horse' is Tobler
    time in hours."""
    directed = True

    def __init__(self, m, nb, thr, extent, cost="road"):
        self.kind = "mesh"
        self.m, self.nb = m, nb
        self.cost = cost
        self.units = "road cost (km x slope x terrain)" if cost == "road" else "hours"
        self.router = mpw_human.Router(m, nb, thr)
        ok = self.router.ok
        self.nodes = [i for i in range(len(m["x"])) if ok[i]]
        self.ok = set(self.nodes)
        self.x0, self.y0, x1, _ = extent
        self.s = 1000.0 / (x1 - self.x0)
        self._cache = {}

    def elev(self, i):
        return max(0.0, self.m["h"][i]) * mpw_human.ELEV_LAND

    def step(self, a, b):
        if self.cost == "road":
            return self.router.step(a, b)
        m = self.m
        d = math.hypot(m["x"][b] - m["x"][a], m["y"][b] - m["y"][a])
        s = (self.elev(b) - self.elev(a)) / (d * 1000.0) if d else 0.0
        return d / tobler_kmh(s, self.cost)

    def _out(self, n):
        return [(q, self.step(n, q)) for q in sorted(self.nb[n]) if q in self.ok]

    def est(self, n, goals):
        X, Y = self.m["x"], self.m["y"]
        best = min(math.hypot(X[n] - X[g], Y[n] - Y[g]) for g in goals)
        return best if self.cost == "road" else best / (6.0 * MODES[self.cost])

    def node(self, v):
        if len(v) != 2:
            raise ValueError("worlds and regions take X,Y in map km (y south)")
        X, Y = self.m["x"], self.m["y"]
        return min(self.nodes, key=lambda i: ((X[i] - v[0]) ** 2 + (Y[i] - v[1]) ** 2, i))

    def xy(self, n):
        return [round(self.m["x"][n], 6), round(self.m["y"][n], 6)]

    def sxy(self, n):
        return ((self.m["x"][n] - self.x0) * self.s, (self.m["y"][n] - self.y0) * self.s)


def erode(g, w, h, agent):
    """Squares where an agent `agent` squares wide may stand, anchored at its top-left square: the whole
    agent x agent block from (x, y) must be walkable. The anchor keeps its own character. agent 1 is a copy."""
    if agent <= 1:
        return [list(r) for r in g]
    out = [["#"] * w for _ in range(h)]
    for y in range(h - agent + 1):
        for x in range(w - agent + 1):
            if all(g[yy][xx] in P.PASS for yy in range(y, y + agent) for xx in range(x, x + agent)):
                out[y][x] = g[y][x]
    return out


def build(d, moves=8, cost="road", agent=1):
    rc = _load(d, "recipe.json")
    k = rc.get("kind")
    if agent < 1:
        raise ValueError("--agent is the body width in squares, 1 or more")
    if agent > 1 and not (k in ("dungeon", "battle") and _load(d, "grid.json")["grid"] == "square"):
        raise ValueError("--agent works on square dungeon and battle grids")
    if k in ("dungeon", "battle"):
        gj = _load(d, "grid.json")
        if gj["grid"] == "hex":
            return HexGraph(gj, rc["params"]["pps"]), rc
        if agent > 1:
            gj = dict(gj, cells=erode(gj["cells"], gj["w"], gj["h"], agent))
        G = SquareGraph(gj, rc["params"]["pps"], moves)
        G.agent = agent
        return G, rc
    if k == "deck":
        return DeckGraph(_load(d, "deck.json"), rc["params"].get("pps", 16)), rc
    if k in ("world", "region"):
        import mpw_gen
        m = _load(d, "mesh.json")
        return MeshGraph(m, mpw_gen._neighbours(m), rc["params"].get("river_threshold", 20), rc["extent"], cost), rc
    if k == "city":
        raise ValueError("a city has streets and lots, not a movement grid; path works on dungeon, battle, deck, "
                         "world and region recipes")
    raise ValueError("path does not know recipe kind %r" % k)


# ------------------------------------------------------------------ search
def search(G, src, goals, heuristic=True):
    """A* (or Dijkstra with heuristic=False) from src to the nearest of goals. Returns (cost, node list, expanded)
    or (None, None, expanded)."""
    goals = list(goals)
    gs = set(goals)
    dist = {src: 0.0}
    prev = {}
    closed = set()
    pq = [(G.est(src, goals) if heuristic else 0.0, 0.0, src)]
    while pq:
        _, gc, n = heapq.heappop(pq)
        if n in closed:
            continue
        closed.add(n)
        if n in gs:
            path = [n]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return gc, path[::-1], len(closed)
        for m, c in G.out(n):
            nd = gc + c
            if m not in closed and nd < dist.get(m, 1e300):
                dist[m] = nd
                prev[m] = n
                heapq.heappush(pq, (nd + (G.est(m, goals) if heuristic else 0.0), nd, m))
    return None, None, len(closed)


def lock_search(G, src, goal):
    """A* over (square, keys held) on a cyclic dungeon: a locked door is passed only with its key, a key is
    picked up on entering its square (the centre of its room's cell), one-way doors as in G.out.
    Returns (cost, squares, pickups, expanded); pickups are dicts key, cell index along the path."""
    gl = [goal]
    k0 = frozenset([G.keycell[src]]) if src in G.keycell else frozenset()
    s0 = (src, k0)
    dist = {s0: 0.0}
    prev = {}
    closed = set()
    pq = [(G.est(src, gl), 0.0, src, tuple(sorted(k0)))]
    while pq:
        _, gc, n, kt = heapq.heappop(pq)
        st = (n, frozenset(kt))
        if st in closed:
            continue
        closed.add(st)
        if n == goal:
            seq = [st]
            while seq[-1] in prev:
                seq.append(prev[seq[-1]])
            seq.reverse()
            picks = []
            held = set()
            for i, (c, ks) in enumerate(seq):
                for k in sorted(ks - held):
                    picks.append(dict(key=k, step=i))
                held |= ks
            return gc, [c for c, _ in seq], picks, len(closed)
        keys = st[1]
        for m, c in G.out(n):
            lk = G.lockdoor.get(m)
            if lk is not None and lk not in keys:
                continue
            km = G.keycell.get(m)
            nk = keys | {km} if km is not None else keys
            ns = (m, nk)
            nd = gc + c
            if ns not in closed and nd < dist.get(ns, 1e300):
                dist[ns] = nd
                prev[ns] = st
                heapq.heappush(pq, (nd + G.est(m, gl), nd, m, tuple(sorted(nk))))
    return None, None, [], len(closed)


def jps_refusal(G):
    """None when jump point search can run on G, else the reason it cannot."""
    if not isinstance(G, SquareGraph):
        return ("--jps needs a uniform-cost square grid (dungeon or square battle map); %s graphs have %s"
                % (G.kind, {"hex": "six neighbours per cell", "deck": "lifts between decks",
                            "mesh": "weighted, directed road or Tobler steps"}.get(G.kind, "other steps")))
    if G.moves != 8:
        return "--jps is for 8-way moves; with --moves 4 use plain A*"
    return None


def jps(G, src, goal):
    """Jump point search (Harabor and Grastien 2011) with the same moves as SquareGraph.out: 8-way, diagonals
    sqrt(2), no corner cutting. Doors break uniform cost (no diagonal through them, one-way entry), so any square
    within one step of a door is a jump point expanded with every move G.out gives. Returns
    (cost, squares, expanded) like search(); expanded counts jump points closed."""
    err = jps_refusal(G)
    if err:
        raise ValueError(err)
    ok = G.ok
    special = set()
    for x, y in G.doors:
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                special.add((x + ddx, y + ddy))

    def stop(c):
        return c == goal or c in special

    def straight(x, y, dx, dy):
        while True:
            if (x, y) not in ok:
                return None
            if stop((x, y)):
                return (x, y)
            if dx:
                if (((x, y - 1) in ok and (x - dx, y - 1) not in ok) or
                        ((x, y + 1) in ok and (x - dx, y + 1) not in ok)):
                    return (x, y)
            else:
                if (((x - 1, y) in ok and (x - 1, y - dy) not in ok) or
                        ((x + 1, y) in ok and (x + 1, y - dy) not in ok)):
                    return (x, y)
            x += dx
            y += dy

    def jump(x, y, dx, dy):
        if not (dx and dy):
            return straight(x, y, dx, dy)
        while True:
            if (x, y) not in ok:
                return None
            if stop((x, y)):
                return (x, y)
            if straight(x + dx, y, dx, 0) or straight(x, y + dy, 0, dy):
                return (x, y)
            if (x + dx, y) in ok and (x, y + dy) in ok:
                x += dx
                y += dy
            else:
                return None

    def nbrs(n, par):
        x, y = n
        if par is None or n in special:
            return [m for m, _ in G.out(n)]
        dx = (x > par[0]) - (x < par[0])
        dy = (y > par[1]) - (y < par[1])
        res = []
        if dx and dy:
            a, b = (x, y + dy) in ok, (x + dx, y) in ok
            if a:
                res.append((x, y + dy))
            if b:
                res.append((x + dx, y))
            if a and b and (x + dx, y + dy) in ok:
                res.append((x + dx, y + dy))
        elif dx:
            nx, up, dn = (x + dx, y) in ok, (x, y - 1) in ok, (x, y + 1) in ok
            if nx:
                res.append((x + dx, y))
                if up and (x + dx, y - 1) in ok:
                    res.append((x + dx, y - 1))
                if dn and (x + dx, y + 1) in ok:
                    res.append((x + dx, y + 1))
            if up:
                res.append((x, y - 1))
            if dn:
                res.append((x, y + 1))
        else:
            nx, lf, rt = (x, y + dy) in ok, (x - 1, y) in ok, (x + 1, y) in ok
            if nx:
                res.append((x, y + dy))
                if lf and (x - 1, y + dy) in ok:
                    res.append((x - 1, y + dy))
                if rt and (x + 1, y + dy) in ok:
                    res.append((x + 1, y + dy))
            if lf:
                res.append((x - 1, y))
            if rt:
                res.append((x + 1, y))
        return res

    gl = [goal]
    dist = {src: 0.0}
    prev = {}
    closed = set()
    pq = [(G.est(src, gl), 0.0, src)]
    while pq:
        _, gc, n = heapq.heappop(pq)
        if n in closed:
            continue
        closed.add(n)
        if n == goal:
            jp = [n]
            while jp[-1] in prev:
                jp.append(prev[jp[-1]])
            jp.reverse()
            path = [jp[0]]
            for a, b in zip(jp, jp[1:]):
                sx, sy = (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])
                c = a
                while c != b:
                    c = (c[0] + sx, c[1] + sy)
                    path.append(c)
            return gc, path, len(closed)
        for m in nbrs(n, prev.get(n)):
            dx, dy = m[0] - n[0], m[1] - n[1]
            j = jump(m[0], m[1], dx, dy)
            if j is None or j in closed:
                continue
            k = max(abs(j[0] - n[0]), abs(j[1] - n[1]))
            nd = gc + k * (SQ2 if dx and dy else 1.0)
            if nd < dist.get(j, 1e300):
                dist[j] = nd
                prev[j] = n
                heapq.heappush(pq, (nd + G.est(j, gl), nd, j))
    return None, None, len(closed)


def dijkstra(adj_fn, sources):
    """Single or multi-source Dijkstra over adj_fn(n) -> [(m, c)]. Returns (dist, prev)."""
    dist = {s: 0.0 for s in sources}
    prev = {}
    pq = [(0.0, s) for s in sorted(sources)]
    heapq.heapify(pq)
    done = set()
    while pq:
        dn, n = heapq.heappop(pq)
        if n in done:
            continue
        done.add(n)
        for m, c in adj_fn(n):
            nd = dn + c
            if nd < dist.get(m, 1e300):
                dist[m] = nd
                prev[m] = n
                heapq.heappush(pq, (nd, m))
    return dist, prev


def resum(G, path):
    """Re-sum a path's cost from its steps; raises if a step is not an edge."""
    tot = 0.0
    for a, b in zip(path, path[1:]):
        cs = [c for m, c in G.out(a) if m == b]
        if not cs:
            raise ValueError("step %r -> %r is not an edge" % (a, b))
        tot += cs[0]
    return tot


def field(G, goals):
    """Cost-to-goal for every node (Dijkstra on the reversed graph from all goals) and the flow step per node."""
    rev = G.reverse()
    dist, _ = dijkstra(lambda n: rev[n], list(goals))
    gs = set(goals)
    flow = {}
    for n in G.nodes:
        if n in dist and n not in gs:
            best = None
            for m, c in G.out(n):
                if m in dist:
                    v = c + dist[m]
                    if best is None or v < best[0] - 1e-12:
                        best = (v, m)
            flow[n] = best[1]
    return dist, flow


# ------------------------------------------------------------------ chokepoints
def articulation(adj):
    """Articulation points and bridges of an undirected graph (iterative Hopcroft-Tarjan)."""
    disc, low = {}, {}
    aps, bridges = set(), []
    t = 0
    for root in sorted(adj):
        if root in disc:
            continue
        disc[root] = low[root] = t
        t += 1
        kids = 0
        stack = [(root, None, iter(adj[root]))]
        while stack:
            n, par, it = stack[-1]
            adv = False
            for m in it:
                if m == par:
                    continue
                if m in disc:
                    low[n] = min(low[n], disc[m])
                else:
                    disc[m] = low[m] = t
                    t += 1
                    if n == root:
                        kids += 1
                    stack.append((m, n, iter(adj[m])))
                    adv = True
                    break
            if adv:
                continue
            stack.pop()
            if par is not None:
                low[par] = min(low[par], low[n])
                if low[n] > disc[par]:
                    bridges.append(tuple(sorted((par, n))))
                if par != root and low[n] >= disc[par]:
                    aps.add(par)
        if kids > 1:
            aps.add(root)
    return sorted(aps), sorted(bridges)


def components(adj, removed=frozenset()):
    seen = set()
    comps = []
    for s in sorted(adj):
        if s in seen or s in removed:
            continue
        comp = [s]
        seen.add(s)
        i = 0
        while i < len(comp):
            for m in adj[comp[i]]:
                if m not in seen and m not in removed:
                    seen.add(m)
                    comp.append(m)
            i += 1
        comps.append(comp)
    return comps


def brute_articulation(adj):
    base = len(components(adj))
    return sorted(n for n in adj if len(components(adj, frozenset([n]))) > base)


def min_vertex_cut(adj, s, t):
    """Smallest set of cells (not s or t) whose removal separates s from t: unit-capacity max flow with split
    nodes. Returns (size, cells) or (None, []) when s and t are neighbours."""
    if t in adj[s]:
        return None, []
    INF = 10 ** 9
    cap = {}
    g = {}

    def add(u, v, c):
        g.setdefault(u, []).append(v)
        g.setdefault(v, []).append(u)
        cap[(u, v)] = cap.get((u, v), 0) + c
        cap.setdefault((v, u), 0)
    for n in adj:
        add((n, 0), (n, 1), INF if n in (s, t) else 1)
        for m in adj[n]:
            add((n, 1), (m, 0), INF)
    src, snk = (s, 0), (t, 1)
    flow = 0
    while True:
        par = {src: None}
        q = [src]
        i = 0
        while i < len(q) and snk not in par:
            u = q[i]
            i += 1
            for v in g[u]:
                if v not in par and cap[(u, v)] > 0:
                    par[v] = u
                    q.append(v)
        if snk not in par:
            break
        v = snk
        while par[v] is not None:
            u = par[v]
            cap[(u, v)] -= 1
            cap[(v, u)] += 1
            v = u
        flow += 1
        if flow > 64:
            break
    cut = sorted(n for n in adj if (n, 0) in par and (n, 1) not in par)
    return flow, cut


def chokepoints(G, rooms=(), ref=None, goal=None, brute_limit=1500):
    adj = G.undirected_adj()
    aps, bridges = articulation(adj)
    comps = components(adj)
    main = max(comps, key=len) if comps else []
    ref = ref if ref in adj else (min(main) if main else None)
    total = len(adj)
    rows = []
    for a in aps:
        own = set(next(c for c in comps if a in c))
        pieces = [c for c in components(adj, frozenset([a])) if c[0] in own]
        base = next((c for c in pieces if ref in c), None) if ref in own and a != ref else None
        base = base or max(pieces, key=len)
        rs = set(base)
        lost = [r["id"] + 1 for r in rooms
                if not any((x, y) in rs for x in range(r["x"], r["x"] + r["w"]) for y in range(r["y"], r["y"] + r["h"]))]
        rows.append(dict(cell=G.xy(a), cut_off=len(own) - 1 - len(base), rooms_cut_off=lost))
    rep = dict(passable=total, components=len(comps), chokepoints=rows, bridges=len(bridges))
    if ref is not None and goal is not None and goal in adj:
        k, cut = min_vertex_cut(adj, ref, goal)
        rep["min_cut"] = dict(size=k, cells=[G.xy(c) for c in cut])
    if total <= brute_limit:
        rep["brute_force_equal"] = brute_articulation(adj) == aps
    return rep


# ------------------------------------------------------------------ fairness
def fair(G, starts, resources):
    dists = [dijkstra(G.out, [s])[0] for s in starts]
    area = [0] * len(starts)
    tie = unreached = 0
    for n in G.nodes:
        vals = [dd.get(n) for dd in dists]
        got = [v for v in vals if v is not None]
        if not got:
            unreached += 1
            continue
        lo = min(got)
        win = [i for i, v in enumerate(vals) if v is not None and abs(v - lo) <= 1e-9]
        if len(win) > 1:
            tie += 1
        else:
            area[win[0]] += 1
    res_rows = []
    first = [0] * len(starts)
    for r in resources:
        ds = [dd.get(r) for dd in dists]
        got = [v for v in ds if v is not None]
        winner = None
        if got:
            lo = min(got)
            w = [i for i, v in enumerate(ds) if v is not None and abs(v - lo) <= 1e-9]
            if len(w) == 1:
                winner = w[0]
                first[winner] += 1
        res_rows.append(dict(cell=G.xy(r), dist=[None if v is None else round(v, 9) for v in ds],
                             first=None if winner is None else winner + 1))
    pos = [a for a in area if a]
    return dict(starts=[G.xy(s) for s in starts], areas=area, tied=tie, unreached=unreached,
                passable=len(G.nodes), area_ratio=round(max(area) / min(area), 6) if len(pos) == len(area) else None,
                resources=res_rows, resources_first=first)


# ------------------------------------------------------------------ output
def _svg_overlay(d, out_name, body):
    src = os.path.join(d, "map.svg")
    with open(src, encoding="utf-8") as f:
        svg = f.read()
    i = svg.rstrip().rfind("</svg>")
    svg = svg[:i] + body + "\n</svg>\n"
    return svg


def write(out, name, obj):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, indent=1, sort_keys=True)
            f.write("\n")


def path_files(d, out, G, src, dst, cost, path, expanded, extra=None):
    coords = [G.xy(n) for n in path]
    rep = dict(kind=G.kind, units=G.units, directed=G.directed, start=G.xy(src), goal=G.xy(dst),
               cost=round(cost, 9), steps=len(path) - 1, expanded=expanded, path=coords)
    rep.update(extra or {})
    write(out, "path.json", rep)
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": dict(kind="path", cost=rep["cost"], units=G.units),
         "geometry": {"type": "LineString", "coordinates": [c[-2:] for c in coords]}}]}
    if G.kind == "deck":
        gj["features"][0]["properties"]["decks"] = [c[0] for c in coords]
    write(out, "path.geojson", gj)
    pts = " ".join("%.1f,%.1f" % G.sxy(n) for n in path)
    a, b = G.sxy(src), G.sxy(dst)
    body = ('<g class="path"><polyline points="%s" fill="none" stroke="#e8352b" stroke-width="3" '
            'stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>'
            '<circle cx="%.1f" cy="%.1f" r="6" fill="#2b9e4a"/><circle cx="%.1f" cy="%.1f" r="6" fill="#e8352b"/></g>'
            % (pts, a[0], a[1], b[0], b[1]))
    write(out, "path.svg", _svg_overlay(d, "path.svg", body))
    return rep


def heat_svg(d, G, vals, r=None, bands=8):
    got = [v for v in vals.values() if v is not None]
    mx = max(got) if got else 1.0
    o = ['<g class="heat" opacity="0.6">']
    rr = r or max(2.0, getattr(G, "pps", 8) * 0.45)
    for n in G.nodes:
        v = vals.get(n)
        if v is None:
            continue
        t = min(bands - 1, int(bands * v / (mx or 1.0)))
        hue = int(240 * (1 - t / (bands - 1)))
        x, y = G.sxy(n)
        o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="hsl(%d,85%%,50%%)"/>' % (x, y, rr, hue))
    o.append("</g>")
    return _svg_overlay(d, "", "\n".join(o))


def field_files(d, out, G, goals, dist, flow, name="field"):
    rows = []
    for n in G.nodes:
        v = dist.get(n)
        rows.append(dict(cell=G.xy(n), value=None if v is None else round(v, 9),
                         next=G.xy(flow[n]) if n in flow else None))
    rep = dict(kind=G.kind, units=G.units, goals=[G.xy(g) for g in goals], reachable=len(dist),
               unreachable=len(G.nodes) - len(dist), max=round(max(dist.values()), 9), cells=rows)
    write(out, name + ".json", rep)
    write(out, name + ".svg", heat_svg(d, G, dist, r=3.0 if G.kind == "mesh" else None))
    return rep


# ------------------------------------------------------------------ travel
def travel(d, out, G, src, band=6.0, goal=None):
    """Travel time in hours from src over a Tobler-cost mesh graph; travel.json, travel.svg."""
    dist, prev = dijkstra(G.out, [src])
    bands = {}
    for v in dist.values():
        k = int(v // band)
        bands[k] = bands.get(k, 0) + 1
    rows = [dict(cell=G.xy(n), hours=None if n not in dist else round(dist[n], 9)) for n in G.nodes]
    rep = dict(kind="travel", mode=G.cost, units="hours", start=G.xy(src), reachable=len(dist),
               unreachable=len(G.nodes) - len(dist), max_hours=round(max(dist.values()), 9), band_hours=band,
               bands=[bands.get(k, 0) for k in range(max(bands) + 1)], cells=rows)
    if goal is not None:
        if goal in dist:
            p = [goal]
            while p[-1] in prev:
                p.append(prev[p[-1]])
            rep["to"] = dict(goal=G.xy(goal), hours=round(dist[goal], 9), path=[G.xy(n) for n in p[::-1]])
        else:
            rep["to"] = dict(goal=G.xy(goal), hours=None, path=[])
    write(out, "travel.json", rep)
    write(out, "travel.svg", heat_svg(d, G, dist, r=3.0, bands=max(2, len(rep["bands"]))))
    return rep
