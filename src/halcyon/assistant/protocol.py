"""The wire format between the assistant daemon and its clients.

Newline-delimited JSON over a Unix socket in XDG_RUNTIME_DIR. One object
per line, in both directions; a request may be answered by many events,
which is how streaming works without a second protocol.

The socket is user-private (0600 in a 0700 directory) because a
conversation with an assistant is as sensitive as the clipboard.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator

from .. import paths

#: Requests are small; a client that sends more than this is confused.
MAX_LINE = 1 << 20
CONNECT_TIMEOUT = 2.0
READ_TIMEOUT = 300.0


def socket_path() -> str:
    return str(paths.ASSISTANT_SOCKET)


@dataclass
class Event:
    """One message from the daemon."""

    event: str
    text: str = ""
    state: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def encode(self) -> bytes:
        return (json.dumps(asdict(self), separators=(",", ":")) + "\n").encode("utf-8")

    @staticmethod
    def decode(line: bytes | str) -> "Event":
        payload = json.loads(line)
        return Event(
            event=str(payload.get("event", "")),
            text=str(payload.get("text", "")),
            state=str(payload.get("state", "")),
            data=payload.get("data") or {},
        )


def send_request(payload: dict[str, Any], *, timeout: float = READ_TIMEOUT) -> Iterator[Event]:
    """Send one request and yield events until the daemon closes the turn.

    Raises ConnectionError when nothing is listening, which every caller
    treats as "the assistant is not running" rather than as a failure.
    """
    path = socket_path()
    if not os.path.exists(path):
        raise ConnectionError(f"no assistant socket at {path}")

    try:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(CONNECT_TIMEOUT)
        connection.connect(path)
    except (ConnectionRefusedError, FileNotFoundError) as exc:
        raise ConnectionError(f"nothing is listening on {path}") from exc
    except OSError as exc:
        raise ConnectionError(f"cannot reach the assistant: {exc}") from exc

    try:
        connection.settimeout(timeout)
        connection.sendall(
            (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        )
        buffer = b""
        while True:
            try:
                chunk = connection.recv(65536)
            except socket.timeout:
                return
            if not chunk:
                return
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    event = Event.decode(line)
                except (ValueError, TypeError):
                    continue
                yield event
                if event.event in ("final", "error", "closed"):
                    return
    finally:
        try:
            connection.close()
        except OSError:
            pass
