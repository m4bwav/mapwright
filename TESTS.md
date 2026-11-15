# Tests: mapwright

Test runs for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and `scripts/mpw.py`. Unit tests live in `tests/`, skill cases in `evals/evals.json` (not run yet). A test passes on evidence, never on a transcript's claim.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per notable result, then `led to:`. Newest first.

## Runs

### T-20261114-1 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6 · 24/24 in 0.5 s
- Round trips: GeoJSON to GPX to GeoJSON, GeoJSON to KML to GeoJSON (polygon with hole), GPX to KML to GPX, all within 1e-7 deg (coordinates are written with repr, so they come back exact).
- Shapefile (written by the test: CW outer, CCW hole, DBF NAME field, .prj) to GeoJSON: outer CCW, hole CW, names and CRS read.
- Geodesics: Geoscience Australia's Flinders Peak to Buninyong (GRS80) 54 972.271 m within 1 mm, azimuths within 0.01"; GeographicLib docs' Wellington to Salamanca (WGS84) 19 959 679.267 m within 1 mm, azimuths within 1e-6 deg. Near-antipodal pair falls back with the method stated.
- Area: WGS84 whole-earth 510 065 621.724 km2 within 0.01 km2; authalic radius 6 371 007.181 m.
- Projections, 10-degree grid to +-80 lat: forward then inverse worst error webmercator 1.8e-14, equirectangular 7.1e-15, mollweide 2.3e-13, laea 2.3e-12 (also centred 20E 50N, points within 2000 km of the antipode skipped), robinson 2.8e-14, equalearth 5.7e-14 deg (bar 1e-9).
- Equal-area: Mollweide, LAEA and Equal Earth keep the area ratio of a 10x10 deg equatorial cell to one at 55-65N within 1e-6 (2000 points per edge); Web Mercator misses by more than 50%, as it should.
- led to: L-001, L-002
