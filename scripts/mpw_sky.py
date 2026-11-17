"""mapwright sky charts: stars from RA/Dec onto a stereographic or sinusoidal chart.

Input: a CSV with columns ra,dec,mag,name (RA and Dec in degrees, J2000 unless --epoch says otherwise).
Standard library only. The chart states its five descriptors (sky area, orientation, projection, epoch,
magnitude limit) in the margin and in a JSON sidecar, and check() fails a chart that leaves one out.
"""
import csv
import json
import math
from xml.sax.saxutils import escape

W, H = 900, 700
MARGIN = 60
PROJECTIONS = ("stereographic", "sinusoidal")
ORIENTATIONS = ("sky", "globe")  # sky: as seen from Earth, east left when north is up; globe: mirrored
DESCRIPTORS = ("sky_area", "orientation", "projection", "epoch", "mag_limit")
R_STEP = 1.3   # each magnitude brighter multiplies the dot radius by this
R_FAINT = 1.2  # radius of the faintest step, px
SANS = "'Helvetica Neue', Arial, sans-serif"


def read_stars(path):
    """Rows of a ra,dec,mag,name CSV (lines starting with # are skipped)."""
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        rows = csv.DictReader(line for line in f if line.strip() and not line.startswith("#"))
        for r in rows:
            try:
                out.append(dict(ra=float(r["ra"]), dec=float(r["dec"]), mag=float(r["mag"]),
                                name=(r.get("name") or "").strip()))
            except (KeyError, TypeError, ValueError):
                raise ValueError("%s: every row needs numeric ra, dec, mag (degrees, degrees, magnitude)" % path)
    if not out:
        raise ValueError("%s: no stars" % path)
    return out


def project(ra, dec, ra0, dec0, projection="stereographic", orientation="sky"):
    """Sky position to plane x (east positive before orientation), y north up. Unit sphere radians scale."""
    if projection not in PROJECTIONS:
        raise ValueError("unknown projection %r; projections: %s" % (projection, ", ".join(PROJECTIONS)))
    if orientation not in ORIENTATIONS:
        raise ValueError("unknown orientation %r; orientations: %s" % (orientation, ", ".join(ORIENTATIONS)))
    da = math.radians(((ra - ra0 + 180.0) % 360.0) - 180.0)
    d, d0 = math.radians(dec), math.radians(dec0)
    if projection == "stereographic":
        cosc = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(da)
        if cosc <= -0.999:
            return None
        k = 2.0 / (1.0 + cosc)
        x = k * math.cos(d) * math.sin(da)
        y = k * (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(da))
    else:  # sinusoidal about the central hour line
        x = da * math.cos(d)
        y = d
    # x is east-positive here. Seen from below, east lies to the left of north-up: flip for the sky view.
    return (-x if orientation == "sky" else x), y


def mag_steps(mags, mag_limit):
    """Integer magnitude steps from the brightest star to the limit."""
    lo = math.floor(min(mags))
    return list(range(int(lo), int(math.floor(mag_limit)) + 1))


def radius(mag, mag_limit):
    """Dot radius for a magnitude: rounded to its step, R_STEP times larger per magnitude brighter."""
    step = min(round(mag), math.floor(mag_limit))
    return R_FAINT * R_STEP ** (math.floor(mag_limit) - step)


def _centre(stars):
    xs = [math.cos(math.radians(s["ra"])) for s in stars]
    ys = [math.sin(math.radians(s["ra"])) for s in stars]
    ra0 = math.degrees(math.atan2(sum(ys), sum(xs))) % 360.0
    decs = [s["dec"] for s in stars]
    return ra0, (min(decs) + max(decs)) / 2.0


def sky_area(stars):
    ras = sorted(s["ra"] for s in stars)
    decs = [s["dec"] for s in stars]
    return "RA %.1fh to %.1fh, Dec %+.0f to %+.0f deg" % (ras[0] / 15, ras[-1] / 15, min(decs), max(decs))


def render(stars, projection="stereographic", orientation="sky", epoch="J2000", mag_limit=6.0,
           centre=None, title=None):
    """Returns (svg, descriptor dict)."""
    import mpw_render as R
    stars = [s for s in stars if s["mag"] <= mag_limit]
    if not stars:
        raise ValueError("no star at or brighter than the magnitude limit %.1f" % mag_limit)
    ra0, dec0 = centre or _centre(stars)
    pts = [project(s["ra"], s["dec"], ra0, dec0, projection, orientation) for s in stars]
    keep = [(s, p) for s, p in zip(stars, pts) if p is not None]
    xs = [p[0] for _, p in keep]
    ys = [p[1] for _, p in keep]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-6) * 1.15
    sc = min(W - 2 * MARGIN, H - 2 * MARGIN - 60) / span
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    top = MARGIN + 30

    def to_px(p):
        return W / 2 + (p[0] - cx) * sc, top + (H - 2 * MARGIN - 60) / 2 - (p[1] - cy) * sc

    desc = dict(sky_area=sky_area(stars), orientation=orientation, projection=projection, epoch=epoch,
                mag_limit=mag_limit, centre=[round(ra0, 4), round(dec0, 4)], grid="equatorial")
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
         '<rect width="100%" height="100%" fill="#0b1026"/>',
         '<clipPath id="chart"><rect x="%d" y="%d" width="%d" height="%d"/></clipPath>'
         % (MARGIN, top - 10, W - 2 * MARGIN, H - 2 * MARGIN - 40)]
    # equatorial grid: RA lines every hour, Dec lines every 10 degrees, over the charted area plus a margin
    decs = [s["dec"] for s, _ in keep]
    dlo, dhi = max(-90, math.floor(min(decs) / 10) * 10 - 20), min(90, math.ceil(max(decs) / 10) * 10 + 20)
    paths = []
    for h in range(24):
        seg = [project(h * 15.0, d, ra0, dec0, projection, orientation) for d in range(dlo, dhi + 1)]
        paths.append(seg)
    for d in range(dlo, dhi + 1, 10):
        seg = [project(r / 4.0, d, ra0, dec0, projection, orientation) for r in range(0, 1441)]
        paths.append(seg)
    gd = []
    for seg in paths:
        run = []
        for p in seg + [None]:
            if p is None or abs(p[0] - cx) * sc > W or abs(p[1] - cy) * sc > H:
                if len(run) > 1:
                    gd.append("M" + "L".join("%.1f %.1f" % q for q in run))
                run = []
            else:
                run.append(to_px(p))
    o.append('<path class="grid" clip-path="url(#chart)" d="%s" stroke="#33407a" stroke-width="0.6" fill="none"/>'
             % "".join(gd))
    o.append('<g class="stars" fill="#ffffff">')
    placed = []
    for s, p in sorted(keep, key=lambda sp: sp[0]["mag"]):
        x, y = to_px(p)
        r = radius(s["mag"], mag_limit)
        o.append('<circle cx="%.1f" cy="%.1f" r="%.2f" data-mag="%.2f"/>' % (x, y, r, s["mag"]))
        placed.append((s, x, y, r))
    o.append("</g>")
    # labels: try four spots beside the dot, drop the label when none is free (never overlap)
    reserved = [(x - r, y - r, x + r, y + r) for _, x, y, r in placed]
    boxes, lab = [], []
    for s, x, y, r in placed:
        if not s["name"]:
            continue
        for dx, dy, anchor in ((r + 3, 4, "start"), (-r - 3, 4, "end"), (0, -r - 4, "middle"), (0, r + 12, "middle")):
            b = R.text_box(x + dx, y + dy, 11, s["name"], anchor, 0.0, 0.0, 1.0)
            if b[0] < MARGIN or b[2] > W - MARGIN or b[1] < top - 10 or b[3] > H - MARGIN - 30:
                continue
            if any(R.overlap(b, q) for q in boxes) or any(R.overlap(b, q) for q in reserved):
                continue
            boxes.append(b)
            lab.append('<text x="%.1f" y="%.1f" font-size="11" text-anchor="%s">%s</text>'
                       % (x + dx, y + dy, anchor, escape(s["name"])))
            break
    o.append('<g class="labels" font-family="%s" fill="#e9ecff">' % escape(SANS, {"'": "&apos;"}))
    o.extend(lab)
    o.append("</g>")
    # magnitude legend: one entry per step
    steps = mag_steps([s["mag"] for s, _ in keep], mag_limit)
    o.append('<g class="legend" font-family="%s" font-size="10" fill="#e9ecff">' % escape(SANS, {"'": "&apos;"}))
    lx = MARGIN
    ly = H - MARGIN + 10
    o.append('<text x="%d" y="%d">magnitude</text>' % (lx, ly + 4))
    lx += 70
    for m in steps:
        r = radius(m, mag_limit)
        o.append('<circle class="legend-mag" cx="%.1f" cy="%d" r="%.2f" data-mag="%d" fill="#ffffff"/>' % (lx + r, ly, r, m))
        o.append('<text x="%.1f" y="%d">%d</text>' % (lx + 2 * r + 3, ly + 4, m))
        lx += 2 * r + 24
    o.append("</g>")
    # the five statements in the top margin
    line = "%s | %s view | %s projection | epoch %s | to magnitude %g" % (
        desc["sky_area"], "sky (as seen from Earth)" if orientation == "sky" else "globe (mirrored)",
        projection, epoch, mag_limit)
    o.append('<g class="descriptor" font-family="%s" font-size="11" fill="#c9d4ff">' % escape(SANS, {"'": "&apos;"}))
    if title:
        o.append('<text x="%d" y="%d" font-size="16">%s</text>' % (MARGIN, MARGIN - 28, escape(title)))
    o.append('<text x="%d" y="%d">%s</text>' % (MARGIN, MARGIN - 8, escape(line)))
    o.append("</g>")
    o.append('<metadata id="sky-descriptor">%s</metadata>' % escape(json.dumps(desc, sort_keys=True)))
    o.append("</svg>")
    return "\n".join(o) + "\n", desc


def check(desc, svg=None):
    """Bars (name, ok, detail): the five statements, then the legend and the label bars when the SVG is given."""
    import mpw_render as R
    miss = [k for k in DESCRIPTORS if desc.get(k) in (None, "")]
    bars = [("sky chart states area, orientation, projection, epoch, magnitude limit", not miss,
             ("missing: " + ", ".join(miss)) if miss else "all five stated")]
    if svg is not None:
        import xml.etree.ElementTree as ET
        ns = "{http://www.w3.org/2000/svg}"
        root = ET.fromstring(svg.encode("utf-8"))
        leg = [c for c in root.iter(ns + "circle") if c.get("class") == "legend-mag"]
        rs = [float(c.get("r")) for c in leg]
        mono = all(a > b for a, b in zip(rs, rs[1:]))
        ratios = [a / b for a, b in zip(rs, rs[1:])]
        fixed = all(abs(q - R_STEP) < 0.01 * R_STEP for q in ratios)
        bars.append(("magnitude legend: one entry per step, radii strictly decreasing in fixed steps",
                     bool(leg) and mono and fixed, "%d entries, ratios %s" % (len(leg), ", ".join("%.2f" % q for q in ratios))))
        bars += R.label_bars(svg)[:2]  # overlap and edge; OCR is the map check's job
    return bars


def sky_conventions(desc):
    """Period-lint conventions this chart draws."""
    used = {"equatorial-grid", "magnitude-scale", desc["projection"]}
    if str(desc.get("epoch", "")).upper().replace(".0", "") in ("J2000", "2000"):
        used.add("epoch-2000")
    return used
