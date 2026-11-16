# GitHub wiki update to 0.10.2 (2026-11-16)

Updates [2026-11-14-github-wiki.md](2026-11-14-github-wiki.md) (0.2.0), which still describes how the wiki was first made.

- Wiki: https://github.com/m4bwav/mapwright/wiki, working copy `../mapwright.wiki`, branch master, commit 6ed8421.
- Version described: the v0.10.2 tag. Not on a registry, so the verify script now copies `scripts/` and `tests/fixtures/` out of the tag with `git archive` into a scratch folder (pass another tag as its first argument).
- Pages (13): Home, Getting-Started, Commands, Generate-Worlds, Generate-Places, Generate-Space, Export, Paths-and-Travel, Recipe-Format, Styles, Proof-Bars, Versions-and-Upgrading, FAQ, plus _Sidebar and _Footer. New: the three Generate pages, Export, Paths-and-Travel, Versions-and-Upgrading. gen world/region/zoom moved from Commands to Generate-Worlds; Commands has a verb table plus read, trace, find, fetch and aistyle.
- Verify: `sh ai-docs/notes/2026-11-16-wiki-verify.sh | sed 's/\r$//' > new.txt` from the repo root (about 45 s; sets PYTHONIOENCODING=utf-8 so the find credits print the copyright sign), then `wikiwright.py diffout ai-docs/notes/2026-11-16-wiki-verify.out.txt new.txt` and `wikiwright.py outputs <wiki dir> new.txt`.
- Results: diffout against the 0.2.0 output: only the version line, four new doctor lines, five new explain terms and timings changed. check --version 0.10.2: 13 pages 0 errors 0 warnings. outputs: 69 checked, 0 missing, 19 skipped (timings, doctor, JSON excerpt, hand-cut file contents). live: 13 pages, 0 failures. Unit tests on the tag: 222 run, OK, 2 skipped (live ComfyUI and Nominatim).
- Not tested: `find --online` and `fetch` (network; the fetch page example has no output), a real `aistyle` pass (no server; `--dry-run` only), `read --prompt/--answers`, `gen city --parent`, the everwrite prose checker (not installed), OCR bars (no tesseract), macOS and Linux.
- Pages naming the version: _Footer, Home (Version), Commands (intro), Getting-Started (--version, doctor), Versions-and-Upgrading, Recipe-Format (tool_version).
- Doc and code inaccuracies found:
  1. `scripts/mpw.py` VERSION is still "0.10.0" on v0.10.1 and v0.10.2, so `--version`, `doctor` and every new recipe's `tool_version` say 0.10.0 while plugin.json says 0.10.2. Fix in the next release.
  2. README: the Generate bullet still says "(0.2.0, unreleased)" and "`check` runs 13 proof bars"; a world's check prints 16.
  3. CHANGELOG 0.6.0 says planets are kept 12 mutual Hill radii apart; the system check bar tests 10 (the generator's margin, not a contradiction, but the README/CHANGELOG do not say the bar is 10).
  4. The old wiki Styles note said painted looks were outside mapwright; aistyle has done that since 0.8.0 (fixed on the wiki).
- Facts the README lacks: `trace` on an ink-and-parchment render finds no water (parchment sea); `inspect` labels any GeoJSON WGS84 even when `trace` wrote pixels; deck coordinates for `path` are 1-based (`DECK,X,Y`), a non-floor square exits 2; Tiled floor count excludes doors; heightmap range tops differ by target because of edge vs centre sampling.
