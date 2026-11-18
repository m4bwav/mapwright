# mapwright CLI: read, convert, measure, project

`MPW` means `python scripts/mpw.py` from the plugin root. Loaded on demand from skills/mapwright/SKILL.md.

## Read: what a map file holds

`MPW inspect <file> [--json]` reads GeoJSON, GPX, KML/KMZ, shapefiles (.shp with .dbf and .prj), dBASE, PNG (16-bit heightmaps and .pgw world files), GeoPackage and MBTiles. It prints feature counts by geometry type, the extent, property names and the CRS when the file states one. Report "CRS not stated" plainly; never guess it. A world file holds the centre of the top-left pixel, so the extent is half a pixel wider than the naive sum.

Since 0.27.0 `inspect` on a GeoJSON with OpenStreetMap boundary tags (flat or under `tags`) adds `boundaries`: count, disputed ones (`boundary=disputed`, `disputed=yes`, `disputed_by`), the `name:xx` languages present, legend rows and a credit line naming the source and which name tag was used. `find` lists sources only and does not read tags, and mapwright does not draw OSM boundaries itself, so carry these into whatever map draws them.

Reading a map picture (a scan, a screenshot, a fantasy map image): [references/reading-map-pictures.md](reading-map-pictures.md). The script measures; your vision finds; neither invents.

- `MPW read <image>`: size, colour class shares (water, vegetation, relief, light, ink, grey; plain RGB rules listed in the output), dominant colours, and text by tesseract when it is on PATH. Without tesseract every text field (names, legend, printed scale) is `"not sure"` with the reason. PNG needs nothing; other formats need Pillow.
- `MPW read <image> --gcp px,py,lon,lat` (3 or more; pixels from the top-left corner) fits an affine with residuals in metres and metres per pixel at the centre; `--world` writes the world file beside the image. Three points fit exactly and prove nothing: get a 4th. `--units m` for projected coordinates.
- `MPW read <image> --prompt` prints a checklist for your own vision (schema, "not sure" rules, a box for every item). Fill it, save it, then `MPW read <image> --answers a.json [--gcp ...]`: boxes outside the picture or missing are dropped, legend colours are checked against the swatch pixels, a scale bar is checked against the GCP fit (10 percent). Report only what comes back ok or unchecked, and say which.
- `MPW trace <image> [--class water | --colour #rrggbb --tol 40] [--mode polygons|lines] [--epsilon 1] [-o out.geojson]`: masks by colour, then polygons with holes (pixel-edge contours) or centre lines (thinning), simplified by Douglas-Peucker. Coordinates in pixels, or georeferenced with `--gcp` or `--world auto`. Labels and legend boxes over the sea show as holes; `--fill-holes N` fills holes under N px but also fills islands that small.

## Write: convert, measure, project

- `MPW convert <in> <out>` between GeoJSON, GPX and KML; reads shapefiles and KMZ. GPX holds points and lines only, so polygons are skipped with a count. Shapefile outer rings are clockwise and GeoJSON's counter-clockwise; the converter reverses them.
- `MPW measure distance LAT1 LON1 LAT2 LON2 [--ellipsoid WGS84|GRS80|clarke1866]` gives the geodesic distance and the initial and final bearing (Vincenty; geographiclib or a stated haversine fallback near antipodes). Note the argument order: latitude first.
- `MPW measure area <file>` gives polygon area on the ellipsoid (authalic latitude, holes subtracted). Never quote area measured in Web Mercator.
- `MPW measure compact <file> [--planar]` gives each polygon's Polsby-Popper score (4 pi A / P squared), convex-hull ratio (area over hull area), part count and contiguous groups (parts that share a vertex join). 1.0 is a circle or a convex shape. Lon/lat goes to a tangent plane at the polygon's mean point, fine up to a few hundred km; pass `--planar` for coordinates already in a projected CRS. Reock (smallest enclosing circle) is not offered. Standard formulas; the use for districting shapes comes from Volic, Making Democracy Count (2024).
- `MPW measure scale 1:50000 [--map 2cm | --ground 3km]` converts map and ground lengths.
- `MPW project <name> LON LAT [--inverse] [--lon0 --lat0 --radius]` for webmercator, equirectangular, mollweide, laea, robinson, equalearth (`--list`). Picking a projection: [references/projections.md](projections.md) (section "Picking a projection").
- `MPW explain <term>` defines projections, symbols and methods (`explain list`). An unknown term is said to be unknown, with the reference file to search.

Design of the drawn map (hierarchy, colour, type, labels, relief): [references/cartography-design.md](cartography-design.md) and [references/relief-and-labels.md](relief-and-labels.md).
