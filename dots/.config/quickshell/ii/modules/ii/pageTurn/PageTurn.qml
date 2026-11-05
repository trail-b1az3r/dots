pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

/**
 * Manga Ink turns a page when you change workspace, as in an open book whose spine is the middle of the screen. Going
 * on (a higher workspace), the right half of the screen as it was lifts and turns over onto the left half, showing the
 * new workspace beneath it; its back is paper with the print showing through, mirrored. Once it lands, the rest of the
 * old screen fades to the new one. Going back, the left half turns over to the right. It has the manga book's weight
 * (MangaBook.qml): a flick lifts it, it slows as it stands up, falls over and lands with a small bounce; the light
 * falls across it as it turns, its edge is inked, and its shadow lies on the page below.
 *
 * Only on the monitor that changes workspace, and not when the workspace is already shown on another monitor (focus
 * just moves there). Halcyon's workspace keys (hyprland/lib/init.lua) hand the switch to the shell while
 * $XDG_RUNTIME_DIR/halcyon-page-turn holds its process id, writing the target to halcyon-page-turn-target and calling
 * quickshell:pageTurn; the bar's workspaces go through WorkspaceTurn. The screen is captured once per turn, right
 * before the switch, so nothing runs between turns. Manga Ink's own workspace animation is a short fade, hidden under
 * the page. Settings: halcyon.pageTurn.
 */
Scope {
    id: root

    readonly property bool enabled: ["manga-ink", "manga-ink-dark"].includes(Config.options.halcyon.theme)
        && (Config.options.halcyon.pageTurn ?? true)
    readonly property string runtimeDir: Quickshell.env("XDG_RUNTIME_DIR") || "/tmp"
    readonly property string flagPath: `${runtimeDir}/halcyon-page-turn`
    readonly property string targetPath: `${runtimeDir}/halcyon-page-turn-target`

    // The page's physics, as the manga book's (radians, seconds).
    readonly property real gravity: 42
    readonly property real airDrag: 1.6

    // Each monitor's page, by monitor name.
    property var pages: ({})

    Component.onCompleted: {
        WorkspaceTurn.turner = root;
        writeFlag();
    }
    Component.onDestruction: {
        if (WorkspaceTurn.turner === root)
            WorkspaceTurn.turner = null;
        Quickshell.execDetached(["rm", "-f", root.flagPath]);
    }
    onEnabledChanged: writeFlag()

    // The flag the workspace keys look for: this shell's process id while pages turn (the parent of the sh below).
    function writeFlag() {
        flag.command = enabled ? ["sh", "-c", 'echo "$PPID" > "$1"', "sh", flagPath] : ["rm", "-f", flagPath];
        flag.running = true;
    }
    Process {
        id: flag
    }

    // Read when the keys call (the file is only there once they have written to it).
    FileView {
        id: targetFile
        blockLoading: true
    }
    GlobalShortcut {
        name: "pageTurn"
        description: "Manga Ink: go to the workspace in $XDG_RUNTIME_DIR/halcyon-page-turn-target, turning a page"
        onPressed: {
            if (targetFile.path !== root.targetPath)
                targetFile.path = root.targetPath;
            else
                targetFile.reload();
            const target = parseInt(targetFile.text());
            if (target > 0)
                root.turnTo(target);
        }
    }

    function focus(target) {
        Hyprland.dispatch(`hl.dsp.focus({workspace = ${target}})`);
    }

    /** Go to workspace `target` on the focused monitor, turning its page. */
    function turnTo(target) {
        const monitor = HyprlandData.monitors.find(m => m.focused);
        const current = monitor?.activeWorkspace?.id ?? 0;
        if (!monitor || target === current)
            return;
        const page = pages[monitor.name];
        const shownElsewhere = HyprlandData.monitors.some(m => m.name !== monitor.name && m.activeWorkspace?.id === target);
        // Already on another monitor: focus moves there, nothing turns. A turn under way: just go.
        if (!enabled || shownElsewhere || !page || page.busy) {
            focus(target);
            return;
        }
        page.start(target, target > current ? 1 : -1);
    }

    // One half of the screen as it was: the whole screen captured, seen through a window onto the part from `from`.
    // Live only until its first frame (a one-off capture asked for before the recording is set up is refused), then
    // frozen.
    component Half: Item {
        id: half
        property real from: 0
        property var screen
        property bool capturing: false
        property real screenWidth: 0
        property real screenHeight: 0
        signal captured
        clip: true
        ScreencopyView {
            x: -half.from
            width: half.screenWidth
            height: half.screenHeight
            captureSource: half.screen
            live: half.capturing
            paintCursor: false
            onHasContentChanged: if (hasContent) half.captured()
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Scope {
            id: page
            required property var modelData

            property int target: 0
            property int direction: 1          // 1: on (the right half turns over to the left), -1: back
            property bool capturing: false
            property bool turning: false
            property bool landed: false        // on the other side; the rest of the old screen fades
            readonly property bool busy: capturing || turning
            property real angle: 0             // 0 to π
            property real omega: 0
            property real lastStep: 0
            property real fade: 1
            readonly property real lift: Math.sin(angle)
            // Both halves have their picture (each is its own capture, both taken before the switch).
            property int framesIn: 0
            onFramesInChanged: if (framesIn >= 2) captured()

            Component.onCompleted: {
                const pages = root.pages;
                pages[modelData.name] = page;
                root.pages = pages;
            }

            function start(workspace, dir) {
                target = workspace;
                direction = dir;
                angle = 0;
                omega = 0;
                fade = 1;
                landed = false;
                framesIn = 0;
                capturing = true;
                captureTimeout.restart();
            }
            // The screen as it was is on the overlay: go to the new workspace under it, and turn.
            function captured() {
                if (!capturing)
                    return;
                // Turning before no longer capturing, so the overlay (and this capture) is never let go in between.
                // Flicked from its corner: enough to lift it past upright against its weight; then it falls over.
                omega = Math.sqrt(2 * root.gravity) * 1.28 + root.airDrag * 0.5;
                lastStep = Date.now();
                turning = true;
                capturing = false;
                captureTimeout.stop();
                root.focus(target);
            }
            // No picture of the screen in time (a busy compositor): go without the page.
            Timer {
                id: captureTimeout
                interval: 300
                onTriggered: {
                    if (!page.capturing)
                        return;
                    page.capturing = false;
                    root.focus(page.target);
                }
            }
            // As the manga book's pages: its weight pulls it onto whichever side it is over, and it bounces as it
            // lands. Once it lies on the other side, the rest of the old screen fades to the new one.
            function step() {
                if (landed)
                    return;
                const now = Date.now();
                const dt = Math.min(0.033, Math.max(0.001, (now - lastStep) / 1000));
                lastStep = now;
                omega += (-root.gravity * Math.cos(angle) - root.airDrag * omega) * dt;
                angle += omega * dt;
                if (angle >= Math.PI) {
                    angle = Math.PI;
                    if (Math.abs(omega) < 1.2) {
                        landed = true;
                        fadeOut.restart();
                    } else {
                        omega = -Math.abs(omega) * 0.22;
                    }
                }
            }
            FrameAnimation {
                running: page.turning && !page.landed
                onTriggered: page.step()
            }
            SequentialAnimation {
                id: fadeOut
                NumberAnimation { target: page; property: "fade"; to: 0; duration: 200; easing.type: Easing.InQuad }
                ScriptAction { script: page.turning = false }
            }

            Loader {
                active: page.busy
                sourceComponent: PanelWindow {
                    id: window
                    screen: page.modelData
                    color: "transparent"
                    WlrLayershell.namespace: "quickshell:pageTurn"
                    WlrLayershell.layer: WlrLayer.Overlay
                    exclusionMode: ExclusionMode.Ignore
                    mask: Region {}
                    anchors {
                        top: true
                        bottom: true
                        left: true
                        right: true
                    }

                    readonly property real half: width / 2
                    readonly property bool dark: Config.options.halcyon.theme === "manga-ink-dark"
                    readonly property color paper: dark ? "#0d0d0e" : "#f7f3ea"
                    readonly property color ink: dark ? "#f1ece2" : "#141414"

                    // The screen as it was, captured once per half. Each capture is live only until its first frame
                    // (a one-off capture asked for before the recording is set up is refused), then frozen.

                    // The half that stays (the left one going on), until the page lands on it and it all fades.
                    Half {
                        id: stay
                        x: page.direction > 0 ? 0 : window.half
                        from: x
                        screen: page.modelData
                        capturing: page.capturing
                        screenWidth: window.width
                        screenHeight: window.height
                        onCaptured: page.framesIn += 1
                        width: window.half
                        height: window.height
                        opacity: page.fade
                        // Shaded as the page comes over it.
                        Rectangle {
                            anchors.fill: parent
                            color: "black"
                            opacity: page.angle > Math.PI / 2 ? 0.28 * Math.sin(page.angle) : 0
                        }
                    }

                    // The page's shadow on the new workspace, past its edge, deepest as it stands up.
                    Rectangle {
                        readonly property real edge: window.half + page.direction * window.half * Math.cos(page.angle)
                        visible: page.angle < Math.PI / 2
                        width: 110 * page.lift
                        height: window.height
                        x: page.direction > 0 ? edge : edge - width
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: page.direction > 0 ? 0 : 1; color: Qt.rgba(0, 0, 0, 0.4 * page.lift) }
                            GradientStop { position: page.direction > 0 ? 1 : 0; color: Qt.rgba(0, 0, 0, 0) }
                        }
                    }

                    // The page: the other half, hinged at the middle of the screen. Its front is the old screen; past
                    // upright you see its back, paper with the print showing through, mirrored, as manga paper does.
                    Item {
                        id: leaf
                        x: page.direction > 0 ? window.half : 0
                        width: window.half
                        height: window.height
                        opacity: page.fade
                        transform: Scale {
                            origin.x: page.direction > 0 ? 0 : leaf.width
                            origin.y: leaf.height / 2
                            xScale: Math.cos(page.angle)
                            yScale: 1 + 0.04 * page.lift
                        }
                        Rectangle {
                            anchors.fill: parent
                            color: window.paper
                            visible: page.angle >= Math.PI / 2
                        }
                        Half {
                            anchors.fill: parent
                            from: leaf.x
                            screen: page.modelData
                            capturing: page.capturing
                            screenWidth: window.width
                            screenHeight: window.height
                            onCaptured: page.framesIn += 1
                            opacity: page.angle < Math.PI / 2 ? 1 : 0.13
                        }
                        // The light across it as it rises: darker towards the spine.
                        Rectangle {
                            anchors.fill: parent
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: page.direction > 0 ? 0 : 1; color: Qt.rgba(0, 0, 0, 0.42 * page.lift) }
                                GradientStop { position: page.direction > 0 ? 0.55 : 0.45; color: Qt.rgba(0, 0, 0, 0) }
                            }
                        }
                        // Its edge, inked, about 3 px on screen however narrow it is.
                        Rectangle {
                            x: page.direction > 0 ? leaf.width - width : 0
                            width: 3 / Math.max(0.06, Math.abs(Math.cos(page.angle)))
                            height: leaf.height
                            color: window.ink
                        }
                    }
                    // The spine, a faint fold down the middle while the page turns.
                    Rectangle {
                        x: window.half - 1
                        width: 2
                        height: window.height
                        color: Qt.rgba(0, 0, 0, 0.3 * page.fade)
                        visible: page.turning
                    }
                }
            }
        }
    }
}
