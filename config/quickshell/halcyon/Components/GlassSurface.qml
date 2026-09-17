import QtQuick
import QtQuick.Effects
import qs.Config

/**
 * The single surface every panel in Halcyon is built from.
 *
 * The compositor does the blur — Hyprland has a layer rule for each of
 * the shell's namespaces, and it is far better at sampling what is
 * behind a surface than a client can be. What this component adds is
 * everything that turns a blurred rectangle into glass:
 *
 *   · a tint that leans toward the wallpaper's accent, so panels belong
 *     to the desktop instead of sitting on top of it;
 *   · a specular highlight along the top edge and a darker inner shadow
 *     along the bottom, which is what reads as "a pane with thickness"
 *     rather than "a translucent rectangle";
 *   · a border that is brighter where light would hit it and dimmer
 *     where it would not;
 *   · a shadow whose blur, offset and opacity move together with depth.
 *
 * Each decorative layer is skipped when Low Power Graphics or high
 * contrast is on, so the same component is also the cheap one.
 */
Item {
    id: root

    /** 0 flat, 1 raised, 2 floating, 3 overlay, 4 modal. */
    property int level: 2

    property int radius: Theme.radiusLg
    property color surfaceColor: Theme.surface
    property color tintColor: Theme.glassTint
    property color borderColor: Theme.glassBorder

    /** Extra tint on top of the theme's, for panels that need weight. */
    property real tintStrength: 1.0

    /** Clip content to the rounded shape. Off by default: clipping costs
     *  a render target, and most content stays inside anyway. */
    property bool clipContent: false

    /** Content is laid out inside this inset. */
    property int padding: Theme.panelPadding

    readonly property var shadowSpec: Theme.shadowFor(root.level)

    default property alias content: contentHolder.data

    // ── Background stack ───────────────────────────────────────────────
    //
    // Drawn into one layer so the shadow below can be produced from the
    // composed shape rather than from each piece separately.

    Item {
        id: glass
        anchors.fill: parent
        visible: false
        layer.enabled: true

        Rectangle {
            anchors.fill: parent
            radius: root.radius
            color: root.surfaceColor

            // The tint. A vertical gradient rather than a flat wash: real
            // glass picks up more colour where it is thicker.
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                visible: Theme.decorativeEffects && root.tintStrength > 0
                opacity: root.tintStrength
                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: Qt.rgba(
                            root.tintColor.r, root.tintColor.g, root.tintColor.b,
                            root.tintColor.a * 0.9
                        )
                    }
                    GradientStop {
                        position: 1.0
                        color: Qt.rgba(
                            root.tintColor.r, root.tintColor.g, root.tintColor.b,
                            root.tintColor.a * 0.35
                        )
                    }
                }
            }

            // Specular sheen along the top. Kept to the upper third so it
            // reads as a highlight, not as a lighter panel.
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.min(parent.height * 0.42, 96)
                radius: parent.radius
                visible: Theme.decorativeEffects && Theme.specular > 0
                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: Qt.rgba(1, 1, 1, 0.10 * Theme.specular)
                    }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            // The inner shadow at the bottom edge, which gives the pane a
            // back face for light to fall away from.
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: Math.min(parent.height * 0.3, 64)
                radius: parent.radius
                visible: Theme.decorativeEffects
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop {
                        position: 1.0
                        color: Qt.rgba(0, 0, 0, Theme.isDark ? 0.14 : 0.05)
                    }
                }
            }

            // Hairline border. Two rectangles rather than one stroke: the
            // top edge catches light and the rest does not, and a single
            // uniform border makes the whole thing look printed on.
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: "transparent"
                border.width: 1
                border.color: root.borderColor
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: root.radius * 0.5
                anchors.rightMargin: root.radius * 0.5
                anchors.topMargin: 1
                height: 1
                visible: Theme.decorativeEffects && Theme.specular > 0
                color: Qt.rgba(1, 1, 1, 0.22 * Theme.specular)
            }
        }
    }

    // ── Shadow ─────────────────────────────────────────────────────────

    MultiEffect {
        anchors.fill: parent
        source: glass
        // A shadow has to draw outside the item's own bounds, which is
        // exactly what automatic padding is for.
        autoPaddingEnabled: true
        shadowEnabled: root.level > 0 && root.shadowSpec.opacity > 0
        shadowColor: Theme.shadow
        shadowBlur: Math.min(1.0, root.shadowSpec.blur / 64)
        shadowOpacity: root.shadowSpec.opacity
        shadowVerticalOffset: root.shadowSpec.y
        shadowHorizontalOffset: 0
        // Lifting the saturation of what shows through is the cheapest
        // part of the "liquid" look and the one people notice.
        saturation: Theme.decorativeEffects ? (Theme.saturation - 1.0) * 0.5 : 0.0

        Behavior on shadowBlur {
            enabled: Theme.animationsEnabled
            NumberAnimation {
                duration: Theme.durStandard
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.easeStandard
            }
        }
    }

    // ── Content ────────────────────────────────────────────────────────

    Item {
        id: contentHolder
        anchors.fill: parent
        anchors.margins: root.padding
        clip: root.clipContent
    }
}
