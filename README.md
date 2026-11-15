# mapwright

![mapwright: a generated world painted as an atlas](.github/images/banner.jpg)

An agent plugin for maps of real places, fantasy worlds and science fiction settings. It reads, writes, finds and generates maps, and checks its own numbers against published values.

mapwright is a skill for AI coding agents plus one small script, `mpw.py`, that needs nothing but Python's standard library.

## What works in 0.1.0

- **Inspect** a map file: GeoJSON, GPX, KML and KMZ, shapefiles, dBASE, PNG heightmaps with world files, GeoPackage and MBTiles. Feature counts, extent, properties and the CRS when the file states one.
- **Convert** between GeoJSON, GPX and KML, and read shapefiles into GeoJSON. Ring order is fixed on the way (shapefiles clockwise, GeoJSON counter-clockwise).
- **Measure** geodesic distance and bearing on the WGS84, GRS80 or Clarke 1866 ellipsoid, polygon area on the ellipsoid, and map scale conversions.
- **Project** points forward and back: Web Mercator, equirectangular, Mollweide, Lambert azimuthal equal-area, Robinson and Equal Earth.
- **Explain** projections, symbols and methods in plain words.
- **Generate** invented worlds (0.2.0, unreleased): plates, erosion, rivers, lakes, climate and biomes; settlements ranked city, town and village; roads by least-cost paths; place names from a sound pattern. Child maps (zoom) keep the parent's coast, rivers, settlements, roads and names. `check` runs 13 proof bars.

- **Render** a recipe folder to SVG, PNG or PDF in six looks (topographic, atlas, satellite, ink-and-parchment, blueprint, star-chart) with labels that never overlap, a legend of what is on the map, a scale bar and a north arrow; serve it as a pan and zoom page on 127.0.0.1; set styles or seeds side by side on one sheet.

Labels on curves and fetching open data come next.

## Use

```
python scripts/mpw.py doctor
python scripts/mpw.py inspect hike.gpx
python scripts/mpw.py convert hike.gpx hike.geojson
python scripts/mpw.py measure distance -41.32 174.81 40.96 -5.50
python scripts/mpw.py project mollweide 100 45
python scripts/mpw.py explain web-mercator
python scripts/mpw.py gen world --seed 7 --style nordic --out isles.map
python scripts/mpw.py zoom isles.map --out isles-south.map
python scripts/mpw.py check isles-south.map
python scripts/mpw.py names --sample 10 --style desert
python scripts/mpw.py names --list
python scripts/mpw.py render isles.map -o isles.png --style ink-and-parchment
python scripts/mpw.py label isles.map
python scripts/mpw.py legend isles.map --style atlas
python scripts/mpw.py style --list
python scripts/mpw.py serve isles.map
python scripts/mpw.py sheet isles.map --styles atlas,blueprint,star-chart -o pick.png
```

## Tests

`python -m unittest discover -s tests`. Distances match Geoscience Australia's Vincenty example and GeographicLib's documented values to a millimetre.

## Licence

MIT. See [LICENSE](LICENSE). Security reports: [SECURITY.md](SECURITY.md).
