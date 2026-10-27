"""Halcyon on NixOS: ./setup's NixOS step (sdata/dist-nixos/install-deps.sh) against a scratch /etc/nixos with
stand-ins for sudo and nixos-rebuild, the configuration.nix editor on the layouts NixOS writes, and (with Nix
here) that every edited file still parses. Run: python3 -m unittest discover -s tests"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NIXOS = ROOT / "sdata/dist-nixos"
EDIT = NIXOS / "edit-configuration.sh"
NIX_INSTANTIATE = shutil.which("nix-instantiate")

DEFAULT_CONF = """{ config, pkgs, ... }:

{
  imports =
    [ # Include the results of the hardware scan.
      ./hardware-configuration.nix
    ];

  boot.loader.systemd-boot.enable = true;
  users.users.alice = { isNormalUser = true; };
  system.stateVersion = "25.11";
}
"""
NO_IMPORTS = """{ pkgs, ... }: {
  networking.hostName = "box";
}
"""
ONE_LINE = """{ config, pkgs, ... }:
{
  imports = [ ./hardware-configuration.nix ./other.nix ];
  system.stateVersion = "25.11";
}
"""


def edit(text, user="alice"):
    with tempfile.NamedTemporaryFile("w", suffix=".nix", delete=False) as handle:
        handle.write(text)
    try:
        done = subprocess.run(["bash", str(EDIT), handle.name, user], capture_output=True, text=True, check=True)
        return done.stdout
    finally:
        os.unlink(handle.name)


class EditConfigurationTest(unittest.TestCase):
    def test_the_default_layout(self):
        out = edit(DEFAULT_CONF)
        self.assertIn("[ ./halcyon/halcyon.nix # Include the results", out)
        self.assertEqual(out.count("imports"), 1, "into the list that is there, not a second imports")
        self.assertIn('halcyon = { enable = true; user = "alice"; };\n}', out)

    def test_no_imports_yet(self):
        out = edit(NO_IMPORTS)
        self.assertIn("  imports = [ ./halcyon/halcyon.nix ];", out)

    def test_a_one_line_list(self):
        self.assertIn("imports = [ ./halcyon/halcyon.nix ./hardware-configuration.nix ./other.nix ];", edit(ONE_LINE))

    def test_twice_is_once(self):
        once = edit(DEFAULT_CONF)
        self.assertEqual(edit(once), once)

    @unittest.skipUnless(NIX_INSTANTIATE, "no Nix")
    def test_the_results_are_nix(self):
        for text in (DEFAULT_CONF, NO_IMPORTS, ONE_LINE):
            with tempfile.NamedTemporaryFile("w", suffix=".nix", delete=False) as handle:
                handle.write(edit(text))
            try:
                subprocess.run([NIX_INSTANTIATE, "--parse", handle.name], capture_output=True, check=True)
            finally:
                os.unlink(handle.name)

    @unittest.skipUnless(NIX_INSTANTIATE, "no Nix")
    def test_the_module_files_are_nix(self):
        for name in ("halcyon.nix", "packages.nix", "flake.nix"):
            subprocess.run([NIX_INSTANTIATE, "--parse", str(NIXOS / name)], capture_output=True, check=True)


class InstallStepTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.etc = base / "etc/nixos"
        self.etc.mkdir(parents=True)
        self.bin = base / "bin"
        self.bin.mkdir()
        self.log = base / "rebuild.log"
        for name, body in (("sudo", 'exec "$@"'), ("nixos-rebuild", f'echo "$@" >> "{self.log}"'),
                           ("hostname", "echo box")):
            (self.bin / name).write_text(f"#!/bin/sh\n{body}\n")
            (self.bin / name).chmod(0o755)

    def run_step(self, **env):
        script = (f'ask=false; REPO_ROOT="{ROOT}"; source "{ROOT}/sdata/lib/functions.sh"; '
                  f'cd "{ROOT}"; source "{NIXOS}/install-deps.sh"')
        environ = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "HALCYON_NIXOS_DIR": str(self.etc), **env}
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=environ, input="e\n",
                              timeout=120)

    def test_classic_configuration(self):
        (self.etc / "configuration.nix").write_text(DEFAULT_CONF)
        done = self.run_step()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for name in ("halcyon.nix", "packages.nix", "sleep-hook"):
            self.assertTrue((self.etc / "halcyon" / name).is_file(), name)
        self.assertNotIn("__USER__", (self.etc / "halcyon/sleep-hook").read_text())
        conf = (self.etc / "configuration.nix").read_text()
        self.assertIn("./halcyon/halcyon.nix", conf)
        self.assertEqual(len(list(self.etc.glob("configuration.nix.halcyon-backup-*"))), 1)
        self.assertEqual(self.log.read_text().split("\n")[:2], ["dry-build", "switch"], "built before switching")

    def test_a_flake_system_is_told_not_edited(self):
        (self.etc / "configuration.nix").write_text(DEFAULT_CONF)
        (self.etc / "flake.nix").write_text("{ }\n")
        done = self.run_step()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((self.etc / "configuration.nix").read_text(), DEFAULT_CONF)
        self.assertIn("halcyon = { enable = true;", done.stdout)
        self.assertIn("switch --flake", self.log.read_text())

    def test_no_rebuild_when_asked(self):
        (self.etc / "configuration.nix").write_text(DEFAULT_CONF)
        done = self.run_step(HALCYON_NIXOS_REBUILD="no")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse(self.log.exists())


class RoutingTest(unittest.TestCase):
    def test_nixos_is_its_own_group(self):
        script = (f'REPO_ROOT="{ROOT}"; printf "ID=nixos\\n" > "$REPO_ROOT/os-release.test"; '
                  f'sed "s|\\${{REPO_ROOT}}/os-release|$REPO_ROOT/os-release.test|" "{ROOT}/sdata/lib/dist-determine.sh" > /tmp/dd.$$; '
                  f'source /tmp/dd.$$ >/dev/null; rm -f /tmp/dd.$$ "$REPO_ROOT/os-release.test"; '
                  f'echo "$OS_GROUP_ID ${{INSTALL_VIA_NIX:-false}}"')
        done = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "nixos false", done.stderr)


if __name__ == "__main__":
    unittest.main()
