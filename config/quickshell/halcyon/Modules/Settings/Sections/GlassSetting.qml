import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import ".."

/**
 * One numeric setting as a labelled slider.
 *
 * The Liquid Glass section is a dozen of these, and writing each one as
 * a SettingRow plus a slider plus a formatter would be a dozen chances
 * to format a number differently.
 */
SettingRow {
    id: root

    property string path: ""
    property real from: 0
    property real to: 1
    property real step: 0.01
    property real fallback: 0
    property bool integer: false
    property string suffix: ""
    /** Explanatory text; the current value is appended to it. */
    property string prose: ""

    readonly property real current: Config.get(root.path, root.fallback)

    description: {
        const value = root.integer
            ? String(Math.round(root.current))
            : root.current.toFixed(root.step < 0.01 ? 3 : 2);
        const shown = value + root.suffix;
        return root.prose.length > 0 ? root.prose + "  ·  " + shown : shown;
    }

    GlassSlider {
        implicitWidth: 200
        from: root.from
        to: root.to
        step: root.step
        value: root.current
        onCommitted: value => Config.set(
            root.path, root.integer ? Math.round(value) : Math.round(value * 1000) / 1000
        )
    }
}
