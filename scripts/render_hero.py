"""Render the self-hosted, seamlessly looping profile hero.

Install scripts/requirements-art.txt, then run this script from any directory.
The font is bundled under the SIL Open Font License in assets/fonts/OFL.txt.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
W, H, FRAMES = 1120, 460, 64
FONT = ROOT / 'assets/fonts/SpaceGrotesk.ttf'
BG = (8, 13, 25)
CYAN = (102, 242, 218)
PURPLE = (156, 139, 255)


def font(size):
    return ImageFont.truetype(str(FONT), size)


def project(point, spin):
    x, y, z = point
    x, z = x * math.cos(spin) + z * math.sin(spin), -x * math.sin(spin) + z * math.cos(spin)
    y, z = y * .90 - z * .436, y * .436 + z * .90
    scale = 410 / (410 + z)
    return 857 + x * scale, 222 + y * scale, z


def base():
    image = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(image)
    for x in range(0, W, 40):
        d.line((x, 0, x, H), fill=(15, 23, 39))
    for y in range(0, H, 40):
        d.line((0, y, W, y), fill=(15, 23, 39))
    d.rounded_rectangle((1, 1, W-2, H-2), 24, outline=(43, 58, 77), width=2)
    d.rounded_rectangle((40, 32, 233, 61), 14, fill=(17, 42, 43), outline=(41, 82, 77))
    d.ellipse((53, 43, 61, 51), fill=CYAN)
    d.text((71, 37), 'OPEN TO OPPORTUNITIES', font=font(12), fill=CYAN)
    d.text((40, 86), 'HELLO WORLD. I\'M', font=font(16), fill=(147, 163, 185))
    d.text((34, 102), 'RAVI GOHEL', font=font(88), fill=(239, 245, 255), stroke_width=1)
    d.text((41, 218), 'AI / ML  ENGINEER & BUILDER', font=font(23), fill=CYAN)
    d.text((41, 266), 'From curiosity to code.', font=font(21), fill=(218, 226, 241))
    d.text((41, 297), 'From ideas to intelligent systems.', font=font(21), fill=(147, 163, 185))
    d.line((40, 366, 1080, 366), fill=(43, 58, 77))
    for x, n, label in [(41, '01', 'MACHINE LEARNING'), (396, '02', 'GEN AI & AGENTS'), (751, '03', 'FULL STACK')]:
        d.text((x, 393), n, font=font(16), fill=CYAN)
        d.text((x+36, 393), label, font=font(16), fill=(194, 205, 225))
    return image


def frame(index):
    image = base()
    layer = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(layer)
    t = index / FRAMES * math.tau
    # A genuinely projected wireframe sphere, with depth-shaded meridians.
    for meridian in range(12):
        angle = meridian * math.tau / 12
        points = [project((108*math.sin(a)*math.cos(angle), 108*math.cos(a), 108*math.sin(a)*math.sin(angle)), t) for a in [i*math.pi/64 for i in range(65)]]
        for a, b in zip(points, points[1:]):
            depth = int(65 + (110-a[2])*.52)
            d.line((a[0], a[1], b[0], b[1]), fill=(*CYAN, max(35, min(200, depth))), width=1)
    for latitude in range(1, 8):
        a = latitude*math.pi/8
        points = [project((108*math.sin(a)*math.cos(b), 108*math.cos(a), 108*math.sin(a)*math.sin(b)), t) for b in [i*math.tau/96 for i in range(97)]]
        d.line([(p[0], p[1]) for p in points], fill=(*CYAN, 95), width=1)
    # Tilted orbital paths and luminous satellites.
    for orbit in range(3):
        tilt = orbit * math.pi/3 + .2
        def orbital(a):
            x, y = 159*math.cos(a), 52*math.sin(a)
            return 857+x*math.cos(tilt)-y*math.sin(tilt), 222+x*math.sin(tilt)+y*math.cos(tilt)
        d.line([orbital(i*math.tau/128) for i in range(129)], fill=(*PURPLE, 115), width=1)
        x, y = orbital(t + orbit*2)
        d.ellipse((x-5, y-5, x+5, y+5), fill=(*PURPLE, 255))
    glow = layer.filter(ImageFilter.GaussianBlur(7))
    image = Image.alpha_composite(image.convert('RGBA'), glow)
    image = Image.alpha_composite(image, layer).convert('RGB')
    return image


def main():
    frames = [frame(i) for i in range(FRAMES)]
    frames[0].save(ROOT / 'assets/hero-static.png', optimize=True)
    # Shared palette prevents color flicker between frames.
    palette = frames[0].quantize(colors=128)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(ROOT / 'assets/hero.gif', save_all=True, append_images=indexed[1:], duration=80, loop=0, optimize=True, disposal=1)
    print('Rendered assets/hero.gif and assets/hero-static.png')


if __name__ == '__main__':
    main()
