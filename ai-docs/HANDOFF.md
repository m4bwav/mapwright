# HANDOFF: mapwright

Status: Step D.7 done (2026-11-15): gen city/dungeon/battle, place bars in check, export to Universal VTT, in mpw_places.py; 0.5.0 released (tag on a000d5f); tests 115 pass + 1 live skip. Open D.7 items: graph-first and WFC dungeons, Foundry scene JSON, hex PNG/VTT, real Foundry import untried. Next: D.8 (space generators: gen sector, system, planet, deck).

Continue prompt: [plans/mapwright-continue-prompt.md](plans/mapwright-continue-prompt.md)

## Mark's request (2026-11-14)

"can you create a prompt for an evergreen mapmaking plugin? for reading, writing, finding, and generating life-like and fantasy maps and for science fiction"

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
