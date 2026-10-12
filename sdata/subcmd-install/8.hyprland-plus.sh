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
# be put back with: sudo make -C ~/hyprland-plus uninstall && sudo pacman -S hyprland

function setup_hyprland_plus(){
  if [[ "${HALCYON_SKIP_HYPRLAND_PLUS:-0}" == 1 ]]; then
    printf "${STY_YELLOW}Skipping hyprland-plus (HALCYON_SKIP_HYPRLAND_PLUS=1).${STY_RST}\n"
    return 0
  fi

  if ! command -v pacman >/dev/null 2>&1; then
    printf "${STY_YELLOW}hyprland-plus is only installed automatically on Arch. Build it by hand: https://github.com/trail-b1az3r/hyprland-plus${STY_RST}\n"
    return 0
  fi

  # Installed from the AUR (package hyprland-plus): nothing to build here.
  if pacman -Q hyprland-plus >/dev/null 2>&1; then
    printf "${STY_BLUE}hyprland-plus $(pacman -Q hyprland-plus | cut -d' ' -f2) is already installed (from the AUR), so it is not built again.${STY_RST}\n"
    return 0
  fi

  local job="$REPO_ROOT/sdata/lib/hyprland-plus-build.sh"
  local console="${HALCYON_HYPRLAND_CONSOLE:-3}"
  local repo="${HALCYON_HYPRLAND_REPO:-$HOME/hyprland-plus}"
  local ref="${HALCYON_HYPRLAND_REF:-halcyon-0.56.2}"
  local state="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"

  if ! command -v openvt >/dev/null 2>&1; then
    printf "${STY_YELLOW}openvt is not installed (Arch: the kbd package), so hyprland-plus will build in this terminal.${STY_RST}\n"
    local rc=0
    HALCYON_HYPRLAND_REPO="$repo" HALCYON_HYPRLAND_REF="$ref" bash "$job" || rc=$?
  else
    local back
    back="$(fgconsole 2>/dev/null || true)"
    printf "${STY_BLUE}Opening console ${console} to build and install hyprland-plus. Enter your password there if asked.${STY_RST}\n"
    printf "${STY_BLUE}This installer waits for that console to finish, then continues here.${STY_RST}\n"
    local rc=0
    sudo openvt -c "$console" -s -w -- sudo -u "$(id -un)" env HALCYON_HYPRLAND_REPO="$repo" HALCYON_HYPRLAND_REF="$ref" bash "$job" || rc=$?
    if [[ -n "$back" ]]; then
      sudo chvt "$back" 2>/dev/null || true
    fi
  fi

  if [[ $rc -ne 0 ]]; then
    printf "${STY_RED}hyprland-plus was not installed (the build exited with status ${rc}). Fix the error and run ./setup install again.${STY_RST}\n"
    return 1
  fi

  printf "${STY_BLUE}Log out and back in, or restart Hyprland, to run hyprland-plus.${STY_RST}\n"
}

setup_hyprland_plus
