#!/usr/bin/env python3
"""mapwright exports: engine heightmaps (Unity RAW, Unreal and Godot 16-bit, Roblox with a colormap), Tiled maps
(.tmj), deck plans to Universal VTT, hex battle maps to PNG, a terrain mesh (OBJ) with a polywright manifest, and
print-ready PDF and PNG at a paper size. Standard library only. Every writer reads its own file back and returns
proof bars as (name, ok, detail); mpw.py prints them and exits non-zero when one fails."""
import base64
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from html import escape as html_escape

import mpw_gen as G
import mpw_places as P

TARGETS = ("uvtt", "png", "sphere", "t5", "unity", "unreal", "godot", "roblox", "tiled", "mesh", "print")
LAND = ("world", "region")
GRIDS = ("dungeon", "battle", "deck")
EXT_TARGET = {".dd2vtt": "uvtt", ".uvtt": "uvtt", ".tmj": "tiled", ".raw": "unity", ".r16": "godot", ".obj": "mesh",
              ".pdf": "print", ".tab": "t5", ".tsv": "t5", ".txt": "t5"}


def _dump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1)
        f.write("\n")


def _r(v, n=6):
    return round(float(v), n)


def _stem(out):
    return os.path.splitext(out)[0]


# ------------------------------------------------------------------ PNG read back
def read_png_grey(data):
    """Non-interlaced greyscale PNG, 8 or 16 bit, to (w, h, depth, rows of ints). All five filters."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, hdr = 8, [], None
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", data[pos + 8:pos + 8 + ln])
        elif typ == b"IDAT":
            idat.append(data[pos + 8:pos + 8 + ln])
        pos += 12 + ln
    w, h, depth, ctype, _, _, inter = hdr
    if ctype != 0 or inter or depth not in (8, 16):
        raise ValueError("only 8 or 16 bit greyscale non-interlaced PNGs")
    bpp = depth // 8
    stride = w * bpp
    raw = zlib.decompress(b"".join(idat))
    fmt = ">%d%s" % (w, "H" if bpp == 2 else "B")
    prev = bytearray(stride)
    rows = []
    for y in range(h):
        k = y * (stride + 1)
        ft = raw[k]
        line = bytearray(raw[k + 1:k + 1 + stride])
        if ft:
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
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(list(struct.unpack(fmt, bytes(line))))
        prev = line
    return w, h, depth, rows


# ------------------------------------------------------------------ recipe heights
def load_heights(d):
    """Recipe heights in metres (rows north first) and the ground size in metres."""
    rc = G.load(d, "recipe.json")
    if rc.get("kind") not in LAND:
        raise ValueError("heightmap and mesh exports need a world or region recipe, not %s" % rc.get("kind"))
    with open(os.path.join(d, "heights.png"), "rb") as f:
        w, h, depth, rows = read_png_grey(f.read())
    if depth != 16:
        raise ValueError("heights.png is not 16 bit")
    x0, y0, x1, y1 = rc["extent"]
    return rc, [[v - G.PNG_OFFSET for v in r] for r in rows], ((x1 - x0) * 1000.0, (y1 - y0) * 1000.0)


RESAMPLE = {
    "vertex": "bilinear between source pixel centres; output sample i sits at i/(N-1) of the extent, so the first "
              "and last samples lie on the map edges; clamped to the outer pixel centres",
    "pixel": "bilinear between source pixel centres; output pixel i covers (i..i+1)/N of the extent and is sampled "
             "at its centre; clamped to the outer pixel centres; the identity when the size equals the recipe raster",
}


def _axis(n, sn, mode):
    out = []
    for i in range(n):
        t = (i / (n - 1.0)) if mode == "vertex" else (i + 0.5) / n
        u = min(max(t * sn - 0.5, 0.0), sn - 1.0)
        i0 = min(int(u), sn - 2) if sn > 1 else 0
        out.append((i0, u - i0))
    return out


def resample(rows, nw, nh, mode):
    """Bilinear resample of a pixel-centred raster (see RESAMPLE for the two sample layouts)."""
    sh, sw = len(rows), len(rows[0])
    if mode == "pixel" and (nw, nh) == (sw, sh):
        return [[float(v) for v in r] for r in rows]
    if nw < 2 or nh < 2 or sw < 2 or sh < 2:
        raise ValueError("resample needs at least 2 samples per side")
    xs, ys = _axis(nw, sw, mode), _axis(nh, sh, mode)
    out = []
    for j0, fy in ys:
        r0, r1 = rows[j0], rows[j0 + 1]
        gy = 1.0 - fy
        out.append([(r0[i] * (1.0 - fx) + r0[i + 1] * fx) * gy + (r1[i] * (1.0 - fx) + r1[i + 1] * fx) * fy
                    for i, fx in xs])
    return out


def quantise(rows, maxv):
    """Stretch min..max over 0..maxv. Returns (int rows, min, max, metres per step)."""
    lo = min(min(r) for r in rows)
    hi = max(max(r) for r in rows)
    if hi <= lo:
        return [[0] * len(r) for r in rows], lo, hi, 0.0
    k = maxv / (hi - lo)
    return [[int((v - lo) * k + 0.5) for v in r] for r in rows], lo, hi, (hi - lo) / maxv


# ------------------------------------------------------------------ engine heightmaps
UNITY_SIZES = (33, 65, 129, 257, 513, 1025, 2049, 4097)
UNREAL_SIZES = (127, 253, 505, 1009, 2017, 4033, 8129)
ROBLOX_MAX = 4096
STUD_M = 0.28   # community convention for a 5 stud character, not an official unit
# Roblox Terrain Editor colormap colours (references/games-film-print.md section 2.4)
ROBLOX_MATERIALS = {
    "Asphalt": (115, 123, 107), "Basalt": (30, 30, 37), "Brick": (138, 86, 62), "Cobblestone": (132, 123, 90),
    "Concrete": (127, 102, 63), "CrackedLava": (232, 156, 74), "Glacier": (101, 176, 234), "Grass": (106, 127, 63),
    "Ground": (102, 92, 59), "Ice": (129, 194, 224), "LeafyGrass": (115, 132, 74), "Limestone": (206, 173, 148),
    "Mud": (58, 46, 36), "Pavement": (148, 148, 140), "Rock": (102, 108, 111), "Salt": (198, 189, 181),
    "Sand": (143, 126, 95), "Sandstone": (137, 90, 71), "Slate": (63, 127, 107), "Snow": (195, 199, 218),
    "WoodPlanks": (139, 109, 79),
}
BIOME_MATERIAL = {
    "ocean": "Mud", "lake": "Mud", "ice": "Snow", "tundra": "Ground", "boreal forest": "LeafyGrass",
    "temperate grassland": "Grass", "cold desert": "Sandstone", "temperate seasonal forest": "LeafyGrass",
    "temperate rainforest": "LeafyGrass", "subtropical desert": "Sand", "savanna": "Grass",
    "tropical seasonal forest": "LeafyGrass", "tropical rainforest": "LeafyGrass", "alpine": "Rock",
}


def _pick_size(sizes, want, given, what):
    if given:
        if given not in sizes:
            raise ValueError("%s takes sizes %s, not %d" % (what, ", ".join(str(s) for s in sizes), given))
        return given
    for s in sizes:
        if s >= want:
            return s
    return sizes[-1]


def biome_rows(d, rc):
    """Biome id per pixel at the recipe's raster size (same rule as heights.png)."""
    m = G.load(d, "mesh.json")
    x0, y0, x1, y1 = rc["extent"]
    M = dict(X=m["x"], Y=m["y"], tris=G._tris(m))
    _, B, _ = G.raster(M, m["h"], m["biome"], x0, y0, x1, y1, int(rc["params"].get("raster_px", 512)))
    return B


def roblox_colormap(B, w, h):
    """Nearest-neighbour biome raster at w x h as RGB rows of Roblox material colours."""
    sh, sw = len(B), len(B[0])
    pal = [bytes(ROBLOX_MATERIALS[BIOME_MATERIAL[b[0]]]) for b in G.BIOMES]
    cols = [min(sw - 1, int((i + 0.5) * sw / w)) for i in range(w)]
    rows = []
    for j in range(h):
        br = B[min(sh - 1, int((j + 0.5) * sh / h))]
        rows.append(b"".join(pal[br[c]] for c in cols))
    return rows


def _fit(limits, sizes):
    k = max([1.0] + [s / lim for s, lim in zip(sizes, limits)])
    return int(math.ceil(k - 1e-9))


def read_heightmap(path, w=None, h=None):
    """Read an exported heightmap back to integer rows: .raw/.r16 (16-bit little-endian, needs w and h) or a PNG."""
    with open(path, "rb") as f:
        data = f.read()
    if path.lower().endswith(".png"):
        return read_png_grey(data)[3]
    if len(data) != w * h * 2:
        raise ValueError("%s holds %d bytes, not %d x %d x 2" % (path, len(data), w, h))
    return [list(struct.unpack("<%dH" % w, data[j * w * 2:(j + 1) * w * 2])) for j in range(h)]


def export_heightmap(d, out, target, version, size=None, flip=False, bits=None):
    rc, metres, (gw, gl) = load_heights(d)
    sh, sw = len(metres), len(metres[0])
    ext = os.path.splitext(out)[1].lower()
    raw = ext in (".raw", ".r16")
    if target == "unity":
        if not raw:
            raise ValueError("Unity imports a 16-bit RAW: name the output .raw")
        nw = nh = _pick_size(UNITY_SIZES, max(sw, sh), size, "Unity (2^n + 1)")
        mode, depth = "vertex", 16
    elif target == "unreal":
        if ext != ".png":
            raise ValueError("Unreal imports a 16-bit greyscale PNG: name the output .png")
        nw = nh = _pick_size(UNREAL_SIZES, max(sw, sh), size, "Unreal (recommended landscape sizes)")
        mode, depth = "vertex", 16
    elif target == "godot":
        if not raw and ext != ".png":
            raise ValueError("Godot output is .r16 (Terrain3D) or a 16-bit .png")
        nw = size or sw
        nh = max(2, int(round(nw * sh / float(sw))))
        mode, depth = "pixel", 16
    elif target == "roblox":
        if ext != ".png":
            raise ValueError("Roblox imports a .png heightmap")
        nw = size or sw
        nh = max(2, int(round(nw * sh / float(sw))))
        if max(nw, nh) > ROBLOX_MAX:
            raise ValueError("Roblox heightmaps are at most %d px a side" % ROBLOX_MAX)
        mode, depth = "pixel", int(bits or 8)
        if depth not in (8, 16):
            raise ValueError("--bits is 8 or 16")
    else:
        raise ValueError("unknown heightmap target %r" % target)
    if nw < 2 or nw > 8129:
        raise ValueError("--size out of range")
    maxv = (1 << depth) - 1
    res = resample(metres, nw, nh, mode)
    q, lo, hi, step = quantise(res, maxv)
    south_first = bool(flip and target == "unity")
    wrows = q[::-1] if south_first else q
    with open(out, "wb") as f:
        if raw:
            f.write(b"".join(struct.pack("<%dH" % nw, *r) for r in wrows))
        else:
            f.write(G.png_bytes(nw, nh, wrows, depth, 0))
    files = [out]
    div = (nw - 1, nh - 1) if mode == "vertex" else (nw, nh)
    mpp = (gw / div[0], gl / div[1])
    rng = hi - lo
    side = dict(mapwright=version, target=target, file=os.path.basename(out),
                source=dict(recipe=os.path.basename(os.path.abspath(d)), kind=rc["kind"], seed=rc["seed"],
                            raster=[sw, sh], heights="heights.png, 16 bit, 1 m steps"),
                size=[nw, nh], bits=depth, format="RAW, little-endian, no header" if raw else "PNG greyscale",
                row_order="south first" if south_first else "north first",
                resample=RESAMPLE[mode], metres_per_pixel=[_r(mpp[0], 4), _r(mpp[1], 4)],
                ground_m=[_r(gw, 2), _r(gl, 2)], min_m=_r(lo, 6), max_m=_r(hi, 6), metres_per_step=_r(step, 12),
                height_m="min_m + value * metres_per_step",
                sea_level_value=int(round(-lo / step)) if step and lo <= 0 <= hi else None)
    if target == "unity":
        k = _fit((100000.0, 100000.0, 10000.0), (gw, gl, rng))
        imp = dict(menu="Terrain Settings > Texture Resolutions > Import Raw", depth="Bit 16", resolution=nw,
                   byte_order="Windows", flip_vertically=False,
                   terrain_size_m=dict(x=_r(gw, 2), y=_r(rng, 3), z=_r(gl, 2)), position_y_m=_r(lo, 3),
                   limits="width and length 1 to 100000 m, height 1 to 10000 m",
                   note="Value 0 is min_m and 65535 is max_m. Rows are written %s; if north and south come out "
                        "swapped, tick Flip Vertically or export with --flip (which way Unity reads rows is not "
                        "verified here)." % side["row_order"])
        if k > 1:
            imp["fit"] = dict(scale="1:%d" % k, terrain_size_m=dict(x=_r(gw / k, 2), y=_r(rng / k, 3), z=_r(gl / k, 2)),
                              position_y_m=_r(lo / k, 3),
                              note="the true size is past Unity's limits; this is the whole map shrunk evenly")
    elif target == "unreal":
        zs = rng * 12800.0 / 65535.0
        imp = dict(menu="Landscape Mode > Manage > Import from File", heightmap_size=nw,
                   scale=dict(x=_r(mpp[0] * 100.0, 3), y=_r(mpp[1] * 100.0, 3), z=_r(zs, 6)),
                   location_z_cm=_r((lo + rng * 32768.0 / 65535.0) * 100.0, 2),
                   note="Unreal reads value 32768 as zero height and 1/128 cm per step at Z scale 1. The file "
                        "stretches min_m..max_m over 0..65535, so Z scale = range_m x 12800 / 65535 and the Z "
                        "location puts value 0 at min_m. X and Y scale are cm per pixel.")
    elif target == "godot":
        imp = dict(terrain3d=dict(height_file=os.path.basename(out), r16_size=[nw, nh], r16_range=[_r(lo, 3), _r(hi, 3)],
                                  vertex_spacing_m=_r(mpp[0], 4),
                                  note="Terrain3D reads .r16 or .raw as 16-bit little-endian and PNG as 8 bit only "
                                       "(references/games-film-print.md 2.3), so prefer the .r16. Field names are "
                                       "from its importer scene and may differ in your release."),
                   heightmap_shader=dict(height_m="min_m + texel * (max_m - min_m)",
                                         note="a 16-bit PNG may be loaded as 8 bit by an engine's image importer; "
                                              "check the imported format before trusting it"))
    else:
        gscale = (gw / (nw * 4.0)) / STUD_M
        imp = dict(menu="Terrain Editor > Import", heightmap=os.path.basename(out),
                   colormap=os.path.basename(_stem(out) + ".colormap.png"),
                   size_studs=dict(x=nw * 4, z=nh * 4, y_true_scale=_r(rng / STUD_M / gscale, 2)),
                   ground_scale="1:%d" % max(1, int(round(gscale))),
                   sea_level_fraction_of_y=_r(-lo / rng, 5) if rng and lo <= 0 <= hi else None,
                   materials={b[0]: BIOME_MATERIAL[b[0]] for b in G.BIOMES},
                   material_colours={k: list(v) for k, v in sorted(ROBLOX_MATERIALS.items())},
                   note="One pixel is one 4 stud voxel column. y_true_scale is the relief in studs at the ground "
                        "scale (0.28 m per stud, a community convention); raise Y for relief you can see. Sea and "
                        "lake beds are Mud: fill water to sea_level_fraction_of_y x Y with the Sea Level tool. "
                        "The colour table and the 8-bit default (--bits 16 for a 16-bit PNG) are not verified "
                        "against the current Roblox docs.")
        cm = _stem(out) + ".colormap.png"
        crow = roblox_colormap(biome_rows(d, rc), nw, nh)
        with open(cm, "wb") as f:
            f.write(G.png_bytes(nw, nh, crow, 8, 2))
        files.append(cm)
    side["import"] = imp
    sj = _stem(out) + ".import.json"
    _dump(sj, side)
    files.append(sj)
    # read back
    back = read_heightmap(out, nw, nh)
    if south_first:
        back = back[::-1]
    worst = 0.0
    for br, rr in zip(back, res):
        for v, m in zip(br, rr):
            e = abs(lo + v * step - m)
            if e > worst:
                worst = e
    okshape = len(back) == nh and all(len(r) == nw for r in back)
    bars = [("%s heightmap: size the engine accepts" % target, okshape, "%d x %d, %d bit%s"
             % (nw, nh, depth, ", %d bytes" % os.path.getsize(out) if raw else "")),
            ("%s heightmap: reads back within one step" % target, okshape and worst <= step * 0.5 + 1e-9,
             "worst %.5f m, step %.5f m, range %.1f to %.1f m" % (worst, step, lo, hi))]
    if target == "roblox":
        pal = set(bytes(v) for v in ROBLOX_MATERIALS.values())
        used = set(r[i:i + 3] for r in crow for i in range(0, len(r), 3))
        with open(cm, "rb") as f:
            csz = tuple(P.png_size(f.read(32)))
        bars.append(("roblox colormap: every colour is a material, same size", used <= pal and csz == (nw, nh),
                     "%d materials used, %d x %d" % (len(used), csz[0], csz[1])))
    return bars, files


# ------------------------------------------------------------------ grids: dungeon, battle, deck
TILE_SYMS = "#.+TLA"            # gid = index + 1; a space (outside a hull) is gid 0, empty
TILE_NAMES = ("wall", "floor", "door", "tree", "lift", "airlock")
FLIP_MASK = 0x0FFFFFFF


def grid_layers(d):
    """Grid recipes as layers: (recipe, kind, w, h, [(layer name, rows of symbols)], extra)."""
    rc = P.load(d, "recipe.json")
    kind = rc.get("kind")
    if kind in ("dungeon", "battle"):
        gj = P.load(d, "grid.json")
        return rc, kind, gj["w"], gj["h"], [("ground", gj["cells"])], gj
    if kind == "deck":
        dj = P.load(d, "deck.json")
        return rc, kind, dj["w"], dj["h"], [("deck %d" % (i + 1), rows) for i, rows in enumerate(dj["decks"])], dj
    raise ValueError("this export is for dungeon, battle and deck recipes, not %s" % kind)


def deck_solid(rows):
    """A deck as a places grid: space counts as wall, lift is floor, the airlock's outer door is a door."""
    tr = {" ": P.WALLC, "#": P.WALLC, ".": P.FLOOR, "+": P.DOOR, "L": P.FLOOR, "A": P.DOOR}
    return [[tr[c] for c in row] for row in rows]


def grid_walls(kind, rows, w, h, extra):
    """Wall segments and door portals in grid units for one layer."""
    if kind == "deck":
        g = deck_solid(rows)
        return [[list(a), list(b)] for a, b in P.wall_segments(g, w, h, True)], P.door_portals(g, w, h)
    return extra["walls"], extra["portals"]


def tile_colours(kind):
    if kind == "deck":
        import mpw_space as S
        st = S.DST
        return [st["wall"], st["floor"], st["door"], "#3f7f4a", "#7fe0a0", "#ff8a6a"]
    _, st = P.pstyle(None, kind)
    return [st["rock"], st["floor"], st["door"], st["tree"], "#7fe0a0", "#ff8a6a"]


def tileset_png(colours, tile):
    """One row of flat colour tiles with a one pixel darker edge on the top and left."""
    rows = []
    for y in range(tile):
        line = bytearray()
        for c in colours:
            rgb = G.hex_rgb(c)
            dark = bytes(int(v * 0.8) for v in rgb)
            line += dark * tile if y == 0 else dark + bytes(rgb) * (tile - 1)
        rows.append(bytes(line))
    return G.png_bytes(tile * len(colours), tile, rows, 8, 2)


def export_tiled(d, out, version, tile=32, encoding="csv", csv=False):
    rc, kind, w, h, layers, extra = grid_layers(d)
    if kind == "battle" and extra["grid"] != "square":
        raise ValueError("the Tiled export covers square grids; a hex battle map exports with --to png")
    if not out.lower().endswith((".tmj", ".json")):
        raise ValueError("a Tiled map is a .tmj file")
    if encoding not in ("csv", "base64"):
        raise ValueError("--encoding is csv or base64")
    tile = int(tile)
    if tile < 4:
        raise ValueError("--tile must be at least 4 px")
    stem = _stem(out)
    ts_path = stem + ".tiles.png"
    with open(ts_path, "wb") as f:
        f.write(tileset_png(tile_colours(kind), tile))
    files = [out, ts_path]
    gid = {c: i + 1 for i, c in enumerate(TILE_SYMS)}
    gid[" "] = 0
    tl, oid, lid = [], 1, 1
    for name, rows in layers:
        data = [gid[c] for row in rows for c in row]
        layer = dict(id=lid, name=name, type="tilelayer", x=0, y=0, width=w, height=h, opacity=1, visible=True)
        if encoding == "csv":
            layer["data"] = data
        else:
            layer.update(encoding="base64", compression="zlib",
                         data=base64.b64encode(zlib.compress(struct.pack("<%dI" % len(data), *data), 9)).decode("ascii"))
        tl.append(layer)
        lid += 1
        if csv:
            cp = stem + (".csv" if len(layers) == 1 else ".%s.csv" % name.replace(" ", ""))
            with open(cp, "w", encoding="utf-8", newline="\n") as f:
                for y in range(h):
                    f.write(",".join(str(v - 1) for v in data[y * w:(y + 1) * w]) + "\n")
            files.append(cp)
        walls, portals = grid_walls(kind, rows, w, h, extra)
        suffix = "" if len(layers) == 1 else " " + name
        wo = []
        for a, b in walls:
            wo.append(dict(id=oid, name="", type="wall", x=a[0] * tile, y=a[1] * tile, width=0, height=0, rotation=0,
                           visible=True, polyline=[dict(x=0, y=0), dict(x=(b[0] - a[0]) * tile, y=(b[1] - a[1]) * tile)]))
            oid += 1
        tl.append(dict(id=lid, name="walls" + suffix, type="objectgroup", draworder="topdown", x=0, y=0, opacity=1,
                       visible=True, objects=wo))
        lid += 1
        do = []
        for p in portals:
            (ax, ay), (bx, by) = p["bounds"]
            do.append(dict(id=oid, name="", type="door", x=ax * tile, y=ay * tile, width=0, height=0, rotation=0,
                           visible=True, polyline=[dict(x=0, y=0), dict(x=(bx - ax) * tile, y=(by - ay) * tile)],
                           properties=[dict(name="cell_x", type="int", value=p["x"]),
                                       dict(name="cell_y", type="int", value=p["y"])]))
            oid += 1
        tl.append(dict(id=lid, name="doors" + suffix, type="objectgroup", draworder="topdown", x=0, y=0, opacity=1,
                       visible=True, objects=do))
        lid += 1
    n = len(TILE_SYMS)
    tmj = dict(type="map", version="1.10", tiledversion="1.10.2", orientation="orthogonal", renderorder="right-down",
               width=w, height=h, tilewidth=tile, tileheight=tile, infinite=False, compressionlevel=-1,
               nextlayerid=lid, nextobjectid=oid, layers=tl,
               tilesets=[dict(firstgid=1, name="mapwright", image=os.path.basename(ts_path), imagewidth=tile * n,
                              imageheight=tile, tilewidth=tile, tileheight=tile, tilecount=n, columns=n, margin=0,
                              spacing=0, tiles=[dict(id=i, type=TILE_NAMES[i]) for i in range(n)])],
               properties=[dict(name="mapwright_kind", type="string", value=kind),
                           dict(name="mapwright_seed", type="int", value=int(rc["seed"])),
                           dict(name="mapwright_version", type="string", value=version)])
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(tmj, f, separators=(",", ":"))
        f.write("\n")
    return tiled_bars(out, d), files


def tiled_layers(tmj):
    """Tile layers of a parsed .tmj as (name, width, height, list of gids with the flip bits masked off)."""
    out = []
    for L in tmj["layers"]:
        if L["type"] != "tilelayer":
            continue
        data = L["data"]
        if L.get("encoding") == "base64":
            rawb = base64.b64decode(data)
            comp = L.get("compression")
            if comp == "zlib":
                rawb = zlib.decompress(rawb)
            elif comp == "gzip":
                rawb = zlib.decompress(rawb, 31)
            elif comp:
                raise ValueError("layer compression %r is not read" % comp)
            data = list(struct.unpack("<%dI" % (len(rawb) // 4), rawb))
        out.append((L["name"], L["width"], L["height"], [g & FLIP_MASK for g in data]))
    return out


def tiled_bars(path, d):
    """Load a .tmj back and test it against the recipe: parses, layer sizes, gids in the tileset, cells equal."""
    bars = []
    try:
        with open(path, encoding="utf-8") as f:
            tmj = json.load(f)
        rc, kind, w, h, layers, extra = grid_layers(d)
        got = tiled_layers(tmj)
        ts = tmj["tilesets"][0]
        first, count, tw = ts["firstgid"], ts["tilecount"], ts["tilewidth"]
        bars.append(("tiled: parses, one tile layer per level", tmj["type"] == "map" and len(got) == len(layers),
                     "%d tile layer(s), %d object layer(s), version %s"
                     % (len(got), sum(L["type"] == "objectgroup" for L in tmj["layers"]), tmj["version"])))
        ok = (tmj["width"], tmj["height"]) == (w, h) and all((lw, lh, len(dt)) == (w, h, w * h) for _, lw, lh, dt in got)
        bars.append(("tiled: layer size equals the recipe grid", ok, "%d x %d tiles of %d px" % (w, h, tw)))
        bad = sum(1 for _, _, _, dt in got for g in dt if g and not first <= g < first + count)
        with open(os.path.join(os.path.dirname(os.path.abspath(path)), ts["image"]), "rb") as f:
            iw, ih = P.png_size(f.read())
        rows_t = -(-count // ts["columns"])
        img_ok = (iw, ih) == (ts["imagewidth"], ts["imageheight"]) and iw >= ts["columns"] * tw \
            and ih >= rows_t * ts["tileheight"]
        bars.append(("tiled: every gid is a tile in the tileset image", bad == 0 and img_ok,
                     "%d gids outside %d..%d, image %d x %d for %d tiles" % (bad, first, first + count - 1, iw, ih, count)))
        floor_gid = first + TILE_SYMS.index(".")
        diff = fl = 0
        syms = {i + first: c for i, c in enumerate(TILE_SYMS)}
        syms[0] = " "
        for (_, rows), (_, _, _, dt) in zip(layers, got):
            for y in range(h):
                for x in range(w):
                    g = dt[y * w + x] if y * w + x < len(dt) else -1
                    if syms.get(g) != rows[y][x]:
                        diff += 1
                    if g == floor_gid:
                        fl += 1
        want = sum(row.count(".") for _, rows in layers for row in rows)
        bars.append(("tiled: floor cells equal the recipe's", diff == 0 and fl == want,
                     "%d floor cells, recipe %d, %d cells differ" % (fl, want, diff)))
        px_w, px_h = w * tw, h * tw
        off = sum(1 for L in tmj["layers"] if L["type"] == "objectgroup" for o in L["objects"]
                  for p in o.get("polyline", []) if not (0 <= o["x"] + p["x"] <= px_w and 0 <= o["y"] + p["y"] <= px_h))
        nobj = sum(len(L["objects"]) for L in tmj["layers"] if L["type"] == "objectgroup")
        bars.append(("tiled: wall and door objects inside the map", off == 0, "%d objects, %d points outside" % (nobj, off)))
    except (ValueError, KeyError, TypeError, IndexError, OSError, struct.error, zlib.error) as e:
        bars.append(("tiled: parses", False, "%s: %s" % (e.__class__.__name__, e)))
    return bars


# ------------------------------------------------------------------ deck plans to Universal VTT
def deck_png(rows, w, h, pps, colours):
    col = {c: bytes(G.hex_rgb(colours[i])) for i, c in enumerate(TILE_SYMS)}
    import mpw_space as S
    col[" "] = bytes(G.hex_rgb(S.DST["bg"]))
    gl = bytes(G.hex_rgb(S.DST["grid"]))
    out = []
    for y in range(h):
        body = bytearray()
        line = bytearray()
        for x in range(w):
            c = rows[y][x]
            body += (col[c] if c == " " else gl) + col[c] * (pps - 1)
            line += (col[c] if c == " " else gl) * pps
        out.append(bytes(line))
        out.extend([bytes(body)] * (pps - 1))
    return P.png_rgb(w * pps, h * pps, out)


def deck_uvtt(d, deck, pps=None):
    """One deck of a deck recipe as a Universal VTT dict (deck is 0-based)."""
    rc = P.load(d, "recipe.json")
    if rc.get("kind") != "deck":
        raise ValueError("not a deck recipe")
    dj = P.load(d, "deck.json")
    if not 0 <= deck < len(dj["decks"]):
        raise ValueError("--deck is 1..%d" % len(dj["decks"]))
    w, h = dj["w"], dj["h"]
    pps = int(pps or max(int(rc["params"]["pps"]), 50))
    rows = dj["decks"][deck]
    walls, portals = grid_walls("deck", rows, w, h, dj)
    lights = []
    for rm in dj["rooms"]:
        if rm["deck"] == deck:
            cs = rm["cells"]
            lights.append(dict(x=_r(sum(c[0] for c in cs) / len(cs) + 0.5, 3), y=_r(sum(c[1] for c in cs) / len(cs) + 0.5, 3),
                               range=max(3, rm["x1"] - rm["x0"] + 1)))
    return {
        "format": 0.3,
        "resolution": {"map_origin": {"x": 0, "y": 0}, "map_size": {"x": w, "y": h}, "pixels_per_grid": pps},
        "line_of_sight": [[{"x": a[0], "y": a[1]}, {"x": b[0], "y": b[1]}] for a, b in walls],
        "objects_line_of_sight": [],
        "portals": [{"position": {"x": p["x"] + 0.5, "y": p["y"] + 0.5},
                     "bounds": [{"x": b[0], "y": b[1]} for b in p["bounds"]],
                     "rotation": p["rotation"], "closed": True, "freestanding": False} for p in portals],
        "environment": {"baked_lighting": False, "ambient_light": "ffffffff"},
        "lights": [{"position": {"x": L["x"], "y": L["y"]}, "range": L["range"], "intensity": 1,
                    "color": "ffd8ecff", "shadows": True} for L in lights],
        "image": base64.b64encode(deck_png(rows, w, h, pps, tile_colours("deck"))).decode("ascii"),
    }


def export_deck_uvtt(d, out, deck=None, pps=None):
    dj = P.load(d, "deck.json")
    n = len(dj["decks"])
    which = [int(deck) - 1] if deck else list(range(n))
    stem, ext = os.path.splitext(out)
    bars, files = [], []
    for k in which:
        path = out if (deck or n == 1) else "%s.deck%d%s" % (stem, k + 1, ext)
        text = json.dumps(deck_uvtt(d, k, pps), separators=(",", ":"))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        files.append(path)
        with open(path, encoding="utf-8") as f:
            back = f.read()
        tag = "deck %d " % (k + 1)
        bars += [(tag + nm, ok, det) for nm, ok, det in P.uvtt_bars(back)]
        u = json.loads(back)
        doors = sum(c in "+A" for row in dj["decks"][k] for c in row)
        bars.append((tag + "uvtt: one portal per door", len(u["portals"]) == doors,
                     "%d portals, %d door squares" % (len(u["portals"]), doors)))
    return bars, files


# ------------------------------------------------------------------ hex battle map to PNG
def hex_png(gj, pps, st):
    """Pointy-top odd-r hex battle map as RGB PNG bytes by scan line (same geometry as the SVG)."""
    w, h, g = gj["w"], gj["h"], gj["cells"]
    centre, _, W, H = P.hex_geometry(w, h, pps)
    size = pps / math.sqrt(3)
    col = {P.WALLC: P._rgb(st["rock"]), P.FLOOR: P._rgb(st["floor"]), P.DOOR: P._rgb(st["door"]),
           P.TREE: P._rgb(st["tree"])}
    gl, bg = P._rgb(st["grid"]), P._rgb(st["bg"])
    inner = size - 1.0 / math.cos(math.radians(30))      # apothem one pixel smaller: a 1 px grid line each side
    buf = [bytearray(bg * W) for _ in range(H)]

    def span(cx, dy, s):
        ady = abs(dy)
        if ady > s:
            return None
        hw = s * math.sqrt(3) / 2 if ady <= s / 2 else (s - ady) * math.sqrt(3)
        a, b = int(math.ceil(cx - hw - 0.5)), int(math.floor(cx + hw - 0.5))
        a, b = max(a, 0), min(b, W - 1)
        return (a, b) if b >= a else None

    for y in range(h):
        for x in range(w):
            cx, cy = centre(x, y)
            fill = col[g[y][x]]
            for py in range(max(0, int(math.floor(cy - size))), min(H - 1, int(math.ceil(cy + size))) + 1):
                dy = py + 0.5 - cy
                sp = span(cx, dy, size)
                if sp is None:
                    continue
                row = buf[py]
                row[sp[0] * 3:(sp[1] + 1) * 3] = gl * (sp[1] - sp[0] + 1)
                si = span(cx, dy, inner)
                if si:
                    row[si[0] * 3:(si[1] + 1) * 3] = fill * (si[1] - si[0] + 1)
    return P.png_rgb(W, H, [bytes(r) for r in buf]), W, H


def png_rgb_rows(data):
    """8-bit RGB PNG written by this tool (filter 0 rows) or any filter: rows of bytes."""
    import mpw_space as S
    w, h, rows = S.decode_png(data)
    return w, h, rows


def export_grid_png(d, out, style=None):
    rc = P.load(d, "recipe.json")
    if rc.get("kind") not in ("dungeon", "battle"):
        raise ValueError("--to png is for battle maps and dungeons; a %s renders with `render`" % rc.get("kind"))
    if not out.lower().endswith(".png"):
        raise ValueError("name the output .png")
    gj = P.load(d, "grid.json")
    pps = int(rc["params"]["pps"])
    _, st = P.pstyle(style or rc["params"].get("style"), rc["kind"])
    w, h = gj["w"], gj["h"]
    if gj["grid"] != "hex":
        data = P.grid_png([list(r) for r in gj["cells"]], w, h, pps, st)
        with open(out, "wb") as f:
            f.write(data)
        return [("png: image matches the grid", P.png_size(data) == (w * pps, h * pps),
                 "%d x %d px for %d x %d squares at %d" % (w * pps, h * pps, w, h, pps))], [out]
    data, W, H = hex_png(gj, pps, st)
    with open(out, "wb") as f:
        f.write(data)
    with open(out, "rb") as f:
        bw, bh, rows = png_rgb_rows(f.read())
    centre, _, _, _ = P.hex_geometry(w, h, pps)
    col = {P.WALLC: P._rgb(st["rock"]), P.FLOOR: P._rgb(st["floor"]), P.DOOR: P._rgb(st["door"]),
           P.TREE: P._rgb(st["tree"])}
    bad = 0
    for y in range(h):
        for x in range(w):
            cx, cy = centre(x, y)
            if bytes(rows[int(cy)][int(cx)]) != col[gj["cells"][y][x]]:
                bad += 1
    return [("hex png: same size as the SVG", (bw, bh) == (W, H), "%d x %d px, hex width %d px" % (bw, bh, pps)),
            ("hex png: every hex centre has its cell's colour", bad == 0, "%d of %d hexes differ" % (bad, w * h))], [out]


# ------------------------------------------------------------------ terrain mesh (OBJ) for polywright
def terrain_mesh(z, gw, gl, base=None):
    """Grid of heights (rows north first, already in output units) to vertices and triangles. x east, y north,
    z up, faces counter-clockwise seen from outside. With base (the z of a flat bottom) the mesh is closed by a
    skirt and a bottom fan."""
    nh, nw = len(z), len(z[0])
    V = [(gw * i / (nw - 1.0), gl * (1.0 - j / (nh - 1.0)), z[j][i]) for j in range(nh) for i in range(nw)]
    F = []
    for j in range(nh - 1):
        for i in range(nw - 1):
            a = j * nw + i
            b, c, e = a + 1, a + nw + 1, a + nw
            F.append((a, e, c))
            F.append((a, c, b))
    if base is not None:
        per = [j * nw for j in range(nh - 1)] + [(nh - 1) * nw + i for i in range(nw - 1)] \
            + [j * nw + nw - 1 for j in range(nh - 1, 0, -1)] + [i for i in range(nw - 1, 0, -1)]
        b0 = len(V)
        V += [(V[t][0], V[t][1], base) for t in per]
        cen = len(V)
        V.append((gw / 2.0, gl / 2.0, base))
        n = len(per)
        for k in range(n):
            k2 = (k + 1) % n
            t1, t2, b1, b2 = per[k], per[k2], b0 + k, b0 + k2
            F.append((t2, t1, b1))
            F.append((t2, b1, b2))
            F.append((cen, b2, b1))
    return V, F


def mesh_counts(nw, nh, closed):
    v, f = nw * nh, 2 * (nw - 1) * (nh - 1)
    if closed:
        p = 2 * (nw - 1) + 2 * (nh - 1)
        v, f = v + p + 1, f + 3 * p
    return v, f


def write_obj(path, V, F, header):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join("# %s\n" % ln for ln in header))
        f.write("o terrain\n")
        f.write("".join("v %.4f %.4f %.4f\n" % v for v in V))
        f.write("".join("f %d %d %d\n" % (a + 1, b + 1, c + 1) for a, b, c in F))


def read_obj(path):
    """Vertices and triangles of an OBJ (v and f lines only; faces 0-based)."""
    V, F = [], []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("v "):
                p = ln.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif ln.startswith("f "):
                F.append(tuple(int(t.split("/")[0]) - 1 for t in ln.split()[1:]))
    return V, F


def mesh_stats(V, F):
    """Index validity, edge sharing and signed volume of a triangle mesh."""
    n = len(V)
    bad = sum(1 for f in F if len(f) != 3 or len(set(f)) != 3 or any(not 0 <= i < n for i in f))
    und, dirs = {}, {}
    for f in F:
        for k in range(len(f)):
            p, q = f[k], f[(k + 1) % len(f)]
            und[(p, q) if p < q else (q, p)] = und.get((p, q) if p < q else (q, p), 0) + 1
            dirs[(p, q)] = dirs.get((p, q), 0) + 1
    open_e = sum(1 for c in und.values() if c == 1)
    multi = sum(1 for c in und.values() if c > 2)
    twice = sum(1 for c in dirs.values() if c > 1)
    vol = 0.0
    if not bad:
        for a, b, c in F:
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = V[a], V[b], V[c]
            vol += x1 * (y2 * z3 - y3 * z2) - y1 * (x2 * z3 - x3 * z2) + z1 * (x2 * y3 - x3 * y2)
    return dict(vertices=n, faces=len(F), bad_faces=bad, edges=len(und), open_edges=open_e, multi_edges=multi,
                same_way_edges=twice, watertight=bad == 0 and open_e == 0 and multi == 0 and twice == 0,
                volume=vol / 6.0)


def export_mesh(d, out, version, size=None, exaggeration=1.0, base=None, print_mm=None, flat_sea=False):
    rc, metres, (gw, gl) = load_heights(d)
    sh, sw = len(metres), len(metres[0])
    nw = int(size or min(257, sw))
    if not 2 <= nw <= 2049:
        raise ValueError("--size for a mesh is 2..2049 samples on the east-west side")
    nh = max(2, int(round((nw - 1) * sh / float(sw))) + 1)
    exaggeration = float(exaggeration)
    if exaggeration <= 0:
        raise ValueError("--exaggeration must be above 0")
    folder = os.path.splitext(out)[1].lower() != ".obj"
    if folder:
        os.makedirs(os.path.join(out, "out"), exist_ok=True)
        obj, man, rel = os.path.join(out, "out", "terrain.obj"), os.path.join(out, "manifest.json"), "out/terrain.obj"
    else:
        obj, man, rel = out, _stem(out) + ".manifest.json", os.path.basename(out)
    res = resample(metres, nw, nh, "vertex")
    if flat_sea:
        res = [[v if v > 0.0 else 0.0 for v in r] for r in res]
    lo = min(min(r) for r in res)
    hi = max(max(r) for r in res)
    if print_mm:
        units, k = "mm", float(print_mm) / max(gw, gl)          # mm per ground metre
        base_t = 2.0 if base is None else float(base)
    else:
        units, k = "m", 1.0
        base_t = None if base is None else float(base)
    if base_t is not None and base_t <= 0:
        raise ValueError("--base must be above 0 (thickness under the lowest point)")
    closed = base_t is not None
    zoff = base_t - lo * exaggeration * k if closed else 0.0
    z = [[v * exaggeration * k + zoff for v in r] for r in res]
    V, F = terrain_mesh(z, gw * k, gl * k, 0.0 if closed else None)
    name = rc.get("name") or os.path.basename(os.path.abspath(d))
    scale_n = 1.0 / (k / 1000.0) if units == "mm" else 1.0
    write_obj(obj, V, F, ["mapwright %s terrain mesh of %s (%s, seed %s)" % (version, name, rc["kind"], rc["seed"]),
                          "units %s, x east, y north, z up; scale 1:%s; vertical exaggeration %s"
                          % (units, ("%.0f" % scale_n), ("%g" % exaggeration)),
                          "grid %d x %d samples%s" % (nw, nh, ", closed with a %g %s base" % (base_t, units) if closed else "")])
    with open(obj, "rb") as f:
        blob = f.read()
    BV, BF = read_obj(obj)
    stt = mesh_stats(BV, BF)
    wv, wf = mesh_counts(nw, nh, closed)
    dims = [_r(gw * k, 4), _r(gl * k, 4), _r(max(v[2] for v in BV) - min(v[2] for v in BV), 4)]
    target = "print-fdm" if units == "mm" else "terrain"
    manifest = {
        "polywright": "1", "name": name, "kind": "imagined", "route": "procedural",
        "brief": "Terrain of a generated %s (mapwright seed %s), %s." % (
            rc["kind"], rc["seed"], "a print tile %g mm on its longer side" % float(print_mm) if print_mm
            else "at real size in metres"),
        "targets": [target], "units": units, "real_size_m": _r(max(gw, gl), 2), "up": "+Z (x east, y north)",
        "sources": [], "tools": [{"name": "mapwright", "version": version}],
        "outputs": [{"path": rel, "target": target, "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                     "tris": stt["faces"], "dims": dims, "watertight": stt["watertight"]}],
        "reviews": [], "status": "model",
        "mapwright": {
            "recipe": {"path": os.path.relpath(os.path.abspath(d), os.path.dirname(os.path.abspath(man))).replace("\\", "/"),
                       "kind": rc["kind"], "seed": rc["seed"], "generator": rc.get("generator")},
            "grid": [nw, nh], "vertices": stt["vertices"], "faces": stt["faces"], "scale": "1:%.0f" % scale_n,
            "units_per_ground_metre": _r(k, 9), "vertical_exaggeration": exaggeration,
            "base": base_t, "flat_sea": bool(flat_sea), "min_m": _r(lo, 3), "max_m": _r(hi, 3),
            "z_of_sea_level": _r(zoff, 4), "ground_m": [_r(gw, 2), _r(gl, 2)], "resample": RESAMPLE["vertex"],
            "handoff": "Blender: File > Import > Wavefront (.obj) with Forward Y and Up Z, so north stays +Y and "
                       "heights +Z. polywright: `pw.py inspect` the OBJ, then polywright-print for a slicer file "
                       "(the closed mesh is one solid in mm) or polywright-finish for a game mesh. Relief models "
                       "state their vertical exaggeration on the label.",
        },
    }
    _dump(man, manifest)
    files = [obj, man]
    if folder:
        brief = os.path.join(out, "brief.md")
        with open(brief, "w", encoding="utf-8", newline="\n") as f:
            f.write("# %s\n\n%s\n\n- Source: mapwright %s recipe, seed %s.\n- Units: %s. Scale 1:%.0f. Vertical "
                    "exaggeration %g.\n- Mesh: out/terrain.obj, %d vertices, %d triangles%s.\n"
                    % (name, manifest["brief"], rc["kind"], rc["seed"], units, scale_n, exaggeration, stt["vertices"],
                       stt["faces"], ", watertight" if stt["watertight"] else ""))
        files.append(brief)
    bars = [("mesh: vertex and face counts match the grid", (stt["vertices"], stt["faces"]) == (wv, wf),
             "%d vertices, %d faces for %d x %d samples%s" % (stt["vertices"], stt["faces"], nw, nh,
                                                             " with base" if closed else "")),
            ("mesh: every face index is valid", stt["bad_faces"] == 0, "%d bad faces" % stt["bad_faces"])]
    if closed:
        bars.append(("mesh: watertight (every edge shared by exactly two faces)", stt["watertight"]
                     and stt["volume"] > 0, "%d edges, %d open, %d shared by more than two, %d same-way, volume %.1f %s3"
                     % (stt["edges"], stt["open_edges"], stt["multi_edges"], stt["same_way_edges"], stt["volume"], units)))
    return bars, files


# ------------------------------------------------------------------ print: PDF and PNG at a paper size
PAPER_MM = {"A0": (841.0, 1189.0), "A1": (594.0, 841.0), "A2": (420.0, 594.0), "A3": (297.0, 420.0),
            "A4": (210.0, 297.0), "A5": (148.0, 210.0), "LETTER": (215.9, 279.4), "LEGAL": (215.9, 355.6),
            "TABLOID": (279.4, 431.8)}
MAX_PRINT_PX = 16000


def paper_size(name, landscape=False):
    """Paper name or WxH in mm to (width mm, height mm)."""
    key = str(name).strip().upper()
    if key in PAPER_MM:
        w, h = PAPER_MM[key]
    else:
        m = re.match(r"^(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)(?:MM)?$", key)
        if not m:
            raise ValueError("--paper is one of %s, or WxH in mm (for example 300x200)"
                             % ", ".join(sorted(PAPER_MM)))
        w, h = float(m.group(1)), float(m.group(2))
        if not (10 <= w <= 5000 and 10 <= h <= 5000):
            raise ValueError("custom paper is 10 to 5000 mm a side")
        return (w, h)
    return (h, w) if landscape else (w, h)


def page_px(mm, dpi):
    return int(round(mm / 25.4 * dpi))


def print_page_svg(svg, paper, bleed=0.0, marks=True, margin=10.0, fit="contain"):
    """Wrap a map SVG in a page SVG in millimetres: the page is the paper plus the bleed on every edge."""
    pw, ph = paper
    W, H = pw + 2 * bleed, ph + 2 * bleed
    m = re.search(r"<svg\b[^>]*>", svg)
    if not m:
        raise ValueError("no <svg> root in the map")
    tag = m.group(0)

    def attr(nm):
        mm = re.search(r'\s%s="([^"]*)"' % nm, tag)
        return mm.group(1) if mm else None
    vb = attr("viewBox")
    if not vb:
        vb = "0 0 %s %s" % (float(attr("width")), float(attr("height")))
    bgm = re.search(r'<rect width="100%" height="100%" fill="(#[0-9a-fA-F]{3,8})"', svg)
    bg = bgm.group(1) if bgm else "#ffffff"
    if fit == "cover":
        x, y, w, h, par = 0.0, 0.0, W, H, "xMidYMid slice"
    elif fit == "contain":
        x, y, w, h, par = bleed + margin, bleed + margin, pw - 2 * margin, ph - 2 * margin, "xMidYMid meet"
        if w <= 0 or h <= 0:
            raise ValueError("--margin leaves no room on the paper")
    else:
        raise ValueError("--fit is contain or cover")
    keep = re.sub(r'\s(?:width|height|x|y|viewBox|preserveAspectRatio)="[^"]*"', "", tag[:-1])
    inner = '%s x="%.4f" y="%.4f" width="%.4f" height="%.4f" viewBox="%s" preserveAspectRatio="%s">' % (
        keep, x, y, w, h, vb, par)
    body = svg[:m.start()] + inner + svg[m.end():]
    body = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", body)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.4fmm" height="%.4fmm" viewBox="0 0 %.4f %.4f">' % (W, H, W, H),
         '<rect x="0" y="0" width="%.4f" height="%.4f" fill="%s"/>' % (W, H, bg), body]
    if bleed > 0 and marks:
        gap = min(1.0, bleed / 2.0)
        o.append('<g class="crop-marks" stroke="#000000" stroke-width="0.25" fill="none">')
        for cx in (bleed, bleed + pw):
            for y0, y1 in ((0.0, bleed - gap), (H, bleed + ph + gap)):
                o.append('<line x1="%.4f" y1="%.4f" x2="%.4f" y2="%.4f"/>' % (cx, y0, cx, y1))
        for cy in (bleed, bleed + ph):
            for x0, x1 in ((0.0, bleed - gap), (W, bleed + pw + gap)):
                o.append('<line x1="%.4f" y1="%.4f" x2="%.4f" y2="%.4f"/>' % (x0, cy, x1, cy))
        o.append("</g>")
    o.append("</svg>")
    return "\n".join(o) + "\n"


_PDF_NUM = rb"(-?\d*\.?\d+)"
_PDF_BOX = rb"\s*\[\s*" + _PDF_NUM + rb"\s+" + _PDF_NUM + rb"\s+" + _PDF_NUM + rb"\s+" + _PDF_NUM + rb"\s*\]"
PDF_GROW_PT = 2.0   # the page is asked this much larger than needed, then cut back to the drawing


def _pdf_dict(data, pos):
    """The dictionary that opens at or after pos, as bytes with its outer << >>."""
    start = data.index(b"<<", pos)
    depth, i = 0, start
    while True:
        a, b = data.find(b"<<", i), data.find(b">>", i)
        if b < 0:
            raise ValueError("unbalanced PDF dictionary")
        if 0 <= a < b:
            depth, i = depth + 1, a + 2
        else:
            depth, i = depth - 1, b + 2
            if depth == 0:
                return data[start:i]


def pdf_objects(data):
    """Object number to byte offset from the cross-reference tables, newest update first, and the newest trailer.
    Classic tables only (what headless Chrome writes); a cross-reference stream is refused."""
    ends = list(re.finditer(rb"startxref\s+(\d+)\s+%%EOF", data))
    if not ends:
        raise ValueError("no startxref in the PDF")
    off, objs, trailer, seen = int(ends[-1].group(1)), {}, None, set()
    head = re.compile(rb"\s*(\d+)\s+(\d+)[ \t]*\r?\n")
    while off is not None and off not in seen:
        seen.add(off)
        if data[off:off + 4] != b"xref":
            raise ValueError("this PDF uses a cross-reference stream, which is not read")
        pos = off + 4
        while True:
            m = head.match(data, pos)
            if not m:
                break
            first, count, pos = int(m.group(1)), int(m.group(2)), m.end()
            for k in range(count):
                ent = data[pos:pos + 20]
                if ent[17:18] == b"n":
                    objs.setdefault(first + k, int(ent[:10]))
                pos += 20
        td = _pdf_dict(data, data.index(b"trailer", pos))
        trailer = trailer or td
        prev = re.search(rb"/Prev\s+(\d+)", td)
        off = int(prev.group(1)) if prev else None
    return objs, trailer


def pdf_pages(data):
    """Each page of a PDF as a dict: obj, body, MediaBox, and TrimBox and BleedBox when set."""
    objs, trailer = pdf_objects(data)

    def body(n):
        if not re.match(rb"%d\s+0\s+obj" % n, data[objs[n]:objs[n] + 24]):
            raise ValueError("object %d is not where the cross-reference table says" % n)
        return _pdf_dict(data, objs[n])

    def walk(n, out):
        b = body(n)
        if re.search(rb"/Type\s*/Pages", b):
            kids = re.search(rb"/Kids\s*\[([^\]]*)\]", b).group(1)
            for k in re.findall(rb"(\d+)\s+0\s+R", kids):
                walk(int(k), out)
            return
        page = dict(obj=n, body=b)
        for key in ("MediaBox", "TrimBox", "BleedBox"):
            m = re.search(b"/" + key.encode() + _PDF_BOX, b)
            if m:
                page[key] = tuple(float(v) for v in m.groups())
        out.append(page)

    root = int(re.search(rb"/Root\s+(\d+)\s+0\s+R", trailer).group(1))
    out = []
    walk(int(re.search(rb"/Pages\s+(\d+)\s+0\s+R", body(root)).group(1)), out)
    return out


def pdf_set_boxes(data, w_pt, h_pt, bleed_pt=0.0):
    """Cut a one-page PDF back to a w x h point rectangle hanging from the page's top-left corner, where a browser
    puts the drawing, and set BleedBox and TrimBox. Appended as an incremental update, so no byte of the browser's
    file moves."""
    pages = pdf_pages(data)
    if len(pages) != 1 or "MediaBox" not in pages[0]:
        raise ValueError("expected one page with a MediaBox, found %d" % len(pages))
    pg = pages[0]
    x0, _, _, top = pg["MediaBox"]
    box = (x0, top - h_pt, x0 + w_pt, top)
    trim = (box[0] + bleed_pt, box[1] + bleed_pt, box[2] - bleed_pt, box[3] - bleed_pt)

    def arr(b):
        return ("[%s]" % " ".join(("%.4f" % v).rstrip("0").rstrip(".") for v in b)).encode("ascii")
    b = re.sub(rb"/(?:MediaBox|TrimBox|BleedBox|CropBox)" + _PDF_BOX + rb"\s*", b"", pg["body"])
    b = b[:-2] + b"\n/MediaBox " + arr(box) + b"\n/BleedBox " + arr(box) + b"\n/TrimBox " + arr(trim) + b">>"
    _, trailer = pdf_objects(data)
    size = int(re.search(rb"/Size\s+(\d+)", trailer).group(1))
    keep = b"".join(b"\n" + m.group(0) for m in re.finditer(rb"/(?:Root|Info)\s+\d+\s+0\s+R", trailer))
    prev = int(re.findall(rb"startxref\s+(\d+)\s+%%EOF", data)[-1])
    out = data if data.endswith(b"\n") else data + b"\n"
    at = len(out)
    out += b"%d 0 obj\n" % pg["obj"] + b + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n%d 1\n%010d 00000 n \n" % (pg["obj"], at)
    out += b"trailer\n<</Size %d%s\n/Prev %d>>\nstartxref\n%d\n%%%%EOF\n" % (size, keep, prev, xref)
    return out


def _chrome(browser, args, out_abs, timeout):
    if os.path.exists(out_abs):
        os.remove(out_abs)
    subprocess.run([browser] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
    if not os.path.isfile(out_abs):
        raise RuntimeError("the browser did not write " + out_abs)


def recipe_svg(d, style=None):
    rc = P.load(d, "recipe.json")
    kind = rc.get("kind")
    if kind in ("city", "dungeon", "battle"):
        return P.render_svg(d, style)
    if kind in ("sector", "system", "planet", "deck"):
        import mpw_space as S
        return S.render_svg(d, None)
    import mpw_render as R
    return R.render_svg(d, style or R.DEFAULT_STYLE, None, None)[0]


def export_print(d, out, version, paper="A4", landscape=False, dpi=300, bleed=0.0, marks=True, margin=10.0,
                 fit="contain", style=None, browser=None, timeout=180):
    import mpw_render as R
    ext = os.path.splitext(out)[1].lower()
    if ext not in (".pdf", ".png", ""):
        raise ValueError("print output is .pdf, .png, or a name without an extension for both")
    dpi, bleed, margin = int(dpi), float(bleed), float(margin)
    if not 30 <= dpi <= 1200:
        raise ValueError("--dpi is 30 to 1200")
    if not 0 <= bleed <= 25:
        raise ValueError("--bleed is 0 to 25 mm")
    pw, ph = paper_size(paper, landscape)
    W, H = pw + 2 * bleed, ph + 2 * bleed
    px = (page_px(W, dpi), page_px(H, dpi))
    want_png = ext in (".png", "")
    if want_png and max(px) > MAX_PRINT_PX:
        raise ValueError("%d x %d px is past the %d px a browser screenshot holds; lower --dpi or write the .pdf"
                         % (px[0], px[1], MAX_PRINT_PX))
    browser = browser or R.find_browser()
    if not browser:
        raise RuntimeError("print export needs Chrome or Edge (headless) and none was found (`mpw.py doctor`); "
                           "skipped. `render DIR -o map.svg` still works")
    page = print_page_svg(recipe_svg(d, style), (pw, ph), bleed, marks, margin, fit)
    title = P.load(d, "recipe.json").get("name") or os.path.basename(os.path.abspath(d))
    stem = out if ext == "" else _stem(out)
    files, bars = [], []
    tmp = tempfile.mkdtemp(prefix="mpw-print-")
    try:
        common = ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                  "--no-default-browser-check", "--user-data-dir=" + os.path.join(tmp, "prof")]
        if ext in (".pdf", ""):
            pdf = os.path.abspath(stem + ".pdf")
            html = os.path.join(tmp, "pdf.html")
            wpt, hpt = W / 25.4 * 72.0, H / 25.4 * 72.0
            with open(html, "w", encoding="utf-8", newline="\n") as f:
                f.write('<!doctype html><html><head><meta charset="utf-8"><title>%s</title><style>@page{size:%.4fpt '
                        '%.4fpt;margin:0}html,body{margin:0;padding:0;overflow:hidden}svg{display:block}</style></head>'
                        '<body>%s</body></html>' % (html_escape(title), wpt + PDF_GROW_PT, hpt + PDF_GROW_PT, page))
            _chrome(browser, common + ["--no-pdf-header-footer", "--print-to-pdf=" + pdf,
                                       "file:///" + html.replace("\\", "/").lstrip("/")], pdf, timeout)
            files.append(stem + ".pdf")
            with open(pdf, "rb") as f:
                raw = f.read()
            got = pdf_pages(raw)
            bw, bh = (got[0]["MediaBox"][2] - got[0]["MediaBox"][0], got[0]["MediaBox"][3] - got[0]["MediaBox"][1]) \
                if got else (0.0, 0.0)
            roomy = len(got) == 1 and bw >= wpt and bh >= hpt
            if roomy:
                with open(pdf, "wb") as f:
                    f.write(pdf_set_boxes(raw, wpt, hpt, bleed / 25.4 * 72.0))
                with open(pdf, "rb") as f:
                    got = pdf_pages(f.read())
            mb = got[0]["MediaBox"] if got else (0, 0, 0, 0)
            err = max(abs(mb[2] - mb[0] - wpt), abs(mb[3] - mb[1] - hpt))
            bars.append(("print pdf: MediaBox is the paper plus bleed within 0.5 pt", roomy and err <= 0.5,
                         "%.3f x %.3f pt, wanted %.3f x %.3f, difference %.4f pt (browser page was %.2f x %.2f)"
                         % (mb[2] - mb[0], mb[3] - mb[1], wpt, hpt, err, bw, bh)))
            tb = got[0].get("TrimBox") if got else None
            terr = max(abs(tb[2] - tb[0] - pw / 25.4 * 72.0), abs(tb[3] - tb[1] - ph / 25.4 * 72.0)) if tb else 1e9
            bars.append(("print pdf: one page, TrimBox is the paper", len(got) == 1 and terr <= 0.5,
                         "%d page(s), trim difference %.4f pt" % (len(got), terr)))
        if want_png:
            png = os.path.abspath(stem + ".png")
            html = os.path.join(tmp, "png.html")
            sized = page.replace('width="%.4fmm" height="%.4fmm"' % (W, H), 'width="%d" height="%d"' % px, 1)
            sized = sized.replace("<svg ", '<svg preserveAspectRatio="none" ', 1)
            with open(html, "w", encoding="utf-8", newline="\n") as f:
                f.write('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;'
                        'overflow:hidden}svg{display:block}</style></head><body>%s</body></html>' % sized)
            _chrome(browser, common + ["--force-device-scale-factor=1", "--window-size=%d,%d" % px,
                                       "--screenshot=" + png, "file:///" + html.replace("\\", "/").lstrip("/")],
                    png, timeout)
            files.append(stem + ".png")
            with open(png, "rb") as f:
                got = tuple(P.png_size(f.read(32)))
            bars.append(("print png: pixels are the paper plus bleed at the DPI", got == px,
                         "%d x %d px, wanted %d x %d (%.1f x %.1f mm at %d dpi)" % (got[0], got[1], px[0], px[1], W, H, dpi)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    side = dict(mapwright=version, paper=str(paper).upper() if str(paper).upper() in PAPER_MM else "custom",
                orientation="landscape" if pw > ph else "portrait", trim_mm=[pw, ph], bleed_mm=bleed, page_mm=[W, H],
                dpi=dpi, page_px=list(px), page_pt=[_r(W / 25.4 * 72, 3), _r(H / 25.4 * 72, 3)],
                trim_box_pt=[_r(bleed / 25.4 * 72, 3), _r(bleed / 25.4 * 72, 3), _r((bleed + pw) / 25.4 * 72, 3),
                             _r((bleed + ph) / 25.4 * 72, 3)],
                crop_marks=bool(bleed > 0 and marks), fit=fit, margin_mm=margin if fit == "contain" else 0.0,
                files=[os.path.basename(p) for p in files],
                notes=["Colour is RGB; ask the printer for their CMYK profile and convert there.",
                       "The PDF sets MediaBox, BleedBox and TrimBox; it is not PDF/X (no output intent, RGB). "
                       "trim_box_pt is measured from the page's lower left corner.",
                       "Crop marks sit inside the bleed, on the trim lines, and are cut off with it.",
                       "fit contain keeps the whole map inside the margin and fills the rest with the map's "
                       "background; fit cover scales the map over the bleed and crops what does not fit."])
    sj = stem + ".print.json"
    _dump(sj, side)
    files.append(sj)
    return bars, files


# ------------------------------------------------------------------ dispatch
def pick_target(kind, out, to, grid=None):
    if to:
        if to not in TARGETS:
            raise ValueError("--to is one of " + ", ".join(TARGETS))
        return to
    ext = os.path.splitext(out)[1].lower()
    if ext == ".png":
        if kind == "planet":
            return "sphere"
        if kind == "battle" and grid == "hex":
            return "png"
        raise ValueError("a .png can be several things here: say --to %s" % (
            "unreal, godot, roblox or print" if kind in LAND else "png or print"))
    if ext in EXT_TARGET:
        return EXT_TARGET[ext]
    raise ValueError("cannot tell the export from %r: say --to (%s)" % (os.path.basename(out), ", ".join(TARGETS)))


def export(d, out, to=None, version="0.7.0", **o):
    """Run one export. Returns (bars, files); bars are (name, ok, detail)."""
    rc = P.load(d, "recipe.json")
    kind = rc.get("kind")
    grid = None
    if kind == "battle":
        grid = P.load(d, "grid.json").get("grid")
    to = pick_target(kind, out, to, grid)
    if to in ("sphere", "t5"):
        import mpw_space as S
        if kind not in ("planet", "sector"):
            raise ValueError("--to %s is for a %s recipe" % (to, "planet" if to == "sphere" else "sector"))
        return S.export(d, out)
    if to == "uvtt":
        if kind == "deck":
            return export_deck_uvtt(d, out, o.get("deck"), o.get("pps"))
        if kind == "battle" and grid == "hex":
            raise ValueError("Universal VTT is square-grid only (pixels_per_grid has no hex form); a hex battle map "
                             "exports with --to png")
        P.write_uvtt(d, out)
        with open(out, encoding="utf-8") as f:
            return P.uvtt_bars(f.read()), [out]
    if to == "png":
        return export_grid_png(d, out, o.get("style"))
    if to in ("unity", "unreal", "godot", "roblox"):
        return export_heightmap(d, out, to, version, o.get("size"), bool(o.get("flip")), o.get("bits"))
    if to == "tiled":
        return export_tiled(d, out, version, o.get("tile") or 32, o.get("encoding") or "csv", bool(o.get("csv")))
    if to == "mesh":
        return export_mesh(d, out, version, o.get("size"), o.get("exaggeration") or 1.0, o.get("base"),
                           o.get("print_mm"), bool(o.get("flat_sea")))
    return export_print(d, out, version, o.get("paper") or "A4", bool(o.get("landscape")), o.get("dpi") or 300,
                        o.get("bleed") or 0.0, not o.get("no_marks"), 10.0 if o.get("margin") is None else o["margin"],
                        o.get("fit") or "contain", o.get("style"))
