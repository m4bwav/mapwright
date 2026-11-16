# HANDOFF: mapwright

Status: 0.11.0 released 2026-11-16; installed as mapwright@mark-local; wiki still at 0.10.2 (13 pages). Session 17: four subagents in worktrees, PRs #26-#29 merged: lock-aware `path`, `path --jps`, `export --nav`, `gen battle --density` with a legend, `gen dungeon --branches`, L-041 and L-042 closed, SKILL.md body 24.5 KB -> 8.7 KB (detail in references/cli-*.md), description 1,007 chars, evals/run.py kept, source pass 4 (46 marks handled, 249 left; note notes/2026-11-16-source-pass-4.md). Tests 233 pass + 2 skip; evals 38/38 (T-20261116-4) and 10/10 on the final description (T-20261116-5). Waiting on Mark: nothing. Next, in order: (1) wiki to 0.11.0 (wikiwright; rerun notes/2026-11-16-wiki-verify.sh); (2) battle render defects seen in mapwright-lab/s17/battle-31-normal.png: the legend box covers map squares in the bottom-right corner and the title sits over trees (put both outside the grid or on a knockout), and a treasure marker can sit just outside a 3-square room; (3) add an eval trigger case for projections (the description no longer says 'projects points'); (4) L-009 landlocked-window drainage; (5) backlog: nav export agent-size erosion, check --period, per-place seeds, ControlNet aistyle, ports on open coast (build backlog row 21), `gen dungeon --method blocks` (row 7); (6) source pass 5 (relief-and-labels 38, cities-and-dungeons 25, game-map-generation 24 first; loc.gov, Esri blog, ccl.northwestern.edu refuse scripts); (7) heavy worth A/B once there is real use. Beat: three communities stay no-asks. Subagents run on Opus 5.5, effort low; give code agents disjoint modules and keep version, CHANGELOG and SKILL.md with the master.

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
