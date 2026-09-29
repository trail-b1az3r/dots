pragma ComponentBehavior: Bound
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland

/**
 * One window in the window manager: a live thumbnail, its app and title,
 * and (on hover or selection) buttons for what you can do with it.
 */
Rectangle {
    id: tile

    property var windowData
    property var toplevel
    property bool selected: false
    property bool live: true
    readonly property bool hovered: hoverArea.containsMouse
    readonly property real aspect: {
        const size = windowData?.size ?? [16, 10];
        return size[1] > 0 ? Math.min(Math.max(size[0] / size[1], 0.6), 2.4) : 1.6;
    }
    signal activated(string verb)

    implicitHeight: 208
    radius: Appearance.rounding.normal
    color: selected ? Appearance.colors.colSecondaryContainer : hovered ? Appearance.colors.colLayer1Hover : Appearance.colors.colLayer1
    border.width: selected ? 2 : 1
    border.color: selected ? Appearance.colors.colPrimary : ColorUtils.transparentize(Appearance.m3colors.m3outline, 0.85)

    Behavior on color {
        animation: Appearance.animation.elementMoveFast.colorAnimation.createObject(this)
    }

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        onClicked: mouse => tile.activated(mouse.button === Qt.MiddleButton ? "close" : "focus")
    }

    ColumnLayout {
        anchors {
            fill: parent
            margins: 10
        }
        spacing: 8

        // Live thumbnail, letterboxed to the window's shape
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                id: frame
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height * tile.aspect)
                height: width / tile.aspect
                radius: Appearance.rounding.small
                color: Appearance.colors.colLayer2
                clip: true

                ScreencopyView {
                    anchors.fill: parent
                    captureSource: tile.live ? tile.toplevel : null
                    live: tile.live
                }

                // Badges: pinned, floating
                Row {
                    anchors {
                        top: parent.top
                        right: parent.right
                        margins: 6
                    }
                    spacing: 4
                    Repeater {
                        model: [tile.windowData?.pinned ? "keep" : "", tile.windowData?.floating ? "picture_in_picture" : ""].filter(icon => icon.length > 0)
                        delegate: Rectangle {
                            id: badge
                            required property string modelData
                            width: 24
                            height: 24
                            radius: 12
                            color: ColorUtils.transparentize(Appearance.colors.colLayer0, 0.2)
                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: badge.modelData
                                iconSize: 15
                            }
                        }
                    }
                }

                // Actions, on hover or keyboard selection
                Row {
                    anchors {
                        bottom: parent.bottom
                        horizontalCenter: parent.horizontalCenter
                        bottomMargin: 8
                    }
                    spacing: 4
                    opacity: tile.hovered || tile.selected ? 1 : 0
                    visible: opacity > 0
                    Behavior on opacity {
                        animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                    }
                    Repeater {
                        model: [
                            { verb: "minimise", icon: "minimize", tip: Translation.tr("Minimise (Ctrl+M)") },
                            { verb: "float", icon: "picture_in_picture", tip: Translation.tr("Float or tile (Ctrl+F)") },
                            { verb: "pin", icon: "keep", tip: Translation.tr("Pin to every workspace (Ctrl+P)") },
                            { verb: "centre", icon: "center_focus_strong", tip: Translation.tr("Centre (Ctrl+C)") },
                            { verb: "close", icon: "close", tip: Translation.tr("Close (Ctrl+Q)") }
                        ]
                        delegate: RippleButton {
                            id: actionButton
                            required property var modelData
                            implicitWidth: 32
                            implicitHeight: 32
                            buttonRadius: Appearance.rounding.full
                            colBackground: ColorUtils.transparentize(Appearance.colors.colLayer0, 0.15)
                            onClicked: tile.activated(modelData.verb)
                            contentItem: MaterialSymbol {
                                anchors.centerIn: parent
                                horizontalAlignment: Text.AlignHCenter
                                text: actionButton.modelData.icon
                                iconSize: 18
                                color: actionButton.modelData.verb === "close" ? Appearance.m3colors.m3error : Appearance.colors.colOnLayer1
                            }
                            StyledToolTip {
                                text: actionButton.modelData.tip
                            }
                        }
                    }
                }
            }
        }

        // App icon, title, workspace
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            StyledImage {
                source: Quickshell.iconPath(AppSearch.guessIcon(tile.windowData?.class), "image-missing")
                sourceSize: Qt.size(22, 22)
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
            }
            StyledText {
                Layout.fillWidth: true
                text: tile.windowData?.title ?? ""
                elide: Text.ElideRight
                color: tile.selected ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnLayer1
            }
            Rectangle {
                visible: (tile.windowData?.workspace?.name ?? "").length > 0
                implicitWidth: wsLabel.implicitWidth + 14
                implicitHeight: 22
                radius: 11
                color: Appearance.colors.colLayer2
                StyledText {
                    id: wsLabel
                    anchors.centerIn: parent
                    text: {
                        const name = tile.windowData?.workspace?.name ?? "";
                        return name.startsWith("special:") ? name.slice(8) : name;
                    }
                    font.pixelSize: Appearance.font.pixelSize.smaller
                    color: Appearance.colors.colSubtext
                }
            }
        }
    }
}
