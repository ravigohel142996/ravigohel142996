"""NEURAL / FORGE drawing kit shared by the artwork and the metrics renderer.

Standard library only. A Canvas collects SVG markup, places text as vector
outlines through forge_type, and refuses to render when text leaves its
container or collides with other text or reserved diagram areas.
"""
from __future__ import annotations

import math
import random
from html import escape
from itertools import combinations

import forge_type as ft

# Palette: near-black, deep violet, electric cyan, lavender, subtle pink.
INK = '#05040b'
NIGHT = '#0a0816'
DUSK = '#130d29'
EDGE = '#2b2353'
EDGE_SOFT = '#1d1739'
VIOLET_DEEP = '#2a1166'
VIOLET = '#7c4dff'
VIOLET_SOFT = '#a084ff'
CYAN = '#22e1ff'
CYAN_SOFT = '#8ff3ff'
LAVENDER = '#c9bcff'
PINK = '#ff6ec7'
BLUE = '#5b8cff'
MINT = '#5ef2c8'
WHITE = '#f6f4ff'
BODY = '#d9d3f2'
MUTED = '#a59dc9'
DIM = '#6f6894'


class LayoutError(AssertionError):
    """Raised when text would be clipped, overflow, or collide."""


def num(value: float, digits: int = 2) -> str:
    text = f'{value:.{digits}f}'.rstrip('0').rstrip('.')
    return '0' if text in ('-0', '') else text


def rect_overlap(a, b, shrink: float = 0.0) -> bool:
    return (a[0] + shrink < b[2] - shrink and b[0] + shrink < a[2] - shrink
            and a[1] + shrink < b[3] - shrink and b[1] + shrink < a[3] - shrink)


class Canvas:
    def __init__(self, width: float, height: float, title: str, desc: str):
        self.width, self.height = width, height
        self.title, self.desc = title, desc
        self.defs: list[str] = []
        self.body: list[str] = []
        self.glyphs: dict[str, str | None] = {}
        self.texts: list[dict] = []
        self.reserved: list[tuple] = []
        self._counter = 0

    # -- structure -------------------------------------------------------
    def uid(self, prefix: str) -> str:
        self._counter += 1
        return f'{prefix}{self._counter}'

    def add(self, *parts: str) -> None:
        self.body.extend(parts)

    def define(self, *parts: str) -> None:
        self.defs.extend(parts)

    def reserve(self, box, name: str) -> None:
        """Mark a diagram/icon area that ordinary text must not overlap."""
        self.reserved.append((tuple(box), name))

    # -- paint servers ---------------------------------------------------
    def linear(self, stops, x1=0, y1=0, x2=1, y2=0, units: str | None = None) -> str:
        gid = self.uid('lg')
        unit = f' gradientUnits="{units}"' if units else ''
        coords = f'x1="{num(x1, 3)}" y1="{num(y1, 3)}" x2="{num(x2, 3)}" y2="{num(y2, 3)}"'
        self.define(f'<linearGradient id="{gid}" {coords}{unit}>{_stops(stops)}</linearGradient>')
        return f'url(#{gid})'

    def radial(self, stops, cx=.5, cy=.5, r=.5, units: str | None = None, fx=None, fy=None) -> str:
        gid = self.uid('rg')
        unit = f' gradientUnits="{units}"' if units else ''
        focus = f' fx="{num(fx, 3)}" fy="{num(fy, 3)}"' if fx is not None else ''
        self.define(f'<radialGradient id="{gid}" cx="{num(cx, 3)}" cy="{num(cy, 3)}" r="{num(r, 3)}"{focus}{unit}>{_stops(stops)}</radialGradient>')
        return f'url(#{gid})'

    def blur(self, deviation: float) -> str:
        fid = self.uid('bl')
        self.define(f'<filter id="{fid}" x="-60%" y="-60%" width="220%" height="220%" color-interpolation-filters="sRGB">'
                    f'<feGaussianBlur stdDeviation="{num(deviation)}"/></filter>')
        return f'url(#{fid})'

    # -- text --------------------------------------------------------------
    def text(self, value: str, x: float, y: float, *, style: str = 'text', size: float = 14, fill: str = WHITE,
             tracking: float = 0.0, anchor: str = 'start', opacity: float | None = None, mode: str = 'use',
             within=None, overlap_ok: bool = False, extra: str = '', missing: str = 'raise'):
        """Place text with its baseline at (x, y); returns the ink bounding box."""
        box = ft.ink_box(value, style, size, x, y, tracking, anchor, missing)
        self.texts.append({'text': value, 'box': box, 'within': tuple(within or (0, 0, self.width, self.height)),
                           'overlap_ok': overlap_ok})
        alpha = f' opacity="{num(opacity)}"' if opacity is not None else ''
        if mode == 'path':
            data = ft.path_data(value, style, size, x, y, tracking, anchor, missing=missing)
            self.add(f'<path d="{data}" fill="{fill}"{alpha}{extra}/>')
            return box
        placed, width = ft.layout(value, style, size, tracking, missing)
        x0 = x - width / 2 if anchor == 'middle' else x - width if anchor == 'end' else x
        scale = size / ft.style(style)['upm']
        uses = []
        for char, offset in placed:
            gid = ft.glyph_id(style, char)
            if gid not in self.glyphs:
                self.glyphs[gid] = ft.glyph_def(style, char)
            if self.glyphs[gid]:
                position = f' x="{num(offset, 1)}"' if abs(offset) > 0.04 else ''
                uses.append(f'<use href="#{gid}"{position}/>')
        transform = f'translate({num(x0)} {num(y)}) scale({num(scale, 5)} {num(-scale, 5)})'
        self.add(f'<g fill="{fill}"{alpha} transform="{transform}"{extra}>{"".join(uses)}</g>')
        return box

    def measure(self, value: str, style: str, size: float, tracking: float = 0.0) -> float:
        return ft.measure(value, style, size, tracking)

    def fit(self, value: str, style: str, size: float, max_width: float, tracking: float = 0.0, minimum: float = 8) -> float:
        """Largest size <= size at which value fits max_width."""
        while size > minimum and ft.measure(value, style, size, tracking) > max_width:
            size -= 0.5
        return size

    # -- validation and output -------------------------------------------
    def check(self, tolerance: float = 0.6) -> None:
        problems = []
        for item in self.texts:
            x0, y0, x1, y1 = item['box']
            wx0, wy0, wx1, wy1 = item['within']
            if x0 < wx0 - tolerance or y0 < wy0 - tolerance or x1 > wx1 + tolerance or y1 > wy1 + tolerance:
                problems.append(f"text {item['text']!r} {tuple(round(v, 1) for v in item['box'])} "
                                f"leaves {tuple(round(v, 1) for v in item['within'])}")
            if not item['overlap_ok']:
                for box, name in self.reserved:
                    if rect_overlap(item['box'], box, 0.5):
                        problems.append(f"text {item['text']!r} overlaps reserved area {name}")
        for a, b in combinations([t for t in self.texts if not t['overlap_ok']], 2):
            if rect_overlap(a['box'], b['box'], 0.5):
                problems.append(f"text {a['text']!r} collides with {b['text']!r}")
        if problems:
            raise LayoutError(f'{self.title}:\n  ' + '\n  '.join(problems))

    def svg(self) -> str:
        self.check()
        glyphs = ''.join(f'<path id="{gid}" d="{data}"/>' for gid, data in self.glyphs.items() if data)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(self.width)}" height="{num(self.height)}" '
            f'viewBox="0 0 {num(self.width)} {num(self.height)}" role="img" aria-labelledby="title desc">\n'
            f'<title id="title">{escape(self.title)}</title>\n'
            f'<desc id="desc">{escape(self.desc)}</desc>\n'
            f'<defs>{glyphs}{"".join(self.defs)}</defs>\n'
            + '\n'.join(self.body) + '\n</svg>\n'
        )


def _stops(stops) -> str:
    out = []
    for stop in stops:
        offset, color = stop[0], stop[1]
        opacity = f' stop-opacity="{num(stop[2])}"' if len(stop) > 2 else ''
        out.append(f'<stop offset="{num(offset, 3)}" stop-color="{color}"{opacity}/>')
    return ''.join(out)


# -- motifs -----------------------------------------------------------------
def panel(c: Canvas, x, y, w, h, radius=20, *, accent=VIOLET, glow=None, edge=None, base=(DUSK, NIGHT, INK),
          grid: bool = True) -> None:
    """Dark glass panel with an atmospheric glow and a lit hairline edge."""
    fill = c.linear([(0, base[0]), (.55, base[1]), (1, base[2])], 0, 0, 0, 1)
    c.add(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="{num(radius)}" fill="{fill}"/>')
    clip = c.uid('clip')
    c.define(f'<clipPath id="{clip}"><rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="{num(radius)}"/></clipPath>')
    layers = []
    for gx, gy, gr, color, alpha in (glow or [(x + w * .85, y + h * .1, max(w, h) * .55, accent, .32)]):
        paint = c.radial([(0, color, alpha), (.45, color, alpha * .35), (1, color, 0)], gx, gy, gr, 'userSpaceOnUse')
        layers.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{paint}"/>')
    if grid:
        pattern = c.uid('dots')
        c.define(f'<pattern id="{pattern}" width="14" height="14" patternUnits="userSpaceOnUse">'
                 f'<circle cx="1" cy="1" r=".7" fill="{LAVENDER}"/></pattern>')
        fade = c.uid('fade')
        c.define(f'<linearGradient id="{fade}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                 f'<stop offset=".6" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity=".3"/></linearGradient>')
        mask = c.uid('mask')
        c.define(f'<mask id="{mask}"><rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="url(#{fade})"/></mask>')
        layers.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="url(#{pattern})" opacity=".07" mask="url(#{mask})"/>')
    c.add(f'<g clip-path="url(#{clip})">{"".join(layers)}</g>')
    stroke = edge or c.linear([(0, CYAN, .55), (.35, accent, .35), (.7, EDGE, .9), (1, accent, .45)], 0, 0, 1, 1)
    c.add(f'<rect x="{num(x + .5)}" y="{num(y + .5)}" width="{num(w - 1)}" height="{num(h - 1)}" rx="{num(radius - .5)}" '
          f'fill="none" stroke="{stroke}"/>')
    rule(c, x + radius, y + 1, x + w - radius, y + 1, [(0, '#ffffff', 0), (.5, '#ffffff', .16), (1, '#ffffff', 0)])


def rule(c: Canvas, x1, y1, x2, y2, stops, width: float = 1.0, extra: str = '') -> None:
    """Straight line with a gradient along its length.

    The gradient uses userSpaceOnUse coordinates on purpose: a horizontal or
    vertical path has a zero-size bounding box, and renderers (browsers and
    resvg alike) skip objectBoundingBox gradients on such shapes entirely.
    """
    paint = c.linear(stops, x1, y1, x2, y2, 'userSpaceOnUse')
    c.add(f'<path d="M{num(x1)} {num(y1)}L{num(x2)} {num(y2)}" stroke="{paint}" stroke-width="{num(width)}" fill="none"{extra}/>')


def stars(c: Canvas, seed: int, box, count: int, avoid=(), colors=(WHITE, LAVENDER, CYAN_SOFT), max_radius=1.15,
          opacity=(.18, .75)) -> None:
    """Restrained star particles, deterministic per seed."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    dots, tries = [], 0
    while len(dots) < count and tries < count * 40:
        tries += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any(a[0] <= x <= a[2] and a[1] <= y <= a[3] for a in avoid):
            continue
        r = max_radius * (rng.random() ** 2.2) + .3
        alpha = rng.uniform(*opacity) * (0.55 if r < .6 else 1)
        dots.append(f'<circle cx="{num(x, 1)}" cy="{num(y, 1)}" r="{num(r)}" fill="{rng.choice(colors)}" opacity="{num(alpha)}"/>')
    c.add(f'<g>{"".join(dots)}</g>')


def glint(c: Canvas, x, y, size, color=WHITE, opacity=.9) -> None:
    """Four-point lens glint."""
    s, t = size, size * .16
    path = (f'M{num(x)} {num(y - s)}Q{num(x + t)} {num(y - t)} {num(x + s)} {num(y)}'
            f'Q{num(x + t)} {num(y + t)} {num(x)} {num(y + s)}Q{num(x - t)} {num(y + t)} {num(x - s)} {num(y)}'
            f'Q{num(x - t)} {num(y - t)} {num(x)} {num(y - s)}Z')
    halo = c.radial([(0, color, .45 * opacity), (1, color, 0)], x, y, size * 1.3, 'userSpaceOnUse')
    c.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(size * 1.3)}" fill="{halo}"/>'
          f'<path d="{path}" fill="{color}" opacity="{num(opacity)}"/>')


def corner_marks(c: Canvas, x, y, w, h, length=10, color=CYAN, opacity=.7, width=1.2) -> None:
    """Registration brackets on the four corners of a frame."""
    L = length
    d = (f'M{num(x)} {num(y + L)}V{num(y)}H{num(x + L)}M{num(x + w - L)} {num(y)}H{num(x + w)}V{num(y + L)}'
         f'M{num(x + w)} {num(y + h - L)}V{num(y + h)}H{num(x + w - L)}M{num(x + L)} {num(y + h)}H{num(x)}V{num(y + h - L)}')
    c.add(f'<path d="{d}" stroke="{color}" stroke-width="{num(width)}" opacity="{num(opacity)}" fill="none" stroke-linecap="square"/>')


def ticks(c: Canvas, x0, x1, y, step=8, major=5, color=LAVENDER, opacity=.35, height=4) -> None:
    """A technical ruler: short ticks with taller majors."""
    parts, i, x = [], 0, x0
    while x <= x1 + .01:
        tall = height * (1.9 if i % major == 0 else 1)
        parts.append(f'M{num(x, 1)} {num(y)}v{num(-tall)}')
        x += step
        i += 1
    c.add(f'<path d="{"".join(parts)}" stroke="{color}" stroke-width=".8" opacity="{num(opacity)}"/>')


def chip(c: Canvas, x, y, label, color=CYAN, *, size=10, height=20, pad=8, style='mono-bold', tracking=.06,
         within=None, fill_alpha=.09, text_fill=None) -> float:
    """Pill label with a tinted fill; returns its width."""
    width = ft.measure(label, style, size, tracking) + pad * 2
    c.add(f'<rect x="{num(x + .5)}" y="{num(y + .5)}" width="{num(width - 1)}" height="{num(height - 1)}" rx="{num((height - 1) / 2)}" '
          f'fill="{color}" fill-opacity="{num(fill_alpha)}" stroke="{color}" stroke-opacity=".45"/>')
    baseline = y + height / 2 + size * .35
    c.text(label, x + pad, baseline, style=style, size=size, fill=text_fill or color, tracking=tracking,
           within=within or (x, y, x + width, y + height))
    return width


def status_dot(c: Canvas, x, y, color=MINT, r=3.5) -> None:
    halo = c.radial([(0, color, .55), (1, color, 0)], x, y, r * 3.2, 'userSpaceOnUse')
    c.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r * 3.2)}" fill="{halo}"/>'
          f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{color}"/>')


def polar(cx, cy, r, angle_deg):
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)
