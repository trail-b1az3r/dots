#!/usr/bin/env bash
# Halcyon — a menu that works when the shell does not.
#
# Quickshell owns Spotlight, the power menu and the network picker. When
# it is not running — it crashed, it was never installed, the user is on
# a machine where it would not build — those things still have to be
# reachable. This wraps whichever dmenu-style launcher is present so the
# fallback scripts do not each have to.
#
# shellcheck shell=bash

if [[ -n "${HALCYON_MENU_SH_LOADED:-}" ]]; then
	return 0
fi
HALCYON_MENU_SH_LOADED=1

# shellcheck source=scripts/lib/common.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

menu_backend() {
	local candidate
	for candidate in fuzzel wofi rofi tofi bemenu dmenu-wl dmenu; do
		has "$candidate" && {
			printf '%s' "$candidate"
			return 0
		}
	done
	return 1
}

menu_available() { menu_backend >/dev/null 2>&1; }

# menu_pick <prompt> — read lines on stdin, print the chosen one.
menu_pick() {
	local prompt="${1:-Select}"
	local backend
	backend="$(menu_backend)" || {
		log_error "No launcher found (fuzzel, wofi, rofi, tofi, bemenu or dmenu)."
		return 1
	}

	case "$backend" in
	fuzzel) fuzzel --dmenu --prompt "$prompt: " ;;
	wofi) wofi --dmenu --prompt "$prompt" ;;
	rofi) rofi -dmenu -p "$prompt" ;;
	tofi) tofi --prompt-text "$prompt: " ;;
	bemenu) bemenu -p "$prompt" ;;
	dmenu-wl | dmenu) "$backend" -p "$prompt" ;;
	esac
}

# menu_input <prompt> — like menu_pick, but for free text (passwords).
menu_input() {
	local prompt="${1:-Enter}" hidden="${2:-}"
	local backend
	backend="$(menu_backend)" || return 1

	case "$backend" in
	fuzzel)
		if [[ -n "$hidden" ]]; then
			printf '' | fuzzel --dmenu --password --prompt "$prompt: "
		else
			printf '' | fuzzel --dmenu --prompt "$prompt: "
		fi
		;;
	rofi)
		if [[ -n "$hidden" ]]; then
			rofi -dmenu -password -p "$prompt" </dev/null
		else
			rofi -dmenu -p "$prompt" </dev/null
		fi
		;;
	wofi) printf '' | wofi --dmenu ${hidden:+--password} --prompt "$prompt" ;;
	*) printf '' | menu_pick "$prompt" ;;
	esac
}

# shell_or <target> <function> <fallback-script> [args…]
#
# Ask the Quickshell surface first; run the fallback when it does not
# answer. This is the pattern every Waybar button and keybind uses, and
# the reason a dead shell degrades rather than breaking.
shell_or() {
	local target="$1" function="$2" fallback="$3"
	shift 3

	if has halcyon && halcyon shell "$target" "$function" "$@" >/dev/null 2>&1; then
		return 0
	fi

	if [[ -x "$fallback" ]]; then
		log_debug "Quickshell did not answer; using $fallback"
		exec "$fallback" "$@"
	fi

	log_error "Neither the Halcyon shell nor a fallback for $target is available."
	return 1
}
