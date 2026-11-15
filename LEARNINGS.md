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
- Scope: skill
