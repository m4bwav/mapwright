"""Proof bar for `trace`: render a generated world, trace its water back, measure coastline agreement.

Run: python tests/roundtrip_trace.py [--seeds 7,11,23] [--cells 4000] [--chrome]
Without --chrome the land/sea raster the renderer draws is written as a PNG with the stdlib (no
labels, no line work). With --chrome the full map (labels, roads, rivers, legend) is rendered to PNG
by headless Chrome or Edge, the harder case. Distances are in output pixels (1 px = 1 km here).
"""
import argparse
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw_gen as G  # noqa: E402
import mpw_read as R  # noqa: E402
import mpw_render as RD  # noqa: E402


def reference_lines(d, scale, lakes=True):
    """Coast lines and lake rings of a recipe, in picture pixels (y down)."""
    fc = G.load(d, "features.geojson")
    out = []
    for f in fc["features"]:
        k, g = f["properties"]["kind"], f["geometry"]
        if k == "coast" and g["type"] == "LineString":
            out.append([(c[0] / 1000.0 * scale, (G.WORLD - c[1] / 1000.0) * scale) for c in g["coordinates"]])
        elif k == "lake" and lakes:
            for poly in g["coordinates"]:
                for ring in poly:
                    out.append([(c[0] / 1000.0 * scale, (G.WORLD - c[1] / 1000.0) * scale) for c in ring])
    return out


def raster_png(d, path, px=512):
    rc, m, _ = RD.load(d)
    rc = dict(rc, params=dict(rc["params"], raster_px=px))
    rows = RD.land_rows(rc, m, RD.style("topographic"))
    with open(path, "wb") as f:
        f.write(R.png_rgb_bytes(len(rows[0]) // 3, len(rows), rows))
    return len(rows[0]) // 3


def measure(d, png, scale, eps=1.0, lakes=True, fill_holes=0.0):
    t0 = time.perf_counter()
    fc = R.trace(png, "water", eps=eps, min_area=64.0, fill_holes=fill_holes)
    t_trace = time.perf_counter() - t0
    traced = [ring for f in fc["features"] for ring in f["geometry"]["coordinates"]]
    ref = reference_lines(d, scale, lakes)
    # drop traced edges along the picture frame: the recipe has no coast there
    W = fc["mapwright"]["width"]
    H = fc["mapwright"]["height"]

    def interior(ln):
        return [p for p in ln if 3 < p[0] < W - 3 and 3 < p[1] < H - 3]
    traced_i = [x for x in (interior(ln) for ln in traced) if x]
    ref_dense = [densify(ln, 2.0) for ln in ref]
    a = R.polyline_distance_stats(ref_dense, traced)    # recipe coast -> traced
    b = R.polyline_distance_stats(traced_i, ref)        # traced -> recipe coast
    return {"recipe_to_traced": a, "traced_to_recipe": b, "features": len(fc["features"]),
            "trace_s": round(t_trace, 2)}


def densify(ln, step):
    out = [ln[0]]
    for p, q in zip(ln, ln[1:]):
        L = ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5
        n = max(1, int(L // step))
        for i in range(1, n + 1):
            out.append((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7,11,23")
    ap.add_argument("--cells", type=int, default=4000)
    ap.add_argument("--chrome", action="store_true")
    ap.add_argument("--fill-holes", type=float, default=0.0)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="mpw-rt-")
    res = {}
    for seed in [int(s) for s in a.seeds.split(",")]:
        d = os.path.join(tmp, "w%d" % seed)
        G.gen_world(seed, a.cells, d)
        if not os.path.isfile(os.path.join(d, "recipe.json")):
            import subprocess
            subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "scripts", "mpw.py"), "gen", "world",
                            "--seed", str(seed), "--cells", str(a.cells), "--out", d], check=True,
                           stdout=subprocess.DEVNULL)
        png = os.path.join(tmp, "w%d.png" % seed)
        if a.chrome:
            t0 = time.perf_counter()
            svg, _ = RD.render_svg(d)
            RD.write_out(svg, png)
            scale, t_r = 1.0, time.perf_counter() - t0
        else:
            t0 = time.perf_counter()
            w = raster_png(d, png)
            scale, t_r = w / G.WORLD, time.perf_counter() - t0
        r = measure(d, png, scale, lakes=a.chrome, fill_holes=a.fill_holes)
        r["render_s"] = round(t_r, 2)
        res[seed] = r
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
