import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/**
 * The power menu.
 *
 * Lock is first and focused, because it is the one people mean nine
 * times out of ten. Anything that ends a session asks once, in place,
 * before it happens — there is no undo for "log out" with unsaved work.
 */
OverlayWindow {
    id: root

    name: "power"
    namespaceName: "halcyon-overlay"
    origin: "center"
    grabKeyboard: true

    property string confirming: ""

    onOpened: root.confirming = ""

    readonly property var choices: [
        { id: "lock", title: "Lock", glyph: "󰌾", confirm: false, action: "session.lock" },
        { id: "suspend", title: "Sleep", glyph: "󰒲", confirm: true, action: "session.suspend" },
        { id: "logout", title: "Log Out", glyph: "󰍃", confirm: true, action: "session.logout" },
        { id: "reboot", title: "Restart", glyph: "󰜉", confirm: true, action: "session.reboot" },
        { id: "shutdown", title: "Shut Down", glyph: "󰐥", confirm: true, action: "session.shutdown" }
    ]

    function choose(choice: var): void {
        if (choice.confirm && root.confirming !== choice.id) {
            root.confirming = choice.id;
            return;
        }
        Overlays.close(root.name);
        Actions.run(["action", choice.action, "--confirm"]);
    }

    Keys.onEscapePressed: {
        if (root.confirming.length > 0)
            root.confirming = "";
        else
            Overlays.close(root.name);
    }

    GlassSurface {
        anchors.centerIn: parent
        width: column.implicitWidth + padding * 2
        height: column.implicitHeight + padding * 2
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPaddingLoose

        ColumnLayout {
            id: column
            anchors.centerIn: parent
            spacing: Theme.spacingMd

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: root.confirming.length > 0
                    ? root.confirmTitle(root.confirming) + "?"
                    : "Power"
                variant: "title"
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                visible: root.confirming.length > 0
                text: "Anything unsaved will be lost."
                variant: "footnote"
                tone: "secondary"
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.spacingMd
                visible: root.confirming.length === 0

                Repeater {
                    model: root.choices

                    Item {
                        required property int index
                        required property var modelData

                        width: 96
                        height: 96

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.radiusLg
                            color: Theme.surfaceRaised
                            border.width: 1
                            border.color: state.hovered ? Theme.accent : Theme.glassBorder

                            Behavior on border.color {
                                enabled: Theme.animationsEnabled
                                ColorAnimation { duration: Theme.durInstant }
                            }
                        }

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spacingXs

                            Icon {
                                Layout.alignment: Qt.AlignHCenter
                                glyph: modelData.glyph
                                size: 28
                                color: modelData.id === "shutdown" && state.hovered
                                    ? Theme.danger
                                    : Theme.text
                            }

                            Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: modelData.title
                                variant: "footnote"
                            }
                        }

                        StateLayer {
                            id: state
                            anchors.fill: parent
                            radius: Theme.radiusLg
                            onClicked: root.choose(modelData)
                        }
                    }
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.spacingMd
                visible: root.confirming.length > 0

                GlassButton {
                    text: "Cancel"
                    onClicked: root.confirming = ""
                }

                GlassButton {
                    text: root.confirmTitle(root.confirming)
                    variant: "filled"
                    destructive: root.confirming === "shutdown" || root.confirming === "reboot"
                    onClicked: {
                        const choice = root.choices.find(item => item.id === root.confirming);
                        if (choice)
                            root.choose(choice);
                    }
                }
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                visible: root.confirming.length === 0 && Power.hasBattery
                text: Power.percent + "%  ·  " + Power.remaining
                variant: "caption"
                tone: "tertiary"
            }
        }
    }

    function confirmTitle(id: string): string {
        const choice = root.choices.find(item => item.id === id);
        return choice ? choice.title : "";
    }
}
