.pragma library

// Hyprland's binds as the cheat sheet (popups/Cheatsheet.qml) and hypr mode's card show them: each a row of keycaps,
// what it does, and the category it is in (the part of its description before the colon: "Shell: Toggle hypr mode").
// The same choices as halcyon/summit/rofi-menu's keys menu, which is the fallback when Summit is not running.

// Modifier bits in a bind's modmask, in the order keys are written.
var MODS = [[64, "super"], [4, "ctrl"], [8, "alt"], [1, "shift"], [32, "hyper"]];
var HYPER = 1 | 4 | 8 | 64;

// Key names as keycaps show them.
var NAMES = {
    "slash": "/", "backslash": "\\", "return": "Enter", "escape": "Esc", "space": "Space", "tab": "Tab",
    "left": "←", "right": "→", "up": "↑", "down": "↓", "print": "PrtSc", "delete": "Del",
    "backspace": "⌫", "page_up": "PgUp", "page_down": "PgDn", "prior": "PgUp", "next": "PgDn", "home": "Home",
    "end": "End", "insert": "Ins", "grave": "`", "minus": "−", "equal": "=", "plus": "+", "comma": ",",
    "period": ".", "semicolon": ";", "apostrophe": "'", "bracketleft": "[", "bracketright": "]", "menu": "Menu",
    "super_l": "Super", "super_r": "Super", "mouse:272": "Left click", "mouse:273": "Right click",
    "mouse:274": "Middle click", "mouse_up": "Scroll ↑", "mouse_down": "Scroll ↓", "mouse_left": "Scroll ←",
    "mouse_right": "Scroll →"
};
// The media and brightness keys (XF86...): on a laptop they are Fn with a key of the top row.
var FN = {
    "AudioRaiseVolume": "Volume +", "AudioLowerVolume": "Volume −", "AudioMute": "Mute", "AudioMicMute": "Mic mute",
    "AudioPlay": "Play", "AudioPause": "Pause", "AudioNext": "Next", "AudioPrev": "Previous", "AudioStop": "Stop",
    "MonBrightnessUp": "Brightness +", "MonBrightnessDown": "Brightness −", "KbdBrightnessUp": "Keyboard light +",
    "KbdBrightnessDown": "Keyboard light −", "PowerOff": "Power", "Calculator": "Calculator", "Search": "Search",
    "Display": "Display", "TouchpadToggle": "Touchpad", "WLAN": "Wi-Fi", "Sleep": "Sleep"
};

// A key as keycaps: [{kind, label}]. kind is "super", "ctrl", "alt", "shift", "hyper", "fn" (drawn with their
// icons) or "" (just the label).
function keyCaps(key) {
    key = String(key || "");
    if (key.indexOf("XF86") === 0) {
        var rest = key.slice(4);
        var label = FN[rest] || rest.replace(/([a-z])([A-Z])/g, "$1 $2");
        return [{ kind: "fn", label: "Fn" }, { kind: "", label: label }];
    }
    var lower = key.toLowerCase();
    if (NAMES[lower] !== undefined)
        return [{ kind: lower.indexOf("super_") === 0 ? "super" : "", label: NAMES[lower] }];
    if (lower.indexOf("code:") === 0)
        return [{ kind: "", label: "Key " + key.slice(5) }];
    if (/^f\d+$/.test(lower))
        return [{ kind: "", label: key.toUpperCase() }];
    return [{ kind: "", label: key.length === 1 ? key.toUpperCase() : key.replace(/_/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); }) }];
}

function modCaps(mask, hyperPage) {
    if (hyperPage && (mask & HYPER) === HYPER)
        return [{ kind: "hyper", label: "Hyper" }];
    var out = [];
    var labels = { super: "Super", ctrl: "Ctrl", alt: "Alt", shift: "Shift", hyper: "Hyper" };
    for (var i = 0; i < MODS.length; i++)
        if (mask & MODS[i][0])
            out.push({ kind: MODS[i][1], label: labels[MODS[i][1]] });
    return out;
}

// The rows for a page: "all" (everything but hypr mode's own keys) or "hypr" (the toggle, the Hyper chords and the
// mode's keys). Each {caps, text, category, dispatcher, arg, inMode, runnable}.
function rows(binds, page) {
    var hyprPage = page === "hypr";
    var seen = {};
    var out = [];
    for (var i = 0; i < binds.length; i++) {
        var b = binds[i];
        var desc = String(b.description || "").trim();
        if (!desc)
            continue;
        var mask = b.modmask || 0;
        var inMode = b.submap === "hypr" || desc.indexOf("Hypr mode:") === 0;
        var isHypr = inMode || (mask & HYPER) === HYPER || (mask & 32) !== 0;
        var toggle = desc.toLowerCase().indexOf("hypr mode") >= 0 && !inMode;
        if (hyprPage && !(isHypr || toggle))
            continue;
        if (!hyprPage && inMode)
            continue;
        var cut = desc.indexOf(":");
        var category = inMode ? "Hypr mode" : cut > 0 && cut < 24 ? desc.slice(0, cut).trim() : "Other";
        var text = inMode ? desc.replace(/^Hypr mode:\s*/, "") : cut > 0 && cut < 24 ? desc.slice(cut + 1).trim() : desc;
        var caps = (inMode ? [] : modCaps(mask, hyprPage)).concat(keyCaps(b.key));
        var key = JSON.stringify(caps) + "|" + desc;
        if (seen[key])
            continue;
        seen[key] = true;
        var dispatcher = String(b.dispatcher || "");
        out.push({ caps: caps, text: text, category: category, dispatcher: dispatcher, arg: String(b.arg || ""),
                   inMode: inMode, runnable: inMode || (dispatcher !== "" && dispatcher.indexOf("__") !== 0) });
    }
    return out;
}

// Rows grouped by category, in the order the categories first come: [{name, rows}].
function groups(list) {
    var order = [];
    var by = {};
    for (var i = 0; i < list.length; i++) {
        var c = list[i].category;
        if (!by[c]) {
            by[c] = [];
            order.push(c);
        }
        by[c].push(list[i]);
    }
    return order.map(function (c) { return { name: c, rows: by[c] }; });
}

// Whether a row matches what was typed: every word somewhere in its keys, text or category.
function matches(row, query) {
    var words = String(query || "").toLowerCase().split(/\s+/).filter(function (w) { return w.length > 0; });
    if (!words.length)
        return true;
    var hay = (row.category + " " + row.text + " " + row.caps.map(function (c) { return c.label; }).join(" ")).toLowerCase();
    return words.every(function (w) { return hay.indexOf(w) >= 0; });
}

// Groups dealt into `count` columns, each to the shortest so far, so the columns end about level.
function columns(groupList, count) {
    var cols = [];
    var heights = [];
    for (var i = 0; i < count; i++) {
        cols.push([]);
        heights.push(0);
    }
    for (var g = 0; g < groupList.length; g++) {
        var shortest = 0;
        for (var c = 1; c < count; c++)
            if (heights[c] < heights[shortest])
                shortest = c;
        cols[shortest].push(groupList[g]);
        heights[shortest] += groupList[g].rows.length + 2;
    }
    return cols;
}

if (typeof module !== "undefined")
    module.exports = { keyCaps: keyCaps, modCaps: modCaps, rows: rows, groups: groups, matches: matches, columns: columns };
