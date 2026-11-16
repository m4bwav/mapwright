# Reading map pictures: what works, what fails, how to test it

Reference for mapwright's `read` (legend, scale, names, features, georeference) and `trace` (picture to vectors) commands. Every claim names its source inline. Numbers marked "(unverified)" were not re-checked against the paper on 2026-11-14 and must be confirmed before they go into user-facing text or tests. The Sources list at the end has the links.

## 1. The short version

- Vision-language models (VLMs) read big printed labels, titles and obvious map types well. They do badly at spatial reasoning on the map: counting, distances, routes, directions and reading values off a colour ramp. Every map benchmark below shows a large gap between models and people (MapBench, MapEval, MapQA).
- They invent with confidence. A model asked for a scale or coordinates will give one even when the picture has none. mapwright must ask "is it printed on the map?" before "what is it?".
- Place-name text on maps is curved, rotated, spaced out and overlaps line work. Plain OCR such as Tesseract assumes horizontal text lines and misses much of it; map-specific pipelines (mapKurator) exist because of this.
- A georeference is earned from ground control points (GCPs) with a residual error, never stated by a model. Affine needs 3 points, a 2nd-order polynomial 6, 3rd-order 10; thin-plate spline fits every point exactly, so its residuals say nothing (GDAL docs, Allmaps docs).
- Tracing is a pipeline of plain image operations (colour quantisation, masks, skeletons, potrace). It is measurable and does not need a model.
- The output format must have a "not printed / not sure" value for every field, and the test set must contain maps where the right answer is "not present".

## 2. What VLMs read off maps: benchmarks

### 2.1 MapQA (Chang et al., 2022)
- Question answering over choropleth maps of the United States: about 800,000 question-answer pairs over about 60,000 map images, generated synthetically (Chang et al., 2022; https://arxiv.org/abs/2211.08545).
- Question types: retrieval ("what is the value of state X"), comparison and relative position. The paper proposes V-MODEQA, a model that first reads the colour legend and then answers; general VQA baselines fell well short on value retrieval (Chang et al., 2022).
- Lesson for mapwright: reading a value means matching a region's colour to a legend swatch. That is a colour-matching problem a script can do once the legend is located, and a VLM often gets wrong by guessing.

### 2.2 MapEval (Dihan et al., 2024; ICML 2025)
- About 700 multiple-choice questions on map-based reasoning in three groups: textual, API-based and visual (map screenshots), across 180 cities in 54 countries (Dihan et al., 2024; https://arxiv.org/abs/2501.00316).
- The best models (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro) were among 30 models tested; none exceeded 67% accuracy, and all trailed people by more than 20 points (Dihan et al., 2024, abstract; https://arxiv.org/abs/2501.00316; per-task visual score unverified).
- Weak spots named by the authors: counting places, distance and travel-time estimates, and routes. Strong spots: reading a labelled place or point of interest that is plainly printed (Dihan et al., 2024).

### 2.3 MapBench (Xing et al., 2025)
- Navigation questions on map pictures (zoo maps, campus maps, park maps, city maps and similar): 100 maps and over 1,600 path-finding problems (Xing et al., 2025, "Can Large Vision Language Models Read Maps Like a Human?"; https://arxiv.org/abs/2503.14607; map-type list unverified).
- Models were asked to describe a route from a start to a destination. The authors report that leading VLMs often produced routes that crossed walls, skipped landmarks or invented paths; they also provide a structured "map space scene graph" to make answers checkable (Xing et al., 2025; the Map Space Scene Graph (MSSG) is confirmed in the abstract, failure descriptions unverified).
- Lesson: route and connectivity answers need a graph built from traced features, not free text from a model.

### 2.4 GeoBench and related geography benchmarks
- "GeoBench" names more than one benchmark. One set covers remote-sensing tasks for earth-observation models (Lacoste et al., 2023, GEO-Bench); another tests photo geolocation by VLMs (unverified which one the mapwright plan meant). Neither is about reading drawn maps, so treat them as background only.
- Image geolocation work shows models guess a place from visual cues, which is the same habit that makes them "recognise" a fictional map as a real region (unverified as a measured result for drawn maps).

### 2.5 Other map-reading results worth knowing
- ChartQA and chart benchmarks show VLMs read printed numbers well and estimate visual quantities poorly (Masry et al., 2022). Map scale bars and colour ramps are the same kind of visual quantity.
- MapKurator's evaluations on historical maps (section 4) are the best source for text recognition numbers on real map scans.

### 2.6 What this means for `read`
Treat VLM output in three tiers:

| Tier | Examples | Policy |
|---|---|---|
| Usually reliable | title, large printed labels, map type (street, topographic, choropleth, fantasy), presence of a legend or north arrow | accept with the model's evidence (a crop box) |
| Check with code | legend entries, scale bar length, numeric scale text, coordinates in the margin | VLM finds the region; OCR and pixel measurement give the value |
| Do not trust | distances, counts, routes, real-world location of an unlabelled map, values read off colour | compute from traced data, or answer "not determined" |

This split follows the failure patterns in MapEval and MapBench above; the exact boundaries are mapwright's design choice, to be tested with the protocol in section 9.

## 3. Legend and scale bar reading

### 3.1 Legend
- A legend is a list of (symbol, label) pairs. Find the box (VLM or layout detection), split it into rows, OCR each label, and sample each swatch's colour or crop each symbol (method: MapQA's legend-first model, Chang et al., 2022).
- Matching map regions to swatches should be done in a perceptual colour space (CIELAB, delta-E) because scanned colours shift; a delta-E threshold of about 10 is a common starting point for "same ink" on scans (unverified; tune on the test set).
- Report every legend entry with its crop box. An entry the model mentions but cannot point to is dropped.

### 3.2 Scale
Three kinds of printed scale (standard cartography; see any cartography text such as Slocum et al., Thematic Cartography and Geovisualization):
1. Representative fraction, such as "1:50,000". Read by OCR and a regex.
2. Verbal scale, such as "1 inch to 1 mile". Read by OCR and a unit table.
3. Graphic scale bar. Measure the bar in pixels between its tick marks, OCR the tick labels, divide. Example: a bar 412 px long labelled "0 ... 2 km" gives 4.85 m per pixel.

Rules:
- A representative fraction only holds for the printed size. A scan or screenshot changes the pixel size, so "1:50,000" cannot become metres per pixel without the scan DPI. Report the fraction as printed and say metres per pixel is unknown unless DPI or a scale bar is present (follows from the definition; GDAL docs describe geotransform pixel size in the same terms).
- Scale varies across a small-scale map (a world map in most projections). Report the scale bar's value as "valid near the bar" for maps covering large areas (standard cartography; unverified wording in any one source).
- No scale printed means `scale: null, reason: "not printed"`. Never estimate scale from "the city looks about this big" unless the map has been georeferenced (section 5), in which case derive it from the transform.

### 3.3 North arrow and grid
- A north arrow gives a rotation; a coordinate grid or graticule with printed labels gives GCPs for free (section 5). Grid ticks in the margin are the best source of georeference on topographic maps (USGS topographic map symbol sheet lists the tick conventions; unverified detail).

## 4. Place-name text recognition

### 4.1 Why maps are hard for OCR
- Map labels follow curves (rivers, roads), are rotated, letter-spaced across a region ("M O U N T A I N S"), cross line work and use many fonts and sizes (Li et al., 2020, mapKurator; Chiang et al., 2020, "Using historical maps in scientific studies").
- Tesseract is built for document pages. Its page segmentation assumes text in roughly horizontal lines; it handles small skew and offers modes such as `--psm 11` (sparse text) but does not read curved baselines (Tesseract documentation, "Improving the quality of the output"). Expect it to miss or garble rotated and curved names unless each word is cropped and straightened first.

### 4.2 mapKurator
- mapKurator is a pipeline from USC's Knowledge Computing Lab for text on historical maps: detect text (including curved), recognise it, link phrases, and match names to a gazetteer such as OpenStreetMap or GeoNames (Li et al., 2020; Kim et al., 2023, "The mapKurator System").
- It was run on the David Rumsey Map Collection, tens of thousands of maps, producing searchable text (Kim et al., 2023: the current arXiv abstract says "over 60,000 maps and over 100 million text/place names", https://arxiv.org/abs/2306.17059, checked 2026-11-16; earlier versions said 57,000 maps).
- Detection and recognition models it has used include TESTR and later spotter models trained on synthetic map text (checked 2026-11-16: the deployed Spotter-v2 "is built upon Deformable-DETR and TESTR", and PALETTE is the other listed spotter, https://github.com/knowledge-computing/mapkurator-spotter and https://github.com/knowledge-computing/mapkurator-system).
- Its post-processing step corrects OCR with a gazetteer lookup, which raises word accuracy but can "correct" a real but unlisted name into a known one (Kim et al., 2023; failure mode noted by the authors, wording unverified).

### 4.3 Recommended approach for mapwright
1. Detect text regions with an arbitrary-shape detector (mapKurator's spotter, or a general one such as PaddleOCR's detector) and keep the polygon.
2. For each region, straighten along its baseline (or rotate to the polygon's main angle) and run recognition. Tesseract can be the fallback recogniser on straightened single words.
3. Ask a VLM to read the same crop; if VLM and OCR disagree, report both with `status: "disputed"`.
4. Gazetteer matching is a separate, optional field (`matched_name`, `gazetteer_id`, `distance`) and never overwrites the text as read.
5. Score with word accuracy and character error rate against ground-truth polygons (section 9).

## 5. Georeferencing with ground control points

### 5.1 The idea
A GCP pairs a pixel (column, row) with a world coordinate (longitude, latitude or projected x, y). A transform is fitted through the pairs and the picture can then be warped (GDAL, gdal_translate `-gcp` and gdalwarp docs).

### 5.2 Transforms and minimum points

| Transform | What it models | Minimum GCPs | Source |
|---|---|---|---|
| Helmert / similarity | shift, rotate, uniform scale | 2 | Allmaps transformation docs |
| Affine (1st-order polynomial) | plus shear, non-uniform scale | 3 | GDAL gdalwarp `-order 1`; Allmaps |
| 2nd-order polynomial | some bending | 6 | GDAL gdalwarp `-order 2` |
| 3rd-order polynomial | more bending | 10 | GDAL gdalwarp `-order 3` |
| Thin-plate spline (TPS) | local rubber-sheeting, passes through every point | 3 in practice; useful with many | GDAL gdalwarp `-tps`; Allmaps |
| Projective | perspective (a photo of a map) | 4 | Allmaps transformation docs |

- The polynomial minimum is (n+1)(n+2)/2 coefficients per axis: 3, 6, 10 (standard result; GDAL picks the order from the number of GCPs when `-order` is not given, per the gdalwarp docs).
- Map Warper uses GDAL underneath, needs at least 3 control points to rectify, and offers polynomial and thin-plate transforms (checked 2026-11-16 in https://github.com/timwaters/mapwarper: `app/models/map.rb` returns nothing below 3 hard control points and runs `gdalwarp`; `maps_controller.rb` offers `-order 1`, `-order 2`, `-order 3` and `-tps`).
- Allmaps works on IIIF images and stores GCPs as a Georeference Annotation (a W3C Web Annotation profile) so the georeference is a shareable file; it supports Helmert, polynomial of orders 1-3, projective and TPS (Allmaps docs, @allmaps/transform).

### 5.3 Errors
- Residual for one GCP: the distance between where the transform puts its pixel and its stated world position. RMS error is the root mean square of residuals over all GCPs (QGIS Georeferencer docs; Map Warper shows per-point error and RMS).
- RMS needs more points than the minimum to mean anything. With exactly 3 points an affine fit is exact and RMS is 0. TPS is always exact on its points (GDAL and QGIS docs both note TPS honours every GCP).
- Therefore mapwright should hold out points: fit on some, measure error on the rest (leave-one-out). Report held-out error in metres, not only RMS in pixels. This is standard model validation and mapwright's design choice; no map tool above enforces it.
- Practical guidance: use 6-10 or more well-spread points for affine on a scan; points clustered in one corner give a fit that is wrong elsewhere (QGIS Georeferencer docs advise spreading points; numbers unverified).
- A period pass mark in sheet units: the mid-century US accuracy standard for scales of 1:20,000 and smaller tested well-defined points against a fiftieth of an inch (about 0.5 mm) on the sheet; nine in ten had to pass, and displaced symbols were excused (Monmonier, How to Lie with Maps, 1991 ed., ch. 3). It is not the current US standard, and it needs the sheet size or the scan DPI. On a picture of unknown size report held-out error in metres instead.

### 5.4 Where GCPs come from
1. Printed graticule or grid labels (best: exact numbers on the map).
2. Named places matched to a gazetteer: OCR name, look up coordinates, use the label's anchor point. Error is large (a label sits beside its place) and ambiguous names (Springfield) must be dropped unless context settles them (mapKurator's gazetteer linking faces the same problem, Kim et al., 2023).
3. Feature matching against a reference basemap (road intersections). Possible future work.
4. A person clicking points (Map Warper and Allmaps editors).

A VLM saying "this is central Paris" is a search hint, never a GCP.

Two sources never supply GCPs. An inset: find inset boxes first and leave them out, since a feature inside one is at the inset's scale, and islands have been copied onto main maps at inset size. Public Soviet maps from the late 1930s on, more so from the mid 1960s: towns, coasts, rivers and roads were shifted on purpose, by up to about 25 miles, and city maps often had no scale (Monmonier, How to Lie with Maps, 1991 ed., ch. 4, ch. 8).

### 5.5 When a georeference is "earned"
Proposed rule for mapwright: report a georeference only when there are at least affine-minimum + 2 GCPs (5 or more), from sources 1, 2 or 4, with held-out error below a threshold set per map scale (for example under 1% of the map's width on the ground). Otherwise output `georeference: null` with the reason and any candidate GCPs found. The thresholds are proposals to calibrate in section 9.

## 6. Tracing features into vectors

### 6.1 Pipeline
1. Clean: deskew, remove scan noise (median filter), optionally flatten paper colour.
2. Separate colours: quantise with k-means in CIELAB, or match legend swatches (section 3.1). Map colour layer separation on historical maps is an established research area (Chiang et al., 2020, "Using Historical Maps in Scientific Studies", Springer).
3. Make a binary mask per class (water blue, roads red, contours brown).
4. Areas: trace mask outlines to polygons. Lines: skeletonise the mask (Zhang-Suen thinning, Zhang and Suen, 1984; available as `skimage.morphology.skeletonize`), then walk the skeleton into polylines and simplify (Douglas-Peucker, Douglas and Peucker, 1973).
5. Smooth outlines: potrace converts a bitmap to smooth Bezier curves and is the standard tool for clean line art (Selinger, 2003, "Potrace: a polygon-based tracing algorithm"). It traces one colour at a time, so run it per mask.
6. Text removal before tracing: mask out detected text polygons (section 4) or labels become blobs and broken lines.
7. If georeferenced, transform vertex coordinates and export GeoJSON; otherwise export pixel-space SVG or GeoJSON with `crs: null`.

### 6.2 Known failure points
- Labels and symbols crossing lines break them; skeletons sprout spurs that need pruning (standard in skeletonisation literature; Zhang and Suen, 1984 notes thinning artefacts).
- Dashed and dotted lines need gap closing (morphological closing) and that also joins features that should stay apart.
- Similar colours (two greens) merge after scanning; legend-guided matching helps.
- Hatched or patterned fills are not one colour; texture classification is needed (unverified that any simple method works well; learned segmentation is the usual answer, Chiang et al., 2020).
- Learned approaches (for example the DARPA/USGS AI for Critical Mineral Assessment map feature extraction challenge, 2022-2023) beat hand rules on geological maps but need training data (USGS/DARPA CMA challenge pages; results unverified).

### 6.3 Metrics for `trace`
Pixel IoU per class against a hand-made mask; for lines, buffered precision and recall (fraction of traced length within k pixels of truth, and the reverse); topology counts (number of connected components, junctions). These are standard segmentation and road-extraction measures (unverified specific citation; road extraction papers use "completeness/correctness" within a buffer, Wiedemann et al., 1998).

## 7. Real map or invented map

The question has three parts, and mapwright should answer each separately:

1. Is it a map of a real place? Evidence: names that match a gazetteer and lie near each other in the right relative arrangement; a coastline or road network that matches a reference. Several matched names whose real positions fit one affine transform with low error is strong evidence; matched names that cannot fit one transform suggest a fictional map borrowing real names (mapwright design; the fitting itself uses section 5).
2. Is it a fictional map (fantasy, game)? Evidence: no names match, or matches are scattered; drawing style. A VLM's style call ("hand-drawn fantasy map") is useful but must not be the only evidence.
3. Is it an AI-generated or altered picture? Signs: garbled or pseudo-text labels, roads that end nowhere, rivers that split downstream, legends whose symbols do not appear on the map (observations from AI image critique; unverified as a benchmarked detector). Geographic deepfake detection on satellite images exists (Zhao et al., 2021, "Deep fake geography? When geospatial data encounter Artificial Intelligence"), but no benchmark for drawn maps was found (unverified).

Output: `place_reality: real | fictional | mixed | undetermined` with a list of evidence items, each pointing to crops and gazetteer hits. Default is `undetermined`.

### 7.1 Period tells and persuasive-map tells (books, 2026-11-15)

Years are book facts, not cross-checked. HW = Harley and Woodward, History of Cartography vol. 1.

- Dating: the youngest convention on a map gives its earliest possible date. A ratio scale means after 1806, land contours after 1791, a Greenwich prime meridian after 1884, the name America after 1507 (Thrower, Maps and Civilization, ch. 5-7). The table is in [cartography-design.md](cartography-design.md) section 1.6.
- Names on a medieval map can span a thousand years (the Hereford map mixes fourth-century Roman names with its own day), so the youngest name dates it. A scale inside a circle (the four earliest charts only), a drawn compass rose (not before 1375), Jerusalem at the centre (about 1250 to 1400) and the count of lines at the centre of a rhumb network (16, or 32 after 1449) each narrow the range (HW ch. 18-19; Monmonier, How to Lie with Maps, 1991 ed., ch. 4).
- Suspect as an old map: a mappa mundi with a graticule or bar scale before 1400, or rhumb lines before 1300; a portolan chart with a latitude scale, graticule or north arrow before 1500; a Latin or western map with Ptolemaic coordinates or projection before about 1400 (HW ch. 18-19).
- Tells of a persuasive map: a thick straight line for one party and a thin crooked one for the other, arrows across a border, concentric rings with alarming labels, one language's names only, tight cropping that leaves out the neighbours, stamped trees and other decoration, a projection that enlarges the subject. `read` lists the tells it sees. Whether the map misleads is a judgement it does not make (Monmonier, ch. 5-7).

## 8. A "not sure" output that avoids inventing

### 8.1 Rules
- Every field has `value`, `status` and `evidence`. Status is one of `read` (printed and read), `measured` (computed from pixels), `inferred` (reasoned, with stated chain), `disputed` (sources disagree), `not_present` (looked and it is not on the map), `undetermined` (could not tell).
- `read` and `measured` require evidence with a pixel box. No box, no value.
- Numbers that need a scale or georeference (distances, areas, coordinates) are `undetermined` until the scale or transform has status `read` or `measured`.
- Run the VLM twice with different prompts or crops; disagreement downgrades to `disputed`. Self-consistency sampling as a hallucination signal is described by Manakul et al., 2023 (SelfCheckGPT).
- Ask existence first ("is there a scale bar? answer yes, no or unsure, and give its box") before value questions. Asking "what is the scale?" invites an invented one; this matches MapEval's finding that models answer confidently when wrong (Dihan et al., 2024; inference, unverified as a measured effect for this prompt pattern).
- Gazetteer matches and VLM guesses go in separate fields from what is printed.
- Lines, boundaries and colours read off a map are reported as symbols, not as features on the ground: maps carry generalised, displaced or invented artefacts that readers take as real, and image-model maps add more (Kimerling et al., Map Use, ch. 12).
- Hue is not magnitude, counts are not rates, and green is not lush: `read` does not infer these from colour alone (Kimerling et al., Map Use, ch. 6, 9, 10).
- A feature seen in one source only is reported as unconfirmed. Commercial maps may hold streets and towns planted to catch copying, official plans hold streets that were never built, and a map compiled from other maps copies their mistakes (Monmonier, How to Lie with Maps, 1991 ed., ch. 4).

### 8.2 Example

```json
{
  "title": {"value": "Plan of the Town of Bath", "status": "read", "evidence": [{"box": [120, 40, 880, 95], "by": ["ocr", "vlm"]}]},
  "scale": {"value": null, "status": "not_present", "evidence": [{"note": "no bar, fraction or verbal scale found; full-page scan for text matching scale patterns"}]},
  "legend": {"value": [], "status": "not_present"},
  "names": [
    {"text": "Abbey", "status": "read", "box": [410, 512, 470, 530], "matched_name": "Bath Abbey", "gazetteer": "osm:..."},
    {"text": "Ave?n", "status": "disputed", "readings": {"ocr": "Aveen", "vlm": "Avon"}, "box": [...]}
  ],
  "georeference": {"value": null, "status": "undetermined", "reason": "3 candidate GCPs from names; 5 needed", "candidates": [...]},
  "place_reality": {"value": "real", "status": "inferred", "evidence": ["3 names match Bath, UK and fit one affine transform with 140 m held-out error"]}
}
```

## 9. Test protocol

### 9.1 Map set (about 60 maps to start)
Each map comes with a hand-made answer file in the same JSON shape as section 8, including `not_present` fields.

| Group | Count | Source idea | Tests |
|---|---|---|---|
| Modern street/topographic with grid ticks | 10 | USGS topo maps (public domain), OpenStreetMap renders (ODbL) | scale, names, georeference |
| Historical scans | 10 | David Rumsey Collection, Library of Congress (check each licence) | curved text, legend, georeference from names |
| Choropleth / thematic | 10 | Rendered from public data, or MapQA images | legend reading, value lookup |
| Screenshots (web maps) | 8 | Own renders of OSM tiles at known zoom | scale from zoom, names, no-scale cases |
| Hand drawings / sketches | 6 | Own drawings with known intent | tracing, `undetermined` handling |
| Fantasy / game maps | 8 | Own or openly licensed fantasy maps | `fictional`, no invented georeference |
| Traps | 8 | Maps with scale removed, real names on invented layout, AI-generated maps, mirrored real map | `not_present`, `mixed`, hallucination rate |

Synthetic maps rendered from OSM with known style give exact truth for every label, line and coordinate and can be generated in any number (method used for synthetic training data in mapKurator, Kim et al., 2023; and MapQA, Chang et al., 2022).

### 9.2 Metrics

| Field | Metric | Target to start (proposal) |
|---|---|---|
| Names | word-level precision/recall (IoU over 0.5 on box + exact text), character error rate | recall 0.7, CER under 0.15 on modern maps |
| Legend | entry recall; swatch-to-region match accuracy | 0.8 |
| Scale | exact match for fractions; relative error for bar-derived m/px | under 5% error |
| Georeference | held-out GCP error in metres and as % of map width; rate of georeferences issued on maps with none possible | under 1%; issued-when-impossible = 0 |
| Trace | per-class IoU; buffered line precision/recall at 3 px | IoU 0.7 |
| Reality | accuracy over real/fictional/mixed | 0.85 |
| Hallucination | share of fields with status read/measured whose truth is `not_present` | under 2%, hard fail above 5% |
| Abstention | share of fields marked `undetermined` whose truth was readable | report, keep under 25% |

The hallucination and abstention pair is the key trade-off: a tool that says "undetermined" to everything has zero hallucination and is useless, so both are reported together (selective prediction framing, as in risk-coverage curves, El-Yaniv and Wiener, 2010).

### 9.3 Running it
- One command runs `read` and `trace` over the set, writes outputs, scores them against answers, and prints a table per group plus a list of the worst ten fields with crops.
- Store the model name and version with every score; rerun when the VLM changes.
- Add every real user failure as a new test map.

## 10. Open questions
- Which text spotter to bundle: mapKurator's model weights size and licence, versus PaddleOCR, versus VLM-only reading with crops (need measurements on section 9's set).
- Whether a local VLM (on Ollama) is good enough for the "usually reliable" tier or a hosted model is needed.
- Thresholds in 5.5 and 9.2 are guesses until the first run.
- Licences of historical scans for a public test set.

## Sources
All accessed 2026-11-14. Entries marked (unverified) were cited from memory and need a check of the exact figures.

- Chang, S., Palzer, D., Li, J., Fosler-Lussier, E., Xiao, N. (2022). MapQA: A Dataset for Question Answering on Choropleth Maps. arXiv:2211.08545. https://arxiv.org/abs/2211.08545 (counts checked 2026-11-14)
- Dihan, M. L., et al. (2024). MapEval: A Map-Based Evaluation of Geo-Spatial Reasoning in Foundation Models. arXiv:2501.00316; ICML 2025. https://arxiv.org/abs/2501.00316 (abstract figures checked 2026-11-14)
- Xing, S., et al. (2025). Can Large Vision Language Models Read Maps Like a Human? (MapBench). arXiv:2503.14607. https://arxiv.org/abs/2503.14607 (counts checked 2026-11-14)
- Lacoste, A., et al. (2023). GEO-Bench: Toward Foundation Models for Earth Monitoring. NeurIPS Datasets and Benchmarks. https://arxiv.org/abs/2306.03831
- Masry, A., et al. (2022). ChartQA. Findings of ACL 2022. https://arxiv.org/abs/2203.10244
- Li, Z., Chiang, Y.-Y., et al. (2020). An Automatic Approach for Generating Rich, Linked Geo-Metadata from Historical Map Images. KDD 2020. (mapKurator origin) https://arxiv.org/abs/2112.01671 (unverified link)
- Kim, J., Li, Z., Lin, Y., Namgung, M., Jang, L., Chiang, Y.-Y. (2023). The mapKurator System: A Complete Pipeline for Extracting and Linking Text from Historical Maps. SIGSPATIAL 2023. https://arxiv.org/abs/2306.17059 ; code https://github.com/knowledge-computing/mapkurator-system
- Chiang, Y.-Y., Duan, W., Leyk, S., Uhl, J. H., Knoblock, C. A. (2020). Using Historical Maps in Scientific Studies. Springer.
- Tesseract OCR documentation, "Improving the quality of the output". https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- GDAL gdalwarp documentation (-order, -tps, GCP transforms). https://gdal.org/en/stable/programs/gdalwarp.html
- GDAL gdal_translate documentation (-gcp). https://gdal.org/en/stable/programs/gdal_translate.html
- QGIS Georeferencer documentation (transformation types, residuals). https://docs.qgis.org/latest/en/docs/user_manual/working_with_raster/georeferencer.html
- Allmaps documentation and @allmaps/transform. https://allmaps.org/ ; https://github.com/allmaps/allmaps
- Allmaps / IIIF Georeference Annotation specification. https://iiif.io/api/extension/georef/
- Map Warper help and source. https://mapwarper.net/ ; https://github.com/timwaters/mapwarper (control-point minimum and transforms read from the source 2026-11-16)
- Selinger, P. (2003). Potrace: a polygon-based tracing algorithm. https://potrace.sourceforge.net/potrace.pdf
- Zhang, T. Y., Suen, C. Y. (1984). A fast parallel algorithm for thinning digital patterns. Communications of the ACM 27(3).
- Douglas, D., Peucker, T. (1973). Algorithms for the reduction of the number of points required to represent a digitized line. Cartographica 10(2).
- scikit-image skeletonize. https://scikit-image.org/docs/stable/api/skimage.morphology.html#skimage.morphology.skeletonize
- Wiedemann, C., Heipke, C., Mayer, H., Jamet, O. (1998). Empirical evaluation of automatically extracted road axes. (unverified exact venue)
- Zhao, B., Zhang, S., Xu, C., Sun, Y., Deng, C. (2021). Deep fake geography? When geospatial data encounter Artificial Intelligence. Cartography and Geographic Information Science 48(4).
- Manakul, P., Liusie, A., Gales, M. (2023). SelfCheckGPT. EMNLP 2023. https://arxiv.org/abs/2303.08896
- El-Yaniv, R., Wiener, Y. (2010). On the Foundations of Noise-free Selective Classification. JMLR 11.
- USGS / DARPA AI for Critical Mineral Assessment Competition (2022-2023). https://criticalminerals.darpa.mil/ (link answered 200 on 2026-11-16; page content is script-rendered and was not read)
- Slocum, T., et al. Thematic Cartography and Geovisualization, 3rd ed. Pearson.
