# Guided automatic install: ./setup walkthrough.
# Shows the steps, asks once, then runs ./setup install --force, so nothing else is asked. Each step prints
# "Step n of 8" while it runs. The hyprland-plus step switches to its own console by itself, builds there, and
# switches back when it is done. Sourced by ./setup; it does nothing until walkthrough_run is called.

WALK_TITLES=(
  ""
  "Dependencies"
  "Permissions and services"
  "Config files"
  "Fetch"
  "Sleep hook"
  "Updater"
  "Theme"
  "hyprland-plus"
)

WALK_SUMMARIES=(
  ""
  "Installs the packages Halcyon needs, with pacman and the AUR where needed."
  "Sets up permissions and the services the desktop runs."
  "Copies the Halcyon config into ~/.config. What is there now is backed up first."
  "Gets the animated fetch and the Halcyon assets."
  "Sets up the sleep hook for the power menu and resume."
  "Records this checkout for the updater and starts its timer."
  "Applies the automatic theme."
  "Builds the Halcyon Hyprland fork on its own console. The screen switches there, builds, and switches back to this desktop by itself."
)

# walk_step <n>: prints the step banner when running as a walkthrough.
walk_step(){
  [[ "${HALCYON_WALKTHROUGH:-0}" == 1 ]] || return 0
  printf "\n${STY_CYAN}${STY_BOLD}Step $1 of $((${#WALK_TITLES[@]} - 1)): ${WALK_TITLES[$1]}${STY_RST}\n"
}

walkthrough_plan(){
  printf "${STY_PURPLE}${STY_BOLD}Halcyon: automatic install, step by step${STY_RST}\n\n"
  local i
  for ((i = 1; i < ${#WALK_TITLES[@]}; i++)); do
    printf "  ${STY_BOLD}%d. %s${STY_RST}\n     %s\n" "$i" "${WALK_TITLES[$i]}" "${WALK_SUMMARIES[$i]}"
  done
  printf "\nYou type your sudo password once here. The hyprland-plus step may ask for it again on its own console.\n"
  printf "Nothing else is asked. Starting installs everything above.\n\n"
}

# walkthrough_run <setup-path> [install options]: shows the plan, asks once unless -f is given, then installs.
walkthrough_run(){
  local setup="$1"
  shift
  walkthrough_plan
  local force=false arg
  for arg in "$@"; do
    [[ "$arg" == -f || "$arg" == --force ]] && force=true
  done
  if [[ "$force" != true ]]; then
    local answer
    read -r -p "Start the automatic install? [Y/n] " answer
    if [[ "$answer" =~ ^[Nn] ]]; then
      printf "Stopped. Nothing was changed.\n"
      exit 0
    fi
  fi
  HALCYON_WALKTHROUGH=1 exec "$setup" install --force "$@"
}
