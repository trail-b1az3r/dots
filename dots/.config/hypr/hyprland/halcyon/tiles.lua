-- Tile resizing: the focused tile gives or takes space from the tiles around it.
--
--   SUPER + ALT + Right / Down   grow the tile to the right / down (its neighbours give up space)
--   SUPER + ALT + Left / Up      shrink the tile from the right / bottom edge
--
-- Hyprland's resize moves a tile's right and bottom edges only. Growing it to the left or up
-- needs the fork to move the left and top edges too, which is not in stock Hyprland.

local STEP = 40

hl.bind("SUPER + ALT + Right", hl.dsp.window.resize({ x = STEP, y = 0, relative = true }),
    { description = "Tile: Grow to the right" })
hl.bind("SUPER + ALT + Down", hl.dsp.window.resize({ x = 0, y = STEP, relative = true }),
    { description = "Tile: Grow down" })
hl.bind("SUPER + ALT + Left", hl.dsp.window.resize({ x = -STEP, y = 0, relative = true }),
    { description = "Tile: Shrink from the right" })
hl.bind("SUPER + ALT + Up", hl.dsp.window.resize({ x = 0, y = -STEP, relative = true }),
    { description = "Tile: Shrink from the bottom" })
