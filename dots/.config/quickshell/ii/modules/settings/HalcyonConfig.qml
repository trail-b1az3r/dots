import QtQuick
import Quickshell
import Quickshell.Io
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

// Settings > Halcyon: themes, effects and glass.
//
// Everything here is stored under `halcyon` in the shell config, which
// halcyon-theme reads. Changing an effects or glass option re-applies it to
// the active theme through `halcyon-theme refresh`, debounced so dragging a
// slider reloads Hyprland once rather than on every step.
ContentPage {
    id: page
    forceWidth: true

    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`
    // Controls report their initial values while the page is being built;
    // only changes made after that are the user's.
    property bool ready: false
    Component.onCompleted: {
        readyTimer.start();
        customList.running = true;
    }

    Timer {
        id: readyTimer
        interval: 300
        onTriggered: page.ready = true
    }

    Timer {
        id: refreshTimer
        // Longer than Config's own write delay, so the file is saved first.
        interval: 700
        onTriggered: Quickshell.execDetached([page.tool, "refresh"])
    }

    Timer {
        id: cursorTimer
        interval: 700
        onTriggered: Quickshell.execDetached([page.tool, "cursor", "apply"])
    }

    function applyCursor() {
        if (page.ready)
            cursorTimer.restart();
    }

    readonly property string assistantTool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/assistant/halcyon-assistant`

    Timer {
        id: assistantTimer
        interval: 700
        onTriggered: Quickshell.execDetached([page.assistantTool, "reload"])
    }

    function reloadAssistant() {
        if (page.ready)
            assistantTimer.restart();
    }

    // Your own themes (halcyon-theme custom). Read from the tool, so new ones show up.
    property var customThemes: []

    Process {
        id: customList
        command: [page.tool, "custom", "list"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    page.customThemes = JSON.parse(this.text) ?? [];
                } catch (error) {
                    page.customThemes = [];
                }
            }
        }
    }

    Timer {
        id: customListRefresh
        // Long enough for the tool to write the new theme file.
        interval: 800
        onTriggered: customList.running = true
    }

    // Makes a custom theme. Its id comes back on stdout, and it is asked about
    // (what to open) unless "Do not show again" was chosen before.
    Process {
        id: newTheme
        command: [page.tool, "custom", "new"]
        stdout: StdioCollector {
            onStreamFinished: {
                const id = this.text.trim();
                customListRefresh.restart();
                page.askOpenFor = id !== "" && !Config.options.halcyon.customThemeHelpDismissed ? id : "";
            }
        }
    }

    readonly property string halcyonDocsUrl: "https://trail-b1az3r.github.io/dots/"
    readonly property string hyprlandDocsUrl: "https://wiki.hypr.land"
    readonly property string iiDocsUrl: "https://ii.clsty.link"
    // The custom theme just made, while the "what to open" question is showing.
    property string askOpenFor: ""

    // Built-in themes. Their order, and which are hidden, are the user's (Config).
    readonly property var builtinThemes: [
        { id: "hyperneo", name: "HyperNeo", icon: "desktop_mac" },
        { id: "hsr", name: "Star Rail", icon: "train" },
        { id: "shattered-glass", name: "Shattered Glass", icon: "broken_image" },
        { id: "fractured-glass", name: "Fractured Glass", icon: "lens_blur" }
    ]
    property bool showHidden: false
    property string openThemeMenu: "" // Id of the row whose menu is dropped down
    property string pendingDelete: "" // Id of the custom theme waiting for a second click on Delete

    // Built-in themes in the saved order. Ones missing from it go last, in the default order.
    function orderedBuiltins() {
        const ids = Config.options.halcyon.themeOrder.filter(id => page.builtinThemes.some(theme => theme.id === id));
        for (const theme of page.builtinThemes) {
            if (!ids.includes(theme.id))
                ids.push(theme.id);
        }
        return ids.map(id => page.builtinThemes.find(theme => theme.id === id));
    }

    function builtinRows() {
        const hidden = Config.options.halcyon.hiddenThemes;
        return page.orderedBuiltins().filter(theme => page.showHidden || !hidden.includes(theme.id));
    }

    function moveBuiltin(id, step) {
        const ids = page.orderedBuiltins().map(theme => theme.id);
        const from = ids.indexOf(id);
        const to = from + step;
        if (to < 0 || to >= ids.length)
            return;
        ids.splice(from, 1);
        ids.splice(to, 0, id);
        Config.options.halcyon.themeOrder = ids;
    }

    function applyTheme(id) {
        Config.options.halcyon.theme = id;
        if (id === "")
            Quickshell.execDetached([page.tool, "off"]);
        else
            Quickshell.execDetached([page.tool, "apply", id]);
    }

    function toggleThemeMenu(id) {
        page.openThemeMenu = page.openThemeMenu === id ? "" : id;
        page.pendingDelete = "";
    }

    // Auto-apply: the card under the built-in rows, for one theme's time and days.
    property string autoEditing: "" // Id of the theme being scheduled; "" when the card is closed
    property int autoHour: 8
    property int autoMinute: 0
    property var autoDays: [] // ISO weekdays, 1 = Monday. Empty means every day.

    function autoEntry(id) {
        return Config.options.halcyon.autoApply.find(entry => entry.theme === id) ?? null;
    }

    function themeName(id) {
        return page.builtinThemes.find(theme => theme.id === id)?.name ?? id;
    }

    function openAuto(id) {
        const entry = page.autoEntry(id);
        page.autoHour = entry ? parseInt(entry.time.slice(0, 2)) : 8;
        page.autoMinute = entry ? parseInt(entry.time.slice(3, 5)) : 0;
        page.autoDays = entry ? entry.days.slice() : [];
        page.autoEditing = id;
    }

    function toggleAutoDay(day) {
        page.autoDays = page.autoDays.includes(day)
            ? page.autoDays.filter(d => d !== day)
            : page.autoDays.concat([day]).sort((a, b) => a - b);
    }

    function saveAuto() {
        const time = `${String(page.autoHour).padStart(2, "0")}:${String(page.autoMinute).padStart(2, "0")}`;
        const others = Config.options.halcyon.autoApply.filter(entry => entry.theme !== page.autoEditing);
        Config.options.halcyon.autoApply = others.concat([{
            theme: page.autoEditing,
            time: time,
            days: page.autoDays.slice().sort((a, b) => a - b)
        }]);
        page.autoEditing = "";
    }

    function removeAuto() {
        Config.options.halcyon.autoApply = Config.options.halcyon.autoApply.filter(entry => entry.theme !== page.autoEditing);
        page.autoEditing = "";
    }

    function themeMenu(id) {
        if (page.builtinThemes.some(theme => theme.id === id)) {
            const hidden = Config.options.halcyon.hiddenThemes.includes(id);
            return [
                { key: "auto", text: Translation.tr("Auto-apply by time"), icon: "schedule" },
                { key: "up", text: Translation.tr("Move up"), icon: "arrow_upward" },
                { key: "down", text: Translation.tr("Move down"), icon: "arrow_downward" },
                hidden ? { key: "show", text: Translation.tr("Show"), icon: "visibility" }
                       : { key: "hide", text: Translation.tr("Hide"), icon: "visibility_off" }
            ];
        }
        return [
            { key: "apply", text: Translation.tr("Apply"), icon: "check" },
            { key: "duplicate", text: Translation.tr("Duplicate"), icon: "content_copy" },
            { key: "open", text: Translation.tr("Open file"), icon: "open_in_new" },
            {
                key: "delete",
                text: page.pendingDelete === id ? Translation.tr("Click again to delete") : Translation.tr("Delete"),
                icon: "delete"
            }
        ];
    }

    function runThemeAction(id, key) {
        if (key === "delete" && page.pendingDelete !== id) {
            // Deleting needs a second click. The menu stays open until then.
            page.pendingDelete = id;
            return;
        }
        page.openThemeMenu = "";
        page.pendingDelete = "";
        switch (key) {
        case "apply":
            page.applyTheme(id);
            break;
        case "duplicate":
            Quickshell.execDetached([page.tool, "custom", "duplicate", id]);
            customListRefresh.restart();
            break;
        case "open":
            Quickshell.execDetached([page.tool, "custom", "open", id]);
            break;
        case "delete":
            // The tool leaves the theme first if it is the active one.
            Quickshell.execDetached([page.tool, "custom", "delete", id]);
            customListRefresh.restart();
            break;
        case "auto":
            page.openAuto(id);
            break;
        case "up":
            page.moveBuiltin(id, -1);
            break;
        case "down":
            page.moveBuiltin(id, 1);
            break;
        case "hide":
            Config.options.halcyon.hiddenThemes = Config.options.halcyon.hiddenThemes.concat([id]);
            break;
        case "show":
            Config.options.halcyon.hiddenThemes = Config.options.halcyon.hiddenThemes.filter(hidden => hidden !== id);
            break;
        }
    }

    // What to open after a custom theme is made. Each choice closes the question.
    readonly property var openChoices: [
        { text: Translation.tr("Halcyon docs"), icon: "menu_book", run: () => Qt.openUrlExternally(page.halcyonDocsUrl) },
        { text: Translation.tr("Open the config in your default editor"), icon: "edit_document", run: () => Quickshell.execDetached([page.tool, "custom", "open", page.askOpenFor]) },
        { text: Translation.tr("Hyprland docs"), icon: "menu_book", run: () => Qt.openUrlExternally(page.hyprlandDocsUrl) },
        { text: Translation.tr("illogical impulse docs"), icon: "menu_book", run: () => Qt.openUrlExternally(page.iiDocsUrl) },
        { text: Translation.tr("No"), icon: "close", run: () => {} },
        { text: Translation.tr("Do not show again"), icon: "do_not_disturb_on", run: () => { Config.options.halcyon.customThemeHelpDismissed = true; } }
    ]

    function refresh() {
        if (page.ready)
            refreshTimer.restart();
    }

    ContentSection {
        icon: "palette"
        title: Translation.tr("Theme")

        HalcyonThemeRow {
            themeId: ""
            label: Translation.tr("Wallpaper colours")
            icon: "wallpaper"
            isActive: Config.options.halcyon.theme === ""
            onApplied: page.applyTheme("")
        }

        Repeater {
            model: page.builtinRows()

            delegate: HalcyonThemeRow {
                required property var modelData
                readonly property bool hiddenTheme: Config.options.halcyon.hiddenThemes.includes(modelData.id)

                themeId: modelData.id
                label: modelData.name
                icon: modelData.icon
                isActive: Config.options.halcyon.theme === modelData.id
                opacity: hiddenTheme ? 0.5 : 1
                menuItems: page.themeMenu(modelData.id)
                menuOpen: page.openThemeMenu === modelData.id
                onApplied: page.applyTheme(modelData.id)
                onMenuToggled: page.toggleThemeMenu(modelData.id)
                onItemChosen: key => page.runThemeAction(modelData.id, key)
            }
        }

        // Auto-apply card, opened from a built-in theme's menu.
        ColumnLayout {
            visible: page.autoEditing !== ""
            Layout.fillWidth: true
            Layout.leftMargin: 10
            spacing: 8

            StyledText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Appearance.colors.colOnLayer1
                font.pixelSize: Appearance.font.pixelSize.small
                text: Translation.tr("Apply %1 at").arg(page.themeName(page.autoEditing))
            }

            RowLayout {
                spacing: 6
                StyledSpinBox {
                    from: 0
                    to: 23
                    value: page.autoHour
                    onValueModified: page.autoHour = value
                }
                StyledText {
                    text: ":"
                    font.pixelSize: Appearance.font.pixelSize.larger
                    color: Appearance.colors.colOnLayer1
                }
                StyledSpinBox {
                    from: 0
                    to: 59
                    stepSize: 5
                    value: page.autoMinute
                    onValueModified: page.autoMinute = value
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 4

                Repeater {
                    model: [
                        Translation.tr("Mon"), Translation.tr("Tue"), Translation.tr("Wed"), Translation.tr("Thu"),
                        Translation.tr("Fri"), Translation.tr("Sat"), Translation.tr("Sun")
                    ]

                    delegate: RippleButton {
                        required property string modelData
                        required property int index
                        readonly property int day: index + 1

                        implicitHeight: 34
                        implicitWidth: 52
                        buttonRadius: Appearance.rounding.small
                        toggled: page.autoDays.includes(day)
                        onClicked: page.toggleAutoDay(day)

                        contentItem: StyledText {
                            anchors.centerIn: parent
                            text: modelData
                            font.pixelSize: Appearance.font.pixelSize.small
                            color: parent.toggled ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1
                        }
                    }
                }
            }

            StyledText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Appearance.colors.colSubtext
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: page.autoDays.length === 0 ? Translation.tr("No days picked: every day.") : Translation.tr("Only on the days picked.")
            }

            RowLayout {
                spacing: 8
                RippleButtonWithIcon {
                    materialIcon: "check"
                    mainText: Translation.tr("Save")
                    onClicked: page.saveAuto()
                }
                RippleButtonWithIcon {
                    visible: page.autoEntry(page.autoEditing) !== null
                    materialIcon: "delete"
                    mainText: Translation.tr("Remove")
                    onClicked: page.removeAuto()
                }
                RippleButtonWithIcon {
                    materialIcon: "close"
                    mainText: Translation.tr("Cancel")
                    onClicked: page.autoEditing = ""
                }
            }
        }

        Repeater {
            model: page.customThemes

            delegate: HalcyonThemeRow {
                required property var modelData

                themeId: modelData.id
                label: modelData.name
                icon: "edit"
                isActive: Config.options.halcyon.theme === modelData.id
                menuItems: page.themeMenu(modelData.id)
                menuOpen: page.openThemeMenu === modelData.id
                onApplied: page.applyTheme(modelData.id)
                onMenuToggled: page.toggleThemeMenu(modelData.id)
                onItemChosen: key => page.runThemeAction(modelData.id, key)
            }
        }

        RippleButtonWithIcon {
            materialIcon: "add"
            mainText: Translation.tr("New custom theme")
            onClicked: newTheme.running = true
            StyledToolTip {
                text: Translation.tr("Makes a copy of the current theme to change. Make as many as you like; they are JSON files in ~/.config/halcyon/themes")
            }
        }

        // Asked after a custom theme is made, until "Do not show again".
        ColumnLayout {
            visible: page.askOpenFor !== ""
            Layout.fillWidth: true
            spacing: 4

            StyledText {
                Layout.fillWidth: true
                Layout.leftMargin: 10
                wrapMode: Text.Wrap
                color: Appearance.colors.colOnLayer1
                font.pixelSize: Appearance.font.pixelSize.small
                text: Translation.tr("What would you like to open?")
            }

            Repeater {
                model: page.openChoices

                delegate: RippleButtonWithIcon {
                    required property var modelData
                    Layout.fillWidth: true
                    materialIcon: modelData.icon
                    mainText: modelData.text
                    onClicked: {
                        modelData.run();
                        page.askOpenFor = "";
                    }
                }
            }
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Applying a theme takes a few seconds. Picking a new wallpaper leaves the theme.\nStar Rail banner art: halcyon banner hsr ~/Pictures/art.png --title \"Name\"")
        }
    }

    ContentSection {
        icon: "auto_awesome"
        title: Translation.tr("Effects")

        ConfigSelectionArray {
            currentValue: Config.options.halcyon.effects
            onSelected: newValue => {
                Config.options.halcyon.effects = newValue;
                page.refresh();
            }
            options: [
                {
                    displayName: Translation.tr("Theme default"),
                    icon: "tune",
                    value: "default"
                },
                {
                    displayName: Translation.tr("Full"),
                    icon: "blur_on",
                    value: "full"
                },
                {
                    displayName: Translation.tr("Light"),
                    icon: "blur_linear",
                    value: "light"
                },
                {
                    displayName: Translation.tr("Off"),
                    icon: "block",
                    value: "off"
                }
            ]
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Full adds screen effects that follow the pointer. Hyprland then redraws every frame, which uses noticeably more GPU; Light keeps the glass look without that cost.")
        }
    }

    ContentSection {
        icon: "mic"
        title: Translation.tr("Assistant")

        ConfigSwitch {
            buttonIcon: "power_settings_new"
            text: Translation.tr("Voice assistant (Super+Shift+Space)")
            checked: Config.options.halcyon.assistant.enable
            onCheckedChanged: {
                Config.options.halcyon.assistant.enable = checked;
                if (!page.ready)
                    return;
                if (checked)
                    Quickshell.execDetached(["bash", "-c", `'${page.assistantTool}' autostart >/dev/null 2>&1 &`]);
                else
                    Quickshell.execDetached([page.assistantTool, "stop"]);
            }
        }

        ContentSubsection {
            title: Translation.tr("AI")
            tooltip: Translation.tr("Auto uses an Anthropic API key if set, then your Claude plan, then Gemini, then a local Ollama model. Keys are shared with the AI sidebar.")
            ConfigSelectionArray {
                currentValue: Config.options.halcyon.assistant.provider
                onSelected: newValue => {
                    Config.options.halcyon.assistant.provider = newValue;
                    page.reloadAssistant();
                }
                options: [
                    { displayName: Translation.tr("Auto"), icon: "auto_mode", value: "auto" },
                    { displayName: Translation.tr("Claude plan"), icon: "workspace_premium", value: "claude-code" },
                    { displayName: Translation.tr("Claude API"), icon: "neurology", value: "claude" },
                    { displayName: "Gemini", icon: "star", value: "gemini" },
                    { displayName: Translation.tr("Ollama (local)"), icon: "computer", value: "ollama" },
                    { displayName: Translation.tr("OpenAI-compatible"), icon: "api", value: "openai" }
                ]
            }
        }

        RowLayout {
            StyledText {
                Layout.leftMargin: 10
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Appearance.colors.colSubtext
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: Translation.tr("No API key? Use your Claude Pro or Max plan: sign in to Claude Code, Anthropic's own app, and the assistant uses it. Counts against your plan's usage.")
            }
            RippleButtonWithIcon {
                buttonRadius: Appearance.rounding.full
                materialIcon: "login"
                mainText: Translation.tr("Sign in with Claude")
                onClicked: {
                    // A terminal, since signing in may ask to install Claude Code
                    // and to paste a code back from the browser.
                    Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' login; read -rp 'Press Enter to close. '"`]);
                }
                StyledToolTip {
                    text: "halcyon assistant login"
                }
            }
        }

        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "record_voice_over"
                text: Translation.tr("\"Hey Halcyon\"")
                checked: Config.options.halcyon.assistant.wakeWord
                onCheckedChanged: {
                    Config.options.halcyon.assistant.wakeWord = checked;
                    page.reloadAssistant();
                }
                StyledToolTip {
                    text: Translation.tr("Listens for the wake phrase all the time, entirely on this computer. Needs: halcyon assistant setup --wake")
                }
            }
            ConfigSwitch {
                buttonIcon: "volume_up"
                text: Translation.tr("Speak replies")
                checked: Config.options.halcyon.assistant.speak
                onCheckedChanged: {
                    Config.options.halcyon.assistant.speak = checked;
                    page.reloadAssistant();
                }
            }
        }

        ConfigSwitch {
            buttonIcon: "touch_app"
            text: Translation.tr("Let it control the desktop")
            checked: Config.options.halcyon.assistant.allowActions
            onCheckedChanged: {
                Config.options.halcyon.assistant.allowActions = checked;
                page.reloadAssistant();
            }
            StyledToolTip {
                text: Translation.tr("Apps, volume, brightness, media, workspaces, themes, screenshots, lock, web search. Nothing else: it can't run commands.")
            }
        }

        ContentSubsection {
            title: Translation.tr("Speech recognition")
            tooltip: Translation.tr("Whisper, running on this computer. Bigger is more accurate but slower. Set up with: halcyon assistant setup")
            ConfigSelectionArray {
                currentValue: Config.options.halcyon.assistant.speechModel
                onSelected: newValue => {
                    Config.options.halcyon.assistant.speechModel = newValue;
                    page.reloadAssistant();
                }
                options: [
                    { displayName: Translation.tr("Fast"), value: "tiny" },
                    { displayName: Translation.tr("Balanced"), value: "base" },
                    { displayName: Translation.tr("Accurate"), value: "small" }
                ]
            }
        }
    }

    ContentSection {
        icon: "auto_awesome"
        title: Translation.tr("Star Rail characters")

        ConfigSwitch {
            buttonIcon: "auto_awesome"
            text: Translation.tr("Star Rail characters on the wallpaper")
            checked: Config.options.halcyon.starRail.enable
            onCheckedChanged: Config.options.halcyon.starRail.enable = checked
            StyledToolTip {
                text: Translation.tr("Off by default. When on, a random character can be picked. Refreshing the list downloads the public index.")
            }
        }

        RowLayout {
            spacing: 8
            RippleButtonWithIcon {
                materialIcon: "shuffle"
                mainText: Translation.tr("Random character")
                enabled: Config.options.halcyon.starRail.enable
                // Runs the Halcyon tool directly, with its arguments as a list.
                onClicked: Quickshell.execDetached([page.tool, "starrail", "next"])
            }
            RippleButtonWithIcon {
                materialIcon: "sync"
                mainText: Translation.tr("Refresh the list")
                enabled: Config.options.halcyon.starRail.enable
                onClicked: Quickshell.execDetached([page.tool, "starrail", "refresh"])
            }
        }
    }

    ContentSection {
        icon: "arrow_selector_tool"
        title: Translation.tr("Cursor")

        ConfigSwitch {
            buttonIcon: "arrow_selector_tool"
            text: Translation.tr("Halcyon Glass cursor")
            checked: Config.options.halcyon.cursor.enable
            onCheckedChanged: {
                Config.options.halcyon.cursor.enable = checked;
                page.applyCursor();
            }
            StyledToolTip {
                text: Translation.tr("Off uses the standard Bibata cursor")
            }
        }

        ContentSubsection {
            title: Translation.tr("Size")
            ConfigSelectionArray {
                currentValue: Config.options.halcyon.cursor.size
                onSelected: newValue => {
                    Config.options.halcyon.cursor.size = newValue;
                    page.applyCursor();
                }
                options: [24, 32, 48, 64].map(size => ({
                    displayName: `${size}px`,
                    value: size
                }))
            }
        }
    }

    ContentSection {
        icon: "water_drop"
        title: Translation.tr("Glass")

        ContentSubsection {
            title: Translation.tr("Screen effects")
            tooltip: Translation.tr("Only at the Full effects level, with a glass theme. Fractured Glass has the lens only: no ripples or edge fringe")

            ConfigRow {
                uniform: true
                ConfigSwitch {
                    buttonIcon: "arrow_selector_tool"
                    text: Translation.tr("Pointer lens")
                    checked: Config.options.halcyon.glass.pointerLens
                    onCheckedChanged: {
                        Config.options.halcyon.glass.pointerLens = checked;
                        page.refresh();
                    }
                }
                ConfigSwitch {
                    buttonIcon: "touch_app"
                    text: Translation.tr("Click ripples")
                    checked: Config.options.halcyon.glass.clickRipples
                    onCheckedChanged: {
                        Config.options.halcyon.glass.clickRipples = checked;
                        page.refresh();
                    }
                }
            }

            ConfigSwitch {
                buttonIcon: "gradient"
                text: Translation.tr("Colour fringe at screen edges")
                checked: Config.options.halcyon.glass.edgeRefraction
                onCheckedChanged: {
                    Config.options.halcyon.glass.edgeRefraction = checked;
                    page.refresh();
                }
            }

            ConfigSlider {
                buttonIcon: "contrast"
                text: Translation.tr("Strength")
                value: Config.options.halcyon.glass.strength
                from: 0
                to: 1
                stopIndicatorValues: [0.5]
                onValueChanged: {
                    Config.options.halcyon.glass.strength = value;
                    page.refresh();
                }
            }

            ContentSubsection {
                title: Translation.tr("Lens shape")
                tooltip: Translation.tr("The arrow cursor's own shape takes the refraction instead of a round lens, and it doesn't bounce. Needs the Pointer lens on, the Full effects level, and a glass theme")

                ConfigSelectionArray {
                    currentValue: Config.options.halcyon.glass.lensShape
                    onSelected: newValue => {
                        Config.options.halcyon.glass.lensShape = newValue;
                        page.refresh();
                    }
                    options: [
                        { displayName: Translation.tr("Round"), value: "round" },
                        { displayName: Translation.tr("Cursor"), value: "cursor" }
                    ]
                }
            }

            ConfigSlider {
                buttonIcon: "circle"
                text: Translation.tr("Lens size")
                value: Config.options.halcyon.glass.lensSize
                usePercentTooltip: false
                from: 30
                to: 300
                stopIndicatorValues: [90]
                onValueChanged: {
                    Config.options.halcyon.glass.lensSize = Math.round(value);
                    page.refresh();
                }
            }

            ConfigSlider {
                buttonIcon: "animation"
                text: Translation.tr("Lens bounce")
                value: Config.options.halcyon.glass.lensBounce
                from: 0
                to: 1
                stopIndicatorValues: [0.8]
                onValueChanged: {
                    Config.options.halcyon.glass.lensBounce = value;
                    page.refresh();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Glass windows")
            tooltip: Translation.tr("For themes with translucent windows (Shattered Glass, Fractured Glass), at Light or Full")

            ConfigSlider {
                buttonIcon: "opacity"
                text: Translation.tr("Focused window")
                value: Config.options.halcyon.glass.windowOpacity
                from: 0.5
                to: 1
                stopIndicatorValues: [0.96]
                onValueChanged: {
                    Config.options.halcyon.glass.windowOpacity = value;
                    page.refresh();
                }
            }

            ConfigSlider {
                buttonIcon: "select_window"
                text: Translation.tr("Other windows")
                value: Config.options.halcyon.glass.inactiveWindowOpacity
                from: 0.5
                to: 1
                stopIndicatorValues: [0.9]
                onValueChanged: {
                    Config.options.halcyon.glass.inactiveWindowOpacity = value;
                    page.refresh();
                }
            }

            ConfigSpinBox {
                icon: "blur_on"
                text: Translation.tr("Frost (blur size)")
                value: Config.options.halcyon.glass.blurSize
                from: 1
                to: 30
                stepSize: 1
                onValueChanged: {
                    Config.options.halcyon.glass.blurSize = value;
                    page.refresh();
                }
            }
        }
    }

    // At the very bottom. Hidden themes come back here, or with `halcyon-theme show all`.
    RippleButtonWithIcon {
        materialIcon: page.showHidden ? "visibility_off" : "visibility"
        mainText: page.showHidden ? Translation.tr("Hide hidden themes") : Translation.tr("Show hidden themes")
        onClicked: page.showHidden = !page.showHidden
        StyledToolTip {
            text: Translation.tr("Hidden themes show dimmed in the theme list. Right-click one and choose Show to bring it back.")
        }
    }
}
