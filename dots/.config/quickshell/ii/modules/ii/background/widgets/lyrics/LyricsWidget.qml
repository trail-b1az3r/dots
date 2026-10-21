import QtQuick
import QtQuick.Layouts
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import qs.modules.ii.background.widgets

/**
 * The lyrics of what is playing, a few lines at a time, with the one being sung large and in the theme's way
 * (ThemeLook.spec.lyric): lit like the red ring on Red Sun, on a pane of frost on glass, heavy on HyperNeo, between
 * two gold stars on Star Rail, on a keycap on the anime themes.
 * They come from LRCLIB (services/Lyrics.qml). A song with no synced lyrics shows its name and says so; with no
 * player at all the widget fades away.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "lyrics"

    readonly property var settings: Config.options.background.widgets.lyrics
    readonly property int around: 2 // lines shown before and after the current one
    readonly property ThemeLook look: ThemeLook {}
    readonly property string mark: look.spec.lyric

    implicitWidth: Math.max(240, settings.width)
    implicitHeight: (root.around * 2 + 1) * 46 + (settings.panel ? 44 : 0)
    opacity: (GlobalStates.screenLocked && !visibleWhenLocked) ? 0 : (Lyrics.player ? 1 : 0)

    Component.onCompleted: Lyrics.users++
    Component.onDestruction: Lyrics.users--

    ThemedPlate {
        anchors.fill: parent
        visible: root.settings.panel
        themeId: Config.options.halcyon.theme
        kind: "card"
        colBase: Appearance.colors.colLayer1
        colOn: Appearance.colors.colOnLayer1
        colAccent: Appearance.colors.colPrimary
    }

    // The state, in words, for when there is nothing to sing along to.
    StyledText {
        anchors.centerIn: parent
        width: parent.width - 40
        visible: Lyrics.state !== "synced"
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        font.pixelSize: Appearance.font.pixelSize.large
        color: Appearance.colors.colSubtext
        text: Lyrics.state === "loading" ? Translation.tr("Looking for the lyrics…")
            : Lyrics.state === "plain" ? Translation.tr("%1 has lyrics, but not timed ones").arg(Lyrics.title)
            : Lyrics.state === "none" ? Translation.tr("No lyrics found for %1").arg(Lyrics.title)
            : ""
    }

    Column {
        id: stack
        anchors.centerIn: parent
        width: parent.width - (root.settings.panel ? 44 : 0)
        visible: Lyrics.state === "synced"
        spacing: 0

        Repeater {
            model: root.around * 2 + 1

            delegate: StyledText {
                id: row
                required property int index
                readonly property int offset: index - root.around
                readonly property int at: Lyrics.index + offset
                readonly property bool current: offset === 0
                readonly property string words: (at >= 0 && at < Lyrics.lines.length) ? Lyrics.lines[at].text : ""

                width: stack.width
                height: 46
                horizontalAlignment: root.settings.align === "left" ? Text.AlignLeft : root.settings.align === "right" ? Text.AlignRight : Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                maximumLineCount: 1
                // An empty line in the lyrics is a rest: shown as a note while it is the current one.
                readonly property string sung: words !== "" ? words : (current && Lyrics.index >= 0 ? "♪" : "")
                text: (current && root.mark === "rail" && sung !== "") ? `✦  ${sung}  ✦` : sung
                font.pixelSize: current ? (root.mark === "bold" ? Appearance.font.pixelSize.huge + 4 : Appearance.font.pixelSize.huge)
                                        : (root.mark === "bold" ? Appearance.font.pixelSize.large : Appearance.font.pixelSize.larger)
                font.weight: current ? (root.mark === "bold" || root.mark === "key" ? Font.Black : Font.DemiBold) : Font.Normal
                font.letterSpacing: current && root.mark === "rail" ? 1.2 : 0
                color: !current ? root.look.text
                     : root.mark === "glow" ? root.look.text
                     : root.mark === "frost" ? "#ffffff"
                     : root.look.accentA
                opacity: current ? 1 : Math.max(0.12, 0.55 - 0.2 * (Math.abs(offset) - 1))

                // frost and key: something behind the line being sung, as wide as its words
                Rectangle {
                    z: -1
                    visible: row.current && row.sung !== "" && (root.mark === "frost" || root.mark === "key")
                    readonly property real wide: Math.min(row.width, row.contentWidth + 36)
                    x: row.horizontalAlignment === Text.AlignLeft ? -18 : row.horizontalAlignment === Text.AlignRight ? row.width - wide + 18 : (row.width - wide) / 2
                    y: 3
                    width: wide
                    height: row.height - 6
                    radius: root.mark === "key" ? 12 : 4
                    color: root.mark === "key" ? Qt.lighter(Appearance.colors.colLayer1, 1.12) : Qt.rgba(1, 1, 1, 0.12)
                    border.width: root.mark === "key" ? 2.5 : 1
                    border.color: root.mark === "key" ? Qt.darker(Appearance.colors.colLayer1, 2.6) : Qt.rgba(1, 1, 1, 0.35)
                    // the key's hard shadow, straight down
                    Rectangle {
                        z: -1
                        visible: root.mark === "key"
                        y: 5
                        width: parent.width
                        height: parent.height
                        radius: parent.radius
                        color: Qt.darker(Appearance.colors.colLayer1, 2.6)
                    }
                }

                Behavior on opacity {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }
                Behavior on font.pixelSize {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }
                // Red Sun lights the sung line like its ring. Over a wallpaper, without a card, the other words get an
                // edge so they can be read on any picture.
                style: (current && root.mark === "glow") ? Text.Raised : (root.settings.panel || (current && root.mark === "key") ? Text.Normal : Text.Outline)
                styleColor: (current && root.mark === "glow") ? root.look.glow : ColorUtils.transparentize("#000000", 0.45)
            }
        }
    }
}
