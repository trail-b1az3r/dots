# Builds the Halcyon Hyprland fork (hyprland-plus) and installs it in place of the packaged
# Hyprland. Sourced by ./setup install after the auto-theme step.
#
# The build runs on a text console of its own (sdata/lib/hyprland-plus-build.sh), so the
# compositor can be replaced without the graphical session running it. The installer waits
# on that console, switches back when it is done, and then finishes.
#
#   HALCYON_HYPRLAND_CONSOLE       console number for the build (default 3)
#   HALCYON_HYPRLAND_REPO          where the source lives (default ~/hyprland-plus)
#   HALCYON_HYPRLAND_REF           branch to build (default halcyon-0.56.2)
#   HALCYON_SKIP_HYPRLAND_PLUS=1   leave the packaged Hyprland alone
#
# The packaged binary is copied to /usr/bin/hyprland.official before it is removed, so it can
# be put back with: sudo make -C ~/hyprland-plus uninstall (the packaged hyprland is never removed)

function setup_hyprland_plus(){
  if [[ "${HALCYON_SKIP_HYPRLAND_PLUS:-0}" == 1 ]]; then
    printf "${STY_YELLOW}Skipping hyprland-plus (HALCYON_SKIP_HYPRLAND_PLUS=1).${STY_RST}\n"
    return 0
  fi

  if ! command -v pacman >/dev/null 2>&1; then
    printf "${STY_YELLOW}hyprland-plus is only installed automatically on Arch. Build it by hand: https://github.com/trail-b1az3r/hyprland-plus${STY_RST}\n"
    return 0
  fi

  source "$REPO_ROOT/sdata/lib/hyprland-plus-detect.sh"
  local job="$REPO_ROOT/sdata/lib/hyprland-plus-build.sh"
  local console="${HALCYON_HYPRLAND_CONSOLE:-3}"
  local repo="${HALCYON_HYPRLAND_REPO:-$HOME/hyprland-plus}"
  local ref="${HALCYON_HYPRLAND_REF:-halcyon-0.56.2}"
  local url="https://github.com/trail-b1az3r/hyprland-plus"
  local state="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"

  # Installed from the AUR (package hyprland-plus): pacman updates it, nothing to build here.
  if pacman -Q hyprland-plus >/dev/null 2>&1; then
    printf "${STY_BLUE}hyprland-plus $(pacman -Q hyprland-plus | cut -d' ' -f2) is already installed (from the AUR), so it is not built again.${STY_RST}\n"
    return 0
  fi

  # Installed some other way (hyprctl-lite, an earlier run of this installer, by hand). Rebuilt only when the
  # branch has moved on, or when HALCYON_REBUILD_HYPRLAND_PLUS=1 asks for it.
  local found
  if found="$(hyprland_plus_installed)"; then
    hyprland_plus_register_with_pacman || true
    if [[ "${HALCYON_REBUILD_HYPRLAND_PLUS:-0}" != 1 ]] && hyprland_plus_up_to_date "$url" "$ref"; then
      printf "${STY_BLUE}hyprland-plus is already installed and up to date: ${found}. Not built again.${STY_RST}\n"
      return 0
    fi
    printf "${STY_BLUE}hyprland-plus is installed (${found}), but ${ref} has newer commits, so it is updated now.${STY_RST}\n"
  fi

  if ! command -v openvt >/dev/null 2>&1; then
    printf "${STY_YELLOW}openvt is not installed (Arch: the kbd package), so hyprland-plus will build in this terminal.${STY_RST}\n"
    local rc=0
    HALCYON_HYPRLAND_REPO="$repo" HALCYON_HYPRLAND_REF="$ref" bash "$job" || rc=$?
  else
    # The console this desktop runs on. logind sets XDG_VTNR for the session; fgconsole needs root, so it is the fallback.
    local back="${XDG_VTNR:-}"
    if [[ -z "$back" ]]; then
      back="$(sudo fgconsole 2>/dev/null || true)"
    fi
    if [[ "$console" == "$back" ]]; then
      console=$((back + 1))
    fi
    if [[ "${HALCYON_WALKTHROUGH:-0}" == 1 ]]; then
      printf "${STY_BLUE}Switching to console ${console} now. The build runs there, then this installer switches back by itself.${STY_RST}\n"
    else
      printf "${STY_BLUE}Opening console ${console} to build and install hyprland-plus. Enter your password there if asked.${STY_RST}\n"
      printf "${STY_BLUE}This installer waits for that console to finish, then continues here.${STY_RST}\n"
    fi
    local rc=0
    sudo openvt -f -c "$console" -s -w -- sudo -u "$(id -un)" env HALCYON_HYPRLAND_REPO="$repo" HALCYON_HYPRLAND_REF="$ref" bash "$job" || rc=$?
    # Back to the desktop. openvt -s does not switch back by itself, so this is the way back.
    if [[ -n "$back" ]]; then
      sudo chvt "$back" 2>/dev/null || true
      printf "${STY_BLUE}Back on the desktop (console ${back}).${STY_RST}\n"
    else
      printf "${STY_YELLOW}Could not find the desktop's console. Switch back with Ctrl+Alt+F1 to F6, whichever is your session.${STY_RST}\n"
    fi
  fi

  if [[ $rc -ne 0 ]]; then
    printf "${STY_RED}hyprland-plus was not installed (the build exited with status ${rc}). Fix the error and run ./setup install again.${STY_RST}\n"
    return 1
  fi

  printf "${STY_BLUE}Log out and back in to start it. hyprland-plus is not a command: it is Hyprland itself, so you start Hyprland as usual. Run hyprctl version to check.${STY_RST}\n"
}

setup_hyprland_plus
