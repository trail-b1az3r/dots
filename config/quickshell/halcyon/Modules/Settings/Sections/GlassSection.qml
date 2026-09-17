import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    readonly property var presets: [
        { id: "ultra-clear", title: "Ultra Clear" },
        { id: "clear", title: "Clear" },
        { id: "tinted", title: "Tinted" },
        { id: "dark-glass", title: "Dark Glass" },
        { id: "light-glass", title: "Light Glass" },
        { id: "oled", title: "OLED" }
    ]

    SettingsGroup {
        title: "Preset"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "A preset sets every value below at once. Changing any of "
                    + "them afterwards keeps your change."
                variant: "caption"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spacingSm

                Repeater {
                    model: root.presets

                    GlassButton {
                        required property var modelData
                        text: modelData.title
                        variant: Config.get("glass.preset", "tinted") === modelData.id
                            ? "filled" : "tinted"
                        onClicked: Config.applyPreset(modelData.id)
                    }
                }
            }
        }
    }

    SettingsGroup {
        title: "Surface"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            GlassSetting {
                path: "glass.opacity"
                title: "Opacity"
                prose: "How solid a panel is before the compositor blurs behind it."
                from: 0.05; to: 1.0; step: 0.02; fallback: 0.6
            }

            GlassSetting {
                path: "glass.blurStrength"
                title: "Blur strength"
                prose: "Scales the compositor's blur radius."
                from: 0.0; to: 2.0; step: 0.05; fallback: 1.0
            }

            GlassSetting {
                path: "glass.saturation"
                title: "Saturation"
                prose: "Lifts the colour of whatever shows through."
                from: 0.5; to: 2.0; step: 0.05; fallback: 1.2
            }

            GlassSetting {
                path: "glass.tintStrength"
                title: "Tint"
                prose: "How far surfaces lean toward the accent colour."
                from: 0.0; to: 1.0; step: 0.02; fallback: 0.22
            }

            GlassSetting {
                path: "glass.borderOpacity"
                title: "Border"
                from: 0.0; to: 1.0; step: 0.02; fallback: 0.34
            }

            GlassSetting {
                path: "glass.specularStrength"
                title: "Highlight"
                prose: "The sheen along the top edge of a panel."
                from: 0.0; to: 1.0; step: 0.02; fallback: 0.5
            }

            GlassSetting {
                path: "glass.refraction"
                title: "Refraction"
                prose: "How much the edges appear to bend light."
                from: 0.0; to: 1.0; step: 0.02; fallback: 0.4
            }

            GlassSetting {
                path: "glass.noise"
                title: "Noise"
                prose: "A trace of grain, which stops large blurred areas banding."
                from: 0.0; to: 0.06; step: 0.002; fallback: 0.012
            }
        }
    }

    SettingsGroup {
        title: "Geometry"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            GlassSetting {
                path: "glass.cornerRadius"
                title: "Corner radius"
                from: 0; to: 40; step: 1; fallback: 18; integer: true; suffix: " px"
            }

            GlassSetting {
                path: "glass.shadowStrength"
                title: "Shadow"
                from: 0.0; to: 1.5; step: 0.05; fallback: 0.55
            }

            GlassSetting {
                path: "glass.elevationSpread"
                title: "Depth"
                prose: "How far apart the shadow levels sit."
                from: 0.2; to: 2.0; step: 0.05; fallback: 1.0
            }

            GlassSetting {
                path: "glass.panelPadding"
                title: "Panel padding"
                from: 0; to: 32; step: 1; fallback: 12; integer: true; suffix: " px"
            }

            GlassSetting {
                path: "glass.widgetSpacing"
                title: "Widget spacing"
                from: 0; to: 32; step: 1; fallback: 10; integer: true; suffix: " px"
            }
        }
    }
}
