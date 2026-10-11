import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets
import qs.services
import qs.modules.common
import qs.modules.common.widgets

ContentPage {
    forceWidth: true

    ContentSection {
        icon: "box"
        title: Translation.tr("Distro")
        
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 20
            Layout.topMargin: 10
            Layout.bottomMargin: 10
            IconImage {
                implicitSize: 80
                source: Quickshell.iconPath(SystemInfo.logo)
            }
            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                // spacing: 10
                StyledText {
                    text: SystemInfo.distroName
                    font.pixelSize: Appearance.font.pixelSize.title
                }
                StyledText {
                    font.pixelSize: Appearance.font.pixelSize.normal
                    text: SystemInfo.homeUrl
                    textFormat: Text.MarkdownText
                    onLinkActivated: (link) => {
                        Qt.openUrlExternally(link)
                    }
                    PointingHandLinkHover {}
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 5

            RippleButtonWithIcon {
                materialIcon: "auto_stories"
                mainText: Translation.tr("Documentation")
                onClicked: {
                    Qt.openUrlExternally(SystemInfo.documentationUrl)
                }
            }
            RippleButtonWithIcon {
                materialIcon: "support"
                mainText: Translation.tr("Help & Support")
                onClicked: {
                    Qt.openUrlExternally(SystemInfo.supportUrl)
                }
            }
            RippleButtonWithIcon {
                materialIcon: "bug_report"
                mainText: Translation.tr("Report a Bug")
                onClicked: {
                    Qt.openUrlExternally(SystemInfo.bugReportUrl)
                }
            }
            RippleButtonWithIcon {
                materialIcon: "policy"
                materialIconFill: false
                mainText: Translation.tr("Privacy Policy")
                onClicked: {
                    Qt.openUrlExternally(SystemInfo.privacyPolicyUrl)
                }
            }
            
        }

    }
    ContentSection {
        icon: "folder_managed"
        title: Translation.tr("Dotfiles")

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 20
            Layout.topMargin: 10
            Layout.bottomMargin: 10
            // The mark on its own, without the dark tile the app icon has.
            Image {
                Layout.preferredWidth: 80
                Layout.preferredHeight: 80
                sourceSize.width: 80
                sourceSize.height: 80
                fillMode: Image.PreserveAspectFit
                source: Qt.resolvedUrl("../../assets/icons/halcyon-glyph.svg")
            }
            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                // spacing: 10
                StyledText {
                    text: "Halcyon"
                    font.pixelSize: Appearance.font.pixelSize.title
                }
                StyledText {
                    text: "https://github.com/trail-b1az3r/dots"
                    font.pixelSize: Appearance.font.pixelSize.normal
                    textFormat: Text.MarkdownText
                    onLinkActivated: (link) => {
                        Qt.openUrlExternally(link)
                    }
                    PointingHandLinkHover {}
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 5

            RippleButtonWithIcon {
                materialIcon: "auto_stories"
                mainText: Translation.tr("Documentation")
                onClicked: {
                    Qt.openUrlExternally("https://github.com/trail-b1az3r/dots#readme")
                }
            }
            RippleButtonWithIcon {
                materialIcon: "adjust"
                materialIconFill: false
                mainText: Translation.tr("Issues")
                onClicked: {
                    Qt.openUrlExternally("https://github.com/trail-b1az3r/dots/issues")
                }
            }
            
        }
    }
    ContentSection {
        icon: "volunteer_activism"
        title: Translation.tr("Credits")

        StyledText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Appearance.colors.colOnLayer1
            font.pixelSize: Appearance.font.pixelSize.small
            textFormat: Text.MarkdownText
            text: "Halcyon is built on [end-4's illogical-impulse](https://github.com/end-4/dots-hyprland), a Hyprland desktop under GPL-3.0. Its shell, settings and most of the desktop are that project's work.\n\n" +
                  "Also used:\n" +
                  "- [hyprland-revolver](https://github.com/minerofthesoal/hyprland-revolver) by minerofthesoal (MIT): the revolver's look and the game scan.\n" +
                  "- [StarRailRes](https://github.com/Mar-7th/StarRailRes) (AGPL-3.0): the Star Rail character index and portraits, downloaded when you ask for them. Not bundled.\n" +
                  "- [Bibata cursor](https://github.com/ful1e5/Bibata_Cursor) by ful1e5 (GPL-3.0): the cursor that Halcyon's glass cursor replaces.\n" +
                  "- [Quickshell](https://quickshell.org), [Hyprland](https://hyprland.org) and the Material Design symbols."
            onLinkActivated: (link) => {
                Qt.openUrlExternally(link)
            }
            PointingHandLinkHover {}
        }
    }

}
