# Projections, datums and CRS for mapwright

Reference for the mapwright plugin: what a datum and a CRS are, which EPSG codes matter, what each common projection keeps and breaks, how to pick one, how to handle the antimeridian and the poles, which projections a pure-Python (stdlib `math`) implementation can carry, and how to map invented worlds and other bodies.

Status: written 2026-11-14 from primary sources named inline. Only items marked "checked 2026-11-14" were verified against a fetched source (Snyder PP 1395 is confirmed as Snyder, J. P., 1987, "Map projections: A working manual", USGS Professional Paper 1395, 385 p., https://doi.org/10.3133/pp1395, checked 2026-11-14 via the USGS Publications Warehouse listing; its page numbers and worked examples were not re-read because pubs.usgs.gov returned 403 to the fetcher; pass 5 on 2026-11-16 read the PDF via curl and checked the appendix A rows and p.99. EPSG terms: the dataset is free from IOGP, may be subset and redistributed but not for profit, IOGP ownership must be acknowledged and the terms passed on, https://epsg.org/terms-of-use.html, revised 2016-04-08, via search 2026-11-14; the page itself returned 403); every other number below was taken from the sources as remembered and **must be checked against the source before it becomes a test fixture**. Items carrying a specific risk are marked "(unverified)". The Sources list gives the access date 2026-11-14 for all URLs.

## 1. Terms

- **Ellipsoid**: the mathematical surface used for the Earth's shape, defined by semi-major axis `a` and inverse flattening `1/f`. WGS 84: `a = 6378137.0 m`, `1/f = 298.257223563` (EPSG:7030, https://epsg.io/7030; NGA TR8350.2, https://earth-info.nga.mil/).
- **GRS 80**: `a = 6378137.0 m`, `1/f = 298.257222101` (EPSG:7019). It differs from WGS 84 only in `b`, by about 0.1 mm (Moritz, "Geodetic Reference System 1980", Bulletin Géodésique 1980/2000).
- **Datum** (geodetic reference frame): an ellipsoid plus how it is tied to the Earth. WGS 84 (EPSG:6326), NAD83 (EPSG:6269), ETRS89 (EPSG:6258) are datums. The same latitude/longitude pair points to places up to about 1-2 m apart between WGS 84 and NAD83 in North America, and up to hundreds of metres for older local datums such as NAD27 or OSGB36 (PROJ docs, "Geodetic transformation", https://proj.org/en/stable/usage/transformations.html; Ordnance Survey, "A guide to coordinate systems in Great Britain", https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf).
- **CRS** (coordinate reference system): a datum plus a coordinate system. A geographic CRS uses latitude/longitude; a projected CRS adds a map projection with its parameters and units (ISO 19111:2019; https://proj.org/en/stable/glossary.html).
- **Axis order**: EPSG:4326 is officially latitude first, longitude second. GeoJSON (RFC 7946, https://datatracker.ietf.org/doc/html/rfc7946 section 3.1.1) and most software use longitude, latitude. PROJ offers `+proj=longlat`/`OGC:CRS84` for the lon-lat order (https://proj.org/en/stable/faq.html). This is the most common source of swapped maps.
- **GeoJSON** is fixed to WGS 84 lon/lat in decimal degrees (RFC 7946 section 4); the old `crs` member was removed.

## 2. EPSG codes worth knowing

All from the EPSG Geodetic Parameter Dataset (https://epsg.org) unless marked. ESRI codes (`ESRI:` prefix) are not EPSG codes even though some tools accept them as `EPSG:54030`.

| Code | Name | Use |
|---|---|---|
| EPSG:4326 | WGS 84 geographic 2D | GPS, GeoJSON (in lon,lat order) |
| EPSG:4979 | WGS 84 geographic 3D | lat, lon, ellipsoidal height |
| EPSG:4978 | WGS 84 geocentric (ECEF) | X, Y, Z metres |
| EPSG:4269 | NAD83 | US/Canada vector data |
| EPSG:4267 | NAD27 | old US maps |
| EPSG:4258 | ETRS89 | Europe |
| EPSG:4277 | OSGB36 | Great Britain, old |
| EPSG:27700 | OSGB36 / British National Grid | UK Ordnance Survey grid |
| EPSG:3857 | WGS 84 / Pseudo-Mercator | Web tiles (Google, OSM, Bing) |
| EPSG:32601-32660 | WGS 84 / UTM zones 1N-60N | `326` + zone number |
| EPSG:32701-32760 | WGS 84 / UTM zones 1S-60S | `327` + zone number |
| EPSG:269xx | NAD83 / UTM zone xxN (xx = 01-23) | North America |
| EPSG:5070 | NAD83 / Conus Albers | US area statistics |
| EPSG:3035 | ETRS89-extended / LAEA Europe | EU statistics (INSPIRE) |
| EPSG:3995 | WGS 84 / Arctic Polar Stereographic | Arctic |
| EPSG:3031 | WGS 84 / Antarctic Polar Stereographic | Antarctica |
| EPSG:3413 | WGS 84 / NSIDC Sea Ice Polar Stereographic North | sea ice |
| EPSG:4087 | WGS 84 / World Equidistant Cylindrical | plate carrée in metres |
| EPSG:8857 | WGS 84 / Equal Earth Greenwich | world thematic maps |
| ESRI:54030 | World_Robinson | world reference maps |
| ESRI:54042 | World_Winkel_Tripel_NGS | world reference maps (code and name confirmed in PROJ's esri.sql, https://raw.githubusercontent.com/OSGeo/PROJ/master/data/sql/esri.sql, checked 2026-11-15) |
| ESRI:54009 | World_Mollweide | world equal-area |

UTM zone rule: `zone = floor((lon + 180) / 6) + 1`, central meridian `-183 + 6*zone`, with exceptions in Norway (zone 32V widened to 9° wide over 56-64°N) and Svalbard (zones 31X, 33X, 35X, 37X widened; 32X, 34X, 36X unused) (NGA, "The Universal Grids", DMA TM 8358.2, https://earth-info.nga.mil/; Snyder 1987 p.57-64). UTM covers 80°S to 84°N; the poles use UPS (polar stereographic, scale 0.994) (DMA TM 8358.2).

UTM parameters: Transverse Mercator, scale factor `k0 = 0.9996`, false easting 500 000 m, false northing 0 (north) or 10 000 000 m (south) (Snyder 1987 p.57).

## 3. The projections

Each entry gives the property kept, what breaks, and the source. "Conformal" keeps local angles and shape (Tissot ellipses are circles) at the cost of area; "equal-area" keeps area at the cost of shape; "equidistant" keeps distance along some lines only; a "compromise" keeps none exactly. No flat map keeps all of them: Gauss's Theorema Egregium rules out a distortion-free map of a sphere (Snyder 1987 p.3-4).

### 3.1 Mercator (cylindrical, conformal)
- Keeps: angles; rhumb lines (constant compass bearing) are straight lines, hence its navigation use (Snyder 1987 p.38).
- Breaks: area grows with `sec²(φ)`; scale factor `k = sec φ` on the sphere. At 60° area is 4x; the poles are at infinity (Snyder 1987 p.38-41).
- Sphere: `x = R(λ - λ0)`, `y = R ln tan(π/4 + φ/2)`. Inverse: `φ = π/2 - 2 atan(e^(-y/R))` (Snyder 1987 eq. 7-1, 7-2, 7-4).
- Ellipsoid: `y = a ln[tan(π/4 + φ/2) ((1 - e sin φ)/(1 + e sin φ))^(e/2)]`; the inverse iterates or uses a series (Snyder 1987 eq. 7-7, 7-9).

### 3.2 Web Mercator / Pseudo-Mercator (EPSG:3857)
- The spherical Mercator formulas applied to WGS 84 geodetic coordinates with `R = a = 6378137 m`. It is **not conformal** on the ellipsoid; scale errors up to about 0.7% in northing, and NGA has warned against its use for positioning (NGA advisory "Implementation practice Web Mercator map projection", NGA.STND.0039, 2014, https://earth-info.nga.mil/; EPSG:3857 remarks, https://epsg.io/3857).
- Square world: latitude clipped to ±85.0511287798° so that `y` range equals `x` range ±20 037 508.342789244 m (`π·a`) (OSM wiki "Slippy map tilenames", https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames).
- Tile math (OSM): `n = 2^zoom`, `xtile = floor((lon + 180)/360 · n)`, `ytile = floor((1 - asinh(tan φ)/π)/2 · n)` (same OSM wiki page).

### 3.3 Transverse Mercator and UTM (cylindrical, transverse aspect, conformal)
- Keeps: angles; accurate within a few degrees of the central meridian. Breaks: scale grows fast away from it; UTM zones are 6° wide so error stays below about 1 part in 2500 (Snyder 1987 p.48-57).
- Sphere: `B = cos φ sin(λ-λ0)`, `x = ½ R k0 ln((1+B)/(1-B))`, `y = R k0 (atan2(tan φ, cos(λ-λ0)) - φ0)` (Snyder 1987 eq. 8-1, 8-3).
- Ellipsoid: Snyder's series (eq. 8-9 to 8-11) is good to about a millimetre within the zone but degrades beyond ±4° or so. PROJ uses the Poder/Engsager extended Krüger series (`+proj=tmerc` default since PROJ 6, `+approx` for the old one), accurate to a few mm out to about 3900 km from the central meridian (https://proj.org/en/stable/operations/projections/tmerc.html; Karney 2011, "Transverse Mercator with an accuracy of a few nanometers", J. Geodesy 85:475-485, https://doi.org/10.1007/s00190-011-0445-3). Krüger series to order n^6 is short and pure-Python friendly.

### 3.4 Lambert conformal conic (LCC)
- Keeps: angles; true scale on one or two standard parallels. Breaks: area away from the standard parallels; good for mid-latitude regions wider east-west (Snyder 1987 p.104-110).
- Used by US State Plane zones, many national grids, aviation charts (Snyder 1987 p.105).
- Sphere, two standard parallels φ1, φ2: `n = ln(cos φ1 / cos φ2) / ln[tan(π/4+φ2/2)/tan(π/4+φ1/2)]`, `F = cos φ1 tan^n(π/4+φ1/2)/n`, `ρ = R F / tan^n(π/4+φ/2)`, `x = ρ sin θ`, `y = ρ0 - ρ cos θ`, `θ = n(λ-λ0)` (Snyder 1987 eq. 15-1 to 15-5).

### 3.5 Albers equal-area conic
- Keeps: area. Breaks: shape away from the standard parallels; scale along parallels and meridians are reciprocal (Snyder 1987 p.98-103).
- Standard choice for the conterminous US: standard parallels 29.5° and 45.5°, origin 23°N 96°W (EPSG:5070; Snyder 1987 p.99).
- Sphere: `n = (sin φ1 + sin φ2)/2`, `C = cos²φ1 + 2n sin φ1`, `ρ = R sqrt(C - 2n sin φ)/n` (Snyder 1987 eq. 14-1 to 14-3).

### 3.6 Lambert azimuthal equal-area (LAEA)
- Keeps: area, and true direction from the centre. Breaks: shape away from the centre; the antipode becomes a circle (Snyder 1987 p.182-190).
- Good for continents and roughly round regions; EPSG:3035 for Europe centred 52°N 10°E (EPSG registry).
- Sphere: `k' = sqrt(2/(1 + sin φ1 sin φ + cos φ1 cos φ cos(λ-λ0)))`, `x = R k' cos φ sin(λ-λ0)`, `y = R k' (cos φ1 sin φ - sin φ1 cos φ cos(λ-λ0))` (Snyder 1987 eq. 24-1 to 24-4).

### 3.7 Equirectangular / plate carrée
- Keeps: distance along meridians (and along the standard parallels). Breaks: shape and area away from the standard parallel; neither conformal nor equal-area (Snyder 1987 p.90-91).
- `x = R (λ-λ0) cos φ1`, `y = R (φ - φ1)` (Snyder 1987 eq. 12-1, 12-2). With φ1 = 0 it is plate carrée: pixels are degrees. This is the native layout of most global rasters, equirectangular textures, and NASA planetary mosaics (simple cylindrical) (USGS Astrogeology, https://astrogeology.usgs.gov/).
- It is the natural default for an invented world stored as an image: 2:1 aspect, row = latitude, column = longitude.

### 3.8 Robinson (pseudocylindrical compromise)
- Keeps: nothing exactly; designed to "look right" for world maps; poles are lines 0.5322 of the equator length. Used by National Geographic 1988-1998 (Snyder, "Flattening the Earth", 1993, p.214-216; Robinson 1974).
- Defined by a table of `X` and `Y` factors at 5° steps with interpolation, not a closed formula; the inverse needs iteration (Snyder & Voxland, "An Album of Map Projections", USGS PP 1453, 1989, p.82-83, https://pubs.usgs.gov/publication/pp1453; PROJ `+proj=robin`, https://proj.org/en/stable/operations/projections/robin.html). PROJ evaluates a cubic polynomial per 5° interval from four stored coefficients per node, `c0 + z(c1 + z(c2 + z c3))` (https://raw.githubusercontent.com/OSGeo/PROJ/master/src/projections/robin.cpp, checked 2026-11-15). That plain linear interpolation gives visibly kinked meridians is a practice figure, no single source; tunable default (pass 5 on 2026-11-16 found none; plot both to see).

### 3.9 Equal Earth (pseudocylindrical, equal-area)
- Keeps: area; meridians are smooth curves, look similar to Robinson. Published 2018 as a free equal-area alternative to Robinson and Gall-Peters (Šavrič, Patterson, Jenny, "The Equal Earth map projection", IJGIS 33(3), 2019, https://doi.org/10.1080/13658816.2018.1504949).
- Sphere: `θ = asin(√3/2 · sin φ)`, `x = 2√3 R λ cos θ / (3(9A4θ^8 + 7A3θ^6 + 3A2θ^2 + A1))`, `y = R(A4θ^9 + A3θ^7 + A2θ^3 + A1θ)`, with `A1 = 1.340264`, `A2 = -0.081106`, `A3 = 0.000893`, `A4 = 0.003796`. Inverse: Newton iteration on θ, converges in a few steps (Šavrič et al. 2019; https://proj.org/en/stable/operations/projections/eqearth.html).
- EPSG:8857 (WGS 84 / Equal Earth Greenwich), 8858 (Americas), 8859 (Asia-Pacific) (EPSG registry).

### 3.10 Winkel tripel (azimuthal-derived compromise)
- Keeps: nothing exactly; low combined distortion of area, angle and distance; National Geographic's world projection since 1998 (Goldberg & Gott, "Flexion and Skewness in Map Projections of the Earth", Cartographica 42(4), 2007, https://arxiv.org/abs/astro-ph/0608501).
- Mean of Aitoff and equirectangular with φ1 = acos(2/π): `α = acos(cos φ cos(λ/2))`, `sinc α = sin α / α`, `x = ½ R [λ cos φ1 + 2 cos φ sin(λ/2)/sinc α]`, `y = ½ R [φ + sin φ / sinc α]` (Snyder 1993 p.233; PROJ `+proj=wintri`, https://proj.org/en/stable/operations/projections/wintri.html). No closed inverse; use 2D Newton (Ipbüker & Bildirici 2002, "A general algorithm for the inverse transformation of map projections using Jacobian matrices", Proc. Third Int. Symposium on Mathematical & Computational Applications, Konya, 2002, pp. 175-182; title, venue and pages checked 2026-11-16 in the reference list of Applications of Mathematics 2018, https://link.springer.com/article/10.21136/AM.2018.0096-18; the paper text is still not online, blocked. The later Ipbüker & Bildirici 2005 Winkel paper in J. Surveying Engineering is a citable substitute).

### 3.11 Orthographic (azimuthal, perspective from infinity)
- Keeps: the look of a globe from space; only one hemisphere visible. Breaks: area and shape severely near the edge (Snyder 1987 p.145-153).
- `x = R cos φ sin(λ-λ0)`, `y = R (cos φ1 sin φ - sin φ1 cos φ cos(λ-λ0))`; a point is visible when `cos c = sin φ1 sin φ + cos φ1 cos φ cos(λ-λ0) ≥ 0` (Snyder 1987 eq. 20-3, 20-4, 5-3).
- Use for "globe view" art of real or invented planets.
- Minimap or globe inset: a marker on the far side (`cos c < 0`) sits on the rim at angle `atan2(y, x)` of its unclipped `x, y`, so it still points the right way (`mpw_sphere.rim_angle`).
- Draw it smaller or hollow so it reads as "behind the globe", not on the edge.

### 3.12 Stereographic (azimuthal, conformal)
- Keeps: angles; circles on the sphere map to circles. Breaks: area grows away from the centre; the antipode is at infinity (Snyder 1987 p.154-163).
- Polar stereographic is standard for polar regions (UPS, EPSG:3031, 3995) (Snyder 1987 p.157).
- Sphere: `k = 2k0/(1 + sin φ1 sin φ + cos φ1 cos φ cos(λ-λ0))`, `x = R k cos φ sin(λ-λ0)`, `y = R k (cos φ1 sin φ - sin φ1 cos φ cos(λ-λ0))` (Snyder 1987 eq. 21-2 to 21-4).

### 3.13 Gnomonic (azimuthal, perspective from centre)
- Keeps: every great circle is a straight line, so the shortest route is a straight line. Breaks: everything else; less than a hemisphere can be shown (Snyder 1987 p.164-168).
- `cos c` as above; `x = R cos φ sin(λ-λ0)/cos c`, `y = R (cos φ1 sin φ - sin φ1 cos φ cos(λ-λ0))/cos c`; visible only for `cos c > 0` (Snyder 1987 eq. 22-4, 22-5).
- Used for great-circle route planning and as the face projection of cube-sphere planets in games.
- Sphere toolkit in `scripts/mpw_sphere.py` (stdlib): `unit(lon, lat)` gives a unit vector; `frame(c)` and `gnomonic(p, frame)` project, returning None for `cos c <= 0`, the hemisphere clip.
- Point in a spherical polygon: project about the vertex mean and run the plane ray test. Edges are great circles, so they stay straight and the answer is exact for polygons inside one hemisphere.
- Great-circle arc crossing: the two plane normals `a×b` and `p×q` meet at `±(a×b)×(p×q)`; keep the sign that lies on both arcs, or none.
- Use this instead of a lon/lat ray test, which fails across the antimeridian and near the poles.
- Checked against the three-plane inside test on 5000 random points (tests/test_sphere.py).
- Technique idea from robinduckett/boo-mas (no licence there; own code).

### 3.14 Projections by first use (for period styles)

A `since` year per projection lets a period style refuse a later one. All years are from Thrower, Maps and Civilization, ch. 5-9 (book facts, not cross-checked).

| Projection | Since |
|---|---|
| Ptolemy's projections in print | 1470s |
| Heart-shaped (cordiform) and oval world maps | 1507 to 1521; a polar azimuthal world map 1511; a double heart-shaped world map 1538 |
| Conic with two standard parallels | 1554 |
| Mercator | 1569; the mathematics published 1599; usual on sea charts only from the 17th century |
| Sinusoidal | regular use in the 17th century |
| Lambert conformal conic, Lambert azimuthal equal-area, transverse Mercator | 1770s (1772 in the reader's summary) |
| Bonne | the French survey from 1803 (Cassini's projection before that) |
| Gnomonic for land maps | 1803 |
| Mollweide | 1805; Albers equal-area conic about the same time |
| Polyconic | 1820 |
| Eckert's six | 1906 |
| Goode's interrupted homolosine | 1923 |
| Robinson | 1963 (section 3.8 cites the 1974 paper) |

Gall's cylindrical projections are left out: Thrower dates them to an 1885 publication and Monmonier to 1855. The distortion ellipse (section 5) was published in 1881.

### 3.15 Ptolemy's first projection (historical note)

- Before Ptolemy, Marinus of Tyre used a rectangular grid in which the parallel of Rhodes (36 north) stood to the meridian as 4 to 5. Ptolemy faulted it for making every parallel the same length.
- Ptolemy's first projection: meridians are straight lines meeting at a point that is not the pole, and parallels are arcs about that point. Scale is kept along the Rhodes parallel and along the meridians, and the proportion of the Thule parallel (63 north) to the equator is right. The meridians kink at the equator; his second projection curves them to cure that.
- His inhabited world spans 180 degrees of longitude from a prime meridian at the Fortunate Isles and runs from 63 north to about 16.5 south, on a degree of 500 stades (the smaller earth).
- The maps we have are Byzantine or later; whether Ptolemy drew any himself is unsettled. The notes hold no formula, so a `ptolemy1` preset needs the chapter itself.

Source: Harley and Woodward, History of Cartography vol. 1, ch. 11 (book facts, not cross-checked).
## 4. Picking a projection

Snyder's rule of thumb, which mapwright can apply automatically from the bounding box (Snyder 1987 p.33-35; Snyder 1993; also the Projection Wizard by Šavrič, Jenny, White, Strebe 2016, https://projectionwizard.org, Cartography and GIS 43(4)):

| Purpose / extent | Choose |
|---|---|
| Web slippy map, tiles | EPSG:3857 (accept area distortion) |
| Navigation, compass bearings | Mercator |
| Great-circle routes | Gnomonic (draw), azimuthal equidistant (distances from one point) |
| World, area comparison (choropleths, density) | Equal Earth, Mollweide |
| World, general reference | Winkel tripel, Robinson, Equal Earth |
| Continent or round region, area | LAEA centred on the region |
| Mid-latitude region wider east-west, area | Albers with standard parallels at 1/6 and 5/6 of the latitude span |
| Mid-latitude region wider east-west, shape | LCC, same parallels |
| Region elongated north-south, or small (< 6° wide) | Transverse Mercator / the UTM zone |
| Tropical region wider east-west | Mercator (conformal) or cylindrical equal-area |
| Polar region | Polar stereographic (shape) or polar LAEA (area) |
| Globe illustration | Orthographic |
| Raw raster storage, game world texture | Equirectangular (plate carrée) |

The 1/6 and 5/6 rule for conic standard parallels is from Deetz and Adams via Snyder 1987 p.99 (checked 2026-11-16 in https://pubs.usgs.gov/pp/1395/report.pdf: Deetz and Adams 1934 p.79, 91 recommend one-sixth of the central meridian's length in from the north and south limits; Hinks 1912 suggested one-seventh). Projection Wizard's thresholds: whole world, hemisphere, continent, then regions by aspect ratio and latitude of centre (Šavrič et al. 2016).

## 5. Tissot's indicatrix

- An infinitely small circle on the globe projects to an ellipse; its semi-axes `a'` and `b'` are the maximum and minimum scale factors at that point (Tissot 1881; Snyder 1987 p.20-24).
- Conformal: `a' = b'` everywhere (circles stay circles, sizes change). Equal-area: `a'·b' = 1` (ellipses, same area). Maximum angular distortion `ω = 2 asin((a'-b')/(a'+b'))` (Snyder 1987 eq. 4-7).
- Computable numerically for any forward projection from the partial derivatives `∂x/∂φ, ∂x/∂λ, ∂y/∂φ, ∂y/∂λ` (Snyder 1987 eq. 4-9 to 4-12: `h`, `k`, `a'`, `b'`). Finite differences with a step of about 1e-6 rad are enough for drawing and for tests.
- mapwright use: draw Tissot circles at 30° grid points as a diagnostic overlay, and report `max ω` and the area ratio range over the map extent to justify the projection choice.

## 6. Antimeridian and poles

- **Antimeridian (±180°)**: a polygon or line crossing it must be split before projecting in any projection whose central meridian is not chosen to avoid it; otherwise segments wrap across the whole map. RFC 7946 section 3.1.9 requires GeoJSON geometries that cross the antimeridian to be cut into a MultiLineString or MultiPolygon, and bounding boxes may have `west > east` (section 5.2).
- Detect a crossing by `|lon2 - lon1| > 180` between consecutive vertices; interpolate the latitude at ±180 (along the great circle for long edges, linearly for short ones) and split. Re-centring with a new `λ0` moves the seam to `λ0 ± 180` and the split must be done there.
- Normalise longitudes to `[-180, 180)` with `((lon + 180) % 360) - 180` (Python `%` already returns a non-negative result for a positive divisor).
- **Poles**: Mercator and 3857 cannot show them (clip to ±85.0511° for 3857, about ±85° or ±89° for Mercator). A polygon containing a pole (Antarctica) has no closing edge in lon/lat; it needs vertices added along the map's pole line (`lat = -90` from 180 to -180) before projecting into a pseudocylindrical projection, and in polar azimuthals the seam disappears (Natural Earth notes Antarctica is closed this way: blocked, no Natural Earth page saying so found on 2026-11-16; d3-geo handles this with spherical clipping, https://d3js.org/d3-geo).
- Densify long edges before projecting (add points every ~1°), since straight lines in lon/lat become curves in most projections (PROJ `cs2cs` does not densify; GDAL `-segmentize`/`ogr2ogr -segmentize` does, https://gdal.org/programs/ogr2ogr.html).
- Azimuthals: clip at the horizon (`cos c < 0` for orthographic and gnomonic-limit `cos c ≤ small ε`), not after projecting.

## 7. Pure-Python feasibility

All of these need only `math` (sin, cos, tan, atan2, asinh, log, sqrt):

| Projection | Forward | Inverse | Notes |
|---|---|---|---|
| Equirectangular | closed | closed | trivial |
| Mercator sphere / 3857 | closed | closed | |
| Mercator ellipsoid | closed | iterate (or series, Snyder eq. 7-13) | |
| Transverse Mercator ellipsoid | Krüger series | Krüger series | ~60 lines (Karney 2011) |
| LCC, Albers | closed (sphere and ellipsoid) | closed, Albers ellipsoid iterates | Snyder ch. 14-15 |
| LAEA, stereographic, orthographic, gnomonic | closed | closed | sphere; ellipsoidal LAEA uses authalic latitude |
| Equal Earth | closed | Newton | 4 constants |
| Robinson | table + interpolation | iterate | 19-row table |
| Winkel tripel | closed | 2D Newton | |
| Mollweide | Newton on auxiliary angle | closed | Snyder 1987 eq. 31 |

Datum shifts: a 7-parameter Helmert transform via ECEF is pure Python and good to metres between modern datums; grid-based shifts (NADCON, NTv2, OSTN15) need data files and are out of scope without PROJ (PROJ docs, "Helmert transform", https://proj.org/en/stable/operations/transformations/helmert.html). Geodesic distances: Karney's algorithm is available as the pure-Python `geographiclib` package, but stdlib-only code can use Vincenty (fails to converge near antipodes) or haversine on a sphere (error up to about 0.5%) (Karney 2013, "Algorithms for geodesics", J. Geodesy 87:43-55, https://doi.org/10.1007/s00190-012-0578-z).

Policy: implement the table above in stdlib; if `pyproj` is importable, offer it as an optional backend and cross-check.

## 8. Invented worlds and other bodies

### 8.1 IAU planetary CRS in PROJ
- The IAU Working Group on Cartographic Coordinates and Rotational Elements (WGCCRE) publishes radii and rotation models; the latest full report is Archinal et al. 2018, "Report of the IAU WGCCRE: 2015", Celestial Mechanics and Dynamical Astronomy 130:22, https://doi.org/10.1007/s10569-017-9805-5.
- PROJ ships these as authority `IAU_2015` since PROJ 8.2 (2021), code scheme `body*100 + type`: `00` sphere planetocentric, `01` ellipsoid planetographic, `02` ellipsoid planetocentric (fixed 2026-11-15 from PROJ's iau.sql: the draft had `01` and `02` the wrong way round), then projected codes `10`, `15`, `20`... for equirectangular, Mercator, polar stereographic and others (https://proj.org/en/stable/news.html 8.2.0 notes; Marmo et al., GDAL/PROJ IAU codes RFC, https://github.com/OSGeo/PROJ/pull/2876, "Add IAU_2015 CRS definitions", merged 2021-10-05, checked 2026-11-15).
- Examples: `IAU_2015:49900` "Mars (2015) - Sphere / Ocentric" (https://spatialreference.org/ref/iau_2015/49900/, checked 2026-11-14); `IAU_2015:49901` "Mars (2015) / Ographic" and `IAU_2015:49902` "Mars (2015) / Ocentric" (fixed 2026-11-15: the draft called 49901 planetocentric, it is planetographic), `IAU_2015:30100` "Moon (2015) - Sphere / Ocentric", `IAU_2015:39900` "Earth (2015) - Sphere / Ocentric" (names from PROJ's iau.sql, https://raw.githubusercontent.com/OSGeo/PROJ/master/data/sql/iau.sql, checked 2026-11-15).
- Older OGC WMS codes `IAU2000:49900` etc. appear in USGS and NASA services (https://pds-imaging.jpl.nasa.gov/; blocked 2026-11-16: an archived USGS page offers IAU2000 codes for web services, https://webarchive.library.unt.edu/web/20130215033216/http://webgis.wr.usgs.gov/ogc/index.htm, but no fetched page shows 49900 itself; current codes live under IAU_2015 at https://spatialreference.org/ref/iau_2015/49901/).

### 8.2 Radii (IAU 2015 report, Archinal et al. 2018, table 4-5)

| Body | Mean radius | Equatorial a | Polar c | Note |
|---|---|---|---|---|
| Earth (WGS 84) | 6 371 008.8 m (mean) | 6 378 137 m | 6 356 752.3 m | IUGG mean |
| Mars | 3 389.50 km | 3 396.19 km | 3 376.20 km | flattening ~1/170 |
| Moon | 1 737.4 km | 1 737.4 km | 1 737.4 km | sphere by convention |
| Mercury | 2 439.4 km | - | - | sphere |
| Venus | 6 051.8 km | - | - | sphere |

- Mars: USGS and NASA mosaics (MOLA, HiRISE, CTX) use the sphere 3 396 190 m for map projection with planetocentric latitude and east-positive longitude 0-360 (USGS Astrogeology, Mars MOLA product notes, https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m, checked 2026-11-16: "The radius, still as a sphere, has been updated to conform to the IAU 2000 definition for Mars 3396190.0 m"; note that Duxbury et al. 2002 report USGS adopting the ellipsoid A = 3396.19 km, B = 3376.20 km as the reference surface for its MDIM mosaics, and 3389.50 km as the best-fit sphere; the radius itself, 3396190 m, is the IAU_2015 Mars sphere in PROJ's iau.sql, with polar radius 3376200 m for the ellipsoid, checked 2026-11-15). Hand-coded maths should accept both the sphere and the ellipsoid.
- Moon: always the sphere R = 1 737 400 m; LROC and LOLA products use it (Archinal et al. 2018; LOLA data notes, https://pds-geosciences.wustl.edu/missions/lro/lola.htm (URL live 2026-11-16; the page does not state the radius, so the LOLA-uses-1737400 part rests on Archinal et al.); the radius 1737400 m is the IAU_2015 Moon sphere in PROJ's iau.sql, checked 2026-11-15).
- Longitude convention: IAU defines planetographic longitude positive opposite to rotation (west-positive for prograde bodies like Mars); planetocentric longitude is east-positive. Since 2002 NASA Mars missions use planetocentric, east-positive (Archinal et al. 2018 section 2; Duxbury, Kirk, Archinal, Neumann 2002, "Mars Geodesy/Cartography Working Group recommendations on Mars cartographic constants and coordinate systems", ISPRS Commission IV Symposium, Ottawa, Int. Archives XXXIV Part 4, https://www.isprs.org/proceedings/XXXIV/Part4/pdfpapers/521.pdf, checked 2026-11-16: the USGS proposal for east/planetocentric Mars maps was approved at NASA headquarters in early 2002, and MOLA, TES, Odyssey and MER had already adopted it).

### 8.3 Invented worlds
- Store the world on a sphere of chosen radius (an Earth-size default R = 6 371 008.8 m keeps scale bars intuitive) in plate carrée; project for display only. This keeps the data independent of the view.
- Give each invented world a CRS record: radius (or a, 1/f), prime meridian, longitude direction, and a free-form name. A WKT2 `GEOGCRS` with a custom `ELLIPSOID` and no EPSG code is valid (ISO 19162:2019 / OGC 18-010r7, https://docs.ogc.org/is/18-010r7/18-010r7.html).
- Fantasy maps drawn as flat images have no projection. When asked to "put this on a globe", treat the image as equirectangular only if it is 2:1 and covers the whole world; otherwise treat it as a local flat map (a gnomonic or azimuthal-equidistant patch of chosen size) and say so.
- Ring worlds, flat worlds, cylinders (O'Neill colonies) and Dyson spheres: use a planar or cylindrical coordinate system with plain metres; no geodetic CRS applies.
- Cube-sphere worlds in games map each face by gnomonic projection, giving up to about 5x area variation, or by equal-area variants such as the quadrilateralized spherical cube (Chan & O'Neill 1975; COBE sky cube, PROJ `+proj=qsc`, https://proj.org/en/stable/operations/projections/qsc.html).
- Sci-fi star maps: use equatorial (RA/Dec) on the celestial sphere or galactic coordinates; whole-sky maps commonly use Mollweide or Hammer-Aitoff (Calabretta & Greisen 2002, "Representations of celestial coordinates in FITS", A&A 395:1077, https://doi.org/10.1051/0004-6361:20021327).

## 9. Rules the plugin should enforce

Each rule is checkable by a test.

1. **Every dataset carries a CRS.** Reject or warn on any geometry without one; GeoJSON input is EPSG:4326 lon/lat by definition (RFC 7946).
2. **Axis order is explicit.** Internally store lon, lat. If input values have `|first| ≤ 90` and `|second| > 90` for any point, flag a likely lat/lon swap.
3. **Ranges.** Latitude in [-90, 90]; longitude normalised to [-180, 180) (or [0, 360) for bodies whose CRS says so). Test: `normalize(190) == -170`, `normalize(-180) == -180`, `normalize(180) == -180`.
4. **No area statistics in 3857 or Mercator.** Area or density output must use an equal-area CRS (Equal Earth, Albers, LAEA, Mollweide) or geodesic area.
5. **3857 latitude clip at ±85.0511287798°.** Test: forward(lon=180, lat=0) gives `x = 20037508.342789244`; forward(0, 85.0511287798) gives `y ≈ 20037508.34` (OSM wiki; EPSG:3857).
6. **Round trip.** For every implemented projection, `inverse(forward(p))` returns p within 1e-9 degrees for points inside the valid domain (1e-6 for iterated inverses), on a grid of at least 10° spacing excluding singular points (poles in Mercator, antipode in LAEA/stereographic, outside hemisphere for orthographic/gnomonic).
7. **Antimeridian split.** Any edge with `|Δlon| > 180` is split at the seam before projecting; test with a line from (170, 0) to (-170, 0): the result has two parts meeting at x = ±180 equivalents.
8. **Densify** edges longer than 1° before projecting to any non-cylindrical projection.
9. **Visibility clip** for orthographic (`cos c ≥ 0`) and gnomonic (`cos c > 0.01` or a chosen cut) before drawing.
10. **Datum mismatch warning.** Combining layers with different datums without a declared transformation must warn; for WGS 84 vs NAD83 vs ETRS89 note the ~1-2 m difference, for NAD27/OSGB36 refuse to overlay without a shift.
11. **UTM zone selection** follows the formula with the Norway/Svalbard exceptions. Tests: (lon 3, lat 0) → zone 31, EPSG:32631, easting 500 000; (lon 5, lat 60) → zone 32 (Norway exception); (lon 15, lat 78) → zone 33 (Svalbard); (lon -177, lat -10) → EPSG:32701.
12. **Planetary bodies** use the IAU radius and longitude direction of their CRS; never Earth's ellipsoid for Mars or Moon data.
13. **No measurement on raw lat/lon.** Distance, area and buffer never run on unprojected degrees; project to a fitting CRS or use geodesic formulas (Longley et al., Geographic Information Science and Systems, ch. 4).
14. **Print the property.** The map or sidecar says whether its projection is conformal, equal-area or compromise, chosen by task (Longley et al., Geographic Information Science and Systems, ch. 4).
15. **No scale bar on world Web Mercator or Mercator.** Refuse a single scale bar on a Mercator or 3857 map spanning more than about 20 degrees of latitude; a Mercator world map with area claims warns, since Mercator is for constant-bearing navigation, not area comparison (Longley et al., Geographic Information Science and Systems, ch. 4) (Brotton, A History of the World in Twelve Maps, ch. 7). On any projection the stated scale is true only on the standard lines, and distortion grows with distance from them (Monmonier, How to Lie with Maps, 1991 ed., ch. 2).
16. **UTM zone straddle.** Data spanning more than one UTM zone is not drawn in one zone's CRS without a warning (Longley et al., Geographic Information Science and Systems, ch. 4).
17. **Range rings are geodesic.** On a small-scale map a range or distance ring is a geodesic circle, sampled and projected, never a circle drawn in map units: a circle on the globe seldom stays a circle on a flat map (Monmonier, How to Lie with Maps, 1991 ed., ch. 7). Test: every ring vertex lies at the stated geodesic distance from the centre.

### Test values

From Snyder 1987 numerical examples (pass 5 on 2026-11-16 downloaded https://pubs.usgs.gov/pp/1395/report.pdf with curl and a browser user agent (WebFetch had got 403) and checked every row against appendix A; printed page = PDF page - 12):

| Case | Input | Expected | Source |
|---|---|---|---|
| Mercator sphere, R = 1.0, λ0 = 180° | φ = 35°N, λ = 75°W | x = 1.8325957, y = 0.6528366 | Snyder 1987 p.266 (checked 2026-11-16; Snyder gives λ0 = 180° W, so λ-λ0 = +105° directly) |
| Mercator ellipsoid, Clarke 1866 (a = 6378206.4, e² = 0.00676866), λ0 = -180° | φ = 35°N, λ = 75°W | x = 11 688 673.7 m, y = 4 139 145.6 m | Snyder 1987 p.267 (corrected 2026-11-16: the old row had λ = 135°E and a made-up x) |
| Transverse Mercator sphere, R = 1, k0 = 1, λ0 = -75°, φ0 = 0 | φ = 40.5°N, λ = 73.5°W | x = 0.0199077, y = 0.7070276 | Snyder 1987 p.268 (checked 2026-11-16) |
| UTM, Clarke 1866, k0 = 0.9996, λ0 = -75° | φ = 40.5°N, λ = 73.5°W | x = 127 106.5 m (before false easting), y = 4 484 124.4 m | Snyder 1987 p.269-270 (checked 2026-11-16) |
| LCC ellipsoid, Clarke 1866, φ1 = 33°, φ2 = 45°, φ0 = 23°, λ0 = -96° | φ = 35°N, λ = 75°W | x = 1 894 410.9 m, y = 1 564 649.5 m | Snyder 1987 p.296-297 (checked 2026-11-16) |
| Albers ellipsoid, Clarke 1866, φ1 = 29.5°, φ2 = 45.5°, φ0 = 23°, λ0 = -96° | φ = 35°N, λ = 75°W | x = 1 885 472.7 m, y = 1 535 925.0 m | Snyder 1987 p.292-293 (checked 2026-11-16) |
| Web Mercator | lon 180, lat 0 | x = 20 037 508.342789 m | OSM wiki; exact = π·6378137 |
| Web Mercator tile | lon 0, lat 0, zoom 1 | tile (1, 1) | OSM tile formula (lat 0 sits on a tile edge; floor gives 1) |
| Equirectangular, R = 1, φ1 = 0 | lon 90, lat 45 | x = π/2, y = π/4 | definition |
| Equal Earth, R = 1 | lon 180, lat 0 | x ≈ 2.70663 (half-width) | computed from the formula, 2√3π/(3·1.340264) (checked 2026-11-14) |
| Equal Earth, R = 1 | lat 90 | y ≈ 1.317363 | computed from the formula with θ = π/3 (checked 2026-11-14) |
| Orthographic, R = 1, centre (0, 0) | lon 90, lat 0 | x = 1, y = 0 (horizon) | definition |
| Gnomonic, R = 1, centre (0, 0) | lon 45, lat 0 | x = 1, y = 0 | tan 45° |
| Stereographic, R = 1, k0 = 1, centre (0, 0) | lon 90, lat 0 | x = 2, y = 0 | 2 tan(45°) |

Wrap λ - λ0 into [-180, 180) before applying x = R(λ - λ0); Snyder's examples do this (the Mercator row's -255° becomes +105°). PROJ's own test suite (`test/gie/builtins.gie`, https://github.com/OSGeo/PROJ/blob/master/test/gie/builtins.gie) has forward/inverse pairs for every projection at fixed points (2, 1), (2, -1), (-2, 1), (-2, -1) degrees on GRS80; copying those values is the most reliable fixture source and avoids hand-transcription.

## 10. Open questions

- Copy fixtures from PROJ `builtins.gie` rather than from Snyder by hand? PROJ's COPYING is an MIT-style licence covering all source and data files (https://github.com/OSGeo/PROJ/blob/master/COPYING, checked 2026-11-14), so copying values with the notice is fine.
- Ship `geographiclib` (MIT, pure Python; https://github.com/geographiclib/geographiclib-python/blob/main/LICENSE, checked 2026-11-14) as an optional extra for geodesics, or keep haversine/Vincenty only?
- Confirm exact IAU_2015 code numbers for projected Mars and Moon CRS against `projinfo` before baking them in.

## Sources

All accessed 2026-11-14 (as cited; not re-fetched in this session).

- Snyder, John P. 1987. *Map Projections: A Working Manual*. USGS Professional Paper 1395. https://pubs.usgs.gov/publication/pp1395
- Snyder, John P. and Voxland, Philip M. 1989. *An Album of Map Projections*. USGS Professional Paper 1453. https://pubs.usgs.gov/publication/pp1453
- Snyder, John P. 1993. *Flattening the Earth: Two Thousand Years of Map Projections*. University of Chicago Press.
- EPSG Geodetic Parameter Dataset. https://epsg.org ; mirror https://epsg.io
- PROJ documentation, projections and transformations. https://proj.org/en/stable/operations/projections/index.html
- PROJ test suite, builtins.gie. https://github.com/OSGeo/PROJ/blob/master/test/gie/builtins.gie
- spatialreference.org, IAU_2015 list. https://spatialreference.org/ref/iau_2015/
- Butler, H. et al. 2016. RFC 7946, The GeoJSON Format. https://datatracker.ietf.org/doc/html/rfc7946
- OGC 18-010r7 / ISO 19162:2019, WKT for CRS. https://docs.ogc.org/is/18-010r7/18-010r7.html
- NGA. NGA.STND.0039 Web Mercator advisory (2014); DMA TM 8358.2 The Universal Grids; TR8350.2 WGS 84. https://earth-info.nga.mil/
- OpenStreetMap wiki, Slippy map tilenames. https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
- Karney, C. F. F. 2011. Transverse Mercator with an accuracy of a few nanometers. J. Geodesy 85. https://doi.org/10.1007/s00190-011-0445-3
- Karney, C. F. F. 2013. Algorithms for geodesics. J. Geodesy 87. https://doi.org/10.1007/s00190-012-0578-z
- Šavrič, B., Patterson, T., Jenny, B. 2019. The Equal Earth map projection. IJGIS 33(3). https://doi.org/10.1080/13658816.2018.1504949
- Šavrič, B., Jenny, B., White, D., Strebe, D. R. 2016. User preferences / Projection Wizard. https://projectionwizard.org
- Goldberg, D. M. and Gott, J. R. 2007. Flexion and Skewness in Map Projections of the Earth. Cartographica 42(4). https://arxiv.org/abs/astro-ph/0608501
- Archinal, B. A. et al. 2018. Report of the IAU WGCCRE: 2015. Celest. Mech. Dyn. Astr. 130:22. https://doi.org/10.1007/s10569-017-9805-5
- USGS Astrogeology Science Center. https://astrogeology.usgs.gov/
- Calabretta, M. R. and Greisen, E. W. 2002. Representations of celestial coordinates in FITS. A&A 395. https://doi.org/10.1051/0004-6361:20021327
- Ordnance Survey. A guide to coordinate systems in Great Britain. https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf
- GDAL ogr2ogr documentation. https://gdal.org/programs/ogr2ogr.html
- d3-geo documentation. https://d3js.org/d3-geo
