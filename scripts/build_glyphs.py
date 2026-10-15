"""Extract glyph outlines, advances and kerning from the bundled fonts.

The output, ``assets/fonts/forge-glyphs.json``, lets every SVG in this profile
draw its text as vector paths with only Python's standard library. That keeps
the typography identical in every browser (an SVG shown through <img> cannot
load web fonts) and lets the GitHub Actions metrics job run without pip.

Run after changing the fonts or the character set:

    .venv/bin/python scripts/build_glyphs.py

Requires fontTools and uharfbuzz from scripts/requirements-art.txt.
"""
from __future__ import annotations

import json
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'assets/fonts'
TARGET = FONTS / 'forge-glyphs.json'

# style name -> (font file, variable-font coordinates or None)
STYLES = {
    'display': ('SpaceGrotesk.ttf', {'wght': 700}),
    'text': ('SpaceGrotesk.ttf', {'wght': 500}),
    'mono': ('SpaceMono-Regular.ttf', None),
    'mono-bold': ('SpaceMono-Bold.ttf', None),
}
CHARS = [chr(code) for code in range(0x20, 0x7F)] + list('—–·→←↑↓↗•…’‘“”©×°')
NOTICE = (
    'Glyph outlines derived from Space Grotesk (Copyright 2020 The Space Grotesk Project Authors) '
    'and Space Mono (Copyright 2016 The Space Mono Project Authors), licensed under the SIL Open '
    'Font License 1.1. See assets/fonts/SpaceGrotesk-OFL.txt and assets/fonts/SpaceMono-OFL.txt.'
)


def number(value: float) -> str:
    return str(int(round(value)))


def extract(file_name: str, coordinates: dict | None) -> dict:
    path = FONTS / file_name
    font = TTFont(path)
    if 'fvar' in font:
        font = instantiateVariableFont(font, coordinates or {}, inplace=False)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    os2 = font['OS/2']

    blob = hb.Blob.from_file_path(str(path))
    hb_font = hb.Font(hb.Face(blob))
    if coordinates:
        hb_font.set_variations(coordinates)

    glyphs, gids = {}, {}
    for char in CHARS:
        name = cmap.get(ord(char))
        if name is None:
            continue
        pen = SVGPathPen(glyph_set, ntos=number)
        glyph_set[name].draw(pen)
        bounds = BoundsPen(glyph_set)
        glyph_set[name].draw(bounds)
        x_min, y_min, x_max, y_max = bounds.bounds or (0, 0, 0, 0)
        advance = font['hmtx'][name][0]
        gid = font.getGlyphID(name)
        # HarfBuzz and the instanced font must agree, or the kerning below would be skewed.
        assert hb_font.get_glyph_h_advance(gid) == advance, (file_name, char)
        gids[char] = gid
        glyphs[char] = [advance, round(x_min), round(y_min), round(x_max), round(y_max), pen.getCommands()]

    kerning = {}
    for first in gids:
        for second in gids:
            buffer = hb.Buffer()
            buffer.add_str(first + second)
            buffer.guess_segment_properties()
            hb.shape(hb_font, buffer, {'kern': True, 'liga': False, 'calt': False})
            infos, positions = buffer.glyph_infos, buffer.glyph_positions
            if [info.codepoint for info in infos] != [gids[first], gids[second]]:
                continue  # a substitution happened; plain pair kerning does not apply
            adjust = positions[0].x_advance - glyphs[first][0] + positions[1].x_offset
            if adjust:
                kerning[first + second] = adjust

    return {
        'source': file_name,
        'variation': coordinates or {},
        'upm': font['head'].unitsPerEm,
        'ascender': font['hhea'].ascent,
        'descender': font['hhea'].descent,
        'cap': os2.sCapHeight,
        'xheight': os2.sxHeight,
        'glyphs': glyphs,
        'kern': kerning,
    }


def main() -> None:
    data = {
        'generator': 'scripts/build_glyphs.py',
        'license': NOTICE,
        'format': 'glyphs[char] = [advance, xMin, yMin, xMax, yMax, path in font units with y up]',
        'styles': {name: extract(*spec) for name, spec in STYLES.items()},
    }
    TARGET.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + '\n', encoding='utf-8')
    for name, style in data['styles'].items():
        print(f"{name:10} {len(style['glyphs']):3} glyphs, {len(style['kern']):4} kerning pairs")
    print(f'Wrote {TARGET.relative_to(ROOT)} ({TARGET.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()
