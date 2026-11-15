# Learnings: mapwright

Procedural lessons for [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md). Changes are logged in [CHANGELOG.md](CHANGELOG.md); test runs in [TESTS.md](TESTS.md). Trigger and Hypothesis are required.

## Active

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

### L-006 · 2026-11-14 · Embedded RGB PNG drew blank: width passed as bytes per row
- Trigger: map.svg showed only the sea colour.
- Hypothesis: the PNG width was len(row) of an RGB bytearray, three times the pixel width.
- Rule: for RGB rows pass len(row) // 3; render the SVG once with headless Chrome and look before trusting it.
- Evidence: T-20261114-2
- Scope: skill
