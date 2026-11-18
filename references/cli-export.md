# mapwright CLI: export to engines, tabletop, 3D and print

`MPW` means `python scripts/mpw.py` from the plugin root. Loaded on demand from skills/mapwright/SKILL.md.

## Export: games, tabletop, 3D and print

`MPW export DIR -o FILE [--to TARGET]` writes the file, reads it back and prints its proof bars (exit 1 when one fails). The extension picks the target; a .png needs `--to`.

Since 0.27.0 `export DIR --to player -o FOLDER` (dungeons): a handout copy with secret doors walled, the floor reached only through them filled, and secret and treasure marks dropped. Its bar fails if any of those remain. The copy is not a recipe: `check --no-regen` on it skips the lock and key bars.

| Recipe | Command | Gives |
|---|---|---|
| world, region | `-o t.raw [--size 1025] [--flip]` | Unity RAW: 16 bit, little-endian, square, 2^n + 1 |
| world, region | `--to unreal -o t.png [--size 1009]` | 16-bit PNG at an Unreal landscape size |
| world, region | `-o t.r16`, or `--to godot -o t.png` | R16 for Terrain3D, or a 16-bit PNG |
| world, region | `--to roblox -o t.png [--size N] [--bits 16]` | heightmap (4096 px at most) and `t.colormap.png` in Roblox material colours |
| world, region | `-o t.obj [--size 257] [--exaggeration Z] [--base T] [--print-mm 100] [--flat-sea]`, or `--to mesh -o FOLDER` | terrain mesh and a polywright manifest; with a base it is one watertight solid |
| dungeon, square battle, deck | `-o map.tmj [--tile 32] [--encoding base64] [--csv]` | Tiled map, flat-colour tileset PNG, walls and doors as object layers, one tile layer per deck |
| dungeon, square battle, deck | `-o map.dd2vtt [--deck N] [--pps 50]` | Universal VTT (walls, doors as closed portals, lights, the PNG in base64); one file per deck |
| dungeon, square battle | `--nav -o map.nav.json` (0.11.0) | Navigation hand-over: walkable squares merged into rectangles, doors kept separate with lock and one-way info, a portal list; `--agent N` (0.19.0) erodes the walkable set for a body N squares wide, top-left anchor ([games-film-print.md](games-film-print.md) 4.1) |
| battle, dungeon | `--to png -o map.png` | the grid picture; the only raster export for a hex map |
| planet, sector | `-o p.png`, `-o s.tab` | sphere texture with `p.sphere.json`; T5 tab file |
| any | `--to print -o NAME[.pdf or .png] [--paper A4] [--landscape] [--dpi 300] [--bleed 3] [--fit cover]` | PDF and PNG at the paper size plus bleed, crop marks in the bleed |

- Heightmaps stretch the lowest to the highest height over the whole range. `t.import.json` beside the file gives metres per pixel, min and max height in metres and the numbers to type into the engine. A 1000 km world is past Unity's 100 km limit; the sidecar's `fit` block gives the even shrink.
- Not verified in the engines: which way Unity reads RAW rows (swapped north and south: `--flip`), the Roblox colour table and 8-bit default, Terrain3D's field names. Say so when handing the files over.
- Hex battle maps have no Universal VTT (the format has one square `pixels_per_grid`) and no Tiled export yet.
- The mesh is OBJ with x east, y north, z up, real metres unless `--print-mm`. Foundry reads the .dd2vtt through the Universal Battlemap Importer; its own scene JSON is not written.
- Print needs Chrome or Edge and stops with the reason when neither is found. Paper is A0 to A5, Letter, Legal, Tabloid or `WxH` in mm. Colour is RGB and the PDF sets MediaBox, BleedBox and TrimBox but is not PDF/X: say so before it goes to a press.
