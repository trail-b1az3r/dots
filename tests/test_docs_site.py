"""The docs site (docs/site/build.py): every page builds, and every link and image inside the site resolves."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "docs/site"))

try:
    import build as site  # noqa: E402
except ImportError:  # the markdown package is not installed
    site = None


@unittest.skipIf(site is None, "the markdown package is not installed (pip install markdown)")
class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "site"
        cls.written = site.build(cls.out, "https://example.invalid/dots/")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_doc_has_a_page(self):
        sources = sorted((ROOT / "docs/halcyon").glob("*.md")) + sorted((ROOT / "docs/illogical-impulse").glob("*.md"))
        self.assertEqual(len(self.written), len(sources))
        self.assertIn("index.html", self.written)
        self.assertIn("illogical-impulse/index.html", self.written)
        self.assertTrue((self.out / ".nojekyll").exists())
        self.assertTrue((self.out / "assets/hero.jpg").exists())

    def test_internal_links_and_images_resolve(self):
        broken = []
        for page in self.out.rglob("*.html"):
            text = page.read_text(encoding="utf-8")
            ids = set(re.findall(r'id="([^"]+)"', text))
            for attr, url in re.findall(r'(href|src)="([^"]+)"', text):
                parts = urlsplit(url)
                if parts.scheme or parts.netloc or url.startswith(("mailto:", "data:")):
                    continue
                if not parts.path:
                    if parts.fragment and unquote(parts.fragment) not in ids:
                        broken.append(f"{page.relative_to(self.out)}: #{parts.fragment}")
                    continue
                target = (page.parent / unquote(parts.path)).resolve()
                if not target.exists():
                    broken.append(f"{page.relative_to(self.out)}: {url}")
                elif parts.fragment and target.suffix == ".html":
                    target_ids = set(re.findall(r'id="([^"]+)"', target.read_text(encoding="utf-8")))
                    if unquote(parts.fragment) not in target_ids:
                        broken.append(f"{page.relative_to(self.out)}: {url} (no such anchor)")
        self.assertEqual(broken, [])

    def test_repository_links_go_to_github(self):
        text = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="https://github.com/trail-b1az3r/dots/blob/main/CREDITS.md"', text)
        self.assertNotIn('.md"', re.sub(r'https://github\.com/[^"]+', "", text))

    def test_home_has_the_hero_and_credits_the_wallpaper(self):
        text = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="hero"', text)
        self.assertIn("Kenami", text)
        self.assertEqual(text.count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()
