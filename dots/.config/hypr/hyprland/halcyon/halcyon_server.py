#!/usr/bin/env python3
"""Server mode: `halcyon server on|off|status [--json]`, and the button in Settings > Halcyon > Server mode.

While it is on, this computer stays up for whatever it serves:
  - it never suspends or hibernates: not when idle, not when the lid closes, not from the suspend key, and a
    suspend asked for by hand is refused until server mode is off;
  - the screen never locks or blanks by itself (hypridle pauses its timers while an idle lock is held).

It is a systemd-inhibit lock held by the halcyon-server-mode user service, so `systemd-inhibit --list` shows it,
and turning server mode off (or stopping the service) gives everything back at once. The choice is saved in
Settings (halcyon.serverMode), so it is on again after a restart; logging in to Hyprland runs `server apply`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

UNIT = "halcyon-server-mode.service"
HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
SHELL_CONFIG = CONFIG / "illogical-impulse/config.json"
WHAT = "sleep:idle:handle-lid-switch:handle-suspend-key:handle-hibernate-key"
WHO = "Halcyon"


def run(argv: list[str], timeout: float = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        return subprocess.CompletedProcess(argv, 127, "", str(error))


def read_config() -> dict:
    try:
        data = json.loads(SHELL_CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def wanted() -> bool:
    return (read_config().get("halcyon") or {}).get("serverMode") is True


def save(on: bool) -> None:
    data = read_config()
    data.setdefault("halcyon", {})["serverMode"] = on
    SHELL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = SHELL_CONFIG.with_name(SHELL_CONFIG.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, SHELL_CONFIG)


def active() -> bool:
    return run(["systemctl", "--user", "is-active", "--quiet", UNIT]).returncode == 0


def holding() -> list[str]:
    """The inhibitor lines systemd lists for Halcyon (empty when it holds none)."""
    out = run(["systemd-inhibit", "--list", "--no-legend", "--no-pager"]).stdout
    return [line.strip() for line in out.splitlines() if line.strip().startswith(WHO)]


def notify(summary: str, body: str) -> None:
    if shutil.which("notify-send"):
        run(["notify-send", "-a", "Halcyon", "-i", "network-server", summary, body])


def start() -> bool:
    run(["systemctl", "--user", "daemon-reload"])
    done = run(["systemctl", "--user", "start", UNIT])
    if done.returncode != 0:
        print(f"could not start {UNIT}: {(done.stderr or done.stdout).strip()}", file=sys.stderr)
        return False
    return True


def stop() -> bool:
    return run(["systemctl", "--user", "stop", UNIT]).returncode == 0


def status() -> dict:
    return {"wanted": wanted(), "active": active(), "inhibitors": holding(), "what": WHAT.split(":")}


def main(argv: list[str]) -> int:
    action = argv[0] if argv else "status"
    as_json = "--json" in argv
    quiet = "--quiet" in argv
    if action in ("on", "start"):
        save(True)
        if not start():
            return 1
        if not quiet:
            notify("Server mode on", "No suspend, no automatic lock, no screen blanking, until you turn it off.")
        print("server mode on: no suspend, no automatic lock")
        return 0
    if action in ("off", "stop"):
        save(False)
        stop()
        if not quiet:
            notify("Server mode off", "Locking, screen blanking and suspend are back to normal.")
        print("server mode off")
        return 0
    if action == "toggle":
        return main(["off" if wanted() else "on", *argv[1:]])
    if action == "apply":
        # Make the service match the saved choice (login, and Settings after it writes the choice).
        if wanted() and not active():
            start()
        elif not wanted() and active():
            stop()
        return 0
    if action == "status":
        info = status()
        if as_json:
            print(json.dumps(info))
            return 0
        print(f"server mode {'on' if info['active'] else 'off'}"
              + (" (saved as on, but the service is not running: halcyon server on)" if info["wanted"] and not info["active"] else ""))
        for line in info["inhibitors"]:
            print("  " + line)
        return 0
    print("usage: halcyon server on|off|toggle|status [--json]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
