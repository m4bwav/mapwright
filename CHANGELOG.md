# Changelog: mapwright

Every change to [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`) and test runs in [TESTS.md](TESTS.md) (`T-`).

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:`, `files:`, and a sentence on what changed.

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
- `gen sector` places one world per occupied hex of a subsector (8x10) or sector (32x40), joins them by the relative neighbourhood graph plus the minimum spanning tree so the graph is always connected, marks routes beyond the jump range as long, and writes a T5 tab-delimited file; `--real` places twelve near stars from a small bundled table by parallax. `gen system` builds a star, planets kept at least 12 mutual Hill radii apart, moons inside the Hill sphere, and draws a schematic and a to-scale diagram. `gen planet` samples 3D noise on the sphere for six kinds of world, so the texture has no seam and no pole pinch. `gen deck` lays out ship or station decks with a spine corridor, doors, an airlock and lifts. `check` runs the space bars; `export` writes a planet as a sphere PNG plus a hand-off note, or a sector as a T5 file; `render --view scale` draws a system to scale.

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
