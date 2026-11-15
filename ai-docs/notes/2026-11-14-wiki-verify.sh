#!/bin/sh
# Runs every example on the mapwright wiki in a scratch copy of the repo and prints each output.
# Usage: sh ai-docs/notes/2026-11-14-wiki-verify.sh > out.txt   (from the repository root)
set -e
REPO=$(pwd)
W=$(mktemp -d)
cp -r "$REPO/scripts" "$W/scripts"; mkdir -p "$W/tests"; cp -r "$REPO/tests/fixtures" "$W/tests/fixtures"
cd "$W"
run() { echo "=== $*"; "$@" 2>&1 || echo "[exit $?]"; }
M="python scripts/mpw.py"
run $M --version
run $M doctor
run $M explain list
run $M explain web-mercator
run $M explain no-such-term
run $M inspect tests/fixtures/track.gpx
run $M inspect tests/fixtures/heights.png
run $M inspect tests/fixtures/square.geojson --json
run $M convert tests/fixtures/track.gpx track.geojson
run $M convert tests/fixtures/route.geojson route.kml
run $M inspect route.kml
run $M measure distance -41.32 174.81 40.96 -5.50
run $M measure distance -37.95103342 144.42486789 -37.65282114 143.92649553 --ellipsoid GRS80
run $M measure area tests/fixtures/square.geojson
run $M measure scale 1:50000 --map 2cm
run $M measure scale 1:25000 --ground 3km
run $M project --list
run $M project mollweide 100 45
run $M project webmercator 174.78 -41.29
run $M project webmercator 19456639.5 -5057944.4 --inverse
run $M gen world --seed 7 --style nordic --out isles.map
run $M gen world --seed 7 --style nordic --out isles2.map
run cmp isles.map/features.geojson isles2.map/features.geojson
run $M zoom isles.map --out isles-south.map
run $M gen region --parent isles.map --window 100,100,400,350 --cells 8000 --out isles-west.map
run $M check isles-south.map
run $M names --list
run $M names --sample 6 --style desert --seed 3
run $M names --sample 4 --pattern 'C=k t r s;V=a o i;F=n r;S=CV CVF;N=2-3' --seed 1
run $M style --list
run $M style ink-and-parchment
run $M render isles.map -o isles.svg --style atlas
run $M render isles.map -o isles.png --style ink-and-parchment
run $M render isles.map -o isles.pdf --style blueprint --title "The Isles"
run $M label isles.map
run $M legend isles.map --style atlas
run $M legend isles.map --style topographic -o legend.svg
run $M sheet isles.map --styles atlas,blueprint,star-chart -o pick.png
run $M sheet isles.map --seeds 1,2,3,4 --cols 2 -o seeds.svg
echo "=== serve"
python scripts/mpw.py serve isles.map --port 8765 > serve.log 2>&1 &
P=$!; sleep 3
curl -s -o /dev/null -w "GET / -> %{http_code}\n" http://127.0.0.1:8765/ || true
kill $P; sleep 1; head -3 serve.log
cd /; rm -rf "$W"
