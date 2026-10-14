#!/usr/bin/env python3
"""USB devices in the browser (WebUSB, WebHID, Web Serial): `halcyon usb`.

    halcyon usb                       which devices the browser can open, and why not
    halcyon usb allow VID:PID ...     let you (the person at this seat) open those devices; asks for sudo
    halcyon usb allow --all           every USB, HID and USB-serial device except keyboards and mice
    halcyon usb remove                take Halcyon's rule away again
    halcyon usb --json

Why a browser "can't find" a device on Arch:

  - USB device nodes (/dev/bus/usb/BBB/DDD) and /dev/hidraw* belong to root. systemd gives the person at the seat
    access (a "uaccess" ACL) only to kinds of device it knows: sound, cameras, game controllers, security keys.
    A phone, a microcontroller, a keyboard flasher or a USB-serial adapter gets nothing, so the browser cannot open
    it, and its picker lists nothing or says "access denied". A udev rule tagging the device "uaccess" fixes that,
    for whoever is logged in at the screen, and only while they are.
  - USB-serial adapters (/dev/ttyUSB*, /dev/ttyACM*) belong to the uucp group (dialout elsewhere).
  - A Flatpak browser sees no devices at all without --device=all.
  - WebUSB never opens some kinds of interface, by design: keyboards, mice and other HID, storage, sound, video and
    smart cards. Sites reach HID devices with WebHID instead, which needs /dev/hidraw* access.
  - The ACLs only exist while your login session is the active one on seat0.

The rule written is /etc/udev/rules.d/70-halcyon-usb.rules: before 73-seat-late.rules, which turns the tag into the ACL.
"""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RULE_PATH = Path("/etc/udev/rules.d/70-halcyon-usb.rules")
SYS = Path("/sys")
DEV = Path("/dev")

# USB interface classes WebUSB will not open (Chromium's protected list); WebHID covers HID.
PROTECTED = {0x01: "audio", 0x03: "HID", 0x08: "storage", 0x0B: "smart card", 0x0E: "video", 0x10: "audio/video",
             0xE0: "wireless controller"}
FLATPAK_BROWSERS = ("org.chromium.Chromium", "com.google.Chrome", "com.brave.Browser", "com.microsoft.Edge",
                    "com.vivaldi.Vivaldi", "com.opera.Opera", "io.github.ungoogled_software.ungoogled_chromium",
                    "org.mozilla.firefox", "io.gitlab.librewolf-community", "app.zen_browser.zen")
HEADER = "# Halcyon: let the person at this seat open these devices from the browser (WebUSB, WebHID, Web Serial).\n" \
         "# Written by `halcyon usb allow`; `halcyon usb remove` deletes it.\n"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _hex(text: str) -> int | None:
    try:
        return int(text, 16)
    except ValueError:
        return None


# --- what is plugged in -----------------------------------------------------------------------------------------

def usb_devices(sys_root: Path = SYS, dev_root: Path = DEV) -> list[dict]:
    """Every USB device but the root hubs: ids, names, node, interface classes, and whether we can open it."""
    out = []
    base = sys_root / "bus/usb/devices"
    for entry in sorted(base.glob("*")) if base.is_dir() else []:
        if ":" in entry.name or entry.name.startswith("usb"):
            continue  # interfaces and root hubs
        vendor, product = _read(entry / "idVendor"), _read(entry / "idProduct")
        if not vendor:
            continue
        busnum, devnum = _read(entry / "busnum"), _read(entry / "devnum")
        node = dev_root / f"bus/usb/{int(busnum or 0):03d}/{int(devnum or 0):03d}"
        classes = set()
        for iface in entry.glob(f"{entry.name}:*"):
            value = _hex(_read(iface / "bInterfaceClass"))
            if value is not None:
                classes.add(value)
        boot_input = any(_read(i / "bInterfaceClass") == "03" and _read(i / "bInterfaceSubClass") == "01"
                         and _read(i / "bInterfaceProtocol") in ("01", "02") for i in entry.glob(f"{entry.name}:*"))
        name = " ".join(x for x in (_read(entry / "manufacturer"), _read(entry / "product")) if x) or "unknown device"
        out.append({
            "id": f"{vendor}:{product}", "name": name, "node": str(node),
            "access": node.exists() and os.access(node, os.R_OK | os.W_OK),
            "classes": sorted(classes),
            "webusb_blocked": sorted({PROTECTED[c] for c in classes if c in PROTECTED}),
            "only_protected": bool(classes) and all(c in PROTECTED for c in classes),
            "keyboard_or_mouse": boot_input,
            "sys": str(entry),
        })
    return out


def hidraw_devices(sys_root: Path = SYS, dev_root: Path = DEV) -> list[dict]:
    out = []
    base = sys_root / "class/hidraw"
    for entry in sorted(base.glob("hidraw*")) if base.is_dir() else []:
        uevent = dict(line.split("=", 1) for line in _read(entry / "device/uevent").splitlines() if "=" in line)
        hid_id = uevent.get("HID_ID", "")  # BUS:VVVVVVVV:PPPPPPPP
        parts = hid_id.split(":")
        usb_id = f"{parts[1][-4:]}:{parts[2][-4:]}".lower() if len(parts) == 3 else ""
        node = dev_root / entry.name
        out.append({"node": str(node), "name": uevent.get("HID_NAME", "unknown"), "id": usb_id,
                    "access": node.exists() and os.access(node, os.R_OK | os.W_OK)})
    return out


def serial_devices(dev_root: Path = DEV) -> list[dict]:
    nodes = sorted(list(dev_root.glob("ttyUSB*")) + list(dev_root.glob("ttyACM*")))
    out = []
    for node in nodes:
        try:
            group = grp.getgrgid(node.stat().st_gid).gr_name
        except (KeyError, OSError):
            group = ""
        out.append({"node": str(node), "group": group, "access": os.access(node, os.R_OK | os.W_OK)})
    return out


# --- the session, groups, browsers ------------------------------------------------------------------------------

def run(argv: list[str], timeout: float = 10) -> str:
    if not shutil.which(argv[0]):
        return ""
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False,
                              stdin=subprocess.DEVNULL).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def session() -> dict:
    """The logind session this desktop runs in. ACLs from uaccess only exist while it is active on a seat."""
    session_id = os.environ.get("XDG_SESSION_ID", "")
    if not session_id:
        for line in run(["loginctl", "list-sessions", "--no-legend"]).splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[2] == pwd.getpwuid(os.getuid()).pw_name and "seat" in line:
                session_id = fields[0]
                break
    if not session_id:
        return {"id": "", "known": False}
    props = {}
    for line in run(["loginctl", "show-session", session_id, "-p", "Active", "-p", "Seat", "-p", "Type",
                     "-p", "Remote", "-p", "State"]).splitlines():
        key, _, value = line.partition("=")
        props[key] = value
    return {"id": session_id, "known": bool(props), "active": props.get("Active") == "yes",
            "seat": props.get("Seat", ""), "type": props.get("Type", ""), "remote": props.get("Remote") == "yes"}


def my_groups() -> set[str]:
    names = {grp.getgrgid(g).gr_name for g in os.getgroups() if _group_exists(g)}
    user = pwd.getpwuid(os.getuid()).pw_name
    names |= {g.gr_name for g in grp.getgrall() if user in g.gr_mem}  # joined, maybe not yet logged in again
    return names


def _group_exists(gid: int) -> bool:
    try:
        grp.getgrgid(gid)
        return True
    except KeyError:
        return False


def serial_group() -> str:
    for name in ("uucp", "dialout"):
        try:
            grp.getgrnam(name)
            return name
        except KeyError:
            continue
    return ""


def flatpak_browsers() -> list[dict]:
    if not shutil.which("flatpak"):
        return []
    installed = set(run(["flatpak", "list", "--app", "--columns=application"]).split())
    out = []
    for app in FLATPAK_BROWSERS:
        if app in installed:
            perms = run(["flatpak", "info", "--show-permissions", app])
            devices = re.search(r"^devices=(.*)$", perms, re.M)
            out.append({"app": app, "all_devices": bool(devices and "all" in devices.group(1).split(";"))})
    return out


def rule_text() -> str:
    return _read(RULE_PATH)


# --- writing the rule ---------------------------------------------------------------------------------------------

ID_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$")


def rules_for(ids: list[str]) -> str:
    """Rule lines for these vendor:product ids: the USB node, its hidraw nodes, and its serial ports."""
    lines = []
    for item in ids:
        vendor, product = item.lower().split(":")
        match = f'ATTRS{{idVendor}}=="{vendor}", ATTRS{{idProduct}}=="{product}"'
        lines.append(f"# {item.lower()}")
        lines.append(f'SUBSYSTEM=="usb", ENV{{DEVTYPE}}=="usb_device", ATTR{{idVendor}}=="{vendor}", '
                     f'ATTR{{idProduct}}=="{product}", TAG+="uaccess"')
        lines.append(f'SUBSYSTEM=="hidraw", {match}, TAG+="uaccess"')
        lines.append(f'SUBSYSTEM=="tty", KERNEL=="ttyUSB[0-9]*|ttyACM[0-9]*", {match}, TAG+="uaccess"')
    return "\n".join(lines) + "\n"


ALL_RULES = """\
# Every USB device, its HID nodes and its serial ports, except keyboards and mice: raw access to those would let
# any program you run read what you type.
SUBSYSTEM=="hidraw", ATTRS{bInterfaceClass}=="03", ATTRS{bInterfaceSubClass}=="01", ATTRS{bInterfaceProtocol}=="01|02", GOTO="halcyon_usb_end"
# ID_USB_INTERFACES (from udev's usb_id, in 50-udev-default.rules) lists ":class subclass protocol:" per interface;
# 030101 is a boot keyboard and 030102 a boot mouse.
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ENV{ID_USB_INTERFACES}=="*:030101:*|*:030102:*", GOTO="halcyon_usb_end"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{bDeviceClass}=="09", GOTO="halcyon_usb_end"
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", TAG+="uaccess"
SUBSYSTEM=="hidraw", TAG+="uaccess"
SUBSYSTEM=="tty", KERNEL=="ttyUSB[0-9]*|ttyACM[0-9]*", TAG+="uaccess"
LABEL="halcyon_usb_end"
"""


def merged_rules(existing: str, ids: list[str], all_devices: bool) -> str:
    """The new rule file: the --all block, or the existing per-device blocks plus these."""
    if all_devices:
        return HEADER + ALL_RULES
    known = set(re.findall(r"^# ([0-9a-f]{4}:[0-9a-f]{4})$", existing, re.M))
    if "halcyon_usb_end" in existing:
        known = set()  # replacing --all with a list
    wanted = sorted(known | {i.lower() for i in ids})
    return HEADER + rules_for(wanted)


def install_rules(text: str) -> int:
    sudo = [] if os.geteuid() == 0 else ["sudo"]
    with tempfile.NamedTemporaryFile("w", suffix=".rules", delete=False) as handle:
        handle.write(text)
        tmp = handle.name
    try:
        steps = [sudo + ["install", "-m", "644", tmp, str(RULE_PATH)],
                 sudo + ["udevadm", "control", "--reload-rules"],
                 sudo + ["udevadm", "trigger", "--action=change", "--subsystem-match=usb",
                         "--subsystem-match=hidraw", "--subsystem-match=tty"]]
        for step in steps:
            print("+ " + " ".join(step))
            if subprocess.run(step, check=False).returncode != 0:
                print(f"halcyon usb: `{' '.join(step)}` failed", file=sys.stderr)
                return 1
    finally:
        os.unlink(tmp)
    return 0


# --- the report ---------------------------------------------------------------------------------------------------

def gather() -> dict:
    devices = usb_devices()
    return {"session": session(), "usb": devices, "hidraw": hidraw_devices(), "serial": serial_devices(),
            "groups": sorted(my_groups()), "serial_group": serial_group(), "flatpak": flatpak_browsers(),
            "rule": rule_text()}


def advice(info: dict) -> list[str]:
    """What to do, most important first."""
    out = []
    sess = info["session"]
    if sess.get("known") and not sess.get("active"):
        out.append(f"Your login session ({sess['id']}) is not the active one on a seat, so no device ACLs are given. "
                   "Start Hyprland from your login screen or a console login (not over SSH, not with su).")
    for app in info["flatpak"]:
        if not app["all_devices"]:
            out.append(f"{app['app']} is a Flatpak without device access, so it sees no USB devices: "
                       f"flatpak override --user --device=all {app['app']}  (then restart it)")
    blocked = [d for d in info["usb"] if not d["access"] and not d["keyboard_or_mouse"]]
    if blocked:
        ids = " ".join(sorted({d["id"] for d in blocked}))
        out.append(f"The browser cannot open: {', '.join(d['name'] for d in blocked)}. Allow them with:\n"
                   f"    halcyon usb allow {ids}")
    # A keyboard's or mouse's raw HID node is never offered: any program could read what is typed through it.
    skip = {d["id"] for d in blocked} | {d["id"] for d in info["usb"] if d["keyboard_or_mouse"]}
    hid_blocked = [h for h in info["hidraw"] if not h["access"] and h["id"] not in skip]
    if hid_blocked:
        out.append("WebHID cannot open: " + ", ".join(f"{h['name']} ({h['node']})" for h in hid_blocked)
                   + ". `halcyon usb allow " + " ".join(sorted({h['id'] for h in hid_blocked if h['id']})) + "`")
    serial_blocked = [s for s in info["serial"] if not s["access"]]
    if serial_blocked and info["serial_group"] and info["serial_group"] not in info["groups"]:
        out.append(f"Web Serial cannot open {', '.join(s['node'] for s in serial_blocked)}: join the "
                   f"{info['serial_group']} group (sudo gpasswd -a $USER {info['serial_group']}, then log in again), "
                   "or allow the adapter with `halcyon usb allow VID:PID`.")
    only = [d for d in info["usb"] if d["only_protected"] and d["access"] and not d["keyboard_or_mouse"]]
    for device in only:
        out.append(f"{device['name']} only has {', '.join(device['webusb_blocked'])} interfaces, which WebUSB never "
                   "opens on any system; sites reach HID devices through WebHID instead.")
    if not out:
        out.append("Every device here can be opened. If a site still finds nothing, open chrome://device-log in the "
                   "browser: it says why a device was left out.")
    return out


def render(info: dict) -> str:
    lines = []
    sess = info["session"]
    if sess.get("known"):
        lines.append(f"session   {sess['id']}, {'active' if sess['active'] else 'NOT active'}"
                     f"{', seat ' + sess['seat'] if sess['seat'] else ', no seat'}"
                     f"{', remote' if sess.get('remote') else ''}")
    else:
        lines.append("session   not found (loginctl)")
    lines.append(f"rule      {RULE_PATH if info['rule'] else 'none (halcyon usb allow ...)'}")
    lines.append("")
    if info["usb"]:
        lines.append("USB devices")
        for d in info["usb"]:
            mark = "ok " if d["access"] else "no "
            note = ""
            if d["keyboard_or_mouse"]:
                note = "  keyboard/mouse: left alone"
            elif d["webusb_blocked"]:
                note = f"  WebUSB skips: {', '.join(d['webusb_blocked'])}"
            lines.append(f"  {mark} {d['id']}  {d['name']}{note}")
    else:
        lines.append("No USB devices found.")
    if info["hidraw"]:
        lines.append("HID (WebHID)")
        for h in info["hidraw"]:
            lines.append(f"  {'ok ' if h['access'] else 'no '} {h['node']:<14} {h['name']}")
    if info["serial"]:
        lines.append("Serial (Web Serial)")
        for s in info["serial"]:
            lines.append(f"  {'ok ' if s['access'] else 'no '} {s['node']:<14} group {s['group']}")
    for app in info["flatpak"]:
        lines.append(f"Flatpak   {app['app']}: {'all devices' if app['all_devices'] else 'NO device access'}")
    lines.append("")
    lines.extend(advice(info))
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon usb", description="USB devices in the browser.")
    parser.add_argument("action", nargs="?", default="status", choices=("status", "allow", "remove"))
    parser.add_argument("ids", nargs="*", help="vendor:product, as `halcyon usb` lists them")
    parser.add_argument("--all", action="store_true", help="with allow: every device but keyboards and mice")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.action == "status":
        info = gather()
        if args.json:
            print(json.dumps({**info, "advice": advice(info)}, indent=2))
        else:
            print(render(info), end="")
        return 0
    if args.action == "remove":
        if not RULE_PATH.exists():
            print("no Halcyon USB rule is installed")
            return 0
        sudo = [] if os.geteuid() == 0 else ["sudo"]
        if subprocess.run(sudo + ["rm", "-f", str(RULE_PATH)], check=False).returncode != 0:
            return 1
        subprocess.run(sudo + ["udevadm", "control", "--reload-rules"], check=False)
        print("removed; devices keep their access until they are plugged in again")
        return 0
    # allow
    bad = [i for i in args.ids if not ID_RE.match(i)]
    if bad or (not args.ids and not args.all):
        print("usage: halcyon usb allow VID:PID [VID:PID ...] | --all   (ids as `halcyon usb` lists them)",
              file=sys.stderr)
        return 2
    if args.all:
        print("This lets any program you run open every USB, HID and USB-serial device while you are logged in at "
              "the screen. Keyboards and mice are left out.")
    code = install_rules(merged_rules(rule_text(), args.ids, args.all))
    if code == 0:
        print("done. Unplug the device and plug it back in if the browser still cannot open it.")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
