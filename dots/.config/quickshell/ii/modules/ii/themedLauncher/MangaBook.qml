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
 * Manga Ink's app picker: a manga book. It opens with its ink cover swinging over the spine, the apps are printed on
 * its pages, sixteen to a page, and a page turns over when you click the turned-up corner (or the margin) of the
 * left page to go back or of the right page to go on; the arrows, Page Up and Down and the wheel turn them too.
 * Typing searches every app, and a speech bubble on the left page says what Enter will do: open an app, give a sum,
 * run a command (LauncherSearch). Esc closes the book again before it goes.
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
    readonly property var allApps: host ? host.apps() : []
    readonly property var apps: query === "" ? allApps : AppSearch.fuzzyQuery(query)
    readonly property int pageCount: Math.max(2, Math.ceil(apps.length / perPage) + (Math.ceil(apps.length / perPage) % 2))
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
        return book.apps.slice(page * perPage, (page + 1) * perPage);
    }

    // ── Opening and closing ──────────────────────────────────────────────────
    // cover: 0 closed over the right page, 180 swung open over the left; scale and opacity bring the book in.
    property real cover: 0
    property real appear: 0
    property bool closing: false

    Component.onCompleted: openAnim.start()
    function close() {
        if (closing)
            return;
        closing = true;
        openAnim.stop();
        closeAnim.start();
    }

    SequentialAnimation {
        id: openAnim
        NumberAnimation { target: book; property: "appear"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
        NumberAnimation { target: book; property: "cover"; from: 0; to: 180; duration: 560; easing.type: Easing.InOutCubic }
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
    readonly property bool turning: turnAnim.running

    function next() {
        if (turning || spread >= spreads - 1)
            return;
        direction = 1;
        spread += 1;
        rightPage = spread * 2 + 1;   // under the leaf as it lifts
        turnAnim.start();
    }
    function previous() {
        if (turning || spread <= 0)
            return;
        direction = -1;
        spread -= 1;
        leftPage = spread * 2;
        turnAnim.start();
    }
    SequentialAnimation {
        id: turnAnim
        NumberAnimation { target: book; property: "turn"; from: 0; to: 180; duration: 540; easing.type: Easing.InOutCubic }
        ScriptAction {
            script: {
                book.leftPage = book.spread * 2;
                book.rightPage = book.spread * 2 + 1;
                book.turn = 0;
            }
        }
    }

    // ── Keys ─────────────────────────────────────────────────────────────────
    focus: true
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (book.query !== "")
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

        // The leaf that turns: blank paper, shaded as it rises, landing on the other side.
        Item {
            id: leaf
            visible: book.turning
            width: book.pageW
            height: parent.height
            x: book.direction > 0 ? book.pageW + book.spine : 0
            // Folded over the spine: narrowing to its edge, then opening out on the other side, a little taller as
            // it lifts off the page. (A Rotation about y would do it in 3D, but its perspective is far too strong.)
            transform: Scale {
                origin.x: book.direction > 0 ? 0 : leaf.width
                origin.y: leaf.height / 2
                xScale: Math.cos(book.turn * Math.PI / 180)
                yScale: 1 + 0.05 * Math.sin(book.turn * Math.PI / 180)
            }
            Rectangle {
                anchors.fill: parent
                radius: 4
                color: book.paper
                border.width: 3
                border.color: book.ink
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
                // Speed lines across it, as a page turned in a hurry.
                Shape {
                    anchors.fill: parent
                    anchors.margins: 18
                    opacity: 0.25
                    ShapePath {
                        strokeWidth: 1.2
                        strokeColor: book.ink
                        fillColor: "transparent"
                        PathSvg {
                            path: {
                                let d = "";
                                for (let i = 0; i < 14; i++) {
                                    const y = (i + 0.5) * leaf.height / 15;
                                    d += `M ${leaf.width * 0.1 + (i % 3) * 30} ${y} L ${leaf.width * 0.8 - (i % 4) * 25} ${y} `;
                                }
                                return d;
                            }
                        }
                    }
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

    // ── A page ───────────────────────────────────────────────────────────────
    component Page: Item {
        id: page
        property int pageIndex: 0
        property bool isLeft: true
        readonly property var entries: book.pageApps(page.pageIndex)
        readonly property bool hasPrevious: page.isLeft && book.spread > 0
        readonly property bool hasNext: !page.isLeft && book.spread < book.spreads - 1

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
            visible: page.isLeft
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
