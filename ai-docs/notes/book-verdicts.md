# Book verdicts for mapwright

Written 2026-11-14. Fifteen map books were distilled under the technique harvest. Each book's notes are at `Ai/technique-harvest/ai-docs/books/<slug>/notes.md`. Their concrete, checkable rules are now in `references/*.md`, each with a citation. Proposals for commands and scripts (`legend`, `check dungeon`, `gen system --pin`, `render route-anim` and the like) were not built, because mapwright has no scripts yet. The rules those commands would enforce are in the references, so the build can start from them.

## Verdicts

| Book (slug) | Verdict | Rules | Where they went |
|---|---|---|---|
| designing-better-maps-a-guide-for (Brewer) | adopted | 11 | cartography-design rules 3, 5, 10, 14; relief-and-labels 7.2, 7.3, 7.3a, checks 12-14 |
| judith-a-tyner-principles-of-map (Tyner) | adopted | 9 | cartography-design rules 11, 21, 22, 26, 33; relief-and-labels 7.2, 7.3a, checks 12-13 |
| map-use-map-reading-and-design (Kimerling et al.) | partial (ch. 1-5 unread) | 8 | cartography-design rules 7, 14, 28, 29, 31; relief-and-labels 3; reading-map-pictures 8.1 |
| paul-a-longley-et-al-geographic (Longley et al.) | partial (Monte Carlo error propagation not adopted) | 11 | cartography-design rules 5, 27, 30, 32; projections rules 13-16; formats-and-tools traps; realistic-land rule 13 |
| fundamentals-of-geomorphology-richard-john-huggett (Huggett) | adopted | 9 | realistic-land rules 14-19; fantasy-maps R1 |
| nick-kanas-solar-system-maps-from (Kanas) | adopted | 4 | scifi-maps 11 (diagram-mode, planet-orientation, feature-naming, feature-confidence) |
| jerry-brotton-a-history-of-the (Brotton) | partial (survey method is history only; Peters and Google Earth chapters unread) | 3 | cartography-design rule 37; projections rule 15; fantasy-maps R29 |
| fantasy-mapmaker-how-to-draw-r (Blando) | adopted | 8 | cartography-design rules 34, 35; fantasy-maps R18-R22; relief-and-labels 7.3a |
| the-writers-map-an-atlas-of (Lewis-Jones) | adopted | 4 | fantasy-maps R26-R28; games-film-print 5.2a |
| the-atlas-of-middle-earth (Fonstad) | adopted | 5 | cartography-design rule 36; fantasy-maps R23-R25; realistic-land rule 20 |
| world-building-science-fiction-writing-stephen (Gillett) | partial (references/planet-rules.md and `check system` deferred to the build) | 2 | scifi-maps 11 (derivation-order, planet-outputs) |
| procedural-generation-in-godot-christopher-pitt (Pitt) | adopted | 5 | cities-and-dungeons 7 (rules 6, 8) and Book methods |
| dale-green-procedural-content-generation-for (Green) | adopted | 3 | cities-and-dungeons 7 (rule 7) and Book methods |
| cartographic-cinema (Conley) | adopted | 4 | games-film-print 5.2a |
| traveller-world-builders-handbook (Traveller WBH) | partial (sector-file reader not adopted; scifi-maps 3 already covers the formats) | 4 | scifi-maps 11 (pipeline-steps, pin-first, world-record, ico-hex) |

Total: 90 rules.

## Rulings on conflicts

- **Lines under labels.** Brewer knocks lines out under labels; Tyner never breaks a line or lets one cross a label. Ruling: a per-style setting, `label_line_knockout`. Fantasy and engraved styles default to true, reference and topographic styles to false. See relief-and-labels.md 7.3a and check 13.
- **Legend completeness.** Applies only to thematic classes. Labelled base features may be left out of the legend (cartography-design rule 3).
- **Seeds.** Seeds use a stable hash (`hashlib.blake2b`), never Python's built-in `hash()`, which is salted per process. Word seeds are normalised before hashing and recorded in the recipe (cities-and-dungeons rule 6).

## Remaining gaps

- No book filled cave generation (cellular automata) or noise terrain (fBm, domain warping). Green says outright that it has none. cities-and-dungeons 5.2 and realistic-land still rest on web sources only.
- Map Use ch. 1-5 were not read.
- Brotton's chapters on the Peters projection and Google Earth were not read.
- Command proposals wait for the script build: legend templates, callout placement, scale calibration, travel model, plot hooks, route animation with a sync file, era style set, `gen system --pin`, icosahedral hex map, template-assembly dungeons, backtracker dungeon with `--loops`, bitmask tiler.
- Longley's whole-map Monte Carlo error propagation was left out as beyond scope for now.
- The ledger in technique-harvest was updated with these verdicts (see below).
