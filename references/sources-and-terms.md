# Map data sources and their terms

Reference for mapwright: what each source holds, how to get it, its licence, the credit line to save beside each file, and the usage rules a polite fetcher must follow.

**Verification status.** Drafted 2026-11-14 from memory, then source-checked the same day: claims tagged "(checked 2026-11-14)" were confirmed against the linked primary page. Claims marked "(unverified)" could not be confirmed from a primary page in that pass; untagged claims were not re-fetched. Rate limits change more often than licences.

## Rules mapwright applies to every source

1. Send a real User-Agent naming the application and a contact URL (the project page, not a personal email unless the user supplies one). OSM, Nominatim, Wikimedia and USGS all ask for this.
2. One request at a time per host unless the policy says otherwise. Back off on HTTP 429 and 503 and honour `Retry-After`.
3. Cache every response on disk and never fetch the same thing twice within the provider's cache period.
4. Prefer bulk downloads (extracts, dumps, single archives) over many API calls.
5. Write a sidecar next to every file: source id, URL, access date, licence, credit line, and any share-alike or non-commercial flag.
6. Never fetch from a source in the "never scrape" list below.

## OpenStreetMap

- **Holds:** worldwide vector data: roads, buildings, land use, POIs, boundaries, names.
- **Access:** planet file and diffs (planet.openstreetmap.org), regional extracts (Geofabrik, BBBike), Overpass API for queries, the editing API (not for bulk reads), raster tiles on tile.openstreetmap.org.
- **Licence:** Open Database License 1.0 (ODbL); you must credit OSM and make clear the data is available under the ODbL. A derivative *database* that is distributed must stay ODbL. Documentation is CC BY-SA 2.0. https://www.openstreetmap.org/copyright (checked 2026-11-14)
- **Credit line:** `© OpenStreetMap contributors` with a link to https://www.openstreetmap.org/copyright. Attribution guidelines: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
- **Editing API:** reserved for editing; bulk reading from api.openstreetmap.org is forbidden. https://operations.osmfoundation.org/policies/api/

### OSM tile usage policy

https://operations.osmfoundation.org/policies/tiles/

- Tiles are a donated service with no SLA; heavy use may be blocked without notice.
- Must show attribution on the map.
- Must send a distinct, stable User-Agent naming the app; web traffic must also send a valid Referer. Library default UAs are not allowed. (checked 2026-11-14)
- Must honour HTTP caching headers (Cache-Control, Expires, ETag) and use conditional requests; if the cache cannot read headers, keep each tile at least 7 days. (checked 2026-11-14)
- **Forbidden:** bulk downloading or scraping (pre-seeding, tile archives, wide-area scans especially at z14+), any offline/"save area" use, prefetching tiles the user is not viewing. Offline needs: self-hosted tiles or a provider that allows offline use. (checked 2026-11-14)
- mapwright consequence: tiles only for small previews; anything bigger is built from extracts.

### Nominatim (geocoding) usage policy

https://operations.osmfoundation.org/policies/nominatim/

- **Absolute maximum 1 request per second** per application (all its users combined); bulk scripts running over a day or at intervals: 4 requests per minute; bulk jobs single thread on one machine. (checked 2026-11-14)
- Valid HTTP User-Agent or Referer identifying the application; the stock UA of an HTTP library is not enough.
- Must display OSM attribution with results.
- Bulk results must be cached; repeated identical queries can get the client blocked. No personal data in queries. (checked 2026-11-14)
- **Forbidden:** autocomplete, systematic queries (reverse grids, enumerating postcodes/towns/POIs), scraping details pages, reselling results. The policy also says LLM-generated code must comply and LLMs suggesting it must link the policy. Use a self-hosted Nominatim or Photon for bulk. (checked 2026-11-14)

### Overpass API

https://wiki.openstreetmap.org/wiki/Overpass_API and server status https://overpass-api.de/api/status

- Main instance overpass-api.de: guideline about 10,000 requests and under about 1 GB download per day; not a guarantee, heavy users are load-shed first. https://dev.overpass-api.de/overpass-doc/en/preface/commons.html (checked 2026-11-14)
- Slot-based rate limiting per IP: the `/api/status` endpoint says how many slots are free and when the next opens; a client should read it and wait instead of retrying blindly.
- Queries carry `[timeout:]` and `[maxsize:]`; defaults 180 s and 512 MiB.
- Data is ODbL, credit as OSM.
- Large areas: use a Geofabrik extract plus osmium instead.

### Geofabrik extracts

https://download.geofabrik.de/ — daily regional `.osm.pbf` files, ODbL, credit OSM. Polite: do not re-download a region more than daily (unverified as a written rule; it is the update cadence).

## Natural Earth

- **Holds:** small-scale (1:10m, 1:50m, 1:110m) cultural, physical and raster data: countries, admin-1, populated places, coastlines, rivers, relief.
- **Access:** bulk zip downloads; GitHub mirror nvkelso/natural-earth-vector.
- **Licence:** public domain. https://www.naturalearthdata.com/about/terms-of-use/ (checked 2026-11-14)
- **Credit line:** not required; suggested `Made with Natural Earth.` or `Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.` (checked 2026-11-14)
- **Note:** shows de facto boundaries with point-of-view variants (worldview files) for disputed areas.

## GADM

- **Holds:** administrative boundaries for every country down to the lowest available level (often level 3-5).
- **Access:** per-country and whole-world downloads (GeoPackage, shapefile, KMZ, R). https://gadm.org/download_country.html
- **Licence (restrictive):** free for academic and other non-commercial use; **redistribution and commercial use are not allowed without prior permission.** Maps in academic articles are allowed. Austria's data is CC BY-SA 2.0. https://gadm.org/license.html (checked 2026-11-14)
- **Credit line:** licence page states no citation form; record `GADM version <x>, gadm.org`.
- mapwright consequence: flag every GADM file `non-commercial, no redistribution`; never bundle GADM in a repository or a released game; prefer geoBoundaries.

## geoBoundaries

- **Holds:** open administrative boundaries ADM0-ADM5 for ~200 countries, plus simplified global composites (CGAZ).
- **Access:** REST API returning download links, e.g. `https://www.geoboundaries.org/api/current/gbOpen/USA/ADM1/`; GitHub repository wmgeolab/geoBoundaries.
- **Licence:** CC BY 4.0, acknowledgement required in any product (websites: name "geoBoundaries" with a link; apps/films: name in credits). https://www.geoboundaries.org/ (checked 2026-11-14) Per-boundary source licences in metadata and stricter gbHumanitarian/gbAuthoritative terms (unverified).
- **Credit line:** `geoBoundaries (www.geoboundaries.org)`; written works cite `Runfola et al. (2020) geoBoundaries: A global database of political administrative boundaries. PLoS ONE 15(4): e0231866`. (checked 2026-11-14)
- mapwright: read the `boundarySource` and `boundaryLicense` fields and copy them to the sidecar.

## GeoNames

- **Holds:** 12+ million place names with coordinates, feature class, population, alternate names, admin codes.
- **Access:** daily bulk dumps (https://download.geonames.org/export/dump/) and web services needing a registered username.
- **Licence:** Creative Commons Attribution (cc-by), commercial use allowed, credit with a link. https://www.geonames.org/export/ (checked 2026-11-14)
- **Credit line:** `GeoNames (geonames.org), CC BY 4.0`.
- **Limits:** free web services: 10,000 credits per day and 1,000 per hour per application username; one credit is generally one request. https://www.geonames.org/export/ (checked 2026-11-14)
- mapwright: use the dump; the web service needs the user's own username (key needed).

## Wikidata

- **Holds:** structured facts including coordinates (P625), admin hierarchy, population, historical dates, OSM relation ids.
- **Access:** SPARQL at query.wikidata.org, REST/Action API, weekly JSON dumps.
- **Licence:** structured data CC0. https://www.wikidata.org/wiki/Wikidata:Licensing
- **Credit line:** not required; courtesy `Data from Wikidata (CC0)`.
- **Usage:** Wikimedia User-Agent policy requires a descriptive UA with contact info: https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy . SPARQL: 60 seconds of query time per 60 seconds per client (UA + IP), 5 parallel queries per IP, 60 s timeout per query, 30 error queries per minute; honour 429 `Retry-After`. https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual#Query_limits (checked 2026-11-14)
- Media in Commons have their own licences (see historical scans).

## Elevation

### Copernicus DEM (GLO-30 / GLO-90)

- **Holds:** global 30 m and 90 m digital surface model from TanDEM-X.
- **Access:** AWS open data bucket `copernicus-dem-30m` / `-90m` (no key), Copernicus Data Space, OpenTopography.
- **Licence:** GLO-30 licence ("Full, Free & Open") grants free, worldwide, perpetual rights to reproduce, distribute, communicate to the public and adapt; no commercial restriction stated; no implied endorsement; the licence's no-liability sentence must accompany redistribution. https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf (checked 2026-11-14) GLO-90 terms and withheld tiles (Armenia, Azerbaijan per Earth Engine catalogue) (unverified).
- **Credit line:** `© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved`; for modified data prefix `produced using Copernicus WorldDEM-30 `. (checked 2026-11-14)

### SRTM

- **Holds:** 1 arc-second (~30 m) and 3 arc-second elevation, 60°N-56°S, year 2000.
- **Access:** NASA Earthdata (LP DAAC, login needed), OpenTopography, AWS mirrors.
- **Licence:** NASA-led mission data is CC0 with no use restrictions; citation very strongly urged; no implied NASA endorsement. https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance (old LP DAAC policy URL redirects here) (checked 2026-11-14)
- **Credit line:** `NASA JPL (2013). NASA Shuttle Radar Topography Mission Global 1 arc second. NASA EOSDIS LP DAAC.` (doi:10.5067/MEaSUREs/SRTM/SRTMGL1.003)

### ASTER GDEM v3

- **Holds:** global 30 m DEM, 83°N-83°S.
- **Access:** NASA Earthdata (login), Japan's J-spacesystems.
- **Licence:** free for all users since v3 (2019) under NASA/METI data policy, no restriction on use; citation required. https://lpdaac.usgs.gov/products/astgtmv003/
- **Credit line:** `NASA/METI/AIST/Japan Spacesystems and U.S./Japan ASTER Science Team (2019). ASTER Global Digital Elevation Model V003. NASA EOSDIS LP DAAC.`

### USGS 3DEP

- **Holds:** US lidar-derived DEMs at 1/3 arc-second, 1 m, plus lidar point clouds.
- **Access:** The National Map download (TNMAccess API, no key), AWS `prd-tnm` and `usgs-lidar-public` buckets, 3DEP elevation ImageServer.
- **Licence:** USGS-produced data is US public domain (non-USGS images may be copyrighted). https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits (checked 2026-11-14)
- **Credit line:** credit requested, e.g. `Credit: U.S. Geological Survey` (3DEP: `U.S. Geological Survey, 3D Elevation Program`). (checked 2026-11-14)

### OpenTopography

- **Holds:** hosted global DEMs (SRTM, Copernicus, ALOS, NASADEM, GEBCO) and high-res lidar.
- **Access:** REST API `globaldem` endpoint; **API key required** (free account). https://opentopography.org/developers
- **Limits:** free academic/non-academic keys have daily call caps: academic 200 calls per 24 h, non-academic 50 per 24 h; area caps per request 450,000 km² for 30 m datasets and 4,050,000 km² for 90 m (SRTM GL3, COP90). OpenTopography Plus raises limits; putting the API inside commercial software needs an Enterprise key. https://opentopography.org/developers (checked 2026-11-14; earlier draft had the area caps wrong)
- **Licence:** that of each underlying dataset; credit both OpenTopography and the data source. https://opentopography.org/citations

## GEBCO bathymetry

- **Holds:** global ocean and land elevation grid at 15 arc-seconds (latest GEBCO_2026 grid), plus type-identifier (TID) grid and an under-ice version. (checked 2026-11-14)
- **Access:** whole-grid NetCDF/GeoTIFF download and a subset download app. https://www.gebco.net/data_and_products/gridded_bathymetry_data/
- **Licence:** public domain with conditions: free to use, commercially too, but must not imply GEBCO/IHO/IOC endorsement, must acknowledge the source, not for navigation or safety at sea. https://www.gebco.net/data-products/gridded-bathymetry/terms-of-use (checked 2026-11-14)
- **Credit line:** `GEBCO Bathymetric Compilation Group 2026, The GEBCO_2026 Grid (doi:10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa)`; DOI changes per release. (checked 2026-11-14)

## Land cover

### ESA WorldCover

- **Holds:** global 10 m land cover, 11 classes, 2020 and 2021.
- **Access:** AWS `esa-worldcover` bucket (no key), Terrascope, Zenodo.
- **Licence:** CC BY 4.0, no restriction of use. https://esa-worldcover.org/en/data-access (checked 2026-11-14)
- **Credit line:** `© ESA WorldCover project [year] / Contains modified Copernicus Sentinel data ([year]) processed by ESA WorldCover consortium` (year 2020 or 2021); publications also cite the Zenodo DOI (2020 v100: 10.5281/zenodo.5571936; 2021 v200: 10.5281/zenodo.7254221). (checked 2026-11-14)

### Copernicus Global Land Service / CORINE

- **Holds:** global 100 m land cover (CGLS-LC100, 2015-2019) and European CORINE Land Cover.
- **Licence:** Copernicus full, open and free data policy (EU Delegated Regulation 1159/2013): free, commercial included, attribution required. https://land.copernicus.eu/en/data-policy
- **Credit line:** `Contains modified Copernicus Land Monitoring Service information [year]` (exact wording per product page).

## Historical boundaries

### Historical Basemaps (aourednik)

- **Holds:** world polygons of states/cultures from 123,000 BC to the present, GeoJSON per year.
- **Access:** GitHub https://github.com/aourednik/historical-basemaps (clone, no API).
- **Licence:** GPL-3.0 per the repository LICENSE; no separate data licence stated. https://github.com/aourednik/historical-basemaps (checked 2026-11-14) Boundaries are approximate and partly speculative.
- **Credit line:** `Historical Basemaps, A. Ourednik, github.com/aourednik/historical-basemaps`.

### CShapes 2.0

- **Holds:** country borders and capitals 1886-2019 with start/end dates (Gleditsch-Ward and COW codes).
- **Access:** download from ETH ICR https://icr.ethz.ch/data/cshapes/ ; R and Python packages.
- **Licence:** CC BY-NC-SA 4.0: non-commercial. https://icr.ethz.ch/data/cshapes/ (checked 2026-11-14)
- **Credit line:** `Schvitz, G., Rüegger, S., Girardin, L., Cederman, L.-E., Weidmann, N., & Gleditsch, K. S. (2022). Mapping The International System, 1886-2017: The CShapes 2.0 Dataset. Journal of Conflict Resolution 66(1): 144-61.` (checked 2026-11-14)

### Others worth listing

- Newberry Library Atlas of Historical County Boundaries (US): https://digital.newberry.org/ahcb/ ; free use with credit (unverified licence terms).
- Euratlas: commercial, not free (unverified).

## Historical map scans

### David Rumsey Map Collection

- **Holds:** 150,000+ digitised historical maps, many georeferenced.
- **Access:** website, LUNA viewer, IIIF manifests; downloads per image.
- **Licence:** images CC BY-NC-SA 3.0; the site defines commercial use as selling reproductions; commercial use or republication: ask carto@davidrumsey.com. Maps still sold by their makers may not be downloaded. https://davidrumsey.com/about (checked 2026-11-14) (the old /about/permissions URL returns 404)
- **Credit line:** `David Rumsey Map Collection, David Rumsey Map Center, Stanford Libraries`. (checked 2026-11-14)

### Library of Congress (Geography and Map Division)

- **Holds:** large map collection, Sanborn fire insurance maps, panoramic maps.
- **Access:** loc.gov JSON API (`?fo=json`), IIIF image service; no key.
- **Licence:** most items have no known restrictions (public domain); check each item's "Rights & Access". https://www.loc.gov/legal/
- **Limits:** loc.gov API documents burst limits (e.g. collections/items endpoints about 20-80 requests per 10 seconds; exceeding them blocks the IP for an hour). https://www.loc.gov/apis/json-and-yaml/working-within-limits/
- **Credit line:** `Library of Congress, Geography and Map Division` plus item URL.

### Old Maps Online

- **Holds:** a search portal over other libraries' scans; no data of its own.
- **Access:** website. https://www.oldmapsonline.org/
- **Licence:** each holding institution's own terms; mapwright follows the link to the holder and records its licence. No scraping of the portal (no published API; unverified).

### NYPL Digital Collections

- **Holds:** maps and atlases, many public domain; NYPL Map Warper georeferences.
- **Access:** NYPL Digital Collections API (token needed), high-res downloads for public-domain items.
- **Licence:** public-domain items free to use, no permission needed; others per item. https://www.nypl.org/research/resources/digital-collections ; API terms https://api.repo.nypl.org/ (API rate 10,000 requests per day per token; checked 2026-11-14 at https://api.repo.nypl.org/).
- **Credit line (requested):** `From The New York Public Library, digitalcollections.nypl.org`.

### Wikimedia Commons

- **Holds:** millions of map scans and modern maps under mixed free licences.
- **Access:** MediaWiki API on commons.wikimedia.org, `upload.wikimedia.org` for files.
- **Licence:** per file (PD, CC0, CC BY, CC BY-SA); read `extmetadata` (LicenseShortName, Artist, Credit). https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- **Usage:** User-Agent policy (above); API etiquette: serial requests, use `maxlag`. https://www.mediawiki.org/wiki/API:Etiquette
- **Credit line:** author, licence, link to file page, per file.

### Map Warper (mapwarper.net)

- **Holds:** user-georeferenced historical maps with WMS/XYZ tile and GeoTIFF export.
- **Licence:** per uploaded map; site content generally CC BY-SA (unverified). https://mapwarper.net/
- Service is volunteer-run: small requests only.

## Planetary

### USGS Astrogeology

- **Holds:** global mosaics, DEMs and geologic maps for Moon, Mars, Mercury, Venus, moons.
- **Access:** Astropedia catalogue https://astrogeology.usgs.gov/search , STAC API, direct downloads.
- **Licence:** USGS-produced data is US public domain; credit requested. https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits (checked 2026-11-14)
- **Credit line:** `USGS Astrogeology Science Center` plus the product's own citation (often NASA/JPL/mission team).

### NASA PDS

- **Holds:** archived mission data (imaging, altimetry, spectra) from all NASA planetary missions.
- **Access:** PDS nodes (Imaging, Geosciences ODE), PDS API; no key.
- **Licence:** NASA data, no copyright in the US; cite the dataset. https://pds.nasa.gov/ and NASA media guidelines https://www.nasa.gov/nasa-brand-center/images-and-media/
- **Credit line:** dataset citation from PDS label, e.g. `NASA/PDS`.

### Moon LOLA

- **Holds:** Lunar Orbiter Laser Altimeter global DEMs (up to 118 m/px globally, finer at poles); SLDEM2015 merges LOLA with Kaguya.
- **Access:** PDS Geosciences Node https://pds-geosciences.wustl.edu/missions/lro/lola.htm , USGS Astropedia.
- **Licence:** public domain (NASA). **Credit line:** `NASA/GSFC/LOLA Science Team` (SLDEM2015: also JAXA/SELENE).

### Mars MOLA

- **Holds:** Mars Orbiter Laser Altimeter global topography (463 m/px; MOLA-HRSC blend 200 m).
- **Access:** PDS Geosciences Node, USGS Astropedia.
- **Licence:** public domain (NASA); HRSC blend includes ESA/DLR/FU Berlin data with credit. **Credit line:** `NASA/JPL/GSFC MOLA Science Team` (+ `ESA/DLR/FU Berlin` for the blend).

## Stars and exoplanets

### Gaia DR3 (ESA archive)

- **Holds:** ~1.8 billion sources with positions, parallaxes, proper motions, photometry.
- **Access:** ADQL/TAP at https://gea.esac.esa.int/archive/ (astroquery.gaia); anonymous async jobs limited in rows and storage, registered users get more (anonymous sync 2,000 rows by default, unverified current caps). Bulk CSV at https://cdn.gea.esac.esa.int/Gaia/gdr3/.
- **Licence:** **CC BY-NC 3.0 IGO (non-commercial)**; commercial use falls under the ESA space science archive terms and conditions (https://www.cosmos.esa.int/web/esdc/terms-and-conditions). https://www.cosmos.esa.int/web/gaia-users/license (checked 2026-11-14)
- **Credit line:** `This work has made use of data from the European Space Agency (ESA) mission Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis Consortium (DPAC).` (wording unverified); per-release acknowledgements are linked from https://www.cosmos.esa.int/web/gaia-users/credits (DR3: https://gea.esac.esa.int/archive/documentation/GDR3/Miscellaneous/sec_acknowl/). (checked 2026-11-14)

### Hipparcos

- **Holds:** 118,218 stars (main catalogue), Tycho-2 2.5 million.
- **Access:** VizieR (I/239, I/311), ESA archive.
- **Licence:** ESA data free with acknowledgement; VizieR terms https://cds.unistra.fr/vizier-org/licences_vizier.html (CDS data freely usable with citation, ODbL for VizieR metadata; unverified).
- **Credit line:** `ESA (1997) The Hipparcos and Tycho Catalogues, ESA SP-1200` or van Leeuwen 2007 for the new reduction.

### HYG database

- **Holds:** ~120,000 stars merging Hipparcos, Yale Bright Star and Gliese, with XYZ coordinates.
- **Access:** moved to Codeberg https://codeberg.org/astronexus/hyg (the GitHub repo says so); CSV. Current release v4.4. (checked 2026-11-14)
- **Licence:** CC BY-SA 4.0 for v4.0 onward; earlier versions CC BY-SA 2.5. Share-alike applies to derived databases. https://codeberg.org/astronexus/hyg (checked 2026-11-14)
- **Credit line:** `HYG Database (astronexus.com/hyg), CC BY-SA 4.0`; CC BY-SA 4.0 confirmed for v4.0+ (earlier versions CC BY-SA 2.5); the repo moved to https://codeberg.org/astronexus/hyg (GitHub copy archived). Requested credit form is in its ACKNOWLEDGMENTS.md (not read; unverified wording). (checked 2026-11-14)

### NASA Exoplanet Archive

- **Holds:** confirmed exoplanets, stellar hosts, Kepler/TESS candidates.
- **Access:** TAP service https://exoplanetarchive.ipac.caltech.edu/TAP , no key.
- **Licence:** none stated; no restrictions beyond acknowledgement requests. Also cite Christiansen et al. (2025) (replaces Akeson et al. 2013) and any dataset-specific credit. https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html (checked 2026-11-14)
- **Credit line:** `This research has made use of the NASA Exoplanet Archive, which is operated by the California Institute of Technology, under contract with the National Aeronautics and Space Administration under the Exoplanet Exploration Program.` plus dataset DOI. (checked 2026-11-14)

## Never scrape

mapwright refuses these as sources of data or tiles, even when a URL works without a key.

| Service | Clause | Source |
|---|---|---|
| Google Maps / Earth | Maps Platform terms forbid pre-fetching, caching, storing or exporting Google Maps Content except as the service-specific terms allow, and scraping content for use outside the services. Google Earth additional terms forbid extracting imagery for derived data. | https://cloud.google.com/maps-platform/terms (section 3.2.3) ; https://www.google.com/help/terms_maps/ |
| Apple Maps (MapKit, Look Around) | Apple Developer Program License Agreement / MapKit terms forbid scraping, bulk download and caching beyond the API's caching; data only inside Apple's map display. | https://developer.apple.com/support/terms/ (Apple Maps service terms within; unverified section number) |
| Bing Maps / Azure Maps | Microsoft Bing Maps platform terms forbid copying, storing, archiving or creating a database of content, and using content outside the service; Bing Maps for Enterprise is being retired in favour of Azure Maps: free and Basic accounts ended 2025-06-30, Enterprise licences end 2028-06-30 (https://blogs.bing.com/maps/2025-01/What-are-my-options-regarding-Bing-Maps-for-Enterprise-Retirement, checked 2026-11-14). | https://www.microsoft.com/en-us/maps/bing-maps/product (TOU link) ; https://www.microsoft.com/licensing/terms (Azure Maps) |
| Mapbox | Product terms: no scraping, no bulk caching beyond allowed offline limits, no use of tiles without an access token; Mapbox data is OSM-based but Mapbox-styled tiles are its property. | https://www.mapbox.com/legal/tos |
| MapTiler | Terms require an API key; no tile harvesting outside the SDKs; offline only with paid plan or self-hosted data (unverified details). | https://www.maptiler.com/terms/ |
| HERE, TomTom, Esri basemaps | API terms require a key and forbid storing or redistributing map content beyond allowed caching. | https://legal.here.com/ ; https://developer.tomtom.com/legal ; https://www.esri.com/legal/terms (unverified sections) |
| Stadia / Stamen / Thunderforest tiles | Need a key; free tiers forbid bulk download. | https://stadiamaps.com/terms-of-service/ ; https://www.thunderforest.com/terms/ |
| OSM tile.openstreetmap.org for bulk | Tile usage policy forbids bulk download (see above). | https://operations.osmfoundation.org/policies/tiles/ |

Data with an open licence behind a keyed commercial service (for example OSM data in Mapbox vector tiles) is still fetched from the open source, never from the commercial tiles.

## Machine table

Rates are the published ceiling; mapwright runs at or below them. `bulk` = download files instead of calling an API.

| id | licence | credit | rate | key needed |
|---|---|---|---|---|
| osm-extract | ODbL-1.0 | © OpenStreetMap contributors | bulk, daily max | no |
| osm-tiles | ODbL-1.0 data; tile terms per OSMF tile policy | © OpenStreetMap contributors | light preview only, no bulk | no (UA required) |
| nominatim | ODbL-1.0 | © OpenStreetMap contributors | 1 req/s (4/min for long bulk), no autocomplete or systematic queries | no (UA required) |
| overpass | ODbL-1.0 | © OpenStreetMap contributors | ~10k requests and ~1 GB/day; obey /api/status slots | no |
| natural-earth | public domain | Made with Natural Earth | bulk | no |
| gadm | non-commercial, no redistribution | GADM <version>, gadm.org | bulk | no |
| geoboundaries | CC BY 4.0 | geoBoundaries + link; Runfola et al. 2020 | API + bulk, polite | no |
| geonames-dump | CC BY 4.0 | GeoNames, CC BY 4.0 | bulk, daily | no |
| geonames-api | CC BY 4.0 | GeoNames, CC BY 4.0 | 1,000/h, 10,000/day credits | yes (username) |
| wikidata | CC0 | Data from Wikidata (optional) | SPARQL 60 s/60 s, 5 parallel | no (UA required) |
| copernicus-dem | Copernicus WorldDEM-30 licence, free, notice + no-liability sentence | © DLR e.V. / Airbus, Copernicus | bulk (S3) | no |
| srtm | CC0 (NASA) | NASA JPL SRTM | bulk | Earthdata login (mirrors no) |
| aster-gdem | free, citation | NASA/METI/AIST ASTER Team | bulk | Earthdata login |
| usgs-3dep | public domain | USGS 3DEP | bulk/API | no |
| opentopography | per dataset | OpenTopography + source | daily cap per key | yes |
| gebco | public domain, acknowledge, no endorsement, not for navigation | GEBCO Bathymetric Compilation Group (year) | bulk | no |
| esa-worldcover | CC BY 4.0 | © ESA WorldCover project | bulk (S3) | no |
| copernicus-land | Copernicus open policy, attribution | Copernicus Land Monitoring Service | bulk | account for some products |
| historical-basemaps | GPL-3.0 | A. Ourednik, Historical Basemaps | git clone | no |
| cshapes | CC BY-NC-SA 4.0 | Schvitz et al. 2022 | bulk | no |
| rumsey | CC BY-NC-SA 3.0 | David Rumsey Map Collection | per image, polite | no |
| loc | mostly public domain, per item | Library of Congress, G&M Division | documented burst limits | no |
| nypl | PD items free, per item | NYPL Digital Collections | 10k/day per token | yes (token, API only) |
| commons | per file | author + licence per file | serial, maxlag | no (UA required) |
| mapwarper | per map (unverified) | Map Warper + original holder | light | no |
| usgs-astro | public domain | USGS Astrogeology + mission | bulk | no |
| nasa-pds | public domain | NASA/PDS dataset citation | bulk | no |
| lola | public domain | NASA/GSFC/LOLA Science Team | bulk | no |
| mola | public domain | NASA/JPL/GSFC MOLA Team | bulk | no |
| gaia-dr3 | CC BY-NC 3.0 IGO (non-commercial) | ESA Gaia DPAC statement | TAP job caps; bulk CDN | no (login raises caps) |
| hipparcos | ESA free with citation | ESA 1997 SP-1200 | VizieR polite | no |
| hyg | CC BY-SA 4.0 | HYG Database, D. Nash | git/bulk | no |
| exoplanet-archive | no licence stated, acknowledgement + Christiansen 2025 | NASA Exoplanet Archive statement | TAP polite | no |

## Open questions

- Whether other Overpass instances (kumi.systems, private.coffee) publish their own limits.
- Gaia: what the ESA terms allow for commercial use (licence is CC BY-NC 3.0 IGO), exact DR3 acknowledgement text and current anonymous TAP caps.
- Copernicus DEM GLO-90 licence and the current GLO-30 withheld tiles (spacedata.copernicus.eu refused connections 2026-11-14).
- OpenTopography current per-key quotas and commercial terms.
- Whether Old Maps Online offers an API now.

## Sources (listed 2026-11-14; those tagged in the text were fetched that day)

- https://www.openstreetmap.org/copyright
- https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
- https://operations.osmfoundation.org/policies/tiles/
- https://operations.osmfoundation.org/policies/nominatim/
- https://operations.osmfoundation.org/policies/api/
- https://wiki.openstreetmap.org/wiki/Overpass_API
- https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
- https://download.geofabrik.de/
- https://www.naturalearthdata.com/about/terms-of-use/
- https://gadm.org/license.html
- https://www.geoboundaries.org/
- https://www.geonames.org/about.html
- https://www.geonames.org/export/
- https://www.wikidata.org/wiki/Wikidata:Licensing
- https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual#Query_limits
- https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy
- https://www.mediawiki.org/wiki/API:Etiquette
- https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model
- https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf
- https://lpdaac.usgs.gov/products/astgtmv003/
- https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- https://opentopography.org/developers
- https://opentopography.org/citations
- https://www.gebco.net/data_and_products/gridded_bathymetry_data/
- https://esa-worldcover.org/en/data-access
- https://land.copernicus.eu/en/data-policy
- https://github.com/aourednik/historical-basemaps
- https://icr.ethz.ch/data/cshapes/
- https://davidrumsey.com/about
- https://www.loc.gov/legal/
- https://www.loc.gov/apis/json-and-yaml/working-within-limits/
- https://www.oldmapsonline.org/
- https://www.nypl.org/research/resources/digital-collections
- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- https://mapwarper.net/
- https://astrogeology.usgs.gov/search
- https://pds.nasa.gov/
- https://pds-geosciences.wustl.edu/missions/lro/lola.htm
- https://gea.esac.esa.int/archive/documentation/credits.html
- https://www.cosmos.esa.int/web/gaia-users/license
- https://cds.unistra.fr/vizier-org/licences_vizier.html
- https://codeberg.org/astronexus/hyg
- https://www.gebco.net/data-products/gridded-bathymetry/terms-of-use
- https://www.cosmos.esa.int/web/gaia-users/credits
- https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html
- https://cloud.google.com/maps-platform/terms
- https://www.google.com/help/terms_maps/
- https://developer.apple.com/support/terms/
- https://www.mapbox.com/legal/tos
- https://www.maptiler.com/terms/
- https://stadiamaps.com/terms-of-service/
- https://www.thunderforest.com/terms/
