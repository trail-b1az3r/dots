"""minimize-all: against a fake hyprctl that, like the real one, only prints JSON with -j. Every dispatch it sends is
also run through Lua as Hyprland would (`return hl.dispatch(...)`), against a stand-in `hl`, so a malformed one
fails here. Run: python3 -m unittest discover -s tests"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/minimize-all"
LUA = shutil.which("lua") or shutil.which("lua5.4")

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
state_file = os.environ["FAKE_STATE"]
state = json.load(open(state_file))
args = sys.argv[1:]
as_json = "-j" in args
args = [a for a in args if a != "-j"]
if args[0] == "dispatch":
    state.setdefault("dispatched", []).append(" ".join(args[1:]))
    json.dump(state, open(state_file, "w"))
    print("ok")
elif args[0] in ("clients", "activeworkspace"):
    data = state[args[0]]
    print(json.dumps(data) if as_json else "Window 0x1 -> some title:\n\tmapped: 1\n")
'''

STUB = r"""
hl = { dsp = { window = {} } }
function hl.dsp.window.move(t)
  assert(type(t) == "table", "move takes a table")
  assert(t.workspace ~= nil, "workspace is required")
  assert(type(t.window) == "string" and t.window:match("^address:0x%x+$"), "window selector")
  assert(t.follow == false, "minimising never follows")
  return t
end
function hl.dispatch(d) return "ok" end
"""


@unittest.skipUnless(shutil.which("bash") and shutil.which("python3"), "needs bash and python3")
class MinimizeAllTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        fake = self.dir / "hyprctl"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        for name in ("notify-send",):
            stub = self.dir / name
            stub.write_text("#!/bin/sh\nexit 0\n")
            stub.chmod(0o755)
        self.state = self.dir / "state.json"

    def run_tool(self, clients, active_id=1, action=None):
        self.state.write_text(json.dumps({"clients": clients, "activeworkspace": {"id": active_id, "name": str(active_id)}}))
        env = dict(os.environ, PATH=f"{self.dir}:{os.environ['PATH']}", FAKE_STATE=str(self.state))
        done = subprocess.run(["bash", str(TOOL), *([action] if action else [])], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(self.state.read_text()).get("dispatched", [])

    @staticmethod
    def client(address, ws_id, ws_name=None):
        return {"address": address, "mapped": True, "hidden": False,
                "workspace": {"id": ws_id, "name": ws_name or str(ws_id)}}

    def assert_valid_lua(self, expressions):
        if not LUA:
            return
        for expression in expressions:
            script = STUB + f"\nassert(load('return hl.dispatch(' .. {json.dumps(expression)} .. ')'))()\n"
            done = subprocess.run([LUA, "-"], input=script, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, f"{expression}\n{done.stderr}")

    def test_minimises_every_window_on_this_workspace(self):
        sent = self.run_tool([self.client("0xa1", 1), self.client("0xb2", 1), self.client("0xc3", 2)])
        self.assertEqual(len(sent), 2, sent)
        self.assertTrue(all('"special:halcyon-minimized"' in s for s in sent))
        self.assertIn('window = "address:0xa1"', sent[0])
        self.assert_valid_lua(sent)

    def test_runs_again_to_restore_them_here(self):
        hidden = [self.client("0xa1", -98, "special:halcyon-minimized"), self.client("0xb2", -98, "special:halcyon-minimized")]
        sent = self.run_tool(hidden + [self.client("0xd4", 3)], active_id=3)
        self.assertEqual(len(sent), 2)
        self.assertTrue(all("workspace = 3," in s for s in sent), sent)
        self.assert_valid_lua(sent)

    def test_explicit_minimise_with_some_already_hidden(self):
        hidden = [self.client("0xa1", -98, "special:halcyon-minimized")]
        sent = self.run_tool(hidden + [self.client("0xe5", 1)], action="minimise")
        self.assertEqual(len(sent), 1)
        self.assertIn("0xe5", sent[0])


if __name__ == "__main__":
    unittest.main()
