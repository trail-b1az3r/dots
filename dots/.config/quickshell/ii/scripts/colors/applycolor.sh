#!/usr/bin/env bash

QUICKSHELL_CONFIG_NAME="ii"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
CONFIG_DIR="$XDG_CONFIG_HOME/quickshell/$QUICKSHELL_CONFIG_NAME"
CACHE_DIR="$XDG_CACHE_HOME/quickshell"
STATE_DIR="$XDG_STATE_HOME/quickshell"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

term_alpha=100 #Set this to < 100 make all your terminals transparent
# sleep 0 # idk i wanted some delay or colors dont get applied properly
if [ ! -d "$STATE_DIR"/user/generated ]; then
  mkdir -p "$STATE_DIR"/user/generated
fi
cd "$CONFIG_DIR" || exit

render_terminal_template() {
  local template="$1"
  local destination="$2"
  local kind="${3:-text}"
  if [ ! -f "$template" ]; then
    echo "Terminal color template not found: $template"
    return 0
  fi
  mkdir -p "$(dirname "$destination")"
  python3 - "$template" "$destination" "$kind" "$term_alpha" "$STATE_DIR/user/generated/material_colors.scss" <<'PY'
import os
import re
import sys
import tempfile
from pathlib import Path

source, destination, kind, alpha, scss = sys.argv[1:]
source = Path(source)
destination = Path(destination)
scss = Path(scss)
if not scss.is_file():
    raise SystemExit(f"No generated Material colors found at {scss}")
colors = {}
for line in scss.read_text(encoding="utf-8").splitlines():
    match = re.match(r"^\$([A-Za-z0-9_]+):\s*(#[0-9A-Fa-f]{6});\s*$", line)
    if match:
        colors[match.group(1)] = match.group(2)

text = source.read_text(encoding="utf-8")
missing = set()
def replace(match):
    name = match.group(1)
    value = colors.get(name)
    if value is None:
        missing.add(name)
        return match.group(0)
    return value

# Match the complete placeholder literally. This avoids sed treating '$term10'
# as an end-of-line anchor and leaving invalid '#$term10 #' values behind.
text = re.sub(r"#\$([A-Za-z0-9_]+) #", replace, text)
text = text.replace("$alpha", alpha)
if missing:
    raise SystemExit("Missing generated color tokens: " + ", ".join(sorted(missing)))
if re.search(r"#\$[A-Za-z0-9_]+\s*#", text):
    raise SystemExit("Unexpanded terminal color placeholder remains")
if kind == "toml":
    try:
        import tomllib
        tomllib.loads(text)
    except Exception as error:
        raise SystemExit(f"Generated Alacritty TOML is invalid: {error}")
destination.parent.mkdir(parents=True, exist_ok=True)
fd, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
except BaseException:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
PY
}

apply_kitty() {
  render_terminal_template "$SCRIPT_DIR/terminal/kitty-theme.conf" \
    "$STATE_DIR/user/generated/terminal/kitty-theme.conf" text || return
  if pgrep -f kitty >/dev/null 2>&1; then
    pkill -USR1 -x kitty 2>/dev/null || true
  fi
}

apply_alacritty() {
  render_terminal_template "$SCRIPT_DIR/terminal/alacritty-theme.toml" \
    "$STATE_DIR/user/generated/terminal/alacritty-theme.toml" toml
}

apply_anyterm() {
  render_terminal_template "$SCRIPT_DIR/terminal/sequences.txt" \
    "$STATE_DIR/user/generated/terminal/sequences.txt" text || return
  for file in /dev/pts/*; do
    if [[ $file =~ ^/dev/pts/[0-9]+$ ]]; then
      cat "$STATE_DIR/user/generated/terminal/sequences.txt" >"$file" 2>/dev/null &
      disown || true
    fi
  done
}

apply_term() {
  apply_anyterm &
  apply_kitty &
  apply_alacritty &
}

# Check if terminal theming is enabled in config
CONFIG_FILE="$XDG_CONFIG_HOME/illogical-impulse/config.json"
if [ -f "$CONFIG_FILE" ]; then
  enable_terminal=$(jq -r '.appearance.wallpaperTheming.enableTerminal' "$CONFIG_FILE")
  if [ "$enable_terminal" = "true" ]; then
    apply_term &
  fi
else
  echo "Config file not found at $CONFIG_FILE. Applying terminal theming by default."
  apply_term &
fi

# apply_qt & # Qt theming is already handled by kde-material-colors

# Halcyon: Firefox and Chromium follow these colours too. halcyon-theme does it itself once a theme is fully
# applied (it sets HALCYON_THEME_APPLYING for the scripts it runs), so only wallpaper changes are handled here.
if [ -z "$HALCYON_THEME_APPLYING" ] && [ -x "$XDG_CONFIG_HOME/hypr/hyprland/halcyon/halcyon_browsers.py" ]; then
  "$XDG_CONFIG_HOME/hypr/hyprland/halcyon/halcyon_browsers.py" update --quiet >/dev/null 2>&1 &
fi
