"""halcyon.UwU-agent (halcyon_uwu.py): what it tells NetworkManager, and the vault behind the CLI (with openssl, and a
keyring that is not there, so the key goes in a file). The D-Bus side is exercised against a stand-in
NetworkManager by hand; see the module docstring. Run: python3 -m unittest discover -s tests"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
UWU = HALCYON / "halcyon_uwu.py"
sys.path.insert(0, str(HALCYON))

import halcyon_uwu as uwu  # noqa: E402

PSK = {"connection": {"id": "Home"}, "802-11-wireless": {"ssid": b"Home"},
       "802-11-wireless-security": {"key-mgmt": "wpa-psk"}}
SETTING = "802-11-wireless-security"


class AnswerTest(unittest.TestCase):
    def test_kept_password_is_given(self):
        vault = {"wifi": {"Home": "kept-pw"}, "web": {}}
        self.assertEqual(uwu.answer(PSK, SETTING, 0, vault, prompt=lambda p: self.fail("asked")), ("psk", "kept-pw"))

    def test_wrong_password_is_asked_again_and_kept(self):
        vault = {"wifi": {"Home": "old"}, "web": {}}
        got = uwu.answer(PSK, SETTING, uwu.ALLOW_INTERACTION | uwu.REQUEST_NEW, vault, prompt=lambda p: "new")
        self.assertEqual(got, ("psk", "new"))
        self.assertEqual(vault["wifi"]["Home"], "new")

    def test_never_asks_when_not_allowed(self):
        self.assertIsNone(uwu.answer(PSK, SETTING, 0, {"wifi": {}, "web": {}}, prompt=lambda p: self.fail("asked")))

    def test_cancelled_prompt_and_other_settings(self):
        self.assertIsNone(uwu.answer(PSK, SETTING, uwu.ALLOW_INTERACTION, {"wifi": {}}, prompt=lambda p: None))
        self.assertIsNone(uwu.answer(PSK, "vpn", uwu.ALLOW_INTERACTION, {"wifi": {}}, prompt=lambda p: "x"))

    def test_wep_and_enterprise(self):
        wep = {**PSK, SETTING: {"key-mgmt": "none"}}
        self.assertEqual(uwu.secret_field(wep, SETTING), "wep-key0")
        self.assertEqual(uwu.secret_field(PSK, "802-1x"), "password")
        self.assertEqual(uwu.ssid_of({"802-11-wireless": {"ssid": [72, 105]}}), "Hi")


@unittest.skipUnless(shutil.which("openssl"), "openssl is not installed")
class VaultCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin/secret-tool").write_text("#!/bin/sh\nexit 1\n")
        (self.tmp / "bin/secret-tool").chmod(0o755)
        self.env = {**os.environ, "XDG_STATE_HOME": str(self.tmp / "state"),
                    "PATH": f"{self.tmp / 'bin'}:{os.environ.get('PATH', '/usr/bin:/bin')}"}

    def cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(UWU), *args], input=stdin, env=self.env, capture_output=True,
                              text=True, check=False)

    def test_round_trip_never_in_plain_text(self):
        self.assertEqual(self.cli("wifi", "add", "Cafe", stdin="latte123\n").returncode, 0)
        self.assertEqual(self.cli("web", "add", "example.com", "me", stdin="s3cret!\n").returncode, 0)
        self.assertEqual(self.cli("wifi").stdout.split(), ["Cafe"])
        self.assertEqual(self.cli("web", "list").stdout.strip(), "example.com  me")
        vault = self.tmp / "state/halcyon/uwu/vault.enc"
        raw = vault.read_bytes()
        self.assertNotIn(b"latte123", raw)
        self.assertNotIn(b"s3cret", raw)
        self.assertEqual(oct(vault.stat().st_mode & 0o777), "0o600")
        self.assertEqual(oct((vault.parent / "vault.key").stat().st_mode & 0o777), "0o600")
        self.assertEqual(self.cli("web", "remove", "example.com", "me").returncode, 0)
        self.assertEqual(self.cli("web", "list").stdout.strip(), "")

    def test_wired_up(self):
        service = (ROOT / "dots/.config/systemd/user/halcyon-uwu-agent.service").read_text()
        self.assertIn("halcyon_uwu.py\" agent", service)
        self.assertIn("halcyon-uwu-agent.service", (HALCYON / "init.lua").read_text())
        pkg = (ROOT / "sdata/dist-arch/illogical-impulse-kde/PKGBUILD").read_text()
        self.assertIn("python-dbus-next", pkg)
        self.assertNotIn("\n  plasma-nm\n", pkg)


if __name__ == "__main__":
    unittest.main()
