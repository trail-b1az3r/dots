#!/usr/bin/env bash
# Halcyon — show the current palette in the terminal.
#
# Useful when a wallpaper produces colours that look wrong and you want
# to see what was actually derived rather than guess from the screen.

set -Eeuo pipefail
# shellcheck source=scripts/lib/common.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"

theme="$HALCYON_GENERATED_DIR/theme.json"
[[ -f "$theme" ]] || die "No theme yet. Run: halcyon theme apply"

python3 - "$theme" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    tokens = json.load(handle)


def rgb(argb: str) -> tuple[int, int, int]:
    raw = argb.lstrip("#")
    if len(raw) == 8:
        raw = raw[2:]
    return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))


def swatch(argb: str, width: int = 6) -> str:
    r, g, b = rgb(argb)
    return f"\033[48;2;{r};{g};{b}m{' ' * width}\033[0m"


palette = tokens.get("palette", {})
print()
print(f"  Mode      {tokens.get('mode')}")
print(f"  Preset    {tokens.get('preset')}")
print(f"  Palette   {palette.get('source')}")
print()

if palette.get("swatches"):
    print("  From the wallpaper")
    print("    " + " ".join(swatch(c) for c in palette["swatches"]))
    print("    " + "  ".join(f"{c:<5}" for c in palette["swatches"]))
    print()

groups = {
    "Accent": ["accent", "accentHover", "accentPressed", "onAccent", "secondary", "tertiary"],
    "Text": ["text", "textSecondary", "textTertiary", "textDisabled"],
    "Surface": ["backdrop", "surfaceSolid", "surfaceRaisedSolid", "surfaceSunken"],
    "Semantic": ["success", "warning", "danger", "info"],
    "Window": ["borderActive", "borderActiveEnd", "borderInactive"],
}

colors = tokens.get("color", {})
for title, names in groups.items():
    present = [name for name in names if name in colors]
    if not present:
        continue
    print(f"  {title}")
    print("    " + " ".join(swatch(colors[name]) for name in present))
    print("    " + " ".join(f"{name[:6]:<6}" for name in present))
    print()
PY
