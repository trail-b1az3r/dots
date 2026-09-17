import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Config
import qs.Components
import qs.Services

/**
 * The assistant's conversation surface.
 *
 * The orb sits at the top with the current state under it, the
 * conversation scrolls beneath, and a text field is always available —
 * an assistant you can only talk to is useless in a quiet room.
 *
 * Streaming output is rendered as it arrives, and every action the
 * assistant takes is shown as a row in the transcript, so nothing
 * happens to the machine without a visible record of it.
 */
OverlayWindow {
    id: root

    name: "assistant"
    namespaceName: "halcyon-assistant"
    origin: "bottom"
    grabKeyboard: true

    onOpened: {
        if (!Assistant.online)
            Assistant.start();
        const prompt = Overlays.payload.prompt ?? "";
        if (prompt.length > 0)
            Assistant.ask(prompt);
        if (Overlays.payload.listen === true)
            Assistant.listen();
        input.forceActiveFocus();
    }

    GlassSurface {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.spacingXl

        width: Math.min(560, root.width - Theme.spacingXl * 2)
        height: Math.min(660, root.height * 0.76)
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPadding
        tintStrength: 1.15

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spacingMd

            // ── Header ───────────────────────────────────────────────

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: "Halcyon"
                    variant: "title"
                }

                Label {
                    visible: Assistant.providerTitle.length > 0
                    text: Assistant.providerTitle
                    variant: "caption"
                    tone: "tertiary"
                }

                GlassIconButton {
                    glyph: "󰩹"
                    size: 26
                    iconSize: 13
                    tooltip: "Clear the conversation"
                    enabled: Assistant.history.length > 0
                    onClicked: Assistant.clearConversation()
                }

                GlassIconButton {
                    glyph: "󰒓"
                    size: 26
                    iconSize: 13
                    tooltip: "Assistant settings"
                    onClicked: {
                        Overlays.close(root.name);
                        Actions.openSettings("assistant");
                    }
                }
            }

            // ── Orb ──────────────────────────────────────────────────

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 156

                Orb {
                    anchors.centerIn: parent
                    size: 128
                }

                StateLayer {
                    anchors.centerIn: parent
                    width: 128
                    height: 128
                    radius: 64
                    onClicked: {
                        if (Assistant.busy)
                            Assistant.cancel();
                        else
                            Assistant.listen();
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: Assistant.statusText
                variant: "footnote"
                tone: "secondary"
                horizontalAlignment: Text.AlignHCenter
            }

            Label {
                Layout.fillWidth: true
                visible: Assistant.lastError.length > 0
                text: Assistant.lastError
                variant: "caption"
                color: Theme.danger
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 3
            }

            GlassButton {
                Layout.alignment: Qt.AlignHCenter
                visible: !Assistant.online
                text: "Start the assistant"
                variant: "filled"
                onClicked: Assistant.start()
            }

            Separator { Layout.fillWidth: true }

            // ── Conversation ─────────────────────────────────────────

            ListView {
                id: conversation
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: Theme.spacingSm
                boundsBehavior: Flickable.StopAtBounds
                model: root.turns

                // Follow the tail while a reply streams in.
                onCountChanged: positionViewAtEnd()

                delegate: ColumnLayout {
                    required property var modelData

                    width: ListView.view.width
                    spacing: 2

                    Label {
                        Layout.fillWidth: true
                        text: modelData.role === "user" ? "You" : "Halcyon"
                        variant: "caption"
                        tone: "tertiary"
                        horizontalAlignment: modelData.role === "user"
                            ? Text.AlignRight : Text.AlignLeft
                    }

                    GlassSurface {
                        Layout.fillWidth: true
                        Layout.maximumWidth: parent.width * 0.92
                        Layout.alignment: modelData.role === "user"
                            ? Qt.AlignRight : Qt.AlignLeft
                        level: 1
                        radius: Theme.radiusMd
                        padding: Theme.spacingSm
                        surfaceColor: modelData.role === "user"
                            ? Theme.surfaceSelected : Theme.surfaceRaised
                        implicitHeight: bubble.implicitHeight + padding * 2

                        Label {
                            id: bubble
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            text: modelData.content
                            variant: "body"
                            wrapMode: Text.WordWrap
                            elide: Text.ElideNone
                        }
                    }
                }
            }

            // ── Actions taken this turn ──────────────────────────────

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spacingXs
                visible: Assistant.actionsTaken.length > 0

                Repeater {
                    model: Assistant.actionsTaken

                    Rectangle {
                        required property var modelData

                        height: 22
                        width: actionLabel.implicitWidth + Theme.spacingMd
                        radius: height / 2
                        color: Theme.surfaceRaised
                        border.width: 1
                        border.color: Theme.glassBorder

                        Row {
                            anchors.centerIn: parent
                            spacing: 4

                            Icon {
                                anchors.verticalCenter: parent.verticalCenter
                                glyph: modelData.source === "intent" ? "󰐍" : "󰚩"
                                size: 11
                                color: Theme.textTertiary
                            }

                            Label {
                                id: actionLabel
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.title
                                variant: "caption"
                                tone: "secondary"
                            }
                        }
                    }
                }
            }

            // ── Confirmation ─────────────────────────────────────────
            //
            // Destructive actions never run on a transcript alone.

            GlassSurface {
                Layout.fillWidth: true
                visible: Assistant.pendingConfirmation !== null
                level: 1
                radius: Theme.radiusMd
                padding: Theme.spacingSm
                surfaceColor: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.16)
                implicitHeight: confirmRow.implicitHeight + padding * 2

                RowLayout {
                    id: confirmRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: Theme.spacingSm

                    Label {
                        Layout.fillWidth: true
                        text: Assistant.pendingConfirmation
                            ? Assistant.pendingConfirmation.text
                            : ""
                        variant: "footnote"
                        wrapMode: Text.WordWrap
                    }

                    GlassButton {
                        text: "Cancel"
                        implicitHeight: 28
                        onClicked: Assistant.confirm(false)
                    }

                    GlassButton {
                        text: "Do it"
                        variant: "filled"
                        destructive: true
                        implicitHeight: 28
                        onClicked: Assistant.confirm(true)
                    }
                }
            }

            // ── Input ────────────────────────────────────────────────

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingSm

                GlassField {
                    id: input
                    Layout.fillWidth: true
                    glyph: "󰭹"
                    placeholder: "Ask or type a command"
                    onAccepted: text => {
                        if (text.trim().length === 0)
                            return;
                        Assistant.ask(text);
                        input.text = "";
                    }
                    onEscaped: Overlays.close(root.name)
                }

                GlassIconButton {
                    glyph: Assistant.busy ? "󰓛" : "󰍬"
                    size: 40
                    iconSize: 18
                    active: Assistant.state === "listening"
                    tooltip: Assistant.busy ? "Stop" : "Talk"
                    onClicked: {
                        if (Assistant.busy)
                            Assistant.cancel();
                        else
                            Assistant.listen();
                    }
                }
            }
        }
    }

    /** History plus whatever is streaming right now. */
    readonly property var turns: {
        let list = Assistant.history.slice();
        if (Assistant.transcript.length > 0
            && (list.length === 0
                || list[list.length - 1].content !== Assistant.transcript)) {
            list = list.concat([{ role: "user", content: Assistant.transcript }]);
        }
        if (Assistant.reply.length > 0)
            list = list.concat([{ role: "assistant", content: Assistant.reply }]);
        return list;
    }
}
