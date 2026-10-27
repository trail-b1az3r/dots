"""Carrying a dragged window to another workspace: carry.lua under real Lua with a stand-in `hl`.
Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARRY_LUA = ROOT / "dots/.config/hypr/hyprland/halcyon/carry.lua"
LUA = shutil.which("lua") or shutil.which("lua5.4")

STUB = r"""
local cursor = { x = 150, y = 150 }
local ws1, ws2, special = { id = 1 }, { id = 2 }, { id = -98, special = true }
local windows = {
  { address = "0xa", floating = false, workspace = ws1, at = { x = 0, y = 0 }, size = { x = 400, y = 400 } },
  { address = "0xb", floating = true,  workspace = ws1, at = { x = 100, y = 100 }, size = { x = 100, y = 100 } },
  { address = "0xc", floating = true,  workspace = ws2, at = { x = 100, y = 100 }, size = { x = 100, y = 100 } },
}
local binds, handlers, moves = {}, {}, {}
hl = {
  bind = function(keys, fn, opts) binds[keys] = { fn = fn, opts = opts } end,
  on = function(ev, fn) handlers[ev] = fn end,
  get_windows = function() return windows end,
  get_cursor_pos = function() return cursor end,
  get_monitors = function() return { { active_workspace = ws1 } } end,
  dispatch = function(d) moves[#moves + 1] = d end,
  dsp = { window = { move = function(t) return t end } },
}
local M = dofile(%s)
local out = {}
-- Press SUPER + left over the floating window, switch to workspace 2: it is carried.
binds["SUPER + mouse:272"].fn()
handlers["workspace.active"](ws2)
out.first = moves[1] and moves[1].window.address or "none"
out.first_ws = moves[1] and moves[1].workspace or "none"
out.follow = moves[1] and tostring(moves[1].follow) or "none"
-- To the scratchpad: not carried.
handlers["workspace.active"](special)
out.special = #moves
-- Let go: nothing more is carried.
binds["mouse:272"].fn()
handlers["workspace.active"](ws2)
out.after_release = #moves
-- A missed release: the cursor has left the window, so it is forgotten.
binds["SUPER + mouse:272"].fn()
cursor = { x = 900, y = 900 }
handlers["workspace.active"](ws2)
cursor = { x = 150, y = 150 }
handlers["workspace.active"](ws2)
out.stale = #moves
local r = binds["mouse:272"].opts
out.release_opts = tostring(r.release and r.non_consuming and r.ignore_mods)
out.press_opts = tostring(binds["SUPER + mouse:272"].opts.non_consuming)
out.tiled = M.window_at({ windows[1] }, { x = 5, y = 5 }, { [1] = true }).address
local parts = {}
for k, v in pairs(out) do parts[#parts + 1] = string.format("%%q: %%q", k, tostring(v)) end
print("{" .. table.concat(parts, ", ") .. "}")
"""


@unittest.skipUnless(LUA, "no lua interpreter")
class CarryTest(unittest.TestCase):
    def setUp(self):
        done = subprocess.run([LUA, "-"], input=STUB % json.dumps(str(CARRY_LUA)), capture_output=True, text=True)
        if done.returncode != 0:
            raise AssertionError(done.stderr)
        self.got = json.loads(done.stdout)

    def test_the_dragged_window_comes_along(self):
        self.assertEqual(self.got["first"], "0xb", "the floating window on top, on a visible workspace")
        self.assertEqual(self.got["first_ws"], "2")
        self.assertEqual(self.got["follow"], "false", "you are already on the new workspace")

    def test_not_to_the_scratchpad(self):
        self.assertEqual(self.got["special"], "1")

    def test_letting_go_ends_it(self):
        self.assertEqual(self.got["after_release"], "1")

    def test_a_missed_release_cannot_carry_later(self):
        self.assertEqual(self.got["stale"], "1")

    def test_the_drag_and_clicks_are_untouched(self):
        self.assertEqual(self.got["press_opts"], "true")
        self.assertEqual(self.got["release_opts"], "true")

    def test_a_tiled_window_too(self):
        self.assertEqual(self.got["tiled"], "0xa")


class WiringTest(unittest.TestCase):
    def test_loaded(self):
        init = (ROOT / "dots/.config/hypr/hyprland/halcyon/init.lua").read_text()
        self.assertIn('require("hyprland.halcyon.carry")', init)


if __name__ == "__main__":
    unittest.main()
