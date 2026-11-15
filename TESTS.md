# Tests: mapwright

Test runs for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and `scripts/mpw.py`. Unit tests live in `tests/`, skill cases in `evals/evals.json` (not run yet). A test passes on evidence, never on a transcript's claim.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per notable result, then `led to:`. Newest first.

## Runs

### T-20261115-3 · 2026-11-15 · unittest (tests/) + space sweep · Windows, Python 3.14 · 131/131 passed, 1 skipped (live) in 28 s
- New (16, tests/test_space.py): sector, real-star, system, planet (all six kinds) and deck bars pass with byte-identical regeneration; forced failures fail their bar (a world cut off from the routes, a jump route labelled long, a star moved 0.01 pc, two planets squeezed together, moons flung out of the Hill sphere, a texture sampled in (u, v) fails both the seam and the pole bar, a room walled off, a lift moved on one deck, the outer airlock door sealed); T5 file read by header in any column order; planet export to PNG with its sphere note.
- Planet tolerances measured on 20 seeds x 6 kinds at 512 px: correct sphere sampling worst seam ratio 1.54 (gas), worst pole ratio 0.375 (ice); (u, v) sampling seam 5 to 20, pole 0.8 to 1.0. Bars set at seam 2.5 x the 90th percentile adjacent-column difference (+0.5 grey level) and pole row std 0.5 x the texture std, width 512 or more. At 256 px the ice pole ratio reached 0.49 (2 of 120 failed at 0.25), so 256 is refused. Crater slope fitted -1.84 to -2.26 for b = 2 (limit 0.35).
- Sweep: 20 seeds x (subsector, sparse subsector jump 1, full sector, system any/M/F, ship, 3-deck ship, station) = 1545 bars, 0 failures; 40 seeds x 4 deck shapes, 0 failures after L-023.
- Timings (generate, then check with regeneration): subsector 0.04 s + 0.05 s; sector 32x40 0.28 s + 0.32 s; real near stars 0.01 s + 0.03 s; system under 0.01 s + 0.04 s; deck 40x21x2 0.03 s + 0.04 s; planet 512 px about 0.9 s (+1 s check), 1024 px about 4.3 s.
- led to: L-021, L-022, L-023

### T-20261115-2 · 2026-11-15 · unittest (tests/) + place sweep · Windows, Python 3.14 · 115/115 passed, 1 skipped (live) in 15 s
- New (17, tests/test_places.py): city, dungeon (bsp, cave) and battle (square, hex) bars pass with byte-identical regeneration; a city from a parent world takes its settlement's name and language and stores `../world`; forced failures fail their bar (an isolated street, a street through the wall, a walled-off room, a loose wall end, a PNG one pixel per square off, a wall outside the image, a door end off a wall, a fractional pixels_per_grid, broken JSON, a label on top of the title); hex with odd pps and Universal VTT for a city or hex map are refused.
- Sweep: 20 seeds x (city, city with sea and river, city without wall, bsp, cave, square battle, hex battle) = 1241 bars; after the fixes in L-019 and L-020, 0 failures; 60 more battle seeds per grid, 0 failures.
- Timings (generate, then check with regeneration): city 6 rings 0.14 s + 0.19 s, 10 rings 0.20 s + 0.37 s; dungeon bsp 48x36 at 70 px 0.06 s + 0.09 s; cave 80x60 at 70 px 0.16 s + 0.21 s; battle 30x20 at 100 px 0.04 s + 0.08 s, 40x30 at 140 px 0.12 s + 0.15 s; hex 30x20 0.01 s + 0.03 s.
- led to: L-018, L-019, L-020

### T-20261115-1 · 2026-11-15 · unittest (tests/) · Windows, Python 3.14 · 98/98 passed, 1 skipped (live) in 13 s
- New (18, tests/test_find.py, network mocked): every catalogue entry and every result of 11 offline queries and of an online query (mocked Nominatim, Commons, LoC) has a licence and a credit; Commons per-file licence and author read from extmetadata; ten rapid Nominatim requests never closer than 1 s apart; the rate holds across two processes through rate.json; 429 reports Retry-After; 14 never-scrape URLs refused with no request made; look-alike hosts not refused; planet and global GEBCO refused; 300 MB Content-Length refused and a stream past the cap stopped with no file left; a second fetch is a cache hit with no request; sources.json and CREDITS.txt hold both sources' credits; an unknown host needs --licence and --credit; the OpenTopography key reaches the request but not sources.json or CREDITS.txt; CLI exits non-zero on a refusal.
- Live smoke (MAPWRIGHT_LIVE=1, one Nominatim request for Reykjavik): passed 2026-11-15.
- led to: L-016, L-017

### T-20261114-4 · 2026-11-14 · unittest (tests/) + tests/roundtrip_trace.py · Windows, Python 3.14.6 · 81/81 in 13 s
- New (20, tests/test_read.py): PNG decoder (RGB round trip, all five filters, RGBA over white, palette at 1 bit, grey at 2 bit, 16 bit); rings with a hole and an island, diagonal pixels kept apart; Douglas-Peucker; thinning to one centre line; affine from 6 exact GCPs recovers the transform within 1e-9 and rms under 1 mm; 3 points flagged as proving nothing, a 0.001 deg error shows as tens of metres, collinear points refused; world file round trip within 1e-9; read without tesseract says "not sure" in text, printed scale, scale, georeference, legend and names; a fake tesseract's TSV gives words, a low-confidence count and the 1:50,000 scale; GCPs write a .pgw and the right metres per pixel; `--answers` gives ok, mismatch, dropped and not sure verdicts and catches a scale bar 50 percent off; trace georeferenced by GCPs and by `--world auto` agree; a coloured river traces to one line; raster round trip bar.
- Round trip, stdlib land raster (topographic, 512 px, no labels), seeds 7, 11, 23 at 4000 cells, distances in raster px (1 px = 1.95 km): recipe coast to traced median 0.26-0.29, p95 0.75-2.96; traced to recipe coast median 0.49-0.52, p95 0.66-0.67. Bar in the unit test: median <= 1 px and p95 <= 4 px both ways.
- Round trip, full headless Chrome render (1000 px, labels, roads, rivers, legend), same seeds, coast plus lake rings: recipe to traced median 0.57-0.61 px, p95 2.98-7.82 px; traced to recipe median 1.06-1.23 px, p95 20.6-47.7 px. The traced-to-recipe tail is real non-water ink (label halos, legend, scale bar, north arrow over the sea), not coast error. Not a unit test: needs a browser.
- Timings: trace of a 512 px raster 0.10-0.17 s; of a 1000 px PNG 0.8-1.2 s; Chrome render 1.1-1.6 s.
- OCR not measured on real maps: tesseract absent on this machine; the OCR path is covered by a fake only.
- led to: L-013, L-014, L-015


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
