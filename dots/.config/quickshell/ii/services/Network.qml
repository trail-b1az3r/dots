pragma Singleton
pragma ComponentBehavior: Bound

// Took many bits from https://github.com/caelestia-dots/shell (GPLv3)

import Quickshell
import Quickshell.Io
import QtQuick
import qs.modules.common
import qs.modules.common.functions
import qs.services.network

/**
 * Network service. With nmx running (Nexora's network manager) it talks to nmxcli, which answers nmcli's commands
 * the same way; otherwise to NetworkManager's nmcli.
 */
Singleton {
    id: root

    property bool wifi: true
    property bool ethernet: false

    // nmxcli when nmx is running, nmcli otherwise (found once at start, by detectNmx).
    property string cli: "nmcli"
    readonly property bool usingNmx: cli === "nmxcli"
    onCliChanged: {
        subscriber.running = false;
        subscriber.running = true;
        update();
        getNetworks.running = true;
    }

    // On Nexora, nmx whenever it is the network manager there (running, or enabled and on its way back), so nothing
    // needs NetworkManager, nmtui or KDE's network settings. Elsewhere nmx only while it runs.
    property bool nexora: false
    readonly property string toolScript: FileUtils.trimFileProtocol(`${Directories.scriptPath}/network/network-tool.sh`)
    function redetect(): void {
        if (!detectNmx.running) detectNmx.running = true;
    }
    Process {
        id: detectNmx
        running: true
        // Same test as nmxcli -t -f RUNNING general, plus Nexora's rules (scripts/network/network-tool.sh).
        command: ["sh", root.toolScript]
        stdout: StdioCollector {
            onStreamFinished: {
                const lines = text.trim().split("\n");
                root.nexora = lines.includes("nexora");
                if (lines[0] === "nmxcli" || lines[0] === "nmcli") root.cli = lines[0];
            }
        }
    }
    Timer { // nmx enabled or started after the shell, or a switch back to NetworkManager
        interval: 30000
        repeat: true
        running: true
        onTriggered: root.redetect()
    }

    // ── Connectivity and captive portals ──
    // full, limited, portal (hotel/airport/café Wi-Fi waiting for a sign-in), none or unknown.
    property string connectivity: "unknown"
    // The sign-in page. nmx finds the real one; NetworkManager is given a plain-HTTP page the portal redirects.
    property string portalUrl: ""
    readonly property string portalFallback: "http://nmcheck.gnome.org/check_network_status.txt"
    onConnectivityChanged: {
        if (connectivity !== "portal") {
            portalUrl = "";
            return;
        }
        if (usingNmx) portalProc.running = true;
        portalNotice.running = true;
    }
    Process {
        id: portalProc
        command: ["nmxcli", "-t", "portal"]
        stdout: StdioCollector {
            onStreamFinished: if (text.trim().length > 0) root.portalUrl = text.trim()
        }
    }
    Process { // "Sign in" on the notification opens the portal; notify-send prints the action it was given
        id: portalNotice
        command: ["notify-send", "-a", "Shell", "-i", "network-wireless", "-A", "signin=" + Translation.tr("Sign in"),
            Translation.tr("Sign in to this network"),
            root.networkName.length > 0
                ? Translation.tr("%1 wants you to sign in before it lets you online.").arg(root.networkName)
                : Translation.tr("This network wants you to sign in before it lets you online.")]
        stdout: StdioCollector {
            onStreamFinished: if (text.trim() === "signin") root.openPublicWifiPortal()
        }
    }

    /** The network settings: nmx's own TUI with nmx, the configured app (nm-connection-editor or nmtui) otherwise. */
    function openSettings(ethernet = false): void {
        if (usingNmx) {
            Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} -e nmxtui`]);
            return;
        }
        Quickshell.execDetached(["bash", "-c", ethernet ? Config.options.apps.networkEthernet : Config.options.apps.network]);
    }

    property bool wifiEnabled: false
    property bool wifiScanning: false
    property bool wifiConnecting: connectProc.running
    property WifiAccessPoint wifiConnectTarget
    readonly property list<WifiAccessPoint> wifiNetworks: []
    readonly property WifiAccessPoint active: wifiNetworks.find(n => n.active) ?? null
    readonly property list<var> friendlyWifiNetworks: [...wifiNetworks].sort((a, b) => {
        if (a.active && !b.active)
            return -1;
        if (!a.active && b.active)
            return 1;
        return b.strength - a.strength;
    })
    property string wifiStatus: "disconnected"

    property string networkName: ""
    property int networkStrength
    property string materialSymbol: root.ethernet
        ? "lan"
        : (root.wifiEnabled && root.wifiStatus === "connected")
            ? (
                (root.active?.strength ?? 0) > 83 ? "signal_wifi_4_bar" :
                (root.active?.strength ?? 0) > 67 ? "network_wifi" :
                (root.active?.strength ?? 0) > 50 ? "network_wifi_3_bar" :
                (root.active?.strength ?? 0) > 33 ? "network_wifi_2_bar" :
                (root.active?.strength ?? 0) > 17 ? "network_wifi_1_bar" :
                "signal_wifi_0_bar"
            )
            : (root.wifiStatus === "connecting")
                ? "signal_wifi_statusbar_not_connected"
                : (root.wifiStatus === "disconnected")
                    ? "wifi_find"
                    : (root.wifiStatus === "disabled")
                        ? "signal_wifi_off"
                        : "signal_wifi_bad"

    // Control
    function enableWifi(enabled = true): void {
        const cmd = enabled ? "on" : "off";
        enableWifiProc.exec([root.cli, "radio", "wifi", cmd]);
    }

    function toggleWifi(): void {
        enableWifi(!wifiEnabled);
    }

    function rescanWifi(): void {
        wifiScanning = true;
        rescanProcess.running = true;
    }

    function connectToWifiNetwork(accessPoint: WifiAccessPoint): void {
        accessPoint.askingPassword = false;
        accessPoint.lastError = "";
        root.wifiConnectTarget = accessPoint;
        // We use this instead of `nmcli connection up SSID` because this also creates a connection profile
        connectProc.exec([root.cli, "dev", "wifi", "connect", accessPoint.ssid])

    }

    function disconnectWifiNetwork(): void {
        if (active) disconnectProc.exec([root.cli, "connection", "down", active.ssid]);
    }

    /** Open the captive portal's sign-in page. Plain HTTP when we do not know it, so the portal can redirect it. */
    function openPublicWifiPortal() {
        Quickshell.execDetached(["xdg-open", root.portalUrl.length > 0 ? root.portalUrl : root.portalFallback]);
        if (usingNmx) recheckTimer.restart();
    }
    Timer { // nmx checks every 15 s while signed out; ask again sooner after the page is opened
        id: recheckTimer
        interval: 20000
        onTriggered: Quickshell.execDetached(["nmxcli", "networking", "connectivity", "check"])
    }

    /** Connect with a password, and a username for enterprise (802.1X) networks. The secrets go through the
     *  environment, never the command line. */
    function changePassword(network: WifiAccessPoint, password: string, username = ""): void {
        network.askingPassword = false;
        network.lastError = "";
        root.wifiConnectTarget = network;
        if (root.usingNmx) {
            // nmx works out the rest itself: the EAP method, the certificates, the anonymous identity.
            const command = ["nmxcli", "dev", "wifi", "connect", network.ssid, "password", "env:NMX_PASSWORD"];
            if (network.isEnterprise)
                command.push("username", "env:NMX_USERNAME");
            connectProc.exec({
                "environment": { "NMX_PASSWORD": password, "NMX_USERNAME": username, "LANG": "C", "LC_ALL": "C" },
                "command": command
            });
            return;
        }
        changePasswordProc.exec({
            "environment": {
                "PASSWORD": password,
                "USERNAME": username,
                "SSID": network.ssid
            },
            "command": ["bash", "-c", network.isEnterprise
                // NetworkManager needs an enterprise profile made by hand: PEAP/MSCHAPv2, the common case.
                ? 'nmcli connection delete "$SSID" >/dev/null 2>&1; nmcli connection add type wifi con-name "$SSID" ssid "$SSID" '
                  + 'wifi-sec.key-mgmt wpa-eap 802-1x.eap peap 802-1x.phase2-auth mschapv2 '
                  + '802-1x.identity "$USERNAME" 802-1x.password "$PASSWORD"'
                : 'nmcli connection modify "$SSID" wifi-sec.psk "$PASSWORD"']
        })
    }

    Process {
        id: enableWifiProc
    }

    Process {
        id: connectProc
        environment: ({
            LANG: "C",
            LC_ALL: "C"
        })
        stdout: SplitParser {
            onRead: line => {
                // print(line)
                getNetworks.running = true
            }
        }
        stderr: SplitParser {
            onRead: line => {
                // print("err:", line)
                if (!root.wifiConnectTarget)
                    return;
                if (line.includes("Secrets were required")) {
                    root.wifiConnectTarget.askingPassword = true
                } else if (line.startsWith("Error:")) {
                    root.wifiConnectTarget.lastError = line.replace(/^Error: */, "")
                }
            }
        }
        onExited: (exitCode, exitStatus) => {
            if (root.wifiConnectTarget) {
                // A refused certificate or a DHCP timeout is not fixed by a password: say what it was instead.
                root.wifiConnectTarget.askingPassword = (exitCode !== 0) && root.wifiConnectTarget.lastError.length === 0
                    || root.wifiConnectTarget.askingPassword
            }
            root.wifiConnectTarget = null
            getNetworks.running = true
        }
    }

    Process {
        id: disconnectProc
        stdout: SplitParser {
            onRead: getNetworks.running = true
        }
    }

    Process {
        id: changePasswordProc
        onExited: { // Re-attempt connection after changing password
            connectProc.running = false
            connectProc.running = true
        }
    }

    Process {
        id: rescanProcess
        command: [root.cli, "dev", "wifi", "list", "--rescan", "yes"]
        stdout: SplitParser {
            onRead: {
                wifiScanning = false;
                getNetworks.running = true;
            }
        }
    }

    // Status update
    function update() {
        updateConnectionType.startCheck();
        wifiStatusProcess.running = true
        updateNetworkName.running = true;
        updateNetworkStrength.running = true;
    }

    Process {
        id: subscriber
        running: true
        command: [root.cli, "monitor"]
        stdout: SplitParser {
            onRead: root.update()
        }
        onExited: root.redetect() // the manager stopped (or was switched): find the one that is running now
    }

    Process {
        id: updateConnectionType
        property string buffer
        command: ["sh", "-c", `${root.cli} -t -f TYPE,STATE d status && ${root.cli} -t -f CONNECTIVITY g`]
        running: true
        function startCheck() {
            buffer = "";
            updateConnectionType.running = true;
        }
        stdout: SplitParser {
            onRead: data => {
                updateConnectionType.buffer += data + "\n";
            }
        }
        onExited: (exitCode, exitStatus) => {
            const lines = updateConnectionType.buffer.trim().split('\n');
            const connectivity = lines.pop() // none, limited, portal, full
            root.connectivity = connectivity || "unknown";
            let hasEthernet = false;
            let hasWifi = false;
            let wifiStatus = "disconnected";
            lines.forEach(line => {
                if (line.includes("ethernet") && line.includes("connected"))
                    hasEthernet = true;
                else if (line.includes("wifi:")) {
                    if (line.includes("disconnected")) {
                        wifiStatus = "disconnected"
                    }
                    else if (line.includes("connected")) {
                        hasWifi = true;
                        wifiStatus = "connected"

                        if (connectivity === "limited" || connectivity === "portal") {
                            hasWifi = false;
                            wifiStatus = "limited"
                        }
                    }
                    else if (line.includes("connecting")) {
                        wifiStatus = "connecting"
                    }
                    else if (line.includes("unavailable")) {
                        wifiStatus = "disabled"
                    }
                }
            });
            root.wifiStatus = wifiStatus;
            root.ethernet = hasEthernet;
            root.wifi = hasWifi;
        }
    }

    Process {
        id: updateNetworkName
        command: ["sh", "-c", `${root.cli} -t -f NAME c show --active | head -1`]
        running: true
        stdout: SplitParser {
            onRead: data => {
                root.networkName = data;
            }
        }
    }

    Process {
        id: updateNetworkStrength
        running: true
        command: ["sh", "-c", `${root.cli} -f IN-USE,SIGNAL,SSID device wifi | awk '/^\\*/{if (NR!=1) {print $2}}'`]
        stdout: SplitParser {
            onRead: data => {
                root.networkStrength = parseInt(data);
            }
        }
    }

    Process {
        id: wifiStatusProcess
        command: [root.cli, "radio", "wifi"]
        Component.onCompleted: running = true
        environment: ({
            LANG: "C",
            LC_ALL: "C"
        })
        stdout: StdioCollector {
            onStreamFinished: {
                root.wifiEnabled = text.trim() === "enabled";
            }
        }
    }

    Process {
        id: getNetworks
        running: true
        command: [root.cli, "-g", "ACTIVE,SIGNAL,FREQ,SSID,BSSID,SECURITY", "d", "w"]
        environment: ({
            LANG: "C",
            LC_ALL: "C"
        })
        stdout: StdioCollector {
            onStreamFinished: {
                const PLACEHOLDER = "STRINGWHICHHOPEFULLYWONTBEUSED";
                const rep = new RegExp("\\\\:", "g");
                const rep2 = new RegExp(PLACEHOLDER, "g");

                const allNetworks = text.trim().split("\n").map(n => {
                    const net = n.replace(rep, PLACEHOLDER).split(":");
                    return {
                        active: net[0] === "yes",
                        strength: parseInt(net[1]),
                        frequency: parseInt(net[2]),
                        ssid: net[3],
                        bssid: net[4]?.replace(rep2, ":") ?? "",
                        security: net[5] || ""
                    };
                }).filter(n => n.ssid && n.ssid.length > 0);

                // Group networks by SSID and prioritize connected ones
                const networkMap = new Map();
                for (const network of allNetworks) {
                    const existing = networkMap.get(network.ssid);
                    if (!existing) {
                        networkMap.set(network.ssid, network);
                    } else {
                        // Prioritize active/connected networks
                        if (network.active && !existing.active) {
                            networkMap.set(network.ssid, network);
                        } else if (!network.active && !existing.active) {
                            // If both are inactive, keep the one with better signal
                            if (network.strength > existing.strength) {
                                networkMap.set(network.ssid, network);
                            }
                        }
                        // If existing is active and new is not, keep existing
                    }
                }

                const wifiNetworks = Array.from(networkMap.values());

                const rNetworks = root.wifiNetworks;

                const destroyed = rNetworks.filter(rn => !wifiNetworks.find(n => n.frequency === rn.frequency && n.ssid === rn.ssid && n.bssid === rn.bssid));
                for (const network of destroyed)
                    rNetworks.splice(rNetworks.indexOf(network), 1).forEach(n => n.destroy());

                for (const network of wifiNetworks) {
                    const match = rNetworks.find(n => n.frequency === network.frequency && n.ssid === network.ssid && n.bssid === network.bssid);
                    if (match) {
                        match.lastIpcObject = network;
                    } else {
                        rNetworks.push(apComp.createObject(root, {
                            lastIpcObject: network
                        }));
                    }
                }
            }
        }
    }

    Component {
        id: apComp

        WifiAccessPoint {}
    }
}
