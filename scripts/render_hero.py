"""Render the animated NEURAL / FORGE hero and its reduced-motion still.

    .venv/bin/python scripts/render_hero.py                         # assets/hero.gif + assets/hero-static.png
    .venv/bin/python scripts/render_hero.py --cache /tmp/hero-frames  # reuse rendered frames between runs
    .venv/bin/python scripts/render_hero.py --frames 4 [--ss 1]       # quick look, writes /tmp/hero-preview-*.png

Pipeline
* Static layer (nebula, stars, lettering, terminal, floor grid, labels): an SVG
  built with forge_svg, so the type is real Space Grotesk / Space Mono with
  kerning, rasterised by resvg.
* 3D layer: ray-marched per pixel with numpy. An exact torus signed-distance
  field and a convex hexagonal crystal are sphere-traced through the same
  perspective camera as the floor grid, then shaded with analytic normals,
  ambient occlusion, environment reflections, emissive seams and crystal
  bounce light, with 2x supersampling. Particles are depth-tested against it.
* Loop: every motion completes whole periods per loop — the torus turns 180°
  (a symmetry of the torus and its texture), the crystal 60°, particles whole
  orbits, the status pulse and cursor whole cycles — so the GIF is seamless.
* GIF encoding: one shared palette, a fixed ordered dither (no crawling) and
  temporal stabilisation run twice round the loop, so unchanged pixels are
  stored as transparency. That keeps 50 frames of 1400 x 760 under 3 MB.

Requires scripts/requirements-art.txt. A full render takes ~2 minutes on 2 CPUs.
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

import numpy as np
import resvg_py
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forge_svg as fs  # noqa: E402
from forge_svg import Canvas, num  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W, H = 1400, 760
FRAMES, DELAY_MS = 50, 100           # 5.0 s loop; 62 x 80 ms looked marginally smoother but exceeded 3 MB
STILL_PHASE = 0.18                   # loop position used for the static fallback
SS = 2                               # supersampling factor for the 3D layer

# Camera and scene (world units; y up, z into the screen)
CX, CY = 1060.0, 350.0               # screen position of the scene origin
FOCAL, DIST = 1060.0, 6.45
R_MAJOR, R_MINOR = 1.0, 0.34
REGION = (712, 0, 1400, 690)          # screen box that receives the 3D layer
FLOOR_Y = -1.95

TERMINAL = (64, 590, 744, 712)
CURSOR_X = None                      # computed while building the static layer


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def project(points):
    """World points (..., 3) -> screen x, y and depth."""
    z = points[..., 2] + DIST
    return CX + FOCAL * points[..., 0] / z, CY - FOCAL * points[..., 1] / z, z


# ---------------------------------------------------------------------------
# Static layer
# ---------------------------------------------------------------------------
def static_layer() -> tuple[Image.Image, Image.Image]:
    """Return (background, cursor sprite) rendered by resvg."""
    global CURSOR_X
    c = Canvas(W, H, 'Ravi Gohel — NEURAL / FORGE hero', 'Static layer of the animated hero.')
    c.add(f'<rect width="{W}" height="{H}" fill="{fs.INK}"/>')
    for gx, gy, gr, color, alpha in (
        (CX, CY + 10, 640, '#4a1ca6', .50), (CX + 120, 640, 430, '#0b7390', .26),
        (190, 70, 430, '#6d1a5e', .18), (520, 780, 560, '#3a168a', .22), (CX, CY, 260, '#7c4dff', .22),
    ):
        paint = c.radial([(0, color, alpha), (.5, color, alpha * .35), (1, color, 0)], gx, gy, gr, 'userSpaceOnUse')
        c.add(f'<rect width="{W}" height="{H}" fill="{paint}"/>')
    vignette = c.radial([(0, '#000', 0), (.65, '#000', .05), (1, '#000', .62)], W / 2, H / 2, 860, 'userSpaceOnUse')
    c.add(f'<rect width="{W}" height="{H}" fill="{vignette}"/>')
    fs.stars(c, 2026, (20, 20, W - 20, H - 20), 150,
             avoid=[(56, 140, 770, 560), (56, 580, 752, 720), (60, 40, 560, 110), (1080, 40, 1340, 130)],
             max_radius=1.25, opacity=(.15, .7))
    for x, y, s in ((1296, 214, 9), (812, 118, 6), (628, 92, 5), (1338, 470, 5)):
        fs.glint(c, x, y, s, fs.WHITE, .75)

    # perspective floor that shares the 3D camera
    floor = []
    for k in range(-16, 17):
        x = k * .62
        near = np.array([x, FLOOR_Y, -2.4])
        far = np.array([x, FLOOR_Y, 34.0])
        (x1, y1, _), (x2, y2, _) = [tuple(float(v) for v in project(p)) for p in (near, far)]
        floor.append(f'M{num(x1, 1)} {num(y1, 1)}L{num(x2, 1)} {num(y2, 1)}')
    depth_lines = []
    z = -2.4
    while z < 34:
        sy = float(project(np.array([0, FLOOR_Y, z]))[1])
        xl = float(project(np.array([-16 * .62, FLOOR_Y, z]))[0])
        xr = float(project(np.array([16 * .62, FLOOR_Y, z]))[0])
        alpha = max(0.0, min(.55, 1.6 / (z + 3.2)))
        if sy < H + 2:
            depth_lines.append(f'<path d="M{num(xl, 1)} {num(sy, 1)}H{num(xr, 1)}" stroke-opacity="{num(alpha)}"/>')
        z += .62
    horizon = float(project(np.array([0, FLOOR_Y, 34.0]))[1])
    grad = c.linear([(0, fs.CYAN, 0), (.25, fs.CYAN, .10), (1, fs.VIOLET_SOFT, .55)], 0, horizon, 0, H, 'userSpaceOnUse')
    mask = c.uid('floormask')
    fade = c.radial([(0, '#fff', 1), (.55, '#fff', .75), (1, '#fff', 0)], CX + 20, H - 40, 560, 'userSpaceOnUse')
    c.define(f'<mask id="{mask}"><rect width="{W}" height="{H}" fill="{fade}"/></mask>')
    c.add(f'<g mask="url(#{mask})" stroke-width="1.1" fill="none"><path d="{"".join(floor)}" stroke="{grad}"/>'
          f'<g stroke="{fs.CYAN}">{"".join(depth_lines)}</g></g>')
    pool_y = float(project(np.array([0, FLOOR_Y, 0]))[1])
    pool = c.radial([(0, fs.CYAN, .20), (.45, fs.VIOLET, .10), (1, fs.VIOLET, 0)], 0.5, 0.5, 0.5)
    c.add(f'<ellipse cx="{num(CX)}" cy="{num(pool_y)}" rx="360" ry="92" fill="{pool}"/>')

    # frame details
    fs.corner_marks(c, 24, 24, W - 48, H - 48, 18, fs.LAVENDER, .35, 1.2)
    fs.ticks(c, 812, 1336, 734, 8, 5, fs.LAVENDER, .25, 4)

    # masthead
    mx, my, mr = 98, 76, 27
    hexagon = ' '.join(f'{num(x)},{num(y)}' for x, y in (fs.polar(mx, my, mr, a) for a in range(-90, 270, 60)))
    inner = ' '.join(f'{num(x)},{num(y)}' for x, y in (fs.polar(mx, my, mr - 6, a) for a in range(-90, 270, 60)))
    ring = c.linear([(0, fs.CYAN), (1, fs.VIOLET_SOFT)], mx - mr, 0, mx + mr, 0, 'userSpaceOnUse')
    halo = c.radial([(0, fs.VIOLET, .45), (1, fs.VIOLET, 0)], mx, my, 50, 'userSpaceOnUse')
    c.add(f'<circle cx="{mx}" cy="{my}" r="50" fill="{halo}"/>'
          f'<polygon points="{hexagon}" fill="{fs.NIGHT}" stroke="{ring}" stroke-width="2"/>'
          f'<polygon points="{inner}" fill="none" stroke="{fs.LAVENDER}" stroke-opacity=".25"/>')
    c.text('RG', mx, my + 6.4, style='mono-bold', size=18, fill=fs.WHITE, anchor='middle', tracking=.02)
    c.text('ENGINEERING INTELLIGENCE', 144, 72, style='mono-bold', size=15, fill=fs.LAVENDER, tracking=.3)
    c.text('NEURAL / FORGE  ·  PORTFOLIO OF BUILDS', 144, 96, style='mono', size=12.5, fill=fs.DIM, tracking=.2)

    # availability
    label = 'OPEN TO WORK'
    lw = c.measure(label, 'mono-bold', 15, .2)
    px1 = W - 72
    px0 = px1 - lw - 64
    c.add(f'<rect x="{num(px0)}" y="52.5" width="{num(px1 - px0)}" height="46" rx="23" fill="{fs.MINT}" fill-opacity=".08" '
          f'stroke="{fs.MINT}" stroke-opacity=".6" stroke-width="1.3"/>')
    fs.status_dot(c, px0 + 26, 75.5, fs.MINT, 5)
    c.text(label, px0 + 44, 81, style='mono-bold', size=15, fill=fs.MINT, tracking=.2)
    c.text('AI/ML · PYTHON · GENAI  —  REMOTE / INDIA', px0 - 22, 80, style='mono', size=12, fill=fs.MUTED, tracking=.14, anchor='end')

    # role and huge stacked name
    c.add(f'<path d="M66 156h34" stroke="{fs.CYAN}" stroke-width="2.4"/>')
    c.text('AI / ML ENGINEER', 114, 164, style='mono-bold', size=22, fill=fs.CYAN, tracking=.26)
    size, x0 = 198, 60
    c.text('RAVI', x0, 342, style='display', size=size, fill=c.linear([(0, '#ffffff'), (1, fs.LAVENDER)], 0, 190, 0, 342, 'userSpaceOnUse'),
           tracking=-.03, mode='path')
    for step in range(12, 0, -1):  # subtle extrusion for GOHEL.
        shade = fs.VIOLET_DEEP if step > 4 else '#3b1d8f'
        c.text('GOHEL.', x0 + step * .9, 506 + step * .9, style='display', size=size, fill=shade, tracking=-.03,
               mode='path', overlap_ok=True, opacity=.9)
    glow = c.blur(14)
    face = c.linear([(0, fs.CYAN), (.55, '#6f8bff'), (1, fs.VIOLET_SOFT)], x0, 0, x0 + 690, 0, 'userSpaceOnUse')
    c.text('GOHEL.', x0, 506, style='display', size=size, fill=fs.CYAN, tracking=-.03, mode='path', opacity=.28,
           extra=f' filter="{glow}"', overlap_ok=True)
    c.text('GOHEL.', x0, 506, style='display', size=size, fill=face, tracking=-.03, mode='path', overlap_ok=True)
    c.text('GOHEL.', x0, 506, style='display', size=size, fill='none', tracking=-.03, mode='path', overlap_ok=True,
           extra=f' stroke="{fs.CYAN_SOFT}" stroke-opacity=".35" stroke-width="1"')
    c.text('Student by chapter.', 66, 562, style='text', size=30, fill=fs.WHITE)
    c.text('Builder by instinct.', 66 + c.measure('Student by chapter. ', 'text', 30), 562, style='text', size=30, fill=fs.LAVENDER)

    # terminal
    x0, y0, x1, y1 = TERMINAL
    c.add(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="16" fill="{fs.NIGHT}" fill-opacity=".86" '
          f'stroke="{c.linear([(0, fs.CYAN, .55), (.5, fs.EDGE), (1, fs.VIOLET_SOFT, .5)])}" stroke-width="1.3"/>'
          f'<path d="M{x0 + 1} {y0 + 42}H{x1 - 1}" stroke="{fs.EDGE}"/>')
    for i, color in enumerate((fs.PINK, fs.LAVENDER, fs.CYAN)):
        c.add(f'<circle cx="{x0 + 24 + i * 19}" cy="{y0 + 21}" r="5.5" fill="{color}" fill-opacity=".9"/>')
    c.text('ravi@neural-forge ~ /mission', x0 + 92, y0 + 27, style='mono', size=16, fill=fs.MUTED, tracking=.02)
    c.text('zsh', x1 - 22, y0 + 27, style='mono', size=13, fill=fs.DIM, anchor='end')
    base = y0 + 88
    c.text('>', x0 + 24, base, style='mono-bold', size=24, fill=fs.PINK)
    call = 'turn_ideas_into_intelligent_systems'
    c.text(call, x0 + 50, base, style='mono-bold', size=24, fill=fs.WHITE)
    paren_x = x0 + 50 + c.measure(call, 'mono-bold', 24)
    c.text('()', paren_x, base, style='mono-bold', size=24, fill=fs.CYAN)
    CURSOR_X = paren_x + c.measure('()', 'mono-bold', 24) + 6

    # caption for the 3D figure, set on a soft backing so the floor grid never runs through it
    cap_x, cap_y = W - 72, 704
    caption = 'FIG. 01 — RAY-MARCHED TORUS · CRYSTAL CORE'
    cw = c.measure(caption, 'mono', 11.5, .12)
    back = c.linear([(0, fs.INK, 0), (.18, fs.INK, .78), (1, fs.INK, .78)], cap_x - cw - 30, 0, cap_x + 12, 0, 'userSpaceOnUse')
    c.add(f'<rect x="{num(cap_x - cw - 30)}" y="{cap_y - 17}" width="{num(cw + 42)}" height="25" rx="6" fill="{back}"/>')
    c.text(caption, cap_x, cap_y, style='mono', size=11.5, fill=fs.MUTED, tracking=.12, anchor='end')

    background = Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=c.svg())))).convert('RGB')
    cursor = Image.new('RGBA', (16, 30), (*hex_rgb(fs.CYAN), 235))
    return background, cursor


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# 3D scene: sphere-traced signed distance fields (exact torus, convex crystal)
# ---------------------------------------------------------------------------
def unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


LIGHT_KEY = unit([-0.55, 0.66, -0.52])
LIGHT_RIM = unit([0.80, 0.18, 0.72])
LIGHT_FILL = unit([0.20, -1.0, -0.30])
AMBIENT = np.array([0.060, 0.030, 0.150])
ALBEDO = np.array([0.46, 0.33, 0.98])
KEY = np.array([1.0, 0.93, 1.0])
RIM = np.array([0.13, 0.86, 1.0])
FILL = np.array([1.0, 0.42, 0.78])
SEAM = np.array([0.20, 1.25, 1.55])
CREST = np.array([0.55, 0.42, 1.05])
BASE_TILT = rot_z(-0.34) @ rot_x(0.46)
BOUND = R_MAJOR + R_MINOR + 0.03


def crystal_planes():
    """Outward unit normals and offsets of a hexagonal bipyramid with a short prism."""
    ring_top = [(0.27 * math.cos(k * math.pi / 3), 0.13, 0.27 * math.sin(k * math.pi / 3)) for k in range(6)]
    ring_bot = [(0.27 * math.cos(k * math.pi / 3), -0.11, 0.27 * math.sin(k * math.pi / 3)) for k in range(6)]
    top, bottom = (0, 0.56, 0), (0, -0.50, 0)
    faces = []
    for k in range(6):
        n = (k + 1) % 6
        faces += [(top, ring_top[n], ring_top[k]), (ring_top[k], ring_top[n], ring_bot[n]), (bottom, ring_bot[k], ring_bot[n])]
    vertices = np.array([top, bottom, *ring_top, *ring_bot], dtype=float)
    normals, offsets = [], []
    for a, b, c in faces:
        a, b, c = map(np.array, (a, b, c))
        n = unit(np.cross(b - a, c - a))
        normals.append(n)
        offsets.append(float(n @ a))
    return np.array(normals), np.array(offsets), vertices


CRYSTAL_N, CRYSTAL_H, CRYSTAL_V = crystal_planes()

ORBITS = [  # radius, tilt, particle phases, turns per loop, colour
    (1.56, rot_z(0.20) @ rot_x(0.44), (0.0, 2.1, 4.2), 1, fs.CYAN_SOFT),
    (1.68, rot_z(-0.30) @ rot_x(0.30), (0.7, 3.9), -1, fs.LAVENDER),
    (1.40, rot_z(0.62) @ rot_x(-0.58), (1.6, 4.8), 2, fs.PINK),
]


def poses(t: float):
    """Torus and crystal rotations for loop position t (both one-parameter, so the loop is seamless)."""
    torus = BASE_TILT @ rot_x(math.pi * t)                 # 180° per loop: a symmetry of the torus
    crystal = rot_z(0.10) @ rot_y(math.pi / 3 * t + 0.3)   # 60° per loop: a symmetry of the hexagon
    lift = np.array([0.0, 0.035 * math.sin(2 * math.pi * t), 0.0])
    return torus, crystal, lift


def sdf(p, torus, crystal, lift):
    pl = p @ torus                                          # world -> torus local (rows)
    q = np.hypot(pl[:, 0], pl[:, 2]) - R_MAJOR
    d_torus = np.hypot(q, pl[:, 1]) - R_MINOR
    pc = (p - lift) @ crystal
    d_crystal = (pc @ CRYSTAL_N.T - CRYSTAL_H).max(axis=1)
    return np.minimum(d_torus, d_crystal), d_torus <= d_crystal


def environment(r):
    """Cheap studio environment for reflections: violet sky, cyan horizon, dark floor."""
    y = r[:, 1:2]
    sky = np.array([0.20, 0.10, 0.45]) + np.array([0.45, 0.38, 0.75]) * np.clip(y, 0, 1) ** 1.5
    floor = np.array([0.02, 0.02, 0.06]) + np.array([0.0, 0.25, 0.32]) * np.exp(-((y + 0.25) / 0.10) ** 2)
    color = np.where(y > 0, sky, floor)
    return color + np.array([0.25, 0.95, 1.05]) * np.exp(-(y / 0.045) ** 2)


def render_scene(t: float, ss: int = SS):
    """Ray-march the scene. Returns (rgba premultiplied float, emission float, depth) at ss resolution."""
    torus, crystal, lift = poses(t)
    x0, y0, x1, y1 = REGION
    w, h = (x1 - x0) * ss, (y1 - y0) * ss
    sx = x0 + (np.arange(w) + .5) / ss
    sy = y0 + (np.arange(h) + .5) / ss
    gx, gy = np.meshgrid(sx, sy)
    d = np.stack([(gx - CX) / FOCAL, -(gy - CY) / FOCAL, np.ones_like(gx)], -1).reshape(-1, 3)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    origin = np.array([0.0, 0.0, -DIST])
    # bounding-sphere entry/exit
    b = d @ origin
    disc = b * b - (origin @ origin - BOUND ** 2)
    rays = np.nonzero(disc > 0)[0]
    root = np.sqrt(disc[rays])
    t_cur, t_far = -b[rays] - root, -b[rays] + root
    depth = np.full(d.shape[0], np.inf)
    hit_idx, hit_t, hit_torus = [], [], []
    active = np.arange(rays.size)
    for _ in range(110):
        if active.size == 0:
            break
        dirs = d[rays[active]]
        p = origin + dirs * t_cur[active, None]
        dist, is_torus = sdf(p, torus, crystal, lift)
        done = dist < 2.5e-4 * t_cur[active]
        if done.any():
            hit_idx.append(rays[active[done]])
            hit_t.append(t_cur[active[done]])
            hit_torus.append(is_torus[done])
        t_cur[active] += dist
        keep = ~done & (t_cur[active] < t_far[active])
        active = active[keep]
    rgba = np.zeros((d.shape[0], 4))
    emission = np.zeros((d.shape[0], 3))
    if hit_idx:
        idx = np.concatenate(hit_idx)
        th = np.concatenate(hit_t)
        tor = np.concatenate(hit_torus)
        depth[idx] = th
        dirs = d[idx]
        p = origin + dirs * th[:, None]
        view = -dirs
        footprint = th / FOCAL / ss
        color = np.zeros((idx.size, 3))
        glow = np.zeros((idx.size, 3))

        # torus material
        k = np.nonzero(tor)[0]
        if k.size:
            pl = p[k] @ torus
            ring = np.hypot(pl[:, 0], pl[:, 2])
            centre = np.stack([pl[:, 0] / ring * R_MAJOR, np.zeros(k.size), pl[:, 2] / ring * R_MAJOR], -1)
            nl = (pl - centre) / R_MINOR
            n = nl @ torus.T
            n /= np.linalg.norm(n, axis=1, keepdims=True)
            u = np.arctan2(pl[:, 2], pl[:, 0])
            v = np.arctan2(pl[:, 1], ring - R_MAJOR)
            arc_scale = R_MAJOR + R_MINOR * np.cos(v)
            fw = footprint[k] * 1.2

            def band(angle, period, half_width, scale):
                delta = np.abs((angle + period / 2) % period - period / 2) * scale
                return np.clip((half_width + fw - delta) / (2 * fw), 0, 1)

            seam = band(u, 2 * np.pi / 8, 0.020, arc_scale)
            groove = band(u, 2 * np.pi / 32, 0.0045, arc_scale) * (1 - seam)
            crest = band(np.abs(v) - np.pi / 2, 2 * np.pi, 0.0045, R_MINOR)
            vd = view[k]
            ndl = np.clip((n @ LIGHT_KEY + 0.12) / 1.12, 0, 1)[:, None] ** 1.15
            ndv = np.clip(np.sum(n * vd, 1), 0, 1)[:, None]
            half = vd + LIGHT_KEY
            half /= np.linalg.norm(half, axis=1, keepdims=True)
            nh = np.clip(np.sum(n * half, 1), 0, 1)[:, None]
            fres = (1 - ndv) ** 4
            refl = -vd + 2 * ndv * n
            ao = (0.62 + 0.38 * (0.5 + 0.5 * np.cos(v)))[:, None]
            towards_core = np.clip(-np.sum(n * p[k], 1) / np.linalg.norm(p[k], axis=1), 0, 1)[:, None]
            rim = np.clip(n @ LIGHT_RIM, 0, 1)[:, None]
            fill = np.clip(n @ LIGHT_FILL, 0, 1)[:, None]
            base = ALBEDO * (AMBIENT * 1.1 + KEY * ndl * 1.0 + FILL * fill * 0.36) * ao
            base *= (1 - 0.45 * groove)[:, None]
            col = (base + nh ** 80 * 1.35 + nh ** 10 * 0.12 + environment(refl) * (0.14 + 0.8 * fres)
                   + RIM * rim * fres * 1.4 + RIM * towards_core ** 2 * 0.42 * ao)
            em = SEAM * seam[:, None] + CREST * crest[:, None] * 0.55
            color[k] = col + em
            glow[k] = em * 0.9 + RIM * towards_core ** 3 * 0.10

        # crystal material: flat facets with luminous edges
        k = np.nonzero(~tor)[0]
        if k.size:
            pc = (p[k] - lift) @ crystal
            planes = pc @ CRYSTAL_N.T - CRYSTAL_H
            order = np.argsort(planes, axis=1)
            first = order[:, -1]
            gap = planes[np.arange(k.size), first] - planes[np.arange(k.size), order[:, -2]]
            n = CRYSTAL_N[first] @ crystal.T
            vd = view[k]
            facing = np.clip(np.sum(n * vd, 1), 0, 1)[:, None]
            key = np.clip(n @ LIGHT_KEY, 0, 1)[:, None]
            half = vd + LIGHT_KEY
            half /= np.linalg.norm(half, axis=1, keepdims=True)
            spec = np.clip(np.sum(n * half, 1), 0, 1)[:, None] ** 36
            up = (0.5 + 0.5 * CRYSTAL_N[first][:, 1:2])
            tint = np.array([0.42, 0.26, 1.0]) * (1 - up) + np.array([0.22, 0.95, 1.0]) * up
            inner = np.array([0.05, 0.06, 0.28]) * (1 - facing) + tint * (0.35 + 0.85 * facing ** 1.4)
            edge = np.clip((0.007 + footprint[k] * 1.5 - gap) / (footprint[k] * 3), 0, 1)[:, None]
            col = inner * (0.55 + 0.75 * key) + spec * 1.1 + environment(-vd + 2 * facing * n) * 0.18
            col += np.array([0.75, 0.98, 1.0]) * edge * 1.1
            color[k] = col
            glow[k] = inner * 0.55 + np.array([0.6, 0.95, 1.0]) * edge * 0.9

        color = 1 - np.exp(-1.30 * color)                       # filmic shoulder
        rgba[idx, :3] = np.clip(color, 0, 1)
        rgba[idx, 3] = 1.0
        emission[idx] = np.clip(glow, 0, 2)
    return rgba.reshape(h, w, 4), emission.reshape(h, w, 3), depth.reshape(h, w)


def particles(t: float, depth: np.ndarray, ss: int = SS):
    """Orbit paths, comet particles and their glow, depth-tested against the ray-marched scene."""
    x0, y0, x1, y1 = REGION
    w, h = (x1 - x0) * ss, (y1 - y0) * ss
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw, gdraw = ImageDraw.Draw(layer), ImageDraw.Draw(glow)
    origin = np.array([0.0, 0.0, -DIST])

    def visible(point) -> bool:
        sx, sy, _ = project(point)
        px, py = int((sx - x0) * ss), int((sy - y0) * ss)
        if not (0 <= px < w and 0 <= py < h):
            return False
        return float(np.linalg.norm(point - origin)) < depth[py, px] + 1e-3

    def screen(point):
        sx, sy, _ = project(point)
        return (float(sx) - x0) * ss, (float(sy) - y0) * ss

    for radius, tilt, phases, turns, color in ORBITS:
        rgb = hex_rgb(color)
        ring = np.linspace(0, 2 * np.pi, 145)
        path = np.stack([radius * np.cos(ring), np.zeros_like(ring), radius * np.sin(ring)], -1) @ tilt.T
        for a, b in zip(path[:-1], path[1:]):
            if visible((a + b) / 2):
                near = 1 - (float((a + b)[2]) / 2 + radius) / (2 * radius)
                draw.line([screen(a), screen(b)], fill=rgb + (int(34 + 46 * near),), width=ss)
        for phase in phases:
            pts = []
            for k in range(18):
                angle = phase + 2 * math.pi * turns * t - math.copysign(k * 0.04, turns)
                pts.append(np.array([radius * math.cos(angle), 0, radius * math.sin(angle)]) @ tilt.T)
            for k in range(17, 0, -1):
                if visible(pts[k]):
                    fade = 1 - k / 18
                    draw.line([screen(pts[k]), screen(pts[k - 1])], fill=rgb + (int(250 * fade ** 1.2),), width=max(1, round(ss * 3.2 * fade)))
            head = pts[0]
            if visible(head):
                hx, hy = screen(head)
                scale = DIST / float(head[2] + DIST)
                r = 4.0 * scale * ss
                draw.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(255, 255, 255, 255))
                g = r * 3.6
                gdraw.ellipse((hx - g, hy - g, hx + g, hy + g), fill=rgb + (255,))
    return layer, glow


def check_clearance() -> float:
    """Gap between the crystal and the torus tube; rotation-invariant because both share a centre."""
    lift = 0.035
    return float((R_MAJOR - R_MINOR) - (np.linalg.norm(CRYSTAL_V, axis=1).max() + lift))


# ---------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------
def compose(background: Image.Image, cursor: Image.Image, t: float, ss: int = SS) -> Image.Image:
    base = np.asarray(background, dtype=np.float32) / 255.0
    rgba, emission, depth = render_scene(t, ss)
    layer, pglow = particles(t, depth, ss)
    x0, y0, x1, y1 = REGION
    size = (x1 - x0, y1 - y0)

    def down(arr):
        return arr.reshape(size[1], ss, size[0], ss, -1).mean(axis=(1, 3))

    scene = down(rgba)
    emit = down(emission)
    part = down(np.asarray(layer, dtype=np.float32) / 255.0)
    pg = down(np.asarray(pglow, dtype=np.float32) / 255.0)
    bloom_src = emit + pg[..., :3] * pg[..., 3:4] * 1.3 + part[..., :3] * part[..., 3:4] * 0.8
    bloom = np.asarray(Image.fromarray(np.clip(bloom_src * 255 / 2, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)),
                       dtype=np.float32) / 255.0 * 2
    sub = base[y0:y1, x0:x1]
    sub = sub * (1 - scene[..., 3:4]) + scene[..., :3]          # premultiplied over
    sub = sub * (1 - part[..., 3:4]) + part[..., :3] * part[..., 3:4]
    sub = 1 - (1 - sub) * (1 - np.clip(bloom * 0.75, 0, 1))   # screen-blend glow, kept tight for GIF size
    base = base.copy()
    base[y0:y1, x0:x1] = sub
    # status pulse: five expanding rings per loop
    pulse = (t * 5) % 1
    radius, strength = 7 + pulse * 7.5, (1 - pulse) ** 1.5
    cx = W - 72 - fs.ft.measure('OPEN TO WORK', 'mono-bold', 15, .2) - 64 + 26
    yy, xx = np.mgrid[45:107, int(cx) - 31:int(cx) + 32]
    ring = np.clip(1.6 - np.abs(np.hypot(xx - cx, yy - 75.5) - radius), 0, 1) * strength * 0.75
    mint = np.array(hex_rgb(fs.MINT), dtype=np.float32) / 255.0
    patch = base[45:107, int(cx) - 31:int(cx) + 32]
    patch += (mint - patch) * ring[..., None]
    out = Image.fromarray(np.clip(base * 255 + .5, 0, 255).astype(np.uint8))
    if (t * 6) % 1 < 0.5:  # six blinks per loop keeps the seam invisible
        out.paste(cursor.convert('RGB'), (int(CURSOR_X), TERMINAL[1] + 64), cursor)
    return out


BAYER = (np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38],
                   [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                   [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) + .5) / 64 - .5


def to_gif(frames: list[Image.Image], path: Path, threshold: int = 10, dither: float = 6.0,
           motion_dither: float = 2.5) -> None:
    """Encode a seamless GIF with one shared palette.

    * fixed ordered (Bayer) dither, so static pixels never crawl between frames;
      pixels that never change over the loop get the full amount, moving ones less;
    * temporal stabilisation: a pixel keeps its previous colour unless it changed by more
      than `threshold`, so Pillow's optimiser stores unchanged pixels as transparency.
    """
    stack = np.stack([np.asarray(f, dtype=np.int16) for f in frames])
    moving = np.abs(stack - stack[0]).max(axis=(0, 3)) > 2
    del stack
    sample = Image.new('RGB', (W, H * 4 + 48))
    for k, idx in enumerate(np.linspace(0, len(frames) - 1, 4).astype(int)):
        sample.paste(frames[idx], (0, H * k))
    swatches = (fs.MINT, fs.PINK, fs.CYAN, fs.LAVENDER, fs.WHITE, fs.CYAN_SOFT, fs.VIOLET_SOFT)  # keep UI colours exact
    for k, color in enumerate(swatches):
        sample.paste(hex_rgb(color), (k * W // len(swatches), H * 4, (k + 1) * W // len(swatches), H * 4 + 48))
    palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    colors = np.array(palette.getpalette()[:768], dtype=np.int16).reshape(-1, 3)
    amount = np.where(moving, motion_dither, dither)[..., None]
    tile = np.tile(BAYER, (H // 8 + 1, W // 8 + 1))[:H, :W, None] * amount
    quantised = []
    for frame in frames:
        rgb = np.clip(np.asarray(frame, dtype=np.float32) + tile, 0, 255).astype(np.uint8)
        quantised.append(np.asarray(Image.fromarray(rgb).quantize(palette=palette, dither=Image.Dither.NONE)))
    # Two passes round the loop: the second pass stabilises frame 0 against the last frame too,
    # so the wrap-around step is an ordinary step and the loop stays seamless.
    previous, indexed = None, []
    for loop_pass in range(2):
        for idx in quantised:
            if previous is not None:
                change = np.abs(colors[idx] - colors[previous]).sum(axis=-1)
                idx = np.where(change <= threshold, previous, idx).astype(np.uint8)
            previous = idx
            if loop_pass:
                image = Image.fromarray(idx, 'P')
                image.putpalette(palette.getpalette()[:768])
                indexed.append(image)
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=DELAY_MS, loop=0, optimize=True, disposal=1)


def load_or_render(background, cursor, cache: Path | None, ss: int) -> list[Image.Image]:
    frames = []
    for k in range(FRAMES):
        cached = cache / f'frame-{FRAMES}-{k:03d}.png' if cache else None
        if cached and cached.is_file():
            frames.append(Image.open(cached).convert('RGB'))
            continue
        frame = compose(background, cursor, k / FRAMES, ss)
        if cached:
            cache.mkdir(parents=True, exist_ok=True)
            frame.save(cached)
        frames.append(frame)
        if k % 10 == 0:
            print(f'frame {k + 1}/{FRAMES}')
    return frames


def main(argv: list[str]) -> None:
    clearance = check_clearance()
    assert clearance > 0.05, f'crystal intersects the torus (clearance {clearance:.3f})'
    frames_wanted = int(argv[argv.index('--frames') + 1]) if '--frames' in argv else None
    ss = int(argv[argv.index('--ss') + 1]) if '--ss' in argv else SS
    background, cursor = static_layer()
    if frames_wanted:
        for k in range(frames_wanted):
            t = k / frames_wanted
            compose(background, cursor, t, ss).save(f'/tmp/hero-preview-{k}.png')
            print(f'/tmp/hero-preview-{k}.png (t={t:.2f})')
        return
    cache = Path(argv[argv.index('--cache') + 1]) if '--cache' in argv else None
    frames = load_or_render(background, cursor, cache, ss)
    gif = ROOT / 'assets/hero.gif'
    to_gif(frames, gif)
    still = compose(background, cursor, STILL_PHASE)
    still.save(ROOT / 'assets/hero-static.png', optimize=True)
    print(f'Wrote {gif.relative_to(ROOT)} ({gif.stat().st_size / 1e6:.2f} MB, {FRAMES} frames x {DELAY_MS} ms) '
          f'and assets/hero-static.png ({(ROOT / "assets/hero-static.png").stat().st_size / 1e3:.0f} KB); '
          f'crystal clearance {clearance:.2f}')


if __name__ == '__main__':
    main(sys.argv[1:])
