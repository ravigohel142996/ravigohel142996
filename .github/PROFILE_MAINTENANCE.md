# Profile maintenance

This is a GitHub profile README, not a web application. GitHub strips scripts, custom CSS, iframes, and interactive 3D canvases. The orbital hero is a pre-rendered 3D-style GIF that works as an ordinary GitHub image. The design has no external image-hosting dependencies.

## Update your profile

- Edit `README.md` to change your introduction, projects, stack, or contact links.
- Project links lead to source repositories; they do not promise deployed demos.
- Portfolio and LinkedIn links point to external sites. The external sites' availability is outside this repository's control.

## Regenerate the artwork

```sh
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-art.txt
.venv/bin/python scripts/render_hero.py
```

Edit the text and drawing in `scripts/render_hero.py` first. It renders a 64-frame, 5.12-second loop to `assets/hero.gif` and a still to `assets/hero-static.png`. Both should be committed. The README uses the still when the viewer/browser supports the reduced-motion media query. Image viewers or clients that ignore `<picture>` may still show the GIF.

The bundled Space Grotesk font is distributed under the SIL Open Font License; see `assets/fonts/OFL.txt`.

## Refresh the GitHub snapshot

```sh
python3 scripts/update_metrics.py
```

This uses only Python's standard library and GitHub's public API. Optionally supply `GITHUB_TOKEN` in your shell environment for higher API rate limits; do not put a token in a file or commit one.

The snapshot counts public, non-fork repositories owned by `ravigohel142996`, their stars, and the distinct primary languages reported by GitHub. The leading language is measured by repository count, **not** code volume or skill level. Archived repositories are included. It is not a contribution count, streak, or real-time analytics feed.

`.github/workflows/refresh-profile.yml` runs on Mondays at 06:23 UTC, on manual dispatch, and when its script/config changes. It commits only `assets/github-metrics.svg` back to the triggering branch. The initial snapshot is already bundled, so images work before the first Actions run. A failed API request leaves the previous image intact.

Once this change is merged into the default branch, the scheduled workflow becomes active. Ensure GitHub Actions is enabled and repository rules permit the Actions bot to push. If branch protection blocks bot commits, run the script locally and include the generated file in a normal pull request instead. GitHub may disable scheduled workflows in public repositories after 60 days without repository activity; re-enable the workflow from the Actions tab if needed.

The old empty `snake.yml` was removed rather than retaining a broken snake image pointing to a nonexistent generated branch.

## Validate

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests check metric calculations, XML escaping, API failure handling, local image references, font licensing, and GIF loop/static-fallback properties. The render test requires Pillow from `scripts/requirements-art.txt`.
