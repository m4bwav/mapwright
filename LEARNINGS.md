# Learnings: mapwright

Procedural lessons for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md). Changes are logged in [CHANGELOG.md](CHANGELOG.md); test runs in [TESTS.md](TESTS.md). Trigger and Hypothesis are required.

## Active

### L-018 · 2026-11-15 · Recursive lot cuts strand inner lots without a street
- Trigger: first city check: 891 of 1001 lots had no edge on the block boundary.
- Hypothesis: cutting across the long axis again and again leaves middle pieces whose every side is a cut.
- Rule: keep a cut only when both halves still have an edge on the block boundary; try the other axis, else stop splitting. The bar measures frontage from the stored lots, with 0.02 m tolerance for 2-decimal coordinates.
- Evidence: T-20261115-2
- Scope: skill

### L-019 · 2026-11-15 · A straight chord between far-apart ring nodes cuts through the wall
- Trigger: the wall bar found 4 to 10 streets crossing the wall; the ring outside the wall has only gate nodes, 60 degrees apart, and its chords dip inside.
- Hypothesis: a chord at radius r spanning angle a sits r cos(a/2) from the centre.
- Rule: draw ring streets, block sides and the wall as arcs with a point every 7.5 degrees. Count a crossing only when segments properly cross; a street ending on the wall is not a crossing.
- Evidence: T-20261115-2
- Scope: skill

### L-020 · 2026-11-15 · A replayed parameter must not skip a random draw
- Trigger: regeneration of a city differed in features, names and map.svg.
- Hypothesis: `spokes or rng.randint(...)` drew a number only when spokes was unset; the recipe stores the drawn value, so the replay skipped the draw and every later number shifted.
- Rule: always draw, then override with the stored or given value. Same for battle maps: 'touches the map edge' is not one region; keep the largest edge region and fill the rest, or the entrance can sit in a cut-off strip.
- Evidence: T-20261115-2
- Scope: skill

### L-016 · 2026-11-15 · An API key in a URL leaks into the cache name and the credit files
- Trigger: OpenTopography takes its key as a query parameter, so the natural URL to cache and record holds the key.
- Hypothesis: anything keyed on the full URL (cache hash, sources.json, CREDITS.txt) would store the secret.
- Rule: add the key only to the outgoing request; strip key-like parameters (api_key, key, token) before hashing or recording. A test checks the files.

### L-017 · 2026-11-15 · A rate limit kept in memory resets every run
- Trigger: Nominatim's 1 request per second covers the application, but each `mpw.py` call is a new process.
- Hypothesis: back-to-back CLI calls would each send at once and break the policy.
- Rule: keep the last request time per source in the cache folder (rate.json) and wait against it. A test runs two Http objects on one clock.

### L-013 · 2026-11-14 · A 3x3 majority filter rounds square corners
- Trigger: a traced 20x20 square came back with corners cut (x 1.1 and 2.9 instead of 1 and 3) after `clean` with "5 of 9".
- Hypothesis: a corner pixel has only 4 set in its 3x3, so a plain majority clears it.
- Rule: vote with hysteresis: 6+ sets, 3 or fewer clears, otherwise keep. Specks and one-pixel strokes still go.
- Evidence: T-20261114-4
- Scope: script

### L-014 · 2026-11-14 · Filling small holes in a water mask also fills small islands
- Trigger: `--fill-holes 2000` cut label-halo noise on a full render but pushed recipe-to-traced p95 from 3 px to 19 px.
- Hypothesis: an island is a hole in the water polygon, the same shape as a label box.
- Rule: keep `--fill-holes` at 0 by default; state that label, legend and scale boxes over the sea show as holes.
- Evidence: T-20261114-4
- Scope: script

### L-015 · 2026-11-14 · Lakes are vector overlays, not in the land raster
- Trigger: tracing the stdlib land raster gave recipe-to-traced p95 of 46 px when lake rings were in the reference.
- Hypothesis: `land_rows` paints only z < 0 as sea; lakes are drawn later as SVG paths.
- Rule: compare a raster trace with coast lines only; compare a full browser render with coast plus lakes.
- Evidence: T-20261114-4
- Scope: tests


### L-001 · 2026-11-14 · Web Mercator y: use atanh(sin phi), not log(tan(pi/4 + phi/2))
- Trigger: `project webmercator 0 0` gave y = -7.1e-10 m with the log-tan form (T-20261114-1).
- Hypothesis: tan(pi/4) is not exactly 1 in float64; atanh(sin 0) is exactly 0.
- Rule: write Mercator y as R * atanh(sin phi).
- Evidence: T-20261114-1
- Scope: skill

### L-002 · 2026-11-14 · GPX reorders features: waypoints, then routes, then tracks
- Trigger: the GeoJSON to GPX to GeoJSON round trip came back in a different feature order.
- Hypothesis: the GPX 1.1 schema requires wpt, rte, trk in that order, so the writer groups them.
- Rule: compare round trips by order within each kind, or order fixtures wpt, rte, trk.
- Evidence: T-20261114-1
- Scope: skill

### L-003 · 2026-11-14 · Robinson uses linear interpolation of the 5-degree table
- Trigger: design choice in 0.1.0 for a cheap Robinson with an exact inverse.
- Hypothesis: PROJ uses cubic-spline interpolation; linear gives slightly kinked meridians at 5-degree rows (unverified visually).
- Rule: before Robinson is used for a drawn world map, compare against PROJ's values and switch to the spline if the kinks show.
- Evidence: none yet
- 2026-11-14 closed: switched to PROJ's spline coefficients (robin.cpp). PROJ declares them as C floats; with double values y missed builtins.gie by 3 mm, rounded to float32 it matches to 4e-7 m. The float32 table does not meet exactly at the 5-degree nodes, so forward-then-inverse misses by up to 2e-5 deg there, in PROJ too; the round-trip bar for Robinson is 5e-5 deg (T-20261114-2).
- Scope: skill

### L-004 · 2026-11-14 · Priority-Flood lakes can get two outlets; fix by re-treeing, then lift
- Trigger: after re-treeing lakes with 1e-9 steps, 113 river cells failed the downhill bar (mesh.json rounds to 9 decimals), and some lakes had two spill points.
- Hypothesis: a flooded flat can be entered from two spills at near-equal levels; tiny epsilons vanish in rounding.
- Rule: inside raised flats route along the flood's push parent; give a lake with more than one exit a BFS tree to its lowest exit; then walk the receiver tree up from the sea and lift each cell to at least receiver + 1e-7. Never add epsilons smaller than the stored precision.
- Evidence: T-20261114-2
- Scope: skill

### L-005 · 2026-11-14 · Child coast drifts past 1 parent spacing where parent heights are near 0
- Trigger: the zoom bar failed (max 1.1-2.3 parent spacings) on flat low coasts and one-cell inland seas; detail noise and 3-nearest IDW put the zero line on the other side of a parent cell from the parent's linear coast.
- Hypothesis: the parent's coast is the zero line of its triangle surface, not of the IDW field.
- Rule: take each child cell's land/sea side from the parent's barycentric surface; let noise flip it only within a band of the parent coast, band = max(0, 0.8 parent spacing - 1.2 child spacing). Scale the detail amplitude with parent spacing.
- Evidence: T-20261114-2 (70 child maps, max 0.841)
- Scope: skill

### L-007 · 2026-11-14 · A child map floods parent settlements into new lakes and sea
- Trigger: bar 13 failed in a 20-seed sweep: parent settlements sat up to 38 km (2.4 parent spacings) inside a lake the finer child surface made, and parent road vertices snapped onto 2-cell islets in a child inlet.
- Hypothesis: settlements score high on lake shores and coasts, and the child's IDW plus detail noise fills shore valleys and shifts the coast inside its band.
- Rule: before child hydrology, lift child cells under parent settlements and sampled parent road points to just above sea level; after it, lift any of them a new lake covers to lake level + 1e-4 and route again (up to 3 passes). Snap within 1 parent + 1 child spacing; a road piece that crosses into another child landmass starts a new piece instead of dropping the road.
- Evidence: 20 seeds x 5 maps at 4k cells and 4 seeds at 16k: bar 13 max shift 3 km, road points max 3 km.
- Scope: skill

### L-008 · 2026-11-14 · Name and road layers must run on the rounded mesh
- Trigger: design: check and child maps rebuild sea, land, range and river-stem ids from mesh.json to match parent names by id.
- Hypothesis: build_mesh neighbours come from unrounded points; mesh.json stores 6 decimals, so a near-cocircular quad can flip and component ids could differ.
- Rule: build the human layer from the mesh dict as written (rounded values, _neighbours), never from the in-memory arrays.
- Evidence: bars 11 and 13 pass across the sweeps.
- Scope: skill

### L-009 · 2026-11-14 · Open: grandchild of a landlocked window fails bar 1; arid windows sit on bar 7's sample limit
- Trigger: sweep: a grandchild whose window holds no sea fails bar 1 for every river cell (origin/main does the same, so it predates D.3). One arid child had exactly 20 windward samples after the causeway lift, so bar 7 judged a 4.9 vs 5.2 cm/yr desert and failed; before, it had 19 and was skipped.
- Hypothesis: Priority-Flood in a region seeds only from sea cells, so with no sea nothing drains; bar 7 has no margin at its 20-sample floor.
- Rule: open. Fix region hydrology to drain through the window edge, and give bar 7 a minimum precipitation difference or sample size measured on a sweep, written in TESTS.md before changing it.
- Evidence: scratch sweep 2026-11-14
- Scope: skill

### L-010 · 2026-11-14 · A label bar that reuses the placer's own boxes proves nothing
- Trigger: design of the `check` label bars.
- Hypothesis: if check reads the boxes the placer kept, a placer bug passes its own test.
- Rule: measure labels back from the rendered SVG's attributes (x, y, size, anchor, rotate, letter-spacing) with the width table, and test overlaps and edges on those boxes. Tests force an overlap and an edge cut into an SVG to prove the bar fails.
- Evidence: T-20261114-3
- Scope: skill

### L-011 · 2026-11-14 · The width table must be wider than the fonts the stacks name
- Trigger: first table had Georgia Italic 'r' (0.461 em) and Verdana '.' above the table value.
- Hypothesis: a too-narrow estimate lets drawn text overflow its collision box, so labels touch while the bar passes.
- Rule: keep em_width at or above every font in the style stacks; a test compares it with system TTF hmtx (Georgia, Arial, Palatino, Times) and skips where none exist. For monospace styles use a fixed 0.62 em.
- Evidence: T-20261114-3
- Scope: skill

### L-012 · 2026-11-14 · Monospace labels look garbled when a sheet scales a map down
- Trigger: blueprint labels in a 480 px sheet cell read as noise; at full size they are clean.
- Hypothesis: Courier New strokes and the 2.5 px halo collapse below about 6 px text.
- Rule: judge a style from a full-size render, not from a sheet thumbnail; an OCR bar must run on the full-size PNG.
- Evidence: scratch renders 2026-11-14
- Scope: skill

### L-021 · 2026-11-15 · `pole-row-scales-with-width`: a pole bar must name its resolution
- Trigger: sweep: the pole bar (top row std vs texture std) failed 2 of 120 textures at 256 px and passed all at 512.
- Hypothesis: with pixel centres the top row is a circle about pi equator pixels round, so its spread is the texture's local detail at that scale; a sharp feature (an ice crack, a crater rim) crossing the pole raises it, more so at low width.
- Rule: state the width the pole tolerance was measured at and refuse narrower textures; set the limit between the worst correct texture and the best wrong (u, v) one, both measured.
- Evidence: T-20261115-3
- Scope: skill

### L-022 · 2026-11-15 · `seam-bar-needs-a-percentile`: compare the seam with the 90th percentile, not the median
- Trigger: a gas giant with smooth bands failed the seam bar at 1.5 x the median adjacent-column difference while its seam was continuous.
- Hypothesis: most columns of a banded texture barely change, so the median is near zero, while a storm or crater crossing the seam makes one column pair as large as any interior pair with a feature.
- Rule: compare the seam with the 90th percentile of interior adjacent-column differences (2.5 x, +0.5 grey level); a (u, v) sampled texture still fails it by 5 to 20 times.
- Evidence: T-20261115-3
- Scope: skill

### L-023 · 2026-11-15 · `hull-needs-a-space-row`: a hull that fills the grid leaves no outside for the airlock
- Trigger: every 16x11 deck failed with no airlock: the hull reached row 1, its wall row 0, and the outer door had no space square beyond it.
- Hypothesis: the half-beam was (H - 3) // 2, which leaves a wall row but no row of space.
- Rule: keep one row of space beyond the hull wall on each side ((H - 5) // 2); the airlock bar checks the outer door opens onto a space square.
- Evidence: T-20261115-3
- Scope: skill

### L-024 · 2026-11-15 · `chrome-rounds-pdf-page`: a browser PDF page is rounded, so cut the box back yourself
- Trigger: the print bar failed on A3 (MediaBox 841.92 x 1191.12 pt for 841.89 x 1190.55, off 0.57 pt) and A5 with bleed (0.505 pt), and the drawing lost up to one CSS pixel on its right and bottom edges.
- Hypothesis: headless Chrome rounds an `@page` size to whole points, then to 1/300 inch, and lays the page out on a viewport floored to whole CSS pixels, so the page is neither the size asked for nor always as large as the drawing.
- Rule: ask for a page 2 pt larger than needed, then set MediaBox (and BleedBox, TrimBox) to the drawing's rectangle, which hangs from the page's top-left corner, with an incremental update appended to the file; never edit the browser's bytes in place.
- Evidence: T-20261115-4 (60 PDFs, worst difference 0.0001 pt; pypdf, PyMuPDF, mutool and poppler read the update)
- Scope: skill

### L-025 · 2026-11-15 · `sidecar-rounding-eats-the-step`: a scale written with too few digits breaks the read-back
- Trigger: heightmaps read back through their own sidecar missed the half-step bar by 0.0002 m.
- Hypothesis: metres per step rounded to 8 decimals is multiplied by up to 65535 on the way back, and min_m rounded to 4 decimals adds its own error.
- Rule: write metres_per_step with 12 decimals and min_m and max_m with 6; the test reads the file with the sidecar's numbers only, never the exporter's variables.
- Evidence: T-20261115-4
- Scope: skill

### L-026 · 2026-11-15 · `hex-has-no-uvtt`: skip the hex Universal VTT export, it has no honest form
- Trigger: the open item "hex battle maps to VTT" from Step D.7.
- Hypothesis: a .dd2vtt holds one `pixels_per_grid` number for a square grid and no grid type, so an importer would lay squares over the hexes and every wall and door would sit on the wrong cell.
- Rule: refuse hex with the reason and send it to `export --to png` (same canvas as map.svg). Tiled's hexagonal orientation (staggeraxis y, staggerindex odd) is the honest hex target and is not built yet.
- Evidence: T-20261115-4
- Scope: skill

### L-027 · 2026-11-15 · `uvtt-alpha-first-closed-doors`: Universal VTT colours are AARRGGBB and an open portal is a window
- Trigger: source pass 3 read the Foundry importer: it drops the first two characters of a colour, reads `closed: false` as a window, and builds its own door wall from a portal's bounds.
- Hypothesis: a colour written RRGGBBAA still parses and only looks wrong in play, and an open door or a wall left under a door loads without any error.
- Rule: write `ffRRGGBB`, `closed: true` for every door, and leave the wall gap at each portal; `uvtt_bars` checks all three on dungeon, battle and deck exports.
- Evidence: T-20261115-4 (the 0.5.0 exports already met all three; the bar now fails each forced break)
- Scope: skill

### L-028 · 2026-11-15 · `thin-water-does-not-survive-img2img`: redraw lakes and rivers in code after the pass
- Trigger: first style passes kept the coast and painted over the rivers and the largest lake.
- Hypothesis: a 1 to 3 px line and a small flat patch are texture to the model; even a light repaint replaces them.
- Rule: lakes and rivers go in the code-set layer on top of the styled picture with roads, symbols and labels, and are left out of the land IoU. Measured share the model alone kept: river lines 0.51 to 0.78 at denoise 0.35, 0.39 to 0.54 at 0.45, 0.18 to 0.34 at 0.55; lakes 0.09 to 0.76 at 0.45 (means by look, two worlds pooled).
- Evidence: T-20261115-5
- Scope: skill

### L-029 · 2026-11-15 · `denoise-on-the-step-grid`: the denoise typed is not the denoise that runs
- Trigger: the 0.55 and 0.65 columns of the grid ran further from the render than their names.
- Hypothesis: below 1, KSampler takes `steps` steps from the tail of an int(steps / d) step schedule, so the run value is steps / int(steps / d).
- Rule: at 9 steps 0.35 runs as 0.36, 0.45 as 0.45, 0.55 as 0.5625, 0.65 as 0.692. Record both in the sidecar and state a ceiling as the typed value with its run value.
- Evidence: T-20261115-5
- Scope: skill

### L-030 · 2026-11-15 · `fixed-colour-rules-miss-parchment`: train the land and sea colours on each picture
- Trigger: the fixed water rule of `read` (blue clearly above red) gave a land IoU of 0.26 to 0.41 on the clean ink-and-parchment render, where sea and land are both tan.
- Hypothesis: a style changes what colour the sea is; only the picture itself knows.
- Rule: build a colour table per picture from pixels at least 12 px from the true coast (15-bit buckets, coarser buckets for unseen colours), apply it to every pixel, clean with a 3x3 close and open. The band where a coast can drift is never used for training. On blue-sea looks it agrees with the fixed rule within 0.02 at denoise 0.45 and below.
- Evidence: T-20261115-5
- Scope: skill

### L-031 · 2026-11-15 · `line-test-needs-the-clean-render`: a bare contrast test finds lines everywhere
- Trigger: "is there a line here" fired on 22 to 33 percent of places with no river on the clean render (biome patches, hillshade).
- Hypothesis: contrast with both sides is common in a textured picture; a river is contrast in one colour direction at a known place.
- Rule: take the centre-minus-sides colour vector from the clean render at each river sample and count the river kept when the styled picture keeps a third of it in that direction. Always report the noise floor from the same test where the recipe has no line (means by look: 0.01 to 0.04 on ink and watercolour, 0.09 to 0.26 on atlas and satellite), and keep the number out of the bar.
- Evidence: T-20261115-5
- Scope: skill

### L-032 · 2026-11-15 · `the-look-arrives-after-the-coast-leaves`: img2img alone gives a light repaint inside the bar
- Trigger: the pictures that look most painted (denoise 0.65) failed every bar; the ones that pass (0.45 and below) sit close to the code render.
- Hypothesis: with only the init image holding it, the model trades geometry for style one for one.
- Rule: default and ceiling denoise 0.45; never raise it for a stronger look. A stronger look needs a second hold on the coast (a canny or depth control image drawn from the geometry), which is not built yet.
- Evidence: T-20261115-5
- Scope: skill

### L-033 · 2026-11-15 · `gate-on-a-recipe-key`: key new generator behaviour on a recipe field old recipes lack
- Trigger: adding a goal, wall cleanup and a new entrance to `gen dungeon` would change every file a 0.7.0 recipe regenerates.
- Hypothesis: a version-string comparison breaks when tests call the generator with its default version, and a new flag default that changes the draw order breaks the old seed (L-020).
- Rule: new behaviour runs only when the recipe carries the new key (`params.goal`); `regenerate` passes `legacy=True` without it. New flags default to the old behaviour draw for draw (the cave border test keeps its short-circuit, so border squares draw nothing). Keep a fixture written by the old release and run `check` on it.
- Evidence: T-20261115-6 (both 0.7.0 fixtures byte-identical; the cave defaults redraw the 0.7.0 cave cell for cell)
- Scope: skill

### L-034 · 2026-11-15 · `squares-forget-one-way`: a square BFS walks through a one-way door both ways
- Trigger: the first cyclic map passed every graph bar but the square-level gate bar found the goal reachable with the lock shut.
- Hypothesis: the route ran up the valve from the key to the goal; squares carry no direction, so the gate looked open.
- Rule: any square walk over a cyclic map uses `door_dist`, which lets a one-way door be entered only from its source side and a locked door only with the key. Measure the cyclic path as the completion walk (entrance to key, key to goal), not the plain shortest path.
- Evidence: T-20261115-6
- Scope: skill

### L-035 · 2026-11-15 · `corridor-means-no-2x2`: a corridor square is one in no 2x2 open block
- Trigger: the first range run gave bsp a dead-end share of 0 on all 500 maps and counted room corners as corridors.
- Hypothesis: peeling one-neighbour squares stops at any room three squares wide, and a two-neighbour rule catches every room corner.
- Rule: corridor squares are those in no 2x2 open block; dead-end share counts the parts that hang off a single bridge. Check a new metric on a hand-drawn ring and a room-with-stub before trusting a sweep.
- Evidence: T-20261115-6 (the ring scores loop 1, dead end 0; the stub scores loop 0)
- Scope: skill

### L-006 · 2026-11-14 · Embedded RGB PNG drew blank: width passed as bytes per row
- Trigger: map.svg showed only the sea colour.
- Hypothesis: the PNG width was len(row) of an RGB bytearray, three times the pixel width.
- Rule: for RGB rows pass len(row) // 3; render the SVG once with headless Chrome and look before trusting it.
- Evidence: T-20261114-2
- Scope: skill
