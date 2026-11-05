pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Widgets
import "../background/widgets/revolver/RevolverStyles.js" as Styles

/**
 * Manga Ink's app picker: a manga book. It opens with its ink cover swinging over the spine. The first page is the
 * table of contents; the apps follow in chapters by type (the web, making things, pictures, sound and screen,
 * games...), sixteen to a page. A page turns over when you click the turned-up corner (or the margin) of the left
 * page to go back or of the right page to go on, when you drag it across the book, and with the arrows, Page Up and
 * Down and the wheel. Pages have weight: held, one follows your hand with a little lag; let go, it falls onto
 * whichever side it is over, unless you threw it hard enough to carry over, and lands with a small bounce. Typing searches every app, and a
 * speech bubble on the left page says what Enter will do: open an app, give a sum, run a command (LauncherSearch).
 *
 * Double-click the space under the last row of apps on a page and a tablet drops down over the book with every
 * workspace and the apps open on it: click one to go to it, or hold Shift and drag it onto another workspace to move
 * it there (WorkspaceTablet). Esc puts the tablet away, then closes the book.
 *
 * In Manga Ink Dark the same book is printed in negative.
 */
Item {
    id: book

    property var host
    signal closed

    readonly property bool negative: Config.options.halcyon.theme === "manga-ink-dark"
    readonly property color ink: negative ? "#f1ece2" : "#141414"
    readonly property color paper: negative ? "#0d0d0e" : "#f7f3ea"
    readonly property color blush: Appearance.colors.colPrimary

    // The book's size: two pages and a spine, as large as the screen comfortably takes.
    readonly property real bookW: Math.min(width * 0.82, 1240)
    readonly property real bookH: Math.min(height * 0.8, bookW * 0.62)
    readonly property real pageW: (bookW - spine) / 2
    readonly property real spine: 18

    readonly property int perPage: 16
    property string query: ""
    // Read again each time the book opens, so newly installed apps are in it.
    property var allApps: []
    readonly property var apps: query === "" ? allApps : AppSearch.fuzzyQuery(query)

    // The chapters, by the categories in the apps' desktop files; an app goes in the first chapter it fits.
    readonly property var chapterDefs: [
        { name: Translation.tr("Games"), keys: ["Game"] },
        { name: Translation.tr("Pictures"), keys: ["Graphics", "Photography", "2DGraphics", "3DGraphics", "RasterGraphics", "VectorGraphics"] },
        { name: Translation.tr("Sound & Screen"), keys: ["AudioVideo", "Audio", "Video", "Music", "Player", "Recorder"] },
        { name: Translation.tr("Making Things"), keys: ["Development", "IDE", "TextEditor", "Building", "Debugger"] },
        { name: Translation.tr("Work"), keys: ["Office", "WordProcessor", "Spreadsheet", "Presentation", "Calendar", "ContactManagement"] },
        { name: Translation.tr("Learning"), keys: ["Education", "Science", "Math"] },
        { name: Translation.tr("The Web"), keys: ["Network", "WebBrowser", "Email", "Chat", "InstantMessaging", "P2P"] },
        { name: Translation.tr("Tools"), keys: ["Utility", "Accessories", "FileManager", "TerminalEmulator", "Archiving", "Calculator"] },
        { name: Translation.tr("The System"), keys: ["Settings", "System", "Monitor", "PackageManager", "Security", "HardwareSettings"] },
        { name: Translation.tr("Everything Else"), keys: [] },
    ]
    function chapterOf(entry) {
        const cats = entry?.categories ?? [];
        for (let i = 0; i < chapterDefs.length - 1; i++)
            if (chapterDefs[i].keys.some(k => cats.includes(k)))
                return i;
        return chapterDefs.length - 1;
    }
    // The pages: the contents, then each chapter from a new page; or, while searching, just the matches.
    // Each page is { kind: "toc" | "apps" | "blank", chapter, chapterNumber, first, entries }; toc lists the chapters.
    readonly property var layout: {
        const pages = [];
        const toc = [];
        if (query !== "") {
            for (let i = 0; i < Math.max(1, apps.length); i += perPage)
                pages.push({ kind: "apps", chapter: "", entries: apps.slice(i, i + perPage) });
        } else {
            pages.push({ kind: "toc", entries: [] });
            const buckets = chapterDefs.map(() => []);
            for (const a of apps)
                buckets[chapterOf(a)].push(a);
            let number = 0;
            buckets.forEach((entries, c) => {
                if (entries.length === 0)
                    return;
                number += 1;
                toc.push({ name: chapterDefs[c].name, number: number, page: pages.length, count: entries.length });
                for (let i = 0; i < entries.length; i += perPage)
                    pages.push({ kind: "apps", chapter: chapterDefs[c].name, chapterNumber: number, first: i === 0, entries: entries.slice(i, i + perPage) });
            });
        }
        if (pages.length % 2 === 1)
            pages.push({ kind: "blank", entries: [] });
        return { pages: pages, toc: toc };
    }
    readonly property var pages: layout.pages
    readonly property var toc: layout.toc
    readonly property int pageCount: Math.max(2, pages.length)
    // The spread open: pages 2*spread and 2*spread + 1.
    property int spread: 0
    readonly property int spreads: Math.ceil(pageCount / 2)
    // What each page shows; the left one keeps the old spread until the turning leaf lands on it.
    property int leftPage: 0
    property int rightPage: 1

    onQueryChanged: {
        LauncherSearch.query = query;
        spread = 0;
        leftPage = 0;
        rightPage = 1;
    }

    function pageApps(page) {
        return book.pages[page]?.entries ?? [];
    }

    // ── Opening and closing ──────────────────────────────────────────────────
    // cover: 0 closed over the right page, 180 swung open over the left; scale and opacity bring the book in.
    property real cover: 0
    property real appear: 0
    property bool closing: false

    // From the first page, the cover shut. The book is kept between openings, so this resets it.
    function open() {
        closeAnim.stop();
        falling = false;
        dragTurning = false;
        angle = 0;
        omega = 0;
        tabletShown = false;
        closing = false;
        allApps = host ? host.apps() : [];
        query = "";
        spread = 0;
        leftPage = 0;
        rightPage = 1;
        turn = 0;
        cover = 0;
        appear = 0;
        forceActiveFocus();
        openAnim.restart();
    }
    function close() {
        if (closing)
            return;
        closing = true;
        openAnim.stop();
        closeAnim.start();
    }

    SequentialAnimation {
        id: openAnim
        NumberAnimation { target: book; property: "appear"; to: 1; duration: 220; easing.type: Easing.OutCubic }
        NumberAnimation { target: book; property: "cover"; to: 180; duration: 560; easing.type: Easing.InOutCubic }
    }
    SequentialAnimation {
        id: closeAnim
        NumberAnimation { target: book; property: "cover"; to: 0; duration: 420; easing.type: Easing.InOutCubic }
        NumberAnimation { target: book; property: "appear"; to: 0; duration: 180; easing.type: Easing.InCubic }
        ScriptAction { script: book.closed() }
    }

    // ── Turning pages ────────────────────────────────────────────────────────
    // turn: 0..180 while a leaf is over; direction 1 forward (right to left), -1 back.
    property real turn: 0
    property int direction: 1
    // A page held by a drag: it follows the hand, then turns over or falls back on release.
    property bool dragTurning: false
    // A page let go of (or flipped by a click, a key or the wheel): it moves under its own weight until it lands.
    property bool falling: false
    readonly property bool turning: falling || dragTurning

    // Put the leaf up for a turn to `target` (a spread): the page under it shows the new side at once.
    function lift(target) {
        if (turning || target === spread || target < 0 || target >= spreads)
            return false;
        direction = target > spread ? 1 : -1;
        spread = target;
        if (direction > 0)
            rightPage = spread * 2 + 1;   // under the leaf as it lifts
        else
            leftPage = spread * 2;
        return true;
    }
    function goToSpread(target) {
        if (!lift(target))
            return;
        turn = 0;
        // Flicked from its corner: enough to carry it past upright against its own weight, and then it falls over.
        angle = 0;
        omega = Math.sqrt(2 * gravity) * 1.28 + airDrag * 0.5;
        falling = true;
    }
    function goToPage(page) {
        goToSpread(Math.floor(page / 2));
    }
    function next() {
        goToSpread(spread + 1);
    }
    function previous() {
        goToSpread(spread - 1);
    }
    function land() {
        leftPage = spread * 2;
        rightPage = spread * 2 + 1;
        turn = 0;
        angle = 0;
        omega = 0;
        falling = false;
    }

    function dragBegin(dir) {
        if (!lift(spread + dir))
            return false;
        turn = 0;
        angle = 0;
        omega = 0;
        handAngle = 0;
        dragTurning = true;
        return true;
    }
    function dragMove(dx) {
        handAngle = Math.max(0, Math.min(Math.PI * 0.995, Math.abs(dx) / (pageW * 0.9) * Math.PI));
    }
    function dragEnd() {
        // Let go: it keeps the speed the hand gave it, and its weight does the rest. Past upright it falls over;
        // short of it, it falls back, unless it was thrown hard enough to carry over.
        dragTurning = false;
        falling = true;
    }

    // ── The page's physics ───────────────────────────────────────────────────
    // A page is a leaf hinged at the spine. Its weight pulls it down onto whichever side it is over (strongest
    // lying flat, nothing standing upright: −g·cos θ), the air slows it, and it bounces a little as it lands. Held,
    // it follows the hand on a stiff spring, so it lags a touch behind and keeps the hand's speed when let go.
    property real angle: 0          // radians, 0 (lying on its first side) to π (turned over)
    property real omega: 0          // radians a second
    property real handAngle: 0
    readonly property real gravity: 42      // rad/s² at the flat
    readonly property real airDrag: 1.6
    readonly property real handStiffness: 320
    readonly property real handDamping: 28
    readonly property real bounce: 0.22
    property real lastStep: 0
    function step() {
        const now = Date.now();
        const dt = Math.min(0.033, Math.max(0.001, (now - lastStep) / 1000));
        lastStep = now;
        let accel;
        if (dragTurning)
            accel = handStiffness * (handAngle - angle) - handDamping * omega;
        else
            accel = -gravity * Math.cos(angle) - airDrag * omega;
        omega += accel * dt;
        angle += omega * dt;
        if (angle >= Math.PI) {
            angle = Math.PI;
            if (!dragTurning && Math.abs(omega) < 1.2)
                return settle(true);
            omega = -Math.abs(omega) * bounce;
        } else if (angle <= 0) {
            angle = 0;
            if (!dragTurning && Math.abs(omega) < 1.2)
                return settle(false);
            omega = Math.abs(omega) * bounce;
        }
        turn = angle * 180 / Math.PI;
    }
    // Landed: on the other side, the turn is done; back where it was, the book is as it was.
    function settle(over) {
        if (!over)
            spread -= direction;
        land();
    }
    FrameAnimation {
        running: book.falling || book.dragTurning
        onRunningChanged: if (running) book.lastStep = Date.now()
        onTriggered: book.step()
    }

    // ── Keys ─────────────────────────────────────────────────────────────────
    focus: true
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (book.tabletShown)
                book.tabletShown = false;
            else if (book.query !== "")
                book.query = "";
            else
                book.host.dismiss();
        } else if (event.key === Qt.Key_Right || event.key === Qt.Key_PageDown) {
            book.next();
        } else if (event.key === Qt.Key_Left || event.key === Qt.Key_PageUp) {
            book.previous();
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (book.query !== "" && LauncherSearch.results.length > 0)
                book.host.runResult(LauncherSearch.results[0]);
            else if (book.apps.length > 0)
                book.host.launchEntry(book.apps[0]);
        } else if (event.key === Qt.Key_Backspace) {
            book.query = book.query.slice(0, -1);
        } else if (event.text.length === 1 && event.text >= " ") {
            book.query += event.text;
        } else {
            return;
        }
        event.accepted = true;
    }

    // ── The book ─────────────────────────────────────────────────────────────
    Item {
        id: volume
        width: book.bookW
        height: book.bookH
        anchors.centerIn: parent
        opacity: book.appear
        scale: 0.86 + 0.14 * book.appear

        // Clicks on the book don't reach the "click beside it closes it" area.
        MouseArea {
            anchors.fill: parent
            onWheel: wheel => wheel.angleDelta.y < 0 ? book.next() : book.previous()
        }

        // Drag across the book to turn a page: leftwards on, rightwards back. A click on an app is still a click; the
        // drag only takes over once the hand has moved.
        DragHandler {
            id: pageDrag
            target: null
            yAxis.enabled: false
            property int dir: 0
            onActiveChanged: {
                if (active)
                    dir = 0;
                else if (book.dragTurning)
                    book.dragEnd();
            }
            onTranslationChanged: {
                if (!active)
                    return;
                const dx = translation.x;
                if (dir === 0 && Math.abs(dx) > 24)
                    dir = book.dragBegin(dx < 0 ? 1 : -1) ? (dx < 0 ? 1 : -1) : 2;
                if (book.dragTurning)
                    book.dragMove(dx);
            }
        }

        // The hard shadow under both pages, straight down and right, as the manga panels have it.
        Rectangle {
            x: 10
            y: 10
            width: parent.width
            height: parent.height
            radius: 6
            color: book.ink
            opacity: book.cover > 90 ? 1 : 0.0
            visible: opacity > 0
        }

        // The left page shows once the cover has swung past the spine.
        Page {
            id: left
            x: 0
            width: book.pageW
            height: parent.height
            pageIndex: book.leftPage
            isLeft: true
            visible: book.cover > 90
        }
        Page {
            id: right
            x: book.pageW + book.spine
            width: book.pageW
            height: parent.height
            pageIndex: book.rightPage
            isLeft: false
        }

        // The spine: the paper's fold, darker in the middle.
        Rectangle {
            x: book.pageW - 2
            width: book.spine + 4
            height: parent.height
            visible: book.cover > 90
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: book.paper }
                GradientStop { position: 0.5; color: Qt.rgba(book.ink.r, book.ink.g, book.ink.b, 0.55) }
                GradientStop { position: 1.0; color: book.paper }
            }
            border.width: 0
        }

        // The leaf that turns. Its front is the page being turned and its back the page it lands as, so nothing
        // pops in when it lands: forward, the old right page over to the new left one; back, the old left page over
        // to the new right one. Shaded as it rises; drawn as one texture while it turns.
        Item {
            id: leaf
            visible: book.turning
            width: book.pageW
            height: parent.height
            x: book.direction > 0 ? book.pageW + book.spine : 0
            layer.enabled: book.turning
            // Folded over the spine: narrowing to its edge, then opening out on the other side, a little taller as
            // it lifts off the page. (A Rotation about y would do it in 3D, but its perspective is far too strong.)
            transform: Scale {
                origin.x: book.direction > 0 ? 0 : leaf.width
                origin.y: leaf.height / 2
                xScale: Math.cos(book.turn * Math.PI / 180)
                yScale: 1 + 0.05 * Math.sin(book.turn * Math.PI / 180)
            }
            Page {
                anchors.fill: parent
                live: false
                visible: book.turn < 90
                isLeft: book.direction < 0
                pageIndex: book.direction > 0 ? book.spread * 2 - 1 : book.spread * 2 + 2
            }
            // Past the fold the leaf is mirrored; mirrored once more, its back reads the right way round.
            Page {
                anchors.fill: parent
                live: false
                visible: book.turn >= 90
                isLeft: book.direction > 0
                pageIndex: book.direction > 0 ? book.spread * 2 : book.spread * 2 + 1
                transform: Scale { origin.x: book.pageW / 2; xScale: -1 }
            }
            // The light on it as it turns, dark at the fold.
            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: book.direction > 0 ? 0.0 : 1.0; color: Qt.rgba(0, 0, 0, 0.35 * Math.sin(book.turn * Math.PI / 180)) }
                    GradientStop { position: book.direction > 0 ? 0.6 : 0.4; color: Qt.rgba(0, 0, 0, 0.0) }
                }
            }
        }

        // The cover: ink, the title in big lettering, a blush heart. It swings open over the spine.
        Item {
            id: coverLeaf
            visible: book.cover < 180
            width: book.pageW
            height: parent.height
            x: book.pageW + book.spine
            transform: Scale {
                origin.x: 0
                origin.y: coverLeaf.height / 2
                xScale: Math.cos(book.cover * Math.PI / 180)
                yScale: 1 + 0.05 * Math.sin(book.cover * Math.PI / 180)
            }
            // Its front until it is halfway over, then its inside (paper).
            Rectangle {
                anchors.fill: parent
                radius: 6
                color: book.cover < 90 ? book.ink : book.paper
                border.width: 3
                border.color: book.ink
                Column {
                    visible: book.cover < 90
                    anchors.centerIn: parent
                    spacing: 18
                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "APPS"
                        color: book.paper
                        font.pixelSize: Math.round(book.bookH * 0.16)
                        font.weight: Font.Black
                        font.letterSpacing: 6
                    }
                    Shape {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 80
                        height: 70
                        ShapePath {
                            strokeWidth: 3
                            strokeColor: book.paper
                            fillColor: book.blush
                            PathSvg { path: Styles.heart(40, 36, 30) }
                        }
                    }
                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: Translation.tr("vol. %1").arg(book.spreads)
                        color: book.paper
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }
                }
            }
        }
    }

    // ── The workspace tablet ─────────────────────────────────────────────────
    // Drops down over the book on a double-click under the apps, swinging a little as it lands; goes back up the same way.
    property bool tabletShown: false
    property real tabletOpen: tabletShown ? 1 : 0
    Behavior on tabletOpen {
        NumberAnimation {
            duration: book.tabletShown ? 520 : 280
            easing.type: book.tabletShown ? Easing.OutBack : Easing.InCubic
            easing.overshoot: 1.2
        }
    }

    // The page dims behind it; a click there puts it away.
    Rectangle {
        anchors.fill: parent
        visible: book.tabletOpen > 0.01
        color: Qt.rgba(0, 0, 0, 0.28 * Math.min(1, book.tabletOpen))
        MouseArea {
            anchors.fill: parent
            onClicked: book.tabletShown = false
        }
    }

    Item {
        id: tablet
        visible: book.tabletOpen > 0.01
        width: Math.min(book.bookW * 0.92, 1120)
        height: width * 0.62
        x: (book.width - width) / 2
        y: (book.height - height) / 2 - (1 - book.tabletOpen) * (book.height * 0.75)
        rotation: (1 - Math.min(1, book.tabletOpen)) * -7
        transformOrigin: Item.Top

        MouseArea { anchors.fill: parent }   // clicks on the tablet stay on it

        // The hard shadow, as everything in Manga Ink has.
        Rectangle {
            x: 12
            y: 12
            width: parent.width
            height: parent.height
            radius: 36
            color: book.ink
            opacity: 0.85
        }
        // The body: an ink bezel with a camera, a power button on top.
        Rectangle {
            x: parent.width * 0.78
            y: -6
            width: 70
            height: 10
            radius: 4
            color: book.ink
        }
        Rectangle {
            id: bezel
            anchors.fill: parent
            radius: 36
            color: book.ink
            border.width: 3
            border.color: book.negative ? book.paper : "#000000"
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 10
                width: 8
                height: 8
                radius: 4
                color: Qt.rgba(book.paper.r, book.paper.g, book.paper.b, 0.35)
            }
            // The screen: paper, the workspaces printed on it.
            Rectangle {
                id: tabletScreen
                anchors.fill: parent
                anchors.margins: 26
                radius: 14
                color: book.paper
                clip: true
                Item {
                    anchors.fill: parent
                    anchors.margins: 4
                    clip: true
                    Shape {
                        anchors.fill: parent
                        ShapePath {
                            strokeWidth: -1
                            fillColor: Qt.rgba(book.ink.r, book.ink.g, book.ink.b, 0.22)
                            PathSvg { path: Styles.screentone(tabletScreen.width - 10, 0, 120, 7) }
                        }
                    }
                }
                Row {
                    x: 22
                    y: 14
                    spacing: 14
                    StyledText {
                        text: Translation.tr("WORKSPACES")
                        color: book.ink
                        font.pixelSize: 24
                        font.weight: Font.Black
                        font.letterSpacing: 4
                    }
                    StyledText {
                        anchors.baseline: parent.children[0].baseline
                        text: Translation.tr("click an app to go to it · Shift + drag it to move it")
                        color: Qt.rgba(book.ink.r, book.ink.g, book.ink.b, 0.7)
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        font.italic: true
                    }
                }
                WorkspaceBoard {
                    anchors.fill: parent
                    anchors.margins: 22
                    anchors.topMargin: 60
                    ink: book.ink
                    paper: book.paper
                    accent: book.blush
                    corner: 2
                    border: 2.5
                    columns: 4
                    onPicked: book.host.dismiss()
                }
            }
        }
    }

    // ── A page ───────────────────────────────────────────────────────────────
    component Page: Item {
        id: page
        property int pageIndex: 0
        property bool isLeft: true
        // False for the pictures of pages on the turning leaf: nothing on them can be clicked.
        property bool live: true
        enabled: live
        readonly property var entries: book.pageApps(page.pageIndex)
        readonly property var info: book.pages[page.pageIndex] ?? ({ kind: "blank", entries: [] })
        readonly property bool hasPrevious: page.live && page.isLeft && book.spread > 0
        readonly property bool hasNext: page.live && !page.isLeft && book.spread < book.spreads - 1

        Rectangle {
            anchors.fill: parent
            radius: 4
            color: book.paper
            border.width: 3
            border.color: book.ink
        }

        // Screentone in the outer bottom corner.
        Item {
            anchors.fill: parent
            anchors.margins: 4
            clip: true
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: -1
                    fillColor: Qt.rgba(book.ink.r, book.ink.g, book.ink.b, 0.3)
                    PathSvg { path: Styles.screentone(page.isLeft ? 0 : page.width - 8, page.height - 8, 110, 7) }
                }
            }
        }

        // The left page's heading: the title, and what you typed in a speech bubble with what Enter does.
        Item {
            id: heading
            x: 26
            y: 18
            width: parent.width - 52
            height: 58
            visible: page.isLeft && (book.query !== "" || page.info.kind === "toc")
            StyledText {
                anchors.verticalCenter: parent.verticalCenter
                visible: book.query === ""
                text: Translation.tr("APPS · type to search, to sum, to run")
                color: book.ink
                font.pixelSize: 15
                font.weight: Font.Black
                font.letterSpacing: 2
            }
            Rectangle {
                anchors.fill: parent
                visible: book.query !== ""
                radius: height / 2
                color: book.paper
                border.width: 2.5
                border.color: book.ink
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    x: 22
                    spacing: 12
                    StyledText {
                        text: book.query + "▍"
                        color: book.ink
                        font.pixelSize: 18
                        font.weight: Font.Black
                    }
                    StyledText {
                        anchors.verticalCenter: parent.verticalCenter
                        readonly property var first: LauncherSearch.results.length > 0 ? LauncherSearch.results[0] : null
                        visible: first !== null
                        text: first ? `↵ ${first.verb} · ${first.type}: ${first.name}` : ""
                        color: book.blush
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        width: heading.width - 60 - x
                    }
                }
            }
        }
        // A chapter's title, at the head of its pages: big on its first page, small after.
        Row {
            x: 26
            y: page.info.first ? 22 : 34
            spacing: 10
            visible: page.info.kind === "apps" && page.info.chapter !== "" && !(page.isLeft && book.query !== "")
            Rectangle {
                visible: page.info.first === true
                anchors.verticalCenter: parent.verticalCenter
                width: chapterNumber.implicitWidth + 16
                height: chapterNumber.implicitHeight + 6
                color: book.ink
                StyledText {
                    id: chapterNumber
                    anchors.centerIn: parent
                    text: Translation.tr("CH. %1").arg(page.info.chapterNumber ?? "")
                    color: book.paper
                    font.pixelSize: 12
                    font.weight: Font.Black
                    font.letterSpacing: 2
                }
            }
            StyledText {
                anchors.verticalCenter: parent.verticalCenter
                text: page.info.first ? (page.info.chapter ?? "").toUpperCase() : Translation.tr("%1 (cont.)").arg(page.info.chapter ?? "")
                color: book.ink
                font.pixelSize: page.info.first ? 26 : 13
                font.weight: Font.Black
                font.letterSpacing: page.info.first ? 3 : 1
            }
        }

        // The contents: each chapter, a dotted leader, and its page; click one to turn to it.
        Column {
            visible: page.info.kind === "toc"
            x: 30
            y: 92
            width: parent.width - 60
            spacing: 4
            StyledText {
                text: Translation.tr("CONTENTS")
                color: book.ink
                font.pixelSize: 30
                font.weight: Font.Black
                font.letterSpacing: 6
                bottomPadding: 10
            }
            Repeater {
                model: page.info.kind === "toc" ? book.toc : []
                delegate: Item {
                    id: tocRow
                    required property var modelData
                    width: parent.width
                    height: 34
                    Rectangle {
                        anchors.fill: parent
                        color: tocArea.containsMouse ? Qt.rgba(book.blush.r, book.blush.g, book.blush.b, 0.16) : "transparent"
                    }
                    StyledText {
                        id: tocName
                        anchors.verticalCenter: parent.verticalCenter
                        x: 6
                        text: Translation.tr("%1. %2").arg(tocRow.modelData.number).arg(tocRow.modelData.name)
                        color: book.ink
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                    // The leader: dots from the name to the page number.
                    StyledText {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: tocName.right
                        anchors.leftMargin: 8
                        anchors.right: tocPage.left
                        anchors.rightMargin: 8
                        clip: true
                        text: "· ".repeat(80)
                        color: Qt.rgba(book.ink.r, book.ink.g, book.ink.b, 0.5)
                        font.pixelSize: 14
                    }
                    StyledText {
                        id: tocPage
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        text: tocRow.modelData.page + 1
                        color: book.ink
                        font.pixelSize: 16
                        font.weight: Font.Black
                    }
                    MouseArea {
                        id: tocArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: book.goToPage(tocRow.modelData.page)
                    }
                }
            }
        }

        // A blank last page, as a volume ends.
        StyledText {
            visible: page.info.kind === "blank"
            anchors.centerIn: parent
            text: Translation.tr("— to be continued —")
            color: Qt.rgba(book.ink.r, book.ink.g, book.ink.b, 0.55)
            font.pixelSize: 16
            font.weight: Font.Bold
            font.italic: true
        }

        // The right page's heading: where you are in the book.
        StyledText {
            visible: !page.isLeft
            anchors.right: parent.right
            anchors.rightMargin: 28
            y: 34
            text: Translation.tr("p. %1–%2 of %3").arg(book.spread * 2 + 1).arg(book.spread * 2 + 2).arg(book.pageCount)
            color: book.ink
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        // The apps, four by four.
        Grid {
            id: grid
            visible: page.info.kind === "apps"
            x: 26
            y: 88
            width: parent.width - 52
            height: parent.height - 88 - 50
            columns: 4
            readonly property real cellW: width / 4
            readonly property real cellH: height / 4
            Repeater {
                model: page.entries
                delegate: AppCell {
                    required property var modelData
                    entry: modelData
                    width: grid.cellW
                    height: grid.cellH
                }
            }
        }

        // Under the last row of apps: double-click for the workspace tablet. A faint hint while the mouse is there.
        MouseArea {
            id: tabletSpot
            readonly property int rows: Math.ceil(page.entries.length / 4)
            visible: page.info.kind === "apps" || page.info.kind === "blank"
            x: 76
            width: parent.width - 152
            y: page.info.kind === "blank" ? parent.height * 0.6 : grid.y + Math.max(1, rows) * grid.cellH
            height: Math.max(24, parent.height - 44 - y)
            hoverEnabled: true
            onDoubleClicked: book.tabletShown = true
            StyledText {
                anchors.centerIn: parent
                opacity: tabletSpot.containsMouse ? 0.6 : 0
                Behavior on opacity { NumberAnimation { duration: 160 } }
                text: Translation.tr("double-click: workspaces")
                color: book.ink
                font.pixelSize: 12
                font.weight: Font.DemiBold
                font.italic: true
            }
        }

        // The page number, at the foot of the page (the corners are for turning).
        StyledText {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 16
            anchors.horizontalCenter: parent.horizontalCenter
            text: page.pageIndex + 1
            color: book.ink
            font.pixelSize: 13
            font.weight: Font.Black
        }

        // Back and on: the outer margin, and the turned-up corner, which lifts when the mouse is near.
        MouseArea {
            id: margin
            width: 34
            height: parent.height
            x: page.isLeft ? 0 : parent.width - width
            hoverEnabled: true
            enabled: page.hasPrevious || page.hasNext
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: page.isLeft ? book.previous() : book.next()
        }
        Item {
            id: corner
            readonly property bool active: page.hasPrevious || page.hasNext
            property real fold: (cornerArea.containsMouse || margin.containsMouse) && active ? 58 : 38
            Behavior on fold {
                NumberAnimation { duration: 180; easing.type: Easing.OutBack }
            }
            visible: active
            width: 70
            height: 70
            x: page.isLeft ? 0 : parent.width - width
            y: parent.height - height
            Shape {
                anchors.fill: parent
                // The fold: a triangle of the page's back, with its shadow.
                ShapePath {
                    strokeWidth: 2.5
                    strokeColor: book.ink
                    fillColor: Qt.darker(book.paper, book.negative ? 0.6 : 1.12)
                    joinStyle: ShapePath.MiterJoin
                    PathSvg {
                        path: page.isLeft
                            ? `M 3 ${70 - corner.fold} L ${corner.fold} 67 L 3 67 Z`
                            : `M 67 ${70 - corner.fold} L ${70 - corner.fold} 67 L 67 67 Z`
                    }
                }
            }
            StyledText {
                text: page.isLeft ? "‹" : "›"
                color: book.ink
                font.pixelSize: 18
                font.weight: Font.Black
                x: page.isLeft ? 10 : parent.width - width - 10
                y: parent.height - height - 6
            }
            MouseArea {
                id: cornerArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: page.isLeft ? book.previous() : book.next()
            }
        }
    }

    // ── An app on a page: its icon in a small ink panel, its name in bold ────
    component AppCell: Item {
        id: cell
        property var entry
        Item {
            id: panel
            anchors.centerIn: parent
            width: Math.min(cell.width, cell.height) - 22
            height: width
            scale: cellArea.pressed ? 0.93 : 1
            rotation: cellArea.containsMouse ? -2.5 : 0
            Behavior on scale { NumberAnimation { duration: 120 } }
            Behavior on rotation { NumberAnimation { duration: 160; easing.type: Easing.OutBack } }
            Rectangle {
                x: cellArea.containsMouse ? 6 : 4
                y: x
                width: parent.width
                height: parent.height - 16
                radius: 6
                color: book.ink
                Behavior on x { NumberAnimation { duration: 120 } }
            }
            Rectangle {
                width: parent.width
                height: parent.height - 16
                radius: 6
                color: cellArea.containsMouse ? Qt.lighter(book.paper, book.negative ? 1.6 : 1.0) : book.paper
                border.width: 2.5
                border.color: cellArea.containsMouse ? book.blush : book.ink
                IconImage {
                    anchors.centerIn: parent
                    implicitSize: Math.round(parent.height * 0.56)
                    source: AppSearch.iconSource(cell.entry?.icon ?? "")
                }
            }
            StyledText {
                anchors.bottom: parent.bottom
                anchors.bottomMargin: -6
                width: parent.width + 16
                x: -8
                horizontalAlignment: Text.AlignHCenter
                text: cell.entry?.name ?? ""
                color: book.ink
                font.pixelSize: 12
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
        }
        MouseArea {
            id: cellArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: book.host.launchEntry(cell.entry)
        }
    }
}
