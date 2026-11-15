# GitHub wiki (2026-11-14)

- Wiki: https://github.com/m4bwav/mapwright/wiki, working copy `../mapwright.wiki` (sibling of the clone), branch master.
- Version described: 0.2.0, unreleased, from main at 0d65fd5. mapwright is not on a registry, so examples ran against the repository (a scratch copy of scripts/ and tests/fixtures/).
- Pages: Home, Getting-Started, Commands, Recipe-Format, Styles, Proof-Bars, FAQ, _Sidebar, _Footer.
- First page saved through the logged-in browser (GitHub creates the wiki repo only on a UI save), then pushed as a fast-forward.
- Verify: `sh ai-docs/notes/2026-11-14-wiki-verify.sh > new.txt` from the repo root, then `wikiwright.py diffout ai-docs/notes/2026-11-14-wiki-verify.out.txt new.txt` and `wikiwright.py outputs <wiki dir> new.txt`. Result today: check 0 errors, outputs 33 checked 0 missing 10 skipped (timings, doctor, hand-cut file contents), live 7 pages 0 failures. Unit tests 61/61.
- Not tested: the everwrite prose checker (not found on this machine), the OCR bar (no tesseract), macOS and Linux.
- Pages naming the version: _Footer, Home, Commands (intro), Getting-Started (--version, doctor).
- Facts the README lacks: bar list and meanings, recipe file layout and feature kinds, world-file half-pixel note, `explain` exits 1 on unknown terms, project R-unit outputs on the unit sphere.
- README inaccuracy: the 0.2.0 features sit under the heading "What works in 0.1.0".
