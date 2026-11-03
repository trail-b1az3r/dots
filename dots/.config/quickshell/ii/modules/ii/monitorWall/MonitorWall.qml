import qs.modules.common
import qs.services
import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

/**
 * The wall between monitors, seen from the other side (hyprland-plus's plus:monitor_wall): while a dragged window is
 * held against an edge another monitor shares, that monitor's edge bulges in where the window would come through,
 * deeper the harder it is pushed. Let go and it springs back with a wobble; when it gives, it snaps and ripples.
 *
 * Driven by hyprland-plus's monitorwall event: MONITOR,EDGE,START,LENGTH,STRENGTH (EDGE none when the push ends),
 * and monitorwallbreak. Clicks go straight through.
 *
 * Without hyprland-plus there is no wall, but a window that crosses onto another monitor (dragged, or sent there by a
 * key) still gives that monitor's edge a little bulge where it came in, which springs back with a wobble.
 */
Scope {
    id: root

    readonly property real maxDepth: 64
    // How deep the little bulge is when a window arrives on another monitor, as a share of maxDepth.
    readonly property real arrivalDepth: 0.35

    // Which monitor each window was on, to see when one changes monitor (HyprlandData's windows: hyprctl clients).
    property var monitorOf: ({})

    /** The edge of monitor `to` that touches monitor `from` (both hyprctl monitors entries), or "". */
    function sharedEdge(from, to) {
        const box = m => ({ x: m.x, y: m.y, w: m.width / (m.scale || 1), h: m.height / (m.scale || 1) });
        const a = box(from), b = box(to);
        const near = (p, q) => Math.abs(p - q) < 2;
        const overlapY = a.y < b.y + b.h && a.y + a.h > b.y, overlapX = a.x < b.x + b.w && a.x + a.w > b.x;
        if (overlapY && near(a.x + a.w, b.x)) return "left";
        if (overlapY && near(b.x + b.w, a.x)) return "right";
        if (overlapX && near(a.y + a.h, b.y)) return "top";
        if (overlapX && near(b.y + b.h, a.y)) return "bottom";
        return "";
    }

    signal arrived(string monitorName, string edge, real start, real length)

    Connections {
        target: HyprlandData
        function onWindowListChanged() {
            const seen = {};
            for (const w of HyprlandData.windowList) {
                seen[w.address] = w.monitor;
                const before = root.monitorOf[w.address];
                if (before === undefined || before === w.monitor || w.monitor < 0 || before < 0 || (w.workspace?.id ?? 0) < 0)
                    continue;
                const from = HyprlandData.monitors.find(m => m.id === before);
                const to = HyprlandData.monitors.find(m => m.id === w.monitor);
                if (!from || !to)
                    continue;
                const edge = root.sharedEdge(from, to);
                if (edge === "")
                    continue;
                // Where along that edge the window is, in the new monitor's own coordinates.
                const along = edge === "left" || edge === "right";
                const start = along ? w.at[1] - to.y : w.at[0] - to.x;
                root.arrived(to.name, edge, Math.max(0, start), along ? w.size[1] : w.size[0]);
            }
            root.monitorOf = seen;
        }
    }

    /** The bulge, as an SVG path, on a monitor `w` x `h`: along `edge`, from `start` for `length`, `depth` deep. */
    function bulgePath(edge, start, length, depth, w, h) {
        // Work along the edge (u) and into the monitor (v), then map onto the screen.
        const map = (u, v) => {
            switch (edge) {
            case "left": return [v, u];
            case "right": return [w - v, u];
            case "top": return [u, v];
            default: return [u, h - v];
            }
        };
        const pt = (u, v) => map(u, v).map(n => Math.round(n * 10) / 10).join(" ");
        // A soft hump: flat where it meets the edge, round at the top, and a little wider than the window.
        const s = start - length * 0.12, e = start + length * 1.12, l = e - s;
        return `M ${pt(s, 0)} C ${pt(s + l * 0.18, 0)} ${pt(s + l * 0.2, depth)} ${pt(s + l * 0.5, depth)} `
             + `C ${pt(s + l * 0.8, depth)} ${pt(s + l * 0.82, 0)} ${pt(e, 0)} Z`;
    }

    Variants {
        model: Quickshell.screens

        delegate: Scope {
            id: perScreen
            required property var modelData
            property string edge: "left"
            property real start: 0
            property real length: 0
            property real target: 0
            // Springs after the target, so a release wobbles back instead of vanishing.
            property real depth: 0
            Behavior on depth {
                SpringAnimation { spring: 4; damping: 0.18; epsilon: 0.2 }
            }
            property real ripple: 0
            readonly property bool shown: depth > 0.5 || target > 0 || ripple > 0

            Connections {
                target: Hyprland
                function onRawEvent(event) {
                    if (!Config.options.halcyon.plus.monitorWallBulge)
                        return;
                    if (event.name === "monitorwall") {
                        const f = event.data.split(",");
                        if (f[0] !== perScreen.modelData.name)
                            return;
                        if (f[1] === "none") {
                            perScreen.target = 0;
                            perScreen.depth = 0;
                            return;
                        }
                        perScreen.edge = f[1];
                        perScreen.start = Number(f[2]);
                        perScreen.length = Number(f[3]);
                        perScreen.target = Number(f[4]);
                        perScreen.depth = perScreen.target * root.maxDepth;
                    } else if (event.name === "monitorwallbreak" && event.data === perScreen.modelData.name) {
                        perScreen.target = 0;
                        perScreen.depth = 0;
                        rippleAnim.restart();
                    }
                }
            }

            // A window came in through this monitor's edge: a little bulge that springs back (stock Hyprland too).
            Connections {
                target: root
                function onArrived(monitorName, edge, start, length) {
                    if (!Config.options.halcyon.plus.monitorWallBulge || monitorName !== perScreen.modelData.name || perScreen.target > 0)
                        return;
                    perScreen.edge = edge;
                    perScreen.start = start;
                    perScreen.length = length;
                    perScreen.depth = root.arrivalDepth * root.maxDepth;
                    settle.restart();
                }
            }
            Timer {
                id: settle
                interval: 160
                onTriggered: perScreen.depth = 0
            }

            NumberAnimation {
                id: rippleAnim
                target: perScreen
                property: "ripple"
                from: 1
                to: 0
                duration: 520
                easing.type: Easing.OutCubic
            }

            Loader {
                active: perScreen.shown
                sourceComponent: PanelWindow {
                    screen: perScreen.modelData
                    color: "transparent"
                    WlrLayershell.namespace: "quickshell:monitorWall"
                    WlrLayershell.layer: WlrLayer.Overlay
                    exclusionMode: ExclusionMode.Ignore
                    mask: Region {}
                    anchors {
                        top: true
                        bottom: true
                        left: true
                        right: true
                    }

                    Shape {
                        anchors.fill: parent
                        preferredRendererType: Shape.CurveRenderer
                        // The glow round it.
                        ShapePath {
                            strokeWidth: 10
                            strokeColor: Qt.rgba(Appearance.colors.colPrimary.r, Appearance.colors.colPrimary.g, Appearance.colors.colPrimary.b, 0.18)
                            fillColor: "transparent"
                            joinStyle: ShapePath.RoundJoin
                            PathSvg { path: root.bulgePath(perScreen.edge, perScreen.start, perScreen.length, Math.max(0, perScreen.depth), parent.width, parent.height) }
                        }
                        // The membrane: the theme's colour, brighter at its crown.
                        ShapePath {
                            strokeWidth: 2
                            strokeColor: Appearance.colors.colPrimary
                            fillColor: Qt.rgba(Appearance.colors.colPrimary.r, Appearance.colors.colPrimary.g, Appearance.colors.colPrimary.b, 0.16 + 0.22 * perScreen.target)
                            joinStyle: ShapePath.RoundJoin
                            PathSvg { path: root.bulgePath(perScreen.edge, perScreen.start, perScreen.length, Math.max(0, perScreen.depth), parent.width, parent.height) }
                        }
                        // When it gives: a ring of light spreading out from where it broke.
                        ShapePath {
                            strokeWidth: 3 * perScreen.ripple
                            strokeColor: Qt.rgba(Appearance.colors.colPrimary.r, Appearance.colors.colPrimary.g, Appearance.colors.colPrimary.b, perScreen.ripple)
                            fillColor: "transparent"
                            PathSvg { path: perScreen.ripple > 0 ? root.bulgePath(perScreen.edge, perScreen.start - 80 * (1 - perScreen.ripple), perScreen.length + 160 * (1 - perScreen.ripple), root.maxDepth * 1.6 * (1 - perScreen.ripple) + 6, parent.width, parent.height) : "" }
                        }
                    }
                }
            }
        }
    }
}
