import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

Item {
    id: root
    readonly property HyprlandMonitor monitor: Hyprland.monitorFor(root.QsWindow.window?.screen)
    readonly property Toplevel activeWindow: ToplevelManager.activeToplevel

    property string activeWindowAddress: `0x${activeWindow?.HyprlandToplevel?.address}`
    // niri (services/Niri.qml): the focused window when its workspace is on this screen, else the one this
    // screen's workspace shows.
    readonly property string screenName: root.QsWindow.window?.screen?.name ?? ""
    readonly property var niriWorkspace: Niri.available ? Niri.workspacesOn(screenName).find(ws => ws.is_active) ?? null : null
    readonly property var niriWindow: Niri.available ? Niri.mainWindowOf(niriWorkspace) : null
    property bool focusingThisMonitor: Niri.available ? (Niri.focusedWorkspace?.output === screenName)
        : HyprlandData.activeWorkspace?.monitor == monitor?.name
    property var biggestWindow: Niri.available ? (niriWindow ? { class: niriWindow.app_id ?? "", title: niriWindow.title ?? "" } : null)
        : HyprlandData.biggestWindowForWorkspace(HyprlandData.monitors[root.monitor?.id]?.activeWorkspace.id)

    implicitWidth: colLayout.implicitWidth

    ColumnLayout {
        id: colLayout

        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: -4

        StyledText {
            Layout.fillWidth: true
            font.pixelSize: Appearance.font.pixelSize.smaller
            color: Appearance.colors.colSubtext
            elide: Text.ElideRight
            text: root.focusingThisMonitor && root.activeWindow?.activated && root.biggestWindow ? 
                root.activeWindow?.appId :
                (root.biggestWindow?.class) ?? Translation.tr("Desktop")

        }

        StyledText {
            Layout.fillWidth: true
            font.pixelSize: Appearance.font.pixelSize.small
            color: Appearance.colors.colOnLayer0
            elide: Text.ElideRight
            text: root.focusingThisMonitor && root.activeWindow?.activated && root.biggestWindow ? 
                root.activeWindow?.title :
                (root.biggestWindow?.title) ?? `${Translation.tr("Workspace")} ${Niri.available ? (root.niriWorkspace?.idx ?? 1) : (monitor?.activeWorkspace?.id ?? 1)}`
        }

    }

}
