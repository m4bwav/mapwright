"""Design lint for a recipe's optional room plan: warnings, never proof bars.

A recipe may carry a "plan" object. Old recipes without one lint clean with a note.

plan = {
  "rooms": [{"id": "r1", "name": "Gate Hall", "role": "entrance", "kind": "taproom",
             "danger": 2, "empty": false, "combat": true, "terrain": ["pillars"],
             "level": 0, "main": true, "entrance": true, "exit": true, "treasure": false,
             "stairs": false, "staffed": false, "public": true, "door": "front", "area": 48}],
  "links": [["r1", "r2"], {"a": "r2", "b": "r3", "length": 4, "hazard": 2, "cue": "smoke above the trees"}],
  "goal": "r5",
  "landmarks": ["Old Well", "Gate Hall"],
  "factions": [{"name": "kobolds", "eats": "cave fish", "tolerates": "the goblins pay them in iron"}]
}

Rooms may also carry "hook" (why an empty room is worth a look) and "vertical" (true or a note).
A city plan may use rooms as districts: "kind" (market, gate, dock, main-road, residential...) and
"tags" (["nuisance"], ["residential"]); a link then means two districts border each other.

Every field is optional. A room's area falls back to grid.json rooms (w * h) when the id matches.
Checks, each grouped by family:
  layout   - one entrance only; danger not rising with distance from the main entrance; fewer than
             2 links between adjacent levels; empty share outside 15-50%; combat room with no terrain;
             a climax room with fewer than 2 links (no retreat); a level with no vertical feature;
             an empty room with no hook
  routes   - two links joining the same pair of rooms with the same length and hazard (no trade-off);
             a hub (3+ neighbours) with a link that has no "cue", checked only once any link has a cue
  districts- a nuisance district bordering a residential one; a market with no link to a gate, dock
             or main road (kind or tag)
  factions - every plan faction names what it eats and why it tolerates its neighbours
  roles    - five-room roles in path order on the entrance-to-goal path, exactly one climax,
             a setback on that path
  tavern   - taproom the largest public room, kitchen next to the taproom, a front and a rear door,
             vault next to a staffed room, no stairs in a drinking room
  landmarks- every listed landmark found among plan room names, names.json and feature names
  escape   - path length from each treasure room to the nearest exit (a report line, not a warning)
"""
import heapq
import json
import os

ROLE_ORDER = ("entrance", "puzzle", "setback", "climax", "reward")
TAVERN_KINDS = {"taproom", "kitchen", "vault", "cellar", "bar", "snug", "private-dining", "guest-room",
                "stable", "office", "staff", "storeroom", "common-room"}
PUBLIC_KINDS = {"taproom", "bar", "snug", "private-dining", "common-room", "dining"}
DRINKING_KINDS = {"taproom", "bar", "snug"}
STAFFED_KINDS = {"kitchen", "bar", "office", "staff", "taproom"}
EMPTY_LOW, EMPTY_HIGH = 0.15, 0.50
VERTICAL_TERRAIN = {"ledge", "balcony", "pit", "shaft", "stairs", "ladder", "chasm", "gallery", "mezzanine"}


def _load(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class Plan:
    def __init__(self, plan, grid=None):
        self.rooms = {}
        for i, r in enumerate(plan.get("rooms") or []):
            r = dict(r)
            r.setdefault("id", i)
            self.rooms[r["id"]] = r
        if grid:
            for g in grid.get("rooms") or []:
                r = self.rooms.get(g.get("id"))
                if r is not None and "area" not in r and "w" in g and "h" in g:
                    r["area"] = g["w"] * g["h"]
        self.adj = {k: {} for k in self.rooms}
        self.links = []
        self.link_attrs = []
        for l in plan.get("links") or []:
            if isinstance(l, dict):
                a, b, w = l.get("a"), l.get("b"), float(l.get("length", 1))
            else:
                a, b = l[0], l[1]
                w = float(l[2]) if len(l) > 2 else 1.0
            if a not in self.rooms or b not in self.rooms:
                raise ValueError("plan link names an unknown room: %r - %r" % (a, b))
            self.links.append((a, b, w))
            self.link_attrs.append((a, b, l if isinstance(l, dict) else {"length": w}))
            for x, y in ((a, b), (b, a)):
                if y not in self.adj[x] or w < self.adj[x][y]:
                    self.adj[x][y] = w
        self.goal = plan.get("goal")
        self.landmarks = list(plan.get("landmarks") or [])

    def dist(self, src):
        d = {src: 0.0}
        prev = {}
        q = [(0.0, str(src), src)]
        while q:
            du, _, u = heapq.heappop(q)
            if du > d.get(u, float("inf")):
                continue
            for v, w in self.adj[u].items():
                if du + w < d.get(v, float("inf")):
                    d[v] = du + w
                    prev[v] = u
                    heapq.heappush(q, (du + w, str(v), v))
        return d, prev

    def path(self, a, b):
        d, prev = self.dist(a)
        if b not in d:
            return None
        out = [b]
        while out[-1] != a:
            out.append(prev[out[-1]])
        return out[::-1]

    def entrances(self):
        return [k for k, r in self.rooms.items() if r.get("entrance") or r.get("role") == "entrance"]

    def main_entrance(self):
        mains = [k for k, r in self.rooms.items() if r.get("main")]
        if mains:
            return mains[0]
        ents = self.entrances()
        return ents[0] if ents else None


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / (sxx * syy) ** 0.5


def lint_layout(p):
    w, info = [], []
    ents = p.entrances()
    if len(ents) == 1:
        w.append("only one entrance (%s): add a second way in so the party can choose" % ents[0])
    main = p.main_entrance()
    if main is not None and p.links:
        d, _ = p.dist(main)
        pts = [(d[k], float(r["danger"])) for k, r in p.rooms.items() if "danger" in r and k in d]
        if len(pts) >= 3:
            c = _pearson([a for a, _ in pts], [b for _, b in pts])
            info.append("danger vs distance from %s: r = %.2f" % (main, c))
            if c <= 0:
                w.append("danger does not rise with distance from the main entrance (r = %.2f)" % c)
    levels = sorted({r["level"] for r in p.rooms.values() if "level" in r})
    for lo, hi in zip(levels, levels[1:]):
        n = sum(1 for a, b, _ in p.links
                if {p.rooms[a].get("level"), p.rooms[b].get("level")} == {lo, hi})
        if n < 2:
            w.append("%d route(s) between level %s and level %s: fewer than 2" % (n, lo, hi))
    marked = [r for r in p.rooms.values() if "empty" in r]
    if marked:
        share = sum(1 for r in marked if r["empty"]) / len(marked)
        info.append("empty rooms: %.0f%%" % (share * 100))
        if not EMPTY_LOW <= share <= EMPTY_HIGH:
            w.append("empty rooms are %.0f%% of rooms, outside 15-50%%" % (share * 100))
    for k, r in p.rooms.items():
        if r.get("combat") and not r.get("terrain"):
            w.append("combat room %s has no terrain feature (cover, height, hazard)" % k)
    for k, r in p.rooms.items():
        if r.get("role") == "climax" and len(p.adj[k]) < 2:
            w.append("climax room %s has %d link(s): a dead end leaves no retreat" % (k, len(p.adj[k])))
        if r.get("empty") and not r.get("hook"):
            w.append("empty room %s has no hook (something to notice, use or wonder about)" % k)
    by_level = {}
    for r in p.rooms.values():
        if "level" in r:
            by_level.setdefault(r["level"], []).append(r)
    for lv in sorted(by_level, key=str):
        if not any(_vertical(r) for r in by_level[lv]):
            w.append("level %s has no room with a vertical feature (ledge, balcony, pit, shaft, stairs)" % lv)
    return w, info


def _vertical(r):
    if r.get("vertical") or r.get("stairs"):
        return True
    return any(str(t).casefold() in VERTICAL_TERRAIN for t in (r.get("terrain") or []))


def lint_factions(factions):
    w = []
    for i, f in enumerate(factions or []):
        name = f.get("name", "#%d" % i) if isinstance(f, dict) else str(f)
        f = f if isinstance(f, dict) else {}
        for key, why in (("eats", "what it eats"), ("tolerates", "why it tolerates its neighbours")):
            if not f.get(key):
                w.append("faction %s has no %s: say %s" % (name, key, why))
    return w, []


def lint_routes(p):
    w = []
    seen = {}
    for a, b, at in p.link_attrs:
        key = frozenset((a, b))
        sig = (float(at.get("length", 1)), at.get("hazard", 0) or 0)
        for other in seen.get(key, []):
            if other == sig:
                w.append("rooms %s and %s are joined by two routes with the same length and hazard: "
                         "give one a trade-off (shorter but riskier)" % (a, b))
                break
        seen.setdefault(key, []).append(sig)
    if any(at.get("cue") for _, _, at in p.link_attrs):
        for k in p.rooms:
            if len(p.adj[k]) < 3:
                continue
            for a, b, at in p.link_attrs:
                if k in (a, b) and not at.get("cue"):
                    w.append("hub %s: link to %s has no cue the players can see" % (k, b if a == k else a))
    return w, []


def _dtags(r):
    return {str(t).casefold() for t in (r.get("tags") or [])} | {str(r.get("kind", "")).casefold()}


def lint_districts(p):
    w = []
    for k, r in p.rooms.items():
        t = _dtags(r)
        if "nuisance" in t:
            for n in p.adj[k]:
                if "residential" in _dtags(p.rooms[n]):
                    w.append("nuisance district %s borders residential district %s" % (k, n))
        if "market" in t and not any(_dtags(p.rooms[n]) & {"gate", "dock", "main-road"} for n in p.adj[k]):
            w.append("market %s has no link to a gate, dock or main road" % k)
    return w, []


def lint_roles(p):
    w, info = [], []
    roles = {k: r["role"] for k, r in p.rooms.items() if r.get("role")}
    if not roles:
        return w, info
    bad = sorted({v for v in roles.values() if v not in ROLE_ORDER})
    if bad:
        w.append("unknown role(s): %s (use %s)" % (", ".join(bad), ", ".join(ROLE_ORDER)))
    climaxes = [k for k, v in roles.items() if v == "climax"]
    if len(climaxes) != 1:
        w.append("%d climax rooms: want exactly one" % len(climaxes))
    start = next((k for k, v in roles.items() if v == "entrance"), p.main_entrance())
    goal = p.goal
    if goal is None:
        goal = next((k for k, v in roles.items() if v == "reward"), climaxes[0] if climaxes else None)
    if start is None or goal is None:
        w.append("roles need an entrance and a goal (reward, climax or plan.goal) to check path order")
        return w, info
    path = p.path(start, goal)
    if path is None:
        w.append("no path from %s to the goal %s" % (start, goal))
        return w, info
    info.append("critical path: " + " > ".join(str(k) for k in path))
    seq = [(k, roles[k]) for k in path if roles.get(k) in ROLE_ORDER]
    for (k1, r1), (k2, r2) in zip(seq, seq[1:]):
        if ROLE_ORDER.index(r2) < ROLE_ORDER.index(r1):
            w.append("role order broken on the path: %s (%s) comes before %s (%s)" % (k1, r1, k2, r2))
    if not any(roles.get(k) == "setback" for k in path):
        w.append("no setback room on the entrance-to-goal path")
    return w, info


def lint_tavern(p):
    w, info = [], []
    kinds = {k: r.get("kind") for k, r in p.rooms.items()}
    if not any(v in TAVERN_KINDS for v in kinds.values()):
        return w, info
    taps = [k for k, v in kinds.items() if v == "taproom"]
    if not taps:
        w.append("no taproom")
    else:
        tap = max(taps, key=lambda k: p.rooms[k].get("area", 0))
        public = [k for k, r in p.rooms.items() if r.get("public") or kinds[k] in PUBLIC_KINDS]
        if all("area" in p.rooms[k] for k in public):
            big = max(public, key=lambda k: p.rooms[k]["area"])
            if big != tap and p.rooms[big]["area"] >= p.rooms[tap]["area"]:
                w.append("taproom %s is not the largest public room (%s is)" % (tap, big))
        else:
            info.append("some public rooms have no area; taproom size not checked")
        kitchens = [k for k, v in kinds.items() if v == "kitchen"]
        if not kitchens:
            w.append("no kitchen")
        elif not any(kt in p.adj[t] for kt in kitchens for t in taps):
            w.append("kitchen is not next to the taproom")
    doors = {r.get("door") for r in p.rooms.values()}
    for side in ("front", "rear"):
        if side not in doors:
            w.append("no %s door" % side)
    for k, v in kinds.items():
        if v == "vault":
            staffed = [n for n in p.adj[k] if p.rooms[n].get("staffed") or kinds[n] in STAFFED_KINDS]
            if not staffed:
                w.append("vault %s is not next to a staffed room" % k)
        if (v in DRINKING_KINDS) and p.rooms[k].get("stairs"):
            w.append("stairs in drinking room %s" % k)
    return w, info


def map_names(d, p):
    names = {str(r["name"]) for r in p.rooms.values() if r.get("name")}
    n = _load(d, "names.json") or {}
    for e in n.get("names") or []:
        if e.get("name"):
            names.add(str(e["name"]))
    fg = _load(d, "features.geojson") or {}
    for f in fg.get("features") or []:
        nm = (f.get("properties") or {}).get("name")
        if nm:
            names.add(str(nm))
    rc = _load(d, "recipe.json") or {}
    if rc.get("name"):
        names.add(str(rc["name"]))
    return names


def lint_landmarks(d, p, extra=()):
    want = list(p.landmarks) + list(extra)
    if not want:
        return [], []
    have = {n.casefold() for n in map_names(d, p)}
    missing = [n for n in want if n.casefold() not in have]
    w = ["landmark not on the map: %s" % n for n in missing]
    return w, ["landmarks found: %d of %d" % (len(want) - len(missing), len(want))]


def escape_report(p):
    exits = [k for k, r in p.rooms.items() if r.get("exit") or r.get("entrance") or r.get("role") == "entrance"]
    out = []
    for k, r in p.rooms.items():
        if not r.get("treasure"):
            continue
        d, _ = p.dist(k)
        reach = [(d[e], e) for e in exits if e in d]
        if reach:
            best = min(reach)
            out.append(dict(treasure=k, exit=best[1], distance=best[0]))
        else:
            out.append(dict(treasure=k, exit=None, distance=None))
    return out


def lint(d, landmarks=()):
    rc = _load(d, "recipe.json")
    if rc is None:
        raise ValueError("no recipe.json in " + d)
    plan = rc.get("plan")
    if not plan:
        res = dict(warnings=[], info=["recipe has no plan: nothing to lint"], escape=[])
        if landmarks:
            w, i = lint_landmarks(d, Plan({}), landmarks)
            res["warnings"] += [dict(check="landmarks", text=t) for t in w]
            res["info"] += i
        return res
    p = Plan(plan, _load(d, "grid.json"))
    res = dict(warnings=[], info=[], escape=escape_report(p))
    for name, (w, i) in (("layout", lint_layout(p)), ("roles", lint_roles(p)),
                         ("tavern", lint_tavern(p)), ("landmarks", lint_landmarks(d, p, landmarks)),
                         ("factions", lint_factions(plan.get("factions"))),
                         ("routes", lint_routes(p)), ("districts", lint_districts(p))):
        res["warnings"] += [dict(check=name, text=t) for t in w]
        res["info"] += i
    return res
