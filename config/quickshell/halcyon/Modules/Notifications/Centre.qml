import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Config
import qs.Components
import qs.Services

/**
 * The notification centre.
 *
 * A panel on the side the popups appear on, holding the history, grouped
 * by application when the user asked for that. Opening it marks
 * everything seen — the count on the bar is "since you last looked",
 * which is the only definition that does not lie.
 */
OverlayWindow {
    id: root

    name: "notifications"
    namespaceName: "halcyon-notifications"
    origin: Config.get("notifications.position", "top-right").indexOf("right") > 0
        ? "right" : "left"
    scrim: false
    grabKeyboard: false

    onOpened: Notifications.markAllSeen()

    readonly property bool grouped: Config.get("notifications.groupByApp", true)

    /** History, optionally collapsed into one entry per application. */
    readonly property var entries: {
        if (!root.grouped)
            return Notifications.history.map(entry => ({ entry: entry, count: 1 }));

        const order = [];
        const buckets = ({});
        for (const entry of Notifications.history) {
            const key = entry.appName || "Other";
            if (buckets[key] === undefined) {
                buckets[key] = { entry: entry, count: 0, all: [] };
                order.push(key);
            }
            buckets[key].count += 1;
            buckets[key].all.push(entry);
        }
        return order.map(key => buckets[key]);
    }

    GlassSurface {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: root.origin === "right" ? parent.right : undefined
        anchors.left: root.origin === "left" ? parent.left : undefined
        anchors.margins: Theme.spacingMd
        anchors.topMargin: Config.get("bar.height", 34) + Theme.spacingMd

        width: 400
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPaddingTight

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spacingSm

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.spacingSm
                Layout.topMargin: Theme.spacingXs
                spacing: Theme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: "Notifications"
                    variant: "title"
                }

                GlassIconButton {
                    glyph: Notifications.doNotDisturb ? "󰂛" : "󰂚"
                    active: Notifications.doNotDisturb
                    tooltip: "Do Not Disturb"
                    onClicked: Notifications.setDoNotDisturb(!Notifications.doNotDisturb)
                }

                GlassIconButton {
                    glyph: "󰩹"
                    tooltip: "Clear all"
                    enabled: Notifications.history.length > 0
                    onClicked: Notifications.clearAll()
                }
            }

            Separator { Layout.fillWidth: true }

            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: Theme.spacingSm
                topMargin: Theme.spacingXs
                bottomMargin: Theme.spacingXs
                boundsBehavior: Flickable.StopAtBounds
                model: root.entries

                delegate: NotificationCard {
                    required property var modelData

                    width: ListView.view.width
                    entry: modelData.entry
                    compact: false
                    level: 1

                    onDismissed: Notifications.close(modelData.entry.id)

                    // A group shows how many more are behind the newest.
                    Badge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.spacingSm
                        visible: root.grouped && (modelData.count ?? 1) > 1
                        text: String(modelData.count ?? 1)
                        background: Theme.surfaceRaised
                        foreground: Theme.textSecondary
                    }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: Notifications.history.length === 0

                Column {
                    anchors.centerIn: parent
                    spacing: Theme.spacingSm

                    Icon {
                        anchors.horizontalCenter: parent.horizontalCenter
                        glyph: "󰂜"
                        size: 40
                        color: Theme.textTertiary
                    }

                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "No notifications"
                        variant: "body"
                        tone: "tertiary"
                    }
                }
            }
        }
    }
}
