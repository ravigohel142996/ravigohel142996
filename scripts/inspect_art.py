"""Rasterise the SVG artwork to PNG for visual review (nothing is committed).

    .venv/bin/python scripts/inspect_art.py [output-dir] [--zoom 2]

Writes one PNG per SVG plus contact sheets, so clipped text, collisions and
contrast problems can be checked in real pixels. Requires resvg-py and Pillow.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def render(svg_path: Path, zoom: float) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_path=str(svg_path), zoom=zoom)
    return Image.open(io.BytesIO(bytes(data))).convert('RGBA')


def sheet(images: list[Image.Image], width: int, background=(13, 17, 23)) -> Image.Image:
    """Stack images vertically on GitHub's dark page colour."""
    pad = 24
    scaled = [im.resize((width, round(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im for im in images]
    height = sum(im.height for im in scaled) + pad * (len(scaled) + 1)
    out = Image.new('RGBA', (width + pad * 2, height), background + (255,))
    y = pad
    for im in scaled:
        out.alpha_composite(im, (pad + (width - im.width) // 2, y))
        y += im.height + pad
    return out


def main(argv: list[str]) -> None:
    out_dir = Path(argv[0]) if argv and not argv[0].startswith('--') else Path('/tmp/forge-inspect')
    zoom = float(argv[argv.index('--zoom') + 1]) if '--zoom' in argv else 2.0
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = {}
    for svg in sorted([*ROOT.glob('assets/art/*.svg'), ROOT / 'assets/github-metrics.svg']):
        if not svg.is_file():
            continue
        image = render(svg, zoom)
        image.save(out_dir / f'{svg.stem}.png')
        rendered[svg.stem] = image
        print(f'{svg.relative_to(ROOT)} -> {image.width}x{image.height}')
    groups = {
        'sheet-sections': [k for k in rendered if k.startswith(('section-', 'profile', 'toolbox', 'footer', 'github-metrics'))],
        'sheet-cards': [k for k in rendered if k.startswith('card-')],
        'sheet-small': [k for k in rendered if k.startswith(('nav-', 'contact-'))],
    }
    for name, keys in groups.items():
        if keys:
            sheet([rendered[k] for k in keys], 1680 if name != 'sheet-small' else 560).convert('RGB').save(out_dir / f'{name}.png')
    print(f'PNG previews in {out_dir}')


if __name__ == '__main__':
    main(sys.argv[1:])
