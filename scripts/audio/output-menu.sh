#!/usr/bin/env bash
# Halcyon — choose an audio output without the shell.

set -Eeuo pipefail
# shellcheck source=scripts/lib/menu.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/menu.sh"

menu_available || die "Install fuzzel, wofi or rofi to use this fallback."
has wpctl || has pactl || die "Neither wpctl nor pactl is installed."

if has wpctl; then
	# `wpctl status` marks the default sink with an asterisk; the id is
	# what set-default needs.
	choice="$(
		wpctl status |
			awk '/^Audio/,/^Video/' |
			awk '/Sinks:/,/^$/' |
			sed -n 's/^[ │├─└*]*\([0-9]\+\)\. \(.*\)\[vol.*/\1\t\2/p' |
			menu_pick "Output"
	)" || exit 0
	[[ -n "$choice" ]] || exit 0
	exec wpctl set-default "$(printf '%s' "$choice" | cut -f1)"
fi

choice="$(
	pactl -f json list sinks |
		python3 -c '
import json, sys
for sink in json.load(sys.stdin):
    name = sink.get("description") or sink.get("name")
    print(f"{sink.get(\"name\")}\t{name}")
' 2>/dev/null | menu_pick "Output"
)" || exit 0
[[ -n "$choice" ]] || exit 0
exec pactl set-default-sink "$(printf '%s' "$choice" | cut -f1)"
