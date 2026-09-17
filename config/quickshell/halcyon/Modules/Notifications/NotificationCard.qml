import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/**
 * One notification, as a glass card.
 *
 * Used for both the popup and the row in the notification centre, so a
 * notification looks the same wherever you meet it.
 */
GlassSurface {
    id: root

    required property var entry
    property bool compact: false
    property bool showActions: true

    signal dismissed
    signal activated

    level: root.compact ? 1 : 3
    radius: Theme.radiusLg
    padding: Theme.panelPaddingTight
    implicitHeight: layout.implicitHeight + padding * 2

    // A hairline in the urgency colour along the leading edge: enough to
    // tell a critical notification from an ordinary one at a glance,
    // without colouring the whole card.
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: Theme.spacingSm
        width: 3
        radius: 2
        visible: root.entry.urgency === 2
        color: Notifications.urgencyColour(root.entry)
    }

    ColumnLayout {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.spacingXs

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingSm

            Icon {
                Layout.alignment: Qt.AlignTop
                source: root.entry.image.length > 0 ? root.entry.image : root.entry.appIcon
                glyph: "󰂚"
                size: root.compact ? 20 : 28
                color: Theme.textSecondary
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Label {
                        Layout.fillWidth: true
                        text: root.entry.summary
                        variant: "body"
                        font.weight: Theme.weightSemibold
                    }

                    Label {
                        text: root.relativeTime(root.entry.time)
                        variant: "caption"
                        tone: "tertiary"
                    }
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.entry.body.length > 0
                    text: root.entry.body
                    variant: "footnote"
                    tone: "secondary"
                    wrapMode: Text.WordWrap
                    maximumLineCount: root.compact ? 2 : 6
                    textFormat: Text.StyledText
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.entry.appName.length > 0
                    text: root.entry.appName
                    variant: "caption"
                    tone: "tertiary"
                }
            }

            GlassIconButton {
                Layout.alignment: Qt.AlignTop
                glyph: "󰅖"
                size: 24
                iconSize: 12
                tooltip: "Dismiss"
                onClicked: root.dismissed()
            }
        }

        // Action buttons, when the sending application offered any.
        Flow {
            Layout.fillWidth: true
            Layout.topMargin: Theme.spacingXs
            spacing: Theme.spacingSm
            visible: root.showActions && root.actions.length > 0

            Repeater {
                model: root.actions

                GlassButton {
                    required property var modelData
                    text: modelData.text
                    variant: "tinted"
                    implicitHeight: 28
                    horizontalPadding: Theme.spacingMd
                    onClicked: {
                        Notifications.invokeAction(root.entry.id, modelData.identifier);
                        root.activated();
                    }
                }
            }
        }
    }

    readonly property var actions: {
        const list = root.entry.notification?.actions ?? [];
        // "default" is the click-the-notification action, not a button.
        return list.filter(action => action.identifier !== "default");
    }

    StateLayer {
        anchors.fill: parent
        radius: root.radius
        z: -1
        onClicked: {
            const list = root.entry.notification?.actions ?? [];
            const fallback = list.find(action => action.identifier === "default");
            if (fallback)
                fallback.invoke();
            root.activated();
        }
    }

    function relativeTime(timestamp: real): string {
        const seconds = Math.max(0, (Date.now() - timestamp) / 1000);
        if (seconds < 60) return "now";
        if (seconds < 3600) return Math.floor(seconds / 60) + "m";
        if (seconds < 86400) return Math.floor(seconds / 3600) + "h";
        return Math.floor(seconds / 86400) + "d";
    }
}
