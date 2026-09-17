pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Notifications
import qs.Config

/**
 * The notification server.
 *
 * Halcyon is the org.freedesktop.Notifications implementation while the
 * shell is running. Notifications are kept in two lists: the popups that
 * are on screen right now, and the history the notification centre
 * shows. Dismissing a popup does not throw the notification away —
 * that is the difference between a notification system and a toast.
 */
Singleton {
    id: root

    property var popups: []
    property var history: []
    property bool doNotDisturb: Config.get("notifications.doNotDisturb", false)

    readonly property int unread: root.history.filter(entry => !entry.seen).length
    readonly property int historyLimit: Config.get("notifications.historyLimit", 120)
    readonly property int maxVisible: Config.get("notifications.maxVisible", 4)

    signal arrived(var entry)

    NotificationServer {
        id: server

        keepOnReload: true
        bodySupported: true
        bodyMarkupSupported: true
        bodyImagesSupported: true
        actionsSupported: true
        actionIconsSupported: true
        imageSupported: true
        inlineReplySupported: true
        persistenceSupported: true

        onNotification: notification => {
            // Tracking keeps the object alive after the sender goes away,
            // which is what lets history outlive the application.
            notification.tracked = true;
            root.ingest(notification);
        }
    }

    function ingest(notification: var): void {
        const entry = {
            id: notification.id,
            notification: notification,
            appName: notification.appName,
            appIcon: notification.appIcon,
            summary: notification.summary,
            body: notification.body,
            image: notification.image,
            urgency: notification.urgency,
            time: Date.now(),
            seen: false
        };

        root.history = [entry].concat(root.history).slice(0, root.historyLimit);

        // Do Not Disturb silences the popup, not the notification: it
        // still lands in history, which is where people look afterwards.
        // Critical notifications are shown regardless, because that is
        // what the urgency level is for.
        const critical = notification.urgency === NotificationUrgency.Critical;
        if (!root.doNotDisturb || critical)
            root.popups = root.popups.concat([entry]).slice(-root.maxVisible);

        root.arrived(entry);
        root.publish();
    }

    function dismissPopup(id: int): void {
        root.popups = root.popups.filter(entry => entry.id !== id);
    }

    function close(id: int): void {
        const entry = root.history.find(item => item.id === id);
        entry?.notification?.dismiss();
        root.history = root.history.filter(item => item.id !== id);
        root.dismissPopup(id);
        root.publish();
    }

    function clearAll(): void {
        for (const entry of root.history)
            entry.notification?.dismiss();
        root.history = [];
        root.popups = [];
        root.publish();
    }

    function markAllSeen(): void {
        root.history = root.history.map(entry => {
            entry.seen = true;
            return entry;
        });
        root.publish();
    }

    function invokeAction(id: int, identifier: string): void {
        const entry = root.history.find(item => item.id === id);
        const action = entry?.notification?.actions?.find(
            candidate => candidate.identifier === identifier
        );
        action?.invoke();
        root.dismissPopup(id);
    }

    function setDoNotDisturb(value: bool): void {
        root.doNotDisturb = value;
        Config.set("notifications.doNotDisturb", value);
        root.publish();
    }

    function timeoutFor(entry: var): int {
        const notifications = Config.notifications;
        switch (entry.urgency) {
        case NotificationUrgency.Critical:
            return (notifications.criticalTimeout ?? 0) * 1000;
        case NotificationUrgency.Low:
            return (notifications.lowTimeout ?? 4) * 1000;
        default:
            return (notifications.defaultTimeout ?? 6) * 1000;
        }
    }

    function urgencyColour(entry: var): color {
        switch (entry.urgency) {
        case NotificationUrgency.Critical: return Theme.danger;
        case NotificationUrgency.Low: return Theme.textTertiary;
        default: return Theme.accent;
        }
    }

    /**
     * Tell Waybar the count changed.
     *
     * Writing a small state file and signalling the module is much
     * cheaper than having Waybar poll us, and it means the indicator is
     * correct the instant a notification arrives.
     */
    function publish(): void {
        publisher.command = Paths.command([
            "notify", "state",
            String(root.unread),
            root.doNotDisturb ? "on" : "off"
        ]);
        publisher.running = true;
    }

    Process { id: publisher }

    Component.onCompleted: root.publish()
}
