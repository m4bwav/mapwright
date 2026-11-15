# mapwright design note (Step C)

Written 2026-11-14. Settles the recipe, the render core, the generator core, the skill split and the scope edges from measurements in [../notes/prototype-measurements.md](../notes/prototype-measurements.md) and the references in [../../references/](../../references/). Mark's answers (name, public repo, AI style optional, free keys only) are in [../HANDOFF.md](../HANDOFF.md).

## 1. Script name

`mpw.py` (checked 2026-11-14 against every `scripts/*.py` under `Ai/`: `mw.py` is musicwright, `mpn.py` exists, `mpw.py` is free). One file, standard library only; optional extras are probed by `doctor` and never imported at top level.

## 2. The world recipe

One folder per map. Every file is open and readable without mapwright.

```
<name>.map/
  recipe.json        kind, seed, generator + version, projection (PROJ string or EPSG code we computed), extent, parent (path + window) for zooms, style name, label set, tool version
  features.geojson   coast, rivers, lakes, roads, borders, settlements, POIs (RFC 7946, WGS84 for real places; a local metre CRS declared in recipe.json for invented worlds)
  heights.png        16-bit greyscale PNG heightmap (stdlib zlib writer; GIS-openable with a .pgw world file beside it)
  heights.pgw        world file
  mesh.json          generated worlds only: cell points, heights, receivers (lets a zoom re-derive without re-running noise)
  names.json         place names + sound pattern seed, so names stay consistent across zooms
  sources.json       every fetched file: URL, licence, credit line, fetch date, rate used
  CREDITS.txt        human credit lines, written by fetch
  out/               renders (svg, png, pdf, html) and exports; disposable
```

Why these formats: GeoJSON and PNG+world file open in QGIS and every web map library and need nothing but the standard library to write. GeoPackage and COG are read when the extra is present (formats-and-tools.md) but never required for a recipe. The registry rule from sources-and-terms.md holds: we ship only codes we compute, not the EPSG database.

Redraw guarantee: `mpw.py render <dir>` from recipe.json alone gives byte-identical SVG (the prototype passed this bar across processes).

## 3. Render core: decided

| Candidate | Speed (65k map) | Install | Labels | Outputs from one path |
|---|---|---|---|---|
| Stdlib SVG writer | 0.78 s | 0 | full control (we place them; collision check in code) | SVG, then PNG/PDF via any browser, HTML page embeds the same SVG |
| Browser map library (MapLibre) via headless browser | not measured; browser start alone 0.6 s | CDN or vendored JS (~1 MB) | good for tiles, weak for hand-placed curved labels and parchment styles | stills + interactive page from one style |
| Headless QGIS | n/a | not installed (absent on this machine) | best | many, but a 1 GB+ dependency |

**Decision: stdlib SVG is the core.** PNG and PDF come from headless Chrome or Edge (`--screenshot`/`--print-to-pdf`, 0.6 s, probed by `doctor`; playwright with `channel="chrome"` when present). The interactive page (`serve`) wraps the same SVG with pan and zoom in plain JS on 127.0.0.1; for real-place slippy maps over tiles it loads Leaflet from cdnjs with a pinned version and the source's attribution. QGIS is an optional exporter when found, never needed. Reason: one code path serves every invented world and the style looks (ink, parchment, blueprint, star chart) that tile libraries do badly, with zero install.

Next render work (prototype weak spot): barycentric interpolation inside Delaunay triangles for hillshade, instead of nearest cell facets.

## 4. Generator core: decided

- **Mesh**: world-keyed jittered grid, Delaunay as its dual (quad split by in-circle test). Default 16k cells (about 1 s), `--cells` up to 65k stdlib (3.2 s) and higher with numpy (20-40x on noise). Points are keyed to world coordinates and spacing level, so any window at any density regenerates the same points.
- **Land**: Voronoi plates (domain-warped) for continents and mountain belts, then fBm with domain warp (realistic-land.md). The prototype's uplift (straight scarps) is replaced by distance-to-boundary with convergent/divergent/transform rules from realistic-land.md, plus a short stream-power erosion pass (implicit, O(n) per step on the receiver tree; 10-20 steps).
- **Water**: Priority-Flood with epsilon (0.03 s at 65k), steepest-descent single receiver (so no splits outside a marked delta), accumulation, rivers above a threshold, lakes as filled flats with exactly one outlet.
- **Climate and biomes**: latitude bands + prevailing wind + orographic rain shadow along the wind, then a Whittaker-style table (realistic-land.md). Settlements on river mouths, confluences and coasts; roads by least-cost paths between them.
- **Zoom**: child = IDW of the 3 nearest parent cells + world-keyed detail noise (prototype: max coast deviation 0.53 parent spacings, 100% within 1). New: child rivers take parent river paths as constraints (the parent river cell's descendant must carry the river) and add smaller ones by a lower threshold. Proof bar: parent rivers present in the child within 1 parent spacing.
- **Cities, dungeons, battle maps**: graph first then geometry (cities-and-dungeons.md): street growth on the region's road ends, BSP and cellular caves (r=50%, T=5, n=4) for dungeons, rooms keyed to the same seed scheme. Reachability is checked by BFS on every output.
- **Space**: galaxy = density-wave arms + disc/bulge sampling, sector hexes in the Traveller-style text format, hyperlanes as a relative-neighbourhood graph (connected by construction, checked), planets as noise on a sphere sampled through a cube map (no seam, no pole pinch), deck plans as dungeons on a hull outline. Real stars from HYG v4.4 (CC BY-SA, credit written). Built in 0.6.0 (2026-11-15): planets sample 3D noise straight onto the equirectangular grid (a cube map is not written yet); real stars are a twelve-star table of measured facts in scripts/data/near-stars.csv (not HYG rows, so no share-alike), HYG stays a later download script. Gaia is CC BY-NC: fetched for the user only, never bundled. Mark's UniverseGenerator (`Ai/labs/UniverseGenerator`) is read for its galaxy method and naming; mapwright does not depend on it.

## 5. Skills: start with one hub

One skill, `mapwright`, with the four verbs as sections and references loaded on demand. Package size budget favours one; the split is decided by evidence, not now:

- split into `mapwright-generate` (worlds, cities, dungeons, space) and the hub (read, find, write) only if the hub body passes about 400 lines, or the trigger evals show the hub missing generate prompts or stealing a neighbour's.
- Decoys in the eval suite: "map this repo" (evergreen-map), "choropleth of sales by state" (chartwright), "3D model of my town for printing" (polywright-capture), "pixel art tileset" (pixelwright), "level design for my dungeon crawler" (ludowright).

## 6. Scope edges

| Neighbour | Keeps | mapwright does | Hand-off |
|---|---|---|---|
| evergreen-map | codebase maps | never says "codemap"; descriptions say cartography, places, worlds | none |
| chartwright | statistical maps of data (choropleth, bubble, cartogram, hex/tile grid); it already lists them | geography under the data: boundaries, projection, base map, a recipe chartwright can draw on | `mpw.py export --geojson` for chartwright |
| polywright-capture / -print | real place to 3D scene and print tile (`pw.py place`) | 2D maps of the same place; invented terrain heightmaps | `mpw.py export --mesh` writes heights.png + extent for pw.py |
| fractalwright | fractal art, fBm stills, dimension measures | its own terrain noise (inside the generator; no runtime dependency) | can measure a coastline's dimension with fw.py |
| threewright | globes and 3D terrain in the browser | sphere textures and heightmaps | export cube map / equirect texture |
| pixelwright | sprites and tiles | tilemap layout from a generated map | export grid + tile ids |
| historywright-pack | places.geojson, period checks | renders those places on a period-styled map | reads places.geojson |
| comfyui-gen / artwright-judge | image models, blind ranking | `aistyle`: geometry held by a control image, labels set after in code | calls them |
| ludowright, engine plugins, studywright | design and engine import | heightmaps, tilemaps, UVTT tabletop export, minimap images | export formats |
| gis-mcp, qgis-mcp, fmg-mcp (outside tools) | full GIS / Azgaar FMG | stdlib, recipe-based, all three kinds, proof bars; points users to them when they need a full GIS or FMG's editor | documented in prior-art.md; not wrapped |

Built in 0.7.0 (2026-11-15): the hand-offs in this table are `export --to` targets, not separate flags. polywright gets `export DIR -o terrain.obj` (or `--to mesh -o FOLDER` for its asset layout) with a manifest in its contract's fields; engines get `--to unity|unreal|godot|roblox` heightmaps with an import sidecar; pixelwright and engine tile tools get `--to tiled` (.tmj with tile ids and a flat-colour tileset to repaint); tabletops get Universal VTT for dungeons, square battle maps and deck plans; print gets `--to print`. GeoJSON for chartwright needs no export: features.geojson is already in the recipe folder. Not built: a cube map for threewright, hex maps to Tiled, PDF/X.

## 7. Order for Step D (unchanged from the prompt) and first proofs

1. `doctor`, `explain`, `inspect`, `convert`, `measure` with the round-trip, distance and projection bars.
2. `gen world` / `gen region` / `zoom` lifted from prototypes/gen.py with the new uplift, erosion and river-constrained zoom.
3. `render`, `label`, `legend`, `style`, `serve`, `sheet`.
4. Then read/trace, find/fetch, the remaining generators, check, export, aistyle.

The repo m4bwav/mapwright (public, per Mark) is created with the first code; the plugin is converted with evergreen-convert at the same time so `harvest targets` finds harvest.json.
