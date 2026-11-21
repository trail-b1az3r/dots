# OLED care

OLED screens burn in where the same pixels stay lit for hours: a bar, a dock, a clock. Halcyon bundles
[hyproled](https://github.com/mklan/hyproled) by mklan (BSD-3-Clause), a screen shader that turns off some of every
2x2 block of pixels and moves them around, so no pixel stays lit all the time.

```sh
halcyon oled                     # on or off, and how
halcyon oled on                  # 1 of every 4 pixels dimmed, on the whole screen
halcyon oled on --pixels 2       # 2 of every 4 (darker; 3 is the most)
halcyon oled on --area 0:0:2560:48   # only the bar (x:y:width:height, in pixels)
halcyon oled on --monitor 1      # the OLED screen, by its id in `hyprctl monitors`
halcyon oled shift               # move the dimmed pixels now
halcyon oled off
```

- It stays on across logins, config reloads and theme changes, until `halcyon oled off`.
- `halcyon-oled.timer` moves the dimmed pixels every 15 minutes.
- Hyprland runs one screen shader at a time, so while OLED care is on, a theme's screen shader (Liquid Glass's tint,
  a theme's colour grade) gives way to it. `halcyon oled off` brings it back.
- hyproled uses `hyprctl eval` with the Lua config, which needs Hyprland 0.57: hyprland-plus is that.
