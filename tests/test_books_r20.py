"""Book round 20: site-word names with glosses, current arrows, index grid and gazetteer, dungeon player copy,
sector hazard zones, OSM boundary notes."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw  # noqa: E402
import mpw_gen as G  # noqa: E402
import mpw_human as Hm  # noqa: E402
import mpw_names as N  # noqa: E402
import mpw_places as P  # noqa: E402
import mpw_render as R  # noqa: E402
import mpw_space as S  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-r20-")
        cls.world = os.path.join(cls.tmp, "w")
        run_cli("gen", "world", "--seed", "7", "--cells", "2500", "--raster", "64", "--style", "nordic",
                "--out", cls.world)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestSiteNames(Base):
    def test_every_name_glossed_and_site_words_match(self):
        nj = G.load(self.world, "names.json")
        self.assertTrue(all(e.get("gloss") for e in nj["names"]))
        gens = [e for e in nj["names"] if e.get("generic")]
        self.assertTrue(gens)
        for e in gens:
            self.assertTrue(e["name"].lower().endswith(N.ROOTS["nordic"][e["generic"]]), e)
        m = G.load(self.world, "mesh.json")
        nb = Hm.neighbours(m)
        sets = [f["properties"] for f in G.load(self.world, "features.geojson")["features"]
                if f["properties"]["kind"] == "settlement"]
        bar = G.gloss_bar(m, nb, nj["names"], sets)
        self.assertTrue(bar[2], bar[3])

    def test_bar_fails_on_missing_gloss_or_wrong_site(self):
        m = G.load(self.world, "mesh.json")
        nb = Hm.neighbours(m)
        nj = G.load(self.world, "names.json")
        sets = [f["properties"] for f in G.load(self.world, "features.geojson")["features"]
                if f["properties"]["kind"] == "settlement"]
        ents = [dict(e) for e in nj["names"]]
        ents[0].pop("gloss")
        self.assertFalse(G.gloss_bar(m, nb, ents, sets)[2])
        ents = [dict(e) for e in nj["names"]]
        g = [e for e in ents if e.get("generic")][0]
        g["generic"] = "hill" if g["generic"] != "hill" else "ford"
        bar = G.gloss_bar(m, nb, ents, sets)
        self.assertFalse(bar[2])
        self.assertIn("1 mismatched", bar[3])

    def test_custom_pattern_gets_no_site_word(self):
        lang = N.make_language(3, pattern="C=p t k;V=a i u;S=CV")
        nm, gen, gloss = N.site_name(N.Namer(lang), (1, 2), "ford")
        self.assertIsNone(gen)
        self.assertTrue(gloss)


class TestRenderExtras(Base):
    def test_currents_drawn_at_sea_with_legend(self):
        svg, info = R.render_svg(self.world, currents=True)
        self.assertGreater(info["currents"]["warm"] + info["currents"]["cold"], 0)
        self.assertIn('class="currents"', svg)
        self.assertTrue({"warm current", "cold current"} & set(info["legend"]))
        rc, m, _ = R.load(self.world)
        frame = R._frame(rc)
        grid = G.Grid(m["x"], m["y"], 20.0)
        x0, y0, s, _ = frame
        for kind, a, b in R.current_arrows(rc, m, frame):
            for px, py in (a, b):
                c = grid.near(px / s + x0, py / s + y0, 1)[0][1]
                self.assertTrue(m["ocean"][c])

    def test_currents_off_by_default_and_model1_draws_none(self):
        svg, info = R.render_svg(self.world)
        self.assertNotIn('class="currents"', svg)
        rc, m, _ = R.load(self.world)
        rc = dict(rc, params=dict(rc["params"], climate=None))
        self.assertEqual(R.current_arrows(rc, m, R._frame(rc)), [])

    def test_grid_and_gazetteer(self):
        self.assertEqual(R.grid_ref(0, 0, 8), "A1")
        self.assertEqual(R.grid_ref(999, 130, 8), "H2")
        svg, _ = R.render_svg(self.world, grid=8)
        self.assertIn('class="refgrid"', svg)
        csv = os.path.join(self.tmp, "g.csv")
        run_cli("render", self.world, "-o", os.path.join(self.tmp, "g.svg"), "--grid", "8", "--gazetteer", csv)
        rows = open(csv, encoding="utf-8").read().splitlines()
        self.assertEqual(rows[0], "name,kind,ref")
        self.assertGreater(len(rows), 10)
        with self.assertRaises(ValueError):
            R.gazetteer(self.world, 30)


class TestPlayerCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mpw-r20p-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_secret_floor_reported_and_removed(self):
        gm = os.path.join(self.tmp, "gm")
        P.gen_grid("dungeon", 4, gm, 48, 36, method="cyclic", pps=40, branches=4)
        hidden, gaps = P.secret_only(P.load(gm, "grid.json"))
        self.assertTrue(hidden and gaps)
        bar = [b for b in P.check(gm, determinism=False, labels=False) if "secret" in b[1]][0]
        self.assertIn("%d of" % len(hidden), bar[3])
        pl = os.path.join(self.tmp, "pl")
        run_cli("export", gm, "--to", "player", "-o", pl)
        gj = P.load(pl, "grid.json")
        self.assertEqual(P.secret_only(gj), (set(), set()))
        for x, y in hidden | gaps:
            self.assertEqual(gj["cells"][y][x], P.WALLC)
        kinds = {f["properties"]["kind"] for f in P.load(pl, "features.geojson")["features"]}
        self.assertFalse(kinds & {"secret door", "treasure"})
        self.assertNotIn('class="secret"', open(os.path.join(pl, "map.svg"), encoding="utf-8").read())
        self.assertEqual([b for b in P.check(pl, determinism=False, labels=False) if b[2] is False], [])

    def test_no_secrets_no_report_change(self):
        gm = os.path.join(self.tmp, "bsp")
        P.gen_grid("dungeon", 2, gm, 48, 36, pps=40)
        self.assertEqual(P.secret_only(P.load(gm, "grid.json")), (set(), set()))


class TestHazards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mpw-r20s-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_three_tiers_and_routes_avoid(self):
        out = os.path.join(self.tmp, "s")
        dropped = 0
        for seed in range(1, 6):
            S.gen_sector(seed, out, "sector", hazards=6)
            sec = P.load(out, "sector.json")
            self.assertEqual({h["tier"] for h in sec["hazards"]}, set(S.HAZ_TIERS))
            bars = S.check(out, determinism=seed == 1, labels=False)
            self.assertEqual([b for b in bars if b[2] is False], [], seed)
            S.gen_sector(seed, os.path.join(self.tmp, "plain"), "sector")
            dropped += len(P.load(os.path.join(self.tmp, "plain"), "sector.json")["routes"]) - len(sec["routes"])
        self.assertGreater(dropped, 0)

    def test_route_hazard_and_default_unchanged(self):
        haz = {(2, 0): "prohibited"}
        self.assertEqual(S.route_hazard((0, 0), (4, 0), haz), "prohibited")
        self.assertIsNone(S.route_hazard((0, 3), (4, 3), haz))
        out = os.path.join(self.tmp, "d")
        S.gen_sector(3, out)
        self.assertNotIn("hazards", P.load(out, "sector.json"))
        with self.assertRaises(ValueError):
            S.gen_sector(3, out, hazards=40)


class TestBoundaryNotes(unittest.TestCase):
    def test_disputed_and_languages(self):
        fs = [{"type": "Feature", "properties": {"boundary": "administrative", "admin_level": "2", "name": "A",
                                                 "name:en": "A", "name:fr": "A"}, "geometry": None},
              {"type": "Feature", "properties": {"tags": {"boundary": "disputed", "name": "Strip"}}, "geometry": None},
              {"type": "Feature", "properties": {"highway": "road"}, "geometry": None}]
        b = mpw.boundary_notes(fs)
        self.assertEqual((b["count"], b["disputed"]), (2, 1))
        self.assertEqual(b["name_languages"], ["en", "fr"])
        self.assertIn("disputed boundary (dashed)", b["legend"])
        self.assertIsNone(mpw.boundary_notes(fs[2:]))


if __name__ == "__main__":
    unittest.main()
