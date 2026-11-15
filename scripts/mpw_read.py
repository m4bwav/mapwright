"""mapwright picture reading: `read` (what a map picture shows) and `trace` (picture to vectors).

Standard library only. PNG is decoded with zlib; other formats need Pillow (probed, optional).
OCR uses the tesseract command when it is on PATH; when it is not, every text field says
"not sure" with the reason. Nothing here guesses a scale, a place or a coordinate: a
georeference comes only from control points (GCPs) the caller supplies, with residuals.

Pixel coordinates are continuous, measured from the image's top-left corner: pixel (col, row)
covers [col, col+1] x [row, row+1]. A world file uses pixel centres, so it is written with
that half-pixel shift.
"""
import json
import math
import os
import re
import shutil
import struct
import subprocess
import zlib

NOT_SURE = "not sure"


def unsure(reason, **extra):
    d = {"value": None, "status": NOT_SURE, "reason": reason}
    d.update(extra)
    return d


# ------------------------------------------------------------------ image loading
class Image:
    """RGB image: width, height, rows (list of bytearray, 3 bytes per pixel)."""

    def __init__(self, w, h, rows, source="png"):
        self.w, self.h, self.rows, self.source = w, h, rows, source

    def px(self, x, y):
        r = self.rows[y]
        return r[3 * x], r[3 * x + 1], r[3 * x + 2]


def _unfilter(raw, w, h, bpp, stride):
    out, prev, pos = [], bytearray(stride), 0
    for _ in range(h):
        ft = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += stride + 1
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                if i >= bpp:
                    a, c = line[i - bpp], prev[i - bpp]
                else:
                    a = c = 0
                b = prev[i]
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif ft != 0:
            raise ValueError("bad PNG filter type %d" % ft)
        out.append(line)
        prev = line
    return out


def decode_png(data):
    """Decode a non-interlaced PNG (any colour type, 8 or 16 bit; 1-4 bit palette/grey) to RGB rows.
    Alpha is composited over white."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, hdr, plte, trns = 8, [], None, None, None
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"PLTE":
            plte = chunk
        elif typ == b"tRNS":
            trns = chunk
        elif typ == b"IDAT":
            idat.append(chunk)
        elif typ == b"IEND":
            break
        pos += 12 + ln
    w, h, depth, ctype, _, _, inter = hdr
    if inter:
        raise ValueError("interlaced PNG: the stdlib decoder does not handle it; install Pillow")
    chans = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    bits = chans * depth
    bpp = max(1, bits // 8)
    stride = (w * bits + 7) // 8
    lines = _unfilter(zlib.decompress(b"".join(idat)), w, h, bpp, stride)
    rows = []
    for line in lines:
        if depth == 16:
            line = line[0::2]  # high bytes of each 16-bit sample
        elif depth < 8:
            vals, mask = [], (1 << depth) - 1
            for byte in line:
                for s in range(8 - depth, -1, -depth):
                    vals.append((byte >> s) & mask)
            vals = vals[:w]
            if ctype == 0:
                k = 255 // mask
                vals = [v * k for v in vals]
            line = bytearray(vals)
        out = bytearray(3 * w)
        if ctype == 2:
            out[:] = line[:3 * w]
        elif ctype == 0:
            out[0::3] = out[1::3] = out[2::3] = line[:w]
        elif ctype == 3:
            alpha = trns or b""
            for i in range(w):
                k = line[i]
                r, g, b = plte[3 * k:3 * k + 3]
                if k < len(alpha) and alpha[k] < 255:
                    a = alpha[k]
                    r, g, b = [(v * a + 255 * (255 - a)) // 255 for v in (r, g, b)]
                out[3 * i:3 * i + 3] = bytes((r, g, b))
        else:  # 4 grey+alpha, 6 RGBA
            n = chans
            for i in range(w):
                a = line[n * i + n - 1]
                if ctype == 4:
                    r = g = b = line[n * i]
                else:
                    r, g, b = line[n * i], line[n * i + 1], line[n * i + 2]
                if a < 255:
                    r, g, b = [(v * a + 255 * (255 - a)) // 255 for v in (r, g, b)]
                out[3 * i:3 * i + 3] = bytes((r, g, b))
        rows.append(out)
    return Image(w, h, rows, "png")


def load_image(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            return decode_png(data)
        except ValueError as e:
            if "interlaced" not in str(e):
                raise
    try:
        from PIL import Image as PILImage  # optional
    except ImportError:
        raise ValueError("%s: only non-interlaced PNG is read without Pillow (pip install pillow)"
                         % os.path.basename(path))
    im = PILImage.open(path).convert("RGB")
    w, h = im.size
    raw = im.tobytes()
    return Image(w, h, [bytearray(raw[3 * w * y:3 * w * (y + 1)]) for y in range(h)], "pillow")


def png_rgb_bytes(w, h, rows):
    """Encode RGB rows as an 8-bit PNG (for tests and debug masks)."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ colour classes
def classify(r, g, b):
    """Coarse map colour class of one pixel. Rules are plain and documented, not learned:
    water = blue clearly above red and not below green by much; vegetation = green dominant;
    relief = warm browns and tans; snow/paper = very light and grey; ink = very dark."""
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 60:
        return "ink"
    if mn > 215 and mx - mn < 25:
        return "light"
    if b > r + 20 and b >= g - 10:
        return "water"
    if g >= r and g > b + 8:
        return "vegetation"
    if r >= g >= b and r - b > 25:
        return "relief"
    if mx - mn < 25:
        return "grey"
    return "other"


CLASS_NOTE = {
    "water": "sea, lakes and rivers drawn in blue (any blue, so a blue land tint reads as water)",
    "vegetation": "green land tints (lowland, forest)",
    "relief": "browns and tans (hills, mountains, desert, parchment)",
    "light": "near white: snow, paper, label halos",
    "ink": "near black: text, outlines, symbols",
    "grey": "neutral greys",
    "other": "anything else (reds, purples)",
}


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def parse_hex(s):
    s = s.lstrip("#")
    if len(s) != 6:
        raise ValueError("colour wants #rrggbb, got " + s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def colour_stats(img, step=None):
    """Class shares and the dominant colours (4 bits per channel buckets)."""
    step = step or max(1, int(math.sqrt(img.w * img.h / 250000.0)))
    counts, buckets, n = {}, {}, 0
    for y in range(0, img.h, step):
        row = img.rows[y]
        for x in range(0, img.w, step):
            i = 3 * x
            r, g, b = row[i], row[i + 1], row[i + 2]
            k = classify(r, g, b)
            counts[k] = counts.get(k, 0) + 1
            q = (r >> 4, g >> 4, b >> 4)
            e = buckets.get(q)
            if e is None:
                buckets[q] = [1, r, g, b]
            else:
                e[0] += 1
                e[1] += r
                e[2] += g
                e[3] += b
            n += 1
    shares = {k: round(v / n, 4) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])}
    top = sorted(buckets.values(), key=lambda e: -e[0])[:8]
    dom = [{"colour": hexc((e[1] // e[0], e[2] // e[0], e[3] // e[0])), "share": round(e[0] / n, 4),
            "class": classify(e[1] // e[0], e[2] // e[0], e[3] // e[0])} for e in top]
    return shares, dom, step


def make_mask(img, cls=None, colour=None, tol=40.0):
    """List of bytearrays (1 inside). By class name or by colour within RGB distance tol."""
    mask = []
    if colour is not None:
        cr, cg, cb = colour
        t2 = tol * tol
        for row in img.rows:
            m = bytearray(img.w)
            for x in range(img.w):
                i = 3 * x
                dr, dg, db = row[i] - cr, row[i + 1] - cg, row[i + 2] - cb
                if dr * dr + dg * dg + db * db <= t2:
                    m[x] = 1
            mask.append(m)
        return mask
    cache = {}
    for row in img.rows:
        m = bytearray(img.w)
        for x in range(img.w):
            i = 3 * x
            key = (row[i], row[i + 1], row[i + 2])
            v = cache.get(key)
            if v is None:
                v = cache[key] = 1 if classify(*key) == cls else 0
            m[x] = v
        mask.append(m)
    return mask


def clean_mask(mask, passes=1):
    """3x3 vote: 6+ of 9 set turns a pixel on, 3 or fewer turns it off, else it stays. Removes specks and
    one-pixel strokes (label text, thin lines) and fills pin holes, but keeps square corners."""
    h, w = len(mask), len(mask[0])
    for _ in range(passes):
        out = []
        for y in range(h):
            a, b, c = mask[max(y - 1, 0)], mask[y], mask[min(y + 1, h - 1)]
            row = bytearray(w)
            for x in range(w):
                x0, x1 = max(x - 1, 0), min(x + 1, w - 1)
                s = (a[x0] + a[x] + a[x1] + b[x0] + b[x] + b[x1] + c[x0] + c[x] + c[x1])
                row[x] = 1 if s >= 6 else 0 if s <= 3 else b[x]
            out.append(row)
        mask = out
    return mask


# ------------------------------------------------------------------ geometry helpers
def ring_area(ring):
    """Shoelace area in pixel space (y down): positive for rings clockwise on screen."""
    s = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _seg_dist2(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L = dx * dx + dy * dy
    if L == 0:
        return (p[0] - ax) ** 2 + (p[1] - ay) ** 2
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return (p[0] - ax - t * dx) ** 2 + (p[1] - ay - t * dy) ** 2


def douglas_peucker(pts, eps):
    """Iterative Douglas-Peucker on an open polyline."""
    if len(pts) < 3 or eps <= 0:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    e2 = eps * eps
    while stack:
        i, j = stack.pop()
        best, bi = -1.0, -1
        for k in range(i + 1, j):
            d = _seg_dist2(pts[k], pts[i], pts[j])
            if d > best:
                best, bi = d, k
        if best > e2:
            keep[bi] = True
            stack.append((i, bi))
            stack.append((bi, j))
    return [p for p, k in zip(pts, keep) if k]


def simplify_ring(ring, eps):
    """Closed ring (first == last) simplified by splitting at the point farthest from the start."""
    pts = ring[:-1]
    if len(pts) < 4 or eps <= 0:
        return ring
    far = max(range(len(pts)), key=lambda k: (pts[k][0] - pts[0][0]) ** 2 + (pts[k][1] - pts[0][1]) ** 2)
    a = douglas_peucker(pts[:far + 1], eps)
    b = douglas_peucker(pts[far:] + [pts[0]], eps)
    out = a[:-1] + b
    return out if len(out) >= 4 else ring


def point_in_ring(p, ring):
    x, y = p
    inside = False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


# ------------------------------------------------------------------ mask -> polygons
def mask_rings(mask):
    """Boundary rings of a binary mask along pixel edges. Outer rings come out clockwise on screen
    (positive ring_area), holes anticlockwise. Coordinates are pixel corners."""
    h, w = len(mask), len(mask[0])
    nxt = {}

    def add(a, b):
        nxt.setdefault(a, []).append(b)
    for y in range(h):
        row = mask[y]
        up = mask[y - 1] if y > 0 else None
        dn = mask[y + 1] if y + 1 < h else None
        for x in range(w):
            if not row[x]:
                continue
            if up is None or not up[x]:
                add((x, y), (x + 1, y))
            if x + 1 >= w or not row[x + 1]:
                add((x + 1, y), (x + 1, y + 1))
            if dn is None or not dn[x]:
                add((x + 1, y + 1), (x, y + 1))
            if x == 0 or not row[x - 1]:
                add((x, y + 1), (x, y))
    rings = []
    while nxt:
        start = next(iter(nxt))
        ring = [start]
        prev, cur = None, start
        while True:
            outs = nxt.get(cur)
            if not outs:
                break
            if len(outs) > 1 and prev is not None:
                # saddle: turn right (screen clockwise) so diagonal pixels stay separate rings
                dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                right = (cur[0] - dy, cur[1] + dx)
                k = outs.index(right) if right in outs else 0
            else:
                k = 0
            nb = outs.pop(k)
            if not outs:
                del nxt[cur]
            ring.append(nb)
            prev, cur = cur, nb
            if cur == start:
                break
        if len(ring) >= 4 and ring[0] == ring[-1]:
            rings.append(_collinear(ring))
    return rings


def _collinear(ring):
    out = [ring[0]]
    for i in range(1, len(ring) - 1):
        a, b, c = out[-1], ring[i], ring[i + 1]
        if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
            out.append(b)
    out.append(ring[-1])
    return out


def polygons_from_mask(mask, eps=1.0, min_area=0.0, fill_holes=0.0):
    """Polygons [[outer, hole, ...], ...] in pixel coordinates, holes nested by point-in-ring."""
    outers, holes = [], []
    for r in mask_rings(mask):
        a = ring_area(r)
        if abs(a) < min_area or (a < 0 and -a < fill_holes):
            continue
        s = simplify_ring(r, eps)
        (outers if a > 0 else holes).append((abs(a), s))
    outers.sort(key=lambda t: t[0])
    polys = [[o] for _, o in outers]
    for _, hl in holes:
        p = hl[0]
        for poly in polys:  # smallest containing outer first
            if point_in_ring(p, poly[0]):
                poly.append(hl)
                break
    return polys


# ------------------------------------------------------------------ mask -> centre lines
def thin(mask):
    """Zhang-Suen thinning, in place on a copy; returns the skeleton mask."""
    h, w = len(mask), len(mask[0])
    m = [bytearray(r) for r in mask]
    pts = {(x, y) for y in range(h) for x in range(w) if m[y][x]}
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            kill = []
            for (x, y) in pts:
                if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                    continue
                p2, p3, p4 = m[y - 1][x], m[y - 1][x + 1], m[y][x + 1]
                p5, p6, p7 = m[y + 1][x + 1], m[y + 1][x], m[y + 1][x - 1]
                p8, p9 = m[y][x - 1], m[y - 1][x - 1]
                nb = (p2, p3, p4, p5, p6, p7, p8, p9)
                B = sum(nb)
                if B < 2 or B > 6:
                    continue
                A = sum(1 for i in range(8) if nb[i] == 0 and nb[(i + 1) % 8] == 1)
                if A != 1:
                    continue
                if step == 0 and (p2 * p4 * p6 or p4 * p6 * p8):
                    continue
                if step == 1 and (p2 * p4 * p8 or p2 * p6 * p8):
                    continue
                kill.append((x, y))
            for x, y in kill:
                m[y][x] = 0
                pts.discard((x, y))
            changed = changed or bool(kill)
    return m


N8 = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))


def skeleton_lines(skel, eps=1.0, min_len=5.0):
    """Polylines through pixel centres of a one-pixel skeleton, split at junctions and ends."""
    h, w = len(skel), len(skel[0])
    on = {(x, y) for y in range(h) for x in range(w) if skel[y][x]}

    def nbrs(p):
        return [(p[0] + dx, p[1] + dy) for dx, dy in N8 if (p[0] + dx, p[1] + dy) in on]
    deg = {p: len(nbrs(p)) for p in on}
    used = set()
    lines = []

    def walk(a, b):
        path = [a, b]
        used.add(frozenset((a, b)))
        while deg[path[-1]] == 2:
            cur = path[-1]
            n = [q for q in nbrs(cur) if frozenset((cur, q)) not in used]
            if not n:
                break
            used.add(frozenset((cur, n[0])))
            path.append(n[0])
        return path
    for p in on:
        if deg[p] != 2:
            for q in nbrs(p):
                if frozenset((p, q)) not in used:
                    lines.append(walk(p, q))
    for p in on:  # closed loops with no junction
        for q in nbrs(p):
            if frozenset((p, q)) not in used:
                lines.append(walk(p, q))
    out = []
    for ln in lines:
        pts = [(x + 0.5, y + 0.5) for x, y in ln]
        L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        if L >= min_len:
            out.append(douglas_peucker(pts, eps))
    return out


# ------------------------------------------------------------------ georeference
def _solve3(M, v):
    """Solve a 3x3 system by Cramer's rule."""
    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    D = det(M)
    if abs(D) < 1e-18:
        raise ValueError("control points are collinear or repeated; an affine fit needs 3 spread points")
    out = []
    for c in range(3):
        m = [list(r) for r in M]
        for r in range(3):
            m[r][c] = v[r]
        out.append(det(m) / D)
    return out


def parse_gcp(s):
    p = [float(t) for t in s.replace(" ", "").split(",")]
    if len(p) != 4:
        raise ValueError("--gcp wants px,py,X,Y (pixel x, pixel y, lon or easting, lat or northing): " + s)
    return p


def haversine_m(lon1, lat1, lon2, lat2, R=6371008.8):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def fit_affine(gcps, units="deg"):
    """Least-squares affine X = a*px + b*py + c, Y = d*px + e*py + f from >= 3 GCPs, with residuals."""
    if len(gcps) < 3:
        raise ValueError("an affine georeference needs at least 3 control points (got %d)" % len(gcps))
    S = [[0.0] * 3 for _ in range(3)]
    tx, ty = [0.0] * 3, [0.0] * 3
    for px, py, X, Y in gcps:
        v = (px, py, 1.0)
        for i in range(3):
            for j in range(3):
                S[i][j] += v[i] * v[j]
            tx[i] += v[i] * X
            ty[i] += v[i] * Y
    a, b, c = _solve3(S, tx)
    d, e, f = _solve3(S, ty)
    res = []
    for px, py, X, Y in gcps:
        fx, fy = a * px + b * py + c, d * px + e * py + f
        r = {"px": px, "py": py, "dx": fx - X, "dy": fy - Y}
        if units == "deg":
            r["metres"] = haversine_m(fx, fy, X, Y)
        else:
            r["metres"] = math.hypot(fx - X, fy - Y)
        res.append(r)
    rms = math.sqrt(sum(r["metres"] ** 2 for r in res) / len(res))
    out = {"method": "affine", "coefficients": [a, b, c, d, e, f], "units": units, "gcps": len(gcps),
           "residuals": res, "rms_m": rms, "max_m": max(r["metres"] for r in res)}
    if len(gcps) == 3:
        out["note"] = "3 points fit an affine exactly: residuals are zero by construction and prove nothing. Add a 4th."
    return out


def apply_affine(co, p):
    a, b, c, d, e, f = co
    return (a * p[0] + b * p[1] + c, d * p[0] + e * p[1] + f)


def metres_per_pixel(fit, w, h):
    co = fit["coefficients"]
    cx, cy = w / 2.0, h / 2.0
    p0, px, py = apply_affine(co, (cx, cy)), apply_affine(co, (cx + 1, cy)), apply_affine(co, (cx, cy + 1))
    if fit["units"] == "deg":
        return (haversine_m(p0[0], p0[1], px[0], px[1]) + haversine_m(p0[0], p0[1], py[0], py[1])) / 2.0
    return (math.hypot(px[0] - p0[0], px[1] - p0[1]) + math.hypot(py[0] - p0[0], py[1] - p0[1])) / 2.0


def world_file_text(co):
    """World file lines (A, D, B, E, C, F) for the centre of pixel (0, 0)."""
    a, b, c, d, e, f = co
    return "\n".join("%.12g" % v for v in (a, d, b, e, a * 0.5 + b * 0.5 + c, d * 0.5 + e * 0.5 + f)) + "\n"


def world_file_path(img_path):
    stem, ext = os.path.splitext(img_path)
    ext = ext.lower()
    return stem + ({".png": ".pgw", ".jpg": ".jgw", ".jpeg": ".jgw", ".tif": ".tfw", ".tiff": ".tfw",
                    ".gif": ".gfw"}.get(ext, ".wld"))


def read_world_file(path):
    """Affine coefficients (corner convention) from a world file."""
    with open(path, encoding="utf-8") as f:
        A, D, B, E, C, F = [float(t) for t in f.read().split()[:6]]
    return [A, B, C - 0.5 * A - 0.5 * B, D, E, F - 0.5 * D - 0.5 * E]


# ------------------------------------------------------------------ OCR
SCALE_RE = re.compile(r"\b1\s*:\s*(\d{1,3}(?:[ ,.]\d{3})+|\d{3,})\b")


def probe_tesseract(which=shutil.which):
    return which("tesseract")


def run_ocr(path, which=shutil.which, run=subprocess.run):
    """Words and printed scale text from tesseract (--psm 11 sparse text), or a reasoned 'not sure'."""
    exe = probe_tesseract(which)
    if not exe:
        return unsure("tesseract is not on PATH, so no text was read; names, legend labels and printed "
                      "scale are not sure. Install Tesseract, or use `read --prompt` and your own vision.")
    try:
        r = run([exe, path, "stdout", "--psm", "11", "tsv"], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        return unsure("tesseract failed to run: %s" % e)
    if r.returncode != 0:
        return unsure("tesseract exited %d: %s" % (r.returncode, (r.stderr or "").strip()[:200]))
    words = []
    for line in r.stdout.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        try:
            conf = float(f[10])
        except ValueError:
            continue
        if conf < 0:
            continue
        x, y, w, h = (int(v) for v in f[6:10])
        words.append({"text": f[11].strip(), "conf": conf, "box": [x, y, x + w, y + h]})
    text = " ".join(wd["text"] for wd in words)
    scales = [m.group(0) for m in SCALE_RE.finditer(text)]
    return {"status": "read", "engine": "tesseract", "words": words,
            "low_confidence": sum(1 for wd in words if wd["conf"] < 60),
            "scale_text": scales or None,
            "note": "Tesseract misses curved, rotated and letter-spaced map names; absent words are not absent names."}


# ------------------------------------------------------------------ read
def read_report(path, gcps=None, units="deg", ocr=run_ocr, write_world=False):
    img = load_image(path)
    shares, dom, step = colour_stats(img)
    rep = {"image": os.path.basename(path), "width": img.w, "height": img.h, "decoder": img.source,
           "classes": shares, "class_rules": {k: CLASS_NOTE[k] for k in shares},
           "dominant_colours": dom, "sample_step_px": step}
    t = ocr(path)
    rep["text"] = t
    if t.get("status") == "read":
        rep["printed_scale"] = ({"value": t["scale_text"], "status": "read by OCR",
                                 "note": "a 1:N fraction holds only at the printed size; metres per pixel needs the scan DPI"}
                                if t["scale_text"] else unsure("OCR found no 1:N scale text"))
    else:
        rep["printed_scale"] = unsure("no OCR, so printed scale text was not read")
    if gcps:
        fit = fit_affine(gcps, units)
        fit["metres_per_pixel_at_centre"] = metres_per_pixel(fit, img.w, img.h)
        if write_world:
            wf = world_file_path(path)
            with open(wf, "w", encoding="utf-8", newline="\n") as f:
                f.write(world_file_text(fit["coefficients"]))
            fit["world_file"] = wf
        rep["georeference"] = fit
        rep["scale"] = {"metres_per_pixel": fit["metres_per_pixel_at_centre"], "from": "GCP affine fit"}
    else:
        rep["georeference"] = unsure("no control points given; pass --gcp px,py,lon,lat three or more times")
        rep["scale"] = unsure("no georeference and no measured scale bar")
    rep["legend"] = unsure("legend entries need text recognition or an agent reading (read --prompt)")
    rep["names"] = unsure("place names need text recognition or an agent reading (read --prompt)")
    return rep


AGENT_SCHEMA = {
    "title": {"text": "str", "box": "[x0,y0,x1,y1] px"},
    "map_type": "street | topographic | political | choropleth | fantasy | sci-fi | nautical | other",
    "legend": [{"label": "str", "swatch_box": "[x0,y0,x1,y1]", "colour": "#rrggbb (what you see in the swatch)"}],
    "scale": {"kind": "bar | fraction | verbal", "box": "[x0,y0,x1,y1]",
              "bar_px": "length of the bar in pixels, end tick to end tick", "bar_m": "ground length it is labelled with, metres",
              "text": "the printed text, e.g. 1:50,000"},
    "names": [{"text": "str", "box": "[x0,y0,x1,y1]", "kind": "city | town | river | sea | region | range | other"}],
    "north": {"box": "[x0,y0,x1,y1]", "rotation_deg": "clockwise from up"},
}


def agent_prompt(path, img=None):
    img = img or load_image(path)
    return {
        "task": "Read this map picture with your own vision and answer as JSON, then run "
                "`mpw.py read %s --answers answers.json` (add --gcp if you have control points) so the script checks you."
                % os.path.basename(path),
        "image": {"path": path, "width": img.w, "height": img.h,
                  "coordinates": "pixels from the top-left corner, x right, y down"},
        "schema": AGENT_SCHEMA,
        "rules": [
            "Ask 'is it printed on the map?' before 'what is it?'. Anything not printed is the string \"not sure\".",
            "Every item carries a box around the pixels you read it from. Items without a box are dropped.",
            "Never estimate a scale from how big things look. Only a printed bar, fraction or verbal scale counts.",
            "Never give the real-world place of an unlabelled or invented map.",
            "Do not count, measure distances or trace routes by eye: the script does those from traced vectors.",
            "Copy text exactly as printed, including odd spellings.",
        ],
        "checks_the_script_runs": [
            "boxes lie inside the image",
            "each legend colour matches the median colour inside its swatch box (RGB distance <= 40)",
            "a scale bar's metres per pixel agrees with the GCP fit within 10% when GCPs are given",
            "a 1:N fraction is kept as printed; metres per pixel is not derived from it without DPI",
        ],
    }


def _box_ok(box, img):
    try:
        x0, y0, x1, y1 = [float(v) for v in box]
    except (TypeError, ValueError):
        return False
    return 0 <= x0 < x1 <= img.w and 0 <= y0 < y1 <= img.h


def _median_colour(img, box):
    x0, y0, x1, y1 = [int(round(float(v))) for v in box]
    rs, gs, bs = [], [], []
    for y in range(max(0, y0), min(img.h, y1)):
        for x in range(max(0, x0), min(img.w, x1)):
            r, g, b = img.px(x, y)
            rs.append(r)
            gs.append(g)
            bs.append(b)
    if not rs:
        return None
    m = len(rs) // 2
    return sorted(rs)[m], sorted(gs)[m], sorted(bs)[m]


def validate_answers(path, answers, gcps=None, units="deg", colour_tol=40.0, scale_tol=0.10):
    img = load_image(path)
    out = {"image": os.path.basename(path), "items": [], "summary": {}}

    def item(field, verdict, why, **kw):
        d = {"field": field, "verdict": verdict, "why": why}
        d.update(kw)
        out["items"].append(d)

    def boxed(field, v):
        if v == NOT_SURE or v is None:
            item(field, NOT_SURE, "the reader said not sure")
            return False
        if not isinstance(v, dict) or "box" not in v and "swatch_box" not in v:
            item(field, "dropped", "no box, so it cannot be checked")
            return False
        if not _box_ok(v.get("box", v.get("swatch_box")), img):
            item(field, "dropped", "box lies outside the %dx%d image" % (img.w, img.h))
            return False
        return True
    t = answers.get("title", NOT_SURE)
    if boxed("title", t):
        item("title", "unchecked", "box is inside the image; text not verified without OCR", text=t.get("text"))
    for i, n in enumerate(answers.get("names") or []):
        if boxed("names[%d]" % i, n):
            item("names[%d]" % i, "unchecked", "box is inside the image; text not verified without OCR", text=n.get("text"))
    for i, L in enumerate(answers.get("legend") or []):
        f = "legend[%d]" % i
        if not boxed(f, L):
            continue
        seen = _median_colour(img, L["swatch_box"] if "swatch_box" in L else L["box"])
        if L.get("colour") and seen:
            try:
                claim = parse_hex(L["colour"])
            except ValueError:
                item(f, "dropped", "colour is not #rrggbb")
                continue
            dist = math.sqrt(sum((p - q) ** 2 for p, q in zip(claim, seen)))
            item(f, "ok" if dist <= colour_tol else "mismatch",
                 "claimed %s, swatch median %s, RGB distance %.1f (tolerance %.0f)" % (L["colour"], hexc(seen), dist, colour_tol),
                 label=L.get("label"))
        else:
            item(f, "unchecked", "no colour claimed", label=L.get("label"))
    sc = answers.get("scale", NOT_SURE)
    fit = fit_affine(gcps, units) if gcps else None
    if boxed("scale", sc):
        kind = sc.get("kind")
        if kind == "bar" and sc.get("bar_px") and sc.get("bar_m"):
            mpp = float(sc["bar_m"]) / float(sc["bar_px"])
            if fit:
                ref = metres_per_pixel(fit, img.w, img.h)
                err = abs(mpp - ref) / ref
                item("scale", "ok" if err <= scale_tol else "mismatch",
                     "bar gives %.4g m/px, GCP fit gives %.4g m/px at the centre: %.1f%% apart (tolerance %.0f%%)"
                     % (mpp, ref, 100 * err, 100 * scale_tol), metres_per_pixel=mpp)
            else:
                item("scale", "unchecked", "bar gives %.4g m/px; no GCPs to check it against" % mpp, metres_per_pixel=mpp)
        elif kind == "fraction":
            m = SCALE_RE.search(str(sc.get("text", "")))
            item("scale", "ok" if m else "dropped",
                 "fraction kept as printed; metres per pixel needs the scan DPI" if m else "text is not a 1:N fraction",
                 text=sc.get("text"))
        else:
            item("scale", "unchecked", "kind %r with nothing measurable" % kind)
    if fit:
        out["georeference"] = {"rms_m": fit["rms_m"], "max_m": fit["max_m"], "gcps": fit["gcps"]}
    for it in out["items"]:
        out["summary"][it["verdict"]] = out["summary"].get(it["verdict"], 0) + 1
    return out


# ------------------------------------------------------------------ trace
def trace(path, cls="water", colour=None, tol=40.0, mode="polygons", eps=1.0, min_area=16.0, min_len=8.0,
          clean=1, gcps=None, units="deg", world=None, fill_holes=0.0):
    img = load_image(path)
    mask = make_mask(img, cls=None if colour else cls, colour=colour, tol=tol)
    if clean:
        mask = clean_mask(mask, clean)
    co, georef = None, "pixel"
    if gcps:
        fit = fit_affine(gcps, units)
        co, georef = fit["coefficients"], "gcp affine, rms %.3g m" % fit["rms_m"]
    elif world:
        co, georef = read_world_file(world), "world file " + os.path.basename(world)

    def tf(p):
        q = apply_affine(co, p) if co else p
        return [round(q[0], 9 if co else 3), round(q[1], 9 if co else 3)]
    feats = []
    if mode == "polygons":
        for poly in polygons_from_mask(mask, eps, min_area, fill_holes):
            feats.append({"type": "Feature", "properties": {"class": colour and hexc(colour) or cls,
                                                            "area_px": round(abs(ring_area(poly[0])), 1),
                                                            "holes": len(poly) - 1},
                          "geometry": {"type": "Polygon", "coordinates": [[tf(p) for p in r] for r in poly]}})
    else:
        for ln in skeleton_lines(thin(mask), eps, min_len):
            feats.append({"type": "Feature", "properties": {"class": colour and hexc(colour) or cls},
                          "geometry": {"type": "LineString", "coordinates": [tf(p) for p in ln]}})
    inside = sum(sum(r) for r in mask)
    return {"type": "FeatureCollection",
            "mapwright": {"source": os.path.basename(path), "width": img.w, "height": img.h, "mode": mode,
                          "class": cls if not colour else hexc(colour), "epsilon_px": eps, "coordinates": georef,
                          "mask_share": round(inside / float(img.w * img.h), 4), "features": len(feats)},
            "features": feats}


def polyline_distance_stats(src, ref):
    """Distances from every vertex of polylines src to the nearest segment of polylines ref."""
    segs = [(a, b) for ln in ref for a, b in zip(ln, ln[1:])]
    cell = 16.0
    grid = {}
    for s in segs:
        x0, x1 = sorted((s[0][0], s[1][0]))
        y0, y1 = sorted((s[0][1], s[1][1]))
        for gx in range(int(x0 // cell), int(x1 // cell) + 1):
            for gy in range(int(y0 // cell), int(y1 // cell) + 1):
                grid.setdefault((gx, gy), []).append(s)
    ds = []
    for ln in src:
        for p in ln:
            gx, gy = int(p[0] // cell), int(p[1] // cell)
            best = None
            for ring in range(0, 64):
                cand = []
                for dx in range(-ring, ring + 1):
                    for dy in range(-ring, ring + 1):
                        if max(abs(dx), abs(dy)) == ring:
                            cand += grid.get((gx + dx, gy + dy), [])
                for a, b in cand:
                    d = _seg_dist2(p, a, b)
                    if best is None or d < best:
                        best = d
                if best is not None and math.sqrt(best) <= ring * cell:
                    break
            if best is not None:
                ds.append(math.sqrt(best))
    ds.sort()
    if not ds:
        return {"n": 0}
    return {"n": len(ds), "median": ds[len(ds) // 2], "p95": ds[int(0.95 * (len(ds) - 1))], "max": ds[-1],
            "mean": sum(ds) / len(ds)}


def dumps(obj):
    return json.dumps(obj, indent=1)
