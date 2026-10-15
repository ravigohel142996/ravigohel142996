"""Refresh assets/github-metrics.svg from GitHub's public REST API; no third-party stats host.

    python3 scripts/update_metrics.py

Standard library only (text outlines come from assets/fonts/forge-glyphs.json).
GITHUB_TOKEN is optional locally and supplied by Actions for higher rate limits.
Only repositories owned by this user (excluding forks) enter the totals. The
image is a dated snapshot: it is written only after every request succeeds,
so a failed refresh keeps the last good image.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

import forge_svg as fs  # noqa: E402
from forge_svg import Canvas, num  # noqa: E402
import forge_type as ft  # noqa: E402

USERNAME = 'ravigohel142996'
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'assets/github-metrics.svg'
W, H = 840, 378
LANGUAGE_COLORS = (fs.CYAN, fs.VIOLET_SOFT, fs.PINK, fs.BLUE, fs.LAVENDER)
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def github(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'ravi-profile-metrics', 'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urlopen(Request(f'https://api.github.com/{path}', headers=headers), timeout=30) as response:
        return json.load(response)


def drawable(text: str) -> str:
    """API strings are drawn as glyph outlines; swap characters the bundled glyph set lacks."""
    glyphs = ft.style('text')['glyphs']
    return ''.join(ch if ch in glyphs else '?' for ch in text)


def summarise(repos, profile_repo: str = USERNAME) -> dict:
    """Derive every number shown on the card from the raw repository list."""
    owned = [repo for repo in repos if not repo.get('fork')]
    languages = Counter(repo['language'] for repo in owned if repo.get('language'))
    ranked = sorted(languages.items(), key=lambda item: (-item[1], item[0].lower()))
    segments = ranked[:5]
    other = sum(count for _, count in ranked[5:])
    if other:
        segments.append(('Other', other))
    recent = sorted((repo for repo in owned if repo.get('name', '').lower() != profile_repo.lower() and repo.get('pushed_at')),
                    key=lambda repo: repo['pushed_at'], reverse=True)[:3]
    return {
        'repos': len(owned),
        'stars': sum(repo.get('stargazers_count', 0) for repo in owned),
        'languages': len(languages),
        'leading': ranked[0][0] if ranked else 'Exploring',
        'segments': segments,
        'unlabelled': sum(1 for repo in owned if not repo.get('language')),
        'recent': [(repo['name'], repo['pushed_at'][:10], repo.get('language') or '—') for repo in recent],
    }


def since(created_at: str | None) -> str | None:
    if not created_at:
        return None
    year, month = created_at[:4], int(created_at[5:7])
    return f'{MONTHS[month - 1]} {year}'


def tile_icon(c: Canvas, kind: str, x: float, y: float, color: str) -> None:
    common = f'stroke="{color}" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    paths = {
        'repos': 'M2 2.5h10.5a1.5 1.5 0 0 1 1.5 1.5v10.5H3.5A1.5 1.5 0 0 1 2 13zM2 13a1.5 1.5 0 0 1 1.5-1.5H14M5.5 5.5h5',
        'stars': 'M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z',
        'languages': 'M8 1.8l6.2 3.2L8 8.2 1.8 5zM1.8 8.2L8 11.4l6.2-3.2M1.8 11.2L8 14.4l6.2-3.2',
        'leading': 'M2.2 12.6h11.6M3 11l-1-6.6 3.6 2.8L8 2.6l2.4 4.6 3.6-2.8-1 6.6z',
    }
    c.add(f'<g transform="translate({num(x)} {num(y)})" {common}><path d="{paths[kind]}"/></g>')


def render(repos, updated: str, created_at: str | None = None) -> str:
    data = summarise(repos)
    joined = since(created_at)
    recent_text = ', '.join(name for name, _, _ in data['recent']) or 'none yet'
    desc = (f"{data['repos']} public non-fork repositories, {data['stars']} stars, {data['languages']} primary repository "
            f"languages. Leading language by repository count: {data['leading']}. Most recently pushed: {recent_text}. "
            f"Updated {updated} UTC.")
    c = Canvas(W, H, 'Ravi Gohel — GitHub snapshot', desc)
    fs.panel(c, 1, 1, W - 2, H - 2, 22, accent=fs.LAVENDER,
             glow=[(W * .88, 10, 300, fs.LAVENDER, .20), (60, H, 260, fs.CYAN, .10)])
    fs.stars(c, 404 + data['repos'], (14, 12, W - 14, H - 12), 16, avoid=[(20, 18, W - 20, H - 16)])
    c.text('GITHUB · PUBLIC WORK', 32, 42, style='mono-bold', size=11, fill=fs.CYAN, tracking=.22)
    stamp = f'SNAPSHOT · {updated} UTC'
    stamp_w = c.measure(stamp, 'mono-bold', 9.5, .14) + 34
    c.add(f'<rect x="{num(W - 32 - stamp_w)}" y="25.5" width="{num(stamp_w)}" height="24" rx="12" fill="{fs.NIGHT}" '
          f'stroke="{fs.LAVENDER}" stroke-opacity=".45"/>')
    c.add(f'<circle cx="{num(W - 32 - stamp_w + 14)}" cy="37.5" r="3" fill="none" stroke="{fs.LAVENDER}" stroke-width="1.3"/>')
    c.text(stamp, W - 32 - stamp_w + 24, 41, style='mono-bold', size=9.5, fill=fs.LAVENDER, tracking=.14)

    tiles = [(f"{data['repos']}", 'PUBLIC ORIGINAL REPOS', 'repos', fs.CYAN),
             (f"{data['stars']}", 'STARS ON ORIGINAL REPOS', 'stars', fs.PINK),
             (f"{data['languages']}", 'PRIMARY REPO LANGUAGES', 'languages', fs.VIOLET_SOFT),
             (drawable(data['leading']), 'MOST USED BY REPO COUNT', 'leading', fs.MINT)]
    gap, top = 12, 64
    tile_w = (W - 64 - gap * 3) / 4
    for i, (value, label, icon, color) in enumerate(tiles):
        x = 32 + i * (tile_w + gap)
        c.add(f'<rect x="{num(x + .5)}" y="{top + .5}" width="{num(tile_w - 1)}" height="91" rx="14" fill="{fs.NIGHT}" '
              f'fill-opacity=".8" stroke="{fs.EDGE}"/>')
        fs.rule(c, x + 14, top + .8, x + tile_w - 14, top + .8, [(0, color, 0), (.5, color, .7), (1, color, 0)])
        tile_icon(c, icon, x + tile_w - 32, top + 14, color)
        box = (x + 8, top + 4, x + tile_w - 8, top + 88)
        size = c.fit(value, 'display', 36, tile_w - 32, -.01, minimum=14)
        c.text(value, x + 16, top + 56, style='display', size=size, fill=fs.WHITE, tracking=-.01, within=box)
        c.text(label, x + 16, top + 76, style='mono', size=8.5, fill=fs.MUTED, tracking=.1, within=box)

    # language distribution by repository count
    y = 190
    c.text('PRIMARY LANGUAGE · SHARE OF ORIGINAL REPOS', 32, y, style='mono', size=9.5, fill=fs.DIM, tracking=.14)
    total = sum(count for _, count in data['segments'])
    bar_x, bar_w, bar_y = 32, W - 64, y + 12
    c.add(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="10" rx="5" fill="{fs.EDGE_SOFT}"/>')
    if total:
        clip = c.uid('bar')
        c.define(f'<clipPath id="{clip}"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="10" rx="5"/></clipPath>')
        x = float(bar_x)
        parts = []
        for k, (name, count) in enumerate(data['segments']):
            width = bar_w * count / total
            color = fs.DIM if name == 'Other' else LANGUAGE_COLORS[k % len(LANGUAGE_COLORS)]
            parts.append(f'<rect x="{num(x)}" y="{bar_y}" width="{num(width + .4)}" height="10" fill="{color}"/>')
            x += width
        c.add(f'<g clip-path="url(#{clip})">{"".join(parts)}</g>')
        lx, ly = 32.0, bar_y + 32
        entries = [(name, count, fs.DIM if name == 'Other' else LANGUAGE_COLORS[k % len(LANGUAGE_COLORS)])
                   for k, (name, count) in enumerate(data['segments'])]
        size = 10.0
        while size > 7.5 and sum(c.measure(drawable(f'{n} {k}'), 'mono', size, .04) + 34 for n, k, _ in entries) > W - 64:
            size -= .25
        for name, count, color in entries:
            c.add(f'<rect x="{num(lx)}" y="{num(ly - 8)}" width="9" height="9" rx="2.5" fill="{color}"/>')
            label = drawable(f'{name} {count}')
            c.text(label, lx + 15, ly, style='mono', size=size, fill=fs.BODY, tracking=.04, within=(32, ly - 14, W - 32, ly + 6))
            lx += c.measure(label, 'mono', size, .04) + 34
    else:
        c.text('No primary languages detected yet', 32, bar_y + 32, style='mono', size=10, fill=fs.MUTED)

    # most recently pushed original repositories
    y = 272
    c.text('RECENTLY PUSHED', 32, y, style='mono', size=9.5, fill=fs.DIM, tracking=.14)
    col_w = (W - 64) / 3
    if data['recent']:
        for i, (name, date, language) in enumerate(data['recent']):
            x = 32 + i * col_w
            box = (x, y + 4, x + col_w - 16, y + 50)
            c.add(f'<circle cx="{num(x + 4)}" cy="{y + 21}" r="3.2" fill="none" stroke="{fs.CYAN}" stroke-width="1.3"/>')
            shown = ft.truncate(drawable(name), 'text', 14, col_w - 36)
            c.text(shown, x + 16, y + 26, style='text', size=14, fill=fs.WHITE, within=box)
            c.text(drawable(f'{date} · {language}'), x + 16, y + 44, style='mono', size=9.5, fill=fs.MUTED, tracking=.04, within=box)
    else:
        c.text('No original repositories yet', 32, y + 26, style='text', size=13, fill=fs.MUTED)

    notes = ['forks excluded', 'repo counts, not lines of code']
    if data['unlabelled']:
        notes.append(f"{data['unlabelled']} without a detected language")
    notes.append('dated snapshot, refreshed weekly' + (f' · on GitHub since {joined}' if joined else ''))
    note = ' · '.join(notes)
    fs.rule(c, 32, H - 43.5, W - 32, H - 43.5, [(0, fs.LAVENDER, .35), (1, fs.LAVENDER, 0)])
    c.text(note, 32, H - 20, style='mono', size=c.fit(note, 'mono', 9, W - 64, minimum=6.5), fill=fs.DIM)
    return c.svg()


def main():
    repos = []
    page = 1
    while True:
        batch = github(f'users/{USERNAME}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    profile = github(f'users/{USERNAME}')
    svg = render(repos, datetime.now(timezone.utc).strftime('%Y-%m-%d'), profile.get('created_at'))
    # Write only after every API request succeeds, preserving the last good image.
    TARGET.write_text(svg, encoding='utf-8')
    print(f'Updated {TARGET.relative_to(ROOT)} from {len(repos)} public repositories')


if __name__ == '__main__':
    main()
