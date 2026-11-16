"""Tests for `find` and `fetch` (scripts/mpw_find.py). Offline: the network is mocked.
One live smoke test asks Nominatim once when MAPWRIGHT_LIVE=1. Run: python -m unittest discover -s tests"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw  # noqa: E402
import mpw_find as F  # noqa: E402


class FakeResp(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}


class FakeNet:
    """Records requests; answers from a dict of URL prefix -> bytes."""

    def __init__(self, routes=None, headers=None):
        self.routes, self.headers, self.calls = routes or {}, headers or {}, []

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.calls.append((url, req.get_header("User-agent")))
        for prefix, data in self.routes.items():
            if url.startswith(prefix):
                return FakeResp(data, self.headers)
        return FakeResp(b"payload:" + url.encode(), self.headers)


class FakeClock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def wall(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def make_http(tmp, net, clock=None, cap_mb=200):
    clock = clock or FakeClock()
    lim = F.RateLimiter(os.path.join(tmp, "rate.json"), wall=clock.wall, sleep=clock.sleep)
    return F.Http(mpw.VERSION, cache_dir=os.path.join(tmp, "cache"), opener=net, limiter=lim, cap_mb=cap_mb), clock


NOMINATIM = json.dumps([{"display_name": "Paris, France", "lat": "48.85", "lon": "2.35", "osm_type": "relation",
                         "osm_id": 7444, "boundingbox": ["48.81", "48.90", "2.22", "2.47"]}]).encode()
COMMONS = json.dumps({"query": {"pages": {"1": {"title": "File:Paris 1850.jpg", "imageinfo": [{
    "url": "https://upload.wikimedia.org/x/Paris_1850.jpg",
    "extmetadata": {"LicenseShortName": {"value": "Public domain"}, "Artist": {"value": "<a>A. Mapper</a>"}}}]},
    "2": {"title": "File:No meta.png", "imageinfo": [{"url": "https://upload.wikimedia.org/y.png"}]}}}}).encode()
LOC = json.dumps({"results": [{"title": "Plan de Paris", "url": "https://www.loc.gov/item/x/", "date": "1850",
                               "rights": ["No known restrictions on publication."]},
                              {"title": "Other", "id": "https://www.loc.gov/item/y/"}]}).encode()


class FindTests(unittest.TestCase):
    def test_catalogue_complete(self):
        for s in F.CATALOGUE:
            for k in ("licence", "credit", "url", "hosts"):
                self.assertTrue(s[k], (s["id"], k))
            self.assertGreaterEqual(s["min_interval"], 1.0, s["id"])
        self.assertEqual(F.BY_ID["nominatim"]["min_interval"], 1.0)

    def test_every_offline_result_has_licence_and_credit(self):
        for q in ["Paris", "1850 Paris", "elevation of Mont Blanc", "sea depth Hawaii", "mars", "stars near Sol",
                  "exoplanets", "Roman empire 117 AD", "land cover Kenya", "borders of Peru", "zzz"]:
            out = F.find(q)
            for r in out["results"]:
                self.assertTrue(r["licence"] and r["credit"] and r["url"], (q, r))

    def test_kinds(self):
        self.assertIn("time", F.find("London 1666")["kinds"])
        self.assertIn("subject", F.find("moon elevation")["kinds"])
        self.assertIn("place", F.find("Kyoto")["kinds"])
        ids = [r["source"] for r in F.find("mars elevation")["results"]]
        self.assertEqual(ids[0], "mola")
        ids = [r["source"] for r in F.find("sea depth")["results"]]
        self.assertIn("gebco", ids)

    def test_online_results_have_licence_and_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = FakeNet({"https://nominatim.openstreetmap.org/": NOMINATIM,
                           "https://commons.wikimedia.org/": COMMONS, "https://www.loc.gov/": LOC})
            http, _ = make_http(tmp, net)
            out = F.find("Paris 1850", http=http, online=True)
            online = [r for r in out["results"] if r["origin"] != "catalogue"]
            self.assertGreaterEqual(len(online), 5)
            for r in out["results"]:
                self.assertTrue(r["licence"] and r["credit"], r)
            c = [r for r in online if r["title"] == "File:Paris 1850.jpg"][0]
            self.assertEqual(c["licence"], "Public domain")
            self.assertIn("A. Mapper", c["credit"])
            self.assertTrue(any(r["source"] == "opentopography" and "south=48.81" in r["url"] for r in online))
            self.assertEqual(out["errors"], [])
            for _, ua in net.calls:
                self.assertEqual(ua, "mapwright/%s (+%s)" % (mpw.VERSION, F.HOME))

    def test_online_lookup_failure_is_reported_not_fatal(self):
        def down(req, timeout=None):
            raise urllib.error.URLError("offline")
        with tempfile.TemporaryDirectory() as tmp:
            http, _ = make_http(tmp, down)
            out = F.find("Paris", http=http, online=True)
            self.assertTrue(out["errors"])
            self.assertTrue(out["results"])


class RateTests(unittest.TestCase):
    def test_never_exceeds_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = FakeNet()
            clock = FakeClock()
            stamps = []
            orig = net.__call__

            def timed(req, timeout=None):
                stamps.append(clock.t)
                return orig(req, timeout)
            http, _ = make_http(tmp, timed, clock)
            src = F.BY_ID["nominatim"]
            for i in range(10):
                http.get("https://nominatim.openstreetmap.org/search?q=%d" % i, src)
                clock.t += 0.1  # caller fires fast
            gaps = [b - a for a, b in zip(stamps, stamps[1:])]
            self.assertEqual(len(stamps), 10)
            self.assertGreaterEqual(min(gaps), src["min_interval"] - 1e-9)

    def test_rate_kept_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = FakeClock()
            http, _ = make_http(tmp, FakeNet(), clock)
            http.get("https://www.loc.gov/maps/?q=a", F.BY_ID["loc"])
            http2, _ = make_http(tmp, FakeNet(), clock)  # a new process reads rate.json
            http2.get("https://www.loc.gov/maps/?q=b", F.BY_ID["loc"])
            self.assertAlmostEqual(sum(clock.slept), 3.0)

    def test_429_is_reported_with_retry_after(self):
        def busy(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {"Retry-After": "30"}, None)
        with tempfile.TemporaryDirectory() as tmp:
            http, _ = make_http(tmp, busy)
            with self.assertRaisesRegex(F.Refused, "429.*30"):
                http.get("https://nominatim.openstreetmap.org/search?q=x", F.BY_ID["nominatim"])


class FetchTests(unittest.TestCase):
    def test_forbidden_sources_refused_without_network(self):
        urls = ["https://mt1.google.com/vt/lyrs=s&x=1&y=2&z=3", "https://maps.googleapis.com/maps/api/staticmap?x",
                "https://ecn.t0.tiles.virtualearth.net/tiles/a1.jpeg", "https://api.mapbox.com/styles/v1/x",
                "https://api.maptiler.com/tiles/x", "https://tile.openstreetmap.org/5/10/12.png",
                "https://a.tile.openstreetmap.org/5/10/12.png", "https://api.openstreetmap.org/api/0.6/map?bbox=0,0,1,1",
                "https://server.arcgisonline.com/x", "https://tiles.stadiamaps.com/x", "https://tile.thunderforest.com/x",
                "https://atlas.microsoft.com/map/tile", "https://maps.apple.com/x", "https://api.tomtom.com/map/x"]
        with tempfile.TemporaryDirectory() as tmp:
            net = FakeNet()
            http, _ = make_http(tmp, net)
            for u in urls:
                with self.assertRaisesRegex(F.Refused, "never-scrape", msg=u):
                    F.fetch(u, os.path.join(tmp, "out"), http)
            self.assertEqual(net.calls, [])
            self.assertFalse(os.path.exists(os.path.join(tmp, "out")))

    def test_lookalike_host_not_refused(self):
        self.assertIsNone(F.forbidden("https://notgoogle.com.example.org/x"))
        self.assertIsNone(F.forbidden("https://download.geofabrik.de/europe/monaco-latest.osm.pbf"))

    def test_bulk_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = FakeNet()
            http, _ = make_http(tmp, net)
            for u in ["https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf",
                      "https://download.gebco.net/gebco_2025_sub_ice_topo_geotiff.zip"]:
                with self.assertRaisesRegex(F.Refused, "bulk", msg=u):
                    F.fetch(u, tmp, http)
            self.assertEqual(net.calls, [])

    def test_size_cap_by_header_and_by_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            big = FakeNet(headers={"Content-Length": str(300 * 1048576)})
            http, _ = make_http(tmp, big)
            with self.assertRaisesRegex(F.Refused, "over the 200 MB cap"):
                F.fetch("https://download.geofabrik.de/europe-latest.osm.pbf", tmp, http)
            stream = FakeNet({"https://naciscdn.org/": b"x" * 3000})
            http, _ = make_http(tmp, stream, cap_mb=0.001)
            with self.assertRaisesRegex(F.Refused, "passed the"):
                F.fetch("https://naciscdn.org/naturalearth/10m/land.zip", tmp, http)
            self.assertFalse(os.path.exists(os.path.join(tmp, "land.zip")))

    def test_writes_sources_and_credits_and_cache_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = FakeNet({"https://naciscdn.org/": b"ZIPDATA"})
            http, _ = make_http(tmp, net)
            out = os.path.join(tmp, "recipe")
            u = "https://naciscdn.org/naturalearth/110m/physical/ne_110m_land.zip"
            e = F.fetch(u, out, http, today="2026-11-15")
            self.assertEqual(e["cache"], "miss")
            self.assertEqual(len(net.calls), 1)
            e2 = F.fetch(u, out, http, today="2026-11-15")
            self.assertEqual(e2["cache"], "hit")
            self.assertEqual(len(net.calls), 1)  # cache hit: no network
            with open(os.path.join(out, "ne_110m_land.zip"), "rb") as f:
                self.assertEqual(f.read(), b"ZIPDATA")
            F.fetch("https://download.geofabrik.de/europe/monaco-latest.osm.pbf", out, http, today="2026-11-15")
            with open(os.path.join(out, "sources.json"), encoding="utf-8") as f:
                src = json.load(f)
            self.assertEqual([s["file"] for s in src], ["ne_110m_land.zip", "monaco-latest.osm.pbf"])
            for s in src:
                for k in ("url", "licence", "credit", "fetched", "rate", "sha256", "source"):
                    self.assertTrue(s[k], k)
            with open(os.path.join(out, "CREDITS.txt"), encoding="utf-8") as f:
                cr = f.read()
            self.assertIn("Made with Natural Earth", cr)
            self.assertIn("© OpenStreetMap contributors", cr)
            self.assertIn("ODbL-1.0", cr)

    def test_geoboundaries_licence_per_file(self):
        self.assertIn("boundaryLicense", F.BY_ID["geoboundaries"]["licence"])
        api = "https://www.geoboundaries.org/api/current/gbOpen/LIE/ADM0/"
        gj = "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/LIE/ADM0/geoBoundaries-LIE-ADM0.geojson"
        meta = json.dumps({"boundaryISO": "LIE", "boundaryType": "ADM0", "boundarySource": "OpenStreetMap",
                           "boundaryLicense": "Open Data Commons Open Database License 1.0",
                           "gjDownloadURL": gj}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            http, _ = make_http(tmp, FakeNet({api: meta, gj: b'{"type":"FeatureCollection","features":[]}'}))
            out = os.path.join(tmp, "recipe")
            e = F.fetch(api, out, http, name="LIE-ADM0.json", today="2026-11-15")
            self.assertEqual(e["licence"], "Open Data Commons Open Database License 1.0")
            self.assertIn("OpenStreetMap", e["credit"])
            e2 = F.fetch(gj, out, http, today="2026-11-15")
            self.assertEqual(e2["licence"], "Open Data Commons Open Database License 1.0")
            other = gj.replace("LIE", "PER")
            e3 = F.fetch(other, out, http, today="2026-11-15")
            self.assertTrue(e3["licence"].startswith("unknown"))
            with open(os.path.join(out, "CREDITS.txt"), encoding="utf-8") as f:
                cr = f.read()
            self.assertIn("geoBoundaries-LIE-ADM0.geojson: geoBoundaries", cr)
            self.assertIn("Open Database License 1.0", cr)
            self.assertNotIn("CC BY 4.0", cr)

    def test_unknown_host_needs_licence_and_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            http, _ = make_http(tmp, FakeNet())
            with self.assertRaisesRegex(F.Refused, "not in the catalogue"):
                F.fetch("https://example.org/map.geojson", tmp, http)
            e = F.fetch("https://example.org/map.geojson", tmp, http, licence="CC BY 4.0", credit="Example Org")
            self.assertEqual(e["credit"], "Example Org")

    def test_key_from_env_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = FakeNet()
            http, _ = make_http(tmp, net)
            u = "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=1&north=1.1&west=2&east=2.1"
            old = os.environ.pop(F.OT_KEY_ENV, None)
            try:
                with self.assertRaisesRegex(F.Refused, F.OT_KEY_ENV):
                    F.fetch(u, tmp, http, name="dem.tif")
                os.environ[F.OT_KEY_ENV] = "SECRET123"
                e = F.fetch(u, tmp, http, name="dem.tif")
            finally:
                os.environ.pop(F.OT_KEY_ENV, None)
                if old is not None:
                    os.environ[F.OT_KEY_ENV] = old
            self.assertIn("API_Key=SECRET123", net.calls[0][0])
            self.assertNotIn("SECRET", e["url"])
            for name in ("sources.json", "CREDITS.txt"):
                with open(os.path.join(tmp, name), encoding="utf-8") as f:
                    self.assertNotIn("SECRET", f.read())

    def test_cli_refuses_with_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as cm:
                import contextlib
                with contextlib.redirect_stderr(io.StringIO()):
                    mpw.main(["fetch", "https://mt0.google.com/vt/x", "-o", tmp, "--cache", os.path.join(tmp, "c")])
            self.assertNotEqual(cm.exception.code, 0)

    def test_cli_find_json(self):
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mpw.main(["find", "sea", "depth", "--json"])
        out = json.loads(buf.getvalue())
        self.assertTrue(out["results"])


@unittest.skipUnless(os.environ.get("MAPWRIGHT_LIVE") == "1", "live smoke test: set MAPWRIGHT_LIVE=1 (one Nominatim request)")
class LiveSmoke(unittest.TestCase):
    def test_nominatim_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            http = F.Http(mpw.VERSION, cache_dir=tmp)
            data, hit = http.get("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=Reykjavik",
                                 F.BY_ID["nominatim"])
            self.assertFalse(hit)
            self.assertEqual(http.requests, 1)
            self.assertIn("Reykjav", data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
