import QtQuick
import QtTest
import "../../dots/.config/quickshell/ii/modules/ii/background/widgets/clock"

// The After ICEY and Manga Ink clock faces: where their hands point, and both draw.
Item {
    width: 300
    height: 300

    Component {
        id: clockComponent
        ThemeClock { width: 230; height: 230 }
    }

    TestCase {
        name: "ThemeClock"
        when: windowShown

        function test_hands_follow_the_time() {
            const face = createTemporaryObject(clockComponent, parent, { now: new Date(2026, 9, 22, 10, 30, 15) });
            fuzzyCompare(face.hourAngle, 315, 0.01, "half past ten: between ten and eleven");
            fuzzyCompare(face.minuteAngle, 181.5, 0.01, "thirty minutes and a quarter");
            fuzzyCompare(face.secondAngle, 90, 0.01);
            fuzzyCompare(face.sweep, 0.25, 0.001, "the scanning arc runs with the seconds");
            face.showSeconds = false;
            fuzzyCompare(face.sweep, 0.5, 0.001, "and with the minutes without second precision");
        }

        function test_both_faces_draw() {
            for (const kind of ["icey", "ink"]) {
                const face = createTemporaryObject(clockComponent, parent, { kind: kind });
                verify(face !== null, kind);
                waitForRendering(face);
            }
        }
    }
}
