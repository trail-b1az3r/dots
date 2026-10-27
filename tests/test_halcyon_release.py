"""The release's version and name agree everywhere: VERSION, CODENAME, what `halcyon fetch` shows, and the notes.
Run: python3 -m unittest discover -s tests"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon"))
import halcyon_fetch  # noqa: E402


class ReleaseTest(unittest.TestCase):
    def test_fetch_shows_this_release(self):
        self.assertEqual(halcyon_fetch.__version__, (ROOT / "VERSION").read_text().strip())
        self.assertEqual(halcyon_fetch.__codename__, (ROOT / "CODENAME").read_text().strip())

    def test_the_release_has_notes_with_its_name(self):
        version = (ROOT / "VERSION").read_text().strip()
        notes = ROOT / "docs/releases" / f"{version}.md"
        self.assertTrue(notes.is_file(), notes)
        self.assertIn((ROOT / "CODENAME").read_text().strip(), notes.read_text().splitlines()[0])


if __name__ == "__main__":
    unittest.main()
