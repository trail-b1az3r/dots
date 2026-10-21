pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.ii.background.widgets

/**
 * Processor, memory and swap on a card in the theme's shape, each as the theme draws a gauge (ThemedGauge): lit
 * rings on Red Sun, facets on glass, gold rails on Star Rail, keycaps on the anime themes. HyperNeo nests the three
 * as activity rings with a legend. Values come from ResourceUsage, which the shell polls anyway.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "system"

    readonly property ThemeLook look: ThemeLook {}
    readonly property bool activity: look.spec.gauge === "activity"
    readonly property var readings: [
        { label: Translation.tr("Processor"), value: ResourceUsage.cpuUsage, accent: look.accentA },
        { label: Translation.tr("Memory"), value: ResourceUsage.memoryUsedPercentage, accent: look.accentB },
        { label: Translation.tr("Swap"), value: ResourceUsage.swapUsedPercentage, accent: look.accentC }
    ]

    implicitWidth: 330
    implicitHeight: activity ? 162 : (look.spec.gauge === "key" ? 150 : 142)

    ThemedPlate {
        anchors.fill: parent
        themeId: root.look.themeId
        kind: "card"
        colBase: Appearance.colors.colLayer1
        colOn: Appearance.colors.colOnLayer1
        colAccent: Appearance.colors.colPrimary
    }

    RowLayout {
        anchors.centerIn: parent
        visible: !root.activity
        spacing: 14

        Repeater {
            model: root.activity ? [] : root.readings
            delegate: ThemedGauge {
                required property var modelData
                look: root.look
                label: modelData.label
                value: modelData.value
                accent: modelData.accent
            }
        }
    }

    // HyperNeo: three rings inside each other, the outermost the processor, and a legend beside them.
    RowLayout {
        anchors.centerIn: parent
        visible: root.activity
        spacing: 22

        Item {
            implicitWidth: 120
            implicitHeight: 120
            Repeater {
                model: root.activity ? root.readings : []
                delegate: CircularProgress {
                    required property var modelData
                    required property int index
                    anchors.centerIn: parent
                    implicitSize: 120 - index * 30
                    width: implicitSize
                    height: implicitSize
                    lineWidth: 12
                    gapAngle: 0
                    value: Math.max(0, Math.min(1, modelData.value))
                    colPrimary: modelData.accent
                    colSecondary: Qt.rgba(modelData.accent.r, modelData.accent.g, modelData.accent.b, 0.2)
                }
            }
        }
        ColumnLayout {
            spacing: 6
            Repeater {
                model: root.activity ? root.readings : []
                delegate: ColumnLayout {
                    required property var modelData
                    spacing: -2
                    StyledText {
                        text: modelData.label
                        font.pixelSize: Appearance.font.pixelSize.smaller
                        color: root.look.subtext
                    }
                    StyledText {
                        text: `${Math.round(Math.max(0, Math.min(1, modelData.value)) * 100)}%`
                        font.pixelSize: Appearance.font.pixelSize.larger
                        font.weight: Font.DemiBold
                        color: modelData.accent
                    }
                }
            }
        }
    }
}
