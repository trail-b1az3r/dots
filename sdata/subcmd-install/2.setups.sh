# This script is meant to be sourced.
# It's not for directly running.

function prepare_systemd_user_service(){
  if [[ ! -e "/usr/lib/systemd/user/ydotool.service" ]]; then
    x sudo ln -s /usr/lib/systemd/{system,user}/ydotool.service
  fi
}

function setup_user_group(){
  if [[ -z $(getent group i2c) ]] && [[ "$OS_GROUP_ID" != "fedora" ]]; then
    # On Fedora this is not needed. Tested with desktop computer with NVIDIA video card.
    x sudo groupadd i2c
  fi

  if [[ "$OS_GROUP_ID" == "fedora" ]]; then
    x sudo usermod -aG video,input "$(whoami)"
  else
    x sudo usermod -aG video,i2c,input "$(whoami)"
  fi
}
#####################################################################################
# These python packages are installed using uv into the venv (virtual environment). Once the folder of the venv gets deleted, they are all gone cleanly. So it's considered as setups, not dependencies.
showfun install-python-packages
v install-python-packages

if [[ "$OS_GROUP_ID" == "nixos" ]]; then
  # The groups, i2c, ydotool, Bluetooth and power-profiles-daemon are set in the system module
  # (sdata/dist-nixos/halcyon.nix): changed here, the next rebuild would undo them.
  printf "${STY_CYAN}NixOS: groups and services come from the Halcyon module.${STY_RST}\n"
else
showfun setup_user_group
v setup_user_group
fi

if [[ "$OS_GROUP_ID" == "nixos" ]]; then
  true
elif [[ ! -z $(systemctl --version) ]]; then
  # For Fedora, uinput is required for the virtual keyboard to function, and udev rules enable input group users to utilize it.
  if [[ "$OS_GROUP_ID" == "fedora" ]]; then
    v bash -c "echo uinput | sudo tee /etc/modules-load.d/uinput.conf"
    v bash -c 'echo SUBSYSTEM==\"misc\", KERNEL==\"uinput\", MODE=\"0660\", GROUP=\"input\" | sudo tee /etc/udev/rules.d/99-uinput.rules'
  else
    v bash -c "echo i2c-dev | sudo tee /etc/modules-load.d/i2c-dev.conf"
  fi
  # TODO: find a proper way for enable Nix installed ydotool. When running `systemctl --user enable ydotool, it errors "Failed to enable unit: Unit ydotool.service does not exist".
  if [[ ! "${INSTALL_VIA_NIX}" == true ]]; then
    if [[ "$OS_GROUP_ID" == "fedora" ]]; then
      v prepare_systemd_user_service
    fi
    # When $DBUS_SESSION_BUS_ADDRESS and $XDG_RUNTIME_DIR are empty, it commonly means that the current user has been logged in with `su - user` or `ssh user@hostname`. In such case `systemctl --user enable <service>` is not usable. It should be `sudo systemctl --machine=$(whoami)@.host --user enable <service>` instead.
    if [[ ! -z "${DBUS_SESSION_BUS_ADDRESS}" ]]; then
      v systemctl --user enable ydotool --now
    else
      v sudo systemctl --machine=$(whoami)@.host --user enable ydotool --now
    fi
  fi
  # OpenRazer: its daemon is a user service that nothing starts by itself, so it never came up at login.
  # Enable it so it starts at every login. The daemon reaches the devices through the plugdev group.
  if [[ -f /usr/lib/systemd/user/openrazer-daemon.service || -f /usr/share/systemd/user/openrazer-daemon.service ]]; then
    if getent group plugdev >/dev/null && ! id -nG "$(whoami)" | tr ' ' '\n' | grep -qx plugdev; then
      v sudo gpasswd -a "$(whoami)" plugdev
      printf "${STY_YELLOW}Added you to plugdev for OpenRazer. Log out and back in once for it to apply.${STY_RST}\n"
    fi
    if [[ ! -z "${DBUS_SESSION_BUS_ADDRESS}" ]]; then
      v systemctl --user enable --now openrazer-daemon.service
    else
      v sudo systemctl --machine=$(whoami)@.host --user enable --now openrazer-daemon.service
    fi
  fi
  v sudo systemctl enable bluetooth --now
  # Power levels (power saver, balanced, performance) in the power menu and the quick toggles come from
  # power-profiles-daemon. It would fight TLP, auto-cpufreq or tuned over the same settings, so it is only added
  # where none of them is.
  if command -v pacman >/dev/null 2>&1 && ! pacman -Qq 2>/dev/null | grep -qxE 'tlp|auto-cpufreq|tuned'; then
    v sudo pacman -S --needed --noconfirm power-profiles-daemon
    v sudo systemctl enable --now power-profiles-daemon.service
  fi
elif [[ ! -z $(openrc --version) ]]; then
  v bash -c "echo 'modules=i2c-dev' | sudo tee -a /etc/conf.d/modules"
  v sudo rc-update add modules boot
  v sudo rc-update add ydotool default
  v sudo rc-update add bluetooth default

  x sudo rc-service ydotool start
  x sudo rc-service bluetooth start
elif [[ ! -z $(dinitctl --version 2>/dev/null) ]]; then
  # Modules loading
  v bash -c "echo i2c-dev | sudo tee -a /etc/modules"
  v bash -c "echo -e '-- Fix user Ydotool not working\nhl.env(\"YDOTOOL_SOCKET\", \"/tmp/.ydotool_socket\")' | tee -a \$HOME/.config/hypr/custom/env.lua"
  v bash -c "echo -e 'type = process\ncommand = /usr/bin/ydotoold\nlogfile = /var/log/dinit/ydotool.log\ndepends-on = dbus\nsmooth-recovery = true' | sudo tee /etc/dinit.d/ydotool"
  
  # Quick check for services to avoid "service already enabled" error"
  # System services
  for srv in userspawn bluetoothd ydotool; do
    if [ ! -e "/etc/dinit.d/boot.d/$srv" ]; then
      v sudo dinitctl enable "$srv"
    fi
  done

  # User services
  for usrv in pipewire wireplumber pipewire-pulse; do
    if [ ! -e "$HOME/.config/dinit.d/boot.d/$usrv" ]; then
      v dinitctl --user enable "$usrv"
    fi
  done
  
else
  printf "${STY_RED}"
  printf "====================INIT SYSTEM NOT FOUND====================\n"
  printf "${STY_RST}"
  pause
fi

if [[ "$OS_GROUP_ID" == "gentoo" ]]; then
  v sudo chown -R $(whoami):$(whoami) ~/.local/
fi

v gsettings set org.gnome.desktop.interface font-name 'Google Sans Flex Medium 11 @opsz=11,wght=500'
v gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
v kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle Darkly
