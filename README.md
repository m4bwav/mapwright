# mapwright

<!-- Banner owed: .github/images/banner.jpg (1536x640), made once the renderer can draw a map. -->

An agent plugin for maps of real places, fantasy worlds and science fiction settings. It reads, writes, finds and generates maps, and checks its own numbers against published values.

mapwright is a skill for AI coding agents plus one small script, `mpw.py`, that needs nothing but Python's standard library.

## What works in 0.1.0

- **Inspect** a map file: GeoJSON, GPX, KML and KMZ, shapefiles, dBASE, PNG heightmaps with world files, GeoPackage and MBTiles. Feature counts, extent, properties and the CRS when the file states one.
- **Convert** between GeoJSON, GPX and KML, and read shapefiles into GeoJSON. Ring order is fixed on the way (shapefiles clockwise, GeoJSON counter-clockwise).
- **Measure** geodesic distance and bearing on the WGS84, GRS80 or Clarke 1866 ellipsoid, polygon area on the ellipsoid, and map scale conversions.
- **Project** points forward and back: Web Mercator, equirectangular, Mollweide, Lambert azimuthal equal-area, Robinson and Equal Earth.
- **Explain** projections, symbols and methods in plain words.

Generating worlds, rendering, labels and fetching open data come next.

## Use

```
python scripts/mpw.py doctor
python scripts/mpw.py inspect hike.gpx
python scripts/mpw.py convert hike.gpx hike.geojson
python scripts/mpw.py measure distance -41.32 174.81 40.96 -5.50
python scripts/mpw.py project mollweide 100 45
python scripts/mpw.py explain web-mercator
```

## Tests

`python -m unittest discover -s tests`. Distances match Geoscience Australia's Vincenty example and GeographicLib's documented values to a millimetre.

## Licence

MIT. See [LICENSE](LICENSE). Security reports: [SECURITY.md](SECURITY.md).
