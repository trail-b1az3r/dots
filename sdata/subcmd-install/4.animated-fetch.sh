# Asks whether to set up the animated fastfetch: the spinning Halcyon mark
# beside fastfetch's own summary, shown when a fish terminal starts.
# Sourced by ./setup install after the files step.

ANIMATED_FETCH_MARKER="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon/animated-fetch"

function ask_animated_fetch(){
  printf "${STY_BLUE}"
  printf "${STY_BOLD}Set up the animated fastfetch?${STY_RST}\n"
  printf "${STY_BLUE}"
  printf "  It shows the spinning Halcyon mark beside fastfetch's summary whenever a fish terminal opens.\n"
  printf "  It installs fastfetch if it is missing.\n"
  printf "${STY_RST}"
  # Without a terminal to answer on, skip it rather than hang.
  if [[ ! -t 0 ]]; then
    echo "No terminal to answer on, so the animated fastfetch is skipped."
    return 1
  fi
  local p
  read -r -p "===> [Y/n]: " p
  case "$p" in
    [nN]) return 1 ;;
    *) return 0 ;;
  esac
}

if ask_animated_fetch; then
  if ! command -v fastfetch >/dev/null 2>&1; then
    if command -v pacman >/dev/null 2>&1; then
      v sudo pacman -S --needed --noconfirm fastfetch
    else
      printf "${STY_YELLOW}fastfetch is not in pacman here. Install it with your package manager, then the animated fastfetch will show.${STY_RST}\n"
    fi
  fi
  v mkdir -p "$(dirname "$ANIMATED_FETCH_MARKER")"
  v touch "$ANIMATED_FETCH_MARKER"
  printf "${STY_BLUE}Animated fastfetch is set up.${STY_RST}\n"
else
  v rm -f "$ANIMATED_FETCH_MARKER"
  printf "${STY_BLUE}Alright, leaving fastfetch as it is.${STY_RST}\n"
fi
