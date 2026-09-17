#!/usr/bin/env bash
#
# Halcyon — uninstall.
#
#   ./uninstall.sh              remove Halcyon, restore the newest backup
#   ./uninstall.sh --keep-config  leave settings.json and your wallpapers
#   ./uninstall.sh --no-restore   remove without restoring anything
#   ./uninstall.sh --dry-run      show what would be removed
#
# Uninstalling is the other half of installing: what was backed up on the
# way in is put back on the way out, so a machine that had a working
# Hyprland setup before Halcyon has it again afterwards.

set -Eeuo pipefail

HALCYON_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export HALCYON_REPO_ROOT

# shellcheck source=scripts/lib/backup.sh
. "$HALCYON_REPO_ROOT/scripts/lib/backup.sh"

KEEP_CONFIG=0
RESTORE=1
REMOVE_BACKUPS=0

usage() {
	cat <<'USAGE'
Halcyon — uninstall.

Usage: ./uninstall.sh [options]

  -n, --dry-run        Show what would be removed without removing it.
  -y, --yes            Do not prompt; assume yes.
      --keep-config    Keep ~/.config/halcyon (settings, generated files).
      --no-restore     Do not restore the pre-Halcyon configuration.
      --purge          Also delete the backups themselves. Cannot be undone.
  -h, --help           This message.
USAGE
}

while (($# > 0)); do
	case "$1" in
	-n | --dry-run) HALCYON_DRY_RUN=1 ;;
	-y | --yes) HALCYON_ASSUME_YES=1 ;;
	--keep-config) KEEP_CONFIG=1 ;;
	--no-restore) RESTORE=0 ;;
	--purge) REMOVE_BACKUPS=1 ;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		log_error "Unknown option: $1"
		usage
		exit 2
		;;
	esac
	shift
done

export HALCYON_DRY_RUN HALCYON_ASSUME_YES

BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HALCYON_DATA_DIR"
QS_CONFIG_DIR="$XDG_CONFIG_HOME/quickshell/halcyon"
HYPR_CONFIG_DIR="$XDG_CONFIG_HOME/hypr"
WAYBAR_CONFIG_DIR="$XDG_CONFIG_HOME/waybar"
SYSTEMD_DIR="$XDG_CONFIG_HOME/systemd/user"

stop_services() {
	has systemctl || return 0
	log_step "Stopping services"

	local unit
	for unit in "$SYSTEMD_DIR"/halcyon-*.service; do
		[[ -e "$unit" ]] || continue
		unit="$(basename "$unit")"
		run systemctl --user disable --now "$unit" 2>/dev/null || true
	done
	run systemctl --user daemon-reload 2>/dev/null || true
}

stop_processes() {
	log_step "Stopping what is running"

	if has qs; then
		run qs -c halcyon kill 2>/dev/null || true
	elif has quickshell; then
		run quickshell -c halcyon kill 2>/dev/null || true
	fi

	if [[ -x "$BIN_DIR/halcyon" ]]; then
		run "$BIN_DIR/halcyon" assistant stop 2>/dev/null || true
	fi
}

remove_files() {
	log_step "Removing Halcyon"

	local -a targets=(
		"$BIN_DIR/halcyon"
		"$SHARE_DIR"
		"$QS_CONFIG_DIR"
		"$HYPR_CONFIG_DIR/halcyon"
		"$HYPR_CONFIG_DIR/hyprland.lua"
		"$HYPR_CONFIG_DIR/hyprlock.conf"
		"$HYPR_CONFIG_DIR/hypridle.conf"
		"$WAYBAR_CONFIG_DIR/style.css"
		"$WAYBAR_CONFIG_DIR/modules.jsonc"
		"$HALCYON_CACHE_DIR"
	)

	((KEEP_CONFIG)) || targets+=("$HALCYON_CONFIG_DIR")

	local unit
	for unit in "$SYSTEMD_DIR"/halcyon-*.service "$SYSTEMD_DIR"/halcyon-*.target; do
		[[ -e "$unit" ]] && targets+=("$unit")
	done

	local target removed=0
	for target in "${targets[@]}"; do
		[[ -e "$target" || -L "$target" ]] || continue
		if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
			printf '%s\n' "${C_DIM}   would remove:${C_RESET} $target"
		else
			rm -rf -- "$target"
			log_debug "removed $target"
		fi
		removed=$((removed + 1))
	done

	log_ok "Removed $removed path(s)"

	# local.lua is the user's own file, never ours to delete.
	if [[ -f "$HYPR_CONFIG_DIR/local.lua" ]]; then
		log_info "Left $HYPR_CONFIG_DIR/local.lua alone — it is yours."
	fi

	# The session entry needs root, and may not be ours to remove.
	local session_entry="/usr/share/wayland-sessions/halcyon.desktop"
	if [[ -e "$session_entry" ]]; then
		local sudo_cmd
		if sudo_cmd="$(sudo_prefix)"; then
			run $sudo_cmd rm -f "$session_entry" || true
		else
			log_info "Remove $session_entry by hand (needs root)."
		fi
	fi
}

restore_previous() {
	((RESTORE)) || return 0

	local latest="$HALCYON_BACKUP_DIR/latest"
	if [[ ! -e "$latest" ]]; then
		log_info "No backup to restore — nothing was there before Halcyon."
		return 0
	fi

	log_step "Restoring what was there before"
	log_info "From $(readlink -f "$latest")"

	# The newest backup is the state just before the *last* install, which
	# is Halcyon's own files. The first backup is the one holding the
	# user's original configuration.
	local oldest
	oldest="$(backup_list | tail -n1)"
	if [[ -n "$oldest" ]]; then
		log_info "Using the oldest backup ($oldest) — that is the one from before"
		log_info "Halcyon was first installed."
		backup_restore "$HALCYON_BACKUP_DIR/$oldest"
	else
		backup_restore "$(readlink -f "$latest")"
	fi
}

purge_backups() {
	((REMOVE_BACKUPS)) || return 0
	log_step "Deleting backups"
	log_warn "This cannot be undone."
	confirm "Delete every backup in $HALCYON_BACKUP_DIR?" || return 0
	run rm -rf -- "$HALCYON_BACKUP_DIR"
}

main() {
	printf '\n  %s\n\n' "${C_BOLD}Uninstalling Halcyon${C_RESET}"

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "${C_BOLD}Dry run — nothing will be changed.${C_RESET}"
	else
		cat <<PLAN
  This will remove:
    $BIN_DIR/halcyon
    $SHARE_DIR
    $QS_CONFIG_DIR
    $HYPR_CONFIG_DIR/{hyprland.lua,halcyon,hyprlock.conf,hypridle.conf}
    $WAYBAR_CONFIG_DIR/{style.css,modules.jsonc}
PLAN
		((KEEP_CONFIG)) || printf '    %s\n' "$HALCYON_CONFIG_DIR"
		printf '\n'
		confirm "Continue?" || {
			log_info "Nothing was changed."
			exit 0
		}
	fi

	stop_services
	stop_processes
	remove_files
	restore_previous
	purge_backups

	printf '\n  %s\n\n' "${C_GREEN}Halcyon has been removed.${C_RESET}"
	((KEEP_CONFIG)) && printf '  Your settings are still in %s\n\n' "$HALCYON_CONFIG_DIR"
	if [[ -d "$HALCYON_BACKUP_DIR" ]] && ((!REMOVE_BACKUPS)); then
		printf '  Backups are still in %s\n' "$HALCYON_BACKUP_DIR"
		printf '  Delete them with: ./uninstall.sh --purge\n\n'
	fi
}

main "$@"
