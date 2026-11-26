# Summit's assets

## fonts/SummitSymbols.ttf

[Material Symbols Rounded](https://github.com/google/material-design-icons) by Google, Apache License 2.0
(`/licenses/Apache-2.0.txt` in this repository). Cut with fontTools to the icons Summit and its Rofi menus use, with
their name ligatures and all four of the variable font's axes (FILL, GRAD, opsz, wght). It is named "Summit Symbols
v3": the family carries the cut's version, so it never stands in for the full font, and an older cut still installed
(the package's, or a copy in ~/.local/share/fonts) never stands in for it: Qt and fontconfig took an installed font
of the same family over the file Summit loads, and the new icons showed as their names. Summit loads it itself
(common/Theme.qml); `halcyon/summit/rofi-menu` copies it to `~/.local/share/fonts/halcyon` for Rofi.

To add an icon: add its name to `NAMES` in `tools/summit-symbols/subset.py`, raise the version in its `FAMILY` (and
in `halcyon/summit/summit.rasi` and `rofi-menu`, which name it), and cut it from the variable font
(`variablefont/` in github.com/google/material-design-icons): `subset.py VARIABLE.ttf OUT.ttf`.

## fonts/SummitSans.ttf

Summit Sans, Summit's text font: [Google Sans Flex](https://github.com/googlefonts/googlesans-flex) (from
github.com/google/fonts, `ofl/googlesansflex`), modified with fontTools: its rounded ends (ROND) set all the way, as
Summit's icons are, and its slant and width fixed at upright and normal (dropping those axes); weight and optical
size stay variable. SIL Open Font License 1.1 (`SummitSans-OFL.txt`; it has no Reserved Font Name). It is renamed
because "Google Sans" is a trademark of Google LLC that a modified version may not carry; it is not affiliated with
or endorsed by Google. `tools/summit-fonts/make_sans.py` makes it from the variable font.

## model/importance.json

The weights of the notification importance model (`services/importance.js` runs it): written by
`tools/summit-importance/train.py`; docs/halcyon/themes.md says what it does and how well.
