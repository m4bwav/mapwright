# Learnings archive: mapwright

Retired from [LEARNINGS.md](LEARNINGS.md). Each entry keeps its id; the reason is on its first line.

### L-001 · 2026-11-14 · Web Mercator y: use atanh(sin phi), not log(tan(pi/4 + phi/2))
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: `project webmercator 0 0` gave y = -7.1e-10 m with the log-tan form (T-20261114-1).
- Hypothesis: tan(pi/4) is not exactly 1 in float64; atanh(sin 0) is exactly 0.
- Rule: write Mercator y as R * atanh(sin phi).
- Evidence: T-20261114-1
- Scope: skill

### L-002 · 2026-11-14 · GPX reorders features: waypoints, then routes, then tracks
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: the GeoJSON to GPX to GeoJSON round trip came back in a different feature order.
- Hypothesis: the GPX 1.1 schema requires wpt, rte, trk in that order, so the writer groups them.
- Rule: compare round trips by order within each kind, or order fixtures wpt, rte, trk.
- Evidence: T-20261114-1
- Scope: skill

### L-003 · 2026-11-14 · Robinson uses linear interpolation of the 5-degree table
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: design choice in 0.1.0 for a cheap Robinson with an exact inverse.
- Hypothesis: PROJ uses cubic-spline interpolation; linear gives slightly kinked meridians at 5-degree rows (unverified visually).
- Rule: before Robinson is used for a drawn world map, compare against PROJ's values and switch to the spline if the kinks show.
- Evidence: none yet
- 2026-11-14 closed: switched to PROJ's spline coefficients (robin.cpp). PROJ declares them as C floats; with double values y missed builtins.gie by 3 mm, rounded to float32 it matches to 4e-7 m. The float32 table does not meet exactly at the 5-degree nodes, so forward-then-inverse misses by up to 2e-5 deg there, in PROJ too; the round-trip bar for Robinson is 5e-5 deg (T-20261114-2).
- Scope: skill

### L-004 · 2026-11-14 · Priority-Flood lakes can get two outlets; fix by re-treeing, then lift
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: after re-treeing lakes with 1e-9 steps, 113 river cells failed the downhill bar (mesh.json rounds to 9 decimals), and some lakes had two spill points.
- Hypothesis: a flooded flat can be entered from two spills at near-equal levels; tiny epsilons vanish in rounding.
- Rule: inside raised flats route along the flood's push parent; give a lake with more than one exit a BFS tree to its lowest exit; then walk the receiver tree up from the sea and lift each cell to at least receiver + 1e-7. Never add epsilons smaller than the stored precision.
- Evidence: T-20261114-2
- Scope: skill

### L-005 · 2026-11-14 · Child coast drifts past 1 parent spacing where parent heights are near 0
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: the zoom bar failed (max 1.1-2.3 parent spacings) on flat low coasts and one-cell inland seas; detail noise and 3-nearest IDW put the zero line on the other side of a parent cell from the parent's linear coast.
- Hypothesis: the parent's coast is the zero line of its triangle surface, not of the IDW field.
- Rule: take each child cell's land/sea side from the parent's barycentric surface; let noise flip it only within a band of the parent coast, band = max(0, 0.8 parent spacing - 1.2 child spacing). Scale the detail amplitude with parent spacing.
- Evidence: T-20261114-2 (70 child maps, max 0.841)
- Scope: skill

### L-006 · 2026-11-14 · Embedded RGB PNG drew blank: width passed as bytes per row
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: map.svg showed only the sea colour.
- Hypothesis: the PNG width was len(row) of an RGB bytearray, three times the pixel width.
- Rule: for RGB rows pass len(row) // 3; render the SVG once with headless Chrome and look before trusting it.
- Evidence: T-20261114-2
- Scope: skill

### L-007 · 2026-11-14 · A child map floods parent settlements into new lakes and sea
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: bar 13 failed in a 20-seed sweep: parent settlements sat up to 38 km (2.4 parent spacings) inside a lake the finer child surface made, and parent road vertices snapped onto 2-cell islets in a child inlet.
- Hypothesis: settlements score high on lake shores and coasts, and the child's IDW plus detail noise fills shore valleys and shifts the coast inside its band.
- Rule: before child hydrology, lift child cells under parent settlements and sampled parent road points to just above sea level; after it, lift any of them a new lake covers to lake level + 1e-4 and route again (up to 3 passes). Snap within 1 parent + 1 child spacing; a road piece that crosses into another child landmass starts a new piece instead of dropping the road.
- Evidence: 20 seeds x 5 maps at 4k cells and 4 seeds at 16k: bar 13 max shift 3 km, road points max 3 km.
- Scope: skill

### L-008 · 2026-11-14 · Name and road layers must run on the rounded mesh
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: design: check and child maps rebuild sea, land, range and river-stem ids from mesh.json to match parent names by id.
- Hypothesis: build_mesh neighbours come from unrounded points; mesh.json stores 6 decimals, so a near-cocircular quad can flip and component ids could differ.
- Rule: build the human layer from the mesh dict as written (rounded values, _neighbours), never from the in-memory arrays.
- Evidence: bars 11 and 13 pass across the sweeps.
- Scope: skill

### L-011 · 2026-11-14 · The width table must be wider than the fonts the stacks name
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: first table had Georgia Italic 'r' (0.461 em) and Verdana '.' above the table value.
- Hypothesis: a too-narrow estimate lets drawn text overflow its collision box, so labels touch while the bar passes.
- Rule: keep em_width at or above every font in the style stacks; a test compares it with system TTF hmtx (Georgia, Arial, Palatino, Times) and skips where none exist. For monospace styles use a fixed 0.62 em.
- Evidence: T-20261114-3
- Scope: skill

### L-013 · 2026-11-14 · A 3x3 majority filter rounds square corners
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: a traced 20x20 square came back with corners cut (x 1.1 and 2.9 instead of 1 and 3) after `clean` with "5 of 9".
- Hypothesis: a corner pixel has only 4 set in its 3x3, so a plain majority clears it.
- Rule: vote with hysteresis: 6+ sets, 3 or fewer clears, otherwise keep. Specks and one-pixel strokes still go.
- Evidence: T-20261114-4
- Scope: script

### L-014 · 2026-11-14 · Filling small holes in a water mask also fills small islands
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: `--fill-holes 2000` cut label-halo noise on a full render but pushed recipe-to-traced p95 from 3 px to 19 px.
- Hypothesis: an island is a hole in the water polygon, the same shape as a label box.
- Rule: keep `--fill-holes` at 0 by default; state that label, legend and scale boxes over the sea show as holes.
- Evidence: T-20261114-4
- Scope: script

### L-015 · 2026-11-14 · Lakes are vector overlays, not in the land raster
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: tracing the stdlib land raster gave recipe-to-traced p95 of 46 px when lake rings were in the reference.
- Hypothesis: `land_rows` paints only z < 0 as sea; lakes are drawn later as SVG paths.
- Rule: compare a raster trace with coast lines only; compare a full browser render with coast plus lakes.
- Evidence: T-20261114-4
- Scope: tests

### L-016 · 2026-11-15 · An API key in a URL leaks into the cache name and the credit files
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: OpenTopography takes its key as a query parameter, so the natural URL to cache and record holds the key.
- Hypothesis: anything keyed on the full URL (cache hash, sources.json, CREDITS.txt) would store the secret.
- Rule: add the key only to the outgoing request; strip key-like parameters (api_key, key, token) before hashing or recording. A test checks the files.

### L-017 · 2026-11-15 · A rate limit kept in memory resets every run
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: Nominatim's 1 request per second covers the application, but each `mpw.py` call is a new process.
- Hypothesis: back-to-back CLI calls would each send at once and break the policy.
- Rule: keep the last request time per source in the cache folder (rate.json) and wait against it. A test runs two Http objects on one clock.

### L-018 · 2026-11-15 · Recursive lot cuts strand inner lots without a street
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: first city check: 891 of 1001 lots had no edge on the block boundary.
- Hypothesis: cutting across the long axis again and again leaves middle pieces whose every side is a cut.
- Rule: keep a cut only when both halves still have an edge on the block boundary; try the other axis, else stop splitting. The bar measures frontage from the stored lots, with 0.02 m tolerance for 2-decimal coordinates.
- Evidence: T-20261115-2
- Scope: skill

### L-019 · 2026-11-15 · A straight chord between far-apart ring nodes cuts through the wall
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: the wall bar found 4 to 10 streets crossing the wall; the ring outside the wall has only gate nodes, 60 degrees apart, and its chords dip inside.
- Hypothesis: a chord at radius r spanning angle a sits r cos(a/2) from the centre.
- Rule: draw ring streets, block sides and the wall as arcs with a point every 7.5 degrees. Count a crossing only when segments properly cross; a street ending on the wall is not a crossing.
- Evidence: T-20261115-2
- Scope: skill

### L-023 · 2026-11-15 · `hull-needs-a-space-row`: a hull that fills the grid leaves no outside for the airlock
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: every 16x11 deck failed with no airlock: the hull reached row 1, its wall row 0, and the outer door had no space square beyond it.
- Hypothesis: the half-beam was (H - 3) // 2, which leaves a wall row but no row of space.
- Rule: keep one row of space beyond the hull wall on each side ((H - 5) // 2); the airlock bar checks the outer door opens onto a space square.
- Evidence: T-20261115-3
- Scope: skill

### L-025 · 2026-11-15 · `sidecar-rounding-eats-the-step`: a scale written with too few digits breaks the read-back
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: heightmaps read back through their own sidecar missed the half-step bar by 0.0002 m.
- Hypothesis: metres per step rounded to 8 decimals is multiplied by up to 65535 on the way back, and min_m rounded to 4 decimals adds its own error.
- Rule: write metres_per_step with 12 decimals and min_m and max_m with 6; the test reads the file with the sidecar's numbers only, never the exporter's variables.
- Evidence: T-20261115-4
- Scope: skill

### L-027 · 2026-11-15 · `uvtt-alpha-first-closed-doors`: Universal VTT colours are AARRGGBB and an open portal is a window
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: source pass 3 read the Foundry importer: it drops the first two characters of a colour, reads `closed: false` as a window, and builds its own door wall from a portal's bounds.
- Hypothesis: a colour written RRGGBBAA still parses and only looks wrong in play, and an open door or a wall left under a door loads without any error.
- Rule: write `ffRRGGBB`, `closed: true` for every door, and leave the wall gap at each portal; `uvtt_bars` checks all three on dungeon, battle and deck exports.
- Evidence: T-20261115-4 (the 0.5.0 exports already met all three; the bar now fails each forced break)
- Scope: skill

### L-036 · 2026-11-15 · `h-is-taken`: a heuristic method named h shadowed the grid height
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: the first `path` run died with "'int' object is not callable" on G.h(...).
- Hypothesis: the graph classes store the grid height as self.h, which hides a method of the same name.
- Rule: never give a method a one-letter name a map class may also use for a size (w, h, x, y); the estimate is `est`.
- Evidence: T-20261115-7
- Scope: skill

### L-037 · 2026-11-15 · `tobler-flat-is-5-0367`: Tobler on the flat is 5.036742 km/h, not 5.037
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: a flat-leg test against d / 5.0374 failed by 1.6e-4 h.
- Hypothesis: 6 exp(-0.175) = 5.036742; 5.037 and 5.04 are that number rounded, so a 1e-6 bar against d / 5.037 cannot hold.
- Rule: test travel times against the formula (`TOBLER_FLAT`), and the published table only to its 0.01 km/h.
- Evidence: T-20261115-7
- Scope: skill

### L-040 · 2026-11-15 · `grid-map-title-ignored`: render --title did nothing on city, dungeon and battle maps
- Archived: enforced by tests or code (consolidation 2026-11-16, C-20261116-3).
- Trigger: `render DIR --title "The Sunken Vault"` still showed the generated name.
- Hypothesis: cmd_render sent places kinds to mpw_places.render_svg without the title.
- Rule: fixed in 0.10.1 (title replaces the recipe name in the label); space kinds now warn on stderr that --title is unused. The gen's map.png on grid maps is the unlabelled VTT image: render a labelled copy to another file.
- Evidence: tests/test_places.py test_cli_gen_check_render
- Scope: skill

### L-022 · 2026-11-15 · `seam-bar-needs-a-percentile`: compare the seam with the 90th percentile, not the median
- Archived: merged into L-021 (2026-11-16, C-20261116-3).
- Trigger: a gas giant with smooth bands failed the seam bar at 1.5 x the median adjacent-column difference while its seam was continuous.
- Hypothesis: most columns of a banded texture barely change, so the median is near zero, while a storm or crater crossing the seam makes one column pair as large as any interior pair with a feature.
- Rule: compare the seam with the 90th percentile of interior adjacent-column differences (2.5 x, +0.5 grey level); a (u, v) sampled texture still fails it by 5 to 20 times.
- Evidence: T-20261115-3
- Scope: skill

### L-031 · 2026-11-15 · `line-test-needs-the-clean-render`: a bare contrast test finds lines everywhere
- Archived: merged into L-010 (2026-11-16, C-20261116-3).
- Trigger: "is there a line here" fired on 22 to 33 percent of places with no river on the clean render (biome patches, hillshade).
- Hypothesis: contrast with both sides is common in a textured picture; a river is contrast in one colour direction at a known place.
- Rule: take the centre-minus-sides colour vector from the clean render at each river sample and count the river kept when the styled picture keeps a third of it in that direction. Always report the noise floor from the same test where the recipe has no line (means by look: 0.01 to 0.04 on ink and watercolour, 0.09 to 0.26 on atlas and satellite), and keep the number out of the bar.
- Evidence: T-20261115-5
- Scope: skill

### L-033 · 2026-11-15 · `gate-on-a-recipe-key`: key new generator behaviour on a recipe field old recipes lack
- Archived: merged into L-020 (2026-11-16, C-20261116-3).
- Trigger: adding a goal, wall cleanup and a new entrance to `gen dungeon` would change every file a 0.7.0 recipe regenerates.
- Hypothesis: a version-string comparison breaks when tests call the generator with its default version, and a new flag default that changes the draw order breaks the old seed (L-020).
- Rule: new behaviour runs only when the recipe carries the new key (`params.goal`); `regenerate` passes `legacy=True` without it. New flags default to the old behaviour draw for draw (the cave border test keeps its short-circuit, so border squares draw nothing). Keep a fixture written by the old release and run `check` on it.
- Evidence: T-20261115-6 (both 0.7.0 fixtures byte-identical; the cave defaults redraw the 0.7.0 cave cell for cell)
- Scope: skill

