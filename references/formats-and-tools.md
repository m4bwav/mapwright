# Geodata formats and tools for mapwright

What each common map format is, whether Python's standard library alone can read and write it, how much work that takes, and which optional tool takes over when it cannot. Then the spatial operations a map tool needs and the traps in each.

Written 2026-11-14 from the specs and docs listed at the end. Claims marked "checked 2026-11-14" were verified against the fetched source; other citations come from the specs as recalled. Items marked "(unverified)" need checking against the source before code depends on them.

"Stdlib" here means `json`, `csv`, `struct`, `zlib`, `gzip`, `sqlite3`, `zipfile`, `xml.etree.ElementTree`, `math`, `base64` and `io`. No PNG or TIFF codec ships with Python, so raster work needs either a hand-written decoder (`zlib` plus `struct` is enough for PNG) or Pillow.

## Summary table

| Format | Stdlib read | Stdlib write | Effort (stdlib) | Optional tool |
|---|---|---|---|---|
| GeoJSON (RFC 7946) | yes (`json`) | yes | trivial | none needed; shapely for geometry ops |
| CSV with coordinates | yes (`csv`) | yes | trivial | GDAL CSV driver for WKT columns |
| WKT | yes (small parser) | yes | low | shapely `wkt` |
| WKB / EWKB | yes (`struct`) | yes | low | shapely `wkb` |
| GPX 1.1 | yes (`xml.etree`) | yes | low | gpxpy, GDAL GPX driver |
| KML 2.2 | yes (`xml.etree`) | yes | low to medium (styles, MultiGeometry) | GDAL LIBKML driver, simplekml |
| KMZ | yes (`zipfile` + KML) | yes | low | GDAL |
| TopoJSON | yes (`json` + arc decoding) | yes, but building shared arcs is hard | read low, write high | topojson (Python), Node `topojson-server` |
| Shapefile (.shp/.shx/.dbf/.prj) | yes (`struct`) | yes | medium | pyshp (pure Python), GDAL/ogr2ogr |
| GeoPackage | yes (`sqlite3` + GPKG header + WKB) | yes | medium | GDAL GPKG driver, fiona, geopandas |
| MBTiles | yes (`sqlite3`) | yes | low | mb-util, GDAL MBTiles driver |
| PMTiles v3 | yes (`struct` + varints + `gzip`) | yes | medium | `pmtiles` Python package and Go CLI |
| Mapbox Vector Tile (protobuf) | yes (hand-rolled protobuf) | yes | medium to high | mapbox-vector-tile, GDAL MVT driver, tippecanoe |
| XYZ / TMS tile math | yes (`math`) | n/a | trivial | mercantile, morecantile |
| OSM XML | yes (`xml.etree.iterparse`) | yes | low (medium to build ways and relations into polygons) | osmium (pyosmium), GDAL OSM driver |
| OSM PBF | yes, in principle (protobuf + `zlib`) | possible | high | pyosmium, osmium-tool, GDAL OSM driver |
| FlatGeobuf | yes (flatbuffers by hand with `struct`) | yes | high | `flatgeobuf` package, GDAL |
| GeoParquet | no in practice (Parquet needs Thrift, Snappy/Zstd) | no | very high | pyarrow, geopandas, GDAL 3.5+ ([GDAL Parquet driver](https://gdal.org/en/stable/drivers/vector/parquet.html), checked 2026-11-14), DuckDB spatial |
| GeoTIFF / COG | partial (uncompressed or Deflate strips and tiles via `struct` + `zlib`) | yes for uncompressed or Deflate | medium to high | rasterio, GDAL, tifffile |
| PNG + world file (.pgw) | yes (PNG via `zlib`, world file is 6 lines of text) | yes | low to medium | Pillow, GDAL |
| Esri ASCII grid (.asc) | yes | yes | trivial | GDAL AAIGrid driver |
| JPEG 2000 | no (wavelet codec) | no | not practical | GDAL with OpenJPEG, glymur, Pillow with OpenJPEG |
| SRTM .hgt | yes (`struct`, big-endian int16) | yes | trivial | GDAL SRTMHGT driver |
| Terrain-RGB / Terrarium PNG tiles | yes (PNG decode + formula) | yes | low to medium | Pillow, rio-rgbify |
| Routes (GPX rte/trk, GeoJSON LineString, OSRM/Valhalla JSON) | yes | yes | low | OSRM, Valhalla, GraphHopper servers |

Effort levels: trivial is under 50 lines; low is about 50 to 200; medium is about 200 to 600 with binary layout work; high means a hand-written binary codec (protobuf, flatbuffers, TIFF compression) of 600+ lines or open-ended edge cases. These are estimates, not measurements.

## Vector formats

### GeoJSON (RFC 7946)

JSON objects of type Feature, FeatureCollection or a geometry type (Point, LineString, Polygon, Multi*, GeometryCollection) ([RFC 7946 sec. 3](https://www.rfc-editor.org/rfc/rfc7946#section-3)). Rules worth enforcing:

- Coordinates are longitude, latitude, optional elevation, in that order ([RFC 7946 sec. 3.1.1](https://www.rfc-editor.org/rfc/rfc7946#section-3.1.1)).
- The CRS is always WGS 84 (OGC CRS84); the old `crs` member was removed ([RFC 7946 sec. 4](https://www.rfc-editor.org/rfc/rfc7946#section-4)).
- Polygon exterior rings are counterclockwise and holes clockwise (right-hand rule), but parsers must not reject the wrong winding ([RFC 7946 sec. 3.1.6](https://www.rfc-editor.org/rfc/rfc7946#section-3.1.6)).
- Rings are closed: first and last position equal, at least four positions ([RFC 7946 sec. 3.1.6](https://www.rfc-editor.org/rfc/rfc7946#section-3.1.6)).
- Geometries that cross the antimeridian should be cut into a MultiPolygon or MultiLineString ([RFC 7946 sec. 3.1.9](https://www.rfc-editor.org/rfc/rfc7946#section-3.1.9)).
- A `bbox` crossing the antimeridian has west greater than east ([RFC 7946 sec. 5.2](https://www.rfc-editor.org/rfc/rfc7946#section-5.2)).
- The spec suggests about six decimal places is enough precision (about 10 cm) ([RFC 7946 sec. 11.2](https://www.rfc-editor.org/rfc/rfc7946#section-11.2)).

Stdlib: `json` reads and writes it. Large files need streaming; `json` has no streaming parser, so a newline-delimited GeoJSON (GeoJSONSeq, [RFC 8142](https://www.rfc-editor.org/rfc/rfc8142)) path is the stdlib way to handle big data.

### CSV with coordinates

No spec beyond [RFC 4180](https://www.rfc-editor.org/rfc/rfc4180). Coordinates arrive as `lat`/`lon` columns (names vary: `latitude`, `lng`, `x`, `y`) or as a WKT column. GDAL's CSV driver guesses geometry from `X_POSSIBLE_NAMES`/`Y_POSSIBLE_NAMES` and `GEOM_POSSIBLE_NAMES` open options ([GDAL CSV driver](https://gdal.org/en/stable/drivers/vector/csv.html)). Stdlib `csv` covers it; the work is column detection and a sanity check that values fall in -90..90 and -180..180 to catch swapped columns.

### WKT and WKB

Defined in OGC Simple Features Access part 1 ([OGC 06-103r4](https://www.ogc.org/standard/sfa/)). WKT is text (`POLYGON ((x y, ...))`); WKB is a byte-order flag, a uint32 geometry type and then doubles. Type codes: 1 Point, 2 LineString, 3 Polygon, 4-6 Multi*, 7 GeometryCollection; Z, M and ZM add 1000, 2000, 3000 in ISO WKB. PostGIS EWKB instead sets high bits (0x80000000 Z, 0x40000000 M, 0x20000000 SRID) ([PostGIS ST_AsEWKB](https://postgis.net/docs/ST_AsEWKB.html)). Both are easy with `struct`. WKT axis order follows the CRS in theory; in practice almost all software writes x=lon, y=lat.

### Shapefile

Esri's 1998 white paper defines the `.shp` (geometry), `.shx` (index) and `.dbf` (dBASE attributes) trio ([ESRI Shapefile Technical Description](https://www.esri.com/content/dam/esrisites/sitecore-archive/Files/Pdfs/library/whitepapers/pdfs/shapefile.pdf)). Header is 100 bytes with mixed endianness: file code and length big-endian, version and shape type little-endian. Shape types include 1 Point, 3 PolyLine, 5 Polygon, 8 MultiPoint, plus Z (11, 13, 15, 18) and M variants. Traps:

- Polygon rings are clockwise for outer rings and counterclockwise for holes, the opposite of GeoJSON (same white paper, "Polygon" section).
- Polygons store rings without saying which hole belongs to which shell; the reader must assign holes by containment.
- The `.prj` holds an ESRI-flavoured WKT CRS, not EPSG codes; without PROJ the stdlib can only recognise common cases by name.
- DBF field names are capped at 10 characters, files at 2 GB, and the encoding is given by an optional `.cpg` file ([GDAL Shapefile driver](https://gdal.org/en/stable/drivers/vector/shapefile.html)).

Stdlib: fully doable with `struct`; pyshp is a pure-Python reference implementation to compare against ([pyshp](https://github.com/GeospatialPython/pyshp)).

### GeoPackage

An OGC standard SQLite database ([OGC GeoPackage 1.4](https://www.geopackage.org/spec/)). Required tables `gpkg_spatial_ref_sys` and `gpkg_contents`; vector tables register in `gpkg_geometry_columns`. Each geometry blob is a GeoPackageBinary header followed by standard WKB: magic `0x4750` ("GP"), version byte (0 = version 1), flags byte (bit 5 extended type, bit 4 empty, bits 3-1 envelope code 0-4 giving 0/32/48/48/64 bytes for none/XY/XYZ/XYM/XYZM, bit 0 byte order of srs_id and envelope, 1 = little endian), int32 srs_id, then the envelope doubles. The B flag does not govern the WKB, which has its own byte-order byte; WKB axis order is always x, y ([GeoPackage 1.4 spec, "GeoPackageBinary"](https://www.geopackage.org/spec/#gpb_format), checked 2026-11-14). Raster tiles live in tile pyramid tables with `gpkg_tile_matrix_set` and `gpkg_tile_matrix`.

Stdlib: `sqlite3` plus a header parser plus WKB. Writing a valid file means creating the required tables and setting `application_id` to `0x47504B47` ("GPKG") via PRAGMA, and `user_version` to the spec version as an integer (10300 for 1.3.0, so 10400 for 1.4.0) ([spec Req. 2](https://www.geopackage.org/spec/#_file_format), checked 2026-11-14). R-tree spatial indexes use SQLite's rtree module and triggers; the module is usually compiled into Python's sqlite3 but not guaranteed (unverified per platform). GDAL's `ogrinfo`/`ogr2ogr` is the validator to test against.

### KML and KMZ

OGC KML 2.2 ([OGC 07-147r2](https://www.ogc.org/standard/kml/)); KML 2.3 is OGC 12-007r2, approved 2015-05-18, published 2015-08-04, built on XML Schema 1.1 ([OGC 12-007r2](https://docs.ogc.org/is/12-007r2/12-007r2.html), checked 2026-11-14; its namespace URI was not confirmed). Write 2.2 for compatibility. XML in namespace `http://www.opengis.net/kml/2.2`. Coordinates are `lon,lat[,alt]` tuples separated by whitespace. KMZ is a zip whose main file is conventionally `doc.kml`, the first `.kml` at the root ([Google KMZ docs](https://developers.google.com/kml/documentation/kmzarchives)). Stdlib `xml.etree` plus `zipfile` handle both. The hard parts are styles (`Style`, `StyleMap`, shared styles by URL), `gx:` extensions such as `gx:Track`, and `NetworkLink` to remote files. Never parse untrusted XML without care: `xml.etree` is exposed to entity-expansion attacks ([Python XML vulnerabilities](https://docs.python.org/3/library/xml.html#xml-vulnerabilities)); defusedxml is the optional fix.

### GPX

GPX 1.1 schema ([topografix.com/GPX/1/1](https://www.topografix.com/GPX/1/1/)). Elements: `wpt` (waypoints), `rte`/`rtept` (planned routes), `trk`/`trkseg`/`trkpt` (recorded tracks). Points carry `lat` and `lon` as attributes, with optional `ele` and `time` children. Coordinates are WGS 84 decimal degrees by schema. Stdlib `xml.etree.iterparse` is enough even for long tracks. Extensions (heart rate, Garmin TrackPointExtension) sit in `<extensions>` with other namespaces.

### TopoJSON

A JSON extension of GeoJSON that stores shared boundaries once as arcs ([TopoJSON spec](https://github.com/topojson/topojson-specification)). Quantized files delta-encode arc positions and scale them with `transform.scale` and `transform.translate`. Arc index `~i` (negative, ones' complement) means arc `i` reversed. Reading with stdlib is low effort. Writing a real topology (finding shared arcs, quantizing) is the hard part; the reference implementation is Node `topojson-server` ([topojson-server](https://github.com/topojson/topojson-server)).

### FlatGeobuf

A binary file: 8-byte magic `fgb` plus version, a FlatBuffers header, an optional packed Hilbert R-tree index, then size-prefixed FlatBuffers features ([FlatGeobuf spec](https://flatgeobuf.org/) and [schema](https://github.com/flatgeobuf/flatgeobuf/tree/master/src/fbs)). Stdlib can decode FlatBuffers with `struct` (vtables and offsets), but it is fiddly. The index allows HTTP range-request bbox queries. Optional: the `flatgeobuf` Python package or GDAL.

### GeoParquet

Apache Parquet with geometry columns (WKB, or native GeoArrow encodings since 1.1) and a `geo` metadata key in the file footer ([GeoParquet 1.1 spec](https://geoparquet.org/releases/v1.1.0/)). Parquet itself needs Thrift-compact metadata, column encodings (RLE, dictionary) and usually Snappy or Zstd compression ([Apache Parquet format](https://parquet.apache.org/docs/file-format/)); Python's stdlib has neither codec. Treat as optional: pyarrow, geopandas `read_parquet`, DuckDB with the spatial extension, or GDAL's Parquet driver ([GDAL Parquet driver](https://gdal.org/en/stable/drivers/vector/parquet.html)).

### OSM XML and PBF

OSM XML holds `node` (id, lat, lon, tags), `way` (ordered node refs) and `relation` (members with roles) ([OSM XML wiki](https://wiki.openstreetmap.org/wiki/OSM_XML)). Stdlib `iterparse` reads it; building geometry means joining ways to nodes, and multipolygons from relations means stitching outer and inner ways into rings ([Multipolygon relation](https://wiki.openstreetmap.org/wiki/Relation:multipolygon)). Area-ness is decided by tags, not geometry (a closed way tagged `highway` is a line unless `area=yes`) ([OSM wiki "Area"](https://wiki.openstreetmap.org/wiki/Area)).

OSM PBF is a sequence of length-prefixed `BlobHeader` and `Blob` protobuf messages, blobs usually zlib-compressed, containing `PrimitiveBlock`s with string tables, delta-coded dense nodes and a granularity in nanodegrees ([PBF Format wiki](https://wiki.openstreetmap.org/wiki/PBF_Format)). Stdlib can do it with a hand-written protobuf varint decoder plus `zlib`, but planet-scale files need speed that pyosmium gives ([pyosmium](https://osmcode.org/pyosmium/)). Data from the Overpass API arrives as XML or JSON, both stdlib-readable ([Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)). OSM data is ODbL and needs attribution ([OSM copyright](https://www.openstreetmap.org/copyright)).

## Raster formats

### GeoTIFF and Cloud Optimized GeoTIFF

TIFF 6.0 ([Adobe TIFF 6.0](https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf)) plus GeoTIFF tags: ModelPixelScale (33550), ModelTiepoint (33922), ModelTransformation (34264) and GeoKeyDirectory (34735) ([OGC GeoTIFF 1.1](https://docs.ogc.org/is/19-008r4/19-008r4.html)). BigTIFF uses 64-bit offsets and magic 43. Stdlib can parse IFDs with `struct` and decode uncompressed or Deflate (`zlib`) data, including the horizontal-differencing predictor. LZW is about 100 lines more. JPEG, WebP, LERC and Zstd compression are out of reach without libraries.

A COG is a tiled GeoTIFF with overviews and the IFDs placed first so readers can range-request just what they need ([OGC COG 1.0](https://docs.ogc.org/is/21-026/21-026.html)). GDAL's COG driver writes them ([GDAL COG driver](https://gdal.org/en/stable/drivers/raster/cog.html)). Optional route: rasterio or GDAL for anything beyond simple Deflate files.

### PNG plus world file

PNG is chunks with CRC32, IHDR, zlib-compressed IDAT with a per-row filter byte ([PNG spec, W3C 3rd ed.](https://www.w3.org/TR/png-3/)). Stdlib `zlib` plus `struct` decode and encode it in about 150 lines, including the five filters; interlaced (Adam7) and palette PNGs add work. A world file (`.pgw`, `.pngw`, `.wld`) is six lines: x pixel size, two rotation terms, negative y pixel size, and the x, y of the centre of the top-left pixel ([Esri world files](https://pro.arcgis.com/en/pro-app/latest/help/data/imagery/world-files-for-raster-datasets.htm)). The CRS is not in the file; it comes from an `.aux.xml` or `.prj` sidecar or must be stated. Trap: the world file refers to the pixel centre, GeoTIFF tiepoints often to the pixel corner (PixelIsArea vs PixelIsPoint) ([GeoTIFF RasterPixelIsArea](https://docs.ogc.org/is/19-008r4/19-008r4.html)).

### Esri ASCII grid

Header lines `ncols`, `nrows`, `xllcorner`/`xllcenter`, `yllcorner`/`yllcenter`, `cellsize`, optional `NODATA_value`, then rows from north to south ([GDAL AAIGrid driver](https://gdal.org/en/stable/drivers/raster/aaigrid.html)). Trivial with stdlib.

### JPEG 2000

Wavelet codec (ISO/IEC 15444-1) with GeoJP2 or GMLJP2 boxes for georeferencing ([GDAL JP2OpenJPEG driver](https://gdal.org/en/stable/drivers/raster/jp2openjpeg.html)). Sentinel-2 ships in it. Not practical to decode with stdlib; use GDAL with OpenJPEG or glymur.

## Elevation

### SRTM .hgt

Raw big-endian signed 16-bit grid, no header. 1 arc-second tiles are 3601x3601, 3 arc-second tiles 1201x1201; the filename (`N37W122.hgt`) names the south-west corner; edges overlap with neighbours; void value -32768 ([GDAL SRTMHGT driver](https://gdal.org/en/stable/drivers/raster/srtmhgt.html), [USGS SRTM](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1)). Heights are metres above the EGM96 geoid, not the ellipsoid (unverified for every SRTM release). Stdlib: `struct.unpack('>...h')` or `array` with byteswap. Copernicus DEM GLO-30 is the common newer source and ships as COG ([Copernicus DEM](https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model)).

### DEM in general

"DEM" is a role, not a format: it ships as GeoTIFF, ASCII grid, .hgt, USGS DEM, or tile pyramids. Hillshade, slope and aspect are simple 3x3 kernels that stdlib `math` can compute; `gdaldem` does it natively ([gdaldem](https://gdal.org/en/stable/programs/gdaldem.html)). Cell size in degrees must be scaled by cos(latitude) before computing slope.

### Terrain-RGB and Terrarium tiles

Elevation packed into PNG colour channels on XYZ tiles.

- Mapbox Terrain-RGB: `height = -10000 + (R*65536 + G*256 + B) * 0.1` metres ([Mapbox Terrain-RGB docs](https://docs.mapbox.com/data/tilesets/reference/mapbox-terrain-rgb-v1/)).
- Terrarium (AWS Terrain Tiles): `height = (R*256 + G + B/256) - 32768` metres ([Tilezen joerd formats](https://github.com/tilezen/joerd/blob/master/docs/formats.md)).

Stdlib PNG decoding plus the formula covers both. Writing them is the inverse. Lossy compression (JPEG, WebP lossy) breaks the encoding, so keep PNG.

## Tiles

### XYZ and TMS tile math

Web Mercator (EPSG:3857) tile pyramids: zoom z has 2^z by 2^z tiles of usually 256 px. XYZ (slippy map) counts y from the top; TMS counts from the bottom, so `y_tms = 2^z - 1 - y_xyz` ([OSM slippy map tilenames](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames), [OSGeo TMS spec](https://wiki.osgeo.org/wiki/Tile_Map_Service_Specification)). Mercator clips latitude at about ±85.0511 degrees. Lon/lat to tile is a few lines of `math`. Tile servers have usage rules: the OSM tile servers forbid heavy use and bulk download and need a real User-Agent ([OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/)).

### MBTiles

SQLite with a `metadata` (name, value) table and a `tiles` table (`zoom_level`, `tile_column`, `tile_row`, `tile_data`); rows use TMS y order, `tile_row = 2^zoom - 1 - y_xyz`. Metadata MUST include `name` and `format`, plus `json` when format is `pbf`; `bounds`, `center`, `minzoom`, `maxzoom` are SHOULD. Format `pbf` means gzip-compressed MVT by definition ([MBTiles 1.3 spec](https://github.com/mapbox/mbtiles-spec/blob/master/1.3/spec.md), checked 2026-11-14). Stdlib `sqlite3` plus `gzip` read and write it.

### PMTiles

A single-file archive meant for HTTP range requests: a 127-byte header, a root directory, optional leaf directories, metadata JSON and tile data; header plus compressed root directory must fit in the first 16,384 bytes. Tiles are addressed by a TileID that is a cumulative position on Hilbert curves from zoom 0. Directory entries are little-endian varints in columns: TileIDs delta-coded, run lengths and lengths as-is, offsets stored as offset+1 or 0 when contiguous with the previous entry. Internal compression is one of none, gzip, brotli or zstd (0x01-0x04; 0x00 unknown) and covers root, leaf directories and metadata ([PMTiles v3 spec](https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md), checked 2026-11-14). Stdlib: `struct`, a varint reader and `gzip` cover gzip or uncompressed archives; brotli or zstd archives need extra packages (zstd is in the stdlib only from Python 3.14, `compression.zstd`). The reference `pmtiles` Python package is small and pure Python (unverified current version).

### Mapbox Vector Tiles

Protocol Buffers message per tile: layers with features, keys/values string tables, and geometry as a command stream (MoveTo, LineTo, ClosePath) of zigzag-encoded, delta-coded integers in a tile-local grid, `extent` default 4096 ([MVT spec 2.1](https://github.com/mapbox/vector-tile-spec/tree/master/2.1)). Y grows down. Exterior rings are clockwise in tile coordinates (because y is flipped), which is counterclockwise on the map ([spec 4.3.4.4](https://github.com/mapbox/vector-tile-spec/tree/master/2.1#4344-polygon-geometry-type)). Stdlib can do it with a hand-written protobuf reader and writer (varints, length-delimited fields, packed repeated uint32); about 300 lines each way. Producing a tile set well (simplification per zoom, clipping with buffer, feature dropping) is tippecanoe's job ([tippecanoe](https://github.com/felt/tippecanoe)).

## Routes

A route is a LineString plus metadata. Interchange: GPX `rte` for planned routes and `trk` for recorded ones; GeoJSON LineString; encoded polylines (Google's algorithm, precision 5; OSRM and Valhalla often use precision 6) ([Google polyline algorithm](https://developers.google.com/maps/documentation/utilities/polylinealgorithm), [OSRM API](https://project-osrm.org/docs/v5.24.0/api/)). Polyline encode and decode are about 30 lines of stdlib. Routing itself needs a graph engine: OSRM, Valhalla or GraphHopper, self-hosted or hosted; mapwright should call one over HTTP rather than route in Python. A small stdlib Dijkstra over an OSM extract is possible for toy areas only.

## Optional tools

- **GDAL/OGR** (`ogr2ogr`, `gdal_translate`, `gdalwarp`, `gdaldem`): reads and writes nearly every format here ([GDAL drivers](https://gdal.org/en/stable/drivers/index.html)). The one tool to detect first on PATH. Python bindings are awkward to install on Windows; calling the CLI through `subprocess` avoids that.
- **PROJ / pyproj**: datum-aware reprojection and geodesic math (pyproj's `Geod` wraps Karney's GeographicLib algorithms) ([pyproj Geod](https://pyproj4.github.io/pyproj/stable/api/geod.html)). Stdlib can do WGS 84 to Web Mercator and UTM formulas, but not general datum shifts, which need grid files.
- **shapely** (GEOS): buffer, union, intersection, validity, simplify ([shapely docs](https://shapely.readthedocs.io/)). Licences: shapely BSD-3-Clause ([LICENSE.txt](https://github.com/shapely/shapely/blob/main/LICENSE.txt)), pyproj MIT ([LICENSE](https://github.com/pyproj4/pyproj/blob/main/LICENSE)), both checked 2026-11-14; GEOS and PROJ underneath are LGPL-2.1 and MIT respectively (not re-checked).
- **rasterio**: GDAL raster I/O with a Pythonic API ([rasterio](https://rasterio.readthedocs.io/)).
- **QGIS headless**: `qgis_process run <algorithm>` runs Processing algorithms without the GUI ([QGIS qgis_process docs](https://docs.qgis.org/latest/en/docs/user_manual/processing/standalone.html)). Heavy install; useful for cartographic rendering and algorithms nothing else has.
- **Pillow**: PNG/JPEG/WebP codecs and drawing for rendering map images ([Pillow](https://pillow.readthedocs.io/)).
- **Headless browser** (Playwright or Chrome `--headless --screenshot`): renders a MapLibre GL or Leaflet page to an image for styled vector maps ([MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/)).

## Spatial operations

### Geodesic distance

- Haversine on a sphere (R = 6371008.8 m mean radius) errs up to about 0.5% against the ellipsoid (unverified figure; commonly cited as up to 0.3 to 0.5%).
- Vincenty's inverse formula (1975) on WGS 84 gives sub-millimetre accuracy but fails to converge for nearly antipodal points ([Vincenty 1975, Survey Review](https://www.ngs.noaa.gov/PUBS_LIB/inverse.pdf)).
- Karney's algorithm (2013) is accurate to about 15 nm and always converges ([Karney, "Algorithms for geodesics", J. Geodesy 2013](https://doi.org/10.1007/s00190-012-0578-z)); `geographiclib` is a pure-Python port with no dependencies ([geographiclib Python](https://geographiclib.sourceforge.io/Python/)). The Python package is MIT-licensed (copyright Charles Karney; keep the notice), which allows vendoring it and keeps mapwright stdlib-only ([geographiclib-python LICENSE](https://github.com/geographiclib/geographiclib-python/blob/main/LICENSE), checked 2026-11-14).

WGS 84 constants: a = 6378137 m, f = 1/298.257223563 ([NGA WGS 84, TR8350.2](https://earth-info.nga.mil/php/download.php?file=coord-wgs84)).

### Area on the ellipsoid

Planar shoelace area on lon/lat degrees is meaningless. Options: spherical excess for polygons on a sphere (the method behind Turf's `area`) ([Turf area](https://turfjs.org/docs/api/area)); Karney's geodesic polygon area on the ellipsoid (`Geodesic.Polygon` in geographiclib, `Geod.geometry_area_perimeter` in pyproj) ([GeographicLib planimeter](https://geographiclib.sourceforge.io/C++/doc/Planimeter.1.html)); or project to an equal-area CRS first. Signs depend on ring orientation; take the absolute value and subtract holes.

### Buffer

Buffering in degrees gives ellipses that stretch toward the poles. Project to a local metric CRS (UTM zone or azimuthal equidistant centred on the feature), buffer, and project back. A stdlib point buffer is easy (geodesic circle by direct problem at N bearings); line and polygon buffers with joins and self-intersection cleanup belong to GEOS via shapely ([shapely buffer](https://shapely.readthedocs.io/en/stable/reference/shapely.buffer.html)).

### Simplify

- Douglas-Peucker (1973) keeps points farther than a tolerance from the chord; recursive, O(n log n) typical, O(n^2) worst ([Douglas and Peucker 1973, Cartographica](https://doi.org/10.3138/FM57-6770-U75U-7727)).
- Visvalingam-Whyatt (1993) removes the point with the smallest effective triangle area each step; looks smoother for cartography ([Visvalingam and Whyatt 1993](https://doi.org/10.1179/000870493786962263)).

Both are under 80 lines of stdlib. Traps: neither preserves topology, so rings can self-intersect and shared borders between neighbours drift apart (TopoJSON or shapely `simplify(preserve_topology=True)` avoid this); tolerance in degrees means different metres at different latitudes; never let a ring drop below four points.

### Clip and overlay

Clipping to a rectangle (tiles, viewports) is stdlib-friendly: Cohen-Sutherland or Liang-Barsky for lines and Sutherland-Hodgman for polygons. Sutherland-Hodgman can leave degenerate zero-width edges with concave polygons, harmless for rendering but not for analysis ([Sutherland and Hodgman 1974, CACM](https://doi.org/10.1145/360767.360802)). General polygon overlay (intersection, union, difference of arbitrary polygons) needs Weiler-Atherton, Greiner-Hormann or Martinez-Rueda; these are hard to make robust with floats, so use shapely or GEOS for them.

## Traps checklist

- **Lon/lat order**: GeoJSON, KML, WKT in practice, MVT and shapefiles use x=lon, y=lat. GPX attributes are named, so they are safe. EPSG:4326 officially defines latitude first, and GDAL 3+ and PROJ 6+ honour authority axis order unless told otherwise (`OAMS_TRADITIONAL_GIS_ORDER`, pyproj `always_xy=True`) ([GDAL OSR axis order](https://gdal.org/en/stable/tutorials/osr_api_tut.html#crs-and-axis-order), [pyproj Transformer](https://pyproj4.github.io/pyproj/stable/api/transformer.html)). Leaflet and many APIs take `[lat, lon]`. Test with a point whose swap lands off the planet or in the sea.
- **Winding order**: GeoJSON wants CCW outer rings (RFC 7946), shapefiles CW, MVT CW in y-down tile space. Compute the signed area and reverse rings on write.
- **Antimeridian**: lines from 179° to -179° draw across the whole map. Split at ±180 on write (RFC 7946 sec. 3.1.9), and handle bboxes with west > east. Polygons around a pole cannot be represented without a pole vertex.
- **Invalid polygons**: self-intersections (bowties), unclosed rings, duplicate points, holes outside shells and touching rings break area and overlay. OGC validity rules are in Simple Features; shapely `make_valid` or GEOS `MakeValid` fix them, and a buffer of 0 is the old trick ([shapely make_valid](https://shapely.readthedocs.io/en/stable/reference/shapely.make_valid.html)).
- **Datums and heights**: WGS 84 vs NAD83 vs ETRS89 differ by up to a few metres; ellipsoid vs geoid heights differ by up to about 100 m (unverified range; EGM96 undulation spans roughly -106 to +85 m). SRTM is geoid-referenced and GPS reports ellipsoid heights.
- **Web Mercator distortion**: areas and lengths in EPSG:3857 metres are wrong except at the equator; scale factor is sec(latitude).
- **Precision**: 7 decimals is about 1 cm; anything beyond is noise that bloats files.
- **Encoding**: DBF codepages, KML/GPX UTF-8, and BOMs at the start of CSVs.
- **Topology lint for vector output**: line ends snapped within tolerance, no overlapping polygons, no gaps or slivers between neighbours, no duplicate features, and coverages (countries, lots, districts) planar so every point is owned once (Longley et al., Geographic Information Science and Systems, ch. 7, 13).

## Open questions for mapwright

- Vendor `geographiclib` (pure Python) to stay stdlib-only for Karney distance and area, or write a Vincenty fallback? The licence is MIT (checked 2026-11-14), so vendoring is allowed.
- Use GDAL if it is on PATH and fall back to stdlib otherwise, or keep stdlib as the main route?
- PNG decoder scope: support palette and interlaced PNG, or require Pillow for those?
- GeoParquet and JPEG 2000 are optional-only; is that acceptable?

## Sources

Accessed 2026-11-14. PMTiles, MBTiles, GeoPackage and the geographiclib licence were fetched and checked that day (marked "checked 2026-11-14" inline); the rest are from recall of the published specs and not re-fetched.

- geographiclib-python licence: https://github.com/geographiclib/geographiclib-python/blob/main/LICENSE

- RFC 7946 GeoJSON: https://www.rfc-editor.org/rfc/rfc7946
- RFC 8142 GeoJSON Text Sequences: https://www.rfc-editor.org/rfc/rfc8142
- RFC 4180 CSV: https://www.rfc-editor.org/rfc/rfc4180
- OGC Simple Features Access: https://www.ogc.org/standard/sfa/
- PostGIS EWKB: https://postgis.net/docs/ST_AsEWKB.html
- ESRI Shapefile Technical Description: https://www.esri.com/content/dam/esrisites/sitecore-archive/Files/Pdfs/library/whitepapers/pdfs/shapefile.pdf
- pyshp: https://github.com/GeospatialPython/pyshp
- OGC GeoPackage: https://www.geopackage.org/spec/
- OGC KML 2.2: https://www.ogc.org/standard/kml/
- Google KMZ: https://developers.google.com/kml/documentation/kmzarchives
- Python XML vulnerabilities: https://docs.python.org/3/library/xml.html#xml-vulnerabilities
- GPX 1.1: https://www.topografix.com/GPX/1/1/
- TopoJSON spec: https://github.com/topojson/topojson-specification
- FlatGeobuf: https://flatgeobuf.org/
- GeoParquet 1.1: https://geoparquet.org/releases/v1.1.0/
- Apache Parquet: https://parquet.apache.org/docs/file-format/
- OSM XML, PBF, multipolygon, area, Overpass, slippy tiles: https://wiki.openstreetmap.org/
- OSM tile usage policy: https://operations.osmfoundation.org/policies/tiles/
- pyosmium: https://osmcode.org/pyosmium/
- TIFF 6.0: https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf
- OGC GeoTIFF 1.1: https://docs.ogc.org/is/19-008r4/19-008r4.html
- OGC COG 1.0: https://docs.ogc.org/is/21-026/21-026.html
- PNG (W3C): https://www.w3.org/TR/png-3/
- Esri world files: https://pro.arcgis.com/en/pro-app/latest/help/data/imagery/world-files-for-raster-datasets.htm
- GDAL drivers (CSV, Shapefile, Parquet, AAIGrid, JP2OpenJPEG, SRTMHGT, COG, gdaldem): https://gdal.org/en/stable/drivers/index.html
- USGS SRTM: https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1
- Copernicus DEM: https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model
- Mapbox Terrain-RGB: https://docs.mapbox.com/data/tilesets/reference/mapbox-terrain-rgb-v1/
- Tilezen Terrarium: https://github.com/tilezen/joerd/blob/master/docs/formats.md
- OSGeo TMS: https://wiki.osgeo.org/wiki/Tile_Map_Service_Specification
- MBTiles 1.3: https://github.com/mapbox/mbtiles-spec/blob/master/1.3/spec.md
- PMTiles v3: https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md
- MVT 2.1: https://github.com/mapbox/vector-tile-spec/tree/master/2.1
- tippecanoe: https://github.com/felt/tippecanoe
- Google polyline: https://developers.google.com/maps/documentation/utilities/polylinealgorithm
- OSRM API: https://project-osrm.org/docs/v5.24.0/api/
- pyproj: https://pyproj4.github.io/pyproj/stable/
- shapely: https://shapely.readthedocs.io/
- rasterio: https://rasterio.readthedocs.io/
- qgis_process: https://docs.qgis.org/latest/en/docs/user_manual/processing/standalone.html
- Pillow: https://pillow.readthedocs.io/
- MapLibre GL JS: https://maplibre.org/maplibre-gl-js/docs/
- Vincenty 1975: https://www.ngs.noaa.gov/PUBS_LIB/inverse.pdf
- Karney 2013: https://doi.org/10.1007/s00190-012-0578-z
- GeographicLib: https://geographiclib.sourceforge.io/
- NGA WGS 84: https://earth-info.nga.mil/php/download.php?file=coord-wgs84
- Turf area: https://turfjs.org/docs/api/area
- Douglas-Peucker 1973: https://doi.org/10.3138/FM57-6770-U75U-7727
- Visvalingam-Whyatt 1993: https://doi.org/10.1179/000870493786962263
- Sutherland-Hodgman 1974: https://doi.org/10.1145/360767.360802
- GDAL axis order: https://gdal.org/en/stable/tutorials/osr_api_tut.html
