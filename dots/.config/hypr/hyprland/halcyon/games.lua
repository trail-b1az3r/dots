-- Games keep the keyboard when the pointer leaves them.
--
-- Focus follows the mouse (input:follow_mouse = 1), so a pointer that slips off a game (onto another monitor, or over
-- the bar) takes the focus with it, and most games pause or stop drawing when they lose focus: they look frozen.
-- While a game is the focused window, focus follows clicks instead (follow_mouse = 2): the pointer can go anywhere,
-- and the game keeps the keyboard until you click another window or use a keybind. Any other window brings the
-- usual behaviour back.
--
-- A game is a Steam game (steam_app_*), a window that says it is one (the content-type protocol: "game"), or one
-- with the tag "game" (window rules can add it: tag = "+game"). Settings > Halcyon > Games turns this off
-- (halcyon-theme games focus off writes HALCYON_GAME_FOCUS = false to ~/.local/state/halcyon/games.lua).

local M = {}

M.NORMAL = 1   -- general.lua's follow_mouse
M.GAME = 2

function M.is_game(window)
    if not window then
        return false
    end
    local class = window.class or window.initial_class or ""
    if type(class) == "string" and class:match("^steam_app_") then
        return true
    end
    if window.content_type == "game" then
        return true
    end
    local tags = window.tags
    if type(tags) == "table" then
        for _, tag in ipairs(tags) do
            if tag == "game" or tag == "game*" then
                return true
            end
        end
    end
    return false
end

function M.enabled()
    return rawget(_G, "HALCYON_GAME_FOCUS") ~= false
end

-- The follow_mouse a newly focused window calls for.
function M.follow_mouse_for(window)
    return (M.enabled() and M.is_game(window)) and M.GAME or M.NORMAL
end

if rawget(_G, "hl") and hl.on then
    local current = M.NORMAL
    hl.on("window.active", function(window)
        local wanted = M.follow_mouse_for(window)
        if wanted ~= current then
            current = wanted
            hl.config({ input = { follow_mouse = wanted } })
        end
    end)
end

return M
