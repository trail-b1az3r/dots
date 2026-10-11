"""The Halcyon mark, and the references to it.

These check the places a logo can silently go missing: a file that is not
installed, a path the installer and the shell disagree about, or a theme
name that no icon theme contains. Each of those used to fail quietly.
"""

from __future__ import annotations

import pathlib
import re
import struct
import unittest
import xml.etree.ElementTree as ET

REPO = pathlib.Path(__file__).resolve().parent.parent
ICONS = REPO / "assets" / "icons"
QML = REPO / "config" / "quickshell" / "halcyon"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_size(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise AssertionError(f"{path} is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


class TestMarkFiles(unittest.TestCase):
    def test_the_master_is_well_formed_svg(self) -> None:
        root = ET.parse(ICONS / "halcyon.svg").getroot()
        self.assertTrue(root.tag.endswith("svg"))

    def test_the_master_has_no_dependence_on_inherited_colour(self) -> None:
        # currentColor resolves to black in a standalone image, which made
        # the previous mark invisible on a dark background.
        text = (ICONS / "halcyon.svg").read_text(encoding="utf-8")
        body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        self.assertNotIn("currentColor", body)

    def test_the_master_uses_no_gradients_blend_modes_or_filters(self) -> None:
        # The mark must stay legible at launcher size; these are the things
        # that do not survive being shrunk, or being drawn by Qt's renderer.
        text = (ICONS / "halcyon.svg").read_text(encoding="utf-8")
        body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        for forbidden in ("Gradient", "mix-blend-mode", "<filter", "<mask"):
            self.assertNotIn(forbidden, body, msg=forbidden)

    def test_the_pngs_exist_and_are_the_documented_sizes(self) -> None:
        self.assertEqual(png_size(ICONS / "halcyon.png"), (256, 256))
        self.assertEqual(png_size(ICONS / "halcyon-64.png"), (64, 64))

    def test_the_pngs_have_transparent_corners(self) -> None:
        # The tile is rounded; the corners must be transparent, not the
        # colour of whatever background the PNG was rendered on.
        data = (ICONS / "halcyon.png").read_bytes()
        self.assertEqual(data[25], 6, "PNG colour type should be RGBA")

    def test_the_pngs_are_current_with_the_master(self) -> None:
        # Regenerate in memory and compare the sizes at least — a stale
        # PNG after an SVG edit is the commonest way this drifts.
        master = (ICONS / "halcyon.svg").stat().st_mtime
        png = (ICONS / "halcyon.png").stat().st_mtime
        self.assertGreaterEqual(
            png, master - 60,
            msg="halcyon.png is older than halcyon.svg; run scripts/dev/render-logo.py",
        )


class TestTheShellFindsTheInstalledMark(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = (QML / "Config" / "Paths.qml").read_text(encoding="utf-8")
        self.installer = (REPO / "install.sh").read_text(encoding="utf-8")

    def test_paths_defines_the_logo_under_the_share_directory(self) -> None:
        self.assertIn('readonly property string logo: root.shareDir + "/icons/halcyon.png"',
                      self.paths)

    def test_the_share_directory_honours_the_installer_override(self) -> None:
        self.assertIn('Quickshell.env("HALCYON_DATA_DIR")', self.paths)

    def test_the_installer_puts_the_icons_where_the_shell_looks(self) -> None:
        # install.sh copies assets/icons to $SHARE_DIR/icons; Paths.qml
        # reads shareDir + /icons/halcyon.png. If either side moves, the
        # logo silently stops appearing.
        self.assertRegex(
            self.installer,
            r'install_tree\s+"\$HALCYON_REPO_ROOT/assets/icons"\s+"\$SHARE_DIR/icons"',
        )

    def test_the_file_the_shell_loads_is_one_the_installer_ships(self) -> None:
        self.assertTrue((ICONS / "halcyon.png").is_file())

    def test_the_launcher_no_longer_asks_a_theme_for_a_name_it_does_not_have(self) -> None:
        launcher = (QML / "Modules" / "Bar" / "modules" / "Launcher.qml").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(launcher, r'source:\s*"halcyon"')
        self.assertIn("source: Paths.logo", launcher)

    def test_about_shows_the_mark(self) -> None:
        about = (QML / "Modules" / "Settings" / "Sections" / "AboutSection.qml").read_text(
            encoding="utf-8"
        )
        self.assertIn("source: Paths.logo", about)
        # Hidden rather than broken when the file is missing.
        self.assertIn("visible: status === Image.Ready", about)


class TestNoOldBranding(unittest.TestCase):
    """The repository must not refer to another project's branding."""

    FORBIDDEN = ("illogical", "impulse")

    def test_no_file_mentions_the_old_project(self) -> None:
        offenders: list[str] = []
        for path in REPO.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            if path.suffix in {".png", ".pyc"}:
                continue
            # This file has to name the terms it forbids.
            if path.resolve() == pathlib.Path(__file__).resolve():
                continue
            try:
                text = path.read_text(encoding="utf-8").lower()
            except (UnicodeDecodeError, OSError):
                continue
            for word in self.FORBIDDEN:
                if word in text:
                    offenders.append(f"{path.relative_to(REPO)}: {word!r}")
        self.assertEqual(offenders, [], msg="old branding references")

    def test_the_asset_readme_describes_the_mark_as_it_is(self) -> None:
        readme = (ICONS / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("currentColor", readme)
        self.assertIn("halcyon.png", readme)


if __name__ == "__main__":
    unittest.main()
