"""Optional numpy comparison for the vectorisable stages (jitter, plates+uplift
with value-noise fbm, 512^2 Horn hillshade). Priority-Flood and accumulation stay
serial (heap / topological order) so numpy does not apply to them."""
import sys, time, math
import numpy as np

def h(seed, a, b, c=0):
    x = (np.uint64(0x9E3779B97F4A7C15) ^ np.uint64(seed)) * np.uint64(0xBF58476D1CE4E5B9)
    for v in (a, b, c):
        x = (x ^ v.astype(np.uint64) if hasattr(v, 'astype') else x ^ np.uint64(v)) * np.uint64(0x94D049BB133111EB)
        x ^= x >> np.uint64(29)
    return (x >> np.uint64(11)).astype(np.float64) / float(1 << 53)

def vnoise(seed, x, y, f):
    x = x*f; y = y*f; ix = np.floor(x); iy = np.floor(y); fx = x-ix; fy = y-iy
    fx = fx*fx*(3-2*fx); fy = fy*fy*(3-2*fy); ix = ix.astype(np.int64); iy = iy.astype(np.int64)
    a = h(seed, ix, iy); b = h(seed, ix+1, iy); c = h(seed, ix, iy+1); d = h(seed, ix+1, iy+1)
    top = a+(b-a)*fx; bot = c+(d-c)*fx
    return top+(bot-top)*fy

def fbm(seed, x, y, f, o=4):
    s = 0; a = 1.0; t = 0
    for k in range(o):
        s = s + a*vnoise(seed+k, x, y, f); t += a; a *= .5; f *= 2
    return s/t - .5

with np.errstate(over='ignore'):
    for N in (10000, 65536):
        side = int(math.sqrt(N)); sp = 1000/side; seed = 7
        t0 = time.perf_counter()
        gj, gi = np.mgrid[0:side, 0:side]
        X = (gi + (h(seed, gi, gj, 1)-.5)*.8)*sp; Y = (gj + (h(seed, gi, gj, 2)-.5)*.8)*sp
        t1 = time.perf_counter()
        rng = np.random.default_rng(seed); P = rng.random((14, 2))*1000
        xx = X + 60*fbm(57, X, Y, .004); yy = Y + 60*fbm(67, X, Y, .004)
        d = np.sqrt((xx[..., None]-P[:, 0])**2 + (yy[..., None]-P[:, 1])**2)
        ds = np.sort(d, axis=-1); pl = d.argmin(-1)
        H = np.where(pl % 3 == 0, .35, -.45) + np.exp(-(ds[..., 1]-ds[..., 0])/40) + .55*fbm(77, X, Y, .006, 5)
        t2 = time.perf_counter()
        print('N=%d jitter %.3fs plates+uplift %.3fs' % (N, t1-t0, t2-t1))
    Z = np.random.default_rng(1).random((512, 512)).cumsum(0).cumsum(1)/1e3
    t0 = time.perf_counter()
    p = np.pad(Z, 1, mode='edge')
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]; dd, f = p[1:-1, :-2], p[1:-1, 2:]; g, hh, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((c+2*f+i)-(a+2*dd+g))/8; dzdy = ((g+2*hh+i)-(a+2*b+c))/8
    sl = np.arctan(np.hypot(dzdx, dzdy)); asp = np.arctan2(dzdy, -dzdx); zen = math.radians(45); az = math.radians(135)
    hs = np.clip(255*(math.cos(zen)*np.cos(sl)+math.sin(zen)*np.sin(sl)*np.cos(az-asp)), 0, 255).astype(np.uint8)
    print('hillshade 512^2 %.4fs' % (time.perf_counter()-t0))
