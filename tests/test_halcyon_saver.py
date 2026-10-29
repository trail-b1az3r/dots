"""The super battery saver (halcyon_saver.py) and the Alacritty switch (halcyon_terminal.py), against stub nmcli,
brightnessctl, powerprofilesctl and hyprctl that log what they are asked. Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
SAVER = HALCYON / "halcyon_saver.py"
TERMINAL = HALCYON / "halcyon_terminal.py"

STUB = """#!/bin/sh
echo "$(basename "$0") $*" >> "$LOG"
case "$(basename "$0") $*" in
  "nmcli -t -f UUID,TYPE,AUTOCONNECT connection show") printf 'aaa:802-11-wireless:yes\\nbbb:802-11-wireless:no\\nccc:802-3-ethernet:yes\\n' ;;
  "nmcli -t -f STATE general status") echo "${NET:-connected}" ;;
  "brightnessctl -m -c backlight get") echo 742 ;;
  "powerprofilesctl get") echo balanced ;;
esac
"""


class SaverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for tool in ("nmcli", "brightnessctl", "powerprofilesctl", "hyprctl", "notify-send"):
            (self.bin / tool).write_text(STUB)
            (self.bin / tool).chmod(0o755)
        self.log = self.tmp / "log"
        self.env = {**os.environ, "PATH": f"{self.bin}:/usr/bin:/bin", "LOG": str(self.log),
                    "XDG_STATE_HOME": str(self.tmp / "state"), "HYPRLAND_INSTANCE_SIGNATURE": "test"}

    def saver(self, *args, **env):
        return subprocess.run([sys.executable, str(SAVER), *args], env={**self.env, **env}, capture_output=True,
                              text=True, check=False)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_on_then_off_puts_everything_back(self):
        self.assertEqual(self.saver("on").returncode, 0)
        state = json.loads((self.tmp / "state/halcyon/saver.json").read_text())
        self.assertEqual(state, {"brightness": "742", "profile": "balanced", "autoconnect": ["aaa"], "max_fps": 12})
        calls = self.calls()
        self.assertIn("brightnessctl -q -c backlight set 20%", calls)
        self.assertIn("powerprofilesctl set power-saver", calls)
        # Only the Wi-Fi network that autoconnected is changed; Ethernet is left alone.
        self.assertIn("nmcli connection modify aaa connection.autoconnect no", calls)
        self.assertFalse(any("modify bbb" in c or "modify ccc" in c for c in calls))
        self.assertIn("hyprctl reload", calls)

        self.log.unlink()
        self.assertEqual(self.saver("off").returncode, 0)
        self.assertFalse((self.tmp / "state/halcyon/saver.json").exists())
        calls = self.calls()
        self.assertIn("nmcli connection modify aaa connection.autoconnect yes", calls)
        self.assertIn("brightnessctl -q -c backlight set 742", calls)
        self.assertIn("powerprofilesctl set balanced", calls)

    def test_toggle_and_status(self):
        self.saver("toggle")
        self.assertIn("on", self.saver("status").stdout)
        self.saver("toggle")
        self.assertIn("off", self.saver("status").stdout)

    def test_kick_only_when_on_and_down(self):
        self.saver("kick", NET="disconnected")
        self.assertNotIn("nmcli -t -f STATE general status", self.calls())   # off: does nothing at all
        self.saver("on")
        self.log.unlink()
        self.saver("kick", NET="connected")
        self.assertEqual(self.calls(), ["nmcli -t -f STATE general status"])  # up: leaves it

    def test_compositor_part(self):
        lua = (HALCYON / "saver.lua").read_text()
        self.assertIn('/halcyon/saver.json', lua)
        self.assertIn("max_fps", lua)
        self.assertIn("if C.maxFps then", lua)
        self.assertIn('require("hyprland.halcyon.saver")', (HALCYON / "init.lua").read_text())
        idle = (ROOT / "dots/.config/hypr/hypridle.conf").read_text()
        self.assertIn("unlock_cmd = $saver_kick", idle)
        self.assertIn("$saver_kick", idle.split("after_sleep_cmd")[1].splitlines()[0])


class TerminalTest(unittest.TestCase):
    def test_kittys_pins_go_to_alacritty_once(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "bin").mkdir()
        (tmp / "bin/alacritty").write_text("#!/bin/sh\n")
        (tmp / "bin/alacritty").chmod(0o755)
        apps = tmp / "data/applications"
        apps.mkdir(parents=True)
        (apps / "Alacritty.desktop").write_text("[Desktop Entry]\nName=Alacritty\n")
        config = tmp / "config/illogical-impulse/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"dock": {"pinnedApps": ["loaf", "kitty"]}, "launcher": {"pinnedApps": ["kitty"]}}))
        env = {**os.environ, "PATH": f"{tmp / 'bin'}:/usr/bin:/bin", "XDG_CONFIG_HOME": str(tmp / "config"),
               "XDG_DATA_HOME": str(tmp / "data"), "XDG_STATE_HOME": str(tmp / "state")}
        run = lambda: subprocess.run([sys.executable, str(TERMINAL), "login"], env=env, capture_output=True, text=True, check=True)
        run()
        data = json.loads(config.read_text())
        self.assertEqual(data["dock"]["pinnedApps"], ["loaf", "Alacritty"])
        self.assertEqual(data["launcher"]["pinnedApps"], ["Alacritty"])
        # Once: pinning kitty again afterwards stays.
        data["dock"]["pinnedApps"].append("kitty")
        config.write_text(json.dumps(data))
        run()
        self.assertEqual(json.loads(config.read_text())["dock"]["pinnedApps"], ["loaf", "Alacritty", "kitty"])

    def test_ctrl_c_interrupts(self):
        conf = (ROOT / "dots/.config/alacritty/alacritty.toml").read_text()
        self.assertIn('{ key = "C", mods = "Control|Shift", action = "Copy" }', conf)
        self.assertNotIn('mods = "Control", action = "Copy"', conf)
        self.assertNotIn("map ctrl+c ", (ROOT / "dots/.config/kitty/kitty.conf").read_text())
        variables = (ROOT / "dots/.config/hypr/hyprland/variables.lua").read_text()
        self.assertIn("launch_first_available.sh 'alacritty'", variables)


if __name__ == "__main__":
    unittest.main()
