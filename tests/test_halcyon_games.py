"""games.lua: a game keeps the keyboard when the pointer leaves it (follow_mouse 2 while a game is focused, 1 for
anything else), under real Lua with a stand-in `hl`. Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = ROOT / "dots/.config/hypr/hyprland/halcyon/games.lua"
LUA = shutil.which("lua") or shutil.which("lua5.4")

STUB = r"""
hl = { handlers = {}, set = {} }
hl.on = function(ev, fn) hl.handlers[ev] = fn end
hl.config = function(t) hl.set[#hl.set + 1] = t.input.follow_mouse end
"""


def run(body, enabled=True):
    script = STUB + ("" if enabled else "HALCYON_GAME_FOCUS = false\n") + f'local M = dofile({json.dumps(str(GAMES))})\n' + body
    done = subprocess.run([LUA, "-"], input=script, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return done.stdout.strip()


@unittest.skipUnless(LUA, "no lua interpreter")
class GamesTest(unittest.TestCase):
    FOCUS = r"""
local active = hl.handlers["window.active"]
active({ class = "firefox" })
active({ class = "steam_app_1091500" })
active({ class = "steam_app_1091500" })
active({ class = "kitty" })
active({ class = "Minecraft", content_type = "game" })
active({ class = "foo", tags = { "game" } })
active(nil)
print(table.concat(hl.set, ","))
"""

    def test_focus_follows_clicks_only_while_a_game_is_focused(self):
        # Changed only when it needs to: on to 2 for a game, back to 1 for anything else.
        self.assertEqual(run(self.FOCUS), "2,1,2,1")

    def test_off_in_settings(self):
        self.assertEqual(run(self.FOCUS, enabled=False), "")

    def test_what_counts_as_a_game(self):
        out = run('print(M.is_game({class="steam_app_1"}), M.is_game({content_type="game"}), '
                  'M.is_game({tags={"game"}}), M.is_game({class="firefox", content_type="video"}), M.is_game(nil))')
        self.assertEqual(out.split(), ["true", "true", "true", "false", "false"])

    def test_loaded_at_login_and_the_bar_leaves_games_alone(self):
        self.assertIn('require("hyprland.halcyon.games")', (GAMES.parent / "init.lua").read_text())
        bar = (ROOT / "dots/.config/quickshell/ii/modules/ii/bar/Bar.qml").read_text()
        self.assertIn("!HyprlandData.isGame(fullscreenWindow)", bar)
        self.assertIn("?.fullscreen === 1", bar, "only a still-maximized window goes back to fullscreen")


if __name__ == "__main__":
    unittest.main()
