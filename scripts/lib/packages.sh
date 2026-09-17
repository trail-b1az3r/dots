#!/usr/bin/env bash
# Halcyon — package map handling and installation.
#
# The maps in deps/*.pkgs are the single source of truth for what a role
# is called on a given distribution. Nothing else in the tree hardcodes a
# package name.
#
# shellcheck shell=bash

if [[ -n "${HALCYON_PACKAGES_SH_LOADED:-}" ]]; then
	return 0
fi
HALCYON_PACKAGES_SH_LOADED=1

# shellcheck source=scripts/lib/detect.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/detect.sh"

pkg_map_file() {
	[[ -n "${HALCYON_FAMILY:-}" ]] || detect_distro
	local f="$HALCYON_REPO_ROOT/deps/${HALCYON_FAMILY}.pkgs"
	[[ -r "$f" ]] || return 1
	printf '%s' "$f"
}

# pkg_for_role <role> — print the packages for a role, or nothing when the
# role has no native package on this distro.
pkg_for_role() {
	local role="$1" map
	map="$(pkg_map_file)" || return 1
	local line key rest
	while IFS= read -r line; do
		[[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
		key="${line%%[[:space:]]*}"
		[[ "$key" == "$role" ]] || continue
		rest="${line#"$key"}"
		# Strip leading whitespace without invoking a subshell.
		rest="${rest#"${rest%%[![:space:]]*}"}"
		[[ "$rest" == "-" ]] && return 1
		printf '%s' "$rest"
		return 0
	done <"$map"
	return 1
}

# _trim — strip leading and trailing whitespace, no subshell.
_trim() {
	local s="$1"
	s="${s#"${s%%[![:space:]]*}"}"
	s="${s%"${s##*[![:space:]]}"}"
	printf '%s' "$s"
}

# roles_list — every role name declared in deps/roles.conf, in order.
roles_list() {
	local line
	while IFS= read -r line; do
		[[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
		[[ "$line" == @* ]] && continue
		printf '%s\n' "$(_trim "${line%%|*}")"
	done <"$HALCYON_REPO_ROOT/deps/roles.conf"
}

# role_field <role> <1=tier|2=probe|3=description>
role_field() {
	local role="$1" idx="$2" line name
	local IFS='|'
	while read -r line; do
		[[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
		name="$(_trim "${line%%|*}")"
		[[ "$name" == "$role" ]] || continue
		local -a fields
		IFS='|' read -r -a fields <<<"$line"
		_trim "${fields[$idx]-}"
		return 0
	done <"$HALCYON_REPO_ROOT/deps/roles.conf"
	return 1
}

# role_satisfied <role> — evaluate the probe from deps/roles.conf.
role_satisfied() {
	local role="$1" probe
	probe="$(role_field "$role" 2)" || return 1
	case "$probe" in
	cmd:*)
		has "${probe#cmd:}"
		;;
	any:*)
		local candidate
		local IFS=','
		for candidate in ${probe#any:}; do
			has "$candidate" && return 0
		done
		return 1
		;;
	lib:*)
		has pkg-config && pkg-config --exists "${probe#lib:}"
		;;
	file:FONT_UI)
		font_installed 'Inter' || font_installed 'SF Pro' || font_installed 'Roboto'
		;;
	file:FONT_MONO)
		font_installed 'JetBrains' || font_installed 'Mono'
		;;
	file:FONT_SYMBOLS)
		font_installed 'Symbols Nerd' || font_installed 'Font Awesome' ||
			font_installed 'Nerd Font'
		;;
	file:*)
		local p="${probe#file:}"
		[[ -e "$p" ]] && return 0
		# Portals move around between distros; accept any known location.
		[[ "$p" == */xdg-desktop-portal-hyprland ]] &&
			{ [[ -e /usr/lib/xdg-desktop-portal-hyprland ]] ||
				[[ -e /usr/lib64/xdg-desktop-portal-hyprland ]] ||
				[[ -e /usr/libexec/xdg-desktop-portal-hyprland ]]; }
		;;
	*)
		return 1
		;;
	esac
}

font_installed() {
	local pattern="$1"
	if has fc-list; then
		fc-list 2>/dev/null | grep -qi -- "$pattern"
		return
	fi
	# fontconfig may not be present during a bare-metal install.
	local dir
	for dir in "$XDG_DATA_HOME/fonts" /usr/share/fonts /usr/local/share/fonts; do
		[[ -d "$dir" ]] || continue
		find "$dir" -iname "*${pattern// /*}*" -print -quit 2>/dev/null |
			grep -q . && return 0
	done
	return 1
}

# ── Installation ───────────────────────────────────────────────────────

# pkg_install <packages…> — install with the detected package manager.
# Names carrying an `aur:` or `copr:` prefix are routed appropriately.
pkg_install() {
	(($# > 0)) || return 0
	[[ -n "${HALCYON_PKG_MANAGER:-}" ]] || detect_package_manager
	local sudo_cmd
	sudo_cmd="$(sudo_prefix)" || die "Need root privileges but neither sudo nor doas is available."

	local native=() aur=() copr=() p
	for p in "$@"; do
		case "$p" in
		aur:*) aur+=("${p#aur:}") ;;
		copr:*) copr+=("${p#copr:}") ;;
		*) native+=("$p") ;;
		esac
	done

	local repo
	for repo in "${copr[@]+"${copr[@]}"}"; do
		log_info "Enabling COPR $repo"
		run $sudo_cmd dnf -y copr enable "$repo"
	done

	if ((${#native[@]} > 0)); then
		case "$HALCYON_PKG_MANAGER" in
		pacman)
			run $sudo_cmd pacman -S --needed --noconfirm "${native[@]}"
			;;
		dnf5 | dnf | yum)
			run $sudo_cmd "$HALCYON_PKG_MANAGER" install -y --skip-unavailable "${native[@]}"
			;;
		apt-get)
			run $sudo_cmd env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${native[@]}"
			;;
		zypper)
			run $sudo_cmd zypper --non-interactive install --no-recommends "${native[@]}"
			;;
		nix-env)
			local attr nixpkgs=()
			for attr in "${native[@]}"; do nixpkgs+=("nixpkgs.$attr"); done
			run nix-env -iA "${nixpkgs[@]}"
			;;
		*)
			log_warn "No supported package manager; install manually: ${native[*]}"
			return 1
			;;
		esac
	fi

	if ((${#aur[@]} > 0)); then
		if [[ -n "${HALCYON_AUR_HELPER:-}" ]]; then
			run "$HALCYON_AUR_HELPER" -S --needed --noconfirm "${aur[@]}"
		else
			log_warn "No AUR helper found; these need manual installation: ${aur[*]}"
			return 1
		fi
	fi
}

pkg_refresh() {
	[[ -n "${HALCYON_PKG_MANAGER:-}" ]] || detect_package_manager
	local sudo_cmd
	sudo_cmd="$(sudo_prefix)" || return 1
	case "$HALCYON_PKG_MANAGER" in
	pacman) run $sudo_cmd pacman -Sy --noconfirm ;;
	apt-get) run $sudo_cmd apt-get update -qq ;;
	dnf5 | dnf | yum) run $sudo_cmd "$HALCYON_PKG_MANAGER" makecache -q ;;
	zypper) run $sudo_cmd zypper --non-interactive refresh ;;
	nix-env) run nix-channel --update ;;
	esac
}

# pkg_group <@name> — packages for a build group such as @build.
pkg_group() { pkg_for_role "$1"; }
