pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland

/**
 * What a ringing alarm looks like: a card on every screen with the event, the sound playing, and Stop and Snooze.
 * Enter or Escape stops it, S snoozes it. It sits above everything, fullscreen games included, and only takes the
 * keyboard while it is up.
 */
Scope {
    id: root

    LazyLoader {
        active: Alarm.ringing

        Variants {
            model: Quickshell.screens

            delegate: PanelWindow {
                id: win
                required property var modelData
                screen: modelData
                anchors {
                    top: true
                    left: true
                    right: true
                    bottom: true
                }
                color: "transparent"
                exclusionMode: ExclusionMode.Ignore
                WlrLayershell.namespace: "quickshell:alarm"
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

                // A dim, pulsing wash, red once the siren starts.
                Rectangle {
                    anchors.fill: parent
                    color: Alarm.stage === 2 ? "#5a0000" : "#000000"
                    opacity: 0.35 + 0.15 * pulse.value
                }
                QtObject {
                    id: pulse
                    property real value: 0
                    SequentialAnimation on value {
                        loops: Animation.Infinite
                        running: Alarm.ringing
                        NumberAnimation { to: 1; duration: Alarm.stage === 2 ? 450 : 700; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 0; duration: Alarm.stage === 2 ? 450 : 700; easing.type: Easing.InOutSine }
                    }
                }

                Item {
                    anchors.fill: parent
                    focus: true
                    Keys.onPressed: event => {
                        if (event.key === Qt.Key_S) {
                            Alarm.snooze();
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Escape || event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                            Alarm.stop();
                            event.accepted = true;
                        }
                    }
                }

                Rectangle {
                    id: card
                    anchors.centerIn: parent
                    width: 440
                    height: column.implicitHeight + 56
                    radius: Appearance.rounding.large
                    color: Appearance.colors.colLayer1
                    border.width: 3
                    border.color: Alarm.stage === 2 ? Qt.rgba(1, 0.25, 0.2, 0.5 + 0.5 * pulse.value) : Qt.rgba(Appearance.colors.colPrimary.r, Appearance.colors.colPrimary.g, Appearance.colors.colPrimary.b, 0.4 + 0.6 * pulse.value)
                    scale: 1 + 0.015 * pulse.value

                    ColumnLayout {
                        id: column
                        anchors.centerIn: parent
                        width: parent.width - 56
                        spacing: 10

                        MaterialSymbol {
                            Layout.alignment: Qt.AlignHCenter
                            text: Alarm.stage === 2 ? "crisis_alert" : "alarm"
                            iconSize: 64
                            fill: 1
                            color: Alarm.stage === 2 ? "#ff5544" : Appearance.colors.colPrimary
                            rotation: 8 * Math.sin(pulse.value * Math.PI * 2)
                        }
                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            text: Alarm.event?.time ?? ""
                            font.pixelSize: 54
                            font.weight: Font.DemiBold
                            color: Appearance.colors.colOnLayer1
                        }
                        StyledText {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            text: Alarm.event?.title ?? ""
                            font.pixelSize: Appearance.font.pixelSize.huge
                            color: Appearance.colors.colOnLayer1
                        }
                        StyledText {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            color: Appearance.colors.colSubtext
                            text: {
                                const s = Config.options.calendar.alarm;
                                const now = Alarm.describe(Alarm.stage === 2 ? s.secondSound : s.firstSound);
                                if (Alarm.stage === 1 && s.secondSound && s.secondSound !== "none" && s.secondSound !== s.firstSound)
                                    return Translation.tr("%1, then %2 after %3 s").arg(now).arg(Alarm.describe(s.secondSound)).arg(s.escalateAfter);
                                return now;
                            }
                        }
                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.topMargin: 8
                            spacing: 10
                            DialogButton {
                                visible: (Alarm.event?.id ?? "") !== ""
                                buttonText: Translation.tr("Snooze %1 min (S)").arg(Config.options.calendar.alarm.snoozeMinutes)
                                onClicked: Alarm.snooze()
                            }
                            RippleButton {
                                implicitWidth: 140
                                implicitHeight: 44
                                buttonRadius: Appearance.rounding.full
                                colBackground: Appearance.colors.colPrimary
                                colBackgroundHover: Appearance.colors.colPrimaryHover
                                onClicked: Alarm.stop()
                                contentItem: StyledText {
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    text: Translation.tr("Stop")
                                    font.pixelSize: Appearance.font.pixelSize.large
                                    font.weight: Font.DemiBold
                                    color: Appearance.colors.colOnPrimary
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
