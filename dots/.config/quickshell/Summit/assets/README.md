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
