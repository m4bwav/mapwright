"""Tests for typed and geographic caves, the signal lint, transition-first growth and city quarters."""
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
import mpw_caves as C  # noqa: E402
import mpw_grow  # noqa: E402
import mpw_lint as L  # noqa: E402
import mpw_places as P  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mpw-r2s9-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def d(self, n):
        return os.path.join(self.tmp, n)


class TestCaveTypes(Base):
    def test_every_type_passes_check_and_regens(self):
        for t in C.CAVE_TYPES:
            out = self.d(t)
            P.gen_grid("dungeon", 7, out, 48, 36, "cave", cave=dict(type=t))
            bad = [b for b in P.check(out, labels=False) if b[2] is False]
            self.assertEqual(bad, [], t)
            gj = json.load(open(os.path.join(out, "grid.json"), encoding="utf-8"))
            self.assertEqual(gj["cave"]["type"], t)

    def test_shapes_differ(self):
        def floor(t):
            g, _ = C.typed_cave(48, 36, P.Rng(5, 2), t)
            return sum(r.count(".") for r in g)
        self.assertGreater(floor("glacial"), 2 * floor("crevice"))

    def test_lava_tube_runs_end_to_end(self):
        g, _ = C.typed_cave(48, 36, P.Rng(5, 2), "lava")
        xs = [x for r in g for x, c in enumerate(r) if c == "."]
        self.assertGreater(max(xs) - min(xs), 36)

    def test_unknown_type_refused(self):
        with self.assertRaises(ValueError):
            C.typed_cave(48, 36, P.Rng(1, 2), "volcano")


class TestCaveGeography(Base):
    def grid(self):
        g, _ = C.typed_cave(48, 36, P.Rng(9, 2), "solution")
        return g

    def test_water_table_floods_more(self):
        g = self.grid()
        lo = C.annotate(g, 48, 36, 9, "solution", dict(water_table=0.1))
        hi = C.annotate(g, 48, 36, 9, "solution", dict(water_table=0.6))
        self.assertGreater(sum(r.count("~") for r in hi["cells"]), sum(r.count("~") for r in lo["cells"]))

    def test_weak_rock_under_lake_collapses_granite_does_not(self):
        g = self.grid()
        weak = C.annotate(g, 48, 36, 9, "solution", dict(rock="shale", above="lake"))
        firm = C.annotate(g, 48, 36, 9, "solution", dict(rock="granite", above="soil"))
        self.assertTrue(any(s["collapse"] for s in weak["sections"]))
        self.assertFalse(any(s["collapse"] for s in firm["sections"]))

    def test_cold_gives_ice_built_gives_worked_stone(self):
        g = self.grid()
        cold = C.annotate(g, 48, 36, 9, "solution", dict(heat="cold"))
        built = C.annotate(g, 48, 36, 9, "solution", dict(built=True))
        self.assertEqual({s["climb"] for s in cold["sections"]}, {"ice"})
        self.assertEqual({s["climb"] for s in built["sections"]}, {"worked stone"})
        self.assertTrue(all(s["clearance"] in ("crawl", "stoop", "walk", "hall") for s in cold["sections"]))

    def test_bad_geography_refused(self):
        with self.assertRaises(ValueError):
            C.geo_defaults("solution", dict(rock="cheese"))
        with self.assertRaises(ValueError):
            C.geo_defaults("solution", dict(water_table=2))

    def test_light_overlay_has_shadow_band(self):
        g = [list("#" * 12)] + [list("#" + "." * 10 + "#") for _ in range(3)] + [list("#" * 12)]
        ov = C.light_overlay(g, 12, 5, [dict(x=1.5, y=2.5, range=3)])
        self.assertEqual(ov[2][1], "L")
        self.assertEqual(ov[2][4], "L")
        self.assertEqual(ov[2][6], "s")
        self.assertEqual(ov[2][9], " ")

    def test_cli_geo_flags_reach_grid_json(self):
        out = self.d("cli")
        run_cli("gen", "dungeon", "--seed", "3", "--method", "cave", "--cave-type", "sea", "--rock", "shale",
                "--above", "city", "--water-table", "0.4", "--out", out)
        gj = json.load(open(os.path.join(out, "grid.json"), encoding="utf-8"))
        self.assertEqual(gj["cave"]["geo"]["above"], "city")
        self.assertIn("light", gj["cave"])
        self.assertEqual([b for b in P.check(out, labels=False) if b[2] is False], [])


def plan_dir(tmp, plan):
    with open(os.path.join(tmp, "recipe.json"), "w", encoding="utf-8") as f:
        json.dump(dict(kind="plan", seed=1, plan=plan), f)
    return tmp


class TestSignal(Base):
    def plan(self, ridge_elev=0):
        return dict(rooms=[dict(id="keep", entrance=True, x=0, y=0, elev=10),
                           dict(id="o1", outpost=True, x=8, y=0, elev=10),
                           dict(id="o2", outpost=True, x=16, y=0, elev=10),
                           dict(id="road", x=24, y=0)],
                    links=[["keep", "o1"], ["o1", "o2"], ["o2", "road"]],
                    signal=dict(keep="keep", range=10, routes=[["road", "o2"]],
                                ridges=[dict(x=12, y=0, elev=ridge_elev)]))

    def test_chain_reaches_keep(self):
        res = L.lint(plan_dir(self.tmp, self.plan()))
        self.assertFalse([w for w in res["warnings"] if w["check"] == "signal"])
        self.assertIn("signal: outpost o2 reaches the keep in 2 hop(s)", res["info"])

    def test_ridge_breaks_chain(self):
        res = L.lint(plan_dir(self.tmp, self.plan(ridge_elev=50)))
        self.assertTrue(any("o2 cannot pass a signal" in w["text"] for w in res["warnings"]))

    def test_route_without_outpost_and_fire_load(self):
        pl = self.plan()
        pl["signal"]["routes"].append(["road"])
        pl["rooms"][0]["fire_load"] = "high"
        pl["rooms"][1]["under"] = "keep"
        res = L.lint(plan_dir(self.tmp, pl))
        txt = [w["text"] for w in res["warnings"] if w["check"] == "signal"]
        self.assertTrue(any("route 2" in t for t in txt))
        self.assertTrue(any("fire load" in t for t in txt))
        self.assertTrue(any("hard to retrofit" in i for i in res["info"]))
        pl["rooms"][0]["secret_exit"] = True
        txt = [w["text"] for w in L.lint(plan_dir(self.tmp, pl))["warnings"]]
        self.assertFalse(any("fire load" in t for t in txt))


class TestGrow(Base):
    def test_transitions_tricks_and_determinism(self):
        a = mpw_grow.grow_plan(4, transitions=12, trick_every=3)
        self.assertEqual(a, mpw_grow.grow_plan(4, transitions=12, trick_every=3))
        self.assertEqual(len(a["links"]), 12)
        self.assertEqual(len(a["rooms"]), 13)
        self.assertEqual([i + 1 for i, l in enumerate(a["links"]) if "trick" in l], [3, 6, 9, 12])
        self.assertTrue(all("transition" in l for l in a["links"]))
        self.assertTrue(a["rooms"][0]["entrance"])

    def test_lair_caps_empty_share(self):
        for s in range(1, 30):
            p = mpw_grow.grow_plan(s, transitions=20, lair=True)
            self.assertLessEqual(p["grow"]["empty_share"], mpw_grow.LAIR_EMPTY_CAP + 1e-9)

    def test_cli_writes_a_plan_lint_reads(self):
        out = self.d("g")
        txt = run_cli("grow", "--seed", "2", "--out", out, "--transitions", "6")
        self.assertIn("6 transitions", txt)
        res = L.lint(out)
        self.assertIn("critical path", " ".join(res["info"]))

    def test_bad_args_refused(self):
        with self.assertRaises(ValueError):
            mpw_grow.grow_plan(1, edge="up")
        with self.assertRaises(ValueError):
            mpw_grow.grow_plan(1, trick_every=0)


class TestCityQuarters(Base):
    def test_districts_carry_people_and_shops(self):
        out = self.d("c")
        P.gen_city(4, out, version="0.37.0")
        fc = json.load(open(os.path.join(out, "features.geojson"), encoding="utf-8"))
        ds = [f["properties"] for f in fc["features"] if f["properties"]["kind"] == "district"]
        self.assertTrue(ds)
        for d in ds:
            self.assertIn(d["people"], P.PEOPLE)
            self.assertEqual(d["quarter"], d["people"] + " quarter")
            self.assertTrue(d["shops"])
            self.assertTrue(set(d["shops"]) <= set(P.SHOPS[d["type"]]))
        self.assertEqual([b for b in P.check(out, labels=False) if b[2] is False], [])

    def test_old_recipe_keeps_old_districts(self):
        out = self.d("old")
        P.gen_city(4, out, version="0.36.0")
        fc = json.load(open(os.path.join(out, "features.geojson"), encoding="utf-8"))
        ds = [f["properties"] for f in fc["features"] if f["properties"]["kind"] == "district"]
        self.assertFalse(any("shops" in d for d in ds))


if __name__ == "__main__":
    unittest.main()
