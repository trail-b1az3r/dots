# Finds an installed hyprland-plus, however it was installed, and tells pacman about it.
# Sourced by the installer (install-deps.sh and the hyprland-plus step). Needs bash.
#
# hyprland-plus can be installed three ways: the AUR package (pacman knows it, and it provides hyprland),
# hyprctl-lite or the installer's own build (make install to /usr/local, which pacman does not know about), or
# by hand. Only the first used to count, so a /usr/local build was rebuilt on every install, and the
# illogical-impulse-hyprland meta package pulled in the stock hyprland package beside it. Every hyprland-plus
# build names itself in `Hyprland --version`, so that is what is checked here.

# The first line of `--version` of an installed hyprland-plus binary, and its path, as "LINE|PATH". Status 1 if
# none is installed.
hyprland_plus_find(){
  local bin line seen=""
  for bin in /usr/local/bin/Hyprland /usr/bin/Hyprland "$(command -v Hyprland 2>/dev/null)" "$(command -v hyprland 2>/dev/null)"; do
    [[ -n "$bin" && -x "$bin" ]] || continue
    bin="$(readlink -f "$bin")"
    [[ " $seen " == *" $bin "* ]] && continue
    seen="$seen $bin"
    line="$("$bin" --version 2>/dev/null || true)"
    line="${line%%$'\n'*}"
    if [[ "${line,,}" == *hyprland-plus* ]]; then
      printf '%s|%s\n' "$line" "$bin"
      return 0
    fi
  done
  return 1
}

# Human description of what is installed, or nothing. Status 0 when hyprland-plus is installed.
hyprland_plus_installed(){
  if pacman -Q hyprland-plus >/dev/null 2>&1; then
    printf 'the hyprland-plus package %s\n' "$(pacman -Q hyprland-plus | cut -d' ' -f2)"
    return 0
  fi
  local found
  found="$(hyprland_plus_find)" || return 1
  printf '%s, in %s\n' "${found%%|*}" "$(dirname "${found##*|}")"
}

# The commit an installed hyprland-plus was built from (short hash), or nothing.
hyprland_plus_commit(){
  local state="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon/hyprland-plus-commit" found
  found="$(hyprland_plus_find)" || return 0
  if [[ "${found%%|*}" =~ commit\ ([0-9a-f]{7,40}) ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  elif [[ -s "$state" ]]; then
    head -n 1 "$state"
  fi
}

# The Hyprland version it is based on ("0.56.2"), for pacman. Falls back to 0.
hyprland_plus_base_version(){
  local found line
  found="$(hyprland_plus_find)" || { echo 0; return; }
  line="${found%%|*}"
  if [[ "$line" =~ \(Hyprland\ ([0-9]+(\.[0-9]+)+)\) ]]; then
    echo "${BASH_REMATCH[1]}"
  elif [[ "$line" =~ hyprland-plus\ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo 0
  fi
}

# Whether the installed build is the head of BRANCH on the remote. Status 0: up to date. 1: older or unknown.
hyprland_plus_up_to_date(){
  local url="$1" branch="$2" have head
  have="$(hyprland_plus_commit)"
  [[ -n "$have" ]] || return 1
  head="$(git ls-remote "$url" "refs/heads/$branch" 2>/dev/null | cut -c1-40)"
  [[ -n "$head" && "$head" == "$have"* ]]
}

# With hyprland-plus installed outside pacman, and nothing in pacman providing hyprland, install a small empty
# package, hyprland-plus-local, that provides hyprland. Packages that depend on hyprland (illogical-impulse-hyprland,
# for one) are then satisfied, and pacman never installs the stock hyprland beside the fork. Remove it with
# `sudo pacman -R hyprland-plus-local`. Runs makepkg as the calling user, so call it as that user (with sudo set up).
hyprland_plus_register_with_pacman(){
  command -v pacman >/dev/null 2>&1 || return 0
  pacman -T hyprland >/dev/null 2>&1 && return 0     # something already provides hyprland
  pacman -Q hyprland-plus-local >/dev/null 2>&1 && return 0
  hyprland_plus_find >/dev/null || return 0
  local version dir
  version="$(hyprland_plus_base_version)"
  dir="$(mktemp -d)"
  cat > "$dir/PKGBUILD" <<EOF
pkgname=hyprland-plus-local
pkgver=${version}
pkgrel=1
pkgdesc="Marks hyprland-plus (installed in /usr/local by Halcyon) as the installed Hyprland, for pacman"
arch=(any)
url="https://github.com/trail-b1az3r/hyprland-plus"
license=(BSD-3-Clause)
provides=("hyprland=${version}")
EOF
  printf 'Telling pacman that hyprland-plus provides hyprland (package hyprland-plus-local %s).\n' "$version"
  if (cd "$dir" && makepkg -f --noconfirm >/dev/null 2>&1) && sudo pacman -U --noconfirm "$dir"/hyprland-plus-local-*.pkg.tar.* >/dev/null; then
    rm -rf "$dir"
    return 0
  fi
  rm -rf "$dir"
  printf 'Could not register hyprland-plus with pacman. The stock hyprland package may be installed beside it; the fork in /usr/local still runs first.\n' >&2
  return 1
}
