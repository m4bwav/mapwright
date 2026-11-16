---
name: mapwright
description: "Cartography for real, fantasy and sci-fi worlds: read, write, find and generate maps of places. Reads and converts GeoJSON, GPX, KML and shapefiles, finds OpenStreetMap or Overpass data with its licence, measures distance, area and scale, grows seeded worlds, regions, cities, dungeons, battle maps, star sectors, systems, planets and ship deck plans. Exports engine heightmaps (Unity, Unreal, Godot, Roblox), Tiled tilemaps, Universal VTT, meshes and PDFs. Use for any map of a place or world: 'what is in this GPX', 'KML to GeoJSON', 'find OpenStreetMap data for this area', 'make a fantasy continent map', 'generate a dungeon for my game', 'star sector or deck plan for my sci-fi setting', 'shortest path or chokepoints on my game map', 'export it as a Unity heightmap, Tiled map or dd2vtt'. Also 'refresh mapwright'. Not for code or repository maps (evergreen-map), data charts on a map such as choropleths (chartwright), 3D models of real places (polywright-capture) or pixel-art tiles (pixelwright)."
license: MIT
metadata:
  version: 0.10.2
---

# mapwright

Outcome: a map someone can open, trust and redraw. Files stay in open formats (GeoJSON, GPX, KML, PNG with a world file). Numbers (distance, area, scale, projected coordinates) come from `mpw.py`, never from memory.

`MPW` means `python scripts/mpw.py` from the repository root (run it, do not read it).

## Step 0: tools

Run `MPW doctor` once per machine. Python 3.9+ is all it needs. It reports Chrome or Edge (used later for PNG and PDF export) and the optional extras numpy, shapely, pyproj, GDAL and geographiclib. None is required.

## Step 1: which kind of world, which verb

Three kinds of world:

- **Real places**: Earth data in WGS84 lon/lat. Licences and credit lines matter; never scrape Google, Apple or MapTiler tiles ([references/sources-and-terms.md](../../references/sources-and-terms.md)).
- **Fantasy worlds**: invented land with believable coasts, rivers and mountains ([references/fantasy-maps.md](../../references/fantasy-maps.md), [references/realistic-land.md](../../references/realistic-land.md)).
- **Sci-fi**: galaxies, sectors, star charts, planets and deck plans ([references/scifi-maps.md](../../references/scifi-maps.md)).

Four verbs, below. Pick one, then read only the reference that step names.

Requests and where they go: a file to read or convert (Read, Write); a real place's data (Find); "make me a world, city, dungeon, battle map, star sector, star system, planet or deck plan" (Generate); "shortest path", "how long to travel", "chokepoints", "is this map fair" (Generate: `path`, `travel`, `check`); "as a Unity, Unreal, Godot or Roblox heightmap", "Tiled map", "Universal VTT / dd2vtt", "mesh", "print it" (Export).

## Read: what a map file holds

- `MPW inspect <file> [--json]`: feature counts by geometry type, extent, property names and the CRS when the file states one (GeoJSON, GPX, KML/KMZ, shapefiles, dBASE, PNG heightmaps with .pgw, GeoPackage, MBTiles). Report "CRS not stated" plainly; never guess it.
- `MPW read <image>` and `MPW trace <image>` for a map picture (scan, screenshot, fantasy map image). The script measures; your vision finds; neither invents.

Read [references/cli-read-write.md](../../references/cli-read-write.md) before reading a map picture (`read --gcp`, `--prompt`, `--answers`, `trace`) or when a world file's extent matters, and [references/reading-map-pictures.md](../../references/reading-map-pictures.md) for the method.

## Write: convert, measure, project

- `MPW convert <in> <out>` between GeoJSON, GPX and KML (reads shapefiles and KMZ).
- `MPW measure distance LAT1 LON1 LAT2 LON2` (latitude first), `MPW measure area <file>`, `MPW measure scale 1:50000 --map 2cm`.
- `MPW project <name> LON LAT [--inverse]`, `MPW explain <term>`.

Read [references/cli-read-write.md](../../references/cli-read-write.md) for options and per-command traps (GPX drops polygons, ring order, ellipsoids, projection list). Picking a projection: [references/projections.md](../../references/projections.md). Drawn-map design: [references/cartography-design.md](../../references/cartography-design.md) and [references/relief-and-labels.md](../../references/relief-and-labels.md).

## Find: data for a real place

- `MPW find QUERY [--online]` lists candidate sources (OpenStreetMap, Overpass, elevation, old maps, stars) with each one's licence and credit line; `MPW find --list` prints the catalogue.
- `MPW fetch URL -o FOLDER` downloads one file into the recipe folder with `sources.json` and `CREDITS.txt`, at each source's rate, cached, and refuses never-scrape hosts, planet-sized files and unknown hosts without `--licence` and `--credit`.

Read [references/cli-find.md](../../references/cli-find.md) before any `--online` lookup or `fetch` (refusal list, size cap, cache, OpenTopography key), and [references/sources-and-terms.md](../../references/sources-and-terms.md) for the terms.

## Generate: invented worlds

- `MPW gen world|region|city|dungeon|battle|sector|system|planet|deck --seed N --out DIR`, then `MPW check DIR` (exit 1 on any failed bar; run it before handing a map over).
- `MPW path DIR --from X,Y --to X,Y`, `MPW travel DIR --from X,Y`, `MPW check DIR --chokepoints [--fair]` for routes, travel times and fairness.

Read [references/cli-generate.md](../../references/cli-generate.md) before running any `gen`, `zoom`, `names`, `path`, `travel` or `check` option beyond the line above: it holds every kind's options, outputs, timings and proof bars. Background: [references/cities-and-dungeons.md](../../references/cities-and-dungeons.md), [references/scifi-maps.md](../../references/scifi-maps.md), [references/game-map-generation.md](../../references/game-map-generation.md), [references/pathfinding.md](../../references/pathfinding.md).

## Render: print maps and pages

- `MPW render DIR -o out.svg|png|pdf [--style S]` draws the map from the recipe folder alone (PNG and PDF need Chrome or Edge). `MPW style --list` names the styles.

Read [references/cli-render.md](../../references/cli-render.md) for `label`, `legend`, `serve` (127.0.0.1 only), `sheet` and the AI style pass (`aistyle`, denoise 0.45 or below, the model never draws text). AI image models: [references/ai-image-models.md](../../references/ai-image-models.md).

## Export: games, tabletop, 3D and print

- `MPW export DIR -o FILE [--to TARGET]` writes the file, reads it back and prints its proof bars (exit 1 when one fails). The extension picks the target: `.raw` Unity, `.r16`, `.obj`, `.tmj` Tiled, `.dd2vtt` Universal VTT; `--to unreal|godot|roblox|mesh|png|print`.

Read [references/cli-export.md](../../references/cli-export.md) before any export: the recipe-to-target table, sizes, sidecars, what is not verified in the engines (say so when handing files over) and print limits. Games, film and print: [references/games-film-print.md](../../references/games-film-print.md).

## Hand-offs

- Code and repository maps: evergreen-map. mapwright never maps a codebase.
- Statistical maps of data (choropleth, bubble, cartogram): chartwright; mapwright supplies the boundaries as GeoJSON.
- A real place as a 3D scene or print: polywright-capture. An invented terrain as a mesh or print tile: `export -o t.obj`, then polywright-print or polywright-finish. Sprites and tiles: pixelwright. Game level design: ludowright.
- A full desktop GIS: QGIS. mapwright points to it and does not wrap it ([references/prior-art.md](../../references/prior-art.md)).

## Traps

- Lon/lat order: GeoJSON and KML are x = lon, y = lat; `measure distance` takes lat first; Leaflet takes [lat, lon]. Test with a point whose swap lands in the sea.
- Web Mercator stops at 85.0511 degrees and inflates area; never use it for area or density.
- XML with a DOCTYPE or ENTITY is refused (entity-expansion attacks).
- Never scrape Google, Apple, Bing, Mapbox, MapTiler, OSM tile servers or other never-scrape hosts; `fetch` refuses them ([references/cli-find.md](../../references/cli-find.md)).
- Privacy: never send a home address or any person's private location to a geocoder or online lookup.
- Never ask the user for an API key; tell them where to get one.
- Format traps in detail: [references/formats-and-tools.md](../../references/formats-and-tools.md) (section "Traps checklist").

## Maintenance

Lessons go in [LEARNINGS.md](../../LEARNINGS.md), changes in [CHANGELOG.md](../../CHANGELOG.md), test runs in [TESTS.md](../../TESTS.md). Research and schedule: [RESEARCH.md](../../RESEARCH.md) and `evergreen.json` at the plugin root; protocol in [MAINTENANCE.md](../../MAINTENANCE.md). Refresh with evergreen-refresh when due.
