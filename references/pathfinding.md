# Pathfinding: reference for mapwright

Search over grids, graphs and meshes: which algorithm, which heuristic, how games speed it up, how to hand a map to an engine's navigation, how to cost travel over generated land, and how to use search to test a map. Each claim cites a source in brackets, keyed to the list at the end. "(unverified)" means it was written from memory, or from a search snippet, and the source was not read on 2026-11-15. Check these before code depends on them. Statements about mapwright's own code were read from `scripts/` on the same day.

Related files:

- [game-map-generation.md](game-map-generation.md): how shipped games build the maps that these searches run on.
- [cities-and-dungeons.md](cities-and-dungeons.md), section 6 (hex and square grid maths) and section 7 (the BFS reachability proof rule).
- [realistic-land.md](realistic-land.md), section 10 (roads and borders by least-cost search).
- [scifi-maps.md](scifi-maps.md), section 4 (jump routes and proximity graphs).
- [games-film-print.md](games-film-print.md), section 4 (navigation mesh parameters).

---

## 1. Graph search

### 1.1 Which algorithm

From Red Blob Games [RBG-A]:

| Need | Use |
|---|---|
| Paths to or from all cells, every step costs the same | Breadth-first search. It "explores equally in all directions" |
| Paths to or from all cells, costs vary | Dijkstra. It "takes into account movement costs" |
| One goal, or the nearest of a few | A*. It "explores more towards a single destination" |
| Fast and rough | A* with an inflated heuristic, in preference to greedy best-first |

- Greedy best-first orders the frontier by the estimate to the goal alone. It is quick in open ground, but "it may not find the shortest path" [RBG-A]. Its trap is the concave obstacle: it runs into the pocket, then crawls around the wall, and keeps the bad route.
- Early exit: stop when the goal is taken off the queue, not when it is first put on. Only then is its cost final when costs vary [RBG-A].
- Many goals at once: add one extra node joined to every goal and search from it [RBG-TD].

### 1.2 A*

- Published in 1968 by Hart, Nilsson and Raphael at Stanford Research Institute, for the robot Shakey [WP-A]. The paper itself was not read.
- A* expands the node with the lowest f(n) = g(n) + h(n): cost so far plus estimated cost to go [WP-A].
- Admissible: h never exceeds the true remaining cost. Then the path returned is a shortest one [WP-A][RBG-A].
- Consistent (monotone): h(x) <= d(x, y) + h(y) for every edge. Then A* never has to process a node twice [WP-A].
- Admissible but not consistent: a node may need to be re-opened when a cheaper route to it turns up. Code that keeps a closed set and never re-opens is then wrong, silently [WP-A].
- With h = 0 everywhere A* is Dijkstra [WP-A].
- Memory is the usual limit: every generated node is kept [WP-A].

### 1.3 The right heuristic for the grid

From Amit Patel's heuristics page [RBG-H], with dx = |x - goal.x|, dy = |y - goal.y|, D the cost of a straight step and D2 the cost of a diagonal step:

| Movement | Heuristic | Formula |
|---|---|---|
| Square, 4 neighbours | Manhattan | `D * (dx + dy)` |
| Square, 8 neighbours, diagonal costs the same | Chebyshev | `D * max(dx, dy)` (the next row with D2 = D) |
| Square, 8 neighbours, diagonal costs sqrt(2) | Octile | `D * (dx + dy) + (D2 - 2 * D) * min(dx, dy)` |
| Any angle | Euclidean | `D * sqrt(dx * dx + dy * dy)` |
| Hexagons, 6 neighbours | Hex distance | `(|dq| + |dr| + |ds|) / 2` in cube coordinates; see [cities-and-dungeons.md section 6](cities-and-dungeons.md#6-hex-and-square-grids) |

- What the scale of h does [RBG-H]: at 0, Dijkstra. Never above the true cost: shortest path, more nodes the lower h is. Exactly the true cost: almost no wasted work. Sometimes above: faster, shortest path no longer promised. Far above g: greedy best-first.
- Units: "The units (meters, minutes, etc.) returned by the heuristic should match the units used by the cost function." Test on an empty map with even costs: h at the start must equal the cost of the path found [RBG-H].
- With terrain costs, D must be the cheapest step anywhere on the map, or h overestimates on cheap ground (follows from the definition of admissible).
- Using Manhattan on an 8-neighbour grid overestimates. Using Euclidean on a 4-neighbour grid is admissible but weak.

### 1.4 Ties

Many grid paths have the same cost, so A* can flood a wide band of equal f. Fixes from [RBG-H]:

- Scale h up a hair: `heuristic *= (1.0 + p)`, with p below (cheapest step) / (longest expected path), for example p = 1/1000 for paths under about 1000 steps. This breaks admissibility by a hair.
- Prefer cells near the straight line from start to goal: add `abs(dx1 * dy2 - dx2 * dy1) * 0.001`, where (dx1, dy1) runs from the current cell to the goal and (dx2, dy2) from the start to the goal. Paths look good in open ground and odd near obstacles.
- Among equal f, take the newest entry first.
- For reproducible output, end the queue key with a stable value such as the cell index. Never let the tie fall to object identity or insertion accidents. mapwright's road search pushes `(f, g, cell)`, so ties resolve by lower g, then lower cell number.
- Float ties: sqrt(2) costs make sums differ in the last bits by route order. Compare with a tolerance, or use whole-number costs such as 10 and 14 (common practice, no source read).

### 1.5 Weighted and bidirectional search

- Weighted A*: multiply an admissible h by a factor above 1. The path costs at most that factor times the optimum [WP-A].
- Bidirectional search runs from both ends and stops when the two frontiers prove no better meeting point exists. The first meeting is not always the best one. It needs reversible edges or a reversed graph (textbook material, not fetched: unverified).

---

## 2. Grid speed-ups

mapwright's grids are small (a dungeon is tens of cells on a side), so plain A* with `heapq` is enough. This section is for users whose game runs thousands of queries.

### 2.1 Jump Point Search

Harabor and Grastien, AAAI 2011 [JPS]:

- Setting: undirected uniform-cost grid maps, 8 neighbours, each cell traversable or not, straight steps cost 1 and diagonal steps sqrt(2).
- Idea: from each node, prune neighbours that can be reached as cheaply without passing through it, then "jump" in a straight or diagonal line until a node with a forced neighbour, or the goal. Nodes between two jump points are never put on the queue.
- Guarantee: "fast, optimal and requires no memory overhead", and no preprocessing.
- Speed: "can speed up A* by an order of magnitude and more". The author's blog gives 3 to 15 times on Adaptive Depth maps, 2 to 30 on Baldur's Gate, 3 to 26 on Dragon Age and 3 to 16 on Rooms; the low figure is for short paths. Gains come from open areas with many equal paths [JPS-B].
- Limit: uniform cost only. Terrain weights, one-way edges and hexes are outside the paper.

### 2.2 Hierarchical search (HPA*)

Botea, Müller and Schaeffer 2004 [HPA]:

- Cut the grid into square clusters. Find entrances on cluster borders. Build an abstract graph of entrances with the cost of crossing each cluster. Search the abstract graph, then refine each leg inside its cluster, then smooth.
- Reported: up to 10 times faster than a highly tuned A*, with paths within 1 percent of optimal (unverified: abstract seen in a search result; the paper's PDF returned 404). Cluster size 10x10 (unverified).
- Use: very large maps, or many agents, where a slightly long path is fine. Clusters can be rebuilt one at a time when the map changes.

### 2.3 Precomputed distances

From [RBG-H]:

- A table of the true distance between every pair of cells is a perfect heuristic (a "distance oracle"). A path database stores the next step for every pair. Most game maps are too large: a 100x100 grid has 10,000 cells and 100 million pairs.
- Landmarks: store distances from a few chosen points and bound h from them by the triangle inequality ("differential heuristics", ALT, 2004).

### 2.4 Goal bounding

Rabin and Sturtevant, Game AI Pro 3 [GB]:

- For every node and every edge out of it, precompute a bounding box (4 values) of all goals that are reached optimally through that edge. At run time, skip an edge if the goal is outside its box.
- Limits stated: the map must be static; 4 values per edge per node in memory; precomputation is O(n squared) in the number of nodes.
- Speed in their test: 8.2 times faster than A* alone, and JPS+ with goal bounding 7.2 times faster than JPS+.
- It works on any graph, including waypoint graphs and navigation meshes.

---

## 3. Any-angle and smooth paths

### 3.1 Smoothing a grid path

"A* with post-smoothing" in Nash, Daniel, Koenig and Felner 2007 [TH]: walk the path; while the current vertex has line of sight to the vertex after next, drop the one between. It gives "significantly shorter paths than A* but is not guaranteed to find shortest paths", because the grid path it starts from may hug the wrong side of an obstacle.

### 3.2 Theta*

From the same paper [TH]:

- The loop is A*. The change is in the update: when expanding s and looking at its neighbour s2, if parent(s) has line of sight to s2, try the path through parent(s) straight to s2. Otherwise use the grid edge as A* does. A parent need not be a neighbour.
- Uses straight-line distance as h.
- "Basic Theta* is simple, fast and finds short and realistic looking paths, but is not guaranteed to find shortest paths". In the paper's counter-example the paths are under 0.2 percent longer than the minimum.
- Cost: one line-of-sight test per update. Lazy Theta* delays these tests [WP-TH].

### 3.3 The funnel algorithm

Mikko Mononen's "Simple Stupid Funnel Algorithm" [FUN]:

- Input: the list of portals along a corridor of polygons. A portal is the left and right end of the edge shared by two polygons. The start is the first portal and the goal the last.
- State: an apex and a left and right funnel side. For each portal, try to narrow each side. If a new point crosses the opposite side, that side's point becomes a corner of the path and the new apex, and the scan restarts from there.
- The side test is the sign of twice the triangle area (a 2D cross product), so no angles are computed.
- Portals must already be shrunk by the agent radius.
- Recast and Detour work this way: a query first finds a strip of polygons, then refines it by string pulling [RC].

---

## 4. Many units, one goal

### 4.1 Dijkstra maps

From the RogueBasin article by Brogue's developer [DM]:

- Set goal cells to 0 and all other floor cells to a very high number. Repeat over all floor cells: if a cell is more than 1 above its lowest neighbour, set it to that neighbour plus 1. Stop when nothing changes. Each cell then holds its step distance to the nearest goal, and a unit "rolls downhill".
- A breadth-first search from the goals gives the same field in one pass [RBG-TD].
- Flee map: take the map of distance to the player, multiply every value by about -1.2, and relax again. Monsters rolling downhill run away, and round corners instead of into them.
- Auto-explore: goals are the unseen cells; recompute each turn.
- Combined desires: one map per goal type, one weight per monster per map; each turn move to the neighbour with the best weighted sum.
- Brogue also uses one to warn when a levitation potion will run out over lava.

### 4.2 Flow fields

- Tower defence form: one breadth-first search from the goal over the whole map. "Instead of running A* once per enemy, we can run an algorithm once". The flow field is the direction to the lower neighbour, the negative gradient of the distance field [RBG-TD].
- Supreme Commander 2, from Elijah Emerson's chapter [FF]: the map is cut into sectors of 10x10 grid squares of 1 metre, joined by portals. Three fields per sector:
  - Cost field: 8 bits, 1 to 254 for path cost, 255 for a wall.
  - Integration field: 24 bits, 16 for the summed cost to the goal and the rest for flags such as line of sight.
  - Flow field: 8 bits, 4 for an index into a direction table and 4 for flags.
- A path request runs A* over the portal graph, then builds flow field tiles only for the sectors on the route. The integrator spreads a wave front out from the goal. Units that have line of sight to the goal ignore the field and steer straight at it.
- Use when many units share a goal. Cost is per map cell, not per unit.

### 4.3 Influence maps

A grid where each unit adds a value that falls off with distance, summed per side. Used for where to stand and what to avoid, as input to costs, not as paths [IM] (introduction of the chapter read; the propagation formulas were not).

---

## 5. Changing maps

- LPA* (Lifelong Planning A*) keeps two values per vertex: g, and rhs, a one-step lookahead from its neighbours' g. A vertex is locally consistent when the two are equal. After an edge cost changes, only vertices made inconsistent are queued and repaired, with key [min(g, rhs) + h; min(g, rhs)] [DL].
- D* Lite builds on LPA* and searches from the goal toward the moving agent, so stored values stay useful as the agent advances. It "implements the same behavior as Stentz' Focussed Dynamic A* but is algorithmically different" and is shorter [DL]. Stentz's D* dates from 1994. The family ran on Mars rover prototypes and the winning DARPA Urban Challenge car [WP-D].
- When to simply run A* again: the map is small, changes are rare, or the change is close to the agent, where most of the stored tree is invalid anyway. This covers nearly every mapwright use. Incremental search pays when one long-lived query sees many small far-off changes (judgement, no source).
- Engines signal changes instead: Roblox fires `Path.Blocked` with the index of the blocked waypoint and expects a recompute [RBX]. Unreal offers navigation mesh generation modes "Static", "Dynamic" and "Dynamic Modifiers Only" [UE].
- Rule for any cache: store a map version with every cached path or field, and drop it when the version moves.

---

## 6. Navigation meshes

### 6.1 What they are

"A navmesh is a simplified view of the traversable area of a game world". Polygons are the graph nodes and shared edges are the links. A mesh is built for one agent size: radius, height, steepest walkable slope and highest step [RC]. Typical values are in [games-film-print.md section 4](games-film-print.md#4-navigation-meshes).

### 6.2 How Recast builds one

Recast rasterises the input triangles into voxels, filters out voxels where the agent cannot stand, splits the walkable voxels into regions, and re-triangulates the regions into polygons [RC-S]. The sample build calls, in order [RC]:

1. `rcCreateHeightfield`, `rcMarkWalkableTriangles`, `rcRasterizeTriangles`: voxelise; mark by slope.
2. `rcFilterLowHangingWalkableObstacles`, `rcFilterLedgeSpans`, `rcFilterWalkableLowHeightSpans`: steps, ledges, low ceilings.
3. `rcBuildCompactHeightfield`, then `rcErodeWalkableArea`: shrink the walkable area by the agent radius.
4. `rcBuildDistanceField`, `rcBuildRegions`: split into regions.
5. `rcBuildContours`, `rcBuildPolyMesh`, `rcBuildPolyMeshDetail`: outlines, polygons, height detail.

Recast is under the Zlib licence and is the builder inside Unity, Unreal, Godot and O3DE [RC-S].

### 6.3 What each engine offers

| Engine | Offer | Numbers and limits |
|---|---|---|
| Unity (AI Navigation package) | A NavMesh Surface component bakes a mesh for one agent type from render meshes or physics colliders, plus terrains. Areas carry costs. Modifiers and links adjust it [UN] | Voxel size defaults to a third of the agent radius. Tile size defaults to 256 voxels. 29 custom areas beside Walkable, Not Walkable and Jump [UN] |
| Unreal | Builds a navigation mesh from level collision, split into tiles and polygons. "Each polygon is assigned a cost". Links join separate surfaces. Avoidance by RVO or the Detour crowd manager [UE] | Generation modes Static, Dynamic, Dynamic Modifiers Only [UE] |
| Godot | `NavigationServer2D` and 3D search navigation polygons held by region nodes; links join distant points with a cost; layers filter regions. `AStar2D` searches a hand-built point graph, and `AStarGrid2D` is the same for a grid with no manual wiring [GD] | Obstacles affect avoidance only, not paths. Leave a margin between navigation polygon edges and colliders [GD] |
| Roblox | `PathfindingService:CreatePath` with agent parameters, then `ComputeAsync`. Materials and labelled modifier parts carry costs; `PathfindingLink` joins gaps [RBX] | Defaults: radius 2, height 5, can jump, cannot climb, waypoint spacing 4. Start to goal at most 3,000 studs in a straight line. A search may give up past 20,000 nodes. Waypoints below Y -65,536 or above 65,536 are ignored. A cost of `math.huge` blocks a material [RBX] |

### 6.4 What a map exporter should hand over

mapwright does not bake meshes; engines do that from geometry. Two hand-overs cover every engine above:

- Walkable polygons: floor outlines with holes, in map units, each with an area class (floor, door, water, road, rough). Unity, Unreal and Godot regions take these as geometry or as modifier volumes. The wall segments and door portals already written for Universal VTT bound the same space.
- A cost grid: one number per cell, 0 for blocked and 1 upward for cost, plus the neighbour rule (4, 8 or hex) and whether corners may be cut. Godot's `AStarGrid2D`, a Tiled tile property, or a Roblox material map can be filled from it.

Either way, export the agent size the map was checked for, and the entrance and exit points.

---

## 7. Grids, costs and doors

### 7.1 Square grids

- Choose 4 or 8 neighbours once, and use the same rule in the generator, the checker and the export.
- Corner cutting: a diagonal step from (x, y) to (x+1, y+1) passes the corners of (x+1, y) and (x, y+1). The strict rule allows it only when both are open. The loose rule needs one. Allowing it with neither lets paths slip between two walls that touch at a corner. The JPS paper's grid simply says "Moves involving non-traversable (obstacle) nodes are disallowed" [JPS], and implementations differ on what that means for corners, so state the rule.
- mapwright's dungeon and square battle maps use 4 neighbours for the reachability bar. Anything reachable with 4 is reachable with 8, so the bar is safe for tables that allow diagonals.

### 7.2 Hex grids

Coordinates, distance, neighbours, rounding and line drawing are in [cities-and-dungeons.md section 6](cities-and-dungeons.md#6-hex-and-square-grids). For search: six neighbours, hex distance as h, no corner problem. mapwright stores battle hexes in offset form and has a hex distance in the sector code.

### 7.3 Costs

- Put the cost on the step, usually by the cell being entered. Keep the cheapest cost on the map for the heuristic (section 1.3).
- If the cost depends on direction (slope, current, one-way door), the graph is directed. Then a to b and b to a must be computed separately, and "reachable" splits into "can get there" and "can get back".
- A blocked step is no edge, not a huge number. Huge numbers leak into sums and heuristics.

### 7.4 Doors and keys

- Search state is (cell, set of keys held). With k keys that is up to 2^k copies of the map, fine for small k.
- If keys are never used up, the cheaper test is the repeated flood fill in [the dungeon proof rules](cities-and-dungeons.md#proof-rules-for-dungeons): flood, collect keys, open their doors, repeat.
- Fuel, jump range and levitation turns are the same pattern: (cell, amount left).

---

## 8. Travel on generated worlds

### 8.1 Least-cost roads

What mapwright does now, from `Router` in `scripts/mpw_human.py`:

- Step cost between neighbouring cells: distance x (1 + 60 x gradient squared) x terrain factor of the entered cell (1.0 for grassland up to 2.5 for ice).
- Entering a river cell that has no road yet adds a bridge cost: distance x min(6, 1 + 0.2 x flow / river threshold). Wide rivers cost more to bridge.
- A cell that already carries a road costs 0.35 of normal, so later roads join earlier ones into trunks.
- Sea and lake cells are not passable. Bar 10 of `check` asserts no road cell is in water.
- The search is A* when a goal point is given, with h = 0.35 x straight-line distance, else Dijkstra to the nearest cell of a target set. h is admissible because no step costs less than 0.35 of its length.
- `connect_all` then joins every settlement on a landmass into one road network, cheapest link first. Bar 9 asserts it.

Background is in [realistic-land.md, Roads](realistic-land.md#roads). Fords fit the same model: a low bridge cost where flow is small.

### 8.2 Sea and river routes

Not built. The usual model (no source read): a second graph over water cells; ports are the only joins between the land and water graphs and carry a loading cost; river travel downstream is cheaper than upstream, so river edges are directed.

### 8.3 Travel time and Tobler's hiking function

- A travel-time map (isochrones) is one Dijkstra run from the origin with step cost in hours, then contours of the result at chosen intervals.
- Tobler's function for walking speed on a slope [TOB]: W = 6 x exp(-3.5 x |S + 0.05|) km/h, where S = dh/dx is the slope as rise over run (the tangent of the angle), positive uphill.
- Fastest is 6 km/h at S = -0.05, a gentle descent of about 2.86 degrees. On the flat it gives 5.04 km/h [TOB].
- Off-path travel: multiply by 3/5. On horseback: multiply by 5/4 [TOB].
- As pace: p = 0.6 x exp(3.5 x |m + 0.05|) seconds per metre [TOB].
- Source chain: Tobler's 1993 technical report, fitted to data from Eduard Imhof (1950) [TOB]. The report itself was not read.

Values computed from the formula:

| Slope S | -0.40 | -0.20 | -0.10 | -0.05 | 0 | 0.05 | 0.10 | 0.20 | 0.40 |
|---|---|---|---|---|---|---|---|---|---|
| km/h | 1.76 | 3.55 | 5.04 | 6.00 | 5.04 | 4.23 | 3.55 | 2.50 | 1.24 |
| minutes per km | 34.0 | 16.9 | 11.9 | 10.0 | 11.9 | 14.2 | 16.9 | 24.0 | 48.3 |

- Uphill and downhill differ, so travel time is a directed cost.
- For A* on time, h = straight-line distance / fastest speed anywhere (6 km/h on foot, more if roads or horses are in play).
- Naismith's rule is the older rule of thumb: about 5 km/h plus an hour per 600 m climbed (unverified).

### 8.4 Route graphs in space

The outline is in [scifi-maps.md section 4](scifi-maps.md#4-jump-routes-and-hyperlane-graphs). What `gen sector` does, from `scripts/mpw_space.py`: a relative neighbourhood graph over the worlds, with the Euclidean minimum spanning tree added so the graph is connected at any radius. Routes within the jump number are marked "jump", longer ones "long". `check` asserts one connected component and counts bridges, the routes whose loss would split the map.

- Jump-range graph: an edge wherever two worlds are within range. It may be disconnected; the spanning tree shows which long links are needed.
- A spanning tree alone has no loops and every edge is a chokepoint. Extra short edges add choice. The count of bridges after adding them is the measure.
- Search is plain Dijkstra on parsecs or BFS on jumps. Fuel is a state variable (section 7.4).

---

## 9. Using pathfinding to test a map

| Test | How | Reads as |
|---|---|---|
| Reachability | Flood fill from the entrance; count against all passable cells | Must be equal. mapwright asserts this for dungeon, battle and deck recipes |
| Region count | Flood fill from every unvisited passable cell | 1 for a finished map; more means sealed pockets |
| Shortest critical path | BFS or Dijkstra, entrance to exit | Length in steps; share of all floor on the path |
| Farthest point | Largest value in the distance field from the entrance | Where a boss or exit belongs; The Binding of Isaac puts the boss in a farthest dead end [ISAAC] |
| Loops | Edges minus nodes plus 1 on the room graph | 0 is a tree: every wrong turn is a walk back |
| Chokepoints | Articulation points of the room graph or cell graph | Doors to guard; single points of failure |
| Width of connection | Minimum cut between entrance and exit (maximum flow with unit capacities) | Number of independent routes |
| Dead-end share | Rooms of degree 1, or floor beyond a chokepoint with nothing in it | Wasted walking |
| Heat map | Distance field from the entrance, drawn as a colour ramp | Shows pacing at a glance |
| Start fairness | Distance field from each start; compare distance to each resource type and the area each start reaches first | Ratio of worst to best start |

Notes:

- Articulation points: a depth-first search that records each vertex's depth and lowpoint. A non-root vertex v is a cut vertex if some child y has lowpoint(y) >= depth(v); the root is one if it has two or more children. Linear time; Hopcroft and Tarjan 1973 [BC].
- On a raw cell grid most corridor cells are articulation points. Keep those that cut off at least a few cells, as Brogue does: it stores the size of the region behind each chokepoint and ignores regions under 4 cells [BROGUE]. Or run the test on the room graph.
- The area each start reaches first is one Dijkstra run seeded with all starts at once, the same search that draws borders in [realistic-land.md](realistic-land.md#borders).
- Lock and key order is tested by the repeated flood fill (section 7.4).
- Every one of these is a number, so each can be a proof bar or an axis of an expressive-range plot ([game-map-generation.md section 10.3](game-map-generation.md#103-expressive-range)).

---

## 10. Common bugs

1. Heuristic not admissible: Manhattan on a grid that allows diagonals, or D set to the usual cost when cheaper ground exists. Paths come out slightly long, with no error.
2. Heuristic not consistent together with a closed set that is never re-opened (section 1.2).
3. Heuristic in other units than the costs: cells against metres, distance against time (section 1.3).
4. Diagonal steps through wall corners, or between two walls that touch at a corner (section 7.1).
5. Float ties: the path changes between platforms or runs because equal costs differ in the last bit. Give the queue a stable last key and compare with a tolerance.
6. Costs that differ each way by accident: neighbours built on the fly, with the cost read from the source cell in one place and the entered cell in another.
7. Goal test on push instead of on pop, with varied costs: returns a path that is not the cheapest (section 1.1).
8. Stale caches: a path or field kept after the map changed. Stamp with a map version.
9. Blocked cells given a large cost instead of no edge: the search walks through walls when no other route exists.
10. Unreachable goal: the search visits the whole map and returns nothing. Check region membership first by flood-fill labels.
11. Jump Point Search on a grid with terrain costs: wrong paths, since the pruning assumes uniform cost [JPS].
12. Queue entries that are out of date: with a binary heap and no decrease-key, skip any popped entry whose cost is above the best known for that cell (mapwright's road search does this).
13. Unordered containers deciding neighbour order: output changes with the hash seed. Iterate neighbours in a fixed order.

---

## 11. What mapwright has and lacks

Has, as internal code:

- A* and Dijkstra over the world cell graph for roads, with slope, terrain, bridge and reuse costs (`Router`, section 8.1).
- Flood fills: every floor square, room and door reached from the entrance (dungeon, battle), every room from the airlock (deck), regions of a cave.
- Graph tests: one connected route graph and a bridge count (sector); all settlements of a landmass joined by road (world, region).

Lacks: any command a user can call to get a path, a distance field, a travel time, a chokepoint list, or a navigation hand-over.

Candidate commands and the proof bar each would need:

| Command | Does | Proof bars |
|---|---|---|
| `path DIR --from A --to B` | Cheapest route between two points on any recipe (cells, hexes, worlds, deck squares) | Cost equals a no-heuristic Dijkstra on every fixture, to 1e-9. Cost re-summed from the listed steps equals the reported cost. Every step joins two neighbours and enters a passable cell: no path crosses a wall, water or a cut corner. On undirected maps A to B costs the same as B to A. Same inputs give byte-identical output |
| `path DIR --field --to B` | Dijkstra map or flow field to one or more goals, as JSON and a heat-map layer | Every reachable cell's value equals single-pair Dijkstra (all cells on small fixtures). Every reachable non-goal cell has a neighbour with a lower value. Following the flow from any cell reaches a goal with total cost equal to its value. Unreachable cells are null, never a large number |
| `path --jps` (speed only) | Jump Point Search on uniform square grids | JPS and A* return equal cost on at least 1,000 random pairs over the fixtures. Refuses any grid with terrain costs or hexes |
| `travel DIR --from A --mode walk` | Travel-time map with Tobler speeds, isochrone contours | Speeds match the table in section 8.3 to 0.01 km/h. A flat straight leg of d km takes d / 5.037 hours within 1e-6. Time never decreases along a shortest-path tree. On a slope A to B differs from B to A; on flat ground they are equal |
| `check DIR --chokepoints` | Articulation points and bridges with the size of what each cuts off; minimum cut entrance to exit | Equals brute force (remove each node, recount components) on small fixtures. Removing a reported chokepoint leaves at least one room unreachable; removing any other single cell leaves none |
| `check DIR --fair` | Per-start distances to resources and first-reach areas | Distances equal brute-force Dijkstra. Areas sum to the passable total. The reported ratio is reproducible |
| `export DIR --nav` | Walkable polygons and a cost grid (section 6.4) | Polygon area equals passable cells x cell area within 1e-9. Polygons are simple and do not overlap; no vertex lies inside a wall. Grid is w x h and blocked cells equal wall cells exactly. Flood fill on the re-read grid reaches the same count as `check` |

Order suggested: `path` and its field first (everything else reuses them), then `--chokepoints`, then `travel`, then `--nav`.

---

## Sources (all accessed 2026-11-15 unless marked unverified)

- [RBG-A] Patel, A. (Red Blob Games). "Introduction to the A* Algorithm." https://www.redblobgames.com/pathfinding/a-star/introduction.html
- [RBG-H] Patel, A. "Heuristics", Amit's A* Pages. https://theory.stanford.edu/~amitp/GameProgramming/Heuristics.html
- [RBG-TD] Patel, A. "Flow Field Pathfinding for Tower Defense." https://www.redblobgames.com/pathfinding/tower-defense/
- [WP-A] Wikipedia, "A* search algorithm". https://en.wikipedia.org/wiki/A*_search_algorithm. Original paper, not read: Hart, P. E., Nilsson, N. J., Raphael, B. "A Formal Basis for the Heuristic Determination of Minimum Cost Paths." IEEE Transactions on Systems Science and Cybernetics 4(2), 1968. https://doi.org/10.1109/TSSC.1968.300136
- [JPS] Harabor, D., Grastien, A. "Online Graph Pruning for Pathfinding on Grid Maps." AAAI 2011. https://harabor.net/data/papers/harabor-grastien-aaai11.pdf (PDF text read)
- [JPS-B] Harabor, D. "Jump Point Search", 2011-09-07. https://harablog.wordpress.com/2011/09/07/jump-point-search/
- [HPA] Botea, A., Müller, M., Schaeffer, J. "Near Optimal Hierarchical Path-Finding." Journal of Game Development 1(1), 2004 (unverified: PDF at webdocs.cs.ualberta.ca returned 404; page range differs between listings).
- [GB] Rabin, S., Sturtevant, N. R. "Faster A* with Goal Bounding." Game AI Pro 3, chapter 22. http://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter22_Faster_A_Star_with_Goal_Bounding.pdf (PDF text read)
- [TH] Nash, A., Daniel, K., Koenig, S., Felner, A. "Theta*: Any-Angle Path Planning on Grids." AAAI 2007. https://cdn.aaai.org/AAAI/2007/AAAI07-187.pdf (PDF text read)
- [WP-TH] Wikipedia, "Theta*". https://en.wikipedia.org/wiki/Theta*
- [FUN] Mononen, M. "Simple Stupid Funnel Algorithm", Digesting Duck, 2010-03-08. https://digestingduck.blogspot.com/2010/03/simple-stupid-funnel-algorithm.html
- [DM] "The Incredible Power of Dijkstra Maps", RogueBasin. https://www.roguebasin.com/index.php/The_Incredible_Power_of_Dijkstra_Maps
- [FF] Emerson, E. "Crowd Pathfinding and Steering Using Flow Field Tiles." Game AI Pro, chapter 23. http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter23_Crowd_Pathfinding_and_Steering_Using_Flow_Field_Tiles.pdf (PDF text read)
- [IM] Mark, D. "Modular Tactical Influence Maps." Game AI Pro 2, chapter 30. http://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter30_Modular_Tactical_Influence_Maps.pdf (introduction read)
- [DL] Koenig, S., Likhachev, M. "D* Lite." AAAI 2002. https://cdn.aaai.org/AAAI/2002/AAAI02-072.pdf (PDF text read)
- [WP-D] Wikipedia, "D*". https://en.wikipedia.org/wiki/D*
- [RC] Recast Navigation, `Docs/_1_Introduction.md`. https://github.com/recastnavigation/recastnavigation/blob/main/Docs/_1_Introduction.md
- [RC-S] Recast Navigation site. https://recastnav.com/
- [UN] Unity, AI Navigation 2.0 manual, "NavMesh Surface". https://docs.unity3d.com/Packages/com.unity.ai.navigation@2.0/manual/NavMeshSurface.html
- [UE] Epic Games, "Navigation System in Unreal Engine". https://dev.epicgames.com/documentation/en-us/unreal-engine/navigation-system-in-unreal-engine
- [GD] Godot documentation, "2D navigation overview". https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_introduction_2d.html
- [RBX] Roblox Creator Hub, "Character pathfinding". https://create.roblox.com/docs/characters/pathfinding
- [TOB] Wikipedia, "Tobler's hiking function". https://en.wikipedia.org/wiki/Tobler%27s_hiking_function. Original, not read: Tobler, W. "Three Presentations on Geographical Analysis and Modeling." NCGIA Technical Report 93-1, 1993.
- [BC] Wikipedia, "Biconnected component" (Hopcroft and Tarjan 1973). https://en.wikipedia.org/wiki/Biconnected_component
- [BROGUE] Brogue Community Edition, `src/brogue/Architect.c`, `analyzeMap`. https://github.com/tmewett/BrogueCE/blob/master/src/brogue/Architect.c
- [ISAAC] Boris the Brave. "Dungeon Generation in Binding of Isaac." https://www.boristhebrave.com/2020/09/12/dungeon-generation-in-binding-of-isaac/

Refused or unreachable on 2026-11-15: the HPA* paper PDF (404 at both University of Alberta addresses) and its publication database page (502). The Roblox `PathfindingService` class page loads but holds none of the limits; they are on the "Character pathfinding" guide cited above.
