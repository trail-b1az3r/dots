#!/usr/bin/env bash
#
# Halcyon — install.
#
#   ./install.sh              install everything
#   ./install.sh --dry-run    print what would happen, change nothing
#   ./install.sh --no-deps    skip package installation
#   ./install.sh --help       the full list
#
# The contract:
#
#   * Nothing is overwritten without a timestamped copy landing in
#     ~/.local/state/halcyon/backups first, with a manifest ./restore.sh
#     can put back exactly.
#   * Running it twice changes nothing the second time.
#   * --dry-run is honest: every mutating step goes through one function,
#     and that function prints instead of acting.
#   * It finishes by validating what it wrote and telling you what is
#     still missing.

set -Eeuo pipefail

HALCYON_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export HALCYON_REPO_ROOT

# shellcheck source=scripts/lib/backup.sh
. "$HALCYON_REPO_ROOT/scripts/lib/backup.sh"
# shellcheck source=scripts/lib/packages.sh
. "$HALCYON_REPO_ROOT/scripts/lib/packages.sh"
# shellcheck source=scripts/lib/build.sh
. "$HALCYON_REPO_ROOT/scripts/lib/build.sh"

# ── Options ────────────────────────────────────────────────────────────

INSTALL_DEPS=1
INSTALL_OPTIONAL=1
INSTALL_AI=0
ENABLE_SERVICES=1
BUILD_SOURCES=1
NIX_IMPERATIVE=0
ONLY_CONFIG=0

usage() {
	cat <<'USAGE'
Halcyon — a Liquid-Glass-inspired desktop environment for Hyprland.

Usage: ./install.sh [options]

  -n, --dry-run        Show what would be done without doing it.
  -y, --yes            Do not prompt; assume yes.
      --no-deps        Do not install system packages.
      --no-optional    Install only what the desktop cannot start without.
      --with-ai        Also install the local AI stack (Ollama, Piper, whisper).
      --no-services    Do not enable systemd user units.
      --no-build       Never build from source; skip what has no package.
      --config-only    Install dotfiles only — no packages, no builds.
      --nix-imperative On NixOS, install with nix-env instead of writing a module.
      --prefix PATH    Where to install built binaries (default: ~/.local).
  -v, --verbose        Print every command that runs.
  -h, --help           This message.

Examples:
  ./install.sh --dry-run          See the plan for this machine.
  ./install.sh --with-ai          Include the local assistant stack.
  ./install.sh --config-only      Re-apply the dotfiles after editing them.
USAGE
}

while (($# > 0)); do
	case "$1" in
	-n | --dry-run) HALCYON_DRY_RUN=1 ;;
	-y | --yes) HALCYON_ASSUME_YES=1 ;;
	--no-deps) INSTALL_DEPS=0 ;;
	--no-optional) INSTALL_OPTIONAL=0 ;;
	--with-ai) INSTALL_AI=1 ;;
	--no-services) ENABLE_SERVICES=0 ;;
	--no-build) BUILD_SOURCES=0 ;;
	--config-only) ONLY_CONFIG=1; INSTALL_DEPS=0; BUILD_SOURCES=0 ;;
	--nix-imperative) NIX_IMPERATIVE=1 ;;
	--prefix)
		shift
		HALCYON_PREFIX="${1:?--prefix needs a path}"
		;;
	-v | --verbose) HALCYON_DEBUG=1 ;;
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

export HALCYON_DRY_RUN HALCYON_ASSUME_YES HALCYON_DEBUG HALCYON_PREFIX

HALCYON_LOG_FILE="${HALCYON_STATE_DIR}/install.log"
[[ -n "${HALCYON_DRY_RUN:-}" ]] || mkdir -p "$HALCYON_STATE_DIR"
export HALCYON_LOG_FILE

trap 'log_error "install.sh failed on line $LINENO. The log is at $HALCYON_LOG_FILE"' ERR

# ── Where things go ────────────────────────────────────────────────────

SHARE_DIR="$HALCYON_DATA_DIR"
BIN_DIR="${HALCYON_PREFIX:-$HOME/.local}/bin"
LIB_DIR="$SHARE_DIR/lib"
QS_CONFIG_DIR="$XDG_CONFIG_HOME/quickshell/halcyon"
HYPR_CONFIG_DIR="$XDG_CONFIG_HOME/hypr"
WAYBAR_CONFIG_DIR="$XDG_CONFIG_HOME/waybar"
SYSTEMD_DIR="$XDG_CONFIG_HOME/systemd/user"

# ── Steps ──────────────────────────────────────────────────────────────

step_detect() {
	log_step "Looking at this machine"
	detect_all

	log_info "Distribution   ${C_BOLD}${HALCYON_DISTRO_NAME}${C_RESET} (${HALCYON_FAMILY})"
	log_info "Architecture   ${HALCYON_ARCH}"
	log_info "Packages       ${HALCYON_PKG_MANAGER:-none found}${HALCYON_AUR_HELPER:+ + $HALCYON_AUR_HELPER}"
	log_info "Graphics       ${HALCYON_GPU_VENDORS:-none detected}"
	if nvidia_proprietary_loaded; then
		log_info "               NVIDIA proprietary driver is loaded"
	fi
	if is_laptop; then
		log_info "Form factor    laptop"
	else
		log_info "Form factor    desktop"
	fi
	log_info "Session        ${HALCYON_SESSION_TYPE}"

	local version
	if version="$(hyprland_version)"; then
		log_info "Hyprland       $version"
		if ! version_ge "$version" 0.56.0; then
			log_warn "Halcyon needs Hyprland 0.56 or newer: it configures in Lua"
			log_warn "(introduced in 0.53) and uses options added in 0.56."
			confirm "Continue anyway?" || exit 1
		fi
	else
		log_info "Hyprland       not installed"
	fi

	version="$(quickshell_version || true)"
	log_info "Quickshell     ${version:-not installed}"
	version="$(waybar_version || true)"
	log_info "Waybar         ${version:-not installed}"

	if [[ -n "$HALCYON_POWER_CONFLICTS" ]]; then
		log_warn "More than one power daemon is running: $HALCYON_POWER_CONFLICTS"
		log_warn "They fight over the CPU governor. Halcyon will drive only one;"
		log_warn "disable the others, e.g. systemctl disable --now tlp"
	else
		log_info "Power          ${HALCYON_POWER_BACKEND}"
	fi

	if [[ "$HALCYON_FAMILY" == "unknown" ]]; then
		log_warn "This distribution is not one Halcyon has package lists for."
		log_warn "The dotfiles will still install; dependencies are yours to supply."
	fi
}

step_plan() {
	log_step "What this will change"

	local -a plan=(
		"Configuration|"
		"  $HYPR_CONFIG_DIR/hyprland.lua|Hyprland configuration (Lua)"
		"  $HYPR_CONFIG_DIR/halcyon/|Halcyon's Hyprland modules"
		"  $QS_CONFIG_DIR/|the Quickshell shell"
		"  $WAYBAR_CONFIG_DIR/|Waybar layout and stylesheet"
		"  $HALCYON_CONFIG_DIR/settings.json|your settings (created if absent)"
		"|"
		"Programs and data|"
		"  $BIN_DIR/halcyon|the command everything calls"
		"  $LIB_DIR/halcyon/|its Python modules"
		"  $SHARE_DIR/|presets, catalogs, wallpapers"
	)
	if ((ENABLE_SERVICES)); then
		plan+=("  $SYSTEMD_DIR/halcyon-*|systemd user units")
	fi

	# Work out the column width from the longest path so the descriptions
	# line up whatever the home directory is called.
	local width=0 entry path
	for entry in "${plan[@]}"; do
		path="${entry%%|*}"
		((${#path} > width)) && width=${#path}
	done

	printf '\n'
	for entry in "${plan[@]}"; do
		path="${entry%%|*}"
		printf '   %-*s  %s\n' "$width" "$path" "${C_DIM}${entry#*|}${C_RESET}"
	done

	cat <<PLAN

   Anything already at those paths is copied to
     ${HALCYON_BACKUP_DIR}/<timestamp>/
   and ./restore.sh puts it back.
PLAN

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "${C_BOLD}Dry run — nothing below will be changed.${C_RESET}"
	elif ! confirm "Install Halcyon?"; then
		log_info "Nothing was changed."
		exit 0
	fi
}

step_dependencies() {
	((INSTALL_DEPS)) || return 0

	log_step "Installing dependencies"

	if [[ "$HALCYON_FAMILY" == "nixos" ]] && ((!NIX_IMPERATIVE)); then
		write_nix_module
		return 0
	fi

	if [[ -z "${HALCYON_PKG_MANAGER:-}" ]]; then
		log_warn "No supported package manager found; skipping."
		return 0
	fi

	run_sh "true" # keeps the dry-run output readable
	pkg_refresh || log_warn "Could not refresh the package lists; continuing."

	local -a wanted=() split=()
	local role tier packages
	while read -r role; do
		[[ -n "$role" ]] || continue
		tier="$(role_field "$role" 1)"
		case "$tier" in
		ai) ((INSTALL_AI)) || continue ;;
		extra) ((INSTALL_OPTIONAL)) || continue ;;
		esac
		if role_satisfied "$role"; then
			log_debug "already present: $role"
			continue
		fi
		if packages="$(pkg_for_role "$role")"; then
			# The map stores several packages per role on one line, so
			# splitting on whitespace is the point.
			read -r -a split <<<"$packages"
			wanted+=("${split[@]}")
		else
			log_debug "no package for $role on $HALCYON_FAMILY"
		fi
	done < <(roles_list)

	if ((BUILD_SOURCES)); then
		read -r -a split <<<"$(pkg_group @build 2>/dev/null || true)"
		wanted+=("${split[@]}")
		if ! role_satisfied quickshell; then
			read -r -a split <<<"$(pkg_group @quickshell-dev 2>/dev/null || true)"
			wanted+=("${split[@]}")
		fi
	fi

	if ((${#wanted[@]} == 0)); then
		log_ok "Everything needed is already installed."
		return 0
	fi

	# De-duplicate; several roles share packages.
	local -a unique=()
	local package seen=""
	for package in "${wanted[@]}"; do
		case " $seen " in *" $package "*) continue ;; esac
		seen+=" $package"
		unique+=("$package")
	done

	log_info "Installing ${#unique[@]} package(s)"
	pkg_install "${unique[@]}" || log_warn "Some packages could not be installed; check-deps.sh will say which."
}

write_nix_module() {
	local target="$HALCYON_CONFIG_DIR/nixos/halcyon.nix"
	log_info "NixOS detected — writing a module rather than installing imperatively."
	ensure_dir "$(dirname "$target")"

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "would write $target"
		return 0
	fi

	local -a attrs=() split=()
	local role packages
	while read -r role; do
		[[ -n "$role" ]] || continue
		if packages="$(pkg_for_role "$role")"; then
			read -r -a split <<<"$packages"
			attrs+=("${split[@]}")
		fi
	done < <(roles_list)

	{
		printf '# Generated by Halcyon'\''s install.sh.\n'
		printf '#\n'
		printf '# Import this from your configuration.nix or home-manager config:\n'
		printf '#\n'
		printf '#   imports = [ %s ];\n' "$target"
		printf '#\n'
		printf '# then rebuild. Halcyon does not install packages imperatively on\n'
		printf '# NixOS: a desktop assembled with nix-env is not reproducible, and\n'
		printf '# the next rebuild would silently undo it.\n'
		printf '{ pkgs, ... }:\n{\n'
		printf '  programs.hyprland.enable = true;\n\n'
		printf '  environment.systemPackages = with pkgs; [\n'
		printf '    %s\n' "${attrs[@]}"
		printf '  ];\n'
		printf '}\n'
	} >"$target"

	log_ok "Wrote $target — import it and rebuild, then re-run ./install.sh --config-only"
}

step_build() {
	((BUILD_SOURCES)) || return 0

	if role_satisfied quickshell && ! quickshell_needs_rebuild; then
		log_debug "Quickshell is present and built against the current Qt."
		return 0
	fi

	log_step "Building what this distribution does not package"

	if role_satisfied quickshell && quickshell_needs_rebuild; then
		log_warn "Qt has changed since Quickshell was built. It links against"
		log_warn "private Qt APIs, so it must be rebuilt or it will crash."
	fi

	if ! confirm "Build Quickshell from source (this takes a few minutes)?"; then
		log_warn "Skipped. Waybar will still work; Spotlight and the panels will not."
		return 0
	fi

	build_quickshell || log_warn "Quickshell could not be built; the desktop will run without it."
}

step_backup() {
	log_step "Backing up what is already there"
	backup_begin

	# Only the paths Halcyon does *not* write are copied here — a config
	# from a previous setup that would otherwise be shadowed rather than
	# replaced. Everything Halcyon installs is backed up by install_file
	# and install_tree, and only when the content actually differs, so
	# re-running the installer does not produce a second full copy.
	local path
	for path in \
		"$HYPR_CONFIG_DIR/hyprland.conf" \
		"$WAYBAR_CONFIG_DIR/config" \
		"$WAYBAR_CONFIG_DIR/config.jsonc"; do
		backup_path "$path"
	done
}

step_install_files() {
	log_step "Installing the desktop"

	ensure_dir "$BIN_DIR" "$LIB_DIR" "$SHARE_DIR" "$HALCYON_CONFIG_DIR" \
		"$HALCYON_GENERATED_DIR" "$HALCYON_STATE_DIR"

	# The Python package, and a launcher that finds it.
	install_tree "$HALCYON_REPO_ROOT/src/halcyon" "$LIB_DIR/halcyon"
	install_launcher

	# Shipped data the CLI and the shell read at runtime.
	install_file "$HALCYON_REPO_ROOT/config/system/settings.default.json" \
		"$SHARE_DIR/settings.default.json"
	install_file "$HALCYON_REPO_ROOT/config/system/keybinds.catalog.json" \
		"$SHARE_DIR/keybinds.catalog.json"
	install_file "$HALCYON_REPO_ROOT/deps/hyprland-options.json" \
		"$SHARE_DIR/hyprland-options.json"
	install_file "$HALCYON_REPO_ROOT/config/waybar/modules.jsonc" \
		"$SHARE_DIR/waybar-modules.jsonc"
	install_tree "$HALCYON_REPO_ROOT/themes" "$SHARE_DIR/themes"
	install_tree "$HALCYON_REPO_ROOT/assets/icons" "$SHARE_DIR/icons"
	# Wallpapers go straight to SHARE_DIR/wallpapers rather than under
	# assets/, because that is where HALCYON_WALLPAPER_DIR points by
	# default — rotation looks for them there.
	install_tree "$HALCYON_REPO_ROOT/assets/wallpapers" "$SHARE_DIR/wallpapers"
	# The fallback menus, which run when Quickshell is not available.
	install_tree "$HALCYON_REPO_ROOT/scripts" "$SHARE_DIR/scripts"

	# Configuration.
	install_file "$HALCYON_REPO_ROOT/config/hypr/hyprland.lua" \
		"$HYPR_CONFIG_DIR/hyprland.lua"
	install_tree "$HALCYON_REPO_ROOT/config/hypr/halcyon" "$HYPR_CONFIG_DIR/halcyon"
	install_file "$HALCYON_REPO_ROOT/config/hypr/hyprlock.conf" \
		"$HYPR_CONFIG_DIR/hyprlock.conf"
	install_file "$HALCYON_REPO_ROOT/config/hypr/hypridle.conf" \
		"$HYPR_CONFIG_DIR/hypridle.conf"
	install_tree "$HALCYON_REPO_ROOT/config/quickshell/halcyon" "$QS_CONFIG_DIR"
	install_file "$HALCYON_REPO_ROOT/config/waybar/style.css" \
		"$WAYBAR_CONFIG_DIR/style.css"
	install_file "$HALCYON_REPO_ROOT/config/waybar/modules.jsonc" \
		"$WAYBAR_CONFIG_DIR/modules.jsonc"

	# A place for the user's own Hyprland overrides, created once and
	# never touched again.
	if [[ ! -e "$HYPR_CONFIG_DIR/local.lua" ]]; then
		if [[ -z "${HALCYON_DRY_RUN:-}" ]]; then
			cat >"$HYPR_CONFIG_DIR/local.lua" <<'LOCAL'
-- Your Hyprland overrides.
--
-- Loaded last, after everything Halcyon sets, so anything here wins.
-- Halcyon never rewrites this file.
--
-- For example:
--
--   hl.config({ general = { gaps_out = 24 } })
--   hl.bind("SUPER + G", hl.dsp.exec_cmd("gimp"))
LOCAL
			log_ok "Created $HYPR_CONFIG_DIR/local.lua for your own overrides"
		else
			log_info "would create $HYPR_CONFIG_DIR/local.lua"
		fi
	fi

	# The desktop entry, so a login manager can offer Halcyon.
	install_session_entry
}

install_launcher() {
	local target="$BIN_DIR/halcyon"

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "would install $target"
		return 0
	fi

	local temp
	temp="$(mktemp)"
	cat >"$temp" <<LAUNCHER
#!/usr/bin/env bash
# Halcyon's command-line entry point. Generated by install.sh.
#
# Adds the installed package directory to PYTHONPATH rather than
# installing into site-packages: no pip, no virtualenv, nothing to
# conflict with the system Python.
export PYTHONPATH="${LIB_DIR}\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\${HALCYON_PYTHON:-python3}" -m halcyon.cli "\$@"
LAUNCHER

	# Only rewrite when the content actually differs, so a second install
	# reports nothing rather than claiming to have changed something.
	if [[ -f "$target" ]] && cmp -s "$temp" "$target"; then
		rm -f "$temp"
		log_debug "unchanged: $target"
	else
		# The launcher is written here rather than through install_file,
		# so it needs the manifest entry install_file would have made —
		# without it a restore leaves the binary behind.
		backup_path "$target"
		install -Dm0755 "$temp" "$target"
		rm -f "$temp"
		log_ok "Installed $target"
	fi

	case ":$PATH:" in
	*":$BIN_DIR:"*) ;;
	*)
		log_warn "$BIN_DIR is not on your PATH."
		log_warn "Add it to your shell profile, or the keybinds will not find halcyon."
		;;
	esac
}

install_session_entry() {
	local target="/usr/share/wayland-sessions/halcyon.desktop"
	local sudo_cmd
	sudo_cmd="$(sudo_prefix)" || return 0

	[[ -e "$target" ]] && return 0

	local temp
	temp="$(mktemp)"
	cat >"$temp" <<'ENTRY'
[Desktop Entry]
Name=Halcyon
Comment=A Liquid-Glass-inspired desktop environment for Hyprland
Exec=Hyprland
Type=Application
DesktopNames=Hyprland;Halcyon
Keywords=tiling;wayland;compositor;
ENTRY

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "would install $target"
		rm -f "$temp"
		return 0
	fi

	if $sudo_cmd install -Dm644 "$temp" "$target" 2>/dev/null; then
		log_ok "Installed the session entry for your login manager"
	else
		log_debug "Could not write $target; log in with Hyprland's own entry instead."
	fi
	rm -f "$temp"
}

step_configure() {
	log_step "Generating the theme"

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "would run: halcyon theme apply"
		return 0
	fi

	if [[ ! -f "$HALCYON_CONFIG_DIR/settings.json" ]]; then
		printf '{\n  "version": 1\n}\n' >"$HALCYON_CONFIG_DIR/settings.json"
		log_ok "Created $HALCYON_CONFIG_DIR/settings.json"
	fi

	if "$BIN_DIR/halcyon" theme apply --no-reload >/dev/null; then
		log_ok "Generated the theme, animations, keybinds and bar configuration"
	else
		log_error "halcyon theme apply failed. Run it by hand to see why:"
		log_error "  $BIN_DIR/halcyon theme apply"
		return 1
	fi
}

step_services() {
	((ENABLE_SERVICES)) || return 0
	has systemctl || {
		log_debug "No systemd; the Hyprland config starts the services instead."
		return 0
	}

	log_step "Setting up services"
	ensure_dir "$SYSTEMD_DIR"

	local unit name
	for unit in "$HALCYON_REPO_ROOT"/services/*.service "$HALCYON_REPO_ROOT"/services/*.target; do
		[[ -e "$unit" ]] || continue
		name="$(basename "$unit")"
		install_file "$unit" "$SYSTEMD_DIR/$name"
	done

	run systemctl --user daemon-reload

	# Only enable what can actually run. An enabled unit for a program
	# that is not installed is a failed unit at every login.
	local -a enable=(halcyon-shell.service halcyon-power.service)
	if role_satisfied waybar; then enable+=(halcyon-bar.service); fi
	if role_satisfied hypridle; then enable+=(halcyon-idle.service); fi
	if role_satisfied cliphist; then
		enable+=(halcyon-clipboard.service halcyon-clipboard-image.service)
	fi
	if role_satisfied polkit-agent; then enable+=(halcyon-polkit.service); fi
	if [[ "$(halcyon_setting assistant.enabled)" == "True" ]]; then
		enable+=(halcyon-assistant.service)
	fi

	local service
	for service in "${enable[@]}"; do
		run systemctl --user enable "$service" || log_warn "Could not enable $service"
	done

	log_ok "Enabled ${#enable[@]} service(s) under halcyon-session.target"
	log_info "They start with the session; nothing is running yet."
}

halcyon_setting() {
	[[ -x "$BIN_DIR/halcyon" ]] || return 1
	"$BIN_DIR/halcyon" settings get "$1" 2>/dev/null || true
}

step_validate() {
	log_step "Checking what was installed"

	local problems=0

	# Lua: every configuration file has to compile.
	if has luac5.4 || has luac; then
		local luac
		luac="$(command -v luac5.4 || command -v luac)"
		local file
		while IFS= read -r file; do
			if ! "$luac" -p "$file" 2>/dev/null; then
				log_error "Lua syntax error in $file"
				problems=$((problems + 1))
			fi
		done < <(find "$HYPR_CONFIG_DIR" "$HALCYON_GENERATED_DIR" -name '*.lua' 2>/dev/null)
		if ((problems == 0)); then
			log_ok "Hyprland configuration parses"
		fi
	else
		log_debug "No Lua interpreter; skipped the syntax check."
	fi

	# The generated Hyprland config against Hyprland's own option table.
	if has python3 && [[ -f "$HALCYON_REPO_ROOT/scripts/dev/check-hypr-config.py" ]]; then
		if python3 "$HALCYON_REPO_ROOT/scripts/dev/check-hypr-config.py" \
			--config "$HYPR_CONFIG_DIR" --generated "$HALCYON_GENERATED_DIR" >/dev/null 2>&1; then
			log_ok "Every option, rule and bind is valid for this Hyprland"
		else
			log_warn "The configuration check found problems. Details:"
			python3 "$HALCYON_REPO_ROOT/scripts/dev/check-hypr-config.py" \
				--config "$HYPR_CONFIG_DIR" --generated "$HALCYON_GENERATED_DIR" || true
			problems=$((problems + 1))
		fi
	fi

	# JSON the bar and the shell read.
	local json
	for json in "$HALCYON_GENERATED_DIR/theme.json" "$HALCYON_CONFIG_DIR/settings.json"; do
		[[ -f "$json" ]] || continue
		if has jq; then
			jq -e . "$json" >/dev/null 2>&1 || {
				log_error "$json is not valid JSON"
				problems=$((problems + 1))
			}
		elif has python3; then
			python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$json" 2>/dev/null || {
				log_error "$json is not valid JSON"
				problems=$((problems + 1))
			}
		fi
	done
	if ((problems == 0)); then
		log_ok "Generated files are well formed"
	fi

	# A running Hyprland is the last word on its own configuration.
	if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && has hyprctl; then
		local errors
		errors="$(hyprctl configerrors 2>/dev/null || true)"
		if [[ -n "$errors" && "${errors,,}" != "no errors."* ]]; then
			log_error "Hyprland reports configuration errors:"
			printf '%s\n' "$errors" | sed 's/^/      /'
			problems=$((problems + 1))
		else
			log_ok "hyprctl configerrors reports nothing"
		fi
	fi

	# Executable bits. A launcher installed without one is a keybind that
	# silently does nothing.
	if [[ ! -x "$BIN_DIR/halcyon" ]]; then
		log_error "$BIN_DIR/halcyon is not executable"
		problems=$((problems + 1))
	fi

	return $((problems > 0 ? 1 : 0))
}

step_summary() {
	backup_finish

	log_step "Done"

	local missing=0
	local role tier
	while read -r role; do
		[[ -n "$role" ]] || continue
		tier="$(role_field "$role" 1)"
		[[ "$tier" == "core" ]] || continue
		role_satisfied "$role" || {
			log_warn "Missing (required): $role — $(role_field "$role" 3)"
			missing=$((missing + 1))
		}
	done < <(roles_list)

	printf '\n'
	if ((missing > 0)); then
		printf '  %s\n\n' "${C_YELLOW}$missing required component(s) are still missing.${C_RESET}"
		printf '  Run %s to see everything, including the optional pieces.\n\n' \
			"${C_BOLD}./check-deps.sh${C_RESET}"
	else
		printf '  %s\n\n' "${C_GREEN}Everything Halcyon needs is in place.${C_RESET}"
	fi

	cat <<'NEXT'
  Next
    1. Log out and choose Halcyon (or Hyprland) at your login screen.
    2. Super + /          every keyboard shortcut, searchable
       Super + Space      Spotlight
       Super + ,          Settings
       Super + C          Control Center

  Useful
    halcyon doctor        check the installation
    halcyon theme apply   regenerate after editing settings.json by hand
    ./restore.sh          put your previous configuration back

NEXT

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		printf '  %s\n\n' "${C_BOLD}That was a dry run. Nothing was changed.${C_RESET}"
	fi
}

# ── Run ────────────────────────────────────────────────────────────────

main() {
	printf '\n  %s\n  %s\n\n' \
		"${C_BOLD}Halcyon${C_RESET}" \
		"${C_DIM}a Liquid-Glass-inspired desktop for Hyprland${C_RESET}"

	step_detect
	step_plan
	((ONLY_CONFIG)) || step_dependencies
	((ONLY_CONFIG)) || step_build
	step_backup
	step_install_files
	step_configure
	step_services

	if ! step_validate; then
		log_warn "Installation finished, but the checks above found problems."
		log_warn "The desktop may still work; fix them before reporting a bug."
		step_summary
		exit 1
	fi

	step_summary
}

main "$@"
