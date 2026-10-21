import QtQuick
import QtQuick.Layouts
import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.ii.background.widgets

/**
 * Processor, memory and swap as three rings on a card in the theme's shape. Values come from ResourceUsage, which
 * the shell polls anyway.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "system"

    implicitWidth: 330
    implicitHeight: 142

    component Gauge: ColumnLayout {
        id: gauge

        required property string label
        required property real value
        required property color accent
        spacing: 2

        Item {
            Layout.alignment: Qt.AlignHCenter
            implicitWidth: 82
            implicitHeight: 82

            CircularProgress {
                anchors.fill: parent
                implicitSize: 82
                lineWidth: 7
                gapAngle: 0
                value: Math.max(0, Math.min(1, gauge.value))
                colPrimary: gauge.accent
                colSecondary: Qt.rgba(gauge.accent.r, gauge.accent.g, gauge.accent.b, 0.16)
            }
            StyledText {
                anchors.centerIn: parent
                text: `${Math.round(Math.max(0, Math.min(1, gauge.value)) * 100)}`
                font.pixelSize: 24
                font.weight: Font.Medium
                color: Appearance.colors.colOnLayer1
            }
        }
        StyledText {
            Layout.alignment: Qt.AlignHCenter
            text: gauge.label
            font.pixelSize: Appearance.font.pixelSize.smaller
            color: Appearance.colors.colSubtext
        }
    }

    ThemedPlate {
        anchors.fill: parent
        themeId: Config.options.halcyon.theme
        kind: "card"
        colBase: Appearance.colors.colLayer1
        colOn: Appearance.colors.colOnLayer1
        colAccent: Appearance.colors.colPrimary
    }

    RowLayout {
        anchors.centerIn: parent
        spacing: 14

        Gauge {
            label: Translation.tr("Processor")
            value: ResourceUsage.cpuUsage
            accent: Appearance.colors.colPrimary
        }
        Gauge {
            label: Translation.tr("Memory")
            value: ResourceUsage.memoryUsedPercentage
            accent: Appearance.colors.colTertiary
        }
        Gauge {
            label: Translation.tr("Swap")
            value: ResourceUsage.swapUsedPercentage
            accent: Appearance.colors.colSecondary
        }
    }
}
