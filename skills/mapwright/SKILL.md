---
name: mapwright
description: "Cartography for real, fantasy and sci-fi worlds: read, write, find and generate maps of places. Inspects and converts GeoJSON, GPX, KML, shapefiles, GeoPackage, MBTiles and heightmap PNGs, measures geodesic distance, bearing, area and scale, projects points (Web Mercator, Mollweide, Lambert equal-area, Robinson, Equal Earth), explains map terms, and grows invented worlds as recipe folders. Use whenever the user wants a map of a place or world: 'what is in this GPX', 'convert this KML to GeoJSON', 'how far is it from A to B', 'which projection for a world map', 'make a fantasy continent map', 'star map for my sci-fi setting'. Also 'refresh mapwright'. Not for code or repository maps (evergreen-map), charts of data on a map such as choropleths (chartwright) or 3D models of places (polywright)."
license: MIT
metadata:
  version: 0.1.0
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

## Read: what a map file holds

`MPW inspect <file> [--json]` reads GeoJSON, GPX, KML/KMZ, shapefiles (.shp with .dbf and .prj), dBASE, PNG (16-bit heightmaps and .pgw world files), GeoPackage and MBTiles. It prints feature counts by geometry type, the extent, property names and the CRS when the file states one. Report "CRS not stated" plainly; never guess it. A world file holds the centre of the top-left pixel, so the extent is half a pixel wider than the naive sum.

Reading a map picture (a scan, a screenshot, a fantasy map image) is a vision task: [references/reading-map-pictures.md](../../references/reading-map-pictures.md).

## Write: convert, measure, project

- `MPW convert <in> <out>` between GeoJSON, GPX and KML; reads shapefiles and KMZ. GPX holds points and lines only, so polygons are skipped with a count. Shapefile outer rings are clockwise and GeoJSON's counter-clockwise; the converter reverses them.
- `MPW measure distance LAT1 LON1 LAT2 LON2 [--ellipsoid WGS84|GRS80|clarke1866]` gives the geodesic distance and the initial and final bearing (Vincenty; geographiclib or a stated haversine fallback near antipodes). Note the argument order: latitude first.
- `MPW measure area <file>` gives polygon area on the ellipsoid (authalic latitude, holes subtracted). Never quote area measured in Web Mercator.
- `MPW measure scale 1:50000 [--map 2cm | --ground 3km]` converts map and ground lengths.
- `MPW project <name> LON LAT [--inverse] [--lon0 --lat0 --radius]` for webmercator, equirectangular, mollweide, laea, robinson, equalearth (`--list`). Picking a projection: [references/projections.md](../../references/projections.md) (section "Picking a projection").
- `MPW explain <term>` defines projections, symbols and methods (`explain list`). An unknown term is said to be unknown, with the reference file to search.

Design of the drawn map (hierarchy, colour, type, labels, relief): [references/cartography-design.md](../../references/cartography-design.md) and [references/relief-and-labels.md](../../references/relief-and-labels.md).

## Find: data for a real place

Not built in 0.1.0. Until `fetch` lands, name the open source and its licence from [references/sources-and-terms.md](../../references/sources-and-terms.md) (OpenStreetMap via Overpass, Natural Earth, public elevation) and write a credit line with every file used.

## Generate: invented worlds

- `MPW gen world --seed N [--cells 16000] --out DIR`: plates (convergent, divergent, transform uplift), fBm, stream-power erosion, Priority-Flood rivers and one-outlet lakes, latitude + wind + rain-shadow climate, Whittaker biomes. Writes the recipe folder (recipe.json, features.geojson, heights.png + .pgw, mesh.json, names.json stub, sources.json) and map.svg. About 1 s at 16k cells, 3.5 s at 65k.
- `MPW gen region --parent DIR --window x0,y0,x1,y1 --cells N --out DIR` (or `MPW zoom DIR --out DIR`, which picks the coast-richest quarter): a child map that keeps the parent's coast and rivers and adds smaller rivers. Window is in map km (0..1000, y south).
- `MPW check DIR`: the land proof bars (downhill rivers, no splits, one outlet per lake, byte-identical regeneration, child within 1 parent spacing, climate sanity). Exit 1 on any failure; run it before handing a map over.

Names, settlements and roads are not built yet; say so rather than drawing them by hand. Cities and dungeons: [references/cities-and-dungeons.md](../../references/cities-and-dungeons.md). AI image models for a styled look: [references/ai-image-models.md](../../references/ai-image-models.md). Games, film and print exports: [references/games-film-print.md](../../references/games-film-print.md).

## Hand-offs

- Code and repository maps: evergreen-map. mapwright never maps a codebase.
- Statistical maps of data (choropleth, bubble, cartogram): chartwright; mapwright supplies the boundaries as GeoJSON.
- A real place as a 3D scene or print: polywright-capture. Sprites and tiles: pixelwright. Game level design: ludowright.
- A full desktop GIS: QGIS. mapwright points to it and does not wrap it ([references/prior-art.md](../../references/prior-art.md)).

## Traps

- Lon/lat order: GeoJSON and KML are x = lon, y = lat; `measure distance` takes lat first; Leaflet takes [lat, lon]. Test with a point whose swap lands in the sea.
- Web Mercator stops at 85.0511 degrees and inflates area; never use it for area or density.
- XML with a DOCTYPE or ENTITY is refused (entity-expansion attacks).
- Format traps in detail: [references/formats-and-tools.md](../../references/formats-and-tools.md) (section "Traps checklist").

## Maintenance

Lessons go in [LEARNINGS.md](../../LEARNINGS.md), changes in [CHANGELOG.md](../../CHANGELOG.md), test runs in [TESTS.md](../../TESTS.md). The evergreen layer (evergreen.json, research refresh) is added by evergreen-convert in a later step.
