#!/usr/bin/env python3
"""Wi-Fi when Hyprland starts: `halcyon wifi`.

    halcyon wifi            what NetworkManager sees, and what stands in the way
    halcyon wifi boot       get the Wi-Fi up (Hyprland runs this at login)
    halcyon wifi fix        the lasting fixes, as root (asks for sudo)
    halcyon wifi report     everything above plus NetworkManager's log, in one file to send when it still fails
    halcyon wifi --json

The shell's network menu and the login use NetworkManager (nmcli). Why a laptop's Wi-Fi can be left off at login,
above all a Microsoft Surface, whose Marvell card (the mwifiex_pcie driver) is slow to start and fussy:

  - The card isn't ready when the session starts: its firmware is still loading, so NetworkManager lists the device
    as "unavailable", or not at all, for a few seconds. `boot` waits for it.
  - NetworkManager lists the device as "unmanaged", so it never connects it. `boot` hands it back to NetworkManager
    (nmcli device set DEV managed yes) for this session; `fix` writes a NetworkManager setting so it stays managed.
    Something else may claim it: a keyfile `unmanaged-devices` line or a udev rule (NM_UNMANAGED); `status` says.
  - iwd is running next to NetworkManager, which uses wpa_supplicant: both try to drive the card. `fix` makes
    NetworkManager use iwd (wifi.backend=iwd), so they stop fighting and the networks iwd knows stay known. (It
    used to turn iwd off, which left a computer set up with iwd alone with no Wi-Fi at all.)
  - NetworkManager isn't installed (the shell's network menu needs it) or isn't running (not enabled at boot). `fix`
    installs it with pacman and enables it.
  - The radio is off (nmcli radio wifi) or blocked (rfkill). `boot` turns it on.
  - On mwifiex cards, NetworkManager's random MAC address while scanning and Wi-Fi power saving make connections
    fail or drop; the linux-surface project's advice is to turn both off for this card. `fix` does that, for this
    card only.

`fix` writes /etc/NetworkManager/conf.d/90-halcyon-wifi.conf; delete it (and restart NetworkManager) to undo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SYS = Path(os.environ.get("HALCYON_SYSFS", "/sys"))
CONF = Path(os.environ.get("HALCYON_NM_CONF", "/etc/NetworkManager/conf.d/90-halcyon-wifi.conf"))
NM_CONF_DIRS = [Path("/etc/NetworkManager/NetworkManager.conf"), Path("/etc/NetworkManager/conf.d"),
                Path("/usr/lib/NetworkManager/conf.d"), Path("/run/NetworkManager/conf.d")]
STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "halcyon"
LOG = STATE / "wifi.log"
HERE = Path(__file__).resolve().parent

# Seconds to wait, at login, for NetworkManager, then for the card, then for a connection. Tests make them short.
WAIT_NM = float(os.environ.get("HALCYON_WIFI_WAIT_NM", 20))
WAIT_DEVICE = float(os.environ.get("HALCYON_WIFI_WAIT_DEVICE", 30))
WAIT_CONNECT = float(os.environ.get("HALCYON_WIFI_WAIT_CONNECT", 30))
POLL = float(os.environ.get("HALCYON_WIFI_POLL", 1))

MWIFIEX = ("mwifiex_pcie", "mwifiex_sdio", "mwifiex_usb", "mwifiex")


def run(cmd: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(cmd, 127, "", str(error))


def log(message: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + message
    print(message)
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        run(["notify-send", "-a", "Halcyon", "-i", "network-wireless-offline", title, body])


def unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def split_terse(line: str) -> list[str]:
    """One line of `nmcli -t` output: fields split on ':' that isn't escaped."""
    return [unescape(field) for field in re.split(r"(?<!\\):", line)]


# --- what is there --------------------------------------------------------------------------------------------------

def nm_installed() -> bool:
    return bool(shutil.which("NetworkManager") or shutil.which("nmcli"))


def iwd_connected() -> bool:
    """Whether iwd (on its own, without NetworkManager) has a station connected."""
    if not shutil.which("iwctl"):
        return False
    out = run(["iwctl", "station", "list"]).stdout
    return re.search(r"\bconnected\b", re.sub(r"\x1b\[[0-9;]*m", "", out)) is not None


def nm_running() -> bool:
    return run(["nmcli", "-t", "-f", "RUNNING", "general"]).stdout.strip() == "running"


def wifi_devices() -> list[dict]:
    """[{device, state, connection}] for each Wi-Fi device NetworkManager lists (p2p devices left out)."""
    out = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]).stdout
    found = []
    for line in out.splitlines():
        fields = split_terse(line)
        if len(fields) >= 3 and fields[1] == "wifi":
            found.append({"device": fields[0], "state": fields[2].split(" ")[0],
                          "connection": fields[3] if len(fields) > 3 and fields[3] != "--" else ""})
    return found


def kernel_wifi_interfaces() -> list[str]:
    """Wi-Fi interfaces the kernel has, whether or not NetworkManager lists them."""
    net = SYS / "class/net"
    try:
        return sorted(p.name for p in net.iterdir() if (p / "wireless").exists() or (p / "phy80211").exists())
    except OSError:
        return []


def driver_of(interface: str) -> str:
    try:
        return (SYS / "class/net" / interface / "device/driver").resolve().name
    except OSError:
        return ""


def is_surface() -> bool:
    try:
        vendor = (SYS / "class/dmi/id/sys_vendor").read_text().strip()
        product = (SYS / "class/dmi/id/product_name").read_text().strip()
    except OSError:
        return False
    return vendor.startswith("Microsoft") and product.startswith("Surface")


def rfkill_wifi() -> dict:
    """{'soft': bool, 'hard': bool} for the Wi-Fi radios, from sysfs."""
    soft = hard = False
    try:
        for entry in (SYS / "class/rfkill").iterdir():
            if (entry / "type").read_text().strip() != "wlan":
                continue
            soft |= (entry / "soft").read_text().strip() == "1"
            hard |= (entry / "hard").read_text().strip() == "1"
    except OSError:
        pass
    return {"soft": soft, "hard": hard}


def radio_on() -> bool:
    return run(["nmcli", "radio", "wifi"]).stdout.strip() == "enabled"


def unit_active(unit: str) -> bool:
    return run(["systemctl", "is-active", "--quiet", unit]).returncode == 0


def unit_enabled(unit: str) -> bool:
    return run(["systemctl", "is-enabled", "--quiet", unit]).returncode == 0


def nm_config_text() -> str:
    """NetworkManager's configuration as it reads it, or the files themselves when that can't be asked."""
    printed = run(["NetworkManager", "--print-config"])
    if printed.returncode == 0 and printed.stdout:
        return printed.stdout
    text = []
    for place in NM_CONF_DIRS:
        files = sorted(place.glob("*.conf")) if place.is_dir() else [place]
        for path in files:
            try:
                text.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    return "\n".join(text)


def iwd_backend(config: str) -> bool:
    return re.search(r"^\s*wifi\.backend\s*=\s*iwd\s*$", config, re.M) is not None


def unmanaged_by_config(config: str, interface: str) -> str:
    """The `unmanaged-devices` line that names this interface (or all Wi-Fi), or ""."""
    for match in re.finditer(r"^\s*unmanaged-devices\s*=\s*(.+)$", config, re.M):
        for spec in match.group(1).split(";"):
            spec = spec.strip()
            if spec in ("*", f"interface-name:{interface}", "type:wifi") or (
                    spec.startswith("interface-name:") and _glob(spec.split(":", 1)[1], interface)):
                return match.group(0).strip()
    return ""


def _glob(pattern: str, name: str) -> bool:
    from fnmatch import fnmatch
    return fnmatch(name, pattern.lstrip("~="))


def unmanaged_by_udev(interface: str) -> bool:
    out = run(["udevadm", "info", "-q", "property", f"--path=/sys/class/net/{interface}"]).stdout
    return re.search(r"^NM_UNMANAGED=1$", out, re.M) is not None


def status() -> dict:
    running = nm_running()
    config = nm_config_text()
    interfaces = kernel_wifi_interfaces()
    report = {
        "networkmanager": {"installed": nm_installed(), "running": running,
                           "enabled": unit_enabled("NetworkManager.service")},
        "iwd": {"active": unit_active("iwd.service"), "enabled": unit_enabled("iwd.service"),
                "networkmanager_uses_it": iwd_backend(config)},
        "radio": radio_on() if running else None,
        "rfkill": rfkill_wifi(),
        "surface": is_surface(),
        "interfaces": [],
        "devices": wifi_devices() if running else [],
        "halcyon_conf": str(CONF) if CONF.is_file() else "",
    }
    for interface in interfaces:
        report["interfaces"].append({
            "interface": interface, "driver": driver_of(interface),
            "unmanaged_by_config": unmanaged_by_config(config, interface),
            "unmanaged_by_udev": unmanaged_by_udev(interface),
        })
    return report


def problems(report: dict) -> list[str]:
    """What stands in the way, in plain words, each with what to do."""
    found = []
    nm = report["networkmanager"]
    if not nm.get("installed", True):
        found.append("NetworkManager isn't installed: Halcyon's network menu and Wi-Fi at login use it. "
                     "Run: halcyon wifi fix (it installs it, and keeps iwd's networks if you use iwd)")
    elif not nm["running"]:
        found.append("NetworkManager isn't running" + ("" if nm["enabled"] else " (and isn't enabled at boot)")
                     + ". Run: halcyon wifi fix")
    iwd = report["iwd"]
    if iwd["active"] and not iwd["networkmanager_uses_it"] and nm.get("installed", True):
        found.append("iwd is running next to NetworkManager, and both try to drive the Wi-Fi card. Run: halcyon wifi fix "
                     "(NetworkManager then uses iwd; your saved networks stay)")
    if report["rfkill"]["hard"]:
        found.append("The Wi-Fi is switched off by a hardware switch or a firmware setting (rfkill hard block).")
    elif report["rfkill"]["soft"]:
        found.append("The Wi-Fi radio is blocked (rfkill). halcyon wifi boot unblocks it.")
    if report["radio"] is False:
        found.append("NetworkManager's Wi-Fi radio is off. halcyon wifi boot turns it on.")
    if not report["interfaces"]:
        found.append("The kernel has no Wi-Fi interface: the driver or its firmware didn't load (dmesg | grep -i wifi"
                     + (", or mwifiex on a Surface" if report["surface"] else "") + ").")
    listed = {d["device"]: d for d in report["devices"]}
    for item in report["interfaces"]:
        name = item["interface"]
        device = listed.get(name)
        if item["unmanaged_by_config"]:
            found.append(f"{name} is unmanaged by NetworkManager's settings: {item['unmanaged_by_config']}. "
                         "Remove it from that line, or run: halcyon wifi fix")
        if item["unmanaged_by_udev"]:
            found.append(f"{name} is marked unmanaged by a udev rule (NM_UNMANAGED=1). halcyon wifi fix overrides it.")
        if device and device["state"] == "unmanaged" and not (item["unmanaged_by_config"] or item["unmanaged_by_udev"]):
            found.append(f"NetworkManager lists {name} as unmanaged. halcyon wifi boot takes it back for this session; "
                         "halcyon wifi fix keeps it managed.")
        if device and device["state"] == "unavailable":
            found.append(f"{name} is unavailable: the card isn't ready (firmware) or the radio is off.")
        if item["driver"] in MWIFIEX and not report["halcyon_conf"]:
            found.append(f"{name} uses {item['driver']}, which connects more reliably with MAC randomisation while "
                         "scanning and power saving off. Run: halcyon wifi fix")
    return found


# --- boot: this session ---------------------------------------------------------------------------------------------

def wait_for(test, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        if test():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL)


def connected(devices: list[dict]) -> bool:
    return any(d["state"] == "connected" for d in devices)


def boot() -> int:
    """Gets the Wi-Fi up for this session, step by step, logging each (~/.local/state/halcyon/wifi.log)."""
    if iwd_connected() and not (nm_installed() and nm_running() and connected(wifi_devices())):
        # iwd already has a network: whether or not NetworkManager is about, nothing to fight over.
        log("Wi-Fi connected by iwd")
        return 0
    if not nm_installed() and unit_active("iwd.service"):
        # A computer set up with iwd alone: iwd connects by itself. Say whether it did.
        if wait_for(iwd_connected, WAIT_CONNECT):
            log("Wi-Fi connected by iwd (NetworkManager isn't installed)")
            return 0
        log("iwd hasn't connected, and NetworkManager isn't installed")
        notify("Wi-Fi not connected", "iwd hasn't connected. `iwctl station list` shows it; `halcyon wifi fix` "
                                      "installs NetworkManager for the shell's network menu, keeping iwd's networks.")
        return 1
    if not wait_for(nm_running, WAIT_NM):
        log("NetworkManager isn't running")
        notify("No Wi-Fi: NetworkManager isn't running",
               "Run `halcyon wifi fix` in a terminal once (it asks for your password) to start it at every boot.")
        return 1
    if any(item for item in wifi_devices() if item["state"] == "connected"):
        log("Wi-Fi already connected")
        return 0
    if rfkill_wifi()["soft"] and shutil.which("rfkill"):
        log("unblocking the Wi-Fi radio (rfkill)")
        run(["rfkill", "unblock", "wifi"])
    if not radio_on():
        log("turning NetworkManager's Wi-Fi radio on")
        run(["nmcli", "radio", "wifi", "on"])

    # The card may take a while to appear (a Surface's firmware loads after the session starts).
    if not wait_for(lambda: bool(wifi_devices()), WAIT_DEVICE):
        log("no Wi-Fi device appeared")
        notify("No Wi-Fi device", "NetworkManager has no Wi-Fi device. `halcyon wifi` shows why.")
        return 1

    for device in wifi_devices():
        if device["state"] == "unmanaged":
            log(f"{device['device']} is unmanaged; handing it back to NetworkManager")
            done = run(["nmcli", "device", "set", device["device"], "managed", "yes"])
            if done.returncode != 0:
                log(f"couldn't: {done.stderr.strip()}")

    if wait_for(lambda: connected(wifi_devices()), WAIT_CONNECT):
        log("Wi-Fi connected")
        return 0

    for device in wifi_devices():
        if device["state"] == "disconnected":
            log(f"connecting {device['device']}")
            if run(["nmcli", "-w", "25", "device", "connect", device["device"]], timeout=40).returncode == 0:
                log("Wi-Fi connected")
                return 0
    # Last: the last network with a password, the way after a suspend.
    reconnect = HERE / "wifi-reconnect"
    if reconnect.exists():
        log("trying the last Wi-Fi network (wifi-reconnect)")
        if run([sys.executable, str(reconnect)], timeout=180).returncode == 0:
            return 0
    states = ", ".join(f"{d['device']} {d['state']}" for d in wifi_devices()) or "no device"
    log(f"Wi-Fi not connected ({states})")
    notify("Wi-Fi not connected", f"NetworkManager: {states}. `halcyon wifi` shows what stands in the way; "
                                  "`halcyon wifi fix` fixes what it can.")
    return 1


# --- fix: lasting, as root ------------------------------------------------------------------------------------------

def conf_text(report: dict) -> str:
    drivers = sorted({item["driver"] for item in report["interfaces"] if item["driver"] in MWIFIEX})
    lines = [
        "# Written by Halcyon (halcyon wifi fix). Delete this file, then restart NetworkManager, to undo.",
        "",
    ]
    if report["iwd"]["active"] and not report["iwd"]["networkmanager_uses_it"]:
        lines += [
            "# iwd is running: NetworkManager drives the card through it instead of fighting it with wpa_supplicant.",
            "[device]",
            "wifi.backend=iwd",
            "",
        ]
    lines += [
        "# Wi-Fi devices are NetworkManager's, whatever marked them unmanaged.",
        "[device-halcyon-wifi]",
        "match-device=type:wifi",
        "managed=1",
    ]
    if drivers:
        match = ",".join(f"driver:{d}" for d in drivers)
        lines += [
            "",
            "# Marvell mwifiex cards (Surface): scanning with a random MAC address and power saving make connections",
            "# fail or drop (linux-surface's advice).",
            "[device-halcyon-mwifiex]",
            f"match-device={match}",
            "managed=1",
            "wifi.scan-rand-mac-address=no",
            "",
            "[connection-halcyon-mwifiex]",
            f"match-device={match}",
            "wifi.powersave=2",
        ]
    return "\n".join(lines) + "\n"


def fix(dry_run: bool = False) -> int:
    if os.geteuid() != 0 and not dry_run:
        # Everything here is system settings: run again as root.
        sudo = shutil.which("sudo")
        if not sudo:
            print("halcyon wifi fix needs root: run it with sudo", file=sys.stderr)
            return 1
        return subprocess.run([sudo, sys.executable, str(Path(__file__).resolve()), "fix"], check=False).returncode

    report = status()
    steps: list[list[str]] = []
    if not report["networkmanager"].get("installed", True):
        if shutil.which("pacman"):
            print("NetworkManager isn't installed: installing it")
            install = ["pacman", "-S", "--needed", "--noconfirm", "networkmanager"]
            print("+ " + " ".join(install))
            if not dry_run and run(install, timeout=600).returncode != 0:
                print("couldn't install NetworkManager; install the networkmanager package, then run this again",
                      file=sys.stderr)
                return 1
        else:
            print("NetworkManager isn't installed: install it with your package manager, then run this again",
                  file=sys.stderr)
            return 1
    if report["iwd"]["active"] and not report["iwd"]["networkmanager_uses_it"]:
        print("iwd is running: NetworkManager will use it (wifi.backend=iwd), so they stop fighting and iwd's networks stay")
    print(f"writing {CONF}")
    text = conf_text(report)
    if not dry_run:
        CONF.parent.mkdir(parents=True, exist_ok=True)
        CONF.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if report["rfkill"]["soft"]:
        steps.append(["rfkill", "unblock", "wifi"])
    steps.append(["systemctl", "enable", "NetworkManager.service"])
    steps.append(["systemctl", "restart", "NetworkManager.service"])
    for step in steps:
        print("+ " + " ".join(step))
        if not dry_run and run(step, timeout=60).returncode != 0:
            print(f"  that failed; continuing", file=sys.stderr)
    for item in report["interfaces"]:
        if item["unmanaged_by_config"]:
            print(f"note: {item['interface']} is still listed in: {item['unmanaged_by_config']}. "
                  "Halcyon's setting overrides it, but you may want to remove it from that file.")
    if not dry_run:
        time.sleep(3)
        for device in wifi_devices():
            if device["state"] == "disconnected":
                run(["nmcli", "-w", "25", "device", "connect", device["device"]], timeout=40)
        print("NetworkManager now lists: " + (", ".join(f"{d['device']} {d['state']}" for d in wifi_devices())
                                              or "no Wi-Fi device"))
    return 0


# --- report: one file to send ---------------------------------------------------------------------------------------

REPORT = Path(os.environ.get("HALCYON_WIFI_REPORT", Path.home() / "halcyon-wifi-report.txt"))
REPORT_COMMANDS = [
    ["nmcli", "general"],
    ["nmcli", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
    ["nmcli", "radio"],
    ["rfkill", "list"],
    ["ip", "-brief", "link"],
    ["iwctl", "station", "list"],
    ["systemctl", "--no-pager", "status", "NetworkManager.service", "iwd.service", "wpa_supplicant.service"],
    ["journalctl", "-b", "--no-pager", "-n", "80", "-u", "NetworkManager", "-u", "iwd", "-u", "wpa_supplicant"],
]


def report_text() -> str:
    """Everything `halcyon wifi` looks at, the log of the last logins, and what NetworkManager itself says."""
    import io
    from contextlib import redirect_stdout
    info = status()
    out = io.StringIO()
    with redirect_stdout(out):
        print_status(info)
    parts = ["# halcyon wifi report, " + time.strftime("%Y-%m-%d %H:%M"), "", out.getvalue().rstrip()]
    try:
        parts += ["", "## Halcyon's Wi-Fi log (last 40 lines)", *LOG.read_text(encoding="utf-8").splitlines()[-40:]]
    except OSError:
        parts += ["", "## Halcyon's Wi-Fi log", "(none yet: halcyon wifi boot writes it at login)"]
    if CONF.is_file():
        parts += ["", f"## {CONF}", CONF.read_text(encoding="utf-8").rstrip()]
    for cmd in REPORT_COMMANDS:
        if not shutil.which(cmd[0]):
            continue
        done = run(cmd, timeout=20)
        parts += ["", "## " + " ".join(cmd), (done.stdout + done.stderr).rstrip() or "(nothing)"]
    parts += ["", "## as JSON", json.dumps({**info, "problems": problems(info)}, indent=2)]
    return "\n".join(parts) + "\n"


def write_report() -> int:
    REPORT.write_text(report_text(), encoding="utf-8")
    print(f"wrote {REPORT}: send it along with what you saw. (It has no passwords: nmcli and iwd never print them.)")
    return 0


# --- command line ---------------------------------------------------------------------------------------------------

def print_status(report: dict) -> None:
    nm = report["networkmanager"]
    if not nm.get("installed", True):
        print("NetworkManager  NOT installed")
    else:
        print(f"NetworkManager  {'running' if nm['running'] else 'NOT running'}, "
              f"{'enabled' if nm['enabled'] else 'not enabled'} at boot")
    iwd = report["iwd"]
    if iwd["active"] or iwd["enabled"]:
        print(f"iwd             {'running' if iwd['active'] else 'enabled'}"
              + (" (NetworkManager's backend)" if iwd["networkmanager_uses_it"] else " (beside NetworkManager)"))
    if report["radio"] is not None:
        print(f"radio           {'on' if report['radio'] else 'off'}")
    rf = report["rfkill"]
    print(f"rfkill          {'hard blocked' if rf['hard'] else 'soft blocked' if rf['soft'] else 'not blocked'}")
    if report["surface"]:
        print("computer        Microsoft Surface")
    listed = {d["device"]: d for d in report["devices"]}
    for item in report["interfaces"]:
        device = listed.get(item["interface"])
        state = (device["state"] + (f" to {device['connection']}" if device["connection"] else "")) if device else "not listed"
        print(f"{item['interface']:<15} {item['driver'] or 'unknown driver'}, {state}")
    print(f"Halcyon setting {report['halcyon_conf'] or 'not written (halcyon wifi fix)'}")
    found = problems(report)
    if found:
        print()
        for line in found:
            print("- " + line)
    else:
        print("\nNothing in the way.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon wifi", description="Wi-Fi when Hyprland starts.")
    parser.add_argument("action", nargs="?", default="status", choices=("status", "boot", "fix", "report"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="fix: say what it would do")
    args = parser.parse_args(argv)
    if args.action == "boot":
        return boot()
    if args.action == "fix":
        return fix(dry_run=args.dry_run)
    if args.action == "report":
        return write_report()
    report = status()
    if args.json:
        print(json.dumps({**report, "problems": problems(report)}, indent=2))
    else:
        print_status(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
