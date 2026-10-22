import QtQuick
import Quickshell
import Quickshell.Io
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

// Settings > Halcyon: themes, effects, glass, Plus Tiles and the config check.
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
        iconThemesProc.running = true;
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

    // Server mode: the service's real state, read back after every change.
    readonly property string serverTool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon_server.py`
    property bool serverActive: false
    property int serverLocks: 0
    Process {
        id: serverStatus
        running: true
        command: [page.serverTool, "status", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const info = JSON.parse(text);
                    page.serverActive = info.active === true;
                    page.serverLocks = (info.inhibitors ?? []).length;
                } catch (e) {
                    page.serverActive = false;
                }
            }
        }
    }
    Timer {
        id: serverRecheck
        interval: 1200
        onTriggered: serverStatus.running = true
    }

    // Turning a browser off takes its theme away; turning one on (or anything else) writes the themes now.
    function browsersChanged(turnedOff) {
        if (!page.ready)
            return;
        const tool = `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon_browsers.py`;
        if (turnedOff.length > 0)
            Quickshell.execDetached([tool, "off", turnedOff]);
        else
            Quickshell.execDetached([tool, "update", "--quiet"]);
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
        { id: "fractured-glass", name: "Fractured Glass", icon: "lens_blur" },
        { id: "red-sun", name: "Red Sun", icon: "wb_twilight" },
        { id: "after-icey", name: "After ICEY", icon: "ac_unit" },
        { id: "manga-ink", name: "Manga Ink", icon: "draw" }
    ]
    // ── When the theme switches: rules, made below and run by halcyon-theme when a theme is applied or turned off ──
    property string ruleTheme: "after-icey"
    property string ruleWhen: "to"
    property string ruleAction: "widget"
    property string ruleTarget: "revolver"
    property string ruleValue: "off"
    property bool ruleRestore: true
    property var iconThemes: []

    Process {
        id: iconThemesProc
        command: [page.tool, "rules", "icons", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    page.iconThemes = (JSON.parse(this.text) ?? {}).themes ?? [];
                } catch (error) {
                    page.iconThemes = [];
                }
            }
        }
    }

    readonly property var ruleThemeChoices: [
        { displayName: Translation.tr("Any theme"), value: "*" },
        { displayName: Translation.tr("No theme (off)"), value: "off" },
        ...page.builtinThemes.map(t => ({ displayName: t.name, value: t.id })),
        ...page.customThemes.map(t => ({ displayName: t.name, value: t.id }))
    ]
    readonly property var ruleActionChoices: [
        { displayName: Translation.tr("Turn a desktop widget on or off"), value: "widget" },
        { displayName: Translation.tr("Change the icon theme"), value: "icons" },
        { displayName: Translation.tr("Set the effects level"), value: "effects" },
        { displayName: Translation.tr("Change where new windows open"), value: "placement" },
        { displayName: Translation.tr("Change a shell setting"), value: "setting" },
        { displayName: Translation.tr("Run a command"), value: "command" }
    ]
    readonly property var ruleWidgetChoices: [
        { displayName: Translation.tr("Revolver"), value: "revolver" },
        { displayName: Translation.tr("Clock"), value: "clock" },
        { displayName: Translation.tr("Weather"), value: "weather" },
        { displayName: Translation.tr("Visualizer"), value: "visualizer" },
        { displayName: Translation.tr("System"), value: "system" },
        { displayName: Translation.tr("Now playing"), value: "nowPlaying" },
        { displayName: Translation.tr("Lyrics"), value: "lyrics" }
    ]
    readonly property var ruleValueChoices: ({
        "widget": [{ displayName: Translation.tr("Off"), value: "off" }, { displayName: Translation.tr("On"), value: "on" }],
        "effects": [{ displayName: Translation.tr("Theme default"), value: "default" }, { displayName: Translation.tr("Full"), value: "full" },
                    { displayName: Translation.tr("Light"), value: "light" }, { displayName: Translation.tr("Off"), value: "off" }],
        "placement": [{ displayName: Translation.tr("Golden ratio"), value: "golden" }, { displayName: Translation.tr("Golden ratio plus"), value: "golden-plus" },
                      { displayName: Translation.tr("Golden ratio plus (dwindle)"), value: "golden-plus-dwindle" },
                      { displayName: Translation.tr("Halves, by the pointer"), value: "cursor" }, { displayName: Translation.tr("Stacked"), value: "stacked" },
                      { displayName: Translation.tr("Side by side"), value: "side-by-side" }, { displayName: Translation.tr("Mondrian"), value: "mondrian" }],
        "icons": page.iconThemes.map(t => ({ displayName: t.name, value: t.id }))
    })

    function choiceName(list, value) {
        return (list.find(item => item.value === value) ?? { displayName: value }).displayName;
    }

    function setRuleAction(action) {
        page.ruleAction = action;
        page.ruleTarget = action === "widget" ? "revolver" : "";
        const values = page.ruleValueChoices[action];
        page.ruleValue = values && values.length > 0 ? values[0].value : "";
        if (action === "icons")
            iconThemesProc.running = true;
    }

    function ruleText(rule) {
        const theme = page.choiceName(page.ruleThemeChoices, rule.theme);
        const head = rule.when === "from" ? Translation.tr("Leaving %1:").arg(theme) : Translation.tr("Switching to %1:").arg(theme);
        let what = "";
        switch (rule.action) {
        case "widget": what = Translation.tr("%1 %2").arg(page.choiceName(page.ruleWidgetChoices, rule.target)).arg(rule.value === "on" ? Translation.tr("on") : Translation.tr("off")); break;
        case "icons": what = Translation.tr("icons: %1").arg(rule.value); break;
        case "effects": what = Translation.tr("effects: %1").arg(page.choiceName(page.ruleValueChoices.effects, rule.value)); break;
        case "placement": what = Translation.tr("new windows: %1").arg(page.choiceName(page.ruleValueChoices.placement, rule.value)); break;
        case "setting": what = `${rule.target} = ${rule.value}`; break;
        case "command": what = Translation.tr("run %1").arg(rule.value); break;
        }
        return `${head} ${what}` + (rule.restore && rule.when === "to" ? Translation.tr(" (put back after)") : "");
    }

    readonly property bool ruleCanAdd: page.ruleValue.trim() !== "" && (page.ruleAction !== "setting" || /^[A-Za-z][A-Za-z0-9]*(\.[A-Za-z][A-Za-z0-9]*)*$/.test(page.ruleTarget))

    function addRule() {
        if (!page.ruleCanAdd)
            return;
        const rule = { theme: page.ruleTheme, when: page.ruleWhen, action: page.ruleAction, target: page.ruleTarget,
                       value: page.ruleValue.trim(), restore: page.ruleWhen === "to" && page.ruleAction !== "command" && page.ruleRestore };
        Config.options.halcyon.switchRules = Config.options.halcyon.switchRules.concat([rule]);
    }

    function removeRule(index) {
        const rules = Config.options.halcyon.switchRules.slice();
        rules.splice(index, 1);
        Config.options.halcyon.switchRules = rules;
    }

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
    property bool autoUseTime: true
    property string autoTimeKind: "clock" // "clock", "sunset" or "sunrise"
    property int autoOffset: 0 // Minutes after (+) or before (-) sunset or sunrise
    // Today's sunrise and sunset from `halcyon-theme auto sun`: { location, source, sunrise, sunset }
    property var sunInfo: ({})
    property string autoWeather: "" // "" for any weather, else a group from halcyon-theme
    readonly property bool autoCanSave: page.autoUseTime || page.autoWeather !== ""
    readonly property var autoWeatherChoices: [
        { value: "", text: Translation.tr("Any") },
        { value: "clear", text: Translation.tr("Clear") },
        { value: "cloudy", text: Translation.tr("Cloudy") },
        { value: "rain", text: Translation.tr("Rain") },
        { value: "snow", text: Translation.tr("Snow") },
        { value: "storm", text: Translation.tr("Storm") },
        { value: "fog", text: Translation.tr("Fog") }
    ]

    function autoEntry(id) {
        return Config.options.halcyon.autoApply.find(entry => entry.theme === id) ?? null;
    }

    function themeName(id) {
        return page.builtinThemes.find(theme => theme.id === id)?.name ?? id;
    }

    function openAuto(id) {
        const entry = page.autoEntry(id);
        const time = entry?.time ?? "";
        const sun = /^(sunrise|sunset)(?:([+-])([0-9]{1,3}))?$/.exec(time);
        const clock = /^([0-9]{2}):([0-9]{2})$/.exec(time);
        page.autoTimeKind = sun ? sun[1] : "clock";
        page.autoOffset = sun && sun[3] ? parseInt(sun[3]) * (sun[2] === "-" ? -1 : 1) : 0;
        page.autoHour = clock ? parseInt(clock[1]) : 8;
        page.autoMinute = clock ? parseInt(clock[2]) : 0;
        sunProc.running = true;
        page.autoDays = entry?.days ? entry.days.slice() : [];
        page.autoUseTime = entry ? "time" in entry : true;
        page.autoWeather = entry?.weather ?? "";
        page.autoEditing = id;
    }

    function toggleAutoDay(day) {
        page.autoDays = page.autoDays.includes(day)
            ? page.autoDays.filter(d => d !== day)
            : page.autoDays.concat([day]).sort((a, b) => a - b);
    }

    function saveAuto() {
        if (!page.autoCanSave)
            return;
        // Only the conditions that are on are saved. Days narrow the time or the weather.
        const entry = { theme: page.autoEditing };
        if (page.autoUseTime)
            entry.time = page.autoTimeKind === "clock"
                ? `${String(page.autoHour).padStart(2, "0")}:${String(page.autoMinute).padStart(2, "0")}`
                : page.autoTimeKind + (page.autoOffset === 0 ? "" : (page.autoOffset > 0 ? "+" : "-") + Math.abs(page.autoOffset));
        if (page.autoDays.length > 0)
            entry.days = page.autoDays.slice().sort((a, b) => a - b);
        if (page.autoWeather !== "")
            entry.weather = page.autoWeather;
        const others = Config.options.halcyon.autoApply.filter(saved => saved.theme !== page.autoEditing);
        Config.options.halcyon.autoApply = others.concat([entry]);
        page.autoEditing = "";
    }

    // "19:42" moved by the offset, for the "today at" line under a sun time.
    function shiftedTime(hhmm, minutes) {
        if (!hhmm)
            return "";
        const total = (parseInt(hhmm.slice(0, 2)) * 60 + parseInt(hhmm.slice(3, 5)) + minutes + 1440) % 1440;
        return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
    }

    function sunLine() {
        if (!page.sunInfo.location)
            return Translation.tr("No location yet. Type one below, or turn on the bar's weather, which knows where you are.");
        const today = page.sunInfo[page.autoTimeKind];
        if (!today)
            return Translation.tr("The sun doesn't %1 here today, so this won't apply today.").arg(page.autoTimeKind === "sunset" ? Translation.tr("set") : Translation.tr("rise"));
        const where = page.sunInfo.source === "settings" ? Translation.tr("your location") : Translation.tr("the weather location");
        return Translation.tr("Today at %1, from %2.").arg(page.shiftedTime(today, page.autoOffset)).arg(where);
    }

    Process {
        id: sunProc
        command: [page.tool, "auto", "sun"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    page.sunInfo = JSON.parse(this.text) ?? {};
                } catch (error) {
                    page.sunInfo = {};
                }
            }
        }
    }

    Timer {
        id: sunRefresh
        // After Config has written the new location.
        interval: 900
        onTriggered: sunProc.running = true
    }

    function removeAuto() {
        Config.options.halcyon.autoApply = Config.options.halcyon.autoApply.filter(entry => entry.theme !== page.autoEditing);
        page.autoEditing = "";
    }

    function themeMenu(id) {
        if (page.builtinThemes.some(theme => theme.id === id)) {
            const hidden = Config.options.halcyon.hiddenThemes.includes(id);
            return [
                { key: "auto", text: Translation.tr("Auto-apply"), icon: "schedule" },
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

            ConfigSwitch {
                buttonIcon: "schedule"
                text: Translation.tr("At a time")
                checked: page.autoUseTime
                onCheckedChanged: page.autoUseTime = checked
            }

            ConfigSelectionArray {
                visible: page.autoUseTime
                currentValue: page.autoTimeKind
                onSelected: newValue => page.autoTimeKind = newValue
                options: [
                    { displayName: Translation.tr("Clock time"), icon: "schedule", value: "clock" },
                    { displayName: Translation.tr("Sunset"), icon: "wb_twilight", value: "sunset" },
                    { displayName: Translation.tr("Sunrise"), icon: "wb_sunny", value: "sunrise" }
                ]
            }

            ColumnLayout {
                visible: page.autoUseTime && page.autoTimeKind !== "clock"
                Layout.fillWidth: true
                spacing: 6

                RowLayout {
                    spacing: 8
                    StyledText {
                        text: Translation.tr("Minutes after (+) or before (−)")
                        color: Appearance.colors.colOnLayer1
                        font.pixelSize: Appearance.font.pixelSize.small
                    }
                    StyledSpinBox {
                        from: -180
                        to: 180
                        stepSize: 5
                        value: page.autoOffset
                        onValueModified: page.autoOffset = value
                    }
                }

                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.smallie
                    text: page.sunLine()
                }

                MaterialTextArea {
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("Location as latitude, longitude (e.g. 51.51, -0.13). Empty: the weather location")
                    text: Config.options.halcyon.location
                    onTextChanged: {
                        if (text.trim() === Config.options.halcyon.location)
                            return;
                        Config.options.halcyon.location = text.trim();
                        sunRefresh.restart();
                    }
                }
            }

            RowLayout {
                visible: page.autoUseTime && page.autoTimeKind === "clock"
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

            Flow {
                Layout.fillWidth: true
                spacing: 4

                Repeater {
                    model: page.autoWeatherChoices

                    delegate: RippleButton {
                        required property var modelData

                        implicitHeight: 34
                        buttonRadius: Appearance.rounding.small
                        toggled: page.autoWeather === modelData.value
                        onClicked: page.autoWeather = modelData.value

                        contentItem: StyledText {
                            anchors.centerIn: parent
                            text: modelData.text
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
                text: Translation.tr("Weather uses what the bar's Weather fetches, so it needs Weather turned on there. The theme applies when the weather changes to this.")
            }

            StyledText {
                visible: !page.autoCanSave
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Appearance.colors.colError
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: Translation.tr("Pick a time, a weather, or both.")
            }

            RowLayout {
                spacing: 8
                RippleButtonWithIcon {
                    materialIcon: "check"
                    mainText: Translation.tr("Save")
                    enabled: page.autoCanSave
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
        icon: "swap_horiz"
        title: Translation.tr("When the theme switches")

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Changes made each time the theme switches to, or away from, a theme: the revolver off for After ICEY, other icons for Red Sun... They run in this order, when a theme is applied or turned off.")
        }

        Repeater {
            model: Config.options.halcyon.switchRules

            delegate: Rectangle {
                id: ruleRow
                required property var modelData
                required property int index
                Layout.fillWidth: true
                implicitHeight: ruleRowLayout.implicitHeight + 12
                radius: Appearance.rounding.small
                color: Appearance.colors.colLayer2

                RowLayout {
                    id: ruleRowLayout
                    anchors.fill: parent
                    anchors.margins: 6
                    anchors.leftMargin: 12
                    MaterialSymbol {
                        text: ruleRow.modelData.when === "from" ? "logout" : "login"
                        iconSize: Appearance.font.pixelSize.larger
                        color: Appearance.colors.colPrimary
                    }
                    StyledText {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        text: page.ruleText(ruleRow.modelData)
                    }
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "delete"
                        mainText: Translation.tr("Remove")
                        onClicked: page.removeRule(ruleRow.index)
                    }
                }
            }
        }

        StyledText {
            visible: Config.options.halcyon.switchRules.length === 0
            Layout.leftMargin: 10
            color: Appearance.colors.colSubtext
            text: Translation.tr("No rules yet.")
        }

        ContentSubsection {
            title: Translation.tr("Add a rule")

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    StyledComboBox {
                        buttonIcon: "palette"
                        textRole: "displayName"
                        model: page.ruleThemeChoices
                        currentIndex: Math.max(0, model.findIndex(item => item.value === page.ruleTheme))
                        onActivated: index => page.ruleTheme = model[index].value
                    }
                    StyledComboBox {
                        buttonIcon: page.ruleWhen === "from" ? "logout" : "login"
                        textRole: "displayName"
                        model: [{ displayName: Translation.tr("Switching to it"), value: "to" },
                                { displayName: Translation.tr("Switching away from it"), value: "from" }]
                        currentIndex: page.ruleWhen === "from" ? 1 : 0
                        onActivated: index => page.ruleWhen = model[index].value
                    }
                }

                StyledComboBox {
                    buttonIcon: "bolt"
                    textRole: "displayName"
                    model: page.ruleActionChoices
                    currentIndex: Math.max(0, model.findIndex(item => item.value === page.ruleAction))
                    onActivated: index => page.setRuleAction(model[index].value)
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    StyledComboBox {
                        visible: page.ruleAction === "widget"
                        buttonIcon: "widgets"
                        textRole: "displayName"
                        model: page.ruleWidgetChoices
                        currentIndex: Math.max(0, model.findIndex(item => item.value === page.ruleTarget))
                        onActivated: index => page.ruleTarget = model[index].value
                    }
                    StyledComboBox {
                        visible: (page.ruleValueChoices[page.ruleAction] ?? []).length > 0
                        buttonIcon: "tune"
                        textRole: "displayName"
                        model: page.ruleValueChoices[page.ruleAction] ?? []
                        currentIndex: Math.max(0, model.findIndex(item => item.value === page.ruleValue))
                        onActivated: index => page.ruleValue = model[index].value
                    }
                    MaterialTextArea {
                        visible: page.ruleAction === "setting"
                        Layout.fillWidth: true
                        placeholderText: Translation.tr("Setting, e.g. bar.vertical")
                        text: page.ruleTarget
                        onTextChanged: page.ruleTarget = text.trim()
                    }
                    MaterialTextArea {
                        visible: page.ruleAction === "setting" || page.ruleAction === "command"
                        Layout.fillWidth: true
                        placeholderText: page.ruleAction === "command" ? Translation.tr("Command, e.g. notify-send hello") : Translation.tr("Value, e.g. true")
                        text: page.ruleValue
                        onTextChanged: page.ruleValue = text
                    }
                }

                StyledText {
                    visible: page.ruleAction === "icons" && page.iconThemes.length === 0
                    Layout.leftMargin: 10
                    color: Appearance.colors.colSubtext
                    text: Translation.tr("No icon themes found. Install one (papirus-icon-theme, for one), then come back.")
                }

                ConfigSwitch {
                    visible: page.ruleWhen === "to" && page.ruleAction !== "command"
                    buttonIcon: "undo"
                    text: Translation.tr("Put it back when switching away")
                    checked: page.ruleRestore
                    onCheckedChanged: page.ruleRestore = checked
                }

                RowLayout {
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "add"
                        mainText: Translation.tr("Add rule")
                        enabled: page.ruleCanAdd
                        opacity: enabled ? 1 : 0.5
                        onClicked: page.addRule()
                    }
                }
            }
        }
    }

    ContentSection {
        icon: "dns"
        title: Translation.tr("Server mode")

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("For a computer that serves something: it never suspends (idle, lid, or the suspend key), and the screen never locks or blanks by itself. Stays on after a restart until you stop it.")
        }

        RowLayout {
            spacing: 10
            RippleButtonWithIcon {
                buttonRadius: Appearance.rounding.full
                toggled: page.serverActive
                colBackgroundToggled: Appearance.colors.colPrimaryContainer
                colBackgroundToggledHover: Appearance.colors.colPrimaryContainerHover
                materialIcon: page.serverActive ? "stop_circle" : "play_circle"
                mainText: page.serverActive ? Translation.tr("Stop server mode") : Translation.tr("Start server mode")
                onClicked: {
                    const turnOn = !page.serverActive;
                    // The tool saves the choice (halcyon.serverMode) itself, so there is one writer.
                    page.serverActive = turnOn; // at once; the check below confirms it
                    Quickshell.execDetached([page.serverTool, turnOn ? "on" : "off"]);
                    serverRecheck.restart();
                }
                StyledToolTip {
                    text: "halcyon server on | off"
                }
            }
            StyledText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: page.serverActive ? Appearance.colors.colPrimary : Appearance.colors.colSubtext
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: page.serverActive
                    ? Translation.tr("On: no suspend, no automatic lock")
                    : Translation.tr("Off: locking, blanking and suspend as usual")
            }
        }
    }

    ContentSection {
        icon: "sports_esports"
        title: Translation.tr("Games")

        ConfigSwitch {
            buttonIcon: "mouse"
            text: Translation.tr("Games keep the keyboard when the pointer leaves them")
            checked: Config.options.halcyon.gameFocus
            onCheckedChanged: {
                if (Config.options.halcyon.gameFocus === checked)
                    return;
                Config.options.halcyon.gameFocus = checked;
                Quickshell.execDetached([page.tool, "games", "focus", checked ? "on" : "off"]);
            }
            StyledToolTip {
                text: Translation.tr("Most games pause or stop drawing when they lose focus, so they look frozen when the pointer slips onto another monitor or the bar. With this on, focus follows clicks while a game is focused: click another window, or use a keybind, to leave it. Steam games, and windows that say they are games, count.")
            }
        }
    }

    ContentSection {
        icon: "brush"
        title: Translation.tr("On the screen")

        ContentSubsection {
            title: Translation.tr("Volume and brightness popup")
            tooltip: Translation.tr("The popup that shows when you change the volume, the microphone or the brightness with the keys. Avizo draws its own, in the theme's colours and shape. It has to be installed (yay -S avizo).")

            ConfigSelectionArray {
                currentValue: Config.options.osd.provider ?? "shell"
                onSelected: newValue => {
                    if ((Config.options.osd.provider ?? "shell") === newValue)
                        return;
                    Config.options.osd.provider = newValue;
                    Quickshell.execDetached([page.tool, "osd", newValue]);
                }
                options: [
                    { displayName: Translation.tr("The shell's"), icon: "dashboard", value: "shell" },
                    { displayName: Translation.tr("Avizo"), icon: "volume_up", value: "avizo" }
                ]
            }
        }

        ConfigSwitch {
            buttonIcon: "draw"
            text: Translation.tr("Drawing overlay (Wayscriber) at login")
            checked: Config.options.halcyon.annotate.enable
            onCheckedChanged: {
                if (Config.options.halcyon.annotate.enable === checked)
                    return;
                Config.options.halcyon.annotate.enable = checked;
                Quickshell.execDetached([page.tool, "annotate", checked ? "on" : "off"]);
            }
            StyledToolTip {
                text: Translation.tr("Draw on top of anything with a pen, shapes, text and a whiteboard, like ZoomIt. Super + Shift + D shows and hides it. Wayscriber (called Hyprmarker before it was renamed) has to be installed (yay -S wayscriber-bin). Its pen colours follow the theme.")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            spacing: 8

            RippleButtonWithIcon {
                materialIcon: "draw"
                mainText: Translation.tr("Draw now")
                onClicked: Quickshell.execDetached([page.tool, "annotate", "toggle"])
            }
            RippleButtonWithIcon {
                materialIcon: "notifications"
                mainText: Translation.tr("Test the popup")
                visible: (Config.options.osd.provider ?? "shell") === "avizo"
                onClicked: Quickshell.execDetached([page.tool, "osd", "test"])
            }
        }
    }

    ContentSection {
        icon: "web"
        title: Translation.tr("Browsers")

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Firefox and Chromium take the desktop's colours, from a Halcyon theme or the wallpaper. They pick up new colours when they next start. Google Chrome: load ~/.local/share/halcyon/chromium-theme once in chrome://extensions (Developer mode, Load unpacked).")
        }

        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "public"
                text: "Firefox"
                checked: Config.options.halcyon.browsers.firefox
                onCheckedChanged: {
                    if (Config.options.halcyon.browsers.firefox === checked)
                        return;
                    Config.options.halcyon.browsers.firefox = checked;
                    page.browsersChanged(checked ? "" : "firefox");
                }
                StyledToolTip {
                    text: Translation.tr("Firefox, LibreWolf, Zen, Floorp and Waterfox: every profile")
                }
            }
            ConfigSwitch {
                buttonIcon: "language"
                text: "Chromium"
                checked: Config.options.halcyon.browsers.chromium
                onCheckedChanged: {
                    if (Config.options.halcyon.browsers.chromium === checked)
                        return;
                    Config.options.halcyon.browsers.chromium = checked;
                    page.browsersChanged(checked ? "" : "chromium");
                }
                StyledToolTip {
                    text: Translation.tr("Chromium and Brave load the theme by themselves; Chrome needs it loaded once")
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Firefox: other sites")
            tooltip: Translation.tr("How far the theme reaches into web pages. Accents colour what a page leaves to the browser: scrollbars, selected text, checkboxes and sliders, the caret and the focus ring, and sites with a dark mode use it when the theme is dark. A site's own design still wins. Theme colours is Firefox's \"override the colours specified by the page\" set to Always: every site gets the theme's background, text and link colours, but loses the colours of its own design. Restart Firefox to see a change.")

            ConfigSelectionArray {
                currentValue: Config.options.halcyon.browsers.sites ?? "accents"
                onSelected: newValue => {
                    if ((Config.options.halcyon.browsers.sites ?? "accents") === newValue)
                        return;
                    Config.options.halcyon.browsers.sites = newValue;
                    if (page.ready)
                        Quickshell.execDetached([`${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon_browsers.py`, "sites", newValue, "--quiet"]);
                }
                options: [
                    { displayName: Translation.tr("Leave alone"), icon: "block", value: "off" },
                    { displayName: Translation.tr("Accents"), icon: "palette", value: "accents" },
                    { displayName: Translation.tr("Theme colours"), icon: "format_color_fill", value: "override" }
                ]
            }
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
            tooltip: Translation.tr("Auto uses an Anthropic API key if set, then your Claude plan, then Gemini, then a T1 server with a key, then whichever of Ollama, LM Studio and HyperNix is on this computer. Keys are shared with the AI sidebar.")
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
                    { displayName: Translation.tr("LM Studio (local)"), icon: "dns", value: "lmstudio" },
                    { displayName: Translation.tr("HyperNix (local)"), icon: "hexagon", value: "hypernix" },
                    { displayName: Translation.tr("T1 server"), icon: "hub", value: "t1" },
                    { displayName: Translation.tr("OpenAI-compatible"), icon: "api", value: "openai" }
                ]
            }
        }

        StyledText {
            visible: ["lmstudio", "hypernix"].includes(Config.options.halcyon.assistant.provider)
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Config.options.halcyon.assistant.provider === "lmstudio"
                ? Translation.tr("Halcyon starts LM Studio's server and loads a model when you ask something (needs LM Studio's `lms` command). Model: empty uses the loaded one.")
                : Translation.tr("Halcyon starts HyperNix's runtime (`hnx runtime serve`) with a model from ~/.hypernix/models, sub-bit models included. Model: empty uses the newest.")
        }

        MaterialTextArea {
            visible: ["lmstudio", "hypernix", "t1", "ollama", "openai"].includes(Config.options.halcyon.assistant.provider)
            Layout.fillWidth: true
            placeholderText: Translation.tr("Model (empty: the provider's default)")
            text: Config.options.halcyon.assistant.model
            onTextChanged: {
                if (text.trim() === Config.options.halcyon.assistant.model)
                    return;
                Config.options.halcyon.assistant.model = text.trim();
                page.reloadAssistant();
            }
        }

        MaterialTextArea {
            visible: Config.options.halcyon.assistant.provider === "t1" || Config.options.halcyon.assistant.provider === "auto"
            Layout.fillWidth: true
            placeholderText: Translation.tr("T1 server, e.g. http://127.0.0.1:8000 (key: /key in the AI sidebar on a T1 model, or halcyon assistant key t1)")
            text: Config.options.halcyon.assistant.t1Server
            onTextChanged: {
                if (text.trim() === Config.options.halcyon.assistant.t1Server)
                    return;
                Config.options.halcyon.assistant.t1Server = text.trim();
                page.reloadAssistant();
                Ai.refreshHalcyonModels();
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

        ContentSubsection {
            visible: Config.options.halcyon.assistant.speak
            title: Translation.tr("Voice")
            tooltip: Translation.tr("Auto: your own command if one is set, else Kokoro if it is set up, else Piper, else an AI voice if a Gemini or OpenAI key is stored, else espeak-ng. If the chosen voice fails, the next one speaks instead")

            ConfigSelectionArray {
                currentValue: Config.options.halcyon.assistant.voice
                onSelected: newValue => {
                    Config.options.halcyon.assistant.voice = newValue;
                    page.reloadAssistant();
                }
                options: [
                    { displayName: Translation.tr("Auto"), icon: "auto_mode", value: "auto" },
                    { displayName: Translation.tr("Piper"), icon: "record_voice_over", value: "piper" },
                    { displayName: Translation.tr("Kokoro"), icon: "graphic_eq", value: "kokoro" },
                    { displayName: Translation.tr("Your command"), icon: "terminal", value: "command" },
                    { displayName: Translation.tr("Fish S2 Pro"), icon: "set_meal", value: "fish" },
                    { displayName: Translation.tr("Drama 3 small"), icon: "theater_comedy", value: "drama3" },
                    { displayName: Translation.tr("AI voice"), icon: "neurology", value: "ai" },
                    { displayName: Translation.tr("eSpeak"), icon: "robot_2", value: "espeak" },
                    { displayName: Translation.tr("System"), icon: "settings_voice", value: "system" }
                ]
            }

            ConfigSelectionArray {
                visible: Config.options.halcyon.assistant.voice === "ai" || Config.options.halcyon.assistant.voice === "auto"
                currentValue: Config.options.halcyon.assistant.aiVoiceProvider
                onSelected: newValue => {
                    Config.options.halcyon.assistant.aiVoiceProvider = newValue;
                    page.reloadAssistant();
                }
                options: [
                    { displayName: Translation.tr("Whichever key is stored"), icon: "key", value: "auto" },
                    { displayName: "Gemini", icon: "neurology", value: "gemini" },
                    { displayName: Translation.tr("OpenAI-compatible"), icon: "api", value: "openai" }
                ]
            }

            MaterialTextArea {
                visible: Config.options.halcyon.assistant.voice === "ai" || Config.options.halcyon.assistant.voice === "auto"
                Layout.fillWidth: true
                placeholderText: Translation.tr("AI voice name (empty: Kore on Gemini, alloy on OpenAI)")
                text: Config.options.halcyon.assistant.aiVoice
                onTextChanged: {
                    if (text.trim() === Config.options.halcyon.assistant.aiVoice)
                        return;
                    Config.options.halcyon.assistant.aiVoice = text.trim();
                    page.reloadAssistant();
                }
            }

            MaterialTextArea {
                visible: Config.options.halcyon.assistant.aiVoiceProvider === "openai"
                Layout.fillWidth: true
                placeholderText: Translation.tr("Voice server (empty: OpenAI). A local one needs no key, e.g. Kokoro: http://127.0.0.1:8880/v1")
                text: Config.options.halcyon.assistant.aiVoiceEndpoint
                onTextChanged: {
                    if (text.trim() === Config.options.halcyon.assistant.aiVoiceEndpoint)
                        return;
                    Config.options.halcyon.assistant.aiVoiceEndpoint = text.trim();
                    page.reloadAssistant();
                }
            }

            // Kokoro: a local voice model, set up once in a terminal (it downloads ~340 MB).
            ColumnLayout {
                visible: Config.options.halcyon.assistant.voice === "kokoro" || Config.options.halcyon.assistant.voice === "auto"
                Layout.fillWidth: true
                spacing: 6
                MaterialTextArea {
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("Kokoro voice (empty: af_heart). af_ and am_ American, bf_ and bm_ British, ef_ Spanish, ff_ French, jf_ Japanese, zf_ Chinese...")
                    text: Config.options.halcyon.assistant.kokoroVoice
                    onTextChanged: {
                        if (text.trim() === Config.options.halcyon.assistant.kokoroVoice)
                            return;
                        Config.options.halcyon.assistant.kokoroVoice = text.trim();
                        page.reloadAssistant();
                    }
                }
                RowLayout {
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "download"
                        mainText: Translation.tr("Set up Kokoro")
                        onClicked: Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' setup --kokoro; read -rp 'Press Enter to close. '"`])
                        StyledToolTip {
                            text: "halcyon assistant setup --kokoro"
                        }
                    }
                }
            }

            // A voice program of your own.
            MaterialTextArea {
                visible: Config.options.halcyon.assistant.voice === "command" || Config.options.halcyon.assistant.voice === "auto"
                Layout.fillWidth: true
                placeholderText: Translation.tr("Your voice command: gets the text on stdin, plays it or writes a WAV to stdout. E.g. tts --text-stdin --out_path /dev/stdout")
                text: Config.options.halcyon.assistant.ttsCommand
                onTextChanged: {
                    if (text.trim() === Config.options.halcyon.assistant.ttsCommand)
                        return;
                    Config.options.halcyon.assistant.ttsCommand = text.trim();
                    page.reloadAssistant();
                }
            }

            // Big local voice models on servers of their own: Fish Audio S2 Pro and drama3-small.
            ColumnLayout {
                visible: Config.options.halcyon.assistant.voice === "fish"
                Layout.fillWidth: true
                spacing: 6
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.smallie
                    text: Translation.tr("Fish Audio S2 Pro: 80+ languages, and [tags] in the text for tone ([whisper], [laughing], [excited]). About 11 GB; wants a GPU with 12 GB. Its server starts the first time it speaks and loads for a minute or two. Non-commercial use only; the weights are gated: accept the terms at huggingface.co/fishaudio/s2-pro and sign in first.")
                }
                MaterialTextArea {
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("A voice saved on the Fish Speech server (its reference id); empty: its own")
                    text: Config.options.halcyon.assistant.fishReference
                    onTextChanged: {
                        if (text.trim() === Config.options.halcyon.assistant.fishReference)
                            return;
                        Config.options.halcyon.assistant.fishReference = text.trim();
                        page.reloadAssistant();
                    }
                }
                RowLayout {
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "download"
                        mainText: Translation.tr("Set up S2 Pro")
                        onClicked: Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' setup --fish-s2; read -rp 'Press Enter to close. '"`])
                    }
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "stop_circle"
                        mainText: Translation.tr("Free the GPU")
                        onClicked: Quickshell.execDetached([page.assistantTool, "voice-server", "fish", "stop"])
                    }
                }
            }
            ColumnLayout {
                visible: Config.options.halcyon.assistant.voice === "drama3"
                Layout.fillWidth: true
                spacing: 6
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.smallie
                    text: Translation.tr("drama3-small: a compressed Fish Audio Drama 3, Japanese and English, that speaks in the voice of a 10-30 s recording. About 10 GB; needs an NVIDIA GPU with 12 GB and the CUDA toolkit to build. Only clone a voice with its owner's consent.")
                }
                MaterialTextArea {
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("The recording to clone (a WAV file), e.g. ~/voice.wav")
                    text: Config.options.halcyon.assistant.drama3Reference
                    onTextChanged: {
                        if (text.trim() === Config.options.halcyon.assistant.drama3Reference)
                            return;
                        Config.options.halcyon.assistant.drama3Reference = text.trim();
                        page.reloadAssistant();
                    }
                }
                MaterialTextArea {
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("What the recording says, word for word")
                    text: Config.options.halcyon.assistant.drama3ReferenceText
                    onTextChanged: {
                        if (text.trim() === Config.options.halcyon.assistant.drama3ReferenceText)
                            return;
                        Config.options.halcyon.assistant.drama3ReferenceText = text.trim();
                        page.reloadAssistant();
                    }
                }
                RowLayout {
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "build"
                        mainText: Translation.tr("Set up Drama 3 small")
                        onClicked: Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' setup --drama3; read -rp 'Press Enter to close. '"`])
                    }
                    RippleButtonWithIcon {
                        buttonRadius: Appearance.rounding.full
                        materialIcon: "stop_circle"
                        mainText: Translation.tr("Free the GPU")
                        onClicked: Quickshell.execDetached([page.assistantTool, "voice-server", "drama3", "stop"])
                    }
                }
            }

            // Which Piper voice: one here (built-in, downloaded, from the AUR or your own), or one to add from
            // Hugging Face or the AUR. Everything goes through `halcyon assistant voices` and `voice ...`.
            ColumnLayout {
                id: piperPicker
                visible: Config.options.halcyon.assistant.voice === "auto" || Config.options.halcyon.assistant.voice === "piper"
                Layout.fillWidth: true
                spacing: 6

                property var voices: ({ "installed": [], "huggingface": [], "aur": [], "current": "", "errors": [] })
                property string source: "installed"
                property string filter: ""
                property string status: ""
                property bool loaded: false
                readonly property int shown: 40

                function refresh() {
                    voicesProc.running = false;
                    voicesProc.running = true;
                }
                function act(args, message) {
                    piperPicker.status = message;
                    voiceAction.running = false;
                    voiceAction.command = [page.assistantTool, "voice"].concat(args);
                    voiceAction.running = true;
                }
                function matches(entry) {
                    const words = piperPicker.filter.toLowerCase().split(/\s+/).filter(w => w.length > 0);
                    const text = [entry.key, entry.name, entry.language, entry.languageName, entry.country, entry.quality, entry.description].join(" ").toLowerCase();
                    return words.every(w => text.includes(w));
                }
                readonly property var list: (piperPicker.voices[piperPicker.source] ?? []).filter(e => piperPicker.matches(e))
                readonly property var currentVoice: (piperPicker.voices.installed ?? []).find(v => v.key === piperPicker.voices.current) ?? null

                onVisibleChanged: if (visible && !loaded) refresh()
                Component.onCompleted: if (visible) refresh()

                Process {
                    id: voicesProc
                    command: [page.assistantTool, "voices", "--json", "--all"]
                    stdout: StdioCollector {
                        onStreamFinished: {
                            try {
                                piperPicker.voices = JSON.parse(this.text);
                                // Nothing here yet: show what can be downloaded.
                                if (!piperPicker.loaded && (piperPicker.voices.installed ?? []).length === 0)
                                    piperPicker.source = "huggingface";
                                piperPicker.loaded = true;
                                if ((piperPicker.voices.errors ?? []).length > 0)
                                    piperPicker.status = piperPicker.voices.errors.join("\n");
                            } catch (e) {
                                piperPicker.status = Translation.tr("Couldn't list the voices: run halcyon assistant voices --all in a terminal");
                            }
                        }
                    }
                }
                Process {
                    id: voiceAction
                    // Download progress is written as one line rewritten in place (\r)
                    stdout: SplitParser {
                        splitMarker: "\r"
                        onRead: data => {
                            const line = data.trim().split("\n").pop();
                            if (line.length > 0)
                                piperPicker.status = line;
                        }
                    }
                    stderr: SplitParser {
                        onRead: data => piperPicker.status = data
                    }
                    onExited: (code, status) => {
                        piperPicker.refresh();
                        page.reloadAssistant();
                    }
                }

                StyledText {
                    Layout.topMargin: 6
                    text: Translation.tr("Piper voice")
                    color: Appearance.colors.colSubtext
                }
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colOnLayer1
                    text: piperPicker.currentVoice
                        ? Translation.tr("Speaking with %1 (%2)").arg(piperPicker.currentVoice.key).arg(piperPicker.currentVoice.source)
                        : (piperPicker.loaded ? Translation.tr("No Piper voice yet: download one below") : Translation.tr("Looking for voices…"))
                }

                ConfigSelectionArray {
                    currentValue: piperPicker.source
                    onSelected: newValue => piperPicker.source = newValue
                    options: [
                        { displayName: Translation.tr("Here (%1)").arg((piperPicker.voices.installed ?? []).length), icon: "folder", value: "installed" },
                        { displayName: Translation.tr("Hugging Face (%1)").arg((piperPicker.voices.huggingface ?? []).length), icon: "cloud_download", value: "huggingface" },
                        { displayName: Translation.tr("AUR (%1)").arg((piperPicker.voices.aur ?? []).length), icon: "package_2", value: "aur" }
                    ]
                }

                MaterialTextArea {
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("Search: a language, a name, a quality (en_GB, alba, high)")
                    onTextChanged: piperPicker.filter = text
                }

                Repeater {
                    model: piperPicker.list.slice(0, piperPicker.shown)

                    delegate: RowLayout {
                        id: voiceRow
                        required property var modelData
                        readonly property bool isPackage: piperPicker.source === "aur"
                        readonly property string label: isPackage ? modelData.name : modelData.key
                        Layout.fillWidth: true
                        spacing: 6

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            StyledText {
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                text: voiceRow.label
                                color: voiceRow.label === piperPicker.voices.current ? Appearance.colors.colPrimary : Appearance.colors.colOnLayer1
                            }
                            StyledText {
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                font.pixelSize: Appearance.font.pixelSize.smaller
                                color: Appearance.colors.colSubtext
                                text: voiceRow.isPackage ? Translation.tr("Every voice of %1").arg(voiceRow.modelData.description.replace(/.*\(|\).*/g, ""))
                                    : piperPicker.source === "huggingface" ? `${voiceRow.modelData.languageName} (${voiceRow.modelData.country}), ${voiceRow.modelData.quality}, ${Math.round(voiceRow.modelData.size / 1e6)} MB` + (voiceRow.modelData.speakers > 1 ? `, ${voiceRow.modelData.speakers} speakers` : "")
                                    : `${voiceRow.modelData.languageName || voiceRow.modelData.language}, ${voiceRow.modelData.quality}, ${voiceRow.modelData.source}` + (voiceRow.modelData.speakers.length > 0 ? `, ${voiceRow.modelData.speakers.length} speakers` : "")
                            }
                        }
                        // Here: hear it, use it, and delete a downloaded one.
                        DialogButton {
                            visible: piperPicker.source === "installed"
                            buttonText: Translation.tr("Hear")
                            onClicked: piperPicker.act(["preview", voiceRow.modelData.key], Translation.tr("Speaking with %1…").arg(voiceRow.modelData.key))
                        }
                        DialogButton {
                            visible: piperPicker.source === "installed"
                            enabled: voiceRow.modelData.key !== piperPicker.voices.current
                            buttonText: voiceRow.modelData.key === piperPicker.voices.current ? Translation.tr("In use") : Translation.tr("Use")
                            onClicked: piperPicker.act(["use", voiceRow.modelData.source === "custom" ? voiceRow.modelData.path : voiceRow.modelData.key], "")
                        }
                        DialogButton {
                            visible: piperPicker.source === "installed" && voiceRow.modelData.source === "hugging face"
                            buttonText: Translation.tr("Delete")
                            onClicked: piperPicker.act(["remove", voiceRow.modelData.key], "")
                        }
                        // Hugging Face: download (then it is used).
                        DialogButton {
                            visible: piperPicker.source === "huggingface"
                            enabled: !voiceRow.modelData.installed && !voiceAction.running
                            buttonText: voiceRow.modelData.installed ? Translation.tr("Here") : Translation.tr("Download")
                            onClicked: piperPicker.act(["get", voiceRow.modelData.key], Translation.tr("Downloading %1…").arg(voiceRow.modelData.key))
                        }
                        // AUR: in a terminal, since the AUR helper asks for your password.
                        DialogButton {
                            visible: voiceRow.isPackage
                            enabled: !voiceRow.modelData.installed && (piperPicker.voices.aurHelper ?? "") !== ""
                            buttonText: voiceRow.modelData.installed ? Translation.tr("Installed") : Translation.tr("Install")
                            onClicked: Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' voice aur '${voiceRow.modelData.name}'; read -rp 'Press Enter to close. '"`])
                        }
                    }
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: piperPicker.list.length > piperPicker.shown
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.smallie
                    text: Translation.tr("%1 more: search to narrow the list").arg(piperPicker.list.length - piperPicker.shown)
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: piperPicker.source === "aur" && (piperPicker.voices.aurHelper ?? "") === ""
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.smallie
                    text: Translation.tr("AUR packages need an AUR helper (paru or yay). Each one installs every voice of a language; they then show under Here.")
                }

                MaterialTextArea {
                    visible: (piperPicker.currentVoice?.speakers ?? []).length > 0
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("Speaker (this voice has %1): a name or a number").arg((piperPicker.currentVoice?.speakers ?? []).length)
                    text: Config.options.halcyon.assistant.piperSpeaker
                    onTextChanged: {
                        if (text.trim() === Config.options.halcyon.assistant.piperSpeaker)
                            return;
                        Config.options.halcyon.assistant.piperSpeaker = text.trim();
                        page.reloadAssistant();
                    }
                }

                StyledText {
                    Layout.fillWidth: true
                    visible: piperPicker.status !== ""
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colSubtext
                    font.pixelSize: Appearance.font.pixelSize.smallie
                    text: piperPicker.status
                }
            }

            ConfigSwitch {
                buttonIcon: "forum"
                text: Translation.tr("Read the AI sidebar's replies")
                checked: Config.options.halcyon.assistant.sidebarSpeak
                onCheckedChanged: {
                    Config.options.halcyon.assistant.sidebarSpeak = checked;
                    page.reloadAssistant();
                }
                StyledToolTip {
                    text: Translation.tr("Replies typed in the left sidebar are read aloud too, without code or links. Super+Shift+Space stops it")
                }
            }
            // A button of its own, not in a row with the switch: in a uniform row it was drawn over the switch.
            RowLayout {
                RippleButtonWithIcon {
                    buttonRadius: Appearance.rounding.full
                    materialIcon: "campaign"
                    mainText: Translation.tr("Test the voice")
                    // A terminal, so you can read why a voice fails.
                    onClicked: Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' test-voice; read -rp 'Press Enter to close. '"`])
                    StyledToolTip {
                        text: "halcyon assistant test-voice"
                    }
                }
            }
            StyledText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Appearance.colors.colSubtext
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: Translation.tr("An AI voice sends the reply's text to Google or OpenAI (or the server you set) to be spoken. Kokoro, Piper, eSpeak and your own command speak on this computer.")
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

    // Plus Tiles (hyprland-plus): written to Hyprland by `halcyon plus apply`,
    // debounced like refresh() so a spin box reloads Hyprland once.
    property var plusStatus: ({})

    Process {
        id: plusStatusProc
        command: [page.tool, "plus", "status"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    page.plusStatus = JSON.parse(this.text) ?? {};
                } catch (error) {
                    page.plusStatus = {};
                }
            }
        }
    }

    Timer {
        id: plusTimer
        interval: 700
        onTriggered: {
            Quickshell.execDetached([page.tool, "plus", "apply"]);
            plusStatusRefresh.restart();
        }
    }

    Timer {
        id: plusStatusRefresh
        interval: 1200
        onTriggered: plusStatusProc.running = true
    }

    function applyPlus() {
        if (page.ready)
            plusTimer.restart();
    }

    ContentSection {
        icon: "dashboard"
        title: Translation.tr("Plus Tiles")

        NoticeBox {
            Layout.fillWidth: true
            visible: page.plusStatus.running === true && page.plusStatus.plus !== true
            materialIcon: "info"
            text: Translation.tr("These need hyprland-plus, the Halcyon Hyprland fork. On stock Hyprland they are saved but do nothing; the app rules that stock Hyprland has still work.")
        }

        NoticeBox {
            Layout.fillWidth: true
            visible: page.plusStatus.plus === true && page.plusStatus.tiles === false
            materialIcon: "update"
            text: Translation.tr("You are running hyprland-plus, but a build from before Plus Tiles, so these settings have no effect yet. Mini windows and the superposition strip still work. Update it with `sudo hyprctl-lite install update`, then log out and back in.")
        }

        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "select_all"
                text: Translation.tr("Every tiled window")
                checked: Config.options.halcyon.plus.allTiled
                onCheckedChanged: {
                    Config.options.halcyon.plus.allTiled = checked;
                    page.applyPlus();
                }
                StyledToolTip {
                    text: Translation.tr("Off: only the apps marked plus in the app rules are Plus Tiles")
                }
            }
            ConfigSwitch {
                buttonIcon: "preview"
                text: Translation.tr("Preview edge moves")
                checked: Config.options.halcyon.plus.editPreview
                onCheckedChanged: {
                    Config.options.halcyon.plus.editPreview = checked;
                    page.applyPlus();
                }
                StyledToolTip {
                    text: Translation.tr("On: Move Edge shows the new sizes and applies them on Enter. Off: every step applies at once")
                }
            }
        }

        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "restore"
                text: Translation.tr("Keep custom sizes")
                checked: Config.options.halcyon.plus.autoRestore
                onCheckedChanged: {
                    Config.options.halcyon.plus.autoRestore = checked;
                    page.applyPlus();
                }
                StyledToolTip {
                    text: Translation.tr("Tiles whose edges you moved get their size back when windows open, close or move, or the monitor changes")
                }
            }
            ConfigSwitch {
                buttonIcon: "highlight"
                text: Translation.tr("Flash focus target")
                checked: Config.options.halcyon.plus.focusPreview
                onCheckedChanged: {
                    Config.options.halcyon.plus.focusPreview = checked;
                    page.applyPlus();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Move Edge steps")
            tooltip: Translation.tr("How far one key press moves an edge, in pixels. Fine is used with Ctrl, coarse with Shift")

            ConfigSpinBox {
                icon: "straighten"
                text: Translation.tr("Normal")
                value: Config.options.halcyon.plus.step
                from: 2
                to: 400
                stepSize: 5
                onValueChanged: {
                    Config.options.halcyon.plus.step = value;
                    page.applyPlus();
                }
            }
            ConfigSpinBox {
                icon: "remove"
                text: Translation.tr("Fine")
                value: Config.options.halcyon.plus.stepFine
                from: 1
                to: Config.options.halcyon.plus.step
                stepSize: 1
                onValueChanged: {
                    Config.options.halcyon.plus.stepFine = value;
                    page.applyPlus();
                }
            }
            ConfigSpinBox {
                icon: "add"
                text: Translation.tr("Coarse")
                value: Config.options.halcyon.plus.stepCoarse
                from: Config.options.halcyon.plus.step
                to: 1000
                stepSize: 10
                onValueChanged: {
                    Config.options.halcyon.plus.stepCoarse = value;
                    page.applyPlus();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Smallest tile")
            tooltip: Translation.tr("An edge move never makes a tile, or a neighbour, smaller than this")

            ConfigSpinBox {
                icon: "width"
                text: Translation.tr("Width")
                value: Config.options.halcyon.plus.minWidth
                from: 20
                to: 2000
                stepSize: 10
                onValueChanged: {
                    Config.options.halcyon.plus.minWidth = value;
                    page.applyPlus();
                }
            }
            ConfigSpinBox {
                icon: "height"
                text: Translation.tr("Height")
                value: Config.options.halcyon.plus.minHeight
                from: 20
                to: 2000
                stepSize: 10
                onValueChanged: {
                    Config.options.halcyon.plus.minHeight = value;
                    page.applyPlus();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Visual feedback")
            tooltip: Translation.tr("Outlines and flashes for Move Edge, the drag guide, focus and the geometry inspector. Colours are plus:feedback options in ~/.config/hypr/custom")

            ConfigSwitch {
                buttonIcon: "border_style"
                text: Translation.tr("Show feedback")
                checked: Config.options.halcyon.plus.feedback
                onCheckedChanged: {
                    Config.options.halcyon.plus.feedback = checked;
                    page.applyPlus();
                }
            }
            ConfigSpinBox {
                icon: "timer"
                enabled: Config.options.halcyon.plus.feedback
                text: Translation.tr("Flash length (ms)")
                value: Config.options.halcyon.plus.feedbackDuration
                from: 0
                to: 3000
                stepSize: 50
                onValueChanged: {
                    Config.options.halcyon.plus.feedbackDuration = value;
                    page.applyPlus();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Fullscreen")
            tooltip: Translation.tr("Needs a recent hyprland-plus; older builds ignore these")

            ConfigSpinBox {
                icon: "vertical_align_top"
                text: Translation.tr("Drop at the top: fullscreen (px)")
                value: Config.options.halcyon.plus.dragFullscreenEdge
                from: 0
                to: 512
                stepSize: 2
                onValueChanged: {
                    Config.options.halcyon.plus.dragFullscreenEdge = value;
                    page.applyPlus();
                }
            }
            // A note, not a tooltip: a spin box row has no hover of its own, so a tooltip on it was always showing.
            StyledText {
                Layout.fillWidth: true
                Layout.leftMargin: 8
                wrapMode: Text.Wrap
                color: Appearance.colors.colSubtext
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: Translation.tr("Hold Super, drag a window by its middle and let go at the very top of the screen. A click is not a drag, and a window already at the top is left alone. 0 turns it off.")
            }
            ConfigSwitch {
                buttonIcon: "queue_music"
                text: Translation.tr("Music strip over fullscreen")
                checked: Config.options.halcyon.plus.stripOverFullscreen
                onCheckedChanged: {
                    Config.options.halcyon.plus.stripOverFullscreen = checked;
                    page.applyPlus();
                }
                StyledToolTip {
                    text: Translation.tr("Off: a fullscreen window has the whole screen and the strip (Spotify, the visualizer window) waits behind it. On: the strip stays on top and covers the edge of the fullscreen window")
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("App rules and keys")
            tooltip: Translation.tr("Opens your copy in ~/.config/hypr/custom, made from Halcyon's the first time. Hyprland reloads when you save it")

            RowLayout {
                spacing: 8
                RippleButtonWithIcon {
                    materialIcon: "rule"
                    mainText: page.plusStatus.customRules ? Translation.tr("Edit app rules") : Translation.tr("Customise app rules")
                    onClicked: {
                        Quickshell.execDetached([page.tool, "plus", "edit", "rules"]);
                        plusStatusRefresh.restart();
                    }
                }
                RippleButtonWithIcon {
                    materialIcon: "keyboard"
                    mainText: page.plusStatus.customKeys ? Translation.tr("Edit Plus keys") : Translation.tr("Customise Plus keys")
                    onClicked: {
                        Quickshell.execDetached([page.tool, "plus", "edit", "keys"]);
                        plusStatusRefresh.restart();
                    }
                }
            }
        }
    }

    // `halcyon config-check --json`, shown as a list. Only Fix changes anything,
    // and it only fixes file permissions, after a backup.
    property var checkFindings: []
    property string checkSummary: ""

    Process {
        id: configCheck
        property bool fix: false
        command: [page.tool, "config-check", "--json"].concat(fix ? ["--fix"] : [])
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(this.text);
                    page.checkFindings = result.findings ?? [];
                    const errors = page.checkFindings.filter(f => f.severity === "error").length;
                    const warnings = page.checkFindings.filter(f => f.severity === "warning").length;
                    page.checkSummary = page.checkFindings.length === 0
                        ? Translation.tr("No problems found.")
                        : Translation.tr("%1 error(s), %2 warning(s).").arg(errors).arg(warnings);
                    if ((result.fixed ?? []).length > 0)
                        page.checkSummary += " " + Translation.tr("Fixed %1, after a backup to %2.").arg(result.fixed.length).arg(result.backup);
                } catch (error) {
                    page.checkFindings = [];
                    page.checkSummary = Translation.tr("The check didn't run. Try `halcyon config-check` in a terminal.");
                }
            }
        }
    }

    function runCheck(fix) {
        configCheck.fix = fix;
        page.checkSummary = Translation.tr("Checking…");
        configCheck.running = true;
    }

    ContentSection {
        icon: "fact_check"
        title: Translation.tr("Configuration check")

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Looks for config errors, options your Hyprland doesn't have, keybinds that clash, repeated lines, missing plugins and wrong file permissions. Your config is never rewritten.")
        }

        RowLayout {
            spacing: 8
            RippleButtonWithIcon {
                materialIcon: "search_check"
                mainText: Translation.tr("Check")
                enabled: !configCheck.running
                onClicked: page.runCheck(false)
            }
            RippleButtonWithIcon {
                materialIcon: "build"
                mainText: Translation.tr("Fix permissions")
                visible: page.checkFindings.some(f => f.autofix)
                enabled: !configCheck.running
                onClicked: page.runCheck(true)
                StyledToolTip {
                    text: Translation.tr("Backs up ~/.config/hypr, then fixes file permissions only")
                }
            }
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            visible: page.checkSummary !== ""
            wrapMode: Text.Wrap
            color: Appearance.colors.colOnLayer1
            text: page.checkSummary
        }

        Repeater {
            model: page.checkFindings
            delegate: RowLayout {
                id: finding
                required property var modelData
                Layout.fillWidth: true
                Layout.leftMargin: 10
                spacing: 8

                MaterialSymbol {
                    Layout.alignment: Qt.AlignTop
                    text: finding.modelData.severity === "error" ? "error" : finding.modelData.severity === "warning" ? "warning" : "info"
                    iconSize: Appearance.font.pixelSize.large
                    color: finding.modelData.severity === "error" ? Appearance.colors.colError : Appearance.colors.colSubtext
                }
                StyledText {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Appearance.colors.colOnLayer1
                    font.pixelSize: Appearance.font.pixelSize.small
                    text: finding.modelData.message
                        + (finding.modelData.path ? `  (${finding.modelData.path})` : "")
                        + (finding.modelData.fix ? "\n" + Translation.tr("Fix: %1").arg(finding.modelData.fix) : "")
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
