#!/usr/bin/env bash
#
# Halcyon — validate the whole repository.
#
# Runs every checker that exists for every language in the tree, and
# reports what is missing rather than silently skipping it. This is what
# CI runs, and what to run before sending a change.
#
#   - every shell script, with bash -n and ShellCheck
#   - every Lua file, with luac -p
#   - every QML file, with qmlformat (a syntax error makes it fail)
#   - the Python package: compileall, the unit tests, and pyright
#   - every JSON and JSONC file
#   - the generated Hyprland config against Hyprland's own option table

set -Eeuo pipefail

HALCYON_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$HALCYON_REPO_ROOT"

# shellcheck source=scripts/lib/common.sh
. "$HALCYON_REPO_ROOT/scripts/lib/common.sh"

FAILURES=0
SKIPPED=()

record_failure() {
	log_error "$1"
	FAILURES=$((FAILURES + 1))
}

find_tool() {
	local candidate
	for candidate in "$@"; do
		if command -v "$candidate" >/dev/null 2>&1; then
			printf '%s' "$candidate"
			return 0
		fi
		# Qt tools are often not on PATH.
		if [[ -x "/usr/lib/qt6/bin/$candidate" ]]; then
			printf '/usr/lib/qt6/bin/%s' "$candidate"
			return 0
		fi
		if [[ -x "/usr/lib64/qt6/bin/$candidate" ]]; then
			printf '/usr/lib64/qt6/bin/%s' "$candidate"
			return 0
		fi
	done
	return 1
}

# ── Shell ──────────────────────────────────────────────────────────────

check_shell() {
	log_step "Shell scripts"

	local -a scripts=()
	local file
	while IFS= read -r file; do
		scripts+=("$file")
	done < <(find . -name '*.sh' -not -path './.git/*' | sort)
	scripts+=(./install.sh ./uninstall.sh ./restore.sh ./check-deps.sh ./diagnose.sh)

	local count=0 bad=0
	for file in "${scripts[@]}"; do
		[[ -f "$file" ]] || continue
		count=$((count + 1))
		if ! bash -n "$file" 2>/dev/null; then
			record_failure "$file: bash syntax error"
			bad=$((bad + 1))
			continue
		fi
		if command -v shellcheck >/dev/null 2>&1; then
			if ! shellcheck -x "$file" >/dev/null 2>&1; then
				record_failure "$file: shellcheck"
				shellcheck -x "$file" 2>&1 | head -12 | sed 's/^/      /'
				bad=$((bad + 1))
			fi
		fi
	done

	command -v shellcheck >/dev/null 2>&1 || SKIPPED+=("shellcheck")
	((bad == 0)) && log_ok "$count script(s) clean"
}

# ── Executable bits ────────────────────────────────────────────────────

check_permissions() {
	log_step "Executable bits"

	local -a expected=(
		install.sh uninstall.sh restore.sh check-deps.sh diagnose.sh
		scripts/dev/validate.sh scripts/dev/check-hypr-config.py
		scripts/launcher/launcher.sh scripts/network/wifi-menu.sh
		scripts/power/power-menu.sh scripts/audio/output-menu.sh
		scripts/hypernix/hypernix-menu.sh scripts/theme/preview.sh
		scripts/wallpaper/random.sh scripts/session/halcyon-session.sh
	)

	local file bad=0
	for file in "${expected[@]}"; do
		[[ -f "$file" ]] || {
			record_failure "$file is missing"
			bad=$((bad + 1))
			continue
		}
		[[ -x "$file" ]] || {
			record_failure "$file is not executable"
			bad=$((bad + 1))
		}
	done

	# Libraries are sourced, never run: an executable bit on one invites
	# someone to run it and get a confusing no-op.
	while IFS= read -r file; do
		if [[ -x "$file" ]]; then
			record_failure "$file is a library but is executable"
			bad=$((bad + 1))
		fi
	done < <(find scripts/lib -name '*.sh')

	((bad == 0)) && log_ok "${#expected[@]} entry point(s) executable, libraries are not"
}

# ── Lua ────────────────────────────────────────────────────────────────

check_lua() {
	log_step "Lua"

	local luac
	if ! luac="$(find_tool luac5.4 luac5.3 luac)"; then
		SKIPPED+=("luac (Lua syntax)")
		return 0
	fi

	local count=0 bad=0 file
	while IFS= read -r file; do
		count=$((count + 1))
		if ! "$luac" -p "$file" 2>/dev/null; then
			record_failure "$file: Lua syntax error"
			"$luac" -p "$file" 2>&1 | head -3 | sed 's/^/      /'
			bad=$((bad + 1))
		fi
	done < <(find config scripts -name '*.lua' 2>/dev/null | sort)

	((bad == 0)) && log_ok "$count Lua file(s) parse"
}

# ── QML ────────────────────────────────────────────────────────────────

check_qml() {
	log_step "QML"

	local qmlformat
	if ! qmlformat="$(find_tool qmlformat qmlformat6)"; then
		SKIPPED+=("qmlformat (QML syntax)")
		return 0
	fi

	local count=0 bad=0 file
	while IFS= read -r file; do
		count=$((count + 1))
		if ! "$qmlformat" "$file" >/dev/null 2>&1; then
			record_failure "$file: QML syntax error"
			"$qmlformat" "$file" 2>&1 | head -4 | sed 's/^/      /'
			bad=$((bad + 1))
		fi
	done < <(find config/quickshell -name '*.qml' | sort)

	((bad == 0)) && log_ok "$count QML file(s) parse"

	# Every singleton a qmldir declares has to exist, and every .qml in a
	# singleton directory should be declared — a missing line is a type
	# that silently resolves to nothing at runtime.
	local qmldir directory name path missing=0
	while IFS= read -r qmldir; do
		directory="$(dirname "$qmldir")"
		while read -r _ name _ path; do
			[[ -n "$path" ]] || continue
			[[ -f "$directory/$path" ]] || {
				record_failure "$qmldir declares $name -> $path, which does not exist"
				missing=$((missing + 1))
			}
		done < <(grep '^singleton ' "$qmldir" || true)
	done < <(find config/quickshell -name qmldir)
	((missing == 0)) && log_ok "qmldir declarations resolve"
}

# ── Python ─────────────────────────────────────────────────────────────

check_python() {
	log_step "Python"

	command -v python3 >/dev/null 2>&1 || {
		SKIPPED+=("python3")
		return 0
	}

	if ! python3 -m compileall -q src >/dev/null 2>&1; then
		record_failure "src/ does not compile"
		python3 -m compileall -q src 2>&1 | head -10 | sed 's/^/      /' || true
	else
		local count
		count="$(find src -name '*.py' | wc -l)"
		log_ok "$count Python file(s) compile"
	fi

	if [[ -d tests ]]; then
		if PYTHONPATH="src" python3 -m unittest discover -t . -s tests -q >/dev/null 2>&1; then
			log_ok "Unit tests pass"
		else
			record_failure "Unit tests fail"
			PYTHONPATH="src" python3 -m unittest discover -t . -s tests 2>&1 |
				tail -30 | sed 's/^/      /' || true
		fi
	fi

	if command -v pyright >/dev/null 2>&1; then
		if pyright --outputjson src >/dev/null 2>&1; then
			log_ok "Type check clean"
		else
			log_warn "pyright reported findings (not fatal):"
			pyright src 2>&1 | tail -12 | sed 's/^/      /' || true
		fi
	else
		SKIPPED+=("pyright (type check)")
	fi
}

# ── Data files ─────────────────────────────────────────────────────────

check_data() {
	log_step "JSON and JSONC"

	local count=0 bad=0 file
	while IFS= read -r file; do
		count=$((count + 1))
		if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$file" 2>/dev/null; then
			record_failure "$file: invalid JSON"
			bad=$((bad + 1))
		fi
	done < <(find . -name '*.json' -not -path './.git/*' -not -path '*/__pycache__/*' | sort)

	while IFS= read -r file; do
		count=$((count + 1))
		if ! PYTHONPATH=src python3 -c '
import sys
from halcyon import jsonc
jsonc.load_file(sys.argv[1])
' "$file" 2>/dev/null; then
			record_failure "$file: invalid JSONC"
			bad=$((bad + 1))
		fi
	done < <(find . -name '*.jsonc' -not -path './.git/*' | sort)

	((bad == 0)) && log_ok "$count data file(s) valid"
}

# ── Generated configuration ────────────────────────────────────────────

check_generated() {
	log_step "Generated configuration"

	local workdir
	workdir="$(mktemp -d)"
	# The path is expanded now, on purpose: the trap has to know which
	# directory to remove even after the variable goes out of scope.
	# shellcheck disable=SC2064
	trap "rm -rf '$workdir'" RETURN

	if ! PYTHONPATH=src \
		HALCYON_CONFIG_DIR="$workdir/config" \
		HALCYON_GENERATED_DIR="$workdir/config/generated" \
		HALCYON_STATE_DIR="$workdir/state" \
		HALCYON_CACHE_DIR="$workdir/cache" \
		HALCYON_DATA_DIR="$workdir/share" \
		python3 -m halcyon.cli theme apply --no-reload >/dev/null 2>&1; then
		record_failure "halcyon theme apply failed"
		PYTHONPATH=src HALCYON_CONFIG_DIR="$workdir/config" \
			HALCYON_GENERATED_DIR="$workdir/config/generated" \
			python3 -m halcyon.cli theme apply --no-reload 2>&1 | tail -12 | sed 's/^/      /'
		return 0
	fi
	log_ok "Theme generation succeeds"

	if ! python3 scripts/dev/check-hypr-config.py \
		--config config/hypr --generated "$workdir/config/generated" >/dev/null 2>&1; then
		record_failure "The generated Hyprland configuration is not valid"
		python3 scripts/dev/check-hypr-config.py \
			--config config/hypr --generated "$workdir/config/generated" 2>&1 |
			sed 's/^/      /'
		return 0
	fi
	log_ok "Every Hyprland option, rule, animation and bind is valid"

	# Waybar's generated configuration has to reference only modules that
	# have a definition, or the bar starts with gaps in it.
	if ! PYTHONPATH=src python3 - "$workdir/config/generated/waybar-config.jsonc" <<'PY'; then
import sys
from halcyon import jsonc

config = jsonc.load_file(sys.argv[1])
used = []
for key in ("modules-left", "modules-center", "modules-right"):
    used.extend(config.get(key, []))

missing = [name for name in used if name not in config]
if missing:
    print("modules with no definition: " + ", ".join(missing))
    sys.exit(1)
PY
		record_failure "The generated Waybar configuration references undefined modules"
		return 0
	fi
	log_ok "Waybar configuration is complete"
}

# ── Units ──────────────────────────────────────────────────────────────

check_units() {
	log_step "systemd units"

	if command -v systemd-analyze >/dev/null 2>&1; then
		local file bad=0
		for file in services/*.service services/*.target; do
			[[ -e "$file" ]] || continue
			if ! systemd-analyze verify "$file" >/dev/null 2>&1; then
				# verify resolves dependencies too, which fail outside a
				# real session; only a parse error is worth failing on.
				if systemd-analyze verify "$file" 2>&1 | grep -qi 'syntax\|unknown lvalue\|invalid'; then
					record_failure "$file: unit syntax"
					systemd-analyze verify "$file" 2>&1 | head -5 | sed 's/^/      /'
					bad=$((bad + 1))
				fi
			fi
		done
		((bad == 0)) && log_ok "Unit files parse"
	else
		SKIPPED+=("systemd-analyze (unit syntax)")
		# Fall back to checking the sections exist.
		local file bad=0
		for file in services/*.service; do
			[[ -e "$file" ]] || continue
			grep -q '^\[Service\]' "$file" || {
				record_failure "$file has no [Service] section"
				bad=$((bad + 1))
			}
		done
		((bad == 0)) && log_ok "Unit files have the expected sections"
	fi
}

# ── Consistency ────────────────────────────────────────────────────────

check_consistency() {
	log_step "Cross-file consistency"

	# Every role in deps/roles.conf must appear in every package map, or
	# a distribution silently has no way to satisfy it.
	local bad=0 role map
	while read -r role; do
		[[ -n "$role" ]] || continue
		for map in deps/*.pkgs; do
			grep -qE "^${role}[[:space:]]" "$map" || {
				record_failure "$map has no entry for the role '$role'"
				bad=$((bad + 1))
			}
		done
	done < <(PYTHONPATH=src bash -c '. scripts/lib/packages.sh; roles_list')

	((bad == 0)) && log_ok "Every role has an entry in every package map"

	# Keybinds must not collide.
	if ! PYTHONPATH=src python3 - <<'PY'; then
import json
import sys

with open("config/system/keybinds.catalog.json", encoding="utf-8") as handle:
    catalog = json.load(handle)

seen = {}
clashes = []
for bind in catalog["binds"] + catalog["mouseBinds"]:
    key = bind["default"].upper().replace(" ", "")
    if key in seen:
        clashes.append(f"{bind['default']}: {seen[key]} and {bind['id']}")
    seen[key] = bind["id"]

if clashes:
    print("\n".join(clashes))
    sys.exit(1)
PY
		record_failure "The keybind catalog has duplicate shortcuts"
		return 0
	fi
	log_ok "No duplicate shortcuts in the catalog"

	# Every Waybar module the default layout names must have a definition.
	if ! PYTHONPATH=src python3 - <<'PY'; then
import json
import sys

from halcyon import jsonc

modules = jsonc.load_file("config/waybar/modules.jsonc")
with open("config/system/settings.default.json", encoding="utf-8") as handle:
    settings = json.load(handle)

bar = settings["bar"]
used = bar["left"] + bar["center"] + bar["right"]
builtin = {
    "battery", "backlight", "bluetooth", "clock", "cpu", "disk",
    "idle_inhibitor", "memory", "mpris", "network", "privacy", "pulseaudio",
    "temperature", "tray", "power-profiles-daemon", "keyboard-state", "user",
    "load",
}
missing = [
    name for name in used
    if name not in modules and name.split("#")[0] not in builtin
]
if missing:
    print("bar layout names modules with no definition: " + ", ".join(missing))
    sys.exit(1)
PY
		record_failure "The default bar layout references undefined Waybar modules"
		return 0
	fi
	log_ok "Default bar layout resolves"
}

# ── Run ────────────────────────────────────────────────────────────────

main() {
	printf '\n  %s\n\n' "${C_BOLD}Validating Halcyon${C_RESET}"

	check_shell
	check_permissions
	check_lua
	check_qml
	check_python
	check_data
	check_generated
	check_units
	check_consistency

	printf '\n'
	if ((${#SKIPPED[@]} > 0)); then
		log_warn "Not checked (tool missing): ${SKIPPED[*]}"
	fi

	if ((FAILURES > 0)); then
		printf '\n  %s\n\n' "${C_RED}${FAILURES} problem(s).${C_RESET}"
		exit 1
	fi

	printf '\n  %s\n\n' "${C_GREEN}Everything checks out.${C_RESET}"
}

main "$@"
