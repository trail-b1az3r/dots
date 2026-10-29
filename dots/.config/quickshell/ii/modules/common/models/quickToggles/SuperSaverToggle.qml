import QtQuick
import Quickshell
import qs
import qs.services
import qs.modules.common

// The super battery saver (SuperSaver): 12 fps, 20% brightness, power saver, and Wi-Fi that only reconnects when
// you wake, lock or unlock the computer or pick a network. Off puts back what it found.
QuickToggleModel {
    name: Translation.tr("Super saver")
    statusText: SuperSaver.active ? Translation.tr("12 fps, 20%") : Translation.tr("Off")
    icon: "battery_saver"
    toggled: SuperSaver.active
    mainAction: () => SuperSaver.toggle()
    tooltipText: SuperSaver.active
        ? Translation.tr("Super battery saver is on: 12 fps, 20% brightness, power saver, Wi-Fi reconnects only on wake, lock, unlock or when you pick a network. Click to turn it off and put everything back.")
        : Translation.tr("Super battery saver: 12 fps, 20% brightness, power saver, and Wi-Fi stops reconnecting by itself")
}
