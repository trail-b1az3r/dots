"""The shell's network service and Wi-Fi menu use nmx (nmxcli) when it runs, NetworkManager (nmcli) otherwise, and
ask enterprise (802.1X) networks for a username as well as a password. Run: python3 -m unittest discover -s tests"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

II = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii"
NETWORK = (II / "services/Network.qml").read_text()
DIALOG = (II / "modules/ii/sidebarRight/wifiNetworks/WifiDialog.qml").read_text()
ITEM = (II / "modules/ii/sidebarRight/wifiNetworks/WifiNetworkItem.qml").read_text()
AP = (II / "services/network/WifiAccessPoint.qml").read_text()
TOOL = II / "scripts/network/network-tool.sh"
SETTINGS_USERS = [II / "modules/ii/sidebarRight/quickToggles/classicStyle/NetworkToggle.qml",
                  II / "modules/waffle/actionCenter/wifi/WifiControl.qml"]


class NetworkNmxTest(unittest.TestCase):
    def test_every_command_goes_through_the_chosen_tool(self):
        self.assertIn('property string cli: "nmcli"', NETWORK)
        self.assertIn('nmxcli -t -f RUNNING general', TOOL.read_text())
        self.assertIn('command: ["sh", root.toolScript]', NETWORK)
        # No hard-wired nmcli left in a command, except the NetworkManager-only fallbacks for enterprise profiles.
        commands = re.findall(r'command: \[[^\]]*\]', NETWORK) + re.findall(r'\.exec\(\[[^\]]*\]', NETWORK)
        self.assertTrue(commands)
        for command in commands:
            self.assertNotIn('"nmcli"', command, command)

    def test_the_details_menu_asks_the_same_tool(self):
        self.assertIn('"${tool:-nmcli}" -f GENERAL,IP4,IP6 device show', DIALOG)
        self.assertIn("Network.toolScript]", DIALOG)
        self.assertIn("Network.redetect();", DIALOG)

    def test_settings_open_nmxtui_with_nmx(self):
        self.assertIn("${Config.options.apps.terminal} -e nmxtui", NETWORK)
        for path in SETTINGS_USERS:
            text = path.read_text()
            self.assertIn("Network.openSettings(", text, path.name)
            self.assertNotIn("Config.options.apps.network", text, path.name)

    def test_captive_portal(self):
        self.assertIn('command: ["nmxcli", "-t", "portal"]', NETWORK)
        self.assertIn('"-A", "signin="', NETWORK)
        self.assertIn('root.portalUrl.length > 0 ? root.portalUrl : root.portalFallback', NETWORK)
        self.assertTrue(re.search(r'portalFallback: "http://', NETWORK), "plain HTTP, so the portal can redirect it")
        self.assertIn('Network.connectivity === "portal"', ITEM)
        self.assertIn('Network.openPublicWifiPortal()', DIALOG)

    def test_enterprise_networks_ask_for_a_username(self):
        self.assertIn('security.includes("802.1X")', AP)
        self.assertIn("id: usernameField", ITEM)
        self.assertIn("Network.changePassword(root.wifiNetwork, passwordField.text, usernameField.text)", ITEM)
        self.assertIn('command.push("username", "env:NMX_USERNAME")', NETWORK)

    def test_secrets_never_go_on_the_command_line(self):
        self.assertIn('"password", "env:NMX_PASSWORD"', NETWORK)
        self.assertNotRegex(NETWORK, r'"password", *password')



class NetworkToolTest(unittest.TestCase):
    """scripts/network/network-tool.sh against stand-in nmxcli and systemctl."""

    def pick(self, os_id, nmx_running=False, nmx_enabled=False, nm_active=True, has_nmx=True):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp, "bin")
            bin_dir.mkdir()
            if has_nmx:
                (bin_dir / "nmxcli").write_text(f"#!/bin/sh\n{'echo running' if nmx_running else 'exit 8'}\n")
            (bin_dir / "systemctl").write_text(
                "#!/bin/sh\n"
                f'case "$*" in *is-enabled*nmx*) exit {0 if nmx_enabled else 1};; '
                f'*is-active*NetworkManager*) exit {0 if nm_active else 3};; esac\nexit 1\n')
            for tool in bin_dir.iterdir():
                tool.chmod(0o755)
            Path(tmp, "os-release").write_text(f'NAME="X"\nID="{os_id}"\nID_LIKE="endeavouros arch"\n')
            env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "OS_RELEASE": str(Path(tmp, "os-release"))}
            out = subprocess.run(["sh", str(TOOL)], env=env, capture_output=True, text=True, check=True).stdout
            return out.split()

    def test_nexora(self):
        self.assertEqual(self.pick("nexora", nmx_running=True), ["nmxcli", "nexora"])
        self.assertEqual(self.pick("nexora", nmx_enabled=True), ["nmxcli", "nexora"], "nmx on its way back")
        self.assertEqual(self.pick("nexora", nm_active=False), ["nmxcli", "nexora"], "never NetworkManager by default")
        self.assertEqual(self.pick("nexora"), ["nmcli", "nexora"], "NetworkManager chosen in the installer")

    def test_elsewhere_only_while_nmx_runs(self):
        self.assertEqual(self.pick("arch", nmx_running=True), ["nmxcli"])
        self.assertEqual(self.pick("arch", nmx_enabled=True, nm_active=False), ["nmcli"])
        self.assertEqual(self.pick("arch", has_nmx=False), ["nmcli"])

    def test_executable(self):
        self.assertTrue(os.access(TOOL, os.X_OK))


if __name__ == "__main__":
    unittest.main()
