# Research: mapwright

Findings that back [skills/mapwright/SKILL.md](skills/mapwright/SKILL.md). Changes they caused are logged in [CHANGELOG.md](CHANGELOG.md); procedural lessons live in [LEARNINGS.md](LEARNINGS.md); test runs and their evidence in [TESTS.md](TESTS.md); schedule and state in `evergreen.json`. Protocol: MAINTENANCE.md.

Topic: cartography tools, map data formats, projections, fantasy and procedural map generators. Tier `moderate`. Last refresh 2026-11-14; next due 2026-12-14.

## Current understanding

The detailed, sourced research lives in [references/](references/); this section is the summary a refresh checks.

- Settled: GeoJSON (RFC 7946, WGS 84 lon/lat), GPX 1.1, KML 2.2, shapefile, GeoPackage 1.4, MBTiles 1.3 and PMTiles v3 layouts ([formats-and-tools.md](references/formats-and-tools.md)); geodesic maths (Karney / geographiclib, MIT) and the projection formulas in [projections.md](references/projections.md).
- Moving: map MCP servers from vendors (Mapbox, Google Maps, others) and agent map skills ([prior-art.md](references/prior-art.md)); AI image models used for map art ([ai-image-models.md](references/ai-image-models.md)); fantasy generators such as Azgaar's Fantasy Map Generator.
- Licence facts that bite: Gaia is CC BY-NC 3.0 IGO (never bundle), Nominatim bulk limits, HYG moved to Codeberg, Rumsey CC BY-NC-SA ([sources-and-terms.md](references/sources-and-terms.md)).
- Community practice and new tools are harvested through [harvest.json](harvest.json) (the everscout `mapmaking` beat).

## Open questions

- Copernicus GLO-90 terms, Snyder PDF, EPSG and shapely/pyproj facts were not reached by the 2026-11-14 source check (see ai-docs/log.md).

## Search plan

Four tracks; every refresh runs at least one query on each (scope each to the period since the last refresh; add the year). Protocol §4 explains the tracks and how tooling, practice and testing findings are judged.

Subject (the goal and the latest thinking on reaching it):

- `Fantasy Map Generator release <year>`; `PMTiles OR GeoParquet spec change <year>`
- `map mcp server <year>`; `procedural world map generator github <year>`; `AI fantasy map image model <year>`
- Official forums of each tool, platform or vendor this unit depends on (announcements, deprecations, breaking changes and known bugs often land there before the docs): `<forum URL>` (announcements category: `<URL>`); a vendor Discourse, community site or the tool repository's GitHub Discussions. Search announcements first, then known issues, since the last check (`site:<forum host> <terms> <month>`, or Discourse `/latest.json`, a category `.rss`, `search.json?q=<terms> after:<date>`). Staff posts are primary sources; user posts are leads to confirm.

Tooling (skills, plugins, MCP servers, scripts, knowledge graphs built for this subject):

- `path:SKILL.md "cartography map"` on GitHub code search, sorted by recently updated; `npx skills find "cartography map"` and skills.sh for install counts
- `https://registry.modelcontextprotocol.io/v0/servers?search=cartography map`; fallback `"cartography map" mcp server site:glama.ai OR site:pulsemcp.com`
- `"cartography map" skill OR plugin OR "mcp server" <year> site:github.com`
- Most used: skills.sh weekly and 24-hour installs for `cartography map` (never all-time; exclude meta and installer skills); `anthropics/claude-plugins-official` and `claude-plugins-community` searched for `cartography map` (record the tier)
- Practitioner test on every candidate: commit in the last 90 days, issues answered, no bundled `*.test.*` or `conftest.py` from an unknown author, author has other work in the area, ships `evals/` or paired results; `path:SKILL.md "cartography map" evals OR benchmark`
- Provenance tiebreaker: which model and reasoning setting wrote each candidate (`evals.json` / frontmatter `model`, README or changelog credit, commit messages); prefer the latest frontier model at its highest reasoning setting, read over inferred
- Supersession sweep: `"cartography map" skill deprecated OR superseded OR archived <year>`; archive flag on every tool already listed here

Most discussed and the converged thinking (comment volume over points; what the most-used and most-discussed sources agree on becomes a claim in Current understanding):

- `hn.algolia.com/api/v1/search_by_date?query=cartography map` and `site:reddit.com/r/ClaudeAI OR r/ClaudeCode "cartography map" <month>`
- OpenAlex `works?search=cartography map agent&sort=cited_by_count:desc&filter=from_publication_date:<last check>`; the two most-cited through Semantic Scholar

Practice (how others use AI agents on this goal, and everything in between):

- `"how I use" OR "my workflow" "cartography map" "claude code" OR codex OR cursor <year>`
- `site:arxiv.org "cartography map" agent "case study" OR empirical OR telemetry <year>`
- `"cartography map" site:simonwillison.net OR site:latent.space OR site:anthropic.com/engineering <year>`; hn.algolia.com `"cartography map" agent` sorted by date

Testing (how work on this subject is verified, and how skills for it are tuned):

- `"cartography map" verify OR validate OR "smoke test" OR checker agent <year>` (what evidence shows the job was done)
- `path:SKILL.md "cartography map" test OR eval OR evals` on GitHub; `"cartography map" evals OR "eval suite" OR regression "agent skill" <year>`
- `site:arxiv.org "cartography map" agent evaluation OR benchmark <year>`; promptfoo, Inspect or DeepEval docs for assertion types that fit this subject

Best sources (primary first): <official docs / changelog / official forums of the tools used / standards body / key papers; for tooling: skills.sh, the MCP registry, the anthropics plugin catalogs; for testing: the subject's own test tools and the eval-framework docs>. Sources that proved noisy: <list, so they are skipped next time; SEO "top 10" listicles and scraped mega-directories are noise by default>.

## Findings log

Newest first. One entry per material finding; a quiet refresh gets one entry saying so. `Track` is subject, tooling, practice, or testing.

### R-20261118-1 · 2026-11-18 · Historic map drape (georeferencing note)
- Summary: when a scanned map and a DEM disagree, warp the DEM to the scan with a thin-plate spline over many control points, dropping outliers; a power curve on elevation before displacement keeps low ground visible beside high peaks. Build a recipe when a request comes. Idea only, no code.
- Sources: D:/m4bwa/Claude/Projects/Ai/technique-harvest/ai-docs/posts/1xrrijk.md (technique-harvest batch E)

### R-20261117-1 · 2026-11-17 · Books round 20: names, atlases, sci-fi map sets, map politics
- Summary: nine map books read for methods (Rosenfelder Lexipedia; Fonstad atlases of the Forgotten Realms and Dragonlance; Star Trek Maps; Infinity Suite Maps; Dodecahedron 2014 and 2015; Leuenberger, The Politics of Maps; Akerman, Decolonizing the Map). Built: site-matched name roots with glosses, current arrows, index grid and gazetteer, player dungeon copy and secret-only floor report, sector hazard tiers, OSM boundary notes. Book rules unverified on our tools: three hazard tiers, two in five settlements keeping a bare name, the gazetteer as the index form. Star Trek is a Paramount setting and Dodecahedron 2015 has no open licence, so only methods were taken, in our own words; no setting maps ship. Other proposals stay in the notes files and were not built this round.
- Track: practice
- Sources: Ai/technique-harvest/ai-docs/books/<slug>/notes.md for the nine slugs above
- Magnitude: minor
- Applied: C-20261117-2

### R-20261114-1 · 2026-11-14 · Creation pass
- Summary: the current content rests on the 2026-11-14 research in references/ (formats, projections, sources and terms partly source-checked that day; the rest marked unverified there) and 15 map book notes. Converted to evergreen on 2026-11-15 without a new web pass; the first refresh should re-check the unverified items.
- Track: subject
- Sources: references/*.md (each cites its own primary URLs)
- Magnitude: n/a (initial)
- Applied: C-20261115-8

### R-20261114-2 · 2026-11-14 · Tooling pass (prior art)
- Summary: vendor map MCP servers (Mapbox, others) cover real-world geocoding and routing with API keys; no shipped skill covers mapwright's offline read/convert/measure plus invented-world generation, so nothing supersedes it. Details in references/prior-art.md.
- Track: tooling
- Sources: https://github.com/mapbox/mcp-server , references/prior-art.md
- Magnitude: n/a (initial)
- Applied: C-20261115-8
