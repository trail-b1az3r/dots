"""Talking to the assistant daemon from everything else.

Every function here treats "the daemon is not running" as an ordinary
outcome rather than an error: Waybar still draws an indicator, Spotlight
still offers to ask, and the keybind still does something sensible.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Callable, Iterator

from .. import paths, settings as settings_module
from . import providers as providers_module
from .protocol import Event, send_request, socket_path


def running() -> bool:
    try:
        for event in send_request({"op": "ping"}, timeout=3.0):
            if event.event == "final":
                return True
    except ConnectionError:
        return False
    return False


def status(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """State plus a tooltip, for the bar and for `halcyon status`."""
    settings = settings or settings_module.load()

    try:
        for event in send_request({"op": "status"}, timeout=5.0):
            if event.event == "final":
                data = event.data
                provider = data.get("providerTitle") or data.get("provider") or "no backend"
                lines = [f"Halcyon assistant · {provider}"]
                if data.get("reason"):
                    lines.append(str(data["reason"]))
                if data.get("error"):
                    lines.append(str(data["error"]))
                lines.append(f"{data.get('turns', 0)} turn(s) in this conversation")
                return {
                    "state": str(data.get("state", "idle")),
                    "provider": str(data.get("provider", "")),
                    "tooltip": "\n".join(lines),
                    "running": True,
                }
    except ConnectionError:
        pass

    provider, reason = providers_module.select(settings)
    return {
        "state": "offline",
        "provider": provider.id if provider else "",
        "tooltip": "Halcyon assistant is not running\n"
                   f"{reason}\nStart it with: halcyon assistant start",
        "running": False,
    }


def stream(payload: dict[str, Any], *, timeout: float = 300.0) -> Iterator[Event]:
    return send_request(payload, timeout=timeout)


def ask(prompt: str, *, speak: bool = True, on_event: Callable[[Event], None] | None = None) -> tuple[bool, str]:
    """Ask a question and wait for the answer."""
    collected: list[str] = []
    try:
        for event in send_request({"op": "ask", "text": prompt, "speak": speak}):
            if on_event is not None:
                on_event(event)
            if event.event == "delta":
                collected.append(event.text)
            elif event.event == "error":
                return False, event.text
            elif event.event == "final":
                return True, (event.text or "".join(collected))
    except ConnectionError as exc:
        return False, str(exc)
    return True, "".join(collected)


def ask_detached(prompt: str) -> tuple[bool, str]:
    """Fire a question at the daemon without waiting for the answer.

    Used by Spotlight: the user has already moved on, and the reply will
    arrive in the assistant panel.
    """
    if running():
        try:
            subprocess.Popen(
                [sys.executable, "-m", "halcyon.cli", "assistant", "ask", prompt],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True, "Asked the assistant."
        except OSError as exc:
            return False, str(exc)
    return False, "The assistant is not running (halcyon assistant start)."


def listen(*, speak: bool = True, on_event: Callable[[Event], None] | None = None) -> tuple[bool, str]:
    collected: list[str] = []
    try:
        for event in send_request({"op": "listen", "speak": speak}):
            if on_event is not None:
                on_event(event)
            if event.event == "delta":
                collected.append(event.text)
            elif event.event == "error":
                return False, event.text
            elif event.event == "final":
                return True, (event.text or "".join(collected))
    except ConnectionError as exc:
        return False, str(exc)
    return True, "".join(collected)


def cancel() -> tuple[bool, str]:
    return _simple({"op": "cancel"}, timeout=5.0)


def confirm(accept: bool) -> tuple[bool, str]:
    return _simple({"op": "confirm", "accept": accept}, timeout=60.0)


def history() -> list[dict[str, str]]:
    try:
        for event in send_request({"op": "history"}, timeout=5.0):
            if event.event == "final":
                return list(event.data.get("history") or [])
    except ConnectionError:
        pass
    return []


def clear() -> tuple[bool, str]:
    return _simple({"op": "clear"}, timeout=5.0)


def _simple(payload: dict[str, Any], *, timeout: float) -> tuple[bool, str]:
    """One request, one answer — reporting an error event as the answer."""
    try:
        for event in send_request(payload, timeout=timeout):
            if event.event == "final":
                return True, event.text
            if event.event == "error":
                return False, event.text
    except ConnectionError as exc:
        return False, str(exc)
    return False, "The assistant did not answer."


def start() -> tuple[bool, str]:
    """Start the daemon in the background."""
    if running():
        return True, "The assistant is already running."
    try:
        subprocess.Popen(
            [sys.executable, "-m", "halcyon.cli", "assistant", "daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return False, str(exc)

    import time

    for _ in range(40):
        time.sleep(0.1)
        if running():
            return True, "Assistant started."
    return False, "The assistant did not come up; run `halcyon assistant daemon` to see why."


def stop() -> tuple[bool, str]:
    """Stop the daemon by removing its socket and signalling it."""
    path = socket_path()
    if not os.path.exists(path):
        return True, "The assistant was not running."
    cancel()
    # The daemon has no "quit" op on purpose — it is managed by systemd
    # when installed that way, and by the user otherwise.
    import signal

    stopped = False
    try:
        entries = os.listdir("/proc")
    except OSError:
        entries = []
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as handle:
                cmdline = handle.read().split(b"\0")
        except OSError:
            continue
        if b"halcyon.cli" in b" ".join(cmdline) and b"daemon" in cmdline:
            with open(os.devnull, "w"):
                pass
            try:
                os.kill(int(entry), signal.SIGTERM)
                stopped = True
            except OSError:
                continue
    return stopped, "Assistant stopped." if stopped else "Could not find the assistant process."
