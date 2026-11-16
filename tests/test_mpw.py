"""Tests for scripts/mpw.py. Run: python -m unittest discover -s tests"""
import io
import json
import math
import os
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import mpw  # noqa: E402

DEG_TOL = 1e-7  # round-trip bar for format conversion, degrees


def coords_of(collection):
    out = []
    for f in collection["features"]:
        out.append(list(mpw.iter_coords(f["geometry"])))
    return out


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def write_shapefile(stem, polys, names):
    """Tiny Polygon shapefile writer (CW outer rings, CCW holes) for fixtures."""
    recs = []
    for i, rings in enumerate(polys):
        pts = [p for r in rings for p in r]
        parts, n = [], 0
        for r in rings:
            parts.append(n)
            n += len(r)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        body = struct.pack("<i4d2i", 5, min(xs), min(ys), max(xs), max(ys), len(rings), len(pts))
        body += struct.pack("<%di" % len(parts), *parts)
        body += b"".join(struct.pack("<2d", *p) for p in pts)
        recs.append(struct.pack(">2i", i + 1, len(body) // 2) + body)
    allp = [p for rings in polys for r in rings for p in r]
    bbox = (min(p[0] for p in allp), min(p[1] for p in allp), max(p[0] for p in allp), max(p[1] for p in allp))
    total = 100 + sum(len(r) for r in recs)
    hdr = struct.pack(">7i", 9994, 0, 0, 0, 0, 0, total // 2) + struct.pack("<2i", 1000, 5)
    hdr += struct.pack("<4d", *bbox) + struct.pack("<4d", 0, 0, 0, 0)
    with open(stem + ".shp", "wb") as f:
        f.write(hdr + b"".join(recs))
    # DBF: one character field NAME (20)
    nrec = len(names)
    dh = struct.pack("<B3BIHH20x", 3, 126, 11, 14, nrec, 32 + 32 + 1, 1 + 20)
    fd = b"NAME".ljust(11, b"\0") + b"C" + b"\0" * 4 + bytes([20, 0]) + b"\0" * 14
    rows = b"".join(b" " + n.encode("latin-1").ljust(20) for n in names)
    with open(stem + ".dbf", "wb") as f:
        f.write(dh + fd + b"\r" + rows + b"\x1a")
    with open(stem + ".prj", "w") as f:
        f.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
                'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')


class TestConvert(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def p(self, name):
        return os.path.join(self.tmp, name)

    def assertCoordsClose(self, a, b):
        self.assertEqual(len(a), len(b))
        for fa, fb in zip(a, b):
            self.assertEqual(len(fa), len(fb))
            for pa, pb in zip(fa, fb):
                self.assertLess(abs(pa[0] - pb[0]), DEG_TOL)
                self.assertLess(abs(pa[1] - pb[1]), DEG_TOL)

    def test_geojson_gpx_geojson(self):
        src = os.path.join(FIX, "route.geojson")
        mpw.convert(src, self.p("a.gpx"))
        mpw.convert(self.p("a.gpx"), self.p("b.geojson"))
        a, b = mpw.read_geojson(src), mpw.read_geojson(self.p("b.geojson"))
        self.assertCoordsClose(coords_of(a), coords_of(b))
        self.assertEqual([f["properties"]["name"] for f in b["features"]], ["Start", "Plan", "Walk", "Paris"])
        self.assertEqual(b["features"][1]["properties"]["gpx"], "rte")
        self.assertEqual(b["features"][0]["geometry"]["coordinates"][2], 11.0)

    def test_geojson_kml_geojson(self):
        for name in ("route.geojson", "square.geojson"):
            src = os.path.join(FIX, name)
            mpw.convert(src, self.p("a.kml"))
            mpw.convert(self.p("a.kml"), self.p("b.geojson"))
            a, b = mpw.read_geojson(src), mpw.read_geojson(self.p("b.geojson"))
            self.assertCoordsClose(coords_of(a), coords_of(b))
        self.assertEqual(len(b["features"][0]["geometry"]["coordinates"]), 2)  # hole kept

    def test_gpx_kml_gpx(self):
        src = os.path.join(FIX, "track.gpx")
        mpw.convert(src, self.p("a.kml"))
        mpw.convert(self.p("a.kml"), self.p("b.gpx"))
        self.assertCoordsClose(coords_of(mpw.read_gpx(src)), coords_of(mpw.read_gpx(self.p("b.gpx"))))

    def test_polygon_to_gpx_is_skipped(self):
        n, skipped = mpw.convert(os.path.join(FIX, "square.geojson"), self.p("s.gpx"))
        self.assertEqual((n, skipped), (1, 1))

    def test_shapefile_to_geojson(self):
        outer = [[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]  # clockwise
        hole = [[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5], [0.5, 0.5]]  # counter-clockwise
        far = [[10, 10], [10, 11], [11, 11], [11, 10], [10, 10]]
        stem = self.p("parcels")
        write_shapefile(stem, [[outer, hole], [far]], ["Field", "Wood"])
        mpw.convert(stem + ".shp", self.p("p.geojson"))
        col = mpw.read_geojson(self.p("p.geojson"))
        self.assertEqual([f["properties"]["NAME"] for f in col["features"]], ["Field", "Wood"])
        g = col["features"][0]["geometry"]
        self.assertEqual(g["type"], "Polygon")
        self.assertEqual(len(g["coordinates"]), 2)
        self.assertGreater(mpw._ring_area(g["coordinates"][0]), 0)  # RFC 7946: outer CCW
        self.assertLess(mpw._ring_area(g["coordinates"][1]), 0)
        s = mpw.inspect_file(stem + ".shp")
        self.assertEqual(s["shape_type"], "Polygon")
        self.assertEqual(s["features"], 2)
        self.assertIn("WGS_1984", s["crs"])
        self.assertEqual(s["extent"], [0, 0, 11, 11])

    def test_xml_entities_refused(self):
        bad = self.p("bomb.gpx")
        with open(bad, "w") as f:
            f.write('<?xml version="1.0"?><!DOCTYPE g [<!ENTITY a "aaaa">]><gpx>&a;</gpx>')
        with self.assertRaises(SystemExit):
            mpw.read_gpx(bad)


class TestInspect(unittest.TestCase):
    def test_geojson(self):
        s = mpw.inspect_file(os.path.join(FIX, "route.geojson"))
        self.assertEqual(s["features"], 4)
        self.assertEqual(s["geometry_types"], {"Point": 1, "LineString": 2, "MultiLineString": 1})
        self.assertAlmostEqual(s["extent"][3], 52.5200066)

    def test_gpx(self):
        s = mpw.inspect_file(os.path.join(FIX, "track.gpx"))
        self.assertEqual((s["features"], s["points"]), (2, 4))

    def test_png16_world_file(self):
        s = mpw.inspect_file(os.path.join(FIX, "heights.png"))
        self.assertEqual((s["width"], s["height"], s["bit_depth"]), (16, 12, 16))
        self.assertEqual(s["extent"], [500000.0, 4199880.0, 500160.0, 4200000.0])
        self.assertEqual(s["value_range"], [0, 18300])  # (15*1000 + 11*300) % 65536

    def test_gpkg_and_mbtiles(self):
        tmp = tempfile.mkdtemp()
        g = os.path.join(tmp, "t.gpkg")
        con = sqlite3.connect(g)
        con.executescript("""
            PRAGMA application_id = 1196444487; PRAGMA user_version = 10400;
            CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT, srs_id INTEGER PRIMARY KEY, organization TEXT,
              organization_coordsys_id INTEGER, definition TEXT, description TEXT);
            INSERT INTO gpkg_spatial_ref_sys VALUES ('WGS 84', 4326, 'EPSG', 4326, 'x', NULL);
            CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY, data_type TEXT, identifier TEXT,
              description TEXT, last_change TEXT, min_x REAL, min_y REAL, max_x REAL, max_y REAL, srs_id INTEGER);
            INSERT INTO gpkg_contents VALUES ('towns', 'features', 'towns', '', '', -1, 50, 2, 53, 4326);
            CREATE TABLE towns (fid INTEGER PRIMARY KEY, geom BLOB);
            INSERT INTO towns (geom) VALUES (NULL), (NULL), (NULL);""")
        con.commit()
        con.close()
        s = mpw.inspect_file(g)
        self.assertEqual(s["format"], "GeoPackage")
        self.assertEqual(s["application_id"], "0x47504b47")
        self.assertEqual(s["layers"][0]["rows"], 3)
        self.assertIn("EPSG:4326", s["layers"][0]["crs"])
        m = os.path.join(tmp, "t.mbtiles")
        con = sqlite3.connect(m)
        con.executescript("""CREATE TABLE metadata (name TEXT, value TEXT);
            INSERT INTO metadata VALUES ('name','demo'),('format','png');
            CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB);
            INSERT INTO tiles VALUES (0,0,0,x'00'),(1,0,0,x'00'),(1,1,1,x'00');""")
        con.commit()
        con.close()
        s = mpw.inspect_file(m)
        self.assertEqual((s["format"], s["tiles"], s["zooms"], s["metadata"]["name"]), ("MBTiles", 3, [0, 1], "demo"))


class TestGeodesy(unittest.TestCase):
    def test_flinders_peak_buninyong(self):
        # Geoscience Australia's Vincenty worked example (GRS80):
        # Flinders Peak -37 57 03.72030, 144 25 29.52440 to Buninyong -37 39 10.15610, 143 55 35.38390
        # distance 54 972.271 m, azimuth 306 52 05.37, reverse azimuth 127 10 25.07.
        lat1 = -(37 + 57 / 60 + 3.72030 / 3600)
        lon1 = 144 + 25 / 60 + 29.52440 / 3600
        lat2 = -(37 + 39 / 60 + 10.15610 / 3600)
        lon2 = 143 + 55 / 60 + 35.38390 / 3600
        s, a1, a2 = mpw.vincenty_inverse(lat1, lon1, lat2, lon2, "GRS80")
        self.assertLess(abs(s - 54972.271), 0.001)
        self.assertLess(abs(a1 - (306 + 52 / 60 + 5.37 / 3600)), 0.01 / 3600)
        self.assertLess(abs((a2 + 180) % 360 - (127 + 10 / 60 + 25.07 / 3600)), 0.01 / 3600)

    def test_wellington_salamanca(self):
        # GeographicLib Python docs example (WGS84): Inverse(-41.32, 174.81, 40.96, -5.50)
        # s12 = 19959679.26735382 m, azi1 = 161.06766998615, azi2 = 18.825195123248.
        r = mpw.geodesic_inverse(-41.32, 174.81, 40.96, -5.50)
        self.assertLess(abs(r["distance_m"] - 19959679.26735382), 0.001)
        self.assertLess(abs(r["azimuth1"] - 161.06766998615), 1e-6)
        self.assertLess(abs(r["azimuth2"] - 18.825195123248), 1e-6)

    def test_antipodal_falls_back(self):
        r = mpw.geodesic_inverse(0.0, 0.0, 0.5, 179.7)
        self.assertTrue(r["method"].startswith(("haversine", "Karney")), r["method"])
        self.assertGreater(r["distance_m"], 19e6)

    def test_whole_earth_area(self):
        # WGS84 surface area 510 065 621.724 km^2 (4 pi c^2, c = authalic radius 6 371 007.181 m;
        # GeographicLib geodesic docs).
        ring = [[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]
        self.assertLess(abs(mpw.ellipsoid_area(ring) / 1e6 - 510065621.724), 0.01)
        self.assertLess(abs(mpw.authalic_radius() - 6371007.181), 0.001)

    def test_hole_subtracted(self):
        col = mpw.read_geojson(os.path.join(FIX, "square.geojson"))
        g = col["features"][0]["geometry"]
        cell = mpw.ellipsoid_area(g["coordinates"][0])
        self.assertLess(abs(mpw.polygon_area(g) / cell - 0.75), 0.01)  # hole is a quarter, slightly off by latitude

    def test_scale_cli(self):
        self.assertIn("1000 m", run_cli("measure", "scale", "1:50000", "--map", "2cm"))
        self.assertIn("6 cm", run_cli("measure", "scale", "1:50,000", "--ground", "3km"))


GRID = [(lon, lat) for lon in range(-170, 180, 10) for lat in range(-80, 90, 10)]


class TestProjections(unittest.TestCase):
    def test_round_trip(self):
        for name in mpw.PROJECTIONS:
            for lon0, lat0 in ((0, 0), (20, 50)) if name == "laea" else ((0, 0),):
                worst = 0.0
                for lon, lat in GRID:
                    if name == "laea" and mpw.geodesic_inverse(lat, lon, -lat0, lon0 + 180)["distance_m"] < 2e6:
                        continue  # near the antipode of the centre LAEA is singular
                    x, y = mpw.forward(name, lon, lat, 1.0, lon0, lat0)
                    lo, la = mpw.inverse(name, x, y, 1.0, lon0, lat0)
                    worst = max(worst, abs(mpw._wrap(lo - lon)), abs(la - lat))
                # Robinson: PROJ's float32 spline table does not meet exactly at the 5-degree
                # nodes, so its own inverse misses by up to ~2e-5 deg there (PROJ behaves the same)
                tol = 5e-5 if name == "robinson" else 1e-9
                self.assertLess(worst, tol, "%s lon0=%s lat0=%s worst %.3g" % (name, lon0, lat0, worst))

    def test_known_values(self):
        x, _ = mpw.forward("webmercator", 180, 0)
        self.assertAlmostEqual(abs(x), 20037508.342789244, places=6)
        x, y = mpw.forward("equirectangular", 90, 45)
        self.assertAlmostEqual(x, math.pi / 2, places=12)
        self.assertAlmostEqual(y, math.pi / 4, places=12)
        self.assertAlmostEqual(mpw.forward("equalearth", 179.999999999, 0)[0], 2.70663, places=5)
        self.assertAlmostEqual(mpw.forward("equalearth", 0, 90)[1], 1.317363, places=6)
        self.assertAlmostEqual(mpw.forward("mollweide", 0, 90)[1], math.sqrt(2), places=12)
        self.assertAlmostEqual(mpw.forward("robinson", 0, 90)[1], 1.3523, places=12)
        self.assertAlmostEqual(mpw.forward("laea", 90, 0)[0], math.sqrt(2), places=12)

    def test_equal_area_ratios(self):
        # Two lon/lat cells; on the unit sphere area = dlon * (sin lat2 - sin lat1).
        cells = [(0, 0, 10, 10), (30, 55, 40, 65)]

        def sphere(c):
            return math.radians(c[2] - c[0]) * (math.sin(math.radians(c[3])) - math.sin(math.radians(c[1])))

        def projected(name, c, n=2000):
            lo1, la1, lo2, la2 = c
            ring = ([(lo1 + (lo2 - lo1) * i / n, la1) for i in range(n)]
                    + [(lo2, la1 + (la2 - la1) * i / n) for i in range(n)]
                    + [(lo2 - (lo2 - lo1) * i / n, la2) for i in range(n)]
                    + [(lo1, la2 - (la2 - la1) * i / n) for i in range(n)])
            pts = [mpw.forward(name, lo, la) for lo, la in ring]
            pts.append(pts[0])
            return abs(sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1] for i in range(len(pts) - 1)) / 2)

        want = sphere(cells[0]) / sphere(cells[1])
        for name in ("mollweide", "laea", "equalearth"):
            got = projected(name, cells[0]) / projected(name, cells[1])
            self.assertLess(abs(got / want - 1), 1e-6, "%s ratio %.9f want %.9f" % (name, got, want))
        # and the trap: Web Mercator does not preserve it
        got = projected("webmercator", cells[0]) / projected("webmercator", cells[1])
        self.assertGreater(abs(got / want - 1), 0.5)

    def test_webmercator_cut(self):
        with self.assertRaises(ValueError):
            mpw.forward("webmercator", 0, 89)


class TestCli(unittest.TestCase):
    def test_doctor_json(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "mpw.py"), "doctor", "--json"],
                             capture_output=True, text=True, check=True).stdout
        d = json.loads(out)
        self.assertTrue(d["python_ok"])
        self.assertIn("numpy", d["extras"])

    def test_explain(self):
        self.assertIn("Equal-area", run_cli("explain", "Mollweide"))
        self.assertIn("web-mercator", run_cli("explain", "EPSG:3857"))
        with self.assertRaises(SystemExit):
            run_cli("explain", "no-such-term")

    def test_project_cli(self):
        out = json.loads(run_cli("project", "webmercator", "0", "0", "--json"))
        self.assertEqual(out, {"x": 0.0, "y": 0.0})
        out = json.loads(run_cli("project", "mollweide", "1", "0.5", "--inverse", "--json"))
        x, y = mpw.forward("mollweide", out["lon"], out["lat"])
        self.assertAlmostEqual(x, 1, places=12)

    def test_no_optional_imports_at_top(self):
        src = open(os.path.join(ROOT, "scripts", "mpw.py"), encoding="utf-8").read()
        for mod in ("numpy", "shapely", "pyproj", "osgeo", "geographiclib"):
            self.assertNotIn("\nimport " + mod, src)
            self.assertNotIn("\nfrom " + mod, src)



class TestRobinsonProj(unittest.TestCase):
    """PROJ builtins.gie rows for +proj=robin +a=6400000 (tolerance 0.1 mm there).
    references/projections.md has no gie rows; these were read from
    https://github.com/OSGeo/PROJ/blob/master/test/gie/builtins.gie on 2026-11-14."""
    R = 6400000.0

    def test_forward_rows(self):
        for lon, lat, ex, ey in ((2, 1, 189588.423282508, 107318.530350703),
                                 (2, -1, 189588.423282508, -107318.530350703),
                                 (-2, 1, -189588.423282508, 107318.530350703),
                                 (0, 89.5, 0.0, 8639799.718722090125),
                                 (0, 90, 0.0, 8654720.0),
                                 (0, -90, 0.0, -8654720.0)):
            x, y = mpw.forward("robinson", lon, lat, R=self.R)
            self.assertLess(abs(x - ex), 1e-4, (lon, lat))
            self.assertLess(abs(y - ey), 1e-4, (lon, lat))

    def test_inverse_rows(self):
        for x, y, elon, elat in ((200, 100, 0.002109689, 0.000931806), (200, -100, 0.002109689, -0.000931806),
                                 (-200, 100, -0.002109689, 0.000931806)):
            lon, lat = mpw.inverse("robinson", x, y, R=self.R)
            self.assertAlmostEqual(lon, elon, places=9)
            self.assertAlmostEqual(lat, elat, places=9)

    def test_round_trip_and_smooth(self):
        for lat in (0.3, 4.99, 5.0, 37.2, 62.5, 84.9, 89.99):
            x, y = mpw.forward("robinson", 120, lat)
            lon2, lat2 = mpw.inverse("robinson", x, y)
            self.assertLess(abs(lon2 - 120), 5e-5)
            self.assertLess(abs(lat2 - lat), 5e-5)
        # the spline nodes meet: no jump at a 5-degree node
        a = mpw.forward("robinson", 100, 45 - 1e-9)
        b = mpw.forward("robinson", 100, 45 + 1e-9)
        self.assertLess(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1e-6)


import mpw_gen  # noqa: E402

GEN_FILES = ("recipe.json", "features.geojson", "heights.png", "heights.pgw", "mesh.json", "names.json",
             "sources.json", "map.svg")


class TestGen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-gen-")
        cls.world = os.path.join(cls.tmp, "w")
        run_cli("gen", "world", "--seed", "7", "--cells", "1600", "--raster", "96", "--out", cls.world)
        cls.child = os.path.join(cls.tmp, "c")
        run_cli("gen", "region", "--parent", cls.world, "--window", "250,250,550,550", "--cells", "1600",
                "--raster", "96", "--out", cls.child)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_world_folder(self):
        for fn in GEN_FILES:
            self.assertTrue(os.path.isfile(os.path.join(self.world, fn)), fn)
        rc = json.load(open(os.path.join(self.world, "recipe.json")))
        self.assertEqual(rc["seed"], 7)
        self.assertEqual(rc["tool_version"], mpw.VERSION)
        self.assertEqual(mpw.png_header(os.path.join(self.world, "heights.png"))["bit_depth"], 16)
        kinds = {f["properties"]["kind"] for f in
                 json.load(open(os.path.join(self.world, "features.geojson")))["features"]}
        self.assertIn("coast", kinds)
        self.assertIn("river", kinds)
        with open(os.path.join(self.world, "map.svg"), encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("<svg"))

    def test_world_bars_pass(self):
        out = run_cli("check", self.world)
        self.assertEqual(out.count("PASS") + out.count("SKIP"), 17, out)
        self.assertEqual(out.count("FAIL"), 0, out)
        self.assertEqual(run_cli("check", self.world, "--no-labels").count("PASS"), 14)

    def test_bar7_arid_not_judged(self):
        bars = mpw_gen.check(self.world, determinism=False)
        self.assertNotIn("arid", bars[6][3])
        old = mpw_gen.SHADOW_MIN_WET
        mpw_gen.SHADOW_MIN_WET = 10000
        try:
            bars = mpw_gen.check(self.world, determinism=False)
        finally:
            mpw_gen.SHADOW_MIN_WET = old
        self.assertTrue(bars[6][2])
        self.assertIn("too arid to judge", bars[6][3])

    def test_priority_flood_drains_to_outlet(self):
        # a 1-D valley with no sea: the edge outlet takes all water
        H = [0.5, 0.3, 0.4, 0.2, 0.1]
        nb = [[1], [0, 2], [1, 3], [2, 4], [3]]
        hyd = mpw_gen.hydrology(H, nb, 2.0, None, [4])
        self.assertEqual(hyd["rcv"], [1, 2, 3, 4, -1])
        self.assertEqual(hyd["outlets"], [4])
        self.assertTrue(all(hyd["F"][c] > hyd["F"][hyd["rcv"][c]] for c in range(4)))
        # with sea present the outlets are ignored
        hyd2 = mpw_gen.hydrology([0.5, 0.3, 0.4, 0.2, -0.1], nb, 2.0, None, [0])
        self.assertEqual(hyd2["outlets"], [])

    def test_landlocked_grandchild_drains_through_edge(self):
        w = os.path.join(self.tmp, "lw")
        c = os.path.join(self.tmp, "lc")
        g = os.path.join(self.tmp, "lg")
        mpw_gen.gen_world(2, 1600, w, raster_px=64)
        mpw_gen.gen_region(w, None, 1600, c, raster_px=64)
        rc = json.load(open(os.path.join(c, "recipe.json")))
        m = json.load(open(os.path.join(c, "mesh.json")))
        x0, y0, x1, y1 = rc["extent"]
        win = (x0, y0, x0 + (x1 - x0) / 4, y0 + (y1 - y0) / 4)   # all land in the seed 2 sweep (T-20261116-8)
        cs = [i for i in range(len(m["x"])) if win[0] <= m["x"][i] <= win[2] and win[1] <= m["y"][i] <= win[3]]
        self.assertFalse(any(m["ocean"][i] for i in cs))
        mpw_gen.gen_region(c, win, 1600, g, raster_px=64)
        gm = json.load(open(os.path.join(g, "mesh.json")))
        self.assertTrue(gm["outlets"])
        nx, ny = gm["nx"], gm["ny"]
        for i in gm["outlets"]:
            self.assertTrue(i % nx in (0, nx - 1) or i // nx in (0, ny - 1))
        self.assertGreater(sum(gm["river"]), 0)
        bars = mpw_gen.check(g)
        self.assertTrue(all(b[2] for b in bars), [b for b in bars if not b[2]])

    def test_child_bars_pass(self):
        bars = mpw_gen.check(self.child)
        self.assertTrue(all(b[2] for b in bars), bars)
        self.assertIn("max", bars[4][3])
        self.assertIn("max", bars[5][3])

    def test_same_seed_identical(self):
        other = os.path.join(self.tmp, "w2")
        run_cli("gen", "world", "--seed", "7", "--cells", "1600", "--raster", "96", "--out", other)
        for fn in GEN_FILES:
            with open(os.path.join(self.world, fn), "rb") as a, open(os.path.join(other, fn), "rb") as b:
                self.assertEqual(a.read(), b.read(), fn)
        third = os.path.join(self.tmp, "w3")
        run_cli("gen", "world", "--seed", "8", "--cells", "1600", "--raster", "96", "--out", third)
        with open(os.path.join(self.world, "mesh.json"), "rb") as a, open(os.path.join(third, "mesh.json"), "rb") as b:
            self.assertNotEqual(a.read(), b.read())

    def test_zoom_alias(self):
        z = os.path.join(self.tmp, "z")
        out = run_cli("zoom", self.world, "--cells", "1200", "--raster", "64", "--out", z, "--json")
        r = json.loads(out)
        self.assertEqual(len(r["window"]), 4)
        rc = json.load(open(os.path.join(z, "recipe.json")))
        self.assertEqual(rc["kind"], "region")
        self.assertEqual(rc["parent"]["window"], r["window"])

    def test_region_rejects_coarse_child(self):
        with self.assertRaises(SystemExit):
            run_cli("gen", "region", "--parent", self.world, "--window", "0,0,1000,1000", "--cells", "100",
                    "--out", os.path.join(self.tmp, "bad"))

    def test_check_fails_on_broken_river(self):
        import shutil
        bad = os.path.join(self.tmp, "broken")
        shutil.copytree(self.world, bad)
        p = os.path.join(bad, "mesh.json")
        m = json.load(open(p))
        c = next(i for i, r in enumerate(m["river"]) if r and not m["ocean"][i])
        m["f"][m["rcv"][c]] = m["f"][c] + 1.0   # receiver now uphill
        with open(p, "w") as f:
            json.dump(m, f)
        with self.assertRaises(SystemExit) as cm:
            run_cli("check", bad, "--no-regen")
        self.assertNotEqual(cm.exception.code, 0)
        bars = mpw_gen.check(bad, determinism=False)
        self.assertFalse(bars[0][2])

    def test_whittaker_and_climate(self):
        self.assertEqual(mpw_gen.whittaker(27, 400), "tropical rainforest")
        self.assertEqual(mpw_gen.whittaker(27, 10), "subtropical desert")
        self.assertEqual(mpw_gen.whittaker(-12, 50), "ice")
        self.assertGreater(mpw_gen.sea_level_temp(0), mpw_gen.sea_level_temp(45))
        self.assertEqual(mpw_gen.wind_dir(45), 1)
        self.assertEqual(mpw_gen.wind_dir(15), -1)


import mpw_names  # noqa: E402
import mpw_human  # noqa: E402


class TestNames(unittest.TestCase):
    def test_sample_deterministic_unique_clean(self):
        for st in sorted(mpw_names.STYLES):
            lang, a = mpw_names.sample(200, 5, st)
            _, b = mpw_names.sample(200, 5, st)
            self.assertEqual(a, b, st)
            self.assertEqual(len({x.lower() for x in a}), 200, st)
            for x in a:
                self.assertTrue(mpw_names.ok_name(x.lower()), (st, x))
            self.assertEqual(lang["style"], st)
        self.assertNotEqual(mpw_names.sample(20, 5, "soft")[1], mpw_names.sample(20, 6, "soft")[1])

    def test_custom_pattern(self):
        lang, names = mpw_names.sample(30, 1, pattern="C=t k m;V=a o;F=n;S=CV CVF;N=2-3")
        self.assertEqual(lang["style"], "custom")
        for x in names:
            self.assertTrue(set(x.lower()) <= set("tkmaon"), x)
        for bad in ("V=a", "C=t;V=a;S=CVX", "C=t;V=a;S=CVF", "Q=x;C=t;V=a;S=CV"):
            with self.assertRaises(ValueError):
                mpw_names.parse_pattern(bad)
        with self.assertRaises(ValueError):
            mpw_names.make_language(1, "nosuch")

    def test_filter(self):
        for bad in ("aaab", "xy", "kkkra", "abcdefghijk", "brrrt", "ptk", "aeiou"):
            self.assertFalse(mpw_names.ok_name(bad), bad)
        self.assertTrue(mpw_names.ok_name("valdor"))

    def test_names_cli(self):
        out = run_cli("names", "--sample", "5", "--style", "nordic", "--seed", "3")
        self.assertEqual(len(out.split()), 5)
        self.assertIn("isle", run_cli("names", "--list"))
        with self.assertRaises(SystemExit):
            run_cli("names", "--pattern", "C=t")


class TestHuman(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-hum-")
        cls.world = os.path.join(cls.tmp, "w")
        run_cli("gen", "world", "--seed", "11", "--cells", "2500", "--raster", "64", "--style", "latinate",
                "--out", cls.world)
        cls.child = os.path.join(cls.tmp, "kids", "c")
        run_cli("gen", "region", "--parent", cls.world, "--window", "100,100,400,400", "--cells", "2500",
                "--raster", "64", "--out", cls.child)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def feats(self, d):
        with open(os.path.join(d, "features.geojson")) as f:
            return [x["properties"] for x in json.load(f)["features"]]

    def load(self, d, fn):
        with open(os.path.join(d, fn)) as f:
            return json.load(f)

    def test_world_has_settlements_roads_names(self):
        fs = self.feats(self.world)
        kinds = {f["kind"] for f in fs}
        for k in ("settlement", "road", "land"):
            self.assertIn(k, kinds)
        self.assertTrue(kinds & {"sea", "ocean"})
        sets = [f for f in fs if f["kind"] == "settlement"]
        self.assertEqual({f["rank"] for f in sets}, {"city", "town", "village"})
        for f in fs:
            if f["kind"] in ("settlement", "lake", "sea", "ocean", "range", "land", "river"):
                self.assertTrue(f.get("name"), f)
        nj = self.load(self.world, "names.json")
        self.assertEqual(nj["language"]["style"], "latinate")
        self.assertEqual(self.load(self.world, "recipe.json")["language"], nj["language"])
        low = [e["name"].lower() for e in nj["names"]]
        self.assertEqual(len(low), len(set(low)))

    def test_settlement_spacing_and_sites(self):
        m = self.load(self.world, "mesh.json")
        sets = [f for f in self.feats(self.world) if f["kind"] == "settlement"]
        sp = max(mpw_human.SPACING_WORLD, 3 * m["sp"])
        for i, a in enumerate(sets):
            for b in sets[i + 1:]:
                d = math.hypot(m["x"][a["cell"]] - m["x"][b["cell"]], m["y"][a["cell"]] - m["y"][b["cell"]])
                self.assertGreaterEqual(d, sp - 1e-9)
        scores = [f["score"] for f in sets]
        self.assertEqual(scores[0], max(scores))

    def test_river_named_once_per_stem(self):
        fs = [f for f in self.feats(self.world) if f["kind"] == "river"]
        by = {}
        for f in fs:
            by.setdefault(f["name"], set()).add(f["stem"])
        for nm, stems in by.items():
            self.assertEqual(len(stems), 1, nm)

    def test_main_stem_follows_biggest_branch(self):
        # toy: 2 -> 1 -> 0 -> sea (4), and a small branch 3 -> 1
        m = dict(x=[0] * 5, y=[0] * 5, river=[1, 1, 1, 1, 0], rcv=[4, 0, 1, 1, -1],
                 acc=[30, 25, 20, 4, 0], ocean=[0, 0, 0, 0, 1], lake=[-1] * 5)
        stem, mouths = mpw_human.river_stems(m, None)
        self.assertEqual(mouths, [0])
        self.assertEqual(stem[0], stem[1])
        self.assertEqual(stem[1], stem[2])
        self.assertNotEqual(stem[3], stem[2])

    def test_rng_connected(self):
        pts = [(math.cos(i) * i, math.sin(i * 1.7) * i) for i in range(15)]
        uf = mpw_human.UF()
        for _, a, b in mpw_human.rng_edges(pts):
            uf.union(a, b)
        self.assertEqual(len({uf.find(i) for i in range(15)}), 1)

    def test_bars_world_and_child(self):
        for d in (self.world, self.child):
            bars = mpw_gen.check(d)
            self.assertEqual(len(bars), 14)
            self.assertTrue(all(b[2] for b in bars), [b for b in bars if not b[2]])
        b13 = mpw_gen.check(self.child, determinism=False)[12]
        self.assertIn("parent settlements in window", b13[3])

    def test_child_inherits(self):
        pf = {f["id"]: f for f in self.feats(self.world) if f["kind"] == "settlement"}
        cs = [f for f in self.feats(self.child) if f["kind"] == "settlement"]
        inh = [f for f in cs if "parent_id" in f]
        self.assertTrue(inh)
        for f in inh:
            self.assertEqual(f["name"], pf[f["parent_id"]]["name"])
            self.assertEqual(f["rank"], pf[f["parent_id"]]["rank"])
        self.assertTrue(any(f["rank"] == "village" and "parent_id" not in f for f in cs))
        cn = self.load(self.child, "names.json")
        pn = self.load(self.world, "names.json")
        self.assertEqual(cn["language"], pn["language"])
        mine = {e["name"] for e in cn["names"] if "parent_id" not in e and e["kind"] != "settlement"}
        mine |= {f["name"] for f in cs if "parent_id" not in f}
        self.assertFalse(mine & {e["name"] for e in pn["names"]})

    def test_parent_path_relative(self):
        rc = self.load(self.child, "recipe.json")
        self.assertEqual(rc["parent"]["path"], "../../w")
        self.assertEqual(os.path.normcase(mpw_gen.parent_dir(self.child, rc)), os.path.normcase(self.world))
        # old recipes stored an absolute path: still read
        rc2 = dict(rc, parent=dict(rc["parent"], path=os.path.abspath(self.world)))
        self.assertEqual(mpw_gen.parent_dir("elsewhere", rc2), os.path.abspath(self.world))

    def test_moved_pair_still_checks(self):
        import shutil
        dst = os.path.join(self.tmp, "moved")
        shutil.copytree(self.world, os.path.join(dst, "w"))
        shutil.copytree(self.child, os.path.join(dst, "kids", "c"))
        bars = mpw_gen.check(os.path.join(dst, "kids", "c"))
        self.assertTrue(all(b[2] for b in bars), [b for b in bars if not b[2]])

    def test_bars_catch_breakage(self):
        import shutil
        bad = os.path.join(self.tmp, "bad")
        shutil.copytree(self.world, bad)
        p = os.path.join(bad, "features.geojson")
        with open(p) as f:
            fc = json.load(f)
        sea = self.load(bad, "mesh.json")["ocean"].index(1)
        sets = [f for f in fc["features"] if f["properties"]["kind"] == "settlement"]
        sets[0]["properties"]["cell"] = sea                          # settlement in the sea
        road = next(f for f in fc["features"] if f["properties"]["kind"] == "road")
        road["properties"]["cells"].append(sea)                      # road into the sea
        with open(p, "w") as f:
            json.dump(fc, f)
        bars = {b[0]: b for b in mpw_gen.check(bad, determinism=False)}
        self.assertFalse(bars[8][2])
        self.assertFalse(bars[10][2])
        # drop every road: settlements of one landmass are no longer connected
        sets[0]["properties"]["cell"] = road["properties"]["cells"][0]
        fc["features"] = [f for f in fc["features"] if f["properties"]["kind"] not in ("road", "track")]
        with open(p, "w") as f:
            json.dump(fc, f)
        self.assertFalse({b[0]: b for b in mpw_gen.check(bad, determinism=False)}[9][2])
        nj = self.load(bad, "names.json")
        nj["names"].append(dict(nj["names"][0]))
        with open(os.path.join(bad, "names.json"), "w") as f:
            json.dump(nj, f)
        self.assertFalse({b[0]: b for b in mpw_gen.check(bad, determinism=False)}[11][2])

    def test_rename_world(self):
        import shutil
        d = os.path.join(self.tmp, "ren")
        shutil.copytree(self.world, d)
        out = run_cli("names", d, "--style", "isle")
        self.assertIn("language: isle", out)
        bars = mpw_gen.check(d)
        self.assertTrue(all(b[2] for b in bars), [b for b in bars if not b[2]])
        with self.assertRaises(SystemExit):
            run_cli("names", self.child, "--style", "isle")


class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import mpw_gen
        import mpw_render
        cls.R = mpw_render
        cls.tmp = tempfile.mkdtemp(prefix="mpw-render-")
        cls.world = os.path.join(cls.tmp, "w")
        mpw_gen.gen_world(7, 3000, cls.world, raster_px=256)
        cls.browser = mpw.find_browser()

    def out(self, name):
        return os.path.join(self.tmp, name)

    def read(self, p):
        with open(p, "rb") as f:
            return f.read()

    def test_render_svg_deterministic_every_style(self):
        for st in self.R.STYLES:
            a, b = self.out("a-%s.svg" % st), self.out("b-%s.svg" % st)
            run_cli("render", self.world, "-o", a, "--style", st)
            run_cli("render", self.world, "-o", b, "--style", st)
            data = self.read(a)
            self.assertEqual(data, self.read(b), st)
            self.assertNotIn(b"\r", data)
            root = mpw.ET.fromstring(data)
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            for cls in (b'class="rivers"', b'class="coast"', b'class="legend"', b'class="scalebar"',
                        b'class="north"', b'class="lbl"'):
                self.assertIn(cls, data, (st, cls))

    def test_render_json_and_bad_style(self):
        j = json.loads(run_cli("render", self.world, "-o", self.out("j.svg"), "--json"))
        self.assertGreater(j["placed"], 5)
        self.assertGreater(j["svg_bytes"], 10000)
        with self.assertRaises(SystemExit):
            run_cli("render", self.world, "-o", self.out("x.svg"), "--style", "nope")
        with self.assertRaises(SystemExit):
            run_cli("render", self.world, "-o", self.out("x.bmp"))

    def test_river_width_by_flow(self):
        svg, _ = self.R.render_svg(self.world)
        g = svg.split('class="rivers"')[1].split("</g>")[0]
        ws = [float(x.split('"')[0]) for x in g.split('stroke-width="')[1:]]
        self.assertGreater(max(ws), min(ws))

    def test_label_bars_pass_and_catch(self):
        out = run_cli("label", self.world)
        self.assertIn("PASS: labels: none overlap", out)
        self.assertIn("PASS: labels: none cut by the edge", out)
        j = json.loads(run_cli("label", self.world, "--json"))
        boxes = [p["box"] for p in j["placed"]]
        for i in range(len(boxes)):
            for k in range(i + 1, len(boxes)):
                self.assertFalse(self.R.overlap(boxes[i], boxes[k]))
        ocr = [b for b in j["bars"] if "OCR" in b["name"]][0]
        if not shutil_which("tesseract"):
            self.assertIsNone(ocr["ok"])  # skipped, never a fake pass
            self.assertIn("skipped", ocr["detail"])
        # the bars catch a forced overlap and an edge cut
        svg, _ = self.R.render_svg(self.world)
        bad = svg.replace('<g class="labels"', '<g class="labels"', 1).replace(
            "</g>\n<rect x=", '<text class="lbl" x="2" y="5" font-size="20">EDGE</text>'
            '<text class="lbl" x="2" y="5" font-size="20">EDGE</text></g>\n<rect x=', 1)
        bars = self.R.label_bars(bad)
        self.assertFalse(bars[0][1])
        self.assertFalse(bars[1][1])

    def test_width_table_is_wide_enough(self):
        import string
        chars = string.ascii_letters + string.digits + " .,'-"
        fonts = [p for p in ("C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/arial.ttf",
                             "C:/Windows/Fonts/pala.ttf", "C:/Windows/Fonts/times.ttf",
                             "/Library/Fonts/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
                 if os.path.isfile(p)]
        if not fonts:
            self.skipTest("no system TTF to compare against")
        for p in fonts:
            m = self.R.TTFMetrics(p)
            for c in chars:
                self.assertLessEqual(m.em(c), self.R.em_width(c) + 1e-9, (p, c))
            self.assertGreater(self.R.text_width("Hello", 10, metrics=m), 10)

    def test_legend_only_symbols_on_map(self):
        rc, m, feats = self.R.load(self.world)
        st = self.R.style("atlas")
        labels = [e["label"] for e in self.R.legend_entries(feats, m, st, rc)]
        has_track = any(f["properties"].get("rank") == "track" for f in feats if f["properties"]["kind"] in ("road", "track"))
        self.assertEqual("track" in labels, has_track)
        no_roads = [f for f in feats if f["properties"]["kind"] not in ("road", "track", "lake")]
        labels2 = [e["label"] for e in self.R.legend_entries(no_roads, m, st, rc)]
        self.assertNotIn("major road", labels2)
        self.assertNotIn("lake", labels2)
        biomes = set(self.R.G.BIOMES[b][0] for b, o, l in zip(m["biome"], m["ocean"], m["lake"]) if not o and l < 0)
        self.assertTrue(biomes <= set(labels))
        out = run_cli("legend", self.world, "-o", self.out("legend.svg"))
        self.assertIn("coast", out)
        self.assertTrue(self.read(self.out("legend.svg")).startswith(b"<svg"))

    def test_style_list(self):
        out = run_cli("style", "--list")
        for st in ("topographic", "atlas", "satellite", "ink-and-parchment", "blueprint", "star-chart"):
            self.assertIn(st, out)
        self.assertIn('"sea"', run_cli("style", "blueprint"))

    def test_serve_binds_loopback(self):
        import threading
        import urllib.request
        svg, _ = self.R.render_svg(self.world)
        srv = self.R.make_server(svg, "t", 0)
        try:
            self.assertEqual(srv.server_address[0], "127.0.0.1")
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = "http://127.0.0.1:%d/" % srv.server_address[1]
            page = urllib.request.urlopen(url, timeout=10).read().decode()
            self.assertIn("<svg", page)
            self.assertIn("viewBox", page)
            self.assertEqual(urllib.request.urlopen(url + "map.svg", timeout=10).read().decode(), svg)
            with self.assertRaises(Exception):
                urllib.request.urlopen(url + "etc/passwd", timeout=10)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_sheet_styles_and_seeds(self):
        p = self.out("sheet.svg")
        out = run_cli("sheet", self.world, "--styles", "atlas,blueprint", "-o", p)
        self.assertIn("2 maps", out)
        data = self.read(p).decode()
        self.assertEqual(data.count("<svg"), 3)
        self.assertIn(">blueprint<", data)
        mpw.ET.fromstring(data)
        p2 = self.out("sheet2.svg")
        sub_world = os.path.join(self.tmp, "small")
        import mpw_gen
        mpw_gen.gen_world(3, 1500, sub_world, raster_px=128)
        run_cli("sheet", sub_world, "--seeds", "3,4", "-o", p2)
        self.assertIn("seed 4", self.read(p2).decode())

    def test_png_pdf_via_browser(self):
        if not self.browser:
            with self.assertRaises(SystemExit):
                run_cli("render", self.world, "-o", self.out("m.png"))
            return
        run_cli("render", self.world, "-o", self.out("m.png"))
        self.assertTrue(self.read(self.out("m.png")).startswith(b"\x89PNG"))
        w, h = struct.unpack(">II", self.read(self.out("m.png"))[16:24])
        self.assertEqual(w, 1000)
        run_cli("render", self.world, "-o", self.out("m.pdf"), "--style", "ink-and-parchment")
        self.assertTrue(self.read(self.out("m.pdf")).startswith(b"%PDF"))

    def test_render_region(self):
        import mpw_gen
        child = os.path.join(self.tmp, "child")
        mpw_gen.gen_region(self.world, None, 1500, child, raster_px=128)
        out = run_cli("label", child)
        self.assertNotIn("FAIL", out)


def shutil_which(name):
    import shutil
    return shutil.which(name)


if __name__ == "__main__":
    unittest.main()
