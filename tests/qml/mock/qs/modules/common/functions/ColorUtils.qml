pragma Singleton
import QtQuick
QtObject {
    function applyAlpha(color, alpha) {
        const c = Qt.color(color);
        return Qt.rgba(c.r, c.g, c.b, alpha);
    }
}
