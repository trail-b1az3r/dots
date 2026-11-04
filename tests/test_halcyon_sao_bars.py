"""The Sword Art Online theme's own top bar (the game's HUD), dock buttons and menu panels.
Run: python3 -m unittest discover -s tests"""

import re
import unittest
from pathlib import Path

II = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii"
BAR = (II / "modules/ii/bar/BarContent.qml").read_text()
HUD = (II / "modules/ii/bar/SaoBar.qml").read_text()
PANEL = (II / "modules/common/widgets/SaoPanel.qml").read_text()
POPUP = (II / "modules/ii/bar/StyledPopup.qml").read_text()
TRAY = (II / "modules/ii/bar/SysTrayMenu.qml").read_text()
DOCK_BUTTON = (II / "modules/ii/dock/DockAppButton.qml").read_text()
FRAME = (II / "modules/ii/dock/DockFrame.qml").read_text()


class SaoTopBarTest(unittest.TestCase):
    def test_the_hud_replaces_the_bar_in_the_theme(self):
        self.assertIn('Config.options.halcyon.theme === "sword-art-online"', BAR)
        self.assertIn('source: "SaoBar.qml"', BAR)
        # The stock sections step aside, and neither the plain panel nor the frame is drawn behind the HUD.
        self.assertEqual(BAR.count("visible: !root.sao"), 3)
        self.assertIn('!root.sao ? Styles.frameKindFor', BAR)
        self.assertIn('opacity: root.frameKind !== "" || root.sao ? 0 : 1', BAR)

    def test_the_player_floors_and_menu(self):
        self.assertIn("onBattery ? Battery.percentage : 1 - ResourceUsage.memoryUsedPercentage", HUD)
        self.assertIn('hp > 0.5 ? "#7FD15B" : hp > 0.2 ? "#F2C94C"', HUD)       # green, yellow, red as it empties
        self.assertIn("SystemInfo.username", HUD)
        self.assertIn("hl.dsp.focus({workspace = ${floorMark.floorId}})", HUD)
        self.assertIn('hl.dsp.focus({workspace = "r+1"})', HUD)
        self.assertIn("GlobalStates.overviewOpen = !GlobalStates.overviewOpen", HUD)   # the game's main menu
        self.assertIn("GlobalStates.sidebarLeftOpen = !GlobalStates.sidebarLeftOpen", HUD)
        self.assertIn("GlobalStates.sidebarRightOpen = !GlobalStates.sidebarRightOpen", HUD)
        self.assertIn("badge: Notifications.unread", HUD)
        for popup in ("BatteryPopup", "ClockWidgetPopup", "SysTray"):
            self.assertIn(popup + " {", HUD)

    def test_scrolling_keeps_its_jobs(self):
        self.assertIn("Brightness.increaseBrightness()", HUD)
        self.assertIn("Audio.incrementVolume()", HUD)


class SaoDockAndMenusTest(unittest.TestCase):
    def test_dock_apps_are_round_buttons(self):
        self.assertIn('readonly property bool sao: Config.options.halcyon.theme === "sword-art-online"', DOCK_BUTTON)
        self.assertIn("root.sao ? Math.round(root.iconSize * 0.7) : root.iconSize", DOCK_BUTTON)
        self.assertIn("rotation: root.sao ? 45 : 0", DOCK_BUTTON)                 # diamonds for open windows
        # Other themes keep the button's usual colours.
        self.assertIn('sao ? "transparent" : (Appearance?.colors.colLayer1Hover', DOCK_BUTTON)

    def test_popups_and_tray_menus_are_sao_panels(self):
        self.assertIn("sourceComponent: SaoPanel", POPUP)
        self.assertIn('Config.options.bar.bottom ? "bottom" : "top"', POPUP)
        self.assertIn("sourceComponent: SaoPanel { pointer: \"\" }", TRAY)
        self.assertIn('color: sao ? "transparent" : Appearance.colors.colLayer0', TRAY)

    def test_colour_strings_are_not_black(self):
        # withAlpha("#28313C", a) read .r off a string and drew black: typed, the string is made a colour first.
        for name, text in (("SaoPanel", PANEL), ("DockFrame", FRAME)):
            self.assertIn("function withAlpha(colour: color, alpha: real): color", text, name)
            self.assertNotRegex(text, r"function withAlpha\(colour, alpha\)", name)
        self.assertTrue(re.search(r'withAlpha\("#28313C"', PANEL))
        # The same helper elsewhere (themed plates, the revolver, the clocks) is typed too.
        untyped = [str(p.relative_to(II)) for p in II.rglob("*.qml")
                   if re.search(r"function withAlpha\(colour, alpha\)", p.read_text(errors="replace"))]
        self.assertEqual(untyped, [])


if __name__ == "__main__":
    unittest.main()
