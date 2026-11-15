# Changelog: mapwright

Every change to [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`) and test runs in [TESTS.md](TESTS.md) (`T-`).

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:`, `files:`, and a sentence on what changed.

### C-20261114-1 · 2026-11-14 · 0.1.0 scaffold: mpw.py doctor, explain, inspect, convert, measure, project
- because: user request (Step D.1 of ai-docs/plans/design.md), T-20261114-1
- files: plugin.json, .claude-plugin/, skills/mapwright/SKILL.md, scripts/mpw.py, tests/, evals/evals.json, AGENTS.md, CLAUDE.md, README.md
- First hub skill draft and a standard-library CLI: file inspection for seven formats, GeoJSON/GPX/KML conversion with shapefile reading, Vincenty geodesics with fallbacks, ellipsoid area, scale, and six projections with inverses.
