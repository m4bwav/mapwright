# Relief and labels: reference for mapwright

Scope: how to draw terrain (hillshade, contours, tints, hachures, Tanaka, Swiss style) and how to place names (rules, positions, algorithms, SVG mechanics), in a form a stdlib-only Python renderer can implement and test. Source tags in square brackets point to the Sources list at the end. Anything marked "(unverified)" was written from memory and not checked against the source on 2026-11-14.

## 1. Hillshade

### 1.1 What it computes

Hillshade models a surface lit by a distant point source and gives each cell a brightness equal to the cosine of the angle between the surface normal and the light direction (Lambertian reflectance) [Horn1981]. Output is usually scaled 0..255. Flat ground lit from altitude `alt` gets `255 * sin(alt)`, so at 45 degrees flat ground is about 180, not white [EsriHS].

### 1.2 The 3x3 window

Name the neighbourhood of cell `e` like this (row 0 is north/top):

```
a b c
d e f
g h i
```

`cs` is the cell size in the same horizontal units as the elevation, `z` the z-factor (section 1.5).

### 1.3 Horn (1981) derivatives

Horn's third-order finite difference weights the centre row and column twice [Horn1981]; Esri's Slope and Hillshade tools use it [EsriSlope]:

```
dzdx = ((c + 2f + i) - (a + 2d + g)) / (8 * cs)
dzdy = ((g + 2h + i) - (a + 2b + c)) / (8 * cs)
```

With row 0 at the top, `dzdy` as written is positive when elevation rises toward the south; Esri's formulas use this sign convention [EsriSlope]. Keep the sign consistent with the aspect formula below, or the light will appear to come from the wrong side. Test: a plane rising to the east must come out brighter when lit from the east (azimuth 90) than from the west.

### 1.4 Zevenbergen-Thorne (1987) derivatives

Zevenbergen and Thorne fit a partial quartic to the 3x3 window; the first derivatives reduce to a second-order central difference that ignores the corners [ZT1987]:

```
dzdx = (f - d) / (2 * cs)
dzdy = (h - b) / (2 * cs)
```

It is cheaper and follows fine detail more closely; Horn smooths more and is said to behave better on rough or noisy DEMs [Jones1998] (Jones compared eight methods by RMS error on a synthetic surface with added noise; Horn beat Fleming and Hoffer's four-cell method, the slope term Zevenbergen-Thorne shares, when noise was large; checked 2026-11-16 via the abstract, https://doi.org/10.1016/S0098-3004(98)00032-6; the full ranking is still unverified). GDAL exposes both (`gdaldem hillshade -alg Horn|ZevenbergenThorne`) and notes ZT suits smoother landscapes [GDAL].

### 1.5 Slope, aspect, shade (Esri formulation)

From [EsriHS]:

```
zenith_rad  = radians(90 - altitude)
azimuth_math = 360 - azimuth + 90          # compass to math angle
if azimuth_math >= 360: azimuth_math -= 360
azimuth_rad = radians(azimuth_math)

slope_rad = atan(z * sqrt(dzdx**2 + dzdy**2))

if dzdx != 0:
    aspect_rad = atan2(dzdy, -dzdx)
    if aspect_rad < 0: aspect_rad += 2*pi
else:
    aspect_rad = pi/2 if dzdy > 0 else (3*pi/2 if dzdy < 0 else 0)

shade = 255 * (cos(zenith_rad) * cos(slope_rad)
               + sin(zenith_rad) * sin(slope_rad) * cos(azimuth_rad - aspect_rad))
shade = max(0, shade)
```

Pure-Python note: a 1000x1000 grid is a million `math` calls per term; precompute `cos(zenith)`, `sin(zenith)`, and use `a = z*dzdx`, `b = z*dzdy` with the vector form `shade = 255 * (cosZ - b*sinZ*sinA' ... )` only if it is derived and tested against the reference form (unverified shortcut; keep the reference form as the oracle in tests). Edge cells: replicate the border or leave them NoData; GDAL offers `-compute_edges` [GDAL].

### 1.6 Azimuth 315, altitude 45

The default light is from the north-west (azimuth 315 degrees, clockwise from north) at 45 degrees above the horizon; Esri and GDAL both default to it [EsriHS][GDAL]. Light from the upper left matches how readers expect shadow to fall; lit from the south (bottom), many readers see relief inverted, valleys as ridges [Imhof1982, ch. on light direction][Patterson-SR]. Imhof and Patterson recommend adjusting the azimuth locally (roughly between 270 and 360) so that major ridges running along the light direction still get shaded on one side [Imhof1982][Patterson-SR]. The habit is older than computed hillshade: Thrower ties north-west light to the 19th-century Swiss Dufour map, which drew heavier hachures on south and east slopes (Maps and Civilization, ch. 6) (book fact, not cross-checked).

### 1.7 Multidirectional hillshade

One light leaves ridges parallel to it flat. Multidirectional shading blends several azimuths. Mark (1992) weighted the illumination from 225, 270, 315 and 360 degrees by aspect so each slope gets lit from the most revealing direction [Mark1992]; GDAL's `-multidirectional` implements that method [GDAL]. Esri's multidirectional option combines light from six directions (count checked 2026-11-16 in the ArcGIS Pro Hillshade function help, https://pro.arcgis.com/en/pro-app/3.3/help/analysis/raster-functions/hillshade-function.htm; the weights are not published there, unverified) [EsriHS]. Simple stdlib version: compute shades at several azimuths and take a weighted mean with weights `w_k = sin(aspect - az_k)**2` for az_k in 225, 270, 315, 360 (checked 2026-11-16 in GDAL's implementation of [Mark1992], apps/gdaldem_lib.cpp `GDALHillshadeMultiDirectionalAlg`, https://github.com/OSGeo/gdal/blob/master/apps/gdaldem_lib.cpp; the USGS PDF of Mark's report answered 403).

### 1.8 Z-factor and lat/lon grids

The z-factor converts vertical units to horizontal units and can exaggerate relief [EsriHS]. If the DEM is in geographic coordinates (cell size in degrees, elevation in metres) the slope is nonsense unless corrected. Derived rule (Esri's page, now https://doc.esri.com/en/arcgis-pro/latest/tool-reference/3d-analyst/applying-a-z-factor.html, gives only a table, which this reproduces) [EsriZ]:

```
z = 1 / (111320 * cos(radians(latitude)))
```

Esri's own table lists 0.00000898 at the equator and 0.00001792 at 60 degrees [EsriZ]. Better for large extents: compute the x spacing per row (`cs_x = cs_deg * 111320 * cos(lat_row)`, `cs_y = cs_deg * 110574`) and use separate `cs_x`, `cs_y` in the derivatives; GDAL's `-s 111120` scale option is the single-value equivalent [GDAL]. Vertical exaggeration for small-scale maps of flat regions is common (2x to 5x; unverified range), and Patterson suggests exaggerating lowlands more than mountains [Patterson-SR].

### 1.9 Making shading look good

- Generalise first. Shading a full-resolution DEM at small scale gives noise; resample or blur the DEM to the output pixel size, or use a Gaussian or median filter [Patterson-SR]. Leonowicz, Jenny and Hurni's Terrain Sculptor generalises DEMs for this reason [Leonowicz2010].
- Lighten flats. Pure Lambert shading makes flat land mid-grey; cartographers lift it toward white so tints show through [Patterson-SR]. A curve such as `out = 255 - (255 - shade) * k` or a gamma on the shade layer is common.
- Blend with multiply over tints, at about 50-80 percent opacity (practice figure, no single source; tunable default). In SVG: `mix-blend-mode: multiply` on the shade `<image>`, or composite to PNG in Python.
- Aerial perspective: Imhof makes high peaks more contrasty and low land paler and hazier [Imhof1982]; Jenny and Patterson describe implementing this digitally [Jenny-Patterson2007].

## 2. Contours

Depth contours are older than land contours: manuscript ones in 1584 and 1697 and an engraved river chart in 1729, against 1791 for land contours over a large area, which became usual in national surveys only from about 1850 (Thrower, Maps and Civilization, ch. 6-7) (book facts, not cross-checked). First-use years for every relief method: [cartography-design.md](cartography-design.md) section 1.6.

### 2.1 Marching squares

Treat the DEM as a grid of cell corners. For each square of four samples and a level `L`, build a 4-bit index from which corners are above `L` (16 cases); each case maps to zero, one or two segments whose endpoints are linearly interpolated along the edges [Lorensen1987 (marching cubes, the 3D parent)][Maple-MS (unverified secondary)]:

```
t = (L - z0) / (z1 - z0)      # position along an edge from corner 0 to 1
p = p0 + t * (p1 - p0)
```

Cases 5 and 10 (diagonal corners above) are saddles and ambiguous. Resolve with the mean of the four corners: if the centre is above `L`, connect around the high corners' side, else the other way. Do this consistently or contours will cross (checked 2026-11-16: Wikipedia "Marching squares" gives the centre-average rule for the ambiguous cases, https://en.wikipedia.org/wiki/Marching_squares; secondary source). Then join segments into polylines by matching endpoints (hash rounded coordinates), close rings, and simplify (Douglas-Peucker) at roughly the output pixel tolerance [DP1973].

Checkable rules:
- Contours at different levels never cross or touch (test by segment intersection).
- A sample exactly equal to `L` must be counted consistently, e.g. treat `z >= L` as above; nudge levels by a tiny epsilon if needed.
- Closed contours must close; open ones must end on the data edge.

### 2.2 Interval choice

USGS topographic maps use intervals tied to scale and relief; 1:24,000 quads use a basic interval of 5, 10, 20, 40 or 80 ft chosen per sheet for the terrain, and US Topo allows 100 ft or more in steep areas [USGS-Topo] (USGS manual 800-2, checked 2026-11-16 via the UNT web archive: https://webarchive.library.unt.edu/eot2008/20090512131010/http:/www.usgs.gov/usgs-manual/800/800-2.html). A workable rule: pick the interval from the series 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500 so that the steepest common slope gives lines no closer than about 0.2-0.3 mm on the page, and the map has roughly 10-30 levels (practice figure, no single source; tunable default). Imhof notes contour spacing is set by the scale and by the minimum separation the eye can resolve [Imhof1982].

Compute the minimum spacing: horizontal distance between lines on the page = `interval / tan(slope) / scale_denominator`. Reject an interval if that is below the threshold over more than a few percent of the area.

### 2.3 Index and supplementary contours

Every fifth contour is an index contour, drawn heavier and labelled; USGS uses this convention [USGS-Topo]. Typical weights: intermediate about 0.1-0.15 mm, index about 0.25-0.3 mm, in brown. Corrected 2026-11-16 from the USGS US Topo elevation specification (https://www.usgs.gov/ngp-standards-and-specifications/us-topo-cartographic-specifications-elevation): index 0.504 pt (about 0.18 mm) RGB 145,88,40, intermediate 0.216 pt (about 0.08 mm) RGB 179,134,89, supplemental 0.36 pt. Supplementary contours at half interval may be dashed in flat areas [USGS-Topo]. Depression contours carry ticks pointing downslope [USGS-Topo].

### 2.4 Contour labels

Labels sit on index contours, read uphill (top of the letters toward higher ground) and break the line under them [Imhof1982][USGS-Topo] (2026-11-16: the US Topo elevation spec only says index labels are "straight and centered on line", 6 pt Segoe UI Italic with a 0.70 pt halo; uphill reading not stated there, unverified). Place them in a staggered "ladder" so a reader can follow values up a slope, avoid sharp bends, and never upside down relative to the page beyond what uphill reading forces (practice; unverified as a stated rule).

## 3. Hypsometric tints

Layer tints colour elevation bands. The classic green-lowland to brown-highland scheme confuses readers into reading green as vegetation and brown as dry [Patterson-Jenny2011]. Patterson and Jenny's cross-blended tints vary the lowland colour by climate (humid green vs arid tan) and blend between them [Patterson-Jenny2011]. Imhof preferred light-to-dark or pale-highs schemes combined with shading so that tints do not fight shadows [Imhof1982].

Implementation rules:
- Define tints as a list of `(elevation, rgb)` stops and interpolate in a perceptual space (CIELAB or Oklab) rather than RGB to avoid muddy midpoints (practice figure, no single source; tunable default).
- Use class breaks that follow the data: more classes low, fewer high, often geometric (e.g. 0, 100, 200, 500, 1000, 2000, 4000 m) because area per elevation band falls off with height (practice figure, no single source; tunable default).
- Water is not a tint class; bathymetric tints darken with depth [Patterson-SR].
- Shade on top with multiply; tints must stay distinguishable after shading (test with a contrast check per class against its darkest shaded value).
- Pick the ramp by climate, not elevation alone: arid lowlands get tan cross-blended tints so green is not read as lush; record whether tints are discrete bands or continuous, since discrete bands read better for values and continuous for form (Kimerling et al., Map Use, ch. 10).
- Period preset: the International Map of the World at 1:1,000,000 (proposed 1891, specified 1909) used contours at 200, 500 and 1,000 m and then every thousand, with tints from green lowland through ochre to brown (Thrower, Maps and Civilization, ch. 8) (book fact, not cross-checked). It is a period look, not a default: the green-to-brown warning above still holds.
- A tint legend is titled as elevation, so that green is not read as lush and brown as barren (Monmonier, How to Lie with Maps, 1991 ed., ch. 2, ch. 10).

## 4. Hachures

Hachures are short strokes drawn down the line of steepest slope; denser and thicker strokes mean steeper ground. Lehmann's 1799 system fixed the ratio of black to white by slope, with 45 degrees fully black (often cited; blocked 2026-11-16: Wikipedia "Hachure map" names only Lehmann 1799 and thicker strokes for steeper slopes; the Geographia Technica 2017 hachure paper, https://doi.org/10.21163/GT_2017.121.08, gives 5-45 degrees in 8 classes but credits that range to later work; its PDF had no readable text and academia.edu answered 403) [Imhof1982][Kennelly2008]. Shadow hachures (Dufour map of Switzerland) vary weight with illumination instead of slope [Imhof1982].

Algorithm sketch (after Kennelly's review and modern digital hachure work [Kennelly2008][KennellyKimerling2000]):
1. Compute contours at a small interval as guide lines.
2. Seed points along each contour with spacing inversely related to slope.
3. From each seed, trace downhill along the gradient until the next contour; that segment is one hachure.
4. Stroke width proportional to slope (Lehmann) or to `1 - shade` (shadow hachures).
5. Drop strokes on slopes below a threshold (flat land stays blank).

Check: strokes never cross one another; minimum gap between strokes at least the stroke width.

## 5. Imhof and Swiss-style relief

Eduard Imhof's "Kartographische Geländedarstellung" (1965), translated as "Cartographic Relief Presentation" (1982; Esri Press reprint 2007) is the standard reference [Imhof1982]. Swiss-style relief, as practised in Swiss school atlases and national maps, combines [Imhof1982][Jenny2001][Patterson-SR]:

- shading from the upper left, with local adjustment of light direction to model each landform;
- aerial perspective: high ground more contrast, low ground paler and bluish-grey;
- warm (yellowish) sunlit slopes and cool (bluish-grey or violet) shaded slopes;
- skeletal lines and rock drawing for cliffs at large scale;
- generalisation of landforms rather than literal DEM fidelity.

Jenny's work made "analytical" shading interactively adjustable to imitate manual shading [Jenny2001]. Recent work trains neural networks on manual Swiss relief (Jenny, Heitzler, Singh, Farmakis-Serebryakova, Liu, Hurni, "Cartographic relief shading with neural networks", IEEE TVCG 2021) [Jenny2021]; out of scope for stdlib, but the target look.

Stdlib approximation (mapwright's own recipe, not taken from any source):
1. Generalise DEM (blur scaled to output resolution).
2. Hillshade at 315/45 plus multidirectional blend.
3. Elevation-dependent contrast: `shade' = 128 + (shade - 128) * (0.6 + 0.4 * norm_elev)`.
4. Colour: map shade to a ramp from blue-grey (shadow) through neutral to pale yellow (light).
5. Multiply over pale hypsometric tints.

## 6. Tanaka illuminated contours

Tanaka Kitirô's relief contour method draws contours with width proportional to how directly they face the light, coloured white on lit sides and black on shadowed sides, over a mid-grey ground [Tanaka1950]. Line width varies with `|cos(theta)|`, where theta is the angle between the contour's normal and the light azimuth [Tanaka1950][Kennelly-Kimerling2001].

Per segment:

```
nx, ny = normal pointing downhill (perpendicular to segment)
theta = angle between (nx, ny) and the light vector from azimuth 315
w = w_min + (w_max - w_min) * abs(cos(theta))
colour = white if cos(theta) facing light else black
```

Contours must be fine-interval and dense to work. Kennelly and Kimerling modernised the method with GIS [Kennelly-Kimerling2001]. Pure SVG: emit one `<line>` or short `<path>` per segment, or group by quantised width to keep file size down.

## 7. Label placement: cartographic rules

### 7.1 Imhof's principles

Imhof's 1975 paper "Positioning names on maps" set the rules most automated systems encode [Imhof1975]:
- Names must be legible, discriminable and quickly found.
- A name must clearly belong to its feature (association).
- Names must not cover or cut other features or names more than unavoidable.
- Names should reflect the extent and hierarchy of the feature (type size and spacing).
- Names should not be evenly scattered nor crowded; density should follow the map.

### 7.2 Point labels: position priority

Yoeli (1972) and Imhof (1975) rank positions around a point; upper right is preferred [Yoeli1972][Imhof1975]. A common eight-position order used in the literature and in tools is (numbering after Christensen et al. 1995 and many textbooks; exact order varies by author, unverified):

```
1 upper right   2 upper left   3 lower right   4 lower left
5 right (centred vertically)    6 left
7 above (centred)               8 below
```

Some authorities rank lower right above upper left, or right-centre second (Slocum et al.; unverified). Implement the order as data so it can be switched. Further rules [Imhof1975]:
- Labels for coastal or riverside places go entirely on land or entirely on the water side of the shore, not straddling it.
- Avoid placing a settlement name across a river or border from its symbol.
- Offset from the symbol by a small fixed gap, about 0.5-1 mm (practice figure, no single source; tunable default).
- A point label sits beside its symbol, never on a text row running through the symbol (Tyner, Principles of Map Design, ch. 3).
- Each point label is nearer its own symbol than any other symbol (test: nearest symbol to the label box is its own) (Brewer, Designing Better Maps, ch. 7).
- Labels placed left of the symbol are right-justified, so the ragged edge is away from the symbol (Brewer, Designing Better Maps, ch. 7).
- Coastal places are labelled in the water where there is room; no label crosses a land-water edge (Brewer, Designing Better Maps, ch. 7).
- A water-area label lies wholly inside or wholly outside the water body, never across the shoreline; water labels are italic (Tyner, Principles of Map Design, ch. 3).
- When no candidate fits, fall back to a callout: the label moved to open space with a thin leader line to the symbol (Tyner, Principles of Map Design, ch. 3). Monmonier names the same fix for a label moved away from its feature: a tie line or a key number (How to Lie with Maps, 1991 ed., ch. 3).

### 7.3 Line labels

Rules from Imhof and later systems [Imhof1975][Edmondson1996]:
- Text follows the line's curve, set above the line (or between for wide rivers), on gentle stretches; avoid sharp bends.
- Letter spacing may increase but stays even; never spread so far the word breaks apart (Imhof warns against excessive spacing).
- Read left to right; text on near-vertical lines reads bottom to top on the left side of the map and is commonly allowed to read top to bottom on the right (convention; unverified).
- Repeat long features' names at intervals (rivers, roads) rather than one huge spacing.
- Rivers: label upstream-readable direction is less important than not being upside down (rule: flip the path if the mean direction points leftward).
- Line labels sit a small offset gap from the line, on a smoothed copy of the path; no glyph is upside down, and the angle change between adjacent glyphs is bounded (default 30 degrees) (Brewer, Designing Better Maps, ch. 7).
- Period label mode for chart styles: on a portolan chart the place names sit on the land side at right angles to the shore, in one unbroken run round the coast; names of nearby islands run the other way; the more important places are in red, and these are not only ports (Harley and Woodward, History of Cartography vol. 1, ch. 19, p. 377) (book fact, not cross-checked). Check: label angle within a limit of the local coast normal, anchor on land.

### 7.3a Lines under labels (ruling)

Brewer allows a line to be broken (knocked out) under a label (Brewer, Designing Better Maps, ch. 7); Tyner forbids it: no label breaks a line and no line crosses a label, fixed by a halo, a mask or a callout (Tyner, Principles of Map Design, ch. 3). Ruling 2026-11-14: this is a per-style setting, `label_line_knockout`. `true` (Brewer) clears line art under each glyph; `false` (Tyner) moves the label or uses a callout so the line stays whole and uncrossed. Fantasy and engraved styles default to `true` (Blando also knocks out art under labels, Fantasy Mapmaker, ch. 6); reference and topographic styles default to `false`. The proof check reads the setting.

### 7.4 Area labels

Name spans the area, follows its main axis, curved in a gentle arc if the shape is curved, spaced out letters for large areas [Imhof1975]. Algorithms use the medial axis or skeleton of the polygon to find a baseline [Barrault2001 (unverified citation)]. Simple stdlib version: principal axis from the polygon's second moments; fit a circular arc or quadratic through skeleton points; spread letters to 60-80 percent of the axis length (practice figure, no single source; tunable default). Small areas get a horizontal label inside or a point-style label outside.

### 7.5 Type choice

Conventions [Imhof1975][Imhof1982][USGS-Topo]:
- Hydrography (seas, lakes, rivers) in italic, often serif, in blue.
- Landforms (mountains, ranges) in a different style, often upright or sans, brown or black; ranges letterspaced.
- Settlements in upright type, size by population class.
- Hierarchy shown by size, weight, case (capitals for larger regions) and spacing, with no more than a few size steps.
- Minimum legible size: about 6-7 pt for print on paper; 5 pt is a hard floor for high-quality print (practice figure, no single source; tunable default; 2026-11-16 the US Topo spec sets contour labels at 6 pt, consistent with the 6 pt floor). For screen output use 10-11 px minimum (practice figure, no single source; tunable default).
- Halos (a thin background-coloured stroke behind text) improve legibility over relief; keep them narrow (about 1-1.5 px or 0.3 mm; 2026-11-16 the US Topo spec uses a 0.70 pt, about 0.25 mm, halo on 6 pt contour labels) and use `paint-order: stroke` in SVG [SVG2].
- Tactile labels: braille plus large print (the book's example is 16 pt sans with Marburg Medium braille), horizontal and straight unless following a line, repeated along long lines, never over key detail; names too long for braille become codes keyed in the legend (van Altena and Wabinski, Tactile Mapping, 2025, ch. 5-6).
- Pale icons on a pale ground get a knock-out (paper-coloured) outline so they do not merge into it, the icon form of a halo (Hancock et al., The Art of Map Illustration, 2017, sec. 16) (book rule, unverified).

## 8. Curved text in SVG

`<textPath href="#id">` renders text along a `<path>` [SVG11][SVG2]. Key attributes:
- `startOffset="50%"` with `text-anchor="middle"` centres the label on the path.
- `side="right"` flips text to the other side (SVG 2, experimental; MDN marks it "limited availability", not Baseline, as of 2026-11-14: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/side). Instead, reverse the path's point order in Python when it runs right to left.
- `method="stretch"` and `spacing="auto"` are in the spec; MDN browser-compat-data lists both attributes as supported in Chrome, Firefox and Safari but does not record whether `stretch` renders differently from `align`, and `side` and `path` are Firefox-only or Firefox and Safari 27.3 (https://github.com/mdn/browser-compat-data/blob/main/svg/elements/textPath.json, checked 2026-11-16), so test output in the target viewer; do letter spacing with `letter-spacing` or by computing glyph positions yourself.
- Glyphs falling off the path end are not rendered [SVG11]; so the path must be longer than the text.

Text width without a font engine: stdlib Python cannot measure glyphs. Options: ship a per-font advance-width table (parse the TTF `hmtx` table with `struct`: one advanceWidth (uint16, font units; divide by `head.unitsPerEm`) per glyph up to `hhea.numberOfHMetrics`, after which the last advance repeats [OpenType], checked 2026-11-16) or use an average width factor (about 0.5-0.6 em per character for typical sans; practice figure, no single source). Collision tests depend on this, so prefer the `hmtx` table.

For PNG output, curved text needs per-glyph rotation; place each glyph at arc length `s_i` along the path, rotate by the tangent angle there.

Curvature limit: reject a candidate line position if the turning angle between adjacent glyphs exceeds about 20-30 degrees, or if total curvature over the label exceeds about 45-60 degrees (practice figure, no single source; tunable default; cf. Edmondson et al. on line label quality).

## 9. Collision handling and algorithms

### 9.1 The problem

Point-feature label placement (choose one of k positions per point so labels do not overlap) is NP-hard [Marks-Shieber1991][Formann-Wagner1991]. So all practical methods are heuristics.

### 9.2 Candidate model

For each feature generate candidates with a cost: position rank penalty (7.2), overlap with other features, distance from line or area axis, curvature. Represent each candidate as a rectangle (or a chain of rectangles for curved text). A stdlib spatial index: a uniform grid of buckets sized to the median label; each candidate stored in all buckets it touches.

### 9.3 Algorithms

- Greedy: sort features by priority (importance, then number of free candidates ascending), place the cheapest non-conflicting candidate, drop the label if none. Fast, decent [Christensen1995].
- Gradient descent / local search: start from a placement, repeatedly move one label to the position that most lowers total cost [Hirsch1982][Christensen1995].
- Simulated annealing: random moves, accept worse moves with probability `exp(-delta/T)`, cool `T` geometrically. Christensen, Marks and Shieber (1995, ACM TOG 14(3):203-232) compared methods and found annealing gave the best quality for reasonable time, beating greedy, gradient descent, Hirsch's method and Zoraster's integer programming approach [Christensen1995]. Their schedule: initial T set so that a cost increase of 1 is rejected (undone) with probability 2/3; at most 20n repositionings per temperature (n = point count), or fewer if 5n changes succeed first; then T drops 10 percent; at most 50 stages, stopping early if a stage accepts no move (pp. 218-219, scanned copy read 2026-11-16 at https://www.cs.du.edu/~snarayan/sada/maplabel/classes/docs/mapRef7.pdf).
- Rule-based expert systems (Ahn and Freeman's AUTONAP, Doerschler and Freeman) and the commercial Maplex/Esri label engine use rule sets plus optimisation [Freeman2005][EsriMaplex].
- Wagner and Wolff (1997) keep the factor-1/2 guarantee of Formann and Wagner's algorithm for the four-position point model while placing labels much closer to the optimum in practice [Wagner-Wolff1997]. Corrected 2026-11-16 (abstract checked by search): that paper is not about sliding labels; slider models come from van Kreveld, Strijk and Wolff, "Point set labeling with sliding labels", SoCG 1998.

Annealing in stdlib Python is fine for hundreds to a few thousand labels; cost function is the hot loop, so keep conflicts precomputed as candidate-pair lists.

### 9.4 Cost function (suggested)

```
cost = sum over placed labels of:
    W_rank * rank_penalty(position)
  + W_feat * area_overlapping_other_features
  + W_lab  * number_of_label_overlaps * BIG
  + W_drop * (1 if not placed) * feature_priority
```

Weights are design choices (no source); make them configurable.

## 10. What automated placement gets right and wrong

Right: no overlaps, consistent positions for points, fast relabelling at any scale, reliable for dense point sets [Christensen1995]. Wrong or weak (from comparisons with manual work; general claims, partly unverified):
- Association: labels placed legally but ambiguous between two symbols.
- Line labels on wiggly sections; poor river names in bends.
- Area names that ignore shape (straight text across a crescent).
- Uniform look: no deliberate hierarchy or rhythm, names spread evenly instead of grouped as Imhof asked [Imhof1975].
- Dropping important names to satisfy no-overlap; a human would move a lesser name or the feature.
- Crossing shoreline and borders with point labels.
- Ignoring background contrast (dark relief behind dark text).

Mitigations: priority-ordered dropping, association checks (nearest symbol to the label centre must be its own), halo or contrast checks, and a manual override file.

## 11. Checkable rules for mapwright tests

Each is a pure function over the rendered geometry:

1. No label-label overlap: rectangles (or glyph boxes for curved text) intersect pairwise with zero area. Allow an optional padding of 0.5 mm.
2. No edge cut: every label box lies inside the map frame minus a margin (default 1 mm).
3. Minimum size: every text element's size >= 6 pt (print profile) or >= 10 px (screen profile); halo width <= 0.4 x font size (unverified ratio; the US Topo labels use about 0.12).
4. Association: for each point label, the nearest point symbol to the label's anchor is its own feature, and the gap is <= 2 mm. Swapped labels are a classic slip (Monmonier, How to Lie with Maps, 1991 ed., ch. 4).
5. Feature overlap: point labels do not cover other point symbols; optional limit on covered line length.
6. Line labels: total turning angle within limit (section 8); text not upside down (glyph rotation in [-90, 90] degrees).
7. Curved text fits: path length >= text length + 2 x padding.
8. Contours: no crossings; levels sorted; index every Nth.
9. Hillshade oracle: a synthetic plane `z = x` lit from 90 degrees has the expected value from the reference formula within 1 unit; lit from 270 degrees is darker.
10. Z-factor: for a geographic DEM, slope on a known 45-degree synthetic ramp computes to 45 +/- 1 degrees at latitudes 0 and 60.
11. Hydrography type is italic; check styles by feature class.
12. Water straddle: no label box intersects a land-water edge; water-area labels are wholly inside or outside their water polygon (Brewer, Designing Better Maps, ch. 7) (Tyner, Principles of Map Design, ch. 3).
13. Line crossing: if the style's `label_line_knockout` is false, no line passes through any label box; if true, the line has a gap under each crossing label (Tyner, Principles of Map Design, ch. 3) (Brewer, Designing Better Maps, ch. 7).
14. Glyph angle: adjacent glyphs on a line label differ by at most the style's bound (default 30 degrees) (Brewer, Designing Better Maps, ch. 7).

## Open questions

- Exact point-position order to default to (Imhof vs Yoeli vs Christensen numbering).
- GDAL's multidirectional weighting formula: copy after reading GDAL docs or source.
- Font metrics in stdlib: parse TTF `hmtx` (needs a bundled font) or ship metric tables.
- Whether to support SVG `side` attribute or always reverse paths.

## Sources

All accessed 2026-11-14 unless marked unverified (cited from memory, not opened this session).

- [Barrault2001] Barrault, M., Lecordix, F. "An automated system for linear feature name placement which complies with cartographic quality criteria." AutoCarto 12, 1995, https://cartogis.org/docs/proceedings/archive/auto-carto-12/pdf/an-automated-system-for-linear-feature-name-placement.pdf (found 2026-11-16; the key keeps its old year; Barrault's real 2001 paper is on area labels, "A methodology for placement and evaluation of area map labels", Computers, Environment and Urban Systems 25. Earlier note: Crossref finds only Barrault, "An automated system for name placement which complies with cartographic quality criteria: The hydrographic network", COSIT 1997, LNCS, pp. 499-500, https://doi.org/10.1007/3-540-63623-4_71; cite that if the 2001 paper cannot be found; re-searched on Crossref 2026-11-16, still no 2001 paper, left unverified)
- [Christensen1995] Christensen, J., Marks, J., Shieber, S. "An empirical study of algorithms for point-feature label placement." ACM Transactions on Graphics 14(3):203-232, 1995.
- [DP1973] Douglas, D., Peucker, T. "Algorithms for the reduction of the number of points required to represent a digitized line or its caricature." The Canadian Cartographer 10(2):112-122, 1973.
- [Edmondson1996] Edmondson, S., Christensen, J., Marks, J., Shieber, S. "A general cartographic labelling algorithm." Cartographica 33(4):13-24, 1996.
- [EsriHS] Esri, "How Hillshade works", ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/latest/tool-reference/3d-analyst/how-hillshade-works.htm
- [EsriSlope] Esri, "How Slope works", ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/latest/tool-reference/3d-analyst/how-slope-works.htm
- [EsriZ] Esri, "Setting the z-factor parameter correctly" (ArcGIS blog and help table of z-factors by latitude). Table checked 2026-11-16 at https://desktop.arcgis.com/en/arcmap/latest/tools/spatial-analyst-toolbox/applying-a-z-factor.htm (0.00000898 at 0°, 0.00001792 at 60°, metres); the blog itself answered 403.
- [EsriMaplex] Esri, "Labeling basics", ArcGIS Pro documentation, https://doc.esri.com/en/arcgis-pro/latest/help/mapping/text/labeling-basics.html (checked 2026-11-16: Maplex is the default engine, with priorities, weights and a draft-quality mode that spends less time resolving conflicts; its internal rules are not published there)
- [Formann-Wagner1991] Formann, M., Wagner, F. "A packing problem with applications to lettering of maps." Proc. 7th ACM Symposium on Computational Geometry, 281-288, 1991.
- [Freeman2005] Freeman, H. "Automated cartographic text placement." Pattern Recognition Letters, 2005, https://doi.org/10.1016/j.patrec.2004.10.023 (citation checked via Crossref 2026-11-16; corrected from a 1995 "On the automated labeling of maps" in Shape, Structure and Pattern Recognition, which neither Crossref nor a web search could find).
- [GDAL] GDAL, "gdaldem" documentation. https://gdal.org/programs/gdaldem.html
- [Hirsch1982] Hirsch, S. "An algorithm for automatic name placement around point data." The American Cartographer 9(1):5-17, 1982.
- [Horn1981] Horn, B.K.P. "Hill shading and the reflectance map." Proceedings of the IEEE 69(1):14-47, 1981.
- [Imhof1975] Imhof, E. "Positioning names on maps." The American Cartographer 2(2):128-144, 1975. https://doi.org/10.1559/152304075784313304 (citation checked via Crossref 2026-11-16)
- [Imhof1982] Imhof, E. Cartographic Relief Presentation. Ed. H.J. Steward. de Gruyter, 1982; Esri Press reprint 2007.
- [Jenny2001] Jenny, B. "An interactive approach to analytical relief shading." Cartographica 38(1-2):67-75, 2001.
- [Jenny-Patterson2007] Jenny, B., Patterson, T. "Introducing plan oblique relief." Cartographic Perspectives 57, 2007, pp. 21-40, https://doi.org/10.14714/cp57.279 (citation checked via Crossref 2026-11-16; that it holds the aerial perspective discussion is still unverified).
- [Jenny2021] Jenny, B., Heitzler, M., Singh, D., Farmakis-Serebryakova, M., Liu, J.C., Hurni, L. "Cartographic relief shading with neural networks." IEEE TVCG 27(2):1225-1235, 2021.
- [Jones1998] Jones, K.H. "A comparison of algorithms used to compute hill slope as a property of the DEM." Computers & Geosciences 24(4):315-323, 1998. https://doi.org/10.1016/S0098-3004(98)00032-6 (citation checked via Crossref 2026-11-16)
- [Kennelly2008] Kennelly, P. "Terrain maps displaying hill-shading with curvature." Geomorphology 102(3-4), 2008, pp. 567-577, https://doi.org/10.1016/j.geomorph.2008.05.046 (citation checked via Crossref 2026-11-16; "his hachure reviews" not identified, unverified).
- [Kennelly-Kimerling2001] Kennelly, P., Kimerling, A.J. "Modifications of Tanaka's illuminated contour method." Cartography and Geographic Information Science 28(2):111-123, 2001.
- [Leonowicz2010] Leonowicz, A., Jenny, B., Hurni, L. "Terrain Sculptor: generalizing terrain models for relief shading." Cartographic Perspectives 67, 2010.
- [Lorensen1987] Lorensen, W., Cline, H. "Marching cubes: a high resolution 3D surface construction algorithm." SIGGRAPH 1987.
- [Maple-MS] Wikipedia, "Marching squares", https://en.wikipedia.org/wiki/Marching_squares (checked 2026-11-16; secondary).
- [Mark1992] Mark, R.K. "A multidirectional, oblique-weighted, shaded-relief image of the Island of Hawaii." USGS Open-File Report 92-422, 1992.
- [Marks-Shieber1991] Marks, J., Shieber, S. "The computational complexity of cartographic label placement." Harvard TR-05-91, 1991.
- [OpenType] Microsoft, OpenType specification, "hmtx — Horizontal Metrics Table". https://learn.microsoft.com/en-us/typography/opentype/spec/hmtx
- [Patterson-SR] Patterson, T. shadedrelief.com, "Shaded relief" tutorials and design notes. https://www.shadedrelief.com
- [Patterson-Jenny2011] Patterson, T., Jenny, B. "The development and rationale of cross-blended hypsometric tints." Cartographic Perspectives 69:31-46, 2011.
- [KennellyKimerling2000] Kennelly, P., Kimerling, A.J. "Desktop hachure maps from digital elevation models." Cartographic Perspectives 37, 2000, https://cartographicperspectives.org/index.php/journal/article/download/cp37-kennelly-kimerling/pdf/3966 (found 2026-11-16 by search; replaces a "Pegg2012" citation that no search could find; see also Eric Fischer's 2012 digital hachures via https://persquaremile.com/2012/04/26/digital-hachures)
- [SVG11] W3C, Scalable Vector Graphics 1.1 (Second Edition), "Text on a path". https://www.w3.org/TR/SVG11/text.html#TextOnAPath
- [SVG2] W3C, SVG 2, "Text" chapter (textPath `side`, `paint-order`). https://www.w3.org/TR/SVG2/text.html
- [Tanaka1950] Tanaka, K. "The relief contour method of representing topography on maps." Geographical Review 40(3):444-456, 1950.
- [USGS-Topo] USGS, "Topographic Map Symbols" booklet and US Topo standards. https://pubs.usgs.gov/gip/TopographicMapSymbols/topomapsymbols.pdf
- [Wagner-Wolff1997] Wagner, F., Wolff, A. "A practical map labeling algorithm." Computational Geometry 7:387-404, 1997.
- [Yoeli1972] Yoeli, P. "The logic of automated map lettering." The Cartographic Journal 9(2):99-108, 1972. https://doi.org/10.1179/caj.1972.9.2.99 (citation checked via Crossref 2026-11-16)
- [ZT1987] Zevenbergen, L.W., Thorne, C.R. "Quantitative analysis of land surface topography." Earth Surface Processes and Landforms 12(1):47-56, 1987.
