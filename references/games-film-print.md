# Games, film and print export reference

What mapwright's `export` must know to write maps for game engines, tabletop tools, film shots, print and 3D print hand-off. Every claim has a source in brackets, keyed to the Sources list at the end. Anything marked "(unverified)" was written from memory and needs checking against the source before code depends on it. Compiled 2026-11-14 without live fetches in this session, so treat version-specific numbers as due for a check.

## 1. Tilemap and level formats

### 1.1 Tiled TMX (XML) and TMJ (JSON)

Tiled saves maps as `.tmx` (XML) or `.tmj` (JSON, formerly `.json`), and tilesets as `.tsx` / `.tsj` [S1][S2]. The JSON format mirrors the XML element for element [S2].

Map-level attributes [S1]:

| Attribute | Values | Notes |
|---|---|---|
| `version` | e.g. `1.10` | format version, not the editor version |
| `orientation` | `orthogonal`, `isometric`, `staggered`, `hexagonal` | |
| `renderorder` | `right-down` (default), `right-up`, `left-down`, `left-up` | orthogonal only |
| `width`, `height` | tiles | ignored for infinite maps |
| `tilewidth`, `tileheight` | pixels | |
| `infinite` | 0 or 1 | infinite maps store data in `<chunk>` elements |
| `hexsidelength`, `staggeraxis` (`x`/`y`), `staggerindex` (`odd`/`even`) | | hex and staggered only |

Layer types: `layer` (tile layer), `objectgroup`, `imagelayer`, `group` [S1]. Tile layer `<data>` takes `encoding` = `csv` or `base64` (no encoding = deprecated per-tile XML), and for base64 an optional `compression` = `gzip`, `zlib` or `zstd`, zstd being a compile-time option since Tiled 1.3 [S1] (https://doc.mapeditor.org/en/stable/reference/tmx-map-format/). mapwright should default to CSV for readability and base64+zlib for size; zstd support in loaders is patchy (blocked: support varies per engine importer and version, no single source to check; test each loader).

Global tile IDs (GIDs): each tileset has a `firstgid`; GID 0 means empty [S1]. The top four bits of a 32-bit GID are flip flags and must be masked off before lookup [S1]:

| Bit | Mask | Meaning |
|---|---|---|
| 32 | `0x80000000` | flipped horizontally |
| 31 | `0x40000000` | flipped vertically |
| 30 | `0x20000000` | flipped diagonally (orthogonal) or rotated 60 degrees (hex) |
| 29 | `0x10000000` | rotated 120 degrees (hex only) |

Objects carry `x`, `y` in pixels, `width`, `height`, `rotation` in degrees clockwise, and shape children (`ellipse`, `point`, `polygon`, `polyline`, `text`) [S1]. Polygon points are relative to the object position [S1]. Custom properties take types `string`, `int`, `float`, `bool`, `color`, `file`, `object`, `class` [S1].

Practical export choice: write TMJ, since every target has a JSON parser; write TMX only when a loader needs it (some engine plugins read only TMX; blocked: per-plugin, no single source).

Chunk-stable rule for infinite or chunked maps: a cell is the same whatever order the map was generated in, and a cell already made is never overwritten. Test: generate region A, then A plus B; A's cells are byte-identical. One shared random stream fails this, so each chunk or coordinate gets its own seed (Watkins, Procedural Content Generation for Unity Game Development, ch. 3; Short and Adams, Procedural Generation in Game Design, ch. 26, p. 272-273).

### 1.2 LDtk

LDtk saves a single `.ldtk` JSON file, optionally with one `.ldtkl` file per level ("save levels to separate files") [S3][S4]. The JSON schema is published and versioned [S4].

Key structure [S4]:

| Path | Content |
|---|---|
| `defs.layers`, `defs.entities`, `defs.tilesets`, `defs.enums` | definitions |
| `levels[]` | `identifier`, `worldX`, `worldY`, `pxWid`, `pxHei`, `layerInstances[]` |
| `layerInstances[].__type` | `IntGrid`, `Entities`, `Tiles`, `AutoLayer` |
| `intGridCsv` | flat array of ints, row major, 0 = empty |
| `gridTiles[]` / `autoLayerTiles[]` | `px` [x,y], `src` [x,y] in the tileset, `f` flip bits (0 none, 1 X, 2 Y, 3 both), `t` tile id |
| `entityInstances[]` | `__identifier`, `px`, `fieldInstances[]` |
| `worldLayout` | `Free`, `GridVania`, `LinearHorizontal`, `LinearVertical` |

Fields beginning with `__` are read-only helpers that LDtk writes for loaders [S4]. LDtk also offers a "Super simple export": one PNG per layer plus CSV of IntGrid layers and a small JSON per level [S3]. For mapwright the IntGrid layer is the natural carrier of terrain classes (water=1, sand=2...), with an auto-layer rule set doing the tiling inside LDtk.

### 1.3 Godot TileMap

Godot 4.3 deprecated the single `TileMap` node in favour of one `TileMapLayer` node per layer [S5]. Tiles reference a `TileSet` resource by source id, atlas coordinates and alternative id [S5]. Tile data is stored in the scene (`.tscn`) as a packed byte array (`tile_map_data`), whose layout is internal: the class reference says only "The raw tile map data as a byte array", and the source versions it with a `TileMapLayerDataFormat` enum that has only `TILE_MAP_LAYER_DATA_FORMAT_0` today (https://github.com/godotengine/godot/blob/master/modules/tilemap/doc_classes/TileMapLayer.xml and `tile_map_layer.h`, checked 2026-11-16), so no stability promise. mapwright should not write that array directly; instead export TMJ or LDtk and let an importer plugin (for example YATI for Tiled, or the LDtk importer) build the scene, or emit a GDScript that calls `set_cell(coords, source_id, atlas_coords)` [S5].

## 2. Terrain heightmap imports

### 2.1 Unity Terrain

| Item | Value | Source |
|---|---|---|
| Heightmap resolution | power of two plus one: 33, 65, 129, 257, 513, 1025, 2049, 4097 | [S6] |
| Import format | RAW, 8-bit or 16-bit | [S6] |
| Byte order | Windows (little-endian) or Mac (big-endian), chosen on import | [S6] |
| Default terrain size | 1000 x 600 x 1000 m (blocked: the current manual no longer states a default; it gives only the ranges: width/length 1-100,000, height 1-10,000, heightmap resolution 2^n+1, https://docs.unity.com/en-us/engine/current/manual/creating-environments/script-terrain/terrain-other-settings) | [S6] |
| Height mapping | 0..65535 maps linearly to 0..Terrain Height | [S6] |

Write 16-bit little-endian RAW, rows top to bottom; Unity flips vertically relative to some tools, so mapwright's test must check orientation against a known asymmetric map (blocked: the manual does not say which way; Import Raw offers Depth 8/16 bit, Byte Order and Flip Vertically, https://docs.unity.com/en-us/engine/6000.6/manual/creating-environments/script-terrain/terrain-heightmaps). Tiled terrain beyond 4097 uses several Terrain objects with matching neighbours [S6].

### 2.2 Unreal Engine Landscape

Unreal recommends sizes that fill whole components without waste [S7]:

| Heightmap size | Quads/section | Sections/component | Components |
|---|---|---|---|
| 8129 x 8129 | 127 | 4 (2x2) | 32 x 32 |
| 4033 x 4033 | 63 | 4 | 32 x 32 |
| 2017 x 2017 | 63 | 4 | 16 x 16 |
| 1009 x 1009 | 63 | 4 | 8 x 8 |
| 1009 x 1009 | 126 | 1 | 8 x 8 |
| 505 x 505 | 63 | 4 | 4 x 4 |
| 505 x 505 | 126 | 1 | 4 x 4 |
| 253 x 253 | 63 | 4 | 2 x 2 |
| 127 x 127 | 63 | 4 | 1 x 1 |

Format: 16-bit grayscale PNG or 16-bit RAW (little-endian) [S7]. Scale [S7]:

- One heightmap pixel = X/Y scale in cm; default X/Y scale 100 means 1 m per pixel.
- Z scale 100 gives a range of -256 m to +256 m (512 m total). Height range in cm = Z scale x 512.
- Value 32768 is zero height.
- To fit a real relief of H metres: Z scale = H x 100 / 512 (for example 1000 m of relief needs Z = 195.3).

World Partition landscapes can be larger and are imported in tiles named `_x0_y0` (Epic's heightmap import page, checked 2026-11-16, https://dev.epicgames.com/documentation/unreal-engine/importing-and-exporting-landscape-heightmaps-in-unreal-engine, documents tiled import but not the pattern; the `name_x0_y0` suffix is from the editor's error text as reported on forums.unrealengine.com).

### 2.3 Godot Terrain3D

Terrain3D is a GDExtension addon, not core Godot [S8]. It stores terrain in regions; region size is configurable, default 256, and must exceed image width / 32 because the world holds at most 32 x 32 = 1024 regions [S8] (https://terrain3d.readthedocs.io/en/latest/docs/import_export.html). Its importer reads EXR, R16/RAW (`.raw` read as r16), PNG (8-bit only) and other Godot image formats, with a height scale and offset [S8]. 16-bit or 32-bit float (EXR) avoids terracing; mapwright should prefer EXR or R16 for it.

### 2.4 Roblox terrain from heightmap

The Terrain Editor's Import tool takes a heightmap image and an optional colormap that sets materials by colour [S9]. Terrain voxels are 4 x 4 x 4 studs [S9]. Max heightmap size and the colour-to-material table are documented on the same page; the limit is 4096 x 4096 px, .png or .jpg, one pixel = 4 studs (https://create.roblox.com/docs/parts/terrain). Scripts can also fill terrain with `Terrain:WriteVoxels` or `FillBlock` for full control [S10]. Scale: 1 stud = 28 cm. Fixed 2026-11-15: this is Roblox's own conversion, not only a community convention; the Units page lists length as 1 stud = 28 cm (https://create.roblox.com/docs/physics/units, checked 2026-11-15).

### 2.5 Minecraft

| Item | Value | Source |
|---|---|---|
| Overworld build height (Java 1.18+) | Y -64 to 319 (384 blocks) | [S11] |
| Custom dimension height limits | `min_y` multiple of 16, -2032..2031; `height` multiple of 16, max 4064 | [S11] |
| 1 block | 1 m by convention | [S11] |

Two routes:

1. Data pack world generation: JSON under `data/<ns>/worldgen/` (`noise_settings`, `density_function`, `biome`, `configured_feature`) and `dimension/` [S11]. It changes generation rules, not a fixed map, so it cannot reproduce an exact heightmap without very elaborate density functions.
2. WorldPainter: imports a grayscale heightmap (8- or 16-bit) into a world, with a scale and a water level, then exports a playable save [S12]. This is the route for an exact map. Hand off a 16-bit PNG at 1 px = 1 block plus a material mask.

Bedrock edition limits differ (blocked: not checked in this pass; see the Minecraft Wiki before relying on them).

## 3. Fog of war and minimaps

Fog of war is usually a low-resolution visibility texture laid over the map: one texel per tile or cell, three states (unseen, seen-before, visible now), blurred or bilinear-filtered when drawn [S13]. Visibility comes from field-of-view algorithms on the grid (shadowcasting is the common choice for roguelikes) [S14]. Tabletop VTTs (Foundry, Roll20, Owlbear Rodeo) compute vision from wall segments rather than tiles [S15]; mapwright can help by exporting wall polylines along with the image.

Universal VTT format (`.dd2vtt` / `.uvtt`, from Dungeondraft) is JSON with `resolution` (`map_size`, `pixels_per_grid`), `line_of_sight` (wall polylines in grid units), `portals` (doors), `lights`, and a base64 PNG image [S16]. Foundry and several modules import it [S16]. This is the single most useful tabletop export.

Common tabletop grid scale: 5 ft per square in D&D 5e [S17]; VTT images are often authored at 70, 100, 140 or 200 px per grid (practice figure, no single source; tunable default; Roll20 uses 70 px per unit [S15]).

Minimap approaches [S13]:

| Approach | Cost | Use |
|---|---|---|
| Pre-rendered map image, player marker drawn on top | cheapest | static worlds; mapwright can export this image directly |
| Second orthographic camera into a render texture | one extra render | dynamic worlds |
| Shader that samples the fog texture over the minimap | small | combine with fog of war |

Export a top-down image with a known world-to-pixel transform (origin and metres per pixel) in a sidecar JSON so the engine can place the marker.

## 4. Navigation meshes

Most engines build navmeshes with Recast-style voxelisation [S18]. Parameters that come from the map and its intended agent [S18][S19]:

| Parameter | Typical default | Notes |
|---|---|---|
| Agent radius | 0.5 m (Unity), 0.5 m (Godot) | erodes walkable area |
| Agent height | 2 m | |
| Max slope | 45 degrees | steeper is unwalkable |
| Step height | 0.4 m (Unity's manual, checked 2026-11-16, gives no default and advises 0.1 to 0.4 for a 2 m human, https://docs.unity.com/en-us/engine/current/manual/physics-section/physics-overview/character-control-section/class-character-controller) | |
| Cell size | about radius / 2 to / 3 | Recast guidance |

mapwright does not need to bake navmeshes; engines bake from geometry. What helps is exporting clean collision geometry and walkability/area masks (water, road with lower cost) that the engine can turn into navmesh areas or modifiers [S19]. A tile export carries a blocking layer for anything that stops movement, apart from the ordered draw layers (Watkins, Procedural Content Generation for Unity Game Development, ch. 3).

### 4.1 mapwright nav export

`mpw.py export DIR --nav -o map.nav.json` (or `--to nav`) works on dungeon and square battle recipes; hex maps, decks and worlds are refused. It merges walkable squares into axis-aligned rectangles (greedy: grow right, then down, row by row) and lists the shared edges between them as portals. Rectangles never mix floor and door squares, so a door is its own rectangle.

Fields: `w`, `h`, `units` (squares, origin top-left, y down), `moves` (8 neighbours, diagonal cost 1.414213562, no corner cutting, no diagonal through a door), `rects` (`id`, `x`, `y`, `w`, `h`, `area` floor or door; a locked door carries `lock` with the key id, a one-way door `enter_from` as the [dx, dy] side it is entered from), `portals` (`a`, `b`, `seg` as two square-corner points), and `entrance`, `goal` and `keys` when the recipe has them. Keys are sorted and the file is byte-identical for the same recipe.

Bars printed on every export: every walkable square covered exactly once, no wall covered, and the portal graph has the same connected components as the 4-way square grid (8-way without corner cutting joins the same squares). An engine can load the rectangles as convex navmesh polygons and the portals as their links, or run A* over rectangle centres and the funnel algorithm through the portal segments.

## 5. Film: animated routes and zoom shots

### 5.1 Frame rates and delivery

| Use | Rate | Source |
|---|---|---|
| Cinema | 24 fps (23.976 for NTSC-based video) | [S20] |
| PAL broadcast, Europe | 25 fps | [S20] |
| NTSC broadcast, web | 29.97 / 30 fps | [S20] |
| Smooth web and game capture | 60 fps | [S20] |

Render at the delivery rate; do not convert 30 to 24 afterward. Common resolutions: 1920x1080, 3840x2160 (UHD) [S20].

### 5.2 Flight path animation conventions

Conventions from travel-map films and documentary graphics (practice figure, no single source; tunable default):

- Draw the route line progressively, with an icon (plane, ship, marker) at its head, ease-in and ease-out at each stop.
- Air routes are drawn as great-circle arcs, often lifted into a curve on flat maps so short and long hops read differently.
- Hold 1 to 2 s on each named stop so labels can be read; reading speed for on-screen text is about 3 words per second (practice figure, no single source; tunable default).
- Keep the camera moving slower than the line; let the line lead.
- Avoid camera moves that require more than about one screen width of pan per second at 24 fps, to prevent strobing (judder guidance from cinematography: pan speed rule of about 7 s for an object to cross the frame at 24 fps) [S21] (RED: pan no faster than one full image width per 7 s at 24 fps, 180-degree shutter; checked 2026-11-16, https://www.red.com/red-101/camera-panning-speed).

### 5.2a Map shots and route animation (books)

- Map-shot grammar: establishing globe or map, push-in to a place name, dissolve to the location; a route line growing across the map; a hand placing pins; a map insert on a line of dialogue (Conley, Cartographic Cinema, p. 96, p. 105, p. 205).
- The map style matches the story's era and culture (Ptolemaic, early-modern engraved, mid-century relief globe, modern briefing screen) (Conley, p. 104, p. 205).
- Labels are story devices: decide what is named, what is withheld and when each label appears (Conley, p. 97, p. 103).
- A route animation reads a sync file of stops (name, time in seconds) shared with the edit, so voice and route stay matched (Conley, p. 105).
- Story-map print profile: endpaper spread with a gutter band kept clear, frontispiece page, chapter insets (Lewis-Jones, The Writer's Map, sec. 2).

### 5.3 Smooth zoom and pan (van Wijk and Nuij 2003)

van Wijk and Nuij, "Smooth and efficient zooming and panning", IEEE InfoVis 2003 [S22], model a view by centre u and width w, and find the optimal path between two views. With rho the ratio of zoom to pan speed (they found rho about 1.42, near sqrt(2), preferred in user tests [S22]), for start (u0, w0), end (u1, w1), d = |u1 - u0| [S22]:

```
b_i = (w1^2 - w0^2 + (-1)^i rho^4 d^2) / (2 w_i rho^2 d),  i = 0, 1
r_i = ln(-b_i + sqrt(b_i^2 + 1))
S   = (r1 - r0) / rho                                   # path length
u(s) = u0 + (w0/rho^2) * cosh(r0) * tanh(rho s + r0) - (w0/rho^2) * sinh(r0)
w(s) = w0 * cosh(r0) / cosh(rho s + r0)
```

When d is near zero use the pure-zoom case: S = |ln(w1/w0)| / rho, w(s) = w0 exp(k rho s) with k = sign(w1 - w0) [S22]. Animate s from 0 to S at constant speed; duration proportional to S (they suggest a constant velocity V so time = S/V) [S22]. d3-interpolate's `interpolateZoom` implements this with rho = sqrt(2) by default and returns a `duration` in ms computed as `|S| * 1000 * rho / sqrt(2)`, so exactly S x 1000 ms at the default rho [S23] (https://github.com/d3/d3-interpolate/blob/main/src/zoom.js). Copying that implementation is the lowest-risk route.

## 6. Print

### 6.1 Paper sizes

ISO 216 A series (portrait, mm) [S24]:

| Size | mm | in | Pixels at 300 ppi |
|---|---|---|---|
| A0 | 841 x 1189 | 33.1 x 46.8 | 9933 x 14043 |
| A1 | 594 x 841 | 23.4 x 33.1 | 7016 x 9933 |
| A2 | 420 x 594 | 16.5 x 23.4 | 4961 x 7016 |
| A3 | 297 x 420 | 11.7 x 16.5 | 3508 x 4961 |
| A4 | 210 x 297 | 8.3 x 11.7 | 2480 x 3508 |
| A5 | 148 x 210 | 5.8 x 8.3 | 1748 x 2480 |

North American sizes [S25]:

| Size | in | mm | Pixels at 300 ppi |
|---|---|---|---|
| Letter | 8.5 x 11 | 216 x 279 | 2550 x 3300 |
| Legal | 8.5 x 14 | 216 x 356 | 2550 x 4200 |
| Tabloid / Ledger (ANSI B) | 11 x 17 | 279 x 432 | 3300 x 5100 |
| ANSI C | 17 x 22 | 432 x 559 | 5100 x 6600 |
| ANSI D | 22 x 34 | 559 x 864 | 6600 x 10200 |
| Arch D (common poster) | 24 x 36 | 610 x 914 | 7200 x 10800 |

Pixels = inches x ppi; mm / 25.4 = inches.

### 6.2 Resolution, bleed and safe zone

| Rule | Value | Source |
|---|---|---|
| Raster resolution at final size | 300 ppi (offset and good digital); 150 ppi acceptable for large posters viewed from afar | [S26][S27] |
| Line art / 1-bit | 1200 ppi | [S26] |
| Bleed | 3 mm per edge (Europe), 0.125 in (3.175 mm) per edge (US) | [S26][S27] |
| Safe zone (keep text and labels inside) | 3 to 5 mm, or 0.125 to 0.25 in from trim | [S27] |
| File size with bleed | trim + 2 x bleed each axis (A4 with 3 mm bleed = 216 x 303 mm) | [S26] |

Map consequence: extend the map data into the bleed (render a larger extent), never stretch. Keep scale bar, legend, north arrow and credits inside the safe zone.

### 6.3 Folding

| Fold | Panels | Note | Source |
|---|---|---|---|
| Half (bi-fold) | 4 pages | | [S28] |
| Tri-fold (roll/letter) | 6 | inner folding panel 1/32 to 1/16 in (about 1 to 2 mm) narrower so it tucks in | [S28] |
| Z-fold / accordion | 6+ | panels equal width | [S28] |
| Map fold | accordion then cross-fold | road maps; panel edges get wear, keep labels off folds | [S28] |
| Gate fold | 6 | outer panels each half width of centre, minus about 1/16 in | [S28] |

Avoid placing small labels or thin features on a fold line; mapwright can output fold guides as a separate non-printing layer.

### 6.4 CMYK conversion caveats

- Convert with a named ICC profile matching the press: FOGRA39 / FOGRA51 (ISO coated, Europe), GRACoL 2013 / SWOP (US) [S29]. Ask the printer which one.
- Saturated RGB blues, greens and oranges (water, vegetation) fall outside CMYK gamut and dull; soft-proof first [S29].
- Total area coverage (ink limit) 300% to 340% for coated stock, lower (about 260%) for uncoated or newsprint [S29].
- Small black text and thin lines should be 100% K only, not rich black, to avoid misregistration [S29]. Rich black for large fills e.g. C60 M40 Y40 K100 (practice figure, no single source; tunable default; printers vary).
- Use a perceptual or relative colorimetric intent with black point compensation; relative keeps in-gamut colours exact [S29].
- Python note: Pillow's `ImageCms` can do ICC conversion; a plain `.convert("CMYK")` ignores profiles: Pillow's `rgb2cmyk` sets C, M, Y to 255 minus R, G, B and K to 0, "no undercolour removal" (https://github.com/python-pillow/Pillow/blob/main/src/libImaging/Convert.c, checked 2026-11-16), so blacks come out as C255 M255 Y255 K0.

### 6.5 PDF/X

| Standard | ISO | Colour | Transparency | Source |
|---|---|---|---|---|
| PDF/X-1a:2001/2003 | 15930-1/-4 | CMYK and spot only | flattened, none live | [S30] |
| PDF/X-3:2002/2003 | 15930-3/-6 | colour-managed RGB/Lab allowed with ICC | flattened | [S30] |
| PDF/X-4:2010 | 15930-7 | ICC-based, RGB allowed | live transparency and layers allowed | [S30] |

All require embedded fonts, an OutputIntent (the target ICC profile), and TrimBox/BleedBox set [S30]. PDF/X-4 is the current recommendation from most printers and from Ghent Workgroup (practice figure, no single source; tunable default; ask the printer). Python route: write a PDF with ReportLab or cairo, then validate or convert with Ghostscript's PDF/X support or a preflight tool (Acrobat, callas) [S30] (Ghostscript docs, checked 2026-11-16, https://ghostscript.readthedocs.io/en/latest/VectorDevices.html, say the PDFX option takes 1, 3 or 4 but a warning on the same page says only X-1 and X-3 are supported; validate X-4 output in a preflight tool).

## 7. 3D print terrain tiles (hand-off)

mapwright should export a heightmap or a mesh and hand it to a print tool (polywright-print, TouchTerrain, Blender).

| Item | Common value | Source |
|---|---|---|
| Vertical exaggeration, mountains | 1.0 to 1.5x | [S31] (practice figure, no single source; tunable default) |
| Vertical exaggeration, rolling or flat regions, city scale | 2x to 5x | [S31] (practice figure, no single source; tunable default) |
| TouchTerrain default z-scale | z-scale 1.0, tile width 80 mm, base 1 mm, print resolution 0.5 mm (defaults in `TouchTerrain_standalone.py`, https://github.com/ChHarding/TouchTerrain_for_CAGEO, checked 2026-11-16) | [S31] |
| Base thickness under lowest point | 1 to 2 mm minimum | [S31] |
| FDM nozzle | 0.4 mm, so features under about 0.8 mm horizontally vanish | [S32] |
| FDM layer height | 0.1 to 0.2 mm, so relief steps finer than that vanish | [S32] |

Rules: state the exaggeration on the print or its label (cartographic convention for relief models) (practice figure, no single source; tunable default); compute real scale first (tile mm / ground m), then exaggeration; keep tiles the same base height and size so they tile; output STL or 3MF in millimetres with a flat bottom and watertight walls [S32].

## 8. Open items

- Check current Unreal recommended size table and World Partition tile naming for UE 5.6+.
- Confirm Roblox heightmap max size and colormap material table.
- Confirm Terrain3D region sizes and import formats in its current release.
- Confirm d3 `interpolateZoom` duration constant before reusing it.
- Confirm Unity RAW row orientation with a test map.

## Sources

All accessed 2026-11-14 (from prior knowledge; URLs to be re-fetched before code relies on them).

- [S1] Tiled documentation, "TMX Map Format". https://doc.mapeditor.org/en/stable/reference/tmx-map-format/
- [S2] Tiled documentation, "JSON Map Format". https://doc.mapeditor.org/en/stable/reference/json-map-format/
- [S3] LDtk documentation, "Super simple export" and file format. https://ldtk.io/docs/
- [S4] LDtk JSON schema documentation. https://ldtk.io/json/
- [S5] Godot Engine documentation, "Using TileMaps" and `TileMapLayer` class (4.3+). https://docs.godotengine.org/en/stable/tutorials/2d/using_tilemaps.html
- [S6] Unity Manual, "Terrain settings" / "Working with Heightmaps". https://docs.unity3d.com/Manual/terrain-Heightmaps.html
- [S7] Unreal Engine documentation, "Landscape Technical Guide" (recommended sizes, scale). https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-technical-guide-in-unreal-engine
- [S8] Terrain3D documentation, "Importing data". https://terrain3d.readthedocs.io/
- [S9] Roblox Creator Docs, "Terrain Editor" (Import, heightmaps and colormaps). https://create.roblox.com/docs/studio/terrain-editor
- [S10] Roblox Creator Docs, `Terrain` class. https://create.roblox.com/docs/reference/engine/classes/Terrain
- [S11] Minecraft Wiki, "Custom world generation" and "Dimension type". https://minecraft.wiki/w/Custom_world_generation
- [S12] WorldPainter, "Importing height maps". https://www.worldpainter.net/
- [S13] Red Blob Games and general engine practice on fog of war and minimaps. https://www.redblobgames.com/
- [S14] RogueBasin, "FOV using recursive shadowcasting". https://www.roguebasin.com/
- [S15] Foundry VTT Knowledge Base, "Walls" and "Vision"; Roll20 help, page settings (70 px units). https://foundryvtt.com/kb/
- [S16] Universal VTT format (Dungeondraft export, `.dd2vtt`), as documented by importer modules such as "Universal Battlemap Importer". https://github.com/moo-man/FVTT-DD-Import
- [S17] D&D 5e System Reference Document 5.1, "Movement and Position" (5-foot squares, optional grid rule). https://dnd.wizards.com/resources/systems-reference-document
- [S18] Recast Navigation documentation. https://recastnav.com/
- [S19] Unity Manual, "AI Navigation" package; Godot docs, "Using NavigationMeshes". https://docs.unity3d.com/Packages/com.unity.ai.navigation@latest
- [S20] SMPTE / EBU common frame rates; YouTube Help, "Recommended upload encoding settings". https://support.google.com/youtube/answer/1722171
- [S21] RED Digital Cinema, "Panning Speed Best Practices" (checked 2026-11-16). https://www.red.com/red-101/camera-panning-speed
- [S22] J. J. van Wijk and W. A. A. Nuij, "Smooth and efficient zooming and panning", Proc. IEEE Symposium on Information Visualization (InfoVis) 2003, pp. 15-23. doi:10.1109/INFVIS.2003.1249004
- [S23] d3-interpolate, `interpolateZoom`. https://d3js.org/d3-interpolate/zoom
- [S24] ISO 216:2007, writing paper and certain classes of printed matter, A and B series.
- [S25] ANSI/ASME Y14.1 drawing sheet sizes; paper size tables. https://www.papersizes.org/
- [S26] Printer prepress guides (for example Moo, Vistaprint, Mixam "How to set up bleed"). https://www.mixam.co.uk/support/bleed
- [S27] Adobe InDesign Help, "Bleed and slug"; US printer guides (0.125 in bleed). https://helpx.adobe.com/indesign/
- [S28] Printer folding guides (for example PrintingForLess, "Brochure fold types"). https://www.printingforless.com/
- [S29] FOGRA and Idealliance (GRACoL) characterization data; Adobe "Color conversion" help. https://www.color.org/
- [S30] ISO 15930 series (PDF/X); Ghent Workgroup and PDF Association overviews. https://www.pdfa.org/
- [S31] TouchTerrain (Iowa State University) documentation and app defaults. https://touchterrain.geol.iastate.edu/
- [S32] Prusa Knowledge Base and Bambu Lab Wiki, layer height and minimum feature size. https://help.prusa3d.com/
