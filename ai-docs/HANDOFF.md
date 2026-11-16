# HANDOFF: mapwright

Status: 0.10.1 released 2026-11-15 (tag on 62ad87e, PR #20); tests 223 pass + 2 skips. Session 14: evergreen-convert merged (PR #19: evergreen.json, RESEARCH.md, MAINTENANCE.md; harvest targets lists mapwright). Step E maps made (PR #20, note ai-docs/notes/2026-11-15-step-e-maps.md, files in Ai/mapwright-lab/step-e); all pass check (OCR bar skipped). WAITING ON MARK: askwright set ask/mapwright-step-e-1 in worktree D:/m4bwa/Claude/Projects/Ai/mapwright-stepe (keep that worktree until answered; read with ask.py read there, then copy the set to main and remove the worktree). WAITING ON MARK: evergreen registry still points at worktree D:/m4bwa/Claude/Projects/Ai/mapwright-evergreen (re-register blocked by permissions): unregister it, register D:/m4bwa/Claude/Projects/Ai/mapwright, then remove that worktree. Next, in order: (1) act on Step E answers (guess: redo the fantasy battle map, which is sparse and has no legend; L-041 habitable-zone legend not drawn); (2) Step F: hub skill trigger phrases, evals.json `evals` list with decoys + baseline (unit shows untested), worth check, wiki update (still 0.2.0), install the plugin; (3) evergreen-learn consolidation (LEARNINGS 41 > 25, TESTS.md archive); (4) backlog: path --jps, export --nav, path honours locks/keys, cyclic dead-end branches, check --period, per-place seeds, ControlNet aistyle; (5) source pass 4. Beat: r/mapmaking, r/cartography, Cartographers' Guild set to no asks (rules unreadable by script). Subagents run on Opus 5.5, effort low.

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
