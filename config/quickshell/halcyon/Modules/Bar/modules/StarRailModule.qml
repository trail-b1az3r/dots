import QtQuick
import Quickshell.Io
import qs.Config
import qs.Services
import "../"

/**
 * The Star Rail theme's current character, with that character's element
 * colour as a dot. Hidden until a character has been fetched and chosen,
 * so a bar that never asked for Star Rail does not show an empty slot.
 * Clicking shows another character; that is the one network request this
 * module makes, and it only happens after the click.
 */
BarItem {
    id: root

    property var hostBar: null
    property var character: null

    visible: root.character !== null
    tooltip: root.character
        ? qsTr("%1 · %2 · %3 — click for another").arg(root.character.name).arg(root.character.element).arg(root.character.path)
        : ""
    onActivated: Actions.run(["action", "starrail.next"])

    function refresh(): void {
        Actions.capture(["starrail", "status", "--json"], function (text) {
            try {
                const data = JSON.parse(text);
                root.character = data.current ?? null;
            } catch (error) {
                root.character = null;
            }
        });
    }

    Component.onCompleted: root.refresh()

    Timer {
        interval: 5 * 60 * 1000
        running: true
        repeat: true
        onTriggered: root.refresh()
    }

    content: Row {
        spacing: Theme.spacingXs

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 8
            height: 8
            radius: 4
            color: root.character && root.character.accent ? root.character.accent : Theme.accent
        }

        Text {
            text: root.character ? root.character.name : ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeBody
            renderType: Text.QtRendering
        }
    }
}
