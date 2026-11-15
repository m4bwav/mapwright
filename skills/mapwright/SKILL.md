---
name: mapwright
description: "Cartography for real, fantasy and sci-fi worlds: read, write, find and generate maps of places. Inspects and converts GeoJSON, GPX, KML, shapefiles, GeoPackage, MBTiles and heightmap PNGs, measures geodesic distance, bearing, area and scale, projects points (Web Mercator, Mollweide, Lambert equal-area, Robinson, Equal Earth), explains map terms, and grows invented worlds as recipe folders. Use whenever the user wants a map of a place or world: 'what is in this GPX', 'convert this KML to GeoJSON', 'how far is it from A to B', 'which projection for a world map', 'make a fantasy continent map', 'star map for my sci-fi setting'. Also 'refresh mapwright'. Not for code or repository maps (evergreen-map), charts of data on a map such as choropleths (chartwright) or 3D models of places (polywright)."
license: MIT
metadata:
  version: 0.7.0
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

`MPW find QUERY` takes a place, a time or a subject ("Kyoto", "Paris 1850", "sea depth Hawaii", "stars near Sol") and lists candidate sources from a built-in catalogue, each with its licence and credit line. `--online` adds live lookups: Nominatim for the place and its bounding box, Wikimedia Commons files with each file's own licence and author, Library of Congress maps for a time, and a ready OpenTopography Copernicus GLO-30 request for the place's box. `MPW find --list` prints the catalogue. The terms behind it are in [references/sources-and-terms.md](../../references/sources-and-terms.md).

`MPW fetch URL -o FOLDER` downloads one file and writes `sources.json` (URL, licence, credit, date, rate, sha256) and `CREDITS.txt` beside it; fetch into the recipe folder. It sends `User-Agent: mapwright/<version>` and nothing personal, waits out each source's rate (Nominatim 1 request per second, even across runs), caches every response (MAPWRIGHT_CACHE, default ~/.cache/mapwright) so a repeat costs no request, and refuses:
- the never-scrape list (Google, Apple, Bing and Azure, Mapbox, MapTiler, HERE, TomTom, Esri, Stadia, Thunderforest, OSM tile servers, the OSM editing API), with the reason;
- whole-planet and global sets, and anything over `--max-mb` (200 by default). Raise the cap only for a file you meant to get; a planet file or global DEM waits for the owner;
- a host not in the catalogue unless you pass `--licence` and `--credit` from its terms page.

OpenTopography needs the user's own free key in `OPENTOPOGRAPHY_API_KEY`; it is added to the request and never written to the cache name, sources.json or CREDITS.txt. Never ask the user for a key; tell them where to get one.

Privacy guard: never send a home address, or any private address or location of a person or family, to a geocoder or any online lookup (`find --online` sends the query to Nominatim, Commons and the LoC). Use a town, a landmark or coordinates the user typed, or work from data already on disk.

## Generate: invented worlds

- `MPW gen world --seed N [--cells 16000] [--style S | --pattern P] --out DIR`: plates (convergent, divergent, transform uplift), fBm, stream-power erosion, Priority-Flood rivers and one-outlet lakes, latitude + wind + rain-shadow climate, Whittaker biomes, then settlements (scored on river mouths, confluences, coasts, lake shores, fertile flat land; 35 km apart; ranked city, town, village), roads (A* least-cost paths over a relative neighbourhood graph per landmass, reusing earlier roads) and names. Writes the recipe folder (recipe.json with the language, features.geojson, heights.png + .pgw, mesh.json, names.json, sources.json) and map.svg. About 1.4 s at 16k cells, 4.3 s at 65k.
- `MPW gen region --parent DIR --window x0,y0,x1,y1 --cells N --out DIR` (or `MPW zoom DIR --out DIR`, which picks the coast-richest quarter): a child map that keeps the parent's coast, rivers, settlements, roads and names, and adds smaller rivers, villages and tracks. Window is in map km (0..1000, y south). The child stores its parent's path relative to itself, so move the two folders together.
- `MPW names --sample N [--style S | --pattern 'C=..;V=..;F=..;S=CV CVF;N=2-3']`: print names from a sound pattern. `MPW names --list` shows the styles (soft, harsh, nordic, latinate, desert, isle). `MPW names DIR` prints a world's names; with `--style` or `--pattern` it renames the world (zoom its children again after).
- `MPW gen city --seed N [--parent WORLD --settlement ID] [--bands 6 --wall 4 | --no-walls] [--sea RAD --river RAD] --out DIR`: rings and gate roads grown from a market, blocks between them, lots cut so each fronts a street, buildings on the lots, a wall on one ring with gates only where the gate roads cross it, districts with names. With `--parent` it takes the settlement's name and language, and a coast or river when the world has one within 1.5 cell spacings. About 0.15 s.
- `MPW gen dungeon --seed N [--method bsp|cave] [--w 48 --h 36 --pps 70] --out DIR`: BSP rooms with corridors and about 12 percent extra loops, or cellular caves (largest cave kept); doors at one-wide room openings, a light per room; grid.json, map.png (whole pixels per square) and map.svg.
- `MPW gen battle --seed N [--grid square|hex] [--w 30 --h 20 --pps 100] --out DIR`: ruins with doors, rocks, trees, torches; pockets cut off from the main open ground become rock. Hex needs an even `--pps` and writes map.svg; `export --to png` draws the PNG.
- `MPW check DIR` on a city, dungeon or battle recipe runs the place bars: every street reached from the market, every block fronts a reached street, lots simple and inside their block, every built lot has frontage, streets cross the wall only at gates; every floor square, room and door reached, rooms never overlap, walls closed, map.png exactly squares x pps, the Universal VTT round trip; byte-identical regeneration; the label bars.
- `MPW gen sector --seed N [--size subsector|sector] [--density 0.5] [--jump 2] --out DIR`: one world per occupied hex (flat-topped columns, 0-based odd columns half a hex lower), routes as the relative neighbourhood graph joined with the minimum spanning tree (always connected), routes beyond `--jump` hexes marked long; sector.json, sector.tab (T5 tab-delimited, read back by header) and map.svg. The UWP-shaped codes are random filler, never a published setting's data. `--real [--radius-pc 6 --jump 2.5]` places the twelve near stars in scripts/data/near-stars.csv by parallax instead.
- `MPW gen system --seed N [--star M|K|G|F] [--planets N] --out DIR`: star mass, luminosity and radius, habitable zone (0.95 to 1.67 AU times sqrt L), snow line, planets kept at least 12 mutual Hill radii apart, moons inside the Hill sphere; each body names the `gen planet --kind` that fits it. map.svg is a schematic (not to scale), orbits.svg is to scale (`render --view scale`).
- `MPW gen planet --seed N --kind rocky|ice|ocean|gas|moon|locked [--width 1024] --out DIR`: equirectangular texture.png from 3D noise sampled on the sphere (no seam, no pole pinch; width 512 or more). Moon craters follow N(>D) ~ D^-2; a locked world has its substellar point at the texture's centre. About 4 s at 1024, 1 s at 512. `MPW export DIR -o planet.png` copies it with a hand-off note for threewright and polywright.
- `MPW gen deck --seed N [--hull ship|station] [--w 40 --h 21 --decks 2] --out DIR`: 1.5 m squares, spine corridor, rooms each with a door, an airlock with inner and outer doors, lifts on the same square on every deck; deck.json and map.svg.
- `MPW check DIR` on a sector, system, planet or deck: route graph connected, jump labels right, T5 file reads back, near stars at 1000/parallax within 1e-6 pc; orbits outside the star, neighbours 10+ mutual Hill radii apart, moons inside the Hill sphere, habitable zone; texture 2:1, seam (col 0 vs last within 2.5 x the 90th percentile adjacent-column difference), pole rows (std within 0.5 x the texture's), crater slope within 0.35; every room and floor square reached from the airlock across lifts, doors join two floors, the airlock opens to space, lifts line up; byte-identical regeneration; the label bars.
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

## Export: games, tabletop, 3D and print

`MPW export DIR -o FILE [--to TARGET]` writes the file, reads it back and prints its proof bars (exit 1 when one fails). The extension picks the target; a .png needs `--to`.

| Recipe | Command | Gives |
|---|---|---|
| world, region | `-o t.raw [--size 1025] [--flip]` | Unity RAW: 16 bit, little-endian, square, 2^n + 1 |
| world, region | `--to unreal -o t.png [--size 1009]` | 16-bit PNG at an Unreal landscape size |
| world, region | `-o t.r16`, or `--to godot -o t.png` | R16 for Terrain3D, or a 16-bit PNG |
| world, region | `--to roblox -o t.png [--size N] [--bits 16]` | heightmap (4096 px at most) and `t.colormap.png` in Roblox material colours |
| world, region | `-o t.obj [--size 257] [--exaggeration Z] [--base T] [--print-mm 100] [--flat-sea]`, or `--to mesh -o FOLDER` | terrain mesh and a polywright manifest; with a base it is one watertight solid |
| dungeon, square battle, deck | `-o map.tmj [--tile 32] [--encoding base64] [--csv]` | Tiled map, flat-colour tileset PNG, walls and doors as object layers, one tile layer per deck |
| dungeon, square battle, deck | `-o map.dd2vtt [--deck N] [--pps 50]` | Universal VTT (walls, doors as closed portals, lights, the PNG in base64); one file per deck |
| battle, dungeon | `--to png -o map.png` | the grid picture; the only raster export for a hex map |
| planet, sector | `-o p.png`, `-o s.tab` | sphere texture with `p.sphere.json`; T5 tab file |
| any | `--to print -o NAME[.pdf or .png] [--paper A4] [--landscape] [--dpi 300] [--bleed 3] [--fit cover]` | PDF and PNG at the paper size plus bleed, crop marks in the bleed |

- Heightmaps stretch the lowest to the highest height over the whole range. `t.import.json` beside the file gives metres per pixel, min and max height in metres and the numbers to type into the engine. A 1000 km world is past Unity's 100 km limit; the sidecar's `fit` block gives the even shrink.
- Not verified in the engines: which way Unity reads RAW rows (swapped north and south: `--flip`), the Roblox colour table and 8-bit default, Terrain3D's field names. Say so when handing the files over.
- Hex battle maps have no Universal VTT (the format has one square `pixels_per_grid`) and no Tiled export yet.
- The mesh is OBJ with x east, y north, z up, real metres unless `--print-mm`. Foundry reads the .dd2vtt through the Universal Battlemap Importer; its own scene JSON is not written.
- Print needs Chrome or Edge and stops with the reason when neither is found. Paper is A0 to A5, Letter, Legal, Tabloid or `WxH` in mm. Colour is RGB and the PDF sets MediaBox, BleedBox and TrimBox but is not PDF/X: say so before it goes to a press.

## Hand-offs

- Code and repository maps: evergreen-map. mapwright never maps a codebase.
- Statistical maps of data (choropleth, bubble, cartogram): chartwright; mapwright supplies the boundaries as GeoJSON.
- A real place as a 3D scene or print: polywright-capture. An invented terrain as a mesh or print tile: `export -o t.obj`, then polywright-print or polywright-finish. Sprites and tiles: pixelwright. Game level design: ludowright.
- A full desktop GIS: QGIS. mapwright points to it and does not wrap it ([references/prior-art.md](../../references/prior-art.md)).

## Traps

- Lon/lat order: GeoJSON and KML are x = lon, y = lat; `measure distance` takes lat first; Leaflet takes [lat, lon]. Test with a point whose swap lands in the sea.
- Web Mercator stops at 85.0511 degrees and inflates area; never use it for area or density.
- XML with a DOCTYPE or ENTITY is refused (entity-expansion attacks).
- Format traps in detail: [references/formats-and-tools.md](../../references/formats-and-tools.md) (section "Traps checklist").

## Maintenance

Lessons go in [LEARNINGS.md](../../LEARNINGS.md), changes in [CHANGELOG.md](../../CHANGELOG.md), test runs in [TESTS.md](../../TESTS.md). The evergreen layer (evergreen.json, research refresh) is added by evergreen-convert in a later step.
