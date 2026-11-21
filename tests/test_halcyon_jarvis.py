"""`halcyon jarvis`: jarvis-linux, an offline voice assistant, at a pinned commit, started only in Hyprland.
Run: python3 -m unittest discover -s tests"""

import io
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
UNITS = Path(__file__).resolve().parent.parent / "dots/.config/systemd/user"
sys.path.insert(0, str(HALCYON))
import halcyon_jarvis as jarvis  # noqa: E402


class JarvisTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.calls = []

        def run(cmd, **kwargs):
            self.calls.append([str(c) for c in cmd])
            return subprocess.CompletedProcess(cmd, 0, "", "")

        self.patches = [unittest.mock.patch.object(jarvis, name, root / sub) for name, sub in
                        [("CODE", "share/halcyon/jarvis-linux"), ("MODELS", "share/jarvis"),
                         ("CONFIG", "config/jarvis/config.toml"), ("ON", "state/halcyon/jarvis-on"),
                         ("LOG", "state/jarvis/jarvis.log")]]
        self.patches += [unittest.mock.patch.object(jarvis.subprocess, "run", run),
                         unittest.mock.patch.object(jarvis.shutil, "which", lambda name: f"/usr/bin/{name}")]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def quiet(self, argv):
        with redirect_stdout(io.StringIO()) as out:
            code = jarvis.main(argv)
        return code, out.getvalue()

    def test_the_wake_phrase_goes_into_its_config(self):
        self.quiet(["wake", 'Hey "Computer"'])
        text = jarvis.CONFIG.read_text()
        self.assertIn('wake_phrase = "hey computer"', text)
        self.assertIn('language = "english"', text)
        self.quiet(["wake", "wake up jarvis"])
        self.assertEqual(jarvis.CONFIG.read_text().count("wake_phrase"), 1)

    def test_off_stops_it_and_login_starts_it_only_when_on(self):
        jarvis.ON.parent.mkdir(parents=True)
        jarvis.ON.touch()
        with unittest.mock.patch.object(jarvis, "installed", lambda: True):
            self.quiet(["login"])
            self.assertIn(["systemctl", "--user", "restart", "halcyon-jarvis.service"], self.calls)
            self.quiet(["off"])
            self.assertFalse(jarvis.ON.exists())
            self.calls.clear()
            self.quiet(["login"])
        self.assertEqual(self.calls, [])

    def test_the_model_zip_cannot_write_outside_its_folder(self):
        path = Path(self.tmp.name) / "bad.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../../evil", "x")
        with zipfile.ZipFile(path) as archive, self.assertRaises(jarvis.JarvisError):
            jarvis.safe_extract(archive, Path(self.tmp.name) / "out")

    def test_status_when_not_installed(self):
        code, out = self.quiet([])
        self.assertEqual(code, 0)
        self.assertIn("not installed", out)


class WiringTest(unittest.TestCase):
    def test_pinned_to_a_full_commit(self):
        self.assertRegex(jarvis.COMMIT, r"^[0-9a-f]{40}$")
        self.assertTrue(jarvis.MODEL_URL.startswith("https://alphacephei.com/vosk/models/"))

    def test_only_in_hyprland_and_at_login(self):
        service = (UNITS / "halcyon-jarvis.service").read_text()
        self.assertIn("ExecCondition=", service)
        self.assertIn("Restart=on-failure", service)
        self.assertNotIn("[Install]", service)   # started from init.lua, never in KDE or GNOME
        init = (HALCYON / "init.lua").read_text()
        self.assertIn("halcyon_jarvis.py login", init)
        self.assertIn('hl.env("QT_LINUX_ACCESSIBILITY_ALWAYS_ON", "1")', init)
        self.assertIn('argv[0] == "jarvis"', (HALCYON / "halcyon-theme").read_text())


if __name__ == "__main__":
    unittest.main()
