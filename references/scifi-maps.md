# Sci-fi maps: reference for mapwright

Reference for the planned `gen sector`, `gen system`, `gen planet`, `gen deck` commands and the star charts built from real catalogues. Every claim cites a source in brackets; numbers refer to the Sources list at the end. Claims I could not check against a primary source on 2026-11-14 are marked (unverified); source pass 2026-11-16 resolved each as verified, corrected, blocked or practice figure. Published settings are described only in general terms. Do not copy their maps or data into the plugin.

## 1. Real star positions in 3D

### 1.1 From RA, Dec and parallax to distance

- Distance in parsecs is the inverse of parallax in arcseconds: d = 1 / p. With parallax in milliarcseconds (Hipparcos, Gaia), d = 1000 / p_mas [1][2].
- Inverting parallax is only honest when the relative error is small. Gaia's documentation warns that 1/p is a biased estimator once sigma_p / p goes past about 0.1-0.2, and recommends Bayesian distance estimates (such as Bailer-Jones et al.) for faint or distant stars [2][3].
- Negative or zero parallaxes happen in Gaia data. They mean "far or noisy", never a negative distance. Drop them or use a catalogue distance estimate [2].
- Rule for mapwright: within about 100 pc, bright stars from Hipparcos/HYG have small parallax errors and 1/p is fine (practice figure, no single source; tunable default; check sigma_p/p per star).

### 1.2 Equatorial cartesian

With RA alpha and Dec delta in radians and distance d:

```
x = d * cos(delta) * cos(alpha)   # towards RA 0h, Dec 0 (vernal equinox)
y = d * cos(delta) * sin(alpha)   # towards RA 6h
z = d * sin(delta)                # towards north celestial pole
```

This is the convention the HYG database uses for its x, y, z columns (parsecs, equatorial, Sun at origin) [4]. RA is often stored in hours: multiply by 15 to get degrees first [4].

### 1.3 Equatorial to galactic

The ICRS-to-galactic rotation is fixed by the Hipparcos catalogue (ESA 1997, Vol. 1, section 1.5.3) [1][5]. The galactic north pole is at RA 192.85948 deg, Dec +27.12825 deg, and the galactic centre direction is at l = 0 [1]. Apply this matrix to the equatorial unit vector (rows give galactic x, y, z):

```
[ -0.0548755604  -0.8734370902  -0.4838350155 ]
[ +0.4941094279  -0.4448296300  +0.7469822445 ]
[ -0.8676661490  -0.1980763734  +0.4559837762 ]
```

Galactic X points to the galactic centre (l = 0, b = 0), Y in the direction of rotation (l = 90), Z to the north galactic pole [1][5]. Then l = atan2(Y, X), b = asin(Z / d). Astropy's `Galactic` frame uses the same definition and can be used once as a test oracle, not as a runtime dependency [5].

Proof test: the galactic centre (RA 266.405 deg, Dec -28.936 deg) must map to l about 0, b about 0, and the north galactic pole to b = +90 within 1e-4 deg [1][5].

### 1.4 HYG database fields

The HYG database (Hipparcos + Yale Bright Star + Gliese) by David Nash, distributed as CSV on GitHub [4]. Columns in the current release include [4]:

- `id`, `hip`, `hd`, `hr`, `gl`, `bf` - catalogue identifiers (Hipparcos, Henry Draper, Harvard Revised, Gliese, Bayer/Flamsteed).
- `proper` - proper name where one exists.
- `ra` (hours), `dec` (degrees), epoch and equinox 2000.
- `dist` - parsecs; a value of 100000 marks a missing or unreliable distance and must be filtered out.
- `pmra`, `pmdec` (mas/yr), `rv` (km/s).
- `mag` (apparent visual), `absmag`, `spect` (spectral type), `ci` (B-V colour index).
- `x`, `y`, `z` (equatorial cartesian, parsecs) and `vx`, `vy`, `vz`.
- radian copies of position and proper motion, constellation `con`, multiple-star fields `comp`, `comp_primary`, `base`, and `lum`, `var`.

Licence: the repository states CC BY-SA (version per release; check the LICENSE file before bundling) [4]: CC BY-SA 4.0 International (https://github.com/astronexus/HYG-Database/blob/main/LICENSE, checked 2026-11-14). Share-alike matters: a bundled subset inherits it. Safer route: ship a download script plus checksums, not the CSV.

Gaia DR3 is the deeper alternative with its own archive terms (ESA asks for an acknowledgement) [3]. For a stdlib tool, HYG covers the naked-eye and near-Sun neighbourhood well.

Colour from B-V: a common approximation maps `ci` to temperature with Ballesteros' formula T = 4600 * (1/(0.92*BV + 1.7) + 1/(0.92*BV + 0.62)) K [6], then to RGB with a blackbody table.

## 2. Flattening 3D star maps honestly

A 2D chart of 3D stars lies in some way. The goal is to say which way.

- Project onto the galactic plane (X, Y) and print Z next to each star, in parsecs or light years, signed. This is the convention of most "stars within N light years" charts, including the Atlas of the Universe's plots of nearby stars (blocked 2026-11-16: atlasoftheuniverse.com refused the TLS handshake, so the site-wide claim is not rechecked) [7].
- Stalks (drop lines): draw each star at (X, Y, Z) in an oblique or perspective view, with a vertical line down to its foot on the plane. The foot gives position, the stalk length gives Z. Above-plane stalks solid, below-plane dashed is a common readability choice (practice figure, no single source; tunable default).
- Two-view charts: a plan (X, Y) plus an elevation (X, Z), like an engineering drawing. Nothing is hidden, at the cost of cross-referencing.
- Distance-preserving lie checks: nearest-neighbour pairs in 2D can be far apart in 3D. Print 3D distances on route lines, never the 2D lengths.
- Sky maps (what you see from a point) are a different thing: use RA/Dec with a projection (stereographic for constellations, Hammer-Aitoff or Mollweide for the whole sky) [8].
- Sky charts in mapwright: `MPW sky STARS.csv` (columns ra,dec,mag,name in degrees). Stereographic suits a hemisphere or a constellation; sinusoidal, conic and trapezoidal were the atlas choices for strips of sky. Seen from Earth with north up, east (higher RA) lies to the left; a celestial globe shows the mirror image, so the chart names which one it draws (`--orientation sky|globe`).
- Every sky chart states five things: the area of sky, the orientation, the projection, the epoch and the faintest magnitude drawn. Dot sizes step by whole magnitudes with a legend. `check --period YEAR --period-kind sky` dates the conventions (Bayer letters 1603, IAU list 1922 against IAU boundaries 1930, NGC 1888 and so on); years that are a famous atlas rather than a first use only warn. Source: Nick Kanas, Star Maps (3rd ed., 2019), book rule, cross-checked on Wikipedia 2026-11-16 for Flamsteed numbers and the Bonner Durchmusterung (see LEARNINGS L-067, L-068).
- Sky chart conventions from a modern popular guide (Carole Stott, Starfinder, DK 2007, p. 10-13, 47): figure lines are thin and light between member stars; boundaries use a separate contrasting style (colour or dash), never the figure style; asterisms get a third, weaker line and no boundary. Label tiers: constellation in spaced capitals, proper names in mixed case, then Greek letter, Flamsteed number, deep-sky id; stars sharing one Greek letter carry superscript numbers. Bayer order is only roughly brightness order (Orion's alpha is not its brightest), so keep catalogue letters for real skies and use brightness order only for invented ones. Any timed view states how it handles daylight saving (add an hour). Invented constellations should vary widely in area, as the 88 real ones do (book rule, unverified). An optional star-hopping route layer (numbered hops from an obvious pattern) suits game or fiction sky maps. Stott credits Flamsteed numbers to 1725; keep 1765 (Kanas 6.4.2).
- The `star-chart` render style draws decorative dots from no catalogue; `check` warns about it.
- Sky from a place (any world with a spin axis), for scenes, fantasy calendars and sky charts drawn for an observer. The visible celestial pole stands at an altitude equal to the observer's latitude. At latitude L (north positive) a star of declination d never sets when d > 90 - L, never rises when d < L - 90, and rises and sets otherwise; flip the signs in the south. Only stars on the celestial equator rise due east. Checked against the culmination altitudes on six cases (2026-11-18). (Hockey, How We See the Sky, 2011, ch. 2-3.)
- A pole star is luck, not a law. Precession turns the pole in a circle (about 26,000 years on Earth; an invented world sets its own period), so a chart with an epoch far from J2000 moves the pole and may have no pole star at all. (Hockey, ch. 4.)
- Moon placement follows phase, for an Earth-like moon: a crescent sits near the sun, low in the east before sunrise or low in the west after sunset, lit side toward the sun; first quarter (straight terminator) comes about a week after new moon; a moon seen by day is usually between first and third quarter. A crescent high at midnight is wrong. (Hockey, ch. 8.) Book rules; the geometry carries to invented worlds, the Earth numbers do not.

Proof rules:
- `catalogue-distance`: for each charted star, the distance recomputed from x, y, z equals the catalogue `dist` within 0.1 percent.
- `z-label`: every star on a plane projection carries a Z label or stalk; count of unlabelled stars = 0.
- `route-length`: every route line's printed length equals the 3D distance between its endpoints.

## 3. Traveller-style sector and subsector hex maps

### 3.1 Geometry

- A sector is 32 hexes wide by 40 tall, 1280 hexes [9]. It divides into 16 subsectors lettered A to P [9]; each subsector is 8 by 10 hexes (implied by 32x40 / 4x4; the file-format page lists A-P but does not state 8x10) [9].
- Each hex is addressed `XXYY`, column then row, starting at 0101 at top left [9].
- Hexes are flat-topped in columns; odd and even columns are offset by half a hex. The direction of the offset must be fixed in code and tested On travellermap.com odd-numbered columns (01, 03, ...) sit half a hex higher than even ones: `Astrometrics.cs` shifts even world-X columns up 0.5 and notes that numbered-hex parity is the opposite of world-X parity (https://github.com/inexorabletash/travellermap/blob/main/server/Astrometrics.cs, checked 2026-11-16).
- Hex distance on offset columns: convert to cube coordinates first, then distance = max(|dx|, |dy|, |dz|) [10]. Red Blob Games' hex guide is the standard reference for offset, axial and cube conversions [10].

### 3.2 Text formats (travellermap.com file formats page) [9]

- GEnie ("Sunbane"): fixed width, Windows-1252.
- Legacy SEC: variable width, Windows-1252, parsed by regular expressions.
- T5 Column Delimited: fixed-width columns whose widths are defined by a dashed separator line under the header, UTF-8. Columns: Hex, Name, UWP, Remarks, {Ix}, (Ex), [Cx], N, B, Z, PBG, W, A, Stellar.
- T5 Tab Delimited: tab-separated, UTF-8, with a header row. Columns: Hex, Name, UWP, Bases, Remarks, Zone, PBG, Allegiance, Stars, {Ix}, (Ex), [Cx], Nobility, W; optional Sector, SS, RU. Field order is not fixed, so a parser must read the header.

Recommended for mapwright: write and read T5 Tab Delimited. It is the simplest to parse with `csv` (delimiter `\t`), carries a header, and is UTF-8. Metadata (sector name, subsector names, routes, borders) lives in a separate XML/MSEC metadata file in the Traveller Map ecosystem [9]. Checked 2026-11-16 at https://travellermap.com/doc/metadata: the site has its own XML format and also reads plain-text MSEC files; elements cover subsector names, routes, borders, labels, regions, allegiances and stylesheets (the page does not list a sector-name element).

UWP (Universal World Profile) is a code string like `A788899-C`: starport, size, atmosphere, hydrographics, population, government, law level, dash, tech level [11]. A generator that emits UWPs should emit valid digits per field (eHex 0-9, A-Z skipping I and O) [9][11]. Traveller Map's eHex table skips I and O "to avoid confusion with 1 and 0"; X, Y, Z are 31-33 or reserved, and X is reserved for unknown values (https://travellermap.com/doc/secondsurvey, checked 2026-11-16).

### 3.3 Licensing of travellermap.com data

From the site's About page, 2026-11-14 [12]:

- The Traveller game is owned by Mongoose Publishing; fan sites are permitted under Mongoose's Fair Use Policy with a notice, subject to withdrawal on 90 days notice.
- "The contents of this site are for personal, non-commercial use only."
- Files contributed to the site "cannot be republished or distributed without the consent of the author."
- Map data mixes official data (from Far Future Enterprises, including T5 Second Survey) with apocryphal and unofficial data.
- The site's source code is Apache-licensed.

Consequence for mapwright: never bundle Traveller Map sector data, never fetch and redistribute it, never generate output that reproduces an official sector. Supporting the T5 file format is fine: a format is not the data, and the site's code is Apache-licensed [12]. A user may load their own file. Avoid the Traveller trademark in command names; say "T5 tab sector format" in docs with a pointer to the spec.

## 4. Jump routes and hyperlane graphs

### 4.1 Jump-range graphs

Traveller-style travel links two systems if their hex distance is at most the ship's jump number [11]. In 3D catalogues the equivalent is a distance threshold (a "unit disk graph"). Problem: one threshold either strands outliers or makes a hairball.

### 4.2 Proximity graphs

Standard family, each a subgraph of the next [13][14]:

```
EMST  subset of  RNG  subset of  Gabriel graph  subset of  Delaunay triangulation
```

- Delaunay triangulation: no point inside any triangle's circumcircle; always connected, planar in 2D [13].
- Gabriel graph: edge (p, q) if the disc with diameter pq is empty [14].
- Relative neighbourhood graph (RNG): edge (p, q) if no r is closer to both p and q than they are to each other, i.e. no r with max(d(p,r), d(q,r)) < d(p,q) [14]. Sparse, connected, looks like hand-drawn lanes.
- Euclidean minimum spanning tree (EMST): the sparsest connected one; a tree, so no loops [13].

Because EMST is contained in each, RNG, Gabriel and Delaunay are all connected [13][14]. Games with hyperlanes (Stellaris-style) look like a pruned Delaunay or RNG plus a few extra loops (blocked 2026-11-16: no primary source publishes any specific game's hyperlane algorithm). One shipped map links each node to the start or an already linked neighbour and then adds links up to a designer-set mean connections per node (Korn and Lee, Game Dynamics, ch. 9, sec. 6). Space games drop grids for node networks, since space is points of interest in a void (Short and Adams, Procedural Generation in Game Design, ch. 10, p. 98).

Stdlib-friendly route: RNG by brute force is O(n^3), fine up to a few thousand stars; or build the EMST with Prim's algorithm in O(n^2) and add back short Gabriel edges for loops. Delaunay in pure Python: Bowyer-Watson, O(n^2) worst case, adequate for sector sizes [13] (corrected 2026-11-16: the naive version is O(n^2); with triangle-connectivity point location it is about O(n log n) typical, O(n^2) in degenerate cases, https://en.wikipedia.org/wiki/Bowyer%E2%80%93Watson_algorithm). In 3D the same definitions hold with spheres instead of discs.

### 4.3 Proof rule: connected route graph

- Union-find or BFS from any node reaches all nodes: component count = 1.
- No edge longer than the declared max jump unless the graph marks it as a "long route".
- Optional: report bridges (edges whose removal disconnects); chokepoints are a design feature, so list them, do not fail on them.

## 5. Galaxy shapes and density

- Logarithmic spiral arm: r = r0 * exp(theta * tan(phi)), where the pitch angle phi is the constant angle between the arm and a circle of the same radius [15]. Milky Way arms have pitch angles of roughly 10-14 degrees in Reid et al.'s maser fits [16].
- Disc density: stellar discs follow an exponential profile in radius and height, rho(R, z) = rho0 * exp(-R / h_R) * exp(-|z| / h_z) (or sech^2 in z) [17]. For the Milky Way thin disc, scale length about 2.6 kpc and scale height about 300 pc, thick disc about 900 pc [17].
- Bulge/bar: add a central component (a Plummer or exponential sphere, or an elongated bar). Elliptical galaxies follow a de Vaucouleurs / Sersic profile [18].
- Generation recipe: sample R from the exponential disc, theta uniform, then boost acceptance near arm angles theta_arm(R) = ln(R/r0)/tan(phi) + k*2pi/m for m arms, with Gaussian falloff across the arm. Sample z from exp(-|z|/h_z).
- Sun's position for real-scale maps: about 8.2 kpc from the galactic centre, about 20 pc above the plane [17].

## 6. System diagrams

- To scale is unreadable: Earth's radius is about 1/23,000 of an AU [19], so planets vanish on a linear orbit chart.
- Schematic: equal spacing in order, bodies sized by class, distances printed. Honest if labelled "not to scale".
- Log scale: place orbits at log10(a). Planet orbits roughly follow geometric spacing (the Titius-Bode pattern is empirical, not a law) [20], so log spacing looks even.
- Two scales: orbit distance on a log axis, body sizes on a separate, stated scale. Say both in the legend.
- Delta-v maps: a "subway map" where nodes are orbits or surfaces and edges are the delta-v (km/s) between them. Total mission cost is the sum along a path [21]. Values come from the vis-viva equation v^2 = GM(2/r - 1/a) and Hohmann transfers [21]. Generated systems can compute their own delta-v map from masses and radii: low orbit speed sqrt(GM/r), escape speed sqrt(2GM/r).
- Habitable zone: scale Earth's boundaries by sqrt(L / L_sun); Kopparapu et al. give conservative inner 0.95 and outer about 1.67 AU for the Sun (recent revisions vary) [22].

Proof rule: every orbit in a system is outside the star's radius, inside its Hill sphere if a moon, and adjacent planets are separated by several mutual Hill radii (about 10 is a common stability rule of thumb; practice figure, no single source; tunable default, not a hard limit) [23].

### 6.1 Orbit and climate record per planet (`gen system`)

Fresh rules from public physics; added 2026-11-16 after comparing with a world-building handbook (whose tables and numbers are not used). Physics fields come from their own random stream, so the orbits, masses, moons and SVGs of a seed do not change.

- Year: Kepler's third law in solar units, P(yr) = sqrt(a^3 / M), M the enclosed mass (4 AU around 1 sun gives 8.0 yr).
- Days: solar day from 1/solar = 1/sidereal - 1/year (prograde) or + (retrograde, tilt above 90 degrees); 23.934 h and 365.256 d give 24.00 h. A locked world has sidereal day = year and no solar day (written null).
- Temperature: T_eq = 278.3 K x L^1/4 x (1 - A)^1/4 / sqrt(a), a fast rotator; Earth (A 0.3) gives 254.6 K, and a greenhouse term (about 33 K for Earth) gives about 288 K. Highs and lows scale by (1 -/+ e)^-1/2 at periapsis and apoapsis. Albedo and greenhouse ranges per kind are tunable defaults, not measurements.
- Tidal lock: despin time t = w a^6 I Q / (3 G M*^2 k2 R^5), I = 0.4 m R^2 [35], compared with the system age (drawn below the main-sequence life, about 10 M^-2.5 Gyr). Q, k2 and the initial 12 h spin are stated assumptions, good to an order of magnitude. `--lock physics` uses it (and needs e below 0.1); the default keeps the older distance rule (rocky, inside half the HZ inner edge, M or K star) so default textures do not change. Over seeds 1-200 the physics rule locks 415 of 792 rocky planets, the distance rule 142.
- Eccentricity: Rayleigh with sigma 0.05, capped at 0.3 (multi-planet systems are nearly circular [36]); halved for any neighbour pair whose inner apoapsis reaches the outer periapsis. Proof bar: no crossing.
- Companion star (`--companion`, random or q,a,e): S-type planets stay inside the Holman and Wiegert (1999) limit a_c/a_b = 0.464 - 0.380 mu - 0.631 e + 0.586 mu e + 0.150 e^2 - 0.198 mu e^2 [37]. An equal-mass pair 20 AU apart on a circular orbit allows 5.48 AU (0.274 a_b), not 0.46 a_b: 0.464 is the limit for a massless companion. About 45 percent of Sun-like stars have companions [38]; mapwright adds one only when asked. Planets past the limit are dropped. Circumbinary (P-type) systems are not generated.
- Pins from a sector row (`--tab sector.tab` with `--sector-seed` and `--hex`): the Stars column's class (M, K, G, F) and the PBG gas-giant digit are pinned; belts are recorded but not generated.

Proof bars: no orbit crossing; years match Kepler within 0.1 percent; planets inside the companion's stable limit.

## 7. Planet generation for non-Earth worlds

- Tidally locked worlds: one hemisphere faces the star. Climate models show a hot substellar point, a cold night side, and often a habitable "terminator" band or an "eyeball" ocean around the substellar point [24]. Render with the substellar point as the texture's focus, not the equator.
- Ice worlds: high albedo, cracks and lineae (Europa), cryovolcanic plains (practice figure, no single source; tunable default; describe as reference). Use ridged noise for crack networks.
- Ocean worlds: no continents or a few island arcs; vary colour by depth and latitude, add cloud bands.
- Gas giants: latitude bands (zones and belts) driven by zonal jets; Jupiter has about 5-6 prograde jets per hemisphere [25]. Generate as 1D colour bands in latitude, perturbed by noise advected in longitude, plus ovals (storms).
- Cratered bodies: crater size-frequency distributions follow a power law, N(>D) proportional to D^-b with b around 2 for many surfaces (cumulative), and saturated surfaces approach an equilibrium distribution [26][27]. Sample diameters by inverse transform from a truncated power law; place uniformly on the sphere (sample z uniform in [-1, 1], longitude uniform), larger first so small ones overprint. Simple craters have depth/diameter about 0.2 on the Moon; complex craters above about 15 km on the Moon are shallower with central peaks [27].

Proof rule: generated crater counts per diameter bin fit the declared exponent within a tolerance (log-log slope test).

## 8. Sphere-wrapping textures without seam or pole pinch

- The cause: sampling 2D noise on (u, v) of an equirectangular map gives a seam at u = 0/1 (noise does not wrap) and pinching at the poles (each top row maps to one point) [28].
- The fix: sample 3D noise at the point on the unit sphere, (cos(lat)cos(lon), cos(lat)sin(lon), sin(lat)), for every output pixel. Seams and pole pinch disappear because the noise field is continuous in 3D [28][29].
- Output layouts:
  - Equirectangular (2:1): simplest, what most tools import; oversamples the poles [28].
  - Cube map: six faces, near-uniform sampling; normalise each face point to the sphere before sampling [29].
- Pure Python 3D noise: value noise or Perlin with a permutation table; Simplex/OpenSimplex is nicer but has patent and licence history worth checking (Perlin's simplex patent expired in 2022) [30]: US 6,867,776 expired 2022-01-08 (https://patents.google.com/patent/US6867776, status 'expired - lifetime', checked 2026-11-14).

Numerical proof rules:
- `seam`: mean absolute difference between column 0 and column W-1 is no larger than the mean difference between any two adjacent interior columns (times a small factor, e.g. 1.5).
- `pole`: the top row's variance across longitude is near zero (it is one point) and the second row's values change smoothly; or compare against direct 3D sampling at the pole.
- `cube-edge`: shared edge pixels of adjacent cube faces differ by no more than adjacent interior pixels.

## 9. Deck plans and station layouts

- Square grid, a fixed scale per square. Traveller deck plans traditionally use 1.5 m squares, two squares per displacement ton of volume at 3 m deck height; T5 states one ton as two deck squares with 3 m deck separation, and some plans use a 2 m ceiling (3 squares per ton) and TNE a 2 m grid (checked 2026-11-16 against https://wiki.travellerrpg.com/Layout and https://wiki.travellerrpg.com/DTon; community wiki, not the rulebook text) [11].
- Conventions shared by most published deck plans (practice figure, no single source; tunable default): walls as thick lines, doors as gaps with a swing or slide mark, irises as circles, airlocks as two doors with a small room, ladders and lifts with symbols, a legend and a scale bar, one drawing per deck with decks aligned on a common grid so lifts line up.
- Orientation: "up" on a ship under thrust is away from the drive, so decks stack along the thrust axis; spinning habitats put "down" outward (see section 10).
- Stations: rings, hub-and-spoke, or stacked cylinders; label the rotation axis and spin direction.
- Decks, stations and castles are space-first: generate the plan, abstract it to a room graph, then fit the mission to it. The plan must offer doors and bottlenecks to hang locks on (Shaker, Togelius and Nelson, Procedural Content Generation in Games, ch. 5, p. 88). Check (ours): at least one bridge edge, a door whose removal splits the graph, per requested lock.

Proof rule: `deck-reachability`. Model each deck as a grid graph (floor cells, door edges) with lifts/ladders as edges between decks. BFS from the main airlock reaches every room; report rooms unreachable, airlocks with only one door, and lift shafts that do not align across decks.

## 10. Megastructures and their inner surfaces

- Spin gravity: a = omega^2 * r. For 1 g at r metres, omega = sqrt(9.81 / r) [31]. NASA SP-413 set 1 rpm as "the upper limit of permissible rotation rate for the principal living quarters", noting most people can adapt to about 3 rpm, and specified 0.9 g to 1 g for permanent residents (https://settlement.nss.org/75SummerStudy/Chapt3.html, checked 2026-11-16) [31].
- O'Neill cylinder: two counter-rotating cylinders, the original design about 8 km in diameter and 32 km long, alternating land and window strips [32]. Map the inside as a rectangle: circumference by length. The unrolled rectangle is exact (a cylinder is developable), so no projection distortion [33].
- Stanford torus: a ring of radius about 900 m [31]; same unrolling: the floor is a long strip, circumference by width.
- Ringworld-scale rings: also developable as a strip; draw with a strongly anisotropic scale, or in segments.
- Dyson shell or sphere interior: a sphere is not developable, so any flat map distorts [33]. Use equirectangular or a cube map exactly as for planets (section 8), with "up" pointing towards the star. Note: a rigid Dyson shell is not gravitationally stable relative to its star (net gravity inside a uniform shell is zero) [34], so only the star's gravity applies to its inner surface; label such maps as fiction physics.
- Proof rule: the unrolled cylinder or ring map's left and right edges join (seam test from section 8 applied to the circumference axis).

## 11. Summary of proof rules for mapwright

| Rule | Check |
|---|---|
| catalogue-distance | recomputed 3D distance equals catalogue `dist` within 0.1 percent; galactic-centre and pole round-trip within 1e-4 deg |
| z-label | every plane-projected star has a Z label or stalk |
| route-connected | one component; no edge above max jump unless marked |
| system-stable | orbits outside star radius, moons inside Hill sphere, spacing in mutual Hill radii |
| crater-sfd | log-log slope matches declared exponent |
| seam / pole / cube-edge | numerical comparisons in section 8 |
| deck-reachability | BFS from airlock reaches every room; lifts align |
| data-licence | no bundled third-party sector data; HYG only via download script |
| diagram-mode | a system diagram declares `schematic` (orbits not to scale, plus a separate to-scale body-size row) or `true-scale` (with insets), and prints a scale note (Kanas, Solar System Maps, p. 113, p. 241) |
| planet-orientation | a planet map states its orientation; south-up is allowed only as a declared period style (Kanas, p. 169) |
| feature-naming | feature names come from one theme per feature class, with related names clustered (Kanas, p. 146-147) |
| feature-confidence | mixed-source or invented features carry a confidence field; a feature seen by one source only is drawn as unconfirmed (Kanas, p. 176-177) |
| derivation-order | `gen system` derives in order: star mass, luminosity and age, ice line and zones, planets, then tilt, tidal lock and atmosphere; no later value contradicts an earlier one, and an exception needs a written reason (Gillett, World-Building, p. 7, p. 19, p. 48, p. 138) |
| planet-outputs | `gen planet` outputs tropic and polar-circle latitudes, day length and the sun's angular size for climate bands (Gillett, p. 20, p. 142) |
| pipeline-steps | system pipeline: star, companions, world census, allowed zones, habitable zone, placement, orbits, sizes, moons, per-world physics, life, society; each step writes its fields to the recipe so `check system` can re-verify (Traveller World Builder's Handbook, p. 247, p. 249) |
| pin-first | known facts (main world, star type) can be pinned before generation and the rest grown around them (Traveller WBH, p. 4, p. 248) |
| world-record | each world stores diameter, density, gravity, mass, escape speed, pressure, O2 partial pressure, scale height, water percent, sidereal and solar day, tilt, lock status, mean/high/low temperature, seismic stress and plate count, plus a compact profile string (Traveller WBH, p. 249) |
| ico-hex | an icosahedral hex world map records hexes per triangle edge and km per hex (Traveller WBH, p. 135) |

## Open questions

- HYG release licence version and whether mapwright downloads v3 or v4 (check the repository LICENSE).
- Which hex column parity Traveller Map shifts, if mapwright wants visual parity with its renderer.
- Whether to write the Traveller Map metadata (XML/MSEC) format at all, or only the T5 tab sector file.
- Whether Gaia support (non-stdlib-friendly volume) is in scope.

## Sources (accessed 2026-11-14)

1. ESA, The Hipparcos and Tycho Catalogues (ESA SP-1200), Vol. 1, section 1.5.3, "Galactic coordinates". https://www.cosmos.esa.int/web/hipparcos/catalogues
2. Gaia Collaboration, Luri et al. 2018, "Gaia Data Release 2: using Gaia parallaxes", A&A 616, A9. https://doi.org/10.1051/0004-6361/201832964
3. ESA Gaia archive and DR3 documentation. https://www.cosmos.esa.int/web/gaia/dr3
4. Nash, D., HYG Database repository (astronexus/HYG-Database), README and LICENSE. https://github.com/astronexus/HYG-Database
5. Astropy documentation, `astropy.coordinates.Galactic`. https://docs.astropy.org/en/stable/api/astropy.coordinates.Galactic.html
6. Ballesteros, F. J. 2012, "New insights into black bodies", EPL 97, 34008. https://arxiv.org/abs/1201.1809
7. Powell, R., An Atlas of the Universe, "The Stars within 20 light years". http://www.atlasoftheuniverse.com/20lys.html
8. Snyder, J. P. 1987, Map Projections: A Working Manual, USGS Professional Paper 1395. https://pubs.usgs.gov/pp/1395/report.pdf
9. Traveller Map, "Sector File Formats". https://travellermap.com/doc/fileformats
10. Patel, A., Red Blob Games, "Hexagonal Grids". https://www.redblobgames.com/grids/hexagons/
11. Traveller rules (Mongoose Traveller core rulebook; Traveller5) for UWP, jump and deck-plan scale; general description only (blocked 2026-11-16: edition rulebooks are paid and not checked; deck scale checked against the Traveller wiki, see deck plans). https://www.mongoosepublishing.com/
12. Traveller Map, "About". https://travellermap.com/doc/about
13. de Berg, Cheong, van Kreveld, Overmars 2008, Computational Geometry: Algorithms and Applications, 3rd ed., ch. 9 (Delaunay triangulations, including EMST and RNG containment exercises). https://doi.org/10.1007/978-3-540-77974-2
14. Toussaint, G. T. 1980, "The relative neighbourhood graph of a finite planar set", Pattern Recognition 12(4), 261-268. https://doi.org/10.1016/0031-3203(80)90066-7
15. Weisstein, E. W., "Logarithmic Spiral", MathWorld. https://mathworld.wolfram.com/LogarithmicSpiral.html
16. Reid, M. J. et al. 2019, "Trigonometric Parallaxes of High-mass Star-forming Regions: Our View of the Milky Way", ApJ 885, 131. https://arxiv.org/abs/1910.03357
17. Bland-Hawthorn, J. & Gerhard, O. 2016, "The Galaxy in Context", ARA&A 54, 529. https://arxiv.org/abs/1602.07702
18. Graham, A. W. & Driver, S. P. 2005, "A Concise Reference to (Projected) Sersic R^1/n Quantities", PASA 22, 118. https://arxiv.org/abs/astro-ph/0503176
19. NASA, Earth Fact Sheet. https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html
20. Wikipedia, "Titius-Bode law" (secondary; for the empirical status). https://en.wikipedia.org/wiki/Titius%E2%80%93Bode_law
21. Curtis, H. D., Orbital Mechanics for Engineering Students (vis-viva, Hohmann transfers); delta-v map concept: Wikipedia "Delta-v budget". https://en.wikipedia.org/wiki/Delta-v_budget
22. Kopparapu, R. K. et al. 2013, "Habitable Zones around Main-sequence Stars: New Estimates", ApJ 765, 131. https://arxiv.org/abs/1301.6674
23. Chambers, J. E., Wetherill, G. W., Boss, A. P. 1996, "The Stability of Multi-Planet Systems", Icarus 119, 261. https://doi.org/10.1006/icar.1996.0019
24. Pierrehumbert, R. T. 2011, "A Palette of Climates for Gliese 581g", ApJL 726, L8. https://arxiv.org/abs/1011.4851
25. Porco, C. C. et al. 2003, "Cassini Imaging of Jupiter's Atmosphere, Satellites, and Rings", Science 299, 1541. https://doi.org/10.1126/science.1079462
26. Crater Analysis Techniques Working Group 1979, "Standard techniques for presentation and analysis of crater size-frequency data", Icarus 37, 467. https://doi.org/10.1016/0019-1035(79)90009-5
27. Melosh, H. J. 1989, Impact Cratering: A Geologic Process, Oxford University Press (depth/diameter, simple-complex transition).
28. Bourke, P., "Converting to/from cubemaps" and equirectangular notes. https://paulbourke.net/panorama/cubemaps/
29. Gustavson, S. 2005, "Simplex noise demystified" (3D noise sampling). https://weber.itn.liu.se/~stegu/simplexnoise/simplexnoise.pdf
30. Perlin, K., US Patent 6,867,776 "Standard for perlin noise" (simplex). https://patents.google.com/patent/US6867776B2
31. Johnson, R. D. & Holbrow, C. (eds.) 1977, Space Settlements: A Design Study, NASA SP-413. https://space.nss.org/settlement/nasa/75SummerStudy/Design.html
32. O'Neill, G. K. 1974, "The Colonization of Space", Physics Today 27(9), 32. https://doi.org/10.1063/1.3128863
33. do Carmo, M. P., Differential Geometry of Curves and Surfaces (developable surfaces; Gauss's Theorema Egregium: a sphere cannot be flattened without distortion).
34. Newton's shell theorem; see Wikipedia "Dyson sphere" (stability of a rigid shell). https://en.wikipedia.org/wiki/Dyson_sphere
35. Gladman, B. et al. 1996, "Synchronous Locking of Tidally Evolving Satellites", Icarus 122, 166. https://doi.org/10.1006/icar.1996.0117
36. Van Eylen, V., Albrecht, S. 2015, "Eccentricity from transit photometry: small planets in Kepler multi-planet systems have low eccentricities", ApJ 808, 126. https://arxiv.org/abs/1505.02814
37. Holman, M. J., Wiegert, P. A. 1999, "Long-Term Stability of Planets in Binary Systems", AJ 117, 621. https://arxiv.org/abs/astro-ph/9809315
38. Raghavan, D. et al. 2010, "A Survey of Stellar Families: Multiplicity of Solar-type Stars", ApJS 190, 1. https://arxiv.org/abs/1007.0414
