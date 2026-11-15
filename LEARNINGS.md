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

### L-006 · 2026-11-14 · Embedded RGB PNG drew blank: width passed as bytes per row
- Trigger: map.svg showed only the sea colour.
- Hypothesis: the PNG width was len(row) of an RGB bytearray, three times the pixel width.
- Rule: for RGB rows pass len(row) // 3; render the SVG once with headless Chrome and look before trusting it.
- Evidence: T-20261114-2
- Scope: skill
