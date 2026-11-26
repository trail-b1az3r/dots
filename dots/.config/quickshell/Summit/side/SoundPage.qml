pragma ComponentBehavior: Bound

import QtQuick
import Quickshell.Services.Pipewire
import qs.common
import qs.services

// Sound, as the Halcyon shell's volume mixer: where sound goes (pick the output), each app's own volume, and where
// it comes from (pick the input).
Item {
    id: root
    signal back

    readonly property var nodes: Pipewire.nodes.values
    readonly property var outputs: nodes.filter(n => n.audio && n.isSink && !n.isStream)
    readonly property var inputs: nodes.filter(n => n.audio && !n.isSink && !n.isStream)
    readonly property var apps: nodes.filter(n => n.audio && n.isSink && n.isStream)
    PwObjectTracker { objects: root.apps.concat(root.outputs, root.inputs) }

    function nameOf(node) {
        return node?.properties?.["application.name"] || node?.nickname || node?.description || node?.name || "";
    }

    PageHeader {
        id: head
        width: parent.width
        title: "Sound"
        onBack: root.back()
        BarButton {
            icon: "tune"
            onClicked: Actions.run("pavucontrol-qt || pavucontrol")
        }
    }

    Flickable {
        anchors.top: head.bottom
        anchors.topMargin: 10
        anchors.bottom: parent.bottom
        width: parent.width
        contentHeight: col.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            width: parent.width
            spacing: 6

            Section { text: "Output" }
            Repeater {
                model: root.outputs
                delegate: Choice {
                    required property var modelData
                    icon: "speaker"
                    text: root.nameOf(modelData)
                    chosen: Pipewire.defaultAudioSink === modelData
                    onPicked: Pipewire.preferredDefaultAudioSink = modelData
                }
            }

            Section { text: "Apps"; visible: root.apps.length > 0 }
            Repeater {
                model: root.apps
                delegate: Column {
                    id: app
                    required property var modelData
                    width: col.width
                    spacing: 4
                    Text {
                        text: root.nameOf(app.modelData)
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 12
                        font.weight: Font.Medium
                        leftPadding: 4
                    }
                    Slider {
                        width: parent.width
                        implicitHeight: 32
                        icon: (app.modelData.audio?.muted ?? false) ? "volume_off" : "volume_up"
                        value: Math.min(1, app.modelData.audio?.volume ?? 0)
                        onMoved: v => { if (app.modelData.audio) app.modelData.audio.volume = v; }
                    }
                }
            }

            Section { text: "Input" }
            Repeater {
                model: root.inputs
                delegate: Choice {
                    required property var modelData
                    icon: "mic"
                    text: root.nameOf(modelData)
                    chosen: Pipewire.defaultAudioSource === modelData
                    onPicked: Pipewire.preferredDefaultAudioSource = modelData
                }
            }
        }
    }

    component Section: Text {
        color: Theme.muted
        font.family: Theme.font
        font.pixelSize: 11
        font.weight: Font.DemiBold
        font.capitalization: Font.AllUppercase
        font.letterSpacing: 0.6
        topPadding: 8
        leftPadding: 4
    }
    component Choice: Rectangle {
        id: choice
        property string icon
        property string text
        property bool chosen
        signal picked
        width: col.width
        height: 44
        radius: 14
        color: chosen ? Theme.alpha(Theme.accent, 0.2) : choiceArea.containsMouse ? Theme.alpha(Theme.text, 0.08) : Theme.alpha(Theme.text, 0.04)
        Row {
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10
            Symbol {
                name: choice.chosen ? "radio_button_checked" : "radio_button_unchecked"
                color: choice.chosen ? Theme.accent : Theme.muted
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: choice.text
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 13
                elide: Text.ElideRight
                width: col.width - 60
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        MouseArea {
            id: choiceArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: choice.picked()
        }
    }
}
