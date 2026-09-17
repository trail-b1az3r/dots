import QtQuick
import Quickshell
import qs.Config

/**
 * A themed icon, with a text glyph as the fallback.
 *
 * Icon themes are not guaranteed to have an entry for everything a panel
 * wants to show, and a missing icon that renders as an empty box looks
 * like a bug. When the theme has no match, the glyph is drawn instead.
 */
Item {
    id: root

    /** An icon theme name, an absolute path, or an image:// url. */
    property string source: ""
    /** Fallback glyph (Nerd Font) drawn when `source` resolves to nothing. */
    property string glyph: ""
    property int size: 18
    property color color: Theme.text

    implicitWidth: root.size
    implicitHeight: root.size

    readonly property string resolved: {
        if (!root.source || root.source.length === 0)
            return "";
        if (root.source.indexOf("/") === 0)
            return "file://" + root.source;
        if (root.source.indexOf("://") > 0)
            return root.source;
        return Quickshell.hasThemeIcon(root.source)
            ? Quickshell.iconPath(root.source, true)
            : "";
    }

    Image {
        id: image
        anchors.fill: parent
        source: root.resolved
        visible: root.resolved.length > 0 && status === Image.Ready
        sourceSize.width: root.size * 2
        sourceSize.height: root.size * 2
        fillMode: Image.PreserveAspectFit
        smooth: true
        asynchronous: true
        cache: true
    }

    Text {
        anchors.centerIn: parent
        visible: !image.visible && root.glyph.length > 0
        text: root.glyph
        color: root.color
        font.pixelSize: root.size
        font.family: Theme.fontFamily
    }
}
