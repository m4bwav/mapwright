# HANDOFF: mapwright

Status: finished (session 45, 2026-11-16: reopened for four books found on disk, built and released). 0.25.0 released and installed: climate model 2 (PR #72), `sky` charts and sky period rules (PR #70), orbit physics and companions in gen system (PR #71). Tests 301 pass + 2 skip. Book notes in Ai/technique-harvest/ai-docs/books (geosystems-christopherson-birkeland, rosenfelder-planet-construction-kit, nick-kanas-star-maps, traveller-world-builders-handbook). Waiting on Mark: nothing; other 'wanted' books need him to supply them. Next, optional: (1) seasonal rain so climate model 2 makes s/w/Am/Aw; check the typed station normals against a source; (2) constellation figures/boundaries dial (L-071); (3) skipped gen system items listed in PR #71; (4) corridor for cave; (5) heavy worth A/B once there is real use. Before declaring 'finished' again, run book_harvest.py find on D:/RawStorage/BigDownloads/Unorganized and 'Books and Texts' and compare with books.md. Each release: update the wiki in the same session. Next free IDs: L-077, T-20261116-34, C-20261116-19. Beat: three communities stay no-asks. Subagents run on Opus 5.5, effort low; give code agents disjoint modules and ID ranges, keep version, CHANGELOG and SKILL.md with the master.

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
