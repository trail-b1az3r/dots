#!/usr/bin/env bash
# Builds the Halcyon Hyprland fork (hyprland-plus) and installs it in place of the packaged Hyprland.
# ./setup install runs this on a text console of its own (see sdata/subcmd-install/8.hyprland-plus.sh),
# so the compositor can be replaced without the graphical session running it. It runs as your user;
# the steps that need root call sudo, and sudo asks for your password on this console.
#
#   HALCYON_HYPRLAND_REPO   where the source lives (default ~/hyprland-plus)
#   HALCYON_HYPRLAND_REF    branch to build (default halcyon-0.56.2)
#
# Exit status 0 when hyprland-plus is installed. On failure the console stays open until you press Enter,
# so the error can be read.

REPO="${HALCYON_HYPRLAND_REPO:-$HOME/hyprland-plus}"
REF="${HALCYON_HYPRLAND_REF:-halcyon-0.56.2}"
URL="https://github.com/trail-b1az3r/hyprland-plus"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"

step(){ printf '\n\033[36m==> %s\033[0m\n' "$*"; }

fail(){
    printf '\n\033[31m%s\033[0m\n' "$*"
    printf 'The packaged Hyprland is still installed. Press Enter to close this console.\n'
    read -r _
    exit 1
}

step "Installing the build tools"
sudo pacman -S --needed --noconfirm git cmake base-devel || fail "Could not install git, cmake and base-devel."

if [[ -d "$REPO/.git" ]]; then
    step "Updating $REPO to $REF"
    git -C "$REPO" fetch origin "$REF" || fail "Could not fetch $REF."
    git -C "$REPO" checkout "$REF" || fail "Could not check out $REF."
    git -C "$REPO" pull --ff-only origin "$REF" || fail "$REPO has local changes that stop the update. Commit or stash them, then run ./setup install again."
else
    step "Cloning $URL ($REF) into $REPO"
    git clone --branch "$REF" "$URL" "$REPO" || fail "Could not clone $URL."
fi
git -C "$REPO" submodule update --init --recursive || fail "Could not fetch the submodules."

step "Building hyprland-plus (this takes a while)"
make -C "$REPO" all || fail "hyprland-plus did not build. Read the first error above."

# The packaged Hyprland is not removed: illogical-impulse-hyprland and others depend on it.
# hyprland-plus goes to /usr/local/bin, which comes before /usr/bin in PATH, so it is the one that runs.
if pacman -Q hyprland >/dev/null 2>&1 && [[ -e /usr/bin/hyprland && ! -e /usr/bin/hyprland.official ]]; then
    step "Keeping a copy of the packaged Hyprland binary"
    sudo cp /usr/bin/hyprland /usr/bin/hyprland.official || fail "Could not copy /usr/bin/hyprland."
fi

step "Installing hyprland-plus"
sudo make -C "$REPO" install || fail "make install failed."
sudo ln -sf /usr/local/bin/Hyprland /usr/local/bin/hyprland
if [[ "$(command -v Hyprland)" != /usr/local/bin/Hyprland ]]; then
    printf '\033[33mPATH finds %s first, not /usr/local/bin/Hyprland. Put /usr/local/bin before /usr/bin in PATH.\033[0m\n' "$(command -v Hyprland)"
fi

# pacman does not know about /usr/local. Without this, packages that depend on hyprland would pull the stock
# hyprland package in beside the fork.
source "$(dirname "$(readlink -f "$0")")/hyprland-plus-detect.sh"
hyprland_plus_register_with_pacman || true

mkdir -p "$STATE"
git -C "$REPO" rev-parse --short HEAD > "$STATE/hyprland-plus-commit"
printf '\n\033[32mInstalled hyprland-plus %s from %s.\033[0m\n' "$(cat "$STATE/hyprland-plus-commit")" "$REF"
exit 0
