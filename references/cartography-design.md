# Cartography: history, conventions and design rules

Reference for mapwright. It covers where map conventions came from, what a reader expects to find on a map, and design rules the plugin can check in code. Sources are cited inline. Claims written from established references without a fresh web check in this session are marked "(unverified)". Accessed 2026-11-14.

## 1. Short history

### 1.1 Oldest surviving maps

- **Babylonian Map of the World (Imago Mundi)**, clay tablet, c. 6th century BCE, British Museum BM 92687. It shows Babylon on the Euphrates inside a circular "bitter river" (ocean), with triangular outer regions. It is a cosmological diagram more than a survey. Source: British Museum collection record, https://www.britishmuseum.org/collection/object/W_1882-0714-509.
- **Older candidates** exist: the Çatalhöyük wall painting (c. 6600 BCE) has been read as a town plan with a volcano, but the reading is disputed (Meece, "A bird's eye view - of a leopard's spots", Anatolian Studies 56, 2006) (blocked: paywalled). The Turin Papyrus Map (c. 1160 BCE) shows a route to quarries in the Wadi Hammamat and is often called the oldest surviving geological/topographic map (Harrell & Brown, "The oldest surviving topographical map from ancient Egypt", JARCE 29, 1992, pp. 81-105; the "oldest geological map" claim is their separate paper in Journal of Geology 100, 1992, pp. 3-18; citations checked via https://zenon.dainst.org/Record/000529918/Description, papers not opened).
- **Ptolemy's Geography** (c. 150 CE) gave coordinates in latitude and longitude for about 8,000 places and described two projections. It survives through Byzantine manuscripts of the late 13th century; the maps in them were redrawn from the text. Source: J. L. Berggren and A. Jones, *Ptolemy's Geography*, Princeton UP, 2000.
- The standard scholarly survey of all of this is *The History of Cartography* (ed. J. B. Harley and D. Woodward, Univ. of Chicago Press, vol. 1 1987 onward), free online: https://press.uchicago.edu/books/HOC/index.html.

### 1.2 Medieval and portolan charts

- **Mappae mundi** (e.g. Hereford, c. 1300; about 1290 in Harley and Woodward, vol. 1, ch. 18) are religious and encyclopedic, not navigational. The Hereford map is a T-O map: east at top, Jerusalem at centre. Source: Hereford Cathedral, https://www.themappamundi.co.uk/ (checked 2026-11-16: "around the year 1300", east at top, Jerusalem at centre).
- Corrected 2026-11-15: Jerusalem at the centre is not the medieval norm. This file used to state it for all mappae mundi. Most maps outside the T-O diagrams do not have it. It marks maps of the later 13th and 14th centuries (Hereford, Ebstorf, a psalter map), roughly 1250 to 1400, and 15th-century makers dropped it as the known world outgrew the circle (Harley and Woodward, History of Cartography vol. 1, ch. 18) (book fact, not cross-checked).
- Four classes of mappa mundi: tripartite (the T-O family; the T is the Don, the Nile and the Mediterranean), zonal (north or south up, five climate zones), quadripartite (a fourth continent in the south) and transitional (14th and 15th century, with a chart-style Mediterranean). About 1,100 survive, some 900 of them as small diagrams in manuscript books; a wall-size map is the exception. They rarely have a graticule or a stated scale (Harley and Woodward, vol. 1, ch. 18) (book facts, not cross-checked). Presets: [fantasy-maps.md](fantasy-maps.md) section 2.1.
- **Portolan charts** appear in the Mediterranean from the late 13th century; the Carta Pisana (c. 1275, BnF) is usually named the oldest surviving one. They are drawn on vellum, with networks of rhumb lines radiating from wind roses, coastal place names written perpendicular to the coast, and a scale bar. Accuracy of the Mediterranean outline is remarkably high for the time. Source: Tony Campbell, "Portolan Charts from the Late Thirteenth Century to 1500", in Harley & Woodward vol. 1 ch. 19, 1987, https://press.uchicago.edu/books/HOC/HOC_V1/HOC_VOLUME1_chapter19.pdf. Thrower dates the Pisan chart about 1290 (Maps and Civilization, ch. 4); both dates are estimates. The oldest dated chart is of 1311 (Harley and Woodward, vol. 1, ch. 19; Thrower gives 1310) (book facts, not cross-checked). How the rhumb network is built: [fantasy-maps.md](fantasy-maps.md) section 3.4.
- Conventions portolans left behind: the compass rose, bar scale, and name placement along coasts. The drawn compass rose is a Catalan addition first seen on the atlas of 1375; before that a wind rose is a bare crossing of lines (Harley and Woodward, vol. 1, ch. 19) (book fact, not cross-checked).

### 1.3 Mercator and the printed atlas

- **Gerardus Mercator, 1569**, world map "Nova et aucta orbis terrae descriptio". Its projection is conformal: rhumb lines (constant compass bearings) are straight lines, which suits navigation. Scale grows with latitude as sec(φ), so Greenland looks about the size of Africa although Africa is about 14 times larger. Source: John P. Snyder, *Flattening the Earth: Two Thousand Years of Map Projections*, Univ. of Chicago Press, 1993; Snyder, *Map Projections: A Working Manual*, USGS Professional Paper 1395, 1987, https://pubs.usgs.gov/publication/pp1395.
- **Ortelius, Theatrum Orbis Terrarum, 1570**, is usually called the first modern atlas: uniform sheets bound as a book. Source: Library of Congress, https://www.loc.gov/item/2003623404/ (blocked: loc.gov refuses automated fetch with 403).
- **Web Mercator** (EPSG:3857) is the spherical Mercator used by Google Maps (2005) and almost every slippy-map tile service. It is not conformal on the ellipsoid in a strict sense and was long rejected by surveying bodies; it cuts off near ±85.06° (85.0511° exactly). EPSG remarks: "Not a recognised geodetic system", spherical development of ellipsoidal coordinates, up to 0.7% scale error and 43 km northing difference versus EPSG:3395. Source: https://epsg.io/3857 (checked 2026-11-14); NGA advisory NGA.SIG.0011 (2014) (blocked: not opened, NGA site not fetchable).

### 1.4 National surveys

- **Cassini map of France** (Carte de Cassini), 180 maps on 181 sheet numbers (sheet 160 is merged into 131) at 1:86,400 (one line per 100 toises), built on a triangulation network; survey work spanned roughly 1750-1815 over four generations of the Cassini family. Source: Bibliothèque nationale de France / IGN, https://gallica.bnf.fr/html/und/cartes/france-en-cartes/la-carte-de-cassini, https://carteancienne.com/en/pages/assembly-chart-cassini-map (sheet count corrected 2026-11-14).
- **Ordnance Survey** (Great Britain), founded 1791; the Principal Triangulation ran 1783-1853; first one-inch (1:63,360) map, of Kent, published 1 January 1801 by William Faden (surveyed at six inches to the mile); the first map OS published itself was Essex, 1805. Source: https://www.ordnancesurvey.co.uk/about/history (page exists) and https://www.ordnancesurvey.co.uk/blog/the-beginning-of-our-paper-maps; Principal Triangulation dates not re-checked.
- **Great Trigonometrical Survey of India**, 1802 onward, measured the Great Arc and gave the first height of Everest. Source: John Keay, *The Great Arc*, HarperCollins, 2000.
- **USGS topographic mapping**, from 1879; the 7.5-minute quadrangle at 1:24,000 became the US standard series. Source: USGS, "History of the topographic map", https://www.usgs.gov/programs/national-geospatial-program/topographic-maps (checked 2026-11-16: page states 1879 mandate and 1:24,000 7.5-minute quadrangles).
- National surveys fixed the modern toolkit: a datum, a triangulation network, a projection grid, contour lines, a standard legend per series, and margin information (scale, date, declination).

### 1.5 Digital and web maps

- GIS begins with the Canada Geographic Information System (Roger Tomlinson, 1960s). Source: Esri, "History of GIS", https://www.esri.com/en-us/what-is-gis/history-of-gis.
- **Google Maps** launched in February 2005 with pre-rendered 256 px tiles in Web Mercator, a z/x/y pyramid where zoom 0 is one tile for the world and each zoom level doubles resolution. Source: OpenStreetMap wiki, "Slippy map tilenames", https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames.
- **OpenStreetMap**, founded 2004 by Steve Coast, open data under ODbL since 2012. Source: https://wiki.openstreetmap.org/wiki/History_of_OpenStreetMap.
- **Vector tiles** (Mapbox Vector Tile spec, 2014) moved styling to the client, so one dataset can carry many styles and smooth zooming. Source: https://github.com/mapbox/vector-tile-spec.

### 1.6 First use of conventions by year

A period style carries a year, and nothing it draws may be younger than that year. Each year below is "not before". All are one book's dates, several are contested, and none was cross-checked (book facts, not cross-checked). Where two sources differ, a lint uses the earlier year, so it never fails a date that one source allows. T = Thrower, Maps and Civilization, 3rd ed.; HW = Harley and Woodward, History of Cartography vol. 1. Projections by year are in [projections.md](projections.md) section 3.14.

| Convention | Not before | Source |
|---|---|---|
| Square scale grid | 3rd century in China (rules for official maps: grid for scale and position, orientation); a stone map has a grid at one hundred li to a square, north at top | T ch. 3 |
| Printed map | about 1155 in China; 1472 in Europe (a T-O diagram, Augsburg); first printed Ptolemy atlas 1477 (Bologna, copper plates) | T ch. 3, ch. 5 |
| Rhumb-line network | late 13th century, on sea charts and maps derived from them; sixteen lines leave the centre until 1449, thirty-two after | HW ch. 19; T ch. 4 |
| Bar scale | sea charts: the Pisan chart (c. 1275 or c. 1290, see 1.2); a scale inside a circle only on the four earliest charts. Mappae mundi: 15th century. European local maps: 1421-22 (a plan of Vienna and Bratislava, in paces) | T ch. 4; HW ch. 18-20 |
| Drawn compass rose | 1375; the sixteen-point compass card dates from about 1300 | HW ch. 19 |
| Latitude scale on a sea chart | start of the 16th century; portolan charts have no graticule | HW ch. 19 |
| Graticule on European land maps | 15th century, when Ptolemy's Geography reached Latin readers | T ch. 5; HW ch. 18 |
| Printed colour | red and black names, Venice 1511; three-colour woodcut, Strasbourg 1513; otherwise hand wash until lithography | T ch. 5 |
| Print method | woodcut from 1472; copper engraving dominant about 1550 to 1800; lithography on maps from the early 19th century (about 1820) | T ch. 5, ch. 7 |
| The name America | 1507 | T ch. 5 |
| Printed sea atlas with soundings in fathoms, standard signs and coastal views | 1584 | T ch. 5 |
| Depth contours | manuscript 1584 and 1697; engraved river chart 1729; English Channel 1737 | T ch. 6 |
| Isoline map | 1701 (lines of equal compass variation) | T ch. 6 |
| Land contours | 1791 over a large area; usual in national surveys only from about 1850 | T ch. 6-7 |
| Hachures as a system | 1799; before that, profile molehills | T ch. 5-6 |
| Elevation by tone | 1804 (darker with height), 1806 (lighter with height); green through ochre to brown fixed for the 1:1,000,000 world map in 1909 | T ch. 7-8 |
| Ratio scale (1:N) | 1806, France; verbal scales in local units before that | T ch. 6 |
| Geological map with sections | 1815 | T ch. 7 |
| Isotherm map | 1817; weather maps from the 1840s | T ch. 7 |
| Dot map | 1830 (France, one dot for ten thousand people) | T ch. 7 |
| Shaded-area map | 1831 is the example found, in seven tones with white as the highest class; the reader's note says 1826 is the usual credit and that the search may have missed it | T ch. 7 |
| Proportional circles, flow lines | 1837; every common thematic technique existed by 1865 | T ch. 7 |
| Greenwich as the world prime meridian | 1884; earlier maps use a national or island meridian | T ch. 6-7 |
| Landform (physiographic) diagrams | middle of the 20th century | T ch. 9 |

## 2. Conventions a reader expects

### 2.1 Scale

- Three forms: representative fraction (1:50,000), verbal ("1 cm to 500 m"), and graphic bar. A bar scale stays correct when the map is resized or reprinted; a printed fraction does not. Source: Slocum, McMaster, Kessler & Howard, *Thematic Cartography and Geovisualization*, 3rd ed., Pearson, 2009, ch. 2 (blocked: book, no open text). Monmonier says the same: only the bar survives enlargement or reduction (How to Lie with Maps, 1991 ed., ch. 2).
- A verbal scale says one unit represents a distance, not that it equals it (Monmonier, ch. 2).
- Distance read from a map is planimetric. Over ground with relief the real distance is longer (Monmonier, ch. 3).
- "Large scale" means a large fraction (1:10,000, small area, much detail); "small scale" means a small fraction (1:10,000,000, large area). Readers and even writers often invert this. Source: USGS, https://www.usgs.gov/faqs/why-are-usgs-topographic-maps-called-quadrangles (1:24,000 = 1 in to 2,000 ft) and USGS General Interest Publication https://pubs.usgs.gov/gip/70039400/report.pdf (large scale = more detail); the FAQ title originally cited was not found.
- On small-scale world maps scale varies across the sheet, so a single bar scale is misleading; state "scale true along the equator" or omit the bar. Source: Snyder 1987, USGS PP 1395.
- Fantasy and sci-fi maps still need scale: travel time in days, or a bar in leagues/parsecs. Readers judge distance from it (no formal source; design practice).

### 2.2 Legend (key)

- A legend lists every symbol that is not self-explanatory, in the same size and colour as on the map, ordered by importance or by category (points, lines, areas). Do not title it "Legend"; the box says what it is. Source: Brewer, *Designing Better Maps*, Esri Press, 2nd ed. 2015 (blocked: book, no open text); Dent, Torguson & Hodler, *Cartography: Thematic Map Design*, 6th ed., McGraw-Hill, 2009.
- Class breaks in a choropleth legend should not overlap or leave gaps (e.g. "0-10, 10-20" is ambiguous; use "0-9.9, 10-19.9"). Source: Dent et al. 2009 (blocked: book, no open text).
- Legend swatches sit on the map's ground colour, not on white: a colour looks lighter inside a dark surround, and big patches look more saturated than small ones. With many qualitative classes add a letter code or a pattern as a second cue (Monmonier, How to Lie with Maps, 1991 ed., ch. 10).

### 2.3 Orientation

- North-up is the default for most modern maps since the printed atlases; medieval mappae mundi used east-up and many Islamic maps (al-Idrisi, 1154) used south-up. Source: Jerry Brotton, *A History of the World in Twelve Maps*, Penguin, 2012. Thrower agrees and adds that Ptolemaic and Chinese grid maps are north-up (Maps and Civilization, ch. 3-5). East-up holds for the T-O family; zonal mappae mundi are north or south up, and portolan charts have no top because they were made to be turned (Harley and Woodward, vol. 1, ch. 18-19) (book facts, not cross-checked).
- A north arrow is needed when north is not up or the map is large scale; on a north-up small-scale map with a graticule it is redundant clutter. Source: Brewer 2015 (blocked: book, no open text).
- Grid north, true north and magnetic north differ; topographic series state the declination in the margin. Source: Ordnance Survey, "A guide to coordinate systems in Great Britain", https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf.

### 2.4 Grid and graticule

- A graticule is lines of latitude and longitude; a grid is a planar coordinate system (UTM, British National Grid) with eastings and northings in metres. Source: Snyder 1987.
- Read grid references "eastings first, then northings" ("along the corridor, then up the stairs"). Source: Ordnance Survey map reading guide, https://www.ordnancesurvey.co.uk/mapzone (blocked: page loads by script, no text fetched 2026-11-16).
- Game and fantasy maps often use letter-number grids (A1) or hex grids; hexes give six equal neighbours and equal distances to centres. Source: Red Blob Games, "Hexagonal Grids", https://www.redblobgames.com/grids/hexagons/.

### 2.5 Inset and locator maps

- An inset shows either a detail at larger scale or a locator at smaller scale; each needs its own scale and must not suggest it is at the main map's scale. Alaska and Hawaii insets on US maps are the classic case of misleading scale and position. Source: Monmonier, *How to Lie with Maps*, 3rd ed., Univ. of Chicago Press, 2018.

### 2.6 Other expected elements

- Title, data source and date, projection, author. Source: Dent et al. 2009; ICA Commission on Map Design materials, https://mapdesign.icaci.org/.
- Water is blue, vegetation green, relief brown or shaded from the upper left (northwest light). A light source from the lower right causes relief inversion, where valleys read as ridges. Source: Imhof, *Cartographic Relief Presentation*, 1965 (English ed. Esri Press 2007); Shaded Relief, http://www.shadedrelief.com/.
- Lettering: water features in italic, often blue; settlements upright; type size proportional to importance; place point labels upper right of the point by preference. Source: Imhof, "Positioning Names on Maps", The American Cartographer 2(2), 1975.

## 3. Design rules

### 3.1 Visual hierarchy

- The subject of the map should be visually strongest, reference data (roads, borders, labels) weaker, and the base (background, water) weakest. Source: Dent et al. 2009; Brewer 2015.
- Hierarchy is built with size, weight, contrast and saturation. Base layers in desaturated, light tones let thematic layers stand out. Source: Slocum et al. 2009.
- Squint test: blur or shrink the map; what remains visible should be the subject (practice figure, no single source; tunable default).

### 3.2 Figure and ground

- Readers separate a figure (land, area of interest) from ground (sea, surroundings) through closure, contrast, texture, and a darker or more detailed figure. Gestalt principles applied to maps: Dent, "Visual organization and thematic map communication", Annals of the AAG 62(1), 1972 (blocked: paywalled).
- Practical devices: vignette or drop shadow on coasts, water lining, darker figure fill, fading features outside the area of interest. Source: Brewer 2015.

### 3.3 Generalisation by scale

- Generalisation operators: selection (omit), simplification, smoothing, aggregation, collapse (area to point), displacement, exaggeration, typification. Source: McMaster & Shea, *Generalization in Digital Cartography*, AAG, 1992.
- **Töpfer's radical law** (1966): n_f = n_a × sqrt(M_a / M_f), where n is number of objects and M the scale denominator. Going from 1:25,000 to 1:100,000 keeps about half the objects. Source: Töpfer & Pillewizer, "The Principles of Selection", The Cartographic Journal 3(1), 1966.
- Line simplification: Douglas-Peucker (1973) with tolerance tied to scale; Visvalingam-Whyatt (1993) removes points by effective triangle area and gives more natural shapes. Sources: Douglas & Peucker, The Canadian Cartographer 10(2), 1973; Visvalingam & Whyatt, The Cartographic Journal 30(1), 1993.
- **Minimum dimensions**: a common rule is to drop detail smaller than about 0.5 mm at the output scale; Li & Openshaw's "natural principle" uses a smallest visible object of 0.5-0.7 mm. Source: Li & Openshaw, "A natural principle for the objective generalization of digital maps", Cartography and GIS 20(1), 1993 (blocked: paywalled). Swiss Society of Cartography *Topographic Maps: Map Graphics and Generalisation* (2005) lists minimum line widths of about 0.08-0.1 mm for printed maps (blocked: book, no open text).
- **Symbol footprint**: a symbol claims more ground than its feature. Footprint on the ground = width on the page x scale denominator, so a line 0.5 mm wide (about a fiftieth of an inch) covers 12 m at 1:24,000 and 50 m at 1:100,000. Overlapping footprints call for selection or displacement (Monmonier, How to Lie with Maps, 1991 ed., ch. 3).
- **Tactile generalisation**: for touch, legibility outranks position. Displace and schematise (snap near 0/45/90 degree directions) to keep gaps and topology. Selection is much harsher, but keep connectivity (a minor road that links two major ones) and density character (keep some small lakes in a lake district) (van Altena and Wabinski, Tactile Mapping, 2025, ch. 5-6).
- On screens, a 1 px line at 96 dpi is about 0.26 mm; labels under about 10-11 px are hard to read. Source: practice figure, no single source; tunable default.

### 3.4 Bertin's visual variables

- Jacques Bertin, *Sémiologie graphique*, 1967 (English: *Semiology of Graphics*, Univ. of Wisconsin Press 1983; Esri Press 2010). Original variables: two planar dimensions (x, y), size, value (lightness), texture (grain), colour (hue), orientation, shape.
- Later additions: colour saturation, arrangement, crispness, resolution, transparency. Source: MacEachren, *How Maps Work*, Guilford, 1995; Roth, "Visual Variables", International Encyclopedia of Geography, 2017, https://doi.org/10.1002/9781118786352.wbieg0761.
- Suitability by data level (Roth 2017 summary of Bertin and MacEachren):

| Variable | Nominal | Ordinal | Numerical |
|---|---|---|---|
| Position | good | good | good |
| Size | poor | good | good |
| Value (lightness) | poor | good | marginal |
| Hue | good | poor | poor |
| Saturation | poor | good | marginal |
| Shape | good | poor | poor |
| Orientation | good | marginal | poor |
| Texture/grain | good | marginal | poor |

  (Cell grades are a simplified reading of Roth 2017; practice figure, no single source; tunable default.)
- Choropleth maps must map rates or densities, not raw counts; counts go on proportional symbols. Source: Slocum et al. 2009; Monmonier 2018.
- Proportional circles scale by area (radius ∝ sqrt(value)); Flannery (1971) proposed apparent-magnitude scaling with exponent 0.57 to correct perceived underestimation. Source: Flannery, "The relative effectiveness of some common graduated point symbols", The Canadian Cartographer 8(2), 1971.

### 3.5 Colour schemes and colour blindness

- **Scheme types** (Brewer): sequential (ordered low-high, lightness steps), diverging (two hues from a meaningful midpoint), qualitative (categories, distinct hues of similar lightness). Source: Harrower & Brewer, "ColorBrewer.org: An Online Tool for Selecting Colour Schemes for Maps", The Cartographic Journal 40(1), 2003; https://colorbrewer2.org/.
- ColorBrewer schemes run 3-9 classes for sequential (up to 11 for diverging, 12 for qualitative) and flag each as colourblind safe, print friendly and photocopy safe. Source: https://colorbrewer2.org/ and its scheme data https://github.com/axismaps/colorbrewer.
- Humans distinguish about 5-7 classes on a choropleth reliably; more classes rarely help. Source: Dent et al. 2009; Slocum et al. 2009 (blocked: books, no open text).
- **Viridis** (Smith & van der Walt, 2015) is perceptually uniform in CAM02-UCS, monotonic in lightness, and readable under common CVD and in greyscale; it replaced jet as matplotlib's default in 2.0. Source: https://bids.github.io/colormap/; matplotlib docs, https://matplotlib.org/stable/users/explain/colors/colormaps.html.
- **Cividis** (Nuñez, Anderton & Renslow, 2018) is optimised so people with deuteranomaly and normal vision see nearly the same map. Source: PLOS ONE 13(7): e0199239, https://doi.org/10.1371/journal.pone.0199239.
- Rainbow/jet colour maps create false boundaries and are not ordered in lightness. Source: Borland & Taylor, "Rainbow Color Map (Still) Considered Harmful", IEEE CG&A 27(2), 2007; Crameri, Shephard & Heron, "The misuse of colour in science communication", Nature Communications 11, 5444, 2020, https://doi.org/10.1038/s41467-020-19160-7.
- **Prevalence**: red-green colour vision deficiency affects about 8% of men and 0.5% of women of Northern European descent. Source: National Eye Institute, https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/color-blindness.
- **CVD simulation**: Brettel, Viénot & Mollon (1997) and Viénot, Brettel & Mollon (1999) give dichromat simulation in LMS space; Machado, Oliveira & Fernandes (2009) give a matrix model for anomalous trichromacy with severity 0-1, used by many tools. Sources: JOSA A 14(10), 1997; Color Research & Application 24(4), 1999; IEEE TVCG 15(6), 2009, https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html. A stdlib implementation needs only sRGB linearisation and 3x3 matrices.
- **Colour difference**: CIEDE2000 (ΔE00) is the CIE recommended formula; ΔE00 around 2-3 is just noticeable in practice; for map classes aim well above that. Source: Sharma, Wu & Dalal, "The CIEDE2000 Color-Difference Formula", Color Research & Application 30(1), 2005, https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/. Thresholds for map classes: practice figure, no single source; tunable default.
- **Text contrast**: WCAG 2.x asks for 4.5:1 for normal text and 3:1 for large text and graphical objects (1.4.11 non-text contrast). Source: https://www.w3.org/TR/WCAG22/.
- Do not encode meaning by red-versus-green hue alone; add lightness difference, pattern, or labels. Source: WCAG 1.4.1 Use of Color, https://www.w3.org/TR/WCAG22/#use-of-color.

### 3.6 Projections, briefly

- Use equal-area projections for choropleth and density maps (e.g. Equal Earth, Šavrič, Patterson & Jenny 2018; Albers for mid-latitude countries), conformal for navigation and large-scale maps, and compromise projections (Robinson, Winkel Tripel, Natural Earth) for general world reference. Sources: Šavrič et al., IJGIS 33(3), 2019, https://doi.org/10.1080/13658816.2018.1504949; Snyder 1987.
- Web Mercator is acceptable for street-level navigation but distorts area badly at world scale. Source: Battersby et al., "Implications of Web Mercator and Its Use in Online Mapping", Cartographica 49(2), 2014.

## 4. Rules the plugin should enforce

Each rule is checkable from a map spec, a rendered image or vector data. "Hard" means fail the check; "soft" means warn.

1. **Scale present (hard).** Every map has a bar scale unless it is a world/continental map on a non-equidistant projection, in which case it states the projection instead. Fantasy maps carry a bar in a named unit or a travel-time note. A schematic (transit-style) map carries no bar and says it is not to scale (Monmonier, How to Lie with Maps, 1991 ed., ch. 3).
2. **Bar scale over fraction (soft).** If a representative fraction is printed and the output can be resized (web, PNG), also draw a bar (Monmonier, How to Lie with Maps, 1991 ed., ch. 2).
3. **Legend completeness (hard).** Every thematic symbol class drawn on the map appears in the legend with identical style; no legend entry is unused. Legend never titled just "Legend". Ruling 2026-11-14: completeness applies only to thematic classes; base features that are already labelled on the map (named rivers, roads, towns) may be left out of the legend (Brewer, Designing Better Maps, ch. 4). Legend content follows the map type: class ranges for a choropleth, the value of one dot for a dot map, the interval for isolines, short descriptions for qualitative classes (Brewer, Designing Better Maps, ch. 4).
4. **Class break integrity (hard).** Choropleth breaks are contiguous, non-overlapping, and cover the data min and max.
5. **Class count (soft).** 3-7 classes for sequential/diverging choropleths; warn above 7, fail above 9 (ColorBrewer limit for sequential). The break method is printed with the legend or in the sidecar (Longley et al., Geographic Information Science and Systems, ch. 11). Point and line symbols get fewer classes than areas (default warn above 5) (Brewer, Designing Better Maps, ch. 9).
6. **Rates, not counts (soft).** A choropleth variable whose name or values look like raw totals (integers, no denominator) gets a warning to normalise or use proportional symbols.
7. **Proportional symbol area (hard).** Circle radius ∝ sqrt(value) (or exponent 0.57 if apparent-magnitude scaling is chosen and stated); never radius ∝ value. Apparent-magnitude compensation applies to circles only; squares, bars and other shapes scale by plain area (Kimerling et al., Map Use, ch. 9).
8. **Scheme matches data (hard).** Ordered data uses sequential or diverging; nominal data uses qualitative. Diverging requires a declared midpoint, neutral in the middle (Monmonier, How to Lie with Maps, 1991 ed., ch. 10).
9. **No rainbow for ordered data (hard).** Reject jet/rainbow/hsv for sequential data; default to viridis, cividis or a ColorBrewer sequential scheme.
10. **Lightness monotonic (hard).** In a sequential scheme CIELAB L* changes monotonically; adjacent classes differ by at least 5 L* (practice figure, no single source; tunable default). Darker means more unless the style declares a dark background (Brewer, Designing Better Maps, ch. 9). The legend states the direction: the earliest shaded-area map found, of 1831, ran white for the highest class (Thrower, Maps and Civilization, ch. 7) (book fact, not cross-checked). The order must survive the output device (Monmonier, How to Lie with Maps, 1991 ed., ch. 4, ch. 10).
11. **CVD distinctness (hard).** After Machado 2009 simulation at severity 1.0 for protan, deutan and tritan, every pair of adjacent legend classes keeps ΔE00 ≥ 10 and every pair of qualitative classes ΔE00 ≥ 10 (practice figure, no single source; tunable default). Qualitative classes also keep CIELAB L* and chroma near equal (default spread L* <= 15) so no class reads as more important (Tyner, Principles of Map Design, ch. 4).
12. **Greyscale survival (soft).** Sequential classes stay distinct when converted to luminance (ΔL* ≥ 5).
13. **Text contrast (hard).** Labels against their local background reach 4.5:1 (3:1 for text ≥ 18.66 px bold or 24 px regular; also 3:1 for symbol edges), per WCAG 2.2. Use a halo when not met. Test every background the label crosses (Monmonier, How to Lie with Maps, 1991 ed., ch. 10).
14. **Minimum label size (hard).** Print ≥ 6 pt, screen ≥ 10 px; warn below 8 pt / 11 px (Brewer, Designing Better Maps, ch. 6) (Kimerling et al., Map Use, ch. 7). Sizes are set by measured x-height, so two faces at the same nominal size are normalised to the same x-height before the floor is applied (Brewer, Designing Better Maps, ch. 6). Adjacent levels of the type hierarchy differ by at least 2 pt between 5 and 15 pt, and by at least 15 percent (prefer 25) above 15 pt (Kimerling et al., Map Use, ch. 7).
15. **Minimum feature size (soft).** Features smaller than 0.5 mm (print) or 2 px (screen) at output scale are dropped, collapsed or exaggerated. The minimum is the same for every map in a set (Monmonier, How to Lie with Maps, 1991 ed., ch. 3).
16. **Line simplification by scale (soft).** Simplification tolerance ≈ 0.2-0.5 mm at output scale (converted to ground units); no vertices closer than the tolerance remain (practice figure, no single source; tunable default).
17. **Selection by radical law (soft).** When scale changes from 1:Ma to 1:Mf, keep about n × sqrt(Ma/Mf) features of each class; warn when the count exceeds 1.5× that.
18. **Hierarchy (soft).** The thematic layer has higher contrast against the background than any reference layer (compute mean contrast per layer).
19. **Relief lighting (hard).** Hillshade azimuth between 270° and 360° (default 315°), altitude 30-50° (default 45°), to avoid relief inversion.
20. **Water conventions (soft).** Water fill in the blue hue range (about 180-240° hue) unless the style declares otherwise; water labels italic.
21. **Orientation (soft).** North-up by default; if rotated more than 5°, a north arrow is required. If north-up with a visible graticule, a north arrow is optional. A north arrow is forbidden (hard) where meridians are visibly curved or converge inside the frame, since north differs across the map; show the graticule instead (Tyner, Principles of Map Design, ch. 2).
22. **Insets (hard).** Each inset at a different scale from the main map has its own scale (Tyner, Principles of Map Design, ch. 2) or explicit "not to scale" note and a border; locator insets mark the main map's extent.
23. **Projection fit (soft).** Choropleth/density world or continental maps use an equal-area projection; warn on Web Mercator beyond zoom 4 equivalent extents. Dot-density maps too: on a projection that is not equal-area, equal counts look like different densities (Monmonier, How to Lie with Maps, 1991 ed., ch. 2).
24. **Metadata (hard).** Title, data source, date, and projection/CRS present in the map or its sidecar. The data date or date range is given apart from the making date; `sources.json` keeps a date per layer, and a wide spread warns (Monmonier, How to Lie with Maps, 1991 ed., ch. 4).
25. **Grid labels (soft).** Planar grids label eastings and northings at the margin; hex/letter grids label both axes.
26. **Scale precision (soft).** The finest graphic-scale division is no finer than the map's positional accuracy at output scale (Tyner, Principles of Map Design, ch. 5).
27. **Precision follows accuracy (soft).** Printed coordinates, distances and areas are rounded to the source accuracy; projection and datum are recorded as separate fields, with the source accuracy, in every recipe (Longley et al., Geographic Information Science and Systems, ch. 4-5).
28. **Classing method fits the distribution (soft).** The break method is chosen from the data's histogram; quantiles on skewed data (skewness above 1) warn (Kimerling et al., Map Use, ch. 6).
29. **Symbol pair contrast (soft).** Two symbols that must be told apart differ by at least 125 in brightness (0-255, the W3C brightness formula) (Kimerling et al., Map Use, ch. 7).
30. **Generalisation by named operators (soft).** A child map at a smaller scale records which operators it used (simplify, smooth, aggregate, amalgamate, merge, collapse, refine, exaggerate, enhance, displace) and a per-scale minimum size; features that must stay visible are exaggerated, not dropped (Longley et al., Geographic Information Science and Systems, ch. 3). It also records the priority between classes used where areas compete, since other priorities give another map (Monmonier, How to Lie with Maps, 1991 ed., ch. 3).
31. **Declare artefacts (soft).** Features that were generalised, displaced or invented are listed in the sidecar, since readers take them as real (Kimerling et al., Map Use, ch. 12).
32. **Aggregation caution (soft).** A choropleth of areal units carries a note that the pattern depends on the units chosen (MAUP) and does not describe individuals (ecological fallacy) (Longley et al., Geographic Information Science and Systems, ch. 5, 11). The key names the areal unit (Monmonier, How to Lie with Maps, 1991 ed., ch. 9).
33. **Route maps (hard).** A route map labels the origin, the destination and the direction of travel (Tyner, Principles of Map Design, ch. 12).
34. **One light direction (hard).** Every shadowed symbol, hillshade and drop shadow on one map uses the same light azimuth (Blando, Fantasy Mapmaker, ch. 2).
35. **Width encodes rank (soft).** Within a feature family the line width rises with rank: stream < river, track < dirt road < paved road (Blando, Fantasy Mapmaker, ch. 2).
36. **One atlas, one system (hard for a map set).** Maps in one set share one grid, one distance unit, one spelling authority (a place table with name variants by era) and one symbol set (Fonstad, The Atlas of Middle-Earth, p. x-xi). A dated history series also shares one base map, frame and scale, so that sheets can be compared (Goffart, Historical Atlases, Conclusion, p. 443 ff.).
37. **Orientation is a style field (soft).** Styles carry an orientation (north, east, south up) and historical presets set it with their period; a non-north orientation is declared on the map (Brotton, A History of the World in Twelve Maps, intro. and ch. 2-4).
38. **Fuzzy boundaries (soft).** Boundaries of fuzzy classes (biome, soil, climate, culture) are drawn soft or dashed, not as a hard line, and are never used as control points (Monmonier, How to Lie with Maps, 1991 ed., ch. 3).
39. **Reserved fills (hard).** No class fill is pure black or pure white, which read as water or as no data. The no-data and water colours differ from every class (Monmonier, How to Lie with Maps, 1991 ed., ch. 9).
40. **Disputed areas (soft).** Disputed land is shaded by who holds it, the claim is noted in small type, the second name goes in brackets, and the map says whose view its boundary set shows (Monmonier, How to Lie with Maps, 1991 ed., ch. 7).
41. **Tactile legend and furniture (hard for tactile output).** The legend is complete and ordered points, lines, areas, with "you are here" first on large scales; braille abbreviations are keyed there. Required: title, legend, orientation mark, imprint (date, author). Avoid insets; scale bar and north arrow are optional (van Altena and Wabinski, Tactile Mapping, 2025, ch. 5).
42. **Haptic variables (soft).** Touch reads height, texture, shape, size and orientation; hue helps only low-vision readers. Make symbols differ in more than one variable, prefer raised to sunken, and cap both the number of distinct textures and the total textured area (van Altena and Wabinski, Tactile Mapping, 2025, ch. 4-5).
43. **Pictorial (tourist) maps (soft).** Curated places, one icon each, on a simplified base with main roads only. Build order: outline, main roads, water, landmark icons, filler icons, labels; reserve compass and title boxes at the sketch. Fill large empty land with small flavour items or terrain marks, not more labels (Hancock et al., The Art of Map Illustration, 2017, sec. 10-12, 16, 21) (book rule, unverified).
44. **Allowed distortion in pictorial mode only (hard).** Far places may be pulled toward the focus and the map rotated so the main route runs straight, but only in an explicit pictorial mode, and the map then says "not to scale" and shows north by a compass (Hancock et al., The Art of Map Illustration, sec. 17, 21, 23) (book rule, unverified).

## 5. Open questions

- Exact CVD ΔE thresholds for "distinct" map classes lack a single standard; rules 10-12 and 16 use mapwright defaults to tune by testing.
- Whether to ship ColorBrewer data inline (Apache 2.0 licence per the axismaps repo) or regenerate schemes; licence text to confirm before bundling.
- Several history dates above are marked unverified and should be checked against the cited institutions before publishing.

## Sources

All accessed 2026-11-14 unless a book.

- British Museum, Babylonian Map of the World: https://www.britishmuseum.org/collection/object/W_1882-0714-509
- Harley, J. B. & Woodward, D. (eds.), *The History of Cartography*, vol. 1, Univ. of Chicago Press, 1987: https://press.uchicago.edu/books/HOC/index.html
- Campbell, T., "Portolan Charts from the Late Thirteenth Century to 1500", HoC vol. 1 ch. 19, 1987
- Berggren, J. L. & Jones, A., *Ptolemy's Geography*, Princeton UP, 2000
- Snyder, J. P., *Map Projections: A Working Manual*, USGS PP 1395, 1987: https://pubs.usgs.gov/publication/pp1395
- Snyder, J. P., *Flattening the Earth*, Univ. of Chicago Press, 1993
- Brotton, J., *A History of the World in Twelve Maps*, Penguin, 2012
- Keay, J., *The Great Arc*, HarperCollins, 2000
- EPSG:3857: https://epsg.io/3857
- Battersby, S. et al., Cartographica 49(2), 2014
- OpenStreetMap wiki, Slippy map tilenames: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
- OpenStreetMap history: https://wiki.openstreetmap.org/wiki/History_of_OpenStreetMap
- Mapbox Vector Tile spec: https://github.com/mapbox/vector-tile-spec
- Esri, History of GIS: https://www.esri.com/en-us/what-is-gis/history-of-gis
- Ordnance Survey, Guide to coordinate systems in Great Britain: https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf
- Bertin, J., *Semiology of Graphics*, 1967/1983
- MacEachren, A. M., *How Maps Work*, Guilford, 1995
- Roth, R. E., "Visual Variables", 2017: https://doi.org/10.1002/9781118786352.wbieg0761
- Slocum, T. et al., *Thematic Cartography and Geovisualization*, 3rd ed., 2009
- Dent, B., Torguson, J. & Hodler, T., *Cartography: Thematic Map Design*, 6th ed., 2009
- Brewer, C., *Designing Better Maps*, 2nd ed., Esri Press, 2015
- Monmonier, M., *How to Lie with Maps*, 3rd ed., 2018 (cited for 2.5 and 3.4); 1st ed., Univ. of Chicago Press, 1991 (the edition read on 2026-11-15; every chapter citation above is to it)
- Thrower, N. J. W., *Maps and Civilization: Cartography in Culture and Society*, 3rd ed., Univ. of Chicago Press
- Goffart, W., *Historical Atlases: The First Three Hundred Years, 1570-1870*, Univ. of Chicago Press, 2003
- Imhof, E., *Cartographic Relief Presentation*, 1965/2007; "Positioning Names on Maps", 1975
- McMaster, R. & Shea, K. S., *Generalization in Digital Cartography*, AAG, 1992
- Töpfer, F. & Pillewizer, W., The Cartographic Journal 3(1), 1966
- Douglas, D. & Peucker, T., The Canadian Cartographer 10(2), 1973
- Visvalingam, M. & Whyatt, J., The Cartographic Journal 30(1), 1993
- Flannery, J., The Canadian Cartographer 8(2), 1971
- Harrower, M. & Brewer, C., The Cartographic Journal 40(1), 2003; https://colorbrewer2.org/; https://github.com/axismaps/colorbrewer
- Smith, N. & van der Walt, S., viridis: https://bids.github.io/colormap/
- Matplotlib colormaps: https://matplotlib.org/stable/users/explain/colors/colormaps.html
- Nuñez, J. R. et al., PLOS ONE 2018: https://doi.org/10.1371/journal.pone.0199239
- Borland, D. & Taylor, R., IEEE CG&A 27(2), 2007
- Crameri, F. et al., Nature Communications 11, 2020: https://doi.org/10.1038/s41467-020-19160-7
- National Eye Institute, Color blindness: https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/color-blindness
- Machado, G. M. et al., IEEE TVCG 15(6), 2009: https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
- Brettel, H., Viénot, F. & Mollon, J., JOSA A 14(10), 1997
- Sharma, G. et al., CIEDE2000: https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
- W3C, WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Šavrič, B., Patterson, T. & Jenny, B., Equal Earth: https://doi.org/10.1080/13658816.2018.1504949
- Red Blob Games, Hexagonal Grids: https://www.redblobgames.com/grids/hexagons/
- ICA Commission on Map Design: https://mapdesign.icaci.org/
- Shaded Relief: http://www.shadedrelief.com/
