# AI image models for the `aistyle` pass

What diffusion and edit models can and cannot do for maps, how to hold geometry with a control image, how to measure that it held, which models and LoRAs are safe to use and under what licence, and how to keep text out of the pass.

Researched 2026-11-14. Claims carry a source in brackets, keyed to the list at the end. Anything not checked against a primary source is marked (unverified). Licences change: re-read the model card before shipping anything sellable.

## 1. The design rule this file supports

mapwright draws geometry in code, renders it clean, sends that render through a style pass in local ComfyUI, then sets labels in code on top. The model never owns geometry or text. Every section below is about keeping that true.

House rules that apply:

- No Meta-gated models (for example SAM 3, Llama-licensed checkpoints). Use ungated equivalents.
- Krea 2 stays out of any project that may be sold. It may be used for private experiments only.
- Local ComfyUI is the only runtime the plugin assumes.

## 2. What generative models get wrong on maps

### 2.1 Text

Diffusion models trained before 2024 render text as letter-like shapes, not words. Place names come out garbled or invented [Kang2023] (unverified exact wording). Newer models (FLUX.1, Qwen-Image, Z-Image) render short prompted text much better; Qwen-Image's report puts text rendering as a headline feature, including Chinese [QwenImage]. That does not help a map: the model still chooses where the label goes, may misspell long names, and has no idea which feature a label belongs to. Labels set in code are exact, searchable, translatable and placed by rules. Keep them out of the pass.

### 2.2 Geography and physics

Image models learn what maps look like, not how terrain works. Known failure classes:

- Rivers that branch downstream, end in nowhere, or cross ridges (rivers flowing uphill). No published benchmark measures this directly that I found (unverified gap); it follows from the model having no elevation model.
- Coastlines that drift, islands that appear or vanish, roads that end, when the model is not held by a control image [Kang2023] (unverified detail).
- No scale and no projection. A generated "map" has no consistent scale bar, grid or north arrow that means anything; any scale bar drawn by the model is decoration.
- Invented features: the model adds towns, legends, compass roses and borders it was never asked for, because training maps had them.

Studies:

- Kang, Zhang and Roth, "The ethics of AI-generated maps: A study of DALLE 2 and implications for cartography" (2023) generated maps with DALL-E 2 and catalogued inaccuracy, fake features and the risk of misleading maps [Kang2023].
- Map-to-aerial translation work (pix2pix and MapGAN, section 6) is the closest thing to a benchmark: it scores how well generated images match ground truth, but on satellite tiles, not cartographic accuracy [pix2pix][MapGAN].
- I found no standard benchmark for "cartographic correctness" of diffusion output as of this date (unverified; worth a repeat search).

Conclusion: the model may only change surface appearance. Topology, positions, elevation logic and text all come from code.

## 3. The control route: holding coastlines

Three families, from loosest to tightest hold.

### 3.1 img2img with denoise strength

img2img starts sampling from a noised copy of the input. Denoise (strength) sets how much noise: low keeps structure, high allows the model to repaint. SDEdit formalised this trade-off between faithfulness and realism [SDEdit].

Working ranges (community practice, unverified as numbers; tune per model):

| Denoise | Effect on a clean map render |
|---|---|
| 0.15-0.30 | Texture and colour shift; coastlines intact; style weak |
| 0.35-0.55 | Usable style; small coast details start to move |
| 0.6+ | Geometry drifts; islands merge or vanish |

Measured for Z-Image Turbo (2026-11-15, `mpw.py aistyle`, 72 pictures, 4 looks, 2 worlds, 9 steps, cfg 1, 1024 px; [TESTS.md](../TESTS.md) T-20261115-5):

| Denoise typed (as run) | Land IoU against the recipe, min to max | Pictures passing the bar | What happens |
|---|---|---|---|
| 0.35 (0.36) | 0.9435 to 0.9810 | 12 of 12 | Light repaint; coast holds; about half the thin rivers already gone |
| 0.45 (0.45) | 0.9244 to 0.9736 | 24 of 24 | Light repaint; coast holds; ceiling |
| 0.55 (0.5625) | 0.8728 to 0.9547 | 11 of 24 | Bays fill, capes move, towns end up off the land |
| 0.65 (0.692) | 0.7301 to 0.8997 | 0 of 12 | The painted look arrives and the coast is redrawn |

Two things the measurement settled:

- Thin water does not survive at any useful denoise. The model alone kept 0.51 to 0.78 of river lines at 0.35 and 0.39 to 0.54 at 0.45, and lakes about as badly. `aistyle` therefore redraws lakes and rivers in code on top of the styled picture, with roads, symbols and labels.
- KSampler's denoise runs on a step grid: steps / int(steps / typed). At 9 steps, 0.55 runs as 0.5625 and 0.65 as 0.692.

img2img alone is not enough for a strong style: inside the bar it gives a light repaint. Pair it with a ControlNet, or use an edit model.

### 3.2 ControlNet

ControlNet adds a trainable copy of the encoder that takes a condition image (edges, depth, segmentation) and steers generation to match it [ControlNet]. For maps, mapwright can emit the condition image directly from its geometry, which is better than detecting edges from a render.

| Control | What mapwright feeds it | Holds | Notes |
|---|---|---|---|
| Canny | Coastline, river, road edges drawn as thin white lines on black | Edges exactly | Most common; hard edges can look traced |
| Lineart | Same lines, anti-aliased, varied width | Edges, softer | Suits hand-drawn and ink styles |
| Depth | Heightmap rendered as greyscale | Relief, mountains | Good for painted terrain; coastline only as a depth step |
| Segmentation | Flat colour per class (sea, land, forest, urban) | Regions | Tightest region hold; original SD1.5 seg used ADE20K colours [ControlNet] |
| Tile | Low-res copy of the render | Overall layout | Good for upscale passes (unverified for all bases) |

Availability per base model:

- SDXL: many ControlNets (canny, depth, lineart, union models such as xinsir's ControlNet-union-sdxl) (unverified exact repos; check licence per repo).
- FLUX.1: official BFL "FLUX.1 Canny/Depth [dev]" control models exist, under the FLUX dev non-commercial licence [FluxTools]; third-party union ControlNets exist (unverified licence per repo).
- Qwen-Image: InstantX Qwen-Image-ControlNet-Union, Apache 2.0, canny, soft edge, depth, pose; no segmentation (checked 2026-11-14, https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union).
- Z-Image: alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union, Apache 2.0, canny, HED, depth, pose, MLSD; no segmentation; a 2.0 version adds control blocks and inpaint (checked 2026-11-14, https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union). Neither Apache union ControlNet has a segmentation mode, so the seg route needs SDXL, or canny plus depth on the Apache bases.

Strength: start with ControlNet strength 0.8-1.0 and end percent near 1.0 when coastlines must hold; lower end percent lets the model add detail late (unverified numbers; community practice).

Stack two controls when needed: segmentation (regions) plus canny (coast edge). Both come from the same geometry, so they agree.

### 3.3 Instruction edit models

Edit models take an input image and a text instruction and change the image while keeping what the instruction does not mention.

- FLUX.1 Kontext [dev]: in-context image editing; BFL reports character and layout consistency across edits [Kontext]. Weights under the FLUX non-commercial licence [FluxDevLicence].
- Qwen-Image-Edit (and 2509, 2511): Apache 2.0, supports semantic and appearance editing, with appearance edits meant to keep untouched regions [QwenImage][InVideo2026]. The newest Qwen-Image 2.0 line is reported as API-only [InVideo2026]; The Decoder agrees (Alibaba Cloud API and Qwen Chat only, https://the-decoder.com/qwen-image-2-0-renders-ancient-chinese-calligraphy-and-powerpoint-slides-with-near-perfect-text-accuracy/). A secondary report says Qwen-Image 2.1 shipped open weights in Sept 2026 (unverified: no official Qwen or Hugging Face page checked).
- FLUX.2 [klein] 4B: Apache 2.0; the 9B is FLUX Non-Commercial [Klein]. BFL says klein unifies generation and editing: 4B does image-to-image editing and multi-reference, 9B single-reference editing (checked 2026-11-14, [Klein]); edit quality on maps is untested.
- Z-Image-Edit: announced; downloadable weights not confirmed [InVideo2026] (unverified).

Edit models are attractive because an "appearance edit" ("restyle as an old parchment map, keep every coastline") needs no control image. They still drift: small islands and thin rivers move or disappear (unverified for maps; consistent with general reports of edit drift). Always measure (section 4). A safe recipe: edit model at full strength, then reject the output if land IoU falls below the threshold, or composite the original edges back.

### 3.4 Recommended order for mapwright

1. Segmentation or canny ControlNet on an Apache-licensed base (Z-Image-Turbo or Qwen-Image) with img2img denoise 0.4-0.6.
2. Qwen-Image-Edit appearance edit as the alternative when no ControlNet exists for the chosen style.
3. FLUX dev, Kontext, Klein 9B only for non-commercial output.

## 4. Measuring geometry preservation

The pass is accepted only if geometry survived. mapwright knows the true land mask, so measurement is cheap.

### 4.1 Land-mask IoU

1. Before: rasterise the land polygons to a binary mask at output resolution (exact, from code).
2. After: classify each pixel of the styled image as land or sea. Options, cheapest first:
   - Colour threshold in a known style (sea is blue-ish): k-means with k=2 in Lab space, pick the cluster nearest the input sea colour.
   - Ask the model to keep a sea colour, then threshold.
   - A small segmenter; avoid SAM 3 (Meta-gated); SAM 2.1 is the house ungated default but SAM 2 is itself a Meta release under Apache 2.0, not gated (repo licence Apache-2.0, https://github.com/facebookresearch/sam2, checked 2026-11-16).
3. IoU = |A and B| / |A or B| (Jaccard index) [Jaccard].

Thresholds as built (set by testing, T-20261115-5): `aistyle` accepts at land IoU >= 0.92, with lakes and a 3 px river band left out of the mask because both are redrawn in code. The clean render itself scores 0.972 to 0.988 on this measure, so 0.97 was never reachable for a repainted picture. The classifier is a colour table trained on the picture's own pixels at least 12 px from the true coast; a fixed "sea is blue" rule fails on parchment looks.

IoU hides small losses: a vanished islet barely moves it. Add:

- Component count: number of connected land regions before and after (islands lost or gained).
- Per-component IoU for every island above a minimum area.

### 4.2 Edge overlap

- Extract the coastline as a 1 px line from the true mask; run Canny on the styled image.
- Boundary F-score: precision and recall of edge pixels within a tolerance of d pixels (e.g. 2-3 px), the measure used in the BSDS boundary benchmark [BSDS].
- Chamfer distance or Hausdorff distance between the true coastline and detected edges gives worst-case drift in pixels (Hausdorff is sensitive to outliers; report the 95th percentile instead).

### 4.3 Thin features

Rivers and roads: dilate the true line by tolerance d, then measure the fraction of the true line covered by dark or matching-colour pixels in the output (coverage). Report breaks: count gaps longer than k pixels.

As built: a bare "is there a contrasting line here" test fires on 22 to 33 percent of places with no river on a clean render (biome patches, hillshade). `aistyle` instead takes the centre-minus-sides colour vector from the clean render at each river sample and counts the river kept when the styled picture keeps a third of it within 3 px, and reports the same test's noise floor where the recipe has no line. The number is reported, not a bar: rivers are redrawn in code. The bars that remain are that code-set rivers (0.98) and settlements (0.94) have painted land within 3 px.

### 4.4 Text leakage

Run OCR (Tesseract, Apache 2.0) on the styled image before labels go on. Any confident word means the model painted text; reject or inpaint it out [Tesseract] (licence Apache-2.0, https://github.com/tesseract-ocr/tesseract, checked 2026-11-16).

## 5. Base models and licence classes

| Base | Licence | Commercial output | Notes |
|---|---|---|---|
| SDXL 1.0 | CreativeML OpenRAIL++-M | Yes, with use restrictions | [SDXL] |
| FLUX.1 [dev] | FLUX.1 [dev] Non-Commercial (renamed FLUX Non-Commercial) | Weights non-commercial; outputs: licence s.2(d): "You may use Output for any purpose (including for commercial purposes)", except to train, fine-tune or distill a competing model (checked 2026-11-14, https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md) | [FluxDevLicence][Klein] |
| FLUX.1 [schnell] | Apache 2.0 | Yes | [Schnell] |
| FLUX.1 Kontext [dev] | FLUX non-commercial | As dev | [Kontext] |
| FLUX.2 [klein] 4B | Apache 2.0 | Yes | [Klein] |
| FLUX.2 [klein] 9B | FLUX Non-Commercial | As dev | [Klein] |
| Qwen-Image, Qwen-Image-Edit (to 2511) | Apache 2.0 | Yes | [QwenImage][InVideo2026] |
| Z-Image-Turbo | Apache 2.0 | Yes | [ZImage][InVideo2026] |
| Krea 2 | House rule: never in sellable projects | Private only | Mark's rule |
| Meta-gated (SAM 3 etc.) | Gated | Not used | Mark's rule |

Default for mapwright: Z-Image-Turbo or Qwen-Image for generation, Qwen-Image-Edit for edits. Both Apache 2.0, both run locally, both fit 16 GB with quantisation (unverified for Qwen-Image at full precision; it is a 20B model [QwenImage]).

### 5.1 LoRA licence classes

A LoRA inherits the base model's licence terms on top of its own. A LoRA for FLUX dev is non-commercial as weights even if the uploader says "free to use".

Civitai shows per-model permission icons (commercial use of images, of the model, of generation services, merges, credit required) set by the uploader [CivitaiLicence]. Treat these as the uploader's claim, not proof of right: check the base licence and whether the training data looks scraped from a living artist or a commercial map maker.

Classes to record for every LoRA mapwright ships a preset for:

1. Base licence (from section 5).
2. Uploader permissions (Civitai icons or HF card licence field).
3. Training data note (own work, public domain, scraped).
4. Verdict: `ok-commercial`, `non-commercial`, `avoid`.

Map style LoRAs that exist (found 2026-11-14; uploader permissions not read, check before adding a preset):

- Mapcraft: The Ultimate TTRPG Mapmaker (Civitai 799901), SDXL and FLUX versions, trigger `mapcraft`, battle and world maps. The FLUX version carries FLUX dev non-commercial weight terms. https://civitai.com/models/799901
- Fantasy Map (Civitai 382959), SDXL 1.0, trigger `fantasy map`. https://civitai.com/models/382959
- OgMapTerrainPatch (Civitai 1113248), SDXL and FLUX, VTT terrain patches. https://civitai.com/models/1113248
- dnd-map-world (Hugging Face, Muapi). https://huggingface.co/Muapi/dnd-map-world
- No map LoRA for Z-Image or Qwen-Image was found; an Apache-base house LoRA is the open gap.
- More fantasy and parchment map LoRAs on Civitai (search "fantasy map", "old map", "D&D map").
- Isometric and game-map LoRAs.
- Satellite/aerial LoRAs for SDXL and FLUX.
- Watercolour and ink cartography LoRAs.

None were verified in this pass. Public-domain historical maps (Library of Congress, David Rumsey under CC BY-NC-SA, which is non-commercial) make clean training sets for a house LoRA; note David Rumsey's NC terms (unverified current terms).

## 6. Satellite and aerial looks

- pix2pix (Isola et al., 2017) trained conditional GANs on paired Google Maps tiles and aerial photos, both directions; map-to-aerial results were judged in an AMT "real vs fake" study where generated aerials fooled participants about 18.9% of the time (unverified figure) [pix2pix].
- CycleGAN did the same unpaired [CycleGAN].
- MapGAN (Li et al., 2020) generates web map tiles from remote sensing images with an added map-specific loss and reports gains over pix2pix and CycleGAN on its dataset [MapGAN] (unverified detail).
- For mapwright the direction is map-to-aerial. A modern route: segmentation ControlNet (water, forest, field, urban classes from geometry) plus an aerial LoRA, at moderate denoise. Expect plausible texture, not real places; buildings will be invented. Label the result as illustrative.
- Real imagery (Sentinel-2, CC BY-SA-like Copernicus terms; NAIP public domain in the US) beats generation when a real place is mapped (unverified licence detail per source).

## 7. Keeping text out of the pass

1. Never put labels in the input render. Render geometry only, labels after.
2. Negative prompt: "text, letters, words, labels, watermark, signature, legend, compass rose, scale bar". Helps, does not guarantee.
3. Reserve label areas: mapwright knows where labels will go. Make a mask of label boxes and either:
   - composite the clean render back into those boxes after the pass (no inpainting needed, cheapest), or
   - use a soft "calm" mask so the style there is flat (feather 4-8 px), giving labels a quiet ground (common cartographic halo practice).
4. Differential diffusion / inpaint masks in ComfyUI let the pass change only masked regions; use the inverse of the label mask (unverified node names per ComfyUI version).
5. After the pass, run the OCR check (4.4). Reject or composite on any hit.
6. Set labels with a real text engine (vector SVG or PIL with a licensed font), with halos for legibility.

## 8. Open questions

- The Apache union ControlNets for Z-Image and Qwen-Image have no segmentation mode (checked 2026-11-14); test canny plus depth as the region hold, or use SDXL seg.
- Do Qwen-Image-Edit appearance edits keep 1-2 px rivers? Needs IoU and coverage tests. Z-Image Turbo img2img does not (measured, section 3.1).
- A stronger look inside the coast bar: canny or depth from the geometry through the Z-Image Fun ControlNet union, at higher denoise. Not built or measured.
- Labels and the legend keep the code style's colours; after a heavy repaint the legend swatches may no longer match the picture. Not measured.
- Is SAM 2.1 acceptable under the Meta rule (Apache 2.0 but Meta-released)? Ask Mark, or avoid by thresholding.
- No benchmark for cartographic correctness found; repeat the search.

## Sources (accessed 2026-11-14)

- [BSDS] Arbelaez et al., "Contour Detection and Hierarchical Image Segmentation", TPAMI 2011. https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html
- [CivitaiLicence] Civitai model licence permissions. https://civitai.com/content/tos (unverified page for icons)
- [ControlNet] Zhang, Rao, Agrawala, "Adding Conditional Control to Text-to-Image Diffusion Models", 2023. https://arxiv.org/abs/2302.05543
- [CycleGAN] Zhu et al., "Unpaired Image-to-Image Translation using Cycle-Consistent Adversarial Networks", 2017. https://arxiv.org/abs/1703.10593
- [FluxDevLicence] FLUX.1 [dev] model card and licence. https://huggingface.co/black-forest-labs/FLUX.1-dev
- [FluxTools] BFL, FLUX.1 Tools (Canny, Depth, Fill, Redux). https://bfl.ai/announcements/24-11-21-tools
- [InVideo2026] "Open Source Image Models: The License Matrix Everyone Gets Wrong (August 2026)". https://invideo.io/blog/open-source-image-models-licenses/
- [Jaccard] Jaccard index. https://en.wikipedia.org/wiki/Jaccard_index
- [Kang2023] Kang, Zhang, Roth, "The ethics of AI-generated maps: A study of DALLE 2 and implications for cartography", 2023. https://arxiv.org/abs/2304.10743 (checked 2026-11-14)
- [Klein] BFL, "FLUX.2 [klein]: Towards Interactive Visual Intelligence". https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence
- [Kontext] BFL, "FLUX.1 Kontext: Flow Matching for In-Context Image Generation and Editing in Latent Space", 2025. https://arxiv.org/abs/2506.15742
- [MapGAN] Li et al., "MapGAN: An Intelligent Generation Model for Network Tile Maps", Sensors 20(11), 2020. https://www.mdpi.com/1424-8220/20/11/3119 (unverified URL)
- [pix2pix] Isola et al., "Image-to-Image Translation with Conditional Adversarial Networks", 2017. https://arxiv.org/abs/1611.07004
- [QwenImage] Qwen team, "Qwen-Image Technical Report", 2025. https://arxiv.org/abs/2508.02324
- [Schnell] FLUX.1 [schnell] model card (Apache 2.0). https://huggingface.co/black-forest-labs/FLUX.1-schnell
- [SDEdit] Meng et al., "SDEdit: Guided Image Synthesis and Editing with Stochastic Differential Equations", 2021. https://arxiv.org/abs/2108.01073
- [SDXL] SDXL base 1.0 model card (CreativeML OpenRAIL++-M). https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- [Tesseract] Tesseract OCR. https://github.com/tesseract-ocr/tesseract
- [ZImage] Z-Image technical report. https://arxiv.org/abs/2511.22699 ; model card https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
