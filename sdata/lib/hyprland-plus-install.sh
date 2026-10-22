# Installs a built hyprland-plus and checks that it is there. Sourced by the installer's build step; hyprctl-lite
# carries its own copy of this function (it is a single file). Run as root.
#
#   hyprland_plus_install REPO BIN_DIR
#
# `make install` copies everything (binaries, man pages, headers, the session file). It stops at the first file it
# can't copy, and Hyprland itself is among the last, so a failure part way left /usr/local/bin empty or holding
# only hyprctl. Whatever make install does, the built binaries are then copied straight into BIN_DIR, and the
# result is checked: BIN_DIR/Hyprland must run and say it is hyprland-plus. Status 0 only then.
hyprland_plus_install(){
  local repo="$1" bin_dir="$2" build rc=0 line tool
  build="$repo/build"
  if [[ ! -x "$build/Hyprland" ]]; then
    printf 'hyprland-plus is not built: %s is missing. The build step failed; its first error is above.\n' "$build/Hyprland" >&2
    return 1
  fi
  make -C "$repo" install || rc=$?
  if (( rc != 0 )); then
    printf 'make install stopped (status %s); copying the built programs into %s directly.\n' "$rc" "$bin_dir" >&2
  fi
  mkdir -p "$bin_dir"
  # Always, so a make install that stopped early (or installed somewhere else) still leaves these in place.
  install -m755 "$build/Hyprland" "$bin_dir/Hyprland" || return 1
  for tool in hyprctl/hyprctl hyprpm/hyprpm start/start-hyprland; do
    [[ -x "$build/$tool" ]] && install -m755 "$build/$tool" "$bin_dir/${tool##*/}"
  done
  ln -sf Hyprland "$bin_dir/hyprland"
  # Hyprland exits before printing its version when XDG_RUNTIME_DIR is unset, as it is under sudo; give it one.
  line="$(XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}" "$bin_dir/Hyprland" --version 2>/dev/null | head -n 1)"
  if [[ "${line,,}" != *hyprland-plus* ]]; then
    printf '%s/Hyprland does not say it is hyprland-plus (it says: %s).\n' "$bin_dir" "${line:-nothing}" >&2
    return 1
  fi
  printf 'Installed in %s: %s\n' "$bin_dir" "$(cd "$bin_dir" && ls -1 Hyprland hyprland hyprctl hyprpm start-hyprland 2>/dev/null | tr '\n' ' ')"
  printf '%s\n' "$line"
}
