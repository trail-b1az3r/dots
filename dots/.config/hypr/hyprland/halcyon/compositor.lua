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

-- Why a feature is missing, in words, or nil when it is there.
function C.missing(feature)
    if C[feature] then
        return nil
    end
    if not C.plus then
        return "needs hyprland-plus"
    end
    return "needs a newer hyprland-plus (update it with: sudo hyprctl-lite install full)"
end

return C
