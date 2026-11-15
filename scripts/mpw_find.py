"""find and fetch for mapwright: a source catalogue, polite cached HTTP, credit files.

Standard library only. Network calls go through Http, whose opener and clock can be
replaced (the tests do, so they never touch the network).
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HOME = "https://github.com/m4bwav/mapwright"
DEFAULT_CAP_MB = 200
OT_KEY_ENV = "OPENTOPOGRAPHY_API_KEY"

# id, name, tags (words a query matches), licence, credit, min seconds between requests,
# hosts, how to get it, key env var or None, note.
_C = [
    ("osm-extract", "OpenStreetMap regional extract (Geofabrik)", "place road street building city town park osm vector",
     "ODbL-1.0", "© OpenStreetMap contributors", 86400, ["download.geofabrik.de"],
     "https://download.geofabrik.de/", None, "bulk .osm.pbf per region; at most once a day per file"),
    ("overpass", "OpenStreetMap via Overpass API", "place road street building park river poi osm vector small area",
     "ODbL-1.0", "© OpenStreetMap contributors", 10, ["overpass-api.de"],
     "https://overpass-api.de/api/interpreter", None, "small areas only; obey /api/status slots"),
    ("nominatim", "Nominatim geocoder (OSM)", "place geocode name city town",
     "ODbL-1.0", "© OpenStreetMap contributors", 1.0, ["nominatim.openstreetmap.org"],
     "https://nominatim.openstreetmap.org/search", None, "1 req/s max, no autocomplete, no systematic queries, no private addresses"),
    ("natural-earth", "Natural Earth", "world country coast border river lake small scale atlas place",
     "public domain", "Made with Natural Earth", 5, ["naciscdn.org", "www.naturalearthdata.com"],
     "https://www.naturalearthdata.com/downloads/", None, "bulk zips at 1:10m, 1:50m, 1:110m"),
    ("gadm", "GADM administrative areas", "border admin province county district",
     "non-commercial, no redistribution", "GADM 4.1, gadm.org", 5, ["geodata.ucdavis.edu", "gadm.org"],
     "https://gadm.org/download_country.html", None, "non-commercial; prefer geoBoundaries"),
    ("geoboundaries", "geoBoundaries", "border admin province county district place",
     "CC BY 4.0", "geoBoundaries (Runfola et al. 2020), https://www.geoboundaries.org", 2,
     ["www.geoboundaries.org", "github.com"], "https://www.geoboundaries.org/api.html", None, ""),
    ("geonames-dump", "GeoNames dump", "place name gazetteer city town",
     "CC BY 4.0", "GeoNames, CC BY 4.0", 86400, ["download.geonames.org"],
     "https://download.geonames.org/export/dump/", None, "daily dumps"),
    ("wikidata", "Wikidata", "place subject history entity",
     "CC0", "Data from Wikidata", 1.0, ["query.wikidata.org", "www.wikidata.org"],
     "https://query.wikidata.org/sparql", None, "SPARQL 60 s per 60 s"),
    ("copernicus-dem", "Copernicus DEM GLO-30/90", "elevation terrain height dem mountain relief place",
     "Copernicus WorldDEM licence (free, notice + no-liability)", "© DLR e.V. 2010-2014 and © Airbus 2014-2018, provided under COPERNICUS by the European Union and ESA",
     2, ["copernicus-dem-30m.s3.amazonaws.com", "copernicus-dem-90m.s3.amazonaws.com"],
     "https://registry.opendata.aws/copernicus-dem/", None, "one 1x1 deg tile at a time"),
    ("srtm", "SRTM", "elevation terrain height dem",
     "CC0 (NASA)", "NASA JPL SRTM", 2, ["e4ftl01.cr.usgs.gov"], "https://lpdaac.usgs.gov/", None, "Earthdata login"),
    ("usgs-3dep", "USGS 3DEP", "elevation terrain lidar dem usa united states",
     "public domain", "USGS 3D Elevation Program", 2, ["prd-tnm.s3.amazonaws.com", "tnmaccess.nationalmap.gov"],
     "https://apps.nationalmap.gov/downloader/", None, "US only"),
    ("opentopography", "OpenTopography global DEM API", "elevation terrain dem lidar",
     "per dataset", "OpenTopography (opentopography.org) and the dataset's source", 2,
     ["portal.opentopography.org"], "https://portal.opentopography.org/API/globaldem", OT_KEY_ENV,
     "your own free key in " + OT_KEY_ENV + "; daily cap per key"),
    ("gebco", "GEBCO bathymetry", "sea depth ocean bathymetry seafloor",
     "public domain (acknowledge, no endorsement, not for navigation)", "GEBCO Compilation Group (2025) GEBCO 2025 Grid",
     5, ["www.gebco.net", "download.gebco.net"], "https://download.gebco.net/", None, "use the subset tool, not the global grid"),
    ("esa-worldcover", "ESA WorldCover", "land cover forest farmland vegetation",
     "CC BY 4.0", "© ESA WorldCover project / Contains modified Copernicus Sentinel data processed by ESA WorldCover consortium",
     2, ["esa-worldcover.s3.eu-central-1.amazonaws.com"], "https://esa-worldcover.org/", None, "3x3 deg tiles"),
    ("historical-basemaps", "Historical Basemaps (aourednik)", "history historical empire border ancient medieval time",
     "GPL-3.0", "A. Ourednik, Historical Basemaps", 2, ["raw.githubusercontent.com", "github.com"],
     "https://github.com/aourednik/historical-basemaps", None, "world borders by year"),
    ("cshapes", "CShapes 2.0", "history historical border country 1886 time",
     "CC BY-NC-SA 4.0", "Schvitz et al. 2022, CShapes 2.0", 5, ["icr.ethz.ch"], "https://icr.ethz.ch/data/cshapes/", None,
     "non-commercial"),
    ("rumsey", "David Rumsey Map Collection", "history historical scan old map atlas time",
     "CC BY-NC-SA 3.0", "David Rumsey Map Collection, David Rumsey Map Center, Stanford Libraries", 5,
     ["www.davidrumsey.com", "media.davidrumsey.com"], "https://www.davidrumsey.com/", None, "per image, polite"),
    ("loc", "Library of Congress, Geography and Map Division", "history historical scan old map atlas time usa",
     "mostly public domain, check each item", "Library of Congress, Geography and Map Division", 3,
     ["www.loc.gov", "tile.loc.gov"], "https://www.loc.gov/maps/", None, "burst limits; one request every 3 s"),
    ("commons", "Wikimedia Commons", "history historical scan old map image time subject",
     "per file", "author and licence per file (see the file page)", 1.0,
     ["commons.wikimedia.org", "upload.wikimedia.org"], "https://commons.wikimedia.org/w/api.php", None, "serial requests, maxlag"),
    ("usgs-astro", "USGS Astrogeology", "planet moon mars mercury venus planetary space",
     "public domain", "USGS Astrogeology Science Center and the mission team", 2,
     ["astrogeology.usgs.gov", "planetarymaps.usgs.gov"], "https://astrogeology.usgs.gov/search", None, ""),
    ("lola", "Moon LOLA", "moon lunar elevation planetary space",
     "public domain", "NASA/GSFC/LOLA Science Team", 2, ["pds-geosciences.wustl.edu"],
     "https://pds-geosciences.wustl.edu/missions/lro/lola.htm", None, ""),
    ("mola", "Mars MOLA", "mars elevation planetary space",
     "public domain", "NASA/JPL/GSFC MOLA Science Team", 2, ["pds-geosciences.wustl.edu"],
     "https://pds-geosciences.wustl.edu/missions/mgs/mola.html", None, ""),
    ("hyg", "HYG star database", "star stars galaxy sci-fi space catalogue",
     "CC BY-SA 4.0", "HYG Database, David Nash (astronexus)", 2, ["raw.githubusercontent.com", "github.com",
                                                                   "codeberg.org"],
     "https://codeberg.org/astronexus/hyg", None, ""),
    ("gaia-dr3", "Gaia DR3", "star stars galaxy space catalogue",
     "CC BY-NC 3.0 IGO", "This work has made use of data from the ESA mission Gaia, processed by the Gaia DPAC", 2,
     ["gea.esac.esa.int"], "https://gea.esac.esa.int/archive/", None, "non-commercial; small TAP queries"),
    ("exoplanet-archive", "NASA Exoplanet Archive", "exoplanet planet star space sci-fi",
     "no licence stated; acknowledgement asked", "This research has made use of the NASA Exoplanet Archive, operated by Caltech under contract with NASA",
     2, ["exoplanetarchive.ipac.caltech.edu"], "https://exoplanetarchive.ipac.caltech.edu/TAP", None, ""),
]

CATALOGUE = [dict(id=c[0], name=c[1], tags=c[2].split(), licence=c[3], credit=c[4], min_interval=float(c[5]),
                  hosts=c[6], url=c[7], key_env=c[8], note=c[9]) for c in _C]
BY_ID = {s["id"]: s for s in CATALOGUE}

# host suffix -> service and reason (references/sources-and-terms.md, "Never scrape")
FORBIDDEN = [
    ("google.com", "Google Maps / Earth", "Maps Platform terms forbid caching, storing or scraping map content"),
    ("googleapis.com", "Google Maps / Earth", "Maps Platform terms forbid caching, storing or scraping map content"),
    ("gstatic.com", "Google Maps / Earth", "Maps Platform terms forbid caching, storing or scraping map content"),
    ("apple.com", "Apple Maps", "MapKit terms forbid scraping and bulk download"),
    ("bing.com", "Bing Maps", "Bing Maps terms forbid storing or building a database of content"),
    ("virtualearth.net", "Bing Maps", "Bing Maps terms forbid storing or building a database of content"),
    ("atlas.microsoft.com", "Azure Maps", "Azure Maps terms forbid storing content outside the service"),
    ("mapbox.com", "Mapbox", "product terms forbid scraping and bulk caching"),
    ("maptiler.com", "MapTiler", "terms forbid tile harvesting outside the SDKs"),
    ("here.com", "HERE", "API terms forbid storing map content"),
    ("hereapi.com", "HERE", "API terms forbid storing map content"),
    ("tomtom.com", "TomTom", "API terms forbid storing map content"),
    ("arcgisonline.com", "Esri basemaps", "terms forbid storing basemap content"),
    ("arcgis.com", "Esri basemaps", "terms forbid storing basemap content"),
    ("stadiamaps.com", "Stadia / Stamen", "free tiers forbid bulk download"),
    ("stamen.com", "Stadia / Stamen", "free tiers forbid bulk download"),
    ("thunderforest.com", "Thunderforest", "free tiers forbid bulk download"),
    ("tile.openstreetmap.org", "OSM tile servers", "the tile usage policy forbids downloading tiles; use an extract"),
    ("api.openstreetmap.org", "OSM editing API", "reserved for editing; bulk reads are forbidden; use Overpass or an extract"),
]
# whole-planet or global sets: refused whatever the size header says
BULK_PATTERNS = [
    (r"planet\.openstreetmap\.org|planet-latest|planet-\d", "a whole-planet OSM file"),
    (r"gebco_\d{4}(_sub_ice_topo|_tid)?(_geotiff|_netcdf)?\.zip", "the global GEBCO grid"),
    (r"GLO-?30.*(global|world)|(global|world).*GLO-?30", "a global DEM set"),
]

STOP = set("a an the of in on at for to and or map maps data from with near around show me find".split())


class Refused(Exception):
    pass


def user_agent(version):
    return "mapwright/%s (+%s)" % (version, HOME)


def _host(url):
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def forbidden(url):
    h = _host(url)
    for suffix, service, why in FORBIDDEN:
        if h == suffix or h.endswith("." + suffix):
            return service, why
    return None


def check_url(url):
    """Raise Refused for a forbidden source or a bulk set; return None when fine."""
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise Refused("only http and https URLs are fetched: " + url)
    f = forbidden(url)
    if f:
        raise Refused("refused: %s is on the never-scrape list (%s). Use an open source instead; "
                      "see references/sources-and-terms.md." % (f[0], f[1]))
    for pat, what in BULK_PATTERNS:
        if re.search(pat, url, re.I):
            raise Refused("refused: %s is a bulk download. Fetch a regional extract or a tile instead; "
                          "a whole-planet or global set needs the owner's go-ahead." % what)


def source_for(url):
    h = _host(url)
    for s in CATALOGUE:
        for host in s["hosts"]:
            if h == host or h.endswith("." + host):
                return s
    return None


def _strip_key(url):
    """Drop API keys from a URL before it is cached or written down."""
    parts = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
         if k.lower() not in ("api_key", "apikey", "key", "token", "access_token")]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


# ---------------------------------------------------------------- polite HTTP
class RateLimiter:
    """At most one request per min_interval seconds per source, across runs (state on disk)."""

    def __init__(self, state_path=None, clock=time.monotonic, wall=time.time, sleep=time.sleep):
        self.state_path, self.clock, self.wall, self.sleep = state_path, clock, wall, sleep
        self.last = {}
        if state_path and os.path.isfile(state_path):
            try:
                with open(state_path, encoding="utf-8") as f:
                    self.last = {k: float(v) for k, v in json.load(f).items()}
            except (ValueError, OSError):
                self.last = {}

    def wait(self, source_id, interval):
        now = self.wall()
        prev = self.last.get(source_id)
        if prev is not None and now - prev < interval:
            self.sleep(interval - (now - prev))
            now = self.wall()
        self.last[source_id] = now
        if self.state_path:
            try:
                with open(self.state_path, "w", encoding="utf-8") as f:
                    json.dump(self.last, f)
            except OSError:
                pass


def default_cache():
    return os.environ.get("MAPWRIGHT_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "mapwright")


class Http:
    def __init__(self, version, cache_dir=None, opener=None, limiter=None, cap_mb=DEFAULT_CAP_MB):
        self.ua = user_agent(version)
        self.cache_dir = cache_dir or default_cache()
        os.makedirs(self.cache_dir, exist_ok=True)
        self.opener = opener or urllib.request.urlopen
        self.limiter = limiter or RateLimiter(os.path.join(self.cache_dir, "rate.json"))
        self.cap = int(cap_mb * 1024 * 1024)
        self.requests = 0

    def cache_path(self, url):
        return os.path.join(self.cache_dir, hashlib.sha256(_strip_key(url).encode()).hexdigest())

    def get(self, url, source, add_key=None):
        """Bytes of url, from the cache when present. source is a catalogue entry."""
        check_url(url)
        cp = self.cache_path(url)
        if os.path.isfile(cp):
            with open(cp, "rb") as f:
                return f.read(), True
        real = url
        if add_key:
            sep = "&" if urllib.parse.urlsplit(url).query else "?"
            real = url + sep + urllib.parse.urlencode({"API_Key": add_key})
        self.limiter.wait(source["id"], source["min_interval"])
        req = urllib.request.Request(real, headers={"User-Agent": self.ua})
        self.requests += 1
        try:
            resp = self.opener(req, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After") if e.headers else None
                raise Refused("%s answered %d; wait %s s before trying again" % (source["id"], e.code, ra or "a while"))
            raise Refused("%s answered HTTP %d for %s" % (source["id"], e.code, _strip_key(url)))
        except urllib.error.URLError as e:
            raise Refused("could not reach %s: %s" % (_host(url), e.reason))
        with resp:
            size = resp.headers.get("Content-Length") if resp.headers else None
            if size and int(size) > self.cap:
                raise Refused("refused: %s is %.0f MB, over the %d MB cap (bulk downloads need the owner's "
                              "go-ahead; raise --max-mb only for a file you meant to get)"
                              % (_strip_key(url), int(size) / 1048576.0, self.cap // 1048576))
            chunks, total = [], 0
            while True:
                b = resp.read(1 << 16)
                if not b:
                    break
                total += len(b)
                if total > self.cap:
                    raise Refused("refused: download passed the %d MB cap and was stopped" % (self.cap // 1048576))
                chunks.append(b)
        data = b"".join(chunks)
        tmp = cp + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, cp)
        return data, False


# ---------------------------------------------------------------- find
def _words(q):
    return [w for w in re.findall(r"[a-z0-9\-]+", q.lower()) if w not in STOP]


def classify(query):
    """Which kinds the query asks for: place, time, subject (a list, maybe several)."""
    w = set(_words(query))
    years = [int(y) for y in re.findall(r"\b(1[0-9]{3}|20[0-2][0-9]|[1-9][0-9]{1,2})\s*(?:ad|ce|bc|bce)?\b", query.lower())]
    kinds = []
    if years or w & {"history", "historical", "old", "ancient", "medieval", "century", "empire", "war"}:
        kinds.append("time")
    if w & {"elevation", "terrain", "dem", "height", "depth", "bathymetry", "star", "stars", "moon", "mars",
            "planet", "exoplanet", "land", "cover", "border", "borders", "roads", "rivers", "galaxy"}:
        kinds.append("subject")
    if not kinds or (w - set(t for s in CATALOGUE for t in s["tags"])):
        kinds.append("place")
    return kinds, years


def catalogue_hits(query, limit=8):
    w = _words(query)
    kinds, years = classify(query)
    scored = []
    for s in CATALOGUE:
        score = sum(2 for x in w if x in s["tags"] or x.rstrip("s") in s["tags"])
        if "time" in kinds and "time" in s["tags"]:
            score += 2
        if "place" in kinds and "place" in s["tags"]:
            score += 1
        if score:
            scored.append((-score, s["id"], s))
    scored.sort()
    return [result_from_source(s) for _, _, s in scored[:limit]]


def result_from_source(s, title=None, url=None, origin="catalogue", extra=None):
    r = dict(source=s["id"], title=title or s["name"], url=url or s["url"], licence=s["licence"],
             credit=s["credit"], origin=origin, rate="1 request per %g s" % s["min_interval"], note=s["note"])
    if s["key_env"]:
        r["key"] = "set" if os.environ.get(s["key_env"]) else "missing: set " + s["key_env"]
    if extra:
        r.update(extra)
    return r


def _json(http, url, source):
    data, _ = http.get(url, source)
    return json.loads(data.decode("utf-8"))


def online_lookups(query, http, kinds):
    out, errors = [], []
    q = urllib.parse.quote(query)
    place = None
    if "place" in kinds:
        try:
            hits = _json(http, "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=3&q=" + q, BY_ID["nominatim"])
            for h in hits:
                bb = [float(x) for x in h.get("boundingbox", [])] if h.get("boundingbox") else None
                out.append(result_from_source(BY_ID["nominatim"], title=h.get("display_name"),
                                              url="https://www.openstreetmap.org/%s/%s" % (h.get("osm_type"), h.get("osm_id")),
                                              origin="online", extra=dict(lat=float(h["lat"]), lon=float(h["lon"]), bbox=bb)))
            if hits:
                place = out[0]
        except (Refused, ValueError, KeyError) as e:
            errors.append("nominatim: %s" % e)
    try:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6"
               "&gsrlimit=5&prop=imageinfo&iiprop=url|extmetadata&maxlag=5&gsrsearch=" + urllib.parse.quote(query + " map"))
        js = _json(http, url, BY_ID["commons"])
        for p in (js.get("query") or {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata") or {}
            lic = (md.get("LicenseShortName") or {}).get("value") or "unknown: check the file page"
            artist = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value") or "unknown author").strip()
            out.append(result_from_source(BY_ID["commons"], title=p.get("title"), url=ii.get("url") or ii.get("descriptionurl"),
                                          origin="online", extra=dict(licence=lic, credit="%s, %s, via Wikimedia Commons" % (artist, lic))))
    except (Refused, ValueError) as e:
        errors.append("commons: %s" % e)
    if "time" in kinds:
        try:
            js = _json(http, "https://www.loc.gov/maps/?fo=json&c=5&q=" + q, BY_ID["loc"])
            for it in js.get("results", [])[:5]:
                rights = it.get("rights") or ""
                if isinstance(rights, list):
                    rights = " ".join(rights)
                lic = "public domain (no known restrictions)" if "no known restrictions" in rights.lower() else \
                    "check the item's rights statement"
                out.append(result_from_source(BY_ID["loc"], title=it.get("title"), url=it.get("url") or it.get("id"),
                                              origin="online", extra=dict(licence=lic, date=it.get("date"))))
        except (Refused, ValueError) as e:
            errors.append("loc: %s" % e)
    if place and place.get("bbox") and ("subject" in kinds or "place" in kinds):
        s, n, w, e = place["bbox"]
        ot = BY_ID["opentopography"]
        url = ("https://portal.opentopography.org/API/globaldem?demtype=COP30&south=%s&north=%s&west=%s&east=%s"
               "&outputFormat=GTiff" % (s, n, w, e))
        out.append(result_from_source(ot, title="Copernicus GLO-30 for " + (place["title"] or query), url=url,
                                      origin="built", extra=dict(credit="OpenTopography (opentopography.org); " + BY_ID["copernicus-dem"]["credit"],
                                                                 licence=BY_ID["copernicus-dem"]["licence"])))
    return out, errors


def find(query, http=None, online=False, limit=8):
    kinds, years = classify(query)
    results = catalogue_hits(query, limit)
    errors = []
    if online:
        more, errors = online_lookups(query, http, kinds)
        results = more + results
    for r in results:
        if not r.get("licence") or not r.get("credit"):
            raise AssertionError("result without licence or credit: %r" % r)
    return dict(query=query, kinds=kinds, years=years, results=results, errors=errors)


# ---------------------------------------------------------------- fetch
def _safe_name(url):
    name = os.path.basename(urllib.parse.urlsplit(url).path) or "download"
    name = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.unquote(name))[:120]
    return name or "download"


def write_credits(out_dir):
    path = os.path.join(out_dir, "sources.json")
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    lines = ["Credits for the files in this folder (written by mapwright fetch).", ""]
    for e in entries:
        lines.append("%s: %s (licence: %s; fetched %s from %s)" % (e["file"], e["credit"], e["licence"], e["fetched"], e["url"]))
    seen = []
    for e in entries:
        if e["credit"] not in seen:
            seen.append(e["credit"])
    lines += ["", "Credit lines to show with any map made from them:"] + ["  " + c for c in seen] + [""]
    with open(os.path.join(out_dir, "CREDITS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def record(out_dir, entry):
    path = os.path.join(out_dir, "sources.json")
    entries = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
    entries = [e for e in entries if e["file"] != entry["file"]] + [entry]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(entries, f, indent=1, ensure_ascii=False)
        f.write("\n")
    write_credits(out_dir)


def fetch(url, out_dir, http, source_id=None, name=None, licence=None, credit=None, today=None):
    check_url(url)
    if source_id:
        if source_id not in BY_ID:
            raise Refused("unknown source %r; `mpw.py find --list` shows the catalogue" % source_id)
        src = BY_ID[source_id]
    else:
        src = source_for(url)
    if src is None:
        if not (licence and credit):
            raise Refused("refused: %s is not in the catalogue. Name its --licence and --credit (from the source's "
                          "own terms page) to fetch it anyway." % _host(url))
        src = dict(id="other:" + _host(url), licence=licence, credit=credit, min_interval=2.0, key_env=None)
    key = None
    if src.get("key_env"):
        key = os.environ.get(src["key_env"])
        if not key:
            raise Refused("%s needs your own free key in %s" % (src["id"], src["key_env"]))
    data, hit = http.get(url, src, add_key=key)
    os.makedirs(out_dir, exist_ok=True)
    fname = name or _safe_name(url)
    with open(os.path.join(out_dir, fname), "wb") as f:
        f.write(data)
    entry = dict(file=fname, url=_strip_key(url), source=src["id"], licence=licence or src["licence"],
                 credit=credit or src["credit"], fetched=today or time.strftime("%Y-%m-%d"),
                 rate="at most 1 request per %g s" % src["min_interval"], bytes=len(data),
                 sha256=hashlib.sha256(data).hexdigest(), cache="hit" if hit else "miss")
    record(out_dir, entry)
    return entry
