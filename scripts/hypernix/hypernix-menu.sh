#!/usr/bin/env bash
# Halcyon — HyperNix actions, without the shell.
#
# Read-only and interactive entries only. Nothing here starts a training
# or quantisation run: those belong to HyperNix's own interface, where
# the person can see what they are about to spend an hour on.

set -Eeuo pipefail
# shellcheck source=scripts/lib/menu.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/menu.sh"

binary=""
for candidate in hypernix hnx; do
	if has "$candidate"; then
		binary="$candidate"
		break
	fi
done

[[ -n "$binary" ]] || die "HyperNix is not installed (pip install hypernix)."
menu_available || die "Install fuzzel, wofi or rofi to use this fallback."

choice="$(printf '%s\n' \
	"Open the agent" \
	"Accelerators" \
	"Doctor" \
	"Chat" \
	"Version" | menu_pick "HyperNix")" || exit 0

[[ -n "$choice" ]] || exit 0

terminal="$(halcyon settings get applications.terminal 2>/dev/null || printf 'kitty')"
has "$terminal" || terminal="$(command -v kitty foot alacritty xterm 2>/dev/null | head -n1)"
[[ -n "$terminal" ]] || die "No terminal emulator found."

case "$choice" in
"Open the agent")
	for agent in hyped-pro hyped; do
		if has "$agent"; then exec "$terminal" -e "$agent"; fi
	done
	exec "$terminal" -e "$binary" --help
	;;
Accelerators) exec "$terminal" -e sh -c "$binary devices; read -r _" ;;
Doctor) exec "$terminal" -e sh -c "$binary doctor; read -r _" ;;
Chat) exec "$terminal" -e "$binary" chat ;;
Version) exec "$terminal" -e sh -c "$binary --version; read -r _" ;;
esac
