import qs.services
import qs.modules.common
import qs.modules.common.functions
import Qt5Compat.GraphicalEffects
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets

DockButton {
    id: root
    property var appToplevel
    property var appListRoot
    property int lastFocused: -1
    property real iconSize: 35
    property real countDotWidth: 10
    property real countDotHeight: 4
    property bool appIsActive: appToplevel.toplevels.find(t => (t.activated == true)) !== undefined

    readonly property bool isSeparator: appToplevel.appId === "SEPARATOR"
    // Sword Art Online: each app is one of the game's round menu buttons, orange while its window has focus.
    readonly property bool sao: Config.options.halcyon.theme === "sword-art-online"
    colBackgroundHover: sao ? "transparent" : (Appearance?.colors.colLayer1Hover ?? "#E5DFED")
    colRipple: sao ? Qt.rgba(1, 0.75, 0.4, 0.25) : (Appearance?.colors.colLayer1Active ?? "#D6CEE2")
    property var desktopEntry: DesktopEntries.heuristicLookup(appToplevel.appId)
    enabled: !isSeparator
    implicitWidth: isSeparator ? 1 : implicitHeight - topInset - bottomInset

    Connections {
        target: DesktopEntries

        function onApplicationsChanged() {
            root.desktopEntry = DesktopEntries.heuristicLookup(appToplevel.appId);
        }
    }

    Loader {
        active: isSeparator
        anchors {
            fill: parent
            topMargin: dockVisualBackground.margin + dockRow.padding + Appearance.rounding.normal
            bottomMargin: dockVisualBackground.margin + dockRow.padding + Appearance.rounding.normal
        }
        sourceComponent: DockSeparator {}
    }

    Loader {
        anchors.fill: parent
        active: appToplevel.toplevels.length > 0
        sourceComponent: MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
            onEntered: {
                appListRoot.lastHoveredButton = root
                appListRoot.buttonHovered = true
                lastFocused = appToplevel.toplevels.length - 1
            }
            onExited: {
                if (appListRoot.lastHoveredButton === root) {
                    appListRoot.buttonHovered = false
                }
            }
        }
    }

    onClicked: {
        if (appToplevel.toplevels.length === 0) {
            root.desktopEntry?.execute();
            return;
        }
        lastFocused = (lastFocused + 1) % appToplevel.toplevels.length
        appToplevel.toplevels[lastFocused].activate()
    }

    middleClickAction: () => {
        root.desktopEntry?.execute();
    }

    altAction: () => {
        TaskbarApps.togglePin(appToplevel.appId);
    }

    contentItem: Loader {
        active: !isSeparator
        sourceComponent: Item {
            anchors.centerIn: parent

            // Sword Art Online: the round button, and the glow round the one in focus.
            Rectangle {
                visible: root.sao
                anchors.centerIn: iconImageLoader
                width: root.iconSize + 14
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Qt.rgba(1, 0.75, 0.4, 0.55)
                opacity: root.appIsActive ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 180 } }
            }
            Rectangle {
                visible: root.sao
                anchors.centerIn: iconImageLoader
                width: root.iconSize + 6
                height: width
                radius: width / 2
                border.width: 1
                border.color: root.appIsActive ? "#E08A1E" : "#C9D0D8"
                gradient: Gradient {
                    GradientStop { position: 0; color: root.appIsActive ? "#FFC77A" : "#FFFFFF" }
                    GradientStop { position: 1; color: root.appIsActive ? "#F5A43B" : "#DDE2E8" }
                }
                scale: root.down ? 0.92 : root.hovered && !root.appIsActive ? 1.07 : 1
                Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
            }

            Loader {
                id: iconImageLoader
                anchors {
                    left: parent.left
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                }
                active: !root.isSeparator
                sourceComponent: IconImage {
                    source: AppSearch.iconSource(appToplevel.appId)
                    // Sword Art Online: smaller, so the white button shows round it.
                    implicitSize: root.sao ? Math.round(root.iconSize * 0.7) : root.iconSize
                }
            }

            Loader {
                active: Config.options.dock.monochromeIcons
                anchors.fill: iconImageLoader
                sourceComponent: Item {
                    Desaturate {
                        id: desaturatedIcon
                        visible: false // There's already color overlay
                        anchors.fill: parent
                        source: iconImageLoader
                        desaturation: 0.8
                    }
                    ColorOverlay {
                        anchors.fill: desaturatedIcon
                        source: desaturatedIcon
                        color: ColorUtils.transparentize(Appearance.colors.colPrimary, 0.9)
                    }
                }
            }

            RowLayout {
                spacing: 3
                anchors {
                    top: iconImageLoader.bottom
                    topMargin: root.sao ? 9 : 2
                    horizontalCenter: parent.horizontalCenter
                }
                Repeater {
                    model: Math.min(appToplevel.toplevels.length, 3)
                    delegate: Rectangle {
                        required property int index
                        // Sword Art Online: small diamonds, as the game marks things.
                        radius: root.sao ? 0 : Appearance.rounding.full
                        rotation: root.sao ? 45 : 0
                        implicitWidth: root.sao ? 5 : (appToplevel.toplevels.length <= 3) ?
                            root.countDotWidth : root.countDotHeight // Circles when too many
                        implicitHeight: root.sao ? 5 : root.countDotHeight
                        color: root.sao ? (appIsActive ? "#F5A43B" : "#F4F6F8") : appIsActive ? Appearance.colors.colPrimary
                             : ColorUtils.transparentize(Config.options.halcyon.theme === "manga-ink" ? "#141414" : Appearance.colors.colOnLayer0, 0.4)
                    }
                }
            }
        }
    }
}
