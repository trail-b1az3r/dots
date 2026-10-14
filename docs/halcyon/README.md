# Halcyon docs

A Hyprland desktop built on [end-4's dots-hyprland](https://github.com/end-4/dots-hyprland)
(illogical-impulse), with a small layer of our own on top.

The earlier Halcyon was a desktop written from scratch: a Python theme
generator, its own Quickshell shell and its own installer. It broke, so
this repository now starts from end-4's desktop, which is maintained and
known to work, and keeps Halcyon's own changes in one place on top of it.


## What you get

Everything illogical-impulse provides: the Quickshell bar and sidebars,
overview, search, notifications, lock screen, on-screen keyboard, AI
sidebar, Material You colours taken from your wallpaper, and the
installer for Arch, Fedora, Gentoo and Nix. See the
[illogical-impulse docs](../illogical-impulse/README.md) for all of it. Those docs
apply here unchanged.

On top of that, Halcyon adds:

| | |
|---|---|
| **Glass panels** | Shell transparency is on by default. It can still be turned off in Settings. |
| **Softer layout** | Wider gaps, rounder corners, deeper blur (popups too), a softer shadow. |
| **Wallpapers** | The hyperNeo fire wallpaper is the default. It and the three Halcyon wallpapers are copied into `~/Pictures/Wallpapers`, where the wallpaper picker looks. |
| **Themes** | Five hand-made themes: HyperNeo, Star Rail, Shattered Glass, Fractured Glass and Red Sun. [More below.](themes.md) |
| **Voice assistant** | Press `Super + Shift + Space` and speak. It answers aloud and can run the desktop. [More below.](voice-assistant.md) |
| **Keybinds** | Extra shortcuts, listed below. They only use key combinations upstream leaves free. |
| **hyprland-plus** | The compositor is [hyprland-plus](https://github.com/trail-b1az3r/hyprland-plus): Hyprland 0.56.2 with mini windows, superposition windows, plustile windows and a drag fix. [More below.](hyprland-plus.md) |

## Pages

| Page | What's in it |
|---|---|
| [Install](install.md) | Installing Halcyon, the walkthrough, options and uninstall |
| [hyprland-plus](hyprland-plus.md) | The compositor fork, dot sets, saves, and hyprctl-lite |
| [Themes](themes.md) | The five themes, effects, cursor, banners, and making your own |
| [Voice assistant](voice-assistant.md) | Setup, the Claude plan, what it can do |
| [Keybinds](keybinds.md) | The shortcuts Halcyon adds, and Hypr mode |
| [Architecture](architecture.md) | How the config is laid out, and taking updates from upstream |
| [Development](development.md) | Validation, releases |
| [illogical-impulse](../illogical-impulse/README.md) | The desktop Halcyon is built on, ported from end-4's docs |

## Credits and licence

Most of this desktop is the work of **[end-4](https://github.com/end-4)**, who
made illogical-impulse ([dots-hyprland](https://github.com/end-4/dots-hyprland)):
the Quickshell bar, sidebars, overview, search, the installer, the Material You
colour system and the docs at [ii.clsty.link](https://ii.clsty.link). Thank you,
end-4, and to everyone who contributes to that project. Halcyon is a small layer
on top of it.

The full list, with the other projects and licences, is in [CREDITS.md](../../CREDITS.md).

Licensed under the GPL-3.0, like upstream. See [LICENSE](../../LICENSE). Some parts
carry their own licences, listed in [licenses/](../../licenses/).
