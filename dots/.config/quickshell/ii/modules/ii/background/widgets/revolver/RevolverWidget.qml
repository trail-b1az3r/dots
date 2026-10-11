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

/**
 * The revolver: a drum of installed games, drawn on the wallpaper.
 *
 * The look follows hyprland-revolver (MIT License, Copyright (c) 2026
 * minerofthesoal): a wavy cookie dial, eight chambers around a hub, a
 * hammer, a side-loading clip, a muzzle burst, and a diagonal lock bar
 * while the screen is locked. Chambers come from `halcyon-theme revolver
 * scan`, which reads the local Steam library or PrismLauncher.
 *
 * Dragging spins the drum with flick inertia, and the chamber that stops
 * under the pin is the one loaded. Firing is deliberately a click on the
 * hub, not the spin's end, so a stray drag can never launch a game. The
 * click plays the fire sequence: the clip slides in, the hammer strikes,
 * the game starts, and the spent shell is ejected and a new one loaded.
 *
 * Its place is set by background.widgets.revolver.x and .y, and its size
 * by .size. The drawing is laid out on a 230 × 268 stage and scaled.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "revolver"
    draggable: false

    readonly property int chamberCount: 8
    readonly property real stageWidth: 230
    readonly property real stageHeight: 268
    readonly property real scaleFactor: Math.max(200, configEntry.size) / stageWidth

    readonly property color colBackground: Appearance.colors.colPrimaryContainer
    readonly property color colOnBackground: Appearance.colors.colSecondary
    readonly property color colAccent: Appearance.colors.colTertiary
    readonly property color colChamber: Appearance.colors.colShadow

    implicitWidth: stageWidth * scaleFactor
    implicitHeight: stageHeight * scaleFactor

    property bool loading: false
    property bool spinning: false
    property bool firing: false
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
            root.statusText = Translation.tr("Nothing found for this source");
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

    // Valid resting rotations put a chamber's centre exactly under the pin at
    // the top (270°). Chamber i sits at i·step before rotation, so it lands on
    // the pin when the rotation is 270 - i·step, modulo one step.
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
        // A nudge settles where it is; a flick carries the drum on.
        const extraDegrees = vAbs < 0.03 ? 0 : vAbs * 900;
        const duration = vAbs < 0.03 ? 350 : Math.max(500, Math.min(3200, 500 + vAbs * 1400));
        const target = root.snapToChamber(drum.rotation + dir * extraDegrees);

        root.committedSpin = root.chambers.length >= root.chamberCount;
        root.landedIndex = root.chamberAtRotation(target);
        root.spinning = true;
        root.statusText = root.committedSpin ? Translation.tr("Spinning...") : Translation.tr("Still chambering...");

        spinAnim.duration = duration;
        spinAnim.to = target;
        spinAnim.start();
    }

    function onSpinStopped(): void {
        root.spinning = false;
        const chosen = root.chambers[root.landedIndex];
        if (!root.committedSpin || !chosen) {
            root.statusText = Translation.tr("Drag to spin");
            return;
        }
        root.statusText = Translation.tr("Click the hub to fire");
    }

    function fire(): void {
        const chosen = root.chambers[root.landedIndex];
        if (!chosen || root.firing || root.spinning)
            return;
        root.pendingChosen = chosen;
        fireSequence.start();
    }

    // Called as the hammer strikes. The source and id are passed as
    // arguments and never spliced into a script.
    function fireShot(): void {
        if (!root.pendingChosen)
            return;
        Quickshell.execDetached(["bash", "-c",
            'exec "$HOME/.config/hypr/hyprland/halcyon/halcyon-theme" revolver fire "$1" "$2"',
            "bash", root.pendingChosen.source, root.pendingChosen.id]);
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

        command: ["bash", "-c",
            'exec "$HOME/.config/hypr/hyprland/halcyon/halcyon-theme" revolver scan --json' +
            ' --source "$1" --mode "$2"',
            "bash", root.configEntry.source, root.configEntry.mode]
        stdout: StdioCollector {
            onStreamFinished: root.onScanFinished(this.text)
        }
        // A scan that cannot run at all never reaches onStreamFinished, so
        // `loading` must be cleared here too, or the drum would stay locked.
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0 && root.loading) {
                root.loading = false;
                root.statusText = Translation.tr("Scan failed");
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
                root.statusText = Translation.tr("Scan timed out");
            }
        }
    }

    NumberAnimation {
        id: spinAnim

        target: drum
        property: "rotation"
        easing.type: Easing.OutCubic
        onStopped: root.onSpinStopped()
    }

    SequentialAnimation {
        id: fireSequence

        ScriptAction { script: root.firing = true }
        NumberAnimation { target: gunFrame; property: "opacity"; to: 1; duration: 180 }
        NumberAnimation { target: clipItem; property: "x"; to: 4; duration: 220; easing.type: Easing.OutBack }
        PauseAnimation { duration: 120 }
        NumberAnimation { target: clipItem; property: "x"; to: -40; duration: 180; easing.type: Easing.InBack }
        NumberAnimation { target: hammer; property: "rotation"; to: -35; duration: 180; easing.type: Easing.OutQuad }
        ScriptAction { script: root.fireShot() }
        ScriptAction { script: root.firing = false }
        ParallelAnimation {
            NumberAnimation { target: hammer; property: "rotation"; to: 0; duration: 70; easing.type: Easing.InQuad }
            NumberAnimation { target: recoilWrapper; property: "y"; to: -8; duration: 60; easing.type: Easing.OutQuad }
            ScriptAction { script: muzzleBurst.burst() }
        }
        NumberAnimation { target: recoilWrapper; property: "y"; to: 0; duration: 260; easing.type: Easing.OutBack }
        NumberAnimation { target: gunFrame; property: "opacity"; to: 0; duration: 220 }
    }

    Item {
        id: stage

        width: root.stageWidth
        height: root.stageHeight
        scale: root.scaleFactor
        transformOrigin: Item.TopLeft

        Item {
            id: drumArea

            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: 230
            height: 230

            // The gun frame: an abstract outline that fades in behind the
            // drum during the fire sequence.
            Rectangle {
                id: gunFrame

                anchors.centerIn: parent
                width: parent.width + 36
                height: parent.height * 0.5
                y: parent.height * 0.58
                radius: 20
                color: "transparent"
                border.color: root.colOnBackground
                border.width: 2
                opacity: 0
                z: -1
            }

            // Everything that kicks back on recoil lives in this plain Item, so
            // animating its y cannot disturb an anchor on drumArea.
            Item {
                id: recoilWrapper

                width: parent.width
                height: parent.height

                StyledDropShadow {
                    target: cookieLoader
                }

                Loader {
                    id: cookieLoader

                    anchors.fill: parent
                    visible: false // StyledDropShadow draws it
                    sourceComponent: MaterialCookie {
                        implicitSize: drumArea.width
                        sides: root.chamberCount
                        color: root.colBackground
                    }
                }

                Item {
                    id: drum

                    anchors.fill: parent
                    rotation: 0

                    Repeater {
                        model: root.chamberCount

                        delegate: Item {
                            id: chamberSlot

                            required property int index
                            readonly property var entry: root.chambers[index]
                            readonly property real angle: index * (360 / root.chamberCount) * Math.PI / 180
                            readonly property bool isLive: root.landedIndex === index && !root.spinning && root.committedSpin
                            readonly property bool isEjecting: root.ejectingIndex === index

                            x: drum.width / 2 + Math.cos(angle) * 82 - 24
                            y: drum.height / 2 + Math.sin(angle) * 82 - 24
                            width: 48
                            height: 48
                            // Counter-rotate so the labels stay upright as the drum turns.
                            rotation: -drum.rotation

                            // Rising edge only: the sequence runs to the end once started.
                            onIsEjectingChanged: if (chamberSlot.isEjecting) ejectReload.start()

                            // Everything that moves during an eject and reload lives here,
                            // so the chamber's own position stays fixed on the drum.
                            Item {
                                id: shell

                                property real fallY: 0
                                property real wobble: 0

                                anchors.fill: parent
                                transform: [
                                    Rotation { angle: shell.wobble; origin.x: shell.width / 2; origin.y: shell.height / 2 },
                                    Translate { y: shell.fallY }
                                ]

                                // The brass rim, peeking out behind the casing.
                                Rectangle {
                                    anchors.fill: parent
                                    radius: width / 2
                                    color: chamberSlot.isLive ? root.colAccent : Qt.lighter(root.colChamber, 1.4)
                                    opacity: chamberSlot.isLive ? 0.55 : 0.35
                                }

                                // The casing face, carrying the game's name.
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    radius: width / 2
                                    color: chamberSlot.isLive ? root.colAccent : root.colChamber
                                    opacity: chamberSlot.isLive ? 0.92 : 0.5
                                    border.width: 1
                                    border.color: Qt.darker(chamberSlot.isLive ? root.colAccent : root.colChamber, 1.3)

                                    StyledText {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        text: chamberSlot.entry ? chamberSlot.entry.name : "—"
                                        color: root.colOnBackground
                                        font.pixelSize: chamberSlot.isLive ? 9 : 8
                                        font.bold: chamberSlot.isLive
                                        wrapMode: Text.WordWrap
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        maximumLineCount: 4
                                    }
                                }

                                // The primer, a small dot near the rim.
                                Rectangle {
                                    anchors.top: parent.top
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.topMargin: 3
                                    width: 7
                                    height: 7
                                    radius: 3.5
                                    color: chamberSlot.isLive ? root.colOnBackground : Qt.darker(root.colChamber, 1.2)
                                    opacity: chamberSlot.isLive ? 0.9 : 0.55
                                    border.width: 1
                                    border.color: root.colBackground
                                }
                            }

                            // The spent shell drops clear, the next round loads while
                            // it is out of sight, and it drops back in and settles.
                            SequentialAnimation {
                                id: ejectReload

                                ParallelAnimation {
                                    NumberAnimation { target: shell; property: "fallY"; to: 46; duration: 240; easing.type: Easing.InQuad }
                                    NumberAnimation { target: shell; property: "wobble"; to: (chamberSlot.index % 2 === 0 ? 1 : -1) * 50; duration: 240; easing.type: Easing.InQuad }
                                    NumberAnimation { target: shell; property: "opacity"; to: 0; duration: 220 }
                                }
                                ScriptAction { script: root.replaceChamber(chamberSlot.index) }
                                PropertyAction { target: shell; property: "fallY"; value: -46 }
                                PropertyAction { target: shell; property: "wobble"; value: 0 }
                                PropertyAction { target: shell; property: "opacity"; value: 0 }
                                PauseAnimation { duration: 60 }
                                ParallelAnimation {
                                    NumberAnimation { target: shell; property: "fallY"; to: 0; duration: 260; easing.type: Easing.OutBack }
                                    NumberAnimation { target: shell; property: "opacity"; to: 1; duration: 200 }
                                }
                                ScriptAction { script: if (root.ejectingIndex === chamberSlot.index) root.ejectingIndex = -1 }
                            }
                        }
                    }
                }

                // The hub, the axis the cylinder turns on.
                Item {
                    anchors.centerIn: parent
                    width: 46
                    height: 46

                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: root.colChamber
                        opacity: 0.65
                        border.color: root.colOnBackground
                        border.width: 1
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * 0.55
                        height: width
                        radius: width / 2
                        color: root.colAccent
                        opacity: 0.85
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * 0.3
                        height: 3
                        radius: 1.5
                        color: root.colBackground
                        opacity: 0.85
                    }
                }

                // The hammer hinges at its base, cocks back, then strikes.
                Item {
                    id: hammer

                    anchors.horizontalCenter: parent.horizontalCenter
                    y: -26
                    width: 14
                    height: 20
                    rotation: 0
                    transformOrigin: Item.Bottom

                    Rectangle {
                        anchors.fill: parent
                        radius: 3
                        color: root.colAccent
                        border.color: root.colOnBackground
                        border.width: 1
                    }
                }

                // The side clip. It is only visible during the fire sequence, and
                // x: -40 is its retracted position, not an off-widget one.
                Rectangle {
                    id: clipItem

                    visible: root.firing
                    width: 14
                    height: 50
                    radius: 3
                    anchors.verticalCenter: parent.verticalCenter
                    x: -40
                    color: root.colChamber
                    border.color: root.colOnBackground
                    border.width: 1
                }

                // The muzzle burst. Hand-animated dots, not QtQuick.Particles.
                Item {
                    id: muzzleBurst

                    anchors.horizontalCenter: parent.horizontalCenter
                    y: -4
                    width: 1
                    height: 1

                    function burst(): void {
                        for (let i = 0; i < 8; i++) {
                            const p = particleComponent.createObject(muzzleBurst);
                            const angle = (Math.random() * 140 - 70 - 90) * Math.PI / 180;
                            const dist = 18 + Math.random() * 14;
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

                            width: 4
                            height: 4
                            radius: 2
                            x: -2
                            y: -2
                            color: root.colAccent

                            function start(): void {
                                particleAnim.start();
                            }

                            ParallelAnimation {
                                id: particleAnim

                                NumberAnimation { target: particle; property: "x"; to: particle.targetX; duration: 260; easing.type: Easing.OutQuad }
                                NumberAnimation { target: particle; property: "y"; to: particle.targetY; duration: 260; easing.type: Easing.OutQuad }
                                NumberAnimation { target: particle; property: "opacity"; from: 1; to: 0; duration: 260 }
                                onStopped: particle.destroy()
                            }
                        }
                    }
                }

                // The firing pin. Whatever chamber stops here is the one loaded.
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: -4
                    width: 8
                    height: 8
                    radius: 4
                    color: root.colAccent
                }
            }

            // The diagonal safety bar, shown while the screen is locked.
            Rectangle {
                id: lockBar

                visible: GlobalStates.screenLocked
                z: 20
                anchors.centerIn: parent
                width: parent.width * 1.05
                height: 26
                rotation: -8
                radius: 4
                border.color: root.colBackground
                border.width: 1
                gradient: Gradient {
                    GradientStop { position: 0.0; color: root.colChamber }
                    GradientStop { position: 0.5; color: root.colOnBackground }
                    GradientStop { position: 1.0; color: root.colChamber }
                }

                // Brushed-metal hatching.
                Repeater {
                    model: 14

                    delegate: Rectangle {
                        required property int index

                        x: index * (lockBar.width / 14)
                        width: 2
                        height: lockBar.height
                        rotation: 20
                        color: root.colBackground
                        opacity: 0.25
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8
                    height: 8
                    radius: 4
                    color: root.colAccent
                    border.color: root.colBackground
                }
                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8
                    height: 8
                    radius: 4
                    color: root.colAccent
                    border.color: root.colBackground
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
                enabled: !GlobalStates.screenLocked && !root.firing
                preventStealing: true

                function angleAt(mx: real, my: real): real {
                    return Math.atan2(my - height / 2, mx - width / 2) * 180 / Math.PI;
                }

                onPressed: mouse => {
                    if (root.spinning)
                        return;
                    spinAnim.stop();
                    dragArea.lastAngle = dragArea.angleAt(mouse.x, mouse.y);
                    dragArea.lastTimestamp = Date.now();
                    dragArea.velocity = 0;
                    root.statusText = "...";
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
                    drum.rotation += delta;
                    dragArea.lastAngle = a;
                    dragArea.lastTimestamp = now;
                }

                onReleased: {
                    if (root.spinning)
                        return;
                    root.releaseSpin(dragArea.velocity);
                }
            }

            // The trigger. A click on the hub fires the chamber under the pin,
            // and only once a spin has landed on a loaded chamber.
            MouseArea {
                anchors.centerIn: parent
                width: 46
                height: 46
                z: 30
                enabled: root.committedSpin && !root.spinning && !root.firing
                    && root.ejectingIndex < 0 && !GlobalStates.screenLocked
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.fire()
            }
        }

        StyledText {
            anchors.top: drumArea.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 10
            text: root.statusText
            color: root.colOnBackground
            font.pixelSize: 11
        }
    }
}
