pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Networking
import qs.Config

/**
 * Wi-Fi and wired networking, through NetworkManager.
 *
 * The scanner is only enabled while a surface is actually showing the
 * network list: a continuous Wi-Fi scan wakes the radio every few
 * seconds and is one of the classic reasons a laptop's idle drain is
 * worse under a custom desktop than under GNOME.
 */
Singleton {
    id: root

    readonly property var devices: Networking.devices.values

    readonly property var wifiDevice:
        root.devices.find(device => device.type === DeviceType.Wifi) ?? null
    readonly property var wiredDevice:
        root.devices.find(device => device.type === DeviceType.Ethernet) ?? null

    readonly property bool wifiEnabled: Networking.wifiEnabled
    readonly property bool wifiHardwareEnabled: Networking.wifiHardwareEnabled

    readonly property var activeNetwork: {
        const wifi = root.wifiDevice;
        if (wifi && wifi.connected) {
            const networks = wifi.networks?.values ?? [];
            return networks.find(network => network.connected) ?? null;
        }
        return null;
    }

    readonly property bool wiredConnected: root.wiredDevice?.connected ?? false
    readonly property bool connected: root.wiredConnected || (root.activeNetwork !== null)

    readonly property string connectionName: {
        if (root.wiredConnected)
            return root.wiredDevice?.network?.name ?? "Wired";
        return root.activeNetwork?.name ?? "";
    }

    readonly property int signalStrength:
        Math.round(root.activeNetwork?.signalStrength ?? 0)

    readonly property string glyph: {
        if (root.wiredConnected) return "󰈀";
        if (!root.wifiEnabled) return "󰖪";
        if (!root.connected) return "󰖪";
        if (root.signalStrength >= 75) return "󰤨";
        if (root.signalStrength >= 50) return "󰤥";
        if (root.signalStrength >= 25) return "󰤢";
        return "󰤟";
    }

    readonly property string summary: {
        if (root.wiredConnected) return "Wired";
        if (!root.wifiEnabled) return "Wi-Fi off";
        if (root.connected) return root.connectionName;
        return "Not connected";
    }

    /** Visible networks, strongest first, with duplicates removed. */
    readonly property var networks: {
        const wifi = root.wifiDevice;
        if (!wifi)
            return [];
        const seen = {};
        const out = [];
        for (const network of wifi.networks?.values ?? []) {
            if (!network.name || network.name.length === 0)
                continue;
            const existing = seen[network.name];
            if (existing !== undefined) {
                // The same SSID on two access points: keep the stronger.
                if (network.signalStrength > out[existing].signalStrength)
                    out[existing] = network;
                continue;
            }
            seen[network.name] = out.length;
            out.push(network);
        }
        return out.sort((a, b) => b.signalStrength - a.signalStrength);
    }

    /** Turn scanning on only while something is looking at the list. */
    property bool scanning: false
    onScanningChanged: {
        if (root.wifiDevice)
            root.wifiDevice.scannerEnabled = root.scanning;
    }

    function setWifiEnabled(value: bool): void {
        Networking.wifiEnabled = value;
    }

    function toggleWifi(): void {
        root.setWifiEnabled(!root.wifiEnabled);
    }

    function connect(network: var, password: string): void {
        if (!network)
            return;
        if (password && password.length > 0 && network.connectWithPsk)
            network.connectWithPsk(password);
        else
            network.connect();
    }

    function disconnect(): void {
        root.wifiDevice?.disconnect();
    }

    function forget(network: var): void {
        network?.forget();
    }

    function securityLabel(network: var): string {
        if (!network)
            return "";
        switch (network.security) {
        case WifiSecurityType.None: return "Open";
        case WifiSecurityType.Wep: return "WEP";
        case WifiSecurityType.Wpa: return "WPA";
        case WifiSecurityType.Wpa2: return "WPA2";
        case WifiSecurityType.Wpa3: return "WPA3";
        default: return "Secured";
        }
    }
}
