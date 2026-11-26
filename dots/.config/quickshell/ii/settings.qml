//@ pragma UseQApplication
//@ pragma Env QS_NO_RELOAD_POPUP=1
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic
//@ pragma Env QT_QUICK_FLICKABLE_WHEEL_DECELERATION=10000

// Adjust this to make the app smaller or larger
//@ pragma Env QT_SCALE_FACTOR=1

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions as CF
import "modules/settings/SettingsIndex.js" as SettingsIndex

ApplicationWindow {
    id: root
    property string firstRunFilePath: CF.FileUtils.trimFileProtocol(`${Directories.state}/user/first_run.txt`)
    property string firstRunFileContent: "This file is just here to confirm you've been greeted :>"
    property real contentPadding: 8
    property bool showNextTime: false
    // Every page, under the Halcyon shell (and MacShell, Noctalia: Settings is the Halcyon shell's).
    readonly property var allPages: [
        {
            name: Translation.tr("Quick"),
            icon: "instant_mix",
            component: "modules/settings/QuickConfig.qml"
        },
        {
            name: Translation.tr("Halcyon"),
            icon: "auto_awesome",
            component: "modules/settings/HalcyonConfig.qml"
        },
        {
            name: Translation.tr("Revolver"),
            icon: "casino",
            component: "modules/settings/RevolverConfig.qml"
        },
        {
            name: Translation.tr("General"),
            icon: "browse",
            component: "modules/settings/GeneralConfig.qml"
        },
        {
            name: Translation.tr("Bar"),
            icon: "toast",
            iconRotation: 180,
            component: "modules/settings/BarConfig.qml"
        },
        {
            name: Translation.tr("Background"),
            icon: "texture",
            component: "modules/settings/BackgroundConfig.qml"
        },
        {
            name: Translation.tr("Interface"),
            icon: "bottom_app_bar",
            component: "modules/settings/InterfaceConfig.qml"
        },
        {
            name: Translation.tr("Services"),
            icon: "settings",
            component: "modules/settings/ServicesConfig.qml"
        },
        {
            name: Translation.tr("Advanced"),
            icon: "construction",
            component: "modules/settings/AdvancedConfig.qml"
        },
        {
            name: Translation.tr("About"),
            icon: "info",
            component: "modules/settings/About.qml"
        }
    ]
    // While Summit is the shell: its own page first, then what of Halcyon's applies to it (its page leaves out what only
    // the Halcyon shell does), and About. The Halcyon shell's bar, background, interface and services pages do nothing
    // under Summit, so they are not shown.
    readonly property var summitPages: [
        {
            name: Translation.tr("Summit"),
            icon: "landscape",
            component: "modules/settings/SummitConfig.qml"
        },
        allPages.find(p => p.component === "modules/settings/HalcyonConfig.qml"),
        allPages.find(p => p.component === "modules/settings/About.qml")
    ]
    readonly property var pages: RunningShell.summit ? summitPages : allPages
    property int currentPage: 0

    // ── Search ──────────────────────────────────────────────────────────────────────────────────────────────
    // Every setting on every page, read from the pages themselves (SettingsIndex.js), so new settings are found
    // without anything to keep up to date.
    property var searchIndex: []
    property string query: ""
    readonly property bool searching: query.trim().length > 0
    // The setting to show once its page has loaded: {label, section, subsection}.
    property var pendingTarget: null

    function shown(entry) {
        return {
            label: Translation.tr(entry.label),
            hint: entry.hint ? Translation.tr(entry.hint) : "",
            section: entry.section ? Translation.tr(entry.section) : "",
            subsection: entry.subsection ? Translation.tr(entry.subsection) : "",
            page: root.pages[entry.page]?.name ?? ""
        };
    }

    readonly property var searchResults: {
        if (!searching)
            return [];
        const found = [];
        for (const entry of root.searchIndex) {
            const view = root.shown(entry);
            const score = SettingsIndex.score(entry, view, root.query);
            if (score > 0)
                found.push({ entry: entry, view: view, score: score });
        }
        found.sort((a, b) => b.score - a.score || a.entry.page - b.entry.page);
        return found.slice(0, 60);
    }

    function goTo(entry) {
        root.pendingTarget = entry;
        searchField.text = "";
        if (root.currentPage === entry.page)
            revealTimer.restart();
        else
            root.currentPage = entry.page;
    }

    // The item on the loaded page that shows a label (a setting's text, a section's title).
    function findLabelled(item, label, raw) {
        if (!item)
            return null;
        const queue = [item];
        while (queue.length) {
            const it = queue.shift();
            for (const key of ["title", "text", "mainText", "placeholderText"]) {
                const v = it[key];
                if (typeof v === "string" && (v === label || v === raw) && it !== item)
                    return it;
            }
            if (it.contentItem && it.contentItem !== it && it.contentItem.children)
                queue.push(it.contentItem);
            for (let i = 0; i < (it.children?.length ?? 0); i++)
                queue.push(it.children[i]);
        }
        return null;
    }

    function reveal() {
        const target = root.pendingTarget;
        const page = pageLoader.item;
        if (!target || !page)
            return;
        // A folded section is opened first; the setting is found once it has laid out.
        if (target.section) {
            const section = root.findLabelled(page, Translation.tr(target.section), target.section);
            if (section && section.collapsed && typeof section.toggle === "function" && !target.opened) {
                section.toggle();
                target.opened = true;
                revealTimer.restart();
                return;
            }
        }
        root.pendingTarget = null;
        const item = root.findLabelled(page, Translation.tr(target.label), target.label);
        if (!item)
            return;
        if (page.contentItem && page.contentHeight !== undefined) {
            const y = item.mapToItem(page.contentItem, 0, 0).y;
            page.contentY = Math.max(0, Math.min(y - 80, page.contentHeight - page.height));
        }
        highlightComponent.createObject(item);
    }

    // From elsewhere (a launcher, a script): `qs -p <shell>/settings.qml ipc call settings search "wall"` shows the
    // results; `... reveal "wall"` goes straight to the best one.
    IpcHandler {
        target: "settings"
        function search(text: string): void {
            searchField.text = text;
            searchField.forceActiveFocus();
        }
        function reveal(text: string): void {
            searchField.text = text;
            if (root.searchResults.length)
                root.goTo(root.searchResults[0].entry);
        }
    }

    Timer {
        id: revealTimer
        interval: 160
        onTriggered: root.reveal()
    }

    // A ring of the accent colour round the setting that was found, fading out.
    Component {
        id: highlightComponent
        Rectangle {
            id: ring
            anchors.fill: parent
            anchors.margins: -6
            z: 100
            radius: Appearance.rounding.normal
            color: CF.ColorUtils.transparentize(Appearance.colors.colPrimary, 0.85)
            border.width: 2
            border.color: Appearance.colors.colPrimary
            SequentialAnimation on opacity {
                running: true
                NumberAnimation { from: 0; to: 1; duration: 150 }
                PauseAnimation { duration: 1100 }
                NumberAnimation { to: 0; duration: 600 }
                ScriptAction { script: ring.destroy() }
            }
        }
    }

    Instantiator {
        model: root.pages
        delegate: FileView {
            required property var modelData
            required property int index
            path: Quickshell.shellPath(modelData.component)
            onLoaded: {
                const others = root.searchIndex.filter(e => e.page !== index);
                root.searchIndex = others.concat(SettingsIndex.parse(text(), index));
            }
        }
    }

    visible: true
    onClosing: Qt.quit()
    title: "Halcyon Settings"

    Component.onCompleted: {
        MaterialThemeLoader.reapplyTheme()
        Config.readWriteDelay = 0 // Settings app always only sets one var at a time so delay isn't needed
    }

    minimumWidth: 750
    minimumHeight: 500
    width: 1100
    height: 750
    color: Appearance.m3colors.m3background

    ColumnLayout {
        anchors {
            fill: parent
            margins: contentPadding
        }

        Keys.onPressed: (event) => {
            if (event.modifiers === Qt.ControlModifier) {
                if (event.key === Qt.Key_F) {
                    searchField.forceActiveFocus();
                    searchField.selectAll();
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_PageDown) {
                    root.currentPage = Math.min(root.currentPage + 1, root.pages.length - 1)
                    event.accepted = true;
                } 
                else if (event.key === Qt.Key_PageUp) {
                    root.currentPage = Math.max(root.currentPage - 1, 0)
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_Tab) {
                    root.currentPage = (root.currentPage + 1) % root.pages.length;
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_Backtab) {
                    root.currentPage = (root.currentPage - 1 + root.pages.length) % root.pages.length;
                    event.accepted = true;
                }
            }
        }

        Item { // Titlebar
            visible: Config.options?.windows.showTitlebar
            Layout.fillWidth: true
            Layout.fillHeight: false
            implicitHeight: Math.max(titleText.implicitHeight, windowControlsRow.implicitHeight)
            StyledText {
                id: titleText
                anchors {
                    left: Config.options.windows.centerTitle ? undefined : parent.left
                    horizontalCenter: Config.options.windows.centerTitle ? parent.horizontalCenter : undefined
                    verticalCenter: parent.verticalCenter
                    leftMargin: 12
                }
                color: Appearance.colors.colOnLayer0
                text: Translation.tr("Settings")
                font {
                    family: Appearance.font.family.title
                    pixelSize: Appearance.font.pixelSize.title
                    variableAxes: Appearance.font.variableAxes.title
                }
            }
            RowLayout { // Window controls row
                id: windowControlsRow
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                RippleButton {
                    buttonRadius: Appearance.rounding.full
                    implicitWidth: 35
                    implicitHeight: 35
                    onClicked: root.close()
                    contentItem: MaterialSymbol {
                        anchors.centerIn: parent
                        horizontalAlignment: Text.AlignHCenter
                        text: "close"
                        iconSize: 20
                    }
                }
            }
        }

        RowLayout { // Window content with navigation rail and content pane
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: contentPadding
            Item {
                id: navRailWrapper
                Layout.fillHeight: true
                Layout.margins: 5
                implicitWidth: navRail.expanded ? 150 : fab.baseSize
                Behavior on implicitWidth {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }
                NavigationRail { // Window content with navigation rail and content pane
                    id: navRail
                    anchors {
                        left: parent.left
                        top: parent.top
                        bottom: parent.bottom
                    }
                    spacing: 10
                    expanded: root.width > 900
                    
                    NavigationRailExpandButton {
                        focus: root.visible
                    }

                    FloatingActionButton {
                        id: fab
                        property bool justCopied: false
                        iconText: justCopied ? "check" : "edit"
                        buttonText: justCopied ? Translation.tr("Path copied") : Translation.tr("Config file")
                        expanded: navRail.expanded
                        downAction: () => {
                            Qt.openUrlExternally(`${Directories.config}/illogical-impulse/config.json`);
                        }
                        altAction: () => {
                            Quickshell.clipboardText = CF.FileUtils.trimFileProtocol(`${Directories.config}/illogical-impulse/config.json`);
                            fab.justCopied = true;
                            revertTextTimer.restart()
                        }

                        Timer {
                            id: revertTextTimer
                            interval: 1500
                            onTriggered: {
                                fab.justCopied = false;
                            }
                        }

                        StyledToolTip {
                            text: Translation.tr("Open the shell config file\nAlternatively right-click to copy path")
                        }
                    }

                    NavigationRailTabArray {
                        currentIndex: root.currentPage
                        expanded: navRail.expanded
                        Repeater {
                            model: root.pages
                            NavigationRailButton {
                                required property var index
                                required property var modelData
                                toggled: root.currentPage === index
                                onPressed: root.currentPage = index;
                                expanded: navRail.expanded
                                buttonIcon: modelData.icon
                                buttonIconRotation: modelData.iconRotation || 0
                                buttonText: modelData.name
                                showToggledHighlight: false
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
            ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: root.contentPadding

            // The search field: type part of a setting's name (or what it does) to find it on any page.
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Appearance.rounding.full
                color: searchField.activeFocus ? Appearance.m3colors.m3surfaceContainerHigh : Appearance.m3colors.m3surfaceContainer
                Behavior on color {
                    animation: Appearance.animation.elementMoveFast.colorAnimation.createObject(this)
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 6
                    spacing: 10
                    MaterialSymbol {
                        text: "search"
                        iconSize: Appearance.font.pixelSize.huge
                        color: Appearance.colors.colSubtext
                    }
                    TextField {
                        id: searchField
                        Layout.fillWidth: true
                        background: null
                        placeholderText: Translation.tr("Search settings")
                        placeholderTextColor: Appearance.colors.colSubtext
                        color: Appearance.colors.colOnLayer1
                        selectedTextColor: Appearance.colors.colOnSecondaryContainer
                        selectionColor: Appearance.colors.colSecondaryContainer
                        font {
                            family: Appearance.font.family.main
                            pixelSize: Appearance.font.pixelSize.normal
                            variableAxes: Appearance.font.variableAxes.main
                        }
                        onTextChanged: {
                            root.query = text;
                            resultsList.currentIndex = 0;
                        }
                        Keys.onPressed: event => {
                            if (event.key === Qt.Key_Escape) {
                                text = "";
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Down) {
                                resultsList.incrementCurrentIndex();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Up) {
                                resultsList.decrementCurrentIndex();
                                event.accepted = true;
                            } else if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && root.searchResults.length) {
                                root.goTo(root.searchResults[Math.max(0, resultsList.currentIndex)].entry);
                                event.accepted = true;
                            }
                        }
                    }
                    StyledText {
                        visible: root.searching
                        text: root.searchResults.length === 1 ? Translation.tr("1 setting") : Translation.tr("%1 settings").arg(root.searchResults.length)
                        color: Appearance.colors.colSubtext
                        font.pixelSize: Appearance.font.pixelSize.small
                    }
                    RippleButton {
                        visible: root.searching
                        buttonRadius: Appearance.rounding.full
                        implicitWidth: 34
                        implicitHeight: 34
                        onClicked: searchField.text = ""
                        contentItem: MaterialSymbol {
                            anchors.centerIn: parent
                            horizontalAlignment: Text.AlignHCenter
                            text: "close"
                            iconSize: 20
                        }
                    }
                }
            }

            Rectangle { // Content container
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Appearance.m3colors.m3surfaceContainerLow
                radius: Appearance.rounding.windowRounding - root.contentPadding

                // The results, over the page while there is something typed.
                ListView {
                    id: resultsList
                    anchors.fill: parent
                    anchors.margins: 12
                    visible: root.searching
                    z: 2
                    clip: true
                    spacing: 4
                    model: root.searchResults
                    highlightMoveDuration: 0
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: RippleButton {
                        id: result
                        required property var modelData
                        required property int index
                        width: ListView.view.width
                        implicitHeight: resultRow.implicitHeight + 20
                        buttonRadius: Appearance.rounding.normal
                        toggled: ListView.isCurrentItem
                        onClicked: root.goTo(modelData.entry)
                        contentItem: RowLayout {
                            id: resultRow
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 14
                            MaterialSymbol {
                                text: result.modelData.entry.icon || (result.modelData.entry.kind === "ContentSection" ? "folder_open" : "tune")
                                iconSize: Appearance.font.pixelSize.huge
                                color: result.toggled ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colPrimary
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                StyledText {
                                    Layout.fillWidth: true
                                    text: result.modelData.view.label
                                    elide: Text.ElideRight
                                    font.pixelSize: Appearance.font.pixelSize.normal
                                    font.weight: Font.Medium
                                    color: result.toggled ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnLayer1
                                }
                                StyledText {
                                    Layout.fillWidth: true
                                    text: [result.modelData.view.page, result.modelData.view.section, result.modelData.view.subsection]
                                        .filter(s => s.length > 0).join("  ›  ")
                                    elide: Text.ElideRight
                                    font.pixelSize: Appearance.font.pixelSize.smaller
                                    color: Appearance.colors.colSubtext
                                }
                                StyledText {
                                    Layout.fillWidth: true
                                    visible: text.length > 0
                                    text: result.modelData.view.hint
                                    maximumLineCount: 1
                                    elide: Text.ElideRight
                                    font.pixelSize: Appearance.font.pixelSize.smaller
                                    color: Appearance.colors.colSubtext
                                    opacity: 0.8
                                }
                            }
                            MaterialSymbol {
                                text: "arrow_forward"
                                iconSize: Appearance.font.pixelSize.larger
                                color: Appearance.colors.colSubtext
                            }
                        }
                    }
                    // Nothing found.
                    StyledText {
                        anchors.centerIn: parent
                        visible: root.searching && root.searchResults.length === 0
                        text: Translation.tr("No setting matches “%1”").arg(root.query.trim())
                        color: Appearance.colors.colSubtext
                        font.pixelSize: Appearance.font.pixelSize.normal
                    }
                }

                Loader {
                    id: pageLoader
                    anchors.fill: parent
                    opacity: 1.0
                    visible: !root.searching
                    onLoaded: {
                        if (root.pendingTarget)
                            revealTimer.restart();
                    }

                    active: Config.ready
                    Component.onCompleted: {
                        source = root.pages[0].component
                    }

                    Connections {
                        target: root
                        function onCurrentPageChanged() {
                            switchAnim.complete();
                            switchAnim.start();
                        }
                    }

                    SequentialAnimation {
                        id: switchAnim

                        NumberAnimation {
                            target: pageLoader
                            properties: "opacity"
                            from: 1
                            to: 0
                            duration: 100
                            easing.type: Appearance.animation.elementMoveExit.type
                            easing.bezierCurve: Appearance.animationCurves.emphasizedFirstHalf
                        }
                        ParallelAnimation {
                            PropertyAction {
                                target: pageLoader
                                property: "source"
                                value: root.pages[root.currentPage].component
                            }
                            PropertyAction {
                                target: pageLoader
                                property: "anchors.topMargin"
                                value: 20
                            }
                        }
                        ParallelAnimation {
                            NumberAnimation {
                                target: pageLoader
                                properties: "opacity"
                                from: 0
                                to: 1
                                duration: 200
                                easing.type: Appearance.animation.elementMoveEnter.type
                                easing.bezierCurve: Appearance.animationCurves.emphasizedLastHalf
                            }
                            NumberAnimation {
                                target: pageLoader
                                properties: "anchors.topMargin"
                                to: 0
                                duration: 200
                                easing.type: Appearance.animation.elementMoveEnter.type
                                easing.bezierCurve: Appearance.animationCurves.emphasizedLastHalf
                            }
                        }
                    }
                }
            }
            }
        }
    }
}
