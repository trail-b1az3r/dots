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

        function test_night_and_unknown() {
            const arc = createTemporaryObject(arcComponent, parent);
            arc.progress = -0.3;
            verify(!arc.daytime);
            fuzzyCompare(arc.sunX, arc.cx - arc.r, 0.01, "before dawn it waits under the left end");
            verify(arc.sunY > arc.baseY, "under the horizon");
            arc.progress = 1.4;
            fuzzyCompare(arc.sunX, arc.cx + arc.r, 0.01, "after dusk it rests under the right end");
            arc.progress = undefined;
            verify(!arc.known);
            arc.progress = null;
            verify(!arc.known);
        }
    }
}
