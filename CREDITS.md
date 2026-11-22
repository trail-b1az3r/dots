# Credits

Halcyon is a layer on top of **end-4's illogical-impulse**. Most of what you see and use on the desktop
was written by end-4 and the illogical-impulse contributors. Halcyon adds a few keybinds, looks, themes and
the hyprland-plus compositor on top.

## end-4 and illogical-impulse

- **[end-4](https://github.com/end-4)** wrote illogical-impulse, the desktop this repository starts from:
  [dots-hyprland](https://github.com/end-4/dots-hyprland). That includes the Quickshell bar, sidebars,
  overview, search, notifications, lock screen, on-screen keyboard, AI sidebar, the installer and the
  Material You colour system.
- The **docs** for illogical-impulse are at [ii.clsty.link](https://ii.clsty.link), and they apply here.
- The **Google Sans Flex** font is packaged by end-4 at [end-4/google-sans-flex](https://github.com/end-4/google-sans-flex),
  which the installer fetches.
- The **rounded polygon shapes** used by the shell are a submodule from
  [end-4/rounded-polygon-qmljs](https://github.com/end-4/rounded-polygon-qmljs).
- The **package builds** for distributions other than Arch come from end-4's package repositories, which
  the installer's dependency router points to.

The dots are licensed under the GPL-3.0, like upstream. See [LICENSE](LICENSE).

## Hyprland and hyprland-plus

- **[Hyprland](https://github.com/hyprwm/Hyprland)** is by vaxerski and the Hyprland contributors, BSD-3-Clause.
- **[hyprland-plus](https://github.com/trail-b1az3r/hyprland-plus)** is Hyprland 0.57.0 with the Halcyon
  additions. Its own [CREDITS.md](https://github.com/trail-b1az3r/hyprland-plus/blob/main/CREDITS.md)
  lists the bundled code and its licences.

## Other projects

- **[Quickshell](https://git.outfoxxed.me/quickshell/quickshell)** by outfoxxed, which runs the shell.
- **Bibata** cursors, the default cursor in illogical-impulse. Its licence is in the upstream project.
- **Material Symbols**, Google's icon font, used in the shell. Its licence is in Google's distribution.
- **RightFont** by Right of the Bell ([video](https://youtu.be/NTY_yunv2To), [rightofthebell.com/fonts](https://www.rightofthebell.com/fonts)),
  made from Inter and Open Sans, SIL Open Font License: in `dots/.local/share/fonts/halcyon-rightfont` with its licence.
- **[jarvis-linux](https://github.com/DwizSharma/jarvis-linux)** by DwizSharma, MIT: the offline voice assistant
  (`halcyon jarvis`). Not bundled: `halcyon jarvis install` downloads it at a pinned commit.
- **[hyproled](https://github.com/mklan/hyproled)** by mklan, BSD-3-Clause: OLED burn-in care (`halcyon oled`). Bundled
  unchanged in `dots/.config/hypr/hyprland/halcyon/hyproled` with its licence.
- **[MacShell](https://github.com/0-ss/MacShell)** by Rickky (0-ss), MIT: the Liquid Glass theme's desktop shell
  (menu bar, Dock, Spotlight, Control Center and the Liquid Glass shader) and MacLock, its lock screen. Bundled in
  `dots/.config/quickshell/MacShell`, `dots/.config/quickshell/MacLock` and `dots/.config/hypr-macshell`, each with
  its licence; Halcyon adds a theme picker to `MacBar.qml` (Super+Shift+T). Its UI font, Open Runde, is under the SIL
  Open Font License.
- **[Iced](https://iced.rs)**, MIT: the GUI library of Summit's forecast window (`tools/halcyon-forecast`).
- **Weather and location services** the forecast uses, all without an account: [BeaconDB](https://beacondb.net)
  (where you are, from nearby Wi-Fi), [ipapi.co](https://ipapi.co) (from your IP address, when that fails),
  [Nominatim](https://nominatim.org) with © OpenStreetMap contributors' data (the place's name), and
  [Open-Meteo](https://open-meteo.com) (the forecast, CC BY 4.0).
- **Material Symbols Rounded**, Apache License 2.0: ten of its icons, cut to the Regular weight, are embedded in the
  forecast window (`tools/halcyon-forecast/assets`).

## Licences in this repository

Files from other projects keep their own licence notice. Copies of those licences are in
[licenses/](licenses/).


# Art Work
Wallpaper: "HyperNeo v2" (*Craggy peaks of Grand Teton National Park, Jackson, Wyoming*, Carol M. Highsmith,
Carol M. Highsmith Archive, Library of Congress, LCCN 2011633676), public domain; cropped to 2560×1440.
Source: [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Craggy_peaks_of_Grand_Teton_National_Park,_Jackson,_Wyoming_LCCN2011633676.tif)

Wallpaper: "red sun" (*Eclipse* by Alena Aenami, 2017)
Source: [wallhaven](https://wallhaven.vip/w/yjl8mk)

##### buy it [here](https://www.artstation.com/marketplace/p/oAol/wallpaper-pack-02)
