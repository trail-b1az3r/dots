"""Telling hyprland-plus from stock Hyprland, per build; and `halcyon crashes`."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))

import halcyon_compositor as hc  # noqa: E402
import halcyon_config_check as cc  # noqa: E402
import halcyon_crashes as cr  # noqa: E402

OLD_PLUS = "hyprland-plus 0.56.2.p1 built from branch halcyon-0.56.2 at commit 7dd6020 (Drag fix)."
NEW_PLUS = "hyprland-plus 0.56.2.p1 (Hyprland 0.56.2) built from branch halcyon-0.56.2 at commit 42102df (x)."
STOCK = "Hyprland 0.56.2 built from branch  at commit abcdef0 (version: bump)."
LUA = shutil.which("lua") or shutil.which("lua5.4")


class VersionTests(unittest.TestCase):
    def test_every_plus_build_is_plus(self):
        self.assertTrue(hc.is_plus_version(OLD_PLUS))
        self.assertTrue(hc.is_plus_version(NEW_PLUS))
        self.assertFalse(hc.is_plus_version(STOCK))
        self.assertFalse(hc.is_plus_version(None))

    def test_describe(self):
        self.assertIn("stock Hyprland", hc.describe({"running": True, "plus": False, "version": STOCK}))
        old = hc.describe({"running": True, "plus": True, "tiles": False, "version": OLD_PLUS})
        self.assertIn("before Plus Tiles", old)
        self.assertIn("hyprctl-lite", old)
        self.assertEqual(hc.describe({"running": True, "plus": True, "tiles": True, "version": NEW_PLUS}), f"hyprland-plus ({NEW_PLUS})")
        self.assertEqual(hc.describe({"running": False, "plus": False, "version": ""}), "Hyprland was not found")


class ConfigErrorTests(unittest.TestCase):
    ERR = ['config option "plus:step" does not exist']

    def test_old_plus_build_is_told_to_update(self):
        found = cc.classify_config_errors(self.ERR, has_plus=True, tiles=False)
        self.assertEqual(found[0].area, "version")
        self.assertIn("newer than the running hyprland-plus", found[0].message)
        self.assertIn("hyprctl-lite", found[0].fix)

    def test_stock_and_typo_cases_unchanged(self):
        self.assertIn("needs hyprland-plus", cc.classify_config_errors(self.ERR, has_plus=False)[0].message)
        self.assertEqual(cc.classify_config_errors(self.ERR, has_plus=True)[0].area, "config")


@unittest.skipUnless(LUA, "no lua interpreter")
class LuaCapabilityTests(unittest.TestCase):
    """compositor.lua and rules.lua against mock hl tables for stock, old-plus and new-plus builds."""

    def run_lua(self, build: str) -> str:
        script = textwrap.dedent(f"""
            package.path = "{HALCYON.parent.parent}/?.lua;" .. package.path
            package.preload["hyprland.halcyon.compositor"] = function() return dofile("{HALCYON}/compositor.lua") end
            local build = "{build}"
            local window = {{}}
            local dsp = {{ window = window }}
            if build ~= "stock" then window.mini = function() end end
            if build == "old" or build == "new" then window.fit_plustile = function() end end
            if build == "new" then dsp.plus = {{}} end
            local rules_made, notified = {{}}, {{}}
            hl = {{ dsp = dsp, window_rule = function(r) rules_made[#rules_made + 1] = r end,
                   exec_cmd = function(c) notified[#notified + 1] = c end }}
            local caps = dofile("{HALCYON}/compositor.lua")
            local rules = dofile("{HALCYON}/rules.lua")
            local report = rules.apply({{
                {{ class = "^(spotify)$", superposition = true }},
                {{ class = "^(mpv)$", plus = true, keep_size = true }},
                {{ class = "^(kitty)$", role = "plus" }},
            }}, caps)
            local spot = rules_made[1] or {{}}
            print("plus=" .. tostring(caps.plus) .. " strips=" .. tostring(caps.strips) .. " tiles=" .. tostring(caps.tiles))
            print("superposition=" .. tostring(spot.superposition))
            print("notified=" .. #notified .. " skipped=" .. #rules.skipped)
            for _, r in ipairs(rules_made) do if r.match.class == "^(kitty)$" then print("kitty_plustile=" .. tostring(r.plustile)) end end
            print("missing_tiles=" .. tostring(caps.missing("tiles")))
        """)
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as f:
            f.write(script)
        try:
            out = subprocess.run([LUA, f.name], capture_output=True, text=True, check=False)
        finally:
            os.unlink(f.name)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_stock(self):
        out = self.run_lua("stock")
        self.assertIn("plus=false strips=false tiles=false", out)
        self.assertIn("superposition=nil", out)
        self.assertIn("notified=0", out)        # no warning on stock Hyprland for the shipped rules
        self.assertIn("missing_tiles=needs hyprland-plus", out)

    def test_old_plus_keeps_strips_and_plustile(self):
        out = self.run_lua("old")
        self.assertIn("plus=true strips=true tiles=false", out)
        self.assertIn("superposition=true", out)
        self.assertIn("kitty_plustile=true", out)
        self.assertIn("notified=0", out)
        self.assertIn("skipped=1", out)          # keep_size needs the newer build
        self.assertIn("missing_tiles=needs a newer hyprland-plus", out)

    def test_new_plus_has_everything(self):
        out = self.run_lua("new")
        self.assertIn("plus=true strips=true tiles=true", out)
        self.assertIn("skipped=0", out)
        self.assertIn("missing_tiles=nil", out)


class CrashTests(unittest.TestCase):
    def test_oom_lines(self):
        lines = ["Out of memory: Killed process 4242 (vesktop) total-vm:1kB",
                 "oom-kill:constraint=CONSTRAINT_NONE,nodemask=(null),task=spotify,pid=99", "unrelated"]
        self.assertEqual(cr.parse_oom(lines), ["vesktop", "spotify"])

    def test_coredumps(self):
        rows = cr.parse_coredumps('[{"time": 1, "pid": 5, "sig": 11, "exe": "/usr/lib/electron/electron"}]')
        self.assertEqual(rows[0]["signal"], 11)
        self.assertEqual(cr.parse_coredumps("not json"), [])

    def test_verdict_old_unit(self):
        notes = cr.verdict({"KillMode": "control-group", "OOMPolicy": "stop"}, [], [], ["Scheduled restart job, restart counter is at 3."], ["vesktop", "spotify"])
        joined = " ".join(notes)
        self.assertIn("closes every app it opened", joined)
        self.assertIn("vesktop", joined)
        self.assertIn("restarted 1 time", joined)

    def test_verdict_fixed_unit(self):
        notes = cr.verdict({"KillMode": "process", "OOMPolicy": "continue"}, [], [], [], [])
        self.assertEqual(notes, ["Nothing recorded: no core dumps, memory kills or shell restarts in this period."])

    def test_shipped_unit_is_fixed(self):
        unit = (ROOT / "dots/.config/systemd/user/halcyon-quickshell.service").read_text()
        self.assertIn("KillMode=process", unit)
        self.assertIn("OOMPolicy=continue", unit)


@unittest.skipUnless(shutil.which("bash"), "no bash")
class InstallerDetectionTests(unittest.TestCase):
    def detect(self, version_line: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "Hyprland"
            fake.write_text(f"#!/bin/sh\necho '{version_line}'\n")
            fake.chmod(0o755)
            script = (f'pacman(){{ return 1; }}; source "{ROOT}/sdata/lib/hyprland-plus-detect.sh"; '
                      'hyprland_plus_installed && hyprland_plus_commit && hyprland_plus_base_version')
            env = dict(os.environ, PATH=f"{d}:/usr/bin:/bin", HOME=d)
            return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, check=False)

    def test_old_and_new_builds_found(self):
        old = self.detect(OLD_PLUS)
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertIn("7dd6020", old.stdout)
        self.assertIn("0.56.2", old.stdout)
        new = self.detect(NEW_PLUS)
        self.assertIn("42102df", new.stdout)

    def test_stock_is_not_plus(self):
        self.assertNotEqual(self.detect(STOCK).returncode, 0)


if __name__ == "__main__":
    unittest.main()
