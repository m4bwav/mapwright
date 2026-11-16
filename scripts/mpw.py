#!/usr/bin/env python3
"""mapwright CLI: read, write, measure and project maps with the standard library.

Subcommands: doctor, explain, inspect, convert, measure, project, read, trace, gen, zoom, check,
names, render, label, legend, style, serve, sheet, aistyle.
Optional extras (numpy, shapely, pyproj, GDAL, geographiclib) are probed, never
imported at the top level.
"""
import argparse
import importlib
import importlib.util
import json
import math
import os
import shutil
import sqlite3
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib

VERSION = "0.20.0"

# ---------------------------------------------------------------- ellipsoids
ELLIPSOIDS = {
    "WGS84": (6378137.0, 1 / 298.257223563),
    "GRS80": (6378137.0, 1 / 298.257222101),
    "clarke1866": (6378206.4, 1 / 294.978698214),
}
WEB_R = 6378137.0


def die(msg, code=2):
    print("mpw: " + msg, file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- doctor
def _probe_module(name):
    spec = importlib.util.find_spec(name)
    if spec is None:
        return None
    try:
        mod = importlib.import_module(name)
        return getattr(mod, "__version__", "present")
    except Exception as e:  # broken install
        return "broken: %s" % e.__class__.__name__



def find_browser():
    cands = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            if not base:
                continue
            cands += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                      os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for c in cands:
        if os.path.isfile(c):
            return c
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"):
        p = shutil.which(n)
        if p:
            return p
    return None


def cmd_doctor(a):
    gdal = _probe_module("osgeo")
    info = {
        "mapwright": VERSION,
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 9),
        "browser": find_browser(),
        "sqlite": sqlite3.sqlite_version,
        "extras": {
            "numpy": _probe_module("numpy"),
            "shapely": _probe_module("shapely"),
            "pyproj": _probe_module("pyproj"),
            "gdal": gdal or (shutil.which("gdalinfo") and "gdalinfo on PATH"),
            "geographiclib": _probe_module("geographiclib"),
            "pillow": _probe_module("PIL"),
            "tesseract": shutil.which("tesseract") and "tesseract on PATH",
        },
    }
    # export targets: everything but print is standard library only
    info["export"] = {"heightmaps": True, "tiled": True, "uvtt": True, "mesh": True, "print": bool(info["browser"])}
    try:
        info["aistyle"] = _aistyle().doctor(getattr(a, "host", None))
    except (ValueError, OSError) as e:
        info["aistyle"] = {"note": "workflow template unreadable: %s" % e}
    if a.json:
        print(json.dumps(info, indent=2))
        return
    print("mapwright %s" % VERSION)
    print("python        %s %s" % (info["python"], "ok" if info["python_ok"] else "(need 3.9+)"))
    print("sqlite        %s" % info["sqlite"])
    print("browser       %s" % (info["browser"] or "none found (PNG/PDF export needs Chrome or Edge)"))
    for k, v in info["extras"].items():
        print("%-14s%s" % (k, v or "absent (optional)"))
    print("export        heightmaps, tiled, uvtt and mesh ready; print (PDF/PNG at a paper size) %s"
          % ("ready" if info["browser"] else "skipped: no Chrome or Edge"))
    ai = info["aistyle"]
    if not ai.get("answers"):
        print("aistyle       %s" % ai.get("note", "not checked"))
    else:
        files = ai.get("files", {})
        missing = sorted(k for k, v in files.items() if v is False)
        unknown = sorted(k for k, v in files.items() if v is None)
        print("aistyle       ComfyUI %s answers; model %s %s"
              % (ai.get("comfyui") or "?", ai.get("model"),
                 ("MISSING on the server: " + ", ".join(missing)) if missing
                 else ("not checked: " + ", ".join(unknown)) if unknown else "present"))


# ---------------------------------------------------------------- explain
GLOSSARY = {
    "web-mercator": ("EPSG:3857. Spherical Mercator on the WGS84 radius used by web tiles. Conformal, "
                     "area grows as sec^2(lat); cut at about 85.0511 deg. Never use it for area.",
                     "references/projections.md"),
    "mercator": ("Conformal cylindrical projection: angles and local shapes kept, area wildly "
                 "inflated toward the poles. Good for navigation (rhumb lines are straight).",
                 "references/projections.md"),
    "equirectangular": ("Plate carree when the standard parallel is 0: x = lon, y = lat scaled. "
                        "Neither equal-area nor conformal; the usual texture layout for globes.",
                        "references/projections.md"),
    "mollweide": ("Equal-area pseudocylindrical world projection, elliptical outline; meridians are "
                  "ellipses. Needs a Newton step on the auxiliary angle. Common for whole-sky maps.",
                  "references/projections.md"),
    "laea": ("Lambert azimuthal equal-area: true area, directions true from the centre. Good for "
             "continents and polar maps (EPSG:3035 is Europe's).", "references/projections.md"),
    "robinson": ("Compromise world projection from a 5-degree table; keeps nothing exactly, looks "
                 "right. Poles are lines 0.5322 of the equator.", "references/projections.md"),
    "equal-earth": ("Equal-area pseudocylindrical projection (2018), a free equal-area alternative "
                    "to Robinson.", "references/projections.md"),
    "utm": ("Universal Transverse Mercator: 60 zones 6 deg wide, k0 = 0.9996, false easting "
            "500 000 m. Do not draw data spanning several zones in one zone.", "references/projections.md"),
    "tissot": ("Tissot's indicatrix: the ellipse a small circle becomes; shows a projection's "
               "local scale and angle distortion.", "references/projections.md"),
    "geodesic": ("Shortest path on the ellipsoid. mpw.py uses Vincenty's inverse formula, with "
                 "geographiclib (Karney) when installed or near antipodes.", "references/projections.md"),
    "rhumb-line": ("Loxodrome: a line of constant bearing; straight on Mercator, longer than the "
                   "geodesic.", "references/projections.md"),
    "authalic-sphere": ("The sphere with the same surface area as the ellipsoid (WGS84 R = 6371007.2 m). "
                        "With authalic latitude it maps ellipsoid area exactly.", "references/projections.md"),
    "scale": ("Representative fraction 1:N: 1 unit on the map is N on the ground. 1:50000 means "
              "1 cm = 500 m. Large scale = small N = more detail.", "references/cartography-design.md"),
    "contour": ("Line of equal elevation. Interval stays constant on one map; every fifth is an "
                "index contour, drawn heavier and labelled uphill.", "references/relief-and-labels.md"),
    "hillshade": ("Relief shading from a light, usually NW at 315 deg azimuth, 45 deg altitude, "
                  "from the slope and aspect of a heightmap.", "references/relief-and-labels.md"),
    "hachures": ("Short strokes drawn down the slope, denser and heavier where steeper; the "
                 "pre-contour way to show relief.", "references/relief-and-labels.md"),
    "geojson": ("RFC 7946: JSON features in WGS84 lon/lat, CCW outer rings, no CRS member.",
                "references/formats-and-tools.md"),
    "world-file": ("Six-line sidecar (.pgw, .wld): pixel size x, two rotations, negative pixel "
                   "size y, x and y of the top-left pixel centre. Holds no CRS.",
                   "references/formats-and-tools.md"),
    "priority-flood": ("Depression filling in O(n log n): flood from the edges with a priority "
                       "queue, raise pits to their spill height (plus epsilon so water drains).",
                       "references/realistic-land.md"),
    "voronoi": ("Cells closest to each seed point; the dual of the Delaunay triangulation. The "
                "mesh mapwright generators grow land on.", "references/realistic-land.md"),
    "heightmap": ("A grey image whose values are elevations. Engines want set sizes: Unity a square 16-bit RAW of "
                  "2^n + 1 samples, Unreal a 16-bit PNG of 1009, 2017 and kin, Roblox a PNG up to 4096 px. The "
                  "file holds no scale, so `export` writes the metres per pixel and height range beside it.",
                  "references/games-film-print.md"),
    "bleed": ("Print that runs past the trim line, 3 mm per edge in Europe and 0.125 in in the US, so a cut that "
              "lands a little off shows no white edge. The page is the paper plus the bleed on every side.",
              "references/games-film-print.md"),
    "crop-marks": ("Short lines at the corners of a printed sheet that show where to cut. `export --to print "
                   "--bleed 3` draws them inside the bleed, on the trim lines.", "references/games-film-print.md"),
    "tmj": ("Tiled's JSON map: tile layers of global tile ids (0 is empty, the top four bits are flip flags), "
            "object layers for walls and doors, and a tileset with a first gid and an image.",
            "references/games-film-print.md"),
    "jump-point-search": ("JPS (Harabor and Grastien 2011): A* on a uniform-cost grid that jumps along straight and "
                          "diagonal lines and queues only squares with a forced neighbour. Same cost as A*, fewer "
                          "queued nodes. mpw.py path --jps; doors are always jump points.",
                          "references/pathfinding.md"),
    "nav-export": ("Navigation hand-over: walkable squares merged into convex rectangles plus the portals between "
                   "them, JSON an engine can load as a navmesh. mpw.py export DIR --nav -o map.nav.json.",
                   "references/games-film-print.md"),
    "keys-and-locks": ("Lock-aware search: state is (square, keys held), a locked door opens only with its key. "
                       "mpw.py path on a cyclic dungeon does this by default; --ignore-locks opens every lock.",
                       "references/pathfinding.md"),
    "uvtt": ("Universal VTT (.dd2vtt): one JSON file with a square-grid map picture in base64, walls as line of "
             "sight, doors as portals and lights. Foundry and other tabletops import it. It has no hex form.",
             "references/games-film-print.md"),
}
ALIASES = {"epsg:3857": "web-mercator", "3857": "web-mercator", "webmercator": "web-mercator",
           "plate-carree": "equirectangular", "lambert-azimuthal-equal-area": "laea",
           "indicatrix": "tissot", "great-circle": "geodesic", "loxodrome": "rhumb-line",
           "pgw": "world-file", "representative-fraction": "scale", "tiled": "tmj", "dd2vtt": "uvtt", "jps": "jump-point-search",
           "navmesh": "nav-export", "nav": "nav-export", "locks": "keys-and-locks",
           "universal-vtt": "uvtt", "trim-marks": "crop-marks", "height-map": "heightmap"}


def cmd_explain(a):
    key = a.term.strip().lower().replace(" ", "-").replace("_", "-")
    key = ALIASES.get(key, key)
    if key == "list":
        print("\n".join(sorted(GLOSSARY)))
        return
    if key not in GLOSSARY:
        print("Not in the built-in glossary: %r. Try `mpw.py explain list`, or search "
              "references/sources-and-terms.md and references/projections.md." % a.term)
        sys.exit(1)
    text, ref = GLOSSARY[key]
    print("%s: %s\nMore: %s" % (key, text, ref))


# ---------------------------------------------------------------- safe XML
def parse_xml(data):
    if isinstance(data, bytes):
        head = data[:4096].decode("utf-8", "replace")
    else:
        head = data[:4096]
    if "<!ENTITY" in head or "<!DOCTYPE" in head:
        die("refusing XML with a DOCTYPE or ENTITY (entity-expansion risk)")
    return ET.fromstring(data)


def local(tag):
    return tag.rsplit("}", 1)[-1]


# ---------------------------------------------------------------- GeoJSON model
def fc(features):
    return {"type": "FeatureCollection", "features": features}


def feat(geom, props=None):
    return {"type": "Feature", "geometry": geom, "properties": props or {}}


def read_geojson(path):
    with open(path, encoding="utf-8-sig") as f:
        d = json.load(f)
    if d.get("type") == "FeatureCollection":
        return d
    if d.get("type") == "Feature":
        return fc([d])
    return fc([feat(d)])


def iter_coords(geom):
    t = geom["type"] if geom else None
    if t is None:
        return
    if t == "GeometryCollection":
        for g in geom["geometries"]:
            yield from iter_coords(g)
        return
    c = geom["coordinates"]
    depth = {"Point": 0, "MultiPoint": 1, "LineString": 1, "MultiLineString": 2,
             "Polygon": 2, "MultiPolygon": 3}[t]

    def walk(x, d):
        if d == 0:
            yield x
        else:
            for y in x:
                yield from walk(y, d - 1)
    yield from walk(c, depth)


def extent(features):
    xs, ys = [], []
    for f in features:
        for p in iter_coords(f.get("geometry")):
            xs.append(p[0])
            ys.append(p[1])
    if not xs:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


# ---------------------------------------------------------------- GPX
GPX_NS = "http://www.topografix.com/GPX/1/1"


def _pt(el):
    p = [float(el.get("lon")), float(el.get("lat"))]
    for ch in el:
        if local(ch.tag) == "ele" and ch.text:
            p.append(float(ch.text))
    return p


def _meta(el):
    props = {}
    for ch in el:
        if local(ch.tag) in ("name", "desc", "type", "time") and ch.text:
            props[local(ch.tag)] = ch.text
    return props


def read_gpx(path):
    with open(path, "rb") as f:
        root = parse_xml(f.read())
    out = []
    for el in root:
        t = local(el.tag)
        if t == "wpt":
            out.append(feat({"type": "Point", "coordinates": _pt(el)}, dict(_meta(el), gpx="wpt")))
        elif t == "rte":
            pts = [_pt(p) for p in el if local(p.tag) == "rtept"]
            out.append(feat({"type": "LineString", "coordinates": pts}, dict(_meta(el), gpx="rte")))
        elif t == "trk":
            segs = [[_pt(p) for p in s if local(p.tag) == "trkpt"] for s in el if local(s.tag) == "trkseg"]
            props = dict(_meta(el), gpx="trk")
            if len(segs) == 1:
                out.append(feat({"type": "LineString", "coordinates": segs[0]}, props))
            else:
                out.append(feat({"type": "MultiLineString", "coordinates": segs}, props))
    return fc(out)


def _fmt(v):
    return repr(float(v))


def write_gpx(collection, path):
    ET.register_namespace("", GPX_NS)
    root = ET.Element("{%s}gpx" % GPX_NS, version="1.1", creator="mapwright mpw.py " + VERSION)
    skipped = 0

    def add_meta(el, props):
        for k in ("name", "desc", "type"):
            if k in props and props[k] is not None:
                ET.SubElement(el, "{%s}%s" % (GPX_NS, k)).text = str(props[k])

    def add_pt(parent, tag, p):
        e = ET.SubElement(parent, "{%s}%s" % (GPX_NS, tag), lat=_fmt(p[1]), lon=_fmt(p[0]))
        if len(p) > 2:
            ET.SubElement(e, "{%s}ele" % GPX_NS).text = _fmt(p[2])
        return e

    wpts, rtes, trks = [], [], []
    for f in collection["features"]:
        g, props = f.get("geometry"), f.get("properties") or {}
        if not g:
            continue
        t = g["type"]
        if t == "Point":
            wpts.append((g["coordinates"], props))
        elif t == "MultiPoint":
            wpts += [(c, props) for c in g["coordinates"]]
        elif t == "LineString":
            (rtes if props.get("gpx") == "rte" else trks).append(([g["coordinates"]], props))
        elif t == "MultiLineString":
            trks.append((g["coordinates"], props))
        else:
            skipped += 1
    for c, props in wpts:  # GPX 1.1 schema order: wpt, rte, trk
        add_meta(add_pt(root, "wpt", c), props)
    for segs, props in rtes:
        r = ET.SubElement(root, "{%s}rte" % GPX_NS)
        add_meta(r, props)
        for p in segs[0]:
            add_pt(r, "rtept", p)
    for segs, props in trks:
        t = ET.SubElement(root, "{%s}trk" % GPX_NS)
        add_meta(t, props)
        for s in segs:
            se = ET.SubElement(t, "{%s}trkseg" % GPX_NS)
            for p in s:
                add_pt(se, "trkpt", p)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return skipped


# ---------------------------------------------------------------- KML
KML_NS = "http://www.opengis.net/kml/2.2"


def _kml_coords(text):
    pts = []
    for tok in (text or "").split():
        pts.append([float(v) for v in tok.split(",")])
    return pts


def _kml_geom(el):
    t = local(el.tag)
    if t == "Point":
        return {"type": "Point", "coordinates": _kml_coords(_find_text(el, "coordinates"))[0]}
    if t == "LineString":
        return {"type": "LineString", "coordinates": _kml_coords(_find_text(el, "coordinates"))}
    if t == "Polygon":
        rings = []
        for b in el:
            if local(b.tag) in ("outerBoundaryIs", "innerBoundaryIs"):
                for lr in b.iter():
                    if local(lr.tag) == "coordinates":
                        if local(b.tag) == "outerBoundaryIs":
                            rings.insert(0, _kml_coords(lr.text))
                        else:
                            rings.append(_kml_coords(lr.text))
        return {"type": "Polygon", "coordinates": rings}
    if t == "MultiGeometry":
        gs = [_kml_geom(c) for c in el if local(c.tag) in ("Point", "LineString", "Polygon", "MultiGeometry")]
        return {"type": "GeometryCollection", "geometries": gs}
    return None


def _find_text(el, name):
    for e in el.iter():
        if local(e.tag) == name:
            return e.text
    return None


def read_kml(path):
    if path.lower().endswith(".kmz"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".kml")]
            main = "doc.kml" if "doc.kml" in names else names[0]
            data = z.read(main)
    else:
        with open(path, "rb") as f:
            data = f.read()
    root = parse_xml(data)
    out = []
    for pm in root.iter():
        if local(pm.tag) != "Placemark":
            continue
        props, geom = {}, None
        for ch in pm:
            t = local(ch.tag)
            if t in ("name", "description") and ch.text:
                props["desc" if t == "description" else t] = ch.text
            elif t == "ExtendedData":
                for d in ch:
                    if local(d.tag) == "Data":
                        v = _find_text(d, "value")
                        props[d.get("name")] = v
            elif t in ("Point", "LineString", "Polygon", "MultiGeometry"):
                geom = _kml_geom(ch)
        out.append(feat(geom, props))
    return fc(out)


def write_kml(collection, path):
    ET.register_namespace("", KML_NS)
    k = "{%s}" % KML_NS
    root = ET.Element(k + "kml")
    doc = ET.SubElement(root, k + "Document")

    def coords(pts):
        return " ".join(",".join(_fmt(v) for v in p) for p in pts)

    def geom(parent, g):
        t = g["type"]
        if t == "Point":
            ET.SubElement(ET.SubElement(parent, k + "Point"), k + "coordinates").text = coords([g["coordinates"]])
        elif t == "LineString":
            ET.SubElement(ET.SubElement(parent, k + "LineString"), k + "coordinates").text = coords(g["coordinates"])
        elif t == "Polygon":
            pe = ET.SubElement(parent, k + "Polygon")
            for i, ring in enumerate(g["coordinates"]):
                b = ET.SubElement(pe, k + ("outerBoundaryIs" if i == 0 else "innerBoundaryIs"))
                ET.SubElement(ET.SubElement(b, k + "LinearRing"), k + "coordinates").text = coords(ring)
        elif t.startswith("Multi"):
            m = ET.SubElement(parent, k + "MultiGeometry")
            for c in g["coordinates"]:
                geom(m, {"type": t[5:], "coordinates": c})
        elif t == "GeometryCollection":
            m = ET.SubElement(parent, k + "MultiGeometry")
            for sub in g["geometries"]:
                geom(m, sub)

    for f in collection["features"]:
        pm = ET.SubElement(doc, k + "Placemark")
        props = dict(f.get("properties") or {})
        if "name" in props:
            ET.SubElement(pm, k + "name").text = str(props.pop("name"))
        if "desc" in props:
            ET.SubElement(pm, k + "description").text = str(props.pop("desc"))
        if props:
            ed = ET.SubElement(pm, k + "ExtendedData")
            for key, v in props.items():
                d = ET.SubElement(ed, k + "Data", name=str(key))
                ET.SubElement(d, k + "value").text = "" if v is None else str(v)
        if f.get("geometry"):
            geom(pm, f["geometry"])
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return 0


# ---------------------------------------------------------------- Shapefile / DBF
SHP_TYPES = {0: "Null", 1: "Point", 3: "PolyLine", 5: "Polygon", 8: "MultiPoint",
             11: "PointZ", 13: "PolyLineZ", 15: "PolygonZ", 18: "MultiPointZ",
             21: "PointM", 23: "PolyLineM", 25: "PolygonM", 28: "MultiPointM", 31: "MultiPatch"}


def read_dbf(path, encoding=None):
    if encoding is None:
        cpg = os.path.splitext(path)[0] + ".cpg"
        encoding = open(cpg).read().strip() if os.path.exists(cpg) else "latin-1"
    with open(path, "rb") as f:
        hdr = f.read(32)
        nrec, hlen, rlen = struct.unpack("<IHH", hdr[4:12])
        fields = []
        while True:
            fd = f.read(32)
            if not fd or fd[0] == 0x0D:
                break
            name = fd[:11].split(b"\0")[0].decode("ascii", "replace")
            fields.append((name, chr(fd[11]), fd[16], fd[17]))
        f.seek(hlen)
        rows = []
        for _ in range(nrec):
            rec = f.read(rlen)
            if not rec or rec[0:1] == b"*":
                continue
            pos, row = 1, {}
            for name, typ, size, dec in fields:
                raw = rec[pos:pos + size].decode(encoding, "replace").strip()
                pos += size
                if typ in "NF":
                    try:
                        row[name] = (float(raw) if (dec or "." in raw) else int(raw)) if raw else None
                    except ValueError:
                        row[name] = None
                elif typ == "L":
                    row[name] = raw.upper() in ("Y", "T") if raw and raw != "?" else None
                else:
                    row[name] = raw
            rows.append(row)
    return fields, rows


def _ring_area(r):
    return sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1)) / 2.0


def read_shp(path):
    """Return (shape_type_name, bbox, list of GeoJSON geometries)."""
    geoms = []
    with open(path, "rb") as f:
        hdr = f.read(100)
        code, = struct.unpack(">i", hdr[:4])
        if code != 9994:
            die("not a shapefile (file code %d)" % code)
        stype, = struct.unpack("<i", hdr[32:36])
        bbox = struct.unpack("<4d", hdr[36:68])
        while True:
            rh = f.read(8)
            if len(rh) < 8:
                break
            _, clen = struct.unpack(">2i", rh)
            body = f.read(clen * 2)
            t, = struct.unpack("<i", body[:4])
            base = t % 10 if t < 30 else t
            if t == 0:
                geoms.append(None)
            elif base == 1:
                x, y = struct.unpack("<2d", body[4:20])
                geoms.append({"type": "Point", "coordinates": [x, y]})
            elif base == 8:
                n, = struct.unpack("<i", body[36:40])
                pts = [list(struct.unpack("<2d", body[40 + 16 * i:56 + 16 * i])) for i in range(n)]
                geoms.append({"type": "MultiPoint", "coordinates": pts})
            elif base in (3, 5):
                nparts, npts = struct.unpack("<2i", body[36:44])
                parts = list(struct.unpack("<%di" % nparts, body[44:44 + 4 * nparts]))
                o = 44 + 4 * nparts
                pts = [list(struct.unpack("<2d", body[o + 16 * i:o + 16 * i + 16])) for i in range(npts)]
                rings = [pts[parts[i]:(parts[i + 1] if i + 1 < nparts else npts)] for i in range(nparts)]
                if base == 3:
                    geoms.append({"type": "LineString", "coordinates": rings[0]} if nparts == 1
                                 else {"type": "MultiLineString", "coordinates": rings})
                else:
                    # Shapefile outer rings are clockwise (negative signed area), holes CCW.
                    # A hole goes to the last outer ring before it (common writer order).
                    polys = []
                    for r in rings:
                        if _ring_area(r) <= 0 or not polys:
                            polys.append([list(reversed(r))])  # to RFC 7946 CCW outer
                        else:
                            polys[-1].append(list(reversed(r)))  # CW hole
                    geoms.append({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                                 else {"type": "MultiPolygon", "coordinates": polys})
            else:
                geoms.append(None)
    return SHP_TYPES.get(stype, str(stype)), bbox, geoms


def read_shapefile(path):
    stype, bbox, geoms = read_shp(path)
    dbf = os.path.splitext(path)[0] + ".dbf"
    rows = read_dbf(dbf)[1] if os.path.exists(dbf) else [{}] * len(geoms)
    return fc([feat(g, r) for g, r in zip(geoms, rows)])


# ---------------------------------------------------------------- PNG + world file
def png_header(path):
    with open(path, "rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            die("not a PNG")
        ln, typ = struct.unpack(">I4s", f.read(8))
        if typ != b"IHDR":
            die("PNG without IHDR first")
        w, h, depth, ctype, comp, filt, inter = struct.unpack(">IIBBBBB", f.read(13))
    names = {0: "greyscale", 2: "RGB", 3: "palette", 4: "greyscale+alpha", 6: "RGBA"}
    return {"width": w, "height": h, "bit_depth": depth, "colour": names.get(ctype, ctype),
            "interlaced": bool(inter), "colour_type": ctype}


def png_grey_range(path):
    """Min and max of a non-interlaced greyscale PNG (8 or 16 bit), stdlib only."""
    with open(path, "rb") as f:
        data = f.read()
    pos, idat, hdr = 8, b"", None
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + ln
    w, h, depth, ctype, _, _, inter = hdr
    if ctype != 0 or inter or depth not in (8, 16):
        return None
    bpp = depth // 8
    stride = w * bpp
    raw = zlib.decompress(idat)
    prev = bytearray(stride)
    lo, hi = None, None
    for y in range(h):
        ft = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                line[i] = (line[i] + a) & 255
            elif ft == 2:
                line[i] = (line[i] + b) & 255
            elif ft == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        vals = struct.unpack(">%d%s" % (w, "H" if bpp == 2 else "B"), bytes(line))
        mn, mx = min(vals), max(vals)
        lo = mn if lo is None else min(lo, mn)
        hi = mx if hi is None else max(hi, mx)
        prev = line
    return lo, hi


def write_png_grey16(path, rows):
    """Write a 16-bit greyscale PNG from a list of rows of ints 0..65535."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + struct.pack(">%dH" % w, *r) for r in rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def world_file_for(path):
    stem, ext = os.path.splitext(path)
    short = "." + ext[1] + ext[-1] + "w" if len(ext) == 4 else None
    for cand in ([stem + short] if short else []) + [path + "w", stem + ".wld"]:
        if os.path.exists(cand):
            vals = [float(x) for x in open(cand).read().split()[:6]]
            return cand, vals
    return None, None


# ---------------------------------------------------------------- inspect
def _crs_from_prj(path):
    prj = os.path.splitext(path)[0] + ".prj"
    if os.path.exists(prj):
        txt = open(prj, encoding="utf-8", errors="replace").read().strip()
        return txt[:120] + ("..." if len(txt) > 120 else "")
    return None


def _summary_fc(collection, fmt, crs):
    counts = {}
    for f in collection["features"]:
        t = (f.get("geometry") or {}).get("type", "null")
        counts[t] = counts.get(t, 0) + 1
    keys = sorted({k for f in collection["features"] for k in (f.get("properties") or {})})
    return {"format": fmt, "features": len(collection["features"]), "geometry_types": counts,
            "extent": extent(collection["features"]), "crs": crs, "properties": keys[:30]}


def inspect_file(path):
    low = path.lower()
    if not os.path.exists(path):
        die("no such file: " + path)
    if low.endswith((".geojson", ".json")):
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
        crs = "WGS84 lon/lat (RFC 7946)"
        if "crs" in d:
            crs = "stated (pre-RFC 7946 crs member): " + json.dumps(d["crs"])[:100]
        return _summary_fc(read_geojson(path), "GeoJSON", crs)
    if low.endswith(".gpx"):
        s = _summary_fc(read_gpx(path), "GPX 1.1", "WGS84 (by schema)")
        pts = sum(1 for f in read_gpx(path)["features"] for _ in iter_coords(f["geometry"]))
        s["points"] = pts
        return s
    if low.endswith((".kml", ".kmz")):
        return _summary_fc(read_kml(path), "KMZ" if low.endswith("kmz") else "KML", "WGS84 (by spec)")
    if low.endswith(".shp"):
        stype, bbox, geoms = read_shp(path)
        s = _summary_fc(read_shapefile(path), "Shapefile", _crs_from_prj(path) or "not stated (no .prj)")
        s["shape_type"] = stype
        s["header_bbox"] = list(bbox)
        return s
    if low.endswith(".dbf"):
        fields, rows = read_dbf(path)
        return {"format": "dBASE", "records": len(rows),
                "fields": [{"name": n, "type": t, "size": s} for n, t, s, _ in fields]}
    if low.endswith(".png"):
        h = png_header(path)
        s = {"format": "PNG", **{k: v for k, v in h.items() if k != "colour_type"}}
        if h["colour_type"] == 0 and h["bit_depth"] == 16:
            s["note"] = "16-bit greyscale: likely a heightmap"
        rng = png_grey_range(path) if h["colour_type"] == 0 and h["width"] * h["height"] <= 4_000_000 else None
        if rng:
            s["value_range"] = list(rng)
        wf, vals = world_file_for(path)
        if wf:
            A, D, B, E, C, F = vals
            s["world_file"] = os.path.basename(wf)
            s["pixel_size"] = [A, E]
            s["rotation"] = [D, B]
            # world file holds the centre of the top-left pixel; edges are half a pixel out
            x0, y0 = C - A / 2, F - E / 2
            s["extent"] = [x0, y0 + E * h["height"], x0 + A * h["width"], y0]
            s["crs"] = _crs_from_prj(path) or "not stated (world files carry no CRS)"
        return s
    if low.endswith((".gpkg", ".mbtiles", ".sqlite")):
        con = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
        try:
            tabs = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
            app = con.execute("pragma application_id").fetchone()[0]
            if "gpkg_contents" in tabs:
                rows = con.execute("select table_name, data_type, srs_id, min_x, min_y, max_x, max_y "
                                   "from gpkg_contents").fetchall()
                layers = []
                for tn, dt, srs, *bb in rows:
                    n = con.execute('select count(*) from "%s"' % tn.replace('"', '""')).fetchone()[0]
                    srsname = con.execute("select srs_name, organization, organization_coordsys_id "
                                          "from gpkg_spatial_ref_sys where srs_id=?", (srs,)).fetchone()
                    layers.append({"table": tn, "type": dt, "rows": n, "extent": bb,
                                   "crs": "%s (%s:%s)" % srsname if srsname else srs})
                return {"format": "GeoPackage", "application_id": hex(app),
                        "user_version": con.execute("pragma user_version").fetchone()[0], "layers": layers}
            if "tiles" in tabs or "metadata" in tabs:
                meta = dict(con.execute("select name, value from metadata").fetchall()) if "metadata" in tabs else {}
                s = {"format": "MBTiles", "metadata": meta}
                if "tiles" in tabs:
                    s["tiles"] = con.execute("select count(*) from tiles").fetchone()[0]
                    s["zooms"] = [r[0] for r in con.execute("select distinct zoom_level from tiles order by 1")]
                s["crs"] = "EPSG:3857 tiles (TMS row order)"
                return s
            return {"format": "SQLite", "tables": sorted(tabs)}
        finally:
            con.close()
    die("unknown format: %s (GeoJSON, GPX, KML/KMZ, SHP, DBF, PNG, GPKG, MBTiles)" % path)


def cmd_inspect(a):
    s = inspect_file(a.file)
    if a.json:
        print(json.dumps(s, indent=2, default=str))
    else:
        for k, v in s.items():
            print("%-15s %s" % (k, json.dumps(v, default=str) if isinstance(v, (list, dict)) else v))


# ---------------------------------------------------------------- convert
READERS = {".geojson": read_geojson, ".json": read_geojson, ".gpx": read_gpx, ".kml": read_kml,
           ".kmz": read_kml, ".shp": read_shapefile}


def write_geojson(collection, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(collection, f, indent=1)
        f.write("\n")
    return 0


WRITERS = {".geojson": write_geojson, ".json": write_geojson, ".gpx": write_gpx, ".kml": write_kml}


def convert(src, dst):
    ri = os.path.splitext(src)[1].lower()
    wo = os.path.splitext(dst)[1].lower()
    if ri not in READERS:
        die("cannot read %s (reads %s)" % (ri, ", ".join(sorted(READERS))))
    if wo not in WRITERS:
        die("cannot write %s (writes %s)" % (wo, ", ".join(sorted(WRITERS))))
    col = READERS[ri](src)
    skipped = WRITERS[wo](col, dst)
    return len(col["features"]), skipped


def cmd_convert(a):
    n, skipped = convert(a.input, a.output)
    print("wrote %s: %d features%s" % (a.output, n - skipped,
                                       ", %d skipped (GPX holds points and lines only)" % skipped if skipped else ""))


# ---------------------------------------------------------------- geodesy
def vincenty_inverse(lat1, lon1, lat2, lon2, ell="WGS84", tol=1e-12, maxiter=200):
    """Distance (m), initial and final azimuth (deg). Raises ValueError if it does not converge."""
    a, f = ELLIPSOIDS[ell]
    b = a * (1 - f)
    if lat1 == lat2 and lon1 == lon2:
        return 0.0, 0.0, 0.0
    L = math.radians(lon2 - lon1)
    U1 = math.atan((1 - f) * math.tan(math.radians(lat1)))
    U2 = math.atan((1 - f) * math.tan(math.radians(lat2)))
    sU1, cU1, sU2, cU2 = math.sin(U1), math.cos(U1), math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(maxiter):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.hypot(cU2 * sl, cU1 * sU2 - sU1 * cU2 * cl)
        if ss == 0:
            return 0.0, 0.0, 0.0
        cs = sU1 * sU2 + cU1 * cU2 * cl
        sig = math.atan2(ss, cs)
        sa = cU1 * cU2 * sl / ss
        c2a = 1 - sa * sa
        c2sm = cs - 2 * sU1 * sU2 / c2a if c2a else 0.0
        C = f / 16 * c2a * (4 + f * (4 - 3 * c2a))
        lp = lam
        lam = L + (1 - C) * f * sa * (sig + C * ss * (c2sm + C * cs * (-1 + 2 * c2sm * c2sm)))
        if abs(lam - lp) < tol:
            break
    else:
        raise ValueError("Vincenty did not converge (nearly antipodal points)")
    u2 = c2a * (a * a - b * b) / (b * b)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = B * ss * (c2sm + B / 4 * (cs * (-1 + 2 * c2sm ** 2) - B / 6 * c2sm * (-3 + 4 * ss ** 2) * (-3 + 4 * c2sm ** 2)))
    s = b * A * (sig - ds)
    a1 = math.degrees(math.atan2(cU2 * math.sin(lam), cU1 * sU2 - sU1 * cU2 * math.cos(lam)))
    a2 = math.degrees(math.atan2(cU1 * math.sin(lam), -sU1 * cU2 + cU1 * sU2 * math.cos(lam)))
    return s, a1 % 360, a2 % 360


def geodesic_inverse(lat1, lon1, lat2, lon2, ell="WGS84"):
    """Returns dict with distance, azimuths and the method used."""
    try:
        s, a1, a2 = vincenty_inverse(lat1, lon1, lat2, lon2, ell)
        return {"distance_m": s, "azimuth1": a1, "azimuth2": a2, "method": "Vincenty (%s)" % ell}
    except ValueError:
        pass
    try:
        from geographiclib.geodesic import Geodesic
        a, f = ELLIPSOIDS[ell]
        r = Geodesic(a, f).Inverse(lat1, lon1, lat2, lon2)
        return {"distance_m": r["s12"], "azimuth1": r["azi1"] % 360, "azimuth2": r["azi2"] % 360,
                "method": "Karney via geographiclib (%s)" % ell}
    except ImportError:
        pass
    R = authalic_radius(ell)
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    s = 2 * R * math.asin(min(1.0, math.sqrt(h)))
    az = math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                 math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)))
    return {"distance_m": s, "azimuth1": az % 360, "azimuth2": None,
            "method": "haversine on the authalic sphere (Vincenty failed near antipodes; install "
                      "geographiclib for an exact answer; error up to ~0.5%)"}


def _q(sinphi, e):
    """Snyder 1987 eq. 3-12 (q for authalic latitude)."""
    if e == 0:
        return 2 * sinphi
    es = e * sinphi
    return (1 - e * e) * (sinphi / (1 - es * es) - (1 / (2 * e)) * math.log((1 - es) / (1 + es)))


def authalic_radius(ell="WGS84"):
    a, f = ELLIPSOIDS[ell]
    e = math.sqrt(f * (2 - f))
    return a * math.sqrt(_q(1.0, e) / 2)


def ellipsoid_area(ring, ell="WGS84"):
    """Area (m^2) of a lon/lat ring on the ellipsoid.

    Each point goes to the cylindrical equal-area projection of the ellipsoid
    (x = a*lambda, y = a*q(phi)/2), which is exact for area, and the ring's area
    is the planar shoelace there. Edges are therefore taken as straight in that
    projection: exact for parallels and meridians, an approximation for long
    oblique edges (densify them first).
    """
    a, f = ELLIPSOIDS[ell]
    e = math.sqrt(f * (2 - f))
    pts = [(a * math.radians(p[0]), a * _q(math.sin(math.radians(p[1])), e) / 2) for p in ring]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return abs(sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1] for i in range(len(pts) - 1)) / 2)


def polygon_area(geom, ell="WGS84"):
    t = geom["type"]
    polys = [geom["coordinates"]] if t == "Polygon" else geom["coordinates"] if t == "MultiPolygon" else []
    total = 0.0
    for poly in polys:
        total += ellipsoid_area(poly[0], ell) - sum(ellipsoid_area(h, ell) for h in poly[1:])
    return total


def parse_scale(s):
    s = s.replace(",", "").replace(" ", "")
    if ":" in s:
        s = s.split(":")[1]
    return float(s)


UNITS = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "mi": 1609.344}


def parse_len(s):
    for u in sorted(UNITS, key=len, reverse=True):
        if s.endswith(u):
            return float(s[:-len(u)]) * UNITS[u], u
    return float(s), "m"


def cmd_measure(a):
    if a.what == "distance":
        r = geodesic_inverse(a.lat1, a.lon1, a.lat2, a.lon2, a.ellipsoid)
        if a.json:
            print(json.dumps(r, indent=2))
        else:
            print("distance  %.3f m (%.3f km)" % (r["distance_m"], r["distance_m"] / 1000))
            print("bearing   %.6f deg (initial)" % r["azimuth1"])
            if r["azimuth2"] is not None:
                print("final     %.6f deg" % r["azimuth2"])
            print("method    %s" % r["method"])
    elif a.what == "area":
        col = READERS[os.path.splitext(a.file)[1].lower()](a.file)
        total = sum(polygon_area(f["geometry"], a.ellipsoid) for f in col["features"] if f.get("geometry"))
        r = {"area_m2": total, "area_km2": total / 1e6,
             "method": "ellipsoid (%s) via authalic latitude; edges straight in cylindrical equal-area" % a.ellipsoid}
        print(json.dumps(r, indent=2) if a.json else "area  %.1f m2 (%.6f km2)\nmethod %s" % (total, total / 1e6, r["method"]))
    elif a.what == "scale":
        n = parse_scale(a.scale)
        if a.map:
            m, _ = parse_len(a.map)
            g = m * n
            print("%s on the map = %.6g m = %.6g km on the ground at 1:%g" % (a.map, g, g / 1000, n))
        elif a.ground:
            g, _ = parse_len(a.ground)
            m = g / n
            print("%s on the ground = %.6g cm on the map at 1:%g" % (a.ground, m * 100, n))
        else:
            print("1:%g  1 cm = %.6g m = %.6g km; 1 km = %.6g cm" % (n, n / 100, n / 1e5, 1e5 / n))


# ---------------------------------------------------------------- projections (sphere unless noted)
def _wrap(lon):
    return (lon + 180.0) % 360.0 - 180.0


# Robinson as PROJ does it (src/projections/robin.cpp, MIT): per 5-degree node the
# value and cubic spline coefficients in degrees within the interval, stored by PROJ
# as C floats, so they are rounded to float32 here to reproduce PROJ to 0.1 mm.
def _f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


_ROB_X = [tuple(_f32(v) for v in c) for c in (
    (1.0, 2.2199e-17, -7.15515e-05, 3.1103e-06), (0.9986, -0.000482243, -2.4897e-05, -1.3309e-06),
    (0.9954, -0.00083103, -4.48605e-05, -9.86701e-07), (0.99, -0.00135364, -5.9661e-05, 3.6777e-06),
    (0.9822, -0.00167442, -4.49547e-06, -5.72411e-06), (0.973, -0.00214868, -9.03571e-05, 1.8736e-08),
    (0.96, -0.00305085, -9.00761e-05, 1.64917e-06), (0.9427, -0.00382792, -6.53386e-05, -2.6154e-06),
    (0.9216, -0.00467746, -0.00010457, 4.81243e-06), (0.8962, -0.00536223, -3.23831e-05, -5.43432e-06),
    (0.8679, -0.00609363, -0.000113898, 3.32484e-06), (0.835, -0.00698325, -6.40253e-05, 9.34959e-07),
    (0.7986, -0.00755338, -5.00009e-05, 9.35324e-07), (0.7597, -0.00798324, -3.5971e-05, -2.27626e-06),
    (0.7186, -0.00851367, -7.01149e-05, -8.6303e-06), (0.6732, -0.00986209, -0.000199569, 1.91974e-05),
    (0.6213, -0.010418, 8.83923e-05, 6.24051e-06), (0.5722, -0.00906601, 0.000182, 6.24051e-06),
    (0.5322, -0.00677797, 0.000275608, 6.24051e-06))]
_ROB_Y = [tuple(_f32(v) for v in c) for c in (
    (-5.20417e-18, 0.0124, 1.21431e-18, -8.45284e-11), (0.062, 0.0124, -1.26793e-09, 4.22642e-10),
    (0.124, 0.0124, 5.07171e-09, -1.60604e-09), (0.186, 0.0123999, -1.90189e-08, 6.00152e-09),
    (0.248, 0.0124002, 7.10039e-08, -2.24e-08), (0.31, 0.0123992, -2.64997e-07, 8.35986e-08),
    (0.372, 0.0124029, 9.88983e-07, -3.11994e-07), (0.434, 0.0123893, -3.69093e-06, -4.35621e-07),
    (0.4958, 0.0123198, -1.02252e-05, -3.45523e-07), (0.5571, 0.0121916, -1.54081e-05, -5.82288e-07),
    (0.6176, 0.0119938, -2.41424e-05, -5.25327e-07), (0.6769, 0.011713, -3.20223e-05, -5.16405e-07),
    (0.7346, 0.0113541, -3.97684e-05, -6.09052e-07), (0.7903, 0.0109107, -4.89042e-05, -1.04739e-06),
    (0.8435, 0.0103431, -6.4615e-05, -1.40374e-09), (0.8936, 0.00969686, -6.4636e-05, -8.547e-06),
    (0.9394, 0.00840947, -0.000192841, -4.2106e-06), (0.9761, 0.00616527, -0.000256, -4.2106e-06),
    (1.0, 0.00328947, -0.000319159, -4.2106e-06))]
_ROB_FXC, _ROB_FYC = 0.8487, 1.3523


def _robv(c, z):
    return c[0] + z * (c[1] + z * (c[2] + z * c[3]))


def _robdv(c, z):
    return c[1] + z * (c[2] + c[2] + z * 3 * c[3])


def _rob_fwd(lam, phi):
    dphi = abs(phi)
    i = min(int(math.floor(dphi * 11.45915590261646417544 + 1e-15)), 18)
    dphi = math.degrees(dphi - 0.08726646259971647884 * i)
    return _robv(_ROB_X[i], dphi) * _ROB_FXC * lam, math.copysign(_robv(_ROB_Y[i], dphi) * _ROB_FYC, phi)


def _rob_inv(x, y):
    lam = x / _ROB_FXC
    phi = abs(y / _ROB_FYC)
    if phi >= 1.0:
        if phi > 1.000001:
            raise ValueError("outside the Robinson outline")
        return lam / _ROB_X[18][0], math.copysign(math.pi / 2, y)
    i = int(math.floor(phi * 18))
    while True:
        if _ROB_Y[i][0] > phi:
            i -= 1
        elif _ROB_Y[i + 1][0] <= phi:
            i += 1
        else:
            break
    c = _ROB_Y[i]
    t = 5.0 * (phi - c[0]) / (_ROB_Y[i + 1][0] - c[0])
    for _ in range(100):  # Newton-Raphson, as PROJ
        t1 = (_robv(c, t) - phi) / _robdv(c, t)
        t -= t1
        if abs(t1) < 1e-10:
            break
    return lam / _robv(_ROB_X[i], t), math.copysign(math.radians(5 * i + t), y)


EE = (1.340264, -0.081106, 0.000893, 0.003796)


def forward(name, lon, lat, R=1.0, lon0=0.0, lat0=0.0):
    lam = math.radians(_wrap(lon - lon0))
    phi = math.radians(lat)
    if name == "webmercator":
        if abs(lat) > 85.05112877980659:
            raise ValueError("Web Mercator is cut at +-85.0511 deg")
        return WEB_R * lam, WEB_R * math.atanh(math.sin(phi))
    if name == "equirectangular":
        return R * lam * math.cos(math.radians(lat0)), R * phi
    if name == "mollweide":
        th = phi
        if abs(abs(phi) - math.pi / 2) < 1e-15:
            th = math.copysign(math.pi / 2, phi)
        else:
            k = math.pi * math.sin(phi)
            th = phi
            for _ in range(100):  # Newton on 2t + sin 2t = pi sin(phi), t = theta
                d = -(2 * th + math.sin(2 * th) - k) / (2 + 2 * math.cos(2 * th))
                th += d
                if abs(d) < 1e-15:
                    break
        return R * 2 * math.sqrt(2) / math.pi * lam * math.cos(th), R * math.sqrt(2) * math.sin(th)
    if name == "laea":
        p0 = math.radians(lat0)
        cc = math.sin(p0) * math.sin(phi) + math.cos(p0) * math.cos(phi) * math.cos(lam)
        if cc <= -1 + 1e-15:
            raise ValueError("LAEA is undefined at the antipode of the centre")
        k = math.sqrt(2 / (1 + cc))
        return (R * k * math.cos(phi) * math.sin(lam),
                R * k * (math.cos(p0) * math.sin(phi) - math.sin(p0) * math.cos(phi) * math.cos(lam)))
    if name == "robinson":
        x, y = _rob_fwd(lam, phi)
        return R * x, R * y
    if name == "equalearth":
        A1, A2, A3, A4 = EE
        th = math.asin(math.sqrt(3) / 2 * math.sin(phi))
        t2 = th * th
        t6 = t2 * t2 * t2
        x = R * 2 * math.sqrt(3) * lam * math.cos(th) / (3 * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
        y = R * th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
        return x, y
    raise ValueError("unknown projection " + name)


def inverse(name, x, y, R=1.0, lon0=0.0, lat0=0.0):
    if name == "webmercator":
        lam, phi = x / WEB_R, 2 * math.atan(math.exp(y / WEB_R)) - math.pi / 2
    elif name == "equirectangular":
        lam, phi = x / (R * math.cos(math.radians(lat0))), y / R
    elif name == "mollweide":
        th = math.asin(max(-1.0, min(1.0, y / (R * math.sqrt(2)))))
        phi = math.asin(max(-1.0, min(1.0, (2 * th + math.sin(2 * th)) / math.pi)))
        c = math.cos(th)
        lam = math.pi * x / (2 * R * math.sqrt(2) * c) if c > 1e-15 else 0.0
    elif name == "laea":
        p0 = math.radians(lat0)
        rho = math.hypot(x, y)
        if rho < 1e-15:
            return lon0, lat0
        c = 2 * math.asin(min(1.0, rho / (2 * R)))
        phi = math.asin(max(-1.0, min(1.0, math.cos(c) * math.sin(p0) + y * math.sin(c) * math.cos(p0) / rho)))
        lam = math.atan2(x * math.sin(c), rho * math.cos(p0) * math.cos(c) - y * math.sin(p0) * math.sin(c))
    elif name == "robinson":
        lam, phi = _rob_inv(x / R, y / R)
    elif name == "equalearth":
        A1, A2, A3, A4 = EE
        yy = y / R
        th = yy
        for _ in range(100):
            t2 = th * th
            t6 = t2 * t2 * t2
            fy = th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2)) - yy
            fpy = A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)
            d = fy / fpy
            th -= d
            if abs(d) < 1e-15:
                break
        t2 = th * th
        t6 = t2 * t2 * t2
        lam = 3 * (x / R) * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)) / (2 * math.sqrt(3) * math.cos(th))
        phi = math.asin(max(-1.0, min(1.0, 2 * math.sin(th) / math.sqrt(3))))
    else:
        raise ValueError("unknown projection " + name)
    return _wrap(math.degrees(lam) + lon0), math.degrees(phi)


PROJECTIONS = {
    "webmercator": "EPSG:3857 spherical Mercator on R = 6378137 m (metres; conformal)",
    "equirectangular": "plate carree (lat0 = standard parallel; R units)",
    "mollweide": "Mollweide, equal-area (R units)",
    "laea": "Lambert azimuthal equal-area centred on lon0, lat0 (sphere, R units)",
    "robinson": "Robinson, PROJ cubic-spline table (compromise; R units)",
    "equalearth": "Equal Earth, equal-area (R units)",
}


def cmd_project(a):
    if a.list:
        for k, v in PROJECTIONS.items():
            print("%-16s %s" % (k, v))
        return
    if a.name not in PROJECTIONS:
        die("unknown projection %r; --list shows them" % a.name)
    try:
        if a.inverse:
            lon, lat = inverse(a.name, a.x, a.y, a.radius, a.lon0, a.lat0)
            r = {"lon": lon, "lat": lat}
        else:
            x, y = forward(a.name, a.x, a.y, a.radius, a.lon0, a.lat0)
            r = {"x": x, "y": y}
    except ValueError as e:
        die(str(e))
    print(json.dumps(r) if a.json else "  ".join("%s=%.10g" % kv for kv in r.items()))


# ---------------------------------------------------------------- find / fetch
def _find():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mpw_find
    return mpw_find


def cmd_find(a):
    F = _find()
    if a.list:
        for s in F.CATALOGUE:
            print("%-19s %-40s %s | %s" % (s["id"], s["name"][:40], s["licence"], s["credit"]))
        return
    if not a.query:
        die("find QUERY (a place, a time or a subject); --list shows the catalogue")
    http = F.Http(VERSION, cache_dir=a.cache) if a.online else None
    out = F.find(" ".join(a.query), http=http, online=a.online, limit=a.limit)
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    print("query: %s  (kinds: %s)" % (out["query"], ", ".join(out["kinds"])))
    for r in out["results"]:
        print("- [%s] %s\n    %s\n    licence: %s\n    credit: %s" % (r["source"], r["title"], r["url"], r["licence"], r["credit"]))
        if r.get("key"):
            print("    key: " + r["key"])
    for e in out["errors"]:
        print("lookup failed: " + e)


def cmd_fetch(a):
    F = _find()
    try:
        http = F.Http(VERSION, cache_dir=a.cache, cap_mb=a.max_mb)
        e = F.fetch(a.url, a.out, http, source_id=a.source, name=a.name, licence=a.licence, credit=a.credit)
    except F.Refused as ex:
        die(str(ex))
    print("%s  %d bytes  (%s, cache %s)\ncredit: %s\nwrote %s and %s" % (
        os.path.join(a.out, e["file"]), e["bytes"], e["source"], e["cache"], e["credit"],
        os.path.join(a.out, "sources.json"), os.path.join(a.out, "CREDITS.txt")))


# ---------------------------------------------------------------- generator
# ---------------------------------------------------------------- read / trace
def _read():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mpw_read
    return mpw_read


def _gcps(R, a):
    try:
        return [R.parse_gcp(g) for g in (a.gcp or [])]
    except ValueError as e:
        die(str(e))


def cmd_read(a):
    R = _read()
    if not os.path.isfile(a.image):
        die("no such image: " + a.image)
    g = _gcps(R, a)
    try:
        if a.prompt:
            out = R.agent_prompt(a.image)
        elif a.answers:
            with open(a.answers, encoding="utf-8") as f:
                out = R.validate_answers(a.image, json.load(f), g, a.units)
        else:
            out = R.read_report(a.image, g, a.units, write_world=a.world)
    except ValueError as e:
        die(str(e))
    print(R.dumps(out))


def cmd_trace(a):
    R = _read()
    if not os.path.isfile(a.image):
        die("no such image: " + a.image)
    g = _gcps(R, a)
    world = a.world
    if world == "auto":
        world = R.world_file_path(a.image)
        world = world if os.path.isfile(world) else None
    try:
        colour = R.parse_hex(a.colour) if a.colour else None
        fc_ = R.trace(a.image, a.cls, colour, a.tol, a.mode, a.epsilon, a.min_area, a.min_length, a.clean,
                      g, a.units, world, a.fill_holes)
    except ValueError as e:
        die(str(e))
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(fc_, f)
        print(json.dumps(dict(fc_["mapwright"], out=a.out)))
    else:
        print(json.dumps(fc_))


def _gen():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mpw_gen
    return mpw_gen


def _window(s):
    try:
        v = tuple(float(t) for t in s.split(","))
    except ValueError:
        v = ()
    if len(v) != 4:
        die("--window wants x0,y0,x1,y1 in map km (0..1000, y south)")
    return v


def _places():
    _gen()
    import mpw_places
    return mpw_places


def _space():
    _gen()
    import mpw_space
    return mpw_space


SPACE = ("sector", "system", "planet", "deck")


def cmd_gen_space(a):
    S = _space()
    try:
        if a.what == "sector":
            r = S.gen_sector(a.seed, a.out, a.size, a.density, a.jump, a.real, a.radius_pc, VERSION, a.name_style,
                             a.systems)
        elif a.what == "system":
            r = S.gen_system(a.seed, a.out, a.star, a.planets, VERSION, a.name_style, a.sector_seed, a.hex)
        elif a.what == "planet":
            r = S.gen_planet(a.seed, a.out, a.kind, a.width, VERSION)
        else:
            r = S.gen_deck(a.seed, a.out, a.w, a.h, a.decks, a.hull, a.pps, VERSION, a.name_style)
    except (ValueError, OSError, KeyError) as e:
        die(str(e))
    if a.json:
        print(json.dumps(r, indent=1))
    elif a.what == "sector":
        print("wrote %s: %s, %d worlds, %d routes (%d long) in %.2f s"
              % (r["out"], r["name"], r["worlds"], r["routes"], r["long"], r["times"]["total"]))
    elif a.what == "system":
        print("wrote %s: %s (%s), %d planets, %d moons in %.2f s"
              % (r["out"], r["name"], r["star"], r["planets"], r["moons"], r["times"]["total"]))
    elif a.what == "planet":
        print("wrote %s: %s planet texture %dx%d, %d craters in %.2f s"
              % (r["out"], r["planet"], r["width"], r["height"], r["craters"], r["times"]["total"]))
    else:
        print("wrote %s: %s, %d deck(s), %d rooms in %.2f s" % (r["out"], r["name"], r["decks"], r["rooms"],
                                                                r["times"]["total"]))


def _kind(d):
    try:
        with open(os.path.join(d, "recipe.json"), encoding="utf-8") as f:
            return json.load(f).get("kind")
    except (OSError, ValueError):
        return None


def cmd_gen_place(a):
    P = _places()
    try:
        if a.what == "city":
            r = P.gen_city(a.seed, a.out, a.bands, None if a.no_walls else a.wall, a.spokes, a.ring_m, a.lot_m2,
                           a.parent, a.settlement, a.sea, a.river, a.style, VERSION, a.name_style)
        else:
            cave = {k: getattr(a, k) for k in ("fill", "passes", "birth", "survival", "radius", "border")
                    if getattr(a, k, None) is not None}
            r = P.gen_grid(a.what, a.seed, a.out, a.w, a.h, getattr(a, "method", "bsp"), getattr(a, "grid", "square"),
                           a.pps, a.style, VERSION, a.name_style, cave=cave or None,
                           density=getattr(a, "density", None), branches=getattr(a, "branches", None))
    except (ValueError, OSError, KeyError) as e:
        die(str(e))
    if a.json:
        print(json.dumps(r, indent=1))
    elif a.what == "city":
        print("wrote %s: %s, %d streets, %d blocks, %d lots, %d districts, %d gates, %d bridges in %.2f s"
              % (r["out"], r["name"], r["streets"], r["blocks"], r["lots"], r["districts"], r["gates"], r["bridges"],
                 r["times"]["total"]))
    else:
        print("wrote %s: %s, %dx%d %s squares at %d px, %d rooms, %d doors, %d wall runs, %d lights in %.2f s"
              % (r["out"], r["name"], r["w"], r["h"], r["grid"], r["pps"], r["rooms"], r["doors"], r["walls"],
                 r["lights"], r["times"]["total"]))


def cmd_gen(a):
    if a.what in ("city", "dungeon", "battle"):
        return cmd_gen_place(a)
    if a.what in SPACE:
        return cmd_gen_space(a)
    g = _gen()
    try:
        if a.what == "world":
            r = g.gen_world(a.seed, a.cells, a.out, a.plates, a.erosion, a.lat_top, a.lat_bottom, a.raster, VERSION,
                            style=a.style, pattern=a.pattern)
        else:
            win = _window(a.window) if a.window else None
            ch = None
            if getattr(a, "chunk", None):
                try:
                    c_, r_ = (int(v) for v in a.chunk.split(","))
                except ValueError:
                    die("--chunk is COL,ROW, e.g. 1,2")
                ch = (c_, r_, a.chunk_km)
            r = g.gen_region(a.parent, win, a.cells, a.out, a.detail, a.raster, VERSION, chunk=ch)
    except (ValueError, OSError) as e:
        die(str(e))
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print("wrote %s: %d cells, %d rivers, %d lakes, %d settlements, %d roads, %d names in %.2f s"
              % (r["out"], r["cells"], r["rivers"], r["lakes"], r["settlements"], r["roads"], r["names"],
                 r["times"]["total"]))


def cmd_zoom(a):
    a.what = "region"
    a.parent = a.dir
    cmd_gen(a)


def cmd_check_range(a):
    P = _places()
    if a.seeds < 2:
        die("--seeds must be at least 2")
    out = a.dir or "range-" + a.range
    try:
        rep = P.dungeon_range(a.range, a.seeds, a.w, a.h)
    except ValueError as e:
        die(str(e))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "range.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, indent=1)
        f.write("\n")
    with open(os.path.join(out, "range.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(P.range_svg(rep))
    if a.json:
        print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1))
        return
    print("expressive range: gen dungeon --method %s, %d seeds, %dx%d -> %s" % (a.range, a.seeds, a.w, a.h, out))
    for k, m in rep["metrics"].items():
        print("  %-19s min %.3f  mean %.3f  max %.3f" % (k, m["min"], m["mean"], m["max"]))
    for p in rep["pairs"]:
        print("  %s x %s: %d of %d bins used, fullest bin %.1f%%%s, %s TV %.3f"
              % (p["x"], p["y"], p["occupied"], P.RANGE_BINS ** 2, 100 * p["fullest_share"],
                 " DOMINANT" if p["dominant"] else "", rep["stability"], p["stability_tv"]))


def _pathmod():
    _places()
    import mpw_path
    return mpw_path


def _xy(s):
    try:
        return tuple(float(t) for t in s.split(","))
    except (ValueError, AttributeError):
        die("bad coordinate %r: want X,Y" % s)


def cmd_path(a):
    M = _pathmod()
    out = a.out or a.dir
    try:
        G, rc = M.build(a.dir, a.moves, agent=a.agent)
        if a.jps and M.jps_refusal(G):
            die(M.jps_refusal(G))
        if not a.to:
            die("path needs --to")
        goals = [G.node(_xy(t)) for t in a.to]
        if a.field:
            dist, flow = M.field(G, goals)
            rep = M.field_files(a.dir, out, G, goals, dist, flow)
            rep = {k: v for k, v in rep.items() if k != "cells"}
            msg = "field: %d goal(s), %d cells reached, %d unreachable, max %.3f %s -> %s" % (
                len(goals), rep["reachable"], rep["unreachable"], rep["max"], G.units, out)
        else:
            if not a.src or len(goals) != 1:
                die("path needs --from and one --to (or --field)")
            s = G.node(_xy(a.src))
            locked = getattr(G, "locks", 0) and not a.ignore_locks
            extra = None
            if a.jps:
                if locked:
                    die("--jps does not track keys; add --ignore-locks to search with every lock open")
            if locked:
                cost, path, picks, exp = M.lock_search(G, s, goals[0])
                extra = {"locks": G.locks, "keys": [dict(key=p["key"], step=p["step"], cell=G.xy(path[p["step"]]))
                                                    for p in picks] if path else []}
                if cost is None:
                    die("no route: the goal cannot be reached from the start with the keys on the map "
                        "(--ignore-locks opens every lock)", 1)
            else:
                cost, path, exp = (M.jps if a.jps else M.search)(G, s, goals[0] if a.jps else goals)
                if cost is None:
                    die("no route: the goal cannot be reached from the start", 1)
                if getattr(G, "locks", 0):
                    extra = {"locks_open": G.locks}
            if a.jps:
                extra = dict(extra or {}, search="jps")
            if a.agent > 1:
                extra = dict(extra or {}, agent=dict(squares=a.agent, anchor="top-left"))
            rep = M.path_files(a.dir, out, G, s, goals[0], cost, path, exp, extra)
            rep = {k: v for k, v in rep.items() if k != "path"}
            msg = "path: cost %.4f %s, %d steps, %d cells expanded -> %s" % (rep["cost"], G.units, rep["steps"],
                                                                             exp, out)
    except (ValueError, OSError) as e:
        die(str(e))
    print(json.dumps(rep, indent=1) if a.json else msg)


def cmd_travel(a):
    M = _pathmod()
    out = a.out or a.dir
    if _kind(a.dir) not in ("world", "region"):
        die("travel works on world and region recipes")
    G, rc = M.build(a.dir, cost=a.mode)
    s = G.node(_xy(a.src))
    rep = M.travel(a.dir, out, G, s, a.band, G.node(_xy(a.to)) if a.to else None)
    if a.json:
        print(json.dumps({k: v for k, v in rep.items() if k != "cells"}, indent=1))
    else:
        print("travel (%s): %d cells reached, farthest %.2f h, bands of %.1f h: %s -> %s" % (
            a.mode, rep["reachable"], rep["max_hours"], a.band, rep["bands"], out)
            + ("; to goal %s h" % rep["to"]["hours"] if rep.get("to") else ""))


def _pts(G, s):
    return [G.node(_xy(t)) for t in s.split(";") if t.strip()]


def cmd_check_grid(a):
    M = _pathmod()
    if _kind(a.dir) not in ("dungeon", "battle", "deck"):
        die("--chokepoints and --fair work on dungeon, battle and deck recipes")
    G, rc = M.build(a.dir)
    gj = M._load(a.dir, "grid.json") if rc["kind"] != "deck" else {}
    ent = tuple(gj["entrance"]) if gj.get("entrance") else G.nodes[0]
    out = {}
    try:
        if a.chokepoints:
            goal = tuple(gj["goal"]) if gj.get("goal") else None
            rep = M.chokepoints(G, gj.get("rooms", []), ent, goal)
            M.write(a.dir, "chokepoints.json", rep)
            out["chokepoints"] = rep
            if not a.json:
                print("chokepoints: %d cells, %d bridges, %d passable%s%s" % (
                    len(rep["chokepoints"]), rep["bridges"], rep["passable"],
                    ", min cut entrance to goal %s" % rep["min_cut"]["size"] if "min_cut" in rep else "",
                    ", equals brute force: %s" % rep["brute_force_equal"] if "brute_force_equal" in rep else ""))
                for r in sorted(rep["chokepoints"], key=lambda r: -r["cut_off"])[:8]:
                    print("  %s cuts off %d cells%s" % (r["cell"], r["cut_off"],
                                                        ", rooms %s" % r["rooms_cut_off"] if r["rooms_cut_off"] else ""))
        if a.fair:
            if a.starts:
                starts = _pts(G, a.starts)
            else:
                d0, _ = M.dijkstra(G.out, [ent])
                starts = [ent, max(d0, key=lambda n: (d0[n], n))]
            if a.resources:
                res = _pts(G, a.resources)
            else:
                cand = [(int(L["x"]), int(L["y"])) for L in gj.get("lights", [])]
                cand = cand or [(r["x"] + r["w"] // 2, r["y"] + r["h"] // 2) for r in gj.get("rooms", [])]
                res = [c for c in cand if c in G.ok]
            if not res:
                die("--fair needs resources: none found, pass --resources X,Y;X,Y")
            rep = M.fair(G, starts, res)
            M.write(a.dir, "fair.json", rep)
            out["fair"] = rep
            if not a.json:
                print("fair: areas %s (ratio %s), tied %d, unreached %d of %d; resources reached first %s" % (
                    rep["areas"], rep["area_ratio"], rep["tied"], rep["unreached"], rep["passable"],
                    rep["resources_first"]))
    except ValueError as e:
        die(str(e))
    if a.json:
        print(json.dumps(out, indent=1))


def cmd_check(a):
    if a.range:
        return cmd_check_range(a)
    if (a.chokepoints or a.fair) and a.dir:
        return cmd_check_grid(a)
    if not a.dir:
        die("check needs a recipe folder (or --range METHOD)")
    g = _gen()
    if not os.path.isfile(os.path.join(a.dir, "recipe.json")):
        die("no recipe.json in " + a.dir)
    if _kind(a.dir) in ("city", "dungeon", "battle"):
        bars = _places().check(a.dir, determinism=not a.no_regen, labels=not a.no_labels)
    elif _kind(a.dir) in SPACE:
        bars = _space().check(a.dir, determinism=not a.no_regen, labels=not a.no_labels)
    else:
        bars = g.check(a.dir, determinism=not a.no_regen)
    if not a.no_labels and _kind(a.dir) not in ("city", "dungeon", "battle") + SPACE:
        r = _render()
        try:
            lb = r.check_labels(a.dir, a.style)
        except ValueError as e:
            die(str(e))
        nxt = max(b[0] for b in bars) + 1
        bars += [(nxt + i, name, ok, detail) for i, (name, ok, detail) in enumerate(lb)]
    if not a.no_aistyle and _kind(a.dir) not in ("city", "dungeon", "battle") + SPACE:
        # optional: one bar per styled picture with a sidecar in the folder; none there, no bar
        ab = _aistyle().bars(a.dir)
        nxt = max(b[0] for b in bars) + 1
        bars += [(nxt + i, name, ok, detail) for i, (name, ok, detail) in enumerate(ab)]
    period = a.period
    if period is None and a.style in _render().STYLES:
        period = _render().STYLES[a.style].get("period")  # a style may carry its year
    if period is not None:
        r = _render()
        try:
            used = set()
            if _kind(a.dir) not in ("city", "dungeon", "battle") + SPACE:
                with open(os.path.join(a.dir, "recipe.json"), encoding="utf-8") as f:
                    used = r.map_conventions(a.style, json.load(f))
            used |= {u.strip() for u in (a.uses or "").split(",") if u.strip()}
            pb = r.period_lint(used, period, a.period_kind)
        except ValueError as e:
            die(str(e))
        nxt = max(b[0] for b in bars) + 1
        bars += [(nxt + i, name, ok, detail) for i, (name, ok, detail) in enumerate(pb)]
    if a.json:
        print(json.dumps([dict(bar=b[0], name=b[1], ok=b[2], detail=b[3]) for b in bars], indent=1))
    else:
        for num, name, ok, detail in bars:
            print("bar %d %s: %s (%s)" % (num, "SKIP" if ok is None else ("PASS" if ok else "FAIL"), name, detail))
    if any(b[2] is False for b in bars):
        sys.exit(1)


def cmd_names(a):
    _gen()
    import mpw_names
    if a.list:
        for k in sorted(mpw_names.STYLES):
            st = mpw_names.STYLES[k]
            print("%-9s %s (C=%s; V=%s; S=%s)" % (k, st["desc"], st["C"], st["V"], st["S"]))
        return
    try:
        if a.dir:
            g = _gen()
            rc_path = os.path.join(a.dir, "recipe.json")
            if not os.path.isfile(rc_path):
                die("no recipe.json in " + a.dir)
            with open(rc_path, encoding="utf-8") as f:
                rc = json.load(f)
            if rc["kind"] != "world":
                die("names DIR renames a world; a child map takes its parent's language (rename the parent, "
                    "then zoom again)")
            if a.style or a.pattern:
                rc["language"] = mpw_names.make_language(rc["seed"], a.style, a.pattern)
                p = rc["params"]
                g.gen_world(rc["seed"], p["cells"], a.dir, p["plates"], p["erosion_steps"], p["lat_top"],
                            p["lat_bottom"], p["raster_px"], rc["tool_version"], language=rc["language"])
            with open(os.path.join(a.dir, "names.json"), encoding="utf-8") as f:
                nj = json.load(f)
            if a.json:
                print(json.dumps(nj, indent=1))
            else:
                print("language: %s" % nj["language"]["style"])
                for e in nj["names"]:
                    print("%-10s %4d  %s" % (e["kind"], e["id"], e["name"]))
            return
        lang, names = mpw_names.sample(a.sample, a.seed, a.style, a.pattern)
    except ValueError as e:
        die(str(e))
    if a.json:
        print(json.dumps(dict(language=lang, names=names), indent=1))
    else:
        print("\n".join(names))


# ---------------------------------------------------------------- render
def _render():
    _gen()
    import mpw_render
    return mpw_render


def _need_recipe(d):
    if not os.path.isfile(os.path.join(d, "recipe.json")):
        die("no recipe.json in " + d)


def cmd_render(a):
    r = _render()
    _need_recipe(a.dir)
    if _kind(a.dir) in SPACE:
        try:
            if a.title:
                print("mpw: --title is not used on %s maps yet; the recipe's name stays" % _kind(a.dir), file=sys.stderr)
            svg = _space().render_svg(a.dir, a.view)
            r.write_out(svg, a.out)
        except (ValueError, RuntimeError, OSError) as e:
            die(str(e))
        print("wrote %s" % a.out)
        return
    if _kind(a.dir) in ("city", "dungeon", "battle"):
        try:
            svg = _places().render_svg(a.dir, None if a.style == "topographic" else a.style, a.title)
            r.write_out(svg, a.out)
        except (ValueError, RuntimeError, OSError) as e:
            die(str(e))
        print("wrote %s" % a.out)
        return
    try:
        svg, info = r.render_svg(a.dir, a.style, a.font, a.title)
        r.write_out(svg, a.out)
    except (ValueError, RuntimeError, OSError) as e:
        die(str(e))
    info.pop("labels")
    info["out"] = a.out
    info["svg_bytes"] = len(svg.encode("utf-8"))
    if a.json:
        print(json.dumps(info, indent=1))
    else:
        print("wrote %s: style %s, %d labels (%d dropped), %d legend entries, %.2f s"
              % (a.out, a.style, info["placed"], len(info["dropped"]), len(info["legend"]), info["times"]["total"]))


def _export():
    _gen()
    import mpw_export
    return mpw_export


EXPORT_OPTS = ("size", "flip", "bits", "tile", "encoding", "csv", "deck", "pps", "exaggeration", "base", "print_mm",
               "flat_sea", "paper", "landscape", "dpi", "bleed", "no_marks", "margin", "fit", "style", "nav", "agent")


def cmd_export(a):
    _need_recipe(a.dir)
    try:
        bars, files = _export().export(a.dir, a.out, a.to, VERSION, **{k: getattr(a, k) for k in EXPORT_OPTS})
    except (ValueError, OSError, KeyError, RuntimeError) as e:
        die(str(e))
    if a.json:
        print(json.dumps(dict(files=files, bars=[dict(name=n, ok=ok, detail=det) for n, ok, det in bars]), indent=1))
    else:
        for name, ok, detail in bars:
            print("%s: %s (%s)" % ("PASS" if ok else "FAIL", name, detail))
        print("wrote %s" % ", ".join(files))
    if any(b[1] is False for b in bars):
        sys.exit(1)


def cmd_label(a):
    r = _render()
    _need_recipe(a.dir)
    try:
        svg, info = r.render_svg(a.dir, a.style, a.font)
    except (ValueError, OSError) as e:
        die(str(e))
    bars = r.label_bars(svg)
    res = dict(placed=[dict(text=x["text"], kind=x["kind"], x=x["x"], y=x["y"], size=x["size"], angle=x["angle"],
                            box=[round(v, 1) for v in x["box"]]) for x in info["labels"]],
               dropped=info["dropped"], bars=[dict(name=n, ok=ok, detail=dt) for n, ok, dt in bars])
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print("%d labels placed, %d dropped (no free spot)" % (len(res["placed"]), len(res["dropped"])))
        for n, ok, dt in bars:
            print("%s: %s (%s)" % ("SKIP" if ok is None else ("PASS" if ok else "FAIL"), n, dt))
    if any(b[1] is False for b in bars):
        sys.exit(1)


def cmd_legend(a):
    r = _render()
    _need_recipe(a.dir)
    kind = _kind(a.dir)
    if kind == "battle":
        P = _places()
        ents = [dict(kind=k, label=t) for k, t in P.battle_legend(P.load(a.dir, "grid.json"))]
        if a.out and ents:
            _, st = P.pstyle(None, "battle")
            body, box = P.legend_box_svg([(e["kind"], e["label"]) for e in ents], 0, 0, st, 40)
            w, h = box[2] - box[0] + 8, box[3] - box[1] + 8
            svg = "\n".join(['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%.1f %.1f %d %d">'
                             % (w, h, box[0] - 4, box[1] - 4, w, h), body, "</svg>", ""])
            try:
                r.write_out(svg, a.out)
            except (ValueError, RuntimeError) as e:
                die(str(e))
        if a.json:
            print(json.dumps(ents, indent=1))
        else:
            for e in ents:
                print("%-6s %s" % (e["kind"], e["label"]))
        return
    if not os.path.exists(os.path.join(a.dir, "mesh.json")):
        die("legend lists symbols on world, region and battle maps; this %s map has no legend" % (kind or "unknown"))
    try:
        st = r.style(a.style)
    except ValueError as e:
        die(str(e))
    rc, m, feats = r.load(a.dir)
    ents = r.legend_entries(feats, m, st, rc)
    if a.out:
        frame = (0, 0, 1, 22 + 15 * len(ents) + 2 * r.MARGIN)
        body, box = r.legend_svg(ents, frame, st)
        w, h = box[2] + r.MARGIN, box[3] + r.MARGIN
        svg = "\n".join(['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
                         % (w, h, w, h)] + body + ["</svg>", ""])
        try:
            r.write_out(svg, a.out)
        except (ValueError, RuntimeError) as e:
            die(str(e))
    if a.json:
        print(json.dumps(ents, indent=1))
    else:
        for e in ents:
            print("%-6s %s" % (e["kind"], e["label"]))


def cmd_style(a):
    r = _render()
    if a.list or not a.name:
        for k in sorted(r.STYLES):
            print("%-18s %s" % (k, r.STYLES[k]["desc"]))
        return
    try:
        print(json.dumps(r.style(a.name), indent=1))
    except ValueError as e:
        die(str(e))


def _aistyle():
    _render()
    import mpw_aistyle
    return mpw_aistyle


def cmd_aistyle(a):
    ai = _aistyle()
    if a.list:
        for k in sorted(ai.LOOKS):
            print("%-18s over %-18s %s" % (k, ai.LOOKS[k]["base"], ai.LOOKS[k]["desc"]))
        return
    if not a.dir:
        die("aistyle RECIPE --look NAME [--dry-run]; --list shows the looks")
    _need_recipe(a.dir)
    if a.measure:
        try:
            m = ai.measure(a.dir, a.measure)
        except (ValueError, OSError) as e:
            die(str(e))
        ok, detail = ai.judge(m)
        if a.json:
            print(json.dumps(dict(overlap=m, ok=ok, detail=detail), indent=1))
        else:
            print("%s: %s" % ("SKIP" if ok is None else ("PASS" if ok else "FAIL"), detail))
        if ok is False:
            sys.exit(1)
        return
    if not a.look:
        die("aistyle wants --look NAME (%s)" % ", ".join(sorted(ai.LOOKS)))
    try:
        res = ai.run(a.dir, a.look, out=a.out, host=a.host, denoise=a.denoise, seed=a.seed, dry_run=a.dry_run,
                     template=a.workflow, model=a.model, clip=a.clip, vae=a.vae, size=a.size, style=a.style,
                     font=a.font, title=a.title, timeout=a.timeout, do_measure=not a.no_measure)
    except (ValueError, RuntimeError, OSError) as e:
        die(str(e))
    if a.json:
        print(json.dumps(res, indent=1))
        return
    if res.get("warning"):
        print("warning: " + res["warning"])
    if res["dry_run"]:
        print("dry run: wrote %s and %s (%dx%d, %s, seed %d, denoise %.2f runs as %.3f); no server contacted"
              % (res["control"], res["workflow"], res["size"][0], res["size"][1], res["look"], res["seed"],
                 res["denoise"], res["denoise_effective"]))
        return
    ov = res["overlap"]
    print("wrote %s (%s, seed %d, denoise %.2f runs as %.3f, %.0f s) and %s"
          % (res["out"], res["look"], res["seed"], res["denoise"], res["denoise_effective"], res["seconds"],
             res["sidecar"]))
    print("%s: %s" % ("SKIP" if ov["ok"] is None else ("PASS" if ov["ok"] else "FAIL"), ov["detail"]))
    if ov["ok"] is False:
        sys.exit(1)


def cmd_serve(a):
    r = _render()
    _need_recipe(a.dir)
    try:
        svg, info = r.render_svg(a.dir, a.style)
    except ValueError as e:
        die(str(e))
    srv = r.make_server(svg, os.path.basename(os.path.abspath(a.dir)), a.port)
    print("serving http://%s:%d/ (127.0.0.1 only; Ctrl+C stops)" % srv.server_address[:2], flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def cmd_sheet(a):
    import tempfile
    r = _render()
    g = _gen()
    _need_recipe(a.dir)
    items = []
    styles = [s.strip() for s in a.styles.split(",")] if a.styles else []
    try:
        seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else []
    except ValueError:
        die("--seeds wants a comma list of integers")
    if not styles and not seeds:
        styles = sorted(r.STYLES)
    tmp = tempfile.mkdtemp(prefix="mpw-sheet-")
    try:
        if seeds:
            with open(os.path.join(a.dir, "recipe.json"), encoding="utf-8") as f:
                rc = json.load(f)
            if rc["kind"] != "world":
                die("--seeds works on a world recipe")
            p = rc["params"]
            st = styles[0] if styles else r.DEFAULT_STYLE
            for sd in seeds:
                out = os.path.join(tmp, "s%d" % sd)
                g.gen_world(sd, p["cells"], out, p["plates"], p["erosion_steps"], p["lat_top"], p["lat_bottom"],
                            p["raster_px"], VERSION)
                items.append(("seed %d, %s" % (sd, st), r.render_svg(out, st)[0]))
        else:
            for st in styles:
                items.append((st, r.render_svg(a.dir, st)[0]))
        svg = r.sheet_svg(items, a.cols)
        r.write_out(svg, a.out)
    except (ValueError, RuntimeError, OSError) as e:
        die(str(e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("wrote %s: %d maps" % (a.out, len(items)))


# ---------------------------------------------------------------- main
def build_parser():
    p = argparse.ArgumentParser(prog="mpw.py", description="mapwright: read, write, measure and project maps")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("doctor", help="check Python, browser and optional extras")
    s.add_argument("--json", action="store_true")
    s.add_argument("--host", help="ComfyUI server to probe for aistyle (default: MAPWRIGHT_COMFYUI; unset = not probed)")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("explain", help="explain a cartography term (`explain list`)")
    s.add_argument("term")
    s.set_defaults(fn=cmd_explain)

    s = sub.add_parser("inspect", help="what a map file holds")
    s.add_argument("file")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("convert", help="convert between GeoJSON, GPX and KML (reads SHP, KMZ)")
    s.add_argument("input")
    s.add_argument("output")
    s.set_defaults(fn=cmd_convert)

    s = sub.add_parser("measure", help="geodesic distance, ellipsoid area, map scale")
    ms = s.add_subparsers(dest="what", required=True)
    d = ms.add_parser("distance", help="distance and bearing: LAT1 LON1 LAT2 LON2")
    for n in ("lat1", "lon1", "lat2", "lon2"):
        d.add_argument(n, type=float)
    ar = ms.add_parser("area", help="area of the polygons in a file")
    ar.add_argument("file")
    sc = ms.add_parser("scale", help="1:N conversions")
    sc.add_argument("scale", help="e.g. 1:50000")
    sc.add_argument("--map", help="length on the map, e.g. 2cm")
    sc.add_argument("--ground", help="length on the ground, e.g. 3km")
    for x in (d, ar, sc):
        x.add_argument("--ellipsoid", default="WGS84", choices=sorted(ELLIPSOIDS))
        x.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_measure)

    s = sub.add_parser("project", help="forward or inverse projection of one point")
    s.add_argument("name", nargs="?")
    s.add_argument("x", nargs="?", type=float, help="lon (forward) or x (inverse)")
    s.add_argument("y", nargs="?", type=float, help="lat (forward) or y (inverse)")
    s.add_argument("--inverse", action="store_true")
    s.add_argument("--radius", type=float, default=1.0)
    s.add_argument("--lon0", type=float, default=0.0)
    s.add_argument("--lat0", type=float, default=0.0)
    s.add_argument("--list", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_project)

    s = sub.add_parser("read", help="what a map picture shows: size, colour classes, text (OCR), georeference from GCPs")
    s.add_argument("image")
    s.add_argument("--gcp", action="append", help="px,py,lon,lat (pixel from top-left corner); 3 or more fit an affine")
    s.add_argument("--units", choices=["deg", "m"], default="deg", help="GCP map units: degrees or metres")
    s.add_argument("--world", action="store_true", help="write a world file beside the image from the GCP fit")
    s.add_argument("--prompt", action="store_true", help="print the checklist for an agent's own vision to fill in")
    s.add_argument("--answers", help="JSON answers from --prompt to check against the picture")
    s.set_defaults(fn=cmd_read)

    s = sub.add_parser("trace", help="map picture to GeoJSON polygons or centre lines by colour class or colour")
    s.add_argument("image")
    s.add_argument("--class", dest="cls", default="water",
                   choices=["water", "vegetation", "relief", "light", "ink", "grey", "other"])
    s.add_argument("--colour", help="#rrggbb to trace instead of a class")
    s.add_argument("--tol", type=float, default=40.0, help="RGB distance for --colour")
    s.add_argument("--mode", choices=["polygons", "lines"], default="polygons")
    s.add_argument("--epsilon", type=float, default=1.0, help="Douglas-Peucker tolerance, pixels")
    s.add_argument("--min-area", type=float, default=16.0, help="drop rings smaller than this, pixels")
    s.add_argument("--min-length", type=float, default=8.0, help="drop lines shorter than this, pixels")
    s.add_argument("--fill-holes", type=float, default=0.0,
                   help="fill holes smaller than this, pixels (label halos over the sea)")
    s.add_argument("--clean", type=int, default=1, help="3x3 majority filter passes before tracing")
    s.add_argument("--gcp", action="append", help="px,py,lon,lat; output georeferenced by an affine fit")
    s.add_argument("--units", choices=["deg", "m"], default="deg")
    s.add_argument("--world", help="world file to georeference with ('auto' looks beside the image)")
    s.add_argument("-o", "--out", help="write GeoJSON here (default stdout)")
    s.set_defaults(fn=cmd_trace)

    s = sub.add_parser("gen", help="generate a world or a child region as a recipe folder")
    gs = s.add_subparsers(dest="what", required=True)
    w = gs.add_parser("world", help="new world: plates, erosion, rivers, lakes, climate, biomes")
    w.add_argument("--seed", type=int, required=True)
    w.add_argument("--cells", type=int, default=16000)
    w.add_argument("--plates", type=int, default=12)
    w.add_argument("--erosion", type=int, default=15, help="stream-power steps (10-20)")
    w.add_argument("--lat-top", type=float, default=60.0)
    w.add_argument("--lat-bottom", type=float, default=0.0)
    w.add_argument("--out", required=True)
    w.add_argument("--style", help="name sound pattern (`names --list`); default: picked from the seed")
    w.add_argument("--pattern", help="custom sound pattern 'C=..;V=..;F=..;S=CV CVF;N=2-3'")
    rg = gs.add_parser("region", help="child map of a window of a parent world")
    rg.add_argument("--parent", required=True)
    for x in (rg,):
        x.add_argument("--window", help="x0,y0,x1,y1 in parent map km; default: the coast-richest quarter tile")
        x.add_argument("--chunk", help="COL,ROW: that chunk of the parent as the window, with its own per-place "
                       "seed so it regenerates alone (instead of --window)")
        x.add_argument("--chunk-km", type=float, default=250.0, help="with --chunk: chunk width in km (default 250)")
        x.add_argument("--cells", type=int, default=16000)
        x.add_argument("--detail", type=float, default=0.03, help="detail noise amplitude (height units)")
        x.add_argument("--out", required=True)
    for x in (w, rg):
        x.add_argument("--raster", type=int, default=512, help="heights.png width in pixels")
        x.add_argument("--json", action="store_true")
    c = gs.add_parser("city", help="seeded city: streets, blocks, lots, wall and gates, districts, names")
    c.add_argument("--seed", type=int, required=True)
    c.add_argument("--bands", type=int, default=6, help="rings of blocks around the market")
    c.add_argument("--wall", type=int, default=4, help="ring the wall stands on (1..bands-1)")
    c.add_argument("--no-walls", action="store_true")
    c.add_argument("--spokes", type=int, help="gate roads from the market (default 5-7 by seed)")
    c.add_argument("--ring-m", type=float, default=55.0, help="metres between rings")
    c.add_argument("--lot-m2", type=float, default=300.0, help="target lot area inside the wall")
    c.add_argument("--parent", help="world recipe folder: the city takes a settlement's name, coast and river")
    c.add_argument("--settlement", type=int, help="settlement id in the parent (default: the top-scored one)")
    c.add_argument("--sea", type=float, help="direction of the sea in radians (0 east, pi/2 south)")
    c.add_argument("--river", type=float, help="direction a river runs through the city, radians")
    d = gs.add_parser("dungeon", help="seeded dungeon on a square grid: BSP rooms, cellular caves or a cyclic "
                                      "lock-and-key graph; doors, lights, entrance and goal")
    d.add_argument("--seed", type=int, required=True)
    d.add_argument("--method", choices=("bsp", "cave", "cyclic", "blocks"), default="bsp")
    d.add_argument("--fill", type=float, help="cave: share of squares that start as wall (default 0.45)")
    d.add_argument("--passes", type=int, help="cave: smoothing passes (default 5)")
    d.add_argument("--birth", type=int, help="cave: floor turns to wall at this many wall neighbours (default 5)")
    d.add_argument("--survival", type=int, help="cave: wall stays wall at this many wall neighbours (default 4)")
    d.add_argument("--radius", type=int, choices=(1, 2), help="cave: neighbourhood radius, 1 = 8 cells, 2 = 24")
    d.add_argument("--border", type=int, help="cave: solid border in squares (default 1)")
    d.add_argument("--branches", type=int, help="cyclic: dead-end side branches, 0 to 8 (treasure, secret doors; "
                                                "never a key). Default none")
    d.add_argument("--w", type=int, default=48, help="width in squares")
    d.add_argument("--h", type=int, default=36, help="height in squares")
    d.add_argument("--pps", type=int, default=70, help="pixels per square (whole number)")
    b = gs.add_parser("battle", help="gridded battle map (square or hex): ruins, rocks, trees, torches")
    b.add_argument("--seed", type=int, required=True)
    b.add_argument("--grid", choices=("square", "hex"), default="square")
    b.add_argument("--w", type=int, default=30, help="width in squares or hexes")
    b.add_argument("--h", type=int, default=20, help="height in squares or hex rows")
    b.add_argument("--pps", type=int, default=100, help="pixels per square (hex: hex width, even)")
    b.add_argument("--density", choices=("sparse", "normal", "dense"), default="normal",
                   help="share of squares holding a feature: sparse = the pre-0.11 map (about 0.13 square, 0.07 hex), "
                        "normal 0.22, dense 0.32")
    sc = gs.add_parser("sector", help="hex subsector or sector: worlds, T5 tab file, connected routes; --real for near stars")
    sc.add_argument("--seed", type=int, default=1)
    sc.add_argument("--size", choices=("subsector", "sector"), default="subsector", help="8x10 or 32x40 hexes")
    sc.add_argument("--density", type=float, default=0.5, help="share of hexes with a world")
    sc.add_argument("--jump", type=float, default=2, help="jump range: hexes, or parsecs with --real")
    sc.add_argument("--real", action="store_true", help="bundled near stars (scripts/data/near-stars.csv) by parallax")
    sc.add_argument("--radius-pc", type=float, default=6.0, help="with --real: stars within this distance")
    sc.add_argument("--systems", action="store_true", help="also write systems/<hex>/ per world from per-place seeds")
    sy = gs.add_parser("system", help="star, planets on stable orbits, moons; schematic and to-scale diagrams")
    sy.add_argument("--seed", type=int, help="system seed; or use --sector-seed with --hex")
    sy.add_argument("--sector-seed", type=int, help="with --hex: the system at that hex of this sector's seed")
    sy.add_argument("--hex", help="with --sector-seed: four-digit hex such as 0118")
    sy.add_argument("--star", choices=("M", "K", "G", "F"))
    sy.add_argument("--planets", type=int)
    pl = gs.add_parser("planet", help="equirectangular sphere texture with no seam or pole pinch")
    pl.add_argument("--seed", type=int, required=True)
    pl.add_argument("--kind", choices=("rocky", "ice", "ocean", "gas", "moon", "locked"), default="rocky")
    pl.add_argument("--width", type=int, default=1024, help="texture width (even, 512+); height is half")
    dk = gs.add_parser("deck", help="ship or station deck plan: rooms, doors, airlock, lifts, all reachable")
    dk.add_argument("--seed", type=int, required=True)
    dk.add_argument("--hull", choices=("ship", "station"), default="ship")
    dk.add_argument("--w", type=int, default=40, help="length in 1.5 m squares")
    dk.add_argument("--h", type=int, default=21, help="beam in 1.5 m squares")
    dk.add_argument("--decks", type=int, default=2)
    dk.add_argument("--pps", type=int, default=16, help="pixels per square in map.svg")
    for x in (sc, sy, pl, dk):
        x.add_argument("--out", required=True)
        x.add_argument("--json", action="store_true")
    for x in (sc, sy, dk):
        x.add_argument("--name-style", help="name sound pattern (`names --list`)")
    for x in (c, d, b):
        x.add_argument("--out", required=True)
        x.add_argument("--style", choices=("ink-and-parchment", "blueprint"))
        x.add_argument("--name-style", help="name sound pattern (`names --list`)")
        x.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_gen)

    s = sub.add_parser("export", help="recipe to game, tabletop, 3D and print files: engine heightmaps, Tiled maps, "
                                      "Universal VTT, a terrain mesh, a sphere PNG, a T5 file, PDF and PNG at a paper size")
    s.add_argument("dir")
    s.add_argument("-o", "--out", required=True, help="output file; the extension picks the target when --to is absent "
                                                      "(.dd2vtt .tmj .raw .r16 .obj .pdf .tab, .png for a planet or hex map)")
    s.add_argument("--to", choices=("uvtt", "png", "sphere", "t5", "unity", "unreal", "godot", "roblox", "tiled",
                                    "mesh", "print", "nav"))
    s.add_argument("--nav", action="store_true", help="same as --to nav: walkable squares merged into rectangles "
                                                      "with portals, JSON for a game engine (dungeon, square battle)")
    s.add_argument("--agent", type=int, help="nav: body width in squares (default 1); walkable squares are eroded "
                                             "so each rect square is a top-left anchor where the whole body fits")
    s.add_argument("--size", type=int, help="heightmap or mesh samples on a side (unity 2^n+1, unreal 1009 and kin)")
    s.add_argument("--flip", action="store_true", help="unity: write the south row first")
    s.add_argument("--bits", type=int, choices=(8, 16), help="roblox heightmap depth (default 8)")
    s.add_argument("--tile", type=int, help="tiled: tile size in px (default 32)")
    s.add_argument("--encoding", choices=("csv", "base64"), help="tiled: layer data as numbers or base64 + zlib")
    s.add_argument("--csv", action="store_true", help="tiled: also write each tile layer as a .csv")
    s.add_argument("--deck", type=int, help="uvtt: one deck of a deck plan (default every deck)")
    s.add_argument("--pps", type=int, help="uvtt for a deck: pixels per square (default 50 or the recipe's if larger)")
    s.add_argument("--exaggeration", type=float, help="mesh: vertical exaggeration (default 1)")
    s.add_argument("--base", type=float, help="mesh: close it with a base this thick under the lowest point")
    s.add_argument("--print-mm", type=float, help="mesh: a print tile this many mm on its longer side (base 2 mm)")
    s.add_argument("--flat-sea", action="store_true", help="mesh: flatten everything below sea level")
    s.add_argument("--paper", help="print: A0..A5, Letter, Legal, Tabloid or WxH in mm (default A4)")
    s.add_argument("--landscape", action="store_true")
    s.add_argument("--dpi", type=int, help="print: PNG resolution (default 300)")
    s.add_argument("--bleed", type=float, help="print: bleed in mm on every edge, with crop marks")
    s.add_argument("--no-marks", action="store_true", help="print: no crop marks")
    s.add_argument("--margin", type=float, help="print: margin in mm inside the trim (default 10)")
    s.add_argument("--fit", choices=("contain", "cover"), help="print: whole map inside the margin, or map over the bleed")
    s.add_argument("--style", help="print and png: the look to draw")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("zoom", help="same as `gen region --parent DIR`")
    s.add_argument("dir")
    s.add_argument("--window")
    s.add_argument("--cells", type=int, default=16000)
    s.add_argument("--detail", type=float, default=0.03)
    s.add_argument("--raster", type=int, default=512)
    s.add_argument("--out", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_zoom)

    s = sub.add_parser("check", help="run the proof bars on a recipe folder (world, region, city, dungeon, battle, sector, system, planet, deck)")
    s.add_argument("dir", nargs="?", help="recipe folder (with --range: where range.json and range.svg go)")
    s.add_argument("--range", choices=("bsp", "cave", "cyclic", "blocks"), help="expressive range of gen dungeon --method over many seeds")
    s.add_argument("--seeds", type=int, default=500, help="--range: number of seeds (default 500)")
    s.add_argument("--w", type=int, default=48, help="--range: width in squares")
    s.add_argument("--h", type=int, default=36, help="--range: height in squares")
    s.add_argument("--no-regen", action="store_true", help="skip the byte-identical regeneration bar")
    s.add_argument("--no-labels", action="store_true", help="skip the label bars (overlap, edge, OCR)")
    s.add_argument("--style", default="topographic", help="style the label bars render with")
    s.add_argument("--no-aistyle", action="store_true", help="skip the bars on styled pictures (*.aistyle.json) in the folder")
    s.add_argument("--period", type=int, help="period lint: fail every convention on the map younger than YEAR "
                   "(first-use tables, book dates; a style may carry a 'period' year)")
    s.add_argument("--period-kind", choices=("map", "chart", "mappa"), default="map",
                   help="--period: land map, sea chart or mappa mundi (their rules differ)")
    s.add_argument("--uses", help="--period: more conventions the map carries, comma separated (e.g. "
                   "mercator,land-contours,dot-map,greenwich)")
    s.add_argument("--chokepoints", action="store_true", help="grid recipes: cells whose loss cuts the map, what each "
                   "cuts off, the minimum cut entrance to goal; writes chokepoints.json")
    s.add_argument("--fair", action="store_true", help="grid recipes: per-start distances to resources and "
                   "first-reach areas; writes fair.json")
    s.add_argument("--starts", help="--fair: starts as X,Y;X,Y (default: entrance and the cell farthest from it)")
    s.add_argument("--resources", help="--fair: resources as X,Y;X,Y (default: lights, else room centres)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("path", help="cheapest route (A*) or a Dijkstra field on a dungeon, battle, deck, world or "
                       "region recipe; writes path.json, path.geojson and path.svg (or field.json and field.svg)")
    s.add_argument("dir")
    s.add_argument("--from", dest="src", help="start: X,Y squares or hexes, DECK,X,Y on decks, map km on worlds")
    s.add_argument("--to", action="append", help="goal (repeat for several goals with --field)")
    s.add_argument("--field", action="store_true", help="cost to the nearest goal from every cell, with a flow step")
    s.add_argument("--moves", type=int, choices=(4, 8), default=8, help="square grids: 4- or 8-way moves")
    s.add_argument("--ignore-locks", action="store_true",
                   help="cyclic dungeons: treat every locked door as open (default: fetch each key before its lock)")
    s.add_argument("--jps", action="store_true", help="jump point search on 8-way square grids (same cost as A*)")
    s.add_argument("--agent", type=int, default=1, help="square grids: body width in squares (default 1); "
                   "--from and --to name the body's top-left square, which must have room for the whole body")
    s.add_argument("--out", help="folder for the output files (default: the recipe folder)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_path)

    s = sub.add_parser("travel", help="travel-time map on a world or region with Tobler's hiking function; "
                       "writes travel.json and travel.svg")
    s.add_argument("dir")
    s.add_argument("--from", dest="src", required=True, help="start in map km X,Y")
    s.add_argument("--to", help="also report the fastest route to X,Y")
    s.add_argument("--mode", choices=("walk", "offpath", "horse"), default="walk")
    s.add_argument("--band", type=float, default=6.0, help="isochrone band width in hours (default 6)")
    s.add_argument("--out", help="folder for the output files (default: the recipe folder)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_travel)

    s = sub.add_parser("find", help="maps and data for a place, time or subject, each with licence and credit")
    s.add_argument("query", nargs="*")
    s.add_argument("--online", action="store_true", help="also ask Nominatim, Wikimedia Commons and the Library of Congress")
    s.add_argument("--list", action="store_true", help="print the source catalogue")
    s.add_argument("--limit", type=int, default=8)
    s.add_argument("--cache", help="cache folder (default MAPWRIGHT_CACHE or ~/.cache/mapwright)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("fetch", help="download one file politely and cached; writes sources.json and CREDITS.txt")
    s.add_argument("url")
    s.add_argument("-o", "--out", required=True, help="folder the file, sources.json and CREDITS.txt go in")
    s.add_argument("--source", help="catalogue id when the host alone does not say")
    s.add_argument("--name", help="file name to save as")
    s.add_argument("--licence", help="licence, required for a host not in the catalogue")
    s.add_argument("--credit", help="credit line, required for a host not in the catalogue")
    s.add_argument("--max-mb", type=float, default=200, help="size cap; bigger downloads are refused")
    s.add_argument("--cache", help="cache folder (default MAPWRIGHT_CACHE or ~/.cache/mapwright)")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("names", help="place names from a sound pattern: sample, list styles, or rename a world")
    s.add_argument("dir", nargs="?", help="world recipe folder: print its names, or rename with --style/--pattern")
    s.add_argument("--sample", type=int, default=12, help="how many names to print without a folder")
    s.add_argument("--style", help="built-in style (see --list)")
    s.add_argument("--pattern", help="custom 'C=p t k;V=a i u;F=n;S=CV CVF;N=2-3'")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--list", action="store_true", help="list the built-in styles")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_names)

    s = sub.add_parser("render", help="recipe folder to a print map (.svg, or .png/.pdf via headless Chrome or Edge)")
    s.add_argument("dir")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--title")
    s.add_argument("--view", choices=("schematic", "scale"), help="system recipes: schematic (default) or to scale")
    s.set_defaults(fn=cmd_render)
    rn = s

    s = sub.add_parser("label", help="place labels with collision avoidance and run the label bars")
    s.add_argument("dir")
    s.set_defaults(fn=cmd_label)
    lb = s

    s = sub.add_parser("legend", help="the legend entries for the symbols on this map")
    s.add_argument("dir")
    s.add_argument("-o", "--out", help="write the legend alone (.svg/.png/.pdf)")
    s.set_defaults(fn=cmd_legend)
    lg = s
    for x in (rn, lb, lg):
        x.add_argument("--style", default="topographic", help="named look (`style --list`)")
        x.add_argument("--json", action="store_true")
    for x in (rn, lb):
        x.add_argument("--font", help="TTF whose hmtx widths measure the labels (default: shipped wide table)")

    s = sub.add_parser("style", help="list the named looks or show one")
    s.add_argument("name", nargs="?")
    s.add_argument("--list", action="store_true")
    s.set_defaults(fn=cmd_style)

    s = sub.add_parser("serve", help="pan/zoom page of the rendered map on 127.0.0.1 only")
    s.add_argument("dir")
    s.add_argument("--style", default="topographic")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("sheet", help="several styles or seeds side by side in one SVG/PNG/PDF")
    s.add_argument("dir")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--styles", help="comma list (default: all styles)")
    s.add_argument("--seeds", help="comma list of seeds: regenerate the world per seed (first --styles entry)")
    s.add_argument("--cols", type=int)
    s.set_defaults(fn=cmd_sheet)

    s = sub.add_parser("aistyle", help="optional AI style pass on a ComfyUI server: the unlabelled render is the "
                                       "init image, labels and furniture are set in code after, the coast is measured")
    s.add_argument("dir", nargs="?", help="world or region recipe folder")
    s.add_argument("--look", help="named look (`aistyle --list`)")
    s.add_argument("--list", action="store_true", help="list the looks")
    s.add_argument("--denoise", type=float, help="how far the model may repaint, 0-1 (default 0.45, the "
                                                 "measured ceiling: above it the coast drifts)")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--host", help="ComfyUI server URL (default: the MAPWRIGHT_COMFYUI environment variable)")
    s.add_argument("-o", "--out", help=".png, .svg or .pdf (default: RECIPE/aistyle-LOOK.png); the control "
                                       "picture, workflow, raw styled picture and sidecar go beside it")
    s.add_argument("--dry-run", action="store_true", help="write the control PNG and the workflow JSON; contact no server")
    s.add_argument("--measure", metavar="PNG", help="only measure an unlabelled picture of this map against the recipe")
    s.add_argument("--workflow", help="workflow template JSON (default: scripts/data/aistyle-zimage-turbo.json)")
    s.add_argument("--model", help="diffusion model file name on the server (overrides the template)")
    s.add_argument("--clip", help="text encoder file name on the server")
    s.add_argument("--vae", help="VAE file name on the server")
    s.add_argument("--size", type=int, help="long side sent to the model, px (default: the template's, 1024)")
    s.add_argument("--style", help="code style under the look (default: the look's own)")
    s.add_argument("--font", help="TTF whose hmtx widths measure the labels")
    s.add_argument("--title")
    s.add_argument("--timeout", type=float, default=900, help="seconds to wait for the server")
    s.add_argument("--no-measure", action="store_true", help="skip the overlap measurement")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_aistyle)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.cmd == "project" and not a.list and (a.name is None or a.x is None or a.y is None):
        die("project NAME X Y [--inverse]; --list shows names")
    a.fn(a)


if __name__ == "__main__":
    main()
