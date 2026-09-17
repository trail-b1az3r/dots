import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/**
 * The HyperNix status tile.
 *
 * Deliberately small and deliberately optional: it reports what the
 * toolkit says about itself and offers to open it. Halcyon does not
 * start training runs, and this tile does not pretend it can.
 */
GlassSurface {
    id: root

    level: 1
    radius: Theme.radiusLg
    padding: Theme.panelPaddingTight
    implicitHeight: layout.implicitHeight + padding * 2

    RowLayout {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.spacingMd

        Rectangle {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            radius: width / 2
            color: HyperNix.available ? Theme.surfaceSelected : Theme.surfaceSunken

            Icon {
                anchors.centerIn: parent
                glyph: "󰆧"
                size: 16
                color: HyperNix.available ? Theme.accentText : Theme.textTertiary
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            Label {
                Layout.fillWidth: true
                text: HyperNix.version.length > 0
                    ? "HyperNix " + HyperNix.version
                    : "HyperNix"
                variant: "body"
                font.weight: Theme.weightMedium
            }

            Label {
                Layout.fillWidth: true
                text: HyperNix.available
                    ? HyperNix.summary
                    : "Not installed — pip install hypernix"
                variant: "caption"
                tone: "tertiary"
            }
        }

        GlassIconButton {
            visible: HyperNix.available
            glyph: "󰆍"
            tooltip: "Open HyperNix"
            onClicked: {
                Overlays.close("control");
                HyperNix.launch();
            }
        }
    }
}
