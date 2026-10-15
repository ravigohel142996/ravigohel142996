"""Standard-library text layout that turns strings into SVG vector outlines.

Glyph data comes from assets/fonts/forge-glyphs.json (see build_glyphs.py), so
artwork renders identically everywhere and the metrics workflow needs no pip.
Kerning and tracking are applied; every placement reports its ink bounds so the
renderers can fail loudly instead of shipping clipped or colliding text.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLYPH_FILE = ROOT / 'assets/fonts/forge-glyphs.json'
STYLE_IDS = {'display': 'd', 'text': 't', 'mono': 'm', 'mono-bold': 'b'}
_TOKEN = re.compile(r'[MLHVQCZmlhvqcz]|-?(?:\d+\.?\d*|\.\d+)')
_ARITY = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'Q': 4, 'C': 6, 'Z': 0}


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(GLYPH_FILE.read_text(encoding='utf-8'))


def style(name: str) -> dict:
    return _data()['styles'][name]


@lru_cache(maxsize=None)
def _outline(style_name: str, char: str) -> tuple:
    """Parse a glyph path into absolute ('M'|'L'|'Q'|'C'|'Z', points) commands."""
    raw = style(style_name)['glyphs'][char][5]
    tokens = _TOKEN.findall(raw)
    commands, i, cmd = [], 0, None
    x = y = start_x = start_y = 0.0
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in 'Zz':
                commands.append(('Z', ()))
                x, y = start_x, start_y
                continue
        if cmd is None:
            raise ValueError(f'bad path for {char!r}')
        upper = cmd.upper()
        values = [float(v) for v in tokens[i:i + _ARITY[upper]]]
        i += _ARITY[upper]
        if cmd.islower():  # relative coordinates
            if upper == 'H':
                values = [values[0] + x]
            elif upper == 'V':
                values = [values[0] + y]
            else:
                values = [v + (x if k % 2 == 0 else y) for k, v in enumerate(values)]
        if upper == 'H':
            points = ((values[0], y),)
        elif upper == 'V':
            points = ((x, values[0]),)
        else:
            points = tuple(zip(values[0::2], values[1::2]))
        kind = 'L' if upper in 'HV' else upper
        commands.append((kind, points))
        x, y = points[-1]
        if upper == 'M':
            start_x, start_y = x, y
            cmd = 'l' if cmd == 'm' else 'L'  # implicit lineto after a moveto
    return tuple(commands)


def _number(value: float, digits: int) -> str:
    text = f'{value:.{digits}f}'
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    if text in ('-0', ''):
        text = '0'
    if text.startswith('0.'):
        text = text[1:]
    elif text.startswith('-0.'):
        text = '-' + text[2:]
    return text


def _join(numbers: list[str]) -> str:
    out = ''
    for n in numbers:
        if out and not n.startswith('-'):
            out += ' '
        out += n
    return out


def _emit(commands, transform, digits: int) -> str:
    """Emit compact relative path data; rounding happens on absolute values to avoid drift."""
    parts, cx, cy, sx, sy = [], 0.0, 0.0, 0.0, 0.0
    scale = 10 ** digits
    for kind, points in commands:
        if kind == 'Z':
            parts.append('z')
            cx, cy = sx, sy
            continue
        absolute = [transform(px, py) for px, py in points]
        absolute = [(round(px * scale) / scale, round(py * scale) / scale) for px, py in absolute]
        rel = []
        for px, py in absolute:
            rel += [_number(px - cx, digits), _number(py - cy, digits)]
        parts.append(kind.lower() + _join(rel))
        cx, cy = absolute[-1]
        if kind == 'M':
            sx, sy = cx, cy
    return ''.join(parts)


def has_glyphs(text: str, style_name: str) -> bool:
    glyphs = style(style_name)['glyphs']
    return all(ch in glyphs for ch in text)


def _clean(text: str, style_name: str, missing: str) -> str:
    glyphs = style(style_name)['glyphs']
    if missing == 'replace':
        return ''.join(ch if ch in glyphs else '?' for ch in text)
    absent = sorted({ch for ch in text if ch not in glyphs})
    if absent:
        raise ValueError(f'{style_name} has no glyph for {absent!r} in {text!r}')
    return text


def layout(text: str, style_name: str, size: float, tracking: float = 0.0, missing: str = 'raise'):
    """Return ([(char, x_offset_in_font_units)], advance_width_px)."""
    text = _clean(text, style_name, missing)
    font = style(style_name)
    glyphs, kern, upm = font['glyphs'], font['kern'], font['upm']
    pen, placed, previous = 0.0, [], None
    for ch in text:
        if previous is not None:
            pen += kern.get(previous + ch, 0) + tracking * upm
        placed.append((ch, pen))
        pen += glyphs[ch][0]
        previous = ch
    return placed, pen * size / upm


def measure(text: str, style_name: str, size: float, tracking: float = 0.0) -> float:
    return layout(text, style_name, size, tracking, missing='replace')[1]


def ink_box(text: str, style_name: str, size: float, x: float, y: float, tracking: float = 0.0,
            anchor: str = 'start', missing: str = 'raise'):
    """Bounding box (x0, y0, x1, y1) of the painted outlines for a baseline at (x, y)."""
    placed, width = layout(text, style_name, size, tracking, missing)
    font = style(style_name)
    scale = size / font['upm']
    x = x - width / 2 if anchor == 'middle' else x - width if anchor == 'end' else x
    boxes = [font['glyphs'][ch][1:5] for ch, _ in placed]
    painted = [(off, b) for (ch, off), b in zip(placed, boxes) if b[2] > b[0]]
    if not painted:
        return (x, y, x + width, y)
    return (
        x + min(off + b[0] for off, b in painted) * scale,
        y - max(b[3] for _, b in painted) * scale,
        x + max(off + b[2] for off, b in painted) * scale,
        y - min(b[1] for _, b in painted) * scale,
    )


def path_data(text: str, style_name: str, size: float, x: float, y: float, tracking: float = 0.0,
              anchor: str = 'start', digits: int = 1, missing: str = 'raise') -> str:
    """Absolute-positioned outlines in canvas units (use for gradient or stroked text)."""
    placed, width = layout(text, style_name, size, tracking, missing)
    scale = size / style(style_name)['upm']
    x = x - width / 2 if anchor == 'middle' else x - width if anchor == 'end' else x
    parts = []
    for ch, offset in placed:
        commands = _outline(style_name, ch)
        if commands:
            ox = x + offset * scale
            parts.append(_emit(commands, lambda px, py, ox=ox: (ox + px * scale, y - py * scale), digits))
    # Each glyph starts with a relative move from (0, 0) only for the first; make all absolute moves.
    return ''.join(_absolute_first_move(p) for p in parts)


def _absolute_first_move(part: str) -> str:
    # _emit starts at (0, 0), so the first relative 'm' equals an absolute 'M'.
    return 'M' + part[1:] if part.startswith('m') else part


def glyph_id(style_name: str, char: str) -> str:
    return f'{STYLE_IDS[style_name]}{ord(char):x}'


def glyph_def(style_name: str, char: str) -> str | None:
    """Path data for a reusable glyph in font units (y up); None for blank glyphs."""
    commands = _outline(style_name, char)
    if not commands:
        return None
    return _absolute_first_move(_emit(commands, lambda px, py: (px, py), 0))


def wrap(text: str, style_name: str, size: float, max_width: float, tracking: float = 0.0) -> list[str]:
    """Greedy word wrap using real advance widths."""
    lines, current = [], ''
    for word in text.split():
        trial = f'{current} {word}'.strip()
        if current and measure(trial, style_name, size, tracking) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def truncate(text: str, style_name: str, size: float, max_width: float, tracking: float = 0.0) -> str:
    """Shorten text with an ellipsis until it fits max_width."""
    if measure(text, style_name, size, tracking) <= max_width:
        return text
    while text and measure(text + '…', style_name, size, tracking) > max_width:
        text = text[:-1]
    return text.rstrip(' -_.') + '…'
