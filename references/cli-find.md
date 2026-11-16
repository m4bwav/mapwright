# mapwright CLI: find and fetch real-place data

`MPW` means `python scripts/mpw.py` from the plugin root. Loaded on demand from skills/mapwright/SKILL.md.

## Find: data for a real place

`MPW find QUERY` takes a place, a time or a subject ("Kyoto", "Paris 1850", "sea depth Hawaii", "stars near Sol") and lists candidate sources from a built-in catalogue, each with its licence and credit line. `--online` adds live lookups: Nominatim for the place and its bounding box, Wikimedia Commons files with each file's own licence and author, Library of Congress maps for a time, and a ready OpenTopography Copernicus GLO-30 request for the place's box. `MPW find --list` prints the catalogue. The terms behind it are in [references/sources-and-terms.md](sources-and-terms.md).

`MPW fetch URL -o FOLDER` downloads one file and writes `sources.json` (URL, licence, credit, date, rate, sha256) and `CREDITS.txt` beside it; fetch into the recipe folder. It sends `User-Agent: mapwright/<version>` and nothing personal, waits out each source's rate (Nominatim 1 request per second, even across runs), caches every response (MAPWRIGHT_CACHE, default ~/.cache/mapwright) so a repeat costs no request, and refuses:
- the never-scrape list (Google, Apple, Bing and Azure, Mapbox, MapTiler, HERE, TomTom, Esri, Stadia, Thunderforest, OSM tile servers, the OSM editing API), with the reason;
- whole-planet and global sets, and anything over `--max-mb` (200 by default). Raise the cap only for a file you meant to get; a planet file or global DEM waits for the owner;
- a host not in the catalogue unless you pass `--licence` and `--credit` from its terms page.

OpenTopography needs the user's own free key in `OPENTOPOGRAPHY_API_KEY`; it is added to the request and never written to the cache name, sources.json or CREDITS.txt. Never ask the user for a key; tell them where to get one.

Privacy guard: never send a home address, or any private address or location of a person or family, to a geocoder or any online lookup (`find --online` sends the query to Nominatim, Commons and the LoC). Use a town, a landmark or coordinates the user typed, or work from data already on disk.
