#!/usr/bin/env bash
#
# Halcyon — restore a backup.
#
#   ./restore.sh              list the backups
#   ./restore.sh latest       restore the most recent
#   ./restore.sh 20260917-1204  restore a specific one
#   ./restore.sh --dry-run latest
#
# Every install writes a manifest recording where each file came from and
# which paths did not exist yet. Restoring replays that manifest exactly:
# saved files go back where they were, and anything Halcyon created that
# was not there before is removed.

set -Eeuo pipefail

HALCYON_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export HALCYON_REPO_ROOT

# shellcheck source=scripts/lib/backup.sh
. "$HALCYON_REPO_ROOT/scripts/lib/backup.sh"

TARGET=""

usage() {
	cat <<'USAGE'
Halcyon — restore a backup.

Usage: ./restore.sh [options] [backup]

  backup               A timestamp from the list, or "latest", or "oldest".
                       Omit to list what is available.

  -n, --dry-run        Show what would be restored without doing it.
  -y, --yes            Do not prompt; assume yes.
  -l, --list           List the backups and exit.
  -s, --show BACKUP    Print what a backup contains.
  -h, --help           This message.
USAGE
}

SHOW=""

while (($# > 0)); do
	case "$1" in
	-n | --dry-run) HALCYON_DRY_RUN=1 ;;
	-y | --yes) HALCYON_ASSUME_YES=1 ;;
	-l | --list) TARGET="" ;;
	-s | --show)
		shift
		SHOW="${1:?--show needs a backup name}"
		;;
	-h | --help)
		usage
		exit 0
		;;
	-*)
		log_error "Unknown option: $1"
		usage
		exit 2
		;;
	*) TARGET="$1" ;;
	esac
	shift
done

export HALCYON_DRY_RUN HALCYON_ASSUME_YES

# manifest_count <dir> <state> — how many lines of that kind.
#
# awk rather than `grep -c`, which exits 1 when it counts zero and turns
# a `|| echo 0` fallback into two zeroes on one line.
manifest_count() {
	awk -v want="$2" '$1 == want {n++} END {print n + 0}' "$1/manifest" 2>/dev/null
}

resolve() {
	local name="$1"
	case "$name" in
	latest) backup_list | head -n1 ;;
	oldest) backup_list | tail -n1 ;;
	*) printf '%s' "$name" ;;
	esac
}

list_backups() {
	local -a names=()
	local name
	while IFS= read -r name; do
		[[ -n "$name" ]] && names+=("$name")
	done < <(backup_list)

	if ((${#names[@]} == 0)); then
		log_info "No backups in $HALCYON_BACKUP_DIR"
		log_info "They are created the first time ./install.sh runs."
		return 1
	fi

	printf '\n  %s\n\n' "${C_BOLD}Backups${C_RESET}"
	local index=0 dir saved absent created marker
	for name in "${names[@]}"; do
		dir="$HALCYON_BACKUP_DIR/$name"
		saved="$(manifest_count "$dir" saved)"
		absent="$(manifest_count "$dir" absent)"
		created="$(awk '/^created /{print $2}' "$dir/manifest" 2>/dev/null)"
		index=$((index + 1))

		marker=""
		((index == 1)) && marker="  ← newest"
		((index == ${#names[@]} && ${#names[@]} > 1)) && marker="  ← before Halcyon"

		printf '   %s%-18s%s %s%s\n' \
			"$C_BOLD" "$name" "$C_RESET" "${C_DIM}${created}${C_RESET}" "$marker"
		printf '   %-18s %s\n\n' "" \
			"${C_DIM}${saved} file(s) saved · ${absent} path(s) absent at the time${C_RESET}"
	done

	printf '  Restore one with: %s\n\n' "${C_BOLD}./restore.sh <name>${C_RESET}"
	printf '  The %s backup is the one from before Halcyon was first installed.\n\n' \
		"${C_BOLD}oldest${C_RESET}"
}

show_backup() {
	local name dir
	name="$(resolve "$SHOW")"
	dir="$HALCYON_BACKUP_DIR/$name"
	[[ -f "$dir/manifest" ]] || die "No backup called $name"

	printf '\n  %s\n\n' "${C_BOLD}$name${C_RESET}"
	local state path rel
	while IFS=$'\t' read -r state path rel; do
		case "$state" in
		saved) printf '   %s %s\n' "${C_GREEN}restore${C_RESET}" "$path" ;;
		absent) printf '   %s %s\n' "${C_YELLOW}remove ${C_RESET}" "$path" ;;
		esac
	done <"$dir/manifest"
	printf '\n'
}

main() {
	if [[ -n "$SHOW" ]]; then
		show_backup
		exit 0
	fi

	if [[ -z "$TARGET" ]]; then
		list_backups || exit 1
		exit 0
	fi

	local name dir
	name="$(resolve "$TARGET")"
	dir="$HALCYON_BACKUP_DIR/$name"

	[[ -f "$dir/manifest" ]] || {
		log_error "No backup called $name"
		list_backups || true
		exit 1
	}

	printf '\n  %s\n\n' "${C_BOLD}Restoring $name${C_RESET}"

	local saved absent
	saved="$(manifest_count "$dir" saved)"
	absent="$(manifest_count "$dir" absent)"
	printf '  %s file(s) will be put back.\n' "$saved"
	printf '  %s path(s) that did not exist then will be removed.\n\n' "$absent"
	printf '  See exactly what changes with: ./restore.sh --show %s\n\n' "$name"

	if [[ -z "${HALCYON_DRY_RUN:-}" ]]; then
		confirm "This overwrites your current configuration. Continue?" || {
			log_info "Nothing was changed."
			exit 0
		}
	fi

	backup_restore "$dir"

	printf '\n  %s\n' "${C_GREEN}Restored.${C_RESET}"
	printf '  Log out and back in, or run: hyprctl reload\n\n'
}

main "$@"
