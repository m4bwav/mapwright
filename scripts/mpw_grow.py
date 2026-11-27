"""Transition-first dungeon growth: a room plan grown from one map edge.

Idea from the Points of Light and Book of Lairs era notes (p. 135, 149-150): place the way in first and then
the area beyond it, so every step deeper starts with a transition (stair, door, bridge, squeeze); every N-th
transition carries a trick; lair mode keeps the empty share low because a lair is lived in. Word lists and
numbers are our own. The output is a plan that `mpw lint` reads.
"""
import mpw_gen as G

EDGES = ("north", "south", "east", "west")
TRANSITIONS = ("door", "stair down", "stair up", "bridge", "squeeze", "ladder", "arch", "rope descent", "ford")
TRICKS = ("false floor", "rotating wall", "one-way door", "illusory wall", "weighted plate", "riddle lock",
          "sliding block", "mirror ward")
AREAS = ("hall", "cave", "shrine", "store", "barracks", "well room", "gallery", "cistern", "workshop", "den")
EMPTY_SHARE, LAIR_EMPTY_CAP = 0.35, 0.15
STEP = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}   # inward from that edge


def _r(seed, *k):
    return (G.h64(seed, 4100, *k) >> 11) / 9007199254740992.0


def grow_plan(seed, transitions=8, trick_every=3, lair=False, edge="south"):
    """A plan: rooms on a coarse lattice and links, each link a transition. Deterministic by seed."""
    if edge not in EDGES:
        raise ValueError("--edge must be one of %s" % ", ".join(EDGES))
    if not 1 <= transitions <= 60:
        raise ValueError("--transitions must be 1 to 60")
    if trick_every < 1:
        raise ValueError("--trick-every must be 1 or more")
    dx0, dy0 = STEP[edge]
    rooms = [dict(id="a0", name="Way In", kind="entrance", role="entrance", entrance=True, main=True,
                  x=0, y=0, empty=False, hook="the edge of the map: tracks lead inside")]
    taken = {(0, 0): "a0"}
    links = []
    cap = LAIR_EMPTY_CAP if lair else EMPTY_SHARE
    empties = 0
    for i in range(1, transitions + 1):
        # grow from the newest room most of the time, else from an earlier one (side branches)
        src = rooms[-1] if _r(seed, i, 1) < 0.7 or len(rooms) < 3 else rooms[int(_r(seed, i, 2) * len(rooms))]
        dirs = [(dx0, dy0), (dy0, dx0), (-dy0, -dx0)]          # deeper first, then sideways
        if _r(seed, i, 3) < 0.4:
            dirs = dirs[1:] + dirs[:1]
        pos = None
        for c in rooms[::-1] if src is None else [src] + rooms[::-1]:
            for dx, dy in dirs:
                q = (c["x"] + dx, c["y"] + dy)
                if q not in taken:
                    src, pos = c, q
                    break
            if pos:
                break
        tr = dict(id="t%d" % i, a=src["id"], b="a%d" % i, transition=TRANSITIONS[int(_r(seed, i, 4) *
                                                                                     len(TRANSITIONS))])
        if i % trick_every == 0:
            tr["trick"] = TRICKS[int(_r(seed, i, 5) * len(TRICKS))]
        links.append(tr)
        want_empty = _r(seed, i, 6) < EMPTY_SHARE and (empties + 1) / float(i + 1) <= cap
        room = dict(id="a%d" % i, name="Area %d" % i, kind=AREAS[int(_r(seed, i, 7) * len(AREAS))],
                    x=pos[0], y=pos[1], depth=abs(pos[0] * dx0) + abs(pos[1] * dy0) if (dx0 or dy0) else 0,
                    empty=want_empty)
        if want_empty:
            empties += 1
            room["hook"] = "signs of passing: something lives deeper" if lair else "an old mark on the wall"
        elif lair:
            room["occupant"] = "lair dweller"
        rooms.append(room)
        taken[pos] = room["id"]
    goal = max(rooms, key=lambda r: (r.get("depth", 0), r["id"] != "a0", -int(r["id"][1:])))["id"]
    plan = dict(rooms=rooms, links=links, goal=goal,
                grow=dict(edge=edge, transitions=transitions, trick_every=trick_every, lair=lair,
                          empty_cap=cap, empty_share=round(empties / float(len(rooms)), 3),
                          tricks=sum("trick" in l for l in links)))
    return plan


def write_plan(out, seed, version, **kw):
    import json
    import os
    plan = grow_plan(seed, **kw)
    recipe = dict(kind="plan", seed=seed, tool="mapwright", tool_version=version, generator="grow-1",
                  params=dict(kw), plan=plan)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "recipe.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(recipe, f, indent=1, sort_keys=True)
        f.write("\n")
    return plan


# Stronghold footprint (Engineering Castles pp. 19, 26 idea: the shape comes from a roll on the ground plan, the
# room count and storeys from the building style) and home-base duty shifts with break values on doors and
# windows (Adventurers Guild pp. 3, 41 idea). Shapes, styles, duties and numbers are our own.
SHAPES = ("square", "oblong", "L", "round", "polygon", "rock-following", "D", "twin-ward")
STYLES = {  # style: (rooms lo, hi), (storeys lo, hi)
    "tower": ((4, 7), (3, 5)), "hall-keep": ((6, 10), (2, 3)), "shell-keep": ((5, 9), (1, 2)),
    "courtyard": ((8, 14), (1, 2)), "concentric": ((10, 18), (2, 3)), "manor": ((5, 9), (1, 2)),
}
ROOMS = ("hall", "chamber", "store", "chapel", "guardroom", "kitchen", "armoury", "solar", "well room",
         "barracks", "office", "workshop")
DUTIES = ("watch", "cook", "clerk", "smith", "porter", "patrol")
BREAK = {"door": (12, 25), "window": (6, 15)}


def stronghold_plan(seed, style="hall-keep", facade_only=False):
    if style not in STYLES:
        raise ValueError("--stronghold must be one of %s" % ", ".join(sorted(STYLES)))
    (rl, rh), (sl, sh) = STYLES[style]
    shape = SHAPES[int(_r(seed, 1, 1) * len(SHAPES))]
    storeys = sl + int(_r(seed, 1, 2) * (sh - sl + 1))
    count = rl + int(_r(seed, 1, 3) * (rh - rl + 1))
    out = dict(id="out", name="Approach", kind="outside", entrance=True)
    gate = dict(id="g0", name="Gate", kind="gatehouse", floor=0, facade=True)
    rooms, links = [out, gate], [dict(a="out", b="g0", kind="door", door=True, **_brk(seed, "door", 0))]
    if not facade_only:
        for i in range(1, count + 1):
            f = (i - 1) * storeys // count
            r = dict(id="r%d" % i, name="Room %d" % i, kind=ROOMS[int(_r(seed, 2, i) * len(ROOMS))], floor=f)
            prev = rooms[-1]
            rooms.append(r)
            kind = "stair" if prev.get("floor") != f else "door"
            l = dict(a=prev["id"], b=r["id"], kind=kind)
            if kind == "door":
                l.update(door=True, **_brk(seed, "door", i))
            links.append(l)
            if f > 0 and _r(seed, 3, i) < 0.5:
                links.append(dict(a=r["id"], b="out", kind="window", **_brk(seed, "window", i)))
    shifts = {}
    for name in ("day", "night"):
        duty = {}
        for f in sorted({r["floor"] for r in rooms if "floor" in r}):
            here = [r for r in rooms if r.get("floor") == f]
            pick = here[int(_r(seed, 4, len(name), f) * len(here))]
            duty[pick["id"]] = DUTIES[int(_r(seed, 5, len(name), f) * len(DUTIES))]
        shifts[name] = duty
    return dict(rooms=rooms, links=links, goal=rooms[-1]["id"], base=dict(shifts=shifts),
                stronghold=dict(style=style, shape=shape, storeys=storeys, rooms=count, facade_only=facade_only))


def _brk(seed, kind, i):
    lo, hi = BREAK[kind]
    return {"break": lo + int(_r(seed, 6, len(kind), i) * (hi - lo + 1))}


def write_stronghold(out, seed, version, **kw):
    import json
    import os
    plan = stronghold_plan(seed, **kw)
    recipe = dict(kind="plan", seed=seed, tool="mapwright", tool_version=version, generator="stronghold-1",
                  params=dict(kw), plan=plan)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "recipe.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(recipe, f, indent=1, sort_keys=True)
        f.write("\n")
    return plan
