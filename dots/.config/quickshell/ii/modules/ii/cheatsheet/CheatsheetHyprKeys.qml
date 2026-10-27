pragma ComponentBehavior: Bound

import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell

// The hypr keys, on a page of their own: the Hyper chords (a Hyper key sends Super + Ctrl + Alt + Shift, or Mod3)
// and the keys of hypr mode, the second layer of binds (halcyon/hypr_mode.lua).
Item {
    id: root
    implicitWidth: QsWindow?.window?.screen.width * 0.7 ?? 0
    implicitHeight: QsWindow?.window?.screen.height * 0.7 ?? 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Appearance.rounding.small
        spacing: 14

        // How to get at them.
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: intro.implicitHeight + 24
            radius: Appearance.rounding.normal
            color: Appearance.colors.colLayer1
            ColumnLayout {
                id: intro
                anchors.fill: parent
                anchors.margins: 12
                spacing: 6
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Appearance.font.pixelSize.normal
                    text: Translation.tr("<b>Hyper</b> is Super + Ctrl + Alt + Shift pressed together, or one key that sends them (keyd, kanata, or Caps Lock remapped; Mod3 works too).")
                }
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Appearance.font.pixelSize.normal
                    text: Translation.tr("<b>Hypr mode</b> is a second layer of keys: Super + Ctrl + H (or Super + F10 + H) turns it on, Esc turns it off, and it turns itself off after a few seconds without one of its keys. While it is on, the keys below work without Super.")
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

        StyledFlickable {
            id: flickable
            anchors.fill: parent
            clip: true
            contentHeight: height
            contentWidth: flow.implicitWidth
            Flow {
                id: flow
                height: flickable.height
                flow: Flow.TopToBottom
                spacing: 10
                Repeater {
                    model: [...HyprlandKeybinds.categoriesOf(true), ""]
                    delegate: CheatsheetKeybindsCategory {
                        required property var modelData
                        categoryName: modelData
                        hyprOnly: true
                    }
                }
            }
        }

        ScrollEdgeFade {
            target: flickable
            vertical: false
            color: Appearance.colors.colLayer0Base
        }
        }
    }
}
