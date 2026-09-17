"""The assistant daemon.

Holds the conversation, owns the microphone for the length of a turn, and
streams events to whichever clients are connected — the Quickshell orb,
the Waybar indicator, a terminal. One turn runs at a time on purpose: two
overlapping answers through one speaker is not a feature.

Cancellation is cooperative and checked everywhere that blocks, so
`halcyon assistant cancel` stops a reply mid-sentence rather than after
it finishes.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import socketserver
import stat
import threading
import time
from typing import Any

from .. import paths, settings as settings_module, state as state_module
from . import providers as providers_module
from .protocol import Event, socket_path

HISTORY_FILE = "conversation.json"


class Session:
    """Conversation state, shared by every connection."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.turn_lock = threading.Lock()
        self.cancel = threading.Event()
        self.state = "idle"
        self.history: list[dict[str, str]] = []
        self.listeners: set["Handler"] = set()
        self.last_error = ""
        self.provider_id = ""
        self.pending_confirmation: dict[str, Any] | None = None
        self._load_history()

    # ── history ────────────────────────────────────────────────────────

    def _history_path(self) -> str:
        return str(paths.CONVERSATION_DIR / HISTORY_FILE)

    def _load_history(self) -> None:
        try:
            with open(self._history_path(), "r", encoding="utf-8") as handle:
                saved = json.load(handle)
        except (OSError, ValueError):
            return
        if isinstance(saved, list):
            self.history = [
                item for item in saved
                if isinstance(item, dict) and item.get("role") and item.get("content")
            ]

    def save_history(self, settings: dict[str, Any]) -> None:
        privacy = settings.get("assistant", {}).get("privacy", {})
        if not privacy.get("storeConversations", True):
            with contextlib.suppress(OSError):
                os.unlink(self._history_path())
            return

        limit = int(settings.get("assistant", {}).get("historyLimit", 50))
        trimmed = self.history[-limit * 2:]
        paths.CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._history_path(), "w", encoding="utf-8") as handle:
                json.dump(trimmed, handle, indent=1)
            # A transcript is private; do not leave it group-readable.
            os.chmod(self._history_path(), stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    # ── state ──────────────────────────────────────────────────────────

    def set_state(self, value: str) -> None:
        with self.lock:
            if self.state == value:
                return
            self.state = value
        self.broadcast(Event("state", state=value))
        state_module.write(
            "assistant",
            {"state": value, "provider": self.provider_id, "error": self.last_error},
        )

    def broadcast(self, event: Event) -> None:
        with self.lock:
            targets = list(self.listeners)
        for handler in targets:
            with contextlib.suppress(OSError, ValueError):
                handler.send_event(event)


SESSION = Session()


class Handler(socketserver.StreamRequestHandler):
    """One client connection."""

    timeout = 600

    def send_event(self, event: Event) -> None:
        self.wfile.write(event.encode())
        self.wfile.flush()

    def handle(self) -> None:
        line = self.rfile.readline(1 << 20)
        if not line:
            return
        try:
            request = json.loads(line)
        except ValueError:
            self.send_event(Event("error", text="Malformed request."))
            return
        if not isinstance(request, dict):
            self.send_event(Event("error", text="Expected a JSON object."))
            return

        operation = str(request.get("op", ""))
        handler = getattr(self, f"op_{operation.replace('-', '_')}", None)
        if handler is None:
            self.send_event(Event("error", text=f"Unknown operation {operation!r}."))
            return

        try:
            handler(request)
        except BrokenPipeError:
            return
        except Exception as exc:  # noqa: BLE001 — one client must not kill the daemon
            with contextlib.suppress(OSError):
                self.send_event(Event("error", text=str(exc)))

    # ── operations ─────────────────────────────────────────────────────

    def op_ping(self, _request: dict[str, Any]) -> None:
        self.send_event(Event("final", text="ok"))

    def op_status(self, _request: dict[str, Any]) -> None:
        settings = settings_module.load()
        provider, reason = providers_module.select(settings)
        self.send_event(
            Event(
                "final",
                state=SESSION.state,
                data={
                    "state": SESSION.state,
                    "provider": provider.id if provider else "",
                    "providerTitle": provider.title if provider else "",
                    "reason": reason,
                    "voiceInput": bool(provider and provider.supports_voice_input()),
                    "turns": len(SESSION.history) // 2,
                    "error": SESSION.last_error,
                },
            )
        )

    def op_providers(self, _request: dict[str, Any]) -> None:
        settings = settings_module.load()
        self.send_event(
            Event("final", data={"providers": providers_module.describe_all(settings)})
        )

    def op_history(self, _request: dict[str, Any]) -> None:
        self.send_event(Event("final", data={"history": list(SESSION.history)}))

    def op_clear(self, _request: dict[str, Any]) -> None:
        SESSION.history.clear()
        SESSION.save_history(settings_module.load())
        SESSION.broadcast(Event("cleared"))
        self.send_event(Event("final", text="Conversation cleared."))

    def op_cancel(self, _request: dict[str, Any]) -> None:
        SESSION.cancel.set()
        SESSION.set_state("idle")
        self.send_event(Event("final", text="Cancelled."))

    def op_confirm(self, request: dict[str, Any]) -> None:
        """Run, or drop, an action that was held back for confirmation.

        Destructive actions never run on the strength of a transcript
        alone; the user confirms them in the UI, and that confirmation
        arrives here.
        """
        from .. import actions as actions_module

        pending = SESSION.pending_confirmation
        if pending is None:
            self.send_event(Event("final", text="There is nothing waiting to be confirmed."))
            return

        SESSION.pending_confirmation = None

        if not request.get("accept"):
            SESSION.broadcast(Event("cancelled", text="Not doing that."))
            self.send_event(Event("final", text="Cancelled."))
            return

        invocation = actions_module.invoke(
            str(pending.get("action", "")),
            pending.get("params") or {},
            confirmed=True,
        )
        SESSION.broadcast(
            Event("action", text=invocation.message, data=invocation.as_dict())
        )
        self.send_event(Event("final", text=invocation.message, data=invocation.as_dict()))

    def op_ask(self, request: dict[str, Any]) -> None:
        prompt = str(request.get("text", "")).strip()
        if not prompt:
            self.send_event(Event("error", text="Nothing to ask."))
            return
        self._turn(prompt=prompt, listen=False, speak=bool(request.get("speak", True)))

    def op_listen(self, request: dict[str, Any]) -> None:
        self._turn(prompt="", listen=True, speak=bool(request.get("speak", True)))

    def op_subscribe(self, _request: dict[str, Any]) -> None:
        """Stay connected and receive every event until the client leaves."""
        with SESSION.lock:
            SESSION.listeners.add(self)
        self.send_event(Event("state", state=SESSION.state))
        try:
            while True:
                # The client is not expected to send anything; this blocks
                # until it disconnects, which readline reports as b"".
                if not self.rfile.readline(4096):
                    return
        finally:
            with SESSION.lock:
                SESSION.listeners.discard(self)

    # ── the turn ───────────────────────────────────────────────────────

    def _turn(self, *, prompt: str, listen: bool, speak: bool) -> None:
        if not SESSION.turn_lock.acquire(blocking=False):
            self.send_event(Event("error", text="The assistant is already busy."))
            return

        settings = settings_module.load()
        SESSION.cancel.clear()
        SESSION.last_error = ""

        errored = False

        def emit(event: Event) -> None:
            nonlocal errored
            if event.event == "error":
                errored = True
            with contextlib.suppress(OSError, ValueError):
                self.send_event(event)
            if event.event == "confirm":
                # Hold the action until the user says yes; the daemon is
                # the only place that can run it afterwards.
                SESSION.pending_confirmation = {
                    "action": event.data.get("action", ""),
                    "params": event.data.get("params") or {},
                }
            if event.event in ("state", "action", "transcript", "confirm"):
                SESSION.broadcast(event)
            if event.event == "error":
                SESSION.last_error = event.text
                SESSION.broadcast(event)

        def should_stop() -> bool:
            return SESSION.cancel.is_set()

        try:
            provider, reason = providers_module.select(settings)
            if provider is None:
                SESSION.set_state("offline")
                emit(Event("error", text=reason))
                self.send_event(Event("final", text=reason))
                return

            SESSION.provider_id = provider.id

            if listen:
                SESSION.set_state("listening")
                heard = provider.listen(emit=emit, should_stop=should_stop)
                if heard is None:
                    # Either it failed, or the provider took the turn over
                    # (NixOrb raises its own UI and answers there).
                    SESSION.set_state("idle")
                    self.send_event(Event("final", text=""))
                    return
                prompt = heard

            if not prompt or should_stop():
                SESSION.set_state("idle")
                self.send_event(Event("final", text=""))
                return

            SESSION.history.append({"role": "user", "content": prompt})
            SESSION.set_state("thinking")

            answer = provider.respond(
                prompt, SESSION.history[:-1], emit=emit, should_stop=should_stop
            )

            if answer and not errored:
                SESSION.history.append({"role": "assistant", "content": answer})
                SESSION.save_history(settings)
            elif errored:
                # A backend that could not answer did not have a turn;
                # keeping its error in the transcript would poison the
                # next prompt's context.
                if SESSION.history and SESSION.history[-1].get("role") == "user":
                    SESSION.history.pop()

            if speak and answer and not should_stop():
                voice = settings.get("assistant", {}).get("voice", {})
                if voice.get("enabled", True):
                    SESSION.set_state("speaking")
                    provider.speak(answer, should_stop=should_stop)

            SESSION.set_state("idle")
            self.send_event(Event("final", text=answer))
        finally:
            SESSION.cancel.clear()
            SESSION.turn_lock.release()


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address) -> None:  # noqa: D102
        # The default implementation prints a traceback to stderr for
        # every disconnect; a client closing a stream is normal.
        pass


def _claim_socket(path: str) -> bool:
    """True when the socket is ours to create.

    A stale file after a crash is common; a live daemon on the other end
    is not something to stomp on, so probe before unlinking.
    """
    if not os.path.exists(path):
        return True
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(1.0)
            probe.connect(path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(path)
        return True
    return False


def run(*, foreground: bool = True) -> int:
    paths.ensure_dirs()
    path = socket_path()

    if not _claim_socket(path):
        print(f"halcyon: an assistant daemon is already listening on {path}")
        return 1

    server = Server(path, Handler)
    # The conversation is private: only this user may connect.
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    settings = settings_module.load()
    provider, reason = providers_module.select(settings)
    SESSION.provider_id = provider.id if provider else ""
    SESSION.set_state("idle" if provider else "offline")

    if foreground:
        print(f"halcyon assistant listening on {path}")
        print(f"  backend: {reason}")

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        with contextlib.suppress(OSError):
            os.unlink(path)
        state_module.write("assistant", {"state": "offline", "provider": "", "error": ""})
    return 0
