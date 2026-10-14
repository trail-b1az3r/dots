"""`halcyon wifi` against a stand-in NetworkManager (nmcli, systemctl, udevadm, NetworkManager --print-config) and a
stand-in /sys, set up as a Surface with a Marvell card. The fakes keep their state in a JSON file, so `nmcli device
set ... managed yes` really does change what the next `nmcli device` lists.
Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon_wifi.py"

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
path = os.environ["FAKE_STATE"]
state = json.load(open(path))
name = os.path.basename(sys.argv[0])
args = [a for a in sys.argv[1:]]
state.setdefault("calls", []).append([name] + args)
out, code = "", 0
def save():
    json.dump(state, open(path, "w"))
if name == "nmcli":
    a = [x for x in args if x not in ("-t",)]
    if a[:2] == ["-w", "25"]:
        a = a[2:]
    if not state["running"]:
        out, code = "", 8
    elif a[:3] == ["-f", "RUNNING", "general"]:
        out = "running"
    elif a[:2] == ["radio", "wifi"] and len(a) == 2:
        out = "enabled" if state["radio"] else "disabled"
    elif a[:3] == ["radio", "wifi", "on"]:
        state["radio"] = True
    elif a[:1] == ["-f"] and "device" in a:
        lines = []
        for d in state["devices"]:
            st = d["state"] if state["radio"] or d["state"] == "unmanaged" else "unavailable"
            lines.append(f"{d['device']}:wifi:{st}:{d.get('connection') or '--'}")
        lines.append("p2p-dev-wlp1s0:wifi-p2p:disconnected:--")
        out = "\n".join(lines)
    elif a[:2] == ["device", "set"]:
        for d in state["devices"]:
            if d["device"] == a[2] and a[4] == "yes" and not state.get("refuse_managed"):
                d["state"] = "connected" if state.get("autoconnect") else "disconnected"
                if state.get("autoconnect"):
                    d["connection"] = "Home"
    elif a[:2] == ["device", "connect"]:
        code = 1
        for d in state["devices"]:
            if d["device"] == a[2] and d["state"] == "disconnected" and state.get("known_network"):
                d["state"], d["connection"], code = "connected", "Home", 0
elif name == "systemctl":
    unit = args[-1]
    if args[0] == "is-active":
        code = 0 if unit in state.get("active", []) else 3
    elif args[0] == "is-enabled":
        code = 0 if unit in state.get("enabled", []) else 1
elif name == "udevadm":
    out = "NM_UNMANAGED=1" if state.get("udev_unmanaged") else "ID_NET_NAME=wlp1s0"
elif name == "NetworkManager":
    out = state.get("nm_config", "[main]\nplugins=keyfile\n")
elif name == "rfkill":
    open(os.path.join(os.environ["HALCYON_SYSFS"], "class/rfkill/rfkill0/soft"), "w").write("0\n")
save()
print(out)
sys.exit(code)
'''


class WifiTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name in ("nmcli", "systemctl", "udevadm", "NetworkManager", "rfkill"):
            (self.bin / name).write_text(FAKE)
            (self.bin / name).chmod(0o755)
        (self.bin / "notify-send").write_text("#!/bin/sh\necho \"$@\" >> \"$NOTIFY_LOG\"\n")
        (self.bin / "notify-send").chmod(0o755)
        # A Surface with a Marvell card, and its radio switch.
        self.sys = self.tmp / "sys"
        driver = self.sys / "bus/pci/drivers/mwifiex_pcie"
        driver.mkdir(parents=True)
        card = self.sys / "devices/pci0000:00/0000:01:00.0"
        card.mkdir(parents=True)
        (card / "driver").symlink_to(driver)
        net = self.sys / "class/net/wlp1s0"
        (net / "wireless").mkdir(parents=True)
        (net / "device").symlink_to(card)
        (self.sys / "class/net/lo").mkdir(parents=True)
        dmi = self.sys / "class/dmi/id"
        dmi.mkdir(parents=True)
        (dmi / "sys_vendor").write_text("Microsoft Corporation\n")
        (dmi / "product_name").write_text("Surface Pro 7\n")
        rf = self.sys / "class/rfkill/rfkill0"
        rf.mkdir(parents=True)
        (rf / "type").write_text("wlan\n")
        (rf / "soft").write_text("0\n")
        (rf / "hard").write_text("0\n")
        self.state_file = self.tmp / "state.json"
        self.conf = self.tmp / "etc/90-halcyon-wifi.conf"
        self.notify_log = self.tmp / "notify.log"
        self.set_state(running=True, radio=True, devices=[{"device": "wlp1s0", "state": "unmanaged"}],
                       active=["NetworkManager.service"], enabled=["NetworkManager.service"])

    def set_state(self, **state):
        self.state_file.write_text(json.dumps(state))

    def state(self):
        return json.loads(self.state_file.read_text())

    def run_tool(self, *args):
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "FAKE_STATE": str(self.state_file),
               "HALCYON_SYSFS": str(self.sys), "HALCYON_NM_CONF": str(self.conf), "NOTIFY_LOG": str(self.notify_log),
               "XDG_STATE_HOME": str(self.tmp / "state"), "HALCYON_WIFI_WAIT_NM": "0.3",
               "HALCYON_WIFI_WAIT_DEVICE": "0.3", "HALCYON_WIFI_WAIT_CONNECT": "0.3", "HALCYON_WIFI_POLL": "0.05"}
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env, timeout=60)

    def test_status_names_the_surface_card_and_why_it_is_off(self):
        report = json.loads(self.run_tool("--json").stdout)
        self.assertTrue(report["surface"])
        self.assertEqual(report["interfaces"][0]["driver"], "mwifiex_pcie")
        self.assertEqual(report["devices"], [{"device": "wlp1s0", "state": "unmanaged", "connection": ""}],
                         "the p2p device is left out")
        text = " ".join(report["problems"])
        self.assertIn("lists wlp1s0 as unmanaged", text)
        self.assertIn("halcyon wifi fix", text)

    def test_boot_takes_back_an_unmanaged_card_and_connects(self):
        self.set_state(running=True, radio=True, devices=[{"device": "wlp1s0", "state": "unmanaged"}],
                       known_network=True)
        done = self.run_tool("boot")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        calls = self.state()["calls"]
        self.assertIn(["nmcli", "device", "set", "wlp1s0", "managed", "yes"], calls)
        self.assertEqual(self.state()["devices"][0]["state"], "connected")
        self.assertIn("unmanaged; handing it back", (self.tmp / "state/halcyon/wifi.log").read_text())

    def test_boot_turns_the_radio_on_and_unblocks_it(self):
        (self.sys / "class/rfkill/rfkill0/soft").write_text("1\n")
        self.set_state(running=True, radio=False, devices=[{"device": "wlp1s0", "state": "disconnected"}],
                       known_network=True)
        done = self.run_tool("boot")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        calls = self.state()["calls"]
        self.assertIn(["rfkill", "unblock", "wifi"], calls)
        self.assertIn(["nmcli", "radio", "wifi", "on"], calls)

    def test_boot_says_so_when_networkmanager_is_not_running(self):
        self.set_state(running=False, radio=True, devices=[])
        done = self.run_tool("boot")
        self.assertEqual(done.returncode, 1)
        self.assertIn("NetworkManager isn't running", self.notify_log.read_text())
        self.assertIn("halcyon wifi fix", self.notify_log.read_text())

    def test_already_connected_is_left_alone(self):
        self.set_state(running=True, radio=True, devices=[{"device": "wlp1s0", "state": "connected", "connection": "Home"}])
        self.assertEqual(self.run_tool("boot").returncode, 0)
        self.assertFalse(any(c[1:3] == ["device", "set"] for c in self.state()["calls"]))

    def test_fix_keeps_wifi_managed_and_sets_the_surface_card_up(self):
        self.set_state(running=True, radio=True, devices=[{"device": "wlp1s0", "state": "unmanaged"}],
                       active=["NetworkManager.service", "iwd.service"], enabled=["iwd.service"])
        done = self.run_tool("fix", "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout
        self.assertIn("match-device=type:wifi\nmanaged=1", out)
        self.assertIn("match-device=driver:mwifiex_pcie", out)
        self.assertIn("wifi.scan-rand-mac-address=no", out)
        self.assertIn("wifi.powersave=2", out)
        self.assertIn("systemctl disable --now iwd.service", out, "iwd beside NetworkManager is turned off")
        self.assertIn("systemctl enable NetworkManager.service", out)

    def test_fix_leaves_iwd_when_networkmanager_uses_it(self):
        self.set_state(running=True, radio=True, devices=[{"device": "wlp1s0", "state": "disconnected"}],
                       active=["NetworkManager.service", "iwd.service"],
                       nm_config="[device]\nwifi.backend=iwd\n")
        out = self.run_tool("fix", "--dry-run").stdout
        self.assertNotIn("iwd.service", out)

    def test_an_unmanaged_devices_line_is_named(self):
        self.set_state(running=True, radio=True, devices=[{"device": "wlp1s0", "state": "unmanaged"}],
                       nm_config="[keyfile]\nunmanaged-devices=interface-name:wlp*\n")
        report = json.loads(self.run_tool("--json").stdout)
        self.assertIn("unmanaged-devices=interface-name:wlp*", " ".join(report["problems"]))

    def test_login_runs_it(self):
        init = (ROOT / "dots/.config/hypr/hyprland/halcyon/init.lua").read_text()
        self.assertIn("halcyon_wifi.py boot", init)


if __name__ == "__main__":
    unittest.main()
