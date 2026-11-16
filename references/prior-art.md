# Prior art for mapwright

Research date: 2026-11-14. Scope: what already exists for agents that read, write, find
and generate maps, so mapwright does not duplicate it. Every claim carries a source. Items
marked "(unverified)" came from memory or a secondary listing and were not checked against
a primary page on the research date. Wheel and install sizes are approximate and marked
unverified unless a number was read off PyPI or npm that day; re-check them before quoting.

## 1. Agent map tools: MCP servers and skills

### 1.1 Vendor-hosted map MCP servers (real-world, API key required)

**Mapbox MCP server** (`@mapbox/mcp-server`, github.com/mapbox/mcp-server). Officially
maintained by Mapbox. Tools cover directions, isochrones, matrix, forward and reverse
geocoding, POI search, static map images and interactive maps in chat. A hosted endpoint
runs at `https://mcp.mapbox.com/mcp`; local runs need `MAPBOX_ACCESS_TOKEN`. The docs listed
version v0.12.0.
Sources: https://docs.mapbox.com/api/guides/mcp-server/ ,
https://docs.mapbox.com/location-ai/mcp-servers/mcp-server/ , https://github.com/mapbox/mcp-server/wiki

**Mapbox Developer MCP server.** A second Mapbox server aimed at style and token work for
developers (style editing, previews) (unverified: only a directory listing was seen).
Source: https://glama.ai/mcp/servers/jwhmevnk9z

**Google Maps Grounding Lite.** Google's hosted MCP server at
`https://mapstools.googleapis.com/mcp` (Streamable HTTP). It grounds an LLM in places,
weather and routes data, with `search_places` among its tools; auth is an API key header or
OAuth scope `maps-platform.mapstools`. Three core tools are offered.
Sources: https://developers.google.com/maps/ai/grounding-lite ,
https://developers.google.com/maps/ai/grounding-lite/reference/mcp ,
https://developers.google.com/maps/architecture/grounding-with-maps-mcp

**Reference Google Maps server** from the modelcontextprotocol/servers repo
(`@modelcontextprotocol/server-google-maps`: geocode, places, directions, elevation) was
moved to the archived servers repo (read-only); npm marks it deprecated at 0.6.2, MIT, still runs via `npx -y @modelcontextprotocol/server-google-maps` with `GOOGLE_MAPS_API_KEY` (checked 2026-11-14, https://archestra.ai/mcp-catalog/modelcontextprotocol__servers-archived__src__google-maps).
Source: https://github.com/modelcontextprotocol/servers-archived

**Third-party Mapbox wrappers** exist too, e.g. AidenYangX/mapbox-mcp-server (navigation,
matrix, geocoding).
Source: https://glama.ai/mcp/servers/AidenYangX/mapbox-mcp-server

### 1.2 Open GIS MCP servers

**nkarasiak/qgis-mcp.** A QGIS plugin opens a socket inside QGIS; an external Python MCP
server talks to it. Needs QGIS 3.28+ (README: 3.28 to 4.x) and `uv`; no Python version stated. Licence split: plugin GPL-2.0-or-later, MCP server MIT. About 440 stars. The plugin is in the QGIS plugin manager as "QGIS MCP". Install line for Claude Code per the README:
`claude mcp add -s user qgis -- uvx --from https://github.com/nkarasiak/qgis-mcp/archive/refs/heads/main.zip qgis-mcp-server`
(checked 2026-11-14, https://github.com/nkarasiak/qgis-mcp).
Sources: https://vibeindex.ai/mcp/nkarasiak/qgis-mcp , https://github.com/nkarasiak/qgis-mcp

**jjsantos01/qgis_mcp.** The original QGIS MCP: project creation, layer loading, running
processing algorithms and arbitrary PyQGIS code inside a running QGIS.
Sources: https://glama.ai/mcp/servers/@jjsantos01/qgis_mcp/inspect ,
https://claudemarketplaces.com/mcp/jjsantos01/qgis_mcp

**nic01asFr/QgisRemoteMCP and QgisStreamMCP.** QGIS in Docker, with OSM basemaps.
Source: https://glama.ai/mcp/servers/nic01asFr/QgisStreamMCP

**gis-mcp-server** (PyPI, matbel91765). CRS transforms, geocoding and routing; defaults to
public Nominatim and OSRM endpoints, overridable by env vars.
Sources: https://pypi.org/project/gis-mcp-server , https://lobehub.com/mcp/matbel91765-gis-mcp-server

**mcp-geo** (PyPI). Geocoding, routing, Overpass OSM queries, geometry ops, file
inspection, raster sampling, elevation, isochrones, static maps and a workspace store. This
is the broadest single real-world overlap found. Version and licence (could not verify: the PyPI page failed to load on 2026-11-14).
Source: https://pypi.org/project/mcp-geo/

**wiseman/osm-mcp.** An MCP server for OpenStreetMap data (details not opened).
Source: https://relatedrepos.com/gh/wiseman/osm-mcp

**mahdin75/gis-mcp.** A Python GIS MCP built on shapely, pyproj, geopandas and rasterio
(geometry ops, CRS, raster), plus PySAL, folium/pydeck, matplotlib, OSMnx, STAC/Planetary Computer, GBIF and GADM tools. MIT, v0.15.0 beta. It already makes static and interactive maps, so it is the second big real-world overlap after mcp-geo (checked 2026-11-14, https://github.com/mahdin75/gis-mcp).
Source: https://github.com/mahdin75/gis-mcp

Directory searches for more: https://glama.ai/mcp/servers?query=qgis

### 1.3 Fantasy and game map agent tools

**fmg-mcp.** Drives Azgaar's Fantasy Map Generator in a real browser through Playwright so
an MCP client can generate maps, inspect them and export screenshots, SVG or JSON. Runs over
stdio or HTTP. This is the heaviest overlap with mapwright's "generate fantasy map" lane. Env vars `FMG_HEADLESS`, `FMG_OUTPUT_DIR`; a Docker option; a related listing offers it as a remote HTTP claude.ai custom connector. The Glama API path names the author as rashestbread691/fmg-mcp; repo, licence and maintenance (could not verify, 2026-11-14).
Sources: https://glama.ai/mcp/servers/y1t65ahcug , https://glama.ai/mcp/servers/jz6spqiujn

**Mnehmos/rpg-mcp.** An RPG game-state MCP that ships Azgaar reference notes and a licence
note for reusing FMG data.
Sources: https://glama.ai/mcp/servers/@Mnehmos/rpg-mcp/blob/ea933ed6a4b58565dd0d6f34b777961f0509410e/reference/AZGAAR_LICENSE_NOTES.md

**"fantasy-map-generator" skill** (`npx skills add blammectrappora/fantasy-map-generator`).
Listed as an AI fantasy map generator for worldbuilders; whether it wraps Azgaar or an image
model was not confirmed (could not verify, 2026-11-14).
Source: https://openskillindex.com/skills/clawdbot-skills-fantasy-map-generator

**generate2dmap skill.** A 2D game-map generation skill from the agent-sprite-forge set (0x0funky); contents not opened (could not verify).
Sources: https://mcp.directory/skills/generate2dmap , https://claudemarketplaces.com/skills/0x0funky/agent-sprite-forge/generate2dmap

**Other game and worldbuilding MCPs found 2026-11-14** (listings only, not opened):
- RPG Maker MV MCP (diegolopez0208): RPG Maker tile maps; listed July 2026. https://enterprisedna.co/directories/mcp/diegolopez0208-rpgmakermvultimate-mcp
- World Anvil MCP (datagen24): reads and writes World Anvil worlds. https://glama.ai/mcp/servers/@datagen24/World-Anvil-MCP
- vibe-worldbuilding-mcp (jasnonaz) and fantasy-world-mcp (DangerBlack): lore, region descriptors and history simulation, no drawn maps. https://mcpservers.org/es/servers/jasnonaz/vibe-worldbuilding-mcp , https://glama.ai/mcp/servers/DangerBlack/fantasy-world-mcp

**"map-generator" skills** (dmccreary and vishalsachdev claude-skills): interactive Leaflet map MicroSims for teaching geography. They overlap mapwright's "emit a Leaflet HTML page" output; small install counts.
Sources: https://skills.sh/vishalsachdev/claude-skills/map-generator , https://playbooks.com/skills/dmccreary/claude-skills/map-generator

**World-building skills** (wordflowlab fantasy-world-building, Dorothy world-builder) write
setting lore, not maps.
Sources: https://claudemarketplaces.com/skills/wordflowlab/novel-writer-skills/fantasy-world-building ,
https://openskillindex.com/skills/charlie85270-dorothy-world-builder

### 1.4 Local siblings already in Mark's catalog

`polywright-capture` already turns a real place into a 3D model from OSM plus public
elevation (`pw.py place`), and `fractalwright` already does fBm terrain. mapwright should
call or point to these rather than redo them (source: the skill descriptions installed in
this environment, 2026-11-14).

### 1.5 Gap

No tool found does all of: offline, stdlib-first reading of map files (GeoJSON, KML, GPX,
SVG, Azgaar `.map`, Wonderdraft/Dungeondraft files), procedural fantasy and sci-fi map
generation without a browser, and real-world map rendering with one CLI. The MCP servers
above are either vendor API wrappers (Mapbox, Google), QGIS remotes, or one browser-driven
fantasy generator.

## 2. Open renderers, style languages and tile tools

| Tool | What it is | Licence | Install size | Source |
|---|---|---|---|---|
| MapLibre GL JS | WebGL vector-tile renderer, fork of Mapbox GL JS v1 | BSD-3-Clause | ~1.06 MB `dist/maplibre-gl.js` (minified) at v6.18.0; LICENSE.txt is BSD-3-Clause (https://cdn.jsdelivr.net/npm/maplibre-gl/dist/maplibre-gl.js, https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt, checked 2026-11-16) | https://github.com/maplibre/maplibre-gl-js |
| MapLibre Style Spec | JSON style language (sources, layers, expressions) | BSD-3-Clause, with bundled third-party notices (an MIT part, d3-color BSD-3) in its LICENSE.txt; no ISC seen (checked 2026-11-14, https://github.com/maplibre/maplibre-style-spec) | small npm pkg | https://maplibre.org/maplibre-style-spec/ |
| MapLibre Native (`@maplibre/maplibre-gl-native`) | C++ renderer with Node bindings; headless PNG render of a style | BSD-2-Clause | prebuilt binaries tens of MB (unverified) | https://github.com/maplibre/maplibre-native |
| Leaflet | Small raster/vector-overlay JS map library | BSD-2-Clause | ~42 KB gz JS | https://leafletjs.com/ |
| OpenLayers | Full-featured JS GIS client, many projections | BSD-2-Clause | large npm, tree-shakable | https://openlayers.org/ |
| Mapnik | C++ server-side raster renderer (OSM Carto uses it) | LGPL-2.1 | native build, heavy | https://github.com/mapnik/mapnik |
| CartoCSS | CSS-like style language compiled to Mapnik XML; effectively legacy | Apache-2.0 (checked 2026-11-14, https://github.com/mapbox/carto) | npm `carto` | https://github.com/mapbox/carto |
| Tangram | WebGL renderer with YAML scene files and shaders; low activity | MIT | ~615 KB `dist/tangram.min.js` at 0.21.1 (https://unpkg.com/tangram@0.21.1/dist/tangram.min.js, checked 2026-11-16) | https://github.com/tangrams/tangram |
| deck.gl | WebGL2/WebGPU layers for big data, works over MapLibre | MIT | modular npm | https://deck.gl/ |
| Kepler.gl | deck.gl-based exploratory app; heavy React app | MIT | large | https://github.com/keplergl/kepler.gl |
| D3-geo | Projections and SVG path generation in JS | ISC | ~36 KB `dist/d3-geo.min.js` at 3.1.2 (jsDelivr and npm registry, checked 2026-11-16) | https://github.com/d3/d3-geo |
| Protomaps / PMTiles | Single-file tile archive, served from static storage, plus basemap styles | BSD-3-Clause (format and tools) | `pmtiles` Go binary, Windows x86_64 zip 17.8 MB at v1.31.2; reference code BSD-3, spec public domain/CC0 (https://github.com/protomaps/go-pmtiles/releases, https://github.com/protomaps/PMTiles/blob/main/LICENSE, checked 2026-11-16) | https://protomaps.com/ , https://github.com/protomaps/PMTiles |
| tippecanoe (felt fork) | Builds vector tilesets (MBTiles/PMTiles) from GeoJSON | BSD-2-Clause | C++ build; GitHub releases carry no binaries at all (2.79.0, checked 2026-11-16 via the releases API) | https://github.com/felt/tippecanoe |

Notes:
- The MapLibre style spec is the open lingua franca for vector map styling; Mapbox's own
  spec after v2 is under a proprietary licence (Mapbox GL JS v2+ is not open source).
  Source: https://github.com/mapbox/mapbox-gl-js/blob/main/LICENSE.txt
- OpenStreetMap data is ODbL; any rendered OSM map must carry "© OpenStreetMap
  contributors". Source: https://www.openstreetmap.org/copyright
- Public OSM tile servers forbid heavy or bulk use; offline tiles are needed for batch
  rendering. Source: https://operations.osmfoundation.org/policies/tiles/

### Headless rendering options

1. **MapLibre Native via Node** (`@maplibre/maplibre-gl-native`): renders a style JSON to a
   PNG buffer without a browser. Needs Node and a prebuilt binary per platform.
   Source: https://github.com/maplibre/maplibre-native/tree/main/platform/node
2. **Playwright or Puppeteer screenshot** of a MapLibre/Leaflet page: the most faithful,
   but needs a ~150 MB+ Chromium download (unverified size). Playwright is Apache-2.0.
   Source: https://playwright.dev/docs/screenshots
3. **Static-map APIs** (Mapbox Static Images, Google Static Maps) need keys and cost money.
   Source: https://docs.mapbox.com/api/maps/static-images/
4. **Pure Python**: matplotlib or cartopy to PNG, or hand-written SVG. No tiles unless
   fetched. mapwright's stdlib path should be SVG written by hand (see section 5).

## 3. Hobby map programs

| Program | Kind | Licence / price | Source |
|---|---|---|---|
| Wonderdraft | Desktop fantasy world/region map painter, `.wonderdraft_map` files | Proprietary, one-time US$29.99; Windows 10 64-bit or Ubuntu (https://wonderdraft.net/, checked 2026-11-16) | https://www.wonderdraft.net/ |
| Dungeondraft | Desktop battle-map maker by the same team; `.dungeondraft_map` is JSON (unverified); exports Universal VTT | Proprietary, one-time US$19.99; Windows 10 64-bit or Ubuntu, no ARM64 (https://dungeondraft.net/, checked 2026-11-16) | https://dungeondraft.net/ |
| Inkarnate | Browser fantasy map maker, free tier and Pro subscription | Proprietary SaaS | https://inkarnate.com/ |
| Azgaar's Fantasy Map Generator | Browser procedural world generator (Voronoi cells, heightmap, rivers, states, cultures); `.map` save, SVG/PNG/GeoJSON export | MIT (checked 2026-11-14, https://raw.githubusercontent.com/Azgaar/Fantasy-Map-Generator/master/LICENSE, "Copyright 2017-2024 Max Haniyeu") | https://github.com/Azgaar/Fantasy-Map-Generator |
| Watabou generators | Medieval Fantasy City Generator, One Page Dungeon, Village, Perilous Shores etc.; browser | Freeware; the city generator source is public as watabou/TownGeneratorOS under GPL-3.0, an older Haxe version missing later features such as water bodies (checked 2026-11-14, https://watabou.itch.io/medieval-fantasy-city-generator/devlog/6592/source-code). Other generators are closed; terms for outputs (could not verify) | https://watabou.github.io/ , https://watabou.itch.io/ |
| Worldographer | Desktop hex/world/city/dungeon mapper (successor to Hexographer) | Proprietary, free and paid tiers | https://worldographer.com/ |
| Campaign Cartographer 3+ (ProFantasy) | CAD-based fantasy cartography on FastCAD | Proprietary, paid | https://www.profantasy.com/products/cc3plus.asp |
| Gaea (QuadSpinner) | Node-based terrain/heightmap generator | Proprietary; free Community edition with limits | https://quadspinner.com/ |
| World Machine | Node-based terrain generator | Proprietary; free Basic edition (non-commercial) | https://www.world-machine.com/ |
| Gaia Sky | Open 3D universe viewer using Gaia star catalogue | MPL-2.0 | https://codeberg.org/gaiasky/gaiasky |
| SpaceEngine | Procedural universe simulator/visualiser | Proprietary, paid on Steam | https://spaceengine.org/ |
| Universe Sandbox | Gravity/physics space simulator | Proprietary, paid on Steam | https://universesandbox.com/ |

Notes for mapwright:
- Azgaar FMG is MIT, so its algorithms (Voronoi grid, heightmap templates, river flow,
  burgs and states) can be studied and ported with attribution. Its `.map` format is a
  delimited text dump; a reader is feasible. Source: https://github.com/Azgaar/Fantasy-Map-Generator/wiki
- Azgaar has a newer successor in development ("Fantasy Map Generator 2" / Azgaar's
  Deorum) (could not verify, 2026-11-14: the repo page names neither).
- Wonderdraft, Dungeondraft, Inkarnate, CC3+, Worldographer, Gaea, World Machine,
  SpaceEngine and Universe Sandbox are closed. mapwright can read their exports (PNG,
  heightmaps, Universal VTT JSON) but should not try to reproduce them.
- Universal VTT (`.dd2vtt`, `.uvtt`) is a documented JSON with a base64 image plus walls,
  doors and lights; good stdlib read/write target (unverified spec location).
  Source: https://arkenforge.com/universal-vtt-files/ (unverified)

### Non-AI generation methods worth porting (checked 2026-11-14)
- **Wave Function Collapse** (mxgmn/WaveFunctionCollapse): tile and overlap constraint solver for dungeons, towns and tile maps. MIT, copyright 2016 Maxim Gumin; the sample images and tiles are excluded from the licence, so port the algorithm, not the samples. https://raw.githubusercontent.com/mxgmn/WaveFunctionCollapse/master/LICENSE
- **Azgaar FMG** (MIT, above): Voronoi cells, heightmap templates, rivers, states.
- **Watabou TownGeneratorOS** (GPL-3.0): idea source only, never copy into mapwright.

## 4. Python libraries

| Library | Use | Licence | Wheel size (Windows x64, approx.) | Source |
|---|---|---|---|---|
| pyproj | PROJ bindings: CRS transforms, geodesics | MIT | ~6.7 MB cp312 win wheel at 3.8.0, bundles PROJ data (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/pyproj/ |
| shapely | GEOS geometry ops | BSD-3-Clause | ~1.8 MB cp312 win wheel at 2.2.0 (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/shapely/ |
| geopandas | DataFrames of geometries, file IO via pyogrio | BSD-3-Clause | ~0.3 MB itself, but pulls pandas, numpy, shapely, pyproj, pyogrio (~60 MB+ total, estimate; geopandas 1.2.0 wheel itself 0.37 MB, PyPI JSON checked 2026-11-16) | https://pypi.org/project/geopandas/ |
| pyogrio | GDAL vector IO with bundled GDAL | MIT | ~34 MB cp312 win wheel at 0.13.0 (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/pyogrio/ |
| rasterio | GDAL raster IO (GeoTIFF, DEMs) | BSD-3-Clause | ~31 MB cp312 win wheel at 1.5.2, bundles GDAL (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/rasterio/ |
| cartopy | Projected maps on matplotlib; Natural Earth downloads | BSD-3-Clause (relicensed from LGPL-3 in 0.23, April 2024; https://cartopy.readthedocs.io/stable/_sources/whatsnew/v0.23.rst.txt, checked 2026-11-14) | ~9 MB cp312 win wheel at 0.26.0 + matplotlib (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/Cartopy/ |
| folium | Writes Leaflet HTML from Python | MIT | 0.13 MB wheel at 1.0.0, pulls jinja2, requests, branca (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/folium/ |
| prettymaps | Artistic OSM poster maps on matplotlib + osmnx | AGPL-3.0 (checked 2026-11-14, https://github.com/marceloprates/prettymaps) | small, heavy deps | https://github.com/marceloprates/prettymaps |
| osmnx | Downloads and analyses OSM street networks | MIT | small, pulls geopandas, networkx | https://pypi.org/project/osmnx/ |
| matplotlib basemap | Older projected-map toolkit; deprecated in favour of cartopy | MIT code; bundled GEOS library LGPL-2.1-only; basemap-data licences not stated on the repo page (checked 2026-11-14, https://github.com/matplotlib/basemap) | large data package | https://github.com/matplotlib/basemap |
| matplotlib | Plotting, PNG/SVG output | PSF-based matplotlib licence | ~9.3 MB cp312 win wheel at 3.11.2 (PyPI JSON, checked 2026-11-16) | https://pypi.org/project/matplotlib/ |

Notes:
- prettymaps being AGPL (confirmed 2026-11-14) matters: mapwright must not vendor its code, only
  call it as an optional external tool. Source: https://github.com/marceloprates/prettymaps
- The geopandas stack is the standard but is the opposite of stdlib-first; installing
  it for a quick map costs tens of MB. Source: https://geopandas.org/en/stable/getting_started/install.html
- The stdlib can do: JSON (GeoJSON), XML (KML, GPX, SVG, OSM XML), zipfile (KMZ),
  `urllib` (Nominatim, Overpass with a proper User-Agent), `math` for Web Mercator and
  great-circle maths, and `zlib`+`struct` for a minimal PNG writer. Nominatim's usage policy
  caps public use at 1 request per second. Source: https://operations.osmfoundation.org/policies/nominatim/

## 5. Recommendation: call, reimplement, leave alone

### Call (optional, detected at runtime, never required)
- **Mapbox and Google MCP servers** for live geocoding, routing and places when the user
  has keys. mapwright's skill text should point the agent to them, not wrap them.
- **QGIS MCP** (nkarasiak) for heavy GIS analysis when QGIS is installed.
- **mcp-geo / gis-mcp-server** when the user already runs them; do not duplicate their
  routing and isochrone tools.
- **pyproj, shapely, geopandas, rasterio, cartopy** if importable, for exact CRS work,
  reprojection of real data, GeoTIFF/DEM reads and publication maps. Fall back to stdlib.
- **MapLibre Native (Node) or Playwright** for rendering a MapLibre style to PNG, only when
  present; emit a MapLibre style JSON plus HTML page so the user can open it anyway.
- **tippecanoe / pmtiles** for building tile archives, shelling out if on PATH.
- **Azgaar FMG via fmg-mcp** when the user wants Azgaar's full simulation output.
- **polywright `pw.py place`** for real places in 3D, **fractalwright** for fBm art.

### Reimplement in stdlib (mapwright's core)
- Readers/writers: GeoJSON, KML/KMZ, GPX, OSM XML, CSV lat/lon, SVG, Universal VTT,
  Azgaar `.map` (read), plain heightmap PNG/PGM.
- Projections: equirectangular, Web Mercator, orthographic and a few others by formula,
  enough for SVG output; defer to pyproj for anything exact.
- Finding: Nominatim and Overpass queries via urllib, rate-limited, cached, with ODbL
  attribution added to every output.
- Rendering: hand-written SVG (coastlines, rivers, labels, hex and square grids, compass,
  scale bar) and a tiny PNG writer; emit a MapLibre style JSON and a Leaflet HTML page as
  text, without running a browser.
- Generation: fantasy terrain (value or simplex noise, Voronoi or hex cells, erosion-lite,
  river flow downhill, biome by height and moisture, Azgaar-style place names), dungeon and
  city layouts (BSP rooms, Watabou-like wards as an idea only), and sci-fi star maps
  (Poisson-disc star fields, jump-lane graphs, sector hexes). Port ideas from MIT Azgaar
  with credit; do not copy Watabou or prettymaps code.

### Leave alone
- Closed painters (Wonderdraft, Dungeondraft, Inkarnate, CC3+, Worldographer): read their
  exports only.
- Terrain suites (Gaea, World Machine) and universe sims (SpaceEngine, Universe Sandbox,
  Gaia Sky): reference them in the skill as hand-off targets.
- A full tile server, Mapnik/CartoCSS pipelines, Tangram, Kepler.gl and a deck.gl app:
  too heavy and out of scope; mention only.
- Bundling OSM tiles or bulk-fetching from tile.openstreetmap.org: forbidden by policy.

## Open questions
- Is fmg-mcp maintained, and what licence is it under? Repo (rashestbread691/fmg-mcp?) not found on 2026-11-14.
- Exact wheel sizes for the geo stack on Windows (read PyPI file lists).
- Watabou terms for outputs (code: TownGeneratorOS is GPL-3.0; prettymaps AGPL-3.0 confirmed).
- Whether Dungeondraft and Wonderdraft save files are documented enough to read.
- Archived Google Maps MCP: deprecated 0.6.2 but listed as still installable via npx (2026-11-14).

## Sources (accessed 2026-11-14)
- https://docs.mapbox.com/api/guides/mcp-server/
- https://docs.mapbox.com/location-ai/mcp-servers/mcp-server/
- https://github.com/mapbox/mcp-server/wiki
- https://glama.ai/mcp/servers/jwhmevnk9z
- https://glama.ai/mcp/servers/AidenYangX/mapbox-mcp-server
- https://developers.google.com/maps/ai/grounding-lite
- https://developers.google.com/maps/ai/grounding-lite/reference/mcp
- https://developers.google.com/maps/architecture/grounding-with-maps-mcp
- https://github.com/modelcontextprotocol/servers-archived
- https://vibeindex.ai/mcp/nkarasiak/qgis-mcp
- https://github.com/nkarasiak/qgis-mcp
- https://glama.ai/mcp/servers/@jjsantos01/qgis_mcp/inspect
- https://claudemarketplaces.com/mcp/jjsantos01/qgis_mcp
- https://glama.ai/mcp/servers/nic01asFr/QgisStreamMCP
- https://glama.ai/mcp/servers?query=qgis
- https://pypi.org/project/gis-mcp-server
- https://lobehub.com/mcp/matbel91765-gis-mcp-server
- https://pypi.org/project/mcp-geo/
- https://relatedrepos.com/gh/wiseman/osm-mcp
- https://github.com/mahdin75/gis-mcp
- https://glama.ai/mcp/servers/y1t65ahcug
- https://glama.ai/mcp/servers/@Mnehmos/rpg-mcp/blob/ea933ed6a4b58565dd0d6f34b777961f0509410e/reference/AZGAAR_LICENSE_NOTES.md
- https://openskillindex.com/skills/clawdbot-skills-fantasy-map-generator
- https://mcp.directory/skills/generate2dmap
- https://claudemarketplaces.com/skills/wordflowlab/novel-writer-skills/fantasy-world-building
- https://openskillindex.com/skills/charlie85270-dorothy-world-builder
- https://github.com/maplibre/maplibre-gl-js
- https://maplibre.org/maplibre-style-spec/
- https://github.com/maplibre/maplibre-native
- https://leafletjs.com/
- https://openlayers.org/
- https://github.com/mapnik/mapnik
- https://github.com/mapbox/carto
- https://github.com/tangrams/tangram
- https://deck.gl/
- https://github.com/keplergl/kepler.gl
- https://github.com/d3/d3-geo
- https://protomaps.com/
- https://github.com/protomaps/PMTiles
- https://github.com/felt/tippecanoe
- https://github.com/mapbox/mapbox-gl-js/blob/main/LICENSE.txt
- https://www.openstreetmap.org/copyright
- https://operations.osmfoundation.org/policies/tiles/
- https://operations.osmfoundation.org/policies/nominatim/
- https://playwright.dev/docs/screenshots
- https://docs.mapbox.com/api/maps/static-images/
- https://www.wonderdraft.net/
- https://dungeondraft.net/
- https://inkarnate.com/
- https://github.com/Azgaar/Fantasy-Map-Generator
- https://github.com/Azgaar/Fantasy-Map-Generator/wiki
- https://watabou.github.io/
- https://watabou.itch.io/
- https://worldographer.com/
- https://www.profantasy.com/products/cc3plus.asp
- https://quadspinner.com/
- https://www.world-machine.com/
- https://codeberg.org/gaiasky/gaiasky
- https://spaceengine.org/
- https://universesandbox.com/
- https://arkenforge.com/universal-vtt-files/
- https://pypi.org/project/pyproj/
- https://pypi.org/project/shapely/
- https://pypi.org/project/geopandas/
- https://pypi.org/project/pyogrio/
- https://pypi.org/project/rasterio/
- https://pypi.org/project/Cartopy/
- https://pypi.org/project/folium/
- https://github.com/marceloprates/prettymaps
- https://pypi.org/project/osmnx/
- https://github.com/matplotlib/basemap
- https://pypi.org/project/matplotlib/
- https://geopandas.org/en/stable/getting_started/install.html
