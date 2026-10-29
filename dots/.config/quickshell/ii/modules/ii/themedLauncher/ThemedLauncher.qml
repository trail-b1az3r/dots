import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

/**
 * The theme's own app picker, opened with Super (or Hyper) in place of the overview when the theme has one and
 * Settings > Halcyon > On the screen allows it: a manga book for Manga Ink and Manga Ink Dark (MangaBook.qml), a
 * phone for After ICEY (IceyPhone.qml). Both take typing: an app, a sum, a command, whatever LauncherSearch finds.
 *
 * The picker is built once, while the theme is one of these, and kept: building the pages' icons and drawings when Super
 * is pressed made the opening animation stutter, so Super only shows the window and plays it (open()). The window stays
 * while the picker plays its closing animation; the picker says when it is done (closed()).
 */
Scope {
    id: root

    readonly property string kind: GlobalStates.themedLauncher
    property bool shown: false
    // The book or the phone, built while the theme has one.
    property var picker: null
    onKindChanged: if (kind === "") picker = null
    property var focusedScreen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]

    Connections {
        target: GlobalStates
        function onOverviewOpenChanged() {
            if (root.kind === "")
                return;
            if (GlobalStates.overviewOpen) {
                LauncherSearch.query = "";
                root.shown = true;
                root.picker?.open();
            } else if (root.shown && root.picker) {
                root.picker.close();
            } else {
                root.shown = false;
            }
        }
    }

    /** Open an app (a DesktopEntry), as the overview does: in a terminal when it asks for one. */
    function launchEntry(entry) {
        if (!entry)
            return;
        if (!entry.runInTerminal)
            entry.execute();
        else
            Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} -e '${StringUtils.shellSingleQuoteEscape(entry.command.join(" "))}'`]);
        root.dismiss();
    }
    /** Run a LauncherSearch result: open the app, copy the sum, run the command... */
    function runResult(result) {
        if (!result)
            return;
        result.execute();
        root.dismiss();
    }
    function dismiss() {
        GlobalStates.overviewOpen = false;
    }
    /** Apps as the book and the phone list them: shown in menus, each once, by name. */
    function apps() {
        return AppSearch.list.filter(a => !a.noDisplay).sort((a, b) => a.name.localeCompare(b.name));
    }

    Loader {
        active: root.kind !== ""
        sourceComponent: PanelWindow {
            id: panel
            visible: root.shown
            screen: root.focusedScreen
            color: "transparent"
            WlrLayershell.namespace: "quickshell:themedLauncher"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            exclusionMode: ExclusionMode.Ignore
            anchors {
                top: true
                bottom: true
                left: true
                right: true
            }

            // A click beside the picker closes it.
            MouseArea {
                anchors.fill: parent
                onClicked: root.dismiss()
            }

            Loader {
                id: loader
                anchors.fill: parent
                focus: true
                // By file, so a live reload finds them however the folder was imported.
                source: root.kind === "book" ? "MangaBook.qml" : root.kind === "phone" ? "IceyPhone.qml" : ""
                onLoaded: {
                    item.host = root;
                    root.picker = item;
                    if (root.shown)
                        item.open();
                }
                Connections {
                    target: loader.item
                    ignoreUnknownSignals: true
                    function onClosed() {
                        root.shown = false;
                    }
                }
            }
        }
    }
}
