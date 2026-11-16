"""mapwright aistyle: an optional AI style pass over a clean render.

The route: geometry from code, a clean render without roads, symbols, labels or furniture (the
control picture), an img2img pass on a ComfyUI server with that picture as the init image, then
roads, symbols, labels, legend, scale bar and north arrow set in code on top of the result.
The model never owns geometry or text. The coast and the rivers are measured before and after.

Standard library only: urllib talks to the server, the PNG reader in mpw_read reads the result.
"""
import base64
import datetime
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import mpw_gen as G
import mpw_read as RD
import mpw_render as R

ENV_HOST = "MAPWRIGHT_COMFYUI"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEFAULT_TEMPLATE = os.path.join(DATA, "aistyle-zimage-turbo.json")
PREFIX = "mapwright-aistyle"
SIDECAR = ".aistyle.json"

# ------------------------------------------------------------------ looks
NEGATIVE = "text, letters, words, labels, watermark, signature, legend, compass rose, scale bar, border, frame"
LOOKS = {
    "painted-atlas": dict(
        base="atlas", desc="gouache atlas plate: soft greens, painted relief, pale blue sea",
        prompt="A hand-painted atlas map seen from directly above, gouache and watercolour on smooth paper. "
               "Soft green lowlands, ochre and brown mountains with painted relief shading, pale blue sea with "
               "slightly deeper blue offshore, thin blue rivers, a crisp dark coastline. Flat top-down "
               "cartographic view, even light, fine brushwork, plain unmarked paper in open areas."),
    "ink-and-parchment": dict(
        base="ink-and-parchment", desc="brown ink on aged parchment, hachures, shore lines",
        prompt="An antique map drawn in brown ink on aged parchment, seen from directly above. A fine pen "
               "coastline with short hatched water lines along the shore, ink-drawn rivers, small hachure "
               "strokes for hills and mountains, warm tan vellum with soft stains and fibres. Flat top-down "
               "cartographic view, sepia line work, plain blank parchment in open areas."),
    "satellite": dict(
        base="satellite", desc="natural-colour orbital picture: deep ocean, forest, bare ground, relief",
        prompt="A satellite photograph of land and ocean seen from directly above, natural colour. Deep blue "
               "ocean, dark green forest, olive grassland, tan dry ground, rugged mountain relief with sharp "
               "shadows, fine river channels, a crisp shoreline with a thin band of shallow turquoise water. "
               "Orbital imagery, high detail, clear cloudless air."),
    "watercolour": dict(
        base="topographic", desc="loose washes on cold-press paper",
        prompt="A loose watercolour map seen from directly above on cold-press paper. Wet washes of green, "
               "yellow and warm brown for the land, a soft blue wash for the sea with a darker edge along "
               "the shore, thin blue rivers, visible paper grain and granulating pigment. Flat top-down "
               "cartographic view, light and airy, plain blank paper in open areas."),
}
DEFAULT_DENOISE = 0.45
# Proof bar, set from the measurements in TESTS.md (0.8.0 table). Never loosen without a new measurement.
DENOISE_CEILING = 0.45      # typed value; above it the coast drifts on the measured looks
TOL_LAND_IOU = 0.92         # land IoU of the styled picture against the recipe's own land mask
TOL_RIVER_LAND = 0.98       # share of code-set river samples with painted land within RIVER_REACH px
TOL_TOWNS_LAND = 0.94       # share of settlements with painted land within RIVER_REACH px
GUARD_PX = 12               # the classifier trains only on pixels this far from the true coast
RIVER_REACH = 3             # px: river band left out of the IoU, and the reach of the river tests
RIVER_SIDE = 5              # px from the line centre to the two side samples of the line test
RIVER_VISIBLE = 20.0        # RGB distance from both sides a river needs in the clean render to be sampled
RIVER_KEEP = 0.33           # share of the clean render's line contrast the styled picture must keep
RIVER_MIN = 8.0             # and at least this much, in RGB units
RIVER_SHIFT = 14            # px: the same test on lines shifted sideways gives the noise floor


def look(name):
    if name not in LOOKS:
        raise ValueError("unknown look %r; looks: %s" % (name, ", ".join(sorted(LOOKS))))
    return LOOKS[name]


# ------------------------------------------------------------------ workflow template
def load_template(path=None):
    with open(path or DEFAULT_TEMPLATE, encoding="utf-8") as f:
        t = json.load(f)
    for k in ("name", "model", "settings", "workflow"):
        if k not in t:
            raise ValueError("%s: workflow template lacks %r" % (path or DEFAULT_TEMPLATE, k))
    return t


def fill(node, slots):
    """Replace whole-value '{SLOT}' strings; the typed slot value goes in (a seed stays an int)."""
    if isinstance(node, dict):
        return {k: fill(v, slots) for k, v in node.items()}
    if isinstance(node, list):
        return [fill(v, slots) for v in node]
    if isinstance(node, str) and len(node) > 2 and node[0] == "{" and node[-1] == "}":
        key = node[1:-1]
        if key not in slots:
            raise ValueError("workflow template names an unknown slot %s" % node)
        return slots[key]
    return node


def workflow_hash(wf):
    return hashlib.sha256(json.dumps(wf, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def effective_denoise(steps, d):
    """The denoise KSampler really runs: `steps` steps from the tail of an int(steps / d) step schedule."""
    if d >= 0.9999:
        return 1.0
    if d <= 0:
        return 0.0
    return steps / float(int(steps / d))


def model_size(w, h, size=1024, mult=16):
    """Picture size for the model: long side `size`, both sides multiples of `mult`."""
    size = max(mult, int(round(size / float(mult))) * mult)
    if w >= h:
        return size, max(mult, int(round(h / float(w) * size / mult)) * mult)
    return max(mult, int(round(w / float(h) * size / mult)) * mult), size


# ------------------------------------------------------------------ control picture and composite
def _resize_head(head, wm, hm):
    vb = head.split('viewBox="')[1].split('"')[0]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s" preserveAspectRatio="none">'
            % (wm, hm, vb))


def control_svg(p, wm, hm):
    """The map without roads, symbols, labels or furniture, at the model's pixel size."""
    return "\n".join([_resize_head(p["head"][0], wm, hm)] + p["ground"] + p["water"] + p["coast"] + ["</svg>"]) + "\n"


def code_layer(p):
    """What is set in code on top of the styled picture: lakes and rivers, then roads, symbols, labels,
    title, legend, scale bar, north arrow and frame. Line for line the labelled render's own lines."""
    return p["water"] + p["over"]


def composite_svg(p, styled_png, wm, hm):
    """The styled picture under the code-set layer."""
    vb = p["head"][0].split('viewBox="')[1].split('"')[0].split()
    img = ('<image class="aistyle" href="data:image/png;base64,%s" width="%s" height="%s" preserveAspectRatio="none"/>'
           % (base64.b64encode(styled_png).decode("ascii"), vb[2], vb[3]))
    return "\n".join([_resize_head(p["head"][0], wm, hm), img] + code_layer(p) + ["</svg>"]) + "\n"


def layer_of(svg, cls):
    """The lines of one group of a rendered SVG by its class: labels, rivers, legend, scalebar, north."""
    lines = svg.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith('<g class="%s"' % cls):
            return lines[i:lines.index("</g>", i) + 1]
    return []


# ------------------------------------------------------------------ bit-row masks
def _pc(rows):
    return sum(bin(x).count("1") for x in rows)


def _dilate(rows, w, r=1):
    full = (1 << w) - 1
    hx = []
    for x in rows:
        y = x
        for i in range(1, r + 1):
            y |= (x << i) | (x >> i)
        hx.append(y & full)
    n = len(rows)
    out = []
    for j in range(n):
        y = 0
        for k in range(max(0, j - r), min(n, j + r + 1)):
            y |= hx[k]
        out.append(y)
    return out


def _not(rows, w):
    full = (1 << w) - 1
    return [full ^ x for x in rows]


def _erode(rows, w, r=1):
    return _not(_dilate(_not(rows, w), w, r), w)


def _and(a, b):
    return [x & y for x, y in zip(a, b)]


def _edge(rows, w):
    """Inner boundary pixels of a mask."""
    return [x & ~e for x, e in zip(rows, _erode(rows, w, 1))]


def _rows_from_flags(flags, w):
    return [int("".join("1" if v else "0" for v in row), 2) for row in flags]


def _set(rows, w, x, y):
    if 0 <= y < len(rows) and 0 <= x < w:
        rows[y] |= 1 << (w - 1 - x)


def _get(rows, w, x, y):
    if 0 <= y < len(rows) and 0 <= x < w:
        return (rows[y] >> (w - 1 - x)) & 1
    return 0


# ------------------------------------------------------------------ the recipe's own masks
def truth(d, w, h):
    """Land mask, lake mask, river samples and settlement points at w x h pixels, straight from the recipe.

    Returns dict(land, lakes, rivers, towns, w, h). land and lakes are bit rows (most significant bit =
    left pixel); lakes lie inside land. rivers: (x, y, tx, ty, width_px) about every pixel along each
    river line. towns: (x, y, name).
    """
    rc, m, feats = R.load(d)
    x0, y0, x1, y1 = rc["extent"]
    M = dict(X=m["x"], Y=m["y"], tris=G._tris(m))
    Z, _, _ = G.raster(M, m["h"], m["biome"], x0, y0, x1, y1, w)
    n = len(Z)
    land = []
    cache = {}
    for r in range(h):
        k = min(n - 1, int((r + 0.5) * n / h))
        v = cache.get(k)
        if v is None:
            v = cache[k] = int("".join("1" if z >= 0 else "0" for z in Z[k]), 2)
        land.append(v)
    sx, sy = w / float(x1 - x0), h / float(y1 - y0)

    def px(c):
        return (c[0] / 1000.0 - x0) * sx, (G.WORLD - c[1] / 1000.0 - y0) * sy

    lake = [0] * h
    for f in feats:
        if f["properties"]["kind"] != "lake":
            continue
        for poly in f["geometry"]["coordinates"]:
            rings = [[px(c) for c in ring] for ring in poly]
            ys = [p[1] for ring in rings for p in ring]
            if not ys:
                continue
            for r in range(max(0, int(math.floor(min(ys)))), min(h - 1, int(math.ceil(max(ys)))) + 1):
                yc = r + 0.5
                xs = []
                for ring in rings:
                    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
                        if (ay <= yc) != (by <= yc):
                            xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
                xs.sort()
                for a, b in zip(xs[0::2], xs[1::2]):
                    c0, c1 = max(0, int(math.ceil(a - 0.5))), min(w - 1, int(math.floor(b - 0.5)))
                    if c1 >= c0:
                        lake[r] |= ((1 << (c1 - c0 + 1)) - 1) << (w - 1 - c1)
    towns = [px(f["geometry"]["coordinates"]) + (f["properties"].get("name", "?"),)
             for f in feats if f["properties"]["kind"] == "settlement"]
    thr = rc["params"]["river_threshold"]
    pts = []
    for f in feats:
        if f["properties"]["kind"] != "river":
            continue
        wd = min(3.5, 0.5 + 0.35 * math.sqrt(f["properties"]["acc"] / thr)) * sx
        line = [px(c) for c in f["geometry"]["coordinates"]]
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            L = math.hypot(bx - ax, by - ay)
            if L < 1e-9:
                continue
            tx, ty = (bx - ax) / L, (by - ay) / L
            for i in range(max(1, int(L))):
                t = (i + 0.5) / max(1, int(L))
                pts.append((ax + (bx - ax) * t, ay + (by - ay) * t, tx, ty, wd))
    return dict(land=land, lakes=lake, rivers=pts, towns=towns, w=w, h=h)


# ------------------------------------------------------------------ measuring a picture against the recipe
def _keys(img):
    out = []
    for row in img.rows:
        out.append([((r & 0xF8) << 7) | ((g & 0xF8) << 2) | (b >> 3)
                    for r, g, b in zip(row[0::3], row[1::3], row[2::3])])
    return out


def _train(keys, land_in, sea_in, w):
    """Colour table: 15-bit colour bucket -> '1' land or '0' sea, from pixels far from the coast only."""
    cl, cs = [0] * 32768, [0] * 32768
    fmt = "0%db" % w
    for ks, a, b in zip(keys, land_in, sea_in):
        if a:
            for k, bit in zip(ks, format(a, fmt)):
                if bit == "1":
                    cl[k] += 1
        if b:
            for k, bit in zip(ks, format(b, fmt)):
                if bit == "1":
                    cs[k] += 1
    nl, ns = sum(cl), sum(cs)
    if not nl or not ns:
        return None
    coarse = []
    for bits in (4, 3, 2):
        sh = 5 - bits
        tl, ts = {}, {}
        for k in range(32768):
            if cl[k] or cs[k]:
                q = ((k >> 10) >> sh, ((k >> 5) & 31) >> sh, (k & 31) >> sh)
                tl[q] = tl.get(q, 0) + cl[k]
                ts[q] = ts.get(q, 0) + cs[k]
        coarse.append((sh, tl, ts))
    ml = [sum(c * ((k >> s) & 31) for k, c in enumerate(cl) if c) / float(nl) for s in (10, 5, 0)]
    ms = [sum(c * ((k >> s) & 31) for k, c in enumerate(cs) if c) / float(ns) for s in (10, 5, 0)]
    lut = []
    for k in range(32768):
        a, b = cl[k], cs[k]
        if a == b:
            for sh, tl, ts in coarse:
                q = ((k >> 10) >> sh, ((k >> 5) & 31) >> sh, (k & 31) >> sh)
                a, b = tl.get(q, 0), ts.get(q, 0)
                if a != b:
                    break
        if a == b:
            c = ((k >> 10), (k >> 5) & 31, k & 31)
            a = -sum((c[i] - ml[i]) ** 2 for i in range(3))
            b = -sum((c[i] - ms[i]) ** 2 for i in range(3))
        lut.append("1" if a > b else "0")
    return lut


def _avg(img, x, y, tx, ty):
    """Mean colour of three pixels along the line direction."""
    rows, w, h = img.rows, img.w, img.h
    r = g = b = 0
    for j in (-1, 0, 1):
        xi = min(w - 1, max(0, int(x + j * tx)))
        yi = min(h - 1, max(0, int(y + j * ty)))
        row = rows[yi]
        r += row[3 * xi]
        g += row[3 * xi + 1]
        b += row[3 * xi + 2]
    return r / 3.0, g / 3.0, b / 3.0


def _dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _across(img, x, y, tx, ty, o, side=RIVER_SIDE):
    """`o` px sideways of (x, y): the centre colour minus the mean of the two sides `side` px away,
    and the smaller of the two centre-to-side colour distances."""
    nx, ny = -ty, tx
    cx, cy = x + o * nx, y + o * ny
    c = _avg(img, cx, cy, tx, ty)
    a = _avg(img, cx - side * nx, cy - side * ny, tx, ty)
    b = _avg(img, cx + side * nx, cy + side * ny, tx, ty)
    return ((c[0] - (a[0] + b[0]) / 2.0, c[1] - (a[1] + b[1]) / 2.0, c[2] - (a[2] + b[2]) / 2.0),
            min(_dist(c, a), _dist(c, b)))


def line_vector(img, x, y, tx, ty, reach=RIVER_REACH):
    """The clearest line across (x, y) within `reach` px sideways: (centre-minus-sides vector, contrast)."""
    best = ((0.0, 0.0, 0.0), 0.0)
    for o in range(-reach, reach + 1):
        v, c = _across(img, x, y, tx, ty, o)
        if c > best[1]:
            best = (v, c)
    return best


def line_kept(img, x, y, tx, ty, ref, reach=RIVER_REACH):
    """Does the picture still draw a line here in the colour direction `ref` (the clean render's
    centre-minus-sides vector)? True when its own vector, projected on ref, reaches RIVER_KEEP of ref."""
    n = math.sqrt(ref[0] ** 2 + ref[1] ** 2 + ref[2] ** 2)
    if n <= 0:
        return False
    need = max(RIVER_MIN, RIVER_KEEP * n)
    for o in range(-reach, reach + 1):
        v, _ = _across(img, x, y, tx, ty, o)
        if (v[0] * ref[0] + v[1] * ref[1] + v[2] * ref[2]) / n >= need:
            return True
    return False


def measure(d, picture, tr=None, control=None):
    """Compare a picture of the map (control or styled, no labels) with the recipe's own geometry.

    Land and sea are told apart by colour alone: a 15-bit colour table trained on this picture's pixels
    at least GUARD_PX from the true coast, applied to every pixel, cleaned with a 3x3 close and open.
    A coast that moved shows up as land colour where the recipe has sea, or the reverse.
    Rivers: with the clean render (`control`) at hand, a river sample counts as kept when the picture
    still differs from its two sides in the colour direction the clean render had there.
    """
    img = picture if isinstance(picture, RD.Image) else RD.load_image(picture)
    w, h = img.w, img.h
    if tr is None or (tr["w"], tr["h"]) != (w, h):
        tr = truth(d, w, h)
    land, rivers, lakes = tr["land"], tr["rivers"], tr["lakes"]
    full = (1 << w) - 1
    band = [0] * h
    for x, y, _, _, _ in rivers:
        _set(band, w, int(x), int(y))
    band = _dilate(band, w, RIVER_REACH)
    # lakes and rivers are set in code on top of the styled picture, so they are left out of the IoU
    keep = [full & ~(a | b) for a, b in zip(band, _dilate(lakes, w, 2))]
    sea = _not(land, w)
    land_in = _and(_erode(land, w, GUARD_PX), keep)
    sea_in = _and(_erode(sea, w, GUARD_PX), keep)
    keys = _keys(img)
    lut = _train(keys, land_in, sea_in, w)
    res = dict(size=[w, h], classifier="colour table trained %d px from the coast, 3x3 close and open" % GUARD_PX,
               land_share=round(_pc(land) / float(w * h), 4))
    if lut is None:
        res.update(land_iou=None, reason="the recipe has no land or no sea far enough from the coast to train on")
        return res
    raw = [int("".join([lut[k] for k in ks]), 2) for ks in keys]
    got = _erode(_dilate(raw, w, 1), w, 1)
    got = _dilate(_erode(got, w, 1), w, 1)
    inter = union = 0
    for a, b, k in zip(got, land, keep):
        inter += bin(a & b & k).count("1")
        union += bin((a | b) & k).count("1")
    res["land_iou"] = round(inter / float(union), 4) if union else None
    wrong = [(a ^ b) & k for a, b, k in zip(got, land, keep)]
    res["mismatch_share"] = round(_pc(wrong) / float(w * h), 4)
    # the sea coast: how far the painted coast sits from the true one
    true_edge = [(a | b) & full for a, b in zip(_edge(land, w), _edge(sea, w))]
    got_edge = [(a | b) & full for a, b in zip(_edge(got, w), _edge(_not(got, w), w))]
    n_edge = _pc(true_edge)
    near = true_edge
    cover = got_edge
    p95 = None
    for k in range(0, 17):
        if k:
            cover = _dilate(cover, w, 1)
            near = _dilate(near, w, 1)
        share = _pc(_and(true_edge, cover)) / float(n_edge) if n_edge else 0.0
        if p95 is None and share >= 0.95:
            p95 = k
        if k == 3:
            res["coast_within_3px"] = round(share, 4)
        if k == 4:
            res["mismatch_beyond_4px"] = round(_pc([x & ~nr for x, nr in zip(wrong, near)]) / float(w * h), 4)
    res["coast_p95_px"] = p95 if p95 is not None else ">16"
    # what the model did with the water it was shown (reported; lakes and rivers are redrawn in code)
    # lakes: a second table that also counts lake interiors as water, used for this number only
    lake_px = _pc(lakes)
    res["lakes_kept"] = None
    if lake_px:
        lut2 = _train(keys, land_in, [a | (b & ~r) for a, b, r in zip(sea_in, _erode(lakes, w, 2), band)], w)
        wet = [int("".join([lut2[k] for k in ks]), 2) ^ full for ks in keys]
        res["lakes_kept"] = round(_pc(_and(lakes, wet)) / float(lake_px), 4)
    got_near = _dilate(got, w, RIVER_REACH)
    towns = tr.get("towns") or []
    off = [nm for x, y, nm in towns if not _get(got_near, w, int(x), int(y))]
    res.update(towns=len(towns), towns_off=off,
               towns_on_land=round(1.0 - len(off) / float(len(towns)), 4) if towns else None)
    res.update(river_samples=len(rivers), river_on_land=None, river_line=None, river_line_noise=None)
    if rivers:
        res["river_on_land"] = round(sum(_get(got_near, w, int(x), int(y)) for x, y, _, _, _ in rivers)
                                     / float(len(rivers)), 4)
        cimg = control
        if cimg is not None and not isinstance(cimg, RD.Image):
            cimg = RD.load_image(cimg)
        if cimg is not None and (cimg.w, cimg.h) == (w, h):
            # the noise floor is taken where the recipe has no line: clear of rivers and shores
            busy = _dilate([a | b for a, b in zip(band, true_edge)], w, RIVER_SIDE + 2)
            seen = kept = noise = quiet = 0
            for x, y, tx, ty, _ in rivers:
                ref, c = line_vector(cimg, x, y, tx, ty)
                if c < RIVER_VISIBLE:
                    continue
                seen += 1
                kept += line_kept(img, x, y, tx, ty, ref)
                nx, ny = -ty, tx
                for s in (-RIVER_SHIFT, RIVER_SHIFT):
                    qx, qy = x + s * nx, y + s * ny
                    if not (0 <= qx < w and 0 <= qy < h) or _get(busy, w, int(qx), int(qy)):
                        continue
                    quiet += 1
                    noise += line_kept(img, qx, qy, tx, ty, ref)
            res.update(river_visible=seen, river_line=round(kept / float(seen), 4) if seen else None,
                       river_line_noise=round(noise / float(quiet), 4) if quiet else None)
    return res


def judge(m, control=None):
    """Apply the proof bar to a measurement. Returns (ok, detail). ok None = could not be measured.
    `control` (the clean render's own measurement) is quoted for scale; it is not part of the bar."""
    if m.get("land_iou") is None:
        return None, "not measured: %s" % m.get("reason", "no land IoU")
    ok = m["land_iou"] >= TOL_LAND_IOU
    bits = ["land IoU %.4f (bar %.2f%s)" % (m["land_iou"], TOL_LAND_IOU,
                                           ", clean render %.4f" % control["land_iou"]
                                           if control and control.get("land_iou") is not None else "")]
    bits.append("coast within 3 px %.2f" % m.get("coast_within_3px", 0))
    if m.get("river_on_land") is not None:
        ok = ok and m["river_on_land"] >= TOL_RIVER_LAND
        bits.append("code-set rivers on painted land %.4f (bar %.2f)" % (m["river_on_land"], TOL_RIVER_LAND))
    if m.get("towns_on_land") is not None:
        ok = ok and m["towns_on_land"] >= TOL_TOWNS_LAND
        off = m.get("towns_off") or []
        bits.append("settlements on painted land %.4f (bar %.2f)%s"
                    % (m["towns_on_land"], TOL_TOWNS_LAND, (", off it: " + ", ".join(off[:6])) if off else ""))
    kept = ["%s %.2f" % (n, m[k]) for n, k in (("lakes", "lakes_kept"), ("river lines", "river_line"))
            if m.get(k) is not None]
    if kept:
        bits.append("the model alone kept %s (reported, no bar: both are redrawn in code)" % ", ".join(kept))
    return ok, "; ".join(bits)


# ------------------------------------------------------------------ ComfyUI over HTTP
def http(method, url, data=None, headers=None, timeout=30):
    """One HTTP call. Returns (status, body bytes). Tests replace this function."""
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def resolve_host(host=None, env=None):
    host = host or (os.environ if env is None else env).get(ENV_HOST)
    if not host:
        raise ValueError("no ComfyUI server: pass --host URL or set %s (a stock local server is "
                         "http://127.0.0.1:8188)" % ENV_HOST)
    if not (host.startswith("http://") or host.startswith("https://")):
        raise ValueError("--host wants a URL starting http:// or https://, got %r" % host)
    return host.rstrip("/")


class Comfy:
    def __init__(self, host, call=None):
        self.host = host
        self.call = call or http

    def _json(self, method, path, data=None, headers=None, timeout=30):
        st, body = self.call(method, self.host + path, data, headers, timeout)
        try:
            js = json.loads(body.decode("utf-8")) if body else {}
        except ValueError:
            js = {"raw": body[:300].decode("utf-8", "replace")}
        if st != 200:
            raise RuntimeError("server answered %d on %s: %s" % (st, path, json.dumps(js)[:600]))
        return js

    def stats(self, timeout=5):
        return self._json("GET", "/system_stats", timeout=timeout)

    def choices(self, spec, timeout=10):
        """Model files a loader offers. spec: 'UNETLoader.unet_name'."""
        node, field = spec.split(".")
        js = self._json("GET", "/object_info/" + node, timeout=timeout)
        v = js[node]["input"]["required"][field]
        if v and isinstance(v[0], list):
            return v[0]
        if len(v) > 1 and isinstance(v[1], dict) and isinstance(v[1].get("options"), list):
            return v[1]["options"]
        return []

    def upload(self, name, data):
        b = "----mapwright" + hashlib.sha256(os.urandom(16)).hexdigest()[:24]
        body = b"".join([
            ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
             "Content-Type: image/png\r\n\r\n" % (b, name)).encode("ascii"), data, b"\r\n",
            ("--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n" % b).encode("ascii"),
            ("--%s\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\ninput\r\n--%s--\r\n" % (b, b)).encode("ascii")])
        js = self._json("POST", "/upload/image", body,
                        {"Content-Type": "multipart/form-data; boundary=" + b}, 120)
        return (js.get("subfolder") + "/" if js.get("subfolder") else "") + js["name"]

    def queue(self, wf):
        body = json.dumps({"prompt": wf, "client_id": "mapwright"}).encode("utf-8")
        js = self._json("POST", "/prompt", body, {"Content-Type": "application/json"}, 60)
        if "prompt_id" not in js:
            raise RuntimeError("server did not queue the workflow: %s" % json.dumps(js)[:600])
        return js["prompt_id"]

    def wait(self, pid, timeout=900, poll=1.0, sleep=time.sleep, clock=time.monotonic):
        end = clock() + timeout
        while True:
            js = self._json("GET", "/history/" + pid)
            e = js.get(pid)
            if e:
                stt = e.get("status") or {}
                if stt.get("status_str") == "error":
                    msg = [m for m in stt.get("messages", []) if m and m[0] == "execution_error"]
                    raise RuntimeError("the workflow failed on the server: %s"
                                       % (json.dumps(msg[-1][1])[:600] if msg else "no message"))
                imgs = [i for o in e.get("outputs", {}).values() for i in o.get("images", [])]
                if imgs:
                    return imgs[0]
                if stt.get("completed") or stt.get("status_str") == "success":
                    raise RuntimeError("the server finished without a picture (an identical job may be "
                                       "cached; change the seed)")
            if clock() >= end:
                raise RuntimeError("no result after %d s (job %s is still queued or running)" % (timeout, pid))
            sleep(poll)

    def fetch(self, image):
        q = urllib.parse.urlencode(dict(filename=image["filename"], subfolder=image.get("subfolder", ""),
                                        type=image.get("type", "output")))
        st, body = self.call("GET", self.host + "/view?" + q, None, None, 120)
        if st != 200 or body[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("could not download the styled picture (%d)" % st)
        return body


def doctor(host=None, template=None, call=None, env=None):
    """Does a server answer, and does it hold the template's model files? Never raises."""
    t = load_template(template)
    out = dict(env=ENV_HOST, host=None, answers=None, comfyui=None, model=t["model"].get("unet"), files={})
    try:
        out["host"] = resolve_host(host, env)
    except ValueError:
        out["note"] = "no server set (optional: pass --host or set %s)" % ENV_HOST
        return out
    c = Comfy(out["host"], call)
    try:
        out["comfyui"] = c.stats(timeout=4).get("system", {}).get("comfyui_version")
        out["answers"] = True
    except Exception as e:
        out["answers"] = False
        out["note"] = "server does not answer: %s" % e.__class__.__name__
        return out
    for key, spec in sorted(t.get("probe", {}).items()):
        try:
            out["files"][key] = t["model"].get(key) in c.choices(spec)
        except Exception:
            out["files"][key] = None
    return out


# ------------------------------------------------------------------ the pass
def sha(data):
    return hashlib.sha256(data).hexdigest()


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def plan(d, look_name, out=None, denoise=None, seed=0, template=None, model=None, clip=None, vae=None,
         size=None, style=None, font=None, title=None):
    """Everything that can be settled without a server or a browser."""
    lk = look(look_name)
    rc = G.load(d, "recipe.json")
    if rc.get("kind") not in ("world", "region"):
        raise ValueError("aistyle works on world and region recipes, not %r" % rc.get("kind"))
    t = load_template(template)
    md = dict(t["model"])
    for key, val in (("unet", model), ("clip", clip), ("vae", vae)):
        if val and val != md.get(key):
            md[key] = val
            md["licence"] = "unstated"
            md["licence_class"] = "unstated: model file overridden, read its card before shipping a picture"
    st = t["settings"]
    denoise = DEFAULT_DENOISE if denoise is None else float(denoise)
    if not 0.0 < denoise <= 1.0:
        raise ValueError("--denoise wants a value above 0 and at most 1")
    base_style = style or lk["base"]
    svg, info = R.render_parts(d, base_style, font, title)
    vb = svg["head"][0].split('viewBox="')[1].split('"')[0].split()
    wm, hm = model_size(float(vb[2]), float(vb[3]), size or st.get("size", 1024), st.get("multiple", 16))
    out = out or os.path.join(d, "aistyle-%s.png" % look_name)
    ext = os.path.splitext(out)[1].lower()
    if ext not in (".png", ".svg", ".pdf"):
        raise ValueError("--out wants .png, .svg or .pdf")
    stem = out[:-len(ext)]
    return dict(dir=d, look=look_name, base_style=base_style, prompt=lk["prompt"], negative=NEGATIVE,
                seed=int(seed), denoise=denoise, steps=int(st["steps"]), cfg=float(st["cfg"]),
                sampler=st["sampler"], scheduler=st["scheduler"],
                denoise_effective=round(effective_denoise(int(st["steps"]), denoise), 4),
                template=t, model=md, size=(wm, hm), svg=svg, info=info, recipe=rc, out=out,
                files=dict(control=stem + ".control.png", workflow=stem + ".workflow.json",
                           styled=stem + ".styled.png", sidecar=stem + SIDECAR, out=out))


def build_workflow(p, image_name):
    md = p["model"]
    slots = dict(UNET=md.get("unet"), CLIP=md.get("clip"), CLIP_TYPE=md.get("clip_type"), VAE=md.get("vae"),
                 IMAGE=image_name, PROMPT=p["prompt"], NEGATIVE=p["negative"], SEED=p["seed"], STEPS=p["steps"],
                 CFG=p["cfg"], SAMPLER=p["sampler"], SCHEDULER=p["scheduler"], DENOISE=p["denoise"],
                 PREFIX=PREFIX)
    return fill(p["template"]["workflow"], slots)


def sidecar(p, wf, control_png, styled_png, overlap, control_overlap, server=None):
    import mpw
    rel = {k: os.path.basename(v) for k, v in p["files"].items()}
    md = p["model"]
    ok, detail = judge(overlap, control_overlap) if overlap else (None, "not measured")
    return dict(
        tool="mapwright", tool_version=mpw.VERSION, command="aistyle",
        created=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        recipe=dict(kind=p["recipe"].get("kind"), seed=p["recipe"].get("seed"), generator=p["recipe"].get("generator")),
        look=p["look"], base_style=p["base_style"], prompt=p["prompt"], negative=p["negative"],
        seed=p["seed"], denoise=p["denoise"], denoise_effective=p["denoise_effective"], steps=p["steps"],
        cfg=p["cfg"], sampler=p["sampler"], scheduler=p["scheduler"], size=list(p["size"]),
        model=dict(name=md.get("name"), unet=md.get("unet"), clip=md.get("clip"), clip_type=md.get("clip_type"),
                   vae=md.get("vae"), licence=md.get("licence"), licence_class=md.get("licence_class"),
                   card=md.get("card")),
        workflow=dict(template=p["template"]["name"], sha256=workflow_hash(wf), file=rel["workflow"]),
        files=dict(control=rel["control"], styled=rel["styled"], out=rel["out"]),
        sha256=dict(control=sha(control_png), styled=sha(styled_png)),
        server=server or {},
        overlap=dict(styled=overlap, control=control_overlap, ok=ok, detail=detail,
                     tolerance=dict(land_iou=TOL_LAND_IOU, river_on_land=TOL_RIVER_LAND, towns_on_land=TOL_TOWNS_LAND,
                                    denoise_ceiling=DENOISE_CEILING)),
        labels=dict(placed=p["info"]["placed"], dropped=p["info"]["dropped"],
                    note="lakes, rivers, roads, symbols, labels, legend, scale bar and north arrow are set in "
                         "code after the pass"))


def run(d, look_name, out=None, host=None, denoise=None, seed=0, dry_run=False, template=None, model=None,
        clip=None, vae=None, size=None, style=None, font=None, title=None, timeout=900, do_measure=True,
        call=None, env=None, sleep=time.sleep):
    """Render the control picture, run the pass, composite the code-set layer, measure, write the sidecar."""
    p = plan(d, look_name, out, denoise, seed, template, model, clip, vae, size, style, font, title)
    f = p["files"]
    wm, hm = p["size"]
    if not dry_run:
        host = resolve_host(host, env)     # fail before the browser starts
    os.makedirs(os.path.dirname(os.path.abspath(f["out"])), exist_ok=True)
    R.write_out(control_svg(p["svg"], wm, hm), f["control"])
    control_png = _read(f["control"])
    image_name = "%s-%s.png" % (PREFIX, sha(control_png)[:16])
    wf = build_workflow(p, image_name)
    _write_text(f["workflow"], json.dumps(wf, indent=1, sort_keys=True) + "\n")
    res = dict(look=look_name, base_style=p["base_style"], seed=p["seed"], denoise=p["denoise"],
               denoise_effective=p["denoise_effective"], size=[wm, hm], control=f["control"],
               workflow=f["workflow"], workflow_sha256=workflow_hash(wf), model=p["model"].get("unet"),
               licence_class=p["model"].get("licence_class"), dry_run=bool(dry_run))
    if p["denoise"] > DENOISE_CEILING:
        res["warning"] = ("denoise %.2f is above the measured ceiling %.2f: expect the coast to drift"
                          % (p["denoise"], DENOISE_CEILING))
    if dry_run:
        return res
    c = Comfy(host, call)
    server = dict(comfyui=c.stats().get("system", {}).get("comfyui_version"))
    wf = build_workflow(p, c.upload(image_name, control_png))
    t0 = time.monotonic()
    styled_png = c.fetch(c.wait(c.queue(wf), timeout=timeout, sleep=sleep))
    res["seconds"] = round(time.monotonic() - t0, 1)
    _write(f["styled"], styled_png)
    R.write_out(composite_svg(p["svg"], styled_png, wm, hm), f["out"])
    overlap = control_overlap = None
    if do_measure:
        simg = RD.load_image(f["styled"])
        cimg = RD.load_image(f["control"])
        if (cimg.w, cimg.h) != (simg.w, simg.h):
            cimg = None
        tr = truth(d, simg.w, simg.h)
        overlap = measure(d, simg, tr, cimg)
        if cimg is not None:
            control_overlap = measure(d, cimg, tr, cimg)
    sc = sidecar(p, wf, control_png, styled_png, overlap, control_overlap, server)
    _write_text(f["sidecar"], json.dumps(sc, indent=1) + "\n")
    res.update(styled=f["styled"], out=f["out"], sidecar=f["sidecar"], overlap=sc["overlap"])
    return res


# ------------------------------------------------------------------ check bars
def sidecars(d):
    return sorted(os.path.join(d, n) for n in os.listdir(d) if n.endswith(SIDECAR))


def bars(d):
    """Optional proof bars: one per styled picture with a sidecar in the recipe folder.
    Returns [(name, ok, detail)]; ok None = skipped. No sidecar, no bar."""
    out = []
    for sc_path in sidecars(d):
        name = "aistyle %s: coast held, rivers and settlements on painted land" % os.path.basename(sc_path)[:-len(SIDECAR)]
        try:
            with open(sc_path, encoding="utf-8") as f:
                sc = json.load(f)
            styled = os.path.join(d, sc["files"]["styled"])
            control = os.path.join(d, sc["files"]["control"])
        except (ValueError, KeyError, OSError) as e:
            out.append((name, False, "unreadable sidecar: %s" % e))
            continue
        if not os.path.isfile(styled):
            out.append((name, None, "skipped: %s is missing" % sc["files"]["styled"]))
            continue
        if sha(_read(styled)) != sc.get("sha256", {}).get("styled"):
            out.append((name, False, "%s is not the picture the sidecar describes (sha256 differs)"
                        % sc["files"]["styled"]))
            continue
        simg = RD.load_image(styled)
        tr = truth(d, simg.w, simg.h)
        cimg = cm = None
        if os.path.isfile(control):
            cimg = RD.load_image(control)
            if (cimg.w, cimg.h) != (simg.w, simg.h):
                cimg = None
        m = measure(d, simg, tr, cimg)
        if cimg is not None:
            cm = measure(d, cimg, tr, cimg)
        ok, detail = judge(m, cm)
        out.append((name, ok, "%s, denoise %s: %s" % (sc.get("look"), sc.get("denoise"), detail)))
    return out
