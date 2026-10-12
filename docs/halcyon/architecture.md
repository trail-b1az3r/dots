# Architecture

```
dots/.config/hypr/
├── hyprland.lua            entry point: upstream, then Halcyon, then yours
├── hyprland/               upstream defaults (replaced on every install)
│   └── halcyon/            ← the Halcyon layer
│       ├── init.lua          what gets loaded; comment a line out to drop it
│       ├── general.lua       gaps, rounding, blur, shadow
│       ├── keybinds.lua      the extra shortcuts
│       ├── halcyon-theme     the theme tool (the `halcyon` command)
│       ├── halcyon-banner    composes banner art into a wallpaper
│       ├── assistant/        the voice assistant (halcyon-assistant + its Python package)
│       └── themes/           one JSON per theme, their wallpapers and shaders
└── custom/                 your own overrides (never overwritten)
wallpapers/                 copied to ~/Pictures/Wallpapers on install
```

Load order is **upstream defaults → Halcyon → active theme →
`~/.config/hypr/custom`**. The active theme's window style is written to
`~/.local/state/halcyon/theme.lua`.
Anything you put in `custom/` wins over both, so put your changes there,
not in `hyprland/`. The installer replaces `hyprland/` every time.

Outside that folder, Halcyon changes very little in upstream's files:

- `quickshell/ii/modules/common/Config.qml`: transparency on by default
- `quickshell/ii/services/FirstRunExperience.qml`: the welcome text
- `quickshell/ii/assets/images/default_wallpaper.png`: the default wallpaper
- `quickshell/ii/scripts/colors/switchwall.sh`: one line, so a wallpaper change leaves the active theme
- `quickshell/ii/modules/common/Config.qml`: the `halcyon` settings, and `settings.qml` plus `modules/settings/HalcyonConfig.qml` for the Halcyon settings page
- `fish/config.fish` and `zshrc.d/dots-hyprland.zsh`: the `halcyon` alias
- `setup` and `sdata/subcmd-install/`: the wallpaper step, `--skip-wallpapers`, and Halcyon's name in the greeting

Keeping it this small is deliberate: it keeps fixes from upstream easy
to take.

```sh
git remote add upstream https://github.com/end-4/dots-hyprland.git
git fetch upstream
git merge upstream/main
git submodule update --init --recursive
./setup install
```

Conflicts, if any, will be in the few files listed above.
