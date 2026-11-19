"""Spherical geometry helpers on the unit sphere. Standard library only.

Points are unit vectors (x, y, z). Polygons are lists of points, edges are
the shorter great-circle arcs between neighbours. See references/projections.md 3.13.
"""
import math

EPS = 1e-12


def unit(lon, lat):
    """Unit vector from longitude and latitude in degrees."""
    lo, la = math.radians(lon), math.radians(lat)
    c = math.cos(la)
    return (c * math.cos(lo), c * math.sin(lo), math.sin(la))


def lonlat(v):
    """Longitude and latitude in degrees from any non-zero vector."""
    x, y, z = v
    return (math.degrees(math.atan2(y, x)), math.degrees(math.atan2(z, math.hypot(x, y))))


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(v):
    n = math.sqrt(dot(v, v))
    if n < EPS:
        raise ValueError("zero vector")
    return (v[0] / n, v[1] / n, v[2] / n)


def frame(centre):
    """Centre c plus east and north tangent axes for a gnomonic plane."""
    c = norm(centre)
    e = cross((0.0, 0.0, 1.0), c)
    if math.sqrt(dot(e, e)) < 1e-9:  # centre at a pole
        e = (0.0, 1.0, 0.0)
    e = norm(e)
    return c, e, cross(c, e)


def gnomonic(p, fr):
    """Plane (x, y) of point p, or None on or past the centre's horizon."""
    c, e, n = fr
    t = dot(p, c)
    if t <= 1e-9:
        return None
    return (dot(p, e) / t, dot(p, n) / t)


def _pip_plane(x, y, ring):
    inside = False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def contains(poly, p):
    """Point p inside a spherical polygon smaller than a hemisphere.

    Projects gnomonically about the vertex mean: great-circle edges become
    straight lines there, so a plane ray test is exact.
    """
    fr = frame(tuple(sum(v[i] for v in poly) for i in range(3)))
    ring = [gnomonic(v, fr) for v in poly]
    if any(r is None for r in ring):
        raise ValueError("polygon must fit inside one hemisphere")
    q = gnomonic(p, fr)
    return q is not None and _pip_plane(q[0], q[1], ring)


def _on_arc(s, a, b):
    n = cross(a, b)
    return dot(cross(a, s), n) >= -EPS and dot(cross(s, b), n) >= -EPS


def arc_intersection(a, b, p, q):
    """Crossing point of great-circle arcs a-b and p-q, or None."""
    try:
        x = norm(cross(cross(a, b), cross(p, q)))
    except ValueError:
        return None  # same or parallel great circles
    for s in (x, (-x[0], -x[1], -x[2])):
        if _on_arc(s, a, b) and _on_arc(s, p, q):
            return s
    return None


def rim_angle(x, y):
    """Direction for a far-side marker pinned to an orthographic disc's rim."""
    return math.atan2(y, x)


def small_circle(r, radius):
    """Angular radius (rad) and circumference of a range circle of ground radius r.

    Returns None past pi*radius, where the circle has closed on the antipode.
    """
    a = r / radius
    if a < 0 or a > math.pi:
        return None
    return a, 2 * math.pi * radius * math.sin(a)
