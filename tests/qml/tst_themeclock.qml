import QtQuick
import QtTest
import "../../dots/.config/quickshell/ii/modules/ii/background/widgets/clock"

// The themes' own clock faces (After ICEY, Manga Ink and Dark, Silence): where their hands point, and each draws.
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

        function test_every_face_draws() {
            for (const kind of ["icey", "ink", "ink-dark", "silence"]) {
                const face = createTemporaryObject(clockComponent, parent, { kind: kind });
                verify(face !== null, kind);
                waitForRendering(face);
            }
        }

        function test_dark_ink_is_the_page_in_negative() {
            const dark = createTemporaryObject(clockComponent, parent, { kind: "ink-dark" });
            verify(dark.paper.hslLightness < 0.1, "a black page");
            verify(dark.ink.hslLightness > 0.85, "white ink");
        }
    }
}
