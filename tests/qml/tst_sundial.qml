import QtQuick
import QtTest
import "../../dots/.config/quickshell/ii/modules/ii/bar"

// The bar's sun dial: where its sun is drawn for a given time of day.
Item {
    width: 200
    height: 100

    Component {
        id: arcComponent
        SunArc { width: 34; height: 22 }
    }

    TestCase {
        name: "SunArc"
        when: windowShown

        function test_sun_follows_the_day() {
            const arc = createTemporaryObject(arcComponent, parent);
            arc.progress = 0;
            verify(arc.daytime);
            fuzzyCompare(arc.sunX, arc.cx - arc.r, 0.01, "sunrise is on the left");
            fuzzyCompare(arc.sunY, arc.baseY, 0.01);
            arc.progress = 0.5;
            fuzzyCompare(arc.sunX, arc.cx, 0.01, "noon is at the top");
            fuzzyCompare(arc.sunY, arc.baseY - arc.r, 0.01);
            arc.progress = 1;
            fuzzyCompare(arc.sunX, arc.cx + arc.r, 0.01, "sunset is on the right");
        }

        function test_night_turns_it_over_and_the_moon_crosses() {
            const arc = createTemporaryObject(arcComponent, parent);
            arc.dayHours = 12;
            arc.progress = 1;
            verify(arc.daytime);
            arc.progress = 1.0001;
            verify(arc.night);
            fuzzyCompare(arc.moonX, arc.cx - arc.r, 0.05, "the moon starts its night on the left");
            arc.progress = 1.5;                           // half a day of daylight after sunset: midnight
            fuzzyCompare(arc.nightT, 0.5, 0.001);
            fuzzyCompare(arc.moonX, arc.cx, 0.01, "midnight is the middle");
            fuzzyCompare(arc.moonY, arc.height - arc.baseY + arc.r, 0.01, "hanging under the turned-over horizon");
            arc.progress = -0.25;                         // three hours before sunrise
            fuzzyCompare(arc.nightT, 0.75, 0.001);
            tryCompare(arc, "flip", -1, 2000, "the dial turns upside down at night");
            arc.progress = 0.3;
            tryCompare(arc, "flip", 1, 2000, "and back by day");
        }

        function test_moon_phase() {
            const arc = createTemporaryObject(arcComponent, parent);
            compare(arc.moonName(arc.moonPhaseAt(new Date(Date.UTC(2000, 0, 6, 18, 14)))), "new");
            // Full moons: 13 Jan 2025 22:27 UTC, 5 Nov 2025 13:19 UTC; new moon 21 Sep 2025 19:54 UTC.
            compare(arc.moonName(arc.moonPhaseAt(new Date(Date.UTC(2025, 0, 13, 22, 27)))), "full");
            compare(arc.moonName(arc.moonPhaseAt(new Date(Date.UTC(2025, 10, 5, 13, 19)))), "full");
            compare(arc.moonName(arc.moonPhaseAt(new Date(Date.UTC(2025, 8, 21, 19, 54)))), "new");
            fuzzyCompare(arc.moonLit(0.5), 1, 0.001);
            fuzzyCompare(arc.moonLit(0.25), 0.5, 0.001);
            fuzzyCompare(arc.moonLit(0), 0, 0.001);
        }

        function test_unknown() {
            const arc = createTemporaryObject(arcComponent, parent);
            arc.progress = undefined;
            verify(!arc.known);
            arc.progress = null;
            verify(!arc.known);
        }
    }
}
