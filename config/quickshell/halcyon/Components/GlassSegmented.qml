import QtQuick
import qs.Config

/**
 * A segmented control.
 *
 * Preferred over a dropdown wherever the options fit: every choice is
 * visible, it is one click rather than two, and there is no popup to
 * position against the edge of a panel.
 */
Item {
    id: root

    /** ["a", "b"] or [{ value, title, glyph }] */
    property var options: []
    property string value: ""
    property bool enabled: true

    signal selected(string value)

    implicitHeight: 30
    implicitWidth: row.implicitWidth + 4
    opacity: root.enabled ? 1 : 0.4

    function optionValue(option: var): string {
        return (typeof option === "string") ? option : String(option.value ?? "");
    }

    function optionTitle(option: var): string {
        if (typeof option === "string")
            return option.charAt(0).toUpperCase() + option.slice(1).replace(/-/g, " ");
        return String(option.title ?? option.value ?? "");
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: Theme.surfaceSunken
        border.width: 1
        border.color: Theme.glassBorder
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 0

        Repeater {
            model: root.options

            Item {
                required property var modelData

                readonly property string thisValue: root.optionValue(modelData)
                readonly property bool active: root.value === thisValue

                width: Math.max(62, segmentLabel.implicitWidth + Theme.spacingLg)
                height: root.height - 4

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: Theme.radiusXs
                    color: parent.active ? Theme.accent : "transparent"

                    Behavior on color {
                        enabled: Theme.animationsEnabled
                        ColorAnimation {
                            duration: Theme.durInstant
                            easing.type: Easing.BezierSpline
                            easing.bezierCurve: Theme.easeStandard
                        }
                    }
                }

                Label {
                    id: segmentLabel
                    anchors.centerIn: parent
                    text: root.optionTitle(modelData)
                    variant: "footnote"
                    font.weight: parent.active ? Theme.weightMedium : Theme.weightRegular
                    color: parent.active ? Theme.onAccent : Theme.textSecondary
                }

                StateLayer {
                    anchors.fill: parent
                    radius: Theme.radiusXs
                    enabled: root.enabled
                    onClicked: {
                        root.value = parent.thisValue;
                        root.selected(parent.thisValue);
                    }
                }
            }
        }
    }

    Accessible.role: Accessible.ComboBox
    Accessible.name: root.value
}
