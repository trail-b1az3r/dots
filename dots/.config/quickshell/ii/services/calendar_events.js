.pragma library

// Calendar events: plain functions on the saved list, so they run (and are tested) outside the shell.
//
// An event is { id, title, date: "YYYY-MM-DD", time: "HH:MM" or "" for all day, remind: minutes before, or -1,
// reminded, notified }. Dates are local: an event at 09:00 is at 09:00 wherever the clock is.

// How late a missed notification may still be sent (the shell was off when it was due).
var LATE_LIMIT_MS = 12 * 60 * 60 * 1000;

function pad(n) {
    return (n < 10 ? "0" : "") + n;
}

function dateKey(d) {
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
}

function parseKey(key) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key || "");
    if (!m)
        return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function addDays(key, days) {
    var d = parseKey(key);
    d.setDate(d.getDate() + days);
    return dateKey(d);
}

// What was typed in the time field, as "HH:MM"; "" for all day (nothing typed); null if it is not a time.
// Takes 9, 930, 0930, 9:30, 9.30, 9:30pm, 9pm, 21:30.
function parseTime(text) {
    var t = String(text || "").trim().toLowerCase().replace(/\s+/g, "");
    if (t === "")
        return "";
    var m = /^(\d{1,2})(?:[:.h]?(\d{2}))?(am|pm|a|p)?$/.exec(t);
    if (!m)
        return null;
    var h = Number(m[1]);
    var min = m[2] === undefined ? 0 : Number(m[2]);
    var half = m[3] ? m[3][0] : "";
    if (half) {
        if (h < 1 || h > 12)
            return null;
        h = (h % 12) + (half === "p" ? 12 : 0);
    }
    if (h > 23 || min > 59)
        return null;
    return pad(h) + ":" + pad(min);
}

// When the event starts. An all-day event starts at midnight.
function startOf(event) {
    var d = parseKey(event.date);
    if (!d)
        return null;
    if (event.time) {
        var parts = event.time.split(":");
        d.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
    }
    return d;
}

// An all-day event lasts until the end of its day; a timed one is over once it has started.
function isOver(event, now) {
    var start = startOf(event);
    if (!start)
        return true;
    if (!event.time) {
        var end = new Date(start.getTime());
        end.setDate(end.getDate() + 1);
        return end.getTime() <= now.getTime();
    }
    return start.getTime() < now.getTime();
}

// All-day first, then by time, then in the order they were added.
function compare(a, b) {
    if (a.date !== b.date)
        return a.date < b.date ? -1 : 1;
    if ((a.time || "") !== (b.time || ""))
        return (a.time || "") < (b.time || "") ? -1 : 1;
    return 0;
}

function sorted(list) {
    return (list || []).slice().sort(compare);
}

function eventsOn(list, key) {
    return sorted((list || []).filter(function (e) {
        return e.date === key;
    }));
}

// Day key -> how many events, for the dots on the calendar.
function countByDay(list) {
    var counts = {};
    (list || []).forEach(function (e) {
        counts[e.date] = (counts[e.date] || 0) + 1;
    });
    return counts;
}

// The next event that is not over. On a day with both, one at a set time comes before the all-day ones: it is the
// one to be ready for. An all-day event still counts all through its day.
function nextEvent(list, now) {
    var ahead = (list || []).filter(function (e) {
        return !isOver(e, now);
    }).sort(function (a, b) {
        if (a.date !== b.date)
            return a.date < b.date ? -1 : 1;
        if (!a.time !== !b.time)
            return a.time ? -1 : 1;
        return compare(a, b);
    });
    return ahead.length > 0 ? ahead[0] : null;
}

// Whole days from now's day to the event's: 0 today, 1 tomorrow.
function daysAway(event, now) {
    var day = parseKey(event.date);
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return Math.round((day.getTime() - today.getTime()) / 86400000);
}

// The notifications due at `now`: [{ id, kind: "reminder" | "start" }]. A reminder is due `remind` minutes before
// the start, and the start notification at the start (all-day events: at midnight). Ones more than LATE_LIMIT_MS
// late are not sent, but are marked done as well, so they are never sent later.
function due(list, now) {
    var out = [];
    (list || []).forEach(function (e) {
        var start = startOf(e);
        if (!start)
            return;
        if (!e.reminded && e.remind !== undefined && e.remind >= 0) {
            var at = start.getTime() - e.remind * 60000;
            if (at <= now.getTime())
                out.push({ id: e.id, kind: "reminder", late: now.getTime() - at > LATE_LIMIT_MS });
        }
        if (!e.notified && start.getTime() <= now.getTime())
            out.push({ id: e.id, kind: "start", late: now.getTime() - start.getTime() > LATE_LIMIT_MS });
    });
    return out;
}

function makeEvent(title, key, time, remind, now) {
    var t = String(title || "").trim();
    var parsed = parseTime(time);
    if (t === "" || !parseKey(key) || parsed === null)
        return null;
    var minutes = Number(remind);
    var event = {
        id: (now || new Date()).getTime().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
        title: t,
        date: key,
        time: parsed,
        remind: isNaN(minutes) ? -1 : minutes,
        reminded: false,
        notified: false
    };
    // Adding one already under way (or a reminder already passed) does not notify about it straight away.
    var start = startOf(event);
    var at = now || new Date();
    if (start.getTime() <= at.getTime())
        event.notified = true;
    if (event.remind < 0 || start.getTime() - event.remind * 60000 <= at.getTime())
        event.reminded = true;
    return event;
}

// The saved file's contents as a list, whatever was in it.
function load(text) {
    try {
        var data = JSON.parse(text);
        if (!Array.isArray(data))
            return [];
        return data.filter(function (e) {
            return e && typeof e.title === "string" && parseKey(e.date) !== null;
        });
    } catch (err) {
        return [];
    }
}
