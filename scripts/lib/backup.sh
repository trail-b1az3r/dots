#!/usr/bin/env bash
# Halcyon — backup, install and restore of configuration files.
#
# The contract this file implements:
#   * Nothing is ever overwritten without a copy landing in a timestamped
#     backup directory first.
#   * Every backup records a manifest, so restore.sh can put files back
#     exactly where they came from without guessing.
#   * Installing the same version twice is a no-op, not a second backup.
#
# shellcheck shell=bash

if [[ -n "${HALCYON_BACKUP_SH_LOADED:-}" ]]; then
	return 0
fi
HALCYON_BACKUP_SH_LOADED=1

# shellcheck source=scripts/lib/common.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

# Set by backup_begin; consumed by backup_path and backup_finish.
HALCYON_CURRENT_BACKUP=''

backup_begin() {
	local stamp
	stamp="$(timestamp)"
	HALCYON_CURRENT_BACKUP="$HALCYON_BACKUP_DIR/$stamp"
	ensure_dir "$HALCYON_CURRENT_BACKUP"
	if [[ -z "${HALCYON_DRY_RUN:-}" ]]; then
		{
			printf 'halcyon-backup 1\n'
			printf 'created %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
			printf 'host %s\n' "$(uname -n)"
		} >"$HALCYON_CURRENT_BACKUP/manifest"
	fi
	export HALCYON_CURRENT_BACKUP
	log_info "Backups for this run go to ${C_DIM}$HALCYON_CURRENT_BACKUP${C_RESET}"
}

# backup_path <path> — copy an existing path into the current backup and
# record where it came from. Missing paths are recorded as "absent" so
# restore can delete what we created rather than leaving litter behind.
backup_path() {
	local src="$1"
	[[ -n "$HALCYON_CURRENT_BACKUP" ]] || backup_begin

	# Flatten the absolute path into a single file name so two configs
	# with the same basename cannot collide inside one backup.
	local key="${src#"$HOME"/}"
	key="${key//\//__}"
	local dest="$HALCYON_CURRENT_BACKUP/files/$key"

	if [[ ! -e "$src" && ! -L "$src" ]]; then
		if [[ -z "${HALCYON_DRY_RUN:-}" ]]; then
			printf 'absent\t%s\n' "$src" >>"$HALCYON_CURRENT_BACKUP/manifest"
		fi
		return 0
	fi

	ensure_dir "$HALCYON_CURRENT_BACKUP/files"
	if [[ -z "${HALCYON_DRY_RUN:-}" ]]; then
		cp -a -- "$src" "$dest"
		printf 'saved\t%s\t%s\n' "$src" "files/$key" >>"$HALCYON_CURRENT_BACKUP/manifest"
	else
		printf '%s\n' "${C_DIM}   would back up:${C_RESET} $src"
	fi
	log_debug "backed up $src"
}

backup_finish() {
	[[ -n "$HALCYON_CURRENT_BACKUP" ]] || return 0
	[[ -n "${HALCYON_DRY_RUN:-}" ]] && return 0
	# A pointer to the newest backup makes restore.sh's default obvious.
	ln -sfn "$HALCYON_CURRENT_BACKUP" "$HALCYON_BACKUP_DIR/latest"
	log_ok "Backup complete: $HALCYON_CURRENT_BACKUP"
}

# install_tree <src-dir> <dest-dir>
#
# Mirrors a directory from the repository into the user's config, backing
# up anything already there. Idempotent: identical trees are skipped.
install_tree() {
	local src="$1" dest="$2"
	[[ -d "$src" ]] || die "install_tree: missing source $src"

	if [[ -e "$dest" ]] && trees_identical "$src" "$dest"; then
		log_debug "unchanged: $dest"
		return 0
	fi

	backup_path "$dest"
	ensure_dir "$dest"
	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		printf '%s\n' "${C_DIM}   would install:${C_RESET} $src -> $dest"
		return 0
	fi
	# -a keeps modes; --delete would be wrong here because the user may
	# legitimately add files of their own next to ours.
	if has rsync; then
		rsync -a --exclude '.git' "$src/" "$dest/"
	else
		cp -a "$src/." "$dest/"
	fi
	# Show the path relative to $HOME: two different trees can share a
	# basename ("halcyon" is both a library and a config directory), and
	# "Installed halcyon" twice tells the user nothing.
	log_ok "Installed ${dest/#$HOME/~}"
}

# install_file <src> <dest> [mode]
install_file() {
	local src="$1" dest="$2" mode="${3:-0644}"
	[[ -f "$src" ]] || die "install_file: missing source $src"

	if [[ -f "$dest" ]] && cmp -s "$src" "$dest"; then
		log_debug "unchanged: $dest"
		return 0
	fi
	backup_path "$dest"
	ensure_dir "$(dirname "$dest")"
	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		printf '%s\n' "${C_DIM}   would install:${C_RESET} $dest"
		return 0
	fi
	install -m "$mode" "$src" "$dest"
}

trees_identical() {
	local a="$1" b="$2"
	[[ -d "$a" && -d "$b" ]] || return 1
	if has diff; then
		diff -rq --exclude='.git' "$a" "$b" >/dev/null 2>&1
	else
		return 1
	fi
}

# backup_list — newest first.
backup_list() {
	[[ -d "$HALCYON_BACKUP_DIR" ]] || return 0
	find "$HALCYON_BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' 2>/dev/null |
		sort -r
}

# backup_restore <backup-dir> — put every saved file back and remove the
# files that did not exist when the backup was taken.
backup_restore() {
	local dir="$1"
	[[ -f "$dir/manifest" ]] || die "Not a Halcyon backup: $dir"

	local state src rel restored=0 removed=0
	while IFS=$'\t' read -r state src rel; do
		case "$state" in
		saved)
			[[ -n "$src" && -n "$rel" ]] || continue
			[[ -e "$dir/$rel" ]] || {
				log_warn "Backup is missing $rel; skipping $src"
				continue
			}
			run rm -rf -- "$src"
			ensure_dir "$(dirname "$src")"
			run cp -a -- "$dir/$rel" "$src"
			restored=$((restored + 1))
			;;
		absent)
			[[ -n "$src" ]] || continue
			if [[ -e "$src" || -L "$src" ]]; then
				run rm -rf -- "$src"
				removed=$((removed + 1))
			fi
			;;
		esac
	done <"$dir/manifest"

	log_ok "Restored $restored path(s), removed $removed path(s) that did not exist before."
}
