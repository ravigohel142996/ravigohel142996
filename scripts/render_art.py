"""Render the NEURAL / FORGE SVG artwork used by README.md.

Standard library only (text outlines come from assets/fonts/forge-glyphs.json):

    python3 scripts/render_art.py          # write assets/art/*.svg
    python3 scripts/render_art.py --check  # fail if committed art is stale

Every Canvas validates its own layout, so clipped or colliding text raises an
error instead of being written.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import forge_svg as fs  # noqa: E402
from forge_svg import Canvas, num  # noqa: E402
import profile_content as content  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'assets/art'


# ---------------------------------------------------------------------------
# Icons: drawn on a 24-unit grid, stroked, rounded.
# ---------------------------------------------------------------------------
ICON_PATHS = {
    'react': None,  # composed below
    'node': 'M12 2.6l8.2 4.7v9.4L12 21.4l-8.2-4.7V7.3z',
    'stream': 'M3 8.2c3-2.6 6-2.6 9 0s6 2.6 9 0M3 12.4c3-2.6 6-2.6 9 0s6 2.6 9 0M3 16.6c3-2.6 6-2.6 9 0s6 2.6 9 0',
    'db': 'M5 6.2v11.6c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7V6.2M5 12c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7',
    'jupyter': 'M4.6 9.2a8.4 3.8 0 0 1 14.8 0M4.6 14.8a8.4 3.8 0 0 0 14.8 0',
    'git': 'M6.5 7.6v8.8M17.5 10.2c0 3.6-3.2 4.6-6.4 4.6H6.6',
    'terminal': 'M7 9.6l3.2 2.6L7 14.8M12.6 15.2h4.6',
    'editor': 'M3.5 8.6h17M7 12.4h6.5M7 15.6h9.5M7 18.4h4',
    'ml': 'M5.5 7.5L12 5M5.5 7.5L12 12M5.5 7.5L12 19M5.5 16.5L12 5M5.5 16.5L12 12M5.5 16.5L12 19M12 5l6.5 7M12 12h6.5M12 19l6.5-7',
    'cv': 'M2.6 12s3.6-6.2 9.4-6.2 9.4 6.2 9.4 6.2-3.6 6.2-9.4 6.2S2.6 12 2.6 12z',
    'genai': 'M5 3.6h7.2l3 3v5.2M5 3.6v15.2h6.4M7.6 9h4.6M7.6 12.2h3.4',
    'globe': 'M3.8 12h16.4M12 3.8c2.6 2.4 3.8 5.2 3.8 8.2s-1.2 5.8-3.8 8.2c-2.6-2.4-3.8-5.2-3.8-8.2s1.2-5.8 3.8-8.2z',
    'mail': 'M4.4 7.4l7.6 5.8 7.6-5.8',
}
ICON_TEXT = {'py': 'Py', 'js': 'JS', 'html': '</>', 'linkedin': 'in'}


def icon(c: Canvas, kind: str, x: float, y: float, size: float, color: str) -> None:
    """Draw icon `kind` inside the square (x, y, size)."""
    if kind in ICON_TEXT:
        label = ICON_TEXT[kind]
        style = 'display' if kind == 'linkedin' else 'mono-bold'
        font = size * (0.62 if kind == 'linkedin' else 0.5 if len(label) < 3 else 0.42)
        c.text(label, x + size / 2, y + size / 2 + font * .36, style=style, size=font, fill=color, anchor='middle',
               overlap_ok=True, within=(x, y, x + size, y + size))
        return
    s = size / 24
    stroke = f'stroke="{color}" stroke-width="{num(1.55)}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    parts = []
    if kind == 'react':
        for angle in (0, 60, 120):
            parts.append(f'<ellipse cx="12" cy="12" rx="9.6" ry="3.7" transform="rotate({angle} 12 12)"/>')
        parts.append(f'<circle cx="12" cy="12" r="1.7" fill="{color}" stroke="none"/>')
    else:
        parts.append(f'<path d="{ICON_PATHS[kind]}"/>')
    if kind == 'node':
        parts.append(f'<circle cx="12" cy="12" r="2.6" fill="{color}" fill-opacity=".35"/>')
    if kind == 'db':
        parts.append('<ellipse cx="12" cy="6.2" rx="7" ry="2.7"/>')
    if kind == 'jupyter':
        parts.append(f'<circle cx="12" cy="12" r="2.4" fill="{color}" fill-opacity=".35"/>'
                     f'<circle cx="5.2" cy="5.6" r="1.1" fill="{color}" stroke="none"/>'
                     f'<circle cx="18.6" cy="18.8" r="1.4" fill="{color}" stroke="none"/>')
    if kind == 'git':
        parts.append('<circle cx="6.5" cy="5.4" r="2.2"/><circle cx="6.5" cy="18.6" r="2.2"/><circle cx="17.5" cy="8" r="2.2"/>')
    if kind in ('terminal', 'editor'):
        parts.append('<rect x="3.2" y="4.4" width="17.6" height="15.4" rx="2.6"/>')
    if kind == 'ml':
        for cx, cy in ((5.5, 7.5), (5.5, 16.5), (12, 5), (12, 12), (12, 19), (18.5, 12)):
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="1.9" fill="{fs.NIGHT}"/>')
    if kind == 'cv':
        parts.append(f'<circle cx="12" cy="12" r="3.3"/><circle cx="12" cy="12" r="1.1" fill="{color}" stroke="none"/>')
    if kind == 'genai':
        parts.append(f'<path d="M17.4 12.6l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9z" fill="{color}" stroke-width="1"/>')
    if kind == 'globe':
        parts.append('<circle cx="12" cy="12" r="8.2"/>')
    if kind == 'mail':
        parts.append('<rect x="3.4" y="5.8" width="17.2" height="12.6" rx="2.4"/>')
    c.add(f'<g transform="translate({num(x)} {num(y)}) scale({num(s, 4)})" {stroke}>{"".join(parts)}</g>')


def icon_tile(c: Canvas, kind: str, x, y, size, color, dashed=False) -> None:
    dash = ' stroke-dasharray="3 3"' if dashed else ''
    c.add(f'<rect x="{num(x + .5)}" y="{num(y + .5)}" width="{num(size - 1)}" height="{num(size - 1)}" rx="{num(size * .26)}" '
          f'fill="{color}" fill-opacity=".09" stroke="{color}" stroke-opacity=".5"{dash}/>')
    pad = size * .2
    icon(c, kind, x + pad, y + pad, size - pad * 2, color)


# ---------------------------------------------------------------------------
# Navigation tabs
# ---------------------------------------------------------------------------
def nav_tab(section: content.Section) -> Canvas:
    w, h = 160, 44
    c = Canvas(w, h, f'{section.number} · {section.title}', f'Navigation tab: jump to section {section.number}, {section.title}.')
    fs.panel(c, 1, 1, w - 2, h - 2, 13, accent=section.accent, glow=[(w * .92, 2, 80, section.accent, .38)], grid=False)
    c.text(section.number, 15, 26.4, style='mono-bold', size=12, fill=section.accent, tracking=.04)
    c.add(f'<path d="M37.5 15v14" stroke="{fs.EDGE}" stroke-width="1"/>')
    c.text(section.short, 46, 26.8, style='display', size=13.5, fill=fs.WHITE, tracking=.08)
    c.text('↓', w - 14, 26.6, style='mono-bold', size=12, fill=fs.MUTED, anchor='end')
    return c


# ---------------------------------------------------------------------------
# Section banners and their glyphs
# ---------------------------------------------------------------------------
def glyph_human(c: Canvas, cx, cy, accent) -> None:
    ring = [fs.polar(cx, cy, 34, a) for a in range(-90, 270, 60)]
    lines = ''.join(f'M{num(cx)} {num(cy)}L{num(x)} {num(y)}' for x, y in ring)
    lines += ''.join(f'M{num(a[0])} {num(a[1])}L{num(b[0])} {num(b[1])}' for a, b in zip(ring, ring[1:] + ring[:1]))
    c.add(f'<path d="{lines}" stroke="{accent}" stroke-opacity=".45" stroke-width="1"/>')
    c.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="44" stroke="{fs.LAVENDER}" stroke-opacity=".22" stroke-dasharray="2 4" fill="none"/>')
    for x, y in ring:
        c.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="3.6" fill="{fs.NIGHT}" stroke="{accent}" stroke-width="1.3"/>')
    halo = c.radial([(0, accent, .7), (1, accent, 0)], cx, cy, 22, 'userSpaceOnUse')
    c.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="22" fill="{halo}"/><circle cx="{num(cx)}" cy="{num(cy)}" r="9" fill="{fs.WHITE}"/>'
          f'<circle cx="{num(cx)}" cy="{num(cy)}" r="14" stroke="{accent}" stroke-width="1.4" fill="none"/>')


def glyph_archive(c: Canvas, cx, cy, accent) -> None:
    for i, dy in enumerate((22, 4, -14)):
        y = cy + dy
        top = f'M{num(cx)} {num(y - 15)}L{num(cx + 40)} {num(y)}L{num(cx)} {num(y + 15)}L{num(cx - 40)} {num(y)}Z'
        side = f'M{num(cx - 40)} {num(y)}V{num(y + 8)}L{num(cx)} {num(y + 23)}L{num(cx + 40)} {num(y + 8)}V{num(y)}'
        alpha = .25 + i * .22
        c.add(f'<path d="{side}" fill="{fs.VIOLET_DEEP}" fill-opacity=".85" stroke="{accent}" stroke-opacity="{num(alpha)}"/>'
              f'<path d="{top}" fill="{fs.DUSK}" stroke="{accent}" stroke-opacity="{num(alpha + .2)}" stroke-width="1.2"/>')
    c.add(f'<path d="M{num(cx - 14)} {num(cy - 19)}h28" stroke="{fs.CYAN}" stroke-width="1.6" stroke-linecap="round"/>')


def glyph_tools(c: Canvas, cx, cy, accent) -> None:
    pins = ''
    for k in range(-2, 3):
        o = k * 9
        pins += (f'M{num(cx + o)} {num(cy - 30)}v-9M{num(cx + o)} {num(cy + 30)}v9'
                 f'M{num(cx - 30)} {num(cy + o)}h-9M{num(cx + 30)} {num(cy + o)}h9')
    c.add(f'<path d="{pins}" stroke="{accent}" stroke-opacity=".7" stroke-width="1.4" stroke-linecap="round"/>')
    c.add(f'<rect x="{num(cx - 30)}" y="{num(cy - 30)}" width="60" height="60" rx="10" fill="{fs.DUSK}" stroke="{accent}" stroke-width="1.4"/>')
    hexagon = ' '.join(f'{num(x)},{num(y)}' for x, y in (fs.polar(cx, cy, 14, a) for a in range(-90, 270, 60)))
    halo = c.radial([(0, fs.CYAN, .6), (1, fs.CYAN, 0)], cx, cy, 20, 'userSpaceOnUse')
    c.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="20" fill="{halo}"/>'
          f'<polygon points="{hexagon}" fill="{fs.NIGHT}" stroke="{fs.CYAN}" stroke-width="1.5"/>'
          f'<circle cx="{num(cx)}" cy="{num(cy)}" r="4" fill="{fs.WHITE}"/>')


def glyph_proof(c: Canvas, cx, cy, accent) -> None:
    x0, y0 = cx - 42, cy + 32
    c.add(f'<path d="M{num(x0)} {num(cy - 38)}V{num(y0)}H{num(cx + 46)}" stroke="{fs.LAVENDER}" stroke-opacity=".45" fill="none"/>')
    for i, hgt in enumerate((18, 30, 24, 44)):
        x = x0 + 9 + i * 19
        c.add(f'<rect x="{num(x)}" y="{num(y0 - hgt)}" width="11" height="{num(hgt)}" rx="2" fill="{accent}" fill-opacity="{num(.25 + i * .15)}"/>')
    pts = [(x0 + 14, y0 - 26), (x0 + 33, y0 - 38), (x0 + 52, y0 - 33), (x0 + 72, y0 - 54)]
    c.add(f'<polyline points="{" ".join(f"{num(x)},{num(y)}" for x, y in pts)}" stroke="{fs.CYAN}" stroke-width="1.6" fill="none"/>')
    bx, by = cx + 30, cy - 26
    c.add(f'<circle cx="{num(bx)}" cy="{num(by)}" r="13" fill="{fs.NIGHT}" stroke="{fs.MINT}" stroke-width="1.5"/>'
          f'<path d="M{num(bx - 5.5)} {num(by)}l3.8 3.8 7.2-7.6" stroke="{fs.MINT}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


def glyph_mission(c: Canvas, cx, cy, accent) -> None:
    tx, ty = cx + 16, cy - 8
    c.add(f'<circle cx="{num(tx)}" cy="{num(ty)}" r="30" stroke="{accent}" stroke-opacity=".35" fill="none"/>'
          f'<circle cx="{num(tx)}" cy="{num(ty)}" r="18" stroke="{accent}" stroke-opacity=".7" fill="none"/>'
          f'<circle cx="{num(tx)}" cy="{num(ty)}" r="5" fill="{fs.WHITE}"/>'
          f'<path d="M{num(tx)} {num(ty - 38)}v12M{num(tx)} {num(ty + 26)}v12M{num(tx - 38)} {num(ty)}h12M{num(tx + 26)} {num(ty)}h12" '
          f'stroke="{fs.LAVENDER}" stroke-opacity=".6" stroke-width="1.2"/>')
    c.add(f'<path d="M{num(cx - 50)} {num(cy + 40)}C{num(cx - 30)} {num(cy + 10)} {num(cx - 18)} {num(cy + 4)} {num(tx - 7)} {num(ty + 5)}" '
          f'stroke="{fs.CYAN}" stroke-width="1.7" fill="none" stroke-dasharray="1 0" stroke-linecap="round"/>'
          f'<path d="M{num(tx - 7)} {num(ty + 5)}l-8.5-1.2M{num(tx - 7)} {num(ty + 5)}l-3.2 7.8" stroke="{fs.CYAN}" stroke-width="1.7" stroke-linecap="round"/>')
    fs.glint(c, cx - 44, cy - 30, 6, fs.PINK, .85)


SECTION_GLYPHS = {'01': glyph_human, '02': glyph_archive, '03': glyph_tools, '04': glyph_proof, '05': glyph_mission}


def section_banner(section: content.Section, seed: int) -> Canvas:
    W, H = 840, 156
    c = Canvas(W, H, f'{section.number} — {section.title}',
               f'Section {section.number} of 05: {section.title}. {section.subtitle.lstrip("/ ")}.')
    fs.panel(c, 1, 1, W - 2, H - 2, 22, accent=section.accent,
             glow=[(W * .87, 6, 300, section.accent, .34), (40, H, 230, fs.VIOLET, .16)])
    fs.stars(c, seed, (16, 12, W - 16, H - 14), 30, avoid=[(26, 22, 670, 134)])
    gradient = c.linear([(0, fs.CYAN), (1, fs.VIOLET_SOFT)], 30, 0, 175, 0, 'userSpaceOnUse')
    glow = c.blur(9)
    c.text(section.number, 30, 117, style='display', size=104, fill=section.accent, mode='path', opacity=.22,
           extra=f' filter="{glow}"', overlap_ok=True)
    c.text(section.number, 30, 117, style='display', size=104, fill=gradient, mode='path',
           extra=f' fill-opacity=".14" stroke="{gradient}" stroke-width="1.5"')
    fs.rule(c, 190, 34, 190, 122, [(0, section.accent, 0), (.5, section.accent, .8), (1, section.accent, 0)], 1.2)
    text_right = 668
    c.text(f'SECTION {section.number} / 05', 212, 50, style='mono-bold', size=11, fill=section.accent, tracking=.2)
    kicker = 212 + c.measure(f'SECTION {section.number} / 05', 'mono-bold', 11, .2) + 12
    c.text(f'· {section.codename}', kicker, 50, style='mono', size=11, fill=fs.MUTED, tracking=.2)
    size = c.fit(section.title, 'display', 36, text_right - 212, -.01)
    c.text(section.title, 211, 94, style='display', size=size, fill=fs.WHITE, tracking=-.01, within=(205, 0, text_right, H))
    c.text(section.subtitle, 212, 123, style='mono', size=11.5, fill=fs.LAVENDER, opacity=.85, within=(205, 0, text_right, H))
    frame = (694, 26, 814, 130)
    c.reserve(frame, 'glyph frame')
    fs.corner_marks(c, frame[0], frame[1], frame[2] - frame[0], frame[3] - frame[1], 9, section.accent, .75)
    SECTION_GLYPHS[section.number](c, (frame[0] + frame[2]) / 2, (frame[1] + frame[3]) / 2, section.accent)
    fs.ticks(c, 212, 664, 146, 8, 5, fs.LAVENDER, .28, 3.5)
    return c


# ---------------------------------------------------------------------------
# 01 — profile panel with a neural interest map
# ---------------------------------------------------------------------------
def profile_panel() -> Canvas:
    W, H = 840, 300
    c = Canvas(W, H, 'Ravi Gohel — operator profile',
               'B.Tech CSE (AI & ML) student. Student by chapter, builder by instinct. Open to work: AI/ML, Python and GenAI '
               'internships and jobs, remote or in India; also hackathons and collaboration. Interests mapped as a neural '
               'network: practical AI, machine learning, computer vision, GenAI, RAG, automation and full-stack development, '
               'feeding into intelligent systems.')
    fs.panel(c, 1, 1, W - 2, H - 2, 22, accent=fs.CYAN,
             glow=[(640, 150, 300, fs.VIOLET, .30), (60, 20, 240, fs.CYAN, .10)])
    fs.stars(c, 101, (14, 12, W - 14, H - 12), 34, avoid=[(24, 24, 412, 284), (430, 24, 820, 284)])
    left = (24, 16, 410, 290)
    c.text('OPERATOR PROFILE', 34, 50, style='mono-bold', size=11, fill=fs.CYAN, tracking=.22, within=left)
    c.text('Ravi Gohel', 32, 102, style='display', size=48, fill=fs.WHITE, tracking=-.02, within=left)
    c.text('B.Tech CSE (AI & ML) student', 34, 134, style='text', size=17, fill=fs.LAVENDER, within=left)
    c.text('Student by chapter. Builder by instinct.', 34, 160, style='text', size=14.5, fill=fs.MUTED, within=left)
    # status pill
    label = 'OPEN TO WORK'
    width = c.measure(label, 'mono-bold', 10.5, .16) + 40
    c.add(f'<rect x="34.5" y="178.5" width="{num(width)}" height="25" rx="12.5" fill="{fs.MINT}" fill-opacity=".08" stroke="{fs.MINT}" stroke-opacity=".55"/>')
    fs.status_dot(c, 50, 191, fs.MINT, 3.6)
    c.text(label, 62, 195, style='mono-bold', size=10.5, fill=fs.MINT, tracking=.16, within=left)
    rows = (('ROLES', 'AI/ML · Python · GenAI internships & jobs'), ('WHERE', 'Remote / India'), ('ALSO', 'Hackathons · collaboration'))
    for i, (key, value) in enumerate(rows):
        y = 234 + i * 21
        c.text(key, 34, y, style='mono-bold', size=10, fill=fs.DIM, tracking=.14, within=left)
        c.text('/', 86, y, style='mono', size=10, fill=fs.VIOLET_SOFT, within=left)
        c.text(value, 100, y, style='mono', size=10.5, fill=fs.BODY, within=left)
    fs.rule(c, 420, 30, 420, 270, [(0, fs.LAVENDER, 0), (.5, fs.LAVENDER, .35), (1, fs.LAVENDER, 0)])

    # neural interest map
    region = (432, 18, 820, 286)
    a_x, b_x, o_x = 584, 682, 768
    inputs = [(a_x, 60 + i * 31.5) for i in range(len(content.INTERESTS))]
    hidden = [(b_x, 92 + i * 42) for i in range(4)]
    out = (o_x, 155)
    wires = ''.join(f'M{num(x1)} {num(y1)}C{num(x1 + 46)} {num(y1)} {num(x2 - 46)} {num(y2)} {num(x2)} {num(y2)}'
                    for x1, y1 in inputs for x2, y2 in hidden)
    c.add(f'<path d="{wires}" stroke="{fs.LAVENDER}" stroke-opacity=".16" stroke-width=".9" fill="none"/>')
    strong = ''.join(f'M{num(x1)} {num(y1)}C{num(x1 + 40)} {num(y1)} {num(out[0] - 40)} {num(out[1])} {num(out[0])} {num(out[1])}'
                     for x1, y1 in hidden)
    c.add(f'<path d="{strong}" stroke="{c.linear([(0, fs.VIOLET_SOFT, .5), (1, fs.CYAN, .9)], b_x, 0, o_x, 0, "userSpaceOnUse")}" stroke-width="1.4" fill="none"/>')
    for (x, y), name in zip(inputs, content.INTERESTS):
        c.text(name, x - 14, y + 3.6, style='mono-bold', size=10, fill=fs.BODY, tracking=.08, anchor='end', within=region)
        c.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="4.2" fill="{fs.NIGHT}" stroke="{fs.CYAN}" stroke-width="1.3"/>')
    for x, y in hidden:
        c.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="6" fill="{fs.DUSK}" stroke="{fs.VIOLET_SOFT}" stroke-width="1.4"/>'
              f'<circle cx="{num(x)}" cy="{num(y)}" r="2" fill="{fs.LAVENDER}"/>')
    for t, (x1, y1), (x2, y2) in ((.35, inputs[1], hidden[0]), (.6, inputs[4], hidden[2]), (.5, hidden[1], out)):
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        fs.status_dot(c, px, py, fs.CYAN, 1.8)
    halo = c.radial([(0, fs.CYAN, .55), (1, fs.CYAN, 0)], out[0], out[1], 34, 'userSpaceOnUse')
    c.add(f'<circle cx="{num(out[0])}" cy="{num(out[1])}" r="34" fill="{halo}"/>'
          f'<circle cx="{num(out[0])}" cy="{num(out[1])}" r="15" fill="{fs.NIGHT}" stroke="{fs.CYAN}" stroke-width="1.6"/>'
          f'<circle cx="{num(out[0])}" cy="{num(out[1])}" r="6" fill="{fs.WHITE}"/>')
    c.text('INTELLIGENT', out[0], out[1] + 36, style='mono-bold', size=9.5, fill=fs.CYAN, tracking=.1, anchor='middle', within=region)
    c.text('SYSTEMS', out[0], out[1] + 49, style='mono-bold', size=9.5, fill=fs.CYAN, tracking=.1, anchor='middle', within=region)
    for x, label in ((a_x, 'INTERESTS'), (b_x, 'PRACTICE'), (o_x, 'OUTPUT')):
        c.text(label, x, 34, style='mono', size=9, fill=fs.DIM, tracking=.16, anchor='middle', within=region)
    return c


# ---------------------------------------------------------------------------
# 02 — project cards
# ---------------------------------------------------------------------------
def diagram_forecast(c: Canvas, x0, y0, w, h, accent):
    bx, by = x0 + 8, y0 + h - 14
    c.add(f'<path d="M{num(bx)} {num(y0 + 6)}V{num(by)}H{num(x0 + w - 4)}" stroke="{fs.LAVENDER}" stroke-opacity=".35" fill="none"/>')
    hist = [(0, 52), (12, 44), (24, 48), (36, 34), (48, 40), (60, 26), (72, 31)]
    pts = [(bx + 6 + px, by - py) for px, py in hist]
    fut = [(bx + 78, by - 25), (bx + 92, by - 34), (bx + 106, by - 30), (bx + 120, by - 44)]
    (sx0, sy0), (sx1, sy1) = pts[-1], fut[-1]
    wedge = [(sx0, sy0 - 2), (sx1, sy1 - 15), (sx1, sy1 + 15), (sx0, sy0 + 2)]
    c.add(f'<polygon points="{" ".join(f"{num(x)},{num(y)}" for x, y in wedge)}" fill="{accent}" fill-opacity=".16" '
          f'stroke="{accent}" stroke-opacity=".3" stroke-dasharray="2 3"/>')
    c.add(f'<polyline points="{" ".join(f"{num(x)},{num(y)}" for x, y in pts)}" stroke="{accent}" stroke-width="1.7" fill="none" stroke-linejoin="round"/>')
    c.add(f'<polyline points="{" ".join(f"{num(x)},{num(y)}" for x, y in [pts[-1]] + fut)}" stroke="{accent}" stroke-width="1.5" fill="none" stroke-dasharray="3 3"/>')
    ax, ay = pts[3]
    c.add(f'<circle cx="{num(ax)}" cy="{num(ay)}" r="7" stroke="{fs.PINK}" stroke-width="1.3" fill="none"/>'
          f'<circle cx="{num(ax)}" cy="{num(ay)}" r="2.6" fill="{fs.PINK}"/>')
    dx, dy = fut[-1]
    c.add(f'<path d="M{num(dx)} {num(dy - 8)}l8 8-8 8-8-8z" fill="{fs.NIGHT}" stroke="{fs.WHITE}" stroke-width="1.3"/>')
    c.text('FORECAST', bx + 4, by + 11, style='mono', size=8, fill=fs.DIM, tracking=.12, overlap_ok=True, within=(x0, y0, x0 + w, y0 + h))


def diagram_orbit(c: Canvas, x0, y0, w, h, accent):
    cx, cy, r = x0 + w * .46, y0 + h * .55, 30
    c.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{r}" fill="{fs.NIGHT}" stroke="{accent}" stroke-width="1.4"/>'
          f'<ellipse cx="{num(cx)}" cy="{num(cy)}" rx="12" ry="{r}" stroke="{accent}" stroke-opacity=".45" fill="none"/>'
          f'<path d="M{num(cx - r)} {num(cy)}h{2 * r}M{num(cx - 26)} {num(cy - 14)}h52M{num(cx - 26)} {num(cy + 14)}h52" stroke="{accent}" stroke-opacity=".35"/>')
    c.add(f'<ellipse cx="{num(cx)}" cy="{num(cy)}" rx="58" ry="17" transform="rotate(-18 {num(cx)} {num(cy)})" stroke="{fs.LAVENDER}" stroke-opacity=".55" stroke-dasharray="2 3" fill="none"/>')
    sx, sy = cx + 46, cy - 26
    c.add(f'<path d="M{num(sx)} {num(sy)}L{num(cx + 10)} {num(cy - 8)}" stroke="{fs.CYAN}" stroke-opacity=".7" stroke-dasharray="2 2"/>'
          f'<rect x="{num(sx - 4)}" y="{num(sy - 4)}" width="8" height="8" rx="1.5" fill="{fs.WHITE}"/>'
          f'<path d="M{num(sx - 13)} {num(sy)}h7M{num(sx + 6)} {num(sy)}h7" stroke="{fs.CYAN}" stroke-width="2.4"/>')
    px, py = cx - 10, cy + 8
    c.add(f'<circle cx="{num(px)}" cy="{num(py)}" r="3" fill="{fs.PINK}"/>'
          f'<circle cx="{num(px)}" cy="{num(py)}" r="8" stroke="{fs.PINK}" stroke-opacity=".7" fill="none"/>'
          f'<circle cx="{num(px)}" cy="{num(py)}" r="13" stroke="{fs.PINK}" stroke-opacity=".35" fill="none"/>')


def diagram_vision(c: Canvas, x0, y0, w, h, accent):
    fs.corner_marks(c, x0 + 6, y0 + 4, w - 12, h - 8, 10, fs.LAVENDER, .6)
    cx, base = x0 + w * .45, y0 + h - 12
    c.add(f'<path d="M{num(cx - 15)} {num(base)}l4-30h22l4 30z" fill="{fs.DUSK}" stroke="{fs.LAVENDER}" stroke-opacity=".7"/>'
          f'<circle cx="{num(cx)}" cy="{num(base - 42)}" r="9" fill="{fs.DUSK}" stroke="{fs.LAVENDER}" stroke-opacity=".7"/>'
          f'<path d="M{num(cx - 12)} {num(base - 46)}a12 10 0 0 1 24 0z" fill="{fs.PINK}" fill-opacity=".85"/>')
    c.add(f'<rect x="{num(cx - 26)}" y="{num(base - 62)}" width="52" height="64" rx="3" stroke="{accent}" stroke-width="1.5" stroke-dasharray="4 3" fill="none"/>')
    tag = 'PPE'
    c.add(f'<rect x="{num(cx - 26)}" y="{num(base - 75)}" width="30" height="13" rx="2" fill="{accent}"/>')
    c.text(tag, cx - 22, base - 65.2, style='mono-bold', size=8.5, fill=fs.INK, tracking=.08, overlap_ok=True, within=(x0, y0, x0 + w, y0 + h))
    tx, ty = x0 + w - 24, y0 + 22
    c.add(f'<path d="M{num(tx)} {num(ty - 11)}l11 19h-22z" fill="{fs.NIGHT}" stroke="{fs.PINK}" stroke-width="1.4" stroke-linejoin="round"/>'
          f'<path d="M{num(tx)} {num(ty - 4)}v6" stroke="{fs.PINK}" stroke-width="1.6" stroke-linecap="round"/>'
          f'<circle cx="{num(tx)}" cy="{num(ty + 5)}" r="1" fill="{fs.PINK}"/>')
    c.add(f'<path d="M{num(x0 + 12)} {num(y0 + h * .58)}H{num(x0 + w - 12)}" stroke="{fs.CYAN}" stroke-opacity=".55"/>')


def diagram_gauge(c: Canvas, x0, y0, w, h, accent):
    cx, cy, r = x0 + 44, y0 + 60, 34
    colors = (fs.MINT, fs.CYAN, fs.LAVENDER, fs.PINK)
    for i, color in enumerate(colors):
        a1, a2 = 180 + i * 45 + 3, 180 + (i + 1) * 45 - 3
        p1, p2 = fs.polar(cx, cy, r, a1), fs.polar(cx, cy, r, a2)
        c.add(f'<path d="M{num(p1[0])} {num(p1[1])}A{r} {r} 0 0 1 {num(p2[0])} {num(p2[1])}" stroke="{color}" stroke-width="6" fill="none"/>')
    nx, ny = fs.polar(cx, cy, r - 10, 232)
    c.add(f'<path d="M{num(cx)} {num(cy)}L{num(nx)} {num(ny)}" stroke="{fs.WHITE}" stroke-width="2" stroke-linecap="round"/>'
          f'<circle cx="{num(cx)}" cy="{num(cy)}" r="4" fill="{fs.WHITE}"/>')
    c.text('RISK', cx, cy + 18, style='mono-bold', size=8.5, fill=fs.MUTED, tracking=.14, anchor='middle', overlap_ok=True, within=(x0, y0, x0 + w, y0 + h))
    for i, label in enumerate(('KYC', 'AML', 'LOAN')):
        y = y0 + 22 + i * 24
        bx = x0 + 92
        c.add(f'<rect x="{num(bx)}" y="{num(y - 7)}" width="13" height="13" rx="3" fill="{accent}" fill-opacity=".12" stroke="{accent}"/>'
              f'<path d="M{num(bx + 3)} {num(y)}l2.6 2.6 4.6-5" stroke="{fs.MINT}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
        c.text(label, bx + 18, y + 3.4, style='mono-bold', size=8.5, fill=fs.BODY, tracking=.08, overlap_ok=True, within=(x0, y0, x0 + w, y0 + h))


def diagram_retrieval(c: Canvas, x0, y0, w, h, accent):
    dx, dy = x0 + 6, y0 + 20
    c.add(f'<path d="M{num(dx)} {num(dy)}h18l7 7v29h-25z" fill="{fs.DUSK}" stroke="{fs.LAVENDER}" stroke-opacity=".8"/>'
          f'<path d="M{num(dx + 5)} {num(dy + 14)}h14M{num(dx + 5)} {num(dy + 21)}h14M{num(dx + 5)} {num(dy + 28)}h9" stroke="{fs.LAVENDER}" stroke-opacity=".6"/>')
    c.add(f'<path d="M{num(dx + 34)} {num(dy + 18)}h10" stroke="{accent}" stroke-width="1.4"/><path d="M{num(dx + 41)} {num(dy + 14)}l4 4-4 4" stroke="{accent}" stroke-width="1.4" fill="none"/>')
    vx, vy = x0 + 74, y0 + 40
    c.add(f'<circle cx="{num(vx)}" cy="{num(vy)}" r="22" fill="{accent}" fill-opacity=".07" stroke="{accent}" stroke-opacity=".45" stroke-dasharray="2 3"/>')
    import random as _random
    rng = _random.Random(7)
    for _ in range(16):
        a, rr = rng.uniform(0, math.tau), 17 * math.sqrt(rng.random())
        c.add(f'<circle cx="{num(vx + rr * math.cos(a))}" cy="{num(vy + rr * math.sin(a))}" r="1.5" fill="{fs.LAVENDER}" fill-opacity=".75"/>')
    for a in (40, 160, 280):
        px, py = fs.polar(vx, vy, 9, a)
        c.add(f'<circle cx="{num(px)}" cy="{num(py)}" r="2.6" fill="{fs.CYAN}"/>')
    c.add(f'<path d="M{num(vx + 25)} {num(vy)}h12" stroke="{accent}" stroke-width="1.4"/><path d="M{num(vx + 34)} {num(vy - 4)}l4 4-4 4" stroke="{accent}" stroke-width="1.4" fill="none"/>')
    ax, ay = x0 + w - 19, y0 + 40
    c.add(f'<path d="M{num(ax)} {num(ay - 13)}l3.4 9.6 9.6 3.4-9.6 3.4-3.4 9.6-3.4-9.6-9.6-3.4 9.6-3.4z" fill="{fs.WHITE}"/>')
    c.add(f'<rect x="{num(x0 + 40)}" y="{num(y0 + 74)}" width="{num(w - 46)}" height="18" rx="9" fill="{fs.NIGHT}" stroke="{accent}" stroke-opacity=".6"/>')
    c.text('TOP-K CONTEXT', x0 + 50, y0 + 86.5, style='mono-bold', size=8, fill=accent, tracking=.1, overlap_ok=True, within=(x0, y0, x0 + w, y0 + h))


def diagram_relief(c: Canvas, x0, y0, w, h, accent):
    px, py = x0 + 34, y0 + 44
    for rr, alpha in ((24, .25), (15, .45)):
        c.add(f'<ellipse cx="{num(px)}" cy="{num(py + 18)}" rx="{rr}" ry="{num(rr * .36)}" stroke="{accent}" stroke-opacity="{alpha}" fill="none"/>')
    c.add(f'<path d="M{num(px)} {num(py + 18)}c-9-11-14-17-14-24a14 14 0 0 1 28 0c0 7-5 13-14 24z" fill="{fs.DUSK}" stroke="{accent}" stroke-width="1.5"/>'
          f'<path d="M{num(px - 6)} {num(py - 4)}l6-5 6 5v7h-12z" fill="{accent}" fill-opacity=".85"/>')
    hx, hy = x0 + 66, y0 + 70
    pulse = f'M{num(hx)} {num(hy)}h12l5-12 6 22 6-16 4 6h22'
    c.add(f'<path d="{pulse}" stroke="{fs.PINK}" stroke-width="1.6" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')
    bx, by = x0 + 74, y0 + 14
    c.add(f'<path d="M{num(bx)} {num(by)}h50a6 6 0 0 1 6 6v18a6 6 0 0 1-6 6h-36l-9 8v-8h-5a6 6 0 0 1-6-6v-18a6 6 0 0 1 6-6z" fill="{fs.NIGHT}" stroke="{fs.LAVENDER}" stroke-opacity=".8"/>')
    for i in range(3):
        c.add(f'<circle cx="{num(bx + 17 + i * 11)}" cy="{num(by + 15)}" r="2.4" fill="{fs.LAVENDER}" fill-opacity="{num(.45 + i * .25)}"/>')


DIAGRAMS = {'forecast': diagram_forecast, 'orbit': diagram_orbit, 'vision': diagram_vision,
            'gauge': diagram_gauge, 'retrieval': diagram_retrieval, 'relief': diagram_relief}


def screen(c: Canvas, box, accent) -> None:
    """Framed viewport with a faint dot grid that hosts a card diagram."""
    x0, y0, x1, y1 = box
    dots = c.uid('dots')
    c.define(f'<pattern id="{dots}" width="9" height="9" patternUnits="userSpaceOnUse" x="{num(x0)}" y="{num(y0)}">'
             f'<circle cx="4.5" cy="4.5" r=".7" fill="{fs.LAVENDER}" fill-opacity=".28"/></pattern>')
    shade = c.radial([(0, accent, .12), (1, accent, 0)], .5, .45, .7)
    frame = f'x="{num(x0 + .5)}" y="{num(y0 + .5)}" width="{num(x1 - x0 - 1)}" height="{num(y1 - y0 - 1)}" rx="12"'
    c.add(f'<rect {frame} fill="{fs.INK}" fill-opacity=".55"/><rect {frame} fill="url(#{dots})"/>'
          f'<rect {frame} fill="{shade}" stroke="{accent}" stroke-opacity=".28"/>')


def project_card(project: content.Project, index: int) -> Canvas:
    W, H = 420, 272
    c = Canvas(W, H, f'{project.name} — {project.focus}',
               f'Project card {index} of 6. {project.name}: {project.description} Stack: {", ".join(project.stack)}. '
               f'Opens the source repository on GitHub.')
    fs.panel(c, 1, 1, W - 2, H - 2, 18, accent=project.accent,
             glow=[(W * .82, 30, 210, project.accent, .30), (0, H, 170, fs.VIOLET, .12)])
    fs.stars(c, 200 + index, (12, 10, W - 12, H - 12), 16, avoid=[(18, 14, 255, 156), (18, 158, W - 18, H - 14)])
    inner = (16, 10, W - 16, H - 10)
    c.text(f'02.{index}', 22, 33, style='mono-bold', size=10.5, fill=project.accent, tracking=.08, within=inner)
    kicker_x = 22 + c.measure(f'02.{index}', 'mono-bold', 10.5, .08) + 10
    c.text(project.kicker, kicker_x, 33, style='mono', size=9.5, fill=fs.MUTED, tracking=.12, within=inner)
    label = 'SOURCE ↗'
    chip_w = c.measure(label, 'mono-bold', 9, .08) + 16
    fs.chip(c, W - 20 - chip_w, 19, label, project.accent, size=9, height=19, tracking=.08)
    region = (266, 50, 402, 148)
    c.reserve(region, 'diagram')
    screen(c, (258, 44, 404, 154), project.accent)
    DIAGRAMS[project.diagram](c, region[0], region[1], region[2] - region[0], region[3] - region[1], project.accent)
    left = (16, 40, 254, 156)
    size = c.fit(project.name, 'display', 27, 230, -.01)
    c.text(project.name, 21, 82, style='display', size=size, fill=fs.WHITE, tracking=-.01, within=left)
    from forge_type import wrap
    focus = wrap(project.focus, 'text', 13, 228)
    if len(focus) > 2:
        raise fs.LayoutError(f'{project.name}: focus line needs {len(focus)} lines')
    for i, line in enumerate(focus):
        c.text(line, 22, 108 + i * 18, style='text', size=13, fill=project.accent, within=left)
    lines = wrap(project.description, 'text', 12.5, 376)
    if len(lines) > 2:
        raise fs.LayoutError(f'{project.name}: description needs {len(lines)} lines')
    for i, line in enumerate(lines):
        c.text(line, 22, 176 + i * 18.5, style='text', size=12.5, fill=fs.BODY, within=(16, 158, W - 16, 214))
    fs.rule(c, 22, 220.5, W - 22, 220.5, [(0, project.accent, .55), (1, project.accent, 0)])
    x = 22
    for tech in project.stack:
        x += fs.chip(c, x, 234, tech.upper(), project.accent, size=9, height=20, tracking=.06, within=(x, 234, W - 20, 254)) + 7
    if x - 7 > W - 20:
        raise fs.LayoutError(f'{project.name}: stack chips overflow')
    return c


# ---------------------------------------------------------------------------
# 03 — toolbox
# ---------------------------------------------------------------------------
def toolbox() -> Canvas:
    W, H = 840, 470
    tools = ', '.join(name for name, _, _ in content.TOOLS)
    exploring = ', '.join(name for name, _, _ in content.EXPLORING)
    c = Canvas(W, H, 'Tools of the trade — toolkit and frontiers',
               f'Tools I build with: {tools}. Topics I am exploring: {exploring}.')
    fs.panel(c, 1, 1, W - 2, H - 2, 22, accent=fs.BLUE,
             glow=[(W * .9, 20, 320, fs.BLUE, .22), (60, H - 40, 300, fs.PINK, .10), (W * .5, H, 260, fs.VIOLET, .14)])
    fs.stars(c, 303, (14, 12, W - 14, H - 12), 26, avoid=[(24, 20, W - 24, H - 20)])
    c.text('TOOLKIT', 32, 46, style='mono-bold', size=11, fill=fs.CYAN, tracking=.22)
    c.text('· WHAT I BUILD WITH', 32 + c.measure('TOOLKIT', 'mono-bold', 11, .22) + 10, 46, style='mono', size=11, fill=fs.MUTED, tracking=.16)
    # legend
    lx = W - 32
    c.text('EXPLORING', lx, 46, style='mono', size=9.5, fill=fs.MUTED, tracking=.14, anchor='end')
    ex_w = c.measure('EXPLORING', 'mono', 9.5, .14)
    c.add(f'<rect x="{num(lx - ex_w - 18)}" y="38" width="10" height="10" rx="2.5" fill="none" stroke="{fs.PINK}" stroke-dasharray="2 2"/>')
    tool_x = lx - ex_w - 34
    c.text('TOOL', tool_x, 46, style='mono', size=9.5, fill=fs.MUTED, tracking=.14, anchor='end')
    tw = c.measure('TOOL', 'mono', 9.5, .14)
    c.add(f'<rect x="{num(tool_x - tw - 18)}" y="38" width="10" height="10" rx="2.5" fill="{fs.CYAN}" fill-opacity=".2" stroke="{fs.CYAN}"/>')

    cols, gap, tile_h = 4, 12, 66
    tile_w = (W - 64 - gap * (cols - 1)) / cols
    tints = (fs.CYAN, fs.VIOLET_SOFT, fs.BLUE, fs.LAVENDER)
    for i, (name, kind, glyph) in enumerate(content.TOOLS):
        row, col = divmod(i, cols)
        count = min(cols, len(content.TOOLS) - row * cols)
        offset = (cols - count) * (tile_w + gap) / 2
        x = 32 + offset + col * (tile_w + gap)
        y = 66 + row * (tile_h + gap)
        tint = tints[(row + col) % len(tints)]
        c.add(f'<rect x="{num(x + .5)}" y="{num(y + .5)}" width="{num(tile_w - 1)}" height="{tile_h - 1}" rx="13" fill="{fs.NIGHT}" fill-opacity=".85" stroke="{fs.EDGE}"/>')
        fs.rule(c, x + 14, y + .8, x + tile_w - 14, y + .8, [(0, tint, 0), (.5, tint, .6), (1, tint, 0)])
        icon_tile(c, glyph, x + 12, y + 13, 40, tint)
        box = (x + 60, y + 6, x + tile_w - 8, y + tile_h - 6)
        size = c.fit(name, 'display', 16, box[2] - box[0])
        c.text(name, x + 62, y + 32, style='display', size=size, fill=fs.WHITE, within=box)
        c.text(kind, x + 62, y + 50, style='mono', size=8.5, fill=fs.MUTED, tracking=.1, within=box)

    y0 = 66 + 3 * (tile_h + gap) + 22
    fs.rule(c, 32, y0 - 10, W - 32, y0 - 10, [(0, fs.PINK, 0), (.5, fs.PINK, .45), (1, fs.PINK, 0)], extra=' stroke-dasharray="2 4"')
    c.text('EXPLORING', 32, y0 + 22, style='mono-bold', size=11, fill=fs.PINK, tracking=.22)
    c.text('· FRONTIERS I AM LEARNING, NOT CLAIMING TO HAVE MASTERED', 32 + c.measure('EXPLORING', 'mono-bold', 11, .22) + 10, y0 + 22,
           style='mono', size=10, fill=fs.MUTED, tracking=.08)
    gap2 = 14
    ew = (W - 64 - gap2 * 2) / 3
    eh = 84
    ey = y0 + 38
    for i, (name, note, glyph) in enumerate(content.EXPLORING):
        x = 32 + i * (ew + gap2)
        tint = (fs.PINK, fs.LAVENDER, fs.VIOLET_SOFT)[i]
        c.add(f'<rect x="{num(x + .5)}" y="{num(ey + .5)}" width="{num(ew - 1)}" height="{eh - 1}" rx="14" fill="{tint}" fill-opacity=".05" '
              f'stroke="{tint}" stroke-opacity=".6" stroke-dasharray="5 4"/>')
        icon_tile(c, glyph, x + 14, ey + 20, 44, tint, dashed=True)
        box = (x + 68, ey + 8, x + ew - 10, ey + eh - 8)
        c.text(name, x + 72, ey + 38, style='display', size=c.fit(name, 'display', 17.5, box[2] - box[0] - 4), fill=fs.WHITE, within=box)
        c.text(note, x + 72, ey + 58, style='mono', size=c.fit(note, 'mono', 9, box[2] - box[0] - 4), fill=fs.BODY, opacity=.85, within=box)
    if ey + eh > H - 16:
        raise fs.LayoutError('toolbox: exploring row overflows')
    return c


# ---------------------------------------------------------------------------
# 05 — contact panels and footer
# ---------------------------------------------------------------------------
CONTACT_KICKERS = {'linkedin': 'NETWORK', 'portfolio': 'SHOWCASE', 'email': 'DIRECT LINE'}


def contact_panel(slug, title, url, detail, action, accent) -> Canvas:
    W, H = 272, 128
    c = Canvas(W, H, f'{title} — {detail}', f'{title}: {detail}. Select to {action.lower()}.')
    fs.panel(c, 1, 1, W - 2, H - 2, 16, accent=accent, glow=[(W * .9, 10, 150, accent, .32)], grid=False)
    fs.stars(c, len(slug) * 31, (10, 8, W - 10, H - 8), 9, avoid=[(14, 12, W - 14, H - 12)])
    icon_tile(c, {'linkedin': 'linkedin', 'portfolio': 'globe', 'email': 'mail'}[slug], 18, 18, 44, accent)
    inner = (12, 8, W - 12, H - 8)
    c.text(CONTACT_KICKERS[slug], 76, 36, style='mono-bold', size=10, fill=accent, tracking=.2, within=inner)
    c.text(title, 75, 59, style='display', size=20, fill=fs.WHITE, tracking=-.01, within=inner)
    size = c.fit(detail, 'mono', 10.5, W - 40)
    c.text(detail, 20, 86, style='mono', size=size, fill=fs.BODY, within=inner)
    fs.rule(c, 20, 98.5, W - 20, 98.5, [(0, accent, .5), (1, accent, 0)])
    c.text(f'{action} ↗', 20, 117, style='mono-bold', size=10, fill=accent, tracking=.18, within=inner)
    return c


def footer() -> Canvas:
    W, H = 840, 240
    c = Canvas(W, H, 'Stay curious. Build bold.',
               'Closing banner: STAY CURIOUS. BUILD BOLD. A glowing crystal inside a ring floats above a perspective grid. '
               'Ravi Gohel — engineering intelligence.')
    fs.panel(c, 1, 1, W - 2, H - 2, 22, accent=fs.VIOLET,
             glow=[(W / 2, 70, 260, fs.VIOLET, .34), (W / 2, H, 360, fs.CYAN, .12), (90, 30, 200, fs.PINK, .07)])
    fs.stars(c, 404, (14, 12, W - 14, 176), 46, avoid=[(330, 14, 510, 108), (110, 112, 730, 186)])
    # perspective floor
    hy, vx = 188, W / 2
    clip = c.uid('floor')
    c.define(f'<clipPath id="{clip}"><rect x="1" y="{hy}" width="{W - 2}" height="{H - hy - 1}" rx="0"/></clipPath>')
    lines = ''.join(f'M{num(vx + k * 4)} {hy}L{num(vx + k * 120)} {H}' for k in range(-9, 10))
    rows_y = [hy + (H - hy) * (0.58 ** j) for j in range(7)]
    lines += ''.join(f'M1 {num(y, 1)}H{W - 1}' for y in rows_y)
    fade = c.linear([(0, fs.CYAN, 0), (.35, fs.CYAN, .32), (1, fs.VIOLET_SOFT, .55)], 0, hy, 0, H, 'userSpaceOnUse')
    c.add(f'<g clip-path="url(#{clip})"><path d="{lines}" stroke="{fade}" stroke-width=".9" fill="none"/></g>')
    fs.rule(c, 24, hy, W - 24, hy, [(0, fs.CYAN, 0), (.5, fs.CYAN, .9), (1, fs.CYAN, 0)], 1.2)
    # emblem: crystal inside a tilted ring
    ex, ey = W / 2, 60
    halo = c.radial([(0, fs.CYAN, .5), (.5, fs.VIOLET, .18), (1, fs.VIOLET, 0)], ex, ey, 70, 'userSpaceOnUse')
    c.add(f'<circle cx="{num(ex)}" cy="{num(ey)}" r="70" fill="{halo}"/>')
    ring = f'cx="{num(ex)}" cy="{num(ey)}" rx="62" ry="15" transform="rotate(-10 {num(ex)} {num(ey)})"'
    c.add(f'<path d="M{num(ex - 61)} {num(ey + 10)}A62 15 -10 0 1 {num(ex + 61)} {num(ey - 10)}" stroke="{fs.VIOLET_SOFT}" stroke-opacity=".55" stroke-width="5" fill="none"/>')
    top, mid, bot, wdt = ey - 40, ey - 4, ey + 36, 18
    facets = [
        (f'M{num(ex)} {num(top)}L{num(ex - wdt)} {num(mid)}L{num(ex)} {num(mid + 6)}Z', fs.CYAN_SOFT, .95),
        (f'M{num(ex)} {num(top)}L{num(ex + wdt)} {num(mid)}L{num(ex)} {num(mid + 6)}Z', fs.CYAN, .75),
        (f'M{num(ex - wdt)} {num(mid)}L{num(ex)} {num(bot)}L{num(ex)} {num(mid + 6)}Z', fs.VIOLET, .9),
        (f'M{num(ex + wdt)} {num(mid)}L{num(ex)} {num(bot)}L{num(ex)} {num(mid + 6)}Z', fs.VIOLET_DEEP, .95),
    ]
    for d, color, alpha in facets:
        c.add(f'<path d="{d}" fill="{color}" fill-opacity="{num(alpha)}" stroke="{fs.WHITE}" stroke-opacity=".55" stroke-width=".8" stroke-linejoin="round"/>')
    c.add(f'<path d="M{num(ex + 61)} {num(ey - 10)}A62 15 -10 0 1 {num(ex - 61)} {num(ey + 10)}" stroke="{c.linear([(0, fs.CYAN), (1, fs.VIOLET_SOFT)])}" stroke-width="5" fill="none" stroke-linecap="round"/>')
    c.add(f'<ellipse {ring} stroke="{fs.WHITE}" stroke-opacity=".18" fill="none"/>')
    # slogan
    size = 50
    first, second = 'STAY CURIOUS.', 'BUILD BOLD.'
    gap = 22
    w1 = c.measure(first, 'display', size, -.01)
    w2 = c.measure(second, 'display', size, -.01)
    x1 = (W - (w1 + gap + w2)) / 2
    c.text(first, x1, 150, style='display', size=size, fill=fs.WHITE, tracking=-.01)
    gradient = c.linear([(0, fs.CYAN), (.6, fs.VIOLET_SOFT), (1, fs.PINK)], x1 + w1 + gap, 0, x1 + w1 + gap + w2, 0, 'userSpaceOnUse')
    c.text(second, x1 + w1 + gap, 150, style='display', size=size, fill=gradient, tracking=-.01, mode='path')
    c.text('RAVI GOHEL  ·  ENGINEERING INTELLIGENCE  ·  NEURAL / FORGE', W / 2, 176, style='mono', size=10, fill=fs.MUTED,
           tracking=.18, anchor='middle')
    return c


# ---------------------------------------------------------------------------
def build_all() -> dict[str, str]:
    art: dict[str, str] = {}
    for i, section in enumerate(content.SECTIONS):
        art[f'nav-{section.number}-{section.anchor}.svg'] = nav_tab(section).svg()
        art[f'section-{section.number}-{section.anchor}.svg'] = section_banner(section, 11 + i * 7).svg()
    art['profile-panel.svg'] = profile_panel().svg()
    for i, project in enumerate(content.PROJECTS, 1):
        art[f'card-{project.slug}.svg'] = project_card(project, i).svg()
    art['toolbox.svg'] = toolbox().svg()
    for contact in content.CONTACTS:
        art[f'contact-{contact[0]}.svg'] = contact_panel(*contact).svg()
    art['footer.svg'] = footer().svg()
    return art


def main(argv: list[str]) -> int:
    art = build_all()
    if '--check' in argv:
        stale = [name for name, svg in art.items() if not (ART / name).is_file() or (ART / name).read_text(encoding='utf-8') != svg]
        extra = sorted({p.name for p in ART.glob('*.svg')} - set(art))
        if stale or extra:
            print('Stale artwork:', ', '.join(stale + extra))
            return 1
        print(f'All {len(art)} artwork files are current.')
        return 0
    ART.mkdir(parents=True, exist_ok=True)
    for old in ART.glob('*.svg'):
        if old.name not in art:
            old.unlink()
    total = 0
    for name, svg in art.items():
        (ART / name).write_text(svg, encoding='utf-8')
        total += len(svg.encode())
    print(f'Wrote {len(art)} SVG files to {ART.relative_to(ROOT)} ({total // 1024} KB total)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
