#!/usr/bin/env bash
# Halcyon — application launcher, without the shell.
#
# Spotlight lives in Quickshell. This is what runs when Quickshell does
# not: the same search results, rendered through whichever dmenu-style
# launcher is installed.

set -Eeuo pipefail
# shellcheck source=scripts/lib/menu.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/menu.sh"

query="${1:-}"

if ! menu_available; then
	die "Install fuzzel, wofi or rofi for a launcher that works without Quickshell."
fi

if ! has halcyon; then
	die "halcyon is not on PATH."
fi

# `halcyon search` with an empty query returns nothing, so an empty
# invocation asks for the term first.
if [[ -z "$query" ]]; then
	query="$(menu_input "Search")" || exit 0
	[[ -n "$query" ]] || exit 0
fi

mapfile -t results < <(
	halcyon search "$query" --json --limit 30 |
		python3 -c '
import json, sys
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for row in rows:
    subtitle = row.get("subtitle", "")
    label = row.get("title", "")
    if subtitle:
        label = f"{label}  —  {subtitle}"
    print(f"{label}\t{json.dumps(row.get(\"activate\", {}))}")
' 2>/dev/null
)

((${#results[@]} > 0)) || {
	notify-send -a Halcyon "No results" "$query" 2>/dev/null || true
	exit 0
}

choice="$(printf '%s\n' "${results[@]}" | cut -f1 | menu_pick "Halcyon")" || exit 0
[[ -n "$choice" ]] || exit 0

payload="$(printf '%s\n' "${results[@]}" | awk -F'\t' -v want="$choice" '$1 == want {print $2; exit}')"
[[ -n "$payload" ]] || exit 0

exec halcyon activate "$payload"
