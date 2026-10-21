pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions

/**
 * One round gauge (0 to 1) with its number in the middle and a label under it, drawn the way the theme draws gauges
 * (ThemeLook.spec.gauge): a plain ring, a lit ring with its glow, a ring of facets, a gold rail with star ticks, or a
 * keycap that fills from the bottom.
 */
ColumnLayout {
    id: gauge

    required property string label
    required property real value
    required property color accent
    property ThemeLook look: ThemeLook {}
    property int size: 82

    readonly property real level: Math.max(0, Math.min(1, value))
    readonly property string kind: look.spec.gauge === "activity" ? "ring" : look.spec.gauge
    spacing: 4

    Item {
        id: face
        Layout.alignment: Qt.AlignHCenter
        implicitWidth: gauge.size
        implicitHeight: gauge.size

        // ring
        CircularProgress {
            anchors.fill: parent
            visible: gauge.kind === "ring"
            implicitSize: gauge.size
            lineWidth: 7
            gapAngle: 0
            value: gauge.level
            colPrimary: gauge.accent
            colSecondary: Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.16)
        }

        // glow: the light round a thin lit ring, in three passes
        Repeater {
            model: gauge.kind === "glow" ? [{ w: 13, a: 0.12 }, { w: 7, a: 0.3 }, { w: 3, a: 1 }] : []
            delegate: CircularProgress {
                required property var modelData
                anchors.fill: face
                implicitSize: gauge.size
                lineWidth: modelData.w
                gapAngle: 0
                value: gauge.level
                colPrimary: Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, modelData.a)
                colSecondary: modelData.a < 1 ? "transparent" : Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.14)
            }
        }

        // segments: facets round the ring, lit up to the value
        Repeater {
            model: gauge.kind === "segments" ? 20 : 0
            delegate: Item {
                id: facet
                required property int index
                x: face.width / 2
                y: face.height / 2
                rotation: index * 18
                Rectangle {
                    x: -4
                    y: -gauge.size / 2 + 2
                    width: 8
                    height: 11
                    color: facet.index < Math.round(gauge.level * 20) ? gauge.accent : Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.14)
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.35)
                }
            }
        }

        // rail: a fine gold ring, a finer track inside it, and four star ticks
        CircularProgress {
            anchors.fill: parent
            visible: gauge.kind === "rail"
            implicitSize: gauge.size
            lineWidth: 3
            gapAngle: 0
            value: gauge.level
            colPrimary: gauge.accent
            colSecondary: Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.22)
        }
        Rectangle {
            visible: gauge.kind === "rail"
            anchors.centerIn: parent
            width: gauge.size - 16
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.4)
        }
        Repeater {
            model: gauge.kind === "rail" ? 4 : 0
            delegate: StyledText {
                required property int index
                readonly property real angle: index * Math.PI / 2 - Math.PI / 2
                x: face.width / 2 + Math.cos(angle) * (gauge.size / 2 - 2) - width / 2
                y: face.height / 2 + Math.sin(angle) * (gauge.size / 2 - 2) - height / 2
                text: "✦"
                font.pixelSize: 11
                color: gauge.accent
            }
        }

        // key: a keycap whose fill rises with the value
        Item {
            anchors.fill: parent
            visible: gauge.kind === "key"
            Rectangle {
                x: 2
                y: 7
                width: parent.width - 4
                height: parent.height - 7
                radius: 14
                color: Qt.darker(Appearance.colors.colLayer1, 2.6)
            }
            Rectangle {
                id: cap
                x: 2
                y: 0
                width: parent.width - 4
                height: parent.height - 7
                radius: 14
                // the key's face, a shade lighter than the card so it stands off it
                color: ColorUtils.mix(gauge.look.text, Appearance.colors.colLayer1, 0.13)
                border.width: 2.5
                border.color: Qt.darker(Appearance.colors.colLayer1, 2.6)
                // the fill rises inside the cream ring, the ring drawn over its edge
                Item {
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: parent.height * gauge.level
                        radius: 9
                        color: Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.85)
                        Behavior on height {
                            animation: Appearance.animation.elementMove.numberAnimation.createObject(this)
                        }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 10
                    color: "transparent"
                    border.width: 1.5
                    border.color: Qt.rgba(gauge.look.text.r, gauge.look.text.g, gauge.look.text.b, 0.7)
                }
            }
        }

        StyledText {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: gauge.kind === "key" ? -3 : 0
            text: `${Math.round(gauge.level * 100)}`
            font.pixelSize: gauge.kind === "key" ? 26 : 24
            font.weight: gauge.kind === "key" ? Font.Black : Font.Medium
            color: gauge.look.text
            style: gauge.kind === "glow" ? Text.Raised : gauge.kind === "key" ? Text.Outline : Text.Normal
            styleColor: gauge.kind === "glow" ? gauge.look.glow : Qt.darker(Appearance.colors.colLayer1, 2.6)
        }
    }
    StyledText {
        Layout.alignment: Qt.AlignHCenter
        text: gauge.look.label(gauge.label)
        font.pixelSize: Appearance.font.pixelSize.smaller
        font.letterSpacing: gauge.look.spacing
        font.weight: gauge.look.spec.caps ? Font.DemiBold : Font.Normal
        color: gauge.look.subtext
    }
}
