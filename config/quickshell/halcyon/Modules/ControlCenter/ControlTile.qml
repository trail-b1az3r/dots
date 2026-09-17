import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components

/**
 * One tile in Control Center.
 *
 * Two hit targets in one shape: pressing the body toggles the thing,
 * pressing the chevron expands it. That split is what lets Wi-Fi be both
 * a switch and a network list without a second panel.
 */
GlassSurface {
    id: root

    property string title: ""
    property string subtitle: ""
    property string glyph: ""
    property bool active: false
    property bool expandable: false
    property bool expanded: false
    property bool enabled: true

    signal toggled
    signal expandRequested

    level: 1
    radius: Theme.radiusLg
    padding: 0
    surfaceColor: root.active ? Theme.accent : Theme.surfaceRaised
    tintStrength: root.active ? 0 : 1
    implicitHeight: 62

    Behavior on surfaceColor {
        enabled: Theme.animationsEnabled
        ColorAnimation {
            duration: Theme.durQuick
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Theme.easeStandard
        }
    }

    readonly property color foreground: root.active ? Theme.onAccent : Theme.text
    readonly property color subForeground: root.active
        ? Qt.rgba(Theme.onAccent.r, Theme.onAccent.g, Theme.onAccent.b, 0.75)
        : Theme.textTertiary

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingMd
        anchors.rightMargin: Theme.spacingXs
        spacing: Theme.spacingMd

        Rectangle {
            Layout.preferredWidth: 34
            Layout.preferredHeight: 34
            radius: width / 2
            color: root.active
                ? Qt.rgba(Theme.onAccent.r, Theme.onAccent.g, Theme.onAccent.b, 0.18)
                : Theme.surfaceSunken

            Icon {
                anchors.centerIn: parent
                glyph: root.glyph
                size: 17
                color: root.foreground
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            Label {
                Layout.fillWidth: true
                text: root.title
                variant: "body"
                font.weight: Theme.weightMedium
                color: root.foreground
            }

            Label {
                Layout.fillWidth: true
                visible: root.subtitle.length > 0
                text: root.subtitle
                variant: "caption"
                color: root.subForeground
            }
        }

        Item {
            Layout.preferredWidth: root.expandable ? 30 : 0
            Layout.fillHeight: true
            visible: root.expandable

            Icon {
                anchors.centerIn: parent
                glyph: "󰅂"
                size: 14
                color: root.subForeground
                rotation: root.expanded ? 90 : 0

                Behavior on rotation {
                    enabled: Theme.animationsEnabled
                    NumberAnimation {
                        duration: Theme.durQuick
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: Theme.easeStandard
                    }
                }
            }

            StateLayer {
                anchors.fill: parent
                radius: Theme.radiusSm
                enabled: root.enabled
                onClicked: root.expandRequested()
            }
        }
    }

    StateLayer {
        anchors.fill: parent
        anchors.rightMargin: root.expandable ? 34 : 0
        radius: root.radius
        enabled: root.enabled
        z: -1
        onClicked: root.toggled()
    }

    Accessible.role: Accessible.Button
    Accessible.name: root.title
    Accessible.description: root.subtitle
}
