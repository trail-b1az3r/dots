"""The drop-down terminal and lost windows (scratchpad.lua under real Lua with a stand-in `hl`, and halcyon_lost.py).
Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
LUA = shutil.which("lua") or shutil.which("lua5.4")
sys.path.insert(0, str(HALCYON))

import halcyon_lost  # noqa: E402

SCRATCHPAD = r"""
local binds, dispatched, cmds = {}, {}, {}
hl = {
  bind = function(k, f) binds[k] = f end, window_rule = function() end, workspace_rule = function() end,
  exec_cmd = function(c) cmds[#cmds + 1] = c end,
  dispatch = function(d) dispatched[#dispatched + 1] = d end,
  dsp = { workspace = { toggle_special = function(n) return { special = n } end },
          window = { move = function(a) return { move = a.workspace, window = a.window.address } end,
                     float = function(a) return { float = a.action } end, center = function() return { center = true } end },
          focus = function(a) return { focus = a.window } end },
  get_windows = function() return WINDOWS end,
  get_monitors = function() return { { x = 0, y = 0, width = 3840, height = 2160, scale = 2 } } end,
  get_active_workspace = function() return { id = 4 } end,
}
local M = dofile(%s)
WINDOWS = {
  { address = "0xa", class = "firefox", floating = false, at = { x = 10, y = 10 }, size = { x = 800, y = 600 }, workspace = { id = 1 } },
  { address = "0xb", class = "game", floating = true, at = { x = 2500, y = 300 }, size = { x = 800, y = 600 }, workspace = { id = 1 } },
  { address = "0xc", class = "notes", floating = true, at = { x = 9000, y = 9000 }, size = { x = 300, y = 300 }, workspace = { id = -98, special = true } },
}
binds["SUPER + SHIFT + W"]()
local brought = #dispatched
dispatched = {}
binds["SUPER + Z"]()
local launched = cmds[#cmds]
WINDOWS[#WINDOWS + 1] = { address = "0xd", class = "halcyon-dropdown", workspace = { id = -97, special = true } }
binds["SUPER + Z"]()
print(string.format('{"lost": %%d, "brought": %%d, "launched": %%q, "toggled": %%q}', #M.lost(WINDOWS, hl.get_monitors()),
  brought, launched, dispatched[1] and dispatched[1].special or ""))
"""


@unittest.skipUnless(LUA, "lua is not installed")
class ScratchpadLuaTest(unittest.TestCase):
    def test_lost_windows_and_dropdown(self):
        out = subprocess.run([LUA, "-e", SCRATCHPAD % json.dumps(str(HALCYON / "scratchpad.lua"))],
                             capture_output=True, text=True, check=True).stdout
        result = json.loads(out)
        # A 3840x2160 monitor at scale 2 is 1920x1080: the game at x=2500 is off it; the window on a hidden special
        # workspace is put away, not lost.
        self.assertEqual(result["lost"], 1)
        self.assertEqual(result["brought"], 3)                     # moved, focused, centred (it already floats)
        self.assertIn("alacritty --class halcyon-dropdown", result["launched"])
        self.assertEqual(result["toggled"], "dropdown")            # running already: just shown or hidden


class LostCliTest(unittest.TestCase):
    def test_lost(self):
        monitors = [{"x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1},
                    {"x": 1920, "y": 0, "width": 2560, "height": 1440, "scale": 1}]
        clients = [
            {"address": "0x1", "at": [2000, 100], "size": [400, 300], "workspace": {"name": "2"}},
            {"address": "0x2", "at": [-900, 100], "size": [400, 300], "workspace": {"name": "1"}},
            {"address": "0x3", "at": [9000, 0], "size": [10, 10], "workspace": {"name": "special:special"}},
            {"address": "0x4", "at": [9000, 0], "size": [10, 10], "workspace": {"name": "1"}, "mapped": False},
        ]
        self.assertEqual([c["address"] for c in halcyon_lost.lost(clients, monitors)], ["0x2"])

    def test_wired_up(self):
        self.assertIn('require("hyprland.halcyon.scratchpad")', (HALCYON / "init.lua").read_text())


if __name__ == "__main__":
    unittest.main()
