#!/usr/bin/env bash
#
# Halcyon — diagnostics.
#
#   ./diagnose.sh              print a report
#   ./diagnose.sh --save       write it to a file you can attach to a bug
#   ./diagnose.sh --json       machine-readable
#
# What this collects and what it does not:
#
#   Collected: distribution, kernel, architecture, the versions of
#   Hyprland, Quickshell, Waybar and Qt, which GPUs are present and which
#   driver is loaded, monitor geometry, which services are running, which
#   dependencies are satisfied, configuration errors, and the health of
#   the AI and HyperNix integrations.
#
#   Not collected: your hostname, your username, network names, the
#   contents of your settings, your conversation history, your clipboard,
#   or anything from your files. A diagnostic report is something people
#   paste into a public issue tracker.

set -Eeuo pipefail

HALCYON_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export HALCYON_REPO_ROOT

# shellcheck source=scripts/lib/packages.sh
. "$HALCYON_REPO_ROOT/scripts/lib/packages.sh"

SAVE=0
AS_JSON=0
OUTPUT=""

usage() {
	cat <<'USAGE'
Halcyon — diagnostics.

Usage: ./diagnose.sh [options]

  -s, --save [FILE]   Write the report to a file (default: ./halcyon-report.txt).
      --json          Machine-readable output.
  -h, --help          This message.

The report deliberately excludes your hostname, username, network names
and the contents of your configuration. It is safe to paste publicly.
USAGE
}

while (($# > 0)); do
	case "$1" in
	-s | --save)
		SAVE=1
		if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
			OUTPUT="$2"
			shift
		fi
		;;
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

detect_all

section() { printf '\n── %s %s\n\n' "$1" "$(printf '─%.0s' $(seq 1 $((60 - ${#1}))))"; }
field() { printf '  %-22s %s\n' "$1" "${2:-—}"; }

# ── System ─────────────────────────────────────────────────────────────

report_system() {
	section "System"
	field "Halcyon" "$(halcyon_version)"
	field "Distribution" "$HALCYON_DISTRO_NAME"
	field "Family" "$HALCYON_FAMILY"
	field "Kernel" "$(uname -r)"
	field "Architecture" "$HALCYON_ARCH"
	field "Package manager" "${HALCYON_PKG_MANAGER:-none}${HALCYON_AUR_HELPER:+ + $HALCYON_AUR_HELPER}"
	field "Session type" "$HALCYON_SESSION_TYPE"
	field "Desktop" "${XDG_CURRENT_DESKTOP:-—}"
	if is_laptop; then field "Form factor" "laptop"; else field "Form factor" "desktop"; fi
	field "Shell" "$(basename "${SHELL:-unknown}")"
	field "Python" "$(python3 --version 2>&1 | awk '{print $2}')"
}

halcyon_version() {
	if has halcyon; then
		halcyon version 2>/dev/null | awk '{print $2}'
	elif [[ -x "$HOME/.local/bin/halcyon" ]]; then
		"$HOME/.local/bin/halcyon" version 2>/dev/null | awk '{print $2}'
	else
		printf 'not installed'
	fi
}

# ── Graphics ───────────────────────────────────────────────────────────

report_graphics() {
	section "Graphics"
	field "GPUs" "${HALCYON_GPU_VENDORS:-none detected}"
	field "Primary" "$HALCYON_GPU_PRIMARY"

	if nvidia_proprietary_loaded; then
		field "NVIDIA driver" "proprietary, loaded"
		if [[ -r /proc/driver/nvidia/version ]]; then
			field "" "$(awk '{print $8}' /proc/driver/nvidia/version 2>/dev/null)"
		fi
		if [[ -r /sys/module/nvidia_drm/parameters/modeset ]]; then
			field "DRM modeset" "$(cat /sys/module/nvidia_drm/parameters/modeset)"
		fi
	elif [[ " $HALCYON_GPU_VENDORS " == *" nvidia "* ]]; then
		field "NVIDIA driver" "nouveau (proprietary not loaded)"
	fi

	local card
	for card in /sys/class/drm/card[0-9]*; do
		[[ -r "$card/device/uevent" ]] || continue
		local driver
		driver="$(awk -F= '/^DRIVER=/{print $2}' "$card/device/uevent" 2>/dev/null)"
		[[ -n "$driver" ]] && field "$(basename "$card") driver" "$driver"
	done

	field "Qt" "$(qt_version 2>/dev/null || printf 'not found')"
	field "Mesa" "$(mesa_version)"
}

qt_version() {
	local tool
	for tool in qmake6 qmake-qt6 qmake; do
		has "$tool" && { "$tool" -query QT_VERSION 2>/dev/null && return 0; }
	done
	has pkg-config && pkg-config --modversion Qt6Core 2>/dev/null && return 0
	return 1
}

mesa_version() {
	has glxinfo && glxinfo -B 2>/dev/null | awk -F': ' '/OpenGL version/{print $2; exit}' && return 0
	has pkg-config && pkg-config --modversion gl 2>/dev/null && return 0
	printf '—'
}

# ── Compositor ─────────────────────────────────────────────────────────

report_compositor() {
	section "Compositor"

	local version
	version="$(hyprland_version || true)"
	field "Hyprland" "${version:-not installed}"

	if [[ -n "$version" ]] && ! version_ge "$version" 0.56.0; then
		field "" "⚠ Halcyon needs 0.56 or newer (Lua configuration)"
	fi

	if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
		field "Running" "yes"
		if has hyprctl; then
			field "Layout" "$(hyprctl getoption general:layout -j 2>/dev/null | sed -n 's/.*"str": *"\([^"]*\)".*/\1/p')"
			local errors
			errors="$(hyprctl configerrors 2>/dev/null || true)"
			if [[ -n "$errors" && "${errors,,}" != "no errors."* ]]; then
				field "Config errors" "yes"
				printf '%s\n' "$errors" | sed 's/^/      /'
			else
				field "Config errors" "none"
			fi
		fi
	else
		field "Running" "no (or run from outside the session)"
	fi

	if has hyprctl && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
		printf '\n'
		field "Monitors" ""
		# Geometry and scale only; the description can carry a serial
		# number, which is not something to paste into an issue.
		hyprctl monitors -j 2>/dev/null | python3 -c '
import json, sys
try:
    monitors = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for monitor in monitors:
    name = monitor.get("name", "?")
    width = monitor.get("width", 0)
    height = monitor.get("height", 0)
    rate = monitor.get("refreshRate", 0)
    scale = monitor.get("scale", 1)
    x = monitor.get("x", 0)
    y = monitor.get("y", 0)
    focused = "  (focused)" if monitor.get("focused") else ""
    print("    %-10s %dx%d@%.0fHz  scale %s  at %d,%d%s"
          % (name, width, height, rate, scale, x, y, focused))
' 2>/dev/null || printf '    (could not read)\n'
	fi
}

# ── Shell ──────────────────────────────────────────────────────────────

report_shell() {
	section "Shell"

	field "Quickshell" "$(quickshell_version || printf 'not installed')"
	field "Waybar" "$(waybar_version || printf 'not installed')"

	local record="$HALCYON_STATE_DIR/quickshell-build"
	if [[ -r "$record" ]]; then
		field "Built from source" "$(awk '/^quickshell /{print $2}' "$record")"
		local built_qt current_qt
		built_qt="$(awk '/^qt /{print $2}' "$record")"
		current_qt="$(qt_version 2>/dev/null || true)"
		field "Built against Qt" "$built_qt"
		if [[ -n "$current_qt" && "$built_qt" != "$current_qt" ]]; then
			field "" "⚠ Qt is now $current_qt — Quickshell must be rebuilt"
		fi
	fi

	if has qs || has quickshell; then
		local binary
		binary="$(command -v qs || command -v quickshell)"
		if "$binary" -c halcyon ipc show >/dev/null 2>&1; then
			field "Shell running" "yes"
			field "Open overlay" "$("$binary" -c halcyon ipc call shell state 2>/dev/null || printf 'none')"
		else
			field "Shell running" "no"
		fi
	fi
}

# ── Configuration ──────────────────────────────────────────────────────

report_config() {
	section "Configuration"

	field "Settings" "$([[ -f "$HALCYON_CONFIG_DIR/settings.json" ]] && printf 'present' || printf 'missing')"

	local name
	for name in theme.json hypr-theme.lua hypr-animations.lua hypr-keybinds.lua \
		hypr-runtime.lua waybar-config.jsonc waybar-colors.css; do
		if [[ -f "$HALCYON_GENERATED_DIR/$name" ]]; then
			field "  $name" "$(stat -c '%y' "$HALCYON_GENERATED_DIR/$name" 2>/dev/null | cut -d. -f1)"
		else
			field "  $name" "missing"
		fi
	done

	# The palette, which is the most common thing to be surprised by.
	if [[ -f "$HALCYON_GENERATED_DIR/palette.json" ]] && has python3; then
		printf '\n'
		python3 -c '
import json, sys
try:
    palette = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
print("  %-22s %s" % ("Palette source", palette.get("source", "?")))
print("  %-22s %s" % ("Accent", palette.get("accent", "?")))
print("  %-22s %s" % ("Swatches", ", ".join(palette.get("swatches", [])) or "—"))
' "$HALCYON_GENERATED_DIR/palette.json" 2>/dev/null || true
	fi

	# Validate the generated Hyprland config the same way install.sh does.
	if has python3 && [[ -f "$HALCYON_REPO_ROOT/scripts/dev/check-hypr-config.py" ]]; then
		printf '\n'
		if python3 "$HALCYON_REPO_ROOT/scripts/dev/check-hypr-config.py" \
			--config "$XDG_CONFIG_HOME/hypr" \
			--generated "$HALCYON_GENERATED_DIR" 2>&1 | tail -n +2 | sed 's/^/  /'; then
			:
		fi
	fi
}

# ── Services ───────────────────────────────────────────────────────────

report_services() {
	section "Services"

	if ! has systemctl; then
		field "systemd" "not available"
		return 0
	fi

	local unit state
	for unit in halcyon-shell halcyon-bar halcyon-assistant halcyon-power \
		halcyon-wallpaper halcyon-idle halcyon-clipboard halcyon-polkit; do
		if [[ -f "$XDG_CONFIG_HOME/systemd/user/$unit.service" ]]; then
			state="$(systemctl --user is-active "$unit.service" 2>/dev/null || printf 'inactive')"
			local enabled
			enabled="$(systemctl --user is-enabled "$unit.service" 2>/dev/null || printf 'disabled')"
			field "$unit" "$state ($enabled)"
		fi
	done

	printf '\n'
	detect_power_backend
	field "Power backend" "$HALCYON_POWER_BACKEND"
	if [[ -n "$HALCYON_POWER_CONFLICTS" ]]; then
		field "⚠ Conflict" "$HALCYON_POWER_CONFLICTS are all running"
		field "" "They fight over the CPU governor. Keep one."
	fi

	if [[ -d /sys/class/power_supply ]]; then
		local battery
		for battery in /sys/class/power_supply/*; do
			[[ -r "$battery/type" ]] || continue
			[[ "$(cat "$battery/type")" == "Battery" ]] || continue
			field "$(basename "$battery")" \
				"$(cat "$battery/capacity" 2>/dev/null)% $(cat "$battery/status" 2>/dev/null)"
		done
	fi
}

# ── Integrations ───────────────────────────────────────────────────────

report_integrations() {
	section "AI assistant"

	if [[ -x "$HOME/.local/bin/halcyon" ]] || has halcyon; then
		local binary
		binary="$(command -v halcyon || printf '%s' "$HOME/.local/bin/halcyon")"
		"$binary" assistant providers 2>/dev/null | sed 's/^/  /' || field "" "could not query"
		printf '\n'
		field "Daemon" "$("$binary" assistant status 2>/dev/null | head -n1 | sed 's/^State: //')"
	else
		field "halcyon" "not installed"
	fi

	field "NixOrb" "$(has nixorb && nixorb version 2>/dev/null | head -n1 || printf 'not installed')"
	field "Ollama" "$(has ollama && ollama --version 2>/dev/null | head -n1 || printf 'not installed')"
	field "Piper" "$({ has piper || has piper-tts; } && printf 'installed' || printf 'not installed')"
	field "whisper.cpp" "$({ has whisper-cli || has whisper-cpp; } && printf 'installed' || printf 'not installed')"

	section "HyperNix"
	if has hypernix || has hnx; then
		local binary
		binary="$(command -v hypernix || command -v hnx)"
		field "Binary" "$binary"
		field "Version" "$("$binary" --version 2>/dev/null | head -n1 | awk '{print $NF}')"
	else
		field "HyperNix" "not installed"
	fi
}

# ── Dependencies ───────────────────────────────────────────────────────

report_dependencies() {
	section "Dependencies"

	local role tier ok=0 missing=0
	while read -r role; do
		[[ -n "$role" ]] || continue
		tier="$(role_field "$role" 1)"
		if role_satisfied "$role"; then
			ok=$((ok + 1))
		else
			missing=$((missing + 1))
			printf '  %-14s %-8s %s\n' "$role" "$tier" "missing"
		fi
	done < <(roles_list)

	printf '\n'
	field "Satisfied" "$ok"
	field "Missing" "$missing"
	((missing > 0)) && field "" "run ./check-deps.sh for the package names"
}

# ── Output ─────────────────────────────────────────────────────────────

render() {
	printf '\nHalcyon diagnostic report\n'
	printf 'Generated %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

	report_system
	report_graphics
	report_compositor
	report_shell
	report_config
	report_services
	report_integrations
	report_dependencies

	printf '\n'
	printf '  This report contains no hostname, username, network name or\n'
	printf '  configuration content. It is safe to attach to a bug report.\n\n'
}

if ((AS_JSON)); then
	if [[ -x "$HOME/.local/bin/halcyon" ]] || has halcyon; then
		"$(command -v halcyon || printf '%s' "$HOME/.local/bin/halcyon")" doctor --json
	else
		printf '{"error": "halcyon is not installed"}\n'
		exit 1
	fi
	exit 0
fi

if ((SAVE)); then
	OUTPUT="${OUTPUT:-./halcyon-report.txt}"
	# Colour codes in a file people paste into an issue tracker are noise.
	NO_COLOR=1 render >"$OUTPUT"
	log_ok "Wrote $OUTPUT"
	log_info "Read it before sharing — it should contain nothing private."
else
	render
fi
