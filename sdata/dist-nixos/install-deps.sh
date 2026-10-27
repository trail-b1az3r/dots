# This script is meant to be sourced.
# It's not for directly running.
#
# NixOS: Halcyon's dependencies, services and groups are a system module (halcyon.nix here), not packages installed
# one by one. This step copies the module to /etc/nixos/halcyon, imports it from configuration.nix (after a backup)
# or, on a flake system, says what to add, checks the configuration builds, and switches to it.
#
#   HALCYON_NIXOS_REBUILD=boot|switch|no   when to use it (default switch; no: only copy and import)

NIXOS_DIR="${HALCYON_NIXOS_DIR:-/etc/nixos}"
HALCYON_NIXOS_SRC="${REPO_ROOT}/sdata/dist-nixos"
HALCYON_NIXOS_TARGET="${NIXOS_DIR}/halcyon"

function nixos_copy_module(){
  local rendered
  rendered="$(mktemp)"
  # The resume hook runs as root but checks the user's own service, so it needs the user's name.
  sed "s/__USER__/$(whoami)/" "${REPO_ROOT}/dots/.config/hypr/hyprland/halcyon/sleep-hook" > "$rendered"
  x sudo install -d "${HALCYON_NIXOS_TARGET}"
  x sudo install -m644 "${HALCYON_NIXOS_SRC}/halcyon.nix" "${HALCYON_NIXOS_SRC}/packages.nix" "${HALCYON_NIXOS_TARGET}/"
  x sudo install -m755 "$rendered" "${HALCYON_NIXOS_TARGET}/sleep-hook"
  rm -f "$rendered"
}

function nixos_import_module(){
  local conf="${NIXOS_DIR}/configuration.nix"
  if [[ -f "${NIXOS_DIR}/flake.nix" ]]; then
    printf "${STY_YELLOW}This system is configured with a flake (${NIXOS_DIR}/flake.nix), which this installer doesn't edit.\n"
    printf "Add Halcyon's module to your system's modules, then rebuild:\n\n${STY_RST}"
    printf "    modules = [ ... ${HALCYON_NIXOS_TARGET}/halcyon.nix { halcyon = { enable = true; user = \"$(whoami)\"; }; } ];\n\n"
    printf "${STY_YELLOW}(or, as an input: halcyon.url = \"github:trail-b1az3r/dots?dir=sdata/dist-nixos\"; and halcyon.nixosModules.default)\n${STY_RST}"
    NIXOS_USES_FLAKE=true
    return 0
  fi
  if [[ ! -f "$conf" ]]; then
    printf "${STY_RED}${conf} doesn't exist. Import ${HALCYON_NIXOS_TARGET}/halcyon.nix from your configuration and set halcyon = { enable = true; user = \"$(whoami)\"; };${STY_RST}\n"
    return 1
  fi
  if grep -q 'halcyon/halcyon\.nix' "$conf"; then
    echo "${conf} already imports Halcyon."
    return 0
  fi
  local edited
  edited="$(mktemp)"
  bash "${HALCYON_NIXOS_SRC}/edit-configuration.sh" "$conf" "$(whoami)" > "$edited" || { rm -f "$edited"; return 1; }
  if command -v nix-instantiate >/dev/null && ! nix-instantiate --parse "$edited" >/dev/null 2>&1; then
    printf "${STY_RED}Adding Halcyon to ${conf} would break it, so it is left alone. Add it by hand:${STY_RST}\n"
    printf "    imports = [ ./halcyon/halcyon.nix ... ];\n    halcyon = { enable = true; user = \"$(whoami)\"; };\n"
    rm -f "$edited"
    return 1
  fi
  x sudo cp "$conf" "${conf}.halcyon-backup-$(date +%Y%m%d-%H%M%S)"
  printf "${STY_CYAN}The change to ${conf}:${STY_RST}\n"
  diff -u "$conf" "$edited" || true
  x sudo install -m644 "$edited" "$conf"
  rm -f "$edited"
}

function nixos_rebuild(){
  local when="${HALCYON_NIXOS_REBUILD:-switch}"
  if [[ "$when" == "no" ]]; then
    printf "${STY_YELLOW}Not rebuilding (HALCYON_NIXOS_REBUILD=no). Run: sudo nixos-rebuild switch${STY_RST}\n"
    return 0
  fi
  local flake_args=()
  [[ "${NIXOS_USES_FLAKE:-false}" == true ]] && flake_args=(--flake "${NIXOS_DIR}#$(hostname)")
  # Build first: a typo or a package nixpkgs renamed fails here, before anything changes.
  v sudo nixos-rebuild dry-build "${flake_args[@]}"
  v sudo nixos-rebuild "$when" "${flake_args[@]}"
}

function nixos_report(){
  local missing=()
  for cmd in qs Hyprland hyprctl matugen fuzzel cliphist wl-copy grim slurp hyprlock hypridle ffmpeg magick uv brightnessctl playerctl; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if (( ${#missing[@]} )); then
    printf "${STY_YELLOW}Not on PATH yet: ${missing[*]}. After a rebuild with 'boot', or in this shell, log out and back in.${STY_RST}\n"
  else
    printf "${STY_GREEN}Everything Halcyon runs is installed.${STY_RST}\n"
  fi
  printf "${STY_CYAN}hyprland-plus (Halcyon's Hyprland fork) isn't built on NixOS: the module uses nixpkgs' Hyprland, which\n"
  printf "Halcyon works with. Groups (video, input, i2c, ydotool) apply from your next login.${STY_RST}\n"
}

##################################################

printf "${STY_CYAN}NixOS: Halcyon is installed as a system module in ${HALCYON_NIXOS_TARGET}.${STY_RST}\n"
showfun nixos_copy_module
v nixos_copy_module
showfun nixos_import_module
v nixos_import_module
showfun nixos_rebuild
v nixos_rebuild
nixos_report
