# HANDOFF: mapwright

Status: 0.10.1 (Step E maps + two fixes, PR pending; set ask/mapwright-step-e-1 waits on Mark) after 0.10.0 released 2026-11-15 (tag on bb8a63e, PR #17); tests 221 pass + 2 live skips on main. Session 13 shipped: 0.7.0 export (PR #11), 0.8.0 aistyle (PR #15, denoise ceiling 0.45, rivers redrawn in code, samples in Ai/mapwright-lab/aistyle), 0.9.0 dungeons (PR #16: goal, cave flags, cyclic, check --range, geoBoundaries per-file licence), 0.10.0 path/travel/chokepoints/fair (PR #17); references game-map-generation.md + pathfinding.md (PR #14, Mark's 2026-11-15 todo); source pass 3 (PR #9); 8 books judged (PR #12, backlog in notes/book-build-backlog.md). Next, in order: (1) evergreen-convert (evergreen.json so harvest finds harvest.json); (2) Step E: one map per kind (life-like, fantasy, sci-fi) for the gaming/learning plugins, through check, then an askwright page; (3) Step F: hub skill trigger phrases (export, path, game maps), eval suite with decoys and baseline, worth check, wiki update (still at 0.2.0), install the plugin (not installed yet); (4) backlog: path --jps, export --nav, cyclic dead-end branches and the b-not-enterable rule, check --range sample size, check --period, per-place seeds, ControlNet aistyle look; (5) source pass 4 (Snyder values, Tiled/Unity/Unreal/Godot marks). Beat: r/mapmaking, r/cartography, Cartographers' Guild rules unreadable by script (anti-bot, login wall): no asks until Mark reads them or a later fetch works. Subagents run on Opus 5.5, effort low (Mark, 2026-11-15).

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
