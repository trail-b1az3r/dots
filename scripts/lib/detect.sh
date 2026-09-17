#!/usr/bin/env bash
# Halcyon — environment detection.
#
# Everything the installer, the dependency checker and the diagnostics
# script need to know about the machine, in one place so the three of them
# cannot disagree with each other.
#
# shellcheck shell=bash

if [[ -n "${HALCYON_DETECT_SH_LOADED:-}" ]]; then
	return 0
fi
HALCYON_DETECT_SH_LOADED=1

# shellcheck source=scripts/lib/common.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

# ── Distribution ───────────────────────────────────────────────────────

# Sets: HALCYON_DISTRO_ID, HALCYON_DISTRO_LIKE, HALCYON_DISTRO_NAME,
#       HALCYON_DISTRO_VERSION, HALCYON_FAMILY
#
# HALCYON_FAMILY is the coarse bucket the package maps are keyed on:
# arch | fedora | debian | nixos | unknown
detect_distro() {
	local id='' like='' name='' version=''

	if [[ -r /etc/os-release ]]; then
		# os-release is shell-compatible by specification.
		# shellcheck disable=SC1091
		. /etc/os-release
		id="${ID:-}"
		like="${ID_LIKE:-}"
		name="${PRETTY_NAME:-${NAME:-}}"
		version="${VERSION_ID:-}"
	fi

	HALCYON_DISTRO_ID="${id:-unknown}"
	HALCYON_DISTRO_LIKE="$like"
	HALCYON_DISTRO_NAME="${name:-unknown}"
	HALCYON_DISTRO_VERSION="$version"

	case "$id" in
	arch | archarm | endeavouros | manjaro | cachyos | garuda | artix)
		HALCYON_FAMILY=arch
		;;
	fedora | rhel | centos | rocky | almalinux | nobara | bazzite)
		HALCYON_FAMILY=fedora
		;;
	debian | ubuntu | pop | linuxmint | elementary | zorin | raspbian | kali)
		HALCYON_FAMILY=debian
		;;
	nixos)
		HALCYON_FAMILY=nixos
		;;
	opensuse* | sles)
		HALCYON_FAMILY=suse
		;;
	*)
		# Fall back to ID_LIKE, which is a space-separated list.
		case " $like " in
		*" arch "*) HALCYON_FAMILY=arch ;;
		*" fedora "* | *" rhel "*) HALCYON_FAMILY=fedora ;;
		*" debian "* | *" ubuntu "*) HALCYON_FAMILY=debian ;;
		*" suse "*) HALCYON_FAMILY=suse ;;
		*) HALCYON_FAMILY=unknown ;;
		esac
		;;
	esac

	export HALCYON_DISTRO_ID HALCYON_DISTRO_LIKE HALCYON_DISTRO_NAME
	export HALCYON_DISTRO_VERSION HALCYON_FAMILY
}

# Sets HALCYON_PKG_MANAGER to the tool that installs system packages.
# Prefers the native manager; on Arch an AUR helper is recorded separately
# in HALCYON_AUR_HELPER because several dependencies only exist in the AUR.
detect_package_manager() {
	[[ -n "${HALCYON_FAMILY:-}" ]] || detect_distro

	HALCYON_PKG_MANAGER=''
	HALCYON_AUR_HELPER=''

	case "$HALCYON_FAMILY" in
	arch)
		has pacman && HALCYON_PKG_MANAGER=pacman
		local helper
		for helper in paru yay pikaur aura; do
			if has "$helper"; then
				HALCYON_AUR_HELPER="$helper"
				break
			fi
		done
		;;
	fedora)
		if has dnf5; then
			HALCYON_PKG_MANAGER=dnf5
		elif has dnf; then
			HALCYON_PKG_MANAGER=dnf
		elif has yum; then
			HALCYON_PKG_MANAGER=yum
		fi
		;;
	debian)
		has apt-get && HALCYON_PKG_MANAGER=apt-get
		;;
	nixos)
		has nix-env && HALCYON_PKG_MANAGER=nix-env
		;;
	suse)
		has zypper && HALCYON_PKG_MANAGER=zypper
		;;
	esac

	# Last resort: whatever is actually on PATH.
	if [[ -z "$HALCYON_PKG_MANAGER" ]]; then
		local pm
		for pm in pacman dnf5 dnf apt-get zypper nix-env; do
			if has "$pm"; then
				HALCYON_PKG_MANAGER="$pm"
				break
			fi
		done
	fi

	export HALCYON_PKG_MANAGER HALCYON_AUR_HELPER
}

detect_arch() {
	HALCYON_ARCH="$(uname -m)"
	case "$HALCYON_ARCH" in
	x86_64 | amd64) HALCYON_ARCH_FAMILY=x86_64 ;;
	aarch64 | arm64) HALCYON_ARCH_FAMILY=aarch64 ;;
	*) HALCYON_ARCH_FAMILY="$HALCYON_ARCH" ;;
	esac
	export HALCYON_ARCH HALCYON_ARCH_FAMILY
}

# ── Graphics ───────────────────────────────────────────────────────────

# Sets HALCYON_GPU_VENDORS (space separated subset of "intel amd nvidia
# virtio other") and HALCYON_GPU_PRIMARY.
#
# Reads sysfs first because it works without pciutils installed, which is
# common on a minimal install — the very situation the installer runs in.
detect_gpu() {
	local vendors='' card vendor_id

	for card in /sys/class/drm/card[0-9]*; do
		[[ -e "$card/device/vendor" ]] || continue
		vendor_id="$(cat "$card/device/vendor" 2>/dev/null || true)"
		case "$vendor_id" in
		0x8086) vendors+=' intel' ;;
		0x1002 | 0x1022) vendors+=' amd' ;;
		0x10de) vendors+=' nvidia' ;;
		0x1af4 | 0x1b36) vendors+=' virtio' ;;
		'') ;;
		*) vendors+=' other' ;;
		esac
	done

	# Fall back to lspci when sysfs told us nothing (containers, odd setups).
	if [[ -z "$vendors" ]] && has lspci; then
		local line
		while IFS= read -r line; do
			case "${line,,}" in
			*intel*) vendors+=' intel' ;;
			*"advanced micro devices"* | *amd*ati* | *radeon*) vendors+=' amd' ;;
			*nvidia*) vendors+=' nvidia' ;;
			*virtio* | *"red hat"*) vendors+=' virtio' ;;
			esac
		done < <(lspci 2>/dev/null | grep -Ei 'vga|3d controller|display')
	fi

	# De-duplicate while preserving order.
	local seen='' v
	HALCYON_GPU_VENDORS=''
	for v in $vendors; do
		case " $seen " in *" $v "*) continue ;; esac
		seen+=" $v"
		HALCYON_GPU_VENDORS+="${HALCYON_GPU_VENDORS:+ }$v"
	done

	# NVIDIA needs the most special-casing, so it wins the "primary" slot
	# when present; otherwise take the first discovered vendor.
	if [[ " $HALCYON_GPU_VENDORS " == *" nvidia "* ]]; then
		HALCYON_GPU_PRIMARY=nvidia
	else
		HALCYON_GPU_PRIMARY="${HALCYON_GPU_VENDORS%% *}"
	fi
	[[ -n "$HALCYON_GPU_PRIMARY" ]] || HALCYON_GPU_PRIMARY=unknown

	export HALCYON_GPU_VENDORS HALCYON_GPU_PRIMARY
}

# True when the NVIDIA proprietary kernel module is actually loaded, which
# is a different question from "an NVIDIA card is present" — the nouveau
# and nvidia paths want different environment variables.
nvidia_proprietary_loaded() {
	[[ -e /proc/driver/nvidia/version ]] || return 1
	return 0
}

# ── Machine class ──────────────────────────────────────────────────────

is_laptop() {
	local ct
	if [[ -r /sys/class/dmi/id/chassis_type ]]; then
		ct="$(cat /sys/class/dmi/id/chassis_type 2>/dev/null || echo 0)"
		# 8 portable, 9 laptop, 10 notebook, 11 handheld, 14 sub-notebook,
		# 30 tablet, 31 convertible, 32 detachable
		case "$ct" in 8 | 9 | 10 | 11 | 14 | 30 | 31 | 32) return 0 ;; esac
	fi
	# A power_supply of type Battery is the reliable cross-platform hint.
	local ps
	for ps in /sys/class/power_supply/*; do
		[[ -r "$ps/type" ]] || continue
		[[ "$(cat "$ps/type")" == "Battery" ]] && return 0
	done
	return 1
}

has_battery() {
	local ps
	for ps in /sys/class/power_supply/*; do
		[[ -r "$ps/type" ]] || continue
		[[ "$(cat "$ps/type")" == "Battery" ]] && return 0
	done
	return 1
}

# ── Session ────────────────────────────────────────────────────────────

detect_session() {
	HALCYON_SESSION_TYPE="${XDG_SESSION_TYPE:-unknown}"
	HALCYON_HYPRLAND_RUNNING=0
	[[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && HALCYON_HYPRLAND_RUNNING=1
	export HALCYON_SESSION_TYPE HALCYON_HYPRLAND_RUNNING
}

# Hyprland version as reported by the binary, e.g. "0.56.2". Empty when
# Hyprland is not installed.
hyprland_version() {
	has hyprctl || return 1
	# `hyprctl version` works without a running compositor.
	hyprctl version 2>/dev/null |
		grep -oE 'v?[0-9]+\.[0-9]+\.[0-9]+' | head -n1 | tr -d 'v'
}

quickshell_version() {
	local qs
	if has quickshell; then qs=quickshell
	elif has qs; then qs=qs
	else return 1; fi
	"$qs" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1
}

waybar_version() {
	has waybar || return 1
	waybar --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1
}

# ── Power management ───────────────────────────────────────────────────

# Sets HALCYON_POWER_BACKEND to exactly one of:
#   power-profiles-daemon | tlp | tuned | none
#
# Exactly one on purpose: running two of these at once is a known way to
# get a laptop that fights itself over the CPU governor.
detect_power_backend() {
	HALCYON_POWER_BACKEND=none
	HALCYON_POWER_CONFLICTS=''

	local active=''
	if has systemctl; then
		systemctl is-active --quiet power-profiles-daemon.service 2>/dev/null &&
			active+=' power-profiles-daemon'
		systemctl is-active --quiet tlp.service 2>/dev/null && active+=' tlp'
		systemctl is-active --quiet tuned.service 2>/dev/null && active+=' tuned'
	fi

	# Fall back to "installed" when systemd is absent or nothing is running.
	if [[ -z "$active" ]]; then
		has powerprofilesctl && active+=' power-profiles-daemon'
		has tlp && active+=' tlp'
		has tuned-adm && active+=' tuned'
	fi

	local count=0 first=''
	local svc
	for svc in $active; do
		count=$((count + 1))
		[[ -z "$first" ]] && first="$svc"
	done

	if ((count > 1)); then
		HALCYON_POWER_CONFLICTS="${active# }"
	fi
	[[ -n "$first" ]] && HALCYON_POWER_BACKEND="$first"

	export HALCYON_POWER_BACKEND HALCYON_POWER_CONFLICTS
}

# ── AI backends ────────────────────────────────────────────────────────

detect_ai_backends() {
	HALCYON_HAS_NIXORB=0
	HALCYON_HAS_OLLAMA=0
	HALCYON_HAS_PIPER=0
	HALCYON_HAS_WHISPER=0
	HALCYON_HAS_HYPERNIX=0

	has nixorb && HALCYON_HAS_NIXORB=1
	has ollama && HALCYON_HAS_OLLAMA=1
	{ has piper || has piper-tts; } && HALCYON_HAS_PIPER=1
	{ has whisper-cli || has whisper-cpp || has main-whisper; } && HALCYON_HAS_WHISPER=1
	{ has hypernix || has hnx; } && HALCYON_HAS_HYPERNIX=1

	export HALCYON_HAS_NIXORB HALCYON_HAS_OLLAMA HALCYON_HAS_PIPER
	export HALCYON_HAS_WHISPER HALCYON_HAS_HYPERNIX
}

# Run every detector at once.
detect_all() {
	detect_distro
	detect_package_manager
	detect_arch
	detect_gpu
	detect_session
	detect_power_backend
	detect_ai_backends
}
