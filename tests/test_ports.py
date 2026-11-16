"""Row 21: ports only on open coast (open-sea flood from the border, bar 14)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import mpw_gen  # noqa: E402


def grid_mesh(rows, sp=1.0, x0=0.0, y0=0.0):
    """rows: strings, '~' sea, '.' land. Returns mesh dict and 4-neighbour lists."""
    ny, nx = len(rows), len(rows[0])
    m = dict(nx=nx, ny=ny, sp=sp, x=[], y=[], ocean=[])
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            m["x"].append(x0 + i * sp)
            m["y"].append(y0 + j * sp)
            m["ocean"].append(1 if ch == "~" else 0)
    nb = []
    for j in range(ny):
        for i in range(nx):
            nb.append([jj * nx + ii for ii, jj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))
                       if 0 <= ii < nx and 0 <= jj < ny])
    return m, nb


class TestOpenSea(unittest.TestCase):
    def test_enclosed_sea_is_not_open(self):
        m, nb = grid_mesh(["~~~~~~",
                           "~.....",
                           "~.~~..",
                           "~.~~..",
                           "~.....",
                           "~~...."])
        sea = mpw_gen.open_sea(m, nb)
        self.assertEqual(sea[0], 1)
        self.assertEqual(sea[5 * 6 + 1], 1)
        for c in (2 * 6 + 2, 2 * 6 + 3, 3 * 6 + 2, 3 * 6 + 3):
            self.assertEqual(sea[c], 0)

    def test_child_without_border_sea_inherits_parent(self):
        # parent: open sea on the left half; child window shows only an inner bay
        pm, _ = grid_mesh(["~~~...", "~~~...", "~~~...", "~~~..."], sp=2.0)
        pmask = list(pm["ocean"])
        cm, cnb = grid_mesh(["....", ".~~.", ".~~.", "...."], sp=0.5, x0=3.0, y0=2.0)
        self.assertEqual(sum(mpw_gen.open_sea(cm, cnb)), 0)
        sea = mpw_gen.open_sea(cm, cnb, lambda: (pm, pmask))
        self.assertEqual(sum(sea), 4)
        # parent says the same water is enclosed: still not open
        self.assertEqual(sum(mpw_gen.open_sea(cm, cnb, lambda: (pm, [0] * len(pmask)))), 0)


class TestPortsGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-ports-")
        cls.world = os.path.join(cls.tmp, "w")
        cls.child = os.path.join(cls.tmp, "c")
        mpw_gen.gen_world(7, 1600, cls.world, raster_px=64)
        mpw_gen.gen_region(cls.world, None, 1600, cls.child, raster_px=64)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _sets(self, d):
        fe = mpw_gen.load(d, "features.geojson")["features"]
        return [f["properties"] for f in fe if f["properties"]["kind"] == "settlement"]

    def test_flags_match_open_sea_and_recipe(self):
        for d in (self.world, self.child):
            m = mpw_gen.load(d, "mesh.json")
            nb = mpw_gen._neighbours(m)
            sea = mpw_gen.open_sea_dir(d)
            sets = self._sets(d)
            self.assertTrue(sets)
            for s in sets:
                self.assertIn("port", s)
                touch = any(sea[q] for q in nb[s["cell"]])
                self.assertEqual(s["port"], touch)
            lake_only = [s for s in sets if any(m["lake"][q] >= 0 for q in nb[s["cell"]])
                         and not any(sea[q] for q in nb[s["cell"]])]
            self.assertTrue(all(not s["port"] for s in lake_only))
            rc = mpw_gen.load(d, "recipe.json")
            self.assertEqual(sorted(rc["ports"]), sorted(s["id"] for s in sets if s["port"]))

    def test_bar14_passes_and_catches_inland_port(self):
        for d in (self.world, self.child):
            b = {x[0]: x for x in mpw_gen.check(d, determinism=False)}
            self.assertTrue(b[14][2], b[14][3])
        bad = os.path.join(self.tmp, "bad")
        shutil.copytree(self.world, bad)
        m = mpw_gen.load(bad, "mesh.json")
        nb = mpw_gen._neighbours(m)
        sea = mpw_gen.open_sea_dir(bad)
        p = os.path.join(bad, "features.geojson")
        fc = mpw_gen.load(bad, "features.geojson")
        inland = None
        for f in fc["features"]:
            pr = f["properties"]
            if pr["kind"] == "settlement" and not any(sea[q] for q in nb[pr["cell"]]):
                pr["port"] = True
                inland = pr["id"]
                break
        self.assertIsNotNone(inland)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(fc, fh)
        rc = mpw_gen.load(bad, "recipe.json")
        rc["ports"] = sorted(rc["ports"] + [inland])
        with open(os.path.join(bad, "recipe.json"), "w", encoding="utf-8") as fh:
            json.dump(rc, fh)
        b = {x[0]: x for x in mpw_gen.check(bad, determinism=False)}
        self.assertFalse(b[14][2])

    def test_deterministic(self):
        again = os.path.join(self.tmp, "w2")
        mpw_gen.gen_world(7, 1600, again, raster_px=64)
        for fn in mpw_gen.FILES:
            with open(os.path.join(self.world, fn), "rb") as a, open(os.path.join(again, fn), "rb") as b:
                self.assertEqual(a.read(), b.read(), fn)


if __name__ == "__main__":
    unittest.main()
