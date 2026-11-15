# Prototype measurements (2026-11-14)

Throwaway prototypes: [prototypes/gen.py](../../prototypes/gen.py) (stdlib) and [prototypes/np_bench.py](../../prototypes/np_bench.py) (numpy comparison). Run: `python prototypes/gen.py 65536 7 out.svg`.

Machine: AMD Ryzen 9 9900X (12 cores, single-threaded runs), Windows 11, Python 3.14.6, numpy 2.5.2. No GPU.

Pipeline: world-keyed jittered grid (splitmix-style integer hash of seed + lattice coords + spacing level), Delaunay as the dual of the jittered grid (each quad split on the in-circle test, so every quad is locally Delaunay; no Bowyer-Watson needed), 14 Voronoi plates (domain-warped), uplift from plate motion toward its boundary, value-noise fbm, Priority-Flood with epsilon from ocean cells, steepest-descent single receiver, accumulation in descending filled height, rivers at acc >= max(20, n/400).

## Times (seconds, stdlib unless noted)

| Stage | 10k cells | 65k cells | numpy 10k | numpy 65k |
|---|---|---|---|---|
| Points + Delaunay mesh | 0.030 | 0.200 | 0.001 (jitter only) | 0.003 (jitter only) |
| Plates + uplift + fbm | 0.435 | 2.975 | 0.020 | 0.073 |
| Priority-Flood (heapq) | 0.003 | 0.032 | n/a (serial) | n/a |
| Flow + accumulation | 0.002 | 0.015 | n/a (serial) | n/a |
| Total generate | 0.47 | 3.23 | | |
| Raster 512^2 + Horn hillshade | 0.58 | 0.74 | 0.016 (hillshade only) | |
| Child zoom (4x density, 1/16 window) | 0.045 (2.5k cells) | 0.43 (16k cells) | | |

Noise evaluation dominates (about 90 percent of generate); the hydrology is cheap. Priority-Flood here only pushes land cells (about 30 percent of the map); expect roughly 3x on an all-land map, still well under a second at 65k. numpy gives about 20-40x on noise and plates and about 35x on hillshade; it is an optional accelerator, not needed at 65k.

## Render

| | 10k | 65k |
|---|---|---|
| SVG size (coast + rivers + 512^2 hillshade PNG via zlib, base64, 3 labels) | 116 KB (PNG b64 79 KB) | 189 KB (PNG b64 91 KB) |
| Render time (stdlib) | 0.59 s | 0.78 s |
| SVG to PNG 1000x1000, headless Chrome `--screenshot` (incl. browser start) | 0.60 s | 0.63 s |

Tools present: Chrome and Edge (headless works), Python playwright 1.63.0 package installed but no browsers downloaded under ms-playwright (use `channel="chrome"` or the Chrome CLI). Not present: QGIS (no Program Files or OSGeo4W install), Inkscape, rsvg-convert, ImageMagick. Nothing was installed.

## Proof bars

| Bar | 10k | 65k | Notes |
|---|---|---|---|
| Every river cell runs strictly downhill (filled height) to the sea | PASS (207 cells, 0 failures) | PASS (534, 0) | lakes are traversed as filled flats with epsilon slope; seed 8 also 0 failures |
| Every river ends in ocean or a lake outlet | PASS (0 without outlet) | PASS (0) | 171 / 1176 lake cells (filled - raw > 1e-3) |
| No splits | PASS | PASS | one receiver per cell by construction; all receivers are mesh neighbours |
| Same seed, byte-identical output | PASS | PASS | sha256 of heights+receivers and of the SVG matched across two processes; `cmp` on the 65k SVGs identical |
| Zoom: child coast within one parent cell of parent coast | PASS (mean 0.11, p95 0.31, max 0.41 parent spacings) | PASS (mean 0.15, p95 0.39, max 0.53) | child = IDW of 3 nearest parent cells + world-keyed noise (amp 0.03); 100 percent of child coast within 1 spacing |

## Caveats

- The uplift rule is crude (plate edges and the map-frame falloff make straight scarps visible in the render); it is a timing stand-in, not the design.
- Zoom inherits heights only. Child rivers (inherit parent paths as constraints, lower threshold) were not prototyped; the deviation bar is coast only.
- Hillshade raster uses nearest-cell lookup, so it shows cell facets at 65k; barycentric interpolation inside the Delaunay triangles is the next step.
- Times are single runs; expect +-10 percent.
