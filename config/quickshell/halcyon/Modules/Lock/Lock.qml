import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import Quickshell.Services.Pam
import qs.Config
import qs.Components
import qs.Services

/**
 * The lock screen.
 *
 * hyprlock is the default because a lock screen should be a small,
 * single-purpose program that keeps working when the shell does not.
 * This exists for machines without it, and it is a real lock: the
 * compositor holds the session locked through `WlSessionLock`, and only
 * a successful PAM conversation releases it.
 *
 * Nothing here can be dismissed by killing the shell — that is what the
 * session-lock protocol is for.
 */
Scope {
    id: root

    property bool locked: false
    property string message: ""
    property bool failed: false

    function lock(): void {
        root.message = "";
        root.failed = false;
        root.locked = true;
    }

    WlSessionLock {
        id: session
        locked: root.locked

        surface: WlSessionLockSurface {
            id: surface
            color: "transparent"

            // The desktop behind, blurred by the compositor's own
            // session_lock_blur, with a scrim over it.
            Rectangle {
                anchors.fill: parent
                color: Theme.backdrop
                opacity: 0.86
            }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.spacingLg
                width: 340

                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: Qt.formatDateTime(clock.date ?? new Date(), "HH:mm")
                    variant: "hero"
                }

                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: Qt.formatDateTime(clock.date ?? new Date(), "dddd, d MMMM")
                    variant: "body"
                    tone: "secondary"
                }

                Item { Layout.preferredHeight: Theme.spacingXl }

                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: Quickshell.env("USER") ?? ""
                    variant: "body"
                    tone: "secondary"
                }

                GlassField {
                    id: password
                    Layout.fillWidth: true
                    Layout.preferredHeight: 46
                    glyph: "󰌾"
                    placeholder: pam.active ? "Checking…" : "Enter password"
                    echoMode: TextInput.Password
                    enabled: !pam.active

                    onAccepted: text => {
                        if (text.length === 0)
                            return;
                        root.message = "";
                        pam.start();
                    }

                    Component.onCompleted: forceActiveFocus()
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.message.length > 0
                    text: root.message
                    variant: "footnote"
                    color: root.failed ? Theme.danger : Theme.textSecondary
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Theme.spacingLg
                    visible: Power.hasBattery || Media.hasPlayer

                    Label {
                        visible: Power.hasBattery
                        text: Power.glyph + "  " + Power.percent + "%"
                        variant: "caption"
                        tone: "tertiary"
                    }

                    Label {
                        visible: Media.hasPlayer
                        text: "󰎈  " + Media.title
                        variant: "caption"
                        tone: "tertiary"
                        elide: Text.ElideRight
                        Layout.maximumWidth: 200
                    }
                }
            }

            SystemClock {
                id: clock
                enabled: root.locked
                precision: SystemClock.Minutes
            }
        }
    }

    PamContext {
        id: pam
        // The same stack the login manager uses; nothing custom, so a
        // fingerprint reader or a smartcard configured system-wide works
        // here too.
        config: "login"
        user: Quickshell.env("USER") ?? ""

        onResponseRequired: this.respond(password.text)

        onCompleted: result => {
            if (result === PamResult.Success) {
                root.locked = false;
                password.text = "";
                root.message = "";
                root.failed = false;
            } else {
                root.failed = true;
                root.message = result === PamResult.MaxTries
                    ? "Too many attempts."
                    : "Wrong password.";
                password.text = "";
                password.forceActiveFocus();
            }
        }

        onError: error => {
            root.failed = true;
            root.message = "Authentication is unavailable: " + PamError.toString(error);
        }

        onPamMessage: {
            if (this.messageIsError)
                root.failed = true;
            if (this.message.length > 0 && !this.responseRequired)
                root.message = this.message;
        }
    }
}
