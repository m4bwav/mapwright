"""Climate model 2 (book track s45: Geosystems, Planet Construction Kit): currents, marine west coasts,
continentality, snowline, upwind edge, cell edges, Koppen. T-20261116-25..27."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import mpw_gen as g  # noqa: E402

W = g.WORLD


def continent(lt=50.0, lb=0.0, x0=200.0, x1=800.0, sp=20.0, h=0.02, seed=1):
    """Flat rectangular continent from x0 to x1, sea either side: symmetric by construction."""
    M = g.build_mesh(seed, 0.0, 0.0, W - 1e-9, W - 1e-9, sp)
    H = [h if x0 <= x <= x1 else -0.3 for x in M["X"]]
    hyd = dict(ocean=[v < 0 for v in H], lake=[-1] * len(H))
    return M, H, hyd


def mean(v):
    return sum(v) / len(v)


class Currents(unittest.TestCase):
    def strips(self, opts):
        M, H, hyd = continent()
        t, p, _b = g.climate(1, M, H, hyd, 50.0, 0.0, opts)
        kmu = g.climate_km_per_unit(50.0, 0.0)
        dw, de = g.coast_distances(dict(x=M["X"], ocean=hyd["ocean"], nx=M["nx"]), kmu)
        st = 3 * 20.0 * kmu
        band = [c for c in range(len(H)) if not hyd["ocean"][c] and 15 <= g.lat_of(M["Y"][c], 50, 0) <= 35]
        west = [c for c in band if dw[c] <= st < de[c]]
        east = [c for c in band if de[c] <= st < dw[c]]
        self.assertGreater(len(west), 20)
        self.assertGreater(len(east), 20)
        return mean([p[c] for c in east]) / mean([p[c] for c in west]), \
            mean([t[c] for c in east]) - mean([t[c] for c in west])

    def test_east_coast_wetter_and_warmer(self):
        ratio, dt = self.strips({})
        self.assertGreaterEqual(ratio, 1.5)   # measured 4.09 (model 1: 1.95)
        self.assertGreaterEqual(dt, 2.0)      # measured +3.56 C (model 1: +0.62)

    def test_model_one_has_no_current_term(self):
        _ratio, dt = self.strips(None)
        self.assertLess(dt, 2.0)


class Continentality(unittest.TestCase):
    def test_range_doubles_inland(self):
        M, H, hyd = continent()
        ex = {}
        g.climate(1, M, H, hyd, 50.0, 0.0, {}, extra=ex)
        tr = ex["trange"]
        kmu = g.climate_km_per_unit(50.0, 0.0)
        dw, de = g.coast_distances(dict(x=M["X"], ocean=hyd["ocean"], nx=M["nx"]), kmu)
        for lo, hi in ((10, 20), (30, 40), (40, 50)):
            cells = [c for c in range(len(H)) if not hyd["ocean"][c] and lo <= g.lat_of(M["Y"][c], 50, 0) < hi]
            wd = g.wind_dir((lo + hi) / 2.0)
            inland = [tr[c] for c in cells if min(dw[c], de[c]) >= 1500]
            coast = [tr[c] for c in cells if (dw[c] if wd > 0 else de[c]) <= 30 * kmu]
            self.assertTrue(inland and coast)
            self.assertGreaterEqual(mean(inland) / mean(coast), 2.0)   # measured 2.12-2.24

    def test_annual_range_function(self):
        self.assertAlmostEqual(g.annual_range(0, 0), 1.0)
        self.assertGreater(g.annual_range(50, 2000), 2 * g.annual_range(50, 50))


class Snowline(unittest.TestCase):
    def test_points(self):
        self.assertEqual(g.snowline_m(0), 5000.0)
        self.assertEqual(g.snowline_m(45), 2700.0)
        self.assertEqual(g.snowline_m(-62), 900.0)

    def alpine_share(self, lat, metres):
        M, H, hyd = continent(lt=lat + 0.5, lb=lat - 0.5, x0=0.0, x1=W, sp=50.0, h=metres / g.ELEV_LAND)
        _t, _p, b = g.climate(1, M, H, hyd, lat + 0.5, lat - 0.5, {})
        land = [v for c, v in enumerate(b) if not hyd["ocean"][c]]
        return sum(1 for v in land if v == g.BIOME_ID["alpine"]) / float(len(land))

    def test_equator_3000_m_is_not_alpine_but_60_deg_1200_m_is(self):
        self.assertEqual(self.alpine_share(0.0, 3000.0), 0.0)
        self.assertEqual(self.alpine_share(60.0, 1200.0), 1.0)


class UpwindAndCells(unittest.TestCase):
    def edge_rain(self, upwind):
        M, H, hyd = continent(lt=45.0, lb=40.0, x0=0.0, x1=W, sp=20.0)
        _t, p, _b = g.climate(1, M, H, hyd, 45.0, 40.0, dict(upwind=upwind))
        nx = M["nx"]
        return mean([p[j * nx] for j in range(M["ny"])])   # westerlies: the west column is upwind

    def test_land_upwind_is_drier(self):
        self.assertLess(self.edge_rain("land"), 0.4 * self.edge_rain("sea"))

    def test_hadley_edge_moves_winds_and_dry_belt(self):
        self.assertEqual(g.wind_dir(32), 1)
        self.assertEqual(g.wind_dir(32, hadley=35.0), -1)
        lats = [a / 10.0 for a in range(150, 450)]
        low = min(lats, key=lambda a: g.lat_wetness(a, hadley=35.0))
        self.assertLessEqual(abs(low - 0.9 * 35.0), 2.0)

    def test_defaults_match_model_one_wetness(self):
        for a in range(0, 91, 3):
            self.assertEqual(g.lat_wetness(a), g.lat_wetness(a, 30.0, 60.0))


class Koppen(unittest.TestCase):
    # station normals, rounded (monthly mean C, monthly total mm), Jan..Dec
    STATIONS = {
        "Af": ([26.6, 27.1, 27.6, 28.0, 28.3, 28.3, 27.9, 27.8, 27.6, 27.6, 27.1, 26.6],
               [222, 115, 170, 166, 171, 132, 153, 149, 138, 155, 255, 288], 1.3),      # Singapore
        "BWh": ([14.0, 15.3, 17.7, 21.5, 24.9, 27.4, 28.1, 28.0, 26.5, 23.8, 19.3, 15.6],
                [5, 4, 4, 1, 1, 0, 0, 0, 0, 1, 4, 6], 30.1),                              # Cairo
        "Cfb": ([5.2, 5.3, 7.6, 9.9, 13.3, 16.5, 18.7, 18.5, 15.7, 12.0, 8.0, 5.5],
                [55, 41, 42, 44, 49, 45, 45, 50, 49, 69, 59, 55], 51.5),                  # London
        "Dfb": ([-6.5, -6.7, -1.0, 6.7, 13.2, 17.0, 19.2, 17.0, 11.3, 5.6, -0.6, -4.6],
                [52, 41, 35, 37, 49, 80, 85, 82, 68, 71, 55, 52], 55.8),                  # Moscow
        "ET": ([-25.6, -26.7, -25.8, -17.9, -6.4, 1.6, 4.7, 3.4, -0.9, -9.5, -18.5, -23.2],
               [3, 3, 3, 3, 3, 8, 25, 25, 15, 10, 5, 4], 71.3),                            # Utqiagvik (Barrow)
    }

    def test_five_stations(self):
        for want, (t, p, lat) in self.STATIONS.items():
            self.assertEqual(g.koppen(t, p, lat), want, want)

    def test_world_every_land_cell_one_class(self):
        with tempfile.TemporaryDirectory() as d:
            g.gen_world(7, 1200, d)
            rc = json.load(open(os.path.join(d, "recipe.json")))
            m = json.load(open(os.path.join(d, "mesh.json")))
            self.assertEqual(rc["params"]["climate"]["model"], 2)
            kc, bad = g.koppen_counts(rc, m)
            land = sum(1 for c in range(len(m["x"])) if not m["ocean"][c] and m["lake"][c] < 0)
            self.assertEqual(bad, 0)
            self.assertEqual(sum(kc.values()), land)
            bars = g.climate_bars(rc, m)
            self.assertEqual([b for b in bars if b[1] is False], [])


class ModelOne(unittest.TestCase):
    def test_model_one_recipe_has_no_climate_key_and_regenerates(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a"), os.path.join(d, "b")
            g.gen_world(5, 800, a, climate_opts=None)
            rc = json.load(open(os.path.join(a, "recipe.json")))
            self.assertNotIn("climate", rc["params"])
            self.assertNotIn("trange", json.load(open(os.path.join(a, "mesh.json"))))
            g.regenerate(a, b)
            for f in g.FILES:
                with open(os.path.join(a, f), "rb") as x, open(os.path.join(b, f), "rb") as y:
                    self.assertEqual(x.read(), y.read(), f)


if __name__ == "__main__":
    unittest.main()
