# Summit's assets

## fonts/SummitSymbols.ttf

[Material Symbols Rounded](https://github.com/google/material-design-icons) by Google, Apache License 2.0
(`/licenses/Apache-2.0.txt` in this repository). Cut with fontTools to the icons Summit and its Rofi menus use, with
their name ligatures and all four of the variable font's axes (FILL, GRAD, opsz, wght), and named "Summit Symbols" so
it never stands in for the full font. Summit loads it itself (common/Theme.qml); `halcyon/summit/rofi-menu` copies it
to `~/.local/share/fonts/halcyon` for Rofi.

To add an icon: take the variable font from Google Fonts, add the icon's name to the list in the subsetting script
(subset with `layout_closure = False` and the `liga` feature, keeping the letters a-z, 0-9 and `_`), and replace the
file.

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
