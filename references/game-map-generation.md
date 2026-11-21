# How shipped games generate their maps: reference for mapwright

Method families behind the maps of released games, the games known to use each, what the method guarantees, how it usually fails, and the parameters where a primary source gives them. Each claim cites a source in brackets, keyed to the list at the end. "(unverified)" means it was written from memory, or from a search snippet, and the source was not read on 2026-11-15. Check these before code depends on them.

This file describes methods only. It holds no level data, room templates or map content from any game, and mapwright ships none.

It extends the other reference files and does not repeat them:

- [cities-and-dungeons.md](cities-and-dungeons.md), section 5: BSP rooms, cellular caves, drunkard's walk, the Wave Function Collapse loop, cyclic generation in outline, and the dungeon proof rules in section 7.
- [realistic-land.md](realistic-land.md): tectonics, erosion, rivers, climate, and section 10b on Johnson et al. 2010 caves and fBm noise.
- [games-film-print.md](games-film-print.md): Tiled, LDtk, engine heightmaps, Minecraft export, navigation meshes.
- Routes, costs and map tests by search are in [pathfinding.md](pathfinding.md).

---

## 1. Room-and-corridor roguelikes

The family: place rectangular rooms, join them with corridors, then decorate. Connectivity comes from how the corridors are ordered, not from a test afterwards.

### 1.1 Rogue: the 3x3 grid

- The 80x24 terminal is cut into a 3x3 grid of cells, each 26x8 [ROGUE].
- `rnd(4)` cells, so 0 to 3, are marked "gone" and get no room. A level has 6 to 9 rooms [ROGUE].
- Room width and height are random from 4 up to the cell size, and the room is offset inside its cell. A gutter column and row stay clear, so rooms never touch [ROGUE].
- Passages: start from a random cell, link a connected cell to an unconnected neighbour until all nine are linked (a spanning tree over the cell grid), then add 0 to 4 extra links between neighbours for loops. A gone cell gets a corridor junction in place of a door [ROGUE].
- Each corridor has at most two bends [ROGUE].
- Guarantee: connected by construction. Failure: every level is the same tic-tac-toe board, so levels feel alike. Source read: a walkthrough of the Rogue 3.6 `rooms.c`; its passage code is the article's own pseudo-code [ROGUE]. Dark rooms and maze rooms exist in Rogue 5.4: `rooms.c` makes a room dark when `rnd(10) < level - 1`, and a dark room becomes a maze one time in 15; `left_out = rnd(4)` drops up to three of the nine rooms (https://github.com/RoguelikeRestorationProject/rogue5.4/blob/master/rooms.c, checked 2026-11-16).

### 1.2 NetHack: rectangles, sorted rooms, ordered joins

From `mklev.c` of NetHack 3.6.1 [NH]:

- `makerooms()` keeps asking `rnd_rect()` for a free rectangle and puts a room in it until no rectangle is left or `MAXNROFROOMS` is reached (40, "max number of rooms per level", NetHack 3.6 `include/global.h`; the loop is in `src/mklev.c`, https://github.com/NetHack/NetHack/blob/NetHack-3.6/include/global.h, checked 2026-11-16).
- `sort_rooms()` orders rooms by left edge, so room index runs left to right.
- `makecorridors()` joins in three passes: `join(a, a+1)` for neighbours in the sorted order (with a 1 in 50 chance to stop early after each join), then `join(a, a+2)` where the two are not yet connected, then any pair still not connected. Connection sets are tracked in `smeq`.
- Then `rn2(nroom) + 4` extra corridors are dug with the `nxcor` flag. These may dead-end.
- Niches: `rnd((nroom >> 1) + 1)` small closets off a room wall. The vault is a closed 2x2 room made after the corridors, so it is not joined on purpose.
- Doors: 7 in 8 regular, 1 in 8 secret.
- Guarantee: the third pass forces one connected component. Failure: left-to-right joining gives a recognisable look, and dead-end corridors are part of it.

### 1.3 Angband: blocks, room profiles, vaults

- Level profiles are listed in `list-dun-profiles.h` and configured from `lib/gamedata/dungeon_profile.txt`. `cave_generate()` picks a profile, then calls its builder, named after the profile plus `_gen` [ANG].
- The `classic_gen`, `modified_gen` and `moria_gen` builders "divide the level into a grid of rectangular blocks where, in general, each block can only contain one room" [ANG].
- Rooms come from room types in `list-rooms.h`, built by `build_*` functions in `gen-room.c`. Other profiles are built from cavern and labyrinth chunks [ANG].
- Corridors: `do_traditional_tunneling()` joins the rooms, then `ensure_connectedness()` repairs what vault areas cut off [ANG].
- Vaults are hand-drawn dangerous treasure rooms stored as text in `vault.txt`, picked by depth range and type (lesser, medium, greater) (checked 2026-11-16 in Angband's `lib/gamedata/vault.txt`: types Lesser, Medium and Greater vault, each also in a "(new)" set, plus "Interesting room"; each entry carries `min-depth` and `max-depth`, https://github.com/angband/angband/blob/master/lib/gamedata/vault.txt).
- Guarantee: a repair pass after the fact. Failure: tunnels that wander and cross.

### 1.4 Brogue: room accretion, loops, lakes, machines

From `Architect.c` of Brogue CE [BROGUE]:

- Order in `digDungeon`: clear to granite, carve rooms, add loops, place doors, finish walls, design and fill lakes, run autogenerators, add machines, clean lake edges, build bridges, finish doors and walls.
- Accretion: `attachRooms(grid, profile, 35, 35)`, so 35 attempts and at most 35 rooms. Each attempt designs one random room in a scratch grid, then scans the map cells in shuffled order for a door site where the room fits with a one-cell border of rock. If nothing fits, the room is thrown away.
- Eight room shapes: cross, small symmetrical cross, small, circular, chunky, cave, cavern (fills a level) and the depth 1 entrance room. A room may get a hallway stuck to it, by the profile's `corridorChance`, but not in the last 5 attempts.
- Loops: `addLoops(grid, 20)`. A wall cell with floor on both sides becomes a door when the walking distance between the two sides is more than 20. Short cuts that save little are not made.
- Doors: 60 percent of door sites get a door. Secret door chance rises with depth to at most 67 percent.
- Lakes: blobs from at most 30x15 down to height 10, 20 placement tries each. A lake is kept only if `lakeDisruptsPassability` is false: a flood fill from one dry cell must still reach every dry passable cell. Shallow "wreaths" 1 to 2 cells wide surround deep liquid.
- Bridges: built over chasms only where the span is longer than 3 and the bridge shortens the walking distance by more than a depth-scaled ratio.
- Chokepoints: `analyzeMap` marks a cell as a chokepoint when closing it would cut off a region, and stores the size of that region in `chokeMap` (regions under 4 cells are ignored).
- Machines: a room-style blueprint picks a gate site whose `chokeMap` value lies between its minimum and maximum room size, then claims the cells behind that gate as its interior. Up to 50 candidates are collected. This is how vaults, puzzle rooms and guarded treasure sit behind exactly one door.
- Guarantee: every added room attaches to existing floor, and every later feature is tested against connectivity. Failure: none structural; the cost is a long list of hand-tuned checks.
- The designer's interview on this (Rock Paper Shotgun, "How do roguelikes generate levels") could not be fetched.

### 1.5 Dungeon Crawl Stone Soup: layouts plus vaults

From the level-design docs in the game's repository [DCSS1][DCSS2]:

- A vault is a hand-drawn map fragment in a `.des` file. `ORIENT: float` lets the builder put it anywhere and is the preferred setting. `encompass` makes the vault the whole level. `centre` and the compass values pin it to a part of the map. No `ORIENT` line makes it a minivault, placed after the level is built, on top of existing level space.
- Selection: `PLACE` pins a vault to a named level, `DEPTH` gives a range for random use, `TAGS` allow selection by tag, `WEIGHT` defaults to 10, `CHANCE` is out of 10000.
- A vault is used once per game unless tagged `allow_dup`. `uniq_NAME` allows only one vault of a group per game. `luniq` allows one per level.
- A vault tagged `layout` is a level layout, the code that draws the base level. Vaults may name the layouts they fit with `layout_` tags: corridors, rooms, passages, narrow_caves, open_caves, city, open, divisions, vaults, shoals, swamp, forest. No such tag means any layout.
- Connectivity: each `@` in a vault "will be connected to the rest of the level with a corridor". With no `@`, random traversable edge squares are used. Vaults count as non-passable for the level connectivity check unless tagged `transparent`. A cut-off region inside a transparent vault vetoes the level unless marked `opaque`.
- Guarantee: veto and rebuild. Failure: vault authors must think about exits; the docs warn "Make sure that no part of your entry level can be cut off!" [DCSS1].

### 1.6 Growth from a wall (Tyrant)

Mike Anderson's method: fill with rock, carve one room in the centre, then repeat: pick a random wall cell next to floor, pick a feature by weighted chance (room, corridor, arena, vault), test that its footprint plus a wall border is solid rock, carve it or give up and try again [RB-DBA]. Connected by construction. The weights set the style. Brogue's accretion is the same idea with shaped rooms.

### 1.7 What the family gives

| Property | How it is reached |
|---|---|
| Connected | Spanning tree over rooms (Rogue, NetHack), attach-only growth (Tyrant, Brogue), or repair pass (Angband) |
| Loops | Extra joins after the tree: 0 to 4 (Rogue), `rn2(nroom) + 4` (NetHack), distance over 20 (Brogue) |
| Set pieces | Vault files placed before or after the base layout (Angband, DCSS, Brogue machines) |
| Usual failure | Sameness of shape; long empty corridors; set pieces that block the only route unless tested |

mapwright today: `gen dungeon --method bsp` is this family (BSP rooms, L corridors, extra loops as 12 percent of the room count).

---

## 2. Template and chunk assembly

The family: people draw the rooms; code picks, places and joins them. The generator decides structure, never fine detail.

### 2.1 Spelunky: 4x4 rooms with a guaranteed path

From Darius Kazemi's write-up of the Spelunky Classic source [SPEL]:

- The level is 16 rooms in a 4x4 grid. A start room goes in the top row.
- Solution path: roll 1 to 5. On 1 or 2 move left, on 3 or 4 move right, on 5 move down. Hitting the side wall drops down and reverses direction. Dropping from the bottom row places the exit.
- Room types carry exit guarantees: type 1 has left and right exits; type 2 has left, right and bottom; type 3 has left, right and top; type 0 is off the path and has no guaranteed exit.
- A room the path drops out of becomes type 2. The room it lands in must be type 2 or 3.
- Every cell off the path gets a type 0 room.
- Each type has several hand-drawn templates with tiles that are filled in by chance; the write-up covers that in its second part (checked 2026-11-16 https://tinysubversions.com/spelunkyGen2/ : 8 to 16 templates per room type, 10x8 tiles each, with chance tiles).
- Guarantee: a route from entrance to exit that needs no bombs or ropes. Failure by design: off-path rooms can be sealed, which is what the player's tools are for.

### 2.2 Diablo: predungeon, then tiles, then pattern patches

From Boris the Brave's reading of Devilution, the fan reconstruction of the Diablo source [D1]:

- Every level fills a 40x40 grid of tiles. Generation has two steps: a "predungeon" walkability map, then conversion to tiles.
- Cathedral: up to 3 central 10x10 rooms and a corridor, then recursive "budding" of rooms off existing ones.
- Catacombs: recursive subdivision into rooms and hallways, then "fill voids" until at least 700 tiles are open.
- Caves: grow from a 2x2 room with 3 to 4 tile blocks, then erode; retry under 600 floor tiles.
- Hell: bud rooms inside a 20x20 quarter, then mirror both ways.
- Set pieces are pre-authored chunks, one per level. "Minisets" are small pattern-matched patches (about 3x3) for stairs and fixes. Tile substitution swaps in look-alike tiles and avoids repeats close together.
- Guarantee: a "lockout" check tests that the whole dungeon is walkable and restarts generation if not. Failure: restarts cost time; quality depends on the fix-up patterns.
- Diablo II uses hand-made preset rooms joined on a generated layout per area (unverified; 2026-11-16: no developer source known, not found).

### 2.3 Dead Cells: hand-built rooms on a hand-built graph

From Sébastien Bénard's article [DC]:

- Fixed by hand: the world layout, and a library of room templates per biome, each with a purpose (combat, treasure, merchant) and a set of entrances and exits.
- Also by hand: one "concept graph" per biome. It fixes the length of the level, the number of special rooms, how maze-like it is, and the distance from entrance to exit.
- Generated: for each graph node the algorithm tries a random room and keeps it if it meets the node's needs, else tries another.
- Monsters by density: the example is 250 combat tiles at 1 monster per 5 tiles, so 50 monsters, with per-type rules.
- The author later noted the brute-force fit was replaced with matching by exits, close to Wave Function Collapse.
- Guarantee: pacing and critical path are authored, so they hold in every seed. Failure: variety is bounded by the template count.

### 2.4 The Binding of Isaac: rooms grown on a grid

From Boris the Brave's reading of the game [ISAAC]:

- Floor plan on a 9x8 grid, start in the middle.
- Room count: `random(2) + 5 + level * 2.6`, so 7 or 8 on the first floor.
- Growth: a queue seeded with the start cell. For each cell and each of the 4 directions, give up if the neighbour is taken, if the neighbour already has more than one filled neighbour, if the count is reached, or on a 50 percent roll. Otherwise add the room and queue it.
- A cell that adds no neighbour is a dead end. The boss goes in the last dead end found, which is among the furthest. Other special rooms go on other dead ends.
- Reject and restart if the room count is wrong or the boss is next to the start.
- Secret room: an empty cell next to at least 3 rooms and no dead end. The rule loosens after 300 tries and again after 600, so it always places.
- Rooms are drawn from pools by difficulty; the first chapter's pool holds 174 normal rooms. Doors sit at the centre of each wall, so any two rooms join.
- Guarantee: connected, almost loop-free (the "more than one filled neighbour" test), boss far from start. Failure: fixed door positions limit room shapes.

### 2.5 Enter the Gungeon: authored flow graphs

From Boris the Brave's reading of the game [GUN]:

- Each stage has a few hand-authored "flows": directed graphs of room types with no positions. One stage has 4, another 8. Loops are authored in.
- The flow is rewritten: chains of random length, a choice between alternate branches, and "injected" nodes such as shops and secret rooms, each with a chance and conditions.
- Each node gets a hand-made room from a large pool (nearly 300 for the first stage), without repeats.
- Layout: the flow is cut into "composites" by removing the smallest loop first. Trees are laid out depth-first, attaching each room by a pair of exits that does not overlap, with up to 3 re-rolls. Loops are grown from both ends and closed with a small room or a pathfound corridor 4 to 30 units long.
- Guarantee: pacing is authored in the flow, so the order of fights, shops and boss never breaks. Failure: layout can fail and must retry.

### 2.6 Hades and Into the Breach: mostly hand-made

- Hades draws hand-built chambers from a pool per region and shows the next reward on each exit door. There is no spatial layout to solve (unverified, no developer source found; still none 2026-11-16).
- Into the Breach uses about 100 hand-designed 8x8 maps. Matthew Davis: "It was important to control the map design in a way that it didn't generate maps that aren't fun to play on." At 8x8, drawing 100 maps cost less than writing a generator [ITB].
- Lesson: when the map is small and every tile matters, authored maps plus random selection and random dressing beat generation.

---

## 3. Graph-first generation and grammars

The outline is in [cities-and-dungeons.md section 5.5](cities-and-dungeons.md#55-graph-first-and-cyclic-generation). Additions:

- Dormans and Bakkes 2011 treat missions and spaces as two structures generated in two steps, a mission graph first, then a space that fits it [DB11] (abstract read through a search result, paper not read).
- Unexplored, from Boris the Brave's write-up [UNEX]: each level starts as a 5x5 grid of graph nodes. The grid is doubled to add corridor cells, then expanded 5x to tiles. The generator has about 5000 find-and-replace rules in total and about 50 grammar modules for the floor plan. There are 24 cycle types. Each key holds an edge to its lock, which survives node shuffling. The lock and key data also ships with the level: the "Pray For Help" action finds what blocks the player and fixes it at run time.
- Zelda-like dungeons, from the metazelda library [MZ]: rooms are grouped in key-levels, where level n is what n keys can reach. The generator grows a spanning tree of rooms, raises the key-level at intervals and locks the edge it crosses, puts the goal in a dead end behind the boss, then "graphifies" by adding links between neighbours whose key-levels match or differ by one. The key for level n is placed in the hardest room of level n-1. The README calls the result "guaranteed to be solvable by construction". A stage that fails retries up to 20 times.
- Lock and key ordering rule for any generator: a key must be reachable using only keys found before it. Test with the repeated BFS in [the dungeon proof rules](cities-and-dungeons.md#proof-rules-for-dungeons), or with the state search in [pathfinding.md section 7](pathfinding.md#7-grids-costs-and-doors).
- Guarantee: structure and pacing come first, so they hold. Failure: laying the graph out in space can fail (crossing corridors, no room), so a retry loop is needed.

---

## 4. Node maps

The map is a small directed graph the player walks once. Generation is about choice and pacing, not space.

### 4.1 Slay the Spire

From a community write-up of the reverse-engineered rules [STS]. This is not a developer source.

- A grid 7 wide and 15 floors tall.
- Six paths are traced from floor 1 to floor 15. Each step goes to one of the 3 closest nodes on the next floor. The first two paths must start on different nodes. Paths may not cross. Nodes on no path are removed.
- Fixed floors: floor 1 is all monsters, floor 9 all treasure, floor 15 all rest sites. One boss node sits above and all floor 15 nodes lead to it.
- Other nodes are rolled by odds: monster 45 percent and elite 16 percent at Ascension 1 and above (53 and 8 below) [STS]; event 22, rest 12, shop 5 (unverified, the write-up shows them only in images; 2026-11-16: search found no text source for these numbers).
- Rules that override the roll: no elite or rest site below floor 6; elite, shop and rest site cannot follow each other along a path; a node with 2 or more exits must lead to different room types; no rest site on floor 14. A node that breaks a rule is re-rolled until it passes.
- Guarantee: every node lies on a start-to-boss path, and each run meets the same pacing beats. Failure: with few paths, choices can collapse into one line.

### 4.2 FTL and others

- FTL: each sector is a field of jump beacons joined when they are close, with the exit on the far side and a pursuing fleet that sweeps across as a clock. Sectors number about 20 beacons each (checked 2026-11-16 https://ftl.fandom.com/wiki/Sectors via search result: 19 to 24 beacons; a Subset forum survey says 20 to 24 including entrance and exit). The run is a tree of sectors chosen one column at a time (unverified; 2026-11-16: not checked, fan wiki fetch refused earlier).
- Into the Breach islands are fixed; the missions offered on them vary (section 2.6).

### 4.3 Checks for a node map

- Every node is on some path from a start to the goal.
- No two edges cross (compare the order of endpoints on adjacent floors).
- Count of distinct start-to-goal paths, and the minimum and maximum number of each room type along any path. These are the fairness numbers.

---

## 5. Noise and voxel worlds

Terrain is a function of position and seed, so the world can be made in pieces, in any order. The noise itself is covered in [realistic-land.md section 10b](realistic-land.md#10b-caves-and-noise-terrain).

### 5.1 Minecraft (Java Edition)

- Worlds are made of chunks 16x16 blocks wide [MC-WG].
- A chunk moves through ordered statuses: empty, structure_starts, structure_references, biomes, terrain (base terrain and liquids, then surface blocks, then carvers), features, light, spawn, full [MC-WG].
- Overworld biomes are picked from six noise parameters: temperature, humidity, continentalness, erosion, weirdness and depth. Only depth changes with height, by 1/128 per block [MC-WG].
- 1.18 raised the world to 384 blocks, from Y -64 to 319, moved the Overworld to the multi-noise biome source, and made terrain "independent from biomes": terrain shape comes first and biomes adapt to it. It added "cheese", "spaghetti" and "noodle" noise caves and aquifers with their own water levels, and blends old chunks into new ones [MC-118].
- Before 1.18, biomes were chosen first from stacked 2D layers and each biome set its own terrain height through depth and scale values (layer stack checked 2026-11-16 https://minecraft.fandom.com/wiki/Biome/Before_1.18 ; the height role is from secondhand posts only).
- Structures are why there are two early statuses: a structure's start is decided per chunk, then every chunk it touches records a reference, so a village is the same whichever chunk loads first [MC-WG] (the reason given here is an inference).

### 5.2 Terraria

- The world is finite and built once, up front: small 4200x1200 tiles, medium 6400x1800, large 8400x2400 [TER-SIZE].
- Generation is an ordered list of 109 passes (Desktop 1.4.4.9). It opens with Reset, Terrain, Dunes, Ocean Sand, Sand Patches, Tunnels, Mount Caves, Dirt Wall Backgrounds, Rocks In Dirt. Later passes include Jungle (20), Full Desert (22), Floating Islands (26), Underworld (31), Corruption (32), Dungeon (36) and Final Cleanup (109) [TER-WG].
- The method is "paint in order": each pass overwrites what earlier passes left. Order is the design. Failure: late passes can destroy early features, so each pass carries its own placement tests (practice figure, no single source; tunable default).

### 5.3 Valheim

- The world is cut into zones of 64 by 64 metres [VAL].
- Locations (points of interest) are assigned once at world generation from the seed: the game tries up to 100,000 times to place each location's quota, at most one per zone. The location's objects are only created when a player comes near. Vegetation is placed when a zone is first discovered [VAL].
- The world is a disc of radius 10,000 m plus a 500 m edge, and biomes depend on distance from the centre plus noise (radius and edge checked 2026-11-16 https://thunderstore.io/c/valheim/p/JereKuusela/Expand_World/v/1.4.0 , a mod's settings: 10000 + 500 = 10500 m; biome rule from [VAL]).

### 5.4 No Man's Sky

- Sean Murray's GDC 2017 talk "Building Worlds Using Math(s)" covers the terrain noise [NMS]. Only the session page was read. Details from memory: planets are density fields built from layered noise, polygonised from voxels around the player, and everything on a planet derives from its seed (unverified; 2026-11-16: GDC Vault talk is members only).

### 5.5 Chunks and seeds: rules that carry over

- A chunk's random stream is a hash of (world seed, chunk coordinates, pass name). Never draw from one shared generator in load order, or the world depends on the player's route (practice figure, no single source; tunable default. Minecraft's exact scheme not checked).
- A feature larger than a chunk needs a decision made in one place and read by all chunks it touches (Minecraft's two structure statuses), or a finite world generated whole (Terraria).
- Johnson et al. 2010 store one seed per cave grid and blend neighbours with extra automaton passes; see [realistic-land.md section 10b](realistic-land.md#10b-caves-and-noise-terrain).
- mapwright's seed rules are items 5 and 6 of [the checkable proof rules](cities-and-dungeons.md#7-checkable-proof-rules-implement-as-tests).

---

## 6. Simulation worlds

### 6.1 Dwarf Fortress

Tarn Adams, in a 2008 interview [DF], gives this order:

1. Elevation by midpoint displacement.
2. Temperature, "biased by elevation and latitude", and rainfall, later corrected for "orographic precipitation, rain shadows".
3. Drainage: "just another fractal, with values from 0 to 100".
4. Biomes are read off these fields; they are "not the basics". Example: rainfall of 66 or more with drainage under 50 is a swamp. Vegetation, savagery and good or evil are further fields.
5. Salinity is 100 at the ocean and falls off fast over land.
6. Erosion: pick mountain bases and run "temporary river paths" downhill, digging where they get stuck.
7. Real rivers are then forced to the ocean, lakes are bulged out, loops are removed, flow is summed to find tributaries, and rivers are named.
8. Regions are formed and named, then plant and animal populations are set: "a canvas for world history".

Worlds that fail checks are rejected and rerolled, and history is then simulated year by year (checked 2026-11-16 https://dwarffortresswiki.org/index.php/World_rejection : a world failing any rejection check is rerolled; history runs to the end year or a beasts-dead stop).

### 6.2 RimWorld

- The planet is a globe of hexagon tiles with 12 pentagons. Coverage can be 30, 50 or 100 percent [RW].
- Each tile holds a biome, elevation, temperature, rainfall in mm per year and a terrain class (flat, small hills, large hills, mountains) [RW].
- A seed fixes landmasses, rivers and mountains. Roads and faction bases may not be tied to it [RW].
- The local map is generated from the tile: terrain class sets how much rock, a river on the tile becomes a river across the map, caves can form in mountains. Sizes run 200x200 to 325x325 cells [RW]; the wiki names Small 200-225, Medium 250-275, Large 300-325 and does not state a default (corrected 2026-11-16 https://rimworldwiki.com/wiki/World_generation ; 250x250 as default is unconfirmed).
- This is the two-scale pattern mapwright already has in `gen world` and `gen region`: the parent fixes the facts, the child adds detail.

### 6.3 Caves of Qud: history first

- World generation starts from the history of five generated sultans. For each of five periods, new regions and locations are created (2 to 3 regions per period), then "the sultan history for that period is generated, using those regions and locations" [QUD].
- A few main-quest places are pre-built and fixed [QUD].
- Qud also uses Wave Function Collapse for parts of its maps [MS]; how is from Brian Bucklew's talk, which was not read (unverified; 2026-11-16: not reached).
- Contrast: Dwarf Fortress builds land, then history on it. Qud builds history and makes places to hold it.

---

## 7. Strategy maps

### 7.1 Civilization map scripts

- Each map type is a script (Python in Civilization IV, Lua in V and VI) that fills plot types, terrain, features and rivers, then calls a shared start-placement library (unverified; 2026-11-16: scripts not read, no primary source reached).
- "Continents" and "Fractal" scripts threshold a fractal height field at a sea level; grain sets the number and size of landmasses (unverified; 2026-11-16: scripts not read).
- Civilization V's `AssignStartingPlots.lua` divides land into regions by fertility, one per player, places a start in each, then adds resources near weak starts (community-checked 2026-11-16: https://modiki.civfanatics.com/index.php/AssignStartingPlots_(Civ5_Type) lists DivideIntoRegions with a fertility table, and CivFanatics posts say distribution is "based on land fertility, not land size"; the Lua itself was not read).
- Guarantee sought: comparable starts. Failure: balance by one score hides what matters (coast, neighbours, room to grow).

### 7.2 Age of Empires II random map scripts

A script has up to seven sections, and the game always runs them in this order whatever the file order [AOE]:

1. `<PLAYER-SETUP>`: how players are placed.
2. `<LAND-GENERATION>`: land origins are placed, then all lands grow at the same time until they fill their share or meet a border or another land.
3. `<ELEVATION-GENERATION>`: hills. They avoid player land origins by about 9 tiles.
4. `<CLIFF-GENERATION>`: cliffs avoid land origins by 22 tiles.
5. `<TERRAIN-GENERATION>`: terrain patches such as forests, in script order.
6. `<CONNECTION-GENERATION>`: replaces terrain along paths between land origins (roads, shallows). A connection that is not possible is not made.
7. `<OBJECTS-GENERATION>`: resources, units, buildings, in order. An object that finds no valid position is not generated, so the script must place the most important objects first.

Guarantee: none; the script author must order things so that failure hits unimportant objects. Fairness comes from placing each player's resources by distance rings around the start (practice figure, no single source; tunable default).

### 7.3 4X galaxies

- Stellaris picks star positions by galaxy shape (elliptical, spiral with 2 or 4 arms, ring), then joins stars into a hyperlane graph, with script settings for lane density and maximum lane length (unverified: the wiki refused the fetch; setting names `num_hyperlanes` and `max_hyperlane_distance` appear in community setup-scenario examples, e.g. https://steamcommunity.com/app/281990/discussions/0/1692662484242008327 (checked 2026-11-16 via search result; no Paradox documentation found)).
- The graph recipe that works: points by a density function, a minimum spanning tree so the galaxy is connected, then extra short edges for loops, then a check for chokepoints. See [scifi-maps.md section 4](scifi-maps.md#4-jump-routes-and-hyperlane-graphs) and [pathfinding.md section 8.4](pathfinding.md#84-route-graphs-in-space). mapwright's `gen sector` does this with a relative neighbourhood graph plus the spanning tree.

### 7.4 Hex strategy maps

Hex maths is in [cities-and-dungeons.md section 6](cities-and-dungeons.md#6-hex-and-square-grids). Start fairness is a path-distance question; see [pathfinding.md section 9](pathfinding.md#9-using-pathfinding-to-test-a-map).

---

## 8. Wave Function Collapse and constraint solving in shipped games

The algorithm is in [cities-and-dungeons.md section 5.4](cities-and-dungeons.md#54-wave-function-collapse). Paul Merrell described the method as "model synthesis" in 2007; Maxim Gumin's 2016 repository named it Wave Function Collapse. Bad North, Townscaper and Caves of Qud are the shipped games usually named [MS].

- Bad North: over 300 tiles were modelled by hand and their edges scanned for valid neighbours. Generation starts with water at the bottom and sky at the top and every tile possible elsewhere. Each tile "knows its navigability", where it can be entered and left, so that enemies can reach the houses. When constraints cannot be met the generator restarts from a saved state [TS]. Oskar Stålberg presented this at Everything Procedural 2018 [EPC].
- Townscaper: the grid is irregular, made from a hexagon grid split into quads with points then moved. Modules are corner pieces chosen in the manner of marching cubes. The solver runs each time the player adds a block, and where two cells cannot fit "it is actually allowed to fail silently". The player controls large shapes; the solver picks details [TS].
- Dead Cells moved its room fitting to exit matching, close to this method (section 2.3).
- What the method guarantees: local adjacency only. It gives no path, no connectivity and no large structure [WFC-EX]. Shipped uses add a second constraint (Bad North's navigability) or a person (Townscaper's player).
- Failure and extensions as a machine-learning book frames them (Summerville and others, Procedural Content Generation via Machine Learning, ch. 5; book rules, unverified on our tools): because the method only looks at neighbours, a small mismatch can grow into a gap that no tile fills, so contradictions rise with map size; count restarts per finished map and report that number as the method's cost. Two extensions: negative examples (tile pairs or patterns marked as never allowed, learned or listed by hand) and partial pre-fill, where the designer fixes some cells first and the solver completes the rest (Bad North's water and sky rows above are a case of it).
- Answer set programming: Smith and Mateas 2011 describe a design space as a logic program and let a solver return levels that meet every stated constraint [ASP] (citation and abstract through a search result). It shipped in the puzzle game Refraction, and a Warzone 2100 map generator named Diorama used it (both unverified, search snippets only; not rechecked 2026-11-16). Strength: hard guarantees such as "a solution exists and needs this tool". Cost: solve time grows fast with map size.

---

## 9. Open-world tooling

What large studios automate and what they place by hand. Only the session pages were read; talk contents are behind the GDC Vault paywall.

| Game | Source | Automated | By hand |
|---|---|---|---|
| Far Cry 5 | Carrier, GDC 2018 [FC5] | Tools that generate biomes, texture the terrain, set up freshwater networks and generate cliff rocks; built to refill large areas on each iteration | Fine-tuning of smaller locations. Houdini as the tool, and roads, fences and power lines as outputs (unverified; 2026-11-16: GDC Vault members only) |
| Horizon Zero Dawn | van Muijden, 2017 [HZD] | Run-time GPU placement around the player of plants, rocks, sounds, effects, wildlife and gameplay elements, from rules artists build in a graph editor | Painted inputs such as a tree line or a road, which the system reacts to |
| Ghost Recon Wildlands | Werle and Martinez, GDC 2017 [GRW] | A terrain tool chain and renderer for Ubisoft's largest open world | Terrain sculpted first, then roads, rivers and settlements laid by tools from hand-set points (unverified; 2026-11-16: GDC Vault members only) |

Pattern: people author inputs that are cheap to change (masks, splines, rules) and tools regenerate everything downstream. Nothing is placed directly that a rule could place. Landmarks, quest sites and anything a player must find stay hand-made.

---

## 10. Evaluation: is a generated map good

### 10.1 Solvable

Every shipped generator above either builds solvability in or tests and restarts:

| Game | Check | On failure |
|---|---|---|
| Diablo | whole dungeon walkable ("lockout") [D1] | restart |
| Brogue | flood fill after each lake [BROGUE] | drop the lake |
| DCSS | connectivity with transparent vaults [DCSS2] | veto the level |
| Isaac | room count, boss not beside start [ISAAC] | restart |
| Gungeon | room overlap [GUN] | re-roll up to 3 times |
| metazelda | each stage [MZ] | retry up to 20 times |
| Bad North | tile constraints [TS] | restart from saved state |

A restart must stay deterministic: derive attempt k's stream from (seed, k), and record k in the recipe.

### 10.2 Numbers worth measuring

- Critical path length: shortest route from entrance to exit, in steps, and as a share of all floor.
- Loops: independent cycles in the room graph (edges minus nodes plus one). Zero means every wrong turn is a walk back.
- Dead-end share and the length of the longest forced backtrack.
- Chokepoints, and what sits behind each (Brogue's use).
- Landmarks: at least one feature per region that tells the player where they are; one set piece per level is Diablo's rule [D1].
- Pacing: the order and spacing of fights, rests and rewards along the critical path. Gungeon and Dead Cells author it; Slay the Spire enforces it by rules.

How to compute these is in [pathfinding.md section 9](pathfinding.md#9-using-pathfinding-to-test-a-map).

### 10.3 Expressive range

Smith and Whitehead 2010 [ER]: pick metrics that describe a level, generate many levels, and plot 2D histograms of the scores. "This allows us to view peaks of commonly created content and holes in the generative space." Their graphs use 10,000 generated levels and two metrics, linearity and leniency. Re-running after a parameter change shows what the parameter does. The method fits any generator: for a dungeon use critical path length against loop count.

### 10.4 Sameness

- Kate Compton's "10,000 bowls of oatmeal": outputs can all differ and still feel the same; what matters is difference a person can see (checked 2026-11-16 through a secondary source, https://gamedeveloper.com/design/practical-procedural-generation-for-everyone- ; Compton's own post still refused).
- What shipped games do about it: hand-made set pieces and vaults (sections 1.3 to 1.5), several layout algorithms per game (DCSS layouts, Diablo's four level types), authored structure with generated detail (sections 2.3 and 2.5), rare events, and large template pools.

### 10.5 Seeds

Seeds must reproduce the map exactly, because bug reports, shared and daily seeds, regression tests and child maps all depend on it. mapwright's `check` already tests byte-identical regeneration.

---

## 11. What to reach for

| The user is making | Method family | Closest mapwright command today |
|---|---|---|
| Roguelike dungeon | Room accretion or BSP with loops, plus vaults (section 1); caves by cellular automaton | `gen dungeon` (`--method bsp` or `cave`). Vaults, lakes, machines: not built |
| Metroidvania | Authored concept graph plus hand-made room templates, lock and key ordering (sections 2.3 and 3) | Not built. `gen dungeon` gives top-down rooms only; no side view, no keys |
| Node-map run | Layered path graph with pacing rules (section 4) | Not built. `gen sector` is the nearest graph output |
| Colony sim tile map | World tiles holding fields, local map generated from the tile (section 6) | `gen world` then `gen region` for the land; `gen battle` for a small tile map. Per-tile local maps: not built |
| 4X galaxy | Points by shape, spanning tree plus extra lanes, chokepoint check (section 7.3) | `gen sector`; `gen system` and `gen planet` for what is at each star. Spiral and ring shapes: not built |
| Hex wargame | Terrain fields sampled onto hexes, fair starts by path distance (section 7) | `gen battle --grid hex` at tactical scale; `gen region` for the land. Region to hex terrain: not built |
| Survival voxel world | Noise terrain, chunked, staged passes (section 5) | `gen world` and `gen planet` give heightmaps for engine import (see games-film-print.md). Chunked 3D voxels and caves: not built |
| Tabletop battle map | Templates plus scatter on a grid, walls and doors exported (section 2) | `gen battle` (`--biome` for banded ground and scatter rules), `gen dungeon`, `gen deck`, `gen city`, with `export` to Universal VTT |

Candidate additions, in rough order of value for the list above: a `--method accrete` dungeon with a loop-distance threshold; vault files placed with a connectivity veto; a node-map generator with rule re-rolls; a key-level pass over an existing dungeon; an expressive-range report (`sheet` of N seeds plus a histogram of two metrics).

---

## 12. Biomes as data: banded ground and scatter rules

A shipped colony sim keeps its map rules in data files, not code. Two shapes are worth copying.

Ground from noise bands. One smooth noise field per map, cut at fixed values: below the first cut is water, then marsh, then grass. Rank-normalise the field first so a cut of 0.3 covers about 30% of the map whatever the frequency. A biome is then just a frequency and a list of cuts. `gen battle --biome` does this for temperate, boreal, tundra, desert and swamp.

Scatter as rules. Each placed thing is one row: a count per 10 000 cells as a range (so a bigger map gets more, a small one may get none), a minimum spacing between two of the same kind, an edge margin, terrain it may not stand on, and whether it blocks. The generator draws the count once, shuffles candidate cells and takes the first ones that pass. A blocker goes only where its whole ring is open, so it never cuts a route. `--rules FILE.json` replaces a biome's rows; the recipe echoes the rules and the placed counts.

Ordered steps with gaps. The same game runs map generation as named steps with integer orders spaced widely (10, 20, 200, 500, 900), so a new step slots between two old ones without renumbering. Optional features (a river, a cave system, a coast) hook in at a few named points (after elevation, after terrain, final) instead of being separate generators. `gen world` runs a fixed pipeline today; this is the shape to reach for if it ever needs plug-in steps. Not built.

## Sources (all accessed 2026-11-15 unless marked unverified)

- [ROGUE] "How did Rogue Generate its Random Dungeons?", How to Make an RPG, reading Rogue 3.6 `rooms.c`. https://howtomakeanrpg.com/r/a/rogue-dungeon-generation.html
- [NH] NetHack Wiki, annotated `mklev.c` of NetHack 3.6.1. https://nethackwiki.com/wiki/Mklev.c
- [ANG] Angband documentation, "How It Works". https://angband.readthedocs.io/en/stable/hacking/how-it-works.html
- [BROGUE] Brogue Community Edition, `src/brogue/Architect.c`. https://github.com/tmewett/BrogueCE/blob/master/src/brogue/Architect.c (read through the raw file; AGPL-3.0 code, described here, not copied)
- [DCSS1] Dungeon Crawl Stone Soup, `docs/develop/levels/introduction.txt`. https://github.com/crawl/crawl/blob/master/crawl-ref/docs/develop/levels/introduction.txt
- [DCSS2] Dungeon Crawl Stone Soup, `docs/develop/levels/syntax.txt`. https://github.com/crawl/crawl/blob/master/crawl-ref/docs/develop/levels/syntax.txt
- [RB-DBA] Anderson, M. "Dungeon-Building Algorithm", RogueBasin. https://www.roguebasin.com/index.php/Dungeon-Building_Algorithm
- [SPEL] Kazemi, D. "Spelunky Generator Lessons", part 1. https://tinysubversions.com/spelunkyGen/
- [D1] Boris the Brave. "Dungeon Generation in Diablo 1." https://www.boristhebrave.com/2019/07/14/dungeon-generation-in-diablo-1/
- [DC] Bénard, S. "The Level Design of Dead Cells: a Hybrid Approach." https://deepnight.net/tutorial/the-level-design-of-dead-cells-a-hybrid-approach/ (also published on Game Developer, 2017-03-29)
- [ISAAC] Boris the Brave. "Dungeon Generation in Binding of Isaac." https://www.boristhebrave.com/2020/09/12/dungeon-generation-in-binding-of-isaac/
- [GUN] Boris the Brave. "Dungeon Generation in Enter the Gungeon." https://www.boristhebrave.com/2019/07/28/dungeon-generation-in-enter-the-gungeon/
- [ITB] Wiltshire, A. "Reimagining failure in strategy game design in Into the Breach", Game Developer, 2018-02-28. https://www.gamedeveloper.com/design/reimagining-failure-in-strategy-game-design-in-i-into-the-breach-i-
- [UNEX] Boris the Brave. "Dungeon Generation in Unexplored." https://www.boristhebrave.com/2021/04/10/dungeon-generation-in-unexplored/
- [DB11] Dormans, J., Bakkes, S. "Generating Missions and Spaces for Adaptable Play Experiences." IEEE Transactions on Computational Intelligence and AI in Games 3(3), 216-228, 2011. https://doi.org/10.1109/TCIAIG.2011.2149523 (abstract through search result only)
- [MZ] Coxon, T. metazelda, README. https://github.com/tcoxon/metazelda (licence file not read)
- [STS] "Slay the Spire: Map Generation Guide", KosGames, 2022-07-04, a community write-up of reverse-engineered rules. https://kosgames.com/slay-the-spire-map-generation-guide-26769/
- [MC-WG] Minecraft Wiki, "World generation". https://minecraft.wiki/w/World_generation (first 100,000 characters read)
- [MC-118] Minecraft Wiki, "Java Edition 1.18". https://minecraft.wiki/w/Java_Edition_1.18 (first 100,000 characters read)
- [TER-WG] Terraria Wiki, "World generation" (Desktop 1.4.4.9). https://terraria.wiki.gg/wiki/World_generation
- [TER-SIZE] Terraria Wiki, "World size". https://terraria.wiki.gg/wiki/World_size
- [VAL] Jötunn (Valheim modding library), "Zones and Locations" tutorial. https://valheim-modding.github.io/Jotunn/tutorials/zones.html
- [NMS] Murray, S. "Building Worlds Using Math(s)", GDC 2017, session page only. https://gdcvault.com/play/1024514/Building-Worlds-Using
- [DF] "Interview: The Making Of Dwarf Fortress", Game Developer (Gamasutra), 2008. https://www.gamedeveloper.com/design/interview-the-making-of-dwarf-fortress
- [RW] RimWorld Wiki, "World generation". https://rimworldwiki.com/wiki/World_generation
- [QUD] Caves of Qud Wiki, "World generation" (patch 2.0.201.52; page flagged incomplete). https://wiki.cavesofqud.com/wiki/World_generation
- [AOE] aoe2-rms documentation, "Sections". https://docs.racket-lang.org/aoe2-rms/sections.html (a third-party reference to the game's script language)
- [MS] Wikipedia, "Model synthesis". https://en.wikipedia.org/wiki/Model_synthesis
- [TS] Thompson, T. "How Townscaper Works: A Story Four Games in the Making", Game Developer, 2022-04-06. https://www.gamedeveloper.com/game-platforms/how-townscaper-works-a-story-four-games-in-the-making
- [EPC] 80 Level, "Using Wave Function Collapse Algorithm for Dioramas" (Stålberg, Everything Procedural Conference 2018). https://80.lv/articles/using-wave-function-collapse-algorithm-for-dioramas
- [WFC-EX] Boris the Brave. "Wave Function Collapse Explained." https://www.boristhebrave.com/2020/04/13/wave-function-collapse-explained/
- [ASP] Smith, A. M., Mateas, M. "Answer Set Programming for Procedural Content Generation: A Design Space Approach." IEEE Transactions on Computational Intelligence and AI in Games 3(3), 2011 (through search result only).
- [FC5] Carrier, E. "Procedural World Generation of 'Far Cry 5'", GDC 2018, session page. https://gdcvault.com/play/1025215/Procedural-World-Generation-of-Far
- [HZD] van Muijden, J. "GPU-Based Procedural Placement in Horizon Zero Dawn", Guerrilla Games, 2017. https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn
- [GRW] Werle, G., Martinez, B. "'Ghost Recon Wildlands': Terrain Tools and Technology", GDC 2017, session page. https://www.gdcvault.com/play/1024029/-Ghost-Recon-Wildlands-Terrain
- [ER] Smith, G., Whitehead, J. "Analyzing the Expressive Range of a Level Generator." PCG Workshop 2010. https://www.pcgworkshop.com/archive/smith2010analyzing.pdf (PDF text read)

Refused or unreachable on 2026-11-15: Rock Paper Shotgun (Brogue interview, blocked), Stellaris wiki (page failed to load), FTL fan wiki (HTTP 402), Kate Compton's post on Tumblr (HTTP 403), GDC Vault talk contents (members only). Not found by search: a developer source for Hades, FTL, Civilization start balancing, or Diablo II.
