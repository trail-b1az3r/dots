import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland

/**
 * Buttons for the focused window, next to its name: make it mini (or bring it back), float or tile it, close it.
 * They work on tiled windows too, which have no title bar of their own. Shown on the monitor the window is on.
 * Settings > Bar > Window buttons turns them off.
 */
Item {
    id: root

    readonly property HyprlandMonitor monitor: Hyprland.monitorFor(root.QsWindow.window?.screen)
    readonly property string address: MiniWindows.activeAddress
    readonly property var win: HyprlandData.windowByAddress[root.address] ?? null
    readonly property bool shown: root.win !== null && root.win.monitor === root.monitor?.id && !root.win.fullscreen
    readonly property bool isMini: root.shown && MiniWindows.isMini(root.address)

    implicitWidth: root.shown ? row.implicitWidth : 0
    implicitHeight: row.implicitHeight
    visible: root.shown
    clip: true

    function dispatchFloat() {
        Hyprland.dispatch(`hl.dsp.window.float({ action = "toggle", window = "address:${root.address}" })`);
    }

    function dispatchClose() {
        Hyprland.dispatch(`hl.dsp.window.close({ window = "address:${root.address}" })`);
    }

    component WindowButton: RippleButton {
        id: button
        property string symbol
        property string tip
        implicitWidth: 26
        implicitHeight: 26
        buttonRadius: Appearance.rounding.full
        colBackgroundHover: Appearance.colors.colLayer1Hover
        colRipple: Appearance.colors.colLayer1Active
        contentItem: MaterialSymbol {
            horizontalAlignment: Text.AlignHCenter
            text: button.symbol
            iconSize: Appearance.font.pixelSize.large
            fill: button.toggled ? 1 : 0
            color: button.toggled ? Appearance.m3colors.m3onPrimary : Appearance.colors.colOnLayer0
        }
        StyledToolTip {
            text: button.tip
        }
    }

    RowLayout {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2

        WindowButton {
            symbol: root.isMini ? "open_in_full" : "picture_in_picture_alt"
            tip: root.isMini ? Translation.tr("Back to full size") : Translation.tr("Make mini (Super+Ctrl+N)")
            toggled: root.isMini
            onClicked: MiniWindows.toggle(root.address)
        }
        WindowButton {
            symbol: root.win?.floating ? "grid_view" : "select_window"
            tip: root.win?.floating ? Translation.tr("Tile") : Translation.tr("Float")
            onClicked: root.dispatchFloat()
        }
        WindowButton {
            symbol: "close"
            tip: Translation.tr("Close")
            onClicked: root.dispatchClose()
        }
    }
}
