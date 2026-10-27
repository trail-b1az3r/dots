#!/usr/bin/env python3
"""Sound, microphones and webcams in Hyprland: `halcyon audio`.

    halcyon audio                  what PipeWire sees, and what stands in the way
    halcyon audio boot             put the session right (Hyprland runs this at login)
    halcyon audio fix              the same, then restart the sound services so every device is found again
    halcyon audio report           everything above plus the sound services' log, in one file to send
    halcyon audio easyeffects on|off   start EasyEffects at login, or not (off unless you turn it on)
    halcyon audio --json

Why headphones, a webcam and its microphone can work in KDE and not in Hyprland, even when you log in to KDE
first:

  - EasyEffects. Hyprland used to start it at every login (KDE doesn't). It puts its own "Easy Effects Sink" and
    "Easy Effects Source" in front of the real devices and makes them the defaults, sending sound to whichever
    device it was last set to: plug in headphones and nothing comes out of them; pick the webcam's microphone and
    it takes the default back, so the shell's microphone menu flickers between the two. It is now only started
    when you turn it on (`halcyon audio easyeffects on`, or Settings > Halcyon > Sound).
  - What KDE leaves behind. Your systemd user services outlive the KDE session, so after logging out of KDE and
    into Hyprland they still have KDE's environment (XDG_CURRENT_DESKTOP=KDE, KDE_FULL_SESSION...), and
    xdg-desktop-portal is still the one KDE started, with KDE's backend. Browsers, Discord and OBS reach the webcam
    through that portal (and PipeWire), so the camera fails. `boot` clears KDE's variables, hands Hyprland's to
    systemd, and restarts the portals when KDE's were running.
  - Devices you may not open. The webcam (/dev/video*) and sound cards (/dev/snd/*) are opened by the user of the
    active login session. A session started some other way (Hyprland run from a terminal inside another session)
    isn't the active one; `status` says when this is the case.
  - PipeWire, PipeWire's PulseAudio server or WirePlumber not running (`fix` starts them, and installs what's
    missing with pacman).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "halcyon"
LOG = STATE / "audio.log"
EASYEFFECTS_FLAG = STATE / "easyeffects"
REPORT = Path(os.environ.get("HALCYON_AUDIO_REPORT", Path.home() / "halcyon-audio-report.txt"))
DEV = Path(os.environ.get("HALCYON_DEV", "/dev"))

SOUND_UNITS = ("pipewire.service", "pipewire-pulse.service", "wireplumber.service")
PORTAL_UNITS = ("xdg-desktop-portal.service", "xdg-desktop-portal-hyprland.service", "xdg-desktop-portal-gtk.service")
KDE_PORTAL = "xdg-desktop-portal-kde.service"
PACKAGES = ("pipewire", "pipewire-pulse", "wireplumber", "xdg-desktop-portal-hyprland", "xdg-desktop-portal-gtk")
# What a KDE session puts in the systemd user environment that has no place in Hyprland's.
KDE_VARIABLES = ("KDE_FULL_SESSION", "KDE_SESSION_VERSION", "KDE_SESSION_UID", "KDE_APPLICATIONS_AS_SCOPE",
                 "QT_WAYLAND_RECONNECT", "PLASMA_USE_QT_SCALING", "GTK_RC_FILES", "GTK2_RC_FILES")
# What Hyprland's session hands to systemd (and so to the portals, PipeWire and the shell).
SESSION_VARIABLES = ("WAYLAND_DISPLAY", "DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "XDG_CURRENT_DESKTOP",
                     "XDG_SESSION_DESKTOP", "XDG_SESSION_TYPE", "XDG_SESSION_ID", "XDG_SEAT", "DESKTOP_SESSION",
                     "XDG_RUNTIME_DIR")
REPORT_COMMANDS = (["wpctl", "status"], ["systemctl", "--user", "--no-pager", "status", *SOUND_UNITS, *PORTAL_UNITS],
                   ["journalctl", "--user", "--no-pager", "-n", "60", "-u", "wireplumber", "-u", "pipewire",
                    "-u", "xdg-desktop-portal"], ["v4l2-ctl", "--list-devices"])


def run(cmd: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(cmd, 127, "", str(error))


def log(message: str) -> None:
    print(message)
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    except OSError:
        pass


# --- what is there --------------------------------------------------------------------------------------------------

def unit_active(unit: str) -> bool:
    return run(["systemctl", "--user", "is-active", "--quiet", unit]).returncode == 0


def systemd_environment() -> dict:
    env = {}
    for line in run(["systemctl", "--user", "show-environment"]).stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            env[key] = value
    return env


def session() -> dict:
    """The login session this runs in, as logind sees it."""
    sid = os.environ.get("XDG_SESSION_ID", "")
    if not sid or not shutil.which("loginctl"):
        return {"id": sid, "active": None, "type": "", "seat": "", "remote": None}
    props = {}
    out = run(["loginctl", "show-session", sid, "-p", "Active", "-p", "Type", "-p", "Seat", "-p", "Remote"]).stdout
    for line in out.splitlines():
        key, _, value = line.partition("=")
        props[key] = value
    return {"id": sid, "active": props.get("Active") == "yes" if "Active" in props else None,
            "type": props.get("Type", ""), "seat": props.get("Seat", ""),
            "remote": props.get("Remote") == "yes" if "Remote" in props else None}


def device_access() -> dict:
    """Webcams and sound cards, and whether this user may open them."""
    def check(pattern):
        found = sorted(glob.glob(str(DEV / pattern)))
        return {"count": len(found), "blocked": [Path(p).name for p in found if not os.access(p, os.R_OK | os.W_OK)]}
    return {"video": check("video*"), "sound": check("snd/pcmC*")}


def pipewire_nodes() -> dict:
    """Devices PipeWire has (sinks, sources, cameras) and the defaults, from pw-dump."""
    result = {"sinks": [], "sources": [], "cameras": [], "default_sink": "", "default_source": "", "ok": False}
    if not shutil.which("pw-dump"):
        return result
    done = run(["pw-dump"], timeout=15)
    try:
        objects = json.loads(done.stdout or "[]")
    except json.JSONDecodeError:
        return result
    result["ok"] = done.returncode == 0
    for obj in objects:
        info = obj.get("info") or {}
        if obj.get("type") == "PipeWire:Interface:Metadata" and (obj.get("props") or {}).get("metadata.name") == "default":
            for entry in obj.get("metadata") or []:
                value = entry.get("value")
                name = value.get("name", "") if isinstance(value, dict) else ""
                if entry.get("key") == "default.audio.sink":
                    result["default_sink"] = name
                elif entry.get("key") == "default.audio.source":
                    result["default_source"] = name
            continue
        props = info.get("props") or {}
        media = props.get("media.class", "")
        node = {"name": props.get("node.name", ""), "description": props.get("node.description", "")}
        if media == "Audio/Sink":
            result["sinks"].append(node)
        elif media in ("Audio/Source", "Audio/Source/Virtual"):
            result["sources"].append(node)
        elif media == "Video/Source":
            result["cameras"].append(node)
    return result


def easyeffects_running() -> bool:
    return run(["pgrep", "-x", "easyeffects"]).returncode == 0


def status() -> dict:
    env = systemd_environment()
    return {
        "session": session(),
        "services": {unit: unit_active(unit) for unit in SOUND_UNITS},
        "portals": {unit: unit_active(unit) for unit in (*PORTAL_UNITS, KDE_PORTAL)},
        "systemd_desktop": env.get("XDG_CURRENT_DESKTOP", ""),
        "kde_leftovers": [name for name in KDE_VARIABLES if name in env],
        "easyeffects": {"running": easyeffects_running(), "at_login": EASYEFFECTS_FLAG.exists()},
        "pipewire": pipewire_nodes(),
        "devices": device_access(),
        "missing": missing_packages(),
    }


def missing_packages() -> list[str]:
    if not shutil.which("pacman"):
        return []
    out = run(["pacman", "-T", *PACKAGES]).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_easyeffects(name: str) -> bool:
    return name.startswith("easyeffects_")


def problems(report: dict) -> list[str]:
    found = []
    for unit, active in report["services"].items():
        if not active:
            found.append(f"{unit} isn't running: no sound at all (halcyon audio fix starts it)")
    if report["missing"]:
        found.append("not installed: " + ", ".join(report["missing"]) + " (halcyon audio fix installs them)")
    pw = report["pipewire"]
    ee = report["easyeffects"]
    if ee["running"] and not ee["at_login"]:
        found.append("EasyEffects is running and sits in front of your devices: sound can go to the wrong output "
                     "and the microphone menu flickers. Close it, or keep it: halcyon audio easyeffects on")
    if not ee["running"] and (is_easyeffects(pw["default_sink"]) or is_easyeffects(pw["default_source"])):
        found.append("the default output or microphone is still EasyEffects', which isn't running "
                     "(halcyon audio fix picks real devices)")
    if report["kde_leftovers"] or report["portals"].get(KDE_PORTAL):
        found.append("KDE's session environment or portal is still in use: the webcam fails in browsers and "
                     "Discord (halcyon audio boot clears it; Hyprland runs it at login)")
    elif report["systemd_desktop"] and "Hyprland" not in report["systemd_desktop"]:
        found.append(f"systemd still says the desktop is {report['systemd_desktop']}: portals pick the wrong backend")
    sess = report["session"]
    if sess["active"] is False:
        found.append(f"this login session ({sess['id']}) isn't the active one, so its user can't open the webcam "
                     "or sound cards: log in to Hyprland from the login screen, not from inside another session")
    for kind, label in (("video", "webcam"), ("sound", "sound card")):
        blocked = report["devices"][kind]["blocked"]
        if blocked:
            found.append(f"you may not open the {label} ({', '.join(blocked)}): "
                         + ("the session isn't active" if sess["active"] is False else
                            "add yourself to the 'video'/'audio' group, or log in again from the login screen"))
    if report["devices"]["video"]["count"] and pw["ok"] and not pw["cameras"]:
        found.append("there is a webcam but PipeWire lists no camera: WirePlumber can't open it "
                     "(halcyon audio fix restarts it)")
    return found


# --- putting it right -----------------------------------------------------------------------------------------------

def sync_environment() -> list[str]:
    """Hand Hyprland's session to systemd, and drop what KDE left there. Returns what it changed."""
    changed = []
    env = systemd_environment()
    leftovers = [name for name in KDE_VARIABLES if name in env]
    if leftovers:
        run(["systemctl", "--user", "unset-environment", *leftovers])
        changed.append("cleared " + ", ".join(leftovers))
    present = [name for name in SESSION_VARIABLES if os.environ.get(name)]
    if present:
        run(["systemctl", "--user", "import-environment", *present])
    if shutil.which("dbus-update-activation-environment") and present:
        run(["dbus-update-activation-environment", "--systemd", *present])
    if env.get("XDG_CURRENT_DESKTOP", "") != os.environ.get("XDG_CURRENT_DESKTOP", env.get("XDG_CURRENT_DESKTOP", "")):
        changed.append(f"desktop {env.get('XDG_CURRENT_DESKTOP') or '(unset)'} -> {os.environ.get('XDG_CURRENT_DESKTOP')}")
    return changed


def restart_portals(force: bool = False) -> bool:
    """Restart the portals if KDE's are what's running (or when asked), so they come back with Hyprland's backend."""
    kde = unit_active(KDE_PORTAL)
    if not (kde or force):
        return False
    if kde:
        run(["systemctl", "--user", "stop", KDE_PORTAL])
    run(["systemctl", "--user", "stop", *PORTAL_UNITS])
    # They start again on the next request; start the main one now so the first app doesn't wait.
    run(["systemctl", "--user", "start", "xdg-desktop-portal.service"])
    return True


def start_sound() -> list[str]:
    started = [unit for unit in SOUND_UNITS if not unit_active(unit)]
    if started:
        run(["systemctl", "--user", "start", *started])
    return started


def real_defaults(pw: dict) -> list[str]:
    """When EasyEffects isn't running but its nodes are still the defaults, pick the first real device instead."""
    changed = []
    for key, nodes, label in (("default_sink", pw["sinks"], "output"), ("default_source", pw["sources"], "microphone")):
        if not is_easyeffects(pw[key]):
            continue
        real = [n for n in nodes if not is_easyeffects(n["name"])]
        if real and shutil.which("pactl"):
            command = "set-default-sink" if key == "default_sink" else "set-default-source"
            run(["pactl", command, real[0]["name"]])
            changed.append(f"{label}: {real[0]['description'] or real[0]['name']}")
    return changed


def boot() -> int:
    """At login: the environment, KDE's portal, sound services that aren't running, EasyEffects' leftovers."""
    for line in sync_environment():
        log("environment: " + line)
    if restart_portals(force=False):
        log("portals: KDE's was running; restarted them for Hyprland")
    started = start_sound()
    if started:
        log("started " + ", ".join(started))
    if not EASYEFFECTS_FLAG.exists() and easyeffects_running():
        run(["pkill", "-x", "easyeffects"])
        log("closed EasyEffects (not turned on: halcyon audio easyeffects on)")
    if not EASYEFFECTS_FLAG.exists() or not easyeffects_running():
        for line in real_defaults(pipewire_nodes()):
            log("default " + line)
    return 0


def fix(dry_run: bool = False) -> int:
    report = status()
    if report["missing"]:
        print("installing " + " ".join(report["missing"]))
        if not dry_run:
            subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm", *report["missing"]], check=False)
    if dry_run:
        print("would put the session right (halcyon audio boot), restart "
              + ", ".join(SOUND_UNITS) + " and the portals")
        return 0
    boot()
    run(["systemctl", "--user", "restart", *SOUND_UNITS])
    restart_portals(force=True)
    log("restarted " + ", ".join(SOUND_UNITS) + " and the portals")
    # WirePlumber takes a moment to find the devices again.
    time.sleep(float(os.environ.get("HALCYON_AUDIO_SETTLE", 2)))
    after = problems(status())
    if after:
        print("\nStill in the way:")
        for line in after:
            print("- " + line)
        print("\nhalcyon audio report writes everything to one file to send.")
        return 1
    print("\nSound, microphones and cameras should all be there now.")
    return 0


def set_easyeffects(on: bool) -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    if on:
        EASYEFFECTS_FLAG.write_text("on\n", encoding="utf-8")
        if shutil.which("easyeffects") and not easyeffects_running():
            subprocess.Popen(["easyeffects", "--hide-window", "--service-mode"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        print("EasyEffects starts at login")
    else:
        EASYEFFECTS_FLAG.unlink(missing_ok=True)
        if easyeffects_running():
            run(["pkill", "-x", "easyeffects"])
        for line in real_defaults(pipewire_nodes()):
            print("default " + line)
        print("EasyEffects no longer starts at login")
    return 0


# --- command line ---------------------------------------------------------------------------------------------------

def print_status(report: dict) -> None:
    for unit, active in report["services"].items():
        print(f"{unit:<32} {'running' if active else 'NOT running'}")
    portals = [u.removesuffix(".service") for u, active in report["portals"].items() if active]
    print(f"{'portals':<32} {', '.join(portals) or 'none running (they start when asked)'}")
    print(f"{'systemd desktop':<32} {report['systemd_desktop'] or '(unset)'}")
    ee = report["easyeffects"]
    print(f"{'EasyEffects':<32} {'running' if ee['running'] else 'not running'}, "
          f"{'starts' if ee['at_login'] else 'does not start'} at login")
    pw = report["pipewire"]
    if pw["ok"]:
        print(f"{'outputs':<32} {', '.join(n['description'] or n['name'] for n in pw['sinks']) or 'none'}")
        print(f"{'microphones':<32} {', '.join(n['description'] or n['name'] for n in pw['sources']) or 'none'}")
        print(f"{'cameras':<32} {', '.join(n['description'] or n['name'] for n in pw['cameras']) or 'none'}")
        print(f"{'default output / microphone':<32} {pw['default_sink'] or '-'} / {pw['default_source'] or '-'}")
    sess = report["session"]
    if sess["id"]:
        print(f"{'login session':<32} {sess['id']} ({sess['type'] or '?'}, seat {sess['seat'] or 'none'}, "
              f"{'active' if sess['active'] else 'NOT active' if sess['active'] is False else '?'})")
    found = problems(report)
    print()
    if found:
        for line in found:
            print("- " + line)
    else:
        print("Nothing in the way.")


def report_text() -> str:
    import io
    from contextlib import redirect_stdout
    info = status()
    out = io.StringIO()
    with redirect_stdout(out):
        print_status(info)
    parts = ["# halcyon audio report, " + time.strftime("%Y-%m-%d %H:%M"), "", out.getvalue().rstrip()]
    try:
        parts += ["", "## Halcyon's sound log (last 40 lines)", *LOG.read_text(encoding="utf-8").splitlines()[-40:]]
    except OSError:
        parts += ["", "## Halcyon's sound log", "(none yet: halcyon audio boot writes it at login)"]
    for cmd in REPORT_COMMANDS:
        if shutil.which(cmd[0]):
            done = run(cmd, timeout=20)
            parts += ["", "## " + " ".join(cmd), (done.stdout + done.stderr).rstrip() or "(nothing)"]
    parts += ["", "## as JSON", json.dumps({**info, "problems": problems(info)}, indent=2)]
    return "\n".join(parts) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon audio", description="Sound, microphones and webcams in Hyprland.")
    parser.add_argument("action", nargs="?", default="status", choices=("status", "boot", "fix", "report", "easyeffects"))
    parser.add_argument("value", nargs="?", choices=("on", "off"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="fix: say what it would do")
    args = parser.parse_args(argv)
    if args.action == "boot":
        return boot()
    if args.action == "fix":
        return fix(dry_run=args.dry_run)
    if args.action == "report":
        REPORT.write_text(report_text(), encoding="utf-8")
        print(f"wrote {REPORT}: send it along with what you saw.")
        return 0
    if args.action == "easyeffects":
        if args.value is None:
            print("on" if EASYEFFECTS_FLAG.exists() else "off")
            return 0
        return set_easyeffects(args.value == "on")
    report = status()
    if args.json:
        print(json.dumps({**report, "problems": problems(report)}, indent=2))
    else:
        print_status(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
