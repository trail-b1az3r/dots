# hyprland-plus

[hyprland-plus](https://github.com/trail-b1az3r/hyprland-plus) is Hyprland 0.56.2 with the
Halcyon additions. Its own README describes each one. The desktop uses:

- **Mini windows**, `SUPER + CTRL + N`: a window shrinks to a small floating tile.
- **Superposition windows**: Spotify stays on a thin strip at the right edge. A fullscreen window has the whole screen
  and the strip waits behind it (`superposition:over_fullscreen = false`); Settings > Halcyon > Plus Tiles >
  **Music strip over fullscreen** keeps it on top instead, covering that edge of the fullscreen window.
- **Plus Tiles**: terminals are ordinary tiles until you use Move Edge (`SUPER + ALT + E`) on one. Then you pick an
  edge, move it, see the preview and press Enter: the tiles sharing that edge adapt, and the tile keeps its custom
  size from then on. See [Plus Tiles](keybinds.md#plus-tiles) below.
- **Drag fix**: a tiled window keeps the grab point when it floats during a drag, so it does not jump.
  The drag guide tints the tile a dropped window would swap with.
- **Drop at the top to fullscreen**: hold `SUPER`, drag a window by its middle and let go at the very top of the
  screen, and it becomes fullscreen (`binds:drag_fullscreen_edge = 8`, the size of that strip in pixels; 0 turns it
  off, and Settings > Halcyon > Plus Tiles has it). A click is not a drag, and a window already at the top is left
  alone. `SUPER + F` still toggles fullscreen.

The settings are in `~/.config/hypr/hyprland/halcyon/plus.lua`. They only take effect with the fork, and each option
added after Plus Tiles is set only when the running build has it, so an older hyprland-plus loads the config without
errors (update it with `sudo hyprctl-lite install update` to get them).

hyprland-plus is not a command. It is Hyprland itself, built with the Halcyon additions, and it takes the place of
the `Hyprland` program. After installing it, log out and back in and start Hyprland as you always do. To check, run
`halcyon hyprland`, which says whether you run stock Hyprland, hyprland-plus, or a hyprland-plus built before Plus
Tiles (that one still has mini windows and the superposition strip; `sudo hyprctl-lite install update` updates it).
`hyprctl version` says `hyprland-plus` too. (`hyprctl dots plus` below uses `plus` as the name of a dot set, not a
command.)

On Arch, `./setup install` looks for hyprland-plus however it was installed: the AUR package (see `packaging/aur`
in the fork), or a build in `/usr/local` from hyprctl-lite or an earlier install. A build that is already up to date
is not built again; one behind its branch is updated. Otherwise the installer builds the fork on a text console of its
own and installs it to `/usr/local`, ahead of any packaged Hyprland in PATH. Set `HALCYON_SKIP_HYPRLAND_PLUS=1` to
skip that, or `HALCYON_REBUILD_HYPRLAND_PLUS=1` to rebuild anyway.

You do not need the stock `hyprland` package. pacman does not know about `/usr/local`, so when nothing in pacman
provides `hyprland`, the installer (and hyprctl-lite) adds a small empty package, `hyprland-plus-local`, that does.
Packages that depend on Hyprland, like `illogical-impulse-hyprland`, are then satisfied by the fork, and the stock
package is never pulled in beside it. `sudo pacman -R hyprland-plus-local` takes it away again.

Once hyprland-plus is running, `hyprctl dots plus` shows the dots checkout the installer recorded.
`hyprctl dots plus --install` runs `./setup install --force` in that checkout, without asking questions and without
building hyprland-plus again.

The same command installs other people's Hyprland dotfiles, and the base that Halcyon is built on. Run it in a terminal, because their installers ask questions:

| Command | Set | Installer |
|---|---|---|
| `hyprctl dots ii --install` | [illogical-impulse](https://github.com/end-4/dots-hyprland), end-4's desktop that Halcyon is built on | its `./setup install` |
| `hyprctl dots jakoolit --install` | [JaKooLit Hyprland-Dots](https://github.com/JaKooLit/Hyprland-Dots) | its `copy.sh` |
| `hyprctl dots mlfw --install` | [ML4W OS](https://github.com/mylinuxforwork/dotfiles) | ML4W's installer from ml4w.com |
| `hyprctl dots gdots --install` | [gdots](https://github.com/semi710/gdots) | copies its `.config` and `bin` |

`hyprctl dots <set>` without `--install` only describes what it would do. With `--install`, the set is cloned to
`~/.local/share/halcyon/dotsets/<set>` and left as it is upstream. Then the config it replaces is backed up to
`~/.local/state/halcyon/backups/<set>-<time>`, and its installer runs. Each set replaces the desktop's config in
`~/.config`, so `hyprctl dots plus --install` brings Halcyon back. Restore anything else from the backup by copying
it back by hand.

The ML4W installer also installs packages, and gdots does not install the packages its README lists. JaKooLit's
repository says it was archived in March 2026 and is now maintained at
[LinuxBeginnings/Hyprland-Dots](https://github.com/LinuxBeginnings/Hyprland-Dots).

### Saving and loading dots

`hyprctl store` saves the dot files as a `.dhyprsave` file, and `hyprctl load` loads one back:

| Command | Does |
|---|---|
| `hyprctl store -n <name>` | Saves the dot files as `~/.local/share/halcyon/saves/<name>.dhyprsave` |
| `hyprctl load -l` | Lists the saves. The one in use is marked `(active)` |
| `hyprctl load -n <name>` | Loads a save |
| `hyprctl load -a` | Loads the save before the latest switch, so running it again goes back |
| `sudo hyprctl load ...` | The same, but for the user who ran `sudo`, not root |

A `.dhyprsave` is a gzipped tar. It holds the entries of `~/.config` that the dot sets install, as they are now.
It also holds the `.local` files the config refers to: scripts in `~/.local/bin`, fonts, icons and themes, and the
Halcyon state files `theme.lua` and `placement.lua`. Nothing else in `~/.local` is saved. Its `manifest.txt` lists
what it holds.

Loading first backs up the files it replaces to `~/.local/state/halcyon/backups/before-load-<time>`. Each dot set
install, and each `hyprctl dots plus --install`, stores the dots it switched to, so `load -a` has something to go
back to. The first switch also stores the Halcyon desktop it replaces. Those automatic saves take disk space.

hyprctl-lite is a single script with two commands: `install full` installs or updates hyprland-plus, then removes
itself, and `install update` updates an installed hyprland-plus and stays for next time. On Arch, get it with this one
command:

```sh
curl -fsSL https://raw.githubusercontent.com/trail-b1az3r/dots/claude/youthful-gates-rt1csq-v2/tools/hyprctl-lite/hyprctl-lite | sudo tee /usr/local/bin/hyprctl-lite >/dev/null && sudo chmod 755 /usr/local/bin/hyprctl-lite
```

Then run:

```sh
sudo hyprctl-lite install full
```

It clones hyprland-plus into `~/hyprland-plus` (or updates that clone), installs the build dependencies from its
`packaging/aur/PKGBUILD`, builds it as your user, and installs it to `/usr/local`. It keeps the packaged Hyprland as
`/usr/bin/hyprland.official`. If a step fails, it stays in `/usr/local/bin` so you can run it again.

To update later:

```sh
hyprctl-lite install update --check   # is there an update? (no sudo; exit 0 up to date, 10 an update is waiting)
sudo hyprctl-lite install update      # get it
```

`install update` checks that hyprland-plus is installed in `/usr/local` (one from the AUR is updated by your AUR
helper), pulls `~/hyprland-plus`, and stops there when the installed build is already that commit. Otherwise it lists
the new commits, installs only build dependencies that are missing, builds and installs. hyprctl-lite stays in
`/usr/local/bin`, so the next update is the same command. `--force` builds again even when nothing changed.

The `curl` command runs a script from GitHub as root, so read it first if you prefer:
`curl -fsSL <the same URL> | less`. The script is short.
