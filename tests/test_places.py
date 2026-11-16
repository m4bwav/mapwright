"""Tests for gen city / dungeon / battle, their check bars and the Universal VTT export."""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

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
        # Step E 2026-11-15: --title was silently ignored on battle, dungeon and city maps.
        run_cli("render", out, "-o", svg, "--title", "Ruined Watchpost")
        with open(svg, encoding="utf-8") as f:
            self.assertIn(">Ruined Watchpost<", f.read())


FIX = os.path.join(HERE, "fixtures")


def core_gj(D, w, h):
    gj = dict(w=w, h=h, cells=["".join(r) for r in D["g"]], entrance=D["entrance"], goal=D["goal"])
    if D["graph"]:
        gj["graph"] = D["graph"]
    return gj


class TestDungeonGoal(PlacesBase):
    def test_070_recipes_still_pass(self):
        for m in ("bsp", "cave"):
            bars = P.check(os.path.join(FIX, "dungeon-070-" + m))
            self.assertEqual(failed(bars), [], (m, bars))
            self.assertTrue(named(bars, "byte-identical")[-2])
            self.assertFalse([b for b in bars if "goal" in b[1]], "a 0.7.0 recipe gets no goal bars")

    def test_goal_farthest_path_and_walls(self):
        for m in ("bsp", "cave"):
            out = self.d("goal-" + m)
            P.gen_grid("dungeon", 5, out, 40, 30, m, pps=20)
            gj = P.load(out, "grid.json")
            rc = P.load(out, "recipe.json")
            self.assertEqual(rc["params"]["goal"], "farthest")
            dist = P.bfs_dist(gj["cells"], 40, 30, gj["entrance"])
            self.assertEqual(dist[tuple(gj["goal"])], max(dist.values()))
            self.assertGreaterEqual(dist[tuple(gj["goal"])], P.min_path(40, 30))
            self.assertEqual(P.isolated_walls(gj["cells"], 40, 30), [])
            kinds = [f["properties"]["kind"] for f in P.load(out, "features.geojson")["features"]]
            self.assertIn("goal", kinds)
            with open(os.path.join(out, "map.svg"), encoding="utf-8") as f:
                self.assertIn('class="goal"', f.read())
            self.assertEqual(failed(P.check(out, labels=False)), [])

    def test_goal_bars_catch_faults(self):
        out = self.d("goal-bad")
        P.gen_grid("dungeon", 5, out, 40, 30, "bsp", pps=20)
        gj = P.load(out, "grid.json")
        ex, ey = gj["entrance"]
        near = [p for p in P.nbrs4(ex, ey) if gj["cells"][p[1]][p[0]] in P.PASS][0]
        gj["goal"] = list(near)
        cells = [list(r) for r in gj["cells"]]
        x, y = 20, 15
        while cells[y][x] != "#":
            x += 1
        for nx, ny in P.nbrs4(x, y):
            if 0 < nx < 39 and 0 < ny < 29:
                cells[ny][nx] = "."
        gj["cells"] = ["".join(r) for r in cells]
        bars = P.goal_bars(gj, {})
        self.assertFalse(named(bars, "farthest")[-2])
        self.assertFalse(named(bars, "path at least")[-2])
        self.assertFalse(named(bars, "isolated")[-2])

    def test_goal_sweep(self):
        for seed in range(1, 41):
            for m in ("bsp", "cave"):
                D = P.build_dungeon(seed, 40, 30, m)
                self.assertEqual([b for b in P.goal_bars(core_gj(D, 40, 30), {}) if not b[1]], [], (seed, m))


class TestCaveFlags(PlacesBase):
    def test_defaults_match_070_draws(self):
        gj = P.load(os.path.join(FIX, "dungeon-070-cave"), "grid.json")
        rc = P.load(os.path.join(FIX, "dungeon-070-cave"), "recipe.json")
        g, _ = P.cave_dungeon(gj["w"], gj["h"], P.Rng(rc["seed"], 2), **P.CAVE_DEFAULTS)
        self.assertEqual(["".join(r) for r in g], gj["cells"])

    def test_flags_in_recipe_and_regen(self):
        out = self.d("cave-flags")
        txt = run_cli("gen", "dungeon", "--seed", "4", "--method", "cave", "--fill", "0.55", "--passes", "2",
                      "--birth", "6", "--survival", "5", "--border", "2", "--w", "40", "--h", "30", "--pps", "20",
                      "--out", out)
        self.assertIn("40x30", txt)
        cv = P.load(out, "recipe.json")["params"]["cave"]
        self.assertEqual(cv, dict(fill=0.55, passes=2, birth=6, survival=5, radius=1, border=2))
        bars = P.check(out, labels=False)
        self.assertEqual(failed(bars), [], bars)
        g = P.load(out, "grid.json")["cells"]
        self.assertTrue(all(c == "#" for c in g[1]))      # two-square border

    def test_cave_flag_on_bsp_refused(self):
        with self.assertRaisesRegex(ValueError, "cave flags"):
            P.gen_grid("dungeon", 1, self.d("x"), 40, 30, "bsp", cave=dict(fill=0.5))

    def test_settings_move_the_cave(self):
        lo, hi = {}, {}
        P.cave_dungeon(48, 36, P.Rng(3, 2), fill=0.40, stats=lo)
        P.cave_dungeon(48, 36, P.Rng(3, 2), fill=0.55, stats=hi)
        self.assertGreater(lo["largest_region_share"], hi["largest_region_share"])


class TestCyclic(PlacesBase):
    def test_cyclic_passes_and_regens(self):
        out = self.d("cyc")
        r = P.gen_grid("dungeon", 11, out, 48, 36, "cyclic", pps=20)
        self.assertGreaterEqual(r["rooms"], 6)
        bars = P.check(out)
        self.assertEqual(failed(bars), [], bars)
        for part in ("cycle rank", "share a border", "key reached before", "return path", "lock shut",
                     "byte-identical", "every room reached"):
            self.assertTrue(named(bars, part)[-2], part)
        gr = P.load(out, "grid.json")["graph"]
        self.assertTrue(any("lock" in e for e in gr["edges"]) and any("oneway" in e for e in gr["edges"]))
        with open(os.path.join(out, "map.svg"), encoding="utf-8") as f:
            svg = f.read()
        for c in ("key", "lock", "one-way", "goal", "entrance"):
            self.assertIn('class="%s"' % c, svg)

    def test_cyclic_sweep_200(self):
        rerolls = 0
        for seed in range(1, 201):
            D = P.build_dungeon(seed, 48, 36, "cyclic")
            rerolls += D["graph"]["rerolls"]
            bad = [b for b in P.goal_bars(core_gj(D, 48, 36), {}) if not b[1]]
            self.assertEqual(bad, [], seed)
        self.assertLess(rerolls, 200)

    def test_graph_bars_catch_faults(self):
        D = P.build_dungeon(11, 48, 36, "cyclic")
        gj = core_gj(D, 48, 36)
        gr = gj["graph"]

        def bars(mut):
            g2 = json.loads(json.dumps(gj))
            mut(g2["graph"])
            return P.goal_bars(g2, {})
        i = [k for k, e in enumerate(gr["edges"]) if "lock" in e][0]
        j = [k for k, e in enumerate(gr["edges"]) if e.get("oneway") and gr["goal"] in e["oneway"]][0]
        lock = gr["edges"][i]
        b = bars(lambda g: g["keys"][0].update(node=g["goal"]))
        self.assertFalse(named(b, "key reached before")[-2])
        b = bars(lambda g: g["edges"][j].update(oneway=g["edges"][j]["oneway"][::-1]))
        self.assertFalse(named(b, "key reached before")[-2])          # the lock is no longer a gate
        self.assertFalse(named(b, "lock shut")[-2])
        far = lock["a"] if lock["b"] == gr["goal"] else lock["b"]

        def jam(g):
            g["edges"][i].update(oneway=[far, gr["goal"]])
            g["edges"][j].update(oneway=[g["edges"][j]["oneway"][1], gr["goal"]])
        b = bars(jam)
        self.assertFalse(named(b, "return path")[-2])
        b = bars(lambda g: g["edges"].append(dict(a=0, b=g["goal"], door=lock["door"])))
        self.assertFalse(named(b, "share a border")[-2])
        b = bars(lambda g: g["edges"].extend([dict(g["edges"][0]) for _ in range(5)]))
        self.assertFalse(named(b, "cycle rank")[-2])

    def test_small_map_refused(self):
        with self.assertRaisesRegex(ValueError, "at least 22x22"):
            P.gen_grid("dungeon", 1, self.d("small"), 21, 30, "cyclic")


class TestRange(PlacesBase):
    def test_range_report_and_cli(self):
        rep = P.dungeon_range("bsp", 20, 40, 30)
        self.assertEqual(len(rep["rows"]), 20)
        for k in P.RANGE_METRICS:
            self.assertLessEqual(rep["metrics"][k]["min"], rep["metrics"][k]["max"])
        self.assertEqual(sum(map(sum, rep["pairs"][0]["bins"])), 20)
        cy = P.dungeon_range("cyclic", 20, 48, 36)
        self.assertTrue(cy["pairs"][0]["dominant"])     # every corridor on a loop: one bin holds all
        out = self.d("range")
        txt = run_cli("check", "--range", "cave", "--seeds", "12", "--w", "40", "--h", "30", out)
        self.assertIn("first 6 seeds against all 12", txt)
        import xml.etree.ElementTree as ET
        ET.parse(os.path.join(out, "range.svg"))
        with open(os.path.join(out, "range.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["seeds"], 12)

    def test_metrics_on_known_shapes(self):
        ring = ["#######", "#.....#", "#.###.#", "#.....#", "#######"]
        m = P.range_metrics(dict(w=7, h=5, cells=ring, entrance=[1, 1], goal=[5, 3]))
        self.assertEqual(m["loop_share"], 1.0)
        self.assertEqual(m["dead_end_share"], 0.0)
        lolly = ["########", "#...####", "#.......", "#...####", "########"]
        m = P.range_metrics(dict(w=8, h=5, cells=lolly, entrance=[1, 1], goal=[7, 2]))
        self.assertEqual(m["loop_share"], 0.0)
        self.assertGreater(m["dead_end_share"], 0.0)
        self.assertAlmostEqual(m["open_floor_share"], 13 / 40.0)


class TestBattleDensity(PlacesBase):
    """s17: --density on gen battle, cover never blocks reachability, legend lists only kinds present."""

    def test_density_sweep_and_legend(self):
        for grid in ("square", "hex"):
            out = self.d("dens-" + grid)    # a hex map writes no map.png, so never share the folder
            for dens, lo, hi in (("normal", 0.22, 0.26), ("dense", 0.32, 0.36)):
                for seed in range(1, 11):
                    P.gen_grid("battle", seed, out, 30, 20, grid=grid, pps=40, density=dens)
                    self.assertEqual(failed(P.check(out, determinism=seed == 1, labels=False)), [], (grid, dens, seed))
                    gj = P.load(out, "grid.json")
                    self.assertTrue(lo <= P.feature_share(gj["cells"]) < hi, (grid, dens, seed))
                    with open(os.path.join(out, "map.svg"), encoding="utf-8") as f:
                        svg = f.read()
                    kinds = {{"#": "rock", "T": "tree", "+": "door"}[c] for r in gj["cells"] for c in r if c != "."}
                    drawn = {k for k in ("rock", "tree", "door") if 'class="legend-%s"' % k in svg}
                    self.assertEqual(drawn, kinds, (grid, dens, seed))

    def test_sparse_and_default_api_keep_old_map(self):
        a, b = self.d("old"), self.d("sparse")
        P.gen_grid("battle", 31, a, 30, 20, pps=40)
        P.gen_grid("battle", 31, b, 30, 20, pps=40, density="sparse")
        self.assertEqual(P.load(a, "grid.json"), P.load(b, "grid.json"))
        self.assertNotIn("density", P.load(a, "recipe.json")["params"])
        with self.assertRaises(ValueError):
            P.gen_grid("battle", 1, self.d("bad"), 30, 20, density="thick")


class TestCyclicBranches(PlacesBase):
    def test_branches_sweep(self):
        out = self.d("br")
        for seed in range(1, 11):
            P.gen_grid("dungeon", seed, out, 48, 36, method="cyclic", pps=40, branches=4)
            self.assertEqual(failed(P.check(out, determinism=seed == 1, labels=False)), [], seed)
            gr = P.load(out, "grid.json")["graph"]
            self.assertTrue(gr["branches"])
            keyed = {k["node"] for k in gr["keys"]}
            for b in gr["branches"]:
                self.assertFalse(keyed & set(b["nodes"]))

    def test_default_has_no_branches_and_flag_needs_cyclic(self):
        out = self.d("nobr")
        P.gen_grid("dungeon", 77, out, 48, 36, method="cyclic", pps=40)
        self.assertNotIn("branches", P.load(out, "grid.json")["graph"])
        self.assertNotIn("branches", P.load(out, "recipe.json")["params"])
        with self.assertRaises(ValueError):
            P.gen_grid("dungeon", 1, self.d("bspbr"), 48, 36, method="bsp", branches=2)


if __name__ == "__main__":
    unittest.main()


class TestS18BattleFrameAndTreasure(unittest.TestCase):
    """s18: battle title and legend sit outside the grid; treasure always lands on a floor cell in its room."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_title_and_legend_outside_grid(self):
        for grid in ("square", "hex"):
            for seed in (31, 7, 12):
                out = os.path.join(self.tmp, "%s-%d" % (grid, seed))
                P.gen_grid("battle", seed, out, 30, 20, grid=grid, pps=40)
                self.assertEqual(failed(P.check(out, determinism=seed == 31, labels=False)), [], (grid, seed))
                with open(os.path.join(out, "map.svg"), encoding="utf-8") as f:
                    svg = f.read()
                top = int(re.search(r'class="map" transform="translate\(0,(\d+)\)"', svg).group(1))
                gh = 20 * 40 if grid == "square" else P.hex_geometry(30, 20, 40)[3]
                lg = re.search(r'<g class="legend"[^>]*>\s*<rect x="[\d.]+" y="([\d.]+)"', svg)
                self.assertGreaterEqual(float(lg.group(1)), top + gh, (grid, seed))
                ty = float(re.search(r'<g class="labels".*?<text x="[\d.]+" y="([\d.]+)"', svg).group(1))
                self.assertLessEqual(ty, top, (grid, seed))

    def test_treasure_on_floor_in_room(self):
        n = 0
        for br in (2, 4, 8):
            for seed in range(1, 41):
                out = os.path.join(self.tmp, "c%d-%d" % (br, seed))
                P.gen_grid("dungeon", seed, out, 48, 36, method="cyclic", pps=20, branches=br)
                gj = P.load(out, "grid.json")
                for b in gj["graph"]["branches"]:
                    if not b["treasure"]:
                        continue
                    r = gj["rooms"][b["nodes"][-1]]
                    x, y = P.treasure_cell(gj, b["nodes"][-1])
                    self.assertTrue(r["x"] <= x < r["x"] + r["w"] and r["y"] <= y < r["y"] + r["h"], (br, seed))
                    self.assertEqual(gj["cells"][y][x], P.FLOOR, (br, seed))
                    n += 1
                shutil.rmtree(out, ignore_errors=True)
        self.assertGreater(n, 50)

    def test_legend_cli_on_place_recipes(self):
        b = os.path.join(self.tmp, "b")
        P.gen_grid("battle", 31, b, 30, 20, pps=40)
        txt = run_cli("legend", b)
        self.assertIn("rock or ruined wall", txt)
        ents = json.loads(run_cli("legend", b, "--json"))
        self.assertEqual({e["kind"] for e in ents}, {"rock", "tree", "door"})
        svg = os.path.join(self.tmp, "leg.svg")
        run_cli("legend", b, "-o", svg, "--json")
        with open(svg, encoding="utf-8") as f:
            self.assertIn('class="legend-tree"', f.read())
        d = os.path.join(self.tmp, "d")
        P.gen_grid("dungeon", 3, d, 40, 30, pps=20)
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit):
            run_cli("legend", d)
        self.assertIn("no legend", err.getvalue())
