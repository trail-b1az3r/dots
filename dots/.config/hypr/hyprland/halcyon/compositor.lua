-- What the running Hyprland can do.
--
-- hyprland-plus gained its features over several builds, so each one is checked by the Lua names it adds rather
-- than by a single "is this hyprland-plus" test. A hyprland-plus built before Plus Tiles is still hyprland-plus: it
-- gets mini windows and the superposition strip, and only the newer parts are skipped.
--
--   plus    any hyprland-plus build (hl.dsp.window.mini)
--   strips  the superposition strip and the plustile window rule (hl.dsp.window.fit_plustile)
--   tiles   Plus Tiles with Move Edge, Fit to Neighbors and plus:* options (hl.dsp.plus)

local dsp = (hl and hl.dsp) or {}
local window = dsp.window or {}

local C = {}
C.tiles = dsp.plus ~= nil
C.strips = C.tiles or window.fit_plustile ~= nil
C.plus = C.strips or window.mini ~= nil

-- Options added after Plus Tiles. hl.get_config answers nil for a key this build does not have, and setting one it
-- does not have would be a config error, so each is asked for first.
local function hasOption(key)
    if not (hl and hl.get_config) then
        return false
    end
    local ok, value = pcall(hl.get_config, key)
    return ok and value ~= nil
end
C.dragEdge = hasOption("binds:drag_fullscreen_edge")           -- drop a dragged window at the top edge: fullscreen
C.stripFullscreen = hasOption("superposition:over_fullscreen") -- the strip can be kept out of fullscreen windows
C.monitorWall = hasOption("plus:monitor_wall")                -- a dragged window stops at the edge of another monitor
C.maxFps = hasOption("plus:max_fps")                          -- the screen can be drawn less often (battery saver)

-- Why a feature is missing, in words, or nil when it is there.
function C.missing(feature)
    if C[feature] then
        return nil
    end
    if not C.plus then
        return "needs hyprland-plus"
    end
    return "needs a newer hyprland-plus (update it with: sudo hyprctl-lite install update)"
end

return C
