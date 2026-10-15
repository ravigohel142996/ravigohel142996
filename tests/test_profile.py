"""Validation for the NEURAL / FORGE profile: README markup, artwork, hero GIF and metrics.

    python3 -m unittest discover -s tests -v

Everything runs on the standard library except the GIF/PNG checks, which need
Pillow and numpy from scripts/requirements-art.txt and are skipped without them.
"""
from __future__ import annotations

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import forge_svg as fs  # noqa: E402
import profile_content as content  # noqa: E402
import render_art  # noqa: E402
import update_metrics as metrics  # noqa: E402

try:
    import numpy as np
    from PIL import Image, ImageSequence
except ImportError:  # pragma: no cover - optional imaging stack
    np = Image = ImageSequence = None

SVG = '{http://www.w3.org/2000/svg}'
README = (ROOT / 'README.md').read_text(encoding='utf-8')
EXPECTED_PROJECT_URLS = {
    'NeuroCore AI': 'https://github.com/ravigohel142996/NeuroCore-AI-The-Autonomous-Decision-Engine-for-Businesses',
    'Orbital Sentinel': 'https://github.com/ravigohel142996/Orbital-Sentinel-Earth-AI',
    'GuardianVision AI': 'https://github.com/ravigohel142996/GuardianVision-AI',
    'LoanGuardian AI': 'https://github.com/ravigohel142996/LoanGuardian-AI',
    'Enterprise RAG OS': 'https://github.com/ravigohel142996/enterprise-rag-os',
    'Relief Mate AI': 'https://github.com/ravigohel142996/Relief_mate_ai',
}
CONTACT_URLS = ('https://www.linkedin.com/in/ravi-gohel/', 'https://portfolioravigohel.netlify.app/',
                'mailto:ravi.n.gohel811@gmail.com')
SECTION_TITLES = ('01 — The human behind the system', '02 — The build archive', '03 — Tools of the trade',
                  '04 — Proof of work', "05 — Next mission: let's build")


class Markup(HTMLParser):
    """Collects the README's HTML structure: tags, ids, links and the images they wrap."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        self.images: list[dict] = []
        self.links: list[dict] = []
        self.ids: list[str] = []
        self.tags: list[tuple[str, dict, tuple]] = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        parents = tuple(t for t, _ in self.stack)
        self.tags.append((tag, attrs, parents))
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'img':
            link = next((a for t, a in reversed(self.stack) if t == 'a'), None)
            self.images.append({**attrs, 'parents': parents, 'href': link.get('href') if link else None})
        elif tag == 'a':
            self.links.append(attrs)
        if tag not in ('img', 'source', 'br'):
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break


MARKUP = Markup(README)


def svg_files() -> list[Path]:
    return sorted((ROOT / 'assets/art').glob('*.svg')) + [ROOT / 'assets/github-metrics.svg']


def repo(name, language='Python', stars=0, fork=False, pushed='2026-01-01T00:00:00Z'):
    return {'name': name, 'language': language, 'stargazers_count': stars, 'fork': fork, 'pushed_at': pushed}


class ReadmeTests(unittest.TestCase):
    def test_no_markup_github_strips_or_external_image_services(self):
        lowered = README.lower()
        for banned in ('<script', '<style', '<iframe', 'javascript:', ' style=', '<canvas', '<svg'):
            self.assertNotIn(banned, lowered)
        for tag, attrs, _ in MARKUP.tags:
            for attribute in ('src', 'srcset'):
                if attribute in attrs:
                    self.assertFalse(re.match(r'[a-z]+:', attrs[attribute]), f'{tag} {attribute} must be a repo path')

    def test_every_image_reference_exists(self):
        references = [attrs.get('src') or attrs.get('srcset') for tag, attrs, _ in MARKUP.tags if tag in ('img', 'source')]
        self.assertGreaterEqual(len(references), 24)
        for reference in references:
            self.assertTrue((ROOT / reference).is_file(), reference)
        art = {f'assets/art/{p.name}' for p in (ROOT / 'assets/art').glob('*.svg')}
        self.assertEqual(art - set(references), set(), 'generated art that the README never shows')

    def test_images_have_meaningful_alt_text(self):
        for image in MARKUP.images:
            alt = image.get('alt', '').strip()
            self.assertGreaterEqual(len(alt), 12, image['src'])
            self.assertNotRegex(alt.lower(), r'^(image|screenshot|banner|picture)\b')

    def test_hero_has_reduced_motion_fallback(self):
        self.assertTrue(README.startswith('<picture id="top">'))
        source = next(attrs for tag, attrs, _ in MARKUP.tags if tag == 'source')
        self.assertEqual(source, {'media': '(prefers-reduced-motion: reduce)', 'srcset': 'assets/hero-static.png'})
        hero = MARKUP.images[0]
        self.assertEqual(hero['src'], 'assets/hero.gif')
        # GitHub wraps unlinked images in a link; an author-added <a> around <picture> would make
        # it pull the <img> out of the <picture> and break the fallback.
        self.assertEqual(hero['parents'][-1], 'picture')
        self.assertNotIn('a', hero['parents'])

    def test_navigation_and_section_anchors(self):
        anchors = [section.anchor for section in content.SECTIONS]
        nav = [image for image in MARKUP.images if image['src'].startswith('assets/art/nav-')]
        self.assertEqual([image['href'] for image in nav], [f'#{anchor}' for anchor in anchors])
        headings = [(attrs['id'], parents) for tag, attrs, parents in MARKUP.tags if tag == 'h2']
        self.assertEqual([heading for heading, _ in headings], anchors)
        banners = [image for image in MARKUP.images if image['src'].startswith('assets/art/section-')]
        self.assertEqual([image['alt'] for image in banners], list(SECTION_TITLES))
        self.assertTrue(all('h2' in image['parents'] for image in banners))
        for link in MARKUP.links:
            href = link.get('href', '')
            if href.startswith('#'):
                self.assertIn(href[1:], MARKUP.ids, href)
        self.assertEqual(len(MARKUP.ids), len(set(MARKUP.ids)), 'duplicate ids')
        self.assertGreaterEqual(README.count('href="#top"'), 2)

    def test_project_cards_link_to_their_source_repositories(self):
        self.assertEqual({p.name: p.url for p in content.PROJECTS}, EXPECTED_PROJECT_URLS)
        cards = [image for image in MARKUP.images if image['src'].startswith('assets/art/card-')]
        self.assertEqual(len(cards), 6)
        for project, card in zip(content.PROJECTS, cards):
            self.assertEqual(card['src'], f'assets/art/card-{project.slug}.svg')
            self.assertEqual(card['href'], project.url)
            self.assertTrue(card['alt'].startswith(project.name))
            self.assertEqual(card.get('width'), '410', 'fixed width lets cards stack on phones')

    def test_plain_text_project_index(self):
        details = README[README.index('<details>'):README.index('</details>')]
        self.assertIn('<summary>', details)
        for project in content.PROJECTS:
            self.assertIn(f'**{project.name}**', details)
            self.assertIn(f'({project.url})', details)
            self.assertIn(project.focus.rstrip('.'), details)

    def test_contact_panels_and_text_links(self):
        contacts = [image for image in MARKUP.images if image['src'].startswith('assets/art/contact-')]
        self.assertEqual([image['href'] for image in contacts], list(CONTACT_URLS))
        self.assertEqual([url for _, _, url, *_ in content.CONTACTS], list(CONTACT_URLS))
        hrefs = [link.get('href') for link in MARKUP.links]
        for url in CONTACT_URLS:
            self.assertGreaterEqual(hrefs.count(url), 2, f'{url} needs a panel and a text link')

    def test_tools_and_explored_topics_have_text_alternatives(self):
        squash = lambda text: re.sub(r'\s+', '', text.lower())  # noqa: E731
        build_line = next(line for line in README.splitlines() if line.startswith('**Build with:**'))
        explore_line = next(line for line in README.splitlines() if line.startswith('**Exploring:**'))
        for name, _, _ in content.TOOLS:
            self.assertIn(squash(name), squash(build_line))
        for name, _, _ in content.EXPLORING:
            self.assertIn(squash(name), squash(explore_line))

    def test_copy_avoids_unverified_claims(self):
        lowered = README.lower()
        for phrase in ('winner', 'award', 'certified', 'streak', 'years of experience', 'expert'):
            self.assertNotIn(phrase, lowered)
        self.assertIn('dated snapshot, not live telemetry', README)


class ArtworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = render_art.build_all()   # raises LayoutError on clipped or colliding text

    def test_committed_art_matches_the_renderer(self):
        committed = {p.name: p.read_text(encoding='utf-8') for p in (ROOT / 'assets/art').glob('*.svg')}
        self.assertEqual(sorted(committed), sorted(self.built), 'run scripts/render_art.py')
        for name, svg in self.built.items():
            self.assertEqual(committed[name], svg, f'{name} is stale; run scripts/render_art.py')

    def test_every_project_section_and_contact_has_artwork(self):
        names = set(self.built)
        for section in content.SECTIONS:
            self.assertIn(f'nav-{section.number}-{section.anchor}.svg', names)
            self.assertIn(f'section-{section.number}-{section.anchor}.svg', names)
        for project in content.PROJECTS:
            self.assertIn(f'card-{project.slug}.svg', names)
        for slug, *_ in content.CONTACTS:
            self.assertIn(f'contact-{slug}.svg', names)
        self.assertTrue({'profile-panel.svg', 'toolbox.svg', 'footer.svg'} <= names)

    def test_svgs_are_valid_self_contained_and_labelled(self):
        for path in svg_files():
            with self.subTest(path.name):
                text = path.read_text(encoding='utf-8')
                root = ET.fromstring(text)
                self.assertEqual(root.tag, f'{SVG}svg')
                self.assertEqual(root.get('role'), 'img')
                self.assertRegex(root.get('viewBox', ''), r'^0 0 \d+(\.\d+)? \d+(\.\d+)?$')
                self.assertTrue(root.findtext(f'{SVG}title', '').strip())
                self.assertTrue(root.findtext(f'{SVG}desc', '').strip())
                ids = {element.get('id') for element in root.iter() if element.get('id')}
                for reference in re.findall(r'url\(#([^)]+)\)|href="#([^"]+)"', text):
                    self.assertIn(next(filter(None, reference)), ids)
                for banned in ('<script', '<foreignObject', '<text', '<image', '<style', '@import'):
                    self.assertNotIn(banned, text)
                self.assertNotRegex(text, r'(?:href|src)="(?!#)', 'only internal #references are allowed')

    def test_gradients_are_never_attached_to_zero_size_boxes(self):
        """Browsers skip objectBoundingBox gradients on straight horizontal/vertical lines."""
        straight = re.compile(r'^M\s*(-?[\d.]+)[ ,](-?[\d.]+)\s*(?:[HV]\s*-?[\d.]+|L\s*(-?[\d.]+)[ ,](-?[\d.]+))\s*$')
        for path in svg_files():
            root = ET.parse(path).getroot()
            bbox_gradients = {g.get('id') for g in root.iter() if g.tag in (f'{SVG}linearGradient', f'{SVG}radialGradient')
                              and g.get('gradientUnits') != 'userSpaceOnUse'}
            for element in root.iter(f'{SVG}path'):
                paint = (element.get('stroke') or '') + (element.get('fill') or '')
                used = re.findall(r'url\(#([^)]+)\)', paint)
                match = straight.match(element.get('d', ''))
                if not used or not match or not set(used) & bbox_gradients:
                    continue
                x1, y1, x2, y2 = match.groups()
                diagonal = x2 is not None and x1 != x2 and y1 != y2
                self.assertTrue(diagonal, f'{path.name}: {element.get("d")} uses a bounding-box gradient')

    def test_layout_checker_rejects_clipping_and_collisions(self):
        canvas = fs.Canvas(200, 60, 't', 'd')
        canvas.text('A line that is far too long for its box', 10, 30, size=14, within=(0, 0, 120, 60))
        with self.assertRaises(fs.LayoutError):
            canvas.check()
        canvas = fs.Canvas(400, 80, 't', 'd')
        canvas.text('Overlap', 20, 40, size=20)
        canvas.text('Overlap', 30, 44, size=20)
        with self.assertRaises(fs.LayoutError):
            canvas.check()

    def test_render_art_check_mode_reports_stale_files(self):
        with patch.object(render_art, 'build_all', return_value={**self.built, 'footer.svg': '<svg/>'}):
            with patch('builtins.print'):
                self.assertEqual(render_art.main(['--check']), 1)
        with patch('builtins.print'):
            self.assertEqual(render_art.main(['--check']), 0)


class MetricsTests(unittest.TestCase):
    def desc(self, repos, **kwargs):
        root = ET.fromstring(metrics.render(repos, '2026-10-15', **kwargs))
        return root.findtext(f'{SVG}desc')

    def test_counts_exclude_forks(self):
        repos = [repo('a', stars=3), repo('b', stars=4), repo('c', language=None), repo('fork', 'Rust', 1000, fork=True)]
        description = self.desc(repos)
        self.assertIn('3 public non-fork repositories, 7 stars, 1 primary repository languages', description)
        self.assertIn('Leading language by repository count: Python', description)
        self.assertIn('Updated 2026-10-15 UTC', description)

    def test_language_ranking_ties_and_other_bucket(self):
        langs = ['Python'] * 5 + ['HTML'] * 2 + ['C', 'TypeScript', 'Go', 'Rust', 'Java']
        data = metrics.summarise([repo(f'r{k}', language) for k, language in enumerate(langs)])
        self.assertEqual(data['segments'], [('Python', 5), ('HTML', 2), ('C', 1), ('Go', 1), ('Java', 1), ('Other', 2)])
        self.assertEqual(data['languages'], 7)
        self.assertEqual(sum(count for _, count in data['segments']), len(langs))

    def test_recent_pushes_skip_forks_and_the_profile_repository(self):
        repos = [repo('old', pushed='2026-01-01T00:00:00Z'), repo('ravigohel142996', pushed='2026-10-15T00:00:00Z'),
                 repo('newest', None, pushed='2026-10-14T00:00:00Z'), repo('fork', fork=True, pushed='2026-10-16T00:00:00Z'),
                 repo('middle', pushed='2026-05-01T00:00:00Z'), repo('second', pushed='2026-09-01T00:00:00Z')]
        recent = metrics.summarise(repos)['recent']
        self.assertEqual(recent, [('newest', '2026-10-14', '—'), ('second', '2026-09-01', 'Python'),
                                  ('middle', '2026-05-01', 'Python')])

    def test_since_and_empty_account(self):
        self.assertEqual(metrics.since('2025-11-10T11:08:38Z'), 'Nov 2025')
        self.assertIsNone(metrics.since(None))
        svg = metrics.render([], '2026-10-15', '2025-11-10T11:08:38Z')
        self.assertIn('Exploring', self.desc([]))
        ET.fromstring(svg)

    def test_xml_escaping_and_unusual_characters(self):
        description = self.desc([repo('x', 'A&B<test>'), repo('ü-名前', 'Ünïcode')])
        self.assertIn('A&B<test>', description)

    def test_failed_api_preserves_snapshot(self):
        previous = metrics.TARGET.read_bytes()
        with patch.object(metrics, 'github', side_effect=RuntimeError('API unavailable')):
            with self.assertRaises(RuntimeError):
                metrics.main()
        self.assertEqual(previous, metrics.TARGET.read_bytes())

    def test_pagination_and_profile_lookup(self):
        batch = [repo(f'r{k}', None) for k in range(100)]
        with patch.object(metrics, 'github', side_effect=[batch, [], {'created_at': '2025-11-10T11:08:38Z'}]) as api:
            with patch.object(Path, 'write_text') as write, patch('builtins.print'):
                metrics.main()
        self.assertEqual(api.call_count, 3)
        self.assertIn('page=2', api.call_args_list[1].args[0])
        self.assertEqual(api.call_args_list[2].args[0], 'users/ravigohel142996')
        self.assertIn('100 public non-fork repositories', write.call_args.args[0])

    def test_committed_snapshot_is_dated(self):
        root = ET.parse(metrics.TARGET).getroot()
        self.assertRegex(root.findtext(f'{SVG}desc'), r'Updated \d{4}-\d{2}-\d{2} UTC\.$')


@unittest.skipIf(Image is None, 'Pillow and numpy are needed for GIF checks (scripts/requirements-art.txt)')
class HeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / 'assets/hero.gif'
        with Image.open(cls.path) as gif:
            cls.size, cls.loop = gif.size, gif.info.get('loop')
            cls.durations, frames = [], []
            for frame in ImageSequence.Iterator(gif):
                cls.durations.append(frame.info.get('duration'))
                frames.append(np.asarray(frame.convert('RGB'), dtype=np.int16))
        cls.frames = frames

    def test_frames_loop_and_size(self):
        self.assertEqual(self.size, (1400, 760))
        self.assertEqual(len(self.frames), 50)
        self.assertEqual(self.loop, 0, 'loops forever')
        self.assertEqual(set(self.durations), {100})
        self.assertEqual(sum(self.durations), 5000)
        self.assertLess(self.path.stat().st_size, 3_000_000)

    def test_animation_is_seamless(self):
        steps = [np.abs(self.frames[(k + 1) % len(self.frames)] - self.frames[k]).mean() for k in range(len(self.frames))]
        self.assertGreater(min(steps[:-1]), 0.5, 'every frame moves')
        self.assertLessEqual(steps[-1], max(steps[:-1]) * 1.05, 'the wrap-around step must look like any other step')

    def test_static_fallback(self):
        with Image.open(ROOT / 'assets/hero-static.png') as still:
            self.assertEqual(still.format, 'PNG')
            self.assertEqual(still.size, (1400, 760))
            self.assertFalse(getattr(still, 'is_animated', False))


class FontTests(unittest.TestCase):
    def test_bundled_fonts_carry_their_licenses(self):
        for font, license_file, holder in (
                ('SpaceGrotesk.ttf', 'SpaceGrotesk-OFL.txt', 'The Space Grotesk Project Authors'),
                ('SpaceMono-Regular.ttf', 'SpaceMono-OFL.txt', 'The Space Mono Project Authors'),
                ('SpaceMono-Bold.ttf', 'SpaceMono-OFL.txt', 'The Space Mono Project Authors')):
            self.assertGreater((ROOT / 'assets/fonts' / font).stat().st_size, 10_000)
            text = (ROOT / 'assets/fonts' / license_file).read_text(encoding='utf-8')
            self.assertIn('SIL OPEN FONT LICENSE Version 1.1', text)
            self.assertIn(holder, text)
        glyphs = (ROOT / 'assets/fonts/forge-glyphs.json').read_text(encoding='utf-8')
        self.assertIn('SIL Open Font License 1.1', glyphs)


class WorkflowTests(unittest.TestCase):
    def test_refresh_workflow_watches_every_metrics_dependency(self):
        workflow = (ROOT / '.github/workflows/refresh-profile.yml').read_text(encoding='utf-8')
        for path in ('scripts/update_metrics.py', 'scripts/forge_svg.py', 'scripts/forge_type.py',
                     'assets/fonts/forge-glyphs.json'):
            self.assertIn(f"- '{path}'", workflow)
        self.assertIn('git add assets/github-metrics.svg', workflow)
        self.assertRegex(workflow, r'actions/checkout@[0-9a-f]{40}')


if __name__ == '__main__':
    unittest.main()
