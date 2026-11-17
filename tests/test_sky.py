import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import mpw  # noqa: E402
import mpw_render as R  # noqa: E402
import mpw_sky as S  # noqa: E402

SAMPLE = os.path.join(SCRIPTS, "data", "sky-sample.csv")


def lint_ok(conv, year):
    return R.period_lint(set(conv), year, "sky")[0][1]


class SkyPeriod(unittest.TestCase):
    def test_bayer_before_iau(self):
        bars = R.period_lint({"bayer-letters", "iau-boundaries"}, 1700, "sky")
        self.assertFalse(bars[0][1])
        self.assertIn("IAU constellation boundaries", bars[0][2])
        self.assertNotIn("Bayer", bars[0][2])

    def test_flamsteed_numbers_not_1729(self):
        bars = R.period_lint({"flamsteed-numbers"}, 1729, "sky")
        self.assertIn("1765", bars[1][2])  # flagged at 1729, warn only: sources disagree on the first print
        self.assertFalse(lint_ok({"flamsteed-numbers"}, 1700))
        self.assertEqual(len(R.period_lint({"flamsteed-numbers"}, 1790, "sky")), 1)

    def test_iau_list_and_boundaries_apart(self):
        self.assertTrue(lint_ok({"iau-88"}, 1925))
        self.assertFalse(lint_ok({"iau-boundaries"}, 1925))

    def test_uncertain_years_warn_only(self):
        for conv, year in (("stick-figures", 1820), ("equatorial-grid", 1650), ("magnitude-scale", 0),
                           ("stereographic", 1400), ("epoch-2000", 1950)):
            bars = R.period_lint({conv}, year, "sky")
            self.assertTrue(bars[0][1], conv)
            self.assertIn("WARN", bars[1][2], conv)
        self.assertFalse(lint_ok({"magnitude-scale"}, -300))

    def test_sky_rules_stay_on_sky(self):
        self.assertTrue(R.period_lint({"ngc"}, 1800, "map")[0][1])


class SkyChart(unittest.TestCase):
    def test_ra_east_left_in_sky_view(self):
        for proj in S.PROJECTIONS:
            a = S.project(90.0, 10.0, 80.0, 0.0, proj, "sky")   # RA 6h
            b = S.project(75.0, 10.0, 80.0, 0.0, proj, "sky")   # RA 5h
            self.assertLess(a[0], b[0], proj)
            ga = S.project(90.0, 10.0, 80.0, 0.0, proj, "globe")
            gb = S.project(75.0, 10.0, 80.0, 0.0, proj, "globe")
            self.assertGreater(ga[0], gb[0], proj)

    def test_radii_fixed_steps_and_legend(self):
        rs = [S.radius(m, 6) for m in range(1, 7)]
        self.assertTrue(all(a > b for a, b in zip(rs, rs[1:])))
        for a, b in zip(rs, rs[1:]):
            self.assertAlmostEqual(a / b, S.R_STEP, places=9)
        stars = [dict(ra=80 + i, dec=i, mag=float(m), name="") for i, m in enumerate(range(1, 7))]
        svg, desc = S.render(stars)
        self.assertEqual(svg.count('class="legend-mag"'), 6)
        self.assertTrue(all(b[1] for b in S.check(desc, svg)))

    def test_sample_chart_bars_and_determinism(self):
        stars = S.read_stars(SAMPLE)
        for proj in S.PROJECTIONS:
            for ori in S.ORIENTATIONS:
                svg, desc = S.render(stars, proj, ori)
                self.assertTrue(all(b[1] for b in S.check(desc, svg)), (proj, ori))
                self.assertEqual(svg, S.render(stars, proj, ori)[0])

    def test_five_statements(self):
        svg, desc = S.render(S.read_stars(SAMPLE))
        for k in S.DESCRIPTORS:
            d = dict(desc)
            d.pop(k)
            bar = S.check(d)[0]
            self.assertFalse(bar[1])
            self.assertIn(k, bar[2])

    def test_cli(self):
        out = os.path.join(tempfile.mkdtemp(), "orion.svg")
        buf = io.StringIO()
        with redirect_stdout(buf):
            mpw.main(["sky", SAMPLE, "-o", out, "--period", "1700", "--json"])
        j = json.loads(buf.getvalue())
        self.assertTrue(all(b["ok"] for b in j["bars"]))
        self.assertTrue(os.path.isfile(os.path.splitext(out)[0] + ".sky.json"))
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
            mpw.main(["sky", SAMPLE, "-o", out, "--period", "1700", "--uses", "iau-boundaries"])


class StarChartStyle(unittest.TestCase):
    def test_decorative_warn(self):
        bars = R.style_bars("star-chart")
        self.assertEqual(len(bars), 1)
        self.assertTrue(bars[0][1])
        self.assertIn("decorative star field, not a sky chart", bars[0][2])
        self.assertEqual(R.style_bars("topographic"), [])


if __name__ == "__main__":
    unittest.main()
