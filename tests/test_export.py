"""Tests for `export`: engine heightmaps, Tiled maps, deck plans to Universal VTT, hex battle PNG, terrain mesh,
print-ready PDF and PNG. Each proof reads the written file back with code that does not share the writer."""
import base64
import io
import json
import math
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw  # noqa: E402
import mpw_export as X  # noqa: E402
import mpw_gen as G  # noqa: E402
import mpw_places as P  # noqa: E402
import mpw_space as S  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def cli_fails(*args):
    err = io.StringIO()
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            mpw.main(list(args))
    except SystemExit as e:
        return e.code, err.getvalue()
    return 0, err.getvalue()


def rb(path):
    with open(path, "rb") as f:
        return f.read()


def failed(bars):
    return [b for b in bars if b[1] is False]


def recipe_metres(d):
    """Recipe heights in metres, read with mpw's own range reader as a cross-check of the PNG decoder."""
    with open(os.path.join(d, "heights.png"), "rb") as f:
        w, h, depth, rows = X.read_png_grey(f.read())
    lo, hi = mpw.png_grey_range(os.path.join(d, "heights.png"))
    assert depth == 16 and lo == min(map(min, rows)) and hi == max(map(max, rows))
    return [[v - G.PNG_OFFSET for v in r] for r in rows]


def sample(src, n, i, vertex):
    """Position of output sample i of n along one source axis, as (index, fraction): written apart from the
    exporter so the test does not reuse its arithmetic."""
    sn = len(src)
    t = i / (n - 1) if vertex else (i + 0.5) / n
    u = t * sn - 0.5
    u = 0.0 if u < 0 else (sn - 1.0 if u > sn - 1 else u)
    k = int(math.floor(u))
    if k > sn - 2:
        k = sn - 2
    return k, u - k


def expect(src, nw, nh, i, j, vertex):
    cx, fx = sample(src[0], nw, i, vertex)
    cy, fy = sample(src, nh, j, vertex)
    top = src[cy][cx] + (src[cy][cx + 1] - src[cy][cx]) * fx
    bot = src[cy + 1][cx] + (src[cy + 1][cx + 1] - src[cy + 1][cx]) * fx
    return top + (bot - top) * fy


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-export-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def d(self, name):
        return os.path.join(self.tmp, name)


class TestHeightmaps(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.world = os.path.join(cls.tmp, "w.map")
        run_cli("gen", "world", "--seed", "7", "--cells", "1600", "--raster", "128", "--out", cls.world)
        cls.src = recipe_metres(cls.world)
        cls.region = os.path.join(cls.tmp, "r.map")
        run_cli("gen", "region", "--parent", cls.world, "--window", "200,300,700,600", "--cells", "1600",
                "--raster", "100", "--out", cls.region)

    def side(self, out):
        with open(os.path.splitext(out)[0] + ".import.json", encoding="utf-8") as f:
            return json.load(f)

    def worst(self, back, side, src, vertex):
        nw, nh = side["size"]
        lo, step = side["min_m"], side["metres_per_step"]
        w = 0.0
        for j in range(nh):
            for i in range(nw):
                w = max(w, abs(lo + back[j][i] * step - expect(src, nw, nh, i, j, vertex)))
        return w

    def test_unity_raw(self):
        out = self.d("u.raw")
        bars, files = X.export(self.world, out, None, "t")
        self.assertEqual(failed(bars), [])
        sd = self.side(out)
        self.assertEqual(sd["size"], [129, 129])                    # smallest 2^n + 1 at or above the 128 px raster
        self.assertEqual(os.path.getsize(out), 129 * 129 * 2)       # no header, 16 bit
        with open(out, "rb") as f:
            raw = f.read()
        back = [list(struct.unpack("<129H", raw[j * 258:(j + 1) * 258])) for j in range(129)]
        self.assertEqual(min(map(min, back)), 0)
        self.assertEqual(max(map(max, back)), 65535)
        w = self.worst(back, sd, self.src, True)
        self.assertLessEqual(w, sd["metres_per_step"])              # proof bar: one quantisation step
        self.assertLessEqual(w, sd["metres_per_step"] * 0.5 + 1e-6)  # measured: half a step
        self.assertEqual(sd["import"]["resolution"], 129)
        self.assertEqual(sd["import"]["depth"], "Bit 16")
        self.assertAlmostEqual(sd["metres_per_pixel"][0], 1000000.0 / 128, places=3)
        self.assertAlmostEqual(sd["import"]["terrain_size_m"]["y"], sd["max_m"] - sd["min_m"], places=2)
        self.assertEqual(sd["import"]["fit"]["scale"], "1:10")      # 1000 km is past Unity's 100 km

    def test_unity_sizes_and_orientation(self):
        out = self.d("u513.raw")
        bars, _ = X.export(self.world, out, "unity", "t", size=513)
        self.assertEqual(failed(bars), [])
        self.assertEqual(os.path.getsize(out), 513 * 513 * 2)
        with self.assertRaises(ValueError):
            X.export(self.world, self.d("bad.raw"), "unity", "t", size=512)
        with self.assertRaises(ValueError):
            X.export(self.world, self.d("bad.png"), "unity", "t")
        # orientation on an asymmetric map: the first row of the file is the north row unless --flip
        a, b = self.d("n.raw"), self.d("s.raw")
        X.export(self.world, a, "unity", "t", size=129)
        X.export(self.world, b, "unity", "t", size=129, flip=True)
        ra, rb_ = rb(a), rb(b)
        self.assertNotEqual(ra[:258], ra[-258:])
        self.assertEqual(ra[:258], rb_[-258:])
        self.assertEqual(ra[-258:], rb_[:258])
        sd = self.side(a)
        north = [expect(self.src, 129, 129, i, 0, True) for i in range(129)]
        got = [sd["min_m"] + v * sd["metres_per_step"] for v in struct.unpack("<129H", ra[:258])]
        self.assertLess(max(abs(p - q) for p, q in zip(north, got)), sd["metres_per_step"])
        self.assertEqual(self.side(b)["row_order"], "south first")

    def test_unreal_png16(self):
        out = self.d("ue.png")
        bars, _ = X.export(self.world, out, "unreal", "t")
        self.assertEqual(failed(bars), [])
        hdr = mpw.png_header(out)
        self.assertEqual((hdr["width"], hdr["height"], hdr["bit_depth"], hdr["colour"]), (253, 253, 16, "greyscale"))
        sd = self.side(out)
        with open(out, "rb") as f:
            back = X.read_png_grey(f.read())[3]
        self.assertLessEqual(self.worst(back, sd, self.src, True), sd["metres_per_step"] * 0.5 + 1e-6)
        imp = sd["import"]
        rng = sd["max_m"] - sd["min_m"]
        # Unreal: height in cm = (value - 32768) / 128 x Z scale; the two ends must land on min and max
        z0 = imp["location_z_cm"] + (0 - 32768) / 128.0 * imp["scale"]["z"]
        z1 = imp["location_z_cm"] + (65535 - 32768) / 128.0 * imp["scale"]["z"]
        self.assertAlmostEqual(z0 / 100.0, sd["min_m"], delta=0.01)
        self.assertAlmostEqual(z1 / 100.0, sd["max_m"], delta=0.01)
        self.assertAlmostEqual(imp["scale"]["x"], 1000000.0 / 252 * 100, delta=0.01)
        self.assertGreater(rng, 1000)
        bars, _ = X.export(self.world, self.d("ue1009.png"), "unreal", "t", size=1009)
        self.assertEqual(failed(bars), [])
        self.assertEqual(mpw.png_header(self.d("ue1009.png"))["width"], 1009)
        with self.assertRaises(ValueError):
            X.export(self.world, self.d("ue1000.png"), "unreal", "t", size=1000)

    def test_godot_identity_and_r16(self):
        out = self.d("g.r16")
        bars, _ = X.export(self.world, out, None, "t")
        self.assertEqual(failed(bars), [])
        sd = self.side(out)
        self.assertEqual(sd["size"], [128, 128])
        back = X.read_heightmap(out, 128, 128)
        # same size as the recipe raster: the resample is the identity, so every height is within half a step
        w = max(abs(sd["min_m"] + back[j][i] * sd["metres_per_step"] - self.src[j][i])
                for j in range(128) for i in range(128))
        self.assertLessEqual(w, sd["metres_per_step"] * 0.5 + 1e-6)
        self.assertLess(sd["metres_per_step"], 1.0)                 # finer than the recipe's 1 m steps
        self.assertEqual(sd["import"]["terrain3d"]["r16_size"], [128, 128])
        bars, _ = X.export(self.world, self.d("g.png"), "godot", "t")
        self.assertEqual(failed(bars), [])
        self.assertEqual(mpw.png_header(self.d("g.png"))["bit_depth"], 16)

    def test_roblox_heightmap_and_colormap(self):
        out = self.d("rb.png")
        bars, files = X.export(self.world, out, "roblox", "t")
        self.assertEqual(failed(bars), [])
        self.assertEqual([os.path.basename(f) for f in files], ["rb.png", "rb.colormap.png", "rb.import.json"])
        sd = self.side(out)
        self.assertEqual((sd["bits"], sd["size"]), (8, [128, 128]))
        with open(out, "rb") as f:
            back = X.read_png_grey(f.read())[3]
        self.assertLessEqual(self.worst(back, sd, self.src, False), sd["metres_per_step"] * 0.5 + 1e-6)
        w, h, rows = S.decode_png(rb(self.d("rb.colormap.png")))
        self.assertEqual((w, h), (128, 128))
        table = {tuple(v) for v in X.ROBLOX_MATERIALS.values()}
        used = {px for r in rows for px in r}
        self.assertTrue(used <= table)
        self.assertGreaterEqual(len(used), 3)
        # sea and lake beds are Mud; every other pixel is land (heights at or above sea level, within a pixel)
        mud = tuple(X.ROBLOX_MATERIALS["Mud"])
        sea = sum(1 for j in range(h) for i in range(w) if self.src[j][i] < 0)
        muds = sum(1 for r in rows for px in r if px == mud)
        self.assertLess(abs(muds - sea) / float(w * h), 0.03)
        self.assertEqual(set(X.BIOME_MATERIAL), {b[0] for b in G.BIOMES})
        with self.assertRaises(ValueError):
            X.export(self.world, self.d("big.png"), "roblox", "t", size=5000)
        bars, _ = X.export(self.world, self.d("rb16.png"), "roblox", "t", size=300, bits=16)
        self.assertEqual(failed(bars), [])
        self.assertEqual(mpw.png_header(self.d("rb16.png"))["bit_depth"], 16)

    def test_region_not_square(self):
        src = recipe_metres(self.region)
        self.assertEqual((len(src[0]), len(src)), (100, 60))
        out = self.d("r.raw")
        bars, _ = X.export(self.region, out, "unity", "t")
        self.assertEqual(failed(bars), [])
        sd = self.side(out)
        self.assertEqual(sd["size"], [129, 129])                    # Unity wants a square; the ground size keeps the shape
        self.assertEqual(sd["ground_m"], [500000.0, 300000.0])
        self.assertAlmostEqual(sd["metres_per_pixel"][0], 500000.0 / 128, places=3)
        self.assertAlmostEqual(sd["metres_per_pixel"][1], 300000.0 / 128, places=3)
        back = X.read_heightmap(out, 129, 129)
        self.assertLessEqual(self.worst(back, sd, src, True), sd["metres_per_step"] * 0.5 + 1e-6)
        bars, _ = X.export(self.region, self.d("r.png"), "roblox", "t", size=200)
        self.assertEqual(failed(bars), [])
        self.assertEqual(tuple(P.png_size(rb(self.d("r.png")))), (200, 120))

    def test_wrong_recipe_and_cli(self):
        dg = self.d("dg")
        run_cli("gen", "dungeon", "--seed", "3", "--w", "24", "--h", "18", "--out", dg)
        code, err = cli_fails("export", dg, "-o", self.d("x.raw"))
        self.assertEqual(code, 2)
        self.assertIn("world or region", err)
        code, err = cli_fails("export", self.world, "-o", self.d("x.png"))
        self.assertEqual(code, 2)
        self.assertIn("--to", err)
        txt = run_cli("export", self.world, "-o", self.d("cli.raw"), "--json")
        js = json.loads(txt)
        self.assertTrue(all(b["ok"] for b in js["bars"]))
        self.assertEqual(len(js["files"]), 2)

    def test_png_reader_filters(self):
        # a 16-bit grey PNG written with each of the five row filters reads back to the same numbers
        rows = [[(x * 257 + y * 911) % 65536 for x in range(7)] for y in range(6)]
        raw = b""
        prev = bytes(14)
        for y, r in enumerate(rows):
            cur = struct.pack(">7H", *r)
            ft = y % 5
            enc = bytearray()
            for i in range(14):
                a = cur[i - 2] if i >= 2 else 0
                b = prev[i]
                c = prev[i - 2] if i >= 2 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = (0, a, b, (a + b) // 2, a if pa <= pb and pa <= pc else b if pb <= pc else c)[ft]
                enc.append((cur[i] - pred) & 255)
            raw += bytes([ft]) + bytes(enc)
            prev = cur

        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 7, 6, 16, 0, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
        self.assertEqual(X.read_png_grey(png)[3], rows)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestTiled(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dg, cls.bt, cls.bh, cls.dk = (os.path.join(cls.tmp, n) for n in ("dg", "bt", "bh", "dk"))
        run_cli("gen", "dungeon", "--seed", "3", "--w", "30", "--h", "22", "--out", cls.dg)
        run_cli("gen", "battle", "--seed", "3", "--w", "20", "--h", "16", "--out", cls.bt)
        run_cli("gen", "battle", "--seed", "3", "--w", "20", "--h", "16", "--grid", "hex", "--out", cls.bh)
        run_cli("gen", "deck", "--seed", "3", "--out", cls.dk)

    def check_tmj(self, path, layers, w, h):
        """Independent read of a .tmj: sizes, gids against the tileset, cells against the recipe rows."""
        t = load_json(path)
        self.assertEqual((t["type"], t["orientation"], t["infinite"]), ("map", "orthogonal", False))
        self.assertEqual((t["width"], t["height"]), (w, h))
        ts = t["tilesets"][0]
        img = rb(os.path.join(os.path.dirname(path), ts["image"]))
        self.assertEqual(tuple(P.png_size(img)), (ts["imagewidth"], ts["imageheight"]))
        self.assertEqual(ts["imagewidth"], ts["columns"] * ts["tilewidth"])
        self.assertEqual(ts["tilecount"], ts["columns"] * (ts["imageheight"] // ts["tileheight"]))
        self.assertEqual((ts["tilewidth"], ts["tileheight"]), (t["tilewidth"], t["tileheight"]))
        tl = [L for L in t["layers"] if L["type"] == "tilelayer"]
        self.assertEqual(len(tl), len(layers))
        sym = {0: " ", 1: "#", 2: ".", 3: "+", 4: "T", 5: "L", 6: "A"}
        for L, rows in zip(tl, layers):
            data = L["data"]
            if L.get("encoding") == "base64":
                rawb = zlib.decompress(base64.b64decode(data))
                data = list(struct.unpack("<%dI" % (len(rawb) // 4), rawb))
            self.assertEqual((L["width"], L["height"], len(data)), (w, h, w * h))
            for g in data:
                self.assertTrue(g == 0 or ts["firstgid"] <= g < ts["firstgid"] + ts["tilecount"])
            floor_tmj = {(i % w, i // w) for i, g in enumerate(data) if g == 2}
            floor_rc = {(x, y) for y in range(h) for x in range(w) if rows[y][x] == "."}
            self.assertEqual(floor_tmj, floor_rc)
            self.assertEqual(["".join(sym[g] for g in data[y * w:(y + 1) * w]) for y in range(h)], list(rows))
        return t

    def test_dungeon_tmj_csv(self):
        out = self.d("dg.tmj")
        bars, files = X.export(self.dg, out, None, "t", csv=True)
        self.assertEqual(failed(bars), [])
        self.assertEqual([os.path.basename(f) for f in files], ["dg.tmj", "dg.tiles.png", "dg.csv"])
        gj = load_json(os.path.join(self.dg, "grid.json"))
        t = self.check_tmj(out, [gj["cells"]], 30, 22)
        og = {L["name"]: L["objects"] for L in t["layers"] if L["type"] == "objectgroup"}
        self.assertEqual(len(og["walls"]), len(gj["walls"]))
        self.assertEqual(len(og["doors"]), len(gj["portals"]))
        ids = [o["id"] for objs in og.values() for o in objs]
        self.assertEqual(len(ids), len(set(ids)))
        tw = t["tilewidth"]
        for o, (a, b) in zip(og["walls"], gj["walls"]):
            self.assertEqual((o["x"], o["y"]), (a[0] * tw, a[1] * tw))
            self.assertEqual((o["polyline"][1]["x"], o["polyline"][1]["y"]), ((b[0] - a[0]) * tw, (b[1] - a[1]) * tw))
        with open(self.d("dg.csv"), encoding="utf-8") as f:
            lines = f.read().split("\n")[:-1]
        self.assertEqual(len(lines), 22)
        csv = [[int(v) for v in ln.split(",")] for ln in lines]
        self.assertTrue(all(len(r) == 30 for r in csv))
        self.assertEqual([[" #.+TLA".index(c) - 1 for c in row] for row in gj["cells"]], csv)
        self.assertNotIn("\r", rb(out).decode("utf-8"))

    def test_battle_base64_and_tile_size(self):
        out = self.d("bt.tmj")
        bars, files = X.export(self.bt, out, "tiled", "t", encoding="base64", tile=16)
        self.assertEqual(failed(bars), [])
        gj = load_json(os.path.join(self.bt, "grid.json"))
        t = self.check_tmj(out, [gj["cells"]], 20, 16)
        self.assertEqual(t["tilewidth"], 16)
        self.assertEqual(tuple(P.png_size(rb(self.d("bt.tiles.png")))), (96, 16))
        self.assertIn("T", "".join(gj["cells"]))                     # trees are tiles of their own

    def test_deck_layers(self):
        out = self.d("dk.tmj")
        bars, files = X.export(self.dk, out, None, "t", csv=True)
        self.assertEqual(failed(bars), [])
        dj = load_json(os.path.join(self.dk, "deck.json"))
        t = self.check_tmj(out, dj["decks"], dj["w"], dj["h"])
        names = [L["name"] for L in t["layers"]]
        self.assertEqual(names, ["deck 1", "walls deck 1", "doors deck 1", "deck 2", "walls deck 2", "doors deck 2"])
        self.assertIn("dk.deck2.csv", [os.path.basename(f) for f in files])
        doors = [L for L in t["layers"] if L["name"] == "doors deck 1"][0]["objects"]
        self.assertEqual(len(doors), sum(c in "+A" for row in dj["decks"][0] for c in row))

    def test_forced_failures(self):
        out = self.d("bad.tmj")
        X.export(self.dg, out, "tiled", "t")
        good = load_json(out)

        def bars_for(fn):
            t = json.loads(json.dumps(good))
            fn(t)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(t, f)
            return X.tiled_bars(out, self.dg)
        self.assertEqual(failed(bars_for(lambda t: None)), [])
        floor = good["layers"][0]["data"].index(2)

        def wall_in(t):
            t["layers"][0]["data"][floor] = 1
        self.assertIn("floor cells", failed(bars_for(wall_in))[0][0])

        def bad_gid(t):
            t["layers"][0]["data"][0] = 99
        self.assertIn("every gid", failed(bars_for(bad_gid))[0][0])

        def short(t):
            t["layers"][0]["width"] = 29
        self.assertIn("layer size", failed(bars_for(short))[0][0])

        def flipped(t):                                              # flip bits are masked off before lookup
            t["layers"][0]["data"][floor] = 2 | 0x80000000
        self.assertEqual(failed(bars_for(flipped)), [])

        def stray(t):
            t["layers"][1]["objects"][0]["x"] = -64
        self.assertIn("inside the map", failed(bars_for(stray))[0][0])
        with open(out, "w", encoding="utf-8") as f:
            f.write("{not json")
        self.assertEqual(len(failed(X.tiled_bars(out, self.dg))), 1)

    def test_refusals(self):
        with self.assertRaises(ValueError) as c:
            X.export(self.bh, self.d("hex.tmj"), None, "t")
        self.assertIn("square", str(c.exception))
        world = self.d("w")
        run_cli("gen", "world", "--seed", "5", "--cells", "900", "--raster", "64", "--out", world)
        with self.assertRaises(ValueError):
            X.export(world, self.d("w.tmj"), None, "t")
        with self.assertRaises(ValueError):
            X.export(self.dg, self.d("dg.tmx"), "tiled", "t")

    # ---- deck plans to Universal VTT
    def test_deck_uvtt(self):
        out = self.d("ship.dd2vtt")
        bars, files = X.export(self.dk, out, None, "t")
        self.assertEqual(failed(bars), [])
        self.assertEqual([os.path.basename(f) for f in files], ["ship.deck1.dd2vtt", "ship.deck2.dd2vtt"])
        dj = load_json(os.path.join(self.dk, "deck.json"))
        for k, path in enumerate(files):
            u = load_json(path)
            ppg = u["resolution"]["pixels_per_grid"]
            self.assertEqual(ppg, 50)
            self.assertEqual((u["resolution"]["map_size"]["x"], u["resolution"]["map_size"]["y"]), (dj["w"], dj["h"]))
            self.assertEqual(tuple(P.png_size(base64.b64decode(u["image"]))), (dj["w"] * ppg, dj["h"] * ppg))
            rows = dj["decks"][k]
            for p in u["portals"]:                                   # every portal sits on a door square
                self.assertIn(rows[int(p["position"]["y"])][int(p["position"]["x"])], "+A")
            self.assertEqual(len(u["portals"]), sum(c in "+A" for row in rows for c in row))
            self.assertEqual(len(u["lights"]), sum(1 for rm in dj["rooms"] if rm["deck"] == k))
            self.assertTrue(u["line_of_sight"])
        bars, files = X.export(self.dk, self.d("two.dd2vtt"), "uvtt", "t", deck=2, pps=64)
        self.assertEqual(failed(bars), [])
        self.assertEqual([os.path.basename(f) for f in files], ["two.dd2vtt"])
        self.assertEqual(load_json(files[0])["resolution"]["pixels_per_grid"], 64)
        with self.assertRaises(ValueError):
            X.export(self.dk, self.d("no.dd2vtt"), "uvtt", "t", deck=7)

    def test_deck_uvtt_catches_a_sealed_door(self):
        u = X.deck_uvtt(self.dk, 0)
        u["portals"][0]["bounds"][0]["x"] += 0.4                     # a door end pulled off its wall
        self.assertIn("door", failed(P.uvtt_bars(json.dumps(u)))[0][0])

    def test_square_uvtt_still_goes_through_export(self):
        out = self.d("dg.dd2vtt")
        txt = run_cli("export", self.dg, "-o", out)
        self.assertNotIn("FAIL", txt)
        self.assertEqual(load_json(out)["resolution"]["pixels_per_grid"], 70)

    def test_uvtt_colours_closed_doors_and_wall_gaps(self):
        # references/cities-and-dungeons.md: colours are AARRGGBB, a portal with closed false imports as a window,
        # and a wall left under a portal doubles the door wall the importer builds
        us = []
        for src, name in ((self.dg, "c_dg.dd2vtt"), (self.bt, "c_bt.dd2vtt"), (self.dk, "c_dk.dd2vtt")):
            bars, files = X.export(src, self.d(name), "uvtt", "t")
            self.assertEqual(failed(bars), [])
            self.assertTrue(any("alpha first" in b[0] for b in bars))
            us += [load_json(f) for f in files]
        self.assertEqual(len(us), 4)
        doors = 0
        for u in us:
            for c in [u["environment"]["ambient_light"]] + [L["color"] for L in u["lights"]]:
                self.assertRegex(c, r"^ff[0-9a-f]{6}$")
            for p in u["portals"]:
                doors += 1
                self.assertIs(p["closed"], True)
                mx = (p["bounds"][0]["x"] + p["bounds"][1]["x"]) / 2
                my = (p["bounds"][0]["y"] + p["bounds"][1]["y"]) / 2
                for a, b in u["line_of_sight"]:
                    on = (a["x"] == b["x"] == mx and min(a["y"], b["y"]) <= my <= max(a["y"], b["y"])) or \
                         (a["y"] == b["y"] == my and min(a["x"], b["x"]) <= mx <= max(a["x"], b["x"]))
                    self.assertFalse(on)
        self.assertGreater(doors, 20)
        good = us[0]

        def bar(fn):
            u = json.loads(json.dumps(good))
            fn(u)
            return [b for b in P.uvtt_bars(json.dumps(u)) if "alpha first" in b[0]][0]
        self.assertTrue(bar(lambda u: None)[1])

        def rgba(u):                                                 # the same warm light written RRGGBBAA
            u["lights"][0]["color"] = "eccd8bff"
        self.assertFalse(bar(rgba)[1])
        self.assertIn("1 colours", bar(rgba)[2])

        def short(u):
            u["environment"]["ambient_light"] = "ffffff"
        self.assertFalse(bar(short)[1])

        def window(u):
            u["portals"][0]["closed"] = False
        self.assertFalse(bar(window)[1])
        self.assertIn("1 portals not closed", bar(window)[2])

        def walled(u):
            u["line_of_sight"].append(u["portals"][0]["bounds"])
        self.assertFalse(bar(walled)[1])
        self.assertIn("1 doors under a wall", bar(walled)[2])

    # ---- hex battle maps to PNG
    def test_hex_png(self):
        out = self.d("hex.png")
        bars, files = X.export(self.bh, out, None, "t")
        self.assertEqual(failed(bars), [])
        gj = load_json(os.path.join(self.bh, "grid.json"))
        rc = load_json(os.path.join(self.bh, "recipe.json"))
        pps = rc["params"]["pps"]
        w, h, rows = S.decode_png(rb(out))
        svg = rb(os.path.join(self.bh, "map.svg")).decode("utf-8")
        m = re.search(r'<svg[^>]*width="(\d+)" height="(\d+)"', svg)
        self.assertEqual((w, h), (int(m.group(1)), int(m.group(2))))   # same canvas as the SVG
        _, st = P.pstyle(None, "battle")
        col = {"#": st["rock"], ".": st["floor"], "+": st["door"], "T": st["tree"]}
        size = pps / math.sqrt(3)
        for y in range(gj["h"]):
            for x in range(gj["w"]):
                cx = pps * (x + 0.5 * (y % 2)) + pps / 2             # odd rows shifted half a hex (odd-r)
                cy = 1.5 * size * y + size
                self.assertEqual(rows[int(cy)][int(cx)], G.hex_rgb(col[gj["cells"][y][x]]))
        self.assertEqual(rows[0][0], G.hex_rgb(st["bg"]))            # the corner outside the first hex
        flat = {px for r in rows for px in r}
        self.assertIn(G.hex_rgb(st["grid"]), flat)
        self.assertLessEqual(len(flat), 6)                           # flat colours, no blending

    def test_hex_has_no_vtt_and_square_png_is_the_recipe_png(self):
        with self.assertRaises(ValueError) as c:
            X.export(self.bh, self.d("hex.dd2vtt"), None, "t")
        self.assertIn("square-grid only", str(c.exception))
        out = self.d("bt.png")
        bars, _ = X.export(self.bt, out, "png", "t")
        self.assertEqual(failed(bars), [])
        self.assertEqual(rb(out), rb(os.path.join(self.bt, "map.png")))


def read_obj(path):
    V, F = [], []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            t = ln.split()
            if t and t[0] == "v":
                V.append(tuple(float(v) for v in t[1:4]))
            elif t and t[0] == "f":
                F.append(tuple(int(v) - 1 for v in t[1:]))
    return V, F


def edge_counts(F):
    und, dirs = {}, {}
    for f in F:
        for k in range(3):
            p, q = f[k], f[(k + 1) % 3]
            und[frozenset((p, q))] = und.get(frozenset((p, q)), 0) + 1
            dirs[(p, q)] = dirs.get((p, q), 0) + 1
    return und, dirs


def volume(V, F):
    v = 0.0
    for a, b, c in F:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = V[a], V[b], V[c]
        v += x1 * (y2 * z3 - y3 * z2) - y1 * (x2 * z3 - x3 * z2) + z1 * (x2 * y3 - x3 * y2)
    return v / 6.0


class TestMesh(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.world = os.path.join(cls.tmp, "w.map")
        run_cli("gen", "world", "--seed", "7", "--cells", "1600", "--raster", "128", "--out", cls.world)
        cls.src = recipe_metres(cls.world)

    def test_open_surface(self):
        out = self.d("t.obj")
        bars, files = X.export(self.world, out, None, "t", size=33)
        self.assertEqual(failed(bars), [])
        V, F = read_obj(out)
        self.assertEqual((len(V), len(F)), (33 * 33, 2 * 32 * 32))
        self.assertTrue(all(len(f) == 3 and all(0 <= i < len(V) for i in f) for f in F))
        # real size in metres, x east, y north, z up; heights are the recipe's after the stated resample
        self.assertEqual((V[0][0], V[0][1]), (0.0, 1000000.0))       # first vertex is the north-west corner
        self.assertEqual((V[-1][0], V[-1][1]), (1000000.0, 0.0))
        worst = max(abs(V[j * 33 + i][2] - expect(self.src, 33, 33, i, j, True)) for j in range(33) for i in range(33))
        self.assertLess(worst, 1e-3)
        und, _ = edge_counts(F)
        self.assertEqual(sum(1 for c in und.values() if c == 1), 4 * 32)   # an open sheet: only the rim is open
        for a, b, c in F[:200]:                                      # faces wind counter-clockwise seen from above
            (x1, y1, _), (x2, y2, _), (x3, y3, _) = V[a], V[b], V[c]
            self.assertGreater((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1), 0)
        man = load_json(self.d("t.manifest.json"))
        self.assertEqual((man["polywright"], man["units"], man["status"]), ("1", "m", "model"))
        o = man["outputs"][0]
        self.assertEqual((o["path"], o["tris"], o["watertight"]), ("t.obj", len(F), False))
        import hashlib
        self.assertEqual(o["sha256"], hashlib.sha256(rb(out)).hexdigest())
        self.assertEqual(man["mapwright"]["recipe"]["path"], "w.map")
        self.assertEqual(man["mapwright"]["grid"], [33, 33])

    def test_print_tile_is_watertight(self):
        folder = self.d("asset")
        bars, files = X.export(self.world, folder, "mesh", "t", size=33, print_mm=100, exaggeration=20, flat_sea=True)
        self.assertEqual(failed(bars), [])
        self.assertEqual(len(bars), 3)
        for rel in ("out/terrain.obj", "manifest.json", "brief.md"):
            self.assertTrue(os.path.isfile(os.path.join(folder, rel)), rel)
        V, F = read_obj(os.path.join(folder, "out", "terrain.obj"))
        rim = 4 * 32
        self.assertEqual((len(V), len(F)), (33 * 33 + rim + 1, 2 * 32 * 32 + 3 * rim))
        self.assertTrue(all(0 <= i < len(V) for f in F for i in f))
        und, dirs = edge_counts(F)
        self.assertEqual(set(und.values()), {2})                     # every edge shared by exactly two faces
        self.assertEqual(set(dirs.values()), {1})                    # and crossed once each way: no flipped face
        self.assertEqual(len(V) - len(und) + len(F), 2)              # Euler characteristic of a sphere
        self.assertGreater(volume(V, F), 0)                          # outward normals
        zs = [v[2] for v in V]
        self.assertEqual(min(zs), 0.0)
        top = [v[2] for v in V[:33 * 33]]
        self.assertAlmostEqual(min(top), 2.0, places=3)              # 2 mm under the lowest point
        self.assertAlmostEqual(max(v[0] for v in V), 100.0, places=3)
        self.assertAlmostEqual(max(v[1] for v in V), 100.0, places=3)
        man = load_json(os.path.join(folder, "manifest.json"))
        mw = man["mapwright"]
        self.assertEqual((man["units"], man["targets"], man["outputs"][0]["watertight"]), ("mm", ["print-fdm"], True))
        self.assertEqual(man["outputs"][0]["path"], "out/terrain.obj")
        self.assertEqual(mw["scale"], "1:10000000")
        self.assertEqual(mw["vertical_exaggeration"], 20.0)
        self.assertEqual(mw["recipe"]["path"], "../w.map")
        # flat sea: nothing on top lies below sea level, and the relief is the recipe's times the exaggeration
        self.assertAlmostEqual(min(top), mw["z_of_sea_level"], places=3)
        self.assertAlmostEqual(max(top) - min(top), mw["max_m"] * 20 * mw["units_per_ground_metre"], places=3)

    def test_base_in_metres_and_exaggeration(self):
        a, b = self.d("a.obj"), self.d("b.obj")
        bars, _ = X.export(self.world, a, "mesh", "t", size=17, base=500)
        self.assertEqual(failed(bars), [])
        X.export(self.world, b, "mesh", "t", size=17, base=500, exaggeration=3)
        Va, Fa = read_obj(a)
        Vb, _ = read_obj(b)
        self.assertEqual(set(edge_counts(Fa)[0].values()), {2})
        ra = max(v[2] for v in Va[:289]) - min(v[2] for v in Va[:289])
        rb_ = max(v[2] for v in Vb[:289]) - min(v[2] for v in Vb[:289])
        self.assertAlmostEqual(rb_, 3 * ra, places=2)
        self.assertAlmostEqual(min(v[2] for v in Va[:289]), 500.0, places=3)

    def test_mesh_stats_catch_a_hole_and_a_flipped_face(self):
        z = [[float((i * 7 + j * 3) % 5) + 1 for i in range(5)] for j in range(4)]
        V, F = X.terrain_mesh(z, 4.0, 3.0, 0.0)
        self.assertEqual((len(V), len(F)), X.mesh_counts(5, 4, True))
        self.assertTrue(X.mesh_stats(V, F)["watertight"])
        hole = X.mesh_stats(V, F[:-1])
        self.assertFalse(hole["watertight"])
        self.assertEqual(hole["open_edges"], 3)
        a, b, c = F[0]
        flip = X.mesh_stats(V, [(a, c, b)] + F[1:])
        self.assertFalse(flip["watertight"])
        self.assertEqual(flip["same_way_edges"], 3)
        self.assertEqual(X.mesh_stats(V, F + [(0, 1, 999)])["bad_faces"], 1)
        Vo, Fo = X.terrain_mesh(z, 4.0, 3.0)
        self.assertEqual((len(Vo), len(Fo)), X.mesh_counts(5, 4, False))
        self.assertFalse(X.mesh_stats(Vo, Fo)["watertight"])

    def test_refusals(self):
        dg = self.d("dg")
        run_cli("gen", "dungeon", "--seed", "3", "--w", "24", "--h", "18", "--out", dg)
        for kw in (dict(), dict(size=1), dict(exaggeration=-1), dict(base=-2)):
            with self.assertRaises(ValueError):
                X.export(dg if not kw else self.world, self.d("x.obj"), "mesh", "t", **kw)


def tiny_pdf(w, h):
    """A one-page PDF with a classic cross-reference table, built by hand."""
    objs = [b"<</Type /Catalog\n/Pages 2 0 R>>", b"<</Type /Pages\n/Count 1\n/Kids [3 0 R]>>",
            b"<</Type /Page\n/Resources <</ProcSet [/PDF]>>\n/MediaBox [0 0 %s %s]\n/Parent 2 0 R>>"
            % (repr(w).encode(), repr(h).encode())]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    return out + b"trailer\n<</Size %d\n/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)


def newest_page_box(data, key):
    """Walk the file the way a reader does, apart from the exporter's parser: last startxref, that table's entry
    for the page object, then the box inside that object."""
    x = int(re.findall(rb"startxref\s+(\d+)\s+%%EOF", data)[-1])
    assert data[x:x + 4] == b"xref", "startxref does not point at a table"
    lines = data[x:].split(b"\n")
    first, count = (int(v) for v in lines[1].split())
    page = int(re.findall(rb"(\d+) 0 obj\s*<</Type /Page\b", data)[-1])
    assert first <= page < first + count, "the newest table does not list the page"
    off = int(lines[2 + page - first][:10])
    assert data[off:].startswith(b"%d 0 obj" % page), "the entry does not point at the page object"
    body = data[off:data.index(b"endobj", off)]
    m = re.search(b"/" + key + rb"\s*\[\s*([-\d. ]+)\]", body)
    return tuple(float(v) for v in m.group(1).split())


BROWSER = mpw.find_browser()


class TestPrint(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dg = os.path.join(cls.tmp, "dg")
        run_cli("gen", "dungeon", "--seed", "3", "--w", "24", "--h", "18", "--out", cls.dg)

    def test_paper_sizes_and_pixels(self):
        self.assertEqual(X.paper_size("a4"), (210.0, 297.0))
        self.assertEqual(X.paper_size("A3", True), (420.0, 297.0))
        self.assertEqual(X.paper_size("Letter"), (215.9, 279.4))
        self.assertEqual(X.paper_size("tabloid"), (279.4, 431.8))
        self.assertEqual(X.paper_size("300x200"), (300.0, 200.0))
        self.assertEqual(X.paper_size("120.5 x 80mm"), (120.5, 80.0))
        for bad in ("A9", "300", "5x5", "300x"):
            with self.assertRaises(ValueError):
                X.paper_size(bad)
        # the pixel table in references/games-film-print.md 6.1, at 300 ppi
        for name, px in (("A4", (2480, 3508)), ("A3", (3508, 4961)), ("A5", (1748, 2480)), ("Letter", (2550, 3300)),
                         ("Legal", (2550, 4200)), ("Tabloid", (3300, 5100)), ("A0", (9933, 14043))):
            w, h = X.paper_size(name)
            self.assertEqual((X.page_px(w, 300), X.page_px(h, 300)), px, name)

    def test_page_svg_bleed_and_marks(self):
        import xml.etree.ElementTree as ET
        svg = P.render_svg(self.dg)
        page = X.print_page_svg(svg, (210.0, 297.0), 3.0, True, 10.0, "contain")
        root = ET.fromstring(page.encode("utf-8"))
        ns = "{http://www.w3.org/2000/svg}"
        self.assertEqual(root.get("viewBox"), "0 0 216.0000 303.0000")
        self.assertEqual((root.get("width"), root.get("height")), ("216.0000mm", "303.0000mm"))
        marks = [g for g in root.findall(ns + "g") if g.get("class") == "crop-marks"][0].findall(ns + "line")
        self.assertEqual(len(marks), 8)
        for ln in marks:                                             # each mark lies in the bleed, on a trim line
            x1, y1, x2, y2 = (float(ln.get(k)) for k in ("x1", "y1", "x2", "y2"))
            self.assertTrue(x1 == x2 or y1 == y2)
            if x1 == x2:
                self.assertIn(x1, (3.0, 213.0))
                self.assertTrue(max(y1, y2) <= 3.0 or min(y1, y2) >= 300.0)
            else:
                self.assertIn(y1, (3.0, 300.0))
                self.assertTrue(max(x1, x2) <= 3.0 or min(x1, x2) >= 213.0)
        inner = root.find(ns + "svg")
        self.assertEqual([float(inner.get(k)) for k in ("x", "y", "width", "height")], [13.0, 13.0, 190.0, 277.0])
        self.assertEqual(inner.get("preserveAspectRatio"), "xMidYMid meet")
        self.assertEqual(inner.get("viewBox"), "0 0 %d %d" % (24 * 70, 18 * 70))
        self.assertNotIn("crop-marks", X.print_page_svg(svg, (210.0, 297.0), 0.0))
        self.assertNotIn("crop-marks", X.print_page_svg(svg, (210.0, 297.0), 3.0, False))
        cover = ET.fromstring(X.print_page_svg(svg, (210.0, 297.0), 3.0, True, 10.0, "cover").encode("utf-8"))
        ci = cover.find(ns + "svg")
        self.assertEqual([float(ci.get(k)) for k in ("x", "y", "width", "height")], [0.0, 0.0, 216.0, 303.0])
        self.assertEqual(ci.get("preserveAspectRatio"), "xMidYMid slice")
        with self.assertRaises(ValueError):
            X.print_page_svg(svg, (20.0, 20.0), 0.0, True, 10.0)

    def test_pdf_boxes_by_incremental_update(self):
        src = tiny_pdf(614.0, 860.88)                                # a browser page a little larger than asked
        self.assertEqual(X.pdf_pages(src)[0]["MediaBox"], (0.0, 0.0, 614.0, 860.88))
        w, h, b = 216 / 25.4 * 72, 303 / 25.4 * 72, 3 / 25.4 * 72
        out = X.pdf_set_boxes(src, w, h, b)
        self.assertTrue(out.startswith(src))                         # nothing in the original moved
        pg = X.pdf_pages(out)
        self.assertEqual(len(pg), 1)
        mb, tb = pg[0]["MediaBox"], pg[0]["TrimBox"]
        self.assertLess(max(abs(mb[2] - mb[0] - w), abs(mb[3] - mb[1] - h)), 1e-3)
        self.assertEqual(mb[3], 860.88)                              # the box hangs from the top-left corner
        self.assertLess(max(abs(tb[2] - tb[0] - 210 / 25.4 * 72), abs(tb[3] - tb[1] - 297 / 25.4 * 72)), 1e-3)
        self.assertEqual(pg[0]["BleedBox"], mb)
        self.assertEqual(newest_page_box(out, b"MediaBox"), mb)      # an independent walk finds the same box
        self.assertEqual(newest_page_box(out, b"TrimBox"), tb)
        self.assertIn(b"/Prev %d" % src.rindex(b"xref\n0 4"), out)
        with self.assertRaises(ValueError):
            X.pdf_pages(b"%PDF-1.5\nno table here")

    def test_no_browser_is_a_clear_skip(self):
        import mpw_render as R
        keep = R.find_browser
        R.find_browser = lambda: None
        try:
            with self.assertRaises(RuntimeError) as c:
                X.export(self.dg, self.d("nb.pdf"), None, "t")
            self.assertIn("Chrome or Edge", str(c.exception))
            code, err = cli_fails("export", self.dg, "-o", self.d("nb.pdf"))
            self.assertEqual(code, 2)
            self.assertIn("skipped", err)
        finally:
            R.find_browser = keep
        self.assertFalse(os.path.exists(self.d("nb.pdf")))
        with self.assertRaises(ValueError):
            X.export(self.dg, self.d("big.png"), "print", "t", paper="A0", dpi=600)
        with self.assertRaises(ValueError):
            X.export(self.dg, self.d("x.jpg"), "print", "t")

    @unittest.skipUnless(BROWSER, "print export needs Chrome or Edge")
    def test_a4_with_bleed_pdf_and_png(self):
        stem = self.d("a4")
        bars, files = X.export(self.dg, stem, "print", "t", paper="A4", bleed=3.0)
        self.assertEqual(failed(bars), [])
        self.assertEqual([os.path.basename(f) for f in files], ["a4.pdf", "a4.png", "a4.print.json"])
        png = rb(stem + ".png")
        self.assertEqual(struct.unpack(">II", png[16:24]), (2551, 3579))    # 216 x 303 mm at 300 dpi, exactly
        pdf = rb(stem + ".pdf")
        mb = newest_page_box(pdf, b"MediaBox")
        w, h = 216 / 25.4 * 72, 303 / 25.4 * 72
        self.assertLessEqual(max(abs(mb[2] - mb[0] - w), abs(mb[3] - mb[1] - h)), 0.5)     # the proof bar
        self.assertLessEqual(max(abs(mb[2] - mb[0] - w), abs(mb[3] - mb[1] - h)), 0.001)   # measured
        tb = newest_page_box(pdf, b"TrimBox")
        self.assertLessEqual(max(abs(tb[2] - tb[0] - 595.2756), abs(tb[3] - tb[1] - 841.8898)), 0.001)
        self.assertAlmostEqual(tb[0] - mb[0], 3 / 25.4 * 72, places=3)
        self.assertEqual(len(X.pdf_pages(pdf)), 1)
        sd = load_json(stem + ".print.json")
        self.assertEqual((sd["page_px"], sd["page_mm"], sd["crop_marks"]), ([2551, 3579], [216.0, 303.0], True))

    @unittest.skipUnless(BROWSER, "print export needs Chrome or Edge")
    def test_letter_landscape_and_custom(self):
        out = self.d("letter.pdf")
        bars, files = X.export(self.dg, out, None, "t", paper="Letter", landscape=True)
        self.assertEqual(failed(bars), [])
        mb = newest_page_box(rb(out), b"MediaBox")
        self.assertLessEqual(max(abs(mb[2] - mb[0] - 792.0), abs(mb[3] - mb[1] - 612.0)), 0.001)
        out = self.d("card.png")
        txt = run_cli("export", self.dg, "--to", "print", "-o", out, "--paper", "150x100", "--dpi", "127",
                      "--bleed", "2", "--fit", "cover")
        self.assertNotIn("FAIL", txt)
        self.assertEqual(struct.unpack(">II", rb(out)[16:24]), (770, 520))   # 154 x 104 mm at 127 dpi = 5 px per mm


class TestTargets(unittest.TestCase):
    def test_extension_picks_the_target(self):
        pk = X.pick_target
        self.assertEqual(pk("dungeon", "a.dd2vtt", None), "uvtt")
        self.assertEqual(pk("deck", "a.tmj", None), "tiled")
        self.assertEqual(pk("world", "a.raw", None), "unity")
        self.assertEqual(pk("world", "a.r16", None), "godot")
        self.assertEqual(pk("region", "a.obj", None), "mesh")
        self.assertEqual(pk("city", "a.pdf", None), "print")
        self.assertEqual(pk("planet", "a.png", None), "sphere")
        self.assertEqual(pk("battle", "a.png", None, "hex"), "png")
        self.assertEqual(pk("sector", "a.tab", None), "t5")
        self.assertEqual(pk("world", "a.png", "roblox"), "roblox")
        for kind, out in (("world", "a.png"), ("battle", "a.png"), ("world", "a.xyz")):
            with self.assertRaises(ValueError):
                pk(kind, out, None, "square")
        with self.assertRaises(ValueError):
            pk("world", "a.png", "stl")

    def test_doctor_and_explain(self):
        info = json.loads(run_cli("doctor", "--json"))
        self.assertEqual(info["export"]["print"], bool(BROWSER))
        self.assertTrue(info["export"]["heightmaps"] and info["export"]["tiled"] and info["export"]["mesh"])
        for term in ("heightmap", "bleed", "crop-marks", "tmj", "uvtt"):
            self.assertIn("references/games-film-print.md", run_cli("explain", term))


class TestNav(Base):
    """Backlog: export --nav, walkable squares as rectangles with portals."""

    def recipes(self):
        out = []
        for seed in range(1, 6):
            for name, args in (("b", ("dungeon", "--w", "40", "--h", "30")),
                               ("v", ("dungeon", "--method", "cave", "--w", "40", "--h", "30")),
                               ("y", ("dungeon", "--method", "cyclic")),
                               ("t", ("battle", "--w", "30", "--h", "24"))):
                d = self.d("nav-%s%d" % (name, seed))
                if not os.path.isdir(d):
                    run_cli("gen", *args, "--seed", str(seed), "--out", d)
                out.append(d)
        return out

    def test_bars_and_independent_check(self):
        for d in self.recipes():
            out = os.path.join(d, "map.nav.json")
            bars, files = X.export(d, out, None, "t", nav=True)
            self.assertTrue(all(ok for _, ok, _ in bars), (d, bars))
            nav = json.load(open(out, encoding="utf-8"))
            gj = json.load(open(os.path.join(d, "grid.json"), encoding="utf-8"))
            g = gj["cells"]
            seen = {}
            for r in nav["rects"]:
                for y in range(r["y"], r["y"] + r["h"]):
                    for x in range(r["x"], r["x"] + r["w"]):
                        self.assertNotIn((x, y), seen)
                        self.assertIn(g[y][x], ".+")
                        seen[(x, y)] = r["id"]
            walk = {(x, y) for y in range(gj["h"]) for x in range(gj["w"]) if g[y][x] in ".+"}
            self.assertEqual(set(seen), walk)
            adj = {r["id"]: set() for r in nav["rects"]}
            for p in nav["portals"]:
                adj[p["a"]].add(p["b"])
                adj[p["b"]].add(p["a"])
            # every pair of 4-neighbour walkable squares in different rects must be joined by a portal
            for x, y in walk:
                for q in ((x + 1, y), (x, y + 1)):
                    if q in walk and seen[q] != seen[(x, y)]:
                        self.assertIn(seen[q], adj[seen[(x, y)]])
            self.assertLess(len(nav["rects"]), len(walk))

    def test_byte_identical_and_cli(self):
        d = self.recipes()[2]
        a, b = os.path.join(self.tmp, "n1.json"), os.path.join(self.tmp, "n2.json")
        run_cli("export", d, "--nav", "-o", a)
        run_cli("export", d, "--to", "nav", "-o", b)
        with open(a, "rb") as f1, open(b, "rb") as f2:
            self.assertEqual(f1.read(), f2.read())
        nav = json.load(open(a, encoding="utf-8"))
        self.assertTrue(any("lock" in r for r in nav["rects"]))
        self.assertTrue(any("enter_from" in r for r in nav["rects"]))
        self.assertEqual(nav["format"], "mapwright-nav")

    def test_forced_failure_and_refusals(self):
        g = ["....", ".##.", "...."]
        nav = dict(rects=[dict(id=0, x=0, y=0, w=4, h=2)], portals=[])
        names = [n for n, ok, _ in X.nav_bars(g, 4, 3, nav) if not ok]
        self.assertEqual(len(names), 3)
        hexd = self.d("nav-hex")
        run_cli("gen", "battle", "--grid", "hex", "--seed", "2", "--w", "12", "--h", "10", "--out", hexd)
        code, err = cli_fails("export", hexd, "--nav", "-o", os.path.join(self.tmp, "h.json"))
        self.assertNotEqual(code, 0)
        self.assertIn("square-grid only", err)
        wd = self.d("nav-world")
        run_cli("gen", "world", "--seed", "2", "--cells", "300", "--out", wd)
        code, err = cli_fails("export", wd, "--nav", "-o", os.path.join(self.tmp, "w.json"))
        self.assertNotEqual(code, 0)
        self.assertIn("square dungeon and battle", err)


if __name__ == "__main__":
    unittest.main()
