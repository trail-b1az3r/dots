"""The shell's network service and Wi-Fi menu use nmx (nmxcli) when it runs, NetworkManager (nmcli) otherwise, and
ask enterprise (802.1X) networks for a username as well as a password. Run: python3 -m unittest discover -s tests"""

import re
import unittest
from pathlib import Path

II = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii"
NETWORK = (II / "services/Network.qml").read_text()
DIALOG = (II / "modules/ii/sidebarRight/wifiNetworks/WifiDialog.qml").read_text()
ITEM = (II / "modules/ii/sidebarRight/wifiNetworks/WifiNetworkItem.qml").read_text()
AP = (II / "services/network/WifiAccessPoint.qml").read_text()


class NetworkNmxTest(unittest.TestCase):
    def test_every_command_goes_through_the_chosen_tool(self):
        self.assertIn('property string cli: "nmcli"', NETWORK)
        self.assertIn('nmxcli -t -f RUNNING general', NETWORK)
        # No hard-wired nmcli left in a command, except the NetworkManager-only fallbacks for enterprise profiles.
        commands = re.findall(r'command: \[[^\]]*\]', NETWORK) + re.findall(r'\.exec\(\[[^\]]*\]', NETWORK)
        self.assertTrue(commands)
        for command in commands:
            self.assertNotIn('"nmcli"', command, command)

    def test_the_details_menu_asks_the_same_tool(self):
        self.assertIn('command: [Network.cli, "-f", "GENERAL,IP4,IP6", "device", "show"]', DIALOG)

    def test_enterprise_networks_ask_for_a_username(self):
        self.assertIn('security.includes("802.1X")', AP)
        self.assertIn("id: usernameField", ITEM)
        self.assertIn("Network.changePassword(root.wifiNetwork, passwordField.text, usernameField.text)", ITEM)
        self.assertIn('command.push("username", "env:NMX_USERNAME")', NETWORK)

    def test_secrets_never_go_on_the_command_line(self):
        self.assertIn('"password", "env:NMX_PASSWORD"', NETWORK)
        self.assertNotRegex(NETWORK, r'"password", *password')


if __name__ == "__main__":
    unittest.main()
