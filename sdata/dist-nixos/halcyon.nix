# Halcyon (and illogical-impulse) on NixOS, as a system module.
#
# ./setup install puts this folder in /etc/nixos/halcyon and imports it from configuration.nix:
#
#   imports = [ ./hardware-configuration.nix ./halcyon/halcyon.nix ];
#   halcyon = { enable = true; user = "you"; };
#
# With a flake, add this repository's sdata/dist-nixos flake as an input and its nixosModules.default to your
# system's modules instead (see README.md here). The dotfiles themselves are copied to ~/.config by ./setup as on
# any other distribution, so they stay yours to edit, with no rebuild for each change.
{ config, lib, pkgs, ... }:

let
  cfg = config.halcyon;
in
{
  options.halcyon = {
    enable = lib.mkEnableOption "Halcyon, end-4's illogical-impulse with Halcyon's themes, on Hyprland";

    user = lib.mkOption {
      type = lib.types.str;
      example = "alice";
      description = "Your user name: it is added to the groups the shell needs (video, input, i2c, ydotool).";
    };

    quickshell = lib.mkOption {
      type = lib.types.package;
      default = pkgs.quickshell;
      defaultText = lib.literalExpression "pkgs.quickshell";
      description = "The Quickshell to run the shell with.";
    };

    extraPackages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      description = "More packages to install with Halcyon's.";
    };

    sleepHook = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = if builtins.pathExists ./sleep-hook then ./sleep-hook else null;
      defaultText = lib.literalExpression "./sleep-hook, when ./setup install wrote it";
      description = ''
        Halcyon's resume hook (it brings NetworkManager and the Razer daemon back after sleep when the user's own
        halcyon-resume service isn't running). Run from powerManagement.resumeCommands.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    # Hyprland, its portal and a login entry for it.
    programs.hyprland = {
      enable = true;
      xwayland.enable = true;
    };
    xdg.portal = {
      enable = true;
      extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
    };

    # Sound, Bluetooth, networks, power levels, batteries, location (the sun dial and weather), the keyring.
    services.pipewire = {
      enable = true;
      alsa.enable = true;
      pulse.enable = true;
      wireplumber.enable = true;
    };
    hardware.bluetooth.enable = lib.mkDefault true;
    networking.networkmanager.enable = lib.mkDefault true;
    services.power-profiles-daemon.enable = lib.mkDefault (!config.services.tlp.enable && !config.services.auto-cpufreq.enable);
    services.upower.enable = true;
    services.geoclue2.enable = true;
    services.gnome.gnome-keyring.enable = true;
    security.polkit.enable = true;

    # The lock screen's password check, and the virtual keyboard and brightness of external screens.
    security.pam.services.hyprlock = { };
    programs.ydotool.enable = true;
    hardware.i2c.enable = true;

    # The shell's Python helpers live in a uv environment; nix-ld lets that Python (and the wheels it installs) run.
    programs.nix-ld = {
      enable = true;
      libraries = with pkgs; [ stdenv.cc.cc.lib zlib glib libGL cairo gdk-pixbuf gtk4 pango harfbuzz freetype fontconfig ];
    };

    programs.fish.enable = lib.mkDefault true;
    programs.dconf.enable = true;

    users.users.${cfg.user}.extraGroups = [ "video" "input" "i2c" "ydotool" "networkmanager" ];

    fonts.packages = with pkgs; [
      rubik material-symbols nerd-fonts.jetbrains-mono twemoji-color-font noto-fonts noto-fonts-cjk-sans noto-fonts-color-emoji
    ];

    environment.systemPackages = (import ./packages.nix pkgs) ++ [ cfg.quickshell ] ++ cfg.extraPackages;

    # gsettings and the Qt image plugins the shell loads.
    environment.sessionVariables.QT_QPA_PLATFORMTHEME = lib.mkDefault "qt6ct";
    qt.enable = true;

    powerManagement.resumeCommands = lib.mkIf (cfg.sleepHook != null) ''
      ${pkgs.bash}/bin/bash ${cfg.sleepHook} post suspend || true
    '';
  };
}
