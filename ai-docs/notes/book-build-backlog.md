# Build backlog from the books

Written 2026-11-15 with round 2 of [book-verdicts.md](book-verdicts.md). One row per rule that got the verdict BUILD: 22 rules, 22 rows. Each row is a testable behaviour the code did not have on 2026-11-15 (checked against the scripts at 0.6.0 and the 0.7.0 diff). The rule knowledge behind a row is in `references/`; this file says what to build.

How to read a row:

- **Numbers** are given exactly as the reader notes give them. "ours" marks a number that is not in the book and still needs a measurement.
- **Source** names the book and chapter, then the rule ID in that book's notes (`Ai/technique-harvest/ai-docs/books/<slug>/notes.md`).
- **Size** is relative: small (one function and a bar), medium (a new method, flag set or report with tests), large (a new generator).
- Books: M = Monmonier, How to Lie with Maps (1991 ed.). T = Thrower, Maps and Civilization. HW = Harley and Woodward, History of Cartography vol. 1. STN = Shaker, Togelius and Nelson, Procedural Content Generation in Games. SA = Short and Adams, Procedural Generation in Game Design. KL = Korn and Lee, Game Dynamics.

New rows from later research go under the command they belong to, or in a new section at the end.

## Most valuable first

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 1 | `gen dungeon --method cyclic` | Graph-first cyclic dungeon, the open item from step D.7. Start and goal joined by two paths a and b on a grid of cells, more cycles nested inside, a pattern chosen per cycle from the two path lengths, lock and key attributes on nodes and edges, then the grid raised to tiles. Bars: cycle rank, key-before-lock BFS, return-path BFS from goal to entrance that honours one-way edges, every graph edge joins cells that share a border | Cycle rank (edges minus nodes plus 1) 2 to 5 per level. Short a with long b: lock at the goal, key at the far end of b, b not enterable from the start. Ten named patterns and the lock and key kinds are listed in cities-and-dungeons.md 5.5. The chapter gives no layout algorithm beyond starting on a grid | SA ch. 9, p. 84-95 (R1); on-grid ruling from KL ch. 9 | scripts/mpw_places.py | large |
| 2 | `check --range` | Expressive range report for a generator: N seeds, two metrics per map, a 2D histogram, a flag on any bin that holds most of the sample. `gen dungeon` first, then `gen city` and `gen battle` | Sample grown until the plot stops changing; the notes propose comparing 250 against 500 seeds (ours). Dungeon metrics (ours): loop share, dead-end share, entrance-to-exit path length over the map diagonal, open-floor share. Never a metric that is also an input flag | STN ch. 12, p. 215-217 (R1) | scripts/mpw_places.py (metrics), scripts/mpw.py (`check`) | medium |
| 3 | `check --period YEAR` | Period lint. A style carries a year; the lint reads the first-use tables (cartography-design.md 1.6, projections.md 3.14) and lists every convention on the map that is younger than that year | Fail: bar scale before 1275 (the earlier of the two dates for the Pisan chart), ratio scale before 1806, land contours before 1791, systematic hachures before 1799, elevation tints before 1804 (the notes' check line says 1800), Mercator before 1569, Mollweide or Albers before 1805, Robinson before 1963, dot map before 1830, shaded-area map before 1831, flow lines before 1837. Warn: Greenwich assumed before 1884. Chart styles: latitude scale or graticule before 1500, drawn compass rose before 1375. Mappa mundi styles: graticule or bar scale before 1400, rhumb lines before 1300. All years are book facts, not cross-checked | T ch. 4-9 (T1); HW ch. 18-19 | scripts/mpw_render.py (a `period` field on styles), scripts/mpw.py (`check`) | medium |
| 4 | `gen sector`, `gen system`, `gen region` | Per-place seeds. Hash the world seed plus the place's identity (sector hex, system, chunk) to get that place's own seed, so it regenerates alone without being stored. Today `Rng(seed, stream)` gives one counter-hash stream per purpose, a sector draws all its worlds from one stream in order, and `gen system` takes an unrelated seed. Bar: system 118 made alone and made inside a full sector is byte-identical | The same world needs the same order of choices. The book suggests MD5; mapwright keeps a stable hash of its own (`h64`, or `hashlib.blake2b` with `digest_size=8` for word seeds), never the built-in `hash()` | SA ch. 26, p. 272-273 (R21) | scripts/mpw_space.py, scripts/mpw_gen.py (zoom) | medium |

## `gen dungeon`

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 5 | `gen dungeon --method cave --fill --passes --rule`, plus a sweep | Expose the cave parameters and record largest-region share and open-floor share per setting, so the default can be judged on our own code. Nothing changes until the sweep is read | Code today: fill 0.45, wall at 5 or more of 8, floor at 3 or fewer, 5 passes. Johnson et al. 2010: r = 50%, T = 5, n = 4; size-2 neighbourhood with T = 13 of 24. Same paper in STN: 0.5, 5 or more, 2 to 4 passes. Caves of Qud: 55%, open to wall at 6 to 8, wall to open at 0 to 4, 2 passes, two-cell border. Sweep range from the notes (ours): fill 0.40 to 0.55, passes 2 to 5 | STN ch. 3, p. 43-44 (R5); SA ch. 26, p. 288-290 | scripts/mpw_places.py | small |
| 6 | `gen dungeon` (all grid methods) | Room detection in any grid, so caves and imported grids get rooms, doors, keys and stocking like BSP maps. Then a room adjacency graph. Test: on BSP output the detected room count equals the generator's room count | Scan in reading order; seed a room at any empty 3 by 3 block; grow by adding cells with three neighbours already in the room. Adjacency: flood outward from each room; rooms reached without crossing a third room are adjacent | STN ch. 9, p. 165-166 (R11) | scripts/mpw_places.py | medium |
| 7 | `gen dungeon --method blocks` | Exit-matched block grid: blocks with an exit flag per side, placed on a grid so exits match; open edges merge into halls. The nearest standard-library step toward the open wave function collapse item, with a connected result. Bars: no unmatched exit inside the map, block count at or above the bar, re-roll count reported | 7 by 7 blocks; goal 40 blocks; a map with too few placements is thrown away and restarted. Cap on restarts: ours | SA ch. 7, p. 66-72 (R8) | scripts/mpw_places.py | medium |
| 8 | `gen dungeon` | Mark a goal (exit, boss or treasure) at the floor cell farthest from the entrance by path distance. Today a dungeon has an entrance and no exit. Bar: the goal's BFS distance equals the map maximum, within a tolerance | No number in the book; tolerance ours | SA ch. 26, p. 297 (R13) | scripts/mpw_places.py | small |

## `check` on dungeons and battle maps

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 9 | `check` | Minimum path length: reject a dungeon whose shortest entrance-to-exit path is under a set number of steps. Needs row 8 | The book sets no figure; the notes suggest the map width (ours). The chapter's other hard constraints: a valid path exists, entrance and exit on opposite edges | STN ch. 8, p. 144 (R14) | scripts/mpw_places.py | small |
| 10 | `check` | No isolated wall cells after cleanup: count of wall cells with fewer than two wall neighbours is 0 | Every wall cell has two or more wall neighbours (the notes read this as orthogonal neighbours). The same example keeps at least half the cells wall | STN ch. 8, p. 150-151 (R15) | scripts/mpw_places.py | small |

## `check --range` (after row 2)

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 11 | `check --range` | Normalised metrics and one heatmap per parameter setting; report the share of occupied bins and the fullest bin. Adds linearity and leniency (formulas in cities-and-dungeons.md section 7) | Each metric rescaled to 0 to 1 across the sample. The book's worked heatmap used 10,000 levels per setting. Leniency weights run from 0 (fatal) to 1 (harmless) | SA ch. 22, p. 235-241 (R17) | scripts/mpw_places.py, scripts/mpw.py | medium |
| 12 | `check --range --compare` | Dead-flag check: change one flag and the plot must move. Fails when the histogram distance between two settings is under a bar | Bar: ours, unset | STN ch. 12, p. 217 (R4) | scripts/mpw.py | small |
| 13 | `check --range --baseline` | Regression test: store the histogram per release and fail when the distance to the stored one passes a bar. A sudden change after a small edit is a bug signal | Bar: ours, unset | SA ch. 22, p. 243 (R20) | scripts/mpw.py, tests | small |

## `render` and styles

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 14 | `render` | Scale-bar guard: sample the projection's scale factor at the frame corners and centre. When it varies by more than a limit, on any projection, draw no single bar and say where scale is true. Today `scale_bar` always draws one bar from the frame scale | Limit: not in the book, ours. The only number in the references today is Mercator over about 20 degrees of latitude (projections.md rule 15) | M ch. 2, p. 8-9 (M2) | scripts/mpw_render.py | small |
| 15 | `render --style` (chart styles) | Draw the rhumb network by construction, not as random radiating lines, and check it: node count, nodes on one circle and evenly spaced, line colour by bearing class | 16 nodes on one hidden circle (or two touching circles), each joined to most of the others. 16 lines at the centre, 32 in a style dated after 1449. The eight winds black or brown, the eight half winds green, the sixteen quarter winds red. Book facts, not cross-checked | HW ch. 19 (H6); T ch. 4 | scripts/mpw_render.py | medium |
| 16 | `label`, `check` | Rank-monotonic selection: no place is left out while a lower-ranked place in the same view is kept, unless the recipe says why. Catches a collision pass that drops a city and keeps a village | No number | M ch. 4, p. 44 (M21) | scripts/mpw_render.py (label bars) | small |

## `read` and `trace`

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 17 | `read` | Inset detection before georeferencing: find inset boxes, report them, leave them out of the control points. A feature inside an inset is rescaled, never copied at inset size. Needs a fixture with an inset | No number | M ch. 4, p. 45 (M20) | scripts/mpw_read.py | medium |
| 18 | `read` | Not-before year: the youngest convention seen gives the earliest possible date, printed with its reason. Start with what `read` already finds: scale text and names | Ratio scale: after 1806. Land contours: after 1791. Greenwich prime meridian: after 1884. The name America: after 1507. Book facts, not cross-checked | T ch. 5-7 (T18) | scripts/mpw_read.py | small |
| 19 | `read` | Date range for a medieval map from its tells, printed as `inferred` with reasons. Most tells need a person or a vision model to say they are present | The youngest name dates the map. Scale inside a circle: the four earliest charts only. Drawn compass rose: not before 1375. Jerusalem at the centre: about 1250 to 1400. Lines at the centre of a rhumb network: 16, or 32 after 1449. Latitude scale on a chart: after 1500. Book facts, not cross-checked | HW ch. 18-19 (H20) | scripts/mpw_read.py | medium |
| 20 | `trace`, `check` | Sliver list: after an overlay or trace, list polygons under a minimum area or with extreme thinness; a child map meets its parent and neighbours at the shared edge | Thresholds: not in the book, ours | M ch. 4, p. 56-57 (M23) | scripts/mpw_read.py | small |

## `gen world` and `gen region`

| # | Command | What it would do | Numbers | Source | Script | Size |
|---|---|---|---|---|---|---|
| 21 | `gen world`, `check` | Ports only on open coast. Start every cell as land, mark the map border as sea, flood inward through sea cells; water reached this way is open sea, and land next to it is true coast. A settlement flagged as a port must touch it; a lakeshore town is never a port. Today no settlement carries a port flag. A child window with no sea on its border needs its parent's open-sea mask | No number | KL ch. 8, sec. 3.3.1 (R10) | scripts/mpw_gen.py (sea flood), scripts/mpw_human.py (settlement flag) | small |
| 22 | `measure` or a route export | Itinerary: a route as a list of stages with the distance of each and a total, in the world's own unit. Bar: the total equals the sum of the stages (ancient lists did not always agree) | Pace preset, upper figure: about fifty Roman miles (74 km) a day for relay couriers. Book fact, not cross-checked | HW ch. 14 (H16) | scripts/mpw_human.py (roads), scripts/mpw.py | small |

## Flagged candidates that got no row

- **Bar scale instead of ratio scale on resizable output** (M1). The renderer already draws only a bar and never prints a ratio, and cartography-design.md rule 2 states the rule. A lint is worth a row only once a legend or template can print a ratio.
- **Equal-area requirement for dot-density maps** (M3). mapwright draws no dot-density layer; thematic maps belong to chartwright. cartography-design.md rule 23 now names dot maps.

## Explain terms the notes ask for

Not rules, so not counted. One small pass over `mpw.py explain` would add: planimetric distance, trap street, paper street, template effect, relief displacement, standard line, areal aggregation, persuasive map (Monmonier); isobath, isogon, representative fraction, wind rose, cordiform, plane table, triangulation, centuriation, T-O map, portolan chart, strip map (Thrower); mappamundi, zonal map, Beatus map, wind rose versus compass rose, hidden circle, Peutinger map, itinerary, groma, Ptolemy's first projection (Harley and Woodward); historical atlas, map of a moment, dynamic map (Goffart).
