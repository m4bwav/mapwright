# aistyle: what was measured and decided (2026-11-15, 0.8.0)

Handoff note for `mpw.py aistyle`. Numbers and the full table are in [../../TESTS.md](../../TESTS.md) (T-20261115-5); lessons are L-028 to L-032 in [../../LEARNINGS.md](../../LEARNINGS.md); the model notes are in [../../references/ai-image-models.md](../../references/ai-image-models.md) (section 3.1).

## The route as built

1. `render_parts` splits the map's SVG lines into head, ground (sea, land raster), water (lakes, rivers), coast and over (roads, dots, labels, title, legend, scale bar, north arrow, frame).
2. Control picture: head + ground + water + coast, drawn by headless Chrome or Edge at the model's size (long side 1024, both sides multiples of 16). No text, no symbols.
3. The pass: upload, queue, poll, download over ComfyUI's HTTP API with urllib. The workflow is `scripts/data/aistyle-zimage-turbo.json`; slots in braces are filled per run.
4. Composite: the styled PNG as one `<image>`, then water + over on top. The SVG is drawn at the model's pixel size with the map's own viewBox, so the styled pixels are not resampled.
5. Measure the raw styled picture against the recipe, write the sidecar, exit non-zero on a failed bar.

## Rulings made during the build (small, flagged for review)

- Lakes and rivers are set in code after the pass, not left to the model, and are left out of the land IoU. Reason: the model kept about half the river lines at denoise 0.45 and often painted lakes over. The coast line itself is not redrawn: the painted coast is what the bar measures, and a second crisp line a few pixels off would look doubled.
- Roads and settlement dots are in the code-set layer too. A label beside a dot the model smeared would be wrong.
- No default server address. ComfyUI's stock port is 8188, but a host can run it elsewhere, so `--host` or `MAPWRIGHT_COMFYUI` is required. The address is never written to the sidecar or any other file.
- The bar is on the outcome, not on the denoise. Denoise above 0.45 only prints a warning; the measurement decides.
- The legend and labels keep the code style's colours. Inside the bar the repaint is light, so they still match.
- Samples for review are kept outside the repository (package size).

## Open

- Done 2026-11-16: `--control canny|depth [--strength S]` adds a Z-Image Fun ControlNet union hint drawn from the recipe (workflow `scripts/data/aistyle-zimage-cnet.json`). Canny at 0.9 holds the bar to denoise 0.75 on every measured picture (8/8), against 0.45 without control; depth holds less; 0.90 slips. T-20261116-24, L-061 `canny-from-geometry-doubles-the-denoise`. Still open: whether a look at 0.75 reads as clearly stronger to Mark (no review yet), canny plus depth together, and region recipes.
- A river-survival bar on the model's own picture was dropped: the line test has a noise floor of up to 0.26 on textured looks, and the model fails it anyway.
- Non-square maps are sent slightly stretched (up to 0.8 percent) to reach a multiple of 16 and stretched back in the composite; measured only on square worlds.
- OCR text-leak check on the styled picture (tesseract) is not built; tesseract is not installed on the build machine.
- Region (child) recipes run through the same code; only worlds were measured.
- Only Z-Image Turbo was measured. Other models go through `--workflow` and carry an "unstated" licence class until their card is read.

## Rerun

`python tests/aistyle_grid.py WORLD OUTDIR` with a server in `MAPWRIGHT_COMFYUI` reruns the grid and prints the table; `--measure-only` re-measures pictures already made. `MAPWRIGHT_LIVE=1 python -m unittest tests.test_aistyle` runs one real pass.
