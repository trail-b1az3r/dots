# Troubleshooting

## Start here

```sh
./diagnose.sh          # versions, services, config errors, hardware
halcyon doctor         # the same checks from the CLI
halcyon doctor --json  # machine-readable, for a bug report
```

`diagnose.sh` reports Hyprland, Quickshell and Waybar versions, which
services are running, the detected GPU and power backend, any Hyprland
config errors, and which optional dependencies are missing.

## The desktop does not start

**Nothing appears after logging in.**

```sh
journalctl --user -u halcyon-session.target -n 50
journalctl --user -u halcyon-shell -n 50
hyprctl configerrors
```

**Hyprland starts but the desktop is bare.** The generated files failed
to load. `generated.lua` will have bound `Super + Return` for a
terminal, `Super + W` to close a window and `Super + Ctrl + Escape` to
log out, and raised a notification saying so. From that terminal:

```sh
halcyon theme apply
hyprctl reload
```

**Checking the config without Hyprland running** — from a TTY, or over
SSH:

```sh
./scripts/dev/check-hypr-config.py
```

This loads the real configuration against a stand-in `hl` table and
reports every option, bind, animation and rule it would set.

## The bar or shell is missing

```sh
systemctl --user status halcyon-bar halcyon-shell
```

Run the shell in the foreground to see QML errors, which the journal
truncates:

```sh
systemctl --user stop halcyon-shell
qs -c halcyon
```

Waybar the same way:

```sh
systemctl --user stop halcyon-bar
waybar -c ~/.config/halcyon/generated/waybar-config.jsonc \
       -s ~/.config/waybar/style.css
```

**A module is missing from the bar.** Waybar silently drops a module it
has no definition for. Every name in `bar.left`/`center`/`right` must
exist in `config/waybar/modules.jsonc` or be a Waybar builtin —
`./scripts/dev/validate.sh` checks this.

## Appearance

**A change did not take effect.** Settings do not reach the desktop
until they are regenerated:

```sh
halcyon theme apply --json     # what was written, and what reloaded
```

**Colours look wrong.** Check the token document first — the renderers
only project what is in it:

```sh
python3 -m json.tool ~/.config/halcyon/generated/theme.json | head -40
```

**The accent is not what I set.** `appearance.accentSource` must be
`fixed` for `accentColor` to be used; with `wallpaper` it is derived
from the image.

**Text is blurry on a scaled display.** Set the scale per monitor in
`displays.monitors` rather than relying on `defaultScale: auto`.

**Fonts look wrong.** `appearance.fontUi` must name an installed
family — `fc-list | grep -i inter`. Icon glyphs need a Nerd Font;
without one the bar shows boxes.

## Performance

Blur is the expensive part. In order of effect:

```sh
halcyon settings set graphics.blurQuality low
halcyon settings set glass.preset clear
halcyon settings set graphics.renderUnfocusedFps 5
halcyon settings set graphics.lowPowerGraphics true
halcyon settings set motion.preset fast
```

`ultra-clear` is the *heaviest* preset, not the lightest — blur has
nothing to hide behind, so more of it shows.

**Stuttering on a laptop.** Check the power profile and whether the
adaptive policy has already stepped things down:

```sh
halcyon power status
```

## Power

**Two power daemons.** `halcyon doctor` names them. Pick one:

```sh
systemctl disable --now tlp          # or power-profiles-daemon, or tuned
```

Halcyon refuses to configure either while both are running, rather than
adding a third opinion.

**Profile changes do nothing.** `halcyon power status` shows the
detected backend. `none` means none is installed. Set one explicitly if
detection is wrong:

```sh
halcyon settings set power.backend power-profiles-daemon
```

**The battery percentage is wrong on a two-battery laptop.** Halcyon
sums by energy rather than averaging percentages — if it still looks
wrong, `ls /sys/class/power_supply/` and check what the kernel reports.

## Graphics

**NVIDIA.** GPU environment variables are only written when the
proprietary driver is actually loaded. After installing it:

```sh
./install.sh --config-only
```

To see what was detected:

```sh
./diagnose.sh | grep -i gpu
```

To stop Halcyon setting GPU variables at all:

```sh
halcyon settings set graphics.gpuOverrides none
```

**Screen sharing does not work.** `xdg-desktop-portal-hyprland` must be
running, and it must be the portal picked for the screencast interface:

```sh
systemctl --user status xdg-desktop-portal-hyprland
```

## The assistant

See [the assistant guide](assistant.md#troubleshooting) for the full
list.

```sh
halcyon assistant status
halcyon assistant providers
journalctl --user -u halcyon-assistant -n 50
```

## Search

**No application results.** The provider reads `.desktop` files from the
XDG data directories. `ls ~/.local/share/applications /usr/share/applications`.

**No file results.** Check `search.fileRoots` and `search.fileDepth`.
The default depth is 4.

**Currency conversion says no rates are available.** It needs
`assistant.privacy.allowWebAccess` — nothing reaches the network on a
keystroke unless you turn that on.

## Recovering

**Undo the last install:**

```sh
./restore.sh --list
./restore.sh --show latest
./restore.sh latest
```

**Remove Halcyon and restore what it replaced:**

```sh
./uninstall.sh --dry-run
./uninstall.sh
```

**Reset settings without uninstalling:**

```sh
mv ~/.config/halcyon/settings.json ~/.config/halcyon/settings.json.bak
halcyon theme apply
```

## Reporting a problem

```sh
./diagnose.sh > halcyon-report.txt
```

The report contains versions, service states, detected hardware and
configuration errors. Read it before sending — it includes your
hostname and monitor names.
