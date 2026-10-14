pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import qs.modules.ii.background.widgets
import "RevolverStyles.js" as Styles

/**
 * The revolver: a drum of installed games, drawn on the wallpaper.
 *
 * The look follows hyprland-revolver (MIT License, Copyright (c) 2026 minerofthesoal): a dial of eight chambers
 * round a hub, a hammer, and a muzzle burst, with a safety bar while the screen is locked. RevolverDrum draws it
 * in the active theme's own shapes (RevolverStyles.js). Chambers come from `halcyon-theme revolver scan`, which
 * reads the local Steam library or PrismLauncher.
 *
 * Dragging spins the drum with flick inertia, and the chamber that stops under the hammer is the one loaded. A
 * spin that lands on a loaded chamber fires it: the hammer strikes, the game starts, and the spent shell is ejected
 * and a new one loaded. A slow nudge settles the drum without firing, so only a deliberate spin launches a game.
 *
 * In the Red Sun theme the drum is the red ring of the wallpaper. It sits on the painted ring (unless
 * background.widgets.revolver.followRing is off), lights up while it turns, and a real spin breaks the screen:
 * `halcyon-theme collapse arm` switches the theme's collapse shader in for a few seconds.
 *
 * Its place is set by background.widgets.revolver.x and .y, and its size by .size. The drawing is laid out on a
 * 230 × 268 stage and scaled.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "revolver"
    draggable: false

    readonly property int chamberCount: 8
    readonly property real stageWidth: 230
    readonly property real stageHeight: 268
    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`

    readonly property var style: Styles.styleFor(Config.options.halcyon.theme)
    readonly property bool redSun: style.id === "red-sun"

    /** The ring painted in the Red Sun wallpaper, in this widget's parent's coordinates: {x, y, r}, or null. */
    property var sunRing: null
    /** The car on the road in the Red Sun wallpaper, in the same coordinates: {x, y}, or null. */
    property var sunCar: null
    readonly property bool ringAnchored: redSun && !!sunRing && sunRing.r > 0 && root.configEntry.followRing !== false

    readonly property real scaleFactor: ringAnchored ? sunRing.r / Styles.SUN_RING_STAGE_RADIUS
                                                  : Math.max(200, configEntry.size) / stageWidth

    // On the painted ring the drum's centre is the ring's centre.
    x: ringAnchored ? sunRing.x - Styles.CENTRE * scaleFactor : targetX
    y: ringAnchored ? sunRing.y - Styles.CENTRE * scaleFactor : targetY

    implicitWidth: stageWidth * scaleFactor
    implicitHeight: stageHeight * scaleFactor

    // The theme's colours, and Red Sun's own light.
    readonly property color colBase: Appearance.colors.colPrimaryContainer
    readonly property color colOn: Appearance.colors.colOnLayer1
    readonly property color colAccent: Appearance.colors.colPrimary
    readonly property color colChamber: Appearance.colors.colLayer0
    readonly property color colGlow: redSun ? "#ff4940" : Appearance.colors.colPrimary
    readonly property color colHot: redSun ? "#ffe2d6" : Appearance.colors.colOnPrimary

    property bool loading: false
    property bool spinning: false
    property bool firing: false
    /** True when the spin being released was a flick, not a nudge, so it may fire. */
    property bool landing: false
    /** False until a spin has landed on a loaded chamber. */
    property bool committedSpin: false
    /** [{id, name, source, weight}]: the chambers under the drum, one per slot. */
    property var chambers: []
    /** The full weighted pool from the last scan, used to load fresh rounds. */
    property var lastPool: []
    property var pendingChosen: null
    property int landedIndex: -1
    property int ejectingIndex: -1
    property string statusText: Translation.tr("Drag to spin")
    /** 0..1, how fast the drum is turning right now. */
    property real spinSpeed: 0
    property int spinDirection: 1
    /** When the current drag began (ms), to tell the collapse shader how long ago the press was. */
    property real pressTime: 0

    function refresh(): void {
        if (root.loading)
            return;
        root.loading = true;
        root.statusText = Translation.tr("Chambering...");
        scanWatchdog.restart();
        scanner.running = true;
    }

    function onScanFinished(text: string): void {
        root.loading = false;
        scanWatchdog.stop();
        let pool = [];
        try {
            pool = JSON.parse(text) ?? [];
        } catch (error) {
            pool = [];
        }
        if (pool.length === 0) {
            // In Red Sun the ring still turns, and still breaks the screen, with no games to load.
            root.statusText = root.redSun ? "" : Translation.tr("Nothing found for this source");
            return;
        }
        root.lastPool = pool;
        root.chambers = weightedPick(pool, root.chamberCount);
        root.landedIndex = -1;
        root.committedSpin = false;
        root.statusText = Translation.tr("Drag to spin");
    }

    // Weighted sample without replacement. Reshuffles from the full pool
    // when there are fewer games than chambers.
    function weightedPick(pool: var, count: int): var {
        let src = pool.slice();
        const out = [];
        for (let i = 0; i < count; i++) {
            if (src.length === 0)
                src = pool.slice();
            let total = 0;
            for (let j = 0; j < src.length; j++)
                total += src[j].weight;
            const r = Math.random() * total;
            let acc = 0;
            let pick = src.length - 1;
            for (let k = 0; k < src.length; k++) {
                acc += src[k].weight;
                if (r <= acc) {
                    pick = k;
                    break;
                }
            }
            out.push(src[pick]);
            src.splice(pick, 1);
        }
        return out;
    }

    // Valid resting rotations put a chamber's centre exactly under the hammer at
    // the top (270°). Chamber i sits at i·step before rotation, so it lands
    // there when the rotation is 270 - i·step, modulo one step.
    function snapToChamber(raw: real): real {
        const step = 360 / root.chamberCount;
        const offset = 270 % step;
        const mod = ((raw % step) + step) % step;
        let diff = offset - mod;
        if (diff > step / 2)
            diff -= step;
        if (diff < -step / 2)
            diff += step;
        return raw + diff;
    }

    function chamberAtRotation(rot: real): int {
        const step = 360 / root.chamberCount;
        const normR = ((rot % 360) + 360) % 360;
        const i = Math.round((270 - normR) / step);
        return ((i % root.chamberCount) + root.chamberCount) % root.chamberCount;
    }

    function releaseSpin(velocityPerMs: real): void {
        const vAbs = Math.min(2.2, Math.abs(velocityPerMs));
        const dir = velocityPerMs >= 0 ? 1 : -1;
        const flick = vAbs >= 0.03;
        // A nudge settles where it is; a flick carries the drum on.
        const extraDegrees = flick ? vAbs * 900 : 0;
        const duration = flick ? Math.max(500, Math.min(3200, 500 + vAbs * 1400)) : 350;
        const target = root.snapToChamber(drum.rotor.rotation + dir * extraDegrees);

        root.spinDirection = dir;
        root.committedSpin = root.chambers.length >= root.chamberCount;
        root.landedIndex = root.chamberAtRotation(target);
        root.landing = root.committedSpin && flick;
        root.spinning = true;
        if (root.committedSpin)
            root.statusText = Translation.tr("Spinning...");
        else if (!root.redSun)
            root.statusText = Translation.tr("Still chambering...");

        if (root.redSun && flick)
            root.armCollapse();

        spinAnim.duration = duration;
        spinAnim.to = target;
        spinAnim.start();
    }

    // Red Sun: tell the collapse shader where the ring is and how long ago it was grabbed. The tool checks the
    // theme and the effects level, and does nothing when the effect is off.
    function armCollapse(): void {
        const win = root.Window.window;
        const centre = drum.mapToItem(null, Styles.CENTRE, Styles.CENTRE);
        const width = win ? win.width : root.screenWidth;
        const height = win ? win.height : root.screenHeight;
        if (width <= 0 || height <= 0)
            return;
        const ringRadius = Styles.SUN_RING_STAGE_RADIUS * root.scaleFactor;
        const age = Math.max(0, (Date.now() - root.pressTime) / 1000);
        const args = [root.tool, "collapse", "arm", age.toFixed(3),
            (centre.x / width).toFixed(4), (centre.y / height).toFixed(4), (ringRadius / height).toFixed(4)];
        // The eye ends up looking at the car. Off the painted ring the tool puts it where it is in the wallpaper.
        if (root.ringAnchored && root.sunCar && root.parent) {
            const car = root.parent.mapToItem(null, root.sunCar.x, root.sunCar.y);
            args.push((car.x / width).toFixed(4), (car.y / height).toFixed(4));
        }
        Quickshell.execDetached(args);
    }

    function onSpinStopped(): void {
        root.spinning = false;
        if (!root.landing) {
            if (root.chambers.length > 0)
                root.statusText = Translation.tr("Drag to spin");
            return;
        }
        root.landing = false;
        root.fire();
    }

    // Fires the chamber under the hammer: the fire sequence, then the game starts.
    function fire(): void {
        const chosen = root.chambers[root.landedIndex];
        if (!chosen || root.firing || root.spinning)
            return;
        root.pendingChosen = chosen;
        root.statusText = chosen.name;
        fireSequence.start();
    }

    // Called as the hammer strikes. The source and id are passed as
    // arguments and never spliced into a script.
    function fireShot(): void {
        if (!root.pendingChosen)
            return;
        Quickshell.execDetached([root.tool, "revolver", "fire", root.pendingChosen.source, root.pendingChosen.id]);
        root.ejectingIndex = root.landedIndex;
        root.pendingChosen = null;
    }

    // Load a different game into the chamber, preferring one not already in
    // the drum, the way a fresh round is loaded after the spent shell.
    function replaceChamber(index: int): void {
        if (root.lastPool.length === 0)
            return;
        const loaded = root.chambers.map(c => c.id);
        let candidates = root.lastPool.filter(g => loaded.indexOf(g.id) === -1);
        if (candidates.length === 0)
            candidates = root.lastPool.slice();
        const updated = root.chambers.slice();
        updated[index] = root.weightedPick(candidates, 1)[0];
        root.chambers = updated;
    }

    onVisibleChanged: if (visible && root.chambers.length === 0) root.refresh()
    Component.onCompleted: root.refresh()

    Connections {
        target: root.configEntry

        function onSourceChanged(): void {
            root.lastPool = [];
            root.refresh();
        }

        function onModeChanged(): void {
            root.refresh();
        }
    }

    Process {
        id: scanner

        command: [root.tool, "revolver", "scan", "--json", "--source", root.configEntry.source, "--mode", root.configEntry.mode]
        stdout: StdioCollector {
            onStreamFinished: root.onScanFinished(this.text)
        }
        // A scan that cannot run at all never reaches onStreamFinished, so
        // `loading` must be cleared here too, or the drum would stay locked.
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0 && root.loading) {
                root.loading = false;
                root.statusText = root.redSun ? "" : Translation.tr("Scan failed");
            }
        }
    }

    // Belt and braces for a scan that hangs rather than exits.
    Timer {
        id: scanWatchdog

        interval: 15000
        repeat: false
        onTriggered: {
            if (root.loading) {
                scanner.running = false;
                root.loading = false;
                root.statusText = root.redSun ? "" : Translation.tr("Scan timed out");
            }
        }
    }

    NumberAnimation {
        id: spinAnim

        target: drum.rotor
        property: "rotation"
        easing.type: Easing.OutCubic
        onStopped: root.onSpinStopped()
    }

    // How fast the drum turns, sampled while it moves: drives the trails and the Red Sun ring's light.
    Timer {
        id: speedSampler
        property real lastRotation: 0
        interval: 33
        repeat: true
        running: root.spinning || dragArea.pressed
        onRunningChanged: lastRotation = drum.rotor.rotation
        onTriggered: {
            const degreesPerMs = Math.abs(drum.rotor.rotation - lastRotation) / interval;
            lastRotation = drum.rotor.rotation;
            root.spinSpeed = Math.min(1, root.spinSpeed * 0.5 + (degreesPerMs / 1.1) * 0.5);
        }
    }
    onSpinningChanged: if (!spinning && !dragArea.pressed) root.spinSpeed = 0

    SequentialAnimation {
        id: fireSequence

        ScriptAction { script: root.firing = true }
        NumberAnimation { target: drum.hammerItem; property: "rotation"; to: -35; duration: 200; easing.type: Easing.OutQuad }
        PauseAnimation { duration: 90 }
        ScriptAction { script: root.fireShot() }
        ScriptAction { script: root.firing = false }
        ParallelAnimation {
            NumberAnimation { target: drum.hammerItem; property: "rotation"; to: 0; duration: 70; easing.type: Easing.InQuad }
            NumberAnimation { target: recoil; property: "y"; to: -8; duration: 60; easing.type: Easing.OutQuad }
            ScriptAction { script: muzzleBurst.burst() }
        }
        NumberAnimation { target: recoil; property: "y"; to: 0; duration: 260; easing.type: Easing.OutBack }
    }

    Item {
        id: stage

        width: root.stageWidth
        height: root.stageHeight
        scale: root.scaleFactor
        transformOrigin: Item.TopLeft
        // Under a glass theme the drum is a little see-through, like the glass around it.
        opacity: Config.options.halcyon.glassTheme ? 0.86 : 1.0
        Behavior on opacity {
            NumberAnimation { duration: Appearance.animation.elementMoveFast.duration }
        }

        Item {
            id: drumArea

            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: 230
            height: 230

            // Everything that kicks back on recoil, in a plain Item so animating its y cannot disturb an anchor.
            Item {
                id: recoil
                width: parent.width
                height: parent.height

                RevolverDrum {
                    id: drum
                    objectName: "drum"

                    style: root.style
                    colBase: root.colBase
                    colOn: root.colOn
                    colAccent: root.colAccent
                    colChamber: root.colChamber
                    colGlow: root.colGlow
                    colHot: root.colHot
                    fontFamily: Appearance.font.family.main
                    chambers: root.chambers
                    chamberCount: root.chamberCount
                    liveIndex: root.committedSpin ? root.landedIndex : -1
                    ejectingIndex: root.ejectingIndex
                    spinning: root.spinning
                    spinSpeed: root.spinSpeed
                    spinDirection: root.spinDirection
                    locked: GlobalStates.screenLocked
                    // The Red Sun ring burns while it turns, and cools slowly after.
                    heat: root.redSun && (root.spinning || dragArea.pressed) ? Math.max(0.55, root.spinSpeed) : 0
                    standalone: root.redSun && !root.ringAnchored
                    Behavior on heat {
                        NumberAnimation { duration: drum.heat > 0.1 ? 1400 : 380; easing.type: Easing.OutCubic }
                    }

                    onSwapChamber: index => root.replaceChamber(index)
                    onEjectDone: index => {
                        if (root.ejectingIndex === index) {
                            root.ejectingIndex = -1;
                            root.statusText = Translation.tr("Drag to spin");
                        }
                    }
                }

                // The muzzle burst. Hand-animated dots, not QtQuick.Particles.
                Item {
                    id: muzzleBurst

                    x: Styles.CENTRE
                    y: root.redSun ? Styles.CENTRE - Styles.SUN_RING_STAGE_RADIUS : -4
                    width: 1
                    height: 1

                    function burst(): void {
                        const count = root.redSun ? 16 : 9;
                        for (let i = 0; i < count; i++) {
                            const p = particleComponent.createObject(muzzleBurst);
                            const angle = (Math.random() * 140 - 70 - 90) * Math.PI / 180;
                            const dist = (root.redSun ? 26 : 18) + Math.random() * 16;
                            p.targetX = Math.cos(angle) * dist;
                            p.targetY = Math.sin(angle) * dist;
                            p.start();
                        }
                    }

                    Component {
                        id: particleComponent

                        Rectangle {
                            id: particle

                            property real targetX: 0
                            property real targetY: 0

                            width: root.redSun ? 3 : 4
                            height: width
                            radius: width / 2
                            x: -width / 2
                            y: -width / 2
                            color: root.redSun ? (Math.random() < 0.5 ? root.colHot : root.colGlow) : root.colAccent

                            function start(): void {
                                particleAnim.start();
                            }

                            ParallelAnimation {
                                id: particleAnim

                                NumberAnimation { target: particle; property: "x"; to: particle.targetX; duration: 300; easing.type: Easing.OutQuad }
                                NumberAnimation { target: particle; property: "y"; to: particle.targetY; duration: 300; easing.type: Easing.OutQuad }
                                NumberAnimation { target: particle; property: "opacity"; from: 1; to: 0; duration: 300 }
                                onStopped: particle.destroy()
                            }
                        }
                    }
                }
            }

            // Drag anywhere on the drum to turn it. Releasing carries the
            // drum on with the flick's speed.
            MouseArea {
                id: dragArea

                property real lastAngle: 0
                property real lastTimestamp: 0
                property real velocity: 0 // degrees per ms, smoothed

                anchors.fill: parent
                // Spinning waits for a spent shell to be reloaded.
                enabled: !GlobalStates.screenLocked && !root.firing && root.ejectingIndex < 0
                preventStealing: true
                cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor

                function angleAt(mx: real, my: real): real {
                    return Math.atan2(my - height / 2, mx - width / 2) * 180 / Math.PI;
                }

                onPressed: mouse => {
                    if (root.spinning)
                        return;
                    spinAnim.stop();
                    root.pressTime = Date.now();
                    dragArea.lastAngle = dragArea.angleAt(mouse.x, mouse.y);
                    dragArea.lastTimestamp = Date.now();
                    dragArea.velocity = 0;
                }

                onPositionChanged: mouse => {
                    if (!dragArea.pressed || root.spinning)
                        return;
                    const a = dragArea.angleAt(mouse.x, mouse.y);
                    let delta = a - dragArea.lastAngle;
                    while (delta > 180) delta -= 360;
                    while (delta < -180) delta += 360;
                    const now = Date.now();
                    const dt = Math.max(1, now - dragArea.lastTimestamp);
                    dragArea.velocity = dragArea.velocity * 0.7 + (delta / dt) * 0.3;
                    drum.rotor.rotation += delta;
                    dragArea.lastAngle = a;
                    dragArea.lastTimestamp = now;
                }

                onReleased: {
                    if (root.spinning)
                        return;
                    root.releaseSpin(dragArea.velocity);
                }
            }
        }

        StyledText {
            anchors.top: drumArea.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: root.redSun ? 4 : 12
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            visible: root.style.statusLabel && text !== ""
            text: root.statusText
            color: root.redSun ? root.colHot : root.colOn
            style: Text.Outline
            styleColor: ColorUtils.applyAlpha("#000000", 0.35)
            font.pixelSize: 11
            font.weight: Font.Medium
        }
    }
}
