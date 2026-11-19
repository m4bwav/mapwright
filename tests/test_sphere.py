import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import mpw_sphere as S  # noqa: E402


class SphereTests(unittest.TestCase):
    def test_unit_round_trip(self):
        for lon, lat in ((0, 0), (174.81, -41.32), (-5.5, 40.96), (90, 89.9)):
            v = S.unit(lon, lat)
            self.assertAlmostEqual(S.dot(v, v), 1.0, places=12)
            lo, la = S.lonlat(v)
            self.assertAlmostEqual(lo, lon, places=9)
            self.assertAlmostEqual(la, lat, places=9)

    def test_gnomonic_clip_and_centre(self):
        fr = S.frame(S.unit(10, 20))
        x, y = S.gnomonic(S.unit(10, 20), fr)
        self.assertAlmostEqual(x, 0, places=12)
        self.assertAlmostEqual(y, 0, places=12)
        self.assertIsNone(S.gnomonic(S.unit(-170, -20), fr))
        self.assertIsNotNone(S.gnomonic(S.unit(30, 80), S.frame((0, 0, 1))))  # pole centre

    def test_contains_matches_plane_test(self):
        tri = [S.unit(0, 0), S.unit(40, 0), S.unit(20, 40)]
        rnd = random.Random(1)
        for _ in range(5000):
            q = S.unit(rnd.uniform(-10, 50), rnd.uniform(-10, 50))
            truth = all(S.dot(S.cross(tri[i], tri[(i + 1) % 3]), q) > 0 for i in range(3))
            self.assertEqual(S.contains(tri, q), truth)
        self.assertFalse(S.contains(tri, S.unit(200, -20)))

    def test_arc_intersection(self):
        x = S.arc_intersection(S.unit(-10, 0), S.unit(10, 0), S.unit(0, -10), S.unit(0, 10))
        lo, la = S.lonlat(x)
        self.assertAlmostEqual(lo, 0, places=9)
        self.assertAlmostEqual(la, 0, places=9)
        self.assertIsNone(S.arc_intersection(S.unit(-10, 0), S.unit(10, 0), S.unit(0, 5), S.unit(0, 10)))
        self.assertIsNone(S.arc_intersection(S.unit(0, 0), S.unit(10, 0), S.unit(20, 0), S.unit(30, 0)))

    def test_rim_and_small_circle(self):
        self.assertAlmostEqual(S.rim_angle(0, 1), math.pi / 2)
        a, c = S.small_circle(1000.0, 6371.0)
        self.assertAlmostEqual(a, 1000 / 6371)
        self.assertAlmostEqual(c, 2 * math.pi * 6371 * math.sin(1000 / 6371), places=6)
        self.assertLess(c, 2 * math.pi * 1000)
        self.assertAlmostEqual(S.small_circle(math.pi * 6371, 6371)[1], 0, places=6)
        self.assertIsNone(S.small_circle(2 * math.pi * 6371, 6371))


if __name__ == "__main__":
    unittest.main()
