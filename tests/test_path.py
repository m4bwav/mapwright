"""Tests for path, path --field, travel and check --chokepoints/--fair (scripts/mpw_path.py)."""
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw  # noqa: E402
import mpw_path as M  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def read(d, name):
    with open(os.path.join(d, name), "rb") as f:
        return f.read()


def pairs(G, k, seed=7):
    r = random.Random(seed)
    return [(r.choice(G.nodes), r.choice(G.nodes)) for _ in range(k)]


def fake_mesh(xs, ys, hs, edges):
    n = len(xs)
    m = dict(x=xs, y=ys, h=hs, ocean=[False] * n, lake=[-1] * n, biome=[0] * n, river=[False] * n, acc=[0] * n)
    nb = [set() for _ in range(n)]
    for a, b in edges:
        nb[a].add(b)
        nb[b].add(a)
    return M.MeshGraph(m, nb, 20, [0, 0, 1000, 1000], cost="walk")


def square(rows):
    return M.SquareGraph(dict(w=len(rows[0]), h=len(rows), cells=rows), 10)


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-path-")
        cls.d = {}
        for name, args in (("bsp", ("dungeon", "--seed", "4", "--w", "30", "--h", "24")),
                           ("cyclic", ("dungeon", "--seed", "5", "--method", "cyclic")),
                           ("cave", ("dungeon", "--seed", "6", "--method", "cave", "--w", "30", "--h", "24")),
                           ("battle", ("battle", "--seed", "2", "--w", "20", "--h", "16")),
                           ("hex", ("battle", "--seed", "2", "--grid", "hex", "--w", "16", "--h", "14")),
                           ("deck", ("deck", "--seed", "3", "--w", "30", "--h", "15")),
                           ("world", ("world", "--seed", "2", "--cells", "500"))):
            out = os.path.join(cls.tmp, name)
            run_cli("gen", *args, "--out", out)
            cls.d[name] = out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class PathBars(Fixtures):
    def test_astar_equals_dijkstra_and_resum(self):
        n = 0
        for name in ("bsp", "cyclic", "cave", "battle", "hex", "deck", "world"):
            G, _ = M.build(self.d[name])
            for a, b in pairs(G, 60):
                c1, p1, _ = M.search(G, a, [b])
                c0, _, _ = M.search(G, a, [b], heuristic=False)
                if c0 is None:
                    self.assertIsNone(c1, name)
                    continue
                self.assertAlmostEqual(c1, c0, delta=1e-9, msg=name)
                self.assertAlmostEqual(M.resum(G, p1), c1, delta=1e-9, msg=name)
                self.assertEqual((p1[0], p1[-1]), (a, b))
                n += 1
        self.assertGreater(n, 300)

    def test_astar_expands_fewer_than_dijkstra(self):
        G, _ = M.build(self.d["bsp"])
        a1 = a0 = 0
        for a, b in pairs(G, 40):
            a1 += M.search(G, a, [b])[2]
            a0 += M.search(G, a, [b], heuristic=False)[2]
        self.assertLess(a1, a0)

    def test_no_wall_crossing_or_cut_corner(self):
        for name in ("bsp", "cave", "battle"):
            G, _ = M.build(self.d[name])
            g = G.g
            for a, b in pairs(G, 60):
                _, p, _ = M.search(G, a, [b])
                for (x0, y0), (x1, y1) in zip(p or [], (p or [])[1:]):
                    self.assertIn(g[y1][x1], ".+")
                    self.assertLessEqual(max(abs(x1 - x0), abs(y1 - y0)), 1)
                    if x1 != x0 and y1 != y0:
                        self.assertEqual(g[y0][x1] + g[y1][x0], "..", name)
                        self.assertNotIn("+", g[y0][x0] + g[y1][x1])

    def test_hand_grids(self):
        G = square([".#", "#."])
        self.assertIsNone(M.search(G, (0, 0), [(1, 1)])[0])          # no squeezing between two walls
        G = square(["...", "...", "..."])
        self.assertAlmostEqual(M.search(G, (0, 0), [(2, 2)])[0], 2 * math.sqrt(2), delta=1e-12)
        G = M.SquareGraph(dict(w=3, h=3, cells=["...", "...", "..."]), 10, moves=4)
        self.assertEqual(M.search(G, (0, 0), [(2, 2)])[0], 4.0)

    def test_symmetric_where_undirected(self):
        for name in ("bsp", "cave", "battle", "hex", "deck"):
            G, _ = M.build(self.d[name])
            self.assertFalse(G.directed, name)
            for a, b in pairs(G, 30):
                c1, c2 = M.search(G, a, [b])[0], M.search(G, b, [a])[0]
                self.assertAlmostEqual(c1, c2, delta=1e-9, msg=name)

    def test_one_way_doors_entered_from_source_side_only(self):
        G, _ = M.build(self.d["cyclic"])
        self.assertTrue(G.rule, "fixture has no one-way door")
        for a, b in pairs(G, 200):
            _, p, _ = M.search(G, a, [b])
            for u, v in zip(p or [], (p or [])[1:]):
                if v in G.rule:
                    self.assertEqual((u[0] - v[0], u[1] - v[1]), G.rule[v])

    def test_cli_files_and_byte_identical(self):
        d = self.d["bsp"]
        gj = json.loads(read(d, "grid.json"))
        o1, o2 = os.path.join(self.tmp, "p1"), os.path.join(self.tmp, "p2")
        args = ["--from", "%d,%d" % tuple(gj["entrance"]), "--to", "%d,%d" % tuple(gj["goal"])]
        run_cli("path", d, *args, "--out", o1)
        run_cli("path", d, *args, "--out", o2)
        for f in ("path.json", "path.geojson", "path.svg"):
            self.assertEqual(read(o1, f), read(o2, f), f)
        rep = json.loads(read(o1, "path.json"))
        self.assertIn('class="path"', read(o1, "path.svg").decode())
        self.assertEqual(len(rep["path"]), rep["steps"] + 1)

    def test_world_cli_and_city_refused(self):
        G, _ = M.build(self.d["world"])
        a, b = G.nodes[0], G.nodes[-1]
        out = os.path.join(self.tmp, "pw")
        try:
            run_cli("path", self.d["world"], "--from", "%f,%f" % tuple(G.xy(a)), "--to", "%f,%f" % tuple(G.xy(b)),
                    "--out", out)
            self.assertTrue(os.path.isfile(os.path.join(out, "path.svg")))
        except SystemExit as e:
            self.assertEqual(e.code, 1)      # different landmasses
        city = os.path.join(self.tmp, "city")
        run_cli("gen", "city", "--seed", "1", "--out", city)
        with self.assertRaises(ValueError):
            M.build(city)


class FieldBars(Fixtures):
    def check_field(self, G, goals, every=1):
        dist, flow = M.field(G, goals)
        for n in G.nodes[::every]:
            c = M.search(G, n, goals, heuristic=False)[0]
            if c is None:
                self.assertNotIn(n, dist)
                continue
            self.assertAlmostEqual(dist[n], c, delta=1e-9)
            if n in goals:
                continue
            self.assertLess(dist[flow[n]], dist[n])
            tot, cur, k = 0.0, n, 0
            while cur not in goals:
                tot += [cc for m, cc in G.out(cur) if m == flow[cur]][0]
                cur = flow[cur]
                k += 1
                self.assertLess(k, len(G.nodes))
            self.assertAlmostEqual(tot, dist[n], delta=1e-9)
        return dist

    def test_field_all_cells_small(self):
        G, _ = M.build(self.d["bsp"])
        self.check_field(G, [G.nodes[0]])
        G, _ = M.build(self.d["hex"])
        self.check_field(G, [G.nodes[0], G.nodes[-1]])

    def test_field_directed_world_and_null(self):
        G, _ = M.build(self.d["world"])
        dist = self.check_field(G, [G.nodes[len(G.nodes) // 2]], every=3)
        self.assertLess(len(dist), len(G.nodes), "fixture should have unreachable land")
        out = os.path.join(self.tmp, "fw")
        rep = M.field_files(self.d["world"], out, G, [G.nodes[0]], *M.field(G, [G.nodes[0]]))
        nulls = [c for c in rep["cells"] if c["value"] is None]
        self.assertEqual(len(nulls), rep["unreachable"])
        self.assertTrue(all(c["next"] is None for c in nulls))


class TravelBars(Fixtures):
    def test_tobler_table(self):
        table = {-0.40: 1.76, -0.20: 3.55, -0.10: 5.04, -0.05: 6.00, 0: 5.04, 0.05: 4.23, 0.10: 3.55,
                 0.20: 2.50, 0.40: 1.24}
        for s, v in table.items():
            self.assertAlmostEqual(M.tobler_kmh(s), v, delta=0.005 + 1e-9)
        self.assertAlmostEqual(M.TOBLER_FLAT, 5.037, delta=0.001)

    def test_flat_leg(self):
        G = fake_mesh([0, 1.5, 3.0, 4.5, 6.0], [0] * 5, [0.1] * 5, [(i, i + 1) for i in range(4)])
        dist, _ = M.dijkstra(G.out, [0])
        self.assertAlmostEqual(dist[4], 6.0 / M.TOBLER_FLAT, delta=1e-6)
        self.assertAlmostEqual(M.TOBLER_FLAT, 5.036742, delta=1e-6)          # 5.037 is this rounded
        back, _ = M.dijkstra(G.out, [4])
        self.assertAlmostEqual(back[0], dist[4], delta=1e-12)

    def test_slope_directed(self):
        G = fake_mesh([0, 1.0], [0, 0], [0.0, 0.05], [(0, 1)])          # 150 m rise over 1 km
        up, down = M.search(G, 0, [1])[0], M.search(G, 1, [0])[0]
        self.assertGreater(up, down)
        self.assertAlmostEqual(up, 1.0 / M.tobler_kmh(0.15), delta=1e-12)

    def test_world_travel_tree_and_cli(self):
        G, _ = M.build(self.d["world"], cost="walk")
        dist, prev = M.dijkstra(G.out, [G.nodes[0]])
        self.assertTrue(all(dist[prev[n]] <= dist[n] for n in prev))
        asym = sum(1 for a, b in pairs(G, 40) if (M.search(G, a, [b])[0] or 0) != (M.search(G, b, [a])[0] or 0))
        self.assertGreater(asym, 0)
        out = os.path.join(self.tmp, "tw")
        x, y = G.xy(G.nodes[0])
        run_cli("travel", self.d["world"], "--from", "%f,%f" % (x, y), "--out", out)
        rep = json.loads(read(out, "travel.json"))
        self.assertEqual(sum(rep["bands"]), rep["reachable"])
        self.assertEqual(rep["reachable"] + rep["unreachable"], len(G.nodes))


class CheckBars(Fixtures):
    def test_articulation_equals_brute_force(self):
        for name in ("bsp", "cave", "battle", "hex", "deck", "cyclic"):
            G, _ = M.build(self.d[name])
            adj = G.undirected_adj()
            aps, _ = M.articulation(adj)
            self.assertEqual(aps, M.brute_articulation(adj), name)

    def test_hand_ring_and_corridor(self):
        G = square(["#####", "#...#", "#.#.#", "#...#", "#####"])          # a ring: no chokepoint
        self.assertEqual(M.articulation(G.undirected_adj())[0], [])
        G = M.SquareGraph(dict(w=7, h=3, cells=["..#####", ".......", "..#####"]), 10)
        aps, br = M.articulation(G.undirected_adj())
        self.assertEqual(aps, [(x, 1) for x in range(1, 6)])
        rep = M.chokepoints(G, (), (0, 0), (6, 1))
        self.assertEqual(rep["min_cut"]["size"], 1)
        self.assertEqual({r["cut_off"] for r in rep["chokepoints"]}, {1, 2, 3, 4, 5})

    def test_removing_chokepoint_cuts(self):
        G, _ = M.build(self.d["bsp"])
        adj = G.undirected_adj()
        base = len(M.components(adj))
        aps = set(M.articulation(adj)[0])
        for n in G.nodes:
            self.assertEqual(len(M.components(adj, frozenset([n]))) > base, n in aps)

    def test_cli_chokepoints_and_fair(self):
        d = self.d["bsp"]
        out = run_cli("check", d, "--chokepoints", "--fair", "--json")
        rep = json.loads(out)
        ch, fa = rep["chokepoints"], rep["fair"]
        self.assertTrue(ch["brute_force_equal"])
        self.assertEqual(sum(fa["areas"]) + fa["tied"] + fa["unreached"], fa["passable"])
        G, _ = M.build(d)
        for i, s in enumerate(fa["starts"]):
            sn = (int(s[0]), int(s[1]))
            for r in fa["resources"]:
                c = M.search(G, sn, [(int(r["cell"][0]), int(r["cell"][1]))], heuristic=False)[0]
                self.assertAlmostEqual(r["dist"][i], c, delta=1e-9)
        a1 = read(d, "fair.json")
        run_cli("check", d, "--fair", "--json")
        self.assertEqual(a1, read(d, "fair.json"))


if __name__ == "__main__":
    unittest.main()
