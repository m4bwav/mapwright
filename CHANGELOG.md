# Changelog: mapwright

Every change to [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`) and test runs in [TESTS.md](TESTS.md) (`T-`).

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:`, `files:`, and a sentence on what changed.

### C-20261114-3 · 2026-11-14 · 0.2.0 (unreleased): names, settlements, roads; relative parent path; 13 bars
- because: user request (Step D.3), L-007, L-008, L-009
- files: scripts/mpw_names.py (new), scripts/mpw_human.py (new), scripts/mpw_gen.py, scripts/mpw.py, tests/test_mpw.py, skills/mapwright/SKILL.md, README.md
- `names` samples a sound pattern (six styles or a custom C/V/F/S/N pattern), lists styles and renames a world. `gen world` stores the language in recipe.json and names.json and places scored, spaced and ranked settlements, A* roads over a relative neighbourhood graph, and names for settlements, rivers (one per main stem), lakes, seas and oceans, mountain ranges and landmasses. Children keep parent settlements, roads and names, lift parent settlement and road cells out of new sea or lake cells, and add villages and tracks. The child recipe stores its parent path relative to itself; absolute paths still read. `check` gains bars 8 to 13.

### C-20261114-2 · 2026-11-14 · 0.2.0 (unreleased): gen world, gen region / zoom, check; Robinson as PROJ
- because: user request (Step D.2 of ai-docs/plans/design.md), T-20261114-2, L-003, L-004, L-005, L-006
- files: scripts/mpw_gen.py (new), scripts/mpw.py, tests/test_mpw.py, skills/mapwright/SKILL.md
- `gen world` builds the recipe folder and map.svg from plates with distance-to-boundary uplift, domain-warped fBm, 15 steps of implicit stream-power erosion, Priority-Flood with epsilon, single receivers, one-outlet lakes, climate and biomes. `gen region` and `zoom` make a child map by IDW of 3 parent cells plus detail noise, with the parent's coast as a sign constraint and parent rivers burnt in. `check` runs seven numbered proof bars. Robinson now uses PROJ's cubic-spline coefficients (float32, as PROJ stores them) and matches PROJ's builtins.gie rows to 0.1 mm.

### C-20261114-1 · 2026-11-14 · 0.1.0 scaffold: mpw.py doctor, explain, inspect, convert, measure, project
- because: user request (Step D.1 of ai-docs/plans/design.md), T-20261114-1
- files: plugin.json, .claude-plugin/, skills/mapwright/SKILL.md, scripts/mpw.py, tests/, evals/evals.json, AGENTS.md, CLAUDE.md, README.md
- First hub skill draft and a standard-library CLI: file inspection for seven formats, GeoJSON/GPX/KML conversion with shapefile reading, Vincenty geodesics with fallbacks, ellipsoid area, scale, and six projections with inverses.
