import QtQuick

QtObject {
    required property var lastIpcObject
    readonly property string ssid: lastIpcObject.ssid
    readonly property string bssid: lastIpcObject.bssid
    readonly property int strength: lastIpcObject.strength
    readonly property int frequency: lastIpcObject.frequency
    readonly property bool active: lastIpcObject.active
    readonly property string security: lastIpcObject.security
    readonly property bool isSecure: security.length > 0
    // WPA2/WPA3 Enterprise (802.1X): a username as well as a password.
    readonly property bool isEnterprise: security.includes("802.1X")

    property bool askingPassword: false
    // Why the last attempt failed, when it was not just a missing password (a refused certificate, no address...).
    property string lastError: ""
}
