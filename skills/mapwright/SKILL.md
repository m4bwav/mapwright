---
name: mapwright
description: "Cartography for real, fantasy and sci-fi worlds: read, write, find and generate maps of places. Inspects and converts GeoJSON, GPX, KML, shapefiles, GeoPackage, MBTiles and heightmap PNGs, measures geodesic distance, bearing, area and scale, projects points (Web Mercator, Mollweide, Lambert equal-area, Robinson, Equal Earth), explains map terms, and grows invented worlds as recipe folders. Use whenever the user wants a map of a place or world: 'what is in this GPX', 'convert this KML to GeoJSON', 'how far is it from A to B', 'which projection for a world map', 'make a fantasy continent map', 'star map for my sci-fi setting'. Also 'refresh mapwright'. Not for code or repository maps (evergreen-map), charts of data on a map such as choropleths (chartwright) or 3D models of places (polywright)."
license: MIT
metadata:
  version: 0.3.0
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

Reading a map picture (a scan, a screenshot, a fantasy map image): [references/reading-map-pictures.md](../../references/reading-map-pictures.md). The script measures; your vision finds; neither invents.

- `MPW read <image>`: size, colour class shares (water, vegetation, relief, light, ink, grey; plain RGB rules listed in the output), dominant colours, and text by tesseract when it is on PATH. Without tesseract every text field (names, legend, printed scale) is `"not sure"` with the reason. PNG needs nothing; other formats need Pillow.
- `MPW read <image> --gcp px,py,lon,lat` (3 or more; pixels from the top-left corner) fits an affine with residuals in metres and metres per pixel at the centre; `--world` writes the world file beside the image. Three points fit exactly and prove nothing: get a 4th. `--units m` for projected coordinates.
- `MPW read <image> --prompt` prints a checklist for your own vision (schema, "not sure" rules, a box for every item). Fill it, save it, then `MPW read <image> --answers a.json [--gcp ...]`: boxes outside the picture or missing are dropped, legend colours are checked against the swatch pixels, a scale bar is checked against the GCP fit (10 percent). Report only what comes back ok or unchecked, and say which.
- `MPW trace <image> [--class water | --colour #rrggbb --tol 40] [--mode polygons|lines] [--epsilon 1] [-o out.geojson]`: masks by colour, then polygons with holes (pixel-edge contours) or centre lines (thinning), simplified by Douglas-Peucker. Coordinates in pixels, or georeferenced with `--gcp` or `--world auto`. Labels and legend boxes over the sea show as holes; `--fill-holes N` fills holes under N px but also fills islands that small.

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

- `MPW gen world --seed N [--cells 16000] [--style S | --pattern P] --out DIR`: plates (convergent, divergent, transform uplift), fBm, stream-power erosion, Priority-Flood rivers and one-outlet lakes, latitude + wind + rain-shadow climate, Whittaker biomes, then settlements (scored on river mouths, confluences, coasts, lake shores, fertile flat land; 35 km apart; ranked city, town, village), roads (A* least-cost paths over a relative neighbourhood graph per landmass, reusing earlier roads) and names. Writes the recipe folder (recipe.json with the language, features.geojson, heights.png + .pgw, mesh.json, names.json, sources.json) and map.svg. About 1.4 s at 16k cells, 4.3 s at 65k.
- `MPW gen region --parent DIR --window x0,y0,x1,y1 --cells N --out DIR` (or `MPW zoom DIR --out DIR`, which picks the coast-richest quarter): a child map that keeps the parent's coast, rivers, settlements, roads and names, and adds smaller rivers, villages and tracks. Window is in map km (0..1000, y south). The child stores its parent's path relative to itself, so move the two folders together.
- `MPW names --sample N [--style S | --pattern 'C=..;V=..;F=..;S=CV CVF;N=2-3']`: print names from a sound pattern. `MPW names --list` shows the styles (soft, harsh, nordic, latinate, desert, isle). `MPW names DIR` prints a world's names; with `--style` or `--pattern` it renames the world (zoom its children again after).
- `MPW check DIR`: 13 land proof bars, then 3 label bars, (downhill rivers, no splits, one outlet per lake, byte-identical regeneration, child coast and rivers within 1 parent spacing, climate sanity, settlements on dry land, settlements of a landmass joined by roads, no road through water, names unique and present, names and features byte-identical, child keeps parent settlements and roads within 1 parent + 1 child spacing). Exit 1 on any failure; run it before handing a map over.

## Render: print maps and pages

- `MPW render DIR -o out.svg|png|pdf [--style S] [--font F.ttf] [--title T]`: the map from the recipe folder's files alone. Same folder and style give byte-identical SVG. PNG and PDF need Chrome or Edge (headless); without one, write .svg. About 0.7 s at 16k cells, 1.1 s at 65k (raster dominates); SVG 110-460 KB by style.
- `MPW label DIR [--json]`: placed and dropped labels, and the label bars. Labels never overlap and never touch the edge; a label with no free spot is dropped and listed, never squeezed in.
- `MPW legend DIR [--style S] [-o legend.svg]`: only the symbols on this map (biomes or height bands present, roads and settlement ranks present).
- `MPW style --list`, `MPW style NAME`: topographic, atlas, satellite, ink-and-parchment, blueprint, star-chart (palette and star field only, no catalogue stars yet).
- `MPW serve DIR [--port 8765]`: pan and zoom page on 127.0.0.1 only. Never bind it to 0.0.0.0.
- `MPW sheet DIR [--styles a,b] [--seeds 1,2] [--cols N] -o pick.png`: variations side by side for a pick; send the pick to artwright-judge, then Mark on an askwright page.
- `MPW check DIR` also runs the label bars (overlap, edge cut, OCR read-back). The OCR bar shows SKIP with the reason when tesseract is not installed; that is not a pass. `--no-labels` skips them.

There are no ferries yet: islands get their own road networks. Cities and dungeons: [references/cities-and-dungeons.md](../../references/cities-and-dungeons.md). AI image models for a styled look: [references/ai-image-models.md](../../references/ai-image-models.md). Games, film and print exports: [references/games-film-print.md](../../references/games-film-print.md).

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
