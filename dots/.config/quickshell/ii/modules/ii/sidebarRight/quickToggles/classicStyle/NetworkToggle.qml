import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions
import qs.modules.ii.sidebarRight.quickToggles
import qs
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

QuickToggleButton {
    toggled: Network.wifiStatus !== "disabled"
    buttonIcon: Network.materialSymbol
    onClicked: Network.toggleWifi()
    altAction: () => {
        Network.openSettings(Network.ethernet) // nmxtui with nmx; NetworkManager's editor otherwise
        GlobalStates.sidebarRightOpen = false
    }
    StyledToolTip {
        text: Translation.tr("%1 | Right-click to configure").arg(Network.networkName)
    }
}
