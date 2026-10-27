# Halcyon on NixOS

`./setup install` on NixOS installs Halcyon's dependencies the NixOS way: as a system module, not package by
package. (`sdata/dist-nix` is something else: Nix and home-manager on *other* distributions.)

What it does:

1. Copies `halcyon.nix` and `packages.nix` (and the resume hook) to `/etc/nixos/halcyon/`.
2. Imports the module from `/etc/nixos/configuration.nix`, after a backup next to it
   (`configuration.nix.halcyon-backup-DATE`), showing the change:
   ```nix
   imports = [ ./halcyon/halcyon.nix ./hardware-configuration.nix ];
   halcyon = { enable = true; user = "you"; };
   ```
   A system configured with a flake isn't edited: the installer prints the lines to add.
3. `sudo nixos-rebuild dry-build`, then `switch` (`HALCYON_NIXOS_REBUILD=boot` to use it from the next boot,
   `=no` to only copy and import).
4. The rest of `./setup` as everywhere else: the dotfiles are copied to `~/.config`, so they stay yours to edit, with
   no rebuild for each change.

The module turns on Hyprland and its portal, PipeWire, Bluetooth, NetworkManager, power-profiles-daemon (unless TLP
or auto-cpufreq is on), UPower, GeoClue, the GNOME keyring, polkit, hyprlock's PAM entry, ydotool and i2c (with your
user in their groups), nix-ld (the shell's Python helpers run in a uv environment), the fonts, and every package
in `packages.nix`. Options:

| Option | Default | |
|---|---|---|
| `halcyon.enable` | `false` | |
| `halcyon.user` | | your user name, for the groups |
| `halcyon.quickshell` | `pkgs.quickshell` | the Quickshell to run |
| `halcyon.extraPackages` | `[ ]` | more packages |
| `halcyon.sleepHook` | `./sleep-hook` | the resume hook, run from `powerManagement.resumeCommands` |

## With a flake

```nix
inputs.halcyon.url = "github:trail-b1az3r/dots?dir=sdata/dist-nixos";
# ...
nixosConfigurations.box = nixpkgs.lib.nixosSystem {
  modules = [ ./configuration.nix halcyon.nixosModules.default { halcyon = { enable = true; user = "you"; }; } ];
};
```

Then `./setup install` for the dotfiles (it notices the flake and leaves `/etc/nixos` alone).

## Checking the module

```sh
nix flake check ./sdata/dist-nixos     # builds a small test system with it
```

hyprland-plus, Halcyon's Hyprland fork, isn't built on NixOS; nixpkgs' Hyprland is used, and Halcyon works with it.
