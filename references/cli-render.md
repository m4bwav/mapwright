# mapwright CLI: render and AI style pass

`MPW` means `python scripts/mpw.py` from the plugin root. Loaded on demand from skills/mapwright/SKILL.md.

## Render: print maps and pages

- `MPW render DIR -o out.svg|png|pdf [--style S] [--font F.ttf] [--title T]`: the map from the recipe folder's files alone. Same folder and style give byte-identical SVG. PNG and PDF need Chrome or Edge (headless); without one, write .svg. About 0.7 s at 16k cells, 1.1 s at 65k (raster dominates); SVG 110-460 KB by style.
- `MPW label DIR [--json]`: placed and dropped labels, and the label bars. Labels never overlap and never touch the edge; a label with no free spot is dropped and listed, never squeezed in.
- `MPW legend DIR [--style S] [-o legend.svg]`: only the symbols on this map (biomes or height bands present, roads and settlement ranks present).
- `MPW style --list`, `MPW style NAME`: topographic, atlas, satellite, ink-and-parchment, blueprint, star-chart (palette and star field only, no catalogue stars yet).
- `MPW serve DIR [--port 8765]`: pan and zoom page on 127.0.0.1 only. Never bind it to 0.0.0.0.
- `MPW sheet DIR [--styles a,b] [--seeds 1,2] [--cols N] -o pick.png`: variations side by side for a pick; send the pick to artwright-judge, then Mark on an askwright page.
- `MPW check DIR` also runs the label bars (overlap, edge cut, OCR read-back). The OCR bar shows SKIP with the reason when tesseract is not installed; that is not a pass. `--no-labels` skips them.

### AI style pass (optional)

- `MPW aistyle DIR --look painted-atlas|ink-and-parchment|satellite|watercolour [--denoise 0.45] [--seed N] [--host URL] [-o out.png|svg|pdf]` repaints a world or region map on a ComfyUI server and keeps the geography. The picture sent is the render without roads, symbols or text. The model repaints it (img2img; Z-Image Turbo, Apache 2.0, unless you swap it). Lakes, rivers, roads, symbols, labels, legend, scale bar and north arrow are then set in code on top, line for line as `render` sets them, so the label bars hold as they do there. The model never draws text; never accept text it painted.
- The server comes from `--host` or the `MAPWRIGHT_COMFYUI` environment variable. There is no default address and none is written to any file. `--dry-run` writes the control PNG and the workflow JSON and contacts nothing. `MPW doctor [--host URL]` says whether the server answers and holds the model files. `--workflow FILE`, `--model`, `--clip` and `--vae` swap the model; the licence class then reads "unstated" until you have read its card. No Meta-gated models.
- Every pass is measured against the recipe, and the command exits non-zero when it fails: land IoU 0.92 or more against the recipe's own land mask, code-set rivers (0.98) and settlements (0.94) on painted land. Keep `--denoise` at 0.45 or below: 36 of 36 measured pictures passed there, 11 of 24 at 0.55, none of 12 at 0.65 ([TESTS.md](../TESTS.md), T-20261115-5). Inside the bar the look is a light repaint; the heavy painted look costs the coast. On a failure change the seed or lower the denoise, never the bar. The typed denoise runs on a step grid (0.55 runs as 0.5625); the sidecar records both.
- Beside the picture: `NAME.aistyle.json` (model and licence class, look, prompt, seed, denoise, steps, workflow hash, tool version, the measured numbers, any settlement left off painted land), the control picture, the raw styled picture and the workflow. `MPW check DIR` adds one bar for each sidecar in the recipe folder (`--no-aistyle` skips them). `MPW aistyle DIR --measure picture.png` measures a picture you already have.

There are no ferries yet: islands get their own road networks. Cities and dungeons: [references/cities-and-dungeons.md](cities-and-dungeons.md). AI image models for a styled look: [references/ai-image-models.md](ai-image-models.md). Games, film and print exports: [references/games-film-print.md](games-film-print.md).
