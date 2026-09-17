import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Config
import qs.Components
import qs.Services

/**
 * Notification popups.
 *
 * A stack in the corner the user chose, newest nearest the edge, each on
 * its own timer. The layer surface only exists while something is in the
 * stack; an empty notification area should not cost a buffer.
 */
Scope {
    id: root

    readonly property string position: Config.get("notifications.position", "top-right")
    readonly property bool onTop: root.position.indexOf("top") === 0
    readonly property bool onRight: root.position.indexOf("right") > 0

    LazyLoader {
        active: Notifications.popups.length > 0

        PanelWindow {
            anchors {
                top: root.onTop
                bottom: !root.onTop
                right: root.onRight
                left: !root.onRight
            }
            margins {
                top: Config.get("bar.height", 34) + Theme.spacingLg
                bottom: Theme.spacingLg
                left: Theme.spacingLg
                right: Theme.spacingLg
            }

            exclusionMode: ExclusionMode.Ignore
            color: "transparent"
            // Popups accept clicks but must not take the keyboard.
            WlrLayershell.namespace: "halcyon-notifications"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            implicitWidth: 400
            implicitHeight: Math.max(1, stack.implicitHeight)

            Column {
                id: stack
                anchors.fill: parent
                spacing: Theme.spacingSm

                Repeater {
                    model: root.onTop
                        ? Notifications.popups.slice().reverse()
                        : Notifications.popups

                    NotificationCard {
                        required property var modelData

                        width: parent.width
                        entry: modelData
                        compact: true

                        onDismissed: Notifications.dismissPopup(modelData.id)
                        onActivated: Notifications.dismissPopup(modelData.id)

                        // Slide in from the edge it is anchored to.
                        opacity: 0
                        x: root.onRight ? 24 : -24

                        Component.onCompleted: {
                            opacity = 1;
                            x = 0;
                        }

                        Behavior on opacity {
                            enabled: Theme.animationsEnabled
                            NumberAnimation {
                                duration: Theme.durOverlay
                                easing.type: Easing.BezierSpline
                                easing.bezierCurve: Theme.easeDecel
                            }
                        }
                        Behavior on x {
                            enabled: Theme.animationsEnabled && !Theme.reducedMotion
                            NumberAnimation {
                                duration: Theme.durOverlay
                                easing.type: Easing.BezierSpline
                                easing.bezierCurve: Theme.easeEmphasis
                            }
                        }

                        // Each card times out on its own; a critical one
                        // has a timeout of zero and stays until dismissed.
                        Timer {
                            interval: Math.max(0, Notifications.timeoutFor(modelData))
                            running: interval > 0
                            onTriggered: Notifications.dismissPopup(modelData.id)
                        }
                    }
                }
            }
        }
    }
}
