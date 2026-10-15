"""Refresh a local SVG from GitHub's public REST API; no third-party stats host.

GITHUB_TOKEN is optional locally, and supplied by Actions for higher rate limits.
Only repositories owned by this user (excluding forks) enter the project totals.
"""
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USERNAME = 'ravigohel142996'
ROOT = Path(__file__).resolve().parents[1]


def github(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'ravi-profile-metrics', 'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urlopen(Request(f'https://api.github.com/{path}', headers=headers), timeout=30) as response:
        return json.load(response)


def render(repos, updated):
    owned = [repo for repo in repos if not repo['fork']]
    stars = sum(repo['stargazers_count'] for repo in owned)
    languages = Counter(repo['language'] for repo in owned if repo['language'])
    leading = languages.most_common(1)[0][0] if languages else 'Exploring'
    tiles = [(str(len(owned)), 'PUBLIC ORIGINAL REPOS'), (str(stars), 'STARS ON ORIGINAL REPOS'), (str(len(languages)), 'PRIMARY REPO LANGUAGES'), (leading, 'MOST USED BY REPO COUNT')]
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="210" viewBox="0 0 1120 210" role="img" aria-labelledby="title desc">
<title id="title">Ravi Gohel — GitHub snapshot</title>
<desc id="desc">{len(owned)} public non-fork repositories, {stars} stars, {len(languages)} primary repository languages. Leading language by repository count: {escape(leading)}. Updated {updated} UTC.</desc>
<rect x="1" y="1" width="1118" height="208" rx="20" fill="#080d19" stroke="#2b3a4d"/>
<g font-family="DejaVu Sans,Arial,sans-serif"><text x="32" y="35" fill="#66f2da" font-size="12" letter-spacing="2">GITHUB / PUBLIC WORK</text>
<text x="1088" y="35" text-anchor="end" fill="#94a3b8" font-size="12">SNAPSHOT · {updated} UTC</text>''']
    for i, (value, label) in enumerate(tiles):
        x = 32 + i * 275
        if i:
            parts.append(f'<path d="M{x-18} 68v102" stroke="#2b3a4d"/>')
        parts.append(f'<text x="{x}" y="114" fill="#eff5ff" font-size="38" font-weight="bold">{escape(value)}</text><text x="{x}" y="148" fill="#94a3b8" font-size="10" letter-spacing=".8">{label}</text>')
    parts.append('</g></svg>\n')
    return '\n'.join(parts)


def main():
    repos = []
    page = 1
    while True:
        batch = github(f'users/{USERNAME}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    svg = render(repos, datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    target = ROOT / 'assets/github-metrics.svg'
    # Write only after every API request succeeds, preserving the last good image.
    target.write_text(svg, encoding='utf-8')
    print(f'Updated {target.relative_to(ROOT)} from {len(repos)} public repositories')


if __name__ == '__main__':
    main()
