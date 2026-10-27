"""A maximised tiled window hiding the others (maximise.lua), and hypr mode turning itself off (modes.lua), under real
Lua with a stand-in `hl`. Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
LUA = shutil.which("lua") or shutil.which("lua5.4")

MAXIMISE = r"""
local handlers, cmds = {}, {}
local ws = { id = 3 }
local term = { address = "0xa", class = "kitty", floating = false, fullscreen = 1, workspace = ws }
local other = { address = "0xb", class = "firefox", floating = false, fullscreen = 0, workspace = ws }
local float = { address = "0xc", class = "pavucontrol", floating = true, fullscreen = 0, workspace = ws }
hl = { on = function(e, f) handlers[e] = f end, exec_cmd = function(c) cmds[#cmds + 1] = c end,
       get_workspace_windows = function() return WINDOWS end }
local M = dofile(%s)
WINDOWS = { term, other }
handlers["window.fullscreen"](term)
local warned = #cmds
WINDOWS = { term, float }
handlers["window.fullscreen"](term)
local alone = #cmds
term.fullscreen = 2
WINDOWS = { term, other }
handlers["window.fullscreen"](term)
print(string.format('{"warned": %%d, "alone": %%d, "fullscreen": %%d, "cmd": %%q}', warned, alone, #cmds, cmds[1] or ""))
"""

MODES = r"""
local binds, timers, dispatched, submap = {}, {}, {}, ""
hl = {
  bind = function(k, f, o) binds[k] = f end,
  define_submap = function(name, f) f() end,
  dispatch = function(d) dispatched[#dispatched + 1] = d; if d.submap then submap = (d.submap == "reset") and "" or d.submap end end,
  get_current_submap = function() return submap end,
  timer = function(f, o) local t = { f = f, timeout = o.timeout, on = true }
    function t:set_enabled(v) self.on = v end
    timers[#timers + 1] = t; return t end,
  dsp = { submap = function(n) return { submap = n } end, exec_cmd = function(c) return { exec = c } end,
          window = { fullscreen = function(t) return { fs = t } end } },
}
HOME = "/nonexistent"
is_file_exists = function() return false end
package.path = %s .. "/?.lua;" .. package.path
package.loaded["hyprland.halcyon.hypr_mode"] = {
  toggle = "SUPER + CTRL + H", exit = "Escape", idle_exit = 10,
  binds = { { "SHIFT + M", hl.dsp.window.fullscreen({ mode = "maximized" }), "Hypr mode: Maximise" } },
}
dofile(%s)
binds["SUPER + CTRL + H"]()
local on = submap
local armed = timers[#timers].timeout
binds["SHIFT + M"]()
local rearmed = #timers
timers[#timers].f()
print(string.format('{"on": %%q, "armed": %%d, "rearmed": %%d, "after": %%q, "first_off": %%s}',
  on, armed, rearmed, submap, tostring(timers[1].on)))
"""


def run(script):
    done = subprocess.run([LUA, "-"], input=script, capture_output=True, text=True)
    if done.returncode:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


@unittest.skipUnless(LUA, "no lua interpreter")
class MaximiseTest(unittest.TestCase):
    def test_warns_only_when_tiles_are_hidden(self):
        got = run(MAXIMISE % json.dumps(str(HALCYON / "maximise.lua")))
        self.assertEqual(got["warned"], 1, "a maximised terminal over a tiled browser")
        self.assertEqual(got["alone"], 1, "nothing tiled behind it: no warning")
        self.assertEqual(got["fullscreen"], 1, "real fullscreen is meant to cover everything")
        self.assertIn("address:0xa", got["cmd"])
        self.assertIn('action = "unset"', got["cmd"])


@unittest.skipUnless(LUA, "no lua interpreter")
class HyprModeIdleTest(unittest.TestCase):
    def test_the_mode_turns_itself_off(self):
        got = run(MODES % (json.dumps(str(HALCYON.parent.parent)), json.dumps(str(HALCYON / "modes.lua"))))
        self.assertEqual(got["on"], "hypr")
        self.assertEqual(got["armed"], 10000)
        self.assertEqual(got["rearmed"], 2, "a key used starts the wait again")
        self.assertIs(got["first_off"], False, "the earlier wait is cancelled")
        self.assertEqual(got["after"], "", "then, idle, the mode is left")

    def test_maximise_needs_shift(self):
        text = (HALCYON / "hypr_mode.lua").read_text()
        self.assertIn('{ "SHIFT + M", hl.dsp.window.fullscreen', text)
        self.assertNotIn('{ "M", hl.dsp.window.fullscreen', text)


if __name__ == "__main__":
    unittest.main()
