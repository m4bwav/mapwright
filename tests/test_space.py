"""Tests for gen sector / system / planet / deck, their check bars and the planet and sector exports."""
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
import mpw_space as S  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def failed(bars):
    return [b for b in bars if b[-2] is False]


def named(bars, part):
    return [b for b in bars if part in b[-3]][0]


class SpaceBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-space-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def d(self, name):
        return os.path.join(self.tmp, name)

    def edit(self, d, name, fn):
        obj = P.load(d, name)
        fn(obj)
        P.dump(os.path.join(d, name), obj)


class TestSector(SpaceBase):
    def test_rendered_extra_file_does_not_fail_determinism(self):
        # Step E 2026-11-15: `render DIR -o DIR/map.png` left a PNG the gen never
        # writes, and the byte-identical bar failed on it.
        out = self.d("extra")
        S.gen_sector(5, out)
        with open(os.path.join(out, "map.png"), "wb") as f:
            f.write(b"not from gen")
        self.assertTrue(named(S.check(out, labels=False), "byte-identical")[-2])
        os.remove(os.path.join(out, "sources.json"))
        self.assertFalse(named(S.check(out, labels=False), "byte-identical")[-2])

    def test_subsector_bars_pass_and_regen(self):
        out = self.d("sub")
        r = S.gen_sector(3, out)
        self.assertGreater(r["worlds"], 20)
        bars = S.check(out)
        self.assertEqual(failed(bars), [], bars)
        self.assertTrue(named(bars, "byte-identical")[-2])
        self.assertTrue(named(bars, "route graph connected")[-2])
        self.assertTrue(named(bars, "T5 tab")[-2])

    def test_sector_sweep_connected(self):
        for seed in range(1, 4):
            for kw in (dict(size="sector"), dict(density=0.2, jump=1), dict(density=0.9, jump=4)):
                out = self.d("sw%d%s" % (seed, len(kw)))
                S.gen_sector(seed, out, **kw)
                self.assertEqual(failed(S.check(out, determinism=False, labels=False)), [], (seed, kw))

    def test_broken_graph_and_mislabel_fail(self):
        out = self.d("broken")
        S.gen_sector(5, out)
        sec = P.load(out, "sector.json")
        lone = sec["worlds"][0]["id"]
        self.edit(out, "sector.json", lambda s: s.__setitem__("routes", [e for e in s["routes"] if lone not in (e["a"], e["b"])]))
        self.assertFalse(named(S.check(out, False, False), "connected")[-2])
        S.gen_sector(5, out)
        self.edit(out, "sector.json", lambda s: s["routes"][0].__setitem__("kind", "long"))
        self.assertFalse(named(S.check(out, False, False), "jump routes")[-2])

    def test_t5_reader_by_header(self):
        text = "Name\tUWP\tHex\tZone\nAlpha\tA788899-C\t0101\t\nBeta\tX000000-0\t0203\tR\n"
        rows = S.read_t5_tab(text)
        self.assertEqual([(r["Hex"], r["Name"]) for r in rows], [("0101", "Alpha"), ("0203", "Beta")])
        with self.assertRaises(ValueError):
            S.read_t5_tab("Name\tZone\nA\t\n")

    def test_hex_distance(self):
        self.assertEqual(S.hex_dist((0, 0), (1, 0)), 1)
        self.assertEqual(S.hex_dist((1, 0), (2, 0)), 1)
        self.assertEqual(S.hex_dist((0, 0), (0, 3)), 3)
        self.assertEqual(S.hex_dist((0, 0), (4, 0)), 4)

    def test_real_stars_at_published_distances(self):
        out = self.d("real")
        S.gen_sector(1, out, real=True, radius_pc=8, jump=2.5)
        sec = P.load(out, "sector.json")
        by = {w["name"]: w for w in sec["worlds"]}
        self.assertAlmostEqual(by["Proxima Centauri"]["dist_pc"], 1.302, places=3)
        self.assertAlmostEqual(by["Sirius"]["dist_pc"], 2.637, places=3)
        bars = S.check(out)
        self.assertEqual(failed(bars), [], bars)
        self.edit(out, "sector.json", lambda s: s["worlds"][1]["xyz"].__setitem__(0, s["worlds"][1]["xyz"][0] + 0.01))
        self.assertFalse(named(S.check(out, False, False), "published distances")[-2])
        with open(os.path.join(out, "sources.json"), encoding="utf-8") as f:
            self.assertIn("Gaia", f.read())


class TestSystem(SpaceBase):
    def test_system_bars_sweep(self):
        for seed in range(1, 11):
            for star in (None, "M", "G", "F"):
                out = self.d("sys%d%s" % (seed, star))
                S.gen_system(seed, out, star)
                bars = S.check(out, determinism=seed == 1)
                self.assertEqual(failed(bars), [], (seed, star, bars))
        self.assertTrue(os.path.isfile(os.path.join(out, "orbits.svg")))

    def test_forced_failures(self):
        out = self.d("sysbad")
        S.gen_system(4, out, "G", 6)

        def squeeze(s):
            s["bodies"][1]["a_au"] = s["bodies"][0]["a_au"] * 1.001
        self.edit(out, "system.json", squeeze)
        self.assertFalse(named(S.check(out, False, False), "Hill radii apart")[-2])
        S.gen_system(4, out, "G", 6)
        giants = [b for b in P.load(out, "system.json")["bodies"] if b["moons"]]
        self.assertTrue(giants)

        def fling(s):
            for b in s["bodies"]:
                for m in b["moons"]:
                    m["a_au"] = b["a_au"]
        self.edit(out, "system.json", fling)
        self.assertFalse(named(S.check(out, False, False), "Hill sphere")[-2])


class TestPlanet(SpaceBase):
    def test_every_kind_passes(self):
        for i, kind in enumerate(S.PLANET_KINDS):
            out = self.d("pl-" + kind)
            S.gen_planet(i + 1, out, kind, 512)
            bars = S.check(out, determinism=kind in ("moon", "gas"))
            self.assertEqual(failed(bars), [], (kind, bars))
        self.assertTrue(named(S.check(self.d("pl-moon"), False, False), "crater sizes")[-2])

    def test_uv_sampling_fails_seam_and_pole(self):
        out = self.d("pl-uv")
        S.gen_planet(1, out, "rocky", 512, sampling="uv")
        bars = S.check(out, False, False)
        self.assertFalse(named(bars, "seam")[-2])
        self.assertFalse(named(bars, "pinch")[-2])

    def test_small_width_refused_and_png_decoder(self):
        with self.assertRaises(ValueError):
            S.gen_planet(1, self.d("tiny"), "rocky", 256)
        png = S.G.png_bytes(3, 2, [bytearray([1, 2, 3, 4, 5, 6, 7, 8, 9]), bytearray([9, 8, 7, 6, 5, 4, 3, 2, 1])], 8, 2)
        w, h, px = S.decode_png(png)
        self.assertEqual((w, h), (3, 2))
        self.assertEqual(px[1][0], (9, 8, 7))

    def test_export_sphere_png(self):
        out = self.d("pl-exp")
        S.gen_planet(2, out, "ocean", 512)
        dst = self.d("ocean.png")
        txt = run_cli("export", out, "-o", dst)
        self.assertIn("PASS: planet: no seam", txt)
        with open(self.d("ocean.sphere.json"), encoding="utf-8") as f:
            note = json.load(f)
        self.assertIn("threewright", note["plugins"])
        with open(dst, "rb") as f:
            self.assertEqual(P.png_size(f.read(32)), (512, 256))


class TestDeck(SpaceBase):
    def test_deck_bars_sweep(self):
        for seed in range(1, 9):
            for kw in ({}, dict(w=60, h=25, decks=3), dict(w=30, h=30, decks=2, hull="station"), dict(w=16, h=11, decks=1)):
                out = self.d("dk%d%d" % (seed, len(kw)))
                S.gen_deck(seed, out, **kw)
                bars = S.check(out, determinism=seed == 1)
                self.assertEqual(failed(bars), [], (seed, kw, bars))

    def test_forced_failures(self):
        out = self.d("dkbad")
        S.gen_deck(2, out)
        dj = P.load(out, "deck.json")
        rm = [r for r in dj["rooms"] if not r.get("outer")][0]

        def wall_off(d):
            x, y = rm["door"]
            row = d["decks"][rm["deck"]][y]
            d["decks"][rm["deck"]][y] = row[:x] + "#" + row[x + 1:]
        self.edit(out, "deck.json", wall_off)
        self.assertFalse(named(S.check(out, False, False), "every room reached")[-2])
        S.gen_deck(2, out)

        def move_lift(d):
            x, y = d["lift"]
            row = d["decks"][1][y]
            d["decks"][1][y] = row[:x] + ".L" + row[x + 2:]
        self.edit(out, "deck.json", move_lift)
        self.assertFalse(named(S.check(out, False, False), "lifts line up")[-2])
        S.gen_deck(2, out)

        def seal(d):
            al = [r for r in d["rooms"] if r.get("outer")][0]
            x, y = al["outer"]
            row = d["decks"][al["deck"]][y]
            d["decks"][al["deck"]][y] = row[:x] + "#" + row[x + 1:]
        self.edit(out, "deck.json", seal)
        self.assertFalse(named(S.check(out, False, False), "outer door")[-2])


class TestCli(SpaceBase):
    def test_cli_gen_check_render_export(self):
        out = self.d("cli-sec")
        self.assertIn("worlds", run_cli("gen", "sector", "--seed", "2", "--out", out))
        bars = json.loads(run_cli("check", out, "--json"))
        self.assertTrue(all(b["ok"] is not False for b in bars))
        tab = self.d("cli.tab")
        self.assertIn("PASS: T5 tab", run_cli("export", out, "-o", tab))
        sysd = self.d("cli-sys")
        run_cli("gen", "system", "--seed", "2", "--star", "K", "--out", sysd)
        svg = self.d("cli-scale.svg")
        run_cli("render", sysd, "--view", "scale", "-o", svg)
        with open(svg, encoding="utf-8") as f:
            self.assertIn("to scale", f.read())
        deck = self.d("cli-deck")
        self.assertIn("rooms", run_cli("gen", "deck", "--seed", "2", "--decks", "1", "--out", deck))
        with self.assertRaises(SystemExit):
            run_cli("export", sysd, "-o", self.d("x.png"))


if __name__ == "__main__":
    unittest.main()
