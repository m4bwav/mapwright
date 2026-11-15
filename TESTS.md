# Tests: mapwright

Test runs for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and `scripts/mpw.py`. Unit tests live in `tests/`, skill cases in `evals/evals.json` (not run yet). A test passes on evidence, never on a transcript's claim.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per notable result, then `led to:`. Newest first.

## Runs

### T-20261114-3 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6 · 61/61 in 15 s
- New (11): render SVG byte-identical twice in every style, LF only, all layers present; bad style and bad extension refused; river width varies with flow; label bars pass and catch a forced overlap and an edge cut; OCR bar is None (skipped) without tesseract; shipped width table at least as wide as Georgia, Arial, Palatino and Times hmtx for letters, digits and punctuation; legend lists only drawn symbols; style list; serve binds 127.0.0.1, serves page and SVG, 404 elsewhere; sheet by styles and by seeds; PNG (1000 px wide) and PDF through headless Chrome; child map labels pass.
- Timings, `render` seed 7 (Ryzen 9 9900X, stdlib, 512 px raster): 16k cells 0.71-0.86 s, 65k cells 1.05-1.08 s; land raster is 95+ percent of it; placement under 0.02 s. PNG end to end at 65k 2.3 s (browser start included). SVG size 16k: topographic 401 KB, satellite 298 KB, ink-and-parchment 207 KB, atlas 197 KB, star-chart 123 KB, blueprint 110 KB; 65k: topographic 457 KB, ink-and-parchment 259 KB, atlas 252 KB.
- Labels seed 7 at 16k: 78-83 of 140 candidates placed per style, 0 overlaps, 0 edge cuts; the rest (mostly villages in dense clusters) dropped and listed.
- OCR bar not measured: tesseract absent on this machine.
- led to: L-010, L-011, L-012


### T-20261114-2 · 2026-11-14 · unittest (tests/) + generator sweep · Windows, Python 3.14.6 · 35/35 in 1.1 s
- New: Robinson against PROJ builtins.gie (+a=6400000) forward rows within 0.1 mm, inverse rows within 1e-9 deg; gen world folder contents, 16-bit heights.png, all 7 bars pass on a 1600-cell world and its child; same seed byte-identical (8 files), other seed differs; zoom alias; coarse child refused; check exits non-zero on a river made to run uphill.
- Timings, `gen world --seed 7` (Ryzen 9 9900X, stdlib): 16k cells 1.01 s (mesh 0.05, plates+noise 0.22, erosion 0.16, hydrology 0.01, climate 0.04, files+render 0.53); 65k cells 3.54 s (0.20 / 0.92 / 0.86 / 0.08 / 0.16 / 1.33). `gen region` 16k cells 0.77 s; full-window 131k-cell child of a 65k parent 5.5 s.
- Sweep: seeds 1-7 at 16k and 65k, 5 windows each (70 child maps): every bar passed; child coast max 0.841 parent spacings (mean 0.10-0.18), parent rivers in the child max 0.611. World bars on seed 7: 317 river cells / 0 failures, 22 lakes max 1 outlet, 8 files identical, sea-level temp by 10-deg band 24.9/21.3/15.7/10.6/5.6/2.2 C, windward 88 vs leeward 19 cm/yr.
- led to: L-003 (closed), L-004, L-005, L-006

### T-20261114-1 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6 · 24/24 in 0.5 s
- Round trips: GeoJSON to GPX to GeoJSON, GeoJSON to KML to GeoJSON (polygon with hole), GPX to KML to GPX, all within 1e-7 deg (coordinates are written with repr, so they come back exact).
- Shapefile (written by the test: CW outer, CCW hole, DBF NAME field, .prj) to GeoJSON: outer CCW, hole CW, names and CRS read.
- Geodesics: Geoscience Australia's Flinders Peak to Buninyong (GRS80) 54 972.271 m within 1 mm, azimuths within 0.01"; GeographicLib docs' Wellington to Salamanca (WGS84) 19 959 679.267 m within 1 mm, azimuths within 1e-6 deg. Near-antipodal pair falls back with the method stated.
- Area: WGS84 whole-earth 510 065 621.724 km2 within 0.01 km2; authalic radius 6 371 007.181 m.
- Projections, 10-degree grid to +-80 lat: forward then inverse worst error webmercator 1.8e-14, equirectangular 7.1e-15, mollweide 2.3e-13, laea 2.3e-12 (also centred 20E 50N, points within 2000 km of the antipode skipped), robinson 2.8e-14, equalearth 5.7e-14 deg (bar 1e-9).
- Equal-area: Mollweide, LAEA and Equal Earth keep the area ratio of a 10x10 deg equatorial cell to one at 55-65N within 1e-6 (2000 points per edge); Web Mercator misses by more than 50%, as it should.
- led to: L-001, L-002
