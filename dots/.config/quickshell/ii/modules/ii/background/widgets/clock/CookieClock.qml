pragma ComponentBehavior: Bound

import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import Quickshell.Io

import qs.modules.ii.background.widgets
import qs.modules.ii.background.widgets.clock.dateIndicator
import qs.modules.ii.background.widgets.clock.minuteMarks
import "../revolver/RevolverStyles.js" as Styles

Item {
    id: root

    readonly property string clockStyle: Config.options.background.widgets.clock.style

    property real implicitSize: 230

    property color colShadow: Appearance.colors.colShadow
    property color colBackground: Appearance.colors.colPrimaryContainer
    // On a themed face the marks and hands take the theme's look: ember and dawn on Red Sun, white on glass, the
    // palette's accents elsewhere. Upstream's cookie keeps upstream's colours.
    readonly property ThemeLook look: ThemeLook {}
    readonly property bool lookColours: look.id !== "default"
    property color colOnBackground: lookColours ? look.text : ColorUtils.mix(Appearance.colors.colSecondary, Appearance.colors.colPrimaryContainer, 0.15)
    property color colBackgroundInfo: lookColours ? look.subtext : ColorUtils.mix(Appearance.colors.colPrimary, Appearance.colors.colPrimaryContainer, 0.55)
    property color colHourHand: lookColours ? (look.id === "red-sun" || look.id === "glass" ? look.text : look.accentA) : Appearance.colors.colPrimary
    property color colMinuteHand: lookColours ? (look.id === "red-sun" || look.id === "glass" ? look.accentA : look.accentB) : Appearance.colors.colTertiary
    property color colSecondHand: lookColours ? look.glow : Appearance.colors.colPrimary

    readonly property list<string> clockNumbers: DateTime.time.split(/[: ]/)
    readonly property int clockHour: parseInt(clockNumbers[0]) % 12
    readonly property int clockMinute: DateTime.clock.minutes
    readonly property int clockSecond: DateTime.clock.seconds

    implicitWidth: implicitSize
    implicitHeight: implicitSize

    function applyStyle(sides, dialStyle, hourHandStyle, minuteHandStyle, secondHandStyle, dateStyle) {
        Config.options.background.widgets.clock.cookie.sides = sides
        Config.options.background.widgets.clock.cookie.dialNumberStyle = dialStyle
        Config.options.background.widgets.clock.cookie.hourHandStyle = hourHandStyle
        Config.options.background.widgets.clock.cookie.minuteHandStyle = minuteHandStyle
        Config.options.background.widgets.clock.cookie.secondHandStyle = secondHandStyle
        Config.options.background.widgets.clock.cookie.dateStyle = dateStyle
    }

    function setClockPreset(category) {
        if (!Config.options.background.widgets.clock.cookie.aiStyling) return;
        if (category === "") return;
        print("[Cookie clock] Setting clock preset for category: " + category)
        // "abstract", "anime", "city", "minimalist", "landscape", "plants", "person", "space"
        if (category == "abstract") {
            applyStyle(9, "none", "fill", "medium", "dot", "bubble")
        } else if (category == "anime") {
            applyStyle(7, "none", "fill", "bold", "dot", "bubble")
        } else if (category == "city" || category == "space") {
            applyStyle(23, "full", "hollow", "thin", "classic", "bubble")
        } else if (category == "minimalist") {
            applyStyle(6, "none", "fill", "bold", "dot", "hide")
        } else if (category == "landscape") {
            applyStyle(14, "full", "hollow", "medium", "classic", "bubble")
        } else if (category == "plants") {
            applyStyle(9, "dots", "fill", "bold", "dot", "border")
        } else if (category == "person") {
            applyStyle(14, "full", "classic", "classic", "classic", "rect")
        }
    }

    FileView {
        id: categoryFileView
        path: Config.ready ? Directories.generatedWallpaperCategoryPath : ""
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            root.setClockPreset(categoryFileView.text().trim())
        }
    }

    // Under a Halcyon theme the face takes the theme's shape (the same as the revolver's drum); otherwise it is
    // upstream's cookie.
    readonly property string themeId: Config.options.halcyon.theme
    readonly property bool themedFace: Styles.styleFor(themeId).id !== "default"
    // After ICEY, Manga Ink (and Dark) and Silence have a face of their own, drawn like their revolvers (ThemeClock.qml): the rest of
    // this file is the usual face, hidden under them.
    readonly property string customFace: ({ "icey": "icey", "ink": "ink", "ink-dark": "ink-dark", "silence": "silence" })[Styles.revolverStyleFor(themeId).id] ?? ""
    Loader {
        anchors.fill: parent
        z: 10
        active: root.customFace !== ""
        source: "ThemeClock.qml"   // by file, so a live reload finds it however the folder was imported
        onLoaded: {
            item.kind = Qt.binding(() => root.customFace);
            item.now = Qt.binding(() => DateTime.clock.date);
            item.showSeconds = Qt.binding(() => Config.options.time.secondPrecision);
            item.colAccent = Qt.binding(() => Appearance.colors.colPrimary);
            item.colAccent2 = Qt.binding(() => Appearance.colors.colTertiary);
            item.colOn = Qt.binding(() => Appearance.colors.colOnLayer1);
            item.colBase = Qt.binding(() => Qt.rgba(Appearance.colors.colLayer0.r, Appearance.colors.colLayer0.g, Appearance.colors.colLayer0.b, 1));
            item.fontFamily = Qt.binding(() => Appearance.font.family.main);
            item.renderScale = Qt.binding(() => root.width / 230 * (root.QsWindow?.window?.devicePixelRatio ?? 1));
        }
    }
    ThemedPlate {
        anchors.fill: parent
        visible: root.themedFace && root.customFace === ""
        themeId: root.themeId
        kind: "disc"
        colBase: Appearance.colors.colLayer1
        colOn: root.colOnBackground
        colAccent: Appearance.colors.colPrimary
    }

    property bool useSineCookie: Config.options.background.widgets.clock.cookie.useSineCookie
    StyledDropShadow {
        visible: !root.themedFace
        target: root.useSineCookie ? sineCookieLoader : roundedPolygonCookieLoader

        RotationAnimation on rotation {
            running: Config.options.background.widgets.clock.cookie.constantlyRotate
            duration: 30000
            easing.type: Easing.Linear
            loops: Animation.Infinite
            from: 360
            to: 0
        }
    }
    Loader {
        id: sineCookieLoader
        z: 0
        visible: false // The DropShadow already draws it
        active: root.useSineCookie
        sourceComponent: SineCookie {
            implicitSize: root.implicitSize
            sides: Config.options.background.widgets.clock.cookie.sides
            color: root.colBackground
        }
    }
    Loader {
        id: roundedPolygonCookieLoader
        z: 0
        visible: false // The DropShadow already draws it
        active: !root.useSineCookie
        sourceComponent: MaterialCookie {
            implicitSize: root.implicitSize
            sides: Config.options.background.widgets.clock.cookie.sides
            color: root.colBackground
        }
    }

    // Hour/minutes numbers/dots/lines
    MinuteMarks {
        anchors.fill: parent
        visible: root.customFace === ""
        color: root.colOnBackground
    }

    // Stupid extra hour marks in the middle
    FadeLoader {
        id: hourMarksLoader
        anchors.centerIn: parent
        shown: root.customFace === "" && (Config.options.background.widgets.clock.cookie.hourMarks)
        sourceComponent: HourMarks {
            implicitSize: 135 * (1.75 - 0.75 * hourMarksLoader.opacity)
            color: root.colOnBackground
            colOnBackground: ColorUtils.mix(root.colBackgroundInfo, root.colOnBackground, 0.5)
        }
    }

    // Number column in the middle
    FadeLoader {
        id: timeColumnLoader
        anchors.centerIn: parent
        shown: root.customFace === "" && (Config.options.background.widgets.clock.cookie.timeIndicators)
        scale: 1.4 - 0.4 * timeColumnLoader.shown
        Behavior on scale {
            animation: Appearance.animation.elementResize.numberAnimation.createObject(this)
        }

        sourceComponent: TimeColumn {
            color: root.colBackgroundInfo
        }
    }

    // Minute hand
    FadeLoader {
        anchors.fill: parent
        z: 1
        shown: root.customFace === "" && (Config.options.background.widgets.clock.cookie.minuteHandStyle !== "hide")
        sourceComponent: MinuteHand {
            anchors.fill: parent
            clockMinute: root.clockMinute
            style: Config.options.background.widgets.clock.cookie.minuteHandStyle
            color: root.colMinuteHand
        }
    }

    // Hour hand
    FadeLoader {
        anchors.fill: parent
        z: item?.style === "hollow" ? 0 : 2
        shown: root.customFace === "" && (Config.options.background.widgets.clock.cookie.hourHandStyle !== "hide")
        sourceComponent: HourHand {
            clockHour: root.clockHour
            clockMinute: root.clockMinute
            style: Config.options.background.widgets.clock.cookie.hourHandStyle
            color: root.colHourHand
        }
    }

    // Second hand
    FadeLoader {
        id: secondHandLoader
        z: (Config.options.background.widgets.clock.cookie.secondHandStyle === "line") ? 2 : 3
        shown: root.customFace === "" && (Config.options.time.secondPrecision && Config.options.background.widgets.clock.cookie.secondHandStyle !== "hide")
        anchors.fill: parent
        sourceComponent: SecondHand {
            id: secondHand
            clockSecond: root.clockSecond
            style: Config.options.background.widgets.clock.cookie.secondHandStyle
            color: root.colSecondHand
        }
    }

    // Center dot
    FadeLoader {
        z: 4
        anchors.centerIn: parent
        shown: root.customFace === "" && (Config.options.background.widgets.clock.cookie.minuteHandStyle !== "bold")
        sourceComponent: Rectangle {
            color: Config.options.background.widgets.clock.cookie.minuteHandStyle === "medium" ? root.colBackground : root.colMinuteHand
            implicitWidth: 6
            implicitHeight: implicitWidth
            radius: width / 2
        }
    }

    // Date
    FadeLoader {
        anchors.fill: parent
        shown: root.customFace === "" && (Config.options.background.widgets.clock.cookie.dateStyle !== "hide")

        sourceComponent: DateIndicator {
            color: root.colBackgroundInfo
            style: Config.options.background.widgets.clock.cookie.dateStyle
        }
    }
}
