pragma Singleton
pragma ComponentBehavior: Bound

import qs
import qs.modules.common
import "calendar_events.js" as Events
import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Calendar events, added from the calendar in the right sidebar (the + button, or a click on a day).
 *
 * Saved in ~/.local/state/quickshell/user/events.json. Each event can have a reminder some minutes before it, and
 * there is a notification when it starts (all-day events: in the morning of the day, at midnight). An event at a
 * time can also have an alarm, which rings then (services/Alarm.qml) until it is stopped or snoozed. The bar shows
 * the next one.
 */
Singleton {
    id: root

    property string filePath: Directories.eventsPath
    property var list: []
    // The clock the next event and the notifications go by: a minute is fine enough for both.
    property date now: new Date()

    readonly property var counts: Events.countByDay(root.list)
    readonly property var next: Events.nextEvent(root.list, root.now)

    // A day the calendar should open at (the bar's next event was clicked), "" when there is none waiting.
    property string pendingDay: ""
    signal openRequested(string day)

    // Called at start-up so the singleton exists from the start: Quickshell makes one only when it is first used.
    function load() {}

    function dateKey(date) {
        return Events.dateKey(date);
    }

    function parseKey(key) {
        return Events.parseKey(key);
    }

    function addDays(key, days) {
        return Events.addDays(key, days);
    }

    function parseTime(text) {
        return Events.parseTime(text);
    }

    function eventsOn(key) {
        return Events.eventsOn(root.list, key);
    }

    function daysAway(event) {
        return Events.daysAway(event, root.now);
    }

    // Adds an event; false if the title is empty or the time isn't one. An alarm needs a time.
    function add(title, key, time, remind, alarm) {
        const event = Events.makeEvent(title, key, time, remind, new Date(), alarm ?? false);
        if (!event)
            return false;
        root.list = root.list.concat([event]);
        root.save();
        return true;
    }

    // Turns an event's alarm on or off. Off also stops it if it is ringing.
    function setAlarm(id, on) {
        root.list = root.list.map(e => {
            if (e.id !== id || !e.time)
                return e;
            const copy = Object.assign({}, e, { alarm: on, snoozeUntil: 0 });
            // Turned on for an event already under way: it does not ring at once.
            copy.alarmed = on ? Events.startOf(copy).getTime() <= Date.now() : false;
            return copy;
        });
        root.save();
        if (!on && Alarm.event?.id === id)
            Alarm.stop();
    }

    function remove(id) {
        if (Alarm.event?.id === id)
            Alarm.stop();
        root.list = root.list.filter(e => e.id !== id);
        root.save();
    }

    // Opens the right sidebar at the calendar, on this day.
    function open(key) {
        root.pendingDay = key;
        GlobalStates.sidebarRightOpen = true;
        root.openRequested(key);
    }

    function save() {
        eventsFile.setText(JSON.stringify(root.list, null, 2));
    }

    function describeTime(event) {
        return event.time ? event.time : Translation.tr("All day");
    }

    function notifyDue() {
        root.now = new Date();
        const due = Events.due(root.list, root.now);
        if (due.length === 0)
            return;
        const byId = {};
        root.list.forEach(e => byId[e.id] = Object.assign({}, e));
        due.forEach(item => {
            const e = byId[item.id];
            if (item.kind === "alarm") {
                e.alarmed = true;
                if (!item.late)
                    Alarm.ring({ id: e.id, title: e.title, time: e.time });
                return;
            }
            if (item.kind === "reminder")
                e.reminded = true;
            else
                e.notified = true;
            if (item.late)
                return;
            const when = item.kind === "reminder"
                ? (e.time ? Translation.tr("At %1").arg(e.time) : Translation.tr("Today"))
                : (e.time ? Translation.tr("Now, %1").arg(e.time) : Translation.tr("Today, all day"));
            Quickshell.execDetached(["notify-send", "-a", Translation.tr("Calendar"), "-i", "x-office-calendar", e.title, when]);
        });
        root.list = root.list.map(e => byId[e.id]);
        root.save();
    }

    // A snoozed alarm rings again after the snooze.
    Connections {
        target: Alarm
        function onSnoozed(id, minutes) {
            root.list = root.list.map(e => e.id === id ? Events.snooze(e, minutes, new Date()) : e);
            root.save();
        }
    }

    // Every five seconds, so an alarm rings on time.
    Timer {
        interval: 5000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: root.notifyDue()
    }

    FileView {
        id: eventsFile
        path: Qt.resolvedUrl(root.filePath)
        onLoaded: {
            root.list = Events.load(eventsFile.text());
            root.notifyDue();
        }
        onLoadFailed: error => {
            if (error == FileViewError.FileNotFound) {
                root.list = [];
                root.save();
            } else {
                console.log("[Calendar] Couldn't read the events: " + error);
            }
        }
    }

    IpcHandler {
        target: "calendarEvents"

        function add(title: string, date: string, time: string): string {
            return root.add(title, date === "" ? root.dateKey(new Date()) : date, time, -1) ? "added" : "not added: check the date (YYYY-MM-DD) and time";
        }
        // An event with the alarm on: it rings at its time (today when the date is empty).
        function addAlarm(title: string, date: string, time: string): string {
            if (time.trim() === "")
                return "not added: an alarm needs a time";
            return root.add(title, date === "" ? root.dateKey(new Date()) : date, time, -1, true) ? "added" : "not added: check the date (YYYY-MM-DD) and time";
        }
        // Opens the right sidebar's calendar on a day (YYYY-MM-DD), or today.
        function open(date: string): void {
            root.open(date === "" ? root.dateKey(new Date()) : date);
        }
        function next(): string {
            const e = root.next;
            return e ? `${e.date} ${root.describeTime(e)} ${e.title}` : "";
        }
    }
}
