import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import qs.modules.common
import "../../dots/.config/quickshell/ii/modules/ii/background/widgets/revolver"
import "../../dots/.config/quickshell/ii/modules/ii/background/widgets"

// The revolver, driven with real mouse drags against mocked shell modules (tests/qml/mock).
Item {
    id: root
    width: 1920
    height: 1080

    readonly property string games: JSON.stringify([
        { id: "1", name: "Hades II", source: "steam", weight: 3 }, { id: "2", name: "Celeste", source: "steam", weight: 2 },
        { id: "3", name: "Outer Wilds", source: "steam", weight: 2 }, { id: "4", name: "Balatro", source: "steam", weight: 1 },
        { id: "5", name: "Hollow Knight", source: "steam", weight: 1 }, { id: "6", name: "Stardew Valley", source: "steam", weight: 1 },
        { id: "7", name: "Factorio", source: "steam", weight: 1 }, { id: "8", name: "Portal 2", source: "steam", weight: 1 }
    ])

    Component {
        id: revolverComponent
        RevolverWidget {}
    }

    TestCase {
        id: test
        name: "Revolver"
        when: windowShown

        function init() {
            Quickshell.reset();
            MockIo.output = root.games;
            MockIo.exitCode = 0;
            Config.options.halcyon.theme = "";
        }

        function makeRevolver() {
            const widget = createTemporaryObject(revolverComponent, root);
            verify(widget !== null, "the revolver loads");
            tryVerify(() => widget.chambers.length === 8, 2000, "the drum is loaded from the scan");
            return widget;
        }

        function centre(widget) {
            return { x: 115 * widget.scaleFactor, y: 115 * widget.scaleFactor };
        }

        // A drag round the drum: `steps` moves of `degrees` each, `delay` ms apart.
        function drag(widget, degrees, steps, delay) {
            const c = centre(widget);
            const r = 70 * widget.scaleFactor;
            mousePress(widget, c.x + r, c.y);
            for (let i = 1; i <= steps; i++) {
                const t = i * degrees * Math.PI / 180;
                mouseMove(widget, c.x + r * Math.cos(t), c.y + r * Math.sin(t), delay);
            }
            const t = steps * degrees * Math.PI / 180;
            mouseRelease(widget, c.x + r * Math.cos(t), c.y + r * Math.sin(t));
        }

        function callsWith(word) {
            return Quickshell.calls.filter(args => args.indexOf(word) !== -1);
        }

        function test_scan_command() {
            const widget = makeRevolver();
            compare(callsWith("fire").length, 0, "nothing is fired until a spin lands");
            compare(widget.statusText, "Drag to spin");
        }

        function test_flick_fires_a_game() {
            const widget = makeRevolver();
            drag(widget, 20, 6, 8);
            verify(widget.spinning, "a flick spins the drum");
            tryVerify(() => callsWith("fire").length === 1, 6000, "the chamber under the hammer is fired");
            const fired = callsWith("fire")[0];
            compare(fired[1], "revolver");
            compare(fired[3], "steam");
            verify(["1", "2", "3", "4", "5", "6", "7", "8"].indexOf(fired[4]) !== -1, "a loaded game's id");
            tryCompare(widget, "ejectingIndex", -1, 4000, "the spent chamber is reloaded");
            compare(widget.chambers.length, 8);
            compare(callsWith("collapse").length, 0, "no collapse outside Red Sun");
        }

        function test_nudge_does_not_fire() {
            const widget = makeRevolver();
            drag(widget, 1, 4, 90);
            tryCompare(widget, "spinning", false, 3000);
            wait(800);
            compare(callsWith("fire").length, 0, "a slow nudge only settles the drum");
            compare(widget.statusText, "Drag to spin");
        }

        function test_red_sun_arms_the_collapse() {
            Config.options.halcyon.theme = "red-sun";
            const widget = makeRevolver();
            compare(widget.style.id, "red-sun");
            drag(widget, 20, 6, 8);
            tryVerify(() => callsWith("collapse").length === 1, 1000, "a spin arms the collapse");
            const args = callsWith("collapse")[0];
            compare(args[0], "/home/test/.config/hypr/hyprland/halcyon/halcyon-theme");
            compare(args[2], "arm");
            const age = parseFloat(args[3]), x = parseFloat(args[4]), y = parseFloat(args[5]), r = parseFloat(args[6]);
            verify(age >= 0 && age < 2, "how long ago the ring was grabbed: " + age);
            verify(x > 0 && x < 1 && y > 0 && y < 1, "the ring's centre as a fraction of the screen: " + x + ", " + y);
            verify(r > 0.01 && r < 0.5, "the ring's radius as a fraction of the screen height: " + r);
            tryVerify(() => widget.spinSpeed > 0.1, 1000, "the trails and the ring's light follow the speed");
        }

        function test_red_sun_tells_the_eye_where_the_car_is() {
            Config.options.halcyon.theme = "red-sun";
            const widget = makeRevolver();
            widget.sunRing = { x: 942, y: 466, r: 70.8 };
            widget.sunCar = { x: 1245, y: 765 };
            drag(widget, 20, 6, 8);
            tryVerify(() => callsWith("collapse").length === 1, 1000);
            const args = callsWith("collapse")[0];
            compare(args.length, 9, "AGE X Y R and the car");
            const ringY = parseFloat(args[5]), carX = parseFloat(args[7]), carY = parseFloat(args[8]);
            verify(carX > parseFloat(args[4]) && carY > ringY, "the car is below and right of the ring: " + carX + ", " + carY);
            verify(carX < 1 && carY < 1);
        }

        function test_red_sun_nudge_does_not_arm() {
            Config.options.halcyon.theme = "red-sun";
            const widget = makeRevolver();
            drag(widget, 1, 4, 90);
            wait(600);
            compare(callsWith("collapse").length, 0);
        }

        function test_red_sun_spins_without_games() {
            Config.options.halcyon.theme = "red-sun";
            MockIo.output = "[]";
            const widget = createTemporaryObject(revolverComponent, root);
            tryCompare(widget, "loading", false, 2000);
            compare(widget.statusText, "", "no 'nothing found' message on the ring");
            drag(widget, 20, 6, 8);
            tryVerify(() => callsWith("collapse").length === 1, 1000, "the ring still breaks the screen");
            compare(callsWith("fire").length, 0);
        }

        function test_on_the_painted_ring() {
            Config.options.halcyon.theme = "red-sun";
            const widget = makeRevolver();
            widget.sunRing = { x: 942, y: 466, r: 70.8 };
            verify(widget.ringAnchored);
            fuzzyCompare(widget.scaleFactor, 70.8 / 92, 0.001);
            fuzzyCompare(widget.x + 115 * widget.scaleFactor, 942, 0.5);
            fuzzyCompare(widget.y + 115 * widget.scaleFactor, 466, 0.5);
            Config.options.background.widgets.revolver.followRing = false;
            verify(!widget.ringAnchored, "followRing off keeps the saved place");
            Config.options.background.widgets.revolver.followRing = true;
        }

        // Off the painted ring (another wallpaper, the old theme name, followRing off) the drum draws the whole lit
        // sun itself; before, only the beads showed, floating round nothing.
        function test_red_sun_off_the_ring_draws_the_lit_ring() {
            Config.options.halcyon.theme = "red-sun";
            const widget = makeRevolver();
            const drum = findChild(widget, "drum");
            verify(drum, "the drum is reachable");
            verify(!widget.ringAnchored);
            verify(drum.standalone);
            verify(drum.ringLight >= 0.8, "lit at rest");
            widget.sunRing = { x: 942, y: 466, r: 70.8 };
            verify(!drum.standalone, "on the painted ring the wallpaper is the ring");
            compare(drum.ringLight, 0, "dark at rest there");
            widget.sunRing = { x: 0, y: 0, r: 0 };
            verify(!widget.ringAnchored, "a ring of no size is not a ring");
        }
    }

    // Every style, and the plates, load without errors.
    TestCase {
        name: "Styles"
        when: windowShown

        Component {
            id: drumComponent
            RevolverDrum {}
        }
        Component {
            id: plateComponent
            ThemedPlate { width: 200; height: 200 }
        }

        function test_every_style_draws() {
            for (const id of ["", "red-sun", "shattered-glass", "fractured-glass", "hyperneo", "hsr"]) {
                const drum = createTemporaryObject(drumComponent, root, { spinning: true, spinSpeed: 0.9, heat: 1 });
                verify(drum !== null, id);
                for (const kind of ["disc", "card"]) {
                    const plate = createTemporaryObject(plateComponent, root, { themeId: id, kind: kind });
                    verify(plate !== null, id + " " + kind);
                }
            }
        }
    }
}
