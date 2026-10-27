"""`halcyon audio` against stand-ins for systemctl, loginctl, pw-dump, pgrep, pkill and pactl, set up as a Hyprland
login straight after a KDE one: KDE's variables and portal still in the systemd user manager, EasyEffects running
and holding the defaults. The fakes keep their state in a JSON file, so what `boot` does shows in the next status.
Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon_audio.py"

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
path = os.environ["FAKE_STATE"]
state = json.load(open(path))
name = os.path.basename(sys.argv[0])
args = sys.argv[1:]
state.setdefault("calls", []).append([name] + args)
out, code = "", 0
if name == "systemctl":
    a = [x for x in args if x not in ("--user", "--quiet", "--no-pager")]
    if a[0] == "is-active":
        code = 0 if a[1] in state["active"] else 3
    elif a[0] == "show-environment":
        out = "\n".join(f"{k}={v}" for k, v in state["env"].items())
    elif a[0] == "unset-environment":
        for k in a[1:]:
            state["env"].pop(k, None)
    elif a[0] == "import-environment":
        for k in a[1:]:
            state["env"][k] = os.environ.get(k, "")
    elif a[0] == "stop":
        state["active"] = [u for u in state["active"] if u not in a[1:]]
    elif a[0] in ("start", "restart"):
        state["active"] += [u for u in a[1:] if u not in state["active"]]
elif name == "loginctl":
    out = "Active=yes\nType=wayland\nSeat=seat0\nRemote=no"
elif name == "pgrep":
    code = 0 if state["easyeffects"] else 1
elif name == "pkill":
    state["easyeffects"] = False
elif name == "pactl":
    key = "default_sink" if args[0] == "set-default-sink" else "default_source"
    state[key] = args[1]
elif name == "pw-dump":
    nodes = [
        {"type": "PipeWire:Interface:Node", "info": {"props": {"media.class": "Audio/Sink", "node.name": "easyeffects_sink", "node.description": "Easy Effects Sink"}}},
        {"type": "PipeWire:Interface:Node", "info": {"props": {"media.class": "Audio/Sink", "node.name": "alsa_output.usb-headset", "node.description": "Headset"}}},
        {"type": "PipeWire:Interface:Node", "info": {"props": {"media.class": "Audio/Source/Virtual", "node.name": "easyeffects_source", "node.description": "Easy Effects Source"}}},
        {"type": "PipeWire:Interface:Node", "info": {"props": {"media.class": "Audio/Source", "node.name": "alsa_input.usb-webcam", "node.description": "Webcam Microphone"}}},
        {"type": "PipeWire:Interface:Node", "info": {"props": {"media.class": "Video/Source", "node.name": "v4l2_input.webcam", "node.description": "Webcam"}}},
        {"type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": [
            {"key": "default.audio.sink", "value": {"name": state["default_sink"]}},
            {"key": "default.audio.source", "value": {"name": state["default_source"]}}]},
    ]
    out = json.dumps(nodes)
json.dump(state, open(path, "w"))
print(out)
sys.exit(code)
'''

UNITS = ["pipewire.service", "pipewire-pulse.service", "wireplumber.service"]


class AudioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        bin_dir = base / "bin"
        bin_dir.mkdir()
        for name in ("systemctl", "loginctl", "pgrep", "pkill", "pactl", "pw-dump"):
            (bin_dir / name).write_text(FAKE)
            (bin_dir / name).chmod(0o755)
        (base / "dev/snd").mkdir(parents=True)
        self.state_file = base / "state.json"
        self.state = {
            "active": UNITS + ["xdg-desktop-portal.service", "xdg-desktop-portal-kde.service"],
            "env": {"XDG_CURRENT_DESKTOP": "KDE", "KDE_FULL_SESSION": "true", "KDE_SESSION_VERSION": "6"},
            "easyeffects": True,
            "default_sink": "easyeffects_sink",
            "default_source": "easyeffects_source",
        }
        self.save()
        self.env = {
            "PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(base), "FAKE_STATE": str(self.state_file),
            "XDG_STATE_HOME": str(base / "state"), "HALCYON_DEV": str(base / "dev"), "HALCYON_AUDIO_SETTLE": "0",
            "XDG_CURRENT_DESKTOP": "Hyprland", "WAYLAND_DISPLAY": "wayland-1", "XDG_SESSION_ID": "3",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.state_file.write_text(json.dumps(self.state))

    def load(self):
        return json.loads(self.state_file.read_text())

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=self.env,
                              timeout=60, check=False)

    def status(self):
        done = self.run_tool("--json")
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_status_names_easyeffects_and_kde(self):
        got = self.status()
        text = " ".join(got["problems"])
        self.assertIn("EasyEffects is running", text)
        self.assertIn("KDE's session environment or portal", text)
        self.assertEqual([c["name"] for c in got["pipewire"]["cameras"]], ["v4l2_input.webcam"])
        self.assertEqual(got["kde_leftovers"], ["KDE_FULL_SESSION", "KDE_SESSION_VERSION"])

    def test_boot_puts_the_session_right(self):
        done = self.run_tool("boot")
        self.assertEqual(done.returncode, 0, done.stderr)
        state = self.load()
        self.assertNotIn("KDE_FULL_SESSION", state["env"])
        self.assertEqual(state["env"]["XDG_CURRENT_DESKTOP"], "Hyprland")
        self.assertNotIn("xdg-desktop-portal-kde.service", state["active"])
        self.assertIn("xdg-desktop-portal.service", state["active"], "the portal is back, with Hyprland's backend")
        self.assertFalse(state["easyeffects"], "not turned on, so it is closed")
        self.assertEqual(state["default_sink"], "alsa_output.usb-headset")
        self.assertEqual(state["default_source"], "alsa_input.usb-webcam")
        self.assertEqual(self.status()["problems"], [])

    def test_easyeffects_stays_when_turned_on(self):
        self.assertEqual(self.run_tool("easyeffects", "on").returncode, 0)
        self.assertEqual(self.run_tool("easyeffects").stdout.strip(), "on")
        self.run_tool("boot")
        state = self.load()
        self.assertTrue(state["easyeffects"])
        self.assertEqual(state["default_sink"], "easyeffects_sink", "its defaults are left alone while it runs")

    def test_easyeffects_off_hands_the_defaults_back(self):
        self.run_tool("easyeffects", "on")
        self.run_tool("easyeffects", "off")
        state = self.load()
        self.assertFalse(state["easyeffects"])
        self.assertEqual(state["default_source"], "alsa_input.usb-webcam")

    def test_sound_services_started_when_down(self):
        self.state["active"] = []
        self.save()
        self.assertIn("pipewire.service isn't running", " ".join(self.status()["problems"]))
        self.run_tool("boot")
        self.assertTrue(set(UNITS) <= set(self.load()["active"]))

    def test_fix_restarts_and_reports_clean(self):
        done = self.run_tool("fix")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        restarts = [c for c in self.load()["calls"] if c[:3] == ["systemctl", "--user", "restart"]]
        self.assertTrue(restarts and set(UNITS) <= set(restarts[0][3:]))

    def test_unopenable_webcam_is_named(self):
        cam = Path(self.env["HALCYON_DEV"]) / "video0"
        cam.write_text("")
        cam.chmod(0)
        if os.access(cam, os.R_OK):
            self.skipTest("running as root: every file can be opened")
        self.assertIn("you may not open the webcam (video0)", " ".join(self.status()["problems"]))

    def test_report_file(self):
        self.env["HALCYON_AUDIO_REPORT"] = str(Path(self.tmp.name) / "r.txt")
        self.assertEqual(self.run_tool("report").returncode, 0)
        self.assertIn("# halcyon audio report", (Path(self.tmp.name) / "r.txt").read_text())


class WiringTest(unittest.TestCase):
    def test_login_and_easyeffects(self):
        init = (ROOT / "dots/.config/hypr/hyprland/halcyon/init.lua").read_text()
        self.assertIn("halcyon_audio.py boot", init)
        execs = (ROOT / "dots/.config/hypr/hyprland/execs.lua").read_text()
        self.assertIn("halcyon/easyeffects", execs, "EasyEffects only starts when turned on")


if __name__ == "__main__":
    unittest.main()
