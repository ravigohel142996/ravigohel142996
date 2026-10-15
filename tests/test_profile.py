import importlib.util
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metrics', ROOT / 'scripts/update_metrics.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


class MetricsTests(unittest.TestCase):
    def test_counts_exclude_forks(self):
        repos = [
            {'fork': False, 'language': 'Python', 'stargazers_count': 3},
            {'fork': False, 'language': 'Python', 'stargazers_count': 4},
            {'fork': False, 'language': None, 'stargazers_count': 0},
            {'fork': True, 'language': 'Rust', 'stargazers_count': 1000},
        ]
        root = ET.fromstring(metrics.render(repos, '2026-10-15'))
        description = root.find('{http://www.w3.org/2000/svg}desc').text
        self.assertIn('3 public non-fork repositories, 7 stars, 1 primary', description)
        self.assertIn('Leading language by repository count: Python', description)

    def test_empty_account(self):
        root = ET.fromstring(metrics.render([], '2026-10-15'))
        self.assertIn('Exploring', ''.join(root.itertext()))

    def test_xml_escaping(self):
        repos = [{'fork': False, 'language': 'A&B<test>', 'stargazers_count': 0}]
        root = ET.fromstring(metrics.render(repos, '2026-10-15'))
        self.assertIn('A&B<test>', ''.join(root.itertext()))

    def test_failed_api_preserves_snapshot(self):
        target = ROOT / 'assets/github-metrics.svg'
        previous = target.read_bytes()
        with patch.object(metrics, 'github', side_effect=RuntimeError('API unavailable')):
            with self.assertRaises(RuntimeError):
                metrics.main()
        self.assertEqual(previous, target.read_bytes())

    def test_pagination(self):
        batch = [{'fork': False, 'language': None, 'stargazers_count': 0}] * 100
        with patch.object(metrics, 'github', side_effect=[batch, []]) as api:
            with patch.object(Path, 'write_text') as write:
                metrics.main()
        self.assertEqual(api.call_count, 2)
        self.assertIn('page=2', api.call_args.args[0])
        self.assertIn('100 public non-fork repositories', write.call_args.args[0])


class AssetTests(unittest.TestCase):
    def test_readme_assets_exist(self):
        text = (ROOT / 'README.md').read_text()
        references = re.findall(r'(?:src|srcset)="\./([^\"]+)"', text)
        self.assertGreaterEqual(len(references), 3)
        for reference in references:
            self.assertTrue((ROOT / reference).is_file(), reference)
        self.assertNotIn('href="[', text)
        self.assertIn('https://www.linkedin.com/in/ravi-gohel/', text)
        self.assertIn('prefers-reduced-motion: reduce', text)

    def test_snapshot_is_valid_svg(self):
        root = ET.parse(ROOT / 'assets/github-metrics.svg').getroot()
        self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
        self.assertIsNotNone(root.find('{http://www.w3.org/2000/svg}desc'))

    def test_animation_and_fallback(self):
        from PIL import Image, ImageChops
        with Image.open(ROOT / 'assets/hero.gif') as gif:
            self.assertEqual(gif.n_frames, 64)
            self.assertEqual(gif.info['loop'], 0)
            self.assertEqual(gif.size, (1120, 460))
            first = gif.convert('RGB')
            gif.seek(20)
            self.assertIsNotNone(ImageChops.difference(first, gif.convert('RGB')).getbbox())
        with Image.open(ROOT / 'assets/hero-static.png') as still:
            self.assertEqual(still.size, (1120, 460))
        self.assertLess((ROOT / 'assets/hero.gif').stat().st_size, 2_000_000)

    def test_font_license_bundled(self):
        license_text = (ROOT / 'assets/fonts/OFL.txt').read_text()
        self.assertIn('SIL OPEN FONT LICENSE', license_text)
        self.assertGreater((ROOT / 'assets/fonts/SpaceGrotesk.ttf').stat().st_size, 10000)


if __name__ == '__main__':
    unittest.main()
