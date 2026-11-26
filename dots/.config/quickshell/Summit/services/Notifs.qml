pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Services.Notifications
import qs.services
import "importance.js" as Importance

/**
 * Notifications, while Summit is the shell: Summit is the desktop's notification server (org.freedesktop.Notifications;
 * the Halcyon shell is, under it). Every notification is kept in the side menu until it is dismissed. As it arrives:
 *  - Do not disturb: nothing shows.
 *  - The importance model (importance.js, toggled in Settings) finds it important: the banner under the clock
 *    (popups/ImportantBanner.qml), unless a fullscreen window is in front, then nothing pops up.
 *  - Otherwise: a popup in the top right corner (popups/NotificationPopups.qml), if popups are on.
 */
Singleton {
    id: root

    readonly property var list: server.trackedNotifications.values
    readonly property int count: list.length
    // The popups showing now, newest first: [{notification, id}].
    property var popups: []
    // The banner's queue: [{notification, summary, app, icon, id}].
    property var banners: []
    // Newest first, for the side menu.
    readonly property var newestFirst: list.slice().reverse()
    property var model: null

    signal bannerAdded

    function dismiss(n) {
        n?.dismiss();
    }
    function clearAll() {
        for (const n of root.list.slice())
            n.dismiss();
        root.popups = [];
    }
    function closePopup(id) {
        root.popups = root.popups.filter(p => p.id !== id);
    }
    function nextBanner() {
        root.banners = root.banners.slice(1);
    }
    // Whether the focused monitor shows a fullscreen window (a game, a video): then nothing pops up over it.
    function fullscreenInFront() {
        return Hyprland.focusedMonitor?.activeWorkspace?.hasFullscreen ?? false;
    }
    function judge(n) {
        return Importance.judge(root.model, {
            appName: n.appName ?? "",
            summary: n.summary ?? "",
            body: n.body ?? "",
            urgency: n.urgency === NotificationUrgency.Critical ? 2 : n.urgency === NotificationUrgency.Low ? 0 : 1,
            hasActions: (n.actions?.length ?? 0) > 0
        }, Prefs.importantThreshold);
    }

    NotificationServer {
        id: server
        keepOnReload: true
        actionsSupported: true
        bodyMarkupSupported: true
        bodySupported: true
        imageSupported: true
        persistenceSupported: true

        onNotification: n => {
            n.tracked = !n.transient;
            if (Prefs.doNotDisturb)
                return;
            const id = n.id + ":" + Date.now();
            if (Prefs.importantBanner && root.model) {
                const verdict = root.judge(n);
                if (verdict.important) {
                    if (!root.fullscreenInFront()) {
                        root.banners = [...root.banners, { notification: n, summary: verdict.summary, app: n.appName ?? "", icon: n.appIcon ?? "", image: n.image ?? "", id }];
                        root.bannerAdded();
                    }
                    return;
                }
            }
            if (Prefs.popups)
                root.popups = [{ notification: n, id }, ...root.popups].slice(0, 4);
        }
    }

    // The model's weights (tools/summit-importance/train.py writes them).
    FileView {
        path: Qt.resolvedUrl("../assets/model/importance.json").toString().replace("file://", "")
        printErrors: false
        onLoaded: {
            try {
                root.model = JSON.parse(text());
            } catch (e) {
                root.model = null;
            }
        }
    }
}
