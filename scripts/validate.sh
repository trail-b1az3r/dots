#!/usr/bin/env bash
# Static checks for this repository. CI runs exactly this, so running it
# locally tells you what CI will say.
#
#   ./scripts/validate.sh
#
# Needs: git, bash, python3, luac5.4 (or luac).

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

step "Themes are valid and render to parseable Lua"
theme_tool=dots/.config/hypr/hyprland/halcyon/halcyon-theme
python3 "$theme_tool" check || fail "theme check"
render_dir="$(mktemp -d)"
while IFS= read -r theme; do
  python3 "$theme_tool" render "$theme" "$render_dir/$theme" >/dev/null || fail "render $theme"
  [[ -n "$luac" ]] && { "$luac" -p -o /dev/null "$render_dir/$theme/theme.lua" || fail "$theme: theme.lua"; }
  python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "$render_dir/$theme/colors.json" || fail "$theme: colors.json"
done < <(python3 -c 'import pathlib, sys; [print(p.stem) for p in sorted(pathlib.Path(sys.argv[1]).glob("*.json"))]' \
  dots/.config/hypr/hyprland/halcyon/themes)
rm -rf "$render_dir"
grep -q 'halcyon-theme" detach' dots/.config/quickshell/ii/scripts/colors/switchwall.sh ||
  fail "switchwall.sh no longer detaches the theme on wallpaper changes"

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
