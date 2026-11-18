.pragma library

// The settings search's index: every setting on every Settings page, read from the pages' own QML, so a new setting is
// found as soon as it is written (nothing to keep in step by hand).
//
// A page is walked element by element (by its braces). Each section, subsection, switch, spin box, slider, button and
// text field with a label becomes an entry; the tooltip or the note under a setting becomes its hint, which is
// searched too. Labels are kept in English, as written (Translation.tr is applied when shown and when found).

// Elements that are settings, and the property that is their label.
var LABELS = {
    "ContentSection": "title",
    "ContentSubsection": "title",
    "ConfigSwitch": "text",
    "ConfigSpinBox": "text",
    "ConfigSlider": "text",
    "RippleButtonWithIcon": "mainText",
    "MaterialTextField": "placeholderText"
};
var ICONS = ["icon", "buttonIcon", "materialIcon"];

function unescape(s) {
    return s.replace(/\\n/g, " ").replace(/\\"/g, "\"").replace(/\\\\/g, "\\");
}

/** Entries for one page: {label, hint, kind, icon, section, subsection, page}. */
function parse(text, page) {
    var entries = [];
    var stack = [];      // {type, depth, props: {}, hints: []}
    var depth = 0;
    var lines = text.split("\n");
    var open = /^\s*([A-Z][\w.]*)\s*\{/;
    var trProp = /^\s*(\w+)\s*:\s*Translation\.tr\(\s*"((?:[^"\\]|\\.)*)"/;
    var strProp = /^\s*(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"\s*$/;

    function ancestor(type) {
        for (var i = stack.length - 1; i >= 0; i--)
            if (stack[i].type === type && stack[i].props.label)
                return stack[i].props.label;
        return "";
    }

    function close(el) {
        var key = LABELS[el.type];
        if (key && el.props.label) {
            entries.push({
                label: el.props.label,
                hint: el.hints.join(" "),
                kind: el.type,
                icon: el.props.icon || "",
                section: el.type === "ContentSection" ? "" : ancestor("ContentSection"),
                subsection: (el.type === "ContentSection" || el.type === "ContentSubsection") ? "" : ancestor("ContentSubsection"),
                page: page
            });
        }
        // A tooltip, or a note just inside a setting's parent, tells what the setting does: it is searched too.
        if (el.type === "StyledToolTip" && el.props.text && stack.length) {
            stack[stack.length - 1].hints.push(el.props.text);
        }
    }

    for (var n = 0; n < lines.length; n++) {
        var line = lines[n].replace(/\/\/.*$/, "");
        var m = line.match(open);
        var rest = line;
        if (m) {
            stack.push({ type: m[1], depth: depth, props: {}, hints: [] });
            // A one-line element: `StyledToolTip { text: Translation.tr("...") }`.
            rest = line.slice(line.indexOf("{") + 1);
        }
        if (stack.length) {
            var el = stack[stack.length - 1];
            var p = rest.match(trProp);
            if (p) {
                var value = unescape(p[2]);
                if (p[1] === LABELS[el.type])
                    el.props.label = value;
                else if (el.type === "StyledToolTip" && p[1] === "text")
                    el.props.text = value;
                else if (p[1] === "tooltip")
                    el.hints.push(value);
            } else {
                var s = rest.match(strProp);
                if (s && ICONS.indexOf(s[1]) >= 0)
                    el.props.icon = s[2];
            }
        }
        // Braces, outside strings, move the depth; an element ends when its depth is reached again.
        var stripped = line.replace(/"(?:[^"\\]|\\.)*"/g, "").replace(/'(?:[^'\\]|\\.)*'/g, "").replace(/`[^`]*`/g, "");
        for (var c = 0; c < stripped.length; c++) {
            if (stripped[c] === "{") {
                depth++;
            } else if (stripped[c] === "}") {
                depth--;
                while (stack.length && stack[stack.length - 1].depth >= depth) {
                    var done = stack.pop();
                    if (done.depth === depth)
                        close(done);
                }
            }
        }
    }
    return entries;
}

// Lower case, and "Wi-Fi" as "wifi": hyphens and dots inside words do not count.
function norm(s) {
    return String(s).toLowerCase().replace(/([a-z0-9])[-.]([a-z0-9])/g, "$1$2");
}

function isLetter(ch) {
    return /[a-z0-9]/.test(ch);
}

/** How well an entry matches the words typed (0: not at all). Every word must be found; label words count most. */
function score(entry, shown, query) {
    var words = norm(query).split(/\s+/).filter(function (w) { return w.length > 0; });
    if (!words.length)
        return 0;
    var label = norm(shown.label + " " + entry.label);
    var place = norm(shown.section + " " + shown.subsection + " " + shown.page);
    var hint = norm(shown.hint + " " + entry.hint);
    var total = 0;
    for (var i = 0; i < words.length; i++) {
        var w = words[i];
        var at = label.indexOf(w);
        if (at >= 0) {
            var starts = at === 0 || !isLetter(label.charAt(at - 1));
            var whole = starts && !isLetter(label.charAt(at + w.length));
            total += whole ? 14 : starts ? 9 : 5;
        } else if (place.indexOf(w) >= 0)
            total += 3;
        else if (hint.indexOf(w) >= 0)
            total += 2;
        else
            return 0;
    }
    // Settings before the sections that hold them; shorter labels (closer matches) first.
    if (entry.kind !== "ContentSection" && entry.kind !== "ContentSubsection")
        total += 1;
    return total - Math.min(label.length, 120) / 200;
}
