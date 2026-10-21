.pragma library

// Synced lyrics in the LRC format: "[01:23.45] words", one or more time stamps to a line. Lines without a stamp
// (the [ar:Artist] tags) and word-by-word <00:12.30> marks are left out.

function parseLrc(text) {
    var lines = [];
    var raws = String(text || "").split(/\r?\n/);
    for (var i = 0; i < raws.length; i++) {
        var raw = raws[i];
        var stamps = [];
        var re = /\[(\d+):(\d{1,2})(?:[.:](\d{1,3}))?\]/g;
        var m;
        while ((m = re.exec(raw)) !== null)
            stamps.push(m);
        if (stamps.length === 0)
            continue;
        var words = raw.replace(/\[[^\]]*\]/g, "").replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
        for (var j = 0; j < stamps.length; j++) {
            var s = stamps[j];
            var fraction = s[3] ? parseInt(s[3], 10) / Math.pow(10, s[3].length) : 0;
            lines.push({ time: parseInt(s[1], 10) * 60 + parseInt(s[2], 10) + fraction, text: words });
        }
    }
    lines.sort(function (a, b) { return a.time - b.time; });
    return lines;
}

// The line that is being sung at `position` seconds: the last one that has started. -1 before the first.
function indexAt(lines, position) {
    var low = 0, high = lines.length - 1, found = -1;
    while (low <= high) {
        var mid = (low + high) >> 1;
        if (lines[mid].time <= position) {
            found = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return found;
}

// What LRCLIB answered: one song ({"syncedLyrics": "...", "plainLyrics": "..."}) from /get, or a list of them from
// /search, of which the first with timing is used. Returns {state, lines, plain}.
function interpret(output) {
    var none = { state: "none", lines: [], plain: "" };
    var text = String(output || "").trim();
    if (text === "")
        return none;
    var data;
    try {
        data = JSON.parse(text);
    } catch (e) {
        return none;
    }
    if (Array.isArray(data)) {
        var timed = data.filter(function (entry) { return entry && entry.syncedLyrics; });
        data = timed.length > 0 ? timed[0] : data[0];
    }
    if (!data || typeof data !== "object")
        return none;
    var lines = parseLrc(data.syncedLyrics);
    if (lines.length > 0)
        return { state: "synced", lines: lines, plain: "" };
    var plain = data.plainLyrics ? String(data.plainLyrics) : "";
    return { state: plain ? "plain" : "none", lines: [], plain: plain };
}
