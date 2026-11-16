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


def gen(tmp, name, *args):
    out = os.path.join(tmp, name)
    run_cli("gen", *args, "--out", out)
    return out


class LocksAndKeys(unittest.TestCase):
    """Backlog: path honours locks and keys on cyclic dungeons (30-seed sweep)."""
    SEEDS = range(1, 31)

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-lock-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_sweep_key_before_lock(self):
        found = 0
        for seed in self.SEEDS:
            d = gen(self.tmp, "c%d" % seed, "dungeon", "--seed", str(seed), "--method", "cyclic")
            G, _ = M.build(d)
            gj = json.loads(read(d, "grid.json"))
            ent, goal = tuple(gj["entrance"]), tuple(gj["goal"])
            self.assertTrue(G.lockdoor and G.keycell, seed)
            for c in G.keycell:
                self.assertIn(c, G.ok, seed)
            cost, path, picks, _ = M.lock_search(G, ent, goal)
            self.assertIsNotNone(cost, "seed %d: no lock-aware path" % seed)
            self.assertEqual((path[0], path[-1]), (ent, goal))
            self.assertAlmostEqual(M.resum(G, path), cost, delta=1e-9)
            held, order = set(), []
            for c in path:
                if c in G.lockdoor:
                    self.assertIn(G.lockdoor[c], held, "seed %d: lock crossed before its key" % seed)
                if c in G.keycell and G.keycell[c] not in held:
                    held.add(G.keycell[c])
                    order.append(G.keycell[c])
            self.assertEqual([p["key"] for p in picks], order)
            for p in picks:
                self.assertEqual(G.keycell.get(path[p["step"]]), p["key"])
            for u, v in zip(path, path[1:]):
                if v in G.rule:
                    self.assertEqual((u[0] - v[0], u[1] - v[1]), G.rule[v], seed)
            free = M.search(G, ent, [goal])[0]
            self.assertLessEqual(free, cost + 1e-9, seed)
            found += 1
        self.assertGreaterEqual(found, 30)

    def test_cli_reports_keys_and_ignore_locks(self):
        d = gen(self.tmp, "cli", "dungeon", "--seed", "5", "--method", "cyclic")
        gj = json.loads(read(d, "grid.json"))
        fr, to = "%d,%d" % tuple(gj["entrance"]), "%d,%d" % tuple(gj["goal"])
        rep = json.loads(run_cli("path", d, "--from", fr, "--to", to, "--json"))
        self.assertEqual(rep["locks"], 1)
        self.assertEqual([k["key"] for k in rep["keys"]], ["k1"])
        free = json.loads(run_cli("path", d, "--from", fr, "--to", to, "--ignore-locks", "--json"))
        self.assertEqual(free["locks_open"], 1)
        self.assertLessEqual(free["cost"], rep["cost"])
        jp = json.loads(run_cli("path", d, "--from", fr, "--to", to, "--ignore-locks", "--jps", "--json"))
        self.assertAlmostEqual(jp["cost"], free["cost"], delta=1e-9)
        self.assertEqual(jp["search"], "jps")
        with self.assertRaises(SystemExit):
            run_cli("path", d, "--from", fr, "--to", to, "--jps")


class JumpPoints(unittest.TestCase):
    """Backlog: path --jps returns A*'s cost on 48 generated grid maps; expansions recorded for both."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-jps-")
        cls.maps = []
        for seed in range(1, 13):
            cls.maps.append(gen(cls.tmp, "b%d" % seed, "dungeon", "--seed", str(seed), "--w", "48", "--h", "36"))
            cls.maps.append(gen(cls.tmp, "v%d" % seed, "dungeon", "--seed", str(seed), "--method", "cave",
                                "--w", "48", "--h", "36"))
            cls.maps.append(gen(cls.tmp, "y%d" % seed, "dungeon", "--seed", str(seed), "--method", "cyclic"))
            cls.maps.append(gen(cls.tmp, "t%d" % seed, "battle", "--seed", str(seed), "--w", "40", "--h", "30"))
        cls.maps.append(gen(cls.tmp, "hex", "battle", "--seed", "2", "--grid", "hex", "--w", "16", "--h", "14"))
        cls.maps.append(gen(cls.tmp, "deck", "deck", "--seed", "3", "--w", "30", "--h", "15"))
        cls.maps.append(gen(cls.tmp, "world", "world", "--seed", "2", "--cells", "500"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_same_cost_as_astar(self):
        import time
        stats = dict(maps=0, pairs=0, astar_exp=0, jps_exp=0, astar_s=0.0, jps_s=0.0)
        for d in self.maps[:-3]:
            G, _ = M.build(d)
            stats["maps"] += 1
            for a, b in pairs(G, 25, seed=stats["maps"]):
                t0 = time.perf_counter()
                c1, _, e1 = M.search(G, a, [b])
                t1 = time.perf_counter()
                c2, p2, e2 = M.jps(G, a, b)
                t2 = time.perf_counter()
                if c1 is None:
                    self.assertIsNone(c2, d)
                    continue
                self.assertAlmostEqual(c1, c2, delta=1e-9, msg="%s %r %r" % (d, a, b))
                self.assertAlmostEqual(M.resum(G, p2), c2, delta=1e-9)
                self.assertEqual((p2[0], p2[-1]), (a, b))
                stats["pairs"] += 1
                stats["astar_exp"] += e1
                stats["jps_exp"] += e2
                stats["astar_s"] += t1 - t0
                stats["jps_s"] += t2 - t1
        self.assertGreaterEqual(stats["maps"], 48)
        self.assertGreater(stats["pairs"], 1000)
        self.assertLess(stats["jps_exp"], stats["astar_exp"])
        if os.environ.get("MPW_JPS_STATS"):
            print("JPS stats:", json.dumps(stats))

    def test_hand_grid_open_room(self):
        G = square(["." * 20] * 20)
        c1, _, e1 = M.search(G, (0, 0), [(19, 13)])
        c2, _, e2 = M.jps(G, (0, 0), (19, 13))
        self.assertAlmostEqual(c1, c2, delta=1e-12)
        self.assertLess(e2, e1)

    def test_refusals(self):
        for d in self.maps[-3:]:
            G, _ = M.build(d)
            self.assertIsNotNone(M.jps_refusal(G))
            with self.assertRaises(ValueError):
                M.jps(G, G.nodes[0], G.nodes[-1])
        G4, _ = M.build(self.maps[0], moves=4)
        self.assertIn("--moves 4", M.jps_refusal(G4))
        with self.assertRaises(SystemExit):
            run_cli("path", self.maps[-3], "--from", "1,1", "--to", "2,2", "--jps")
        self.assertIn("references/pathfinding.md", run_cli("explain", "jps"))
        self.assertIn("references/pathfinding.md", run_cli("explain", "locks"))
        self.assertIn("references/games-film-print.md", run_cli("explain", "navmesh"))


class AgentBars(Fixtures):
    def test_hand_corridor(self):
        rows = ["#######", "#.....#", "#.....#", "###.###", "#.....#", "#.....#", "#######"]
        g = M.erode(rows, 7, 7, 2)
        G = M.SquareGraph(dict(w=7, h=7, cells=g), 10)
        self.assertIsNone(M.search(G, (1, 1), [(1, 4)])[0])  # one-square gap blocks a 2-wide body
        rows[3] = "###..##"
        G = M.SquareGraph(dict(w=7, h=7, cells=M.erode(rows, 7, 7, 2)), 10)
        self.assertIsNotNone(M.search(G, (1, 1), [(1, 4)])[0])

    def test_body_fits_every_step_and_agent1_identical(self):
        for name in ("bsp", "cave", "battle"):
            d = self.d[name]
            G1, _ = M.build(d)
            self.assertEqual(getattr(G1, "agent", 1), 1)
            G2, _ = M.build(d, agent=2)
            gj = json.load(open(os.path.join(d, "grid.json"), encoding="utf-8"))
            c = gj["cells"]
            for s, t in pairs(G2, 20):
                cost, path, _ = M.search(G2, s, [t])
                if cost is None:
                    continue
                c1 = M.search(G1, s, [t])[0]
                self.assertGreaterEqual(cost + 1e-9, c1)
                for x, y in path:
                    for yy in (y, y + 1):
                        for xx in (x, x + 1):
                            self.assertIn(c[yy][xx], ".+", (name, x, y))

    def test_cli_and_refusals(self):
        d = self.d["battle"]
        G2, _ = M.build(d, agent=2)
        s = G2.nodes[0]
        dist = M.dijkstra(G2.out, [s])[0]
        t = max(dist, key=lambda n: (dist[n], n))
        o = os.path.join(self.tmp, "ag")
        out = run_cli("path", d, "--from", "%d,%d" % s, "--to", "%d,%d" % t, "--agent", "2", "--out", o, "--json")
        self.assertEqual(json.loads(out).get("agent", {}).get("squares", 2), 2)
        for args in (("--agent", "0"),):
            with self.assertRaises(SystemExit):
                run_cli("path", d, "--from", "%d,%d" % s, "--to", "%d,%d" % t, *args)
        for name in ("hex", "deck", "world"):
            with self.assertRaises(ValueError):
                M.build(self.d[name], agent=2)


if __name__ == "__main__":
    unittest.main()