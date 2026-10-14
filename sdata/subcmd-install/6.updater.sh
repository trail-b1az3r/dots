# Sets up the Halcyon updater: records where this repository is, so the
# updater knows what to pull, and enables a timer that checks for updates
# every few hours. Sourced by ./setup install after the sleep hook step.

function setup_updater(){
  local state="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"
  mkdir -p "$state"
  printf '%s\n' "$REPO_ROOT" > "$state/repo"
  # The commit whose files were just installed: the updater copies what changed since this one.
  git -C "$REPO_ROOT" rev-parse HEAD > "$state/installed" 2>/dev/null || rm -f "$state/installed"
  rm -f "$state/update-available" "$state/update-error"
  printf "${STY_BLUE}Updates will be checked from ${REPO_ROOT}.${STY_RST}\n"
  if ! command -v systemctl >/dev/null 2>&1; then
    printf "${STY_YELLOW}systemctl isn't available, so the update timer isn't enabled. Run ~/.config/hypr/hyprland/halcyon/update check by hand.${STY_RST}\n"
    return 0
  fi
  v systemctl --user daemon-reload
  v systemctl --user enable --now halcyon-update.timer
}

setup_updater
