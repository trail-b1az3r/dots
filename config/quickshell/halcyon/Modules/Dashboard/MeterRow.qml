import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components

/** One labelled bar in the system widget. */
ColumnLayout {
    id: root

    property string glyph: ""
    property string label: ""
    property string detail: ""
    property real value: 0
    property color fill: Theme.accent

    spacing: 2

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spacingSm

        Icon {
            glyph: root.glyph
            size: 13
            color: Theme.textTertiary
        }

        Label {
            Layout.fillWidth: true
            text: root.label
            variant: "caption"
            tone: "secondary"
        }

        Label {
            text: root.detail
            variant: "caption"
            tone: "tertiary"
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 4
        radius: 2
        color: Theme.surfaceSunken

        Rectangle {
            width: Math.max(4, parent.width * Math.max(0, Math.min(1, root.value / 100)))
            height: parent.height
            radius: parent.radius
            color: root.fill

            Behavior on width {
                enabled: Theme.animationsEnabled
                NumberAnimation {
                    duration: Theme.durStandard
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: Theme.easeStandard
                }
            }
        }
    }
}
