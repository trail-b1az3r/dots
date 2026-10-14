"""Mini windows: mini.lua under real Lua with a stand-in `hl` (with and without hyprland-plus's mini dispatcher), and
the shell's MiniWindows service that the title bars, the bar's window buttons and the keybind share.
Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MINI_LUA = ROOT / "dots/.config/hypr/hyprland/halcyon/mini.lua"
QS = ROOT / "dots/.config/quickshell/ii"
LUA = shutil.which("lua") or shutil.which("lua5.4")

STUB = r"""
hl = { binds = {}, config_set = {} }
hl.config = function(t) hl.config_set[#hl.config_set + 1] = t end
hl.bind = function(keys, action, opts) hl.binds[#hl.binds + 1] = { keys = keys, action = action, desc = opts and opts.description } end
hl.dsp = { window = {} }
hl.dsp.exec_cmd = function(cmd) return { exec = cmd } end
if WITH_MINI then hl.dsp.window.mini = function() return { mini = true } end end
dofile(%s)
local b = hl.binds[1]
print(string.format('{"binds": %%d, "keys": %%q, "exec": %%q, "native": %%s, "width": %%s, "height": %%s}', #hl.binds, b.keys,
  b.action.exec or "", tostring(b.action.mini == true),
  hl.config_set[1] and hl.config_set[1].binds.mini_width or "null",
  hl.config_set[1] and hl.config_set[1].binds.mini_height or "null"))
"""


def run_mini(with_mini):
    script = f"WITH_MINI = {'true' if with_mini else 'false'}\n" + STUB % json.dumps(str(MINI_LUA))
    done = subprocess.run([LUA, "-"], input=script, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


@unittest.skipUnless(LUA, "no lua interpreter")
class MiniLuaTest(unittest.TestCase):
    def test_hyprland_plus_does_it_itself_at_a_size_you_can_see(self):
        got = run_mini(True)
        self.assertEqual(got["binds"], 1)
        self.assertEqual(got["keys"], "SUPER + CTRL + N")
        self.assertTrue(got["native"])
        self.assertEqual((got["width"], got["height"]), (240, 150))

    def test_stock_hyprland_asks_the_shell(self):
        got = run_mini(False)
        self.assertEqual(got["binds"], 1, "the keybind works without the fork too")
        self.assertEqual(got["keys"], "SUPER + CTRL + N")
        self.assertFalse(got["native"])
        self.assertIn("ipc call miniWindows toggleActive", got["exec"])
        self.assertIsNone(got["width"])


class ShellWiringTest(unittest.TestCase):
    def read(self, rel):
        return (QS / rel).read_text()

    def test_one_service_for_every_way_in(self):
        service = self.read("services/MiniWindows.qml")
        self.assertIn('target: "miniWindows"', service)
        self.assertIn("function toggleActive(): void", service)
        # Stock Hyprland: a tiled window floats first, and tiles again when it comes back.
        self.assertIn('hl.dsp.window.float({ action = "enable"', service)
        self.assertIn('hl.dsp.window.float({ action = "disable"', service)
        self.assertIn("wasTiled", service)
        self.assertIn("readonly property int miniWidth: 240", service)
        self.assertIn("readonly property int miniHeight: 150", service)

        bars = self.read("modules/ii/floatingTitleBars/FloatingTitleBars.qml")
        self.assertIn("MiniWindows.minimize(bar.win.address)", bars)
        self.assertIn("MiniWindows.isMini(win.address)", bars)
        self.assertNotIn("property var minis", bars, "the title bars no longer keep a state of their own")
        self.assertIn("MiniWindows.toggle(root.address)", self.read("modules/ii/bar/WindowButtons.qml"))

    def test_services_exist_from_start_up(self):
        # Quickshell makes a singleton only when it is first used; the keybind's IPC and the reminders must not
        # depend on a panel having used them.
        shell = self.read("shell.qml")
        self.assertIn("MiniWindows.load()", shell)
        self.assertIn("CalendarEvents.load()", shell)


if __name__ == "__main__":
    unittest.main()
