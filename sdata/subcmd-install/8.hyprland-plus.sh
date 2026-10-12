# Builds the Halcyon Hyprland fork (hyprland-plus) from source and installs it in place
# of the packaged Hyprland. Sourced by ./setup install after the auto-theme step.
#
#   HALCYON_HYPRLAND_REPO          where the source lives (default ~/hyprland-plus)
#   HALCYON_HYPRLAND_REF           branch to build (default halcyon-0.56.2)
#   HALCYON_SKIP_HYPRLAND_PLUS=1   leave the packaged Hyprland alone
#
# The packaged binary is copied to /usr/bin/hyprland.official before it is removed, so
# it can be put back with: sudo make -C ~/hyprland-plus uninstall && sudo pacman -S hyprland

HYPRLAND_PLUS_URL="https://github.com/trail-b1az3r/hyprland-plus"

function setup_hyprland_plus(){
  if [[ "${HALCYON_SKIP_HYPRLAND_PLUS:-0}" == 1 ]]; then
    printf "${STY_YELLOW}Skipping hyprland-plus (HALCYON_SKIP_HYPRLAND_PLUS=1).${STY_RST}\n"
    return 0
  fi

  local repo="${HALCYON_HYPRLAND_REPO:-$HOME/hyprland-plus}"
  local ref="${HALCYON_HYPRLAND_REF:-halcyon-0.56.2}"
  local state="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"

  if ! command -v pacman >/dev/null 2>&1; then
    printf "${STY_YELLOW}hyprland-plus is only installed automatically on Arch. Build it by hand: https://github.com/trail-b1az3r/hyprland-plus${STY_RST}\n"
    return 0
  fi

  # Build tools and git. Hyprland's own libraries come from the dependency step.
  v sudo pacman -S --needed --noconfirm git cmake base-devel || return 1

  if [[ -d "$repo/.git" ]]; then
    v git -C "$repo" fetch origin "$ref" || return 1
    v git -C "$repo" checkout "$ref" || return 1
    v git -C "$repo" pull --ff-only origin "$ref" || {
      printf "${STY_RED}$repo has local changes that stop the update. Commit or stash them, then run ./setup install again.${STY_RST}\n"
      return 1
    }
  else
    v git clone --branch "$ref" "$HYPRLAND_PLUS_URL" "$repo" || return 1
  fi
  v git -C "$repo" submodule update --init --recursive || return 1

  v make -C "$repo" all || {
    printf "${STY_RED}hyprland-plus did not build. The packaged Hyprland is still installed.${STY_RST}\n"
    return 1
  }

  # Keep the packaged binary before removing the package.
  if pacman -Q hyprland >/dev/null 2>&1; then
    if [[ ! -e /usr/bin/hyprland.official ]]; then
      v sudo cp /usr/bin/hyprland /usr/bin/hyprland.official || return 1
    fi
    v sudo pacman -R --noconfirm hyprland || {
      printf "${STY_RED}Could not remove the packaged hyprland (other packages depend on it). Nothing was installed.${STY_RST}\n"
      return 1
    }
  fi

  v sudo make -C "$repo" install || return 1
  v sudo ln -sf /usr/local/bin/Hyprland /usr/local/bin/hyprland

  mkdir -p "$state"
  git -C "$repo" rev-parse --short HEAD > "$state/hyprland-plus-commit"
  printf "${STY_BLUE}Installed hyprland-plus $(cat "$state/hyprland-plus-commit") from ${ref}.${STY_RST}\n"
  printf "${STY_BLUE}Log out and back in, or restart Hyprland, to run it.${STY_RST}\n"
}

setup_hyprland_plus
