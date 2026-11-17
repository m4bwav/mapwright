# Learnings: mapwright

Research: [RESEARCH.md](RESEARCH.md).

Procedural lessons for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md). Changes are logged in [CHANGELOG.md](CHANGELOG.md); test runs in [TESTS.md](TESTS.md). Trigger and Hypothesis are required.

## Active

### L-066 · 2026-11-16 · `missing-climate-key-means-model-1`: old recipes regenerate the old climate byte for byte
- Trigger: climate model 2 (currents, marine coasts, continentality, snowline) had to change default output while every existing recipe folder must still pass the determinism bar.
- Hypothesis: a recipe records its climate model only when it has one, so its absence can name the old model.
- Rule: `params.climate` present = model 2 with those settings; absent = model 1. `gen world --climate-model 1` writes no key; regions inherit the parent's model; `regenerate`, `names --style` and `sheet --seeds` pass `p.get("climate")`.
- Evidence: seed 7 world and its default region from origin/main and from model 1 on the branch: all files identical. T-20261116-25
- Scope: skill

### L-065 · 2026-11-16 · `continentality-coast-is-windward`: compare inland range with the windward coast, not any coast
- Trigger: first continentality bar took "coastal" as within one cell of any sea and failed seed 7 (15-20°: x1.12).
- Hypothesis: a lee coast (east coast in the westerlies, west coast in the trades) has continental air and a wide range, as on real east coasts.
- Rule: the bar's coastal set is the windward coast (sea on the upwind side within 1.5 cell spacings); inland is 1500+ km from sea on both sides.
- Evidence: seeds 1-12 after the change: every judged band x2.10-2.54. T-20261116-26
- Scope: skill

### L-064 · 2026-11-16 · `current-rain-loses-to-terrain`: judge the current bar on temperature, report rain
- Trigger: a real-world bar demanding east rain >= 1.5 x west at 15-35° failed 3 of 9 judged seeds (seed 2: x1.02, a windward range on the west coast).
- Hypothesis: orographic rain and rain shadow outweigh the current's rain term on real terrain; the temperature term has no rival.
- Rule: the `check` bar compares lowland (under 500 m) coastal strips band by band and fails only when the east coast is under 1.0 °C warmer; rain is reported. The strict 1.5x / 2 °C bar lives in the unit test on a flat symmetric continent.
- Evidence: seeds 1-12: 7 judged, all pass, east warmer by 2.6-3.1 °C; symmetric continent x4.09 and +3.56 °C. T-20261116-25
- Scope: skill

### L-063 · 2026-11-16 · `marine-term-makes-cfb`: a linear sea-level temperature puts ET where Cfb belongs
- Trigger: book track s45 verdict 2; `sea_level_temp` gives about -2 °C at 60° everywhere.
- Hypothesis: a west-coast warm-drift term poleward of 30° (up to +10 °C, fading inland over about 1000 km) gives marine west coasts.
- Rule: keep the zonal line and add `coastal_terms`; bar 7 subtracts the coast-side terms before judging that temperature falls poleward (seed 12 failed bar 7 without that: 50-60° band 7.8 > 7.4).
- Evidence: lowland west-coast cells 45-60°, seeds 1-12, marine term off vs on: ET 243 / Dfc 86 / Cfb 0 vs Cfb 227 / Dfb 78 / Dfc 6; all land, Cfb+Cfc 885 vs 1313, Dfc 1697 vs 1120. A first try (+10 °C from 35°, 600 km reach, 800 km continentality) gave only Cfb 58 vs Dfb 157. T-20261116-26
- Scope: skill

### L-062 · 2026-11-16 · `climate-km-from-latitude`: the world is 1000 units wide but spans 60° of latitude
- Trigger: continentality needs "1500 km inland", but `WORLD` is 1000 km while 60° of latitude is about 6700 km.
- Hypothesis: climate distances measured in map units are inconsistent with the latitude the climate is built on.
- Rule: climate distances use `climate_km_per_unit` = latitude span x 111.2 / 1000 (minimum 1). Other tools' km (travel, scale bars) are unchanged.
- Evidence: symmetric continent 600 units wide on a 0-50° world = 3336 km; its centre is about 1670 km from both coasts. T-20261116-26
- Scope: skill

### L-061 · 2026-11-16 · `canny-from-geometry-doubles-the-denoise`: a coast hint drawn from the recipe lets the repaint run to 0.75
- Trigger: L-032 capped img2img at denoise 0.45; above it the coast drifted (0 of 4 pictures at 0.75).
- Hypothesis: a second hold on the coast, independent of the init image, lets the model repaint texture without moving the shore.
- Rule: for a stronger look use `--control canny` (strength 0.9, the default) and denoise up to 0.75: 8 of 8 pictures held the bar, IoU 0.94-0.96. Prefer canny over depth (depth 0.6 failed half at 0.75). Draw the hint from the land mask, never edge-detect a render. At 0.90 even canny slips (3 of 4).
- Evidence: T-20261116-24
- Scope: skill

### L-060 · 2026-11-16 · `perpendicular-offset-not-signed`: widen a hall along the perpendicular axis, never by dx*o / dy*o
- When widening a hall drawn along (dx, dy), the first try added `dy*o` to x and `dx*o` to y: the sign flips between N and S (or E and W) halls, so the two halves of a 2-wide hall met one square apart and agent 2 reached every room on 0/100 block dungeons. Offset x by o when dx == 0 and y by o when dy == 0: 97/100. Status: applied in 0.23.0 (T-20261116-23).

### L-059 · 2026-11-16 · `wide-corridor-centre-to-centre`: widen a cyclic edge from room centre to room centre, and gate the whole gap
- Trigger: extending --corridor to cyclic; rooms are 3-5 squares and only certainly cover the cell's middle line, so a corridor widened beside that line can end on a room's outer wall, and a lock on the single door square leaks round it.
- Rule: at corridor > 1 `_carve_edge` carves N wide (centred on the middle line) from cell centre to cell centre, so the run cuts a notch into each room; the edge keeps its lock or one-way flag and records `gap`, and `door_dist` applies the rule to every gap square. Ruling: locks and keys stay, as wide gates, rather than refusing corridor > 1 on cyclic.
- Evidence: seeds 1-100 at 48x36: eroded agent 2 joins every room 0/100 at corridor 1, 100/100 at 2; agent 3 at corridor 3 90/100. Gate bars pass (goal sealed without the key). tests/test_path.py test_cyclic_wide_corridors_keep_the_gate; T-20261116-22
- Scope: skill

### L-058 · 2026-11-16 · `open-coast-is-not-a-harbour`: touching open sea made 89% of settlements ports
- Trigger: after row 21 (0.13.0) ports were every settlement touching open sea; sweep of 24 worlds (seeds 1-8 at 800/1600/3200 cells) gave 742 of 835 (0.889).
- Hypothesis: settlement siting favours coast and rivers, so nearly every town is coastal; "touches open sea" is an eligibility test, not a port rule.
- Rule: `harbour_ports` ranks eligible settlements by `harbour_score` (two-ring land share for shelter + 0.5 x depth of the deepest open-sea neighbour, capped + 0.2 river mouth + rank bonus), ties by id, and keeps the best `port_cap(n) = max(1, ceil(n/4))`. Bar 14 now also fails above the cap.
- Evidence: same sweep after: 218 of 835 (0.261; 0.263/0.266/0.257 by size); tests/test_ports.py test_port_cap_and_harbour_rank, test_bar14_catches_too_many_ports; T-20261116-14
- Scope: skill

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

### L-052 · 2026-11-16 · `block-exit-match-by-growth`: grow the block grid from open exits and every exit inside the map is matched
- Trigger: row 7, `gen dungeon --method blocks`: an exit flag per side must meet an exit on the neighbour.
- Hypothesis: placing blocks in scan order needs back-tracking; growing from a start slot through open exits needs none, because a new block copies its placed neighbours' flags, closes the map edge and only rolls sides toward empty slots.
- Rule: growth stops only when no exit points at an empty slot. One race is left: two queued exits toward one slot. The second one opens the matching side on the placed block. The check bar reads the flags and the squares, so a break shows either way.
- Evidence: T-20261116-10; tests/test_places.py TestBlocks
- Scope: skill

### L-053 · 2026-11-16 · `block-exit-chance-sets-restarts`: exit chance 0.55 needed up to 24 restarts, 0.65 needs 5
- Trigger: first sweep at exit chance 0.55: 200 seeds at 48x36 averaged 2.7 restarts to reach the 25-block bar, worst 24 of the 32 allowed.
- Hypothesis: the growth dies out early when too few sides open (a branching process near its critical point).
- Rule: exit chance 0.65 (ours). 1,000 seeds: worst 5 restarts, 66 percent need none. Restart cap 32 (ours), stream 6000 + k so bsp, cave and cyclic stay byte-identical.
- Evidence: T-20261116-10
- Scope: skill

### L-054 · 2026-11-16 · `blocks-path-bar-needs-restart`: a full block grid can still miss the map-width path bar
- Trigger: the first `check --range blocks` (500 seeds) gave path over diagonal 0.767 at the minimum, 46 steps on a 48-wide map, under the min_path bar.
- Hypothesis: a well-filled grid can still put the goal near the entrance when loops are many.
- Rule: `build_dungeon` restarts a blocks map on a short path too, continuing the same restart counter, so the recipe's `rerolls` counts both causes. After the fix the minimum is 0.833 (50 steps).
- Evidence: T-20261116-11
- Scope: skill

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
# Learnings: mapwright

Research: [RESEARCH.md](RESEARCH.md).

Procedural lessons for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md). Changes are logged in [CHANGELOG.md](CHANGELOG.md); test runs in [TESTS.md](TESTS.md). Trigger and Hypothesis are required.

## Active

### L-076 · 2026-11-16 · `hw-limit-equal-mass-is-0274`: the Holman-Wiegert S-type limit for an equal-mass binary is 0.274 a_b, not 0.46
- Trigger: the book notes for the companion star item said an equal-mass pair 20 AU apart allows no planet beyond about 9.2 AU.
- Hypothesis: 0.464 is the constant term of the fit, which is the limit for a massless companion (mu = 0).
- Rule: use the full fit a_c/a_b = 0.464 - 0.380 mu - 0.631 e + 0.586 mu e + 0.150 e^2 - 0.198 mu e^2 (Holman and Wiegert 1999, eq. 1). Equal mass, e = 0, 20 AU gives 5.48 AU. Check quoted limits against the formula, never against a remembered fraction.
- Evidence: tests/test_space.py TestOrbitPhysics.test_formulas and test_companion_limit; T-20261116-32
- Scope: skill

### L-075 · 2026-11-16 · `physics-on-its-own-stream`: add derived fields from a new Rng stream so old seeds keep their bytes
- Trigger: adding eccentricity, days, tilt and albedo draws to `gen system` inside the orbit loop would shift every later draw on stream 202 and change every seed's orbits, moons and SVGs.
- Hypothesis: drawing the new fields after the loop on stream 203 (age on 205, companion on 204) leaves stream 202 untouched.
- Rule: new random fields in a generator go on a new P.Rng stream, drawn a fixed number of times per body. Seeds 1-3 before and after: map.svg, orbits.svg, names.json and recipe.json byte-identical; every old field in system.json equal; only new keys added.
- Evidence: T-20261116-31
- Scope: skill

### L-074 · 2026-11-16 · `despin-time-locks-three-times-more`: the Gladman despin time locks 415 rocky planets where the distance rule locks 142
- Trigger: verdict 3, tidal lock from physics instead of "rocky inside half the HZ inner edge around M or K".
- Hypothesis: the timescale grows as a^6 and falls as M*^-2, so close-in planets around G and F stars lock too, which the distance rule never allowed.
- Rule: keep the distance rule as default (default textures unchanged) and offer `--lock physics` (Gladman 1996, Q 100, k2 0.3, 12 h initial spin, e below 0.1, against the drawn system age). The two rules agree on 489 of 792 rocky planets over seeds 1-200.
- Evidence: T-20261116-31 sweep; Earth at 1 AU around the Sun 20 Gyr (no lock), Earth-mass at 0.05 AU around 0.2 suns under 1 Gyr.
- Scope: skill

### L-073 · 2026-11-16 · `halve-e-until-no-crossing`: Rayleigh e with sigma 0.05 on Hill-spaced orbits rarely crosses; halve the pair when it does
- Trigger: verdict 4, eccentricity with a peri/apo crossing bar.
- Rule: draw e from a Rayleigh law (sigma 0.05, cap 0.3), then halve both e of any pair whose inner apoapsis reaches the outer periapsis, up to 40 passes. Over 600 systems (seeds 1-200, three variants) no crossing bar failed; largest e 0.18.
- Evidence: T-20261116-31; tests/test_space.py test_crossing_orbits_fail (a 1.0 e 0.3 against a 1.5 e 0.2: apo 1.3 above peri 1.2 fails).
- Scope: skill

### L-072 · 2026-11-16 · `tab-pin-grows-outward`: pinning a gas-giant count needs slots past the snow line
- Trigger: verdict 6, `gen system --hex` pinning counts from the sector's T5 row.
- Hypothesis: a drawn planet count can end before the snow line, so forcing gas into the remaining slots is not enough.
- Rule: with `--tab`, forbid gas past the pinned count, force gas when the remaining slots equal the giants still owed (only past the snow line), and add planets outward until the count is met. Star class pins from the Stars column only for M, K, G, F; belts are recorded, not generated. 20 of 20 rows of a seed-11 sector matched giants and class.
- Evidence: tests/test_space.py test_tab_row_pins_star_and_giants; T-20261116-33
### L-071 · 2026-11-16 · `figures-boundaries-dial-skipped`: no figure or boundary drawing on sky charts yet
- Trigger: book track "sky" proposal 4 (figures full|faint|lines|none, boundaries none|wavy|iau).
- Hypothesis: drawing figures or boundaries needs line data per constellation, and the only boundary set worth using is the IAU one, too large to ship by hand.
- Rule: skipped as not cheap. The period lint already dates `stick-figures`, `constellation-boundaries` and `iau-boundaries` through `--uses`, so a chart drawn elsewhere can still be linted.
- Evidence: T-20261116-30
- Scope: skill

### L-070 · 2026-11-16 · `star-chart-style-is-decorative`: the star-chart style's dots are not stars
- Trigger: the style drew 400 seeded dots and its description read "palette only for now".
- Rule: `check --style star-chart` adds one WARN bar ("decorative star field, not a sky chart"), never a FAIL; real stars go through `mpw.py sky`.
- Evidence: test_check_star_chart_style_warns; T-20261116-29
- Scope: skill

### L-069 · 2026-11-16 · `sky-view-east-left`: a sky chart seen from Earth puts higher RA on the left
- Trigger: building `mpw.py sky` from RA/Dec.
- Hypothesis: projections give x growing eastward, as a globe seen from outside does; looking up with north at the top, east is on the left.
- Rule: `--orientation sky` negates x, `globe` keeps it. Test: RA 6h plots left of RA 5h in the sky view and right of it on the globe, for both projections. Name the option sky/globe, not the book's "geocentric", which reads as cosmology.
- Evidence: test_ra_east_left_in_sky_view; render of the Orion sample (Betelgeuse upper left of Rigel); T-20261116-29
- Scope: skill

### L-068 · 2026-11-16 · `iau-list-not-boundaries`: the 88 IAU constellations (1922) came eight years before their boundaries (1930)
- Trigger: book notes warned against one IAU year.
- Rule: two conventions, `iau-88` (1922) and `iau-boundaries` (1930), both fail. A 1925 chart may carry the list but not the boundaries.
- Evidence: test_iau_list_and_boundaries_apart; T-20261116-28
- Scope: skill

### L-067 · 2026-11-16 · `star-dates-disagree-warn`: sky period years the sources dispute are WARN only
- Trigger: Kanas puts the first print of Flamsteed numbers at 1765, not in Flamsteed's 1729 atlas; Wikipedia (checked 2026-11-16) names an early numbering in Halley's 1712 edition and Lalande's 1783 almanac for today's numbers. Hipparchus as the source of magnitudes is disputed. The book's Bonner Durchmusterung count (324,198) differs from Wikipedia's (342,198, 1859-1863).
- Hypothesis: a hard fail on a disputed year flags honest charts.
- Rule: fail only below the earliest defensible year (Flamsteed numbers 1712, magnitudes and ecliptic grid 150 BC, BD 1859); warn up to the later dates (1765 and 1783; Ptolemy c. 150 AD). Years that mark a famous atlas rather than first use (equatorial grid 1729, stereographic 1515, trapezoidal 1603, conic 1801, stick figures 1831, epoch 2000 in 1981) warn only.
- Evidence: test_flamsteed_numbers_not_1729, test_uncertain_years_warn_only; T-20261116-28
- Scope: skill

### L-061 · 2026-11-16 · `canny-from-geometry-doubles-the-denoise`: a coast hint drawn from the recipe lets the repaint run to 0.75
- Trigger: L-032 capped img2img at denoise 0.45; above it the coast drifted (0 of 4 pictures at 0.75).
- Hypothesis: a second hold on the coast, independent of the init image, lets the model repaint texture without moving the shore.
- Rule: for a stronger look use `--control canny` (strength 0.9, the default) and denoise up to 0.75: 8 of 8 pictures held the bar, IoU 0.94-0.96. Prefer canny over depth (depth 0.6 failed half at 0.75). Draw the hint from the land mask, never edge-detect a render. At 0.90 even canny slips (3 of 4).
- Evidence: T-20261116-24
- Scope: skill

### L-060 · 2026-11-16 · `perpendicular-offset-not-signed`: widen a hall along the perpendicular axis, never by dx*o / dy*o
- When widening a hall drawn along (dx, dy), the first try added `dy*o` to x and `dx*o` to y: the sign flips between N and S (or E and W) halls, so the two halves of a 2-wide hall met one square apart and agent 2 reached every room on 0/100 block dungeons. Offset x by o when dx == 0 and y by o when dy == 0: 97/100. Status: applied in 0.23.0 (T-20261116-23).

### L-059 · 2026-11-16 · `wide-corridor-centre-to-centre`: widen a cyclic edge from room centre to room centre, and gate the whole gap
- Trigger: extending --corridor to cyclic; rooms are 3-5 squares and only certainly cover the cell's middle line, so a corridor widened beside that line can end on a room's outer wall, and a lock on the single door square leaks round it.
- Rule: at corridor > 1 `_carve_edge` carves N wide (centred on the middle line) from cell centre to cell centre, so the run cuts a notch into each room; the edge keeps its lock or one-way flag and records `gap`, and `door_dist` applies the rule to every gap square. Ruling: locks and keys stay, as wide gates, rather than refusing corridor > 1 on cyclic.
- Evidence: seeds 1-100 at 48x36: eroded agent 2 joins every room 0/100 at corridor 1, 100/100 at 2; agent 3 at corridor 3 90/100. Gate bars pass (goal sealed without the key). tests/test_path.py test_cyclic_wide_corridors_keep_the_gate; T-20261116-22
- Scope: skill

### L-058 · 2026-11-16 · `open-coast-is-not-a-harbour`: touching open sea made 89% of settlements ports
- Trigger: after row 21 (0.13.0) ports were every settlement touching open sea; sweep of 24 worlds (seeds 1-8 at 800/1600/3200 cells) gave 742 of 835 (0.889).
- Hypothesis: settlement siting favours coast and rivers, so nearly every town is coastal; "touches open sea" is an eligibility test, not a port rule.
- Rule: `harbour_ports` ranks eligible settlements by `harbour_score` (two-ring land share for shelter + 0.5 x depth of the deepest open-sea neighbour, capped + 0.2 river mouth + rank bonus), ties by id, and keeps the best `port_cap(n) = max(1, ceil(n/4))`. Bar 14 now also fails above the cap.
- Evidence: same sweep after: 218 of 835 (0.261; 0.263/0.266/0.257 by size); tests/test_ports.py test_port_cap_and_harbour_rank, test_bar14_catches_too_many_ports; T-20261116-14
- Scope: skill

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

### L-052 · 2026-11-16 · `block-exit-match-by-growth`: grow the block grid from open exits and every exit inside the map is matched
- Trigger: row 7, `gen dungeon --method blocks`: an exit flag per side must meet an exit on the neighbour.
- Hypothesis: placing blocks in scan order needs back-tracking; growing from a start slot through open exits needs none, because a new block copies its placed neighbours' flags, closes the map edge and only rolls sides toward empty slots.
- Rule: growth stops only when no exit points at an empty slot. One race is left: two queued exits toward one slot. The second one opens the matching side on the placed block. The check bar reads the flags and the squares, so a break shows either way.
- Evidence: T-20261116-10; tests/test_places.py TestBlocks
- Scope: skill

### L-053 · 2026-11-16 · `block-exit-chance-sets-restarts`: exit chance 0.55 needed up to 24 restarts, 0.65 needs 5
- Trigger: first sweep at exit chance 0.55: 200 seeds at 48x36 averaged 2.7 restarts to reach the 25-block bar, worst 24 of the 32 allowed.
- Hypothesis: the growth dies out early when too few sides open (a branching process near its critical point).
- Rule: exit chance 0.65 (ours). 1,000 seeds: worst 5 restarts, 66 percent need none. Restart cap 32 (ours), stream 6000 + k so bsp, cave and cyclic stay byte-identical.
- Evidence: T-20261116-10
- Scope: skill

### L-054 · 2026-11-16 · `blocks-path-bar-needs-restart`: a full block grid can still miss the map-width path bar
- Trigger: the first `check --range blocks` (500 seeds) gave path over diagonal 0.767 at the minimum, 46 steps on a 48-wide map, under the min_path bar.
- Hypothesis: a well-filled grid can still put the goal near the entrance when loops are many.
- Rule: `build_dungeon` restarts a blocks map on a short path too, continuing the same restart counter, so the recipe's `rerolls` counts both causes. After the fix the minimum is 0.833 (50 steps).
- Evidence: T-20261116-11
- Scope: skill

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
