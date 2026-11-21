import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import mpw_biome  # noqa: E402
import mpw_places as P  # noqa: E402


def gen(tmp, name, **kw):
    out = os.path.join(tmp, name)
    P.gen_grid("battle", kw.pop("seed", 7), out, kw.pop("w", 40), kw.pop("h", 30), grid=kw.pop("grid", "square"),
               **kw)
    return out, P.load(out, "recipe.json"), P.load(out, "grid.json")


class BiomeBattle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()

    def test_same_seed_identical(self):
        a, _, _ = gen(self.tmp, "a", biome="boreal")
        b, _, _ = gen(self.tmp, "b", biome="boreal")
        for f in ("grid.json", "recipe.json", "features.geojson"):
            with open(os.path.join(a, f), "rb") as x, open(os.path.join(b, f), "rb") as y:
                self.assertEqual(x.read(), y.read(), f)

    def test_rules_hold(self):
        for biome in mpw_biome.BIOMES:
            for grid in ("square", "hex"):
                _, rc, gj = gen(self.tmp, biome + grid, biome=biome, grid=grid)
                w, h, n = gj["w"], gj["h"], gj["w"] * gj["h"]
                names = gj["terrain_key"]
                for rule, got in zip(rc["params"]["rules"], gj["scatter"]):
                    lo, hi = rule["per10k"]
                    self.assertLessEqual(math.floor(lo * n / 1e4), got["target"])
                    self.assertLessEqual(got["target"], math.ceil(hi * n / 1e4))
                    self.assertEqual(got["placed"], got["target"], (biome, grid, rule["feature"]))
                    pts = got["points"]
                    m = rule["edge_margin"]
                    for i, (x, y) in enumerate(pts):
                        self.assertTrue(m <= x < w - m and m <= y < h - m)
                        self.assertNotIn(names[gj["terrain"][y][x]], rule["avoid"])
                        for x2, y2 in pts[i + 1:]:
                            self.assertGreaterEqual(math.hypot(x - x2, y - y2), rule["min_spacing"])

    def test_swamp_wetter_than_desert(self):
        _, _, s = gen(self.tmp, "sw", biome="swamp")
        _, _, d = gen(self.tmp, "de", biome="desert")
        self.assertGreater(sum(r.count("w") for r in s["terrain"]), sum(r.count("w") for r in d["terrain"]))

    def test_band_shares_follow_cuts(self):
        t = mpw_biome.terrain_grid(3, 60, 50, mpw_biome.BIOMES["swamp"])
        share = sum(r.count("water") for r in t) / 3000.0
        self.assertAlmostEqual(share, 0.38, delta=0.01)

    def test_still_one_open_region(self):
        for biome in mpw_biome.BIOMES:
            _, _, gj = gen(self.tmp, "c" + biome, biome=biome, density="dense")
            g = [list(r) for r in gj["cells"]]
            self.assertEqual(len(P.flood_regions(g, gj["w"], gj["h"], P.PASS, P.nbrs4)), 1, biome)

    def test_density_scales_counts(self):
        _, a, _ = gen(self.tmp, "sp", biome="temperate", density="sparse")
        _, b, _ = gen(self.tmp, "dn", biome="temperate", density="dense")
        self.assertLess(sum(s["target"] for s in a["scatter"]), sum(s["target"] for s in b["scatter"]))

    def test_no_biome_unchanged(self):
        _, rc, gj = gen(self.tmp, "plain")
        self.assertNotIn("terrain", gj)
        self.assertNotIn("biome", rc["params"])

    def test_cli_rules_file_and_check(self):
        rules = os.path.join(self.tmp, "rules.json")
        with open(rules, "w", encoding="utf-8") as f:
            json.dump({"scatter": [{"feature": "crate", "per10k": [50, 50], "min_spacing": 3, "edge_margin": 2,
                                    "avoid": ["water"], "cell": "rock"}]}, f)
        out = os.path.join(self.tmp, "cli")
        mpw = os.path.join(SCRIPTS, "mpw.py")
        r = subprocess.run([sys.executable, mpw, "gen", "battle", "--seed", "4", "--w", "40", "--h", "30",
                            "--rules", rules, "--out", out], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        rc = P.load(out, "recipe.json")
        self.assertEqual(rc["params"]["biome"], "temperate")
        self.assertEqual(rc["scatter"], [dict(feature="crate", target=6, placed=6)])
        c = subprocess.run([sys.executable, mpw, "check", out], capture_output=True, text=True)
        self.assertNotIn("FAIL", c.stdout)

    def test_bad_rule_rejected(self):
        with self.assertRaises(ValueError):
            mpw_biome.validate_rules([{"feature": "x", "per10k": [5, 1]}])
        with self.assertRaises(ValueError):
            mpw_biome.validate_rules([{"feature": "x", "per10k": [1, 2], "avoid": ["lava"]}])


if __name__ == "__main__":
    unittest.main()
