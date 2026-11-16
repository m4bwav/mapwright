# Source pass 4 (2026-11-16)

Fourth pass over the "(unverified)" marks in `references/`. Licences and terms first, then numbers the code relies on, then the rest. Every cleared mark now carries a primary URL and "checked 2026-11-16". Marks were cleared only from primary sources: the project's own repo or docs, the licence file, the package registry, the paper, or the publisher's page.

Totals: 46 marks handled against a primary source (36 cleared as written, 10 corrected), and 15 looked at but left marked, with the reason given below. In `grep -c` terms the count fell from 313 lines to 249. Some lines still match because a mark was narrowed rather than removed.

## Per file

| File | Cleared | Corrected | Left (looked at) | Lines still marked |
|---|---|---|---|---|
| prior-art.md | 10 | 5 | 0 | 8 |
| ai-image-models.md | 6 | 0 | 0 (FLUX third-party ControlNets kept) | 18 |
| scifi-maps.md | 3 | 1 | 0 | 11 |
| game-map-generation.md | 3 | 0 | 1 (Civ V `AssignStartingPlots.lua`) | 24 |
| cities-and-dungeons.md | 0 | 1 | 2 (LE03 venue, One Page Dungeon JSON schema) | 25 |
| fantasy-maps.md | 1 | 1 | 1 (Hunt-Lenox globe) | 23 |
| realistic-land.md | 2 | 0 | 0 | 12 |
| projections.md | 3 | 0 | 1 (Ipbüker & Bildirici 2002) | 13 |
| relief-and-labels.md | 1 | 1 | 3 (Jenny-Patterson content, Kennelly hachure reviews, Barrault 2001) | 38 |
| games-film-print.md | 2 | 1 | 2 (Unreal `_x0_y0` naming, Unity step height) | 18 |
| reading-map-pictures.md | 4 | 1 | 0 | 19 |
| pathfinding.md | 0 | 0 | 2 (HPA* speed-up and cluster size) | 6 |
| cartography-design.md | 0 | 0 | 2 (Ortelius LoC record, USGS history path) | 22 |
| sources-and-terms.md | 0 | 0 | 1 (Gaia credit line) | 6 |
| formats-and-tools.md | 0 | 0 | 0 | 6 |

## Corrections (old -> new, source)

1. Spin-gravity comfort limit (scifi-maps): "about 1-2 rpm (studies cite up to 2 rpm)" -> NASA SP-413 set **1 rpm** as the upper limit for living quarters; most people adapt to about 3 rpm; 0.9 g to 1 g. https://settlement.nss.org/75SummerStudy/Chapt3.html
2. Lechner et al. detour rule (cities-and-dungeons): "threshold about 1.5 to 2 (network over straight distance)" -> the paper compares network distance with a constant **k times the Manhattan distance** and gives no value for k. 1.5 to 2 is now labelled as our own starting range. https://arxiv.org/abs/2507.18899, section 3
3. Dungeon Alchemist terms (fantasy-maps): "commercial use of output allowed per their FAQ" -> only "limited commercial purposes"; a business with annual turnover **above USD 100,000** needs a custom licence. https://www.dungeonalchemist.com/terms-of-use art. 4.1
4. TouchTerrain default tile width (games-film-print): 100 mm -> **80 mm** (z-scale 1.0, base 1 mm, print res 0.5 mm). `TouchTerrain_standalone.py` in https://github.com/ChHarding/TouchTerrain_for_CAGEO
5. mapKurator scale (reading-map-pictures): "about 57,000 maps" -> the current arXiv abstract says **over 60,000 maps and over 100 million names**; v1 said 57,000. https://arxiv.org/abs/2306.17059
6. SVG `textPath` `method`/`spacing` (relief-and-labels): "poorly supported" -> MDN browser-compat-data lists both as supported in Chrome, Firefox and Safari. It does not record whether `stretch` renders differently, so the advice to lay glyphs out ourselves stands. https://github.com/mdn/browser-compat-data/blob/main/svg/elements/textPath.json
7. MapLibre GL JS size (prior-art): ~800 KB -> **~1.06 MB** minified (v6.18.0).
8. Tangram size (prior-art): ~300 KB -> **~615 KB** `tangram.min.js` (0.21.1).
9. pmtiles binary (prior-art): ~15 MB -> **17.8 MB** Windows x86_64 zip (v1.31.2). Spec is public domain/CC0, code BSD-3.
10. Wheel sizes (prior-art): pyogrio 15-20 MB -> **~34 MB**; rasterio ~25 MB -> **~31 MB**; d3-geo ~50 KB -> **~36 KB**. Smaller shifts: shapely 1.5 -> 1.8 MB, matplotlib 8 -> 9.3 MB, cartopy 10 -> 9 MB, folium < 0.2 -> 0.13 MB. Source: PyPI JSON API, cp312 win_amd64 wheels, and jsDelivr/npm.

Other facts confirmed this pass and worth knowing: the eHex code in `scripts/mpw_space.py` matches Traveller Map (skips I and O; X is reserved for unknown). On travellermap.com, odd-numbered columns sit half a hex higher. NetHack `MAXNROFROOMS` = 40. Azgaar's default is 10k cells (1k-100k). Qwen-Image has 20.4 B parameters (about 41 GB at bf16), so it needs quantisation on 16 GB. Pillow `convert("CMYK")` sets K = 0. David Rumsey images are CC BY-NC-SA 3.0, and selling reproductions counts as commercial use.

## Code follow-ups

None of the corrections contradicts a constant, default or format field in `scripts/`. Checked: `EHEX` in `mpw_space.py` agrees with the source. No spin-rate, detour-threshold, TouchTerrain or step-height constant exists in the code. If `gen deck` or a megastructure command later takes a spin rate, its default comfort limit should be 1 rpm (SP-413), not 2.

## Left marked, and why

- HPA* "10x faster, within 1%" and cluster size 10 (pathfinding): the author PDF at webdocs.cs.ualberta.ca still returns 404. Only the abstract (via search) and a secondary report (Horsch, usask) were read. The secondary report agrees on b = 10 and 2 levels "as in the initial report".
- Civ V `AssignStartingPlots.lua`: the only GitHub copies found are mods (nqmod) and may differ from the shipped file.
- Lechner 2003 venue: the arXiv copy carries no venue. The Northwestern PDF returned 403.
- One Page Dungeon JSON schema: the itch page shows exports only through devlogs and comments.
- Ipbüker & Bildirici 2002: only bibliographic listings were found, no text.
- Jenny & Patterson 2007 and Kennelly 2008: citations confirmed via Crossref and now carry DOIs. Their content claims were not read.
- Barrault 2001 (AutoCarto): not found. Crossref finds a 1997 COSIT paper instead, which is noted inline.
- Unreal `_x0_y0` tile naming: only forum posts state it. Epic's docs page confirms tiled import but not the pattern.
- Unity NavMesh default step height: the AI Navigation manual page gives no defaults.
- Hunt-Lenox globe inscription: only Wikipedia and retail pages were found. NYPL's own page was not located.
- Gaia credit wording: no change, because gea.esac.esa.int is on the refused list. The cosmos credits page only links there.

## Sites that refused or failed this pass

- loc.gov (403, including the `?fo=json` API)
- esri.com arcgis-blog (403); the desktop.arcgis.com help table was used instead
- galaxykate0.tumblr.com (403)
- ccl.northwestern.edu PDF (403)
- webdocs.cs.ualberta.ca HPA* PDF (404)
- dungeonalchemist.com/faq (404); the terms page worked
- davidrumsey.com/about/terms-of-use (404); /about worked
- unpkg serves `maplibre-gl` dist only under jsDelivr's path

The earlier no-retry list was not retried: pubs.usgs.gov, TomTom, Old Maps Online, Owlbear docs, VizieR, Gaia archive, Wayback and Reddit.
