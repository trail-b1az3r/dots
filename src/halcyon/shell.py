"""Talking to the Quickshell instance.

Every keybind that opens a panel goes through here rather than calling
`qs` directly, for one reason: when Quickshell is not running, a keybind
must fail quietly and leave the rest of the desktop working. `call()`
returns a message instead of a traceback, and the callers treat a missing
shell as "that surface is unavailable", not as an error worth a dialog.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from . import paths

#: The Quickshell config directory name, i.e. ~/.config/quickshell/halcyon.
CONFIG_NAME = "halcyon"


def binary() -> str | None:
    for candidate in ("qs", "quickshell"):
        if shutil.which(candidate):
            return candidate
    return None


def running() -> bool:
    exe = binary()
    if exe is None:
        return False
    try:
        done = subprocess.run(
            [exe, "-c", CONFIG_NAME, "ipc", "show"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def call(target: str, function: str, arguments: list[str] | None = None) -> tuple[bool, str]:
    """Invoke an IpcHandler function in the running shell."""
    exe = binary()
    if exe is None:
        return False, "Quickshell is not installed; this panel is unavailable."

    argv = [exe, "-c", CONFIG_NAME, "ipc", "call", target, function]
    argv += [str(a) for a in (arguments or [])]
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=6, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Could not reach the shell: {exc}"

    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip().splitlines()
        reason = detail[-1] if detail else "no response"
        return False, f"Quickshell did not answer ({reason})."
    return True, done.stdout.strip()


#: When Quickshell cannot answer, these surfaces have a dmenu-based
#: stand-in. The desktop is meant to degrade, not to stop.
FALLBACKS = {
    ("spotlight", "toggle"): ("launcher", "launcher.sh", []),
    ("spotlight", "open"): ("launcher", "launcher.sh", []),
    ("spotlight", "search"): ("launcher", "launcher.sh", []),
    ("power", "toggle"): ("power", "power-menu.sh", []),
    ("control", "network"): ("network", "wifi-menu.sh", []),
    ("control", "audio"): ("audio", "output-menu.sh", []),
}


def fallback_for(target: str, function: str) -> str | None:
    """The stand-in script for a surface, if one is installed."""
    entry = FALLBACKS.get((target, function))
    if entry is None:
        return None

    directory, name, _ = entry
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(here))
    candidates = [
        os.path.join(str(paths.DATA_DIR), "scripts", directory, name),
        os.path.join(repo_root, "scripts", directory, name),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def call_or_fallback(
    target: str, function: str, arguments: list[str] | None = None
) -> tuple[bool, str]:
    """Ask the shell; fall back to a standalone menu when it is down.

    This is what makes "Quickshell unavailable → the desktop still works"
    true rather than aspirational: a keybind or a bar button reaches the
    same feature either way.
    """
    ok, message = call(target, function, arguments)
    if ok:
        return True, message

    script = fallback_for(target, function)
    if script is None:
        return False, message

    try:
        subprocess.Popen(
            [script, *(arguments or [])],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return False, f"{message} The fallback also failed: {exc}"
    return True, f"The shell is not running; used {os.path.basename(script)} instead."


def start(detached: bool = True) -> tuple[bool, str]:
    exe = binary()
    if exe is None:
        return False, "Quickshell is not installed."
    argv = [exe, "-c", CONFIG_NAME]
    if detached:
        argv.append("--daemonize")
    try:
        subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return False, str(exc)
    return True, "Started the Halcyon shell."


def stop() -> tuple[bool, str]:
    exe = binary()
    if exe is None:
        return False, "Quickshell is not installed."
    try:
        done = subprocess.run(
            [exe, "-c", CONFIG_NAME, "kill"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return (done.returncode == 0, done.stdout.strip() or "Stopped the Halcyon shell.")
