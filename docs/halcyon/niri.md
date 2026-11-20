# Halcyon on niri

The `niri` branch runs Halcyon on [niri](https://github.com/YaLTeR/niri), the scrollable-tiling compositor, as
well as on Hyprland. Pick **niri** at the login screen; Hyprland stays installed and works as before.

## What works

- **The Halcyon shell** (Quickshell, `~/.config/quickshell/ii`): bar, sidebars, search, clipboard, notifications,
  OSDs, wallpaper and its widgets, the theme picker, settings, the lock screen. It starts from niri's config through
  `halcyon-quickshell.service`, as on Hyprland.
- **The bar's workspaces and window title** follow niri (`services/Niri.qml`, which reads
  `niri msg --json event-stream`). Click a workspace to go to it, scroll to move up and down, right-click for niri's
  overview.
- **Themes**: `halcyon-theme apply` also writes `~/.config/niri/halcyon-theme.kdl` (gaps, the border as niri's focus
  ring, rounded corners, shadows), which niri reloads by itself. Neumorph has no ring: its shadows are its edges.
- **Locking**: Super+L, idle and sleep go through `halcyon/lock`, which uses the shell's lock over IPC on niri.

## What stays Hyprland's

- **MacShell** (the Liquid Glass theme's shell) needs Hyprland. On niri the theme's colours and look apply and the
  Halcyon shell stays.
- **The shell's own overview** (Super+Tab on Hyprland) is drawn from Hyprland's windows. On niri, Super+Tab, the
  top-left corner and a right-click on the workspaces open niri's overview instead.
- Hyprland Plus, the GPU guard, window rules written for Hyprland, and the Hyprland-only keys.

## Keys

The same as on Hyprland where niri has the same idea: Super+Space search, Super+V clipboard, Super+A / Super+N the
sidebars, Super+Return terminal, Super+E files, Super+W browser, Super+Q close, Super+1..9 workspaces,
Super+Shift+S screen snip, Super+L lock, Super+Escape session menu, Ctrl+Super+Shift+T themes, Super+I settings.
niri's own: Super+arrows move between columns and workspaces, Super+R column width, Super+F maximize the column,
Super+Shift+F fullscreen, Super+Tab overview. Super+Shift+/ shows niri's list of keys.

## Your changes

Put them in `~/.config/niri/custom.kdl`: it is included last, so it wins, and updates never touch it (they replace
`config.kdl` only, and `halcyon-theme.kdl` is the theme's). `niri validate` checks the whole config.

Packages: `illogical-impulse-niri` (`niri`, `xwayland-satellite`, `hypridle`, `wl-clipboard`, `cliphist`).
