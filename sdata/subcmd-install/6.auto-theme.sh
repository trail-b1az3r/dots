# Enables the timer that applies scheduled themes (Settings > Halcyon, Auto-apply).
# It runs once a minute and does nothing unless a schedule is due.
# Sourced by ./setup install after the updater step.

function setup_auto_theme(){
  if ! command -v systemctl >/dev/null 2>&1; then
    printf "${STY_YELLOW}systemctl isn't available, so scheduled themes won't apply. Run ~/.config/hypr/hyprland/halcyon/halcyon-theme auto by hand.${STY_RST}\n"
    return 0
  fi
  v systemctl --user daemon-reload
  v systemctl --user enable --now halcyon-auto-theme.timer
}

setup_auto_theme
