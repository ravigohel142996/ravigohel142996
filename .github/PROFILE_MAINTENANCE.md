# Profile maintenance — NEURAL / FORGE

This repository is a GitHub profile README, not a website. GitHub strips JavaScript, custom CSS, iframes and canvases from READMEs, so every visual here is a pre-rendered image committed to the repository and referenced by a relative path. No external image services, badges or stats hosts are used.

## What lives where

| Path | What it is | Made by |
| :-- | :-- | :-- |
| `README.md` | Markup only: `<picture>`, linked images, headings, a `<details>` index and plain-text fallbacks | hand-edited |
| `assets/hero.gif`, `assets/hero-static.png` | 1400 × 760 animated hero (50 frames × 100 ms, seamless loop, < 3 MB) and its reduced-motion still | `scripts/render_hero.py` |
| `assets/art/*.svg` | Navigation tabs, section banners, profile panel, six project cards, toolbox, contact panels, footer | `scripts/render_art.py` |
| `assets/github-metrics.svg` | Dated snapshot of public GitHub data | `scripts/update_metrics.py` (weekly Action) |
| `assets/fonts/` | Space Grotesk and Space Mono with their SIL OFL 1.1 licences, plus `forge-glyphs.json` (pre-extracted outlines and kerning) | `scripts/build_glyphs.py` |
| `scripts/profile_content.py` | Single source of truth for the copy drawn into the artwork | hand-edited |
| `scripts/forge_type.py`, `scripts/forge_svg.py` | Standard-library type setter and SVG drawing kit with a built-in layout checker | — |

Text in every SVG is drawn as vector outlines from `forge-glyphs.json`, because an SVG shown through `<img>` cannot load web fonts. That keeps the typography identical everywhere and lets the metrics job run with no `pip install`.

## Change the words

1. Edit `scripts/profile_content.py`: sections, project cards, tools, explored topics, interests and contacts. Project copy was checked against each repository's README, requirements and source; keep claims modest and link to source code, never to imaginary demos.
2. Run `python3 scripts/render_art.py`. It refuses to write anything if text would be clipped or collide (`LayoutError` names the string), so shorten the copy or let the renderer shrink it (`Canvas.fit`).
3. Update the matching text in `README.md`: alt text, the plain-text project index and the **Build with / Exploring** lines. The tests compare the README against `profile_content.py`.
4. Run the tests (below).

Only the characters in `forge-glyphs.json` can be drawn: printable ASCII plus `— – · → ← ↑ ↓ ↗ • … ’ ‘ “ ” © × °`. To add characters, extend `CHARS` in `scripts/build_glyphs.py` and rebuild the glyphs.

## Re-render the artwork

```sh
python3 scripts/render_art.py            # SVG artwork: standard library only
python3 scripts/render_art.py --check    # exit 1 if committed art is stale

python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-art.txt
.venv/bin/python scripts/render_hero.py --frames 4      # quick preview frames in /tmp
.venv/bin/python scripts/render_hero.py                 # full hero, ~2 minutes on 2 CPUs
.venv/bin/python scripts/build_glyphs.py                # only after changing fonts or CHARS
.venv/bin/python scripts/inspect_art.py /tmp/forge-inspect   # PNG renders + contact sheets for review
```

Hero notes. The 3D torus and crystal are ray-marched per pixel with numpy, using the same camera as the floor grid. Every periodic motion must complete a whole number of cycles per loop: the torus turns 180° and the crystal 60° (both symmetries), the particles make whole orbits, and the pulse and cursor complete whole cycles. That is what keeps the loop seamless, and a test checks the wrap-around frame step. If the GIF grows past 3 MB, raise the `threshold` in `to_gif` slightly or reduce `FRAMES`; don't add a wide bloom, since it changes large areas every frame.

## Preview the README locally

```sh
python3 scripts/preview_readme.py    # http://0.0.0.0:8080 (dark) and /light
```

The script renders `README.md` with GitHub's own Markdown API in `markdown` mode, the mode used for README files, and styles it with the published `github-markdown-css`. That page CSS exists only for the preview; GitHub does not allow custom CSS in a README, and this README contains none. Output goes to `.preview/` (git-ignored).

## Markup rules learned the hard way

- **Hero `<picture>` stays bare.** GitHub wraps every unlinked image in a link. If you wrap `<picture>` in your own `<a>`, GitHub pulls the `<img>` out of the `<picture>` and the reduced-motion source is lost. Keep `<picture id="top">` as the first element. Readers who prefer reduced motion are also covered by GitHub's own "Autoplay animated images: sync with system" setting.
- **Multi-column rows use fixed pixel widths** (cards 410, contact panels 272, tabs 160), not percentages. They sit side by side in GitHub's ~850 px column and wrap into one legible column on phones. Percentage widths would shrink the text instead.
- **Section anchors** are explicit `id`s on the `<h2>` headings (GitHub prefixes them with `user-content-` and its JavaScript resolves `#the-human` and friends). GitHub also adds an empty "Permalink" icon to image-only headings; that is expected.
- **Use the GitHub `markdown` mode when testing** with `gh api markdown`. The `gfm` mode renders like an issue comment and turns every newline into a line break.
- **Gradients on straight lines** must use `userSpaceOnUse` coordinates (`forge_svg.rule`). A horizontal or vertical path has a zero-size bounding box, and browsers skip bounding-box gradients on it entirely; a test guards this.

## GitHub snapshot

```sh
python3 scripts/update_metrics.py    # optional: GITHUB_TOKEN=... for higher rate limits (never commit a token)
```

The card counts public, non-fork repositories owned by `ravigohel142996`, their stars, primary languages by repository count (top five plus "Other", ties broken alphabetically) and the three most recently pushed original repositories, excluding this profile repository. It also shows the account's start date. Repository counts are not lines of code or skill levels, and the card is a dated snapshot, not live telemetry; the date is printed on it. All requests must succeed before the file is written, so a failed refresh keeps the last good image.

`.github/workflows/refresh-profile.yml` runs on Mondays at 06:23 UTC, on manual dispatch, and on pushes that change the script, its drawing kit (`forge_svg.py`, `forge_type.py`, `forge-glyphs.json`) or the workflow itself. It commits only `assets/github-metrics.svg` back to the triggering branch. If branch protection blocks the Actions bot, run the script locally and commit the file in a normal pull request. GitHub may pause scheduled workflows after 60 days without repository activity; re-enable it from the Actions tab.

## Validate

```sh
python3 -m unittest discover -s tests -v          # standard library: README, artwork, metrics, fonts, workflow
.venv/bin/python -m unittest discover -s tests -v # adds the GIF frame / loop / seam / still checks
```

The tests cover image references and alt text, the reduced-motion `<picture>`, navigation anchors, card and contact links, the plain-text index, SVG validity and self-containment, layout-checker behaviour, stale artwork, metrics calculations and failure handling, font licences and the workflow's trigger paths.

## Fonts

Space Grotesk (© 2020 The Space Grotesk Project Authors) and Space Mono (© 2016 The Space Mono Project Authors) are bundled under the SIL Open Font License 1.1. See `assets/fonts/SpaceGrotesk-OFL.txt` and `assets/fonts/SpaceMono-OFL.txt`. The outlines in `forge-glyphs.json` are derived from these fonts under the same licence.
