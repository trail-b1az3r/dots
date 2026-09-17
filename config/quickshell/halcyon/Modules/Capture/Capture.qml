import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/**
 * The screenshot and recording panel.
 *
 * What Super+Shift+5 opens: the same choices the individual shortcuts
 * make, in one place, for when you cannot remember which is which.
 */
OverlayWindow {
    id: root

    name: "capture"
    namespaceName: "halcyon-overlay"
    origin: "bottom"
    scrim: false
    grabKeyboard: true

    readonly property var choices: [
        { title: "Region", glyph: "󰩭", mode: "region", kind: "shot" },
        { title: "Screen", glyph: "󰍹", mode: "screen", kind: "shot" },
        { title: "Window", glyph: "󰖯", mode: "window", kind: "shot" },
        { title: "Record", glyph: "󰑊", mode: "toggle", kind: "record" }
    ]

    function run(choice: var): void {
        Overlays.close(root.name);
        if (choice.kind === "record")
            Actions.record(choice.mode);
        else
            Actions.screenshot(choice.mode);
    }

    GlassSurface {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.spacingXl * 2

        width: row.implicitWidth + padding * 2
        height: row.implicitHeight + padding * 2
        level: 4
        radius: Theme.radiusXxl
        padding: Theme.panelPaddingTight

        RowLayout {
            id: row
            anchors.centerIn: parent
            spacing: Theme.spacingXs

            Repeater {
                model: root.choices

                Item {
                    required property var modelData

                    width: 76
                    height: 68

                    Rectangle {
                        anchors.fill: parent
                        radius: Theme.radiusLg
                        color: tile.hovered ? Theme.surfaceHover : "transparent"

                        Behavior on color {
                            enabled: Theme.animationsEnabled
                            ColorAnimation { duration: Theme.durInstant }
                        }
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Icon {
                            Layout.alignment: Qt.AlignHCenter
                            glyph: modelData.glyph
                            size: 24
                            color: modelData.kind === "record" && Theme.decorativeEffects
                                ? Theme.danger
                                : Theme.text
                        }

                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: modelData.title
                            variant: "caption"
                        }
                    }

                    StateLayer {
                        id: tile
                        anchors.fill: parent
                        radius: Theme.radiusLg
                        onClicked: root.run(modelData)
                    }
                }
            }
        }
    }
}
