#!/usr/bin/env bash
# Halcyon — reach your settings without the shell.
#
# The Settings app is a Quickshell surface, so when the shell is down the
# one binding you most need to fix it is the one that stops working.
# settings.json is the same data the app edits, so opening it in an
# editor is a real fallback rather than a consolation prize.

set -Eeuo pipefail
# shellcheck source=scripts/lib/menu.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/menu.sh"

config_dir="${HALCYON_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/halcyon}"
settings="$config_dir/settings.json"

mkdir -p "$config_dir"
if [[ ! -f "$settings" ]]; then
	# An empty override document is valid: every key falls back to a
	# default, and leaving the version out means the file is read as
	# current rather than as one needing migration.
	printf '{\n}\n' >"$settings"
fi

# A terminal editor needs a terminal; a graphical one does not. Try the
# user's choice first, then anything that can open a JSON file at all.
terminal="${TERMINAL:-}"
if [[ -z "$terminal" ]]; then
	for candidate in kitty foot alacritty wezterm ghostty konsole gnome-terminal xterm; do
		if command -v "$candidate" >/dev/null 2>&1; then
			terminal="$candidate"
			break
		fi
	done
fi

editor="${VISUAL:-${EDITOR:-}}"
if [[ -n "$editor" && -n "$terminal" ]]; then
	exec "$terminal" -e "$editor" "$settings"
fi

if command -v xdg-open >/dev/null 2>&1; then
	exec xdg-open "$settings"
fi

if [[ -n "$terminal" ]]; then
	for candidate in nano vi vim; do
		if command -v "$candidate" >/dev/null 2>&1; then
			exec "$terminal" -e "$candidate" "$settings"
		fi
	done
fi

printf 'Halcyon settings live at: %s\n' "$settings" >&2
exit 1
