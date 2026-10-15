"""Serve a local, GitHub-faithful preview of README.md.

    python3 scripts/preview_readme.py            # http://0.0.0.0:8080  (dark)  and /light
    python3 scripts/preview_readme.py --build    # only write .preview/*.html

The README is rendered by GitHub's own Markdown API in `markdown` mode, the
mode used for README files (`gfm` mode would turn every newline into <br>),
via `gh` when available or the public REST endpoint otherwise.
The page is styled with the published `github-markdown-css` package, fetched
once from the npm registry into .preview/ (git-ignored).

The CSS here exists only to imitate github.com for review; the README itself
contains no CSS, scripts or iframes. Three github.com behaviours are emulated:
relative assets are served from the repository; `user-content-` id prefixes
are removed so in-page links resolve without GitHub's JavaScript; and the link
GitHub inserts between <picture> and its <img> is moved outside the picture,
as github.com's client-side <themed-picture> component has to for GitHub's
documented <picture> images (light/dark, reduced motion) to select a source.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.preview'
REPO = 'ravigohel142996/ravigohel142996'


def render_markdown(text: str) -> str:
    if shutil.which('gh'):
        result = subprocess.run(['gh', 'api', 'markdown', '-f', 'mode=markdown', '-F', 'text=@-'],
                                input=text, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'readme-preview'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    body = json.dumps({'text': text, 'mode': 'markdown'}).encode()
    with urlopen(Request('https://api.github.com/markdown', data=body, headers=headers), timeout=30) as response:
        return response.read().decode()


def markdown_css(theme: str) -> str:
    cached = OUT / f'github-markdown-{theme}.css'
    if not cached.is_file():
        with urlopen('https://registry.npmjs.org/github-markdown-css/latest', timeout=30) as response:
            tarball = json.load(response)['dist']['tarball']
        with urlopen(tarball, timeout=60) as response:
            archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode='r:gz')
        for name in ('dark', 'light'):
            member = archive.extractfile(f'package/github-markdown-{name}.css')
            (OUT / f'github-markdown-{name}.css').write_bytes(member.read())
    return cached.read_text(encoding='utf-8')


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>README preview · {theme}</title>
<style>{css}</style>
<style>
  /* Preview chrome only: imitates the profile README box on github.com. Not part of the README. */
  body {{ margin: 0; background: {page}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  .note {{ max-width: 896px; margin: 0 auto; padding: 14px 16px 0; color: {muted}; font-size: 12px; }}
  .note a {{ color: {link}; }}
  .box {{ max-width: 896px; margin: 12px auto 48px; border: 1px solid {border}; border-radius: 6px; background: {page}; }}
  .box header {{ padding: 10px 16px; border-bottom: 1px solid {border}; color: {muted}; font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .markdown-body {{ padding: 24px; background: transparent; }}
  @media (max-width: 767px) {{ .box {{ margin: 8px 8px 32px; }} .markdown-body {{ padding: 16px; }} }}
</style></head>
<body>
<p class="note">Local preview of README.md rendered by GitHub's Markdown API · page styling is preview-only ·
  switch to <a href="{other_href}">{other} theme</a></p>
<div class="box"><header>{repo} / README.md</header>
<article class="markdown-body">
{html}
</article></div>
</body></html>
"""
THEMES = {
    'dark': {'page': '#0d1117', 'muted': '#9198a1', 'border': '#3d444d', 'link': '#4493f8'},
    'light': {'page': '#ffffff', 'muted': '#59636e', 'border': '#d1d9e0', 'link': '#0969da'},
}


def build() -> None:
    OUT.mkdir(exist_ok=True)
    html = render_markdown((ROOT / 'README.md').read_text(encoding='utf-8'))
    html = re.sub(r'(\s(?:id|name))="user-content-', r'\1="', html)   # what GitHub's JS does for #anchors
    html = re.sub(r'(src|srcset|href)="(?:\./)?(assets/[^"]+)"', r'\1="/\2"', html)
    html = re.sub(r'(<picture[^>]*>)(.*?)<a ([^>]*)>(<img [^>]*>)</a>(\s*</picture>)',
                  r'<a \3>\1\2\4\5</a>', html, flags=re.S)   # imitate <themed-picture>
    for theme, colors in THEMES.items():
        other = 'light' if theme == 'dark' else 'dark'
        page = PAGE.format(theme=theme, css=markdown_css(theme), html=html, repo=REPO, other=other,
                           other_href='/light' if other == 'light' else '/', **colors)
        (OUT / f'{theme}.html').write_text(page, encoding='utf-8')
    print(f'Wrote {OUT.relative_to(ROOT)}/dark.html and light.html')


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server API)
        route = self.path.split('?')[0]
        if route in ('/', '/index.html', '/dark'):
            self.path = '/.preview/dark.html'
        elif route == '/light':
            self.path = '/.preview/light.html'
        elif not route.startswith('/assets/'):
            self.send_error(404)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main(argv: list[str]) -> None:
    build()
    if '--build' in argv:
        return
    port = int(argv[argv.index('--port') + 1]) if '--port' in argv else 8080
    server = ThreadingHTTPServer(('0.0.0.0', port), partial(Handler, directory=str(ROOT)))
    print(f'Serving README preview on http://0.0.0.0:{port}  (light theme: /light)')
    server.serve_forever()


if __name__ == '__main__':
    main(sys.argv[1:])
