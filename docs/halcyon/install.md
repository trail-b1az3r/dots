# Install

```sh
git clone --recursive https://github.com/trail-b1az3r/dots.git halcyon
cd halcyon
./setup install
```

`--recursive` matters. The shell's shape widgets are a git submodule, and
without them Quickshell fails to load. If you already cloned without it:

```sh
git submodule update --init --recursive
```

Useful options (`./setup install -h` lists all of them):

| Option | Effect |
|---|---|
| `--skip-alldeps` | Only copy config. Don't install packages. |
| `--skip-wallpapers` | Don't copy wallpapers into `~/Pictures/Wallpapers`. |
| `--core` | Only Hyprland and Quickshell. Skip fish, fontconfig, misc app config and wallpapers. |

When logging in from a display manager, choose **Hyprland**, not
*Hyprland (uwsm)*.

### Automatic install, step by step

`./setup walkthrough` is the install with the steps shown as it goes. It lists the eight steps, asks once
whether to start, and then installs with no more questions. Each step prints `Step n of 8` as it runs.

The hyprland-plus step is automatic too. The screen switches to its own console, builds there, and switches
back to your desktop when it is done. Your sudo password is asked once in the terminal, and again on that
console, because sudo does not share its password across consoles. `./setup walkthrough -f` skips the question.

The switch back uses the console your session runs on (`XDG_VTNR`). If that is not set, it uses `fgconsole`.
If neither works, the installer says so and you switch back with Ctrl+Alt+F1 to F6.

`./setup uninstall` removes what the installer put in place.
