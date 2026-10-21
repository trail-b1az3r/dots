"""Calendar events (services/calendar_events.js, behind the right sidebar's new-event button and the bar's next event),
run under Node with the same file the shell loads. Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QS = ROOT / "dots/.config/quickshell/ii"
EVENTS_JS = QS / "services/calendar_events.js"
NODE = shutil.which("node")

# Loads the file as QML would (minus its `.pragma library` line) and pins the clock zone, so dates are the same
# wherever the tests run.
PRELUDE = r"""
process.env.TZ = "Europe/London";
const vm = require("vm");
const fs = require("fs");
const E = {};
vm.createContext(E);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8").replace(/^\.pragma library\s*$/m, ""), E);
const at = s => new Date(s);
const out = v => console.log(JSON.stringify(v));
"""


def run(body):
    done = subprocess.run([NODE, "-e", PRELUDE + body, str(EVENTS_JS)], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


@unittest.skipUnless(NODE, "no node")
class CalendarEventsTest(unittest.TestCase):
    def test_times_people_type(self):
        cases = ["9", "930", "0930", "9:30", "9.30", "9:30pm", "9pm", "12am", "21:30", "", " ", "25:00", "9:75", "13pm", "soon"]
        got = run(f"out({json.dumps(cases)}.map(t => E.parseTime(t)))")
        self.assertEqual(got, ["09:00", "09:30", "09:30", "09:30", "09:30", "21:30", "21:00", "00:00", "21:30", "", "",
                               None, None, None, None])

    def test_day_keys_across_months(self):
        got = run("out([E.dateKey(new Date(2026, 0, 5)), E.addDays('2026-01-31', 1), E.addDays('2026-03-01', -1),"
                  " E.parseKey('14/10/2026')])")
        self.assertEqual(got, ["2026-01-05", "2026-02-01", "2026-02-28", None])

    def test_next_event_skips_ones_that_are_over_and_keeps_today_all_day(self):
        got = run(r"""
const list = [
  { id: "a", title: "Old", date: "2026-10-13", time: "10:00" },
  { id: "b", title: "Earlier today", date: "2026-10-14", time: "08:00" },
  { id: "c", title: "Dentist", date: "2026-10-14", time: "15:30" },
  { id: "d", title: "Birthday", date: "2026-10-14", time: "" },
  { id: "e", title: "Later", date: "2026-10-20", time: "09:00" },
];
const now = at("2026-10-14T12:00:00");
out([E.nextEvent(list, now).id, E.nextEvent(list.filter(e => e.id !== "c"), now).id,
     E.nextEvent(list, at("2026-10-15T00:00:00")).id, E.nextEvent(list, at("2026-11-01T00:00:00")),
     E.eventsOn(list, "2026-10-14").map(e => e.id), E.countByDay(list),
     E.daysAway(list[4], now)]);
""")
        self.assertEqual(got[0], "c", "a timed event today comes before today's all-day one")
        self.assertEqual(got[1], "d", "with the timed one gone, the all-day one still counts at noon")
        self.assertEqual(got[2], "e")
        self.assertIsNone(got[3])
        self.assertEqual(got[4], ["d", "b", "c"], "all day first, then by time")
        self.assertEqual(got[5], {"2026-10-13": 1, "2026-10-14": 3, "2026-10-20": 1})
        self.assertEqual(got[6], 6)

    def test_reminder_then_start_each_once(self):
        got = run(r"""
const e = E.makeEvent("  Standup ", "2026-10-14", "9:30", 15, at("2026-10-14T08:00:00"));
const list = [e];
const steps = [];
for (const t of ["09:10", "09:15", "09:29", "09:30"]) {
  const due = E.due(list, at("2026-10-14T" + t + ":00"));
  due.forEach(d => { if (d.kind === "reminder") e.reminded = true; else e.notified = true; });
  steps.push(due.map(d => d.kind + (d.late ? "-late" : "")));
}
out({ title: e.title, time: e.time, steps: steps });
""")
        self.assertEqual(got["title"], "Standup")
        self.assertEqual(got["time"], "09:30")
        self.assertEqual(got["steps"], [[], ["reminder"], [], ["start"]])

    def test_missed_while_off_is_marked_late_and_new_past_events_are_quiet(self):
        got = run(r"""
const old = { id: "x", title: "Yesterday", date: "2026-10-13", time: "09:00", remind: 5 };
const late = E.due([old], at("2026-10-14T12:00:00"));
const already = E.makeEvent("Started", "2026-10-14", "10:00", 15, at("2026-10-14T12:00:00"));
const allDay = E.makeEvent("Today", "2026-10-14", "", -1, at("2026-10-14T12:00:00"));
const bad = [E.makeEvent("", "2026-10-14", "", -1), E.makeEvent("x", "2026-10-14", "noon", -1), E.makeEvent("x", "14/10", "", -1)];
out({ late: late, already: [already.reminded, already.notified], allDay: [allDay.reminded, allDay.notified, allDay.remind], bad: bad });
""")
        self.assertEqual(got["late"], [{"id": "x", "kind": "reminder", "late": True}, {"id": "x", "kind": "start", "late": True}])
        self.assertEqual(got["already"], [True, True])
        self.assertEqual(got["allDay"], [True, True, -1])
        self.assertEqual(got["bad"], [None, None, None])

    def test_an_alarm_rings_once_at_its_time(self):
        got = run(r"""
const e = E.makeEvent("Wake up", "2026-10-14", "7:00", -1, at("2026-10-13T22:00:00"), true);
const steps = [];
for (const t of ["06:59:55", "07:00:00", "07:00:05"]) {
  const due = E.due([e], at("2026-10-14T" + t)).filter(d => d.kind === "alarm");
  due.forEach(() => { e.alarmed = true; });
  steps.push(due.map(d => d.kind + (d.late ? "-late" : "")));
}
out({ alarm: e.alarm, steps: steps });
""")
        self.assertTrue(got["alarm"])
        self.assertEqual(got["steps"], [[], ["alarm"], []])

    def test_a_snoozed_alarm_rings_again_after_the_snooze(self):
        got = run(r"""
let e = E.makeEvent("Wake up", "2026-10-14", "7:00", -1, at("2026-10-13T22:00:00"), true);
e.alarmed = true;                                   // it rang at 07:00
e = E.snooze(e, 5, at("2026-10-14T07:01:00"));      // snoozed a minute later
const ring = t => E.due([e], at("2026-10-14T" + t)).filter(d => d.kind === "alarm").length;
out([ring("07:05:59"), ring("07:06:00"), E.alarmAt(e) === at("2026-10-14T07:06:00").getTime()]);
""")
        self.assertEqual(got, [0, 1, True])

    def test_alarms_need_a_time_and_do_not_ring_late_or_for_the_past(self):
        got = run(r"""
const allDay = E.makeEvent("Birthday", "2026-10-14", "", -1, at("2026-10-13T12:00:00"), true);
const past = E.makeEvent("Gone", "2026-10-14", "9:00", -1, at("2026-10-14T10:00:00"), true);
const missed = { id: "m", title: "Missed", date: "2026-10-14", time: "07:00", alarm: true, alarmed: false,
                 reminded: true, notified: true, remind: -1 };
const off = E.makeEvent("Quiet", "2026-10-14", "9:00", -1, at("2026-10-13T12:00:00"), false);
out({
  allDay: [allDay.alarm, E.alarmAt(allDay)],
  past: [past.alarm, past.alarmed],
  justLate: E.due([missed], at("2026-10-14T07:09:59")).filter(d => d.kind === "alarm")[0].late,
  tooLate: E.due([missed], at("2026-10-14T07:10:01")).filter(d => d.kind === "alarm")[0].late,
  off: E.due([off], at("2026-10-14T09:00:00")).map(d => d.kind),
  oldFile: E.alarmAt({ id: "o", title: "Old", date: "2026-10-14", time: "09:00" }),
});
""")
        self.assertEqual(got["allDay"], [False, None])
        self.assertEqual(got["past"], [True, True])
        self.assertFalse(got["justLate"])
        self.assertTrue(got["tooLate"])
        self.assertEqual(got["off"], ["start"])
        self.assertIsNone(got["oldFile"], "events saved before alarms existed have none")

    def test_load_survives_a_broken_file(self):
        got = run(r"""out([E.load("not json"), E.load("{}"), E.load('[{"title":"a","date":"2026-01-01"},{"title":1},null]').length])""")
        self.assertEqual(got, [[], [], 1])


class WiringTest(unittest.TestCase):
    """The pieces the user sees, wired to the service."""

    def read(self, rel):
        return (QS / rel).read_text()

    def test_calendar_has_a_new_event_button_and_day_panel(self):
        widget = self.read("modules/ii/sidebarRight/calendar/CalendarWidget.qml")
        self.assertIn('Translation.tr("New event")', widget)
        self.assertIn("CalendarDayPanel {", widget)
        self.assertIn("onClicked: root.openDay(key)", widget)
        self.assertIn("CalendarEvents.counts[key]", widget)
        panel = self.read("modules/ii/sidebarRight/calendar/CalendarDayPanel.qml")
        self.assertIn("CalendarEvents.add(", panel)
        self.assertIn("CalendarEvents.remove(", panel)

    def test_bar_has_both_new_features_with_settings(self):
        bar = self.read("modules/ii/bar/BarContent.qml")
        self.assertIn("WindowButtons {", bar)
        self.assertIn("NextEvent {", bar)
        config = self.read("modules/common/Config.qml")
        settings = self.read("modules/settings/BarConfig.qml")
        for option in ("windowButtons", "nextEvent"):
            self.assertIn(f"property bool {option}: true", config)
            self.assertIn(f"Config.options.bar.{option} = checked", settings)
        self.assertIn("CalendarEvents.open(", self.read("modules/ii/bar/NextEvent.qml"))
        self.assertIn("MiniWindows.toggle(", self.read("modules/ii/bar/WindowButtons.qml"))

    def test_events_are_saved_next_to_the_todo_list(self):
        self.assertIn("user/events.json", self.read("modules/common/Directories.qml"))
        self.assertIn("Directories.eventsPath", self.read("services/CalendarEvents.qml"))


if __name__ == "__main__":
    unittest.main()
