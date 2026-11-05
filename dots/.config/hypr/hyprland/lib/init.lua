HOME = os.getenv("HOME")

function is_file_exists(name)
   local f = io.open(name, "r")
   if f ~= nil then
      io.close(f)
      return true
   else
      return false
   end
end

function create_if_not_exists(path)
   if not is_file_exists(path) then
      os.execute("mkdir -p \"$(dirname \"" .. path .. "\")\"")
      os.execute("echo '-- This file will not be overwritten across dots-hyprland updates.\n-- The file name is for the sake of organization and does not matter\n-- See the corresponding files in ~/.config/hypr/hyprland for examples' > \"" .. path .. "\"")
      return true
   end
   return false
end

function workspace_in_group(i)
    local curr = hl.get_active_workspace().id
    local newVal = math.floor((curr - 1) / workspaceGroupSize) * workspaceGroupSize + i
    -- hl.notification.create({ text = "curr " .. curr .. " floor " .. math.floor(curr / 10) .. " new " .. newVal, duration = 5000 })
    return newVal
end

-- Manga Ink turns a page when you change workspace (the shell's pageTurn/PageTurn.qml). It needs the screen as it was
-- before the switch, so while it is on, the workspace keys hand the switch to the shell: the target goes in
-- $XDG_RUNTIME_DIR/halcyon-page-turn-target and the shell is told (quickshell:pageTurn). The shell keeps
-- $XDG_RUNTIME_DIR/halcyon-page-turn holding its process id while it can turn pages; when that file is missing or the
-- process is gone, the keys switch workspace themselves, as always.
local runtime_dir = os.getenv("XDG_RUNTIME_DIR") or "/tmp"

function page_turn_on()
    local f = io.open(runtime_dir .. "/halcyon-page-turn", "r")
    if not f then
        return false
    end
    local pid = f:read("*l")
    f:close()
    return pid ~= nil and pid:match("^%d+$") ~= nil and is_file_exists("/proc/" .. pid .. "/status")
end

-- Go to a workspace (an id), turning a page in Manga Ink.
function focus_workspace(target)
    if target < 1 then
        return
    end
    if page_turn_on() then
        local f = io.open(runtime_dir .. "/halcyon-page-turn-target", "w")
        if f then
            f:write(tostring(target), "\n")
            f:close()
            hl.dispatch(hl.dsp.global("quickshell:pageTurn"))
            return
        end
    end
    hl.dispatch(hl.dsp.focus({ workspace = target }))
end

-- The next or previous workspace (step +1 or -1), as "r+1" / "r-1" do.
function focus_workspace_step(step)
    if page_turn_on() then
        focus_workspace(hl.get_active_workspace().id + step)
    else
        hl.dispatch(hl.dsp.focus({ workspace = (step > 0 and "r+" or "r-") .. math.abs(step) }))
    end
end
