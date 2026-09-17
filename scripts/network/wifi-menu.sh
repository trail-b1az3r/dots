#!/usr/bin/env bash
# Halcyon — pick a Wi-Fi network without the shell.
#
# Control Center's network list is the normal way in. This is the same
# thing through nmcli and a dmenu-style launcher, for when Quickshell is
# not running.

set -Eeuo pipefail
# shellcheck source=scripts/lib/menu.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/menu.sh"

has nmcli || die "nmcli is not installed."
menu_available || die "Install fuzzel, wofi or rofi to use this fallback."

case "${1:-list}" in
toggle)
	if [[ "$(nmcli -t radio wifi)" == "enabled" ]]; then
		exec nmcli radio wifi off
	fi
	exec nmcli radio wifi on
	;;
esac

if [[ "$(nmcli -t radio wifi)" != "enabled" ]]; then
	if [[ "$(printf 'Turn Wi-Fi on\nCancel' | menu_pick 'Wi-Fi is off')" == "Turn Wi-Fi on" ]]; then
		nmcli radio wifi on
		sleep 2
	else
		exit 0
	fi
fi

nmcli device wifi rescan >/dev/null 2>&1 || true

# SSID, signal and security, with the connected one marked. Sorted by
# signal, and de-duplicated: the same network on three access points is
# one entry to a person.
choice="$(
	nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list |
		awk -F: '
			$2 == "" { next }
			!seen[$2]++ {
				mark = ($1 == "*") ? "● " : "  "
				security = ($4 == "" || $4 == "--") ? "open" : $4
				printf "%s%s\t%s%%\t%s\n", mark, $2, $3, security
			}
		' |
		sort -t$'\t' -k2 -rn |
		menu_pick "Wi-Fi"
)" || exit 0

[[ -n "$choice" ]] || exit 0
ssid="$(printf '%s' "$choice" | cut -f1 | sed 's/^[●[:space:]]*//')"
[[ -n "$ssid" ]] || exit 0

# A known network connects without asking; a new secured one needs the
# password, and nmcli is the thing that knows which is which.
if nmcli -t -f NAME connection show | grep -qxF "$ssid"; then
	exec nmcli connection up id "$ssid"
fi

security="$(printf '%s' "$choice" | cut -f3)"
if [[ "$security" == "open" ]]; then
	exec nmcli device wifi connect "$ssid"
fi

password="$(menu_input "Password for $ssid" hidden)" || exit 0
[[ -n "$password" ]] || exit 0
exec nmcli device wifi connect "$ssid" password "$password"
