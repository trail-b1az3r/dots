#!/usr/bin/env python3
"""Check rendered theme.lua files against Hyprland's real option table.

Parsing with luac only proves the Lua is valid Lua. Hyprland then rejects
values of the wrong shape at runtime: a gradient written as
"rgba(..) rgba(..) 45deg" parses fine but fails with "invalid color",
because the Lua config wants { colors = {...}, angle = 45 }. This runs each
file with a stand-in `hl` that records every setting, then checks each
one exists in Hyprland 0.56.2 (scripts/data/hyprland-0.56.2-options.json,
extracted from its ConfigValues.cpp) with a value of the right type.

    check-theme-lua.py FILE...
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPTIONS = json.loads((ROOT / "scripts/data/hyprland-0.56.2-options.json").read_text())["options"]
# Hyprland's development version adds these; halcyon-theme only emits them
# after asking the running compositor whether it has them.
FUTURE = re.compile(r"^decoration:blur:(variant|acrylic:.*)$")
RGBA = re.compile(r"^rgba\([0-9A-Fa-f]{8}\)$")
ANIMATION_KEYS = {"leaf", "enabled", "speed", "bezier", "style"}

RECORDER = r"""
local out = {}
local function emit(...) out[#out + 1] = table.concat({...}, "\t") end
local function is_array(t) return #t > 0 end
local function encode(v)
    if type(v) == "table" then
        local parts = {}
        if is_array(v) then
            for _, x in ipairs(v) do parts[#parts + 1] = encode(x) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, x in pairs(v) do parts[#parts + 1] = string.format("%q:%s", k, encode(x)) end
        return "{" .. table.concat(parts, ",") .. "}"
    elseif type(v) == "string" then return string.format("%q", v)
    elseif type(v) == "boolean" then return tostring(v)
    elseif math.type(v) == "integer" then return tostring(v)
    else return string.format("%.6f", v) end
end
local function walk(prefix, t)
    for k, v in pairs(t) do
        local path = prefix == "" and k or (prefix .. ":" .. k)
        if type(v) == "table" and not is_array(v) and v.colors == nil then
            walk(path, v)
        else
            emit("config", path, encode(v))
        end
    end
end
hl = {
    config = function(t) walk("", t) end,
    curve = function(name, spec) emit("curve", name, encode(spec)) end,
    animation = function(spec) emit("animation", encode(spec)) end,
    window_rule = function(spec) emit("window_rule", encode(spec)) end,
}
dofile(arg[1])
print(table.concat(out, "\n"))
"""


def lua_json(text):
    # The recorder's encoding is JSON apart from Lua's %q string escapes,
    # which for the strings a theme can contain are JSON-compatible.
    return json.loads(text)


def check_value(kind, value):
    if kind == "Bool":
        return isinstance(value, bool)
    if kind == "Int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "Float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "String":
        return isinstance(value, str)
    if kind == "Color":
        return isinstance(value, str) and bool(RGBA.match(value))
    if kind == "Vec2":
        return isinstance(value, list) and len(value) == 2 and all(isinstance(v, (int, float)) for v in value)
    if kind == "Gradient":
        if isinstance(value, str):
            return bool(RGBA.match(value))
        return (isinstance(value, dict) and isinstance(value.get("colors"), list) and value["colors"]
                and all(isinstance(c, str) and RGBA.match(c) for c in value["colors"])
                and set(value) <= {"colors", "angle"}
                and isinstance(value.get("angle", 0), (int, float)))
    return True


def check(path):
    result = subprocess.run(["lua5.4", "-", str(path)], input=RECORDER, capture_output=True, text=True)
    if result.returncode != 0:
        return [f"{path}: could not run: {result.stderr.strip()}"]
    problems = []
    curves = set()
    for line in filter(None, result.stdout.splitlines()):
        kind, *rest = line.split("\t")
        if kind == "config":
            name, raw = rest
            value = lua_json(raw)
            key = name.replace(".", ":")
            known = {k.replace(".", ":"): v for k, v in OPTIONS.items()}
            if key not in known:
                if not FUTURE.match(key):
                    problems.append(f"{path}: '{name}' is not a Hyprland 0.56 option")
                continue
            if not check_value(known[key], value):
                problems.append(f"{path}: '{name}' = {raw} is not a valid {known[key]}")
        elif kind == "curve":
            name, raw = rest
            spec = lua_json(raw)
            points = spec.get("points")
            if spec.get("type") != "bezier" or not (isinstance(points, list) and len(points) == 2
                                                  and all(len(p) == 2 for p in points)):
                problems.append(f"{path}: curve {name} is not a bezier with two points")
            curves.add(name)
        elif kind == "animation":
            spec = lua_json(rest[0])
            if set(spec) - ANIMATION_KEYS:
                problems.append(f"{path}: animation has unknown keys {set(spec) - ANIMATION_KEYS}")
            if spec.get("bezier") not in curves:
                problems.append(f"{path}: animation uses undefined curve {spec.get('bezier')}")
        elif kind == "window_rule":
            spec = lua_json(rest[0])
            if not isinstance(spec.get("match"), dict):
                problems.append(f"{path}: window rule without a match table")
    return problems


def main(paths):
    problems = [p for path in paths for p in check(Path(path))]
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"ok: {len(paths)} theme.lua files match Hyprland 0.56.2's options")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
