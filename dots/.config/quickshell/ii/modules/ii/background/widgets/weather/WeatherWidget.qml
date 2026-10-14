import QtQuick
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import qs.modules.common.widgets.widgetCanvas
import qs.modules.ii.background.widgets
import "../revolver/RevolverStyles.js" as Styles

AbstractBackgroundWidget {
    id: root

    configEntryName: "weather"

    implicitHeight: 200
    implicitWidth: 200

    // Under a Halcyon theme the card takes the theme's shape (as the revolver and the clock do); otherwise it is
    // upstream's pill.
    readonly property string themeId: Config.options.halcyon.theme
    readonly property bool themedCard: Styles.styleFor(themeId).id !== "default"
    readonly property bool redSun: Styles.styleFor(themeId).id === "red-sun"

    StyledDropShadow {
        visible: !root.themedCard
        target: backgroundShape
    }

    MaterialShape {
        id: backgroundShape
        anchors.fill: parent
        visible: !root.themedCard
        shape: MaterialShape.Shape.Pill
        color: Appearance.colors.colPrimaryContainer
        implicitSize: 200
    }

    ThemedPlate {
        anchors.fill: parent
        visible: root.themedCard
        themeId: root.themeId
        kind: "card"
        colBase: Appearance.colors.colLayer1
        colOn: Appearance.colors.colOnLayer1
        colAccent: Appearance.colors.colPrimary
    }

    StyledText {
        font {
            pixelSize: 80
            family: Appearance.font.family.expressive
            weight: Font.Medium
        }
        color: root.redSun ? "#ffe2d6" : Appearance.colors.colPrimary
        style: root.redSun ? Text.Raised : Text.Normal
        styleColor: "#ff4940"
        text: Weather.data?.temp.substring(0,Weather.data?.temp.length - 1) ?? "--°"
        anchors {
            right: parent.right
            top: parent.top
            rightMargin: 16
            topMargin: 20
        }
    }

    MaterialSymbol {
        iconSize: 80
        color: root.redSun ? "#ff4940" : Appearance.colors.colOnPrimaryContainer
        text: Icons.getWeatherIcon(Weather.data.wCode) ?? "cloud"
        anchors {
            left: parent.left
            bottom: parent.bottom

            leftMargin: 16
            bottomMargin: 20
        }
    }
}
