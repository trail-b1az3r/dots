"""`halcyon wallpapers` and the two anime themes that use its videos, against a local web server and a scratch
XDG_DATA_HOME. Run: python3 -m unittest discover -s tests"""

import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))
import halcyon_wallpapers as wp  # noqa: E402

MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 64
HTML = b"<!DOCTYPE html><html><body>Please wait</body></html>"


class Handler(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Handler.seen.append((self.path, self.headers.get("Referer"), self.headers.get("User-Agent")))
        body = MP4 if self.path.startswith("/video") else HTML
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class WallpaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = (wp.DIRECTORY, dict(wp.CATALOG["after-icey"]))
        wp.DIRECTORY = Path(self.tmp.name) / "wallpapers"
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        Handler.seen = []

    def tearDown(self):
        wp.DIRECTORY, wp.CATALOG["after-icey"] = self.saved[0], self.saved[1]

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = wp.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_list_says_what_is_missing_and_what_can_be_downloaded(self):
        code, out, _ = self.run_main("list", "--json")
        rows = {r["id"]: r for r in json.loads(out)}
        self.assertEqual(code, 0)
        self.assertEqual({k: (r["installed"], r["downloadable"]) for k, r in rows.items()},
                         {"after-icey": (False, True), "anime-girl-cat": (False, False)})
        self.assertTrue(rows["after-icey"]["path"].startswith(str(wp.DIRECTORY)))

    def test_import_installs_a_video(self):
        source = Path(self.tmp.name) / "mine.mp4"
        source.write_bytes(MP4)
        code, _, _ = self.run_main("import", "anime-girl-cat", str(source))
        self.assertEqual(code, 0)
        self.assertEqual(wp.target("anime-girl-cat").read_bytes(), MP4)
        self.assertEqual([p.name for p in wp.DIRECTORY.iterdir()], ["anime-girl-x-cat.mp4"])

    def test_import_refuses_a_saved_web_page_and_keeps_the_old_file(self):
        good = Path(self.tmp.name) / "good.mp4"
        good.write_bytes(MP4)
        self.run_main("import", "anime-girl-cat", str(good))
        page = Path(self.tmp.name) / "page.mp4"
        page.write_bytes(HTML)
        code, _, err = self.run_main("import", "anime-girl-cat", str(page))
        self.assertEqual(code, 1)
        self.assertIn("not a video", err)
        self.assertEqual(wp.target("anime-girl-cat").read_bytes(), MP4)

    def test_webm_is_a_video_too(self):
        self.assertTrue(wp.looks_like_video(b"\x1a\x45\xdf\xa3" + b"\x00" * 12))

    def test_get_downloads_with_the_page_as_referer(self):
        wp.CATALOG["after-icey"]["url"] = self.base + "/video/hd"
        code, _, _ = self.run_main("get", "after-icey")
        self.assertEqual(code, 0)
        self.assertEqual(wp.target("after-icey").read_bytes(), MP4)
        path, referer, agent = Handler.seen[0]
        self.assertEqual(referer, "https://motionbgs.com/after-icey")
        self.assertIn("Firefox", agent)
        self.assertEqual([p.name for p in wp.DIRECTORY.iterdir()], ["after-icey.mp4"])

    def test_get_4k_uses_the_4k_link(self):
        wp.CATALOG["after-icey"]["url_4k"] = self.base + "/video/4k"
        self.run_main("get", "after-icey", "--4k")
        self.assertEqual(Handler.seen[0][0], "/video/4k")

    def test_get_that_returns_a_web_page_saves_nothing(self):
        wp.CATALOG["after-icey"]["url"] = self.base + "/page"
        code, _, err = self.run_main("get", "after-icey")
        self.assertEqual(code, 1)
        self.assertIn("not a video", err)
        self.assertEqual(list(wp.DIRECTORY.iterdir()), [])

    def test_get_for_a_page_only_wallpaper_explains_the_import(self):
        code, _, err = self.run_main("get", "anime-girl-cat")
        self.assertEqual(code, 1)
        self.assertIn("desktophut.com/anime-girl-x-cat-pl2s", err)
        self.assertIn("halcyon wallpapers import anime-girl-cat", err)
        self.assertEqual(Handler.seen, [])

    def test_unknown_id(self):
        code, _, err = self.run_main("path", "nope")
        self.assertEqual(code, 1)
        self.assertIn("after-icey", err)


class ThemeTests(unittest.TestCase):
    def test_each_wallpaper_belongs_to_a_theme_that_looks_for_it_where_get_puts_it(self):
        for entry_id, entry in wp.CATALOG.items():
            theme = json.loads((HALCYON / "themes" / f"{entry['theme']}.json").read_text())
            self.assertEqual(os.path.expanduser(theme["wallpaper"]), str(wp.target(entry_id)), entry_id)

    def test_the_videos_are_not_in_the_repository(self):
        for path in (HALCYON / "themes").rglob("*"):
            self.assertNotIn(path.suffix, (".mp4", ".webm", ".mkv"), path)

    def test_themes_pass_the_theme_checker(self):
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, "HOME": home, "XDG_CONFIG_HOME": home + "/c", "XDG_DATA_HOME": home + "/d",
                   "XDG_STATE_HOME": home + "/s"}
            for theme in ("after-icey", "manga-ink"):
                result = subprocess.run([sys.executable, str(HALCYON / "halcyon-theme"), "check", theme],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def load_tool(self):
        loader = importlib.machinery.SourceFileLoader("halcyon_theme_wp", str(HALCYON / "halcyon-theme"))
        spec = importlib.util.spec_from_loader("halcyon_theme_wp", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module

    def test_the_border_spins_slowly_and_only_that_animation_may(self):
        module = self.load_tool()
        theme = json.loads((HALCYON / "themes/after-icey.json").read_text())
        spin = [a for a in theme["hyprland"]["animations"] if a["leaf"] == "borderangle"]
        self.assertEqual([a["style"] for a in spin], ["loop"])
        self.assertEqual(module.validate("after-icey", theme), [])
        # a window animation that long is a mistake; a border angle that long is a slow turn
        slow = json.loads(json.dumps(theme))
        for a in slow["hyprland"]["animations"]:
            if a["leaf"] == "windowsIn":
                a["speed"] = 70
        problems = module.validate("after-icey", slow)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("0.1..20", problems[0])

    def test_applying_without_the_video_says_how_to_get_it(self):
        module = self.load_tool()
        icey = module.wallpaper_hint(wp.target("after-icey"))
        self.assertIn("halcyon wallpapers get after-icey", icey)
        manual = module.wallpaper_hint(wp.target("anime-girl-cat"))
        self.assertIn("halcyon wallpapers import anime-girl-cat FILE", manual)
        self.assertEqual(module.wallpaper_hint(Path("/elsewhere.mp4")), "")


if __name__ == "__main__":
    unittest.main()
