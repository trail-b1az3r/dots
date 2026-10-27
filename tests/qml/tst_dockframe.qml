import QtQuick
import QtTest
import "../../dots/.config/quickshell/ii/modules/ii/dock"

// The dock's frame in each non-glass Halcyon theme: every kind draws, and Manga Ink's screentone stays clear of
// the top half (where the dock's buttons are).
Item {
    width: 500
    height: 120

    Component {
        id: frameComponent
        DockFrame { width: 400; height: 60 }
    }

    TestCase {
        name: "DockFrame"
        when: windowShown

        function test_every_kind_draws() {
            for (const kind of ["hyperneo", "hsr", "red-sun", "icey", "ink", "ink-dark", "silence"]) {
                const frame = createTemporaryObject(frameComponent, parent, { kind: kind });
                verify(frame !== null, kind);
                waitForRendering(frame);
            }
        }

        function test_dark_ink_is_negative_everywhere() {
            const dock = createTemporaryObject(frameComponent, parent, { kind: "ink-dark" });
            verify(dock.negative, "the dock too, not only the top bar");
            verify(dock.paper.hslLightness < 0.1);
            verify(dock.tone.length > 0, "with its screentone");
        }

        function test_ink_screentone() {
            const frame = createTemporaryObject(frameComponent, parent, { kind: "ink" });
            verify(frame.tone.length > 0);
            compare(createTemporaryObject(frameComponent, parent, { kind: "hsr" }).tone, "", "only Manga Ink has it");
            const dots = /M ([0-9.]+) ([0-9.]+) A/g;
            let m;
            while ((m = dots.exec(frame.tone)) !== null)
                verify(Number(m[2]) > (60 - 8) * 0.35, "no dots in the top third: " + m[2]);
        }
    }
}
