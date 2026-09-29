"""Tests for halcyon-windows, against a fake hyprctl.

The fake keeps a list of windows in a JSON file and runs every dispatcher
expression through real Lua, with stand-ins for Hyprland's hl.dsp
functions that check field names and types the way Hyprland 0.56 reads
them. So a syntax slip or a wrong field in a dispatcher fails here.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon-windows"

MOCK_LUA = r"""
local function sel(t, fn)
  assert(type(t) == "table", fn .. ": expected a table")
  if t.window ~= nil then
    assert(type(t.window) == "string" and t.window:match("^address:0x%x+$"), fn .. ": bad window selector")
  end
  return t.window and t.window:sub(9) or "active"
end
local function ws(t, fn)
  local w = t.workspace
  assert(type(w) == "number" or type(w) == "string", fn .. ": workspace must be a number or string")
  return tostring(w)
end
hl = { dsp = { window = {}, workspace = {} } }
function hl.dsp.window.move(t)
  local a = sel(t, "window.move")
  for k in pairs(t) do assert(k == "window" or k == "workspace" or k == "follow", "window.move: unknown field " .. k) end
  return "move\t" .. a .. "\t" .. ws(t, "window.move") .. "\t" .. tostring(t.follow)
end
function hl.dsp.focus(t)
  if t.workspace then return "focusws\t" .. ws(t, "focus") end
  return "focus\t" .. sel(t, "focus")
end
function hl.dsp.window.close(t) return "close\t" .. sel(t, "close") end
function hl.dsp.window.float(t) assert(t.action == "toggle"); return "float\t" .. sel(t, "float") end
function hl.dsp.window.pin(t) assert(t.action == "toggle"); return "pin\t" .. sel(t, "pin") end
function hl.dsp.window.center(t) return "center\t" .. sel(t, "center") end
function hl.dispatch(x) print(x) end
hl.dispatch(%s)
"""

FAKE_HYPRCTL = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
state_path = os.environ["FAKE_HYPR_STATE"]
state = json.load(open(state_path))
args = sys.argv[1:]
if args[:2] == ["-j", "clients"]:
    print(json.dumps(state["clients"])); sys.exit()
if args[:2] == ["-j", "activewindow"]:
    act = next((c for c in state["clients"] if c["address"] == state["active"]), {})
    print(json.dumps(act)); sys.exit()
if args[0] == "dispatch":
    lua = open(os.environ["FAKE_HYPR_MOCK"]).read().replace("%s", args[1])
    done = subprocess.run(["lua5.4", "-"], input=lua, capture_output=True, text=True)
    if done.returncode != 0:
        print("error: " + done.stderr.strip()); sys.exit()
    parts = done.stdout.strip().split("\t")
    state.setdefault("log", []).append(parts)
    byaddr = {c["address"]: c for c in state["clients"]}
    if parts[0] == "move":
        c = byaddr[parts[1]]
        target = parts[2]
        if target == "e+0":
            target = state["currentWorkspace"]
        if target.startswith("special:"):
            c["workspace"] = {"id": -98, "name": target}
        else:
            c["workspace"] = {"id": int(target), "name": target}
    elif parts[0] == "focus":
        state["active"] = parts[1]
    elif parts[0] == "close":
        state["clients"] = [c for c in state["clients"] if c["address"] != parts[1]]
    json.dump(state, open(state_path, "w"))
    print("ok"); sys.exit()
print("unknown request"); sys.exit(1)
'''


def window(address, app, title, ws, focus=0):
    return {"address": address, "class": app, "title": title, "workspace": {"id": ws, "name": str(ws)},
            "floating": False, "pinned": False, "fullscreen": 0, "mapped": True, "focusHistoryID": focus}


class WindowsTest(unittest.TestCase):
    def setUp(self):
        if not shutil.which("lua5.4"):
            self.skipTest("lua5.4 not installed")
        self.tmp = Path(tempfile.mkdtemp())
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "hyprctl"
        fake.write_text(FAKE_HYPRCTL)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        (self.tmp / "mock.lua").write_text(MOCK_LUA)
        self.state = self.tmp / "hypr.json"
        self.write({"active": "0xa1", "currentWorkspace": "2", "clients": [
            window("0xa1", "firefox", "News", 1, 0),
            window("0xa2", "firefox", "Mail", 1, 2),
            window("0xb1", "kitty", "shell", 2, 1),
        ]})
        self.env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_HYPR_STATE": str(self.state),
                    "FAKE_HYPR_MOCK": str(self.tmp / "mock.lua"), "XDG_STATE_HOME": str(self.tmp / "st")}
        self._old_env = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        loader = importlib.machinery.SourceFileLoader("halcyon_windows", str(TOOL))
        spec = importlib.util.spec_from_loader("halcyon_windows", loader)
        self.w = importlib.util.module_from_spec(spec)
        loader.exec_module(self.w)

    def tearDown(self):
        for key, value in getattr(self, "_old_env", {}).items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def write(self, data):
        self.state.write_text(json.dumps(data))

    def read(self):
        return json.loads(self.state.read_text())

    def where(self, address):
        return next(c["workspace"]["name"] for c in self.read()["clients"] if c["address"] == address)

    def test_minimise_and_restore_return_windows_home(self):
        self.w.minimise()
        self.assertEqual(self.where("0xa1"), "special:minimised")
        self.w.minimise("0xb1")
        self.assertEqual([e["address"] for e in self.w.read_stack()], ["0xa1", "0xb1"])
        self.w.restore()  # last minimised first
        self.assertEqual(self.where("0xb1"), "2")
        self.w.restore()
        self.assertEqual(self.where("0xa1"), "1")
        self.assertEqual(self.read()["active"], "0xa1")
        with self.assertRaises(self.w.WindowError):
            self.w.restore()

    def test_hide_minimises_the_whole_app(self):
        self.assertIn("2 firefox windows", self.w.hide())
        self.assertEqual(self.where("0xa1"), "special:minimised")
        self.assertEqual(self.where("0xa2"), "special:minimised")
        self.assertEqual(self.where("0xb1"), "2")
        self.assertIn("2 windows", self.w.restore_all())
        self.assertEqual({self.where("0xa1"), self.where("0xa2")}, {"1"})

    def test_hide_a_given_windows_app(self):
        self.assertIn("1 kitty window", self.w.hide("0xb1"))
        self.assertEqual(self.where("0xb1"), "special:minimised")
        self.assertEqual(self.where("0xa1"), "1")

    def test_hide_others_keeps_only_the_focused_window(self):
        self.assertIn("1 other window", self.w.hide_others())
        self.assertEqual(self.where("0xa1"), "1")
        self.assertEqual(self.where("0xa2"), "special:minimised")
        self.assertEqual(self.where("0xb1"), "2")  # another workspace: untouched

    def test_restore_a_specific_window_and_forget_closed_ones(self):
        self.w.minimise("0xa1")
        self.w.minimise("0xa2")
        self.w.restore("0xa1")
        self.assertEqual(self.where("0xa1"), "1")
        self.assertEqual(self.where("0xa2"), "special:minimised")
        # 0xa2 closes while minimised: it drops out of the stack.
        state = self.read()
        state["clients"] = [c for c in state["clients"] if c["address"] != "0xa2"]
        self.write(state)
        self.assertEqual(self.w.live_stack(), [])

    def test_restore_falls_back_to_current_workspace(self):
        self.w.minimise("0xb1")
        entries = self.w.read_stack()
        entries[0]["workspace"] = None
        self.w.write_stack(entries)
        self.w.restore()
        self.assertEqual(self.where("0xb1"), "2")  # the fake's current workspace

    def test_focusing_a_minimised_window_restores_it(self):
        self.w.minimise("0xb1")
        self.w.simple("focus", "0xb1")
        self.assertEqual(self.where("0xb1"), "2")

    def test_simple_actions_produce_valid_dispatchers(self):
        for action in ("close", "float", "pin", "centre"):
            self.w.simple(action, "0xb1")
        kinds = [entry[0] for entry in self.read()["log"]]
        self.assertEqual(kinds, ["close", "float", "pin", "center"])

    def test_listing(self):
        self.w.minimise("0xa2")
        windows = self.w.listing()
        self.assertEqual([w["address"] for w in windows], ["0xa1", "0xb1", "0xa2"])
        self.assertTrue(windows[0]["focused"])
        self.assertTrue(windows[-1]["minimised"])

    def test_rejects_anything_that_isnt_an_address(self):
        for bad in ('0xa1"}) os.execute("x', "firefox", "", "0x"):
            with self.assertRaises(self.w.WindowError):
                self.w.simple("close", bad)
        with self.assertRaises(self.w.WindowError):
            self.w.workspace_literal('1" .. os.exit() .. "')


if __name__ == "__main__":
    unittest.main()
