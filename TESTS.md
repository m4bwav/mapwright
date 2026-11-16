# Tests: mapwright

Companions: [RESEARCH.md](RESEARCH.md), [CHANGELOG.md](CHANGELOG.md), [LEARNINGS.md](LEARNINGS.md).

Test runs for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and `scripts/mpw.py`. Unit tests live in `tests/`, skill cases in `evals/evals.json` (not run yet). A test passes on evidence, never on a transcript's claim.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per notable result, then `led to:`. Newest first.

## Runs

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
### T-20261115-5 · 2026-11-15 · unittest (tests/) + aistyle grid on a real server · Windows, Python 3.14, Chrome 157, ComfyUI 0.44.2, Z-Image Turbo (bf16) on an RTX 5060 Ti 16 GB · 188/188 passed, 2 skipped (live) in 43 s
- New (24 and one live test, tests/test_aistyle.py; the HTTP layer and the SVG rasteriser are faked, so no GPU, network or browser): looks and template; slots keep their types; workflow hash stable and seed-sensitive; denoise step grid; model size; a swapped model marks the licence unstated; `render_parts` joins to the byte-identical render in all six styles; the control picture has no text, circles, legend, scale bar or north arrow; dry run writes the control PNG and workflow and makes no HTTP call; a full faked pass calls stats, upload, prompt, history, view in that order and writes picture, raw styled picture and sidecar (model, licence class, look, prompt, seed, denoise, steps, workflow hash, tool version, numbers; no server address); the check bar passes, fails on a swapped picture (sha256) and on a picture shifted 9 px (land IoU), skips when the picture is gone, and is absent with no sidecar; server errors (400 on queue, an execution error, a timeout) and a missing host are plain messages; doctor without a host makes no call; no LAN address in any public file.
- Label bars on a styled picture: the code-set layer of the composite (labels, rivers, legend, scale bar, north arrow) equals the labelled render's layer line for line in atlas and ink-and-parchment, and `label_bars` gives the same result for both, so bars 14 and 15 (no overlap, none cut by the edge) hold by construction. The OCR read-back bar stays skipped: tesseract is not installed here; the reason is printed, never a pass.
- Live (`MAPWRIGHT_LIVE=1` and a server in `MAPWRIGHT_COMFYUI`): one real pass, painted-atlas, seed 1, denoise 0.45, bar passed (land IoU 0.9572); `check` on that folder showed bar 17 PASS and, for a second picture made at 0.65, bar 18 FAIL (IoU 0.8997). Passed 2026-11-15.
- Grid (tests/aistyle_grid.py): 72 pictures at 1024 x 1024, 9 steps, cfg 1, res_multistep, simple. World seed 7 (16k cells, 81 settlements, 22 lakes, 1941 river samples): 4 looks x seeds 1, 2, 3 x denoise 0.35, 0.45, 0.55, 0.65 (48). World seed 23 (52 settlements): 4 looks x 3 seeds x 0.45, 0.55 (24). Both worlds pooled below; the denoise that runs is steps / int(steps / typed).

| Look | Denoise typed (as run) | Pass | Land IoU min / mean / max | Coast within 3 px | Settlements on painted land, min | Rivers on painted land, min | Lakes the model kept | River lines the model kept (noise floor) |
|---|---|---|---|---|---|---|---|---|
| ink-and-parchment | 0.35 (0.36) | 3 of 3 | 0.9435 / 0.9612 / 0.9707 | 0.92 | 0.9877 | 0.9974 | 0.56 | 0.78 (0.01) |
| ink-and-parchment | 0.45 (0.45) | 6 of 6 | 0.9250 / 0.9442 / 0.9619 | 0.87 | 0.9615 | 0.9948 | 0.09 | 0.54 (0.02) |
| ink-and-parchment | 0.55 (0.5625) | 0 of 6 | 0.8728 / 0.8999 / 0.9138 | 0.68 | 0.9383 | 0.9861 | 0.02 | 0.22 (0.03) |
| ink-and-parchment | 0.65 (0.692) | 0 of 3 | 0.7301 / 0.7442 / 0.7599 | 0.35 | 0.7160 | 0.9567 | 0.03 | 0.13 (0.04) |
| painted-atlas | 0.35 (0.36) | 3 of 3 | 0.9638 / 0.9681 / 0.9732 | 0.91 | 1.0000 | 0.9969 | 0.79 | 0.60 (0.10) |
| painted-atlas | 0.45 (0.45) | 6 of 6 | 0.9526 / 0.9591 / 0.9697 | 0.90 | 0.9615 | 0.9964 | 0.65 | 0.42 (0.09) |
| painted-atlas | 0.55 (0.5625) | 4 of 6 | 0.9226 / 0.9344 / 0.9447 | 0.78 | 0.9136 | 0.9856 | 0.43 | 0.27 (0.09) |
| painted-atlas | 0.65 (0.692) | 0 of 3 | 0.8667 / 0.8760 / 0.8914 | 0.47 | 0.8889 | 0.9820 | 0.35 | 0.20 (0.11) |
| satellite | 0.35 (0.36) | 3 of 3 | 0.9495 / 0.9547 / 0.9583 | 0.83 | 0.9877 | 0.9959 | 0.88 | 0.54 (0.14) |
| satellite | 0.45 (0.45) | 6 of 6 | 0.9244 / 0.9419 / 0.9527 | 0.79 | 0.9423 | 0.9956 | 0.76 | 0.41 (0.14) |
| satellite | 0.55 (0.5625) | 2 of 6 | 0.9024 / 0.9204 / 0.9342 | 0.72 | 0.8846 | 0.9890 | 0.63 | 0.34 (0.18) |
| satellite | 0.65 (0.692) | 0 of 3 | 0.8919 / 0.8954 / 0.8997 | 0.49 | 0.8148 | 0.9701 | 0.11 | 0.31 (0.26) |
| watercolour | 0.35 (0.36) | 3 of 3 | 0.9771 / 0.9797 / 0.9810 | 0.98 | 1.0000 | 0.9948 | 0.83 | 0.51 (0.01) |
| watercolour | 0.45 (0.45) | 6 of 6 | 0.9596 / 0.9660 / 0.9736 | 0.94 | 0.9423 | 0.9938 | 0.69 | 0.39 (0.01) |
| watercolour | 0.55 (0.5625) | 5 of 6 | 0.9389 / 0.9465 / 0.9547 | 0.82 | 0.9231 | 0.9902 | 0.40 | 0.18 (0.02) |
| watercolour | 0.65 (0.692) | 0 of 3 | 0.8875 / 0.8930 / 0.8982 | 0.54 | 0.8642 | 0.9706 | 0.35 | 0.12 (0.03) |

- How it is measured. Truth: the recipe's own land mask rastered at the picture's size, with lake polygons and a 3 px band round every river left out, because lakes and rivers are redrawn in code. Styled picture: land or sea by colour alone, from a 15-bit colour table trained on that picture's pixels at least 12 px from the true coast, then a 3x3 close and open. IoU = land in both / land in either. The clean render scores 0.972 to 0.988 on the same measure (its coast line and anti-aliasing cost the rest). Cross-check with the fixed water rule of `read`: within 0.02 of the table on the three blue-sea looks at denoise 0.45 and below, and useless on ink-and-parchment (0.26 to 0.41 on the clean render), which is why the table is used (L-030).
- Bars, set from the table: land IoU >= 0.92 (worst picture at 0.45 or below: 0.9244; best at 0.65: 0.8997); code-set rivers with painted land within 3 px >= 0.98 (worst at 0.45 or below: 0.9938); settlements with painted land within 3 px >= 0.94 (worst at 0.45 or below: 0.9423, 3 of 52). Passing all three: 12 of 12 at 0.35, 24 of 24 at 0.45, 11 of 24 at 0.55, 0 of 12 at 0.65. Denoise ceiling: 0.45 typed, which runs as 0.45; the next grid value tried, 0.55 (runs as 0.5625), fails more than half. The IoU and settlement bars sit close under the worst 0.45 picture, so another world can fail at 0.45 now and then: change the seed or lower the denoise, do not loosen the bar.
- Rivers, said plainly: the model does not keep them. Share of visible river samples where the styled picture still has the clean render's line (a third of its centre-minus-sides colour vector within 3 px): 0.51 to 0.78 at 0.35, 0.39 to 0.54 at 0.45, 0.18 to 0.34 at 0.55, with a noise floor of 0.01 to 0.03 on ink and watercolour and 0.09 to 0.26 on atlas and satellite, where texture passes the test by chance. Lakes fare the same (0.09 to 0.76 kept at 0.45). So there is no river-survival bar on the model's picture: rivers and lakes are set in code on top (L-028), which makes them exact, and the bar that remains is that they sit on painted land.
- What the eye sees: at 0.45 and below the result is a light repaint of the code render (texture, softer relief, paper). The heavily painted pictures are the 0.65 ones, and they redraw the coast. A stronger look needs a control image as a second hold (not built).
- Timings: control render 2 s (browser), server 13 to 17 s per picture warm (31 to 91 s for the first, model load), recipe masks 0.7 s, measure 0.5 s per picture, composite 2 s.
- led to: L-028, L-029, L-030, L-031, L-032

### T-20261115-4 · 2026-11-15 · unittest (tests/) + export sweep · Windows, Python 3.14, Chrome 157 · 163/163 passed, 1 skipped (live) in 38 s
- New (32, tests/test_export.py). Each proof reads the written file with code that does not share the writer's arithmetic.
- Heightmaps (world 128 px raster, region 100 x 60): Unity RAW 129 and 513 (file size N x N x 2 bytes, values 0 to 65535), Unreal PNG 253 and 1009, Godot R16 and 16-bit PNG, Roblox 8 and 16 bit. Bar: read-back height within one quantisation step of the recipe height after the stated bilinear resample. Measured: half a step in every case (worst 0.5 steps over 8 seeds x world and region x 6 targets; step 0.13 m at 16 bit over an 8.4 km range, 33 m at 8 bit). At the recipe's own size the Godot export is the identity. Sizes outside the engine's list are refused (512 for Unity, 1000 for Unreal, 5000 for Roblox). The first RAW row is the recipe's north row and `--flip` reverses the rows (asymmetric map). Unreal's Z scale and Z location put values 0 and 65535 back on min and max within 1 cm. Roblox colormap: every pixel is a material colour, same size as the heightmap, Mud pixels match the below-sea-level count within 3 percent.
- Tiled: dungeon, square battle (base64 + zlib, 16 px tiles) and a 2-deck ship parse; layer size equals the grid; every gid is 0 or in the tileset, whose image is columns x tile wide; floor cells equal the recipe's as a set and every row decodes to the recipe's symbols; wall and door object counts equal the recipe's; the CSV equals local ids with -1 for empty. Forced failures fail their bar: a floor tile turned to wall, gid 99, a short layer, an object outside the map, broken JSON; a flip bit on a gid is masked and passes. Hex and world recipes refused.
- Deck plans to Universal VTT: one file per deck, pixels_per_grid 50, image 40 x 21 squares x 50 px, a portal on every door square and one light per room; a door end moved 0.4 squares fails. All Universal VTT exports (dungeon, battle, 2 decks): colours match ffRRGGBB, every portal closed, no wall segment under a portal; an RRGGBBAA colour, a 6-digit colour, an open portal and a wall laid on a door each fail the new bar.
- Hex battle PNG: same canvas as map.svg (2050 x 1415 px at 100 px hexes), all 320 hex centres carry their cell's colour, 6 or fewer flat colours.
- Mesh: 33 x 33 samples give 1089 vertices and 2048 faces, all indices valid, vertex heights within 0.001 m of the resample, faces counter-clockwise from above, 128 open rim edges. With a base: 1218 vertices, 2432 faces, every edge shared by exactly two faces and crossed once each way, Euler characteristic 2, positive volume, lowest top point 2.000 mm above the bottom, longer side 100.000 mm. Removing a face gives 3 open edges; flipping one gives 3 same-way edges. Manifest sha256 equals the file's.
- Print: A4 with 3 mm bleed gives a 2551 x 3579 px PNG (exactly 216 x 303 mm at 300 dpi) and a PDF whose MediaBox is 612.283 x 858.898 pt; Letter landscape 792 x 612 pt; 150 x 100 mm with 2 mm bleed at 127 dpi gives 770 x 520 px. Bar: PNG exact, MediaBox within 0.5 pt. Measured over 60 PDFs (10 papers x 3 bleeds x 2 orientations): worst MediaBox and TrimBox difference 0.0001 pt after the box rewrite; before it Chrome's own page was off by up to 0.57 pt and failed 6 of 24. PNG sizes exact up to A2 at 300 dpi (5031 x 7087 px). The rewritten PDF opens in pypdf, PyMuPDF, mutool and poppler (hand check, not a unit test). Eight crop marks, each in the bleed on a trim line. No browser: a RuntimeError naming Chrome or Edge, exit 2, no file. The pixel table of references/games-film-print.md 6.1 is reproduced for 7 papers.
- Sweep: 20 seeds x (bsp, cave, square battle) x (tmj, tmj base64, dd2vtt), 20 hex PNGs, 20 seeds x 4 deck shapes x (tmj, dd2vtt) = 2540 bars; 8 seeds x (world, region) x (6 heightmaps, 3 meshes) = 352 bars; 0 failures.
- Timings (seed 7 world, 512 px raster): Unity 513 0.4 s, 2049 1.8 s; Unreal 1009 0.7 s, 2017 1.5 s; Roblox 4096 with colormap 6.0 s; mesh 257 0.6 s (66 049 vertices, 5 MB), 513 with base 2.1 s (18 MB); hex PNG 1.4 s; PDF 0.5 s; A4 PNG at 300 dpi 2 s, A2 5 s.
- Not measured: an import into Unity, Unreal, Godot, Roblox, Tiled or Foundry (none run here); the files are proven against their written formats only.
- led to: L-024, L-025, L-026, L-027

### T-20261115-3 · 2026-11-15 · unittest (tests/) + space sweep · Windows, Python 3.14 · 131/131 passed, 1 skipped (live) in 28 s
- New (16, tests/test_space.py): sector, real-star, system, planet (all six kinds) and deck bars pass with byte-identical regeneration; forced failures fail their bar (a world cut off from the routes, a jump route labelled long, a star moved 0.01 pc, two planets squeezed together, moons flung out of the Hill sphere, a texture sampled in (u, v) fails both the seam and the pole bar, a room walled off, a lift moved on one deck, the outer airlock door sealed); T5 file read by header in any column order; planet export to PNG with its sphere note.
- Planet tolerances measured on 20 seeds x 6 kinds at 512 px: correct sphere sampling worst seam ratio 1.54 (gas), worst pole ratio 0.375 (ice); (u, v) sampling seam 5 to 20, pole 0.8 to 1.0. Bars set at seam 2.5 x the 90th percentile adjacent-column difference (+0.5 grey level) and pole row std 0.5 x the texture std, width 512 or more. At 256 px the ice pole ratio reached 0.49 (2 of 120 failed at 0.25), so 256 is refused. Crater slope fitted -1.84 to -2.26 for b = 2 (limit 0.35).
- Sweep: 20 seeds x (subsector, sparse subsector jump 1, full sector, system any/M/F, ship, 3-deck ship, station) = 1545 bars, 0 failures; 40 seeds x 4 deck shapes, 0 failures after L-023.
- Timings (generate, then check with regeneration): subsector 0.04 s + 0.05 s; sector 32x40 0.28 s + 0.32 s; real near stars 0.01 s + 0.03 s; system under 0.01 s + 0.04 s; deck 40x21x2 0.03 s + 0.04 s; planet 512 px about 0.9 s (+1 s check), 1024 px about 4.3 s.
- led to: L-021, L-022, L-023

### T-20261115-2 · 2026-11-15 · unittest (tests/) + place sweep · Windows, Python 3.14 · 115/115 passed, 1 skipped (live) in 15 s
- New (17, tests/test_places.py): city, dungeon (bsp, cave) and battle (square, hex) bars pass with byte-identical regeneration; a city from a parent world takes its settlement's name and language and stores `../world`; forced failures fail their bar (an isolated street, a street through the wall, a walled-off room, a loose wall end, a PNG one pixel per square off, a wall outside the image, a door end off a wall, a fractional pixels_per_grid, broken JSON, a label on top of the title); hex with odd pps and Universal VTT for a city or hex map are refused.
- Sweep: 20 seeds x (city, city with sea and river, city without wall, bsp, cave, square battle, hex battle) = 1241 bars; after the fixes in L-019 and L-020, 0 failures; 60 more battle seeds per grid, 0 failures.
- Timings (generate, then check with regeneration): city 6 rings 0.14 s + 0.19 s, 10 rings 0.20 s + 0.37 s; dungeon bsp 48x36 at 70 px 0.06 s + 0.09 s; cave 80x60 at 70 px 0.16 s + 0.21 s; battle 30x20 at 100 px 0.04 s + 0.08 s, 40x30 at 140 px 0.12 s + 0.15 s; hex 30x20 0.01 s + 0.03 s.
- led to: L-018, L-019, L-020

### T-20261115-1 · 2026-11-15 · unittest (tests/) · Windows, Python 3.14 · 98/98 passed, 1 skipped (live) in 13 s
- New (18, tests/test_find.py, network mocked): every catalogue entry and every result of 11 offline queries and of an online query (mocked Nominatim, Commons, LoC) has a licence and a credit; Commons per-file licence and author read from extmetadata; ten rapid Nominatim requests never closer than 1 s apart; the rate holds across two processes through rate.json; 429 reports Retry-After; 14 never-scrape URLs refused with no request made; look-alike hosts not refused; planet and global GEBCO refused; 300 MB Content-Length refused and a stream past the cap stopped with no file left; a second fetch is a cache hit with no request; sources.json and CREDITS.txt hold both sources' credits; an unknown host needs --licence and --credit; the OpenTopography key reaches the request but not sources.json or CREDITS.txt; CLI exits non-zero on a refusal.
- Live smoke (MAPWRIGHT_LIVE=1, one Nominatim request for Reykjavik): passed 2026-11-15.
- led to: L-016, L-017

### T-20261114-4 · 2026-11-14 · unittest (tests/) + tests/roundtrip_trace.py · Windows, Python 3.14.6 · 81/81 in 13 s
- New (20, tests/test_read.py): PNG decoder (RGB round trip, all five filters, RGBA over white, palette at 1 bit, grey at 2 bit, 16 bit); rings with a hole and an island, diagonal pixels kept apart; Douglas-Peucker; thinning to one centre line; affine from 6 exact GCPs recovers the transform within 1e-9 and rms under 1 mm; 3 points flagged as proving nothing, a 0.001 deg error shows as tens of metres, collinear points refused; world file round trip within 1e-9; read without tesseract says "not sure" in text, printed scale, scale, georeference, legend and names; a fake tesseract's TSV gives words, a low-confidence count and the 1:50,000 scale; GCPs write a .pgw and the right metres per pixel; `--answers` gives ok, mismatch, dropped and not sure verdicts and catches a scale bar 50 percent off; trace georeferenced by GCPs and by `--world auto` agree; a coloured river traces to one line; raster round trip bar.
- Round trip, stdlib land raster (topographic, 512 px, no labels), seeds 7, 11, 23 at 4000 cells, distances in raster px (1 px = 1.95 km): recipe coast to traced median 0.26-0.29, p95 0.75-2.96; traced to recipe coast median 0.49-0.52, p95 0.66-0.67. Bar in the unit test: median <= 1 px and p95 <= 4 px both ways.
- Round trip, full headless Chrome render (1000 px, labels, roads, rivers, legend), same seeds, coast plus lake rings: recipe to traced median 0.57-0.61 px, p95 2.98-7.82 px; traced to recipe median 1.06-1.23 px, p95 20.6-47.7 px. The traced-to-recipe tail is real non-water ink (label halos, legend, scale bar, north arrow over the sea), not coast error. Not a unit test: needs a browser.
- Timings: trace of a 512 px raster 0.10-0.17 s; of a 1000 px PNG 0.8-1.2 s; Chrome render 1.1-1.6 s.
- OCR not measured on real maps: tesseract absent on this machine; the OCR path is covered by a fake only.
- led to: L-013, L-014, L-015


### T-20261114-3 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6 · 61/61 in 15 s
- New (11): render SVG byte-identical twice in every style, LF only, all layers present; bad style and bad extension refused; river width varies with flow; label bars pass and catch a forced overlap and an edge cut; OCR bar is None (skipped) without tesseract; shipped width table at least as wide as Georgia, Arial, Palatino and Times hmtx for letters, digits and punctuation; legend lists only drawn symbols; style list; serve binds 127.0.0.1, serves page and SVG, 404 elsewhere; sheet by styles and by seeds; PNG (1000 px wide) and PDF through headless Chrome; child map labels pass.
- Timings, `render` seed 7 (Ryzen 9 9900X, stdlib, 512 px raster): 16k cells 0.71-0.86 s, 65k cells 1.05-1.08 s; land raster is 95+ percent of it; placement under 0.02 s. PNG end to end at 65k 2.3 s (browser start included). SVG size 16k: topographic 401 KB, satellite 298 KB, ink-and-parchment 207 KB, atlas 197 KB, star-chart 123 KB, blueprint 110 KB; 65k: topographic 457 KB, ink-and-parchment 259 KB, atlas 252 KB.
- Labels seed 7 at 16k: 78-83 of 140 candidates placed per style, 0 overlaps, 0 edge cuts; the rest (mostly villages in dense clusters) dropped and listed.
- OCR bar not measured: tesseract absent on this machine.
- led to: L-010, L-011, L-012


### T-20261114-2 · 2026-11-14 · unittest (tests/) + generator sweep · Windows, Python 3.14.6 · 35/35 in 1.1 s
- New: Robinson against PROJ builtins.gie (+a=6400000) forward rows within 0.1 mm, inverse rows within 1e-9 deg; gen world folder contents, 16-bit heights.png, all 7 bars pass on a 1600-cell world and its child; same seed byte-identical (8 files), other seed differs; zoom alias; coarse child refused; check exits non-zero on a river made to run uphill.
- Timings, `gen world --seed 7` (Ryzen 9 9900X, stdlib): 16k cells 1.01 s (mesh 0.05, plates+noise 0.22, erosion 0.16, hydrology 0.01, climate 0.04, files+render 0.53); 65k cells 3.54 s (0.20 / 0.92 / 0.86 / 0.08 / 0.16 / 1.33). `gen region` 16k cells 0.77 s; full-window 131k-cell child of a 65k parent 5.5 s.
- Sweep: seeds 1-7 at 16k and 65k, 5 windows each (70 child maps): every bar passed; child coast max 0.841 parent spacings (mean 0.10-0.18), parent rivers in the child max 0.611. World bars on seed 7: 317 river cells / 0 failures, 22 lakes max 1 outlet, 8 files identical, sea-level temp by 10-deg band 24.9/21.3/15.7/10.6/5.6/2.2 C, windward 88 vs leeward 19 cm/yr.
- led to: L-003 (closed), L-004, L-005, L-006

### T-20261114-1 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6 · 24/24 in 0.5 s
- Round trips: GeoJSON to GPX to GeoJSON, GeoJSON to KML to GeoJSON (polygon with hole), GPX to KML to GPX, all within 1e-7 deg (coordinates are written with repr, so they come back exact).
- Shapefile (written by the test: CW outer, CCW hole, DBF NAME field, .prj) to GeoJSON: outer CCW, hole CW, names and CRS read.
- Geodesics: Geoscience Australia's Flinders Peak to Buninyong (GRS80) 54 972.271 m within 1 mm, azimuths within 0.01"; GeographicLib docs' Wellington to Salamanca (WGS84) 19 959 679.267 m within 1 mm, azimuths within 1e-6 deg. Near-antipodal pair falls back with the method stated.
- Area: WGS84 whole-earth 510 065 621.724 km2 within 0.01 km2; authalic radius 6 371 007.181 m.
- Projections, 10-degree grid to +-80 lat: forward then inverse worst error webmercator 1.8e-14, equirectangular 7.1e-15, mollweide 2.3e-13, laea 2.3e-12 (also centred 20E 50N, points within 2000 km of the antipode skipped), robinson 2.8e-14, equalearth 5.7e-14 deg (bar 1e-9).
- Equal-area: Mollweide, LAEA and Equal Earth keep the area ratio of a 10x10 deg equatorial cell to one at 55-65N within 1e-6 (2000 points per edge); Web Mercator misses by more than 50%, as it should.
- led to: L-001, L-002
