import QtQuick
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

/**
 * The revolver's launch: when a spin starts a game, a shot leaves the drum and the game arrives on screen.
 *
 *   the shot     a flash at the drum, and a tracer from it to the middle of the screen
 *   impact       a shockwave, and the game's card (its Steam art) spinning in like a chamber turning into place
 *   loading      the game's name typed out under LOADING, with the drum's eight chambers going round
 *   gone         when the game's window opens (at most 9 s), the card bursts forward and fades
 *
 * Drawn on its own layer over everything, which takes no clicks and no keyboard, so nothing waits for it.
 * Settings > Revolver > Launch animation turns it off.
 */
Scope {
    id: root

    property color colGlow: Appearance.colors.colPrimary
    property color colHot: Appearance.colors.colOnPrimary
    property string tool: ""

    // What is being launched, and from where on which screen.
    property var game: null            // {id, name, source}
    property var screen: null
    property point origin: Qt.point(0, 0)
    property var art: ({})
    property bool running: false
    property bool leaving: false
    property real startedAt: 0

    readonly property int minShown: 1800
    readonly property int maxShown: 9000

    function play(game, screen, origin): void {
        if (!Config.options.background.widgets.revolver.launchAnimation)
            return;
        root.game = game;
        root.screen = screen;
        root.origin = origin;
        root.art = ({});
        root.startedAt = Date.now();
        root.leaving = false;
        root.running = true;
        if (game.source === "steam" && root.tool !== "") {
            artProc.command = [root.tool, "revolver", "art", "steam", String(game.id)];
            artProc.running = true;
        }
    }

    function finish(): void {
        root.running = false;
        root.leaving = false;
    }

    Process {
        id: artProc
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.art = JSON.parse(this.text) ?? {};
                } catch (error) {
                    root.art = {};
                }
            }
        }
    }

    // The game's window opening ends it: a Steam game's class is steam_app_<id>; anything else, its name in the title.
    Connections {
        target: HyprlandData
        enabled: root.running
        function onWindowListChanged() {
            if (!root.game)
                return;
            const wanted = `steam_app_${root.game.id}`;
            const name = String(root.game.name ?? "").toLowerCase();
            const opened = HyprlandData.windowList.some(win => win.class === wanted
                || (name.length > 3 && String(win.title ?? "").toLowerCase().includes(name)));
            if (opened) {
                // Shown for a moment at least, so it never just flickers.
                outTimer.interval = Math.max(1, root.minShown - (Date.now() - root.startedAt));
                outTimer.restart();
            }
        }
    }
    Timer {
        id: outTimer
        interval: root.maxShown
        running: root.running
        onTriggered: root.leaving = true
        onRunningChanged: if (running) interval = root.maxShown
    }

    LazyLoader {
        active: root.running

        PanelWindow {
            id: win
            screen: root.screen
            color: "transparent"
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.namespace: "quickshell:revolver-launch"
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            anchors {
                top: true
                bottom: true
                left: true
                right: true
            }
            // Takes no clicks: everything under it works as usual.
            mask: Region {}

            Item {
                id: stage
                anchors.fill: parent
                readonly property point centre: Qt.point(width / 2, height * 0.46)
                readonly property real cardWidth: Math.min(width * 0.36, 640)

                function leave(): void {
                    if (!exitAnim.running)
                        exitAnim.start();
                }
                Connections {
                    target: root
                    function onLeavingChanged() {
                        if (root.leaving)
                            stage.leave();
                    }
                }

                // ── The shot ─────────────────────────────────────────────────────────────────
                // A soft glow from the drum, fading out from its middle.
                RadialGradient {
                    id: flash
                    readonly property real size: Math.max(stage.width, stage.height) * 0.9
                    x: root.origin.x - size / 2
                    y: root.origin.y - size / 2
                    width: size
                    height: size
                    opacity: 0
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: ColorUtils.transparentize("white", 0.2) }
                        GradientStop { position: 0.12; color: ColorUtils.transparentize(root.colGlow, 0.35) }
                        GradientStop { position: 0.5; color: "transparent" }
                    }
                }
                Rectangle {
                    id: flashCore
                    x: root.origin.x - 60
                    y: root.origin.y - 60
                    width: 120
                    height: 120
                    radius: 60
                    color: "white"
                    opacity: 0
                    scale: 0.2
                }

                // The tracer: a hot streak from the drum to where the card lands.
                Item {
                    id: tracer
                    readonly property real dx: stage.centre.x - root.origin.x
                    readonly property real dy: stage.centre.y - root.origin.y
                    readonly property real len: Math.sqrt(dx * dx + dy * dy)
                    property real progress: 0
                    x: root.origin.x
                    y: root.origin.y
                    rotation: Math.atan2(dy, dx) * 180 / Math.PI
                    transformOrigin: Item.TopLeft
                    opacity: 0
                    Rectangle {
                        x: Math.max(0, tracer.progress * tracer.len - width)
                        y: -3
                        width: Math.min(tracer.len * 0.45, tracer.progress * tracer.len)
                        height: 6
                        radius: 3
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.7; color: root.colGlow }
                            GradientStop { position: 1.0; color: "white" }
                        }
                    }
                }

                // ── Impact ───────────────────────────────────────────────────────────────────
                Repeater {
                    id: shockwaves
                    model: 2
                    delegate: Rectangle {
                        id: wave
                        required property int index
                        property real grow: 0
                        readonly property real size: 80 + grow * Math.max(stage.width, stage.height) * (0.7 + 0.3 * index)
                        x: stage.centre.x - size / 2
                        y: stage.centre.y - size / 2
                        width: size
                        height: size
                        radius: size / 2
                        color: "transparent"
                        border.width: Math.max(1, 10 * (1 - grow))
                        border.color: index === 0 ? "white" : root.colGlow
                        opacity: grow > 0 ? (1 - grow) * 0.9 : 0
                        NumberAnimation on grow {
                            id: waveAnim
                            running: false
                            from: 0
                            to: 1
                            duration: 900 + wave.index * 300
                            easing.type: Easing.OutCubic
                        }
                        function go(): void {
                            waveAnim.restart();
                        }
                    }
                }

                // The card: the game's art, a frame in the theme's light, spinning in like a chamber.
                Item {
                    id: card
                    width: stage.cardWidth
                    height: width * 215 / 460
                    x: stage.centre.x - width / 2
                    y: stage.centre.y - height / 2
                    opacity: 0
                    scale: 0.4
                    transform: Rotation {
                        id: flip
                        origin.x: card.width / 2
                        origin.y: card.height / 2
                        axis { x: 0; y: 1; z: 0 }
                        angle: 0
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -4
                        radius: Appearance.rounding.normal + 4
                        color: "transparent"
                        border.width: 2
                        border.color: root.colGlow
                        opacity: 0.9
                    }
                    StyledRectangularShadow {
                        target: cardFace
                    }
                    Rectangle {
                        id: cardFace
                        anchors.fill: parent
                        radius: Appearance.rounding.normal
                        color: Appearance.colors.colLayer1
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: root.art.header ? "file://" + root.art.header : (root.art.hero ? "file://" + root.art.hero : "")
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            visible: status === Image.Ready
                        }
                        MaterialSymbol {
                            anchors.centerIn: parent
                            visible: !root.art.header && !root.art.hero
                            text: "sports_esports"
                            iconSize: parent.height * 0.5
                            color: root.colGlow
                        }
                        // A sweep of light across it as it lands.
                        Rectangle {
                            id: sheen
                            property real at: -0.4
                            x: at * parent.width
                            y: -parent.height * 0.5
                            width: parent.width * 0.25
                            height: parent.height * 2
                            rotation: 18
                            opacity: 0.55
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.5; color: ColorUtils.transparentize("white", 0.35) }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                        }
                    }
                }

                // ── Loading ──────────────────────────────────────────────────────────────────
                // A dark glass behind the words, so they read over any wallpaper.
                Rectangle {
                    x: caption.x - 28
                    y: caption.y - 12
                    width: caption.width + 56
                    height: caption.height + 24
                    radius: Appearance.rounding.normal
                    color: ColorUtils.transparentize("black", 0.45)
                    border.width: 1
                    border.color: ColorUtils.transparentize(root.colGlow, 0.6)
                    opacity: caption.opacity
                }
                Column {
                    id: caption
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: card.y + card.height + 28
                    spacing: 6
                    opacity: 0
                    property int typed: 0

                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: Translation.tr("LOADING")
                        font.pixelSize: Appearance.font.pixelSize.small
                        font.letterSpacing: 6
                        color: root.colGlow
                    }
                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        readonly property string full: String(root.game?.name ?? "")
                        text: full.slice(0, caption.typed) + (caption.typed < full.length ? "▌" : "")
                        font.family: Appearance.font.family.expressive
                        font.pixelSize: Math.max(28, stage.cardWidth / 14)
                        font.weight: Font.DemiBold
                        color: "white"
                        style: Text.Raised
                        styleColor: ColorUtils.transparentize("black", 0.4)
                    }
                    // The drum's eight chambers going round while the game starts.
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 10
                        topPadding: 8
                        Repeater {
                            model: 8
                            delegate: Rectangle {
                                required property int index
                                width: 10
                                height: 10
                                radius: 5
                                readonly property real lit: Math.max(0, 1 - ((chamberTick.step - index + 8) % 8) / 3)
                                color: lit > 0.9 ? "white" : root.colGlow
                                opacity: 0.3 + 0.7 * lit
                            }
                        }
                    }
                    Timer {
                        id: chamberTick
                        property int step: 0
                        interval: 110
                        repeat: true
                        running: caption.opacity > 0
                        onTriggered: step = (step + 1) % 8
                    }
                }
                NumberAnimation {
                    id: typeAnim
                    target: caption
                    property: "typed"
                    from: 0
                    to: String(root.game?.name ?? "").length
                    duration: Math.min(900, 45 * String(root.game?.name ?? "").length)
                }

                // ── The timeline ─────────────────────────────────────────────────────────────
                SequentialAnimation {
                    id: enterAnim
                    running: true
                    ParallelAnimation {
                        NumberAnimation { target: flashCore; property: "opacity"; from: 1; to: 0; duration: 260 }
                        NumberAnimation { target: flashCore; property: "scale"; from: 0.2; to: 1.6; duration: 260; easing.type: Easing.OutQuad }
                        NumberAnimation { target: flash; property: "opacity"; from: 0.9; to: 0; duration: 420; easing.type: Easing.OutQuad }
                        SequentialAnimation {
                            PropertyAction { target: tracer; property: "opacity"; value: 1 }
                            NumberAnimation { target: tracer; property: "progress"; from: 0; to: 1; duration: 200; easing.type: Easing.InQuad }
                            NumberAnimation { target: tracer; property: "opacity"; to: 0; duration: 120 }
                        }
                    }
                    ScriptAction {
                        script: {
                            for (let i = 0; i < shockwaves.count; i++)
                                shockwaves.itemAt(i).go();
                        }
                    }
                    ParallelAnimation {
                        NumberAnimation { target: card; property: "opacity"; from: 0; to: 1; duration: 180 }
                        NumberAnimation { target: card; property: "scale"; from: 0.4; to: 1; duration: 620; easing.type: Easing.OutBack; easing.overshoot: 1.6 }
                        NumberAnimation { target: flip; property: "angle"; from: -110; to: 0; duration: 700; easing.type: Easing.OutCubic }
                        NumberAnimation { target: card; property: "rotation"; from: -12; to: 0; duration: 700; easing.type: Easing.OutBack }
                        SequentialAnimation {
                            PauseAnimation { duration: 380 }
                            NumberAnimation { target: sheen; property: "at"; from: -0.4; to: 1.3; duration: 650; easing.type: Easing.InOutQuad }
                        }
                        SequentialAnimation {
                            PauseAnimation { duration: 260 }
                            NumberAnimation { target: caption; property: "opacity"; from: 0; to: 1; duration: 260 }
                            ScriptAction { script: typeAnim.start() }
                        }
                    }
                }
                SequentialAnimation {
                    id: exitAnim
                    ParallelAnimation {
                        NumberAnimation { target: card; property: "scale"; to: 1.35; duration: 420; easing.type: Easing.InCubic }
                        NumberAnimation { target: card; property: "opacity"; to: 0; duration: 420; easing.type: Easing.InCubic }
                        NumberAnimation { target: caption; property: "opacity"; to: 0; duration: 260 }
                    }
                    ScriptAction { script: root.finish() }
                }
            }
        }
    }
}
