# Cities, dungeons and battle maps: reference for mapwright

Research notes behind `gen city`, `gen dungeon`, `gen battle` and the tabletop exports. Each claim cites a source in brackets, keyed to the list at the end. "(unverified)" means it was written from memory and not checked against a primary source on 2026-11-14. Check these before code depends on them.

mapwright is stdlib-first Python, so this file favours methods that need only `random`, `math`, `heapq`, `json` and `collections`, plus a hand-written PNG/SVG writer.

---

## 1. Street networks

### 1.1 Extended L-systems (Parish and Müller 2001)

- Parish and Müller's CityEngine paper grows roads with an extended L-system: the L-system proposes road segments, and two outside functions edit each proposal [PM01].
- **Global goals** set the direction and length a road wants: follow population density peaks, or a road pattern (rectangular grid, radial, or one that follows elevation) [PM01].
- **Local constraints** then accept, trim or reject the proposal: snap to a nearby crossing, end at an existing road, stop at water, cut short on steep ground [PM01].
- Highways and streets are two segment classes. Highways look further ahead for density; streets fill in between [PM01].
- Plain-language rewrite as a priority queue (no grammar needed), widely used in hobby ports: pop a segment with the lowest delay, check local constraints, commit it, push branches with greater delay [SM-PORT] (unverified as to which port is canonical).
- Local-constraint rules worth copying exactly: (a) if the new end is within radius r of a crossing, snap to it; (b) if it crosses an existing segment, end it at the crossing; (c) if it is within r of a segment, extend it to meet that segment [PM01].

### 1.2 Tensor fields (Chen et al. 2008)

- Chen, Esch, Wonka, Müller and Zhang build a 2D tensor field from basis fields (grid with a direction, radial around a centre, along a boundary or river, and so on) blended by distance-based weights [CH08].
- Major and minor hyperstreamlines traced through the field become the main and side roads. Degenerate points (where the field has no direction) become places like roundabouts or plaza centres [CH08].
- The user edits the field, not the roads, so the layout stays coherent while being changed [CH08].
- Fit for mapwright: good for "modern" or organic grids; tracing is RK4 integration plus a minimum separation test, both stdlib work [CH08].

### 1.3 Agent-based growth

- Lechner, Watson, Wilensky et al. let "extender" agents wander in undeveloped land and propose roads back to the network, and "connector" agents add shortcuts where travel distance on roads is far longer than straight-line distance [LE03].
- The detour test (network distance over straight distance above a threshold, e.g. above about 1.5 to 2, gives a new road) is cheap and makes believable connectivity on its own [LE03] (threshold values unverified).

### 1.4 What mapwright should pick

- Medieval and fantasy towns: Voronoi wards plus streets along ward edges and a few main roads from gates to centre, the Watabou approach (section 3). Cheaper and more legible at tabletop scale than either L-systems or tensor fields.
- Modern or large cities: priority-queue L-system with local constraints first; tensor field as an option.
- Planned Roman-style colony and its fields: a grid of squares of 20 actus (2,400 Roman feet, close to 710 m a side; 703 to 714 m found), 200 iugera each, on two main axes, the decumanus and the kardo (Harley and Woodward, History of Cartography vol. 1, ch. 13) (book fact, not cross-checked).

---

## 2. Blocks and lots

- Once roads exist, blocks are the faces of the planar road graph. Find them by walking half-edges, always turning most-left (or most-right) at each node; every closed walk is a face, and the one with negative signed area is the outer face [DCG] (standard computational geometry, de Berg et al.).
- Vanegas, Kelly, Weber, Halatsch, Aliaga and Waddell give two lot methods [VA12]:
  - **OBB subdivision**: take the block's oriented bounding box, split it across its long axis near the middle (with jitter), recurse until each part is under a target area and has street frontage; parts with no street access are dropped or merged.
  - **Straight-skeleton subdivision**: offset the block inward, use the skeleton to make strips along each street, then cut the strips into lots. Gives lots that all face a street.
- Stdlib-friendly: OBB recursion needs only polygon clipping by a line (Sutherland-Hodgman against a half-plane) and the rotating-calipers or a 0-to-180 degree sweep for the box.
- Building footprints: shrink each lot by a setback, then optionally keep only the front part (row houses in old towns cover nearly the whole lot) [WAT-BLOG] (unverified for exact Watabou rules).

### Proof rules for blocks

- Every lot polygon is simple (no self-crossing), has positive area, and lies inside its block.
- Every lot touches a street edge (frontage > 0) unless flagged as courtyard.
- Sum of lot areas plus leftover area equals block area within 1e-6 relative.

---

## 3. Walls, districts and city generators

### 3.1 Watabou Medieval Fantasy City Generator (Oleg Dolya)

- Oleg Dolya publishes as "watabou". His Medieval Fantasy City Generator (MFCG) runs in the browser and its older Haxe source (TownGeneratorOS) is on GitHub under GPL-3.0 [WAT-TGOS] (confirmed: repo sidebar and LICENSE, https://github.com/watabou/TownGeneratorOS, 2026-11-14; GPL means read for ideas, do not copy code into a differently licensed package).
- Method described in the source and his posts [WAT-TGOS][WAT-BLOG]:
  - Scatter seed points in a spiral around a centre, build a Voronoi diagram, and relax it so cells are even.
  - Inner cells become wards (patches); the central one is the plaza or market.
  - The wall is the outline of the inner patches, smoothed; gates go where main roads cross it; towers sit at wall vertices.
  - Each ward gets a type (market, craftsmen, merchant, slum, cathedral, castle, farm, park, administration, military) by rated placement: each type scores candidate patches (near plaza, near wall, near water) and takes the best.
  - Inside a ward, the patch polygon is cut into buildings by recursive splitting with alleys, then some buildings are dropped for gaps.
- Current MFCG exports PNG, SVG and a JSON with features (walls, roads, buildings, districts) [WAT-MFCG] (exact JSON schema unverified).
- Watabou also makes the One Page Dungeon, Perilous Shores, Village and Neighbourhood generators; the Dungeon generator exports JSON with rooms and doors on a grid [WAT-OPD] (schema unverified).
- Do not copy output or code into mapwright; reimplement the method. GPL code cannot go into a permissively licensed plugin.

### 3.2 Townscaper-likes

- Townscaper by Oskar Stålberg uses an irregular grid: a hex grid of triangles, randomly merged into quads, then each quad subdivided into four, then relaxed, so every cell is a quad with four corners [ST-TALK].
- Corner-based modules are picked by a constraint solver in the WFC family, so placing one block changes neighbours to fit [ST-TALK].
- Lesson for mapwright: the "irregular quad grid" is a cheap way to give organic towns a grid that tiles still fit on; useful for `gen city --style organic`.

### 3.3 Districts in general

- Assign districts after roads, by flood-filling blocks from seed blocks with a weight (distance to centre, to water, to gate) [WAT-TGOS].
- Keep districts as data (`district` field per block) so exports can colour or label them.
- Assign the most constrained type first: the one with the least slack between its candidate cells and the count it needs (Korn and Lee, Game Dynamics, ch. 9, sec. 6).

### Proof rules for walls

- The wall is a closed simple polygon; every gate lies on it; every main road crosses it only at a gate.
- Every ward marked "inside" has its centroid inside the wall polygon (ray-cast test).

---

## 4. Floor plans

- Merrell, Schkufza and Koltun train a Bayesian network on real plans to get room lists and adjacency, then lay rooms out by stochastic optimization (Metropolis) over a cost for area, shape and adjacency [ME10].
- Lopes, Tutenel, Smelik, de Kraker and Bidarra grow rooms on a grid from seed cells ("constrained growth"): each room expands rectangularly, then into L shapes, until the floor is full; doors follow an adjacency graph [LO10].
- Squarified treemaps make a fast first cut: split the footprint into rectangles with areas proportional to room sizes, then fix adjacency by swaps [MA10] (Marson and Musse 2010).
- Stdlib route: treemap first, then grid growth to fix shapes, then doors from a spanning tree of the adjacency graph plus extra doors for loops. Check that the entrance reaches every room (section 7).
- House rules from a shipped game: room type sets the target area, the door limit and the furniture list; private rooms (bedroom, bathroom) get one door and public rooms several; furniture never blocks a doorway or other furniture. Known failure: fixtures block each other in small thin bathrooms (Short and Adams, Procedural Generation in Game Design, ch. 6).

---

## 5. Dungeon methods

### 5.1 BSP

- Split the map rectangle recursively (horizontal or vertical, ratio limited to about 0.3 to 0.7) until leaves fall under a size; put one room per leaf with random margins; connect sibling leaves with corridors bottom-up [RB-BSP].
- Gives non-overlapping rooms and guaranteed connectivity by construction (the tree is a spanning tree), but no loops. Add 5 to 15 percent extra corridors between nearby rooms for loops (value is a design choice, not from a source).
- The loop pass now has a source: after assembly, add a door where two rooms share a wall and have no door nearby, which makes circular routes and cuts backtracking (Short and Adams, Procedural Generation in Game Design, ch. 7, ch. 9). The textbook BSP joins siblings only and has no loops (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 3). mapwright's extra-corridor share stays its own number.
- Stop size as a share of the map: the textbook example stops splitting a leaf below a quarter of the map width or height, puts one room per leaf and joins siblings from the lowest level up, which keeps corridors from crossing (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 3, p. 35-37). mapwright stops at a fixed leaf size.
- Split-axis policy sets the look: a random axis is unpredictable, always cutting the shorter side gives long thin regions, always the longer side gives even squarish ones; a weighted mix with a chance to stop early is what shipped (Short and Adams, Procedural Generation in Game Design, ch. 8, p. 76). mapwright cuts the longer side when the sides differ.
- Skim perimeter leaves so the footprint is not a rectangle: random removal for dungeons, from the top for buildings, by traversal for mines. Keep the region adjacency graph through every split, let a random traversal pick the doors, and delete regions it never visits (Short and Adams, Procedural Generation in Game Design, ch. 8, p. 76-79).
- The tree gives themes: a subtree joined by one corridor is a wing that can be locked, with its key placed outside it (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 3, p. 37).

### 5.2 Cellular automata caves

- Fill cells as wall with probability about 0.45, then apply "a cell becomes wall if 5 or more of its 8 neighbours (plus itself, in some versions) are walls" for 4 to 5 passes [RB-CA].
- Johnson, Yannakakis and Togelius used a similar rule for infinite cave levels and studied the parameters [JO10].
- Caves come out in disconnected pockets. Fix: flood-fill each region, keep the largest, or join regions with tunnels to the nearest cell of the main region [RB-CA].

Settings side by side (compared 2026-11-15). Nothing was replaced: the default changes only after a sweep on mapwright's own code.

| Source | Wall fill | Rule per pass | Passes | Notes |
|---|---|---|---|---|
| mapwright `gen dungeon --method cave` (code, 2026-11-15) | 0.45 | wall at 5 or more of 8 wall neighbours, floor at 3 or fewer, unchanged at 4 | 5 | one-cell solid border; keeps the largest region. This is the [RB-CA] form |
| Johnson, Yannakakis and Togelius 2010 [JO10] | r = 50% | rock at T = 5 or more in the Moore neighbourhood, M = 1 | n = 4 | 50 x 50 grid; M = 2 with T = 13 for the multi-room setting ([realistic-land.md](realistic-land.md) 10b) |
| The same paper as quoted in Shaker, Togelius and Nelson, ch. 3, p. 43-44 | 0.5 | rock at 5 or more | 2 to 4 | size-2 neighbourhood: threshold 13, 4 steps, 50% rock. Rooms joined by a tunnel between their largest open areas at the closest point, then 2 more passes over all nine rooms |
| Caves of Qud (Short and Adams, ch. 26, p. 288-290) | 55% | open becomes wall at 6 to 8 wall neighbours, wall becomes open at 0 to 4 | 2 | two-cell solid border |

- A random fill that must be connected with no smoothing wants a sparse start: at 50% filled a path from entrance to exit is very unlikely; at 20% filled, or with walls capped at length 5, nearly every random map is connected (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 9, p. 162, p. 165).
- The automaton cannot be asked for a room count or a connectivity; each parameter moves several features at once (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 3, p. 44).
- Even stocking of an uneven cave: grow nearest-seed regions by breadth-first search, add seeds until the largest region is under a target size, then put the same count in each region (Short and Adams, Procedural Generation in Game Design, ch. 26, p. 296-297).

### 5.3 Drunkard's walk

- A walker starts in the centre and carves floor as it steps randomly until a target fraction (often 40 percent) is floor [RB-DW].
- Always connected by construction. Variants: several walkers, bias toward unvisited direction, restart from a random existing floor cell.

### 5.4 Wave Function Collapse

- Maxim Gumin's WaveFunctionCollapse repository (mxgmn/WaveFunctionCollapse) defines the overlapping model (learns NxN patterns from a sample) and the simple tiled model (tiles plus adjacency rules) [WFC].
- Licence: MIT [WFC] (check the LICENSE file before release; the README states the code is MIT; sample images may carry their own credits).
- Loop: each cell holds the set of allowed tiles; pick the cell with lowest entropy, collapse it to one tile weighted by frequency, propagate constraints to neighbours; on contradiction, restart or backtrack [WFC].
- WFC does not guarantee connectivity or a path from entrance to exit. Run the BFS proof (section 7) and regenerate or patch. Karth and Smith discuss adding global constraints and backtracking [KS17].
- Stdlib: the tiled model is short (sets plus a deque); fine for `gen dungeon --method wfc` with a tileset defined in JSON.
- No book read so far covers wave function collapse (eight books checked 2026-11-15); this section rests on web sources. The nearest covered method is a grid of blocks with a per-side exit flag, placed so exits match and open edges merge into halls: 7 by 7 blocks, a goal of 40 blocks, and a map with too few placements thrown away and restarted (Short and Adams, Procedural Generation in Game Design, ch. 7, p. 66-72). Wang tiles match edge colours the same way (ch. 26, p. 291-292).

### 5.5 Graph-first and cyclic generation

- Dormans generates a mission graph first with graph grammars (lock, key, boss, reward as nodes), then turns it into space with shape grammars [DO10].
- Unexplored (Ludomotion, 2017) uses cyclic dungeon generation: start from a cycle between entrance and goal, then rewrite edges into sub-cycles with patterns such as lock-and-key, hidden shortcut, or two alternative paths [DO-CYC][BTB-CYC].
- Boris the Brave's write-up "Dungeon Generation in Unexplored" explains the cycle patterns and how the graph is laid out on a grid afterwards [BTB-CYC].
- For tabletop use this is the most useful method: rooms get purposes (key, lock, boss, treasure) and loops give players choices. Lay out the graph by placing rooms on a grid via search, with corridors as edges.
- Dormans' own account of cyclic generation (Short and Adams, Procedural Generation in Game Design, ch. 9), rules as given:
  - A cycle is a start and a goal joined by two paths, a and b. Nest cycles instead of branching. Two to five cycles per level give a readable shape; more is clutter (p. 84, p. 95). That figure is one studio's taste, not a measured optimum. Bar: cycle rank of the room graph (edges minus nodes plus 1) between 2 and 5.
  - Pick the pattern from the two path lengths. Short a with long b: a lock at the goal and the key at the far end of b, near where b rejoins. The player may see b from the start but must not be able to enter it there (p. 89).
  - Named patterns: two alternative paths, hidden shortcut, lock and key cycle, double key, key behind valve, patrolled cycle, dangerous route, unknown return path, lure and setback, gambit (p. 89-90).
  - Locks are conditional, dangerous or uncertain; permanent, reversible, temporary or collapsing; a valve (one way) or asymmetrical (opens from one side). Keys are single or multi purpose, particular or not, consumed or persistent, or fixed in place; a fixed key (a lever) should open its lock for good (p. 91-93).
  - Safety: every conditional lock on the main path has a guaranteed solution. Unsafe locks sit only on optional paths, and then the way back is safe. Consumed or multipurpose keys make a lock less safe (p. 92-93). Bars: the key-before-lock BFS below, plus a return-path BFS from goal to entrance that honours one-way edges.
  - Work on a graph first with generic nodes, and choose exact obstacles, locks, keys and room kinds in later passes; each step outputs a model that makes sense alone. Lay the graph out on a grid from the start, so each node and edge maps to a cell, then raise the resolution and decorate (p. 84-86, p. 94-95). The chapter gives no layout algorithm beyond that.
- Layout ruling 2026-11-15. The line above lays the graph out on a grid afterwards, by search. Dormans starts on the grid. A studio that rewrote free graphs first dropped the method: the space of graphs was far larger than the maps wanted, and drawing arbitrary graphs in the plane with even spacing became the real work (Korn and Lee, Game Dynamics, ch. 9, sec. 3.2.3, sec. 4). Two cures are named: allow only rewrite rules that keep the graph drawable, or generate on a grid of cells and derive the graph from it. mapwright takes the second. Bar: every graph edge joins cells that share a border; zero edge crossings.
- Mission in two steps with a fixed rule sequence: a random task list first, lock and key links second. Applying each rule a set number of times controls the length; unbounded rule application does not. Mission alphabet: entrance, task, goal, lock, key (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 5, p. 81-84).
- Room purposes from the graph: boss treasure in a dead-end region far from the entrance, the boss room on the only way to it, traps and stores in other dead ends (Short and Adams, Procedural Generation in Game Design, ch. 8, p. 80). Stock by breadth-first layers from the entrance: light threats first, tougher next, treasure after, exits in the last layer (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 9, p. 166-167). A rare feature is capped at one per map (its chance drops to 0 once one exists) and is better scheduled every 2 to 4 units, the middle most likely, than rolled at a flat chance (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 3, p. 50; Short and Adams, Procedural Generation in Game Design, ch. 2, p. 22).

### Proof rules for dungeons

- Graph rule: every key is reachable from the entrance without passing its own lock (BFS with locked edges removed, then add keys found, repeat until no change).
- Every room reachable from the entrance; the boss/exit reachable.
- Rooms do not overlap (axis-aligned rectangle test or cell occupancy).
- A gate is real: with a lock closed, BFS from the entrance must not reach what lies behind it. If any route skips the gate, reject the map (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 8, p. 153-155).

---

## 6. Hex and square grids

- Red Blob Games' hex guide is the standard reference [RBG-HEX]:
  - **Cube coordinates** (q, r, s) with q + r + s = 0. Distance = (|dq| + |dr| + |ds|) / 2. Neighbours are the six unit vectors.
  - **Axial** stores (q, r) and derives s = -q - r. Use this as the stored form.
  - **Offset** (odd-r, even-r, odd-q, even-q) shifts every other row or column; convenient for arrays but needs conversion for maths.
  - **Doubled** coordinates are an alternative to offset.
  - Pointy-top hex to pixel: x = size * (sqrt(3) q + sqrt(3)/2 r), y = size * (3/2 r). Flat-top swaps the roles.
  - Pixel to hex: inverse matrix, then cube rounding (round each, then fix the component with the largest rounding error).
  - Lines: lerp in cube space N+1 times and round; rings and spirals by walking from a start.
- Square grids: choose 4- or 8-connectivity explicitly. For D&D 5e the default diagonal is 5 ft per step; the optional variant alternates 5/10 ft [DMG14] (unverified page reference). Pathfinder 2e uses alternating 5/10 ft [PF2] (unverified).
- Foundry, Roll20 and Owlbear Rodeo all support square and hex grids [FVTT-SCN][R20-GRID][OBR-DOC].

---

## 7. Checkable proof rules (implement as tests)

1. **Reachability by BFS.** From the entrance cell, BFS over passable cells (4- or 8-connected, matching the export's movement rule; doors count as passable, locked doors only after their key). Proof: every floor cell, every room and the exit are visited. Store the count of visited cells and assert it equals the floor count.
2. **Grid on whole pixels.** Image width = cols * pps and height = rows * pps exactly, where pps (pixels per square) is an integer. Grid line positions are integers. No fractional offset; any map origin offset is a whole number of pixels. Check by asserting `width % pps == 0` and reading the PNG header.
3. **Export loads with walls.** Write the file, parse it back with `json.loads`, assert required keys exist, assert wall count > 0 and equals the generator's wall count, assert every wall point lies inside the map bounds, and assert every door/portal sits on a wall segment within tolerance. For Foundry, assert every wall `c` has four numbers and both endpoints are inside the scene. Manual check: import into Foundry with the Universal Battlemap Importer and see that tokens are blocked [UBI].
4. **Walls are closed.** For each room, wall segments form a closed loop except where portals are. Light from inside a closed room cannot reach outside (segment intersection test from a light to sample points).
5. **Determinism.** Same seed and options give byte-identical output (hash the JSON). The seed is stored with the map and reset at the start of each sub-map, so a discarded dungeon can be rebuilt (Watkins, Procedural Content Generation for Unity Game Development, ch. 1, ch. 4).
6. **Stable seeds (ruling 2026-11-14).** Seeds are derived with a stable hash (`hashlib.blake2b(seed.encode("utf-8"), digest_size=8)`), never Python's built-in `hash()`, which is salted per process for strings. Word seeds such as `--seed "amber fox lantern"` are lower-cased, whitespace-normalised and hashed the same way, and the original words are recorded in the recipe (Pitt, Procedural Generation in Godot, p. 99). Content seeds are kept separate from runtime behaviour randomness (Pitt, p. 96).
7. **Playability check after generation.** Every generator runs its check (reachability, openings per room, spawn on floor, direction bias of the maze) after generating; no algorithm is trusted untested (Green, Procedural Content Generation for C++ Game Development, ch. 1, ch. 9).
8. **Endpoints reachable.** After template assembly, start, exit, waypoints and doors are marked cells, and BFS reaches every one (Pitt, Procedural Generation in Godot, p. 184, p. 241).
9. **Solid border.** No floor cell lies on the outer row or column of a dungeon (Watkins, Procedural Content Generation for Unity Game Development, ch. 4). Both current methods close the border by construction. Caves of Qud uses a two-cell border (Short and Adams, Procedural Generation in Game Design, ch. 26).

### Expressive range (books, 2026-11-15)

A few good outputs say little about a generator that can make thousands. The method (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 12, p. 215-217; Short and Adams, Procedural Generation in Game Design, ch. 22, p. 233-243):

- Choose metrics, generate many maps, normalise each metric to 0 to 1 across the sample, and plot a 2D histogram (heatmap). Hot spots show bias.
- Sample size: keep enlarging the sample until the plot stops changing (Shaker, Togelius and Nelson, p. 216). The worked heatmap in Short and Adams used 10,000 levels per parameter setting (p. 240). A bias can hide where the same region is covered at a different frequency; a few samples will not show it.
- Metrics measure what the generator does not already enforce and sit far from the input flags. A metric that mirrors an input only confirms that the code runs: never room count when room count is a flag.
- Linearity, the book's platformer formula: fit a line through the platform midpoints, average the absolute vertical distance from it, then rescale across the sample to 0 to 1 (Short and Adams, p. 235, p. 240). Leniency: give each hazard type a harm weight from 0 (fatal) to 1 (harmless) and average over all elements (p. 235-236). Density (share of space filled) and the risk-to-reward ratio are named as further metrics. Metrics lose information (leniency ignores the order and spacing of hazards), so read them as rough estimates.
- Dungeon forms are mapwright's translation, not the books': linearity from room centres regressed along the entrance-to-exit axis; loop share (extra edges over the spanning tree); dead-end share; entrance-to-exit path length over the map diagonal; open-floor share. They need their own sanity test.
- Read four things from the plot: variety, unintended bias, response to inputs, content families. Compare plots across settings: a flag that leaves the plot unchanged is dead. A sudden change after a small code edit is a bug signal, so a stored histogram per release works as a regression test. For many metrics use box plots per metric, or clustering by a distance function.

### Book methods (2026-11-14)

- **Backtracker maze dungeon.** Wall-filled grid with odd width and height, recursive backtracker with an explicit stack and shuffled directions, then carve N rooms (size range a-b), order `maze-first` or `rooms-first`; place spawns on floor cells and verify reachability. A perfect maze has no cycles, so a `loops` fraction of dead-end walls is removed afterwards (Green, Procedural Content Generation for C++ Game Development, ch. 9).
- **Bitmask tiling.** Wall and floor tiles are picked by a 4- or 8-neighbour bitmask, shared by dungeon and cave exports (Green, ch. 9).
- **Template assembly.** Small hand-made pieces with colour-coded cells (legend file), picked by seed, transformed only as each piece's tags allow (flip x, flip y, rotate), placed on a slot grid, then validated (Pitt, Procedural Generation in Godot, p. 105, p. 169, p. 175). A slot marked with a kind can take any prop of that kind (Watkins, Procedural Content Generation for Unity Game Development, ch. 10). A fixed grid of room templates with marked re-roll slots chooses its guaranteed route first and may seal side rooms (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 3, p. 49-50).
- **Crafted anchors.** Hub and story pieces can be pinned to slots and the generator fills around them (Pitt, p. 19). A pinned piece can carry a checkpoint cell, and path distances between checkpoints score the layout (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 9, p. 163-164).
- **Guaranteed spine.** Carve a walker route from an entrance on one edge to an exit on the opposite edge first, then hang branches and chambers on it. The route makes the map completable with no repair pass, and its length is at least the grid width (Watkins, Procedural Content Generation for Unity Game Development, ch. 4). Alone it gives a tree with dead ends, so use it as the spine inside methods that can fail connectivity.
- **Wall-growth assembler.** Handmade rooms of irregular shape. A candidate wall tile has two wall neighbours on one axis and faces unused space; pick one, try a random room against it, add a door if it fits, else try again. Never carve a room to make it fit. Shipped numbers: a goal of 20 rooms with a cap of 1,000 tries (Short and Adams, Procedural Generation in Game Design, ch. 7, p. 64-69).


---

## 8. Battle map conventions for virtual tabletops

### 8.1 Pixels per grid square

| VTT | Default grid size | Notes |
| --- | --- | --- |
| Foundry VTT | 100 px per square | Scene configuration "Grid Size"; minimum 50 px; most maps use 70, 100, 140 or 200 px; whole numbers only [FVTT-SCN] (https://foundryvtt.com/article/scenes/, https://foundryvtt.com/article/content-creation-guide/) |
| Roll20 | 70 px per unit | Page "cell width" is a multiple of 70 px; maps are scaled to 70 px per square [R20-GRID] |
| Owlbear Rodeo | Detects or asks on upload; grid set per map in squares | No single fixed px default documented (unverified) [OBR-DOC] |
| Dungeondraft export | User chooses pixels per grid; 256 is the editor's native resolution (unverified) [DD] |

- Practical default for mapwright: 100 px per square for Foundry, 70 for Roll20, and keep the source at a multiple that scales cleanly (e.g. 140 or 200, or 280 = lcm-friendly for both 70 and 140) (design choice).
- Large maps: keep below roughly 8192 or 16384 px a side because of GPU texture limits in browsers (unverified; depends on hardware).

### 8.2 Universal VTT (.dd2vtt / .uvtt) JSON

The format was created by Megasploot, the developer of Dungeondraft, and is shared by Arkenforge, DungeonFog, Dungeon Alchemist, Mapforge and others under the name Universal VTT; `.dd2vtt`, `.df2vtt` and `.uvtt` are the same file underneath [UVTT][DD] (https://arkenforge.com/universal-vtt-files/, checked 2026-11-15). Coordinates are in **grid squares**, not pixels ("All positions and sizes are in the unit of 'Squares'"). The field names and types below match the Arkenforge field list (checked 2026-11-15) [UVTT][UBI]:

- `format`: decimal, "essentially a version number" [UVTT]. The spec lists no versions; the Foundry importer writes `0.2` when it merges several files [UBI] (checked 2026-11-15). Which number current Dungeondraft writes is unverified (closed source; read it from a real export).
- `resolution`:
  - `map_origin`: `{x, y}` in squares, usually `{0, 0}`.
  - `map_size`: `{x, y}` in squares.
  - `pixels_per_grid`: integer.
- `line_of_sight`: array of polylines; each polyline is an array of `{x, y}` points. These are the walls.
- `objects_line_of_sight`: same shape, for walls from objects. It is in the core field list [UVTT]; the Foundry importer treats it as optional and adds it to the walls only when its object-walls option is on [UBI] (checked 2026-11-15).
- `portals`: array of doors/windows, each with `position {x, y}`, `bounds` (two points, the door segment), `rotation` (radians), `closed` (bool), `freestanding` (bool).
- `environment`: `baked_lighting` (bool), `ambient_light` (hex colour string like `"ffffffff"`). The order is alpha first (AARRGGBB): the Foundry importer drops the first two characters of a light's `color` to get `#RRGGBB` [UBI] (ddimport.js, checked 2026-11-15); `ambient_light` uses the same 8-character form.
- `lights`: array, each with `position {x, y}`, `range` (squares), `intensity`, `color` (hex string), `shadows` (bool).
- `image`: "base64 encoded PNG or WEBP" of the whole map [UVTT] (checked 2026-11-15).

Minimal example mapwright should emit:

```json
{
  "format": 0.3,
  "resolution": {"map_origin": {"x": 0, "y": 0}, "map_size": {"x": 20, "y": 15}, "pixels_per_grid": 100},
  "line_of_sight": [[{"x": 2, "y": 2}, {"x": 8, "y": 2}, {"x": 8, "y": 6}, {"x": 2, "y": 6}, {"x": 2, "y": 2}]],
  "objects_line_of_sight": [],
  "portals": [{"position": {"x": 5, "y": 6}, "bounds": [{"x": 4.5, "y": 6}, {"x": 5.5, "y": 6}],
               "rotation": 0, "closed": true, "freestanding": false}],
  "environment": {"baked_lighting": false, "ambient_light": "ffffffff"},
  "lights": [{"position": {"x": 5, "y": 4}, "range": 6, "intensity": 1, "color": "ffeccd8b", "shadows": true}],
  "image": "<base64 PNG>"
}
```

Leave a gap in `line_of_sight` where each portal is, or the importer gets a wall over the door: the Foundry importer builds a separate door wall from each portal's `bounds` [UBI] (checked 2026-11-15). It also reads a portal with `closed: false` as a window (proximity sight and light, not a door unless its openable-windows setting is on), so write `closed: true` for every real door. That Dungeondraft itself leaves the gap is unverified (closed source; inspect a real export).

### 8.3 Foundry VTT scene JSON

A scene export (right-click scene, Export Data) contains, among others [FVTT-API]:

- `name`, `width`, `height` (px), `padding` (fraction, default 0.25), `background.src` (image path; older versions `img`).
- `grid`: in v12+ an object `{type, size, style, thickness, color, alpha, distance, units}`; type 1 = square, 2-5 = hex variants (older versions put `grid` as a number and `gridType` separately) [FVTT-API]. The Version 14 API lists exactly these eight grid fields, and `GRID_TYPES` is GRIDLESS 0, SQUARE 1, HEXODDR 2, HEXEVENR 3, HEXODDQ 4, HEXEVENQ 5 (https://foundryvtt.com/api/interfaces/foundry.documents.types.GridData.html, https://foundryvtt.com/api/variables/CONST.GRID_TYPES.html, checked 2026-11-15). The older number form was not re-checked.
- `walls`: array of WallDocument:
  - `c`: `[x0, y0, x1, y1]` in pixels.
  - `move`, `sight`, `light`, `sound`: sense levels; 0 = none, 10 = limited, 20 = normal (v11+ also 30 proximity, 40 distance) [FVTT-API].
  - `door`: 0 none, 1 door, 2 secret. `ds`: 0 closed, 1 open, 2 locked.
  - `dir`: 0 both, 1 left, 2 right.
- `lights`: array of AmbientLightDocument: `x`, `y` (px), `config: {dim, bright, color, alpha, angle, animation, ...}`, with `dim`/`bright` in grid distance units (e.g. feet), not pixels [FVTT-API].
- Pixel coordinates are measured from the top-left of the scene **including padding**: an image point (px, py) maps to (px + padX, py + padY) where padX = ceil(width * padding / gridSize) * gridSize (unverified exact rounding: the SceneData and GridData API pages give no formula and Foundry's source is not public, 2026-11-15; test against a real scene). Exporting with `padding: 0` avoids this.
- UVTT to Foundry: multiply square coordinates by `pixels_per_grid`, then add padding offset. Module "Universal Battlemap Importer" does this [UBI].

### 8.4 Roll20 dynamic lighting

- Roll20 walls are paths drawn on the Dynamic Lighting layer; doors and windows are separate objects in the updated dynamic lighting [R20-DL].
- Roll20 has no native UVTT import. Community API scripts (Pro subscription needed for API) import .dd2vtt walls, for example UniversalVTTImporter, which is in Roll20's own script repository at version 0.1.13: "Imports UniversalVTT files, `.dd2vtt`, as used by Dungeondraft", run with `!uvtt` [R20-API] (https://github.com/Roll20/roll20-api-scripts/tree/master/UniversalVTTImporter, checked 2026-11-15).
- Practical export for Roll20 users: a PNG at 70 px per square plus the UVTT file; tell the user an API script or a manual wall pass is needed.

### 8.5 Owlbear Rodeo

- Owlbear Rodeo 2.0 has fog and walls through its extension system; the "Dynamic Fog" extension draws walls (unverified) [OBR-DOC]. UVTT import exists through community extensions (unverified). Both stay unverified: docs.owlbear.rodeo answered 403 to WebFetch on 2026-11-15, so this needs a browser.
- Safe default: PNG with the grid size in squares stated in the file name, e.g. `crypt_20x15_100px.png`.

---

## 9. Design notes for mapwright

- One internal model for all three generators: a grid (or polygon set) plus walls as segments in grid units, portals as segments, lights as points. Every exporter converts from grid units.
- Exporters: PNG (stdlib zlib + struct), SVG, UVTT JSON, Foundry scene JSON, plain JSON for other tools.
- Every generator runs the proof rules in section 7 before writing files and prints the results.

---

## Sources (all accessed 2026-11-14 unless marked unverified)

- [PM01] Parish, Y. I. H. and Müller, P. "Procedural Modeling of Cities." SIGGRAPH 2001, pp. 301-308. https://doi.org/10.1145/383259.383292
- [CH08] Chen, G., Esch, G., Wonka, P., Müller, P., Zhang, E. "Interactive Procedural Street Modeling." ACM Transactions on Graphics 27(3), SIGGRAPH 2008. https://doi.org/10.1145/1360612.1360702
- [LE03] Lechner, T., Watson, B., Wilensky, U., Felsen, M. "Procedural City Modeling." 1st Midwestern Graphics Conference, 2003 (unverified venue details).
- [VA12] Vanegas, C. A., Kelly, T., Weber, B., Halatsch, J., Aliaga, D. G., Waddell, P. "Procedural Generation of Parcels in Urban Modeling." Computer Graphics Forum 31(2), Eurographics 2012. https://doi.org/10.1111/j.1467-8659.2012.03034.x
- [DCG] de Berg, M., Cheong, O., van Kreveld, M., Overmars, M. Computational Geometry: Algorithms and Applications, 3rd ed., Springer 2008 (doubly connected edge list, ch. 2).
- [SM-PORT] Hobby priority-queue ports of Parish and Müller, e.g. "citygen" write-ups (unverified; pick one before citing).
- [WAT-TGOS] watabou (Oleg Dolya), TownGeneratorOS. https://github.com/watabou/TownGeneratorOS (GPL-3.0, checked 2026-11-14)
- [WAT-MFCG] watabou, Medieval Fantasy City Generator. https://watabou.github.io/city.html (export formats unverified)
- [WAT-OPD] watabou, One Page Dungeon. https://watabou.github.io/dungeon.html (unverified)
- [WAT-BLOG] watabou's posts on itch.io and his Tumblr/Twitter about MFCG internals (unverified URLs).
- [ST-TALK] Stålberg, O. Talks on Townscaper and irregular grids, e.g. "Beyond Townscapers" / EPC 2018-2021 (unverified exact titles).
- [ME10] Merrell, P., Schkufza, E., Koltun, V. "Computer-Generated Residential Building Layouts." ACM TOG 29(6), SIGGRAPH Asia 2010. https://doi.org/10.1145/1882261.1866203
- [LO10] Lopes, R., Tutenel, T., Smelik, R. M., de Kraker, K. J., Bidarra, R. "A Constrained Growth Method for Procedural Floor Plan Generation." GAME-ON 2010.
- [MA10] Marson, F., Musse, S. R. "Automatic Real-Time Generation of Floor Plans Based on Squarified Treemaps Algorithm." International Journal of Computer Games Technology, 2010. https://doi.org/10.1155/2010/624817
- [RB-BSP] RogueBasin, "Basic BSP Dungeon generation." https://www.roguebasin.com/index.php/Basic_BSP_Dungeon_generation
- [RB-CA] RogueBasin, "Cellular Automata Method for Generating Random Cave-Like Levels." https://www.roguebasin.com/index.php/Cellular_Automata_Method_for_Generating_Random_Cave-Like_Levels
- [RB-DW] RogueBasin, "Random Walk Cave Generation" (drunkard's walk). https://www.roguebasin.com/index.php/Random_Walk_Cave_Generation (page exists, checked 2026-11-14)
- [JO10] Johnson, L., Yannakakis, G. N., Togelius, J. "Cellular Automata for Real-time Generation of Infinite Cave Levels." PCG Workshop 2010. https://doi.org/10.1145/1814256.1814266
- [WFC] Gumin, M. WaveFunctionCollapse. https://github.com/mxgmn/WaveFunctionCollapse (MIT licence per repository LICENSE; recheck before release)
- [KS17] Karth, I., Smith, A. M. "WaveFunctionCollapse is Constraint Solving in the Wild." FDG 2017. https://doi.org/10.1145/3102071.3110566
- [DO10] Dormans, J. "Adventures in Level Design: Generating Missions and Spaces for Action Adventure Games." PCG Workshop 2010. https://doi.org/10.1145/1814256.1814257
- [DO-CYC] Dormans, J. "Cyclic Generation" / talks on Unexplored, e.g. Procjam 2017 and Game Developer article (unverified exact venue).
- [BTB-CYC] Boris the Brave. "Dungeon Generation in Unexplored." https://www.boristhebrave.com/2021/04/10/dungeon-generation-in-unexplored/
- [RBG-HEX] Patel, A. (Red Blob Games). "Hexagonal Grids." https://www.redblobgames.com/grids/hexagons/
- [DMG14] Wizards of the Coast. Dungeon Master's Guide (5e), 2014, optional diagonal rule (unverified page).
- [PF2] Paizo. Pathfinder Core Rulebook, 2nd ed., movement on a grid (unverified page).
- [FVTT-SCN] Foundry VTT Knowledge Base, "Scenes." https://foundryvtt.com/article/scenes/
- [FVTT-API] Foundry VTT API docs: SceneData, WallData, AmbientLightData. https://foundryvtt.com/api/ (field names for GridData, WallData and SceneData checked 2026-11-15 against the Version 14 docs, 14.370; sense, door and direction values not re-checked)
- [UBI] "Universal Battlemap Importer" Foundry module. https://foundryvtt.com/packages/dd-import (checked 2026-11-14: by Moo Man, imports Dungeondraft, DungeonFog and Arkenforge exports, v6.1.1 verified for Foundry 14)
- [UVTT] Arkenforge, "Universal VTT files", with the developer field list. https://arkenforge.com/universal-vtt-files/ (checked 2026-11-15). Dungeondraft publishes no spec of its own that this pass found.
- [DD] Dungeondraft, export documentation. https://dungeondraft.net/ (unverified)
- [R20-GRID] Roll20 Help Center, "Page Settings" (70 px units). https://help.roll20.net/
- [R20-DL] Roll20 Help Center, "Dynamic Lighting." https://help.roll20.net/
- [R20-API] Roll20 API script library, UniversalVTTImporter 0.1.13. https://github.com/Roll20/roll20-api-scripts/tree/master/UniversalVTTImporter (checked 2026-11-15)
- [OBR-DOC] Owlbear Rodeo documentation. https://docs.owlbear.rodeo/ (unverified details)

## Flags added in session 17 (2026-11-16)

- `gen battle --density sparse|normal|dense` (CLI default `normal`). Share of squares holding a feature (rock, ruin wall, tree, door): sparse is the old map (mean 0.136 square, 0.075 hex over seeds 1-30), normal 0.22, dense 0.32 (measured 0.220-0.227 and 0.320-0.328). Extra cover is tree clumps and lone boulders from its own random stream (4000), so the base map's draws are unchanged; a clump that splits the open ground is taken back, a boulder needs an all-floor ring, nothing sits beside a door. Trees block movement (TREE is not passable). Recipes without `params.density` (older ones, or the Python API default) regenerate as sparse.
- Battle maps now draw a legend box (bottom right, untitled, map colours) listing only the cell kinds on the map: rock or ruined wall, trees, doorway. Labels avoid the box. The SVG canvas size is unchanged, so the hex PNG export and the whole-pixel grid stay as they were.
- `gen dungeon --method cyclic --branches N` (0 to 8, default none): dead-end side branches of one or two cells, each hanging off a non-goal node by a plain edge, so the cycle rank is unchanged and no key or lock moves. A branch's first door is secret 40% of the time (purple S); its last room holds treasure always behind a secret door, else 60% (gold disc). Features `treasure` and `secret door` go to features.geojson. Drawn from stream 5000; without the flag the map is byte-identical to 0.10.x (checked on seeds 1, 5, 9, 13, 21, 30).
- System diagrams: the habitable-zone key appears only when the green band is drawn. The schematic draws the band only around planets inside the zone; with none, the footer says "habitable zone a-b AU (no planet in it)" (L-041, closed).
