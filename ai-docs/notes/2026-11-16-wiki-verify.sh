#!/bin/sh
# Runs every example on the mapwright wiki in a scratch copy of the tagged release and prints each output.
# Usage: sh ai-docs/notes/2026-11-16-wiki-verify.sh [TAG] > out.txt   (from the repository root; TAG defaults to v0.11.0)
# mapwright is not on a registry: the scripts/ and tests/fixtures/ of the tag are copied out with git archive.
# Network commands (find --online, fetch) are not run; their page examples carry an outputs: skip marker.
set -e
export PYTHONIOENCODING=utf-8
TAG=${1:-v0.11.0}
REPO=$(pwd)
W=$(mktemp -d)
git -C "$REPO" archive "$TAG" scripts tests/fixtures | tar -x -C "$W"
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
# --- read and trace (0.3.0)
run $M read tests/fixtures/heights.png
run $M read tests/fixtures/heights.png --gcp 0,0,500000,4200000 --gcp 16,0,500160,4200000 --gcp 0,12,500000,4199880 --units m
# --- worlds
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
run $M render isles.map -o isles-atlas.png --style atlas
run $M trace isles-atlas.png --class water --min-area 50 -o water.geojson
run $M inspect water.geojson
# --- places (0.5.0, 0.9.0)
run $M gen city --seed 4 --out town.map
run $M check town.map
run $M gen dungeon --seed 3 --method bsp --out crypt.map
run $M check crypt.map
run $M gen dungeon --seed 3 --method cave --out cave.map
run $M gen dungeon --seed 3 --method cyclic --out keep.map
run $M check keep.map --chokepoints
run $M check crypt.map --fair
run $M check --range bsp --seeds 20
run $M gen battle --seed 2 --grid square --out field.map
run $M gen battle --seed 2 --grid hex --out hexes.map
# --- 0.11.0
run $M gen battle --seed 2 --grid square --density sparse --out sparse.map
run $M gen battle --seed 2 --grid square --density dense --out dense.map
run python -c "import re;[print(m, re.findall('<text x=.2737[^>]*>([^<]*)', open(m+'/map.svg').read())) for m in ('sparse.map','field.map','dense.map')]"
run $M gen dungeon --seed 3 --method cyclic --branches 3 --out wings.map
run $M check wings.map
run $M render crypt.map -o crypt.svg --style blueprint --title "The Crypt"
# --- space (0.6.0)
run $M gen sector --seed 5 --out spin.map
run $M check spin.map
run $M gen sector --real --radius-pc 4 --out near.map
run $M gen system --seed 5 --star G --out sol2.map
run $M check sol2.map
run $M render sol2.map -o sol2-scale.svg --view scale
run $M gen planet --seed 5 --kind ocean --width 512 --out blue.map
run $M check blue.map
run $M gen deck --seed 5 --hull ship --decks 2 --out ship.map
run $M check ship.map
run ls town.map cave.map field.map spin.map sol2.map blue.map ship.map
run $M check tests/fixtures/dungeon-070-bsp
run $M check tests/fixtures/dungeon-070-cave
# --- export (0.7.0)
run $M export crypt.map -o crypt.dd2vtt
run $M export crypt.map -o crypt.tmj
run $M export ship.map --to uvtt -o ship.dd2vtt
run $M export hexes.map -o hexes.png
run $M export isles.map --to unity -o isles.raw
run $M export isles.map --to unreal -o isles-unreal.png
run $M export isles.map --to godot -o isles.r16
run $M export isles.map --to roblox -o isles-roblox.png
run $M export isles-west.map -o west.obj --print-mm 150
run $M export isles.map --to print -o isles-a4.pdf --bleed 3
run $M export blue.map --to sphere -o blue.png
run $M export spin.map -o spin.tab
# --- paths (0.10.0)
run $M path crypt.map --from 2,2 --to 30,20
run $M path crypt.map --from 2,2 --to 30,20 --moves 4
run $M path crypt.map --field --to 30,20
run ls crypt.map
run $M path ship.map --from 1,2,3 --to 2,19,10
run $M path keep.map --from 10,32 --to 17,17
run python -c "import json;d=json.load(open('keep.map/path.json'));print('locks', d['locks'], 'keys', d['keys'])"
run $M path keep.map --from 10,32 --to 17,17 --ignore-locks
run $M path crypt.map --from 2,2 --to 30,20 --jps
run $M path hexes.map --from 1,1 --to 10,8 --jps
run $M export crypt.map --nav -o crypt-nav.json
run python -c "import json;d=json.load(open('crypt-nav.json'));print(sorted(d)); print({k:len(v) for k,v in d.items() if isinstance(v,list)})"
run $M path isles.map --from 200,200 --to 400,300
run $M travel isles.map --from 200,200 --to 400,300 --mode walk
run $M travel isles.map --from 200,200 --to 400,300 --mode horse
# --- find (offline catalogue only) and aistyle (dry run only)
run $M find --list
run $M find "Iceland elevation"
run $M aistyle --list
run $M aistyle isles.map --look painted-atlas --dry-run
echo "=== serve"
python scripts/mpw.py serve isles.map --port 8765 > serve.log 2>&1 &
P=$!; sleep 3
curl -s -o /dev/null -w "GET / -> %{http_code}\n" http://127.0.0.1:8765/ || true
kill $P; sleep 1; head -3 serve.log
cd /; rm -rf "$W"
