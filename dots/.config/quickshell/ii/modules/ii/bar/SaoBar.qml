pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Hyprland

/**
 * The Sword Art Online theme's top bar, drawn as the game's HUD instead of a bar of pills:
 *
 *   left    the player's name tag (your user name, and "Lv" the number of open windows) and the long slanted HP bar
 *           beside it: the battery (free memory without one), green, then yellow, then red as it empties, with the
 *           "84 / 100" under it. Click: the left sidebar. Scroll: brightness. Hover: the battery's details.
 *   middle  the floors (workspaces): a diamond for each, orange where you are, white where there are windows, an
 *           outline where there are none, and the floor's plate. Click a diamond to go there; scroll to walk up
 *           and down.
 *   right   the tray, round white buttons for the network, the sound and the messages (an orange count while some
 *           are unread), the time and date in a plate with its corner cut the other way, and the round orange
 *           menu button that opens the game's main menu (the theme's launcher). Click the buttons: the right
 *           sidebar. Scroll: volume. Hover the time: the calendar popup.
 *
 * BarContent.qml loads it in place of its own sections while the theme is Sword Art Online.
 */
Item {
    id: hud

    property var screen
    property int compact: 0          // BarContent's shortened form: 1 or 2 on narrow screens

    readonly property color plate: "#F4F6F8"
    readonly property color plateEdge: "#C9D0D8"
    readonly property color ink: "#4A525C"
    readonly property color inkDim: "#8A939D"
    readonly property color orange: "#F5A43B"
    readonly property color orangeLight: "#FFC77A"
    readonly property color crimson: "#E0464E"
    readonly property string font: Appearance.font.family.main

    // ── The player ───────────────────────────────────────────────────────────
    readonly property bool onBattery: Battery.available
    readonly property real hp: Math.max(0, Math.min(1, onBattery ? Battery.percentage : 1 - ResourceUsage.memoryUsedPercentage))
    readonly property color hpColour: hp > 0.5 ? "#7FD15B" : hp > 0.2 ? "#F2C94C" : crimson
    readonly property int level: Math.max(1, HyprlandData.windowList.length)

    // ── The floors ───────────────────────────────────────────────────────────
    readonly property int floor: HyprlandData.monitors.find(m => m.name === (hud.screen?.name ?? ""))?.activeWorkspace?.id
        ?? HyprlandData.monitors.find(m => m.focused)?.activeWorkspace?.id ?? 1
    readonly property int floorsShown: Math.max(1, Config.options.bar.workspaces.shown)
    readonly property int firstFloor: Math.floor((Math.max(1, floor) - 1) / floorsShown) * floorsShown + 1
    readonly property var occupied: {
        const ids = {};
        for (const w of HyprlandData.windowList)
            ids[w.workspace?.id ?? 0] = true;
        return ids;
    }

    // ── Left: name tag and HP ────────────────────────────────────────────────
    MouseArea {
        id: playerArea
        anchors.left: parent.left
        anchors.leftMargin: Appearance.rounding.screenRounding
        anchors.verticalCenter: parent.verticalCenter
        width: player.width
        height: parent.height
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        onClicked: GlobalStates.sidebarLeftOpen = !GlobalStates.sidebarLeftOpen
        onWheel: wheel => {
            if (wheel.angleDelta.y > 0)
                Brightness.increaseBrightness();
            else if (wheel.angleDelta.y < 0)
                Brightness.decreaseBrightness();
        }

        Item {
            id: player
            anchors.verticalCenter: parent.verticalCenter
            width: nameTag.width + 8 + (hud.compact >= 2 ? 0 : hpBar.width + 6)
            height: 28

            // Name and level, in a plate with its corner cut, like the HUD's name tag.
            Shape {
                id: nameTag
                width: hud.compact >= 1 ? 128 : 168
                height: 24
                anchors.verticalCenter: parent.verticalCenter
                ShapePath {
                    strokeWidth: 1
                    strokeColor: hud.plateEdge
                    fillGradient: LinearGradient {
                        x1: 0; y1: 0; x2: 0; y2: 24
                        GradientStop { position: 0; color: "#FFFFFF" }
                        GradientStop { position: 1; color: "#E3E8ED" }
                    }
                    PathSvg { path: `M 0 0 L ${nameTag.width - 11} 0 L ${nameTag.width} 11 L ${nameTag.width} 24 L 0 24 Z` }
                }
                // The orange mark at the tag's left edge.
                Rectangle {
                    x: 0
                    y: 0
                    width: 3
                    height: 24
                    color: hud.orange
                }
                StyledText {
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - levelText.width - 26
                    elide: Text.ElideRight
                    text: SystemInfo.username
                    color: hud.ink
                    font.family: hud.font
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.6
                }
                StyledText {
                    id: levelText
                    anchors.right: parent.right
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Lv " + hud.level
                    color: hud.inkDim
                    font.family: hud.font
                    font.pixelSize: 11
                }
            }

            // The HP bar: long and slanted at its end.
            Item {
                id: hpBar
                visible: hud.compact < 2
                x: nameTag.width + 6
                y: 4
                width: hud.compact >= 1 ? 150 : 220
                height: 12
                Shape {
                    anchors.fill: parent
                    ShapePath {
                        strokeWidth: 1
                        strokeColor: Qt.rgba(1, 1, 1, 0.55)
                        fillColor: Qt.rgba(0, 0, 0, 0.32)
                        PathSvg { path: `M 0 0 L ${hpBar.width} 0 L ${hpBar.width - 9} 12 L 0 12 Z` }
                    }
                }
                Rectangle {
                    x: 2
                    y: 2
                    height: 8
                    width: Math.max(0, (hpBar.width - 13) * hud.hp)
                    color: hud.hpColour
                    Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
                    Behavior on color { ColorAnimation { duration: 300 } }
                    Rectangle { width: parent.width; height: 3; color: Qt.rgba(1, 1, 1, 0.35) }
                }
            }
            StyledText {
                visible: hud.compact < 2
                anchors.right: hpBar.right
                anchors.rightMargin: 10
                y: hpBar.y + hpBar.height + 1
                text: `${Math.round(hud.hp * 100)} / 100`
                    + (Battery.isCharging ? "  ⚡" : "")
                color: "#FFFFFF"
                font.family: hud.font
                font.pixelSize: 10
                style: Text.Outline
                styleColor: Qt.rgba(0, 0, 0, 0.45)
            }
            StyledText {
                visible: hud.compact < 2
                x: hpBar.x + 2
                y: hpBar.y + hpBar.height + 1
                text: hud.onBattery ? "HP" : "HP · MEM"
                color: "#FFFFFF"
                font.family: hud.font
                font.pixelSize: 10
                font.weight: Font.Bold
                style: Text.Outline
                styleColor: Qt.rgba(0, 0, 0, 0.45)
            }
        }

        BatteryPopup {
            hoverTarget: playerArea
        }
    }

    // ── Middle: the floors ───────────────────────────────────────────────────
    MouseArea {
        id: floorsArea
        anchors.centerIn: parent
        width: floors.width + 16
        height: parent.height
        acceptedButtons: Qt.NoButton
        onWheel: wheel => {
            if (wheel.angleDelta.y < 0)
                Hyprland.dispatch(`hl.dsp.focus({workspace = "r+1"})`);
            else if (wheel.angleDelta.y > 0)
                Hyprland.dispatch(`hl.dsp.focus({workspace = "r-1"})`);
        }

        Row {
            id: floors
            anchors.centerIn: parent
            spacing: 10

            // The floor's plate.
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: floorText.width + 18
                height: 20
                radius: 3
                gradient: Gradient {
                    GradientStop { position: 0; color: "#FFFFFF" }
                    GradientStop { position: 1; color: "#E3E8ED" }
                }
                border.width: 1
                border.color: hud.plateEdge
                StyledText {
                    id: floorText
                    anchors.centerIn: parent
                    text: Translation.tr("FLOOR %1").arg(hud.floor)
                    color: hud.ink
                    font.family: hud.font
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.2
                }
            }

            Repeater {
                model: hud.floorsShown
                delegate: Item {
                    id: floorMark
                    required property int index
                    readonly property int floorId: hud.firstFloor + index
                    readonly property bool here: floorId === hud.floor
                    readonly property bool lived: hud.occupied[floorId] === true
                    anchors.verticalCenter: parent.verticalCenter
                    width: 16
                    height: 22
                    Rectangle {
                        anchors.centerIn: parent
                        width: floorMark.here ? 12 : 9
                        height: width
                        rotation: 45
                        color: floorMark.here ? hud.orange : floorMark.lived ? hud.plate : "transparent"
                        border.width: floorMark.here ? 0 : 1.5
                        border.color: floorMark.lived ? hud.plate : Qt.rgba(1, 1, 1, 0.55)
                        scale: floorHover.containsMouse && !floorMark.here ? 1.25 : 1
                        Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutBack } }
                        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
                        Behavior on color { ColorAnimation { duration: 160 } }
                    }
                    // The glow round the floor you are on.
                    Rectangle {
                        visible: floorMark.here
                        anchors.centerIn: parent
                        width: 20
                        height: 20
                        rotation: 45
                        color: "transparent"
                        border.width: 1.5
                        border.color: Qt.rgba(1, 0.75, 0.4, 0.55)
                    }
                    MouseArea {
                        id: floorHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Hyprland.dispatch(`hl.dsp.focus({workspace = ${floorMark.floorId}})`)
                    }
                }
            }
        }
    }

    // ── Right: tray, buttons, time, the menu ─────────────────────────────────
    component RoundButton: Item {
        id: roundButton
        property string icon: ""
        property bool lit: false
        property int badge: 0
        signal activated
        width: 28
        height: 28
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            border.width: 1
            border.color: roundButton.lit ? "#E08A1E" : hud.plateEdge
            gradient: Gradient {
                GradientStop { position: 0; color: roundButton.lit ? hud.orangeLight : "#FFFFFF" }
                GradientStop { position: 1; color: roundButton.lit ? hud.orange : "#DDE2E8" }
            }
            scale: buttonArea.pressed ? 0.9 : buttonArea.containsMouse ? 1.08 : 1
            Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
            MaterialSymbol {
                anchors.centerIn: parent
                text: roundButton.icon
                iconSize: 16
                fill: roundButton.lit ? 1 : 0
                color: roundButton.lit ? "#FFFFFF" : hud.ink
            }
        }
        // The count, an orange disc on the button's shoulder.
        Rectangle {
            visible: roundButton.badge > 0
            x: parent.width - width + 4
            y: -3
            width: Math.max(15, badgeText.width + 8)
            height: 15
            radius: 7.5
            color: hud.orange
            border.width: 1
            border.color: "#FFFFFF"
            StyledText {
                id: badgeText
                anchors.centerIn: parent
                text: roundButton.badge > 99 ? "99+" : String(roundButton.badge)
                color: "#FFFFFF"
                font.family: hud.font
                font.pixelSize: 9
                font.weight: Font.Bold
            }
        }
        MouseArea {
            id: buttonArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: roundButton.activated()
        }
    }

    MouseArea {
        id: statusArea
        anchors.right: parent.right
        anchors.rightMargin: Appearance.rounding.screenRounding
        anchors.verticalCenter: parent.verticalCenter
        width: status.width
        height: parent.height
        acceptedButtons: Qt.NoButton
        onWheel: wheel => {
            if (wheel.angleDelta.y > 0)
                Audio.incrementVolume();
            else if (wheel.angleDelta.y < 0)
                Audio.decrementVolume();
        }

        Row {
            id: status
            anchors.verticalCenter: parent.verticalCenter
            layoutDirection: Qt.LeftToRight
            spacing: 8

            SysTray {
                visible: hud.compact === 0
                anchors.verticalCenter: parent.verticalCenter
                height: hud.height
                invertSide: Config?.options.bar.bottom
            }

            HalcyonUpdateButton {
                anchors.verticalCenter: parent.verticalCenter
            }

            RoundButton {
                anchors.verticalCenter: parent.verticalCenter
                icon: Network.materialSymbol
                onActivated: GlobalStates.sidebarRightOpen = !GlobalStates.sidebarRightOpen
            }
            RoundButton {
                anchors.verticalCenter: parent.verticalCenter
                icon: (Audio.sink?.audio?.muted ?? false) ? "volume_off" : "volume_up"
                onActivated: GlobalStates.sidebarRightOpen = !GlobalStates.sidebarRightOpen
            }
            RoundButton {
                anchors.verticalCenter: parent.verticalCenter
                icon: Notifications.silent ? "notifications_paused" : "mail"
                badge: Notifications.unread
                lit: GlobalStates.sidebarRightOpen
                onActivated: GlobalStates.sidebarRightOpen = !GlobalStates.sidebarRightOpen
            }

            // The time, in a plate with the corner cut on the other side.
            MouseArea {
                id: clockArea
                anchors.verticalCenter: parent.verticalCenter
                width: clockPlate.width
                height: 26
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: GlobalStates.sidebarRightOpen = !GlobalStates.sidebarRightOpen
                Shape {
                    id: clockPlate
                    width: Math.max(timeText.width, dateText.width) + 30
                    height: 26
                    ShapePath {
                        strokeWidth: 1
                        strokeColor: hud.plateEdge
                        fillGradient: LinearGradient {
                            x1: 0; y1: 0; x2: 0; y2: 26
                            GradientStop { position: 0; color: "#FFFFFF" }
                            GradientStop { position: 1; color: "#E3E8ED" }
                        }
                        PathSvg { path: `M 11 0 L ${clockPlate.width} 0 L ${clockPlate.width} 26 L 0 26 L 0 11 Z` }
                    }
                    Rectangle {
                        x: clockPlate.width - 3
                        width: 3
                        height: 26
                        color: hud.orange
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        x: 16
                        spacing: -2
                        StyledText {
                            id: timeText
                            text: DateTime.time
                            color: hud.ink
                            font.family: hud.font
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }
                        StyledText {
                            id: dateText
                            visible: hud.compact === 0
                            text: DateTime.date
                            color: hud.inkDim
                            font.family: hud.font
                            font.pixelSize: 9
                        }
                    }
                }
                ClockWidgetPopup {
                    hoverTarget: clockArea
                }
            }

            // The game's menu.
            RoundButton {
                anchors.verticalCenter: parent.verticalCenter
                width: 32
                height: 32
                icon: "menu"
                lit: true
                onActivated: GlobalStates.overviewOpen = !GlobalStates.overviewOpen
            }
        }
    }
}
