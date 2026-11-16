"""Measurement harness for `mpw.py aistyle` (not a unit test; needs a ComfyUI server and Chrome or Edge).

Runs looks x seeds x denoise values on one world or region recipe and tables how well each styled
picture holds the recipe's coast. The numbers in TESTS.md (T-20261115-5) came from this file.

  python tests/aistyle_grid.py WORLD OUTDIR [--looks a,b] [--seeds 1,2,3] [--denoise 0.35,0.45,0.55,0.65]
  python tests/aistyle_grid.py WORLD OUTDIR --control none,canny --strength 0.6,0.9   (ControlNet cells)
  python tests/aistyle_grid.py WORLD OUTDIR --measure-only     (re-measure pictures already in OUTDIR)

The server comes from --host or MAPWRIGHT_COMFYUI. Finished pictures are skipped, so a run can resume.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw_aistyle as A  # noqa: E402
import mpw_read as RD  # noqa: E402


def rule_iou(img, tr):
    """Cross-check with the fixed colour rules of mpw_read.classify (water = blue): land = not water."""
    w, h = img.w, img.h
    lut, got = {}, []
    for row in img.rows:
        bits = []
        for r, g, b in zip(row[0::3], row[1::3], row[2::3]):
            k = (r >> 3, g >> 3, b >> 3)
            v = lut.get(k)
            if v is None:
                v = lut[k] = "0" if RD.classify(r, g, b) == "water" else "1"
            bits.append(v)
        got.append(int("".join(bits), 2))
    got = A._erode(A._dilate(got, w, 1), w, 1)
    got = A._dilate(A._erode(got, w, 1), w, 1)
    band = [0] * h
    for x, y, _, _, _ in tr["rivers"]:
        A._set(band, w, int(x), int(y))
    full = (1 << w) - 1
    keep = [full & ~(a | b) for a, b in zip(A._dilate(band, w, A.RIVER_REACH), A._dilate(tr["lakes"], w, 2))]
    i = u = 0
    for a, b, k in zip(got, tr["land"], keep):
        i += bin(a & b & k).count("1")
        u += bin((a | b) & k).count("1")
    return round(i / float(u), 4)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("world")
    ap.add_argument("outdir")
    ap.add_argument("--looks", default=",".join(sorted(A.LOOKS)))
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--denoise", default="0.35,0.45,0.55,0.65")
    ap.add_argument("--control", default="none", help="comma list of none, canny, depth")
    ap.add_argument("--strength", default="0.9", help="comma list of ControlNet strengths (ignored for none)")
    ap.add_argument("--host")
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--json", help="also write every row to this file")
    a = ap.parse_args(argv)
    os.makedirs(a.outdir, exist_ok=True)
    if not a.measure_only:
        for lk in a.looks.split(","):
            for d in [float(v) for v in a.denoise.split(",")]:
                for ctl in a.control.split(","):
                    sts = [None] if ctl == "none" else [float(v) for v in a.strength.split(",")]
                    for st in sts:
                        tag = "" if ctl == "none" else "-%s%03d" % (ctl, round(st * 100))
                        for s in [int(v) for v in a.seeds.split(",")]:
                            out = os.path.join(a.outdir, "%s%s-s%d-d%03d.svg" % (lk, tag, s, round(d * 100)))
                            if os.path.isfile(out[:-4] + A.SIDECAR):
                                continue
                            r = A.run(a.world, lk, out=out, host=a.host, denoise=d, seed=s, do_measure=False,
                                      control=ctl, strength=st)
                            print("%s %.0f s" % (os.path.basename(out), r["seconds"]), flush=True)
    tr, rows, controls, cimgs = None, [], {}, {}
    for sc_path in sorted(glob.glob(os.path.join(a.outdir, "*" + A.SIDECAR))):
        with open(sc_path, encoding="utf-8") as f:
            sc = json.load(f)
        img = RD.load_image(os.path.join(a.outdir, sc["files"]["styled"]))
        if tr is None:
            tr = A.truth(a.world, img.w, img.h)
        lk = sc["look"]
        if lk not in controls:
            cimgs[lk] = RD.load_image(os.path.join(a.outdir, sc["files"]["control"]))
            controls[lk] = A.measure(a.world, cimgs[lk], tr, cimgs[lk])
            controls[lk]["rule_iou"] = rule_iou(cimgs[lk], tr)
        m = A.measure(a.world, img, tr, cimgs[lk])
        m["rule_iou"] = rule_iou(img, tr)
        m["ok"] = A.judge(m)[0]
        cn = sc.get("controlnet") or {}
        m.update(look=lk, seed=sc["seed"], denoise=sc["denoise"], runs_as=sc["denoise_effective"],
                 control="%s %.2f" % (cn["kind"], cn["strength"]) if cn else "none")
        rows.append(m)

    def mean(v):
        return sum(v) / float(len(v))

    print("clean render (control picture), per look: land IoU, fixed-rule IoU, lakes read as water, line noise floor")
    for lk, c in sorted(controls.items()):
        print("  %-18s %.4f %.4f %.2f %.3f" % (lk, c["land_iou"], c["rule_iou"], c["lakes_kept"] or 0,
                                               c["river_line_noise"] or 0))
    print("look, control and strength, denoise typed (as run), pictures passing, land IoU min/mean/max, coast within 3 px, settlements "
          "on painted land min, rivers on painted land min, lakes kept, river lines kept, line noise floor")
    for lk, ctl, d in sorted(set((m["look"], m["control"], m["denoise"]) for m in rows)):
        g = [m for m in rows if m["look"] == lk and m["denoise"] == d and m["control"] == ctl]
        io = [m["land_iou"] for m in g]
        print("  %-18s %-11s %.2f (%.3f) %d/%d  %.4f/%.4f/%.4f  %.2f  %.4f  %.4f  %.2f  %.2f  %.3f"
              % (lk, ctl, d, g[0]["runs_as"], sum(1 for m in g if m["ok"]), len(g), min(io), mean(io), max(io),
                 mean([m["coast_within_3px"] for m in g]), min(m["towns_on_land"] for m in g),
                 min(m["river_on_land"] for m in g), mean([m["lakes_kept"] or 0 for m in g]),
                 mean([m["river_line"] or 0 for m in g]), mean([m["river_line_noise"] or 0 for m in g])))
    for ctl, d in sorted(set((m["control"], m["denoise"]) for m in rows)):
        g = [m for m in rows if m["denoise"] == d and m["control"] == ctl]
        print("%s, denoise %.2f: %d of %d pictures pass the bar" % (ctl, d, sum(1 for m in g if m["ok"]), len(g)))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dict(controls=controls, rows=rows), f, indent=1)


if __name__ == "__main__":
    main()
