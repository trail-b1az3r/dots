"""Server mode (`halcyon server`), and the user units only ever running inside Hyprland (the shell used to start in
KDE). Run: python3 -m unittest discover -s tests"""

import importlib.util
import json
import os
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
UNITS = ROOT / "dots/.config/systemd/user"
spec = importlib.util.spec_from_file_location("halcyon_server", HALCYON / "halcyon_server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ServerModeTest(unittest.TestCase):
    """Against a fake systemctl that keeps the unit's state in a file, and a fake systemd-inhibit."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        self.state = self.root / "active"
        self.log = self.root / "calls"
        (bin_dir / "systemctl").write_text(f"""#!/bin/sh
echo "systemctl $*" >> {self.log}
case "$*" in
  *is-active*) [ -f {self.state} ] ;;
  *" start "*) touch {self.state} ;;
  *" stop "*) rm -f {self.state} ;;
esac
""")
        (bin_dir / "systemd-inhibit").write_text(f"""#!/bin/sh
[ -f {self.state} ] && echo "Halcyon 1000 user 4242 systemd-inhibit sleep:idle:handle-lid-switch Server mode block"
echo "NetworkManager 0 root 800 NetworkManager sleep NetworkManager needs to turn off networks delay"
""")
        for tool in bin_dir.iterdir():
            tool.chmod(0o755)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"bar": {"x": 1}}))
        for patcher in (unittest.mock.patch.dict(os.environ, {"PATH": f"{bin_dir}:/usr/bin:/bin"}),
                        unittest.mock.patch.object(server, "SHELL_CONFIG", self.config)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def saved(self):
        return json.loads(self.config.read_text())

    def test_on_starts_the_lock_and_saves_the_choice(self):
        self.assertEqual(server.main(["on", "--quiet"]), 0)
        self.assertTrue(server.active())
        self.assertEqual(self.saved(), {"bar": {"x": 1}, "halcyon": {"serverMode": True}})
        status = server.status()
        self.assertTrue(status["wanted"] and status["active"])
        self.assertEqual(len(status["inhibitors"]), 1)  # only Halcyon's own lock
        self.assertIn("systemctl --user start halcyon-server-mode.service", self.log.read_text())

    def test_off_stops_it(self):
        server.main(["on", "--quiet"])
        self.assertEqual(server.main(["off", "--quiet"]), 0)
        self.assertFalse(server.active())
        self.assertIs(self.saved()["halcyon"]["serverMode"], False)
        self.assertEqual(server.status()["inhibitors"], [])

    def test_apply_matches_the_saved_choice(self):
        self.config.write_text(json.dumps({"halcyon": {"serverMode": True}}))
        server.main(["apply"])
        self.assertTrue(server.active())
        self.config.write_text(json.dumps({"halcyon": {"serverMode": False}}))
        server.main(["apply"])
        self.assertFalse(server.active())

    def test_toggle(self):
        server.main(["toggle", "--quiet"])
        self.assertTrue(server.active())
        server.main(["toggle", "--quiet"])
        self.assertFalse(server.active())


class UnitFilesTest(unittest.TestCase):
    def test_server_mode_blocks_sleep_idle_and_the_lid(self):
        unit = (UNITS / "halcyon-server-mode.service").read_text()
        exec_start = re.search(r"^ExecStart=(.*)$", unit, re.M).group(1)
        self.assertIn("systemd-inhibit", exec_start)
        self.assertIn("--mode=block", exec_start)
        for what in ("sleep", "idle", "handle-lid-switch", "handle-suspend-key"):
            self.assertIn(what, exec_start)
        self.assertNotIn("[Install]", unit)
        # hypridle pauses its lock, blanking and suspend timers only if it honours systemd idle locks.
        self.assertIn("ignore_systemd_inhibit = false", (ROOT / "dots/.config/hypr/hypridle.conf").read_text())

    def test_shell_units_run_only_inside_hyprland(self):
        for name in ("halcyon-quickshell", "halcyon-gpu-guard", "halcyon-resume", "halcyon-auto-theme"):
            unit = (UNITS / f"{name}.service").read_text()
            self.assertIn("ExecCondition=/bin/sh -c 'hyprctl version", unit, name)
            self.assertNotIn("WantedBy=default.target", unit, name)

    def test_login_drops_old_enable_links_and_restores_server_mode(self):
        init = (HALCYON / "init.lua").read_text()
        self.assertIn("default.target.wants", init)
        self.assertIn("halcyon-quickshell.service", init)
        self.assertIn("halcyon_server.py apply", init)


class SettingsTest(unittest.TestCase):
    def test_the_button_is_in_settings(self):
        qml = (ROOT / "dots/.config/quickshell/ii/modules/settings/HalcyonConfig.qml").read_text()
        self.assertIn("Start server mode", qml)
        self.assertIn('[page.serverTool, turnOn ? "on" : "off"]', qml)
        self.assertIn("property bool serverMode: false",
                      (ROOT / "dots/.config/quickshell/ii/modules/common/Config.qml").read_text())


if __name__ == "__main__":
    unittest.main()
