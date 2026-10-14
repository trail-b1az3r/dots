"""The Red Sun collapse: a triggered screen shader that `collapse arm` switches in and `collapse disarm` takes out."""

from __future__ import annotations

import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
TOOL = HALCYON / "halcyon-theme"
SHADER = HALCYON / "themes/shaders/red-sun.frag"

FAKE_HYPRCTL = """#!/bin/sh
echo "$@" >> "$HOME/hyprctl.log"
case "$1" in getoption) echo '{"int": 1}';; esac
"""


class CollapseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = root / "home"
        self.state = self.home / ".local/state/halcyon"
        self.state.mkdir(parents=True)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        (bin_dir / "hyprctl").write_text(FAKE_HYPRCTL)
        (bin_dir / "hyprctl").chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_STATE_HOME=str(self.home / ".local/state"), HYPRLAND_INSTANCE_SIGNATURE="test",
                        PATH=f"{bin_dir}:{os.environ['PATH']}")
        (self.state / "active").write_text("red-sun\n")

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=self.env, check=False)

    def log(self):
        path = self.home / "hyprctl.log"
        return path.read_text() if path.exists() else ""

    def test_theme_lua_has_no_shader_and_keeps_damage_tracking(self):
        out = Path(self.tmp.name) / "out"
        self.assertEqual(self.tool("render", "red-sun", str(out)).returncode, 0)
        text = (out / "theme.lua").read_text()
        self.assertNotIn("screen_shader", text)
        self.assertNotIn("damage_tracking", text)

    def test_arm_then_disarm(self):
        result = self.tool("collapse", "arm", "0.6", "0.49", "0.43", "0.073")
        self.assertEqual(result.stdout, "")
        armed = list(self.state.glob("screen-shader-armed-*.frag"))
        self.assertEqual(len(armed), 1)
        text = armed[0].read_text()
        for line in ("#define COLLAPSE_ARMED 1", "#define ARM_AGE 0.600", "#define RING_X 0.4900", "#define RING_R 0.0730"):
            self.assertIn(line, text)
        self.assertIn(f'screen_shader = "{armed[0]}"', self.log())
        self.assertIn("damage_tracking = 0", self.log())
        token = json.loads((self.state / "collapse.json").read_text())["token"]

        self.assertIn("newer spin", self.tool("collapse", "disarm", "--token", str(token + 5)).stdout)
        self.assertTrue(armed[0].exists())
        self.assertEqual(self.tool("collapse", "disarm", "--token", str(token)).stdout, "")
        self.assertFalse(armed[0].exists())
        self.assertIn('screen_shader = ""', self.log())
        self.assertIn("damage_tracking = 2", self.log())

    def test_the_car_the_eye_looks_at(self):
        self.tool("collapse", "arm", "0.2", "0.49", "0.43", "0.073", "0.71", "0.88")
        text = next(self.state.glob("screen-shader-armed-*.frag")).read_text()
        self.assertIn("#define CAR_X 0.7100", text)
        self.assertIn("#define CAR_Y 0.8800", text)

    def test_without_a_car_it_is_where_the_wallpaper_has_it(self):
        self.tool("collapse", "arm", "0.2", "0.4907", "0.4312", "0.0656")
        text = next(self.state.glob("screen-shader-armed-*.frag")).read_text()
        self.assertIn("#define CAR_X 0.6485", text)
        self.assertIn("#define CAR_Y 0.7084", text)

    def test_disarm_waits_for_the_whole_sequence(self):
        duration = float(re.search(r"const float DURATION = ([0-9.]+);", SHADER.read_text()).group(1))
        theme = (HALCYON / "halcyon-theme").read_text()
        seconds = float(re.search(r"^COLLAPSE_SECONDS = ([0-9.]+)", theme, re.M).group(1))
        self.assertGreater(seconds, duration, "the shader is taken out only after the rewind has finished")
        self.assertLess(seconds, duration + 2.0)

    def test_the_sequence_is_all_there(self):
        text = SHADER.read_text()
        for part in ("float sceneTime(", "vec3 drawEye(", "vec3 embers(", "float glyphPixel(", "REW_SPEED", "T_LOCK"):
            self.assertIn(part, text)

    def test_each_arm_uses_a_new_path(self):
        self.tool("collapse", "arm", "0.1", "0.5", "0.5", "0.07")
        self.tool("collapse", "arm", "0.1", "0.5", "0.5", "0.07")
        paths = [line.split('"')[1] for line in self.log().splitlines() if "screen_shader" in line]
        self.assertEqual(len(set(paths)), 2)

    def test_not_armed_below_full_or_on_other_themes(self):
        config = self.home / ".config/illogical-impulse/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"halcyon": {"effects": "light"}}))
        self.assertIn("not full", self.tool("collapse", "arm", "0", "0.5", "0.5", "0.07").stdout)
        config.write_text("{}")
        (self.state / "active").write_text("hyperneo\n")
        self.assertIn("no revolver effect", self.tool("collapse", "arm", "0", "0.5", "0.5", "0.07").stdout)
        self.assertEqual(self.log(), "")

    @unittest.skipUnless(shutil.which("glslangValidator"), "glslangValidator is not installed")
    def test_armed_shader_compiles(self):
        self.tool("collapse", "arm", "0.2", "0.3", "0.6", "0.1")
        armed = next(self.state.glob("screen-shader-armed-*.frag"))
        result = subprocess.run(["glslangValidator", "-S", "frag", str(armed)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_shader_is_a_pass_through_until_armed(self):
        text = SHADER.read_text()
        self.assertIn("#define COLLAPSE_ARMED 0", text)
        self.assertIn("if (age < 0.0 || age > DURATION)", text)


if __name__ == "__main__":
    unittest.main()
