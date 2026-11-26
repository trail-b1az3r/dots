import QtQuick
import qs.common
import qs.services

// The brightness, on the left of the bar: scroll to change it, click for the slider (popups/BrightnessPopup.qml).
BarButton {
    id: root
    required property var screen
    readonly property var monitor: Brightness.forScreen(root.screen)
    readonly property real level: Brightness.value(root.monitor)
    signal peek
    signal toggled

    icon: root.level < Brightness.split && root.monitor?.available ? "brightness_low"
        : root.level > 0.75 ? "light_mode" : "brightness_medium"
    onClicked: root.toggled()
    onScrolled: delta => {
        Brightness.step(root.monitor, delta > 0 ? 0.05 : -0.05);
        root.peek();
    }
}
