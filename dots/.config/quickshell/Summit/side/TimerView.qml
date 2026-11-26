pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.common
import qs.services

// A focus timer, like the Halcyon shell's pomodoro: pick a length, start, pause, reset; a notification when it ends.
// It keeps running while the side menu is closed (its state is in services/SummitState.qml).
Item {
    id: root
    Column {
        anchors.centerIn: parent
        spacing: 14

        // The time left, round a ring that empties.
        Item {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 150
            height: 150
            Canvas {
                id: ring
                anchors.fill: parent
                readonly property real part: SummitState.timerLength > 0 ? SummitState.timerLeft / SummitState.timerLength : 0
                onPartChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();
                    ctx.lineWidth = 8;
                    ctx.lineCap = "round";
                    ctx.strokeStyle = Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.1);
                    ctx.beginPath();
                    ctx.arc(width / 2, height / 2, width / 2 - 6, 0, Math.PI * 2);
                    ctx.stroke();
                    ctx.strokeStyle = Theme.accent;
                    ctx.beginPath();
                    ctx.arc(width / 2, height / 2, width / 2 - 6, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * part);
                    ctx.stroke();
                }
            }
            Text {
                anchors.centerIn: parent
                text: SummitState.formatTime(SummitState.timerLeft)
                color: Theme.text
                font.family: Theme.mono
                font.pixelSize: 30
                font.weight: Font.DemiBold
            }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 6
            Repeater {
                model: [5, 15, 25, 50]
                delegate: BarButton {
                    required property int modelData
                    label: modelData + " min"
                    active: SummitState.timerLength === modelData * 60
                    onClicked: {
                        SummitState.timerRunning = false;
                        SummitState.timerLength = modelData * 60;
                        SummitState.timerLeft = SummitState.timerLength;
                    }
                }
            }
        }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            BarButton {
                icon: SummitState.timerRunning ? "pause" : "play_arrow"
                label: SummitState.timerRunning ? "Pause" : (SummitState.timerLeft < SummitState.timerLength ? "Resume" : "Start")
                active: true
                onClicked: {
                    if (SummitState.timerLeft === 0)
                        SummitState.timerLeft = SummitState.timerLength;
                    SummitState.timerRunning = !SummitState.timerRunning;
                }
            }
            BarButton {
                icon: "replay"
                label: "Reset"
                onClicked: {
                    SummitState.timerRunning = false;
                    SummitState.timerLeft = SummitState.timerLength;
                }
            }
        }
    }
}
