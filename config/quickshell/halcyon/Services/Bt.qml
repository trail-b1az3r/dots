pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Bluetooth
import qs.Config

/**
 * Bluetooth, through BlueZ.
 *
 * Discovery is only on while the Control Center's Bluetooth panel is
 * open, for the same reason Wi-Fi scanning is: an always-discovering
 * adapter is a measurable amount of idle power and a privacy signal the
 * user did not ask to broadcast.
 */
Singleton {
    id: root

    readonly property BluetoothAdapter adapter: Bluetooth.defaultAdapter
    readonly property bool available: root.adapter !== null
    readonly property bool enabled: root.adapter?.enabled ?? false
    readonly property bool discovering: root.adapter?.discovering ?? false

    readonly property var devices: Bluetooth.devices.values

    readonly property var connectedDevices:
        root.devices.filter(device => device.connected)

    readonly property var pairedDevices:
        root.devices.filter(device => device.paired && !device.connected)

    readonly property var nearbyDevices:
        root.devices.filter(device => !device.paired && device.deviceName.length > 0)

    readonly property string glyph: {
        if (!root.available || !root.enabled) return "󰂲";
        if (root.connectedDevices.length > 0) return "󰂱";
        return "󰂯";
    }

    readonly property string summary: {
        if (!root.available) return "No adapter";
        if (!root.enabled) return "Off";
        const count = root.connectedDevices.length;
        if (count === 1) return root.connectedDevices[0].deviceName;
        if (count > 1) return count + " devices";
        return "On";
    }

    property bool scanning: false
    onScanningChanged: {
        if (root.adapter && root.enabled)
            root.adapter.discovering = root.scanning;
    }

    function setEnabled(value: bool): void {
        if (root.adapter)
            root.adapter.enabled = value;
    }

    function toggle(): void { root.setEnabled(!root.enabled); }

    function connectDevice(device: var): void {
        if (!device)
            return;
        if (device.paired)
            device.connect();
        else
            device.pair();
    }

    function disconnectDevice(device: var): void { device?.disconnect(); }
    function forgetDevice(device: var): void { device?.forget(); }

    function deviceGlyph(device: var): string {
        const icon = String(device?.icon ?? "");
        if (icon.indexOf("audio-headset") >= 0 || icon.indexOf("headphone") >= 0)
            return "󰋋";
        if (icon.indexOf("audio") >= 0) return "󰓃";
        if (icon.indexOf("input-keyboard") >= 0) return "󰌌";
        if (icon.indexOf("input-mouse") >= 0) return "󰍽";
        if (icon.indexOf("phone") >= 0) return "󰄜";
        if (icon.indexOf("computer") >= 0) return "󰟀";
        return "󰂯";
    }
}
