#!/usr/bin/env bash
#
# Halcyon — what is installed, what is missing, and how to get it.
#
#   ./check-deps.sh            everything, grouped by how badly it is needed
#   ./check-deps.sh --core     only what the desktop cannot start without
#   ./check-deps.sh --install  install what is missing
#   ./check-deps.sh --json     machine-readable
#
# Every check is a real probe — a binary on PATH, a library pkg-config
# knows about, a font fontconfig can see — not a package-manager query.
# A dependency satisfied by a source build, a Flatpak or a Nix profile
# counts, because it works.

set -Eeuo pipefail

HALCYON_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export HALCYON_REPO_ROOT

# shellcheck source=scripts/lib/packages.sh
. "$HALCYON_REPO_ROOT/scripts/lib/packages.sh"

SHOW_TIERS="core shell extra ai"
DO_INSTALL=0
AS_JSON=0

usage() {
	cat <<'USAGE'
Halcyon — dependency check.

Usage: ./check-deps.sh [options]

      --core       Only what the desktop cannot start without.
      --required   Core and shell tiers (the default for --install).
      --ai         Only the AI assistant's dependencies.
      --install    Install whatever is missing.
      --json       Machine-readable output.
  -h, --help       This message.

Tiers
  core    the desktop will not start without it
  shell   a major surface degrades, but the desktop still works
  extra   optional polish
  ai      only needed for the local assistant
USAGE
}

while (($# > 0)); do
	case "$1" in
	--core) SHOW_TIERS="core" ;;
	--required) SHOW_TIERS="core shell" ;;
	--ai) SHOW_TIERS="ai" ;;
	--install) DO_INSTALL=1 ;;
	--json) AS_JSON=1 ;;
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

detect_distro
detect_package_manager

declare -A TIER_LABEL=(
	[core]="Required"
	[shell]="Recommended"
	[extra]="Optional"
	[ai]="AI assistant"
)

declare -A TIER_NOTE=(
	[core]="the desktop will not start without these"
	[shell]="a surface degrades without them; the desktop still works"
	[extra]="polish"
	[ai]="only for the local assistant backend"
)

collect() {
	local role tier ok packages
	while read -r role; do
		[[ -n "$role" ]] || continue
		tier="$(role_field "$role" 1)"
		case " $SHOW_TIERS " in *" $tier "*) ;; *) continue ;; esac

		if role_satisfied "$role"; then ok=1; else ok=0; fi
		packages="$(pkg_for_role "$role" 2>/dev/null || printf -- '-')"
		printf '%s\t%s\t%s\t%s\t%s\n' \
			"$role" "$tier" "$ok" "$(role_field "$role" 3)" "$packages"
	done < <(roles_list)
}

report_text() {
	local total=0 present=0
	local -a missing=()

	printf '\n  %s\n' "${C_BOLD}Halcyon dependencies${C_RESET}"
	printf '  %s\n\n' "${C_DIM}${HALCYON_DISTRO_NAME} · ${HALCYON_PKG_MANAGER:-no package manager found}${C_RESET}"

	local tier
	for tier in core shell extra ai; do
		case " $SHOW_TIERS " in *" $tier "*) ;; *) continue ;; esac

		local shown=0
		local role role_tier ok description packages
		while IFS=$'\t' read -r role role_tier ok description packages; do
			[[ "$role_tier" == "$tier" ]] || continue
			if ((shown == 0)); then
				printf '  %s %s\n' "${C_BOLD}${TIER_LABEL[$tier]}${C_RESET}" \
					"${C_DIM}— ${TIER_NOTE[$tier]}${C_RESET}"
				shown=1
			fi
			total=$((total + 1))
			if ((ok)); then
				present=$((present + 1))
				printf '    %s %-15s %s\n' "${C_GREEN}✓${C_RESET}" "$role" \
					"${C_DIM}${description}${C_RESET}"
			else
				missing+=("$role")
				printf '    %s %-15s %s\n' "${C_RED}✗${C_RESET}" "$role" "$description"
				if [[ "$packages" == "-" ]]; then
					printf '      %s\n' "${C_DIM}no package on ${HALCYON_FAMILY}; built from source or installed by hand${C_RESET}"
				else
					printf '      %s\n' "${C_DIM}${HALCYON_PKG_MANAGER:-install}: ${packages}${C_RESET}"
				fi
			fi
		done < <(collect)
		((shown)) && printf '\n'
	done

	printf '  %s of %s present.\n' "$present" "$total"

	if ((${#missing[@]} > 0)); then
		printf '\n  Install the missing ones with:\n'
		printf '    %s\n\n' "${C_BOLD}./check-deps.sh --install${C_RESET}"
	else
		printf '\n  %s\n\n' "${C_GREEN}Nothing is missing.${C_RESET}"
	fi

	# A conflict is worse than a missing package: two power daemons will
	# fight, and the symptom is a laptop that behaves differently every
	# time it wakes up.
	detect_power_backend
	if [[ -n "$HALCYON_POWER_CONFLICTS" ]]; then
		printf '  %s More than one power daemon is running: %s\n' \
			"${C_YELLOW}!${C_RESET}" "$HALCYON_POWER_CONFLICTS"
		printf '    They fight over the CPU governor. Keep one and disable the rest.\n\n'
	fi

	((${#missing[@]} == 0))
}

report_json() {
	printf '{\n  "distro": "%s",\n  "family": "%s",\n  "packageManager": "%s",\n  "roles": [\n' \
		"$HALCYON_DISTRO_ID" "$HALCYON_FAMILY" "${HALCYON_PKG_MANAGER:-}"

	local first=1 role tier ok description packages
	while IFS=$'\t' read -r role tier ok description packages; do
		((first)) || printf ',\n'
		first=0
		printf '    {"role": "%s", "tier": "%s", "satisfied": %s, "description": "%s", "packages": "%s"}' \
			"$role" "$tier" "$([[ "$ok" == 1 ]] && echo true || echo false)" \
			"$description" "$packages"
	done < <(collect)

	printf '\n  ]\n}\n'
}

install_missing() {
	local -a wanted=() split=()
	local role tier ok description packages

	while IFS=$'\t' read -r role tier ok description packages; do
		((ok)) && continue
		[[ "$packages" == "-" ]] && continue
		read -r -a split <<<"$packages"
		wanted+=("${split[@]}")
	done < <(collect)

	if ((${#wanted[@]} == 0)); then
		log_ok "Nothing to install."
		return 0
	fi

	local -a unique=()
	local package seen=""
	for package in "${wanted[@]}"; do
		case " $seen " in *" $package "*) continue ;; esac
		seen+=" $package"
		unique+=("$package")
	done

	log_info "Installing: ${unique[*]}"
	pkg_install "${unique[@]}"
}

if ((AS_JSON)); then
	report_json
	exit 0
fi

if ((DO_INSTALL)); then
	install_missing
	printf '\n'
fi

report_text || exit 1
