"""Tests for `read` and `trace` (scripts/mpw_read.py). Run: python -m unittest discover -s tests"""
import io
import json
import math
import os
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import mpw  # noqa: E402
import mpw_read as R  # noqa: E402

SEA, LAND, INK = (60, 120, 200), (120, 170, 90), (20, 20, 20)
NO_TESS = (lambda name: None)


def no_ocr(path):
    return R.run_ocr(path, which=NO_TESS)


def write_png(path, rows):
    w = len(rows[0]) // 3
    with open(path, "wb") as f:
        f.write(R.png_rgb_bytes(w, len(rows), rows))


def picture(w, h, fn):
    return [bytearray(b"".join(bytes(fn(x, y)) for x in range(w))) for y in range(h)]


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


class TestPng(unittest.TestCase):
    def _chunk(self, t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    def _png(self, w, h, depth, ctype, raw_rows, extra=b""):
        raw = b"".join(raw_rows)
        return (b"\x89PNG\r\n\x1a\n" + self._chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0))
                + extra + self._chunk(b"IDAT", zlib.compress(raw)) + self._chunk(b"IEND", b""))

    def test_rgb_round_trip(self):
        rows = picture(7, 5, lambda x, y: (x * 30, y * 40, (x * y) % 256))
        img = R.decode_png(R.png_rgb_bytes(7, 5, rows))
        self.assertEqual((img.w, img.h), (7, 5))
        self.assertEqual(img.rows, rows)

    def test_filters_paeth_sub_up_avg(self):
        # one RGB row per filter type, encoded by hand against a known previous row
        w = 4
        target = [bytes([10 * i + c for i in range(w) for c in range(3)]), bytes([200 - 7 * i for i in range(3 * w)])]
        rows = [b"\x00" + target[0]]
        prev, line = target[0], target[1]
        for ft in (1, 2, 3, 4):
            enc = bytearray()
            for i in range(3 * w):
                a = line[i - 3] if i >= 3 else 0
                b, c = prev[i], (prev[i - 3] if i >= 3 else 0)
                if ft == 1:
                    pr = a
                elif ft == 2:
                    pr = b
                elif ft == 3:
                    pr = (a + b) >> 1
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    pr = a if pa <= pb and pa <= pc else b if pb <= pc else c
                enc.append((line[i] - pr) & 255)
            rows.append(bytes([ft]) + bytes(enc))
            prev = line
        img = R.decode_png(self._png(w, 5, 8, 2, rows))
        for r in img.rows[1:]:
            self.assertEqual(bytes(r), target[1])

    def test_rgba_composited_on_white(self):
        img = R.decode_png(self._png(1, 1, 8, 6, [b"\x00" + bytes([0, 0, 0, 0])]))
        self.assertEqual(img.px(0, 0), (255, 255, 255))

    def test_palette_and_low_bit_grey(self):
        plte = self._chunk(b"PLTE", bytes([255, 0, 0, 0, 0, 255]))
        img = R.decode_png(self._png(3, 1, 1, 3, [b"\x00" + bytes([0b01000000])], plte))
        self.assertEqual([img.px(x, 0) for x in range(3)], [(255, 0, 0), (0, 0, 255), (255, 0, 0)])
        g = R.decode_png(self._png(2, 1, 2, 0, [b"\x00" + bytes([0b11000000])]))
        self.assertEqual([g.px(x, 0) for x in range(2)], [(255, 255, 255), (0, 0, 0)])

    def test_sixteen_bit(self):
        img = R.decode_png(self._png(1, 1, 16, 2, [b"\x00" + bytes([0x12, 0x34, 0xAB, 0xCD, 0xFF, 0x00])]))
        self.assertEqual(img.px(0, 0), (0x12, 0xAB, 0xFF))


class TestGeometry(unittest.TestCase):
    def test_square_with_hole_and_island(self):
        # water square 2..17 with a land hole 6..10 and a water island 8 inside the hole
        def f(x, y):
            if 6 <= x < 11 and 6 <= y < 11:
                return 1 if (x, y) == (8, 8) else 0
            return 1 if 2 <= x < 18 and 2 <= y < 18 else 0
        mask = [bytearray(f(x, y) for x in range(20)) for y in range(20)]
        polys = R.polygons_from_mask(mask, eps=0.0)
        self.assertEqual(len(polys), 2)
        big = max(polys, key=lambda p: R.ring_area(p[0]))
        self.assertEqual(R.ring_area(big[0]), 256.0)
        self.assertEqual(len(big), 2)
        self.assertEqual(R.ring_area(big[1]), -25.0)  # the hole ring bounds the 5x5 land block
        small = min(polys, key=lambda p: R.ring_area(p[0]))
        self.assertEqual(R.ring_area(small[0]), 1.0)

    def test_diagonal_pixels_stay_separate(self):
        mask = [bytearray([1, 0]), bytearray([0, 1])]
        rings = R.mask_rings(mask)
        self.assertEqual(sorted(R.ring_area(r) for r in rings), [1.0, 1.0])

    def test_douglas_peucker(self):
        pts = [(x, 0.3 * math.sin(x)) for x in range(50)]
        self.assertEqual(R.douglas_peucker(pts, 0.7), [pts[0], pts[-1]])
        self.assertGreater(len(R.douglas_peucker(pts, 0.1)), 10)

    def test_skeleton_line(self):
        mask = [bytearray(1 if 9 <= y <= 11 and 5 <= x < 45 else 0 for x in range(50)) for y in range(21)]
        lines = R.skeleton_lines(R.thin(mask), eps=1.0, min_len=5)
        self.assertEqual(len(lines), 1)
        ln = lines[0]
        self.assertTrue(all(abs(p[1] - 10.5) <= 1.0 for p in ln))
        self.assertGreater(abs(ln[-1][0] - ln[0][0]), 30)


class TestGeoref(unittest.TestCase):
    CO = [0.0125, 0.0008, -3.2, -0.0006, -0.0118, 56.4]  # known lon/lat affine with a small rotation

    def gcps(self, pts, noise=None):
        out = []
        for i, (px, py) in enumerate(pts):
            X, Y = R.apply_affine(self.CO, (px, py))
            if noise:
                X, Y = X + noise[i][0], Y + noise[i][1]
            out.append([px, py, X, Y])
        return out

    def test_recovers_known_transform(self):
        fit = R.fit_affine(self.gcps([(10, 12), (980, 40), (500, 700), (60, 760), (900, 690), (400, 300)]))
        for got, want in zip(fit["coefficients"], self.CO):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertLess(fit["rms_m"], 1e-3)  # bar: under 1 mm on exact points

    def test_three_points_flagged_and_noise_shows(self):
        three = R.fit_affine(self.gcps([(10, 12), (980, 40), (500, 700)]))
        self.assertIn("prove nothing", three["note"])
        noisy = R.fit_affine(self.gcps([(10, 12), (980, 40), (500, 700), (60, 760)],
                                       noise=[(0, 0), (0, 0), (0, 0), (0.001, 0)]))
        self.assertGreater(noisy["rms_m"], 10)  # 0.001 deg of lon at 50 N is about 70 m, spread over 4 points
        with self.assertRaises(ValueError):
            R.fit_affine(self.gcps([(0, 0), (1, 1), (2, 2)]))

    def test_world_file_round_trip(self):
        txt = R.world_file_text(self.CO)
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "m.pgw")
            with open(p, "w") as f:
                f.write(txt)
            back = R.read_world_file(p)
        for got, want in zip(back, self.CO):
            self.assertAlmostEqual(got, want, delta=1e-9)


class TestRead(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.png = os.path.join(self.tmp.name, "map.png")
        write_png(self.png, picture(60, 40, lambda x, y: SEA if x < 30 else (LAND if y > 4 else INK)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_not_sure_without_ocr(self):
        rep = R.read_report(self.png, ocr=no_ocr)
        self.assertEqual((rep["width"], rep["height"]), (60, 40))
        self.assertAlmostEqual(rep["classes"]["water"], 0.5, delta=0.01)
        self.assertAlmostEqual(rep["classes"]["vegetation"], 0.4375, delta=0.01)
        for k in ("text", "printed_scale", "scale", "georeference", "legend", "names"):
            self.assertEqual(rep[k]["status"], R.NOT_SURE, k)
            self.assertIsNone(rep[k]["value"])
        self.assertIn("tesseract is not on PATH", rep["text"]["reason"])

    def test_fake_tesseract(self):
        tsv = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
               "5\t1\t1\t1\t1\t1\t3\t30\t20\t6\t91.5\tScale\n"
               "5\t1\t1\t1\t1\t2\t25\t30\t30\t6\t88.0\t1:50,000\n"
               "5\t1\t1\t1\t1\t3\t25\t2\t30\t6\t41.0\tPortwen\n")
        calls = []

        class Done:
            returncode, stdout, stderr = 0, tsv, ""

        def fake_run(args, **kw):
            calls.append(args)
            return Done()
        rep = R.read_report(self.png, ocr=lambda p: R.run_ocr(p, which=lambda n: "/x/tesseract", run=fake_run))
        self.assertEqual(calls[0][0], "/x/tesseract")
        self.assertEqual(rep["text"]["status"], "read")
        self.assertEqual(len(rep["text"]["words"]), 3)
        self.assertEqual(rep["text"]["low_confidence"], 1)
        self.assertEqual(rep["printed_scale"]["value"], ["1:50,000"])

    def test_gcp_writes_world_file(self):
        g = [[0, 0, 10.0, 50.0], [60, 0, 10.06, 50.0], [0, 40, 10.0, 49.96], [60, 40, 10.06, 49.96]]
        rep = R.read_report(self.png, g, write_world=True, ocr=no_ocr)
        self.assertTrue(os.path.isfile(rep["georeference"]["world_file"]))
        self.assertTrue(rep["georeference"]["world_file"].endswith(".pgw"))
        self.assertLess(rep["georeference"]["rms_m"], 1e-3)
        mpp = rep["scale"]["metres_per_pixel"]
        self.assertAlmostEqual(mpp, (0.001 * 111195 * math.cos(math.radians(49.98)) + 0.001 * 111195) / 2, delta=2)

    def test_prompt_and_validate(self):
        p = R.agent_prompt(self.png)
        self.assertIn("not sure", " ".join(p["rules"]))
        self.assertEqual(p["image"]["width"], 60)
        g = [[0, 0, 10.0, 50.0], [60, 0, 10.06, 50.0], [0, 40, 10.0, 49.96], [60, 40, 10.06, 49.96]]
        mpp = R.metres_per_pixel(R.fit_affine(g), 60, 40)
        ans = {"title": "not sure",
               "legend": [{"label": "sea", "swatch_box": [2, 10, 10, 20], "colour": "#3c78c8"},
                          {"label": "land", "swatch_box": [40, 10, 50, 20], "colour": "#3c78c8"},
                          {"label": "ghost", "colour": "#ffffff"}],
               "scale": {"kind": "bar", "box": [5, 30, 25, 35], "bar_px": 20, "bar_m": 20 * mpp * 1.03},
               "names": [{"text": "Off", "box": [50, 30, 90, 35]}]}
        out = R.validate_answers(self.png, ans, g)
        v = {it["field"]: it["verdict"] for it in out["items"]}
        self.assertEqual(v["title"], R.NOT_SURE)
        self.assertEqual(v["legend[0]"], "ok")
        self.assertEqual(v["legend[1]"], "mismatch")
        self.assertEqual(v["legend[2]"], "dropped")
        self.assertEqual(v["scale"], "ok")
        self.assertEqual(v["names[0]"], "dropped")
        ans["scale"]["bar_m"] = 20 * mpp * 1.5
        v = {it["field"]: it["verdict"] for it in R.validate_answers(self.png, ans, g)["items"]}
        self.assertEqual(v["scale"], "mismatch")

    def test_cli(self):
        out = json.loads(run_cli("read", self.png, "--prompt"))
        self.assertIn("schema", out)
        out = json.loads(run_cli("trace", self.png))
        self.assertEqual(out["type"], "FeatureCollection")
        self.assertEqual(len(out["features"]), 1)
        self.assertEqual(out["features"][0]["properties"]["area_px"], 1200.0)


class TestTrace(unittest.TestCase):
    def test_georeferenced_output(self):
        with tempfile.TemporaryDirectory() as t:
            png = os.path.join(t, "m.png")
            write_png(png, picture(40, 40, lambda x, y: SEA if 10 <= x < 30 and 10 <= y < 30 else LAND))
            g = [[0, 0, 0.0, 10.0], [40, 0, 4.0, 10.0], [0, 40, 0.0, 6.0], [40, 40, 4.0, 6.0]]
            fc = R.trace(png, gcps=g)
            xs = sorted({round(c[0], 6) for c in fc["features"][0]["geometry"]["coordinates"][0]})
            ys = sorted({round(c[1], 6) for c in fc["features"][0]["geometry"]["coordinates"][0]})
            self.assertEqual(xs, [1.0, 3.0])
            self.assertEqual(ys, [7.0, 9.0])
            with open(R.world_file_path(png), "w") as f:
                f.write(R.world_file_text(R.fit_affine(g)["coefficients"]))
            fc2 = json.loads(run_cli("trace", png, "--world", "auto"))
            self.assertEqual(fc2["features"][0]["geometry"], fc["features"][0]["geometry"])

    def test_colour_lines(self):
        with tempfile.TemporaryDirectory() as t:
            png = os.path.join(t, "r.png")
            write_png(png, picture(60, 30, lambda x, y: (61, 124, 192) if abs(y - 15 - (x - 30) / 6.0) <= 1.2 else LAND))
            fc = R.trace(png, colour=(61, 124, 192), mode="lines", clean=0)
            self.assertEqual(len(fc["features"]), 1)
            ln = fc["features"][0]["geometry"]["coordinates"]
            self.assertGreater(math.hypot(ln[-1][0] - ln[0][0], ln[-1][1] - ln[0][1]), 50)


class TestRoundTrip(unittest.TestCase):
    """Proof bar: the renderer's land/sea raster traced back agrees with the recipe's coast lines.
    Measured 2026-11-14 on seeds 7, 11, 23 at 4000 cells and 512 px: median 0.26-0.30 px and
    p95 0.75-2.96 px recipe to traced; traced to recipe median 0.49-0.52 px, p95 0.66-0.67 px.
    Bars: median <= 1.0 px both ways, p95 <= 4.0 px both ways (1 px = 1.95 km)."""

    def test_raster_round_trip(self):
        import mpw_gen as G
        import roundtrip_trace as T
        with tempfile.TemporaryDirectory() as t:
            d = os.path.join(t, "w")
            G.gen_world(7, 4000, d)
            png = os.path.join(t, "w.png")
            w = T.raster_png(d, png)
            r = T.measure(d, png, w / G.WORLD, lakes=False)
        for k in ("recipe_to_traced", "traced_to_recipe"):
            self.assertLessEqual(r[k]["median"], 1.0, (k, r[k]))
            self.assertLessEqual(r[k]["p95"], 4.0, (k, r[k]))


if __name__ == "__main__":
    unittest.main()
