#!/usr/bin/env bash
# Halcyon — start the session.
#
# What a login manager runs, and what you run from a TTY. It does the
# three things that have to happen before the compositor starts and are
# easy to get wrong:
#
#   1. Put ~/.local/bin on PATH, so the keybinds can find `halcyon`.
#   2. Tell systemd and D-Bus what kind of session this is, so portals,
#      screen sharing and the user units work.
#   3. Regenerate the theme if it has never been generated, so a first
#      login is a finished desktop rather than a plain one.

set -Eeuo pipefail

: "${XDG_CONFIG_HOME:=$HOME/.config}"
: "${XDG_DATA_HOME:=$HOME/.local/share}"
: "${XDG_STATE_HOME:=$HOME/.local/state}"
export XDG_CONFIG_HOME XDG_DATA_HOME XDG_STATE_HOME

case ":$PATH:" in
*":$HOME/.local/bin:"*) ;;
*) PATH="$HOME/.local/bin:$PATH" ;;
esac
export PATH

export XDG_CURRENT_DESKTOP=Hyprland
export XDG_SESSION_DESKTOP=Hyprland
export XDG_SESSION_TYPE=wayland

# A first login with no generated theme would come up plain; generating
# it here is cheaper than a notification telling the user to.
if [[ ! -f "$XDG_CONFIG_HOME/halcyon/generated/theme.json" ]] && command -v halcyon >/dev/null 2>&1; then
	halcyon theme apply --no-reload >/dev/null 2>&1 || true
fi

if command -v systemctl >/dev/null 2>&1; then
	systemctl --user import-environment PATH XDG_CURRENT_DESKTOP \
		XDG_SESSION_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true
fi

exec Hyprland "$@"
