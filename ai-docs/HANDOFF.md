# HANDOFF: mapwright

Status: Step D.1 done (2026-11-14): local git repo (main, commit 6163744, no remote), plugin scaffold, hub SKILL.md draft, scripts/mpw.py with doctor/explain/inspect/convert/measure/project, tests 24/24 (`python -m unittest discover -s tests`). Next: D.2 gen world/region/zoom.

Continue prompt: [plans/mapwright-continue-prompt.md](plans/mapwright-continue-prompt.md)

## What exists

- The continue prompt (passes `chain.py check`), this file, [log.md](log.md) and a starter book list in [notes/books.md](notes/books.md).
- Backlog entry "Mapmaking plugin" in [../../plugin-backlog/new-plugins.md](../../plugin-backlog/new-plugins.md).

## Mark's request (2026-11-14)

"can you create a prompt for an evergreen mapmaking plugin? for reading, writing, finding, and generating life-like and fantasy maps and for science fiction"

## Next

0. Before creating public m4bwav/mapwright: privacy-check the first commit (ask/ answers and ai-docs/ went in as-is); rewrite history if anything private. Robinson uses linear table interpolation (PROJ: cubic spline) - fix before world maps.
1. Step D.2: gen world/region/zoom from prototypes/gen.py with the design note's uplift, erosion and river-constrained zoom. Decisions in [plans/design.md](plans/design.md): stdlib SVG render core + headless Chrome/Edge for PNG/PDF; one hub skill (split only on evidence); chartwright keeps choropleths.
2. Run evergreen-convert on mapwright (adds evergreen.json) so `harvest targets` picks up the existing harvest.json.
3. Source pass 3, in small batches (agents stop after ~15-40 calls): ~170 (unverified) marks remain over 13 references; priority = never-scrape terms (Google/Apple/MapTiler), tabletop formats (UVTT/Owlbear/Roll20/Dungeondraft), Snyder values (pubs.usgs.gov 403s scripts: try a mirror or Chrome).
4. Beat: read AI rules of r/mapmaking, r/cartography, Cartographers' Guild before any asks there. Beat at Ai/indie-ai-scout/beats/mapmaking, data ~/.everscout/data/mapmaking.
5. Create public repo m4bwav/mapwright when first code lands (Step D).

## Mark's answers (ask/mapwright-setup-1, answered 2026-11-14, set closed)

- Name: mapwright (final).
- Repository: public now (create m4bwav/mapwright public when the first code lands).
- First maps: none of his projects at first; design so his gaming and learning plugins (studywright/studyquest, ludowright, grindwright, engine plugins) can call it. Step E picks examples from those plugins' needs.
- AI styling: optional; the plugin must know the latest non-AI and AI map generation methods.
- Keyed services: free keys allowed (no paid plans).
- Beat: engage where communities allow AI-assisted questions.

## Waiting on Mark

Nothing open. Books: add a books question to the next askwright set if more are wanted.

## Guesses made while writing the prompt (small rulings, change freely)

- One plugin for all three kinds of world, not three.
- Choropleths and other statistical maps: ownership to be settled with chartwright in the design note.
- The everscout beat starts read-only, since hand-drawn map communities are often hostile to AI art.
- Maps of published settings are never shipped in the plugin, examples or tests.

## Permission grants

None yet.
