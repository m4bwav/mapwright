# AGENTS.md

Rules for any AI agent working in this repository. `CLAUDE.md` imports this file.

## What this is

mapwright: one hub skill, `skills/mapwright/`, for maps of real, fantasy and sci-fi worlds (read, write, find, generate). `scripts/mpw.py` is the CLI, `references/` the research (load one file when a step needs it), `ai-docs/` the plans, log and handoff (start with `ai-docs/HANDOFF.md`; decisions in `ai-docs/plans/design.md`).

## Rules

- Scripts: Python 3.9+, standard library only. numpy, shapely, pyproj, GDAL and geographiclib are optional, probed by `mpw.py doctor`, and never imported at the top level (a test checks this). UTF-8, LF.
- Proof bars are numbers: format round trips within 1e-7 degrees, projection round trips within 1e-9 degrees, equal-area ratios within 1e-6, distances against published values to 1 mm. Never loosen one without a new measurement written in TESTS.md.
- Every change gets a test. Run `python -m unittest discover -s tests`.
- Never say "codemap" or "map this repo" in a description: that is evergreen-map's ground. Choropleths belong to chartwright.
- Never ship maps of published settings or scraped commercial tiles in the plugin, examples or tests.
- A release bumps `plugin.json`, `.claude-plugin/plugin.json`, `VERSION` in `mpw.py`, `metadata.version` in SKILL.md and the CHANGELOG together.
- No private names, hostnames or paths in public files. Plain short sentences, no em dashes, relative links. No AI attribution anywhere.

## Commands

- Tests: `python -m unittest discover -s tests`
- Doctor: `python scripts/mpw.py doctor`
- Inspect: `python scripts/mpw.py inspect tests/fixtures/track.gpx`
- Distance: `python scripts/mpw.py measure distance -41.32 174.81 40.96 -5.50`
