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

# Round 2 (2026-11-15): eight more books

The eight books queued in [books.md](books.md) were distilled on 2026-11-15. Their notes hold 168 numbered rules. This round gives every rule one verdict:

- **ADOPT**: true, useful and not in the references. Added to a references file with the book and chapter.
- **ALREADY**: the references said it. At most the book was added as a second source.
- **BUILD**: a testable behaviour the code does not have. One row in [book-build-backlog.md](book-build-backlog.md), with the numbers.
- **REJECT**: opinion, out of scope, wrong, weaker than what mapwright has, or not verifiable from the notes.

Dates and historical facts from Thrower, Harley and Woodward, and Goffart are one book's word. Each is marked "(book fact, not cross-checked)" where it was added. Nothing was cross-checked in this round.

## Verdicts

| Book (slug) | Verdict | Rules | ADOPT | ALREADY | BUILD | REJECT |
|---|---|---|---|---|---|---|
| monmonier-how-to-lie-with-maps (Monmonier, 1st ed. 1991) | adopted (the file is the 1991 first edition, not the 2014 printing its name suggests) | 36 | 16 | 10 | 4 | 6 |
| thrower-maps-and-civilization (Thrower, 3rd ed.) | adopted (read by keyword and dated-sentence search, not page by page) | 20 | 13 | 5 | 2 | 0 |
| harley-woodward-history-of-cartography-v1 (Harley and Woodward) | partial (search hits in ch. 11, 13, 14, 18, 19, 20 only; nothing read end to end) | 20 | 17 | 0 | 3 | 0 |
| goffart-historical-atlases (Goffart) | partial (introduction and conclusion only; ch. 1-6 and the catalogue unread) | 6 | 3 | 0 | 0 | 3 |
| shaker-togelius-nelson-pcg-in-games (Shaker, Togelius, Nelson) | adopted | 28 | 11 | 4 | 6 | 7 |
| short-adams-procedural-generation-in-game-design (Short and Adams, eds.) | adopted | 34 | 14 | 4 | 6 | 10 |
| watkins-pcg-for-unity (Watkins) | partial (low yield; the planet and endless-world chapters are weaker than current methods) | 11 | 4 | 4 | 0 | 3 |
| korn-lee-game-dynamics (Korn and Lee, eds.) | partial (ch. 8 and 9 only; formulas unusable from a shifted text layer) | 13 | 5 | 2 | 1 | 5 |
| **Total** | | **168** | **83** | **29** | **22** | **34** |

## Every rule

Rule IDs are the ones in each book's notes. "2nd source" means the book was cited beside an existing line.

### Monmonier, How to Lie with Maps (1991 ed.)

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | M4 geodesic range rings | projections rule 17 |
| ADOPT | M5 symbol footprint; M9 planimetric distance; M33 "represents", not "equals"; M29 swatches on the map's ground colour, second cue for many classes | cartography-design 3.3, 2.1, 2.2 |
| ADOPT | M10 schematic maps say not to scale; M12 class priorities recorded; M18 data date apart from making date; M11 fuzzy boundaries; M14 no black or white class fills; M32 disputed areas | cartography-design rules 1, 30, 24, 38, 39, 40 |
| ADOPT | M8 nine-in-ten pass mark (period standard); M25 Soviet maps are not control; M34 persuasive-map tells; M24 single-source features unconfirmed, trap and paper streets | reading-map-pictures 5.3, 5.4, 7.1, 8.1 |
| ADOPT | M19 primary or derived flag per source | sources-and-terms rule 5 |
| ALREADY | M1 bar over ratio (rule 2); M3 equal-area for density (rule 23); M6 minimum size (rule 15); M15 areal unit (rule 32); M26 ramp order survives output (rules 10-12); M27 midpoint for two-ended ramps (rule 8); M30 label contrast (rule 13) | 2nd source in cartography-design |
| ALREADY | M7 tie line for a moved label; M22 label belongs to its feature; M28 tint legend and the green lowland caution | 2nd source in relief-and-labels 7.2, 11, 3 |
| BUILD | M2 scale-bar guard; M20 inset detection; M21 rank-monotonic selection; M23 sliver list | backlog rows 14, 17, 16, 20 |
| REJECT | M13, M16, M17 (class breaks, unit-size warning, small counts: choropleth ground, which is chartwright's); M31 related classes get near hues (mostly opinion); M35 in-world bias and M36 title wording (opinion, cannot be tested) | |

### Thrower, Maps and Civilization

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | T2 scale forms by year; T5 grid and graticule; T6 relief by era; T7 depth contours first; T8 thematic types by year; T9 print methods; T12 prime meridian | cartography-design 1.6 (first-use table) |
| ADOPT | T3 rhumb network; T14 printed sea chart from 1584; T15 city views; T16 Roman strip map | fantasy-maps 2.1, 3.3, 3.4 |
| ADOPT | T11 projections by year | projections 3.14 |
| ADOPT | T19 the 1:1,000,000 tint and contour preset | relief-and-labels 3 |
| ALREADY | T4 orientation by tradition (cartography-design 2.3); T10 hand wash before printed colour and T13 the 1570 to 1700 bundle (fantasy-maps section 2); T17 state the shading direction (rule 10); T20 north-west light (relief-and-labels 1.6) | 2nd source |
| BUILD | T1 `check --period YEAR`; T18 not-before year in `read` | backlog rows 3, 18 |

### Harley and Woodward, History of Cartography vol. 1

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | H3 Jerusalem at the centre is a dated habit (correction); H5 most mappae mundi are small book diagrams; H1 the four classes | cartography-design 1.2 |
| ADOPT | H1 and H2 mappa mundi presets; H4 colour; H8 and H10 portolan charts, Italian and Catalan; H11, H12, H13 Ptolemaic look; H15 Roman strip map; H19 medieval picture map; H9 hazard signs; H17 courier pace | fantasy-maps 2.1, 3.3, R12 |
| ADOPT | H7 names at right angles to the coast | relief-and-labels 7.3 |
| ADOPT | H11 Ptolemy's first projection and Marinus's grid | projections 3.15 |
| ADOPT | H14 Ptolemaic coordinates before about 1400 are suspect (with H2 and H8 as tells) | reading-map-pictures 7.1 |
| ADOPT | H18 Roman land grid of about 710 m | cities-and-dungeons 1.4 |
| BUILD | H6 rhumb network by construction; H16 itinerary export; H20 medieval date range | backlog rows 15, 22, 19 |

### Goffart, Historical Atlases

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | G1 one base, frame and scale across a dated series; G2 a date on every sheet and a stated scheme; G3 maps of movement are labelled as spanning time | cartography-design rule 36; fantasy-maps R30, R31 |
| REJECT | G4 a text box of changes (opinion on when to use it); G5 readable without commentary (opinion); G6 first dates of time-ordered atlases (the reader says not to quote a first before ch. 3 and 5 are read) | |

### Shaker, Togelius and Nelson, Procedural Content Generation in Games

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | R2 metrics are not inputs; R3 grow the sample until the plot stops changing | cities-and-dungeons section 7, Expressive range |
| ADOPT | R7 BSP stop size as a share of the map; R8 a subtree as a lockable wing; R10 sparse start (20% connects, 50% does not) | cities-and-dungeons 5.1, 5.2 |
| ADOPT | R17 mission in two steps with a fixed rule sequence; R12 stocking by depth; R20 one-per-map cap; R16 a gate cannot be bypassed | cities-and-dungeons 5.5 and its proof rules |
| ADOPT | R18 decks and stations are space-first | scifi-maps 9 |
| ADOPT | R23 no stub rivers | realistic-land rule 21 |
| ALREADY | R6 joining cave chunks (realistic-land 10b); R13 pinned content; R19 template grid (Book methods); R21 lattice noise in octaves (realistic-land 10b) | 2nd source |
| BUILD | R1 expressive range report; R4 dead-flag check; R5 cave flags and sweep; R11 room detection; R14 minimum path length; R15 no isolated wall cells | backlog rows 2, 12, 5, 6, 9, 10 |
| REJECT | R9 digger agents and R22 agent terrain (weaker than what mapwright has; the book reports their failures); R24, R26, R27, R28 (opinion); R25 fair starts for strategy maps (mapwright's battle maps have no bases or resources) | |

R5's numbers were already in realistic-land 10b from the paper itself. The row asks for flags and a sweep, which the code lacks.

### Short and Adams, Procedural Generation in Game Design

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | R2 pattern from path lengths; R3 lock and key kinds and safety; R4 graph on a grid from the start; R12 room purposes from the graph; R28 paced rarity | cities-and-dungeons 5.5 |
| ADOPT | R6 Caves of Qud settings; R14 even stocking of caves | cities-and-dungeons 5.2 |
| ADOPT | R10 split-axis policy; R11 skimmed perimeter | cities-and-dungeons 5.1 |
| ADOPT | R7 wall-growth assembler; R15 house rules (one door for private rooms) | cities-and-dungeons Book methods, section 4 |
| ADOPT | R18 linearity; R19 leniency | cities-and-dungeons section 7, Expressive range |
| ADOPT | R30 road networks loop | realistic-land 10 |
| ALREADY | R5 loops after the fact (cities-and-dungeons 5.1, now sourced); R22 minimum spacing and R27 break the grid (realistic-land 10, fantasy-maps R17); R31 space maps are node networks (scifi-maps 4.2) | 2nd source |
| BUILD | R1 cyclic dungeons; R8 exit-matched block grid; R13 goal at the farthest cell; R17 normalised metrics per setting; R20 range baseline; R21 per-place seeds | backlog rows 1, 7, 8, 11, 13, 4 |
| REJECT | R9, R25, R26, R29, R33, R34 (opinion); R16 goals from placed items and R23 start opposite objective (game objectives, not maps); R24 shuffled region tiles (needs authored tiles); R32 random-walk rivers (weaker than flow routing) | |

### Watkins, Procedural Content Generation for Unity Game Development

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | R1 and R2 guaranteed spine, entrance and exit on opposite edges; R3 solid border | cities-and-dungeons Book methods, section 7 rule 9 |
| ADOPT | R5 chunk-stable generation | games-film-print 1.1 |
| ALREADY | R7 blocking layer (games-film-print 4); R8 seed stored with the map (cities-and-dungeons rule 5); R9 typed slots (template assembly); R10 icosahedron for spheres (scifi-maps 8 and ico-hex, not edited) | 2nd source |
| REJECT | R4 walls only next to floor (moot: mapwright exports wall segments along floor edges); R6 reveal-on-approach generation (game runtime, and the book's shared stream fails the chunk-stable bar); R11 (opinion) | |

### Korn and Lee, Game Dynamics

| Verdict | Rules | Where |
|---|---|---|
| ADOPT | R1 graph-first needs a drawable graph | cities-and-dungeons 5.5 (layout ruling) |
| ADOPT | R5 most constrained type first | cities-and-dungeons 3.3 |
| ADOPT | R3 placement by influence with an edge weight; R8 island boxes with a sea-lane margin; R9 sea-floor noise below sea level | realistic-land 10, 7 |
| ALREADY | R2 relaxed hex cell grid (realistic-land 12); R6 spanning links plus a mean degree (scifi-maps 4.2) | 2nd source |
| BUILD | R10 ports only on open coast | backlog row 21 |
| REJECT | R7 island mask and R12 crater flip (printed formulas damaged, restated from prose only); R11 bell-curve ground cover (constants in the book's own units); R4 and R13 (opinion) | |

## Rulings where a book and the references disagreed

Both sides are stated. Nothing was overwritten without a line here.

- **Jerusalem at the centre.** cartography-design 1.2 said mappae mundi are T-O maps with Jerusalem at the centre. Harley and Woodward ch. 18 says most do not have it and that it marks maps of the later 13th and 14th centuries; the reader rounds this to about 1250 to 1400. Checked against the notes: they say exactly this. Kept: Harley and Woodward, the survey of some 1,100 maps. The old line was true of the Hereford map and wrong as a general rule; 1.2 now says both.
- **Hereford date.** The references say c. 1300, from the cathedral's own page. Harley and Woodward ch. 18 and Monmonier ch. 4 say about 1290. Both are estimates. Kept c. 1300 as the headline, with 1290 beside it. No check depends on it.
- **Pisan chart date.** The references say c. 1275 (Campbell, in Harley and Woodward ch. 19). Thrower says about 1290. Kept c. 1275 in the text with 1290 beside it. The period lint uses the earlier year, so it never fails a date that one source allows.
- **Cave automaton settings.** The code runs fill 0.45, wall at 5 or more, floor at 3 or fewer, 5 passes (the RogueBasin form). The Johnson paper has 50%, T = 5, n = 4. Shaker quotes the same paper with 2 to 4 passes. Caves of Qud ships 55% with a two-sided rule and 2 passes. Nothing was replaced. All four are side by side in cities-and-dungeons 5.2 and the default waits for a sweep on our own code (backlog row 5).
- **Graph layout.** cities-and-dungeons 5.5 said to lay the mission graph out on a grid afterwards, by search. Dormans (Short and Adams ch. 9) starts on the grid, and Korn and Lee ch. 9 reports a studio that dropped free graph rewriting because drawing the graphs became the real work. Kept: on the grid from the first step. The old line stays, with the ruling under it.
- **Green to brown tints.** relief-and-labels 3 warns that green lowland reads as lush and brown as dry. Monmonier agrees. Thrower records the same ramp as the 1909 standard for the 1:1,000,000 world map. Kept the warning as the default; the 1909 ramp is a period preset only.
- **Grey ramps.** Monmonier distrusts colour for ordered data and prefers grey or one hue. Rule 9 allows viridis and cividis. Kept rule 9: both ramps darken steadily, which is his own test, and both postdate the book.
- **Cassini sheets.** Thrower gives 182 sheets finished in 1793. cartography-design 1.4 says 180 maps on 181 sheet numbers and survey work to about 1815, checked against the French library's page on 2026-11-14. Kept the references. Thrower's count was not added.
- **Seed hash.** Short and Adams suggest MD5. The 2026-11-14 ruling stands: a stable hash of mapwright's own choice, never the built-in `hash()`.
- **Loops in BSP dungeons.** The textbook BSP (Shaker ch. 3) joins siblings only and has no loops. mapwright adds extra corridors. Kept ours; it now has a source in Short and Adams ch. 7 and 9.
- **River methods.** Shaker's river agents and Short and Adams' filtered random walks are both weaker than flow routing. Kept flow routing; both rules rejected.
- **Monmonier edition.** The references cite the 2018 third edition for insets and for counts against rates. The file read is the 1991 first edition, which supports both lines (ch. 4, p. 45; ch. 2, p. 22-23). New citations name the 1991 edition. The later editions' chapters on image and online maps are not on disk.

Two books also disagreed with each other:

- **Sixteen roses or sixteen crossings.** Thrower puts sixteen compass roses on the hidden circle of a portolan chart. Harley and Woodward ch. 19 says sixteen bare crossings, with the drawn rose a Catalan addition of 1375. Kept Harley and Woodward, the specialist chapter.
- **Oldest dated chart.** Thrower says 1310; Harley and Woodward say 1311 and treat the other as undated. Kept 1311.
- **Gall's projections.** Thrower dates them to 1885, Monmonier to 1855. Left out of projections 3.14.

## Could not judge

- Korn and Lee's island mask, volcano flip and ground-cover curves: the printed formulas are damaged, so they were rejected, not disproved.
- Goffart's first dates (1651, the 1740s, about 1800): seen in passing in a light read. Left out until ch. 3 and 5 are read.
- Thrower's 1831 for the first shaded-area map: the reader's own note says 1826 is the usual credit. The table says so.
- Monmonier's nine-in-ten pass mark needs the sheet size or scan DPI, which a map picture rarely has. It is recorded as a period fact, with no check.
- Harley and Woodward: the scale and orientation of the marble plan of Rome and the miles-to-league ratio were garbled or missing in the passages read. Not used.

## Remaining gaps after round 2

- No book on disk covers wave function collapse. All four procedural-generation books of this round say so in their notes; Wang tiles and exit-matched blocks are the nearest thing covered. cities-and-dungeons 5.4 still rests on web sources.
- Cave generation now has two book sources; noise terrain (fBm, domain warping) gained nothing new.
- Thrower was read by search, Harley and Woodward by search hits in six chapters, Goffart by its introduction and conclusion. None of their dates was cross-checked.
- The 22 BUILD rows wait in [book-build-backlog.md](book-build-backlog.md). The first round's command proposals listed above still wait too.
- The ledger in technique-harvest was set for all eight books with `book_harvest.py done --verdict` (adopted or partial, as in round 1). Rows change to `built` only after a release.
