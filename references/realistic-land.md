# Realistic land: research reference for mapwright

Written 2026-11-14 from the author's existing knowledge of the papers and repositories below. None of the sources were fetched again for that pass; a 2026-11-14 source-check pass verified licences, Priority-Flood, stream power and added section 10b (marked "checked 2026-11-14"). Anything not checked against the original is marked "(unverified)", and licences are the claims most worth re-checking before code is copied. Numbers in square brackets point to the source list at the end.

## 1. Pipeline in one paragraph

Generators that look real follow the order nature uses: tectonics sets the uplift, erosion cuts that uplift into valleys, water routing (depression filling, flow directions, accumulation) gives rivers, lakes and basins, then climate (temperature from latitude and height, rain from wind and terrain), then biomes and soils, and last the human layer (settlements, roads, borders). Cordonnier et al. 2016 [9] showed that uplift plus stream-power erosion alone produces believable mountain ranges and drainage networks. Génevaux et al. 2013 [8] go the other way: they build the river network first and fit the terrain to it. For mapwright, consistency across zoom levels pushes the design toward the river-first or graph-first approach, because a graph built at the coarse level can be refined without moving what it already decided (section 12).

## 2. Plate tectonics and mountain belts

- Real belts form where plates converge: ocean-continent subduction gives a trench offshore and a volcanic arc range parallel to the coast (the Andes). Continent-continent collision gives wide high plateaus (Himalaya, Tibet). Divergent boundaries give mid-ocean ridges and rift valleys. Transform boundaries give little relief. This is standard textbook geology [20].
- Cheap generator version, used by Tectonics.js [11] and many hobby generators (practice figure, no single source; tunable default: the recipe is the common hobby pattern, not checked per generator on 2026-11-16): scatter N plate seeds on the sphere or plane, grow plates by flood fill over cells, give each plate a random velocity vector and a continental or oceanic type, then at each boundary edge compute the relative velocity projected on the boundary normal. Positive convergence raises land, negative opens a ridge or rift. Distance from the boundary sets a falloff, so belts are linear.
- PlaTec (Viitanen 2012 thesis, "Physically based terrain generation: procedural heightmap generation using plate tectonics") [12] simulates plates as moving height grids with collision, subduction and crust transfer, iterated over time. It produces convincing continents but is slow and grid-bound. Licence: the maintained Mindwerks fork states LGPL-3.0 (https://github.com/Mindwerks/plate-tectonics, checked 2026-11-14; an earlier note here said LGPL-2.1, which was wrong for that repo). WorldEngine [13] uses PlaTec through the pyplatec binding.
- Tectonics.js (Carl Davidson) [11] runs plate motion on a sphere in the browser with rock column models. Licence: CC-BY-4.0 per the repo's About panel (https://github.com/davidson16807/tectonics.js, checked 2026-11-14; not non-commercial as earlier guessed). CC BY on code is unusual; keep attribution and check per file.
- Practical recommendation: do not simulate plate motion over time. Use one static frame: plates as Voronoi regions of a few seeds (6-20 for a planet), boundary type from relative velocity, uplift field from boundary distance. Then let erosion produce detail. Cordonnier 2016 [9] drives erosion with exactly such an uplift map.

## 3. Erosion

### 3.1 Stream power law

Fluvial incision is modelled as E = K A^m S^n, where A is upstream drainage area (a proxy for discharge), S the local slope, K erodibility [1][2] (form confirmed against Whipple and Tucker 1999, https://planetarygeoscience.uchicago.edu/doc/Whipple_and_Tucker_1999.pdf, 2026-11-14). Observed concavity m/n is near 0.5 (Whipple and Tucker give roughly 0.35-0.6 for shear-stress incision, per Mudd et al. 2018, https://esurf.copernicus.org/articles/6/505/2018/), and n = 1 is the common choice that makes the equation linear and fast [1][3]. Landscape evolution then follows dh/dt = U - K A^m S^n (+ diffusion), with U the uplift rate.

At steady state (dh/dt = 0) slope is S = (U/K)^(1/n) A^(-m/n): slope falls with drainage area, which gives concave river profiles. This is the key property to check (section 11).

### 3.2 Implicit solver (Braun and Willett 2013)

Braun and Willett's O(n) implicit scheme [3] (the FastScape algorithm): compute receivers (steepest downhill neighbour), build the stack (cells ordered from outlet upstream), compute A by summing in reverse stack order, then update heights in stack order with h_i = (h_i_old + dt(U + F h_receiver)) / (1 + dt F), F = K A^m / distance (for n = 1). It is unconditionally stable, so large time steps work. Cordonnier 2016 [9] uses it on irregular point sets. This is the right algorithm for mapwright: linear time, no matrix, pure loops.

### 3.3 Hillslope (thermal) erosion

- Linear diffusion dh/dt = D ∇²h rounds ridges [1].
- "Thermal erosion" in graphics (Musgrave, Kolb and Mace 1989 [4]): wherever the height difference to a neighbour exceeds a talus threshold T, move a fraction c of the excess downhill. Talus angle for loose rock is about 30-40 degrees [4] (the exact value is a tuning choice). This caps cliffs and makes scree slopes.
- Olsen 2004 "Realtime procedural terrain generation" [5] compares thermal and hydraulic erosion and gives a cheap variant that inverts the thermal rule to make plateaus with flat tops ("erosion score"). (blocked 2026-11-16: the paper itself was not reachable; secondary sources confirm only that Olsen compares thermal and hydraulic erosion, gives speed-ups and a game-suitability score from low mean height and slope spread, e.g. https://ianparberry.com/pubs/terrain.pdf)

### 3.4 Hydraulic droplet and grid erosion

- Grid water simulation (Musgrave 1989 [4]; Mei, Decaudin and Hu 2007, "Fast hydraulic erosion simulation and visualization on GPU" [6]): water height, sediment, velocity per cell; capacity C = Kc · |v| · slope, erode when sediment < C, deposit otherwise, evaporate. Good detail, but hundreds of iterations over a grid, which is too slow in pure Python above about 256².
- Particle/droplet erosion (Hans Theobald Beyer 2015 thesis "Implementation of a method for hydraulic erosion" [7]; widely ported, e.g. Sebastian Lague's Unity version, MIT per https://github.com/SebLague/Hydraulic-Erosion, checked 2026-11-14): drop particles at random, move them by gradient with inertia, carry sediment by capacity, deposit in pits. Gives gullies at grid scale. Cost is particles x steps (about 50k x 30 for 256²): roughly 1.5 M inner loop iterations, tens of seconds in CPython (estimate).
- Recommendation: stream-power on the cell graph for macro shape (cheap, physically grounded, gives real river networks); optional droplet erosion only on a zoomed-in tile for fine texture, seeded deterministically from the tile key.

## 4. Depression filling: Priority-Flood

Barnes, Lehman and Mulla 2014, "Priority-flood: An optimal depression-filling and watershed-labeling algorithm for digital elevation models", Computers & Geosciences 62:117-127 [10]:

1. Put all edge (or ocean-adjacent) cells in a min-priority queue keyed by elevation; mark them closed.
2. Pop the lowest cell c. For each unclosed neighbour n: set h_n = max(h_n, h_c) (fill) or, for the epsilon variant, max(h_n, h_c + ε) so every cell drains; mark closed; push.
3. Repeat until empty.

Complexity O(n log n) with a heap; O(n) for integer elevations. Python's heapq is fine. The epsilon variant gives every cell a strictly downhill path to the sea, which removes flat-area ambiguity. A watershed label can be carried through the same pass [10]. Barnes also published "Priority-flood" improved variants and the RichDEM library (GPL-3.0, https://github.com/r-barnes/richdem, checked 2026-11-14) [10]. Paper facts checked against https://arxiv.org/abs/1511.04463 (2026-11-14): O(n) for integer and O(n lg n) for floating-point data; the improved variant ran up to 37% faster.

Use it twice: once to make sure flow directions exist, and to find lakes: cells where filled height > original height are lake candidates (section 6).

## 5. Flow, accumulation, basins and river networks

- Flow direction: D8 (steepest of 8 neighbours, O'Callaghan and Mark 1984 [14]) on grids; on a Voronoi/Delaunay graph, steepest neighbour among graph neighbours. Single-direction flow guarantees a tree, which means no splits (good for the proof rules). Multiple-flow (MFD, Freeman 1991 [14]) looks smoother on slopes but splits flow; keep it out of the river graph.
- Accumulation: process cells from highest to lowest (or in reverse stack order), add each cell's area (times rainfall, once climate exists) to its receiver. O(n) after a sort [3].
- River = cells with accumulation above a threshold. Lowering the threshold adds smaller tributaries, which is the natural zoom knob: coarse levels show high thresholds, fine levels lower ones, and every coarse river is still present at the fine level.
- Basin = all cells that drain to one outlet; free from the receiver tree.
- Hack's law: main stream length L ≈ 1.4 A^0.6 (L in miles, A in square miles in Hack's 1957 data) [15]; exponent observed 0.5-0.6 across later studies [16]. Check: fit log L against log A over generated basins.
- Horton's laws with Strahler ordering [16][17]: bifurcation ratio R_b = N_ω / N_(ω+1) typically 3-5; length ratio R_l typically 1.5-3.5; area ratio R_a typically 3-6. Real networks fall in these ranges almost regardless of geology [16], so they are good statistical checks.
- Width: rivers widen with discharge, w ∝ Q^0.5 (Leopold and Maddock 1953 hydraulic geometry [18]). Use sqrt(accumulation) for draw width.
- Meanders: sinuosity rises on low slopes; the standard map trick is to add midpoint displacement only to low-gradient segments (O'Leary detail blocked 2026-11-16: mewo2.com/notes/terrain answered 404; treat the trick as practice, tunable default) [21].

## 6. Lakes

- A lake fills a depression up to its spill point and drains through one outlet: the lowest cell on its rim. Priority-Flood finds exactly this: the lake surface is the filled height, and the outlet is the cell through which the flood entered the depression [10].
- In dry climates evaporation can exceed inflow; the lake then has no outlet (endorheic basin: Great Salt Lake, Caspian). Rule: if inflow (accumulated rain) < evaporation x lake area, the lake shrinks to the level where they balance and has zero outlets [19]. Azgaar's generator models open vs closed lakes via a similar evaporation balance [22] (checked 2026-11-16 in https://github.com/Azgaar/Fantasy-Map-Generator src/model/physical/lakes.ts and river-generator.ts: per-lake evaporation from a simplified Penman formula on temperature, height and cell count; an outlet is made only when flux > evaporation, and lakes in deep depressions are flagged closed; Azgaar does not lower the lake level to the balance point, that part is this file's rule).
- So the checkable rule is "at most one outlet": exactly one for an open lake, zero for a closed one.

## 7. Coasts

- Coastlines are fractal; Mandelbrot's dimension for Britain's west coast is about 1.25 [23]. Midpoint displacement or noise-perturbed edges give that look at any zoom.
- Make the coast a function of the base height field plus deterministic noise keyed by world position (not by zoom level), so a coarse coast and a fine coast agree where they overlap.
- Features to aim for: continental shelf (shallow water to about 130-200 m depth then a slope) [20]; capes at hard rock, bays at soft rock; deltas where large rivers meet low-energy coasts; fjords in high-latitude mountain coasts (glacial). Deltas are the one place rivers split (distributaries) [24].
- Red Blob's mapgen2 [25] decides land vs water first on the polygon graph (radial or noise shape), then sets elevation from distance to coast; this gives clean islands but no tectonic structure.
- Archipelago by boxes: drop island rectangles of random size, reject any that overlaps an earlier one, and give each a safety margin, so a sea lane always runs between islands and no island touches the map edge. Decorative sea-floor noise keeps its maximum below sea level, so it never cuts off part of the sea. Bars: sea cells form one connected region; no land on the map border; the land mask is the same with and without the sea-floor layer (Korn and Lee, Game Dynamics, ch. 8, sec. 3.1). Only the margin and the bars are taken: the chapter's noise-in-a-box islands have no drainage, and its printed formulas were unreadable.

## 8. Wind, rain and rain shadows

- Global circulation: three cells per hemisphere. Trade winds (easterlies) 0-30°, westerlies 30-60°, polar easterlies 60-90°. Rising air (and rain) near the equator (ITCZ) and at about 60°; sinking dry air at about 30° gives the subtropical deserts [26].
- Orographic rain: air forced up a slope cools and drops moisture on the windward side; the leeward side gets a rain shadow (Atacama, Patagonian steppe, Great Basin) [26].
- Cheap model used by many generators (corrected 2026-11-16): mapgen4 [25] sorts cells by position projected on the wind direction, then each cell takes the mean humidity of its upwind neighbours; boundary cells reset to 1, water adds evaporation, rain = raininess x humidity, plus orographic rain where humidity exceeds 1 - elevation, which is removed from humidity (checked in https://github.com/redblobgames/mapgen4/blob/master/map.ts `assignRainfall`). Azgaar [22] instead passes winds in from the map edges row by row per 5-degree latitude band, losing humidity per step and regaining it over water (checked in https://github.com/Azgaar/Fantasy-Map-Generator src/model/physical/precipitation-generator.ts). O'Leary [21] not confirmed (page 404). Linear time after one sort.
- Temperature: falls from equator to pole (roughly cosine of latitude) and with height, environmental lapse rate about 6.5 °C per km [26]. Oceans damp seasonality (maritime vs continental climates), which matters for Köppen's seasonal tests.
- Climate model 2 in `gen world` (default since the s45 book track; `--climate-model 1` and old recipes keep the old sweep byte for byte). Sources: Christopherson and Birkeland, Geosystems 10th ed. ch. 4, 5, 9, 17; Rosenfelder, The Planet Construction Kit. Each line says what checks it.
  - Currents and coast side: at about 15-35° a cold current cools (-4 °C at the coast) and dries (x0.4) west coasts; a warm current warms (+2 °C) and wets (x1.6) east coasts; both fade over about 300 km. Checked: symmetric test continent east/west rain x4.09 (old sweep x1.95), east warmer by 3.6 °C (old +0.6); `check` judges the temperature side band by band on real worlds and reports the rain side, which terrain can outweigh.
  - Marine west coasts: poleward of 30° a warm drift adds up to +10 °C at the west coast (fading inland over about 1000 km), so windward high-latitude coasts are Cfb, not Dfc or ET. Checked: lowland west-coast cells at 45-60° on seeds 1-12 went from ET 243, Dfc 86, Cfb 0 to Cfb 227, Dfb 78, Dfc 6.
  - Continentality: annual range (warmest minus coldest month) = (1 + 0.22 x |lat|) x (1 + 2.4 x (1 - e^(-d/1500 km))), d = distance from the upwind sea. Checked: 1500+ km inland the range is x2.12-2.24 the windward coast's (book: x2-4 between paired stations).
  - Climate distances use the latitude scale (111.2 km per degree of the map's latitude span), not the map's 1000-unit width, so "1500 km inland" means the same on any world.
  - Snowline by latitude: about 5000 m at the equator, 2700 m at 45°, 900 m at 62°, linear between; alpine starts 300 m below it (replaces the fixed 2600 m). Checked: a 3000 m plateau at 0° has no alpine cell, a 1200 m one at 60° is all alpine.
  - Upwind edge: `gen region --upwind sea|land|parent` (default sea, the old assumption; parent looks for parent sea just outside the upwind edge). Checked: with land upwind the edge column gets under 40% of the rain it gets with sea.
  - Cell edges: `gen world --hadley 30 --ferrel 60` (defaults unchanged) move the trade/westerly switch and the dry dip (at 0.9 x hadley) for hotter or faster-spinning worlds. Checked: with `--hadley 35` a 32° cell has easterlies and the dry dip is within 2° of 31.5°.
  - Monthly values and Köppen: 12 temperatures from the mean and the annual range (sinusoid, coldest month January north, July south) and 12 equal monthly rain totals; classified by 9.1 (E first, then B, then A/C/D; s before w). Rain has no seasons yet, so the generator never gives s, w, Am or Aw. Checked: Singapore Af, Cairo BWh, London Cfb, Moscow Dfb, Utqiagvik ET classify correctly; every land cell gets one class.
  - Book rules, unverified (no check on our tools yet): continuous permafrost poleward of about -7 °C mean annual temperature and discontinuous from about -1 °C, missing on sun-facing slopes; mangroves within about 30° (salt marsh poleward); warm-water reefs need roughly 18-29 °C water and no cold current; Alfisols are the most widespread soil order and reach the tropics, so the soils line below is a default, not a check; Köppen limits come from Peel 2007 (9.1), not from the book's appendix shorthand (its f, s and c wordings differ).

## 9. Climate classes

### 9.1 Köppen-Geiger thresholds (Peel, Finlayson and McMahon 2007 [27])

Inputs per cell: 12 monthly mean temperatures (°C) and 12 monthly precipitations (mm). Let MAT = annual mean temperature, MAP = annual precipitation, Thot / Tcold = warmest / coldest month mean, Pdry = driest month, Psdry / Pwdry = driest summer / winter month, Pswet / Pwwet = wettest summer / winter month (summer = the warmer six months, Apr-Sep in the north), Pthreshold:
- 2 x MAT if ≥70% of MAP falls in winter,
- 2 x MAT + 28 if ≥70% falls in summer,
- 2 x MAT + 14 otherwise.

Order of tests: E first only if Thot < 10; then B; then A, C, D.

| Class | Rule |
|---|---|
| B (arid) | MAP < 10 x Pthreshold |
| BW (desert) | MAP < 5 x Pthreshold |
| BS (steppe) | otherwise within B |
| h / k | MAT ≥ 18 hot (h), else cold (k) |
| A (tropical) | not B, Tcold ≥ 18 |
| Af | Pdry ≥ 60 |
| Am | not Af, Pdry ≥ 100 - MAP/25 |
| Aw | not Af or Am |
| C (temperate) | not B, Thot > 10 and 0 < Tcold < 18 |
| D (cold) | not B, Thot > 10 and Tcold ≤ 0 |
| E (polar) | Thot < 10 |
| ET | 0 < Thot < 10 |
| EF | Thot ≤ 0 |
| s (dry summer) | Psdry < 40 and Psdry < Pwwet / 3 |
| w (dry winter) | Pwdry < Pswet / 10 |
| f | neither s nor w |
| a | Thot ≥ 22 |
| b | not a, at least 4 months ≥ 10 |
| c | not a or b, 1-3 months ≥ 10 |
| d | not a/b/c and Tcold < -38 (D only) |

Peel et al. use 0 °C for the C/D split; Köppen's original used -3 °C [27]. Pick one and state it. If both s and w apply, Peel et al. resolve it by which season is relatively drier (corrected 2026-11-16: Peel et al. 2007 Table 1 gives the s and w criteria but no tie-break, https://hess.copernicus.org/articles/11/1633/2007/; pick an order, for example test s first, and state it). The 0 vs -3 °C split is checked in the same paper, section 2. The table is the "climate table" proof rule: given the monthly arrays, classification must be a pure function and every cell must land in exactly one class.

For a generator, monthly values can come from a seasonal model: temperature = annual mean + amplitude x cos(month), amplitude growing with latitude and distance from ocean; rain shifted by ITCZ position over the year [26] (practice figure, no single source; tunable default).

### 9.2 Whittaker biomes

Whittaker's diagram (Whittaker 1975, "Communities and Ecosystems" [28]) places biomes on a plane of mean annual temperature (about -15 to 30 °C) and annual precipitation (0 to about 450 cm): tundra (cold), boreal forest (about -5 to 5 °C), temperate grassland/desert (dry), temperate seasonal forest, temperate rainforest (wet), tropical seasonal forest/savanna, subtropical desert, tropical rainforest (hot, over about 250 cm). The exact polygon boundaries are drawn, not formulas; Red Blob's mapgen2 [25] uses a simplified grid lookup of elevation zone x moisture zone (6 moisture bands x 4 elevation bands), which is easy to make deterministic. Ricklefs' textbook version of the diagram is the commonly reproduced one (blocked 2026-11-16: provenance of the reproduced version not traced to a primary source). Recommendation: a lookup table keyed on (temperature band, precipitation band) taken from the diagram, kept as data in the plugin so it can be checked.

## 10. Soils, settlements, roads, borders

### Soils
Jenny's 1941 state factors: soil = f(climate, organisms, relief, parent material, time) [29]. Generator version: parent material from plate/rock type; climate from Köppen; relief from slope (steep slopes get thin soils, valley floors and floodplains get deep alluvium); age high on old shields. Rough mapping (USDA orders [30]): Oxisols humid tropics, Aridisols deserts, Mollisols grasslands (prairie, steppe), Spodosols boreal conifer, Gelisols permafrost, Entisols young alluvium and steep slopes, Alfisols/Ultisols temperate forest. Fertility score for settlement siting: high on Mollisols and floodplain alluvium.

### Settlements
- Classic siting factors: fresh water, flat fertile land, defence, river crossings and confluences, harbours, trade routes [31]. Christaller's central place theory gives a hierarchy with roughly hexagonal spacing of market towns and a k=3 ratio between levels [32].
- Azgaar [22] scores cells by habitability (biome), river flux, coast and confluence, then places capitals with a minimum spacing and towns after [22] (checked 2026-11-16 in https://github.com/Azgaar/Fantasy-Map-Generator src/model/society/population-generator.ts and political/burgs-generator.ts: suitability = biome habitability + normalised river flux and confluence x 250 + coast, estuary and harbour bonuses; capitals by randomised score with minimum spacing (width+height)/2/count, shrunk by 1.2 when stuck; towns after with Gaussian-jittered spacing). Same idea in O'Leary [21]: score = flux + flatness + coast, penalise near existing cities.
- Recommendation: score per cell, then greedy pick with minimum spacing (Poisson-disc-like), capitals first. Deterministic if ties break by cell id. An influence map does the same job: after the fixed features, put each new site on the least influenced cell and update the map; extra weight along the map edge pulls sites inward (Korn and Lee, Game Dynamics, ch. 9, sec. 6; no numbers given). Uniform random placement clumps by chance, so keep the minimum spacing (Short and Adams, Procedural Generation in Game Design, ch. 2, p. 17-18).

### Roads
Least-cost paths: Dijkstra or A* over the cell graph, cost = distance x (1 + k·slope²) x terrain factor (water crossing, forest, swamp), with bridges allowed only at narrow river points [33]. Reuse: once a road exists, lower its cost so later roads merge into trunk routes (checked 2026-11-16: Azgaar's getLandPathCost multiplies cost by 0.5 on existing connections, https://github.com/Azgaar/Fantasy-Map-Generator src/model/economy/routes-generator.ts). Build a minimum spanning tree or Delaunay subset between towns first so the network does not become all-to-all. A pure spanning tree leaves dead ends: real networks loop round forests, lakes and mountains, with riskier shortcuts across and notable sites where loops cross (Short and Adams, Procedural Generation in Game Design, ch. 9, p. 96). Bar: the road graph has a cycle rank above 0.

### Borders
Natural borders follow rivers, watersheds and ridge lines [34]. Generator approach (Azgaar [22], O'Leary [21]): multi-source Dijkstra expansion from capitals with costs for crossing rivers, mountains and biome changes; each cell joins the state that reaches it cheapest. This yields borders on rivers and ridges for free and is deterministic.

## 10b. Caves and noise terrain

### Caves by cellular automata

Johnson, Yannakakis and Togelius 2010, "Cellular automata for real-time generation of infinite cave levels", PCGames 2010, Monterey (https://www.um.edu.mt/library/oar/handle/123456789/22895, PDF read 2026-11-14):

- Fill a grid (50x50 in the paper) with rock at r% (r = 50%), the rest floor.
- Each iteration, a cell becomes rock if the count of rock cells in its Moore neighbourhood of size M is >= T, else floor. Paper settings: M = 1, T = 5, n = 4 iterations; a larger M (M = 2, T = 13) gives smoother walls. Higher n widens caves.
- Walls are rock cells touching floor; disconnected floor regions get group numbers and are joined by carved tunnels. Adjacent grids are generated from stored seeds and blended with 2 more CA passes over the joined grids, so the map is infinite and reproducible per seed.
- Cost is n·w·h·(2M+1)²; the paper reports 3x3 grids in 349 ms on a 2010 laptop in C#.
- Proof rules for mapwright: same seed and (r, n, T, M) give the same cave; after joining, a flood fill from any floor cell reaches every floor cell.
- Shaker, Togelius and Nelson quote the same paper with 2 to 4 steps (Procedural Content Generation in Games, ch. 3, p. 43-44). Settings side by side with mapwright's code and Caves of Qud: [cities-and-dungeons.md](cities-and-dungeons.md) 5.2.

### Noise terrain: fBm and domain warping

- fBm sums octaves of a band-limited noise: f(p) = Σ a^i · noise(l^i · p), lacunarity l about 2, gain a about 0.5, which relates to the Hurst exponent by a = 2^-H (Musgrave in Ebert et al., Texturing and Modeling, 3rd ed. 2003; Quilez, https://iquilezles.org/articles/fbm/, checked 2026-11-16: "G=2^-H"; H runs 0 to 1, G = 0.5 is H = 1, which the article measures as a fit for mountain profiles). Ridged variants use 1 - |noise| per octave for crests.
- Domain warping evaluates f(p + h(p)) instead of f(p). Quilez's form: q = (fbm(p), fbm(p + (5.2, 1.3))), result fbm(p + 4·q); a second layer r = (fbm(p + 4q + (1.7, 9.2)), fbm(p + 4q + (8.3, 2.8))), result fbm(p + 4·r). The offsets only decorrelate the components (https://iquilezles.org/articles/warp/, content via search snippet 2026-11-14; direct fetch returned 404).
- Use: noise is the base and detail layer; it never makes drainage networks, so run Priority-Flood and stream power after it (sections 3-5).
- Per-cell random heights look like spikes, because real heights depend on their neighbours. Lattice noise eased with 3x^2 - 2x^3 and summed over scales with falling amplitude is the textbook cure, which fBm already is (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 4, p. 59-63). No book read so far adds to the fBm or domain-warping notes above.

## 11. Prior art

| Project | What it does well | Licence |
|---|---|---|
| Amit Patel, "Polygonal Map Generation for Games" (2010) and mapgen2/mapgen4, Red Blob Games [25] | Voronoi/Delaunay cell graph, coast first, elevation from coast distance, rivers downhill on corners, moisture from rivers, biome lookup. mapgen4 adds wind-swept rain and fast painting. Clearest writing of the whole idea. | mapgen2 Apache-2.0 (https://github.com/redblobgames/mapgen2, checked 2026-11-14; earlier note said MIT, wrong); mapgen4 Apache-2.0, bundled deps ISC/MIT (https://github.com/redblobgames/mapgen4 README, checked 2026-11-14) |
| Martin O'Leary, "Generating fantasy maps" (2016), repo mewo2/terrain [21] | Cell-graph erosion with a stream-power-like rule, Priority-Flood-style fill, cities by score, borders by expansion, label placement, and a hand-drawn look. Small and readable. | MIT, stated in the README (https://github.com/mewo2/terrain, checked 2026-11-14; no LICENSE file at the usual path) |
| Azgaar's Fantasy Map Generator [22] | Most complete feature set: heightmap templates, rivers, lakes, Köppen-like biomes, cultures, states, burgs, routes, religions, markers. Huge Javascript codebase. | MIT (Azgaar/Fantasy-Map-Generator LICENSE; verify, as the claim matters) |
| Tectonics.js [11] | Real plate motion on a sphere over geological time, rock models, climate. | CC-BY-4.0 (checked 2026-11-14) |
| PlaTec [12] | Physically based plate collision heightmaps. | LGPL-3.0 (Mindwerks fork, checked 2026-11-14) |
| WorldEngine (Mindwerks) [13] | Python: PlaTec plates, erosion, rivers, precipitation, temperature, Holdridge life zones, export. Closest Python precedent; uses numpy. | MIT |
| Undiscovered Worlds (Jonathan Hill) [35] | Whole planets with plates, climate, rivers, lakes, glaciers, regional zoom that generates detail consistent with the global map. Strong evidence the multi-scale approach works. | GPL-3.0 (https://github.com/JonathanCRH/Undiscovered_Worlds, checked 2026-11-14) |
| Gaea (QuadSpinner) and World Machine [36] | Node-graph terrain with high-quality hydraulic, thermal and sediment erosion; industry look target. | Commercial, closed |
| Génevaux et al. 2013 [8] | River network grown first (by Rosgen river types and a Horton-like rule), then terrain built from river elevations with primitives. Fully controllable, guarantees valid hydrology. | Paper |
| Cordonnier et al. 2016 [9] | Uplift map + stream-power erosion on irregular points with Braun-Willett solver; minutes for large scenes; also amplifies a low-res result. | Paper |

## 12. Recommended approach for mapwright

1. Cells: jittered grid or Poisson-disc points keyed by integer world coordinates so the same point appears at every zoom; neighbours from a jittered-grid adjacency (cheap) rather than a full Delaunay (a pure-Python Bowyer-Watson for 50k points is slow, roughly a minute, estimate). A relaxed hex grid is the same idea: hex centroids nudged a little, then Voronoi, with optional Lloyd passes and a minimum edge length (Korn and Lee, Game Dynamics, ch. 9, sec. 3.2.2, sec. 6).
2. Plates: Voronoi of few seeds; uplift field from convergent boundaries.
3. Erosion: Braun-Willett stream power on the graph, 20-100 steps, plus a light thermal pass.
4. Priority-Flood with epsilon; lakes from filled minus original; lake outlets; evaporation check.
5. Wind sweep for rain; temperature from latitude, height, ocean distance; monthly arrays; Köppen; Whittaker lookup.
6. Soils, settlement scores, A* roads, Dijkstra borders.
7. Zoom: child tiles inherit parent cell heights and river paths as constraints (Génevaux-style: rivers fixed, terrain fitted), add noise and lower river thresholds. Never re-run global erosion at a fine level, or rivers will move.

### Cell counts and pure-Python runtime (estimates, not measured)

CPython does very roughly 10-30 M simple loop operations per second. Per-cell costs: Priority-Flood about 1-3 µs x log n per cell with heapq; one stream-power step about 2-5 µs per cell.

| Cells | Use | Full pipeline estimate |
|---|---|---|
| 4k (64²) | quick preview, tests | under 1 s |
| 16k (128²) | region map | 1-3 s |
| 65k (256²) | continent or world default | 5-20 s with 50 erosion steps |
| 262k (512²) | detailed world | 30-90 s; memory a few hundred MB as Python lists, use array module |
| 1M | not recommended pure Python | several minutes |

Azgaar defaults to 10k cells (density step 4) and allows 1k to 100k in 13 steps, flagging above 50k as slow (`src/data/graph-density.ts`, https://github.com/Azgaar/Fantasy-Map-Generator, checked 2026-11-16) [22]; mapgen4 is tuned to look best around 25k cells and supports 1M+ (mapgen4 README, checked 2026-11-14) [25]. 10k-65k is the sweet spot. Measure these numbers in the first prototype and replace this table.

## 13. Proof rules (checkable)

Each should be a test function returning failures.

1. Rivers flow downhill: for every river edge u→v, h_filled(v) < h_filled(u) (strict with epsilon fill). Lake surfaces are flat and exempt internally.
2. Every land cell drains: following receivers from any land cell reaches ocean or a closed lake in < n steps (no cycles).
3. No splits outside deltas: every cell has at most one receiver; a cell with more than one downstream river edge is only allowed in a delta zone (river mouth, slope below a threshold, within k cells of coast).
4. Rivers merge, never cross: river edges do not intersect geometrically.
5. One lake outlet: each lake has exactly one outlet if inflow ≥ evaporation, else zero; the outlet is the lowest rim cell.
6. Accumulation conserved: flux at each outlet equals summed rain of its basin (within float tolerance).
7. River widths never shrink downstream.
8. Climate table: Köppen is a pure function of the 12+12 monthly values; every land cell gets exactly one class; a fixed set of test vectors (e.g. real station normals for Singapore Af, Cairo BWh, London Cfb, Moscow Dfb, Barrow ET) classifies correctly [27].
9. Biome consistent with climate: no rainforest in B climates, no forest in EF.
10. Network statistics in range: Horton R_b in 3-5, Hack exponent 0.5-0.6 over basins larger than some size [15][16]. Warn rather than fail.
11. Zoom consistency: every river and coast cell at level k appears at level k+1 within one child-cell tolerance; same seed gives byte-identical output.
12. Roads: every road segment's max slope below a limit; borders form closed regions with every land cell owned once.
13. River network is a directed tree: one outlet per network, edges point downstream, no cycles; asserted at generation time (Longley et al., Geographic Information Science and Systems, ch. 7).
14. Long profiles are concave overall, with local steps (knickpoints) only at resistant bands or fault scarps, and every river ends at a baselevel: sea, lake or playa (Huggett, Fundamentals of Geomorphology, ch. 9).
15. Planform by regime: steep, coarse, high-supply reaches braid; low-gradient fine reaches meander with a wavelength of about ten channel widths (Huggett, Fundamentals of Geomorphology, ch. 9).
16. Drainage pattern matches geology once a rock layer exists: dendritic on uniform rock, trellis on folded bands, radial on domes and volcanoes (Huggett, Fundamentals of Geomorphology, ch. 9).
17. Slopes over 35 degrees in loose debris are rare (warn when above a small share of land cells) (Huggett, Fundamentals of Geomorphology, ch. 8).
18. Landform plausibility (warn): glacial forms (U troughs, hanging tributaries, cirques facing away from the sun and wind at one snowline band, moraines and eskers along flow) need a cold climate (Huggett, Fundamentals of Geomorphology, ch. 10); dune slip faces all agree with the wind field and dune type follows wind regime and sand supply (Huggett, Fundamentals of Geomorphology, ch. 12); spits and bars sit only downdrift of a drift source and wave-cut platforms only below retreating cliffs (Huggett, Fundamentals of Geomorphology, ch. 13).
19. Generator inputs are uplift, precipitation and rock resistance; the output drifts toward steady state but is not run to it (Huggett, Fundamentals of Geomorphology, ch. 2).
20. Terrain and climate inferred by rule carry a reasons log (rule, inputs, result), and hand overrides are logged beside it (Fonstad, The Atlas of Middle-Earth, p. 196, 198).
21. No stub rivers (warn): a river under a set minimum length is dropped, not drawn (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 4, p. 67; the book gives no number).

## 14. Open questions

- Licences checked 2026-11-14: Azgaar FMG MIT (https://github.com/Azgaar/Fantasy-Map-Generator/blob/master/LICENSE), mewo2/terrain MIT (README), mapgen2 and mapgen4 Apache-2.0, PlaTec fork LGPL-3.0, Tectonics.js CC-BY-4.0, Undiscovered Worlds GPL-3.0, RichDEM GPL-3.0. Only MIT/Apache code may be ported freely; GPL/LGPL ideas only.
- Whether a pure-Python Braun-Willett on 65k cells meets the runtime target needs a prototype measurement.
- Monthly climate model: a calibrated cheap seasonal model is needed for Köppen; none of the hobby generators documents one well (practice figure, no single source; tunable default; mapgen4 and Azgaar have no monthly model, checked 2026-11-16).
- C/D boundary: 0 °C (Peel) or -3 °C (Köppen); pick and record.
- Sphere vs flat: plates and wind belts want a sphere; zoom tiles want a plane. Cube-sphere tiling is one route, not researched here.

## Sources

All accessed 2026-11-14 (from prior knowledge; not re-fetched in this pass).

1. Whipple, K. X. and Tucker, G. E. (1999). Dynamics of the stream-power river incision model. JGR 104(B8):17661-17674.
2. Howard, A. D. and Kerby, G. (1983). Channel changes in badlands. GSA Bulletin 94:739-752.
3. Braun, J. and Willett, S. D. (2013). A very efficient O(n), implicit and parallel method to solve the stream power equation. Geomorphology 180-181:170-179. FastScape: https://fastscape.org
4. Musgrave, F. K., Kolb, C. E. and Mace, R. S. (1989). The synthesis and rendering of eroded fractal terrains. SIGGRAPH '89.
5. Olsen, J. (2004). Realtime procedural terrain generation. University of Southern Denmark report.
6. Mei, X., Decaudin, P. and Hu, B.-G. (2007). Fast hydraulic erosion simulation and visualization on GPU. Pacific Graphics.
7. Beyer, H. T. (2015). Implementation of a method for hydraulic erosion. Bachelor thesis, TU München.
8. Génevaux, J.-D., Galin, É., Guérin, É., Peytavie, A. and Beneš, B. (2013). Terrain generation using procedural models based on hydrology. ACM TOG 32(4) (SIGGRAPH 2013).
9. Cordonnier, G., Braun, J., Cani, M.-P., Beneš, B., Galin, É., Peytavie, A. and Guérin, É. (2016). Large scale terrain generation from tectonic uplift and fluvial erosion. Computer Graphics Forum 35(2) (Eurographics 2016).
10. Barnes, R., Lehman, C. and Mulla, D. (2014). Priority-flood: an optimal depression-filling and watershed-labeling algorithm for digital elevation models. Computers & Geosciences 62:117-127. RichDEM: https://github.com/r-barnes/richdem
11. Tectonics.js, Carl Davidson: https://github.com/davidson16807/tectonics.js
12. Viitanen, L. (2012). Physically based terrain generation: procedural heightmap generation using plate tectonics. Thesis, Helsinki Metropolia UAS. Code: https://sourceforge.net/projects/platec/ and https://github.com/Mindwerks/plate-tectonics
13. WorldEngine: https://github.com/Mindwerks/worldengine
14. O'Callaghan, J. F. and Mark, D. M. (1984). The extraction of drainage networks from digital elevation data. CVGIP 28:323-344. Freeman, T. G. (1991). Calculating catchment area with divergent flow. Computers & Geosciences 17(3).
15. Hack, J. T. (1957). Studies of longitudinal stream profiles in Virginia and Maryland. USGS Professional Paper 294-B.
16. Rodríguez-Iturbe, I. and Rinaldo, A. (1997). Fractal River Basins: Chance and Self-Organization. Cambridge UP.
17. Horton, R. E. (1945). Erosional development of streams and their drainage basins. GSA Bulletin 56:275-370. Strahler, A. N. (1957). Quantitative analysis of watershed geomorphology. Trans. AGU 38(6).
18. Leopold, L. B. and Maddock, T. (1953). The hydraulic geometry of stream channels. USGS Professional Paper 252.
19. Endorheic basins overview: https://en.wikipedia.org/wiki/Endorheic_basin
20. Press, Siever et al., Understanding Earth (textbook); continental shelf: https://en.wikipedia.org/wiki/Continental_shelf
21. O'Leary, M. Generating fantasy maps: https://mewo2.com/notes/terrain/ ; code https://github.com/mewo2/terrain
22. Azgaar's Fantasy Map Generator: https://github.com/Azgaar/Fantasy-Map-Generator ; blog https://azgaar.wordpress.com
23. Mandelbrot, B. (1967). How long is the coast of Britain? Science 156:636-638.
24. Deltas and distributaries: https://en.wikipedia.org/wiki/River_delta
25. Patel, A. Polygonal map generation for games: http://www-cs-students.stanford.edu/~amitp/game-programming/polygon-map-generation/ ; mapgen2 https://github.com/redblobgames/mapgen2 ; mapgen4 https://www.redblobgames.com/maps/mapgen4/ and https://github.com/redblobgames/mapgen4
26. Ahrens, C. D. Meteorology Today (textbook); atmospheric circulation: https://en.wikipedia.org/wiki/Atmospheric_circulation ; lapse rate: https://en.wikipedia.org/wiki/Lapse_rate
27. Peel, M. C., Finlayson, B. L. and McMahon, T. A. (2007). Updated world map of the Köppen-Geiger climate classification. Hydrology and Earth System Sciences 11:1633-1644. https://hess.copernicus.org/articles/11/1633/2007/
28. Whittaker, R. H. (1975). Communities and Ecosystems, 2nd ed. Macmillan.
29. Jenny, H. (1941). Factors of Soil Formation. McGraw-Hill.
30. USDA NRCS, The Twelve Orders of Soil Taxonomy: https://www.nrcs.usda.gov/resources/education-and-teaching-materials/the-twelve-orders-of-soil-taxonomy
31. Settlement site factors (geography curriculum): https://en.wikipedia.org/wiki/Human_settlement
32. Christaller, W. (1933). Die zentralen Orte in Süddeutschland. https://en.wikipedia.org/wiki/Central_place_theory
33. Least-cost path analysis: https://en.wikipedia.org/wiki/Least-cost_path ; Hart, Nilsson and Raphael (1968), A* (IEEE TSSC 4(2)).
34. Natural borders: https://en.wikipedia.org/wiki/Natural_border
35. Undiscovered Worlds: https://undiscoveredworlds.blogspot.com ; code https://github.com/JonathanCRH/Undiscovered_Worlds
36. Gaea: https://quadspinner.com ; World Machine: https://www.world-machine.com
