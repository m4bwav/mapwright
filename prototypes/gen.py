"""Throwaway mapwright prototype: world-keyed jittered grid -> Delaunay (dual of
jittered grid, quad diagonal by in-circle test) -> Voronoi plates -> uplift ->
Priority-Flood (epsilon) -> flow accumulation -> rivers -> SVG with embedded
PNG hillshade -> 4x-density child zoom with coast deviation. Stdlib only.
Usage: python gen.py N SEED OUT.svg"""
import sys, time, math, heapq, zlib, struct, base64, hashlib, json

M64 = (1 << 64) - 1
def h64(*k):
    x = 0x9E3779B97F4A7C15
    for v in k:
        x = (x ^ (v & M64)) * 0xBF58476D1CE4E5B9 & M64
        x ^= x >> 31; x = x * 0x94D049BB133111EB & M64; x ^= x >> 29
    return x
def u01(*k): return (h64(*k) >> 11) / float(1 << 53)

def vnoise(seed, x, y, f):
    """value noise keyed by world position (not by zoom level)"""
    x *= f; y *= f; ix = math.floor(x); iy = math.floor(y); fx = x - ix; fy = y - iy
    fx = fx*fx*(3-2*fx); fy = fy*fy*(3-2*fy)
    a = u01(seed, ix, iy); b = u01(seed, ix+1, iy); c = u01(seed, ix, iy+1); d = u01(seed, ix+1, iy+1)
    top = a + (b-a)*fx; bot = c + (d-c)*fx
    return top + (bot-top)*fy
def fbm(seed, x, y, f, octaves=4):
    s = 0.0; a = 1.0; t = 0.0
    for o in range(octaves):
        s += a*vnoise(seed+o, x, y, f); t += a; a *= 0.5; f *= 2
    return s/t - 0.5

WORLD = 1000.0

def build_mesh(seed, x0, y0, x1, y1, sp, jit=0.4):
    gx0 = math.ceil(x0/sp); gy0 = math.ceil(y0/sp)
    nx = int(round((x1-x0)/sp)); ny = int(round((y1-y0)/sp))
    X = []; Y = []
    lvl = round(math.log2(WORLD/sp)*8)
    for j in range(ny):
        for i in range(nx):
            gi = gx0+i; gj = gy0+j
            X.append((gi + (u01(seed, 1, lvl, gi, gj)-0.5)*2*jit)*sp)
            Y.append((gj + (u01(seed, 2, lvl, gi, gj)-0.5)*2*jit)*sp)
    nb = [[] for _ in range(nx*ny)]; tris = []
    def incircle(a, b, c, d):
        ax, ay = X[a]-X[d], Y[a]-Y[d]; bx, by = X[b]-X[d], Y[b]-Y[d]; cx, cy = X[c]-X[d], Y[c]-Y[d]
        return (ax*ax+ay*ay)*(bx*cy-cx*by) - (bx*bx+by*by)*(ax*cy-cx*ay) + (cx*cx+cy*cy)*(ax*by-bx*ay) > 0
    for j in range(ny-1):
        for i in range(nx-1):
            a = j*nx+i; b = a+1; c = a+nx+1; d = a+nx
            if incircle(a, b, c, d):
                tris += [(a, b, d), (b, c, d)]; diag = (b, d)
            else:
                tris += [(a, b, c), (a, c, d)]; diag = (a, c)
            for p, q in ((a, b), (a, d), diag):
                nb[p].append(q); nb[q].append(p)
    for j in range(ny-1):
        a = j*nx+nx-1; nb[a].append(a+nx); nb[a+nx].append(a)
    for i in range(nx-1):
        a = (ny-1)*nx+i; nb[a].append(a+1); nb[a+1].append(a)
    return X, Y, nx, ny, nb, tris

def plates(seed, X, Y, nplates=14):
    P = [(u01(seed, 10, k)*WORLD, u01(seed, 11, k)*WORLD) for k in range(nplates)]
    cont = [u01(seed, 12, k) < 0.4 for k in range(nplates)]
    vel = [(u01(seed, 13, k)-0.5, u01(seed, 14, k)-0.5) for k in range(nplates)]
    n = len(X); pl = [0]*n; d2 = [0.0]*n
    for c in range(n):
        x = X[c] + 60*fbm(seed+50, X[c], Y[c], 0.004); y = Y[c] + 60*fbm(seed+60, X[c], Y[c], 0.004)
        best = 1e18; bk = 0; sec = 1e18
        for k, (px, py) in enumerate(P):
            dd = (x-px)**2 + (y-py)**2
            if dd < best: sec = best; best = dd; bk = k
            elif dd < sec: sec = dd
        pl[c] = bk; d2[c] = math.sqrt(sec) - math.sqrt(best)
    return P, cont, vel, pl, d2

def height_field(seed, X, Y, P, cont, vel, pl, d2):
    n = len(X); H = [0.0]*n
    for c in range(n):
        k = pl[c]; base = 0.35 if cont[k] else -0.45
        x, y = X[c], Y[c]
        px, py = P[k]; dx, dy = x-px, y-py; L = math.hypot(dx, dy) or 1
        conv = (vel[k][0]*dx + vel[k][1]*dy)/L
        up = max(0.0, conv)*1.6*math.exp(-d2[c]/40.0)
        e = x/WORLD; f = y/WORLD
        edge = min(e, f, 1-e, 1-f)
        fall = min(1.0, max(0.0, edge*6))
        H[c] = (base + up + 0.55*fbm(seed+70, x, y, 0.006, 5))*fall - (1-fall)*0.6
    return H

def priority_flood(H, nb, ocean, eps=1e-5):
    n = len(H); F = H[:]; closed = [False]*n; pq = []
    for c in range(n):
        if ocean[c]:
            closed[c] = True
            if any(not ocean[q] for q in nb[c]): heapq.heappush(pq, (F[c], c))
    while pq:
        h, c = heapq.heappop(pq)
        for q in nb[c]:
            if not closed[q]:
                closed[q] = True
                if F[q] <= h + eps: F[q] = h + eps
                heapq.heappush(pq, (F[q], q))
    return F

def flow(F, nb, ocean):
    n = len(F); rcv = [-1]*n
    for c in range(n):
        if ocean[c]: continue
        best = F[c]; b = -1
        for q in nb[c]:
            if F[q] < best: best = F[q]; b = q
        rcv[c] = b
    order = sorted(range(n), key=F.__getitem__, reverse=True)
    acc = [1.0]*n
    for c in order:
        r = rcv[c]
        if r >= 0: acc[r] += acc[c]
    return rcv, acc

def generate(N, seed):
    t = {}; t0 = time.perf_counter()
    side = int(math.sqrt(N)); sp = WORLD/side
    X, Y, nx, ny, nb, tris = build_mesh(seed, 0, 0, WORLD, WORLD, sp); t['mesh'] = time.perf_counter()-t0
    t1 = time.perf_counter(); P, cont, vel, pl, d2 = plates(seed, X, Y); H = height_field(seed, X, Y, P, cont, vel, pl, d2); t['plates_uplift'] = time.perf_counter()-t1
    ocean = [h < 0 for h in H]
    t1 = time.perf_counter(); F = priority_flood(H, nb, ocean); t['priority_flood'] = time.perf_counter()-t1
    t1 = time.perf_counter(); rcv, acc = flow(F, nb, ocean); t['flow_acc'] = time.perf_counter()-t1
    thr = max(20, len(X)//400)
    river = [(acc[c] >= thr and not ocean[c]) for c in range(len(X))]
    t['total_gen'] = time.perf_counter()-t0
    return dict(X=X, Y=Y, nx=nx, ny=ny, nb=nb, tris=tris, H=H, F=F, ocean=ocean, rcv=rcv, acc=acc, river=river, sp=sp, t=t, thr=thr)

def check(m):
    X, F, ocean, rcv, river, H, nb = m['X'], m['F'], m['ocean'], m['rcv'], m['river'], m['H'], m['nb']
    bad_down = 0; bad_end = 0
    for c in range(len(X)):
        if not river[c]: continue
        cur = c; steps = 0
        while not ocean[cur]:
            r = rcv[cur]
            if r < 0: bad_end += 1; break
            if not F[r] < F[cur]: bad_down += 1; break
            cur = r; steps += 1
            if steps > len(X): bad_end += 1; break
    lake = sum(1 for c in range(len(X)) if not ocean[c] and F[c] - H[c] > 1e-3)
    nonnb = sum(1 for c in range(len(X)) if rcv[c] >= 0 and rcv[c] not in nb[c])
    return dict(land=sum(1 for o in ocean if not o), river_cells=sum(river), lake_cells=lake,
                not_downhill=bad_down, no_outlet=bad_end, splits=0, receiver_not_neighbour=nonnb)

def digest(m):
    b = struct.pack('<%dd' % len(m['F']), *m['F']) + struct.pack('<%di' % len(m['rcv']), *m['rcv'])
    return hashlib.sha256(b).hexdigest()

def png(w, h, rows):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t+d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')

def raster(m, R):
    X, Y, nx, ny, F, sp = m['X'], m['Y'], m['nx'], m['ny'], m['F'], m['sp']
    Z = [[0.0]*R for _ in range(R)]
    for r in range(R):
        wy = (r+0.5)/R*WORLD
        for col in range(R):
            wx = (col+0.5)/R*WORLD
            gi = min(nx-1, max(0, round(wx/sp))); gj = min(ny-1, max(0, round(wy/sp)))
            best = 1e18; v = 0.0
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    i = gi+di; j = gj+dj
                    if 0 <= i < nx and 0 <= j < ny:
                        c = j*nx+i; d = (X[c]-wx)**2+(Y[c]-wy)**2
                        if d < best: best = d; v = F[c]
            Z[r][col] = max(v, 0.0)
    return Z

def hillshade(Z, cell, zf=400.0, az=315, alt=45):
    R = len(Z); out = [[0]*R for _ in range(R)]
    zen = math.radians(90-alt); azr = math.radians((360-az+90) % 360)
    cz, sz = math.cos(zen), math.sin(zen)
    for r in range(R):
        r0 = max(r-1, 0); r2 = min(r+1, R-1)
        for c in range(R):
            c0 = max(c-1, 0); c2 = min(c+1, R-1)
            a, b, cc = Z[r0][c0], Z[r0][c], Z[r0][c2]; d, f = Z[r][c0], Z[r][c2]; g, hh, i = Z[r2][c0], Z[r2][c], Z[r2][c2]
            dzdx = ((cc+2*f+i)-(a+2*d+g))/(8*cell)*zf; dzdy = ((g+2*hh+i)-(a+2*b+cc))/(8*cell)*zf
            slope = math.atan(math.hypot(dzdx, dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            v = cz*math.cos(slope) + sz*math.sin(slope)*math.cos(azr-aspect)
            out[r][c] = max(0, min(255, int(255*v)))
    return out

def coast_segments(m):
    X, Y, H, tris = m['X'], m['Y'], m['H'], m['tris']; segs = []
    for t in tris:
        pts = []
        for p, q in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            hp, hq = H[p], H[q]
            if (hp < 0) != (hq < 0):
                s = hp/(hp-hq); pts.append((X[p]+(X[q]-X[p])*s, Y[p]+(Y[q]-Y[p])*s))
        if len(pts) == 2: segs.append(pts)
    return segs

def render(m, path, R=512):
    t0 = time.perf_counter()
    Z = raster(m, R); hs = hillshade(Z, WORLD/R)
    t_hs = time.perf_counter()-t0
    b64 = base64.b64encode(png(R, R, hs)).decode()
    X, Y, rcv, acc, river, ocean = m['X'], m['Y'], m['rcv'], m['acc'], m['river'], m['ocean']
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">',
           '<rect width="1000" height="1000" fill="#a9c8de"/>',
           '<image href="data:image/png;base64,%s" width="1000" height="1000" opacity="0.6"/>' % b64]
    segs = coast_segments(m)
    out.append('<path fill="none" stroke="#2b3a42" stroke-width="1.2" d="%s"/>' % ''.join('M%.1f %.1fL%.1f %.1f' % (a[0], a[1], b[0], b[1]) for a, b in segs))
    rv = []
    for c in range(len(X)):
        if river[c] and rcv[c] >= 0:
            w = 0.4 + 0.25*math.sqrt(acc[c]/m['thr'])
            rv.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="%.2f"/>' % (X[c], Y[c], X[rcv[c]], Y[rcv[c]], w))
    out.append('<g stroke="#2f6fa8" stroke-linecap="round">' + ''.join(rv) + '</g>')
    land = [c for c in range(len(X)) if not ocean[c]]
    peak = max(land, key=m['F'].__getitem__)
    mouth = max((c for c in land if rcv[c] >= 0 and ocean[rcv[c]]), key=acc.__getitem__)
    lab = '<text x="%.1f" y="%.1f" font-family="Georgia,serif" font-size="%d" fill="#222" stroke="#fff" stroke-width="3" paint-order="stroke" text-anchor="middle">%s</text>'
    out += [lab % (X[peak], Y[peak]-8, 16, 'Mount Prime'), lab % (X[mouth], Y[mouth]+18, 14, 'River Mouth'), lab % (500, 40, 24, 'Prototype Land')]
    out.append('</svg>')
    s = '\n'.join(out).encode()
    with open(path, 'wb') as fh: fh.write(s)
    return dict(render_s=round(time.perf_counter()-t0, 3), raster_hillshade_s=round(t_hs, 3), svg_bytes=len(s), png_b64_bytes=len(b64), coast_segs=len(segs))

def zoom(m, seed, frac=0.25):
    t0 = time.perf_counter()
    X, Y, H, nx, ny, sp = m['X'], m['Y'], m['H'], m['nx'], m['ny'], m['sp']
    segs = coast_segments(m); best = None
    for wy in range(4):
        for wx in range(4):
            x0 = wx*WORLD*frac; y0 = wy*WORLD*frac
            k = sum(1 for a, b in segs if x0 <= a[0] < x0+WORLD*frac and y0 <= a[1] < y0+WORLD*frac)
            if best is None or k > best[0]: best = (k, x0, y0)
    _, x0, y0 = best; x1 = x0+WORLD*frac; y1 = y0+WORLD*frac
    CX, CY, cnx, cny, cnb, ctris = build_mesh(seed, x0, y0, x1, y1, sp/2)
    CH = []; amp = 0.03
    for c in range(len(CX)):
        wx, wy = CX[c], CY[c]
        gi = round(wx/sp); gj = round(wy/sp); cand = []
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                i = gi+di; j = gj+dj
                if 0 <= i < nx and 0 <= j < ny:
                    p = j*nx+i; cand.append(((X[p]-wx)**2+(Y[p]-wy)**2, p))
        cand.sort(); s = 0.0; ws = 0.0
        for d, p in cand[:3]:
            w = 1.0/(d+1e-9); s += w*H[p]; ws += w
        CH.append(s/ws + amp*fbm(seed+900, wx, wy, 0.05, 3))
    csegs = coast_segments(dict(X=CX, Y=CY, H=CH, tris=ctris))
    grid = {}
    for a, b in segs:
        grid.setdefault((int(a[0]//sp), int(a[1]//sp)), []).append((a, b))
    def dseg(px, py, a, b):
        ax, ay = a; bx, by = b; vx, vy = bx-ax, by-ay; L = vx*vx+vy*vy or 1e-12
        t = max(0.0, min(1.0, ((px-ax)*vx+(py-ay)*vy)/L)); return math.hypot(px-ax-t*vx, py-ay-t*vy)
    ds = []
    for a, b in csegs:
        px, py = (a[0]+b[0])/2, (a[1]+b[1])/2; gi, gj = int(px//sp), int(py//sp); bd = 1e18
        for r in range(8):
            for dj in range(-r, r+1):
                for di in range(-r, r+1):
                    if max(abs(di), abs(dj)) != r: continue
                    for s in grid.get((gi+di, gj+dj), ()):
                        bd = min(bd, dseg(px, py, s[0], s[1]))
            if bd < (r-1)*sp: break
        ds.append(bd/sp)
    ds.sort()
    return dict(child_cells=len(CX), child_spacing=sp/2, window=[x0, y0, x1, y1], child_coast_segs=len(csegs),
                dev_mean_parent_sp=round(sum(ds)/len(ds), 3), dev_p95=round(ds[int(0.95*len(ds))], 3), dev_max=round(ds[-1], 3),
                frac_within_1_parent_sp=round(sum(1 for d in ds if d <= 1.0)/len(ds), 4), zoom_s=round(time.perf_counter()-t0, 3))

if __name__ == '__main__':
    N = int(sys.argv[1]); seed = int(sys.argv[2]); out = sys.argv[3]
    m = generate(N, seed); ck = check(m); dg = digest(m)
    r = render(m, out); z = zoom(m, seed)
    with open(out, 'rb') as fh: svg_sha = hashlib.sha256(fh.read()).hexdigest()
    print(json.dumps(dict(N=len(m['X']), t={k: round(v, 3) for k, v in m['t'].items()}, check=ck, digest=dg,
                          svg_sha=svg_sha, render=r, zoom=z), indent=1))
