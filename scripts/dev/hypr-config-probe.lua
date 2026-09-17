-- Halcyon — load the Hyprland configuration without Hyprland.
--
-- Defines a stand-in `hl` table that records every call instead of
-- performing it, then loads the real configuration files. The result is
-- a JSON dump of every option, bind, rule and animation the config would
-- set, which scripts/dev/check-hypr-config.py validates against
-- Hyprland's own option table.
--
-- This is how `./install.sh --validate` can tell you that a config is
-- wrong before you log into it.

local recorded = {
    config = {},        -- flattened "a.b.c" -> value
    binds = {},
    animations = {},
    curves = {},
    window_rules = {},
    layer_rules = {},
    workspace_rules = {},
    monitors = {},
    env = {},
    gestures = {},
    submaps = {},
    events = {},
    errors = {},
}

local function flatten(prefix, tbl, out)
    for key, value in pairs(tbl) do
        local path = prefix == "" and tostring(key) or (prefix .. "." .. tostring(key))
        if type(value) == "table" and not value[1] then
            -- A table with no array part is a nested option group; one
            -- with an array part is a value (vec2, gradient colours).
            local nested = false
            for _ in pairs(value) do nested = true break end
            if nested and value.colors == nil then
                flatten(path, value, out)
            else
                out[path] = value
            end
        else
            out[path] = value
        end
    end
end

local function stub_dispatcher(name)
    return function(...)
        return { __dispatcher = name, args = { ... } }
    end
end

local dsp = setmetatable({}, {
    __index = function(_, key)
        return stub_dispatcher(key)
    end,
})
for _, namespace in ipairs({ "window", "workspace", "group", "cursor" }) do
    dsp[namespace] = setmetatable({}, {
        __index = function(_, key)
            return stub_dispatcher(namespace .. "." .. key)
        end,
    })
end

local handle_meta = {
    __index = function()
        return function() end
    end,
}
local function handle()
    return setmetatable({}, handle_meta)
end

hl = {
    dsp = dsp,

    config = function(tbl)
        if type(tbl) ~= "table" then
            table.insert(recorded.errors, "hl.config called with a non-table")
            return
        end
        flatten("", tbl, recorded.config)
    end,

    bind = function(keys, action, opts)
        table.insert(recorded.binds, {
            keys = keys,
            dispatcher = type(action) == "table" and action.__dispatcher or "function",
            opts = opts,
        })
        return handle()
    end,

    unbind = function() end,
    env = function(key, value) recorded.env[key] = value end,
    exec_cmd = function() end,
    curve = function(name, spec) recorded.curves[name] = spec end,
    animation = function(spec) table.insert(recorded.animations, spec) end,
    window_rule = function(spec) table.insert(recorded.window_rules, spec); return handle() end,
    layer_rule = function(spec) table.insert(recorded.layer_rules, spec); return handle() end,
    workspace_rule = function(spec) table.insert(recorded.workspace_rules, spec); return handle() end,
    monitor = function(spec) table.insert(recorded.monitors, spec) end,
    gesture = function(spec) table.insert(recorded.gestures, spec) end,
    device = function() end,
    permission = function() end,
    on = function(event) table.insert(recorded.events, event); return handle() end,
    timer = function() return handle() end,

    define_submap = function(name, a, b)
        table.insert(recorded.submaps, name)
        local fn = type(a) == "function" and a or b
        if type(fn) == "function" then pcall(fn) end
    end,

    notification = {
        create = function() return handle() end,
        get = function() return {} end,
    },
    layout = { register = function() end },
    plugin = setmetatable({}, { __index = function() return function() end end }),

    version = function() return "0.56.2" end,
    dispatch = function() end,
    get_monitors = function() return {} end,
    get_windows = function() return {} end,
    get_workspaces = function() return {} end,
    get_active_window = function() return nil end,
    get_active_workspace = function() return nil end,
    get_config = function() return nil end,
    get_current_submap = function() return "" end,
    is_key_down = function() return false end,
}

------------------------------------------------------------------------
-- Load the configuration
------------------------------------------------------------------------

local root = arg[1] or "."
local generated = arg[2]

package.path = root .. "/?.lua;" .. root .. "/?/init.lua;" .. package.path

local function load_file(path, label)
    local chunk, err = loadfile(path)
    if not chunk then
        table.insert(recorded.errors, label .. ": " .. tostring(err))
        return
    end
    local ok, run_err = pcall(chunk)
    if not ok then
        table.insert(recorded.errors, label .. ": " .. tostring(run_err))
    end
end

if generated and generated ~= "" then
    -- The theme table is a return value, not a side effect.
    local chunk = loadfile(generated .. "/hypr-theme.lua")
    if chunk then
        local ok, value = pcall(chunk)
        if ok then HALCYON_THEME = value end
    end
    for _, name in ipairs({ "hypr-runtime", "hypr-animations", "hypr-keybinds" }) do
        load_file(generated .. "/" .. name .. ".lua", name)
    end
end

load_file(root .. "/halcyon/appearance.lua", "appearance")
load_file(root .. "/halcyon/behaviour.lua", "behaviour")
load_file(root .. "/halcyon/autostart.lua", "autostart")

------------------------------------------------------------------------
-- Emit JSON
------------------------------------------------------------------------

local function escape(str)
    return (tostring(str)
        :gsub("\\", "\\\\")
        :gsub('"', '\\"')
        :gsub("\n", "\\n")
        :gsub("\r", "\\r")
        :gsub("\t", "\\t"))
end

local function encode(value)
    local kind = type(value)
    if kind == "nil" then return "null" end
    if kind == "boolean" then return tostring(value) end
    if kind == "number" then
        if value ~= value or value == math.huge or value == -math.huge then return "null" end
        return string.format("%.14g", value)
    end
    if kind == "string" then return '"' .. escape(value) .. '"' end
    if kind == "table" then
        local is_array = #value > 0
        local parts = {}
        if is_array then
            for _, item in ipairs(value) do parts[#parts + 1] = encode(item) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        local keys = {}
        for key in pairs(value) do keys[#keys + 1] = tostring(key) end
        table.sort(keys)
        for _, key in ipairs(keys) do
            parts[#parts + 1] = '"' .. escape(key) .. '":' .. encode(value[key])
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return "null"
end

io.write(encode(recorded))
