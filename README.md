# mapwright

![mapwright: a generated world painted as an atlas](.github/images/banner.jpg)

An agent plugin for maps of real places, fantasy worlds and science fiction settings. It reads, writes, finds and generates maps, and checks its own numbers against published values.

mapwright is a skill for AI coding agents plus one small script, `mpw.py`, that needs nothing but Python's standard library.

## What works in 0.10.0

- **Inspect** a map file: GeoJSON, GPX, KML and KMZ, shapefiles, dBASE, PNG heightmaps with world files, GeoPackage and MBTiles. Feature counts, extent, properties and the CRS when the file states one.
- **Convert** between GeoJSON, GPX and KML, and read shapefiles into GeoJSON. Ring order is fixed on the way (shapefiles clockwise, GeoJSON counter-clockwise).
- **Measure** geodesic distance and bearing on the WGS84, GRS80 or Clarke 1866 ellipsoid, polygon area on the ellipsoid, and map scale conversions.
- **Project** points forward and back: Web Mercator, equirectangular, Mollweide, Lambert azimuthal equal-area, Robinson and Equal Earth.
- **Explain** projections, symbols and methods in plain words.
- **Generate** invented worlds: plates, erosion, rivers, lakes, climate and biomes; settlements ranked city, town and village; roads by least-cost paths; place names from a sound pattern. Child maps (zoom) keep the parent's coast, rivers, settlements, roads and names. `check` runs 16 proof bars on a world.

- **Render** a recipe folder to SVG, PNG or PDF in six looks (topographic, atlas, satellite, ink-and-parchment, blueprint, star-chart) with labels that never overlap, a legend of what is on the map, a scale bar and a north arrow; serve it as a pan and zoom page on 127.0.0.1; set styles or seeds side by side on one sheet.

- **Read** a map picture (0.3.0): size, colour classes, dominant colours, text when tesseract is installed and "not sure" when it is not; a georeference only from control points you give, with residuals and a world file; a checklist for an agent's own vision whose answers the script then checks.
- **Trace** a map picture to GeoJSON: water or any colour to polygons with holes, or thin features to centre lines, simplified, in pixels or georeferenced. A rendered world traced back lands within 0.3 px (median) of its own coastline.

- **Find** maps and data for a place, a time or a subject (0.4.0): a catalogue of open sources with the licence and credit line for each, plus optional live lookups (Nominatim, Wikimedia Commons, Library of Congress, OpenTopography with your own key).
- **Fetch** one file politely: a plain mapwright User-Agent, each source's rate kept across runs, a disk cache, and `sources.json` plus `CREDITS.txt` written beside the data. The never-scrape list (Google, Bing, Mapbox, OSM tiles and the rest) and bulk sets over a size cap are refused.

- **Cities, dungeons and battle maps** (0.5.0): `gen city` (streets, blocks, lots, wall and gates, districts, optionally sited on a world's settlement), `gen dungeon` (BSP rooms or caves, doors, lights), `gen battle` (square or hex grid, pixels per square), checked by reachability, whole-pixel grid and byte-identical regeneration bars, and `export` to Universal VTT (.dd2vtt) for Foundry and other tabletops.
- **Dungeons** (0.9.0): `gen dungeon --method cyclic` builds a lock-and-key dungeon graph first (two paths from start to goal, nested cycles, one-way doors) and raises it to rooms and corridors; every dungeon gets a goal at its far end; cave parameters are flags; `check --range` measures a generator's expressive range over 500 seeds and draws the heatmap. `fetch` records the licence of each geoBoundaries file from the API answer instead of assuming CC BY 4.0.

- **Block dungeons and ports** (0.13.0): `gen dungeon --method blocks` builds exit-matched block grids, and settlements are flagged as ports only on open sea coast; since 0.14.0 only the best-sheltered quarter of them.
- **Strongholds, bases, traps and anchors** (0.38.0): `grow --stronghold STYLE` rolls a footprint shape and takes rooms and storeys from the style, with day and night shifts and break values on doors and windows (`--facade-only` for outside views). `lint` gains `traps` (separate trigger and effect areas, doors on lockdown rooms, a bypass on the owner route) and `base` (shift cover per floor, break values), and a lair now asks for a home hazard and a resident-only route. `gen hexcrawl --anchors-only --risk-rings` keys one anchor per feature and tiers hexes by distance from villages.
- **Caves, signals, growth and quarters** (0.37.0): `gen dungeon --method cave --cave-type` draws seven natural cave types, and the geography flags (rock, what lies above, water table, heat, humidity, built) tag passages with clearance, ceiling, climb surface, flooding, slick floors, collapse zones and a light overlay with a shadow band. `lint` gains a `signal` family (outposts on approach routes, a line-of-sight chain to the keep, fire load and secret exits). `grow` writes a room plan grown transition-first from one map edge, a trick every N-th transition, and a lair mode that caps empty areas. City districts carry the people who name the quarter and the shop kinds it holds.
- **Hexcrawl sandboxes** (0.36.0): `gen hexcrawl` grows a seeded fantasy wilderness hex map with four-digit column+row hex IDs, terrain features lettered once and listed A-Z, about a third of hexes keyed on purpose, a hazard and a top predator per terrain, and landmark sight radii, and writes a `sandbox.json` kit (overview, geography, rumor and encounter slots, keyed hexes) beside `map.svg`. `lint` checks a `sandbox.json`. The kit format follows Points of Light (Goodman Games); every word list is our own.
- **Hostile bases, doom tracks and open questions** (0.35.0): `lint` checks a hostile plan for warning cues on lethal rooms, baffle walls behind gates and a decoy beside the prize; a doom track as a closed path of linked rooms; omens per site kind; a way back from every one-way portal; and a 0-5 threat `cue` that should rise toward the goal. Locked doors, pits, hidden doors and the goal each get an open question.
- **Period lint** (0.15.0): `check --period 1700` lists every convention on the map that did not exist yet in that year. The ink-and-parchment style carries year 1600, so `check --style ink-and-parchment` runs the lint by itself (0.16.0).
- **Drainage and battle layout** (0.12.0): zoom windows with no sea drain through the edge where the parent's rivers leave, the rain-shadow bar skips arid windward sides, battle maps put the title and legend outside the grid, treasure always sits inside its room, and `legend` works on battle maps.
- **Paths, density and branches** (0.11.0): `path` on a cyclic dungeon fetches each key before its lock (`--ignore-locks` for the old search), `path --jps` runs jump point search on square grids, `export --nav` writes walkable rectangles and portals as JSON, `gen battle --density sparse|normal|dense` with a legend of what is on the map, and `gen dungeon --method cyclic --branches N` adds dead ends with treasure and secret doors.

- **Space** (0.6.0): `gen sector` (hex subsector or sector, worlds, connected jump routes, a T5 tab-delimited file; `--real` for twelve near stars placed by parallax), `gen system` (star, planets on stable orbits, moons, schematic and to-scale diagrams), `gen planet` (rocky, ice, ocean, gas giant, cratered moon or tidally locked sphere textures with no seam and no pole pinch), `gen deck` (ship or station deck plans, every room reachable from the airlock). `check` proves the route graph connected, star distances, orbit spacing, the seam and poles, and deck reachability; `export` writes a planet as a sphere PNG with a hand-off note for three.js and Blender.
- **Per-place seeds** (0.17.0): `gen sector --systems` writes every world's system; `gen system --sector-seed S --hex 0118` regenerates one alone, byte-identical, from a stable hash of seed and hex.
- **Region chunks** (0.18.0): `gen region --chunk COL,ROW [--chunk-km 250]` makes one chunk of the parent world with its own stable seed; reruns are byte-identical.
- **Agent-size navigation** (0.19.0): `export --nav --agent N` erodes the walkable squares for a body N squares wide before merging rectangles and portals.
- **Shape compactness** (0.26.0): `measure compact` gives Polsby-Popper, convex-hull ratio and contiguity per polygon, for districts, regions and generated provinces.
- **Map furniture and play aids** (0.27.0): settlement names with site words and a gloss each, `render --currents`, `--grid` and `--gazetteer`, a dungeon player copy (`export --to player`), sector hazard zones (`gen sector --hazards N`), and OSM boundary notes in `inspect`.
- **Book rules** (0.25.0): `sky` star charts from RA/Dec with sky period rules; world climate model 2 (ocean currents, mild west coasts, continentality, snowline by latitude, Koppen); orbits, temperatures, eccentricity and companion stars in `gen system`.
- **ControlNet style hold** (0.24.0): `aistyle --control canny` draws a hint from the map geometry so a stronger style (denoise up to 0.75) keeps the coast inside the bar.
- **Wide block halls** (0.23.0): `--corridor N` also works with `--method blocks`; halls and hub squares widen, agent 2 at corridor 2 reaches every room on 97 of 100 seeds.
- **Wide cyclic corridors** (0.22.0): `--corridor N` also works with `--method cyclic`; locks and keys hold across the whole gap.
- **Wide corridors** (0.21.0): `gen dungeon --corridor 2` (bsp, 1 to 3) carves corridors two squares wide with open gaps instead of one-square doors, so `path --agent 2` and `export --nav --agent 2` reach every room (100 of 100 seeds).
- **Agent-size paths** (0.20.0): `path --agent N` routes a body N squares wide on square dungeon and battle grids, with the same erosion.

- **Export** (0.7.0) to the tools that take a map further, each file read back and checked before it is reported:
  - engine heightmaps from a world or region: Unity RAW (16 bit, 2^n + 1), Unreal 16-bit PNG at landscape sizes, R16 or 16-bit PNG for Godot, a Roblox heightmap with a colormap of material colours, and a sidecar with metres per pixel, the height range and the import settings;
  - Tiled maps (.tmj) of dungeons, square battle maps and deck plans with a generated tileset, walls and doors as object layers and an optional CSV;
  - deck plans to Universal VTT and hex battle maps to PNG;
  - a terrain mesh (OBJ) with optional vertical exaggeration and a base that makes it a watertight print tile, plus a manifest in polywright's asset format;
  - print-ready PDF and PNG at A4, A3, Letter, Tabloid or a custom size, at a chosen DPI, with bleed and crop marks, through headless Chrome or Edge.

- **AI style pass** (0.8.0, optional): `aistyle` repaints a world or region map on your own ComfyUI server in four looks (painted atlas, ink and parchment, satellite, watercolour) and keeps the geography. The model gets the map without text; lakes, rivers, roads, symbols, labels, the legend, the scale bar and the north arrow are set in code on top. Each picture is measured against the map's own coast and gets a sidecar with the model, its licence class, the prompt, the seed and the numbers. Measured on 72 pictures: every one kept the coast at denoise 0.45 or below, none at 0.65. `--dry-run` works with no server.

- **Pathfinding** (0.10.0): `path` finds the cheapest route on dungeons, battle maps (square and hex), deck plans, worlds and regions and draws it on the map; `path --field` gives every cell its cost to the nearest goal and its next step, a flow field for many units; `travel` turns a world or region into walking hours by Tobler's hiking function; `check --chokepoints` lists the cells whose loss splits a map and the smallest cut from entrance to goal; `check --fair` compares starting points by their distance to resources and the ground each reaches first. Every A* cost equals plain Dijkstra on the test maps.

Labels on curves come next.

## Use

```
python scripts/mpw.py doctor
python scripts/mpw.py inspect hike.gpx
python scripts/mpw.py convert hike.gpx hike.geojson
python scripts/mpw.py measure distance -41.32 174.81 40.96 -5.50
python scripts/mpw.py project mollweide 100 45
python scripts/mpw.py explain web-mercator
python scripts/mpw.py gen world --seed 7 --style nordic --out isles.map
python scripts/mpw.py zoom isles.map --out isles-south.map
python scripts/mpw.py check isles-south.map
python scripts/mpw.py names --sample 10 --style desert
python scripts/mpw.py names --list
python scripts/mpw.py render isles.map -o isles.png --style ink-and-parchment
python scripts/mpw.py label isles.map
python scripts/mpw.py legend isles.map --style atlas
python scripts/mpw.py style --list
python scripts/mpw.py serve isles.map
python scripts/mpw.py sheet isles.map --styles atlas,blueprint,star-chart -o pick.png
python scripts/mpw.py export isles.map -o isles.raw --size 1025
python scripts/mpw.py export isles.map -o tile.obj --print-mm 100 --exaggeration 20
python scripts/mpw.py export crypt.map -o crypt.tmj --csv
python scripts/mpw.py export ship.map -o ship.dd2vtt
python scripts/mpw.py export isles.map --to print -o poster --paper A3 --bleed 3
python scripts/mpw.py aistyle isles.map --look watercolour --dry-run
python scripts/mpw.py gen dungeon --seed 4 --out crypt
python scripts/mpw.py path crypt --from 42,29 --to 24,34
python scripts/mpw.py check crypt --chokepoints --fair
python scripts/mpw.py aistyle isles.map --look painted-atlas --host http://127.0.0.1:8188
```

## Tests

`python -m unittest discover -s tests`. Distances match Geoscience Australia's Vincenty example and GeographicLib's documented values to a millimetre. The tests need no GPU and no network; `tests/aistyle_grid.py` is the harness that measured the style pass on a real server.

## Licence

MIT. See [LICENSE](LICENSE). Security reports: [SECURITY.md](SECURITY.md).
