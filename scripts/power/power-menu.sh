#!/usr/bin/env bash
# Halcyon — the power menu, without the shell.
#
# Anything that ends a session asks twice: once to choose it, once to
# confirm. There is no undo for "shut down" with unsaved work open.

set -Eeuo pipefail
# shellcheck source=scripts/lib/menu.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/menu.sh"

menu_available || die "Install fuzzel, wofi or rofi to use this fallback."

choice="$(printf '%s\n' \
	"Lock" \
	"Sleep" \
	"Log out" \
	"Restart" \
	"Shut down" | menu_pick "Power")" || exit 0

[[ -n "$choice" ]] || exit 0

confirm_destructive() {
	local answer
	answer="$(printf 'Cancel\n%s' "$1" | menu_pick "$1?")" || return 1
	[[ "$answer" == "$1" ]]
}

case "$choice" in
Lock) exec halcyon session lock ;;
Sleep)
	confirm_destructive "Sleep" || exit 0
	exec halcyon session suspend
	;;
"Log out")
	confirm_destructive "Log out" || exit 0
	exec halcyon session logout
	;;
Restart)
	confirm_destructive "Restart" || exit 0
	exec halcyon session reboot
	;;
"Shut down")
	confirm_destructive "Shut down" || exit 0
	exec halcyon session shutdown
	;;
esac
