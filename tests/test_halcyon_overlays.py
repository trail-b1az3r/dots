"""`halcyon osd`, `halcyon annotate` and halcyon-osd, against stand-in avizo, wayscriber, wpctl, brightnessctl,
pgrep and pkill. The configs they write are read back with a real TOML and INI parser.
Run: python3 -m unittest discover -s tests"""

import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
TOOL = HALCYON / "halcyon_overlays.py"
OSD = HALCYON / "halcyon-osd"

COLOURS = {
    "background": "#101418", "surface": "#101418", "surface_container": "#1C2026", "surface_container_low": "#181C22",
    "surface_container_highest": "#31353C", "on_surface": "#E0E2E8", "outline": "#8B919A", "outline_variant": "#41474F",
    "primary": "#FF8A7A", "tertiary": "#7ED6C4",
}


def script(body: str) -> str:
    return "#!/bin/sh\n" + body + "\n"


class Env(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.running = self.tmp / "running"
        self.running.mkdir()
        self.log = self.tmp / "calls.log"
        self.config = self.tmp / "config"
        self.state = self.tmp / "state"
        (self.state / "quickshell/user/generated").mkdir(parents=True)
        (self.state / "quickshell/user/generated/colors.json").write_text(json.dumps(COLOURS))
        # What is "running" is a file per process name.
        self.fake("pgrep", f'[ -e "{self.running}/$2" ]')
        self.fake("pkill", f'rm -f "{self.running}/$2"')
        self.fake("notify-send", f'echo "notify $*" >> "{self.log}"')

    def fake(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(script(body))
        path.chmod(0o755)

    def install(self, *names):
        for name in names:
            if name == "avizo":
                self.fake("avizo-service", f'echo "avizo-service" >> "{self.log}"; touch "{self.running}/avizo-service"; sleep 30')
                self.fake("avizo-client", f'echo "avizo-client $*" >> "{self.log}"')
            elif name == "wayscriber":
                self.fake("wayscriber", f'echo "wayscriber $*" >> "{self.log}"; '
                                        f'case "$1" in --daemon) touch "{self.running}/wayscriber"; sleep 30;; esac')
            elif name == "wpctl":
                self.fake("wpctl", f'case "$1" in get-volume) cat "{self.tmp}/wpctl-$2" ;; esac')
            elif name == "brightnessctl":
                self.fake("brightnessctl", f'[ "$1" = "-m" ] && echo "intel_backlight,backlight,4687,${{BRIGHTNESS:-50}}%,9375"')

    def env(self, **extra):
        return {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(self.tmp / "home"),
                "XDG_CONFIG_HOME": str(self.config), "XDG_STATE_HOME": str(self.state), **extra}

    def run_tool(self, *args, **extra):
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                              env=self.env(**extra), timeout=60)

    def calls(self) -> str:
        return self.log.read_text() if self.log.exists() else ""

    def wait_for(self, text: str, seconds: float = 3.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if text in self.calls():
                return True
            time.sleep(0.05)
        return False


class SyncTest(Env):
    def test_nothing_is_written_for_a_tool_that_is_not_installed(self):
        done = self.run_tool("overlays", "sync")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((self.config / "avizo/config.ini").exists())
        self.assertFalse((self.config / "wayscriber/config.toml").exists())
        self.assertIn("not installed", done.stdout)

    def test_avizo_takes_the_themes_colours_and_shape(self):
        self.install("avizo")
        self.run_tool("overlays", "sync", "--quiet")
        ini = configparser.ConfigParser()
        ini.read(self.config / "avizo/config.ini")
        section = ini["default"]
        self.assertEqual(section["bar-fg-color"], "rgba(255, 138, 122, 1)", "the bar is the theme's primary")
        self.assertEqual(section["background"], "rgba(28, 32, 38, 0.9)")
        self.assertEqual(section["border-radius"], "18", "12 px of window rounding, one and a half times")
        self.assertEqual(section["block-count"], "16")
        self.assertTrue((self.config / "avizo/config.ini").read_text().startswith("; halcyon-managed"))

    def test_the_avizo_shape_follows_the_themes_rounding(self):
        self.install("avizo")
        (self.state / "halcyon").mkdir()
        (self.state / "halcyon/active").write_text("red-sun")
        self.run_tool("overlays", "sync", "--quiet")
        rounding = json.loads((HALCYON / "themes/red-sun.json").read_text())["hyprland"]["rounding"]
        ini = configparser.ConfigParser()
        ini.read(self.config / "avizo/config.ini")
        self.assertEqual(int(ini["default"]["border-radius"]), min(32, max(6, round(rounding * 1.5))))

    def test_wayscriber_gets_a_valid_pen_palette_from_the_theme(self):
        self.install("wayscriber")
        self.run_tool("overlays", "sync", "--quiet")
        text = (self.config / "wayscriber/config.toml").read_text()
        self.assertTrue(text.startswith("# halcyon-managed"))
        data = tomllib.loads(text)
        self.assertEqual(data["drawing"]["default_color"], "#FF8A7A")
        colours = data["drawing"]["quick_colors"]
        self.assertEqual(len(colours), 12)
        self.assertEqual(colours[0], {"label": "Accent", "color": "#FF8A7A"})
        self.assertEqual(colours[1], {"label": "Tertiary", "color": "#7ED6C4"})
        self.assertNotEqual(colours[2]["color"], "#F5333F", "the stock red leans toward the theme")
        for entry in colours:
            self.assertRegex(entry["color"], r"^#[0-9A-F]{6}$")
        for key in ("status_bar_style", "help_overlay_style"):
            panel = data["ui"][key]
            self.assertEqual(len(panel["bg_color"]), 4)
            self.assertTrue(all(0 <= channel <= 1 for channel in panel["bg_color"]))

    def test_a_config_you_edited_is_never_overwritten(self):
        self.install("avizo", "wayscriber")
        for path, text in ((self.config / "avizo/config.ini", "[default]\nwidth = 99\n"),
                           (self.config / "wayscriber/config.toml", "[drawing]\ndefault_color = \"blue\"\n")):
            path.parent.mkdir(parents=True)
            path.write_text(text)
        done = self.run_tool("overlays", "sync")
        self.assertIn("is yours", done.stdout)
        self.assertEqual((self.config / "avizo/config.ini").read_text(), "[default]\nwidth = 99\n")
        self.assertEqual((self.config / "wayscriber/config.toml").read_text(), "[drawing]\ndefault_color = \"blue\"\n")

    def test_a_config_halcyon_wrote_is_rewritten_with_new_colours(self):
        self.install("avizo")
        self.run_tool("overlays", "sync", "--quiet")
        colours = dict(COLOURS, primary="#112233")
        (self.state / "quickshell/user/generated/colors.json").write_text(json.dumps(colours))
        self.run_tool("overlays", "sync", "--quiet")
        self.assertIn("rgba(17, 34, 51, 1)", (self.config / "avizo/config.ini").read_text())


class OsdTest(Env):
    def test_avizo_cannot_be_chosen_when_it_is_not_installed(self):
        done = self.run_tool("osd", "avizo")
        self.assertEqual(done.returncode, 1)
        self.assertIn("not installed", done.stderr)
        self.assertFalse((self.state / "halcyon/osd-avizo").exists())

    def test_choosing_avizo_sets_everything_it_needs(self):
        self.install("avizo")
        done = self.run_tool("osd", "avizo")
        self.assertEqual(done.returncode, 0, done.stderr)
        halcyon = self.state / "halcyon"
        self.assertTrue((halcyon / "osd-avizo").exists(), "halcyon-osd checks this")
        self.assertIn('HALCYON_OSD = "avizo"', (halcyon / "overlays.lua").read_text())
        self.assertEqual(json.loads((halcyon / "overlays.json").read_text())["osd"], "avizo")
        shell = json.loads((self.config / "illogical-impulse/config.json").read_text())
        self.assertEqual(shell["osd"]["provider"], "avizo", "the shell's own popup hides")
        self.assertTrue(self.wait_for("avizo-service"), "the service is started")
        self.assertTrue((self.config / "avizo/config.ini").exists(), "and themed")

    def test_going_back_to_the_shells_popup_stops_avizo(self):
        self.install("avizo")
        self.run_tool("osd", "avizo")
        self.assertTrue(self.wait_for("avizo-service"))
        done = self.run_tool("osd", "shell")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((self.state / "halcyon/osd-avizo").exists())
        self.assertFalse((self.running / "avizo-service").exists(), "stopped")
        shell = json.loads((self.config / "illogical-impulse/config.json").read_text())
        self.assertEqual(shell["osd"]["provider"], "shell")

    def test_the_other_shell_settings_are_kept(self):
        self.install("avizo")
        path = self.config / "illogical-impulse/config.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"bar": {"vertical": True}, "osd": {"timeout": 2500}}))
        self.run_tool("osd", "avizo")
        shell = json.loads(path.read_text())
        self.assertEqual(shell["bar"], {"vertical": True})
        self.assertEqual(shell["osd"], {"timeout": 2500, "provider": "avizo"})

    def test_a_shell_config_that_cannot_be_read_is_not_overwritten(self):
        self.install("avizo")
        path = self.config / "illogical-impulse/config.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ not json")
        self.run_tool("osd", "avizo")
        self.assertEqual(path.read_text(), "{ not json")

    def test_status_says_what_is_on(self):
        self.install("avizo")
        data = json.loads(self.run_tool("osd", "--json").stdout)
        self.assertEqual(data["provider"], "shell")
        self.assertTrue(data["avizo_installed"])
        self.assertFalse(data["avizo_running"])
        self.assertEqual(data["avizo_config"], "none")

    def test_the_test_command_shows_a_popup(self):
        self.install("avizo")
        done = self.run_tool("osd", "test")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("avizo-client --image-resource=volume_high --progress=0.62", self.calls())


class AnnotateTest(Env):
    def test_on_starts_the_daemon_and_remembers_it_for_login(self):
        self.install("wayscriber")
        done = self.run_tool("annotate", "on")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("wayscriber --daemon", self.calls())
        self.assertIn("HALCYON_ANNOTATE = true", (self.state / "halcyon/overlays.lua").read_text())
        shell = json.loads((self.config / "illogical-impulse/config.json").read_text())
        self.assertIs(shell["halcyon"]["annotate"]["enable"], True)

    def test_off_stops_it_and_keeps_it_off_at_login(self):
        self.install("wayscriber")
        self.run_tool("annotate", "on")
        self.run_tool("annotate", "off")
        self.assertFalse((self.running / "wayscriber").exists())
        self.assertIn("HALCYON_ANNOTATE = false", (self.state / "halcyon/overlays.lua").read_text())

    def test_toggle_starts_the_daemon_first_when_it_is_not_running(self):
        self.install("wayscriber")
        done = self.run_tool("annotate", "toggle")
        self.assertEqual(done.returncode, 0, done.stderr)
        calls = self.calls().splitlines()
        self.assertEqual([c for c in calls if c.startswith("wayscriber")], ["wayscriber --daemon", "wayscriber --daemon-toggle"])

    def test_toggle_just_toggles_when_it_is_running(self):
        self.install("wayscriber")
        (self.running / "wayscriber").touch()
        self.run_tool("annotate", "toggle")
        self.assertEqual([c for c in self.calls().splitlines() if c.startswith("wayscriber")], ["wayscriber --daemon-toggle"])

    def test_a_key_press_without_wayscriber_says_so_on_screen(self):
        done = self.run_tool("annotate", "toggle")
        self.assertEqual(done.returncode, 1)
        self.assertIn("notify", self.calls())
        self.assertIn("Wayscriber is not installed", self.calls())

    def test_status(self):
        data = json.loads(self.run_tool("annotate", "--json").stdout)
        self.assertEqual(data, {"installed": False, "running": False, "at_login": True, "config": "none"})


class HalcyonOsdScript(Env):
    def run_osd(self, *args, **extra):
        return subprocess.run(["sh", str(OSD), *args], capture_output=True, text=True, env=self.env(**extra), timeout=30)

    def avizo_on(self):
        (self.state / "halcyon").mkdir(parents=True, exist_ok=True)
        (self.state / "halcyon/osd-avizo").touch()
        self.install("avizo", "wpctl", "brightnessctl")

    def test_it_does_nothing_with_the_shells_popup(self):
        self.install("avizo", "wpctl")
        (self.tmp / "wpctl-@DEFAULT_AUDIO_SINK@").write_text("Volume: 0.50\n")
        self.assertEqual(self.run_osd("volume").returncode, 0)
        self.assertEqual(self.calls(), "")

    def test_volume_levels_pick_the_icon(self):
        self.avizo_on()
        for volume, expected in (("0.00", "volume_low"), ("0.10", "volume_low"), ("0.33", "volume_low"),
                                 ("0.34", "volume_medium"), ("0.50", "volume_medium"), ("0.66", "volume_medium"),
                                 ("0.67", "volume_high"), ("0.90", "volume_high")):
            self.log.write_text("")
            (self.tmp / "wpctl-@DEFAULT_AUDIO_SINK@").write_text(f"Volume: {volume}\n")
            self.assertEqual(self.run_osd("volume").returncode, 0)
            self.assertEqual(self.calls().strip(), f"avizo-client --image-resource={expected} --progress={float(volume):.3f}")

    def test_muted_shows_the_muted_icon_and_keeps_the_level(self):
        self.avizo_on()
        (self.tmp / "wpctl-@DEFAULT_AUDIO_SINK@").write_text("Volume: 0.42 [MUTED]\n")
        self.run_osd("volume")
        self.assertEqual(self.calls().strip(), "avizo-client --image-resource=volume_muted --progress=0.420")

    def test_boosted_volume_fills_the_bar_but_does_not_overflow_it(self):
        self.avizo_on()
        (self.tmp / "wpctl-@DEFAULT_AUDIO_SINK@").write_text("Volume: 1.35\n")
        self.run_osd("volume")
        self.assertEqual(self.calls().strip(), "avizo-client --image-resource=volume_high --progress=1.000")

    def test_the_microphone_has_its_own_icons(self):
        self.avizo_on()
        (self.tmp / "wpctl-@DEFAULT_AUDIO_SOURCE@").write_text("Volume: 0.80 [MUTED]\n")
        self.run_osd("mic")
        self.assertEqual(self.calls().strip(), "avizo-client --image-resource=mic_muted --progress=0.800")

    def test_brightness_reads_the_percentage(self):
        self.avizo_on()
        self.run_osd("brightness", BRIGHTNESS="73")
        self.assertEqual(self.calls().strip(), "avizo-client --image-resource=brightness_high --progress=0.730")

    def test_an_unknown_argument_is_refused(self):
        self.avizo_on()
        self.assertEqual(self.run_osd("bogus").returncode, 2)

    def test_it_is_quiet_when_wpctl_fails(self):
        self.avizo_on()
        self.fake("wpctl", "exit 1")
        self.assertEqual(self.run_osd("volume").returncode, 0)
        self.assertEqual(self.calls(), "")


class WiringTest(unittest.TestCase):
    def test_the_media_keys_call_halcyon_osd_after_changing_the_level(self):
        keybinds = (ROOT / "dots/.config/hypr/hyprland/keybinds.lua").read_text()
        for action, what in (("set-volume @DEFAULT_AUDIO_SINK@ 2%+", "volume"), ("set-volume @DEFAULT_AUDIO_SINK@ 2%-", "volume"),
                             ("set-mute @DEFAULT_SINK@ toggle", "volume"), ("set-mute @DEFAULT_SOURCE@ toggle", "mic"),
                             ("brightnessctl s 5%+", "brightness"), ("brightnessctl s 5%-", "brightness")):
            pattern = re.escape(action) + r'[^\n]*halcyonOsd \.\. " ' + what + '"'
            self.assertRegex(keybinds, pattern, action)

    def test_login_loads_the_choices_and_the_file_that_acts_on_them(self):
        init = (HALCYON / "init.lua").read_text()
        self.assertIn('stateHome .. "/halcyon/overlays.lua"', init)
        self.assertIn('require("hyprland.halcyon.overlays")', init)
        overlays = (HALCYON / "overlays.lua").read_text()
        self.assertIn("avizo-service", overlays)
        self.assertIn("wayscriber --daemon", overlays)
        self.assertIn('"SUPER + SHIFT + D"', overlays)

    def test_the_shell_hides_its_own_popup_when_avizo_is_chosen(self):
        family = (ROOT / "dots/.config/quickshell/ii/panelFamilies/IllogicalImpulseFamily.qml").read_text()
        self.assertRegex(family, r'extraCondition: \(Config\.options\.osd\.provider \?\? "shell"\) === "shell"; component: OnScreenDisplay')
        config = (ROOT / "dots/.config/quickshell/ii/modules/common/Config.qml").read_text()
        self.assertIn('property string provider: "shell"', config)
        self.assertIn("property bool enable: true // Wayscriber", config)

    def test_themes_and_wallpapers_bring_both_tools_along(self):
        source = (HALCYON / "halcyon-theme").read_text()
        self.assertIn('"halcyon_overlays.py", ["overlays", "sync", "--quiet"]', source)

    def test_both_packages_are_installed_with_the_rest(self):
        pkgbuild = (ROOT / "sdata/dist-arch/illogical-impulse-widgets/PKGBUILD").read_text()
        self.assertIn("avizo", pkgbuild)
        self.assertIn("wayscriber-bin", pkgbuild)


if __name__ == "__main__":
    unittest.main()
