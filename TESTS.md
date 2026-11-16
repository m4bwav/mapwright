# Tests: mapwright

Companions: [RESEARCH.md](RESEARCH.md), [CHANGELOG.md](CHANGELOG.md), [LEARNINGS.md](LEARNINGS.md).

Test runs for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and `scripts/mpw.py`. Unit tests live in `tests/`, skill cases in `evals/evals.json` (run log below). A test passes on evidence, never on a transcript's claim.

Entry shape: `### T-20261116-14 · 2026-11-16 · pytest (tests/) + port-share sweep · Windows · 252 passed, 2 skipped
- Sweep: gen_world seeds 1-8 at 800, 1600, 3200 cells. Port share before 0.921/0.929/0.851 (all 0.889, 742/835); after 0.263/0.266/0.257 (all 0.261, 218/835).
- New: test_port_cap_and_harbour_rank (world + child: count = min(cap, coastal), worst port scores >= best non-port), test_cap_values, test_bar14_catches_too_many_ports; existing determinism test byte-identical.
- led to: L-058
### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per notable result, then `led to:`. Newest first.

## Runs

### T-20261116-18 · 2026-11-16 · pytest (python -m pytest -q tests) after row 4, region chunks · Windows · 260 passed, 2 skipped (live) in 74 s
New TestGen cases: `gen region --chunk 1,1` twice gives byte-identical files; recipe carries place (world_seed, chunk, chunk_km) and seed = `place_seed(7, "region", "1,1@250")`; same window via --window keeps seed 7 and a different mesh; `check` on the chunk has no FAIL (zoom bars vs parent); bad chunks exit. Default world, region and zoom outputs for seed 7 diffed byte-identical against origin/main. No existing expectation changed.

### T-20261116-17 · 2026-11-16 · pytest (python -m pytest -q tests) after row 4, per-place seeds · Windows · 258 passed, 2 skipped (live) in 81 s
New TestPlaceSeeds: `place_seed` pinned and stable; `gen system --sector-seed 7 --hex H` byte-identical to `gen sector --seed 7 --systems` systems/H for three hexes (system.json, names.json, recipe.json, map.svg, orbits.svg); default sector writes no systems/. No existing expectation changed.

### T-20261116-16 · 2026-11-16 · pytest (python -m pytest -q tests) after ink-and-parchment period 1600 · Windows · 255 passed, 2 skipped (live) in 78 s
- New: test_builtin_style_period (ink-and-parchment carries 1600, topographic none; `check --style ink-and-parchment` on a world adds a passing period 1600 bar without --period).
- led to: none

### T-20261116-15 · 2026-11-16 · pytest (python -m pytest -q tests) after row 3, `check --period` · Windows · 254 passed, 2 skipped (live) in 81 s
- New: test_period_lint_rules (every row-3 year one year early fails and on the year passes; chart and mappa rules; Greenwich only warns; unknown convention or kind refused), test_check_period_cli (topographic world passes 1900, fails 1700 on bar scale, compass rose and tints; `--uses robinson` fails 1900; ink-and-parchment chart passes 1500).
- led to: none

### T-20261116-11 · 2026-11-16 · pytest (python -m pytest -q) + blocks sweeps after the path restart · Windows, Python 3.14 · 244 passed, 2 skipped (live) in 91 s
- New tests (TestBlocks, 5): a blocks map passes every bar and regenerates byte for byte; a 49x49 map has a 7x7 grid with bar 40; 200 seeds pass the goal and block bars; the block bars catch a dropped exit and a short count; maps under 21 squares refused; the CLI writes method blocks.
- Sweep seeds 1 to 1,000 at 48x36: 0 bar failures; restarts 0: 658, 1: 221, 2: 80, 3: 32, 4: 6, 5: 3.
- `check --range blocks`, 500 seeds: loop share mean 0.666, dead-end share mean 0.173, path over diagonal 0.833 to 2.167 (mean 1.342), open floor 0.182 to 0.331; loop x dead-end 42 bins, fullest 12.0 %; path x open 74 bins, fullest 7.2 %. No dominant bin.
- Byte identity: sha256 over bsp, cave and cyclic (seeds 1 to 8, cyclic with 2 branches) and 4 battle maps, all files, is the same before and after the change.
- led to: L-054

### T-20261116-10 · 2026-11-16 · blocks sweeps while building row 7 (scratch, not kept) · Windows, Python 3.14 · measurement only
- Restarts to reach the bar, 500 seeds on a 6x5 grid: exit chance 0.55 mean 2.66, worst 24; 0.65 mean 0.49, worst 5; 0.75 mean 0.07, worst 3. Chose 0.65 so restarts stay visible in the recipe.
- First full check sweep (200 seeds, 48x36, exit chance 0.55): every bar passed except OCR, skipped without tesseract.
- `check --range blocks` before the path restart: path over diagonal minimum 0.767 (46 steps, under the 48-step bar).
- led to: L-052, L-053, L-054
### T-20261116-13 · 2026-11-16 · before/after output comparison for the port flag (seed 7, 1600 cells, raster 64) · Windows, Python 3.14 · identical apart from the new field
- map.svg, mesh.json, names.json, heights.png, heights.pgw, sources.json byte-identical; features.geojson and recipe.json equal once `port` and `ports` are removed. 39 of 48 settlements are ports on this small map.
- led to: L-057

### T-20261116-12 · 2026-11-16 · pytest (python -m pytest -q) after row 21, ports only on open coast · Windows, Python 3.14 · 244 passed, 2 skipped (live) in 81 s
- New tests/test_ports.py (5): enclosed sea is not open; child with no border sea inherits the parent's mask (and stays closed when the parent says enclosed); every world and child settlement's port flag equals "touches open sea", lakeshore-only towns are never ports, recipe `ports` matches; bar 14 passes on world and child and fails when an inland town is flagged; same seed byte-identical. Bar counts in test_mpw.py moved 13 to 14 and 16 to 17.
- led to: L-055, L-056

### T-20261116-9 · 2026-11-16 · unittest (tests/) + grandchild sweep after the edge-outlet fix · Windows, Python 3.14 · 238/238 passed, 2 skipped (live) in 78 s
- New tests: hydrology drains a no-sea valley to its outlet and ignores outlets when sea exists; a seed 2 all-land grandchild has border outlets, rivers, and passes every bar with determinism; bar 7 says "too arid to judge" when the floor is raised.
- Sweep seeds 1-8 (20 maps): g2_0 now 93 river cells, 0 failures, 1 edge outlet, bar 6 max 0.149 parent spacings (was 0.158); g1_0 40 rivers / 4 outlets, g1_1 13 rivers / 10 outlets, all bars pass.
- Byte identity (sha256 of all 8 files) against origin/main: all 8 worlds, 8 children and grandchild g2_1 (which has sea) identical; only the three all-land grandchildren changed.
- led to: L-047, L-009 closed

### T-20261116-8 · 2026-11-16 · bar 7 rain-shadow sweep before changing the bar (scratch sweep7.py) · Windows, Python 3.14 · measurement only
- 24 seeds: world 1,600 cells, child (default window) 4,000 cells, 48 maps. Windward/leeward samples counted as bar 7 does.
- 12 maps had both sides at 20 or more samples (judged); 36 skipped. Judged: windward 136.6-617.8 cm/yr, leeward 4.7-43.2, smallest difference 115.3 (child seed 24: 136.6 vs 21.3). Every judged map had windward above leeward.
- The L-009 failure was an arid child at exactly 20 samples, 4.9 vs 5.2 cm/yr: a desert with no moisture to shadow, judged on noise.
- Decision from these numbers: judge the shadow only when the windward mean is at least 50 cm/yr (a third of the smallest judged windward mean, ten times the arid case), keeping the 20-sample floor. None of the 12 judged maps changes verdict.
- Grandchild sweep (scratch sweep.py, seeds 1-8, world and child 1,600 cells, up to two all-land grandchild windows): before the fix g2_0 failed bar 1 (60 river cells, 60 failures); g1_0 and g1_1 passed only because they had 0 rivers.
- led to: L-047, L-048

### T-20261116-5 · 2026-11-16 · skill evals after shortening the description to 1,007 characters · 10/10 runs
- `python evals/run.py`: trigger-find-place 3/3; trigger-read-gpx, trigger-path, trigger-export 1/1 each; four decoys 0 fired (1 run each). Pytest 233 pass, 2 skip on the merged branch.

### T-20261116-4 · 2026-11-16 · skill evals, `python evals/run.py` (`claude -p --plugin-dir`, sonnet, other installed plugins present) · Windows · 38/38 runs passed
- L-042 description edit (find phrase names OpenStreetMap or Overpass data with its licence; example 'which projection for a world map' swapped for 'find OpenStreetMap data for this area and its licence'; 'projects points' dropped from the list): trigger-find-place 3/3, then decoys 4/4 not fired (one run each).
- Body trim (SKILL.md 24,508 -> 8,748 bytes; per-verb detail moved verbatim to references/cli-read-write.md, cli-find.md, cli-generate.md, cli-render.md, cli-export.md), then the whole suite with each case's run count: triggers 8/8 at 3 of 3 (find-place 3/3 again, so 6/6 after the edit); decoys 4/4 at 0 of 3 (evergreen-map, chartwright, polywright-capture, pixelwright fired or nothing); action-gen-dungeon evidence exit 0; action-export-vtt evidence exit 0.
- Each run in a fresh temp folder with copies of scripts/ and tests/fixtures/. Trigger runs capped at 3 turns. Unittest: 220 pass, 2 skip.
- not covered: interactive loop, second OS, repeated action runs, whether the moved detail is read when needed (actions passed, so the pointers held for dungeon and dd2vtt).
- led to: L-042 closed
### T-20261116-7 · 2026-11-16 · skill eval trigger-projection, `claude -p --plugin-dir` (sonnet) · Windows · 3/3 passed
- Prompt: projection choice for Antarctica plus projecting three points. mapwright fired in 3 of 3 runs, so the description change did not undertrigger it.
### T-20261116-6 · 2026-11-16 · unittest (tests/) · Windows · 241 passed, 2 skipped (after merging origin/main)
- New: battle title/legend outside the grid (square + hex, 3 seeds), treasure on a floor cell inside its room (cyclic --branches 2/4/8, 40 seeds each), legend CLI on battle and dungeon recipes. Battle render PNG rendered twice: same md5.
- led to: L-044, L-045, L-046
### T-20261116-3 · 2026-11-16 · pytest + scratch sweeps (mapwright-lab/s17/sweep_battle.py, sweep_cyclic.py) · Windows · 225 passed, 2 skipped
- gen battle 30 seeds x 3 densities x 2 grids, 30x20, check (determinism on seeds 1-3): 0 failing; feature share square sparse 0.098/0.136/0.173 (min/mean/max), normal 0.220/0.222/0.227, dense 0.320/0.322/0.327; hex sparse 0.055/0.075/0.098, normal 0.220/0.222/0.227, dense 0.320/0.322/0.328; legend kinds = kinds present on all 180 maps; 0.8-2.1 s per 30 maps.
- gen dungeon cyclic --branches 2/4/8, 30 seeds 48x36: 0 failing (rank, adjacency, key before lock, return path, goal sealed); 2.0, 4.0, 7.7 branches per map; 1.6-2.1 s per 30.
- Default byte-identity against origin/main: cyclic and bsp seeds 1, 5, 9, 13, 21, 30 (grid.json, map.svg, map.png, features.geojson) identical; battle --density sparse grid.json and map.png identical for seeds 3, 31.
- System HZ key: 60 seeds x 2 views, key present iff band drawn (3 schematic maps with no band).
- Not done: L-009 first half (landlocked window drain), left open.
- led to: L-041 closed, L-050, L-051

### T-20261116-2 · 2026-11-16 · skill evals, `claude -p --plugin-dir` (sonnet, other installed plugins present) · Windows · 13/14 passed (one run per case)
- Triggers 7/8: read-gpx, write-kml, fantasy gen, sci-fi sector, deck plan, path, export fired mapwright. trigger-find-place missed (no skill; answered the OSM licence from memory and offered Overpass); two reruns: 1 hit, 1 miss, so 1 of 3 (L-042).
- Decoys 4/4: codemap (evergreen-map), choropleth (none), 3D place (polywright-capture), pixel tiles (pixelwright + comfyui-gen).
- action-gen-dungeon: skill fired, `mpw.py check out/dng` exit 0.
- action-export-vtt (evidence tightened: a gen-battle recipe with seed 3, 20x16, must pass `check` and out/battle.dd2vtt must exist): skill fired, wrote the recipe to ./battle-seed3 (outside out/) and exported from it; check 13 bars pass, exit 0. First grading searched only out/ and failed, so the evidence now globs the whole run folder. Control: the same .dd2vtt alone in a folder fails the evidence (exit 1), so a hand-written script no longer passes.
- not covered: interactive loop, second OS, repeated runs of the action cases.
- led to: L-042, C-20261116-3

### T-20261116-1 · 2026-11-16 · skill evals, `claude -p --plugin-dir` (sonnet, Claude Code 2.1.281, other installed plugins present) · Windows · 14/14 passed
- Triggers 8/8 at 3 of 3 (read, write, find, fantasy gen, sci-fi sector, deck plan, path and chokepoints, engine/VTT export). trigger-read-gpx first went 0/3 (the description had dropped "reads"); fixed by "Reads and converts" and the phrase 'what is in this GPX', then 3/3. write-kml 2/3 and find-place 2/3 before the fix, 3/3 after.
- Decoys 4/4 at 0 of 3: codemap (no skill), choropleth (no skill), 3D town park (polywright-capture fired), pixel tileset (pixelwright fired).
- action-gen-dungeon: with plugin `mpw.py gen dungeon` + `check`, out/dng passes `check` (exit 0). Baseline (no plugin) wrote its own script, no recipe.json, `check` fails.
- action-export-vtt: with plugin `gen battle` + `export` (dd2vtt 100 px, 41 LOS segments, recipe kept). Baseline also wrote a valid dd2vtt by hand (70 px, 24 segments): redundant on file evidence, so the evidence now requires the recipe folder to pass `check`.
- One run per arm for actions; trigger runs are headless `claude -p`, not the interactive loop. Untested elsewhere (no second OS run).
- Worth (lite, `evergreen.py worth --lite`): UNPROVEN, listing ~250 tokens per session, body ~5.9K per use, 0 uses in 60 days (new plugin); baseline gap closed. Static note: Generate and Export sections could move to references/. Verdict stays UNPROVEN until real use or a `--heavy` A/B.
- led to: C-20261116-1

### T-20261115-7 · 2026-11-15 · unittest (tests/) + path sweeps · Windows, Python 3.14 · 221/221 passed, 2 skipped (live) in 57 s
- New (18, tests/test_path.py): fixtures are generated in the test (bsp 30x24, cyclic 48x36, cave 30x24, square battle 20x16, hex battle 16x14, deck 30x15, world 500 cells); the file runs in about 2.5 s.
- `path`: A* cost equals no-heuristic Dijkstra to 1e-9 on 60 random pairs per fixture (over 300 reachable pairs); re-summed step costs equal the reported cost; every step is an edge, enters a floor square, and a diagonal has both orthogonal squares open and touches no door; symmetric fixtures give A to B = B to A; one-way doors of the cyclic fixture are entered only from their source side over 200 pairs; CLI output byte-identical on rerun; a city is refused. Hand grids: two diagonal floors between walls give no route; a 3x3 room costs 2 sqrt 2 corner to corner, 4 with `--moves 4`.
- Sweep, 300 random pairs per map (A* expanded over Dijkstra expanded, largest cost difference): dungeon bsp 48x36 0.52, 0; cave 0.39, 7e-15; square battle 0.21, 0; hex battle 0.19, 0; deck 0.30, 0; world 2,000 cells 0.59, 0. 600 searches take 0.07 to 0.15 s per map. A 16k-cell world (3,703 land cells) answers one cross-continent A* and a full travel map in under 0.05 s each.
- `path --field`: every cell equals single-pair Dijkstra to the goal (all cells of bsp and hex, every third on the world), every reachable non-goal cell's flow step is lower, following the flow re-sums to the value, unreachable cells are null with no next step.
- `travel`: Tobler speeds match the section 8.3 table to 0.005 km/h; flat speed 6 exp(-0.175) = 5.036742 km/h (L-037); a flat 6 km leg takes 6 / 5.036742 h within 1e-6 both ways; 150 m up over 1 km is slower than down; time never decreases along the shortest-path tree; random world pairs differ by direction.
- `check --chokepoints`: articulation points equal brute force (remove each cell, recount) on all six grid fixtures; removing a cell splits the map exactly when it is reported; a ring has none; a 1-wide corridor between two 2x3 rooms gives five cut cells, cut-offs 1 to 5, minimum cut 1. Dungeon bsp 48x36: 40 cut cells, minimum cut entrance to goal 1; the cyclic 48x36: none, minimum cut 2 (its two paths).
- `check --fair`: distances equal Dijkstra, areas + ties + unreached = floor, fair.json byte-identical on rerun. Dungeon bsp 48x36: areas 509 and 325 (ratio 1.57).
- led to: C-20261115-7, L-036, L-037, L-038

### T-20261115-6 · 2026-11-15 · unittest (tests/) + dungeon sweeps · Windows, Python 3.14 · 203/203 passed, 2 skipped (live) in 54 s (after rebase on 0.8.0)
- New (15, tests/test_places.py; 1, tests/test_find.py).
- Backward compatibility: two recipes written by 0.7.0 (tests/fixtures/dungeon-070-bsp, dungeon-070-cave) pass `check` with byte-identical regeneration and get no goal bars. New behaviour is keyed on `params.goal`, which 0.7.0 recipes lack. The cave defaults redraw the 0.7.0 cave cell for cell.
- Goal and path (backlog rows 8, 9, 10). Entrance by two sweeps (the room centre, or square, farthest from a first point), goal at the square farthest from the entrance by BFS. Bar: goal distance equals the map maximum, tolerance 0. Minimum path: map width. Measured over 100 seeds before the bar, path over width: bsp 48x36 min 1.33 (median 1.88), cave 48x36 min 0.92 (1.50), bsp 30x24 min 1.00, cave 30x24 min 0.70. Cave fell under the width on 1 of 100 seeds at 48x36 and 6 of 100 at 30x24, so a short bsp or cave map is re-rolled from stream 3000 + k (at most 16). Over 200 seeds: re-rolls bsp 0, cave 1 (48x36) and 19 (30x24); 0 bar failures. Isolated walls (fewer than two orthogonal wall neighbours) are turned to floor until none is left; doors that lose a wall flank become floor. Forced faults fail their bar: goal moved next to the entrance (farthest and path), a wall square opened on all sides (isolated).
- Cave sweep (row 5), 48x36, seeds 1 to 100, before pruning and cleanup. Largest-region share = largest floor region over all floor; open-floor share = floor kept over all squares.

| setting | fill | passes | birth/survival | largest-region share (mean, min) | open-floor share (mean, min) |
|---|---|---|---|---|---|
| sweep | 0.40 | 2 | 5/4 | 0.993, 0.920 | 0.649, 0.571 |
| sweep | 0.40 | 3 | 5/4 | 0.994, 0.925 | 0.668, 0.579 |
| sweep | 0.40 | 4 | 5/4 | 0.996, 0.929 | 0.679, 0.591 |
| sweep | 0.40 | 5 | 5/4 | 0.996, 0.932 | 0.687, 0.598 |
| sweep | 0.45 | 2 | 5/4 | 0.912, 0.450 | 0.491, 0.224 |
| sweep | 0.45 | 3 | 5/4 | 0.925, 0.461 | 0.505, 0.227 |
| sweep | 0.45 | 4 | 5/4 | 0.931, 0.461 | 0.513, 0.224 |
| sweep | 0.45 | 5 | 5/4 | 0.933, 0.465 | 0.518, 0.225 |
| sweep | 0.50 | 2 | 5/4 | 0.606, 0.187 | 0.248, 0.071 |
| sweep | 0.50 | 3 | 5/4 | 0.640, 0.214 | 0.257, 0.068 |
| sweep | 0.50 | 4 | 5/4 | 0.651, 0.220 | 0.258, 0.067 |
| sweep | 0.50 | 5 | 5/4 | 0.660, 0.221 | 0.258, 0.064 |
| sweep | 0.55 | 2 | 5/4 | 0.332, 0.126 | 0.091, 0.031 |
| sweep | 0.55 | 3 | 5/4 | 0.365, 0.139 | 0.092, 0.029 |
| sweep | 0.55 | 4 | 5/4 | 0.387, 0.146 | 0.091, 0.027 |
| sweep | 0.55 | 5 | 5/4 | 0.406, 0.148 | 0.090, 0.025 |
| code default (0.7.0) | 0.45 | 5 | 5/4 | 0.933, 0.465 | 0.518, 0.225 |
| Johnson et al. 2010, r=1 | 0.50 | 4 | 5/4 | 0.651, 0.220 | 0.258, 0.067 |
| Johnson et al. 2010, r=2, T=13 | 0.50 | 4 | 13/13, radius 2 | 0.920, 0.371 | 0.425, 0.128 |
| STN (Johnson), 3 passes | 0.50 | 3 | 5/4 | 0.640, 0.214 | 0.257, 0.068 |
| Caves of Qud | 0.55 | 2 | 6/5, border 2 | 0.976, 0.551 | 0.571, 0.275 |

- Cave ruling: the default stays fill 0.45, 5 passes, 5/4. Fill moves the cave far more than passes do. At 0.40 the cave is two thirds open, an open field more than a cave. At 0.50 and above a third or more of the floor sits in cut-off pockets that pruning throws away, and open floor drops to a quarter. Caves of Qud's rule scores better on both metrics but needs a different rule and a two-square border; it is one flag set away (`--fill 0.55 --passes 2 --birth 6 --survival 5 --border 2`). Johnson's numbers are read as counting the cell itself (T=5 of 9 is 5/4 here); the paper's 50 % fill with our 8-cell rule loses a third of the floor.
- Cyclic (row 1), 48x36, seeds 1 to 200: 0 failures on cycle rank 2 to 5, edges between bordering cells with an open door, key before lock with the lock a real gate (graph and squares, one-way doors honoured), return path from goal to entrance, completion path (key first) at least the map width, no isolated walls. 10 deterministic graph re-rolls in 200 seeds (stream 2000 + k); 30x24 needs 501 re-rolls in 200 seeds. Forced faults fail their bar: key moved to the goal, the goal valve reversed (lock no longer a gate, on the graph and on the squares), lock and valve turned one-way into the goal (no return path), an edge between cells that do not touch, five duplicate edges (rank 10). Maps under 22x22 refused.
- Expressive range (row 2), `check --range`, 48x36, seeds 1 to 500. Metrics: loop share (corridor squares, in no 2x2 open block, that lie on a loop, over corridor squares; 0 when there are none), dead-end share (squares in parts joined to the rest by a single bridge, over open squares), completion path over the map diagonal, open-floor share. Normalised min to max across the sample, 10 x 10 bins. Stability is the total variation distance between the first 250 seeds and all 500 on the same bins.

| method | loop share (min, mean, max) | dead-end share | path / diagonal | open-floor share | loop x dead-end: bins used, fullest, TV | path x open: bins used, fullest, TV |
|---|---|---|---|---|---|---|
| bsp | 0.000, 0.499, 1.000 | 0.000, 0.380, 0.998 | 1.033, 1.528, 2.300 | 0.369, 0.469, 0.595 | 73, 4.4 %, 0.114 | 72, 6.2 %, 0.142 |
| cave | 0.000, 0.033, 1.000 | 0.000, 0.312, 1.000 | 0.800, 1.224, 1.983 | 0.225, 0.523, 0.715 | 12, 65.2 % DOMINANT, 0.018 | 58, 9.6 %, 0.128 |
| cyclic | 1.000, 1.000, 1.000 | 0.000, 0.000, 0.000 | 0.900, 2.044, 3.767 | 0.081, 0.185, 0.299 | 1, 100 % DOMINANT, 0.000 | 57, 4.8 %, 0.138 |

- Range reading: cyclic has every corridor on a loop and no dead ends by construction, so its first heatmap is one bin; that is the flag doing its job, and dead-end branches are the open item. Most caves have no one-square corridor at all, so loop share reads 0 for 65 % of them: the metric does not describe caves. Distances of 0.11 to 0.14 between 250 and 500 seeds on 100 bins say the fine plot is still moving; the book's rule (grow until it stops) wants more seeds or coarser bins, not yet chosen. Time: 500 seeds bsp 3 s, cave 7 s, cyclic 1 s.
- geoBoundaries (fetch): an API answer whose `boundaryLicense` is "Open Data Commons Open Database License 1.0" (the LIE ADM0 shape, mocked) is recorded with that licence and its source in sources.json and CREDITS.txt; the file named by its `gjDownloadURL` gets the same licence; a geoBoundaries file without an API answer is recorded as licence unknown, never as CC BY 4.0.
- led to: L-033, L-034, L-035

Older runs (T-20261114-1 to T-20261115-5): [TESTS-ARCHIVE.md](TESTS-ARCHIVE.md).

### T-20261116-23 · 2026-11-16 · gen dungeon --corridor on blocks
- pytest tests: 268 pass, 2 skip (84 s). CorridorWidth.test_blocks_wide_halls: seeds 1-20 default equals corridor 1; corridor 2 one agent-2 region on at least 18 of 20. Sweep seeds 1-100 at 48x36: agent 2 at corridor 2 one region 97/100; agent 3 at corridor 3 84/100; corridor 1 agent 2 0/100.

### T-20261116-22 · 2026-11-16 · gen dungeon --corridor on cyclic
- pytest tests: 267 pass, 2 skip (81 s). New test_cyclic_wide_corridors_keep_the_gate: seeds 1-10 corridor 1 equals default; corridor 2 has no door squares, goal unreachable without the key (gap gated), completion path found, eroded agent 2 is one region touching every room; cyclic corridor 4 refused. Sweep seeds 1-100: agent 2 joins all rooms 0/100 at corridor 1, 100/100 at 2; agent 3 at corridor 3 90/100. Default cyclic seed 3 files byte-identical to origin/main; check passes at corridor 2 (L-059).

### T-20261116-21 · 2026-11-16 · gen dungeon --corridor
- pytest tests: 266 pass, 2 skip (73 s). CorridorWidth: seeds 1-20 corridor 1 equals default; corridor 2 eroded at agent 2 is one region touching every room; cave and corridor 4 refused. Sweep seeds 1-100: agent 2 joins all rooms 0/100 at corridor 1, 100/100 at 2; agent 3 at corridor 3 97/100. Default seed 3 files byte-identical to 0.20.0; check passes at corridor 2 and 3.

### T-20261116-20 · 2026-11-16 · path --agent
- pytest tests: 264 pass, 2 skip (71 s). AgentBars: hand grid (a one-square gap blocks a 2-wide body, a two-square gap passes); bsp, cave and battle at agent 2: 20 random pairs each, every path square's 2 x 2 body is walkable and the cost is never below the agent-1 cost; CLI JSON carries agent; agent 0 refused; hex, deck and world refused.

### T-20261116-19 · 2026-11-16 · nav --agent erosion
- pytest tests: 261 pass, 2 skip (71 s). TestNav.test_agent_erosion: 6x4 hand grid against the fit rule; 20 recipes (block, cave, cyclic, battle x 5 seeds) at agent 2 and 3 pass every nav bar and every rect square's N x N body is walkable; agent 1 byte-identical to no flag; agent 0 refused.
