#!/usr/bin/env python3
"""Fail if the Halcyon layer binds a chord upstream already uses.

Hyprland runs every binding registered for a chord, so a Halcyon bind on
an upstream chord would not replace the upstream action, it would fire
alongside it. The layer is meant to only add; this keeps it honest.

Only literal first arguments of hl.bind(...) are compared. Binds built in
loops (workspace numbers, arrow keys) are expanded from the patterns
upstream uses below, so they are covered too.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HYPR = ROOT / "dots/.config/hypr/hyprland"
UPSTREAM = [HYPR / "keybinds.lua"]
HALCYON = sorted((HYPR / "halcyon").glob("*.lua"))

BIND = re.compile(r'hl\.bind\(\s*"([^"]+)"')
# hl.bind("SUPER + " .. (i % 10), ...) style loops over digits and arrows.
LOOP = re.compile(r'hl\.bind\(\s*"([^"]+)"\s*\.\.\s*(\(i % 10\)|arrowkey\[i\]|keys\[i\])')
LOOP_VALUES = {
    "(i % 10)": [str(i) for i in range(10)],
    "arrowkey[i]": ["Left", "Right", "Up", "Down", "BracketLeft", "BracketRight"],
    "keys[i]": ["Left", "Right"],
}


def normalise(chord):
    parts = [p.strip() for p in chord.split("+") if p.strip()]
    *mods, key = parts
    return " + ".join(sorted(m.upper() for m in mods) + [key.lower()])


def chords(path):
    text = path.read_text(encoding="utf-8")
    # Ignore everything inside a submap: those chords only apply there.
    text = re.sub(r"hl\.define_submap\(.*?\nend\)", "", text, flags=re.S)
    found = {normalise(c) for c in BIND.findall(text) if not c.endswith(" ")}
    for prefix, var in LOOP.findall(text):
        found |= {normalise(prefix + v) for v in LOOP_VALUES[var]}
    return found


def main():
    upstream = set().union(*(chords(p) for p in UPSTREAM))
    clashes = []
    for path in HALCYON:
        for chord in sorted(chords(path) & upstream):
            clashes.append(f"{path.relative_to(ROOT)}: {chord} is already bound upstream")
    for line in clashes:
        print(line, file=sys.stderr)
    if clashes:
        return 1
    print(f"ok: {len(upstream)} upstream chords, no Halcyon bind overlaps them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
