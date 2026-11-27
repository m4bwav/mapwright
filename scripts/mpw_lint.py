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
  supply   - opt-in with plan "supply" = {"weights": {"road": 1, "settled": 2, "wild": 3, "desert": 5,
             "river": 1}, "bases": ["h1"], "max": 10, "daily_hex": 6, "ratio": 4}; rooms are hexes with
             "ground" (a weights key) and "army": true. Warns on a hex whose ground has no weight, an army
             with no supply line to a base, and a line costing more than "max"; reports each line's cost
             and path. With "daily_hex" (width of a daily-march hex) it reports the weekly hex width,
             "ratio" (default 4) daily hexes across. The weights are yours: no numbers ship as defaults.
  layers   - opt-in with plan "layers" = {"order": ["outer", "middle", "core"], "arrival": "outer"};
             rooms carry "layer". Warns when arrival is not the first (outer) layer, and when a deeper
             layer has no link to a shallower layer tagged portal or guarded (link "portal": true,
             "guarded": true, or "tags": ["portal"]).
  terrain  - a terrain entry {"name": .., "special": true, "cost": .., "boon": ..} in a room's
             "terrain" list or in plan "terrain" must give both a cost and a boon.
  lair     - opt-in with plan "lair" = {"owner": "huge" or squares across, "hoard": squares};
             entrance rooms may give "opening" (squares across). Warns on fewer than 2 entrances,
             on no entrance narrower than the owner (a gap the owner cannot use), and on a treasure
             room smaller than the hoard footprint; reports each treasure room's area vs the hoard.
             Also warns when no room or link has a "home_hazard" {"gate": "weight" or "size",
             "limit": ..} (squares residents pass freely) and no link is "resident_only" (a secret
             route for those who live there). Book of Lairs pp. 4-5, 8 idea.
  traps    - a room "trap" {"trigger": [cells], "effect": [cells], "bypass": ..} needs both areas;
             a room with "lockdown": true needs "door" on every link it has; plan "owner_route"
             (room ids) warns on a trap room along it with no "bypass". 20 New Traps pp. 2-8 idea.
  base     - opt-in with plan "base" = {"shifts": {"day": {room id: duty}, ..}}: warns on a shift
             naming an unknown room, a floor ("floor" on rooms) left unstaffed in a shift, and a
             door or window link ("kind") with no "break" value. Adventurers Guild pp. 3, 41 idea.
  locks    - opt-in with plan "locks" = [{"at": room id or link "id", "key": "red stone",
             "key_in": room id or "wander", "kind": "key" | "word" | "toll", "oneway": true,
             "drop_from": "foe"}]. Warns when the key_in room cannot be reached from any entrance with
             that lock closed (softlock), when 2+ keys all sit in one room, when a toll lock is not
             marked "oneway" (on the lock or its link), and when a wander key has no "drop_from" foe.
             Rooms may carry "decoy": true; a decoy with no "secret" room or secret link within 2
             rooms warns.
  factions - every plan faction names what it eats and why it tolerates its neighbours
  roles    - five-room roles in path order on the entrance-to-goal path, exactly one climax,
             a setback on that path
  tavern   - taproom the largest public room, kitchen next to the taproom, a front and a rear door,
             vault next to a staffed room, no stairs in a drinking room
  hostile  - opt-in with plan "hostile": true. A room with "lethal": true needs a "warning" (the cue
             players can read first); a gate room (kind or tag "gate") needs a neighbour that is a
             "baffle" (flag, kind or tag: a wall behind the gate); the goal room needs a "decoy"
             neighbour.
  doom     - opt-in with plan "doom" = {"track": [room ids], "circle": true}. Each step must be a room,
             each step linked to the next, the last back to the first when "circle" (default true),
             and at least 3 steps. Reports the track as a path to draw on the map.
  questions- report lines: an open question for each locked door ("locked"), pit (terrain or kind),
             secret room or link, and the goal (centre) that has no "answer" yet.
  omens    - opt-in with plan "omens" = {"crypt": ["cold draft", ..]}: warns on a room kind with no
             omens listed.
  portals  - a link with "oneway": true that is a portal or shift ("portal", "shift" or tag) needs a
             way back from its far side ("b"): a "return" on that room, or a path to "a" without it.
  cue      - rooms may carry "cue": 0-5 (threat the players can sense). Warns on a value outside 0-5
             and when the cue drops between two cued rooms on the entrance-to-goal path.
  signal   - opt-in with plan "signal" = {"keep": room id, "range": sight distance, "routes": [[room ids
             from the map edge toward the keep], ..], "ridges": [{"x":, "y":, "elev":}]}. Rooms with
             "outpost": true carry "x", "y" and "elev". Two posts (or a post and the keep) see each other
             when within range and no ridge point near the line stands above it. Warns on an approach
             route with no outpost on it, and on an outpost whose signal cannot reach the keep; reports
             the hops. Any room with "fire_load": "high" needs "secret_exit": true or a secret link.
             A room with "under": another room id is reported as hard to retrofit.
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


def hex_scale(daily_hex, ratio=4):
    """Nested hex scales: a weekly hex `ratio` daily-march hexes across, ~ratio**2 of them inside."""
    daily_hex, ratio = float(daily_hex), int(ratio)
    if daily_hex <= 0 or ratio < 2:
        raise ValueError("daily_hex must be > 0 and ratio >= 2")
    return dict(daily_hex=daily_hex, weekly_hex=daily_hex * ratio, ratio=ratio, daily_per_weekly=ratio * ratio)


def lint_supply(p, sup):
    if not sup:
        return [], []
    w, info = [], []
    if sup.get("daily_hex"):
        s = hex_scale(sup["daily_hex"], sup.get("ratio", 4))
        info.append("hex scale: daily hex %g, weekly hex %g (%d across, about %d daily hexes inside)"
                    % (s["daily_hex"], s["weekly_hex"], s["ratio"], s["daily_per_weekly"]))
    weights = {str(k).casefold(): float(v) for k, v in (sup.get("weights") or {}).items()}
    if not weights:
        return w + ["supply has no weights: give each ground type (road, settled, wild, desert, river) a cost"], info
    cost = {}
    for k, r in p.rooms.items():
        g = str(r.get("ground", "")).casefold()
        if g not in weights:
            w.append("hex %s ground %r has no supply weight" % (k, r.get("ground")))
        else:
            cost[k] = weights[g]
    bases = [b for b in (sup.get("bases") or []) if b in p.rooms]
    if not bases:
        return w + ["supply has no base among the plan hexes"], info
    best, prev = {}, {}
    q = []
    for b in bases:
        best[b] = 0.0
        heapq.heappush(q, (0.0, str(b), b))
    while q:
        du, _, u = heapq.heappop(q)
        if du > best.get(u, float("inf")):
            continue
        for v in p.adj[u]:
            if v not in cost:
                continue
            nd = du + cost[v]
            if nd < best.get(v, float("inf")):
                best[v], prev[v] = nd, u
                heapq.heappush(q, (nd, str(v), v))
    mx = sup.get("max")
    for k, r in p.rooms.items():
        if not r.get("army"):
            continue
        if k not in best:
            w.append("army at %s has no supply line to a base" % k)
            continue
        path = [k]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        info.append("supply line %s: cost %g via %s" % (k, best[k], " > ".join(str(x) for x in path[::-1])))
        if mx is not None and best[k] > float(mx):
            w.append("army at %s: supply line costs %g, over the max %g" % (k, best[k], float(mx)))
    return w, info


def _tagged(at, *names):
    tags = {str(t).casefold() for t in (at.get("tags") or [])} | {str(at.get("kind", "")).casefold()}
    return any(at.get(n) or n in tags for n in names)


def lint_layers(p, layers):
    if not layers:
        return [], []
    order = list(layers.get("order") or [])
    if not order:
        return ["layers has no order: list the layers from outer to deepest"], []
    w = []
    arrival = layers.get("arrival")
    if arrival is None:
        w.append("layers has no arrival layer")
    elif arrival != order[0]:
        w.append("arrival layer %s is not the outer layer %s: travellers should land on the outside"
                 % (arrival, order[0]))
    depth = {name: i for i, name in enumerate(order)}
    for i, name in enumerate(order[1:], 1):
        ok = False
        for a, b, at in p.link_attrs:
            la, lb = depth.get(p.rooms[a].get("layer")), depth.get(p.rooms[b].get("layer"))
            if la is None or lb is None or i not in (la, lb) or min(la, lb) >= i:
                continue
            if _tagged(at, "portal", "guarded"):
                ok = True
                break
        if not ok:
            w.append("layer %s has no link from a shallower layer tagged portal or guarded" % name)
    return w, []


def lint_terrain(p, extra):
    w = []
    items = [("plan", t) for t in (extra or [])]
    items += [(k, t) for k, r in p.rooms.items() for t in (r.get("terrain") or [])]
    for where, t in items:
        if not isinstance(t, dict) or not t.get("special"):
            continue
        has_c, has_b = bool(t.get("cost")), bool(t.get("boon"))
        if not (has_c and has_b):
            side = "only a cost" if has_c else "only a boon" if has_b else "neither cost nor boon"
            w.append("special terrain %s (%s) has %s: give it both a price and a payoff"
                     % (t.get("name", "?"), where, side))
    return w, []


SIZE_SQUARES = {"tiny": 0.5, "small": 1, "medium": 1, "large": 2, "huge": 3, "gargantuan": 4,
                "colossal": 6}


def _squares(v):
    if isinstance(v, str):
        if v.casefold() not in SIZE_SQUARES:
            raise ValueError("lair owner size %r: use a number of squares or %s" % (v, ", ".join(SIZE_SQUARES)))
        return float(SIZE_SQUARES[v.casefold()])
    return float(v)


def lint_lair(p, lair):
    if not lair:
        return [], []
    w, info = [], []
    ents = p.entrances()
    if len(ents) < 2:
        w.append("lair has %d entrance(s): the owner wants at least 2 ways out" % len(ents))
    if lair.get("owner") is not None:
        own = _squares(lair["owner"])
        widths = {k: float(p.rooms[k]["opening"]) for k in ents if "opening" in p.rooms[k]}
        if len(widths) < len(ents):
            info.append("lair: %d entrance(s) give no opening width" % (len(ents) - len(widths)))
        if not any(v < own for v in widths.values()):
            w.append("no lair entrance is narrower than the owner (%g squares): add a gap only "
                     "small intruders can use" % own)
    hoard = lair.get("hoard")
    for k, r in p.rooms.items():
        if not r.get("treasure"):
            continue
        if "area" not in r:
            info.append("lair: treasure room %s has no area" % k)
            continue
        if hoard is None:
            info.append("lair: treasure room %s area %g squares" % (k, r["area"]))
            continue
        pct = 100.0 * float(hoard) / r["area"] if r["area"] else 0.0
        info.append("lair: treasure room %s area %g squares vs hoard %g (%.0f%%)"
                    % (k, r["area"], float(hoard), pct))
        if r["area"] < float(hoard):
            w.append("treasure room %s (%g squares) is smaller than the hoard (%g squares)"
                     % (k, r["area"], float(hoard)))
    return w, info


def lint_lair_home(p, lair):
    if not lair:
        return [], []
    w = []
    things = list(p.rooms.values()) + [a for _, _, a in p.link_attrs]
    hz = [t["home_hazard"] for t in things if t.get("home_hazard")]
    for h in hz:
        if not isinstance(h, dict) or h.get("gate") not in ("weight", "size") or h.get("limit") is None:
            w.append("home_hazard %r: give gate weight or size and a limit residents stay under" % (h,))
    if not hz:
        w.append("lair has no home_hazard (weight- or size-gated squares the residents pass freely)")
    if not any(a.get("resident_only") for _, _, a in p.link_attrs):
        w.append("lair has no resident_only link (a secret route only those who live there use)")
    return w, ["lair: %d home hazard(s)" % len(hz)]


def lint_traps(p, owner_route=None):
    w, info = [], []
    for k, r in p.rooms.items():
        t = r.get("trap")
        if t:
            if not isinstance(t, dict) or not t.get("trigger") or not t.get("effect"):
                w.append("trap in room %s needs separate trigger and effect areas" % k)
            elif sorted(map(str, t["trigger"])) == sorted(map(str, t["effect"])):
                info.append("traps: room %s trigger and effect cover the same squares" % k)
        if r.get("lockdown"):
            for a, b, at in p.link_attrs:
                if k in (a, b) and not at.get("door"):
                    w.append("lockdown room %s has a link to %s with no door drawn" % (k, b if a == k else a))
    for k in owner_route or []:
        if k not in p.rooms:
            w.append("owner_route names unknown room %s" % k)
            continue
        t = p.rooms[k].get("trap")
        if t and not (isinstance(t, dict) and t.get("bypass")):
            w.append("trap in room %s sits on the owner route with no bypass" % k)
    return w, info


def lint_base(p, base):
    if not base:
        return [], []
    w, info = [], []
    floors = sorted({r["floor"] for r in p.rooms.values() if "floor" in r}, key=str)
    for name, duty in sorted((base.get("shifts") or {}).items()):
        for k in duty:
            if k not in p.rooms and str(k) not in map(str, p.rooms):
                w.append("shift %s names unknown room %s" % (name, k))
        staffed = {p.rooms[k].get("floor") for k in duty if k in p.rooms}
        for f in floors:
            if f not in staffed:
                w.append("floor %s has nobody on the %s shift" % (f, name))
        info.append("base: %s shift covers %d room(s)" % (name, len(duty)))
    for a, b, at in p.link_attrs:
        if at.get("kind") in ("door", "window") and at.get("break") is None:
            w.append("%s %s - %s has no break value" % (at["kind"], a, b))
    return w, info


LOCK_KINDS = ("key", "word", "toll")


def _reach(p, starts, closed_room=None, closed_link=None):
    seen = {k for k in starts if k != closed_room}
    todo = list(seen)
    while todo:
        u = todo.pop()
        for a, b, at in p.link_attrs:
            if closed_link is not None and at.get("id") == closed_link:
                continue
            for x, y in ((a, b), (b, a)):
                if x == u and y != closed_room and y not in seen:
                    seen.add(y)
                    todo.append(y)
    return seen


def lint_locks(p, locks):
    w, info = [], []
    link_ids = {at.get("id"): at for _, _, at in p.link_attrs if at.get("id") is not None}
    ents = p.entrances()
    if locks and not ents:
        info.append("locks: plan has no entrance, softlock check skipped")
    homes = []
    for i, lk in enumerate(locks or []):
        at, key_in, kind = lk.get("at"), lk.get("key_in"), lk.get("kind", "key")
        name = lk.get("key") or "lock %d" % (i + 1)
        if kind not in LOCK_KINDS:
            raise ValueError("lock kind %r: use %s" % (kind, ", ".join(LOCK_KINDS)))
        if at in p.rooms:
            closed_room, closed_link, link = at, None, None
        elif at in link_ids:
            closed_room, closed_link, link = None, at, link_ids[at]
        else:
            raise ValueError("lock at %r names no room or link id" % (at,))
        if key_in == "wander":
            if not lk.get("drop_from"):
                w.append("wandering key %s has no drop_from foe: say who carries it" % name)
        elif key_in in p.rooms:
            homes.append(key_in)
            if ents and key_in not in _reach(p, ents, closed_room, closed_link):
                w.append("key %s in %s cannot be reached with lock at %s closed: softlock" % (name, key_in, at))
        else:
            raise ValueError("lock key_in %r names no room (or use 'wander')" % (key_in,))
        if kind == "toll" and not (lk.get("oneway") or (link or {}).get("oneway")):
            w.append("toll lock at %s is not marked oneway: say whether the far side pays" % at)
    if len(homes) >= 2 and len(set(homes)) == 1:
        w.append("all %d keys sit in room %s: spread them out" % (len(homes), homes[0]))
    for k, r in p.rooms.items():
        if not r.get("decoy"):
            continue
        near = {k}
        for _ in range(2):
            near |= {y for x in near for y in p.adj[x]}
        ok = any(p.rooms[x].get("secret") for x in near) or any(
            at.get("secret") and (a in near or b in near) for a, b, at in p.link_attrs)
        if not ok:
            w.append("decoy %s has no secret door within 2 rooms: hide the real way nearby" % k)
    return w, info


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


def _is(r, name):
    return bool(r.get(name)) or name in _dtags(r)


def lint_hostile(p, on):
    w = []
    if not on:
        return w, []
    for k, r in p.rooms.items():
        if r.get("lethal") and not r.get("warning"):
            w.append("lethal room %s has no warning cue: let players read the danger first" % k)
        if "gate" in _dtags(r) and not any(_is(p.rooms[n], "baffle") for n in p.adj[k]):
            w.append("gate %s has no baffle wall behind it: a straight line of fire runs through" % k)
    goals = [p.goal] if p.goal in p.rooms else [k for k, r in p.rooms.items() if r.get("treasure")]
    for g in goals:
        if not any(p.rooms[n].get("decoy") for n in p.adj[g]):
            w.append("prize room %s has no decoy room beside it" % g)
    return w, []


def lint_doom(p, doom):
    w, info = [], []
    if not doom:
        return w, info
    track = list(doom.get("track") or [])
    bad = [t for t in track if t not in p.rooms]
    if bad:
        raise ValueError("doom track names unknown room(s): %s" % ", ".join(map(str, bad)))
    if len(track) < 3:
        w.append("doom track has %d steps: want 3 or more" % len(track))
        return w, info
    circle = doom.get("circle", True)
    pairs = list(zip(track, track[1:])) + ([(track[-1], track[0])] if circle else [])
    for a, b in pairs:
        if b not in p.adj[a]:
            w.append("doom track step %s > %s has no link: draw the path along linked rooms" % (a, b))
    info.append("doom track: " + " > ".join(str(t) for t in track + ([track[0]] if circle else [])))
    return w, info


def lint_questions(p):
    info = []
    for k, r in p.rooms.items():
        if r.get("answer"):
            continue
        terr = {str(t if not isinstance(t, dict) else t.get("name", "")).casefold() for t in r.get("terrain") or []}
        if r.get("locked"):
            info.append("open question: who locked %s, and who holds the key?" % k)
        if "pit" in terr or "pit" in _dtags(r):
            info.append("open question: what lies at the bottom of the pit in %s?" % k)
        if r.get("secret"):
            info.append("open question: who hid %s, and what for?" % k)
        if k == p.goal:
            info.append("open question: why is the goal %s at the centre of it all?" % k)
    for a, b, at in p.link_attrs:
        if at.get("answer"):
            continue
        if at.get("locked"):
            info.append("open question: who locked the door %s - %s?" % (a, b))
        if at.get("secret"):
            info.append("open question: who built the hidden door %s - %s?" % (a, b))
    return [], info


def lint_omens(p, omens):
    if not omens:
        return [], []
    have = {str(k).casefold() for k, v in omens.items() if v}
    kinds = sorted({str(r["kind"]).casefold() for r in p.rooms.values() if r.get("kind")})
    return ["site kind %s has no omens: give a sign that it is near" % k for k in kinds if k not in have], []


def lint_portals(p):
    w = []
    for i, (a, b, at) in enumerate(p.link_attrs):
        if not (at.get("oneway") and (at.get("portal") or at.get("shift") or _tagged(at, "portal", "shift"))):
            continue
        if p.rooms[b].get("return"):
            continue
        edges = {}
        for j, (x, y, t) in enumerate(p.link_attrs):
            if j == i:
                continue
            edges.setdefault(x, set()).add(y)
            if not t.get("oneway"):
                edges.setdefault(y, set()).add(x)
        seen, todo = {b}, [b]
        while todo:
            for d in edges.get(todo.pop(), ()):
                if d not in seen:
                    seen.add(d)
                    todo.append(d)
        if a not in seen:
            w.append("one-way portal %s > %s: %s states no return exit" % (a, b, b))
    return w, []


def lint_cue(p):
    w = []
    cues = {k: r["cue"] for k, r in p.rooms.items() if "cue" in r}
    for k, v in cues.items():
        if not isinstance(v, (int, float)) or not 0 <= v <= 5:
            w.append("room %s cue %r: use 0-5" % (k, v))
    start = p.main_entrance()
    if not cues or start is None or p.goal not in p.rooms:
        return w, []
    path = p.path(start, p.goal) or []
    seq = [(k, cues[k]) for k in path if isinstance(cues.get(k), (int, float))]
    for (k1, c1), (k2, c2) in zip(seq, seq[1:]):
        if c2 < c1:
            w.append("cue drops from %s (%s) to %s (%s) on the way to the goal" % (k1, c1, k2, c2))
    return w, []


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


def _sees(a, b, rng, ridges):
    ax, ay, az = float(a["x"]), float(a["y"]), float(a.get("elev", 0))
    bx, by, bz = float(b["x"]), float(b["y"]), float(b.get("elev", 0))
    L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    if L > rng:
        return False
    for r in ridges:
        rx, ry, rz = float(r["x"]), float(r["y"]), float(r["elev"])
        t = ((rx - ax) * (bx - ax) + (ry - ay) * (by - ay)) / (L * L) if L else 0.0
        if not 0 < t < 1:
            continue
        off = ((ax + t * (bx - ax) - rx) ** 2 + (ay + t * (by - ay) - ry) ** 2) ** 0.5
        if off <= 0.5 and rz > az + t * (bz - az):
            return False
    return True


def lint_signal(p, sig):
    """Outposts on the approach routes and a line-of-sight signal chain back to the keep (Stronghold
    Builder's Guidebook, pp. 93, 96, 102: idea only)."""
    w, info = [], []
    for k, r in p.rooms.items():
        if r.get("under") is not None:
            info.append("signal: room %s sits under room %s: hard to retrofit, build it first" % (k, r["under"]))
        if str(r.get("fire_load", "")).lower() == "high":
            secret = r.get("secret_exit") or any(at.get("secret") for a, b, at in p.link_attrs if k in (a, b))
            if not secret:
                w.append("room %s has a high fire load and no secret exit (secret_exit or a secret link)" % k)
    if not sig:
        return w, info
    keep = sig.get("keep")
    if keep not in p.rooms:
        return w + ["signal keep %r is not a plan room" % (keep,)], info
    rng = float(sig.get("range", 10))
    ridges = sig.get("ridges") or []
    posts = [k for k, r in p.rooms.items() if r.get("outpost")]
    for k in posts:
        if not all(f in p.rooms[k] for f in ("x", "y")):
            w.append("outpost %s has no x, y position" % k)
    nodes = [k for k in posts if "x" in p.rooms[k] and "y" in p.rooms[k]]
    if "x" in p.rooms[keep] and "y" in p.rooms[keep]:
        nodes.append(keep)
    else:
        w.append("signal keep %s has no x, y position" % keep)
    hops = {keep: 0}
    todo = [keep]
    while todo:
        u = todo.pop(0)
        for v in nodes:
            if v not in hops and _sees(p.rooms[u], p.rooms[v], rng, ridges):
                hops[v] = hops[u] + 1
                todo.append(v)
    for k in posts:
        if k in hops:
            info.append("signal: outpost %s reaches the keep in %d hop(s)" % (k, hops[k]))
        else:
            w.append("outpost %s cannot pass a signal to the keep by line of sight" % k)
    for i, route in enumerate(sig.get("routes") or []):
        if not any(p.rooms.get(k, {}).get("outpost") for k in route):
            w.append("approach route %d (%s) has no outpost on it" % (i + 1, " - ".join(str(k) for k in route)))
    return w, info


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
    sb = _load(d, "sandbox.json")
    if sb is not None:
        import mpw_hexcrawl
        sw = [dict(check="sandbox", text=t) for t in mpw_hexcrawl.sandbox_issues(sb)]
        if not plan:
            return dict(warnings=sw, info=["sandbox.json: %d keyed hexes" % len(sb.get("keys") or [])], escape=[])
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
                         ("routes", lint_routes(p)), ("districts", lint_districts(p)),
                         ("supply", lint_supply(p, plan.get("supply"))),
                         ("layers", lint_layers(p, plan.get("layers"))),
                         ("terrain", lint_terrain(p, plan.get("terrain"))),
                         ("lair", lint_lair(p, plan.get("lair"))),
                         ("lair", lint_lair_home(p, plan.get("lair"))),
                         ("traps", lint_traps(p, plan.get("owner_route"))),
                         ("base", lint_base(p, plan.get("base"))),
                         ("locks", lint_locks(p, plan.get("locks"))),
                         ("hostile", lint_hostile(p, plan.get("hostile"))),
                         ("doom", lint_doom(p, plan.get("doom"))),
                         ("questions", lint_questions(p)),
                         ("omens", lint_omens(p, plan.get("omens"))),
                         ("portals", lint_portals(p)), ("cue", lint_cue(p)),
                         ("signal", lint_signal(p, plan.get("signal")))):
        res["warnings"] += [dict(check=name, text=t) for t in w]
        res["info"] += i
    if sb is not None:
        res["warnings"] += sw
    return res
