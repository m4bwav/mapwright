"""Tests for gen city / dungeon / battle, their check bars and the Universal VTT export."""
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
import mpw_places as P  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def failed(bars):
    return [b for b in bars if b[-2] is False]


def named(bars, part):
    return [b for b in bars if part in b[-3]][0]


class PlacesBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-places-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def d(self, name):
        return os.path.join(self.tmp, name)


class TestCity(PlacesBase):
    def test_city_bars_pass_and_regen(self):
        out = self.d("city")
        r = P.gen_city(3, out)
        self.assertGreater(r["lots"], 200)
        self.assertGreaterEqual(r["gates"], 5)
        bars = P.check(out)
        self.assertEqual(failed(bars), [], bars)
        self.assertTrue(named(bars, "byte-identical")[-2])
        self.assertTrue(named(bars, "every street reachable")[-2])
        for f in ("recipe.json", "features.geojson", "names.json", "map.svg"):
            self.assertTrue(os.path.isfile(os.path.join(out, f)))

    def test_city_sweep_with_sea_river_and_no_wall(self):
        for seed in range(1, 6):
            for kw in ({}, dict(sea=seed * 0.9, river=seed * 1.7), dict(wall=None)):
                out = self.d("sw%d" % seed)
                P.gen_city(seed, out, **kw)
                self.assertEqual(failed(P.check(out, determinism=False, labels=False)), [], (seed, kw))

    def test_cut_street_fails_reachability(self):
        out = self.d("cut")
        P.gen_city(4, out, wall=None)
        fc = P.load(out, "features.geojson")
        # a street that touches nothing else
        fc["features"].append({"type": "Feature", "properties": {"kind": "street", "id": 998, "rank": "street"},
                               "geometry": {"type": "LineString", "coordinates": [[9000.0, 9000.0], [9100.0, 9000.0]]}})
        P.dump(os.path.join(out, "features.geojson"), fc)
        self.assertFalse(named(P._city_bars(out), "every street reachable")[-2])

    def test_street_through_wall_fails(self):
        out = self.d("thru")
        P.gen_city(5, out)
        fc = P.load(out, "features.geojson")
        fc["features"].append({"type": "Feature", "properties": {"kind": "street", "id": 999, "rank": "street"},
                               "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [5000.0, 0.0]]}})
        P.dump(os.path.join(out, "features.geojson"), fc)
        self.assertFalse(named(P._city_bars(out), "gates on the wall")[-2])

    def test_city_from_parent_world(self):
        w = self.d("world")
        run_cli("gen", "world", "--seed", "7", "--cells", "2000", "--out", w, "--raster", "64")
        sets = [f for f in P.load(w, "features.geojson")["features"] if f["properties"]["kind"] == "settlement"]
        sid = sets[0]["properties"]["id"]
        out = self.d("child")
        r = P.gen_city(1, out, parent=w, settlement=sid)
        self.assertEqual(r["name"], sets[0]["properties"]["name"])
        rc = P.load(out, "recipe.json")
        self.assertEqual(rc["parent"], {"path": "../world", "settlement": sid})
        self.assertEqual(rc["language"], P.load(w, "recipe.json")["language"])
        self.assertEqual(failed(P.check(out, labels=False)), [])


class TestDungeon(PlacesBase):
    def test_bsp_and_cave_pass(self):
        for m in ("bsp", "cave"):
            out = self.d("dg-" + m)
            r = P.gen_grid("dungeon", 11, out, 48, 36, m)
            if m == "bsp":
                self.assertGreater(r["rooms"], 6)
                self.assertGreater(r["doors"], 3)
            bars = P.check(out)
            self.assertEqual(failed(bars), [], bars)

    def test_sweep(self):
        for seed in range(1, 13):
            for m in ("bsp", "cave"):
                out = self.d("dsw")
                P.gen_grid("dungeon", seed, out, 40, 30, m, pps=20)
                self.assertEqual(failed(P.check(out, determinism=False, labels=False)), [], (seed, m))

    def test_walled_off_room_fails(self):
        out = self.d("walled")
        P.gen_grid("dungeon", 2, out, 40, 30, "bsp", pps=20)
        gj = P.load(out, "grid.json")
        r = gj["rooms"][-1]
        cells = [list(row) for row in gj["cells"]]
        for y in range(r["y"] - 1, r["y"] + r["h"] + 1):
            for x in range(r["x"] - 1, r["x"] + r["w"] + 1):
                if not (r["x"] <= x < r["x"] + r["w"] and r["y"] <= y < r["y"] + r["h"]):
                    cells[y][x] = "#"
        gj["cells"] = ["".join(c) for c in cells]
        P.dump(os.path.join(out, "grid.json"), gj)
        bars = P._grid_bars(out)
        self.assertFalse(named(bars, "every floor square reachable")[-2])
        self.assertFalse(named(bars, "every room reached")[-2])

    def test_loose_wall_fails(self):
        out = self.d("loose")
        P.gen_grid("dungeon", 2, out, 40, 30, "cave", pps=20)
        gj = P.load(out, "grid.json")
        gj["walls"].append([[3, 3], [3, 4]])
        P.dump(os.path.join(out, "grid.json"), gj)
        self.assertFalse(named(P._grid_bars(out), "walls closed")[-2])


class TestBattle(PlacesBase):
    def test_square_grid_on_whole_pixels(self):
        out = self.d("bt")
        P.gen_grid("battle", 4, out, 30, 20, grid="square", pps=70)
        bars = P.check(out)
        self.assertEqual(failed(bars), [], bars)
        with open(os.path.join(out, "map.png"), "rb") as f:
            self.assertEqual(P.png_size(f.read(32)), (2100, 1400))

    def test_hex_and_sweep(self):
        out = self.d("hx")
        P.gen_grid("battle", 4, out, 24, 16, grid="hex", pps=60)
        bars = P.check(out)
        self.assertEqual(failed(bars), [], bars)
        self.assertIn("max drift", named(bars, "hex grid")[-1])
        for seed in range(1, 21):
            for grid in ("square", "hex"):
                P.gen_grid("battle", seed, out, 30, 20, grid=grid, pps=40)
                self.assertEqual(failed(P.check(out, determinism=False, labels=False)), [], (seed, grid))

    def test_odd_hex_pps_refused_and_wrong_png_fails(self):
        with self.assertRaises(ValueError):
            P.gen_grid("battle", 1, self.d("odd"), 20, 12, grid="hex", pps=61)
        out = self.d("wrongpng")
        P.gen_grid("battle", 1, out, 20, 12, pps=50)
        rc = P.load(out, "recipe.json")
        rc["params"]["pps"] = 49
        P.dump(os.path.join(out, "recipe.json"), rc)
        self.assertFalse(named(P._grid_bars(out), "grid on whole pixels")[-2])


class TestUvtt(PlacesBase):
    def test_round_trip_cli(self):
        out = self.d("ux")
        run_cli("gen", "dungeon", "--seed", "8", "--w", "30", "--h", "24", "--pps", "50", "--out", out)
        f = os.path.join(self.tmp, "x.dd2vtt")
        txt = run_cli("export", out, "-o", f)
        self.assertNotIn("FAIL", txt)
        with open(f, encoding="utf-8") as fh:
            u = json.load(fh)
        gj = P.load(out, "grid.json")
        self.assertEqual(u["resolution"]["pixels_per_grid"], 50)
        self.assertEqual(len(u["line_of_sight"]), len(gj["walls"]))
        self.assertEqual(len(u["portals"]), len(gj["portals"]))
        self.assertEqual(len(u["lights"]), len(gj["lights"]))
        for line in u["line_of_sight"]:
            for p in line:
                self.assertTrue(0 <= p["x"] <= 30 and 0 <= p["y"] <= 24)

    def test_broken_files_fail(self):
        out = self.d("ub")
        P.gen_grid("battle", 2, out, 20, 14, pps=40)
        u = P.uvtt(out)
        u["line_of_sight"].append([{"x": -1, "y": 2}, {"x": 3, "y": 2}])
        if u["portals"]:
            u["portals"][0]["bounds"][0] = {"x": 0.25, "y": 0.25}
        u["resolution"]["pixels_per_grid"] = 40.5
        bars = P.uvtt_bars(json.dumps(u))
        self.assertFalse(bars[0][1])
        self.assertFalse(bars[1][1])
        self.assertFalse(P.uvtt_bars("{not json")[0][1])

    def test_city_and_hex_refused(self):
        out = self.d("uc")
        P.gen_city(2, out)
        with self.assertRaises(ValueError):
            P.uvtt(out)
        P.gen_grid("battle", 2, out, 20, 14, grid="hex", pps=40)
        with self.assertRaises(ValueError):
            P.uvtt(out)


class TestPlaceLabelsAndCli(PlacesBase):
    def test_label_bars_catch_overlap(self):
        import mpw_render as R
        out = self.d("lb")
        P.gen_city(6, out)
        with open(os.path.join(out, "map.svg"), encoding="utf-8") as f:
            svg = f.read()
        bad = svg.replace('<g class="labels"', '<g class="labels"', 1).replace(
            "</g>\n</svg>", '<text x="500.0" y="34.0" font-size="26.0" text-anchor="middle">Overlap</text></g>\n</svg>')
        self.assertTrue(all(b[1] is not False for b in R.label_bars(svg)[:2]))
        self.assertFalse(R.label_bars(bad)[0][1])

    def test_cli_gen_check_render(self):
        out = self.d("cli")
        txt = run_cli("gen", "battle", "--seed", "3", "--w", "16", "--h", "12", "--pps", "30", "--out", out)
        self.assertIn("16x12 square", txt)
        txt = run_cli("check", out, "--no-regen")
        self.assertIn("grid on whole pixels", txt)
        self.assertNotIn("FAIL", txt)
        svg = os.path.join(self.tmp, "b.svg")
        run_cli("render", out, "-o", svg, "--style", "blueprint")
        with open(svg, encoding="utf-8") as f:
            self.assertIn("#1d4e89", f.read())


if __name__ == "__main__":
    unittest.main()
