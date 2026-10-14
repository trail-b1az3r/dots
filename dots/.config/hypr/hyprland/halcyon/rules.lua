-- Turns the smart window rules in app_rules.lua (or ~/.config/hypr/custom/app_rules.lua) into window rules.
--
-- Native fields become native Hyprland rule effects. Plus fields become the hyprland-plus effects. Each is skipped
-- quietly when the running Hyprland lacks it (compositor.lua says which build has what), so the rules shipped with
-- Halcyon never warn on stock Hyprland or an older hyprland-plus. `halcyon config-check` lists what was skipped.
-- Unknown fields and wrong values are reported once, in a notification, and the rest of the entry still applies,
-- so one typo does not lose a whole rule.

local M = {}

-- field -> function(value, effects, problems) that adds rule effects
local NATIVE = {
    workspace = function(v, fx, bad)
        if type(v) == "number" or type(v) == "string" then fx.workspace = tostring(v) else bad("workspace must be a number or a name") end
    end,
    float = function(v, fx, bad) if type(v) == "boolean" then fx.float = v else bad("float must be true or false") end end,
    tile = function(v, fx, bad) if type(v) == "boolean" then fx.tile = v else bad("tile must be true or false") end end,
    center = function(v, fx, bad) if type(v) == "boolean" then fx.center = v else bad("center must be true or false") end end,
    monitor = function(v, fx, bad) if type(v) == "string" then fx.monitor = v else bad("monitor must be a name, like \"DP-1\"") end end,
    title_bar = function(v, fx, bad) if type(v) == "boolean" then fx.decorate = v else bad("title_bar must be true or false") end end,
    min_size = function(v, fx, bad)
        if type(v) == "table" and type(v[1]) == "number" and type(v[2]) == "number" then fx.min_size = v[1] .. " " .. v[2]
        else bad("min_size must be { width, height }") end
    end,
    max_size = function(v, fx, bad)
        if type(v) == "table" and type(v[1]) == "number" and type(v[2]) == "number" then fx.max_size = v[1] .. " " .. v[2]
        else bad("max_size must be { width, height }") end
    end,
}

local PLUS = {
    plus = function(v, fx, bad) if type(v) == "boolean" then fx.plustile = v else bad("plus must be true or false") end end,
    keep_size = function(v, fx, bad) if type(v) == "boolean" then fx.plus_locked = v else bad("keep_size must be true or false") end end,
    superposition = function(v, fx, bad) if type(v) == "boolean" then fx.superposition = v else bad("superposition must be true or false") end end,
}

-- Which compositor feature (compositor.lua) each Plus field needs.
local NEEDS = { plus = "strips", superposition = "strips", keep_size = "tiles" }

-- caps: the table from compositor.lua. A plain true or false (the old argument) means all or nothing.
local function capsOf(caps)
    if type(caps) == "table" then
        return caps
    end
    return { plus = caps == true, strips = caps == true, tiles = caps == true }
end

local ROLES = {
    tile = function(fx) fx.tile = true end,
    float = function(fx) fx.float = true; fx.center = true end,
    plus = function(fx, caps) if caps.strips then fx.plustile = true end; fx.tile = true end,
    pinned = function(fx) fx.float = true; fx.center = true; fx.pin = true end,
}

-- Builds the effects for one entry. Returns match, effects, problems (a list of strings) and skipped (Plus fields
-- the running Hyprland lacks, as strings).
function M.translate(entry, caps)
    caps = capsOf(caps)
    local problems = {}
    local skipped = {}
    local function bad(text) problems[#problems + 1] = text end

    if type(entry) ~= "table" then
        return nil, nil, { "an entry is not a table" }, skipped
    end
    if type(entry.class) ~= "string" and type(entry.title) ~= "string" then
        return nil, nil, { "an entry has neither class nor title to match" }, skipped
    end

    local match = { class = entry.class, title = entry.title }
    local fx = {}

    for key, value in pairs(entry) do
        if key == "class" or key == "title" then
            -- the match
        elseif key == "role" then
            local role = ROLES[value]
            if role then role(fx, caps) else bad("role must be tile, float, plus or pinned, not " .. tostring(value)) end
        elseif NATIVE[key] then
            NATIVE[key](value, fx, bad)
        elseif PLUS[key] then
            if caps[NEEDS[key]] then
                PLUS[key](value, fx, bad)
            else
                skipped[#skipped + 1] = key .. " (" .. (caps.plus and "needs a newer hyprland-plus" or "needs hyprland-plus") .. ")"
            end
        else
            bad("unknown field " .. tostring(key))
        end
    end

    if fx.float and fx.tile then
        bad("float and tile both set; float wins")
        fx.tile = nil
    end

    return match, fx, problems, skipped
end

function M.apply(rules, caps)
    local report = {}
    M.skipped = {}
    for i, entry in ipairs(rules) do
        local match, fx, problems, skipped = M.translate(entry, caps)
        local label = (type(entry) == "table" and (entry.class or entry.title)) or ("entry " .. i)
        for _, p in ipairs(problems) do
            report[#report + 1] = label .. ": " .. p
        end
        for _, s in ipairs(skipped or {}) do
            M.skipped[#M.skipped + 1] = label .. ": " .. s
        end
        if match and next(fx) then
            fx.match = match
            hl.window_rule(fx)
        end
    end

    if #report > 0 then
        local text = table.concat(report, "\n"):gsub("'", "")
        hl.exec_cmd("notify-send -a Hyprland 'Halcyon app rules' '" .. text .. "'")
    end
    return report
end

return M
