#!/usr/bin/env bash
# Static checks for this repository. CI runs exactly this, so running it
# locally tells you what CI will say.
#
#   ./scripts/validate.sh
#
# Needs: git, bash, python3 with Pillow, luac5.4 (or luac), glslangValidator.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

failed=0
fail() { printf 'FAIL: %s\n' "$*" >&2; failed=1; }
step() { printf '\n== %s\n' "$*"; }

luac="$(command -v luac5.4 || command -v luac || true)"

step "Lua parses (Hyprland config)"
if [[ -z "$luac" ]]; then
  fail "luac not found"
else
  while IFS= read -r f; do
    "$luac" -p -o /dev/null "$f" || fail "$f"
  done < <(git ls-files '*.lua')
fi

step "Shell scripts parse"
while IFS= read -r f; do
  first="$(head -n1 "$f")"
  case "$first" in *fish* | *zsh* | *python*) continue ;; esac
  # Some scripts carry data after their code (fuzzel-emoji.sh); only the
  # code above the marker is shell.
  sed '/^### DATA ###$/q' "$f" | bash -n || fail "$f"
done < <(git ls-files '*.sh' setup diagnose)

step "JSON parses"
while IFS= read -r f; do
  python3 -c 'import json, sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$f" || fail "$f"
done < <(git ls-files '*.json')

step "Halcyon keybinds do not collide with upstream"
python3 scripts/check-keybinds.py || fail "keybind collision"

step "Halcyon layer is wired in"
grep -qx 'require("hyprland.halcyon")' dots/.config/hypr/hyprland.lua ||
  fail "hyprland.lua does not require hyprland.halcyon"

step "Themes are valid and render to parseable Lua at every effects level"
halcyon_dir=dots/.config/hypr/hyprland/halcyon
theme_tool="$halcyon_dir/halcyon-theme"
python3 "$theme_tool" check || fail "theme check"
render_dir="$(mktemp -d)"
while IFS= read -r theme; do
  for level in full light off; do
    for native in "" --native-blur; do
      out="$render_dir/$theme-$level$native"
      # shellcheck disable=SC2086 # $native is deliberately empty or one flag
      python3 "$theme_tool" render "$theme" "$out" --effects "$level" $native >/dev/null ||
        fail "render $theme ($level$native)"
      if [[ -n "$luac" ]]; then
        "$luac" -p -o /dev/null "$out/theme.lua" || fail "$theme ($level$native): theme.lua"
      fi
    done
  done
  python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "$render_dir/$theme-full/colors.json" ||
    fail "$theme: colors.json"
done < <(python3 -c 'import pathlib, sys; [print(p.stem) for p in sorted(pathlib.Path(sys.argv[1]).glob("*.json"))]' \
  "$halcyon_dir/themes")
# luac only proves they are Lua; this checks Hyprland would accept them.
mapfile -t rendered < <(find "$render_dir" -name theme.lua | sort)
python3 scripts/check-theme-lua.py "${rendered[@]}" "$halcyon_dir/general.lua" ||
  fail "theme.lua values Hyprland would reject"
rm -rf "$render_dir"
grep -q 'halcyon-theme" detach' dots/.config/quickshell/ii/scripts/colors/switchwall.sh ||
  fail "switchwall.sh no longer detaches the theme on wallpaper changes"

step "Theme shell settings exist in the shell"
python3 scripts/check-theme-shell-config.py || fail "theme shell_config"

step "Screen shaders compile (GLSL ES 3.00)"
if command -v glslangValidator >/dev/null; then
  while IFS= read -r shader; do
    glslangValidator -S frag "$shader" >/dev/null || fail "$shader"
    # The flipped variant halcyon-theme can write must compile too.
    flipped="$(mktemp --suffix=.frag)"
    sed 's/#define FLIP_POINTER_Y 0/#define FLIP_POINTER_Y 1/' "$shader" >"$flipped"
    glslangValidator -S frag "$flipped" >/dev/null || fail "$shader (flipped)"
    rm -f "$flipped"
  done < <(git ls-files "$halcyon_dir/themes/shaders/*.frag")
else
  fail "glslangValidator not found (install glslang-tools)"
fi

step "Banner compositor runs"
if python3 -c 'import PIL' 2>/dev/null; then
  banner_dir="$(mktemp -d)"
  python3 - "$banner_dir" <<'PY'
import sys
from PIL import Image, ImageDraw
out = sys.argv[1]
cut = Image.new("RGBA", (600, 900), (0, 0, 0, 0))
ImageDraw.Draw(cut).ellipse((150, 50, 450, 350), fill=(230, 200, 170, 255))
cut.save(f"{out}/cutout.png")
Image.new("RGB", (1920, 1080), (60, 40, 90)).save(f"{out}/splash.jpg")
PY
  for art in cutout.png splash.jpg; do
    python3 "$halcyon_dir/halcyon-banner" --background "$halcyon_dir/themes/wallpapers/star-rail.jpg" \
      --art "$banner_dir/$art" --out "$banner_dir/out-$art.jpg" --title "Test" ||
      fail "banner compositor ($art)"
    [[ -s "$banner_dir/out-$art.jpg" ]] || fail "banner compositor wrote nothing ($art)"
  done
  rm -rf "$banner_dir"
else
  fail "Pillow not found (pip install pillow)"
fi

step "Cursor theme is complete and well formed"
python3 scripts/check-cursors.py || fail "cursor theme"

step "Shapes submodule is registered"
git ls-files -s dots/.config/quickshell/ii/modules/common/widgets/shapes | grep -q '^160000 ' ||
  fail "shapes submodule gitlink missing"

step "Wallpapers"
[[ -s dots/.config/quickshell/ii/assets/images/default_wallpaper.png ]] || fail "default wallpaper missing"
ls wallpapers/*.png >/dev/null 2>&1 || fail "no wallpapers to install"

if ((failed)); then
  printf '\nSome checks failed.\n' >&2
  exit 1
fi
printf '\nAll checks passed.\n'
