# Changelog: mapwright

Every change to [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`) and test runs in [TESTS.md](TESTS.md) (`T-`).

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:`, `files:`, and a sentence on what changed.

### C-20261116-15 · 2026-11-16 · 0.22.0: wide corridors for cyclic dungeons
- because: HANDOFF backlog "corridor widening for cyclic", T-20261116-22, L-059
- files: scripts/mpw_places.py, scripts/mpw.py, tests, references/cli-generate.md, README.md
- `gen dungeon --method cyclic --corridor N` (1 to 3): edges carved N wide as open gaps; locks and one-way flags kept and applied to every gap square. Agent 2 reaches every room 100/100 seeds at corridor 2; agent 3 at corridor 3 90/100. Default byte-identical. Tests: 267 pass, 2 skip.

### C-20261116-14 · 2026-11-16 · 0.21.0: wide corridors for wide bodies
- because: HANDOFF backlog "nav/path door widening", T-20261116-21
- files: scripts/mpw_places.py, scripts/mpw.py, tests/test_path.py, references/cli-generate.md, README.md
- `gen dungeon --corridor N` (bsp, 1 to 3) carves N-wide corridors; above 1 the room openings stay open gaps rather than doors. Recorded in the recipe so `check` regenerates it. Default byte-identical. Tests: 266 pass, 2 skip.

### C-20261116-13 · 2026-11-16 · 0.20.0: agent-aware path
- because: HANDOFF backlog item "an agent-aware `path`", T-20261116-20
- files: scripts/mpw_path.py, scripts/mpw_export.py, scripts/mpw.py, tests/test_path.py, references/cli-generate.md, README.md
- `path --agent N` searches the same top-left anchored N x N erosion as `export --nav --agent N` (one shared function, mpw_path.erode); `--from`/`--to` name the body's top-left square; the JSON carries `agent`. Square dungeon and battle grids only; hex, decks and worlds are refused. `--agent 1` (default) is unchanged. Tests: 264 pass, 2 skip.

### C-20261116-12 · 2026-11-16 · 0.19.0: nav export agent-size erosion
- because: HANDOFF backlog item "nav export agent-size erosion", T-20261116-19
- files: scripts/mpw_export.py, scripts/mpw.py, tests/test_export.py, references/cli-export.md, README.md
- `export --nav --agent N` keeps only squares where an N x N body fits with its top-left square there, then merges rectangles and portals as before; the nav bars run on the eroded grid; JSON gains `agent`. `--agent 1` (default) is byte-identical; 0 is refused. Tests: 261 pass, 2 skip.

### C-20261116-11 · 2026-11-16 · 0.18.0: per-place seeds for region chunks
- because: book-build backlog row 4 (rest), T-20261116-18
- files: scripts/mpw_gen.py, scripts/mpw.py, tests/test_mpw.py, README.md
- `gen region --chunk COL,ROW [--chunk-km 250]` windows one chunk of the parent; its detail seed is `place_seed(world_seed, "region", "col,row@km")`, recorded under `place` so `check` regenerates it. Coast and rivers still come from the parent. Default outputs byte-identical. Tests: 260 pass, 2 skip.

### C-20261116-10 · 2026-11-16 · 0.17.0: per-place seeds for sector systems
- because: book-build backlog row 4 (SA ch. 26), T-20261116-17
- files: scripts/mpw_space.py, scripts/mpw.py, tests/test_space.py
- `gen sector --systems` writes systems/<hex>/ for each world, each from `place_seed(seed, "system", hex)` (blake2b, 8 bytes); `gen system --sector-seed S --hex H` makes the same system alone, byte-identical. Tests: 258 pass, 2 skip.

### C-20261116-9 · 2026-11-16 · 0.16.0: ink-and-parchment carries period 1600
- because: HANDOFF next item 1 (built-in styles with a period year), T-20261116-16
- files: scripts/mpw_render.py, tests/test_mpw.py, README.md
- The ink-and-parchment style now has `period=1600` (early-modern look), so `check --style ink-and-parchment` adds the period bar without `--period`; a Mollweide or Robinson recipe in that style now fails it. The modern styles carry no year. Tests: 255 pass, 2 skip.

### C-20261116-8 · 2026-11-16 · 0.15.0: check --period
- because: build backlog row 3 (period lint), T-20261116-15
- files: scripts/mpw_render.py, scripts/mpw.py, tests/, TESTS.md
- `check --period YEAR` (with `--period-kind map|chart|mappa` and `--uses`) fails every convention on the map younger than YEAR (bar scale 1275, contours 1791, Mercator 1569, Robinson 1963 and the rest of the book table); a style may carry a `period` year. Tests: 254 pass, 2 skip.

### C-20261116-7 · 2026-11-16 · 0.14.0: harbour ranking caps ports
- because: L-058 (port share 0.889 on 24 worlds), T-20261116-14
- files: scripts/mpw_gen.py, tests/, LEARNINGS.md, TESTS.md
- Open-coast settlements are port candidates ranked by harbour score (shelter, depth, river mouth, rank); the best ceil(settlements/4) become ports; bar 14 also fails over the cap. Share 0.889 -> 0.261.
- Tests: 252 pass, 2 skip.

### C-20261116-6 · 2026-11-16 · 0.13.0: block dungeons, ports on open coast
- because: build backlog rows 7 and 21 (L-052..L-057)
- files: scripts/mpw_places.py, scripts/mpw_gen.py, scripts/mpw_human.py, tests/, references/cli-generate.md, LEARNINGS.md, TESTS.md
- `gen dungeon --method blocks`: exit-matched 7x7-square blocks, block-count bar scaled to the grid, up to 32 restarts recorded as `blocks.rerolls`; two new `check` bars. bsp, cave and cyclic output unchanged.
- Ports: open sea flooded in from the map border (zoom windows inherit the parent's); a settlement is a port only when it touches open sea; new `check` bar. Other files byte-identical on seed 7.
- Tests: 249 pass, 2 skip.

### C-20261116-5 · 2026-11-16 · 0.12.0: landlocked drainage, rain-shadow margin, battle layout, treasure placement, battle legend
- because: L-009 closed (L-047, L-048); battle render defects from session 17 (L-044..L-046); wiki run found `legend` crashing on battle maps
- files: scripts/mpw.py, scripts/mpw_gen.py, scripts/mpw_places.py, tests/, evals/evals.json, LEARNINGS.md, TESTS.md
- Zoom windows with no sea seed Priority-Flood from border cells where the parent's flow leaves; bar 1 accepts rivers ending there. Worlds and windows with sea are byte-identical on seeds 1-8; all-land grandchildren change (they now have rivers).
- Bar 7 skips the rain-shadow judgement when windward rain is under 50 cm/yr (24-seed sweep, T-20261116-8).
- Battle maps: title in a band above the grid, legend in a band below; no square hidden. Note: since 0.11.0 old battle seeds need `--density sparse` to match.
- Cyclic `--branches` treasure always on a floor cell inside its room (old code: 49 of 120 outside).
- `legend` lists battle-map legends; city and dungeon recipes get a clean "no legend" message.
- Eval case trigger-projection added, 3/3. Tests: 241 pass, 2 skip.

### C-20261116-4 · 2026-11-16 · 0.11.0: lock-aware paths, jump point search, nav export, battle density and legend, dungeon branches
- because: backlog items from Step D and the Step E review; L-041; source pass 4
- files: scripts/mpw.py, scripts/mpw_path.py, scripts/mpw_export.py, scripts/mpw_places.py, scripts/mpw_space.py, scripts/mpw_render.py, tests/, references/, LEARNINGS.md
- `path` on a cyclic dungeon fetches each key before its lock, honours one-way doors and reports the pickups; `--ignore-locks` keeps the old search (30 seeds: every path exists, none crosses a lock early).
- `path --jps`: jump point search on square dungeon and battle grids, same cost as A* on 1,200 pairs with 37,932 expansions against 130,239; slower than A* in pure Python (L-043), and it refuses hex maps, decks, worlds and 4-way moves.
- `export --nav`: walkable squares merged into rectangles with a portal list, as JSON for an engine.
- `gen battle --density sparse|normal|dense` (default normal, 0.22 of cells hold a feature; sparse is the old map) and a legend that lists only what is on the map (L-050, L-051).
- `gen dungeon --method cyclic --branches N` (0 to 8): dead-end side rooms with treasure and secret doors, never keys; without the flag old seeds are byte-identical.
- Fixed: the system diagram's habitable-zone legend entry appears exactly when the zone is drawn (L-041 closed).
- References: source pass 4 cleared 36 marks and corrected 10 (spin-gravity limit 1 rpm, Dungeon Alchemist licence, TouchTerrain tile width, package sizes); note in ai-docs/notes/2026-11-16-source-pass-4.md.
- Description names OpenStreetMap and Overpass data with its licence and is back under 1,024 characters (1,007); L-042 closed: find trigger 1/3 before, 3/3 after in T-20261116-4 and 3/3 again on the shortened text (T-20261116-5).
- SKILL.md body trimmed from 24.5 KB to 8.7 KB; per-verb detail moved word for word to references/cli-read-write.md, cli-find.md, cli-generate.md, cli-render.md and cli-export.md, read on demand. evals/run.py is the kept eval runner (standard library).
- Tests: 233 pass, 2 skip. Evals 38/38 runs (T-20261116-4).

### C-20261116-3 · 2026-11-16 · Evals rerun, learnings consolidated, test runs archived
- The dd2vtt action case now needs a gen-battle recipe (seed 3, 20x16) that passes `mpw.py check`; a lone .dd2vtt fails it. Rerun: 13/14 (T-20261116-2), find-place undertriggers (L-042).
- LEARNINGS consolidated (41 to 17 active): merged L-022 into L-021, L-031 into L-010, L-033 into L-020; archived L-001..L-008, L-011, L-013..L-019, L-023, L-025, L-027, L-036, L-037, L-040 to LEARNINGS-ARCHIVE.md as enforced by tests or code; code names added to L-009, L-010, L-012, L-020.
- TESTS.md runs T-20261114-1 to T-20261115-5 moved to TESTS-ARCHIVE.md.
- because: T-20261116-2

### C-20261116-2 · 2026-11-16 · 0.10.3: VERSION constant, README bar count, Hill spacing note
- because: wiki run for 0.10.2 found mpw.py VERSION stuck at 0.10.0, README "(0.2.0, unreleased)" and 13 bars, CHANGELOG 0.6.0 Hill spacing vs the check bar's 10
- files: scripts/mpw.py, plugin.json, .claude-plugin/plugin.json, README.md, CHANGELOG.md
- Version strings agree; README and the 0.6.0 entry match what the code does.
### C-20261116-1 · 2026-11-16 · 0.10.2: Step F description triggers, eval suite in evergreen format
- because: Step F; T-20261116-1 (trigger-read-gpx 0/3 before the fix)
- files: skills/mapwright/SKILL.md, evals/evals.json, TESTS.md, evergreen.json, plugin.json, .claude-plugin/plugin.json, ai-docs/log.md
- Description names export (engine heightmaps, Tiled, Universal VTT), paths, travel and chokepoints, game map kinds and sci-fi sector, system, planet and deck, keeps the boundaries (evergreen-map, chartwright, polywright-capture, pixelwright), 1,024 chars or less. Step 1 lists which request goes to which verb. evals.json is now an `evals` list: 8 triggers, 4 decoys, 2 action cases with command evidence and baselines.
### C-20261115-9 · 2026-11-15 · 0.10.1: Step E example maps; render --title on grid maps; space determinism bar ignores extra files
- because: Step E (one keepable map per kind), L-039, L-040, L-041
- files: scripts/mpw.py, scripts/mpw_places.py, scripts/mpw_space.py, tests/test_places.py, tests/test_space.py, LEARNINGS.md, plugin.json, .claude-plugin/plugin.json, ask/mapwright-step-e-1, ai-docs/notes/2026-11-15-step-e-maps.md
- `render --title` now names city, dungeon and battle maps (space maps warn that it is unused). The sector/system/planet/deck byte-identical bar compares only the files the gen writes, so a render saved in the folder no longer fails it.
### C-20261115-8 · 2026-11-15 · Converted to an evergreen unit
because: the plugin had companions but no schedule or research log.
files: evergreen.json, RESEARCH.md, MAINTENANCE.md, skills/mapwright/SKILL.md
Added evergreen.json (pointer mode, tier moderate, next due 2026-12-14), RESEARCH.md summarising references/, MAINTENANCE.md, and pointed the skill's Maintenance section at them.

### C-20261115-7 · 2026-11-15 · 0.10.0: pathfinding commands (path, path --field, travel, check --chokepoints and --fair)
- because: user request (references/pathfinding.md section 11), T-20261115-7, L-036, L-037, L-038
- files: scripts/mpw_path.py (new), scripts/mpw.py, tests/test_path.py (new), skills/mapwright/SKILL.md, README.md, TESTS.md, LEARNINGS.md, references/pathfinding.md, plugin.json, .claude-plugin/plugin.json
- `path DIR --from --to` finds the cheapest route on dungeon, battle (square and hex), deck, world and region recipes and writes path.json, path.geojson and path.svg. `path --field` writes a Dijkstra field with a flow step per cell. `travel` gives walking, off-path or riding hours by Tobler's hiking function on worlds and regions. `check --chokepoints` lists cut cells, what each cuts off and the minimum entrance-to-goal cut; `check --fair` gives per-start distances to resources and first-reach areas.
- Rulings:
  - Square grids move 8 ways by default (diagonal sqrt 2), never past a wall corner and never diagonally into or out of a door; `--moves 4` for plain 4-way.
  - Cyclic dungeons keep their one-way doors (L-034) and treat locks as open; path.json says how many locks it opened.
  - World and region paths reuse the road router's step cost unchanged, which charges terrain and bridges on the cell entered, so world costs are directed and A to B can differ from B to A.
  - A deck lift step costs 3 m; deck squares are 1.5 m.
  - `path --jps` and `export --nav` are not built in this release.
### C-20261115-6 · 2026-11-15 · 0.9.0: dungeons (goal, cave flags, cyclic, expressive range) and geoBoundaries licences
- because: user request (book build backlog rows 1, 2, 5, 8, 9, 10), T-20261115-6, L-033, L-034, L-035
- files: scripts/mpw_places.py, scripts/mpw.py, scripts/mpw_find.py, tests/test_places.py, tests/test_find.py, tests/fixtures/dungeon-070-bsp (new), tests/fixtures/dungeon-070-cave (new), skills/mapwright/SKILL.md, README.md, references/sources-and-terms.md, ai-docs/notes/book-build-backlog.md, plugin.json, .claude-plugin/plugin.json
- Every new dungeon has an entrance and a goal, both drawn on map.svg and written to grid.json and features.geojson. bsp and cave place the goal at the square farthest from the entrance. `check` adds bars for that, for an entrance-to-goal path at least the map width, and for no isolated wall squares. Cave rules are flags (`--fill --passes --birth --survival --radius --border`) kept in the recipe. `gen dungeon --method cyclic` builds a lock-and-key graph on a grid of 7-square cells and raises it to the same grid.json BSP writes, so render, export and check work on it; check adds cycle rank, adjacency, key before lock, the lock as a gate on the squares, and a return path. `check --range METHOD` writes range.json and range.svg. `fetch` reads `boundaryLicense` from a geoBoundaries API answer and records it for the answer and its download links.
- Rulings:
  - Recipes without `params.goal` (0.7.0 and older) are rebuilt the old way, so they still regenerate byte for byte.
  - Minimum path is the map width, as the notes suggest; a bsp or cave map under it is re-rolled from a new stream (at most 16), a cyclic graph that cannot be placed from stream 2000 + k (at most 64); the count is stored in grid.json.
  - Cyclic pattern: path a short and locked at the goal, the key at the far end of b next to the goal, a one-way valve from the goal down to the key. b is enterable from the start (the book's "not enterable there" is not built). Nested cycles are two-cell bumps that keep the edge they sit on, half of them with a one-way middle door (hidden shortcut).
  - The cave default stays 0.45, 5 passes, 5/4 (TESTS.md table).
  - Expressive range metrics are mapwright's own; dead-end share counts the parts joined by one bridge, loop share counts corridor squares on a loop.
  - Version 0.9.0, skipping 0.8.0, which another branch takes.
### C-20261115-5 · 2026-11-15 · 0.8.0: aistyle, an optional AI style pass that keeps the coast
- because: user request (Step D.10), T-20261115-5, L-028, L-029, L-030, L-031, L-032
- files: scripts/mpw_aistyle.py (new), scripts/data/aistyle-zimage-turbo.json (new), scripts/mpw.py, scripts/mpw_render.py, tests/test_aistyle.py (new), tests/aistyle_grid.py (new), skills/mapwright/SKILL.md, README.md, TESTS.md, LEARNINGS.md, references/ai-image-models.md, ai-docs/notes/2026-11-15-aistyle-measurements.md (new), plugin.json, .claude-plugin/plugin.json
- `aistyle RECIPE --look painted-atlas|ink-and-parchment|satellite|watercolour` renders a world or region without roads, symbols or text, sends that picture to a ComfyUI server as the init image of an img2img pass (standard library urllib: upload, queue, poll, download), then sets lakes, rivers, roads, symbols, labels, legend, scale bar and north arrow in code on top of the result and writes PNG, SVG or PDF. The workflow is a JSON template in scripts/data with the model files as slots (Z-Image Turbo, Apache 2.0, by default; `--workflow`, `--model`, `--clip`, `--vae` swap it). The server comes from `--host` or `MAPWRIGHT_COMFYUI`; there is no default address and none is stored. `--dry-run` writes the control PNG and the workflow JSON and contacts nothing. `doctor` reports whether a server answers and holds the model files.
- Every pass is measured against the recipe's own geometry: land IoU by a colour table trained on the picture away from the coast (bar 0.92), code-set rivers on painted land (0.98), settlements on painted land (0.94). Lakes and river lines the model kept are reported without a bar, because both are redrawn in code (L-028). Default and ceiling denoise 0.45, from 72 measured pictures. A sidecar `NAME.aistyle.json` records model, licence class, look, prompt, seed, denoise typed and as run, steps, workflow hash, tool version and the numbers. `check` adds one optional bar per sidecar in the recipe folder (`--no-aistyle` skips them).
- `mpw_render.render_parts` returns the map's SVG lines in named parts (head, ground, water, coast, over); `render_svg` joins them and is byte-identical to before. Label boxes are read in viewBox units, so a composite drawn at another pixel size is measured correctly.

### C-20261115-4 · 2026-11-15 · 0.7.0: export to engines, Tiled, tabletop, mesh and print
- because: user request (Step D.9), T-20261115-4, L-024, L-025, L-026, L-027
- files: scripts/mpw_export.py (new), scripts/mpw.py, scripts/mpw_places.py, tests/test_export.py (new), skills/mapwright/SKILL.md, README.md, ai-docs/plans/design.md, plugin.json, .claude-plugin/plugin.json
- `export` takes `--to` (or reads the target from the extension) and now writes: engine heightmaps from a world or region (`unity` RAW, `unreal` 16-bit PNG, `godot` R16 or 16-bit PNG, `roblox` heightmap plus a colormap) with an `.import.json` sidecar; Tiled maps (`.tmj`) of dungeons, square battle maps and deck plans; deck plans as Universal VTT, one file per deck; hex battle maps as PNG; a terrain mesh (`.obj`) with a polywright manifest; and print-ready PDF and PNG at a paper size with bleed and crop marks. Every writer reads its own file back and prints proof bars. The Universal VTT bars gain one: colours alpha first (AARRGGBB), every portal closed, no wall under a door (checked against the importer facts in references/cities-and-dungeons.md; the 0.5.0 dungeon and battle export already met all three). `doctor` lists the export targets and says when print is skipped for want of a browser; `explain` knows heightmap, bleed, crop-marks, tmj and uvtt.
- Rulings:
  - Heightmaps stretch the lowest to the highest height over the full range; the sidecar carries the scale.
  - Unity, Unreal and the mesh take vertex samples from edge to edge; Godot and Roblox take pixel centres, the identity at the recipe's raster size.
  - A region that is not square still gives a square Unity or Unreal heightmap, with different metres per pixel east and north (the engines set width and length apart); Roblox and Godot keep the shape.
  - Default size is the smallest the engine takes at or above the recipe raster: 513 for Unity and 1009 for Unreal from a 512 px raster.
  - Unity rows are written north first; `--flip` writes south first. Which one Unity expects is not verified.
  - Godot gets `.r16` by preference: Terrain3D reads PNG as 8 bit. A 16-bit PNG is still offered.
  - Roblox is 8 bit unless `--bits 16`; sea and lake beds are Mud and water is added with the Sea Level tool; the colour table is from the reference, not checked in Studio.
  - Tiled gids are 1 wall, 2 floor, 3 door, 4 tree, 5 lift, 6 airlock, 0 empty; the decks of a ship are tile layers of one map; `--csv` writes Tiled's own CSV shape (local ids, -1 empty); `--encoding base64` is zlib.
  - Deck plans to Universal VTT: space counts as wall, a lift is floor, the airlock's outer door is a portal, at least 50 px per square.
  - The mesh is OBJ with x east, y north, z up, in real metres; `--print-mm` gives millimetres and a 2 mm base; the bottom is a fan from the centre; the manifest uses polywright's contract fields with status `model`, and `-o FOLDER` writes polywright's asset layout.
  - Print: the page is the paper plus the bleed; crop marks sit inside the bleed on the trim lines and stop 1 mm short of the corner; `contain` with a 10 mm margin is the default and `cover` crops; PNG pixels are round(mm / 25.4 x dpi); a name with no extension writes both files.
  - Hex battle maps get no Universal VTT (L-026) and no Tiled export yet.

### C-20261115-3 · 2026-11-15 · 0.6.0: gen sector, gen system, gen planet, gen deck
- because: user request (Step D.8), T-20261115-3, L-021, L-022, L-023
- files: scripts/mpw_space.py (new), scripts/data/near-stars.csv (new), scripts/mpw.py, tests/test_space.py (new), skills/mapwright/SKILL.md, README.md, plugin.json, .claude-plugin/plugin.json
- `gen sector` places one world per occupied hex of a subsector (8x10) or sector (32x40), joins them by the relative neighbourhood graph plus the minimum spanning tree so the graph is always connected, marks routes beyond the jump range as long, and writes a T5 tab-delimited file; `--real` places twelve near stars from a small bundled table by parallax. `gen system` builds a star, planets placed 12 mutual Hill radii apart (the check bar accepts 10 or more), moons inside the Hill sphere, and draws a schematic and a to-scale diagram. `gen planet` samples 3D noise on the sphere for six kinds of world, so the texture has no seam and no pole pinch. `gen deck` lays out ship or station decks with a spine corridor, doors, an airlock and lifts. `check` runs the space bars; `export` writes a planet as a sphere PNG plus a hand-off note, or a sector as a T5 file; `render --view scale` draws a system to scale.

### C-20261115-2 · 2026-11-15 · 0.5.0: gen city, gen dungeon, gen battle, export to Universal VTT
- because: user request (Step D.7), T-20261115-2, L-018, L-019, L-020
- files: scripts/mpw_places.py (new), scripts/mpw.py, tests/test_places.py (new), skills/mapwright/SKILL.md, README.md, plugin.json, .claude-plugin/plugin.json
- `gen city` grows rings and gate roads from a market (the Watabou ward plan reimplemented, not copied), cuts blocks into lots that each keep street frontage, puts buildings on them, a wall with gates and named districts, and can sit on a parent world's settlement (name, language, coast and river). `gen dungeon` makes BSP rooms with loops or cellular caves with doors and lights; `gen battle` makes square or hex battle maps at a whole number of pixels per square. `check` runs place bars (reachability of streets, blocks, rooms, doors and floor; lots and walls; whole-pixel grid; Universal VTT round trip; byte-identical regeneration; label bars). `export` writes a Universal VTT file. `render` draws place recipes in ink-and-parchment or blueprint.

### C-20261115-1 · 2026-11-15 · 0.4.0: find and fetch
- because: user request (Step D.6), T-20261115-1, L-016, L-017
- files: scripts/mpw_find.py (new), scripts/mpw.py, tests/test_find.py (new), skills/mapwright/SKILL.md, README.md, plugin.json, .claude-plugin/plugin.json
- `find` matches a place, time or subject against a 25-source catalogue built from references/sources-and-terms.md, each with licence, credit and rate; `--online` adds Nominatim, Wikimedia Commons (per-file licence and author), Library of Congress and a built OpenTopography request. `fetch` downloads one file with a generic `mapwright/<version>` User-Agent, a per-source rate limiter kept on disk across runs, a disk cache, a 200 MB cap, refusals for the never-scrape list and whole-planet or global sets, and writes sources.json and CREDITS.txt beside the file. API keys come from the environment and never reach the cache name or the credit files. SKILL.md documents the private-address guard.

### C-20261114-5 · 2026-11-14 · 0.3.0: read and trace
- because: user request (Step D.5), T-20261114-4, L-013, L-014, L-015
- files: scripts/mpw_read.py (new), scripts/mpw.py, tests/test_read.py (new), tests/roundtrip_trace.py (new), skills/mapwright/SKILL.md, README.md, plugin.json, .claude-plugin/plugin.json
- `read` reports a picture's size, colour class shares and dominant colours, runs tesseract when present (else every text field is "not sure" with the reason), fits an affine georeference from 3 or more `--gcp` points with residuals and metres per pixel, and writes a world file. `read --prompt` gives an agent a checklist for its own vision; `read --answers` checks those answers (boxes, swatch colours, scale bar against the GCP fit). `trace` turns a colour class or colour into polygons with holes or centre lines, simplified by Douglas-Peucker, in pixels or georeferenced. PNG is decoded with zlib; Pillow is optional for other formats. `doctor` probes Pillow and tesseract. Plugin version files caught up from 0.1.0 to 0.3.0.

### C-20261114-4 · 2026-11-14 · 0.2.0 (unreleased): render, label, legend, style, serve, sheet; label bars in check
- because: user request (Step D.4), T-20261114-3, L-010, L-011, L-012
- files: scripts/mpw_render.py (new), scripts/mpw.py, tests/test_mpw.py, skills/mapwright/SKILL.md, README.md
- `render DIR -o out.svg|png|pdf` draws a recipe folder from its files alone: land raster per style with Horn hillshade, depth-tinted sea, lakes, rivers widened by flow, roads by rank, settlements, labels, a legend of only the symbols drawn, a scale bar and a north arrow. PNG and PDF come from headless Chrome or Edge, with a clear error when neither is found. `label` places point, area and river labels greedily in priority order with collision boxes against labels, settlement dots and the map furniture, and reports what it dropped. Text width comes from a shipped wide table (checked to be at least as wide as Georgia, Arial, Palatino and Times) or a TTF's hmtx with `--font`. `style` lists six looks (topographic, atlas, satellite, ink-and-parchment, blueprint, star-chart; star-chart is a palette plus star field). `serve` wraps the SVG in a pan and zoom page bound to 127.0.0.1 only. `sheet` sets several styles or seeds side by side. `check` adds three label bars: no overlaps, none cut by the edge, OCR read-back (skipped with a reason when tesseract is absent, never a pass).

### C-20261114-3 · 2026-11-14 · 0.2.0 (unreleased): names, settlements, roads; relative parent path; 13 bars
- because: user request (Step D.3), L-007, L-008, L-009
- files: scripts/mpw_names.py (new), scripts/mpw_human.py (new), scripts/mpw_gen.py, scripts/mpw.py, tests/test_mpw.py, skills/mapwright/SKILL.md, README.md
- `names` samples a sound pattern (six styles or a custom C/V/F/S/N pattern), lists styles and renames a world. `gen world` stores the language in recipe.json and names.json and places scored, spaced and ranked settlements, A* roads over a relative neighbourhood graph, and names for settlements, rivers (one per main stem), lakes, seas and oceans, mountain ranges and landmasses. Children keep parent settlements, roads and names, lift parent settlement and road cells out of new sea or lake cells, and add villages and tracks. The child recipe stores its parent path relative to itself; absolute paths still read. `check` gains bars 8 to 13.

### C-20261114-2 · 2026-11-14 · 0.2.0 (unreleased): gen world, gen region / zoom, check; Robinson as PROJ
- because: user request (Step D.2 of ai-docs/plans/design.md), T-20261114-2, L-003, L-004, L-005, L-006
- files: scripts/mpw_gen.py (new), scripts/mpw.py, tests/test_mpw.py, skills/mapwright/SKILL.md
- `gen world` builds the recipe folder and map.svg from plates with distance-to-boundary uplift, domain-warped fBm, 15 steps of implicit stream-power erosion, Priority-Flood with epsilon, single receivers, one-outlet lakes, climate and biomes. `gen region` and `zoom` make a child map by IDW of 3 parent cells plus detail noise, with the parent's coast as a sign constraint and parent rivers burnt in. `check` runs seven numbered proof bars. Robinson now uses PROJ's cubic-spline coefficients (float32, as PROJ stores them) and matches PROJ's builtins.gie rows to 0.1 mm.

### C-20261114-1 · 2026-11-14 · 0.1.0 scaffold: mpw.py doctor, explain, inspect, convert, measure, project
- because: user request (Step D.1 of ai-docs/plans/design.md), T-20261114-1
- files: plugin.json, .claude-plugin/, skills/mapwright/SKILL.md, scripts/mpw.py, tests/, evals/evals.json, AGENTS.md, CLAUDE.md, README.md
- First hub skill draft and a standard-library CLI: file inspection for seven formats, GeoJSON/GPX/KML conversion with shapefile reading, Vincenty geodesics with fallbacks, ellipsoid area, scale, and six projections with inverses.
