import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Config
import qs.Services

/**
 * The shared shell of every overlay: Spotlight, Control Center, the
 * overview, the power menu, Settings.
 *
 * Handles the things each of them would otherwise get subtly different:
 * the layer namespace Hyprland's blur rules key off, taking and giving
 * back keyboard focus, closing on Escape or a click outside, and
 * animating in and out instead of appearing.
 *
 * The window itself only exists while the overlay is open. A layer
 * surface that is merely invisible still costs a buffer and still takes
 * part in the compositor's damage tracking.
 */
PanelWindow {
    id: root

    /** The overlay's name in `Overlays`. */
    required property string name
    /** Layer namespace; must match a rule in the generated Hyprland config. */
    property string namespaceName: "halcyon-overlay"

    /** Dim the desktop behind. */
    property bool scrim: true
    /** Take keyboard focus exclusively (Spotlight, Settings). */
    property bool grabKeyboard: true
    /** Close when the pointer clicks outside the content. */
    property bool closeOnClickOutside: true

    /** Where the panel comes from: center | top | bottom | left | right */
    property string origin: "center"

    readonly property bool shown: Overlays.isOpen(root.name)
    default property alias overlayContent: contentHolder.data

    signal opened
    signal closed

    anchors { top: true; bottom: true; left: true; right: true }
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"

    WlrLayershell.namespace: root.namespaceName
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: root.grabKeyboard
        ? WlrKeyboardFocus.Exclusive
        : WlrKeyboardFocus.None

    // Kept alive a moment past `shown` so the exit animation can run.
    visible: root.shown || exitHold.running

    Timer {
        id: exitHold
        interval: Theme.durOverlay + 40
    }

    onShownChanged: {
        if (root.shown) {
            exitHold.stop();
            root.opened();
        } else {
            exitHold.restart();
            root.closed();
        }
    }

    Scrim {
        shown: root.shown && root.scrim
        onDismissed: Overlays.close(root.name)
    }

    // Catches clicks that land on the layer but not on the panel.
    MouseArea {
        anchors.fill: parent
        enabled: root.closeOnClickOutside && root.shown && !root.scrim
        onClicked: Overlays.close(root.name)
    }

    Item {
        id: contentHolder
        anchors.fill: parent

        opacity: root.shown ? 1 : 0
        scale: root.shown ? 1 : (Theme.reducedMotion ? 1 : 0.97)

        transform: Translate {
            y: {
                if (root.shown || Theme.reducedMotion)
                    return 0;
                switch (root.origin) {
                case "top": return -24;
                case "bottom": return 24;
                default: return 8;
                }
            }
            x: {
                if (root.shown || Theme.reducedMotion)
                    return 0;
                switch (root.origin) {
                case "left": return -24;
                case "right": return 24;
                default: return 0;
                }
            }
        }

        Behavior on opacity {
            enabled: Theme.animationsEnabled
            NumberAnimation {
                duration: Theme.durOverlay
                easing.type: Easing.BezierSpline
                easing.bezierCurve: root.shown ? Theme.easeDecel : Theme.easeAccel
            }
        }

        Behavior on scale {
            enabled: Theme.animationsEnabled
            NumberAnimation {
                duration: Theme.durOverlay
                easing.type: Easing.BezierSpline
                easing.bezierCurve: root.shown ? Theme.easeEmphasis : Theme.easeAccel
            }
        }
    }

    // Escape always closes. Every overlay, no exceptions — an overlay you
    // cannot dismiss with Escape is a trap.
    Keys.onEscapePressed: Overlays.close(root.name)

    /**
     * Give keyboard focus back when the overlay closes.
     *
     * A focus grab holds input away from the window underneath; without
     * releasing it, closing Spotlight would leave the user typing into
     * nothing.
     */
    HyprlandFocusGrab {
        active: root.shown && root.grabKeyboard
        windows: [root]
        onCleared: {
            if (root.shown && root.closeOnClickOutside)
                Overlays.close(root.name);
        }
    }
}
