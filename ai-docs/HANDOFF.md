# HANDOFF: mapwright

Status: 0.10.3 released 2026-11-16; installed as mapwright@mark-local; wiki at 0.10.2 (13 pages, live). Session 15: Step E answered (Mark kept all three maps; set ask/mapwright-step-e-1 closed and moved to main); evergreen registry now points at the main clone; Step F done (PR #22 0.10.2: description triggers, 14-case eval suite 14/14 T-20261116-1, worth lite UNPROVEN; PR #23 wiki note); 0.10.3 fixes VERSION constant, README bar count, Hill spacing note. Waiting on Mark: nothing. Session 16: evals rerun 13/14 (T-20261116-2; find-place undertriggers 1 of 3, L-042 open), LEARNINGS consolidated 41 -> 17 active, TESTS archived (C-20261116-3). Next, in order: (1) L-042: try one description edit for OSM/Overpass finds, rerun find-place x3 + decoys; (2) Ai/plugin-backlog: add mapwright to existing-plugins.md, update its new-plugins.md status line; (4) skill body is ~5.7K tokens: consider moving sections to references; (5) backlog: fantasy battle map density and legend, L-041 habitable-zone legend, path --jps, export --nav, path honours locks/keys, cyclic dead-end branches, check --period, per-place seeds, ControlNet aistyle; (6) source pass 4; (7) heavy worth A/B once there is real use. Delete the leftover folder D:/m4bwa/Claude/Projects/Ai/mapwright-stepf if still on disk. Beat: three communities stay no-asks. Subagents run on Opus 5.5, effort low.

Continue prompt: [plans/mapwright-continue-prompt.md](plans/mapwright-continue-prompt.md)

## Mark's request (2026-11-14)

"can you create a prompt for an evergreen mapmaking plugin? for reading, writing, finding, and generating life-like and fantasy maps and for science fiction"

## Mark's request (2026-11-15)

"it should be familiar with different map generation in games and pathfinding". Added to the todo list: research files references/game-map-generation.md and references/pathfinding.md (started 2026-11-15, session 13), then a hub skill pointer, `explain` entries, and build rows (a `path` command and path bars in `check`) in ai-docs/notes/book-build-backlog.md.

## Next

1. Images and wiki done 2026-11-14 (PR #3 banner + social preview, set in Settings; wiki live at 0.2.0, note ai-docs/notes/2026-11-14-github-wiki.md). At each release rerun the wiki verify script and diff. D.5 done; open: OCR on real maps (no tesseract), a measured reading set for names/legend/scale (Step D "Reading pictures" share), wiki not yet updated to 0.3.0. D.4 open items (LEARNINGS L-010..012): OCR bar untested (no tesseract), straight river labels, star-chart has no catalogue stars, blueprint labels garble when a sheet shrinks.
2. Open issues from D.3 (LEARNINGS L-009): a grandchild window with no sea fails bar 1 (predates D.3); one dry child sits on bar 7's 20-sample edge; no ferries yet (islands get their own road nets).
3. Done: hero banner, social preview, wiki (see 1).
4. Run evergreen-convert on mapwright (adds evergreen.json) so `harvest targets` picks up harvest.json.
5. Then: read/trace, find/fetch, gen city/dungeon/battle, space gens, export, aistyle.
6. Source pass 3 in small batches (~170 unverified marks; priority never-scrape terms, tabletop formats, Snyder values).
7. Beat: read AI rules of r/mapmaking, r/cartography, Cartographers' Guild before any asks.

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
