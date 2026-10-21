"""Halcyon's window layouts (layouts.lua): two at a time stacked or side by side, and the Mondrian grid, run under
real Lua with a stand-in for Hyprland's `hl`, and the placement files `halcyon placement` writes for them.
Run: python3 -m unittest discover -s tests"""

import contextlib
import importlib.machinery
import io
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
LAYOUTS = HALCYON / "layouts.lua"
LUA = shutil.which("lua") or shutil.which("lua5.4")

_loader = importlib.machinery.SourceFileLoader("halcyon_theme_layouts", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_layouts", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)

# A tiny JSON writer, so the Lua side can hand its results back.
JSON_LUA = r"""
local function enc(v)
  local t = type(v)
  if t == "table" then
    if #v > 0 or next(v) == nil then
      local out = {}
      for i, x in ipairs(v) do out[i] = enc(x) end
      return "[" .. table.concat(out, ",") .. "]"
    end
    local out = {}
    for k, x in pairs(v) do out[#out + 1] = string.format("%q", tostring(k)) .. ":" .. enc(x) end
    return "{" .. table.concat(out, ",") .. "}"
  elseif t == "string" then return string.format("%q", v)
  elseif t == "boolean" or t == "number" then return tostring(v)
  else return "null" end
end
"""


def run_lua(body):
    script = JSON_LUA + f'\nlocal L = dofile("{LAYOUTS}")\n' + body
    done = subprocess.run([LUA, "-"], input=script, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


def area_of(box):
    return box["w"] * box["h"]


def overlap(a, b):
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return max(0.0, w) * max(0.0, h)


@unittest.skipUnless(LUA, "no lua interpreter")
class BoxesTest(unittest.TestCase):
    AREA = {"x": 10, "y": 40, "w": 1900, "h": 1030}

    def boxes(self, mode, n):
        fn = {"stacked": "stacked", "side-by-side": "side_by_side", "mondrian": "mondrian",
              "golden-plus": "golden_plus"}[mode]
        a = self.AREA
        return run_lua(f"print(enc(L.{fn}({{x={a['x']}, y={a['y']}, w={a['w']}, h={a['h']}}}, {n})))")

    def assert_tiles_exactly(self, boxes):
        total = sum(area_of(b) for b in boxes)
        self.assertAlmostEqual(total, area_of(self.AREA), delta=1e-3)
        for i, a in enumerate(boxes):
            self.assertGreater(a["w"], 0)
            self.assertGreater(a["h"], 0)
            self.assertGreaterEqual(a["x"], self.AREA["x"] - 1e-6)
            self.assertLessEqual(a["x"] + a["w"], self.AREA["x"] + self.AREA["w"] + 1e-6)
            for b in boxes[i + 1:]:
                self.assertAlmostEqual(overlap(a, b), 0.0, delta=1e-3)

    def test_stacked_and_side_by_side(self):
        one = self.boxes("stacked", 1)
        self.assertEqual(one, [self.AREA])
        top, bottom = self.boxes("stacked", 2)
        self.assertEqual((top["w"], top["h"], bottom["y"]), (1900, 515, 40 + 515))
        left, right = self.boxes("side-by-side", 2)
        self.assertEqual((left["w"], left["h"], right["x"]), (950, 1030, 10 + 950))

    def test_mondrian_tiles_the_screen_without_overlap(self):
        for n in range(1, 13):
            boxes = self.boxes("mondrian", n)
            self.assertEqual(len(boxes), n)
            self.assert_tiles_exactly(boxes)

    def test_mondrian_cuts_alternate(self):
        # Three windows are not three columns: the second cut runs the other way.
        boxes = self.boxes("mondrian", 3)
        self.assertEqual(len({round(b["x"]) for b in boxes}), 2)
        self.assertEqual(len({round(b["y"]) for b in boxes}), 2)

    def test_mondrian_is_uneven_and_never_a_sliver(self):
        boxes = self.boxes("mondrian", 6)
        sizes = sorted(round(area_of(b)) for b in boxes)
        self.assertGreater(len(set(sizes)), 3, "Mondrian blocks differ in size")
        for b in boxes:
            self.assertGreater(min(b["w"], b["h"]) / max(b["w"], b["h"]), 0.2, b)
        first_two = self.boxes("mondrian", 2)
        self.assertAlmostEqual(first_two[0]["w"] / self.AREA["w"], 0.62, places=3)


    def test_golden_plus_is_a_golden_spiral(self):
        one, = self.boxes("golden-plus", 1)
        self.assertEqual(one, self.AREA)
        first, second, third = self.boxes("golden-plus", 3)
        self.assertAlmostEqual(first["w"] / self.AREA["w"], 0.618, places=3, msg="the first window: 61.8 % across")
        self.assertAlmostEqual(second["h"] / self.AREA["h"], 0.618, places=3, msg="the next: 61.8 % of the rest, down")
        self.assertEqual((second["x"], third["x"]), (first["x"] + first["w"], first["x"] + first["w"]))
        self.assertGreater(third["y"], second["y"], "the spiral turns")

    def test_golden_plus_holds_many_windows_and_none_is_a_sliver(self):
        for area in (self.AREA, {"x": 0, "y": 0, "w": 2560, "h": 1440}, {"x": 0, "y": 0, "w": 1366, "h": 768}):
            for n in range(1, 31):
                a = area
                boxes = run_lua(f"print(enc(L.golden_plus({{x={a['x']}, y={a['y']}, w={a['w']}, h={a['h']}}}, {n})))")
                self.assertEqual(len(boxes), n)
                total = sum(area_of(b) for b in boxes)
                self.assertAlmostEqual(total, area_of(a), delta=1e-3, msg=f"{n} windows fill the screen")
                for i, b in enumerate(boxes):
                    for c in boxes[i + 1:]:
                        self.assertAlmostEqual(overlap(b, c), 0.0, delta=1e-3)
                    if n <= 6:
                        self.assertGreaterEqual(min(b["w"], b["h"]), 320 if a["h"] >= 1000 else 150, (a, n, b))
                # Never the old dwindle 81 / 19: the smallest window is at least a fifth of the biggest's short side.
                sides = [min(b["w"], b["h"]) for b in boxes]
                self.assertGreater(min(sides) / max(sides), 0.2, (a, n))

    def test_golden_plus_keeps_the_spiral_while_windows_stay_usable(self):
        boxes = run_lua("print(enc(L.golden_plus({x=0, y=0, w=1920, h=1080}, 5)))")
        self.assertAlmostEqual(boxes[0]["w"], 1920 * 0.618, delta=1, msg="still a golden first window with five")
        self.assertEqual(len({(round(b["w"]), round(b["h"])) for b in boxes[1:]}), 1, "the rest an even grid")


@unittest.skipUnless(LUA, "no lua interpreter")
class HyprlandWiringTest(unittest.TestCase):
    """layouts.lua against a stand-in `hl`: what it registers, how it places windows, and the cap."""

    STUB = r"""
hl = { registered = {}, handlers = {}, dispatched = {}, ws_windows = {} }
hl.layout = { register = function(name, p) hl.registered[name] = p end }
hl.on = function(ev, fn) hl.handlers[ev] = fn end
hl.get_workspace_windows = function(ws) return hl.ws_windows end
hl.dsp = { window = { move = function(t) return t end } }
hl.dispatch = function(d) hl.dispatched[#hl.dispatched + 1] = { workspace = d.workspace, follow = d.follow,
  window = d.window and d.window.address } end
local function win(addr, opts)
  opts = opts or {}
  return { address = addr, floating = opts.floating or false, fullscreen = false, pinned = false,
           workspace = { id = 1, special = opts.special or false } }
end
"""

    def run_wired(self, body):
        return run_lua(self.STUB + "\nL = dofile(\"" + str(LAYOUTS) + "\")\n" + body)

    def test_registers_three_layouts_and_places_every_window(self):
        out = self.run_wired(r"""
local names = {}
for name in pairs(hl.registered) do names[#names + 1] = name end
table.sort(names)
local placed = {}
local targets = {}
for i = 1, 3 do
  targets[i] = { place = function(self, box) placed[#placed + 1] = box end }
end
hl.registered["halcyon-mondrian"].recalculate({ area = { x = 0, y = 0, w = 1000, h = 500 }, targets = targets })
print(enc({ names = names, placed = placed }))
""")
        self.assertEqual(out["names"], ["halcyon-golden-plus", "halcyon-mondrian", "halcyon-side-by-side", "halcyon-stacked"])
        self.assertEqual(len(out["placed"]), 3)
        # 62 / 38 across, then the bigger tile cut the other way, in halves: two rows in the 620 column.
        self.assertEqual([b["w"] for b in out["placed"]], [620, 620, 380])
        self.assertEqual([b["h"] for b in out["placed"]], [250, 250, 500])

    def test_a_third_window_goes_to_the_next_empty_workspace(self):
        out = self.run_wired(r"""
HALCYON_PLACEMENT = "stacked"
local a, b, c = win("0xa"), win("0xb"), win("0xc")
hl.ws_windows = { a, b }          -- two already there; the new one may or may not be listed yet
hl.handlers["window.open"](b)     -- the second: stays
local after_second = #hl.dispatched
hl.ws_windows = { a, b, c }
hl.handlers["window.open"](c)     -- the third: moves
print(enc({ after_second = after_second, moves = hl.dispatched }))
""")
        self.assertEqual(out["after_second"], 0)
        self.assertEqual(out["moves"], [{"workspace": "emptynm", "follow": True, "window": "0xc"}])

    def test_the_cap_leaves_floating_windows_special_workspaces_and_other_modes_alone(self):
        out = self.run_wired(r"""
local a, b = win("0xa"), win("0xb")
HALCYON_PLACEMENT = "side-by-side"
hl.ws_windows = { a, b, win("0xf", { floating = true }) }
hl.handlers["window.open"](win("0xf", { floating = true }))
hl.ws_windows = { a, b, win("0xs", { special = true }) }
hl.handlers["window.open"](win("0xs", { special = true }))
-- a floating window does not count towards the two
hl.ws_windows = { a, win("0xf2", { floating = true }), win("0xn") }
hl.handlers["window.open"](win("0xn"))
HALCYON_PLACEMENT = "mondrian"
hl.ws_windows = { a, b, win("0xm") }
hl.handlers["window.open"](win("0xm"))
HALCYON_PLACEMENT = "golden"
hl.handlers["window.open"](win("0xg"))
print(enc({ moves = #hl.dispatched }))
""")
        self.assertEqual(out["moves"], 0)

    def test_loads_without_hyprland(self):
        # The maths are usable (and testable) where there is no `hl` at all.
        self.assertEqual(run_lua("print(enc({ n = #L.mondrian({x=0,y=0,w=10,h=10}, 4) }))"), {"n": 4})


class PlacementFileTest(unittest.TestCase):
    def write(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "placement.lua")
            with unittest.mock.patch.object(theme, "PLACEMENT_LUA", target), \
                    unittest.mock.patch.object(theme, "hyprland_running", return_value=False), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(theme.cmd_placement([mode]), 0)
                return target.read_text()

    def test_dwindle_modes_set_dwindle_and_no_cap(self):
        text = self.write("golden")
        self.assertIn('HALCYON_PLACEMENT = "golden"', text)
        self.assertIn('layout = "dwindle"', text)
        # Dwindle's ratio is the first window's share times two: 1.236 is 61.8 / 38.2. 1.618 was 81 / 19.
        self.assertIn("default_split_ratio = 1.236", text)
        self.assertIn("split_bias = 1", text, "the window that was there keeps the bigger part")
        plus = self.write("golden-plus-dwindle")
        self.assertIn("default_split_ratio = 1.236, force_split = 2", plus)

    def test_an_old_golden_placement_is_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "placement.lua")
            target.write_text('-- mode: golden\nHALCYON_PLACEMENT = "golden"\n'
                              'hl.config({ general = { layout = "dwindle" }, dwindle = { default_split_ratio = 1.618, force_split = 0 } })\n')
            with unittest.mock.patch.object(theme, "PLACEMENT_LUA", target):
                self.assertTrue(theme.migrate_placement())
                self.assertIn("1.236", target.read_text())
                self.assertFalse(theme.migrate_placement(), "only once")

    def test_halcyon_modes_pick_their_lua_layout(self):
        for mode in ("stacked", "side-by-side", "mondrian", "golden-plus"):
            text = self.write(mode)
            self.assertTrue(text.startswith(f"-- mode: {mode}\n"))
            self.assertIn(f'HALCYON_PLACEMENT = "{mode}"', text)
            self.assertIn(f'layout = "lua:halcyon-{mode}"', text)

    def test_unknown_mode_is_refused(self):
        with self.assertRaises(theme.ThemeError):
            theme.cmd_placement(["spiral"])

    @unittest.skipUnless(shutil.which("luac") or shutil.which("luac5.4"), "no Lua compiler")
    def test_every_placement_file_is_valid_lua(self):
        luac = shutil.which("luac") or shutil.which("luac5.4")
        for mode in list(theme.PLACEMENTS) + list(theme.LUA_PLACEMENTS):
            with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as handle:
                handle.write(theme.placement_lua(mode))
            done = subprocess.run([luac, "-p", handle.name], capture_output=True, text=True, check=False)
            Path(handle.name).unlink()
            self.assertEqual(done.returncode, 0, mode + done.stderr)

    def test_settings_offer_every_mode(self):
        qml = (ROOT / "dots/.config/quickshell/ii/modules/settings/InterfaceConfig.qml").read_text()
        for mode in list(theme.PLACEMENTS) + list(theme.LUA_PLACEMENTS):
            if mode == "golden-plus-dwindle":
                self.assertIn('"golden-plus-dwindle"', qml)   # the switch under Golden ratio plus
                continue
            self.assertIn(f'value: "{mode}"', qml)
        self.assertIn('require("hyprland.halcyon.layouts")', (HALCYON / "init.lua").read_text())


if __name__ == "__main__":
    unittest.main()
