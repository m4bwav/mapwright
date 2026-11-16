# Fantasy maps: tradition, tools, symbols, rules and licences

Reference for mapwright, a Python plugin that renders fantasy maps in hand-drawn styles. Written 2026-11-14 from the author's background knowledge with source pointers; no page in the Sources list was re-fetched for this draft, so every claim not marked otherwise is "verify before quoting" and claims marked "(unverified)" are the shakiest. Published-setting maps are described only in general terms and never reproduced.

## 1. The tradition in brief

- The fantasy-novel endpaper map grew out of older pictorial cartography: medieval mappae mundi, portolan charts and Renaissance atlases (Ortelius, Mercator) supplied the profile mountains, sea monsters, cartouches and compass roses that fantasy maps still borrow [S1][S2].
- Twentieth-century fantasy fixed the reader's template: a single continent or region, coast at one edge, ink line work on a parchment tone, hand-lettered names, few roads, mountains drawn in profile [S3]. Stefan Ekman's *Here Be Dragons* (2013) is the standard academic study of these maps and their conventions [S3].
- Critics note the template's habits: north at top, a coastline on the west, an unexplored edge, and a "medieval Europe" look even for non-European settings [S3][S4] (critics' observation, no single source).
- Jonathan Roberts (Fantastic Maps) and Daniel Reeve, Isaac Stewart and other professional fantasy cartographers keep the hand-drawn look alive in commercial books and games; Roberts publishes tutorials on his blog [S5] (names of individual commissions omitted on purpose).

## 2. Styles readers recognise

| Style | Look | Key marks | Notes for a renderer |
|---|---|---|---|
| Ink and parchment ("Tolkien-like" endpaper) | Black or sepia ink on cream/tan, one colour or two | Profile mountains with shaded side hatched, tree-clump forests, ripple coast lines, serif or uncial labels | Easiest to fake well: line weight variation and paper texture carry it [S5] |
| Antique atlas (16th-17th c.) | Watercoloured washes along borders and coasts, ornate frame | Cartouche, compass rose with fleur-de-lis north, rhumb lines, sea monsters, ships | Rhumb lines radiating from roses are a strong period signal [S1][S2]. Hand wash, a cartouche with a bar scale, ships, sea creatures and molehill relief belong together to about 1570 to 1700 (Thrower, Maps and Civilization, ch. 5) (book fact, not cross-checked) |
| Painted / digital painterly (Inkarnate, Wonderdraft look) | Full colour, textured land and sea, soft shadows | Raster stamp assets, coastal glow, bevelled land | Readers associate it with VTT and D&D homebrew [S6][S7] |
| Hex / gaming map | Hex grid over simple terrain icons | Hex icons per terrain type, numbered hexes | Classic in old-school RPGs; Worldographer and Hexographer [S10] |
| Dungeon blueprint | Blue or white grid, black walls, hatched rock | Cross-hatching around walls, door and stair glyphs | "Old school blue" dungeon look; Dyson Logos popularised hand-hatched dungeon style [S17] (blocked: attribution of a trend has no primary source) |
| Isometric / bird's-eye city | Rooftops, walls, streets as blocks | Building blocks, walls with towers, fields | Watabou MFCG is the reference generator [S12] |

### 2.1 Period looks with fixed structure (books, 2026-11-15)

Each look has a year range and a structure that does not vary. Years are book facts, not cross-checked. The first-use table is in [cartography-design.md](cartography-design.md) section 1.6. HW = Harley and Woodward, History of Cartography vol. 1; T = Thrower, Maps and Civilization.

| Look | Years | Fixed structure | Source |
|---|---|---|---|
| Mappa mundi, T-O | Isidore's pattern, over 660 examples; paradise and its four rivers added from at least the 13th century | Circular or oval, east up, Asia the top half, the T made of the Don, the Nile and the Mediterranean. No graticule, no bar scale, no rhumb lines | HW ch. 18 |
| Mappa mundi, zonal | 9th to 15th century, over 150 survive | North or south up, five bands of 36, 30, 48 (24 + 24), 30 and 36 degrees, an ocean river across the tropics | HW ch. 18 |
| Mappa mundi, quadripartite | medieval | East up, a fourth continent in the south, paradise in a square frame with four rivers, bright opaque colours, an ocean ring with fish | HW ch. 18 |
| Mappa mundi, transitional | 14th and 15th century | Circular frame with a chart-style Mediterranean. Rhumb lines only after 1300, a bar scale only after 1400. Jerusalem at the centre is an option for about 1250 to 1400, never a default | HW ch. 18 |
| Portolan chart, Italian | late 13th century, the pattern copied for some four centuries | One skin about a metre long at roughly 1:6 million, the neck of the skin kept. Coast only, plain. No top, no graticule, no north arrow; no latitude scale before 1500; no drawn compass rose before 1375 | HW ch. 19 |
| Portolan chart, Catalan | 14th century on | As the Italian, plus a filled interior: mountain chains in green, the Red Sea in red, a drawn compass rose | HW ch. 19 |
| Ptolemaic | Greek manuscripts, then Latin from the 15th century | World 180 degrees wide from a prime meridian at the western islands, from 63 north to about 16.5 south, straight meridians meeting above the map and parallels as arcs ([projections.md](projections.md) 3.15). An atlas is a world map plus 26 regions: Europe 10, Africa 4, Asia 12. Coordinate lists give longitude first | HW ch. 11 |
| Roman strip map | original AD 335 to 366 | Height to length about 1 to 20 (34 cm by 6.75 m). Roads as lines with staging posts and stage distances, no true scale, seas squeezed to ribbons, seats of power as seated figures, forests as groups of trees, mountains pale brown, main rivers green | HW ch. 14; T ch. 4 |
| Medieval picture map (local) | to the 15th century | No scale. Anything above ground is drawn in elevation; a town is a ring of walls with towers. A bar scale on a local map not before 1421-22 | HW ch. 20 |
| Printed sea chart | from 1584 | Soundings in fathoms, standard signs and coastal views, still with compass roses and rhumb lines. French charts from the 1693 sea atlas drop the many roses and use Mercator's projection with latitude and longitude | T ch. 5-6 |
| City view | city atlases of 1572 to 1618; again in 19th-century town views | Oblique bird's-eye view. The other form is a measured plan | T ch. 5, ch. 7 |

Mappa mundi colour varies, but water is blue or green and the Red Sea red (HW ch. 18).

## 3. Symbol vocabulary

### 3.1 Mountains
- Drawn in profile (side view) on a plan-view map, a convention from pre-modern maps [S1]. Light from the upper left by habit; the right/lower flank is hatched or shaded [S5].
- Ranges overlap: back peaks drawn first and partly hidden by front ones; sizes vary; peaks cluster rather than line up in single file [S5].
- Hills are low humps, often just an arc with a couple of hatch strokes [S5].

### 3.2 Forests
- Tree-clump or "cloud" outline: a scalloped outer edge with a few individual trees or scallops inside, rather than one stamp per tree [S5].
- Alternative: dense lollipop or conifer stamps, overlapping from back to front (common in antique maps and digital tools) [S6].
- Conifers (triangles) vs deciduous (round tops) signal climate [S5] (practice figure, no single source; tunable default).

### 3.3 Coastlines and water
- Ripple or "water lines": several thin lines parallel to the coast, spacing widening outwards, sometimes broken. A 17th-19th c. engraving convention [S1][S5].
- Alternative: stippled shallows, or a darker band of wash along the coast (atlas style) [S2].
- Coasts should be fractal-ish: rough at every scale, smoother on beaches and sandbars, jagged on fjords [S5][S9].
- Rivers drawn as a single tapering line, thicker downstream, meandering more on flat land [S5].
- Portolan hazard signs: a cross or black dots for rocks, red dots for shallows, and no other depth information. Soundings come with the printed sea atlas of 1584 (Harley and Woodward, History of Cartography vol. 1, ch. 19; Thrower, Maps and Civilization, ch. 5) (book facts, not cross-checked).

### 3.4 Compass roses, cartouches, borders
- Compass rose: 4, 8, 16 or 32 points; fleur-de-lis at north and a cross at east in older maps [S1][S2].
- Cartouche: decorative frame holding the title, scale and maker; scrolls, strapwork, figures [S1].
- Neatline border with a graduated or chequered band; antique maps put lat/long ticks there [S2].
- Scale bar, often in leagues or days of travel in fantasy maps [S3].
- Rhumb network of a portolan chart. It is built, not sprinkled: sixteen evenly spaced points on one hidden circle that fills the skin (sometimes two touching circles), each joined to most of the others, which gives thirty-two directions. Sixteen lines leave the centre until 1449, thirty-two after. Colour follows wind rank: the eight winds black or brown, the eight half winds green, the sixteen quarter winds red. The bar scale has large divisions, one or more split into five parts of ten miles each, and names no unit (Harley and Woodward, History of Cartography vol. 1, ch. 19) (book facts, not cross-checked). Thrower describes sixteen roses on the circle, with the same three colours (Maps and Civilization, ch. 4); Harley and Woodward's sixteen bare crossings are kept, since the drawn rose only comes in 1375.

### 3.5 Sea monsters, ships, decorations
- Sea serpents, whales and ships fill empty sea and signal danger or trade routes; Chet Van Duzer's *Sea Monsters on Medieval and Renaissance Maps* (2013) is the standard survey [S8].
- "Here be dragons" as an actual map phrase is rare; the Hunt-Lenox Globe (c. 1508) carries "HIC SVNT DRACONES" (transcribed "Hc Svnt Dracones" by De Costa, 1879) and is the usual cited example (https://en.wikipedia.org/wiki/Hunt%E2%80%93Lenox_Globe, checked 2026-11-16).

### 3.6 Settlements and features
- Cities: small walled cluster or a circle with towers; towns: a few houses or a dot in a ring; villages: a dot [S5].
- Roads: dashed or thin solid lines; bridges where they cross rivers.
- Ruins, towers, caves: small pictograms, ideally a coherent family of icons.

## 4. Hobbyist tools, file formats and licences

| Tool | Maker / model | Native format | Exports | Licence of output / tool | Source |
|---|---|---|---|---|---|
| Wonderdraft | Megasploot; one-time $29.99, no subscription; Windows 10 64-bit and Ubuntu listed (blocked: Mac support and Godot base not stated on the site) (https://wonderdraft.net/, checked 2026-11-14) | `.wonderdraft_map` (blocked: format undocumented) | PNG, JPG, WEBP | Site says "No additional commercial licensing" and calls pack assets "royalty-free" (https://wonderdraft.net/); asset-redistribution terms not on the site (blocked: terms only in the bundled licence) | [S6] |
| Inkarnate | Browser app; free tier, Pro subscription | Cloud project; no project-file export documented in the FAQ (blocked: not stated) | PNG/JPG; higher resolution on Pro | Commercial use (selling maps, commissions) is a Pro benefit; free tier is personal use, 2K export, up to 10 maps (https://inkarnate.com/faq); one Inkarnate page also lists a "Studio" tier, so check live pricing | [S7] |
| Dungeondraft | Megasploot; paid one-time | `.dungeondraft_map` (JSON text, readable) (blocked: schema undocumented) | PNG, WEBP, Universal VTT `.dd2vtt` (JSON with walls, lights, base64 image) | Assets: user packs `.dungeondraft_pack`; output yours | [S11] |
| Campaign Cartographer 3+ | ProFantasy; paid, CAD-based (FastCAD engine) | `.FCW` drawings | Many raster and vector formats | Output yours; symbol sets under ProFantasy EULA | [S9] |
| Worldographer (Hexographer 2) | Inkwell Ideas; free and paid tiers | `.wxx` (gzipped XML, readable) (blocked: compression undocumented) | PNG, others | Output yours | [S10] |
| Azgaar's Fantasy Map Generator | Open source, browser, by Azgaar | `.map` (plain text, delimited data sections; save/load) | SVG, PNG, JPEG, GeoJSON, JSON | Code MIT; generated maps free to use incl. commercially | [S12] |
| Watabou Medieval Fantasy City Generator | Oleg Dolya (watabou); free in browser | URL parameters/seed; JSON export | PNG, SVG, JSON (GeoJSON-like) | Maps free to use incl. commercially ("copy, modify, include in your commercial rpg adventures"), attribution appreciated not required (https://watabou.itch.io/medieval-fantasy-city-generator); older Haxe source watabou/TownGeneratorOS is GPL-3.0 (https://github.com/watabou/TownGeneratorOS); current version's code licence not stated (blocked: not published) | [S13] |
| Watabou One Page Dungeon | watabou; free | Seed in URL; JSON | PNG, SVG, JSON | Same terms as MFCG: "copy, modify, include in your commercial rpg adventures etc.", attribution appreciated but not required (https://watabou.itch.io/one-page-dungeon, checked 2026-11-16) | [S13] |
| Dungeon Scrawl | Browser, free; v2 by Dungeon Scrawl team | `.ds` project file (JSON) (blocked: format undocumented) | PNG, SVG | Output yours (blocked: no terms page found) | [S14] |
| Dungeon Alchemist | Wired Fly; paid, Steam; 3D, AI-assisted furnishing | Project file (binary) | PNG, UVTT, Foundry/Roll20 formats | Only "limited commercial purposes" (art. 4.1); a business with annual turnover above USD 100,000 needs a custom professional licence (https://www.dungeonalchemist.com/terms-of-use, checked 2026-11-16) | [S15] |

Notes:
- The Universal VTT format (`.dd2vtt`, `.uvtt`) is the de-facto interchange for battle maps: JSON with `resolution` (map size, pixels per grid), `line_of_sight` wall polylines, `portals` (doors), `lights`, and a base64 `image` [S11]; keys `resolution` (with `map_origin`, `map_size`, `pixels_per_grid`), `line_of_sight`, `portals` (`position`, `bounds`, `rotation`, `closed`), `lights` (`position`, `range`, `intensity`, `color`) and `image` confirmed in the importer source (https://github.com/moo-man/FVTT-DD-Import/blob/master/ddimport.js). `.dd2vtt`, `.df2vtt` and `.uvtt` are the same format (https://dungeondraft-encyclopaedia.gitbook.io/guide/final-steps/exporting-your-map/universal-vtt). mapwright could export it for dungeon/battle scale.
- Azgaar `.map` is the only richly structured open world format among these; importing it would let mapwright restyle FMG worlds without generating terrain itself [S12].
- None of these tools' asset packs can be shipped inside mapwright. Generated output (FMG, Watabou) can be used as input by a user, not bundled.

## 5. Procedural symbol drawing in code

- **Martin O'Leary, "Generating fantasy maps"** (mewo2.com/notes/terrain): heightmap on a Voronoi/Delaunay mesh, erosion, rivers by flux, coastline contour, city placement by scoring, and labels placed by simulated annealing-like scoring. Mountains drawn as short hatching strokes on slopes: for selected mesh points on steep terrain, draw strokes aligned with the slope direction, more on the shaded side [S16]. The code is JavaScript (d3) and is MIT licensed (https://github.com/mewo2/terrain/blob/master/LICENSE.md). It also powered the @unchartedatlas bot [S16].
- **Azgaar FMG**: relief icons are SVG symbols placed by height/biome with density and size tuned per cell; style presets (ancient, watercolour, etc.) swap SVG filters and fills [S12].
- **Watabou**: draws everything as vector paths with a stylised line; MFCG builds wards from a Voronoi of the city area, then subdivides into building blocks; One Page Dungeon generates rooms then draws hatching around walls procedurally [S13] (blocked: only informal process notes on Tumblr/Twitter).
- **Common techniques for a Python renderer**:
  - Profile mountain: a jittered inverted-V polyline; fill the shaded half with hatch lines clipped to the peak polygon; draw back-to-front sorted by y (painter's algorithm) [S5][S16].
  - Forest clump: union of jittered circles (shapely `unary_union`), draw only the outline with a scalloped stroke, then a few interior tree marks [S5].
  - Ripple coast: offset the coastline polygon outwards (shapely `buffer`) at increasing distances, with stroke width and opacity decreasing; break lines randomly [S5].
  - Hand-drawn line wobble: resample a path and add low-frequency noise perpendicular to it; vary stroke width along length; rough.js does this in JS and has documented the approach [S18].
  - Dungeon hatching: scatter short stroke clusters in the band outside the walls (buffer of walls minus interior), each cluster with a random angle, as in Dyson Logos-style maps [S13][S17].
  - Paper: multiply a parchment texture or procedural noise (value/Perlin) over the drawing; darker vignette at the edges.
- Libraries worth naming (licences as known): shapely (BSD-3), numpy (BSD-3), scipy Voronoi/Delaunay (BSD-3), noise/opensimplex (MIT), cairo via pycairo (LGPL-2.1/MPL-1.1), svgwrite (MIT), Pillow (MIT-CMU/HPND) [S19] (licence list from memory, verify per package before shipping).

## 6. Usual mistakes as checkable rules

Sources: Jonathan Roberts' Fantastic Maps posts [S5]; the Cartographers' Guild forums and their "worldbuilding" FAQ threads [S20]; Reddit's r/mapmaking and r/worldbuilding wiki [S21] (community rules of thumb, no single source). Each rule is written so code can check it on a generated or loaded map.

| ID | Rule | Check |
|---|---|---|
| R1 | Rivers do not split going downstream (allowed exceptions: deltas, braided reaches, anabranches (Huggett, Fundamentals of Geomorphology, ch. 9)) | River graph: every node has out-degree at most 1, except nodes within N cells of the sea [S5][S20] |
| R2 | Rivers flow downhill and end in the sea, a lake, or an endorheic basin | Height strictly non-increasing along each river; terminal node is sea, lake, or a basin flagged as closed [S5][S16] |
| R3 | Rivers join to form larger rivers; tributaries meet at acute angles pointing downstream | Merge angle between tributary and main stem under ~90 degrees measured downstream [S5] |
| R4 | A lake has at most one outflow | Lake polygon: count of outgoing rivers <= 1 [S20] |
| R5 | Rivers do not run along ridgelines or cross mountain ranges | No river cell above a ridge height threshold except at its source [S5] |
| R6 | Mountain ranges are not straight lines, rectangles or single-file rows | Range shape: fit a line to peak centres; flag if residual is tiny or the range bounding box is near-rectangular with uniform spacing [S5][S20] |
| R7 | Mountains come in ranges along plate-like boundaries, not scattered single peaks everywhere | Share of isolated peaks (no neighbour within d) below a threshold [S20] (practice figure, no single source; tunable default) |
| R8 | Rain shadow: the lee side of a range across prevailing wind is drier | Moisture downwind of high ground lower than upwind [S20][S16] |
| R9 | Deserts do not sit next to rainforests without a cause (range, cold current, large latitude change) | Biome adjacency table: forbid desert-rainforest adjacency unless a mountain or latitude gap separates them [S20][S21] |
| R10 | Biomes follow latitude and moisture (Whittaker-style) | Biome given temperature and moisture falls in an allowed set [S12] |
| R11 | Coastlines are rough at all scales; no smooth circles or straight runs | Fractal dimension or tortuosity of coast above threshold [S5] |
| R12 | Scale and travel are consistent: places a "week apart" in text sit a plausible distance apart (about 30-40 km/day on foot by road) | Distance at map scale vs stated days [S3] (practice figure, no single source; tunable default). Upper figure: Roman official couriers with relays averaged about fifty Roman miles (74 km) a day (Harley and Woodward, History of Cartography vol. 1, ch. 14) (book fact, not cross-checked) |
| R13 | Cities sit on water: rivers, coasts, confluences, fords | Each city within d of water or flagged [S16] |
| R14 | Labels do not overlap symbols or each other; names follow the feature (curved on rivers and ranges) | Bounding-box overlap test; label placement scoring as in O'Leary [S16] |
| R15 | Too many fonts or font sizes; hierarchy unclear | Count distinct faces <= 2-3; size ranks match feature rank [S5] |
| R16 | Symbol scale is consistent across the map | Same symbol type within a size band [S5] |
| R17 | Empty map filled with uniform clutter (every hex a forest, every gap a mountain) | Density variance across the land above threshold [S5] (practice figure, no single source; tunable default). Even spread leaves no breathing room: cluster features into sites with empty ground between, and jitter, rotate and clump symbols so no grid shows (Short and Adams, Procedural Generation in Game Design, ch. 2) |

Rules adopted from books (2026-11-14):

| ID | Rule | Check |
|---|---|---|
| R18 | Settlement render order: road skeleton, square, secondary paths, water, blocks by distance from centre, vegetation, furniture (Blando, Fantasy Mapmaker, ch. 2) | Layer order in the recipe |
| R19 | Density falls with distance from the centre: block size grows, paving and building count fall (Blando, Fantasy Mapmaker, ch. 2) | Building density per ring decreases outward |
| R20 | Hill strokes point downhill with the thick end up; gaps between bands encode height (Blando, Fantasy Mapmaker, ch. 3) | Stroke orientation vs local slope |
| R21 | Furniture: margin band, neat line plus inner line, title box with the legend attached, scale near the compass or title (Blando, Fantasy Mapmaker, ch. 6) | Frame and furniture boxes present and adjacent |
| R22 | A label class table (seven levels: realm, region, range and sea, city, town, feature, minor) sets face, size and spacing for every label (Blando, Fantasy Mapmaker, ch. 8) | Every label has a class; sizes rank with class |
| R23 | Build order for an invented world: physical base, then cultural overlays, then journeys (Fonstad, The Atlas of Middle-Earth, p. x-xi) | Recipe layers in that order |
| R24 | Scale is calibrated against every stated distance (straight-line readings preferred); outliers are listed, and maps in a set fit each other (Fonstad, The Atlas of Middle-Earth, p. x) | Best-fit unit and residuals per stated distance |
| R25 | Travel model: speed per traveller type and terrain; stops between fixed points are interpolated (Fonstad, The Atlas of Middle-Earth, p. x) | Travel times recomputed from the model match the table |
| R26 | A story map is a constraint ledger: distances and travel times are fixed once in a travel-time table (route, mode, hours) and reused (Lewis-Jones, The Writer's Map, sec. 2) | Table present for writer output; R12 checks against it |
| R27 | A world meant to grow keeps deliberate blank or beyond-the-edge regions, flagged `unmapped` (Lewis-Jones, The Writer's Map, sec. 4) | Flagged regions are not filled by the generator |
| R28 | A plot-hooks pass lists notable features (ruins, fords, mills, ferries, standing stones) for writers (Lewis-Jones, The Writer's Map, sec. 2) | Hook list in the sidecar |
| R29 | Historical presets set orientation (north, east, south up) and period frame (disc, oval, graticule); an optional square reference grid of fixed cell size indexes places (Brotton, A History of the World in Twelve Maps, intro., ch. 1-5) | Preset fields present; grid labels both axes |
| R30 | A history series states a date on every sheet, as a moment or a span, and the recipe says which scheme the series follows: even intervals or turning points (Goffart, Historical Atlases, Introduction and Conclusion, p. 443 ff.) | Date field per sheet; scheme field per series |
| R31 | A map of movement (a journey or migration over years) is labelled as spanning time, and features on it that belong to another date are marked as such (Goffart, Historical Atlases, Conclusion, p. 443 ff.) | Journey layer has start and end dates; warn when it lies over boundaries of another date |

Lines under labels follow the per-style `label_line_knockout` setting (see relief-and-labels.md 7.3a); fantasy styles default to knocking art out under labels (Blando, Fantasy Mapmaker, ch. 6).

## 7. Scale by purpose

| Map purpose | Typical scale | Typical page coverage | Symbol style | Source |
|---|---|---|---|---|
| World / continent | 1 hex = 60 miles (~100 km) in D&D DMG "kingdom" scale; printed page often 500-2000 km per inch (practice figure, no single source; tunable default) | Whole continent or world | Profile mountains, forest clumps, few names | [S22] |
| Region / province | 1 hex = 6 miles (~10 km), DMG province scale; about 10-50 km per inch on a page (practice figure, no single source; tunable default) | A kingdom or island | Individual hills, towns, roads | [S22] |
| Local / area | 1 hex = 1 mile, DMG local scale | Valley, forest, a day's travel | Villages, farms, paths | [S22] |
| City | Roughly 50-200 m per inch; a medieval city of 10,000 people spans about 1-2 km (practice figure, no single source; tunable default) | Walls and wards | Blocks or individual buildings | [S13] (practice figure, no single source; tunable default) |
| Building / dungeon | 1 square = 10 ft for overview dungeons; 5 ft for play | Rooms, corridors | Walls, doors, stairs, hatching | [S22][S17] |
| Battle map | 1 square = 5 ft (D&D 5e, Pathfinder) at 1 inch per square for miniatures; VTT usually 70-140 px per square (Roll20 baseline 70 px = 1 inch = 5 ft at 100%, https://help.roll20.net/hc/articles/360039675373, checked 2026-11-16) | One encounter area | Floor textures, furniture | [S22][S11] |

## 8. Open licence symbol sets and fonts usable in a shipped plugin

Licence rules that matter: CC0 and public domain need nothing; CC BY needs attribution in the product (credits file plus a visible note is safe); OFL fonts can be bundled and embedded but the font itself cannot be sold alone and renamed modified versions must drop Reserved Font Names [S23][S24]. Avoid CC BY-NC (blocks commercial users of the plugin's output only if the symbols end up in their maps; safer to exclude), CC BY-SA (share-alike may reach users' maps) and any "free for personal use" asset.

### 8.1 Symbol and icon sets

| Set | Licence | Fit | Source |
|---|---|---|---|
| game-icons.net (Lorc, Delapouite and others, 4000+ SVG icons) | CC BY 3.0, attribution per author | Settlement, ruin, monster, ship icons; flat silhouettes, need a hand-drawn filter to fit ink style | [S25] |
| Kenney assets (kenney.nl) | CC0 | Some map and tile packs; game-y look | [S26] |
| OpenGameArt map tiles and symbols | Mixed per item (CC0, CC BY, GPL); check each | Some hand-drawn map symbol sheets exist | [S27] |
| Public-domain antique map scans (Library of Congress, David Rumsey Map Collection, British Library on Flickr) | Many public domain; Rumsey images are CC BY-NC-SA 3.0, commercial reproduction needs permission (https://purl.stanford.edu/xh235dd9059), so prefer LoC and BL Flickr PD items | Cut out real compass roses, cartouches, sea monsters as raster stamps | [S28][S29] |
| Self-generated procedural symbols (Section 5) | Ours | Safest default; no licence trail | — |

Not shippable: Wonderdraft and Dungeondraft bundled assets, Forgotten Adventures, 2-Minute Tabletop and most Patreon map packs (licences forbid redistribution) [S6][S11] (blocked: per-pack licences not checked; assume no).

### 8.2 Fonts (all SIL Open Font License 1.1 unless noted; all on Google Fonts)

| Font | Look | Use | Source |
|---|---|---|---|
| IM Fell family (IM Fell English, DW Pica, Double Pica, Great Primer, French Canon; SC variants) | Digitised 17th c. Fell types by Igino Marini | Atlas and antique labels, the best period fit | [S24][S30] |
| EB Garamond | Garamond revival | Body text, legends | [S24] |
| Cinzel / Cinzel Decorative | Roman capitals | Titles, realm names | [S24] |
| Uncial Antiqua | Uncial | Celtic/"elvish-feeling" titles | [S24] |
| MedievalSharp | Blackletter-ish | Fantasy labels (overused look) | [S24] |
| Pirata One, UnifrakturMaguntia | Blackletter / fraktur | Titles, sparingly | [S24] |
| Almendra, Almendra SC | Calligraphic | Hand-lettered region names | [S24] |
| Caudex, Cardo | Scholarly serifs | Small labels with good diacritics | [S24] |

Bundle the OFL.txt with each font and keep its original name, or only ship the files unmodified [S23].

## 9. Implications for mapwright

- Default to procedurally drawn symbols (mountain, forest clump, ripple coast, hatching) so the plugin carries no third-party art; offer game-icons.net as an optional pack with an auto-generated CREDITS file.
- Ship IM Fell and one or two other OFL fonts with their licence files.
- Import Azgaar `.map`/GeoJSON and Watabou JSON as inputs; export SVG, PNG and Universal VTT.
- Run the Section 6 rules as a lint on any input or generated map before rendering.

## Open questions

- Exact `.dungeondraft_map`, `.wonderdraft_map` and Dungeon Scrawl file schemas: need a sample file each.
- Watabou's current licence wording for generated maps and whether any code is open.
- Whether O'Leary's terrain code licence is MIT (check the GitHub repo).
- David Rumsey image licence terms for a shipped asset.

## Sources (all accessed 2026-11-14; not re-fetched for this draft)

- [S1] Harley, J. B. and Woodward, D. (eds), *The History of Cartography*, vol. 1 and 3, University of Chicago Press; free online at press.uchicago.edu/books/HOC/.
- [S2] David Rumsey Map Collection, davidrumsey.com (antique atlas examples).
- [S3] Ekman, Stefan, *Here Be Dragons: Exploring Fantasy Maps and Settings*, Wesleyan University Press, 2013.
- [S4] Tor.com / Reactor essays on fantasy map conventions, e.g. "Here There Be Dragons" style articles (blocked: exact titles not located).
- [S5] Roberts, Jonathan, Fantastic Maps blog and tutorials, fantasticmaps.com (rivers, mountains, coasts, forests tutorials).
- [S6] Wonderdraft, wonderdraft.net (FAQ and licence).
- [S7] Inkarnate, inkarnate.com (FAQ, Pro and commercial use).
- [S8] Van Duzer, Chet, *Sea Monsters on Medieval and Renaissance Maps*, British Library, 2013.
- [S9] ProFantasy Software, Campaign Cartographer 3+, profantasy.com.
- [S10] Inkwell Ideas, Worldographer, worldographer.com.
- [S11] Dungeondraft, dungeondraft.net; Universal VTT format notes in the Foundry "Universal Battlemap Importer" module docs (https://github.com/moo-man/FVTT-DD-Import, repo confirmed 2026-11-14).
- [S12] Azgaar, Fantasy Map Generator, github.com/Azgaar/Fantasy-Map-Generator and its wiki; azgaar.github.io/Fantasy-Map-Generator.
- [S13] watabou, watabou.itch.io (Medieval Fantasy City Generator, One Page Dungeon) and watabou.github.io.
- [S14] Dungeon Scrawl, dungeonscrawl.com.
- [S15] Dungeon Alchemist, dungeonalchemist.com and its Steam page.
- [S16] O'Leary, Martin, "Generating fantasy maps", mewo2.com/notes/terrain, and github.com/mewo2/terrain.
- [S17] Dyson Logos, dysonlogos.blog (hand-drawn dungeon maps; many released under free commercial licence, check per map).
- [S18] Shihn, Preet, rough.js, roughjs.com and its "how it works" posts (MIT).
- [S19] PyPI pages for shapely, numpy, scipy, pycairo, svgwrite, Pillow, opensimplex.
- [S20] The Cartographers' Guild, cartographersguild.com (tutorials and worldbuilding forums).
- [S21] r/worldbuilding and r/mapmaking wikis, reddit.com (blocked: page names not located).
- [S22] Wizards of the Coast, *Dungeon Master's Guide* (5e, 2014 and 2024), map scale sections (hex 1/6/60 miles; 5 ft squares).
- [S23] SIL Open Font License 1.1 and FAQ, openfontlicense.org.
- [S24] Google Fonts, fonts.google.com (licence shown per family).
- [S25] game-icons.net, licence page (CC BY 3.0).
- [S26] Kenney, kenney.nl (CC0 licence statement).
- [S27] OpenGameArt.org.
- [S28] Library of Congress Geography and Map Division, loc.gov/maps.
- [S29] British Library Flickr Commons, flickr.com/photos/britishlibrary.
- [S30] Marini, Igino, The Fell Types, iginomarini.com/fell.
