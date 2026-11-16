# Step E: one example map per kind (2026-11-15)

Lab folder (outside the repo): `D:/m4bwa/Claude/Projects/Ai/mapwright-lab/step-e/`. Decision page: set `ask/mapwright-step-e-1` (one keep/redo question per kind). Tool version 0.10.0 for the gens, renders after the 0.10.1 fixes.

## Commands and seeds (run from the repo root, `M="python scripts/mpw.py"`, `L=<lab>/step-e`)

| Kind | Commands | Showcase files |
| --- | --- | --- |
| life-like | `$M gen world --seed 4242 --out $L/life-like/world`; `$M gen region --parent $L/life-like/world --out $L/life-like/region` (default coast-richest window); `$M render $L/life-like/region -o $L/life-like/region-life-like.png --style topographic --title "Belisa coast (studyquest overworld)"`; world `--style atlas` | `life-like/region-life-like.{png,svg}`, `life-like/world-life-like.{png,svg}` |
| fantasy | `$M gen dungeon --seed 77 --method cyclic --style ink-and-parchment --out $L/fantasy/dungeon`; `$M gen battle --seed 31 --style ink-and-parchment --out $L/fantasy/battle`; render each with `--style ink-and-parchment --title "The Sunken Vault"` / `"Ruined Watchpost"`; `$M path $L/fantasy/dungeon --from 38,10 --to 25,23 --out $L/fantasy/dungeon-path` (27 steps, cost 27.41) | `fantasy/dungeon-fantasy.{png,svg}`, `fantasy/battle-fantasy.{png,svg}`, `fantasy/dungeon-path/path.svg` |
| sci-fi | `$M gen sector --seed 2077 --size subsector --out $L/sci-fi/sector`; `$M gen system --seed 2077 --star G --out $L/sci-fi/system`; render each `--style star-chart` | `sci-fi/sector-sci-fi.{png,svg}`, `sci-fi/system-sci-fi.{png,svg}` |

Timings: all six gens 3 s together; each world/region render about 0.6 to 0.7 s; checks a few seconds each. aistyle not run (optional).

## Check results (`mpw.py check DIR`, final)

| Recipe | Pass | Fail | Skip |
| --- | --- | --- | --- |
| life-like/world | 15 | 0 | 1 (OCR, no tesseract) |
| life-like/region | 15 | 0 | 1 (OCR) |
| fantasy/dungeon | 20 | 0 | 1 (OCR) |
| fantasy/battle | 12 | 0 | 1 (OCR) |
| sci-fi/sector | 7 | 0 | 1 (OCR) |
| sci-fi/system | 9 | 0 | 2 (OCR x2) |

Highlights: world 60 settlements, 63 roads, 124 unique names, rain shadow 352 vs 36 cm/yr; region coast within 0.53 parent spacings; dungeon 16/16 rooms, key before lock, goal sealed with the lock shut; sector 42 worlds, 58 routes, one component, 8 bridges; system closest pair 12.7 mutual Hill radii.

## Found and fixed / recorded

- L-039 `render-into-recipe-folder-breaks-determinism`: rendering into the recipe folder failed the byte-identical bar. Space check fixed (extras ignored), test added. Keep showcase renders outside or under other names.
- L-040 `grid-map-title-ignored`: `render --title` ignored on city/dungeon/battle. Fixed, test added; space maps warn.
- L-041 `system-hz-legend-undrawn`: schematic system legend names a green zone it does not draw. Open.
- Judged by eye, open: battle map seed 31 is sparse (two ruins, a few rocks and trees, no torch visible) and has no legend; dungeon labels (title, room numbers) sit close to walls; `path` treats the lock as open (by design, L-034 era ruling), so the 27-step route skips the key.
