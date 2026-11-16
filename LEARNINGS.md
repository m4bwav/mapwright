# Learnings: mapwright

Research: [RESEARCH.md](RESEARCH.md).

Procedural lessons for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md). Changes are logged in [CHANGELOG.md](CHANGELOG.md); test runs in [TESTS.md](TESTS.md). Trigger and Hypothesis are required.

## Active

### L-055 · 2026-11-16 · `ocean-is-not-open-sea`: mesh `ocean` marks every cell below sea level, not only sea joined to the border
- Trigger: row 21 (ports only on open coast) needed "touches the sea"; `ocean[c]` is `h < 0`, which also holds for a pocket below the waterline surrounded by land.
- Hypothesis: hydrology treats every below-zero cell as sea, so a coast test on `ocean` alone would call an enclosed pocket a coast.
- Rule: use `mpw_gen.open_sea(m, nb, parent)` (flood from border sea cells through sea cells) for anything that means navigable coast; keep `ocean` for drainage.
- Evidence: tests/test_ports.py test_enclosed_sea_is_not_open; T-20261116-12
- Scope: skill

### L-056 · 2026-11-16 · `child-open-sea-from-parent`: a zoom window with no sea on its border cannot find open sea by itself
- Trigger: a child window that shows only an inner bay floods from no seed, so every bay town would lose its port flag.
- Hypothesis: open sea is a property of the whole world, and the window only sees part of it.
- Rule: when the child border has no sea, seed the flood with child sea cells whose nearest parent cell is open sea; the parent's mask comes from `open_sea_dir(parent)`, recursively, and is loaded only when needed.
- Evidence: tests/test_ports.py test_child_without_border_sea_inherits_parent; T-20261116-12
- Scope: skill

### L-057 · 2026-11-16 · `port-flag-adds-fields-only`: the port flag changed features.geojson and recipe.json by the new field alone
- Trigger: row 21 had to keep seeded output identical apart from the new field.
- Hypothesis: the flag is computed after settlements are picked and does not feed site scores, so placement, roads, names and map.svg do not move.
- Rule: keep derived flags out of scoring when a change must leave seeded maps in place; check by generating before and after and stripping the new keys.
- Evidence: seed 7, 1600 cells: map.svg, mesh.json, names.json, heights.png byte-identical; features and recipe equal after removing `port` and `ports`; T-20261116-13
- Scope: skill

### L-047 · 2026-11-16 · `landlocked-window-drains-at-edge`: a window with no sea drains through the edge cells where the parent's flow leaves it
- Trigger: L-009; grandchild g2_0 (seed 2) failed bar 1 on all 60 river cells; all-land g1_0 and g1_1 passed only with 0 rivers.
- Hypothesis: Priority-Flood seeded only from sea, so with no sea every cell kept its raw height and water had no outlet.
- Rule: when a region holds no sea, `edge_outlets` marks the border cell nearest each point where a parent flow edge leaves the window (the biggest exit always, others at a tenth of its area or more; the lowest border cell if none), hydrology seeds Priority-Flood and the lift from them, mesh.json stores `outlets`, and bar 1 accepts a path ending at one. Windows with any sea are unchanged byte for byte.
- Evidence: T-20261116-8, T-20261116-9
- Scope: skill

### L-046 · 2026-11-16 · `legend-place-recipes`: `mpw.py legend` crashed on place recipes looking for mesh.json
- Trigger: the wiki run called `legend` on a battle map.
- Rule: battle maps list their own legend rows (text, --json, -o svg); city and dungeon refuse with "has no legend" and exit 1.
- Evidence: T-20261116-6 (test_legend_cli_on_place_recipes)
- Scope: skill

### L-045 · 2026-11-16 · `treasure-off-room`: branch treasure was drawn at the graph cell centre plus one, which misses rooms 3 squares tall
- Trigger: s17 sample dungeon-77-branches; seed 77 room 21 spans y 15-17, the marker went to y 18.
- Rule: `treasure_cell` picks the floor cell inside the room nearest one square below its centre; the SVG marker and the GeoJSON point both use it. Old placement: 49 misplaced across 3 x 40 cyclic seeds; new: 0.
- Evidence: T-20261116-6
- Scope: skill

### L-044 · 2026-11-16 · `battle-frame-bands`: battle title and legend hid map squares
- Trigger: s17 battle-31-normal.png, legend over the bottom-right squares, title over trees.
- Rule: battle maps (square and hex) draw the grid inside `<g class="map" transform="translate(0,top)">` with a title band above and a legend band below. Export PNGs stay grid only, so the SVG is taller than the Tiled/VTT PNG. Render is still byte-deterministic.
- Evidence: T-20261116-6
- Scope: skill

### L-048 · 2026-11-16 · `bar7-arid-floor`: bar 7 does not judge the rain shadow when the windward side is under 50 cm/yr
- Trigger: L-009; an arid child at exactly 20 samples failed on 4.9 vs 5.2 cm/yr.
- Hypothesis: in a desert there is no moisture to shadow; a difference of tenths of a cm/yr is noise.
- Rule: `SHADOW_MIN_WET = 50` cm/yr windward mean, measured first (T-20261116-8: judged maps had windward 136.6 or more and differences 115.3 or more, so no judged map changes). The detail line says "too arid to judge".
- Evidence: T-20261116-8
- Scope: skill

### L-050 · 2026-11-16 · `trees-block-on-battle-maps`: tree cells are not passable, so scattered trees can seal pockets
- Trigger: s17 density sweep: dense battle maps failed "every door reached" on 14 of 30 seeds and one map reached 0.64 feature share.
- Hypothesis: PASS is (FLOOR, DOOR); TREE blocks. Tree clumps closed off doors and pockets, and fill_pockets then turned the pockets to rock.
- Rule: any blocking scatter must keep the open ground in one piece: count flood regions before and after each clump and take it back if the count changes; keep scatter off cells beside a door. The legend says trees block.
- Evidence: T-20261116-3
- Scope: skill

### L-051 · 2026-11-16 · `hex-leaves-stale-map-png`: reusing one folder for a square then a hex map fails determinism
- Trigger: a test wrote a square battle then a hex battle into the same folder; check failed "byte-identical: map.png".
- Hypothesis: hex maps write no map.png, so the square map's PNG stays behind and the regenerated folder has none.
- Rule: one folder per grid kind in sweeps and tests (or clear the folder first).
- Evidence: T-20261116-3
### L-043 · 2026-11-16 · `jps-doors-and-python-speed`: JPS pruning breaks next to doors, and saves expansions but not time in Python
- Trigger: s17 `path --jps` build: dungeon doors forbid diagonals and carry one-way entry, which the JPS paper's uniform grid does not have; the 48-map sweep then showed 3.4 times fewer expansions but 0.39 s against A*'s 0.30 s.
- Hypothesis: pruning at a square is safe only when its 3x3 neighbourhood has uniform moves; the jump loop runs square by square in the interpreter, so pure-Python JPS pays for the scans it saves on the queue.
- Rule: make every square within one step of a door a jump point expanded with all of G.out's moves, and prove JPS against A* to 1e-9 on generated maps with doors before trusting it. Never sell `--jps` as faster in wall time; report expansions and time separately.
- Evidence: tests/test_path.py JumpPoints (MPW_JPS_STATS=1 prints the numbers)
- Scope: skill

### L-042 · 2026-11-16 · `find-osm-undertriggers`: "find OpenStreetMap data ... tell me the licence" fires mapwright 1 of 3
- Trigger: T-20261116-2: trigger-find-place missed in one run and a rerun pair (1 hit of 3); it was 3/3 in T-20261116-1 after the Step F fix.
- Hypothesis: the prompt reads as a licence question sonnet can answer from memory, and the description says "find" maps of places but does not name OpenStreetMap, Overpass or data licences.
- Rule: closed 2026-11-16. Name the data source and the licence in the description ("finds OpenStreetMap or Overpass data for a place with its licence" plus the example 'find OpenStreetMap data for this area and its licence'). A licence question about a named source reads as answerable from memory unless the description names that source.
- Evidence: T-20261116-2 (1/3 before), T-20261116-4 (3/3 after, decoys 0/4 fired)
- Scope: skill

### L-009 · 2026-11-14 · `landlocked-window-no-drain`: Closed: grandchild of a landlocked window fails bar 1; arid windows sit on bar 7's sample limit
- Trigger: sweep: a grandchild whose window holds no sea fails bar 1 for every river cell (origin/main does the same, so it predates D.3). One arid child had exactly 20 windward samples after the causeway lift, so bar 7 judged a 4.9 vs 5.2 cm/yr desert and failed; before, it had 19 and was skipped.
- Hypothesis: Priority-Flood in a region seeds only from sea cells, so with no sea nothing drains; bar 7 has no margin at its 20-sample floor.
- Rule: closed 2026-11-16 by L-047 `landlocked-window-drains-at-edge` (edge outlets) and L-048 `bar7-arid-floor` (50 cm/yr windward floor, measured in T-20261116-8).
- Evidence: scratch sweep 2026-11-14
- Scope: skill

### L-010 · 2026-11-14 · `bar-must-measure-the-output`: A label bar that reuses the placer's own boxes proves nothing
- Trigger: design of the `check` label bars.
- Hypothesis: if check reads the boxes the placer kept, a placer bug passes its own test.
- Rule: measure labels back from the rendered SVG's attributes (x, y, size, anchor, rotate, letter-spacing) with the width table, and test overlaps and edges on those boxes. Tests force an overlap and an edge cut into an SVG to prove the bar fails.
- Evidence: T-20261114-3
- Scope: skill
- Merged L-031 `line-test-needs-the-clean-render` (2026-11-16): a bare contrast test finds lines everywhere (22 to 33 percent of riverless places). Take the centre-minus-sides colour vector from the clean render at each river sample and count it kept when the styled picture holds a third of it in that direction; always report the noise floor from the same test where the recipe has no line, and keep that number out of the bar (T-20261115-5).

### L-012 · 2026-11-14 · `judge-style-at-full-size`: Monospace labels look garbled when a sheet scales a map down
- Trigger: blueprint labels in a 480 px sheet cell read as noise; at full size they are clean.
- Hypothesis: Courier New strokes and the 2.5 px halo collapse below about 6 px text.
- Rule: judge a style from a full-size render, not from a sheet thumbnail; an OCR bar must run on the full-size PNG.
- Evidence: scratch renders 2026-11-14
- Scope: skill

### L-020 · 2026-11-15 · `always-draw-then-override`: A replayed parameter must not skip a random draw
- Trigger: regeneration of a city differed in features, names and map.svg.
- Hypothesis: `spokes or rng.randint(...)` drew a number only when spokes was unset; the recipe stores the drawn value, so the replay skipped the draw and every later number shifted.
- Rule: always draw, then override with the stored or given value. Same for battle maps: 'touches the map edge' is not one region; keep the largest edge region and fill the rest, or the entrance can sit in a cut-off strip.
- Evidence: T-20261115-2
- Scope: skill
- Merged L-033 `gate-on-a-recipe-key` (2026-11-16): new generator behaviour runs only when the recipe carries a new key (`params.goal`); `regenerate` passes `legacy=True` without it, new flags default to the old draw order draw for draw, and a fixture written by the old release keeps passing `check` (T-20261115-6).

### L-021 · 2026-11-15 · `pole-row-scales-with-width`: a pole bar must name its resolution
- Trigger: sweep: the pole bar (top row std vs texture std) failed 2 of 120 textures at 256 px and passed all at 512.
- Hypothesis: with pixel centres the top row is a circle about pi equator pixels round, so its spread is the texture's local detail at that scale; a sharp feature (an ice crack, a crater rim) crossing the pole raises it, more so at low width.
- Rule: state the width the pole tolerance was measured at and refuse narrower textures; set the limit between the worst correct texture and the best wrong (u, v) one, both measured.
- Evidence: T-20261115-3
- Scope: skill
- Merged L-022 `seam-bar-needs-a-percentile` (2026-11-16): compare a texture seam with the 90th percentile of interior adjacent-column differences (2.5 x, +0.5 grey level), not the median, which is near zero on banded textures (T-20261115-3). General rule: set every bar between the worst correct and best wrong case, both measured.

### L-024 · 2026-11-15 · `chrome-rounds-pdf-page`: a browser PDF page is rounded, so cut the box back yourself
- Trigger: the print bar failed on A3 (MediaBox 841.92 x 1191.12 pt for 841.89 x 1190.55, off 0.57 pt) and A5 with bleed (0.505 pt), and the drawing lost up to one CSS pixel on its right and bottom edges.
- Hypothesis: headless Chrome rounds an `@page` size to whole points, then to 1/300 inch, and lays the page out on a viewport floored to whole CSS pixels, so the page is neither the size asked for nor always as large as the drawing.
- Rule: ask for a page 2 pt larger than needed, then set MediaBox (and BleedBox, TrimBox) to the drawing's rectangle, which hangs from the page's top-left corner, with an incremental update appended to the file; never edit the browser's bytes in place.
- Evidence: T-20261115-4 (60 PDFs, worst difference 0.0001 pt; pypdf, PyMuPDF, mutool and poppler read the update)
- Scope: skill

### L-026 · 2026-11-15 · `hex-has-no-uvtt`: skip the hex Universal VTT export, it has no honest form
- Trigger: the open item "hex battle maps to VTT" from Step D.7.
- Hypothesis: a .dd2vtt holds one `pixels_per_grid` number for a square grid and no grid type, so an importer would lay squares over the hexes and every wall and door would sit on the wrong cell.
- Rule: refuse hex with the reason and send it to `export --to png` (same canvas as map.svg). Tiled's hexagonal orientation (staggeraxis y, staggerindex odd) is the honest hex target and is not built yet.
- Evidence: T-20261115-4
- Scope: skill

### L-028 · 2026-11-15 · `thin-water-does-not-survive-img2img`: redraw lakes and rivers in code after the pass
- Trigger: first style passes kept the coast and painted over the rivers and the largest lake.
- Hypothesis: a 1 to 3 px line and a small flat patch are texture to the model; even a light repaint replaces them.
- Rule: lakes and rivers go in the code-set layer on top of the styled picture with roads, symbols and labels, and are left out of the land IoU. Measured share the model alone kept: river lines 0.51 to 0.78 at denoise 0.35, 0.39 to 0.54 at 0.45, 0.18 to 0.34 at 0.55; lakes 0.09 to 0.76 at 0.45 (means by look, two worlds pooled).
- Evidence: T-20261115-5
- Scope: skill

### L-029 · 2026-11-15 · `denoise-on-the-step-grid`: the denoise typed is not the denoise that runs
- Trigger: the 0.55 and 0.65 columns of the grid ran further from the render than their names.
- Hypothesis: below 1, KSampler takes `steps` steps from the tail of an int(steps / d) step schedule, so the run value is steps / int(steps / d).
- Rule: at 9 steps 0.35 runs as 0.36, 0.45 as 0.45, 0.55 as 0.5625, 0.65 as 0.692. Record both in the sidecar and state a ceiling as the typed value with its run value.
- Evidence: T-20261115-5
- Scope: skill

### L-030 · 2026-11-15 · `fixed-colour-rules-miss-parchment`: train the land and sea colours on each picture
- Trigger: the fixed water rule of `read` (blue clearly above red) gave a land IoU of 0.26 to 0.41 on the clean ink-and-parchment render, where sea and land are both tan.
- Hypothesis: a style changes what colour the sea is; only the picture itself knows.
- Rule: build a colour table per picture from pixels at least 12 px from the true coast (15-bit buckets, coarser buckets for unseen colours), apply it to every pixel, clean with a 3x3 close and open. The band where a coast can drift is never used for training. On blue-sea looks it agrees with the fixed rule within 0.02 at denoise 0.45 and below.
- Evidence: T-20261115-5
- Scope: skill

### L-032 · 2026-11-15 · `the-look-arrives-after-the-coast-leaves`: img2img alone gives a light repaint inside the bar
- Trigger: the pictures that look most painted (denoise 0.65) failed every bar; the ones that pass (0.45 and below) sit close to the code render.
- Hypothesis: with only the init image holding it, the model trades geometry for style one for one.
- Rule: default and ceiling denoise 0.45; never raise it for a stronger look. A stronger look needs a second hold on the coast (a canny or depth control image drawn from the geometry), which is not built yet.
- Evidence: T-20261115-5
- Scope: skill

### L-034 · 2026-11-15 · `squares-forget-one-way`: a square BFS walks through a one-way door both ways
- Trigger: the first cyclic map passed every graph bar but the square-level gate bar found the goal reachable with the lock shut.
- Hypothesis: the route ran up the valve from the key to the goal; squares carry no direction, so the gate looked open.
- Rule: any square walk over a cyclic map uses `door_dist`, which lets a one-way door be entered only from its source side and a locked door only with the key. Measure the cyclic path as the completion walk (entrance to key, key to goal), not the plain shortest path.
- Evidence: T-20261115-6
- Scope: skill

### L-035 · 2026-11-15 · `corridor-means-no-2x2`: a corridor square is one in no 2x2 open block
- Trigger: the first range run gave bsp a dead-end share of 0 on all 500 maps and counted room corners as corridors.
- Hypothesis: peeling one-neighbour squares stops at any room three squares wide, and a two-neighbour rule catches every room corner.
- Rule: corridor squares are those in no 2x2 open block; dead-end share counts the parts that hang off a single bridge. Check a new metric on a hand-drawn ring and a room-with-stub before trusting a sweep.
- Evidence: T-20261115-6 (the ring scores loop 1, dead end 0; the stub scores loop 0)
- Scope: skill

### L-038 · 2026-11-15 · `road-cost-is-directed`: the road router charges the cell entered
- Trigger: world paths cost 1225.07 one way and 1234.13 the other.
- Hypothesis: `Router.step` multiplies by the terrain of the cell entered and adds a bridge only when entering a river, so the cost is directed even on flat ground.
- Rule: treat world and region graphs as directed: the symmetry bar applies to grids only, and a field (cost to a goal) runs Dijkstra on reversed edges.
- Evidence: T-20261115-7
- Scope: skill

### L-039 · 2026-11-15 · `render-into-recipe-folder-breaks-determinism`: a render saved inside the recipe folder fails the byte-identical bar
- Trigger: Step E: `render DIR -o DIR/map.png --style star-chart` then `check DIR` failed "same seed gives byte-identical files" on sector and system; world and region failed on map.svg after a restyled render overwrote the gen's file.
- Hypothesis: space check compared the folder's file set both ways, so a file the gen never writes counted as a difference; world check compares the gen's own map.svg.
- Rule: fixed in 0.10.1 for space kinds (only files the gen writes must exist and match; extras are ignored). Still: render showcase copies outside the recipe folder or under another name, never over map.svg/map.png.
- Evidence: tests/test_space.py test_rendered_extra_file_does_not_fail_determinism
- Scope: skill

### L-041 · 2026-11-15 · `system-hz-legend-undrawn`: Closed: schematic system view names a green habitable zone it does not draw
- Trigger: Step E system seed 2077 (G9 V): legend says "green: habitable zone 0.88-1.56 AU", the schematic shows no green band, and no planet sits in the zone.
- Hypothesis: the schematic uses equal spacing, so the zone has no x extent; the legend line is shared with the to-scale view.
- Rule: closed 2026-11-16 (session 17): the key follows the drawing. Both views tag the band `class="hz"` and its key `class="legend-hz"`; the schematic with no planet in the zone prints the range without the colour. Test TestSystemHzLegend (40 seeds, both views, both cases seen).
- Evidence: Step E note 2026-11-15; T-20261116-3
- Scope: skill

## Archived

Folded 2026-11-16 (C-20261116-3) into [LEARNINGS-ARCHIVE.md](LEARNINGS-ARCHIVE.md): entries now enforced by a test or by code, closed fixes, and merged duplicates.
