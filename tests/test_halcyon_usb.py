"""`halcyon usb`: reading devices from a fake sysfs, the advice it gives, and the udev rules it writes.
Run: python3 -m unittest discover -s tests"""

import importlib.util
import os
import stat
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
spec = importlib.util.spec_from_file_location("halcyon_usb", HALCYON / "halcyon_usb.py")
usb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usb)


def by_mode(path, _mode):
    """Access as an ordinary user would have it: the "other" read and write bits, whoever runs the tests."""
    try:
        return Path(path).stat().st_mode & 0o006 == 0o006
    except OSError:
        return False


class FakeSystem:
    def __init__(self, root):
        self.sys, self.dev = Path(root, "sys"), Path(root, "dev")
        (self.sys / "bus/usb/devices").mkdir(parents=True)
        (self.sys / "class/hidraw").mkdir(parents=True)
        self.dev.mkdir()
        self._devnum = 1

    def usb(self, name, vendor, product, label, interfaces, mode=0o664):
        entry = self.sys / "bus/usb/devices" / name
        entry.mkdir()
        self._devnum += 1
        for key, value in {"idVendor": vendor, "idProduct": product, "product": label, "manufacturer": "Acme",
                           "busnum": "1", "devnum": str(self._devnum)}.items():
            (entry / key).write_text(value + "\n")
        for i, (cls, sub, proto) in enumerate(interfaces):
            iface = entry / f"{name}:1.{i}"
            iface.mkdir()
            (iface / "bInterfaceClass").write_text(cls)
            (iface / "bInterfaceSubClass").write_text(sub)
            (iface / "bInterfaceProtocol").write_text(proto)
        node = self.dev / f"bus/usb/001/{self._devnum:03d}"
        node.parent.mkdir(parents=True, exist_ok=True)
        node.write_text("")
        node.chmod(mode)

    def hidraw(self, name, hid_id, label, mode=0o600):
        entry = self.sys / "class/hidraw" / name / "device"
        entry.mkdir(parents=True)
        (entry / "uevent").write_text(f"HID_ID={hid_id}\nHID_NAME={label}\n")
        node = self.dev / name
        node.write_text("")
        node.chmod(mode)


class DevicesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fake = FakeSystem(tmp.name)
        patcher = unittest.mock.patch.object(usb.os, "access", side_effect=by_mode)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.fake.usb("1-1", "2341", "0043", "Uno", [("02", "02", "01"), ("0a", "00", "00")])
        self.fake.usb("1-2", "046d", "c31c", "Keyboard", [("03", "01", "01"), ("03", "00", "00")])
        self.fake.usb("1-3", "1050", "0407", "YubiKey", [("03", "00", "00"), ("0b", "00", "00")], mode=0o666)
        (self.fake.sys / "bus/usb/devices/usb1").mkdir()  # a root hub: skipped
        self.fake.hidraw("hidraw0", "0003:00001050:00000407", "Yubico YubiKey")
        self.fake.hidraw("hidraw1", "0003:0000046D:0000C31C", "Logitech Keyboard")

    def devices(self):
        return {d["id"]: d for d in usb.usb_devices(self.fake.sys, self.fake.dev)}

    def test_reads_devices_and_their_interfaces(self):
        devices = self.devices()
        self.assertEqual(sorted(devices), ["046d:c31c", "1050:0407", "2341:0043"])
        uno = devices["2341:0043"]
        self.assertEqual((uno["name"], uno["access"], uno["classes"]), ("Acme Uno", False, [0x02, 0x0A]))
        self.assertTrue(uno["node"].endswith("bus/usb/001/002"))
        self.assertEqual(uno["webusb_blocked"], [])
        self.assertTrue(devices["046d:c31c"]["keyboard_or_mouse"])
        key = devices["1050:0407"]
        self.assertTrue(key["access"] and key["only_protected"])
        self.assertEqual(key["webusb_blocked"], ["HID", "smart card"])

    def test_hidraw_ids_match_usb_ids(self):
        hid = usb.hidraw_devices(self.fake.sys, self.fake.dev)
        self.assertEqual([(h["id"], h["access"]) for h in hid], [("1050:0407", False), ("046d:c31c", False)])

    def test_advice_names_the_fix(self):
        info = {"session": {"id": "2", "known": True, "active": True, "seat": "seat0"},
                "usb": list(self.devices().values()),
                "hidraw": usb.hidraw_devices(self.fake.sys, self.fake.dev), "serial": [], "groups": [],
                "serial_group": "uucp", "flatpak": [{"app": "org.chromium.Chromium", "all_devices": False}],
                "rule": ""}
        text = "\n".join(usb.advice(info))
        self.assertIn("flatpak override --user --device=all org.chromium.Chromium", text)
        self.assertIn("halcyon usb allow 2341:0043", text)
        self.assertNotIn("allow 046d:c31c", text)  # the keyboard is never offered
        self.assertIn("YubiKey only has HID, smart card interfaces", text)
        self.assertIn("WebHID cannot open: Yubico YubiKey", text)
        rendered = usb.render(info)
        self.assertIn("keyboard/mouse: left alone", rendered)

    def test_an_inactive_session_comes_first(self):
        info = {"session": {"id": "4", "known": True, "active": False, "seat": ""}, "usb": [], "hidraw": [],
                "serial": [], "groups": [], "serial_group": "uucp", "flatpak": [], "rule": ""}
        self.assertIn("not the active one", usb.advice(info)[0])

    def test_serial_group_advice(self):
        node = self.fake.dev / "ttyACM0"
        node.write_text("")
        node.chmod(0o660)
        serial = usb.serial_devices(self.fake.dev)
        info = {"session": {"known": False}, "usb": [], "hidraw": [], "serial": serial, "groups": ["wheel"],
                "serial_group": "uucp", "flatpak": [], "rule": ""}
        self.assertIn("join the uucp group", "\n".join(usb.advice(info)))


class RulesTest(unittest.TestCase):
    def test_per_device_rules_cover_usb_hidraw_and_serial(self):
        text = usb.rules_for(["2341:0043"])
        self.assertIn('SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="2341", ATTR{idProduct}=="0043", '
                      'TAG+="uaccess"', text)
        self.assertIn('SUBSYSTEM=="hidraw", ATTRS{idVendor}=="2341"', text)
        self.assertIn('SUBSYSTEM=="tty", KERNEL=="ttyUSB[0-9]*|ttyACM[0-9]*"', text)

    def test_allowing_more_keeps_what_was_allowed(self):
        first = usb.merged_rules("", ["2341:0043"], False)
        second = usb.merged_rules(first, ["1050:0407", "2341:0043"], False)
        self.assertEqual(second.count("# 2341:0043"), 1)
        self.assertIn("# 1050:0407", second)
        self.assertTrue(second.startswith(usb.HEADER))

    def test_all_leaves_keyboards_mice_and_hubs_out(self):
        text = usb.merged_rules("", [], True)
        self.assertIn('ENV{ID_USB_INTERFACES}=="*:030101:*|*:030102:*", GOTO="halcyon_usb_end"', text)
        self.assertIn('ATTR{bDeviceClass}=="09", GOTO="halcyon_usb_end"', text)
        self.assertLess(text.index("GOTO"), text.index('TAG+="uaccess"'))
        self.assertTrue(text.rstrip().endswith('LABEL="halcyon_usb_end"'))
        # Going back to a list drops the blanket rule.
        self.assertNotIn("halcyon_usb_end", usb.merged_rules(text, ["2341:0043"], False))

    def test_rule_runs_before_seat_late(self):
        # 73-seat-late.rules turns the uaccess tag into the ACL, so the tag has to be added first.
        self.assertLess(usb.RULE_PATH.name, "73-seat-late.rules")

    def test_ids_are_checked_before_anything_runs(self):
        with unittest.mock.patch.object(usb, "install_rules") as install:
            self.assertEqual(usb.main(["allow", "2341:00zz"]), 2)
            self.assertEqual(usb.main(["allow"]), 2)
            install.assert_not_called()

    def test_install_writes_the_rule_and_reloads_udev(self):
        calls = []
        with unittest.mock.patch.object(usb.subprocess, "run",
                                        side_effect=lambda argv, check=False: calls.append(argv) or
                                        unittest.mock.Mock(returncode=0)), \
                unittest.mock.patch.object(usb.os, "geteuid", return_value=1000):
            self.assertEqual(usb.install_rules("x"), 0)
        self.assertEqual(calls[0][:4], ["sudo", "install", "-m", "644"])
        self.assertEqual(calls[0][-1], str(usb.RULE_PATH))
        self.assertEqual(calls[1], ["sudo", "udevadm", "control", "--reload-rules"])
        self.assertEqual(calls[2][:3], ["sudo", "udevadm", "trigger"])


if __name__ == "__main__":
    unittest.main()
