# Installs the systemd sleep hook: a fallback that restarts NetworkManager and
# the Razer daemon after resume, but only when the user's halcyon-resume
# service isn't running. Sourced by ./setup install after the animated fastfetch step.

SLEEP_HOOK_SOURCE="${REPO_ROOT}/dots/.config/hypr/hyprland/halcyon/sleep-hook"
SLEEP_HOOK_TARGET="/usr/lib/systemd/system-sleep/halcyon-resume"

function install_sleep_hook(){
  if [[ ! -f "$SLEEP_HOOK_SOURCE" ]]; then
    printf "${STY_RED}The sleep hook is missing from ${SLEEP_HOOK_SOURCE}; skipping it.${STY_RST}\n"
    return 1
  fi
  if ! command -v sudo >/dev/null 2>&1; then
    printf "${STY_YELLOW}sudo isn't available, so the sleep hook is skipped. Install ${SLEEP_HOOK_TARGET} by hand to use it.${STY_RST}\n"
    return 1
  fi
  local rendered
  rendered="$(mktemp)"
  # The hook runs as root but checks the user's own service, so it needs the user's name.
  sed "s/__USER__/$(whoami)/" "$SLEEP_HOOK_SOURCE" > "$rendered"
  v sudo install -Dm755 "$rendered" "$SLEEP_HOOK_TARGET"
  rm -f "$rendered"
  printf "${STY_BLUE}Sleep hook installed at ${SLEEP_HOOK_TARGET}.${STY_RST}\n"
}

install_sleep_hook
