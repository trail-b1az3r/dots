"""The NixOrb backend.

NixOrb is a separate assistant with its own UI, models and settings. This
adapter drives its real, documented interfaces and nothing else:

* a Unix control socket at `$XDG_RUNTIME_DIR/nixorb.sock`, speaking one
  line of text per request and one per reply, with the commands `ping`,
  `trigger`, `status` and `quit`;
* the `nixorb` CLI, for `ask`, `tts`, `start` and `version`.

It deliberately does not read or write NixOrb's own config file. Settings
that belong to NixOrb are changed in NixOrb (`nixorb config`), and
Halcyon's Settings app links to it rather than duplicating it.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from typing import Any, Callable

from ..protocol import Event
from . import Provider

SOCKET_TIMEOUT = 2.0


def socket_path(settings: dict[str, Any] | None = None) -> str:
    """Where NixOrb's control socket lives.

    Mirrors NixOrb's own resolution order so the two agree without either
    having to be told: XDG_RUNTIME_DIR first, then a uid-suffixed path in
    /tmp.
    """
    configured = str(
        (settings or {}).get("assistant", {}).get("nixorb", {}).get("socketPath", "")
    ).strip()
    if configured:
        return os.path.expanduser(configured)

    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and os.path.isdir(runtime):
        return os.path.join(runtime, "nixorb.sock")
    return f"/tmp/nixorb-{os.getuid()}.sock"  # noqa: S108 — matches NixOrb


def control(command: str, settings: dict[str, Any] | None = None, *, timeout: float = SOCKET_TIMEOUT) -> str | None:
    """Send one control command. None when nothing is listening."""
    path = socket_path(settings)
    if not os.path.exists(path):
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect(path)
            connection.sendall(command.strip().encode("utf-8") + b"\n")
            chunks: list[bytes] = []
            while b"\n" not in b"".join(chunks):
                chunk = connection.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
    except (OSError, socket.timeout):
        return None
    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def running(settings: dict[str, Any] | None = None) -> bool:
    reply = control("ping", settings, timeout=1.0)
    return bool(reply and reply.startswith("ok"))


class NixOrbProvider(Provider):
    id = "nixorb"
    title = "NixOrb"

    def binary(self) -> str | None:
        return shutil.which("nixorb")

    def available(self) -> bool:
        return self.binary() is not None

    def health(self) -> tuple[bool, str]:
        exe = self.binary()
        if exe is None:
            return False, "NixOrb is not installed (pip install nixorb)"

        if running(self.settings):
            status = control("status", self.settings, timeout=8.0) or ""
            if status.startswith("ok"):
                # "ok: llm=ollama/model up asr=… tts=… actions=on"
                detail = status[3:].strip() if status.startswith("ok:") else status[2:].strip()
                return True, f"running · {detail}"
            return True, "running"

        return True, "installed, not running (start it with `nixorb start`)"

    def supports_voice_input(self) -> bool:
        # NixOrb captures and transcribes speech itself; Halcyon hands the
        # turn over rather than recording in parallel.
        return running(self.settings)

    def listen(self, *, emit, should_stop) -> str | None:
        """Hand the turn to NixOrb's own orb.

        NixOrb owns the microphone, the wake word and the conversation UI
        while it is running. Trying to drive its speech pipeline from here
        would mean two processes competing for one input device.
        """
        if not running(self.settings):
            ok, message = self.start()
            if not ok:
                emit(Event("error", text=message))
                return None

        reply = control("trigger", self.settings, timeout=4.0)
        if reply is None or not reply.startswith("ok"):
            emit(Event("error", text="NixOrb did not accept the trigger."))
            return None

        emit(
            Event(
                "handoff",
                text="NixOrb is listening.",
                state="listening",
                data={"provider": self.id},
            )
        )
        return None

    def respond(self, prompt, history, *, emit, should_stop) -> str:
        exe = self.binary()
        if exe is None:
            message = "NixOrb is not installed."
            emit(Event("error", text=message))
            return message

        emit(Event("state", state="thinking"))
        try:
            done = subprocess.run(
                [exe, "ask", prompt],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            message = f"NixOrb did not answer: {exc}"
            emit(Event("error", text=message))
            return message

        if should_stop():
            return ""

        if done.returncode != 0:
            detail = (done.stderr or done.stdout).strip().splitlines()
            message = detail[-1] if detail else "NixOrb returned an error."
            emit(Event("error", text=message))
            return message

        text = _clean(done.stdout)
        # `nixorb ask` is a one-shot command with no streaming API, so the
        # answer arrives whole. Emitting it as a single delta keeps the
        # client's rendering path identical for both backends.
        if text:
            emit(Event("delta", text=text))
        return text

    def speak(self, text: str, *, should_stop) -> bool:
        exe = self.binary()
        if exe is None or not text.strip():
            return False
        try:
            done = subprocess.run(
                [exe, "tts", text], capture_output=True, timeout=180, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0

    def start(self) -> tuple[bool, str]:
        exe = self.binary()
        if exe is None:
            return False, "NixOrb is not installed."
        if running(self.settings):
            return True, "NixOrb is already running."
        try:
            subprocess.Popen(
                [exe, "start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            return False, str(exc)
        return True, "Starting NixOrb."

    def stop(self) -> tuple[bool, str]:
        reply = control("quit", self.settings, timeout=5.0)
        if reply and reply.startswith("ok"):
            return True, "NixOrb is shutting down."
        return False, "NixOrb is not running."


def _clean(text: str) -> str:
    """Strip the CLI's decoration from an answer.

    `nixorb ask` prints a "🤔 Querying …" progress line before the reply
    and prefixes the answer with 🤖; neither belongs in a transcript.
    """
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("🤔", "❌", "═")):
            continue
        if stripped.startswith("🤖"):
            stripped = stripped[1:].strip()
        lines.append(stripped)
    return "\n".join(lines).strip()
