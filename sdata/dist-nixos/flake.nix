# Halcyon as a NixOS module, for systems configured with a flake:
#
#   inputs.halcyon.url = "github:trail-b1az3r/dots?dir=sdata/dist-nixos";
#   ...
#   modules = [ ./configuration.nix halcyon.nixosModules.default { halcyon = { enable = true; user = "you"; }; } ];
#
# `nix flake check` here builds a small test system with it, to catch a package or option nixpkgs renamed.
{
  description = "Halcyon (illogical-impulse with Halcyon's themes) on NixOS";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }: {
    nixosModules.default = import ./halcyon.nix;
    nixosModules.halcyon = self.nixosModules.default;

    # A minimal system with Halcyon on, for checking that the module evaluates.
    nixosConfigurations.halcyon-check = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        self.nixosModules.default
        {
          halcyon = { enable = true; user = "halcyon"; };
          users.users.halcyon = { isNormalUser = true; };
          boot.loader.grub.device = "nodev";
          fileSystems."/" = { device = "/dev/disk/by-label/nixos"; fsType = "ext4"; };
          system.stateVersion = "25.11";
        }
      ];
    };

    checks.x86_64-linux.module = self.nixosConfigurations.halcyon-check.config.system.build.toplevel;
  };
}
