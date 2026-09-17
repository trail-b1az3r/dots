"""`halcyon assistant …`"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .. import settings as settings_module
from . import client, daemon, providers as providers_module
from .protocol import Event


def add_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("assistant", help="the AI voice assistant")
    sub = parser.add_subparsers(dest="assistant_command", required=True)

    ask = sub.add_parser("ask", help="ask a question")
    ask.add_argument("prompt", nargs="+")
    ask.add_argument("--no-speak", action="store_true")
    ask.add_argument("--json", action="store_true")

    listen = sub.add_parser("listen", help="listen, then answer")
    listen.add_argument("--hold", action="store_true", help="push-to-talk (stop on release)")
    listen.add_argument("--no-speak", action="store_true")

    sub.add_parser("cancel", help="stop the current turn")
    sub.add_parser("toggle", help="listen, or cancel if already busy")
    sub.add_parser("start", help="start the daemon in the background")
    sub.add_parser("stop", help="stop the daemon")
    sub.add_parser("history", help="print the conversation")
    sub.add_parser("clear", help="forget the conversation")
    providers_parser = sub.add_parser(
        "providers", help="list the backends and their health"
    )
    providers_parser.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="show the assistant's state")
    status.add_argument("--json", action="store_true")

    confirm = sub.add_parser("confirm", help="answer a pending confirmation")
    confirm.add_argument("answer", choices=["yes", "no"])

    provider = sub.add_parser("provider", help="choose the backend")
    provider.add_argument("name", choices=["nixorb", "local", "auto"])

    daemon_parser = sub.add_parser("daemon", help="run the daemon in the foreground")
    daemon_parser.add_argument("--quiet", action="store_true")

    parser.set_defaults(func=_run, json=False)


def _run(args: argparse.Namespace) -> int:
    return dispatch(args)


def dispatch(args: argparse.Namespace) -> int:
    command = getattr(args, "assistant_command", "")

    if command == "daemon":
        return daemon.run(foreground=not args.quiet)

    if command == "start":
        return _report(*client.start())

    if command == "stop":
        return _report(*client.stop())

    if command == "status":
        info = client.status()
        if getattr(args, "json", False):
            json.dump(info, sys.stdout)
            sys.stdout.write("\n")
            return 0
        print(f"State: {info['state']}")
        print(info["tooltip"])
        return 0

    if command == "providers":
        settings = settings_module.load()
        described = providers_module.describe_all(settings)
        chosen, reason = providers_module.select(settings)
        if getattr(args, "json", False):
            json.dump(described, sys.stdout)
            sys.stdout.write("\n")
            return 0
        for entry in described:
            mark = "✓" if entry["ok"] else "·"
            active = "  ← in use" if chosen and chosen.id == entry["id"] else ""
            print(f" {mark} {entry['title']:<10} {entry['status']}{active}")
        print(f"\nSelection: {reason}")
        return 0

    if command == "provider":
        settings_module.set_value("assistant.provider", args.name)
        return _report(True, f"Assistant backend set to {args.name}.")

    if command == "cancel":
        return _report(*client.cancel())

    if command == "confirm":
        return _report(*client.confirm(args.answer == "yes"))

    if command == "clear":
        return _report(*client.clear())

    if command == "history":
        for turn in client.history():
            who = "You" if turn.get("role") == "user" else "Halcyon"
            print(f"{who}: {turn.get('content', '')}")
        return 0

    if command == "toggle":
        info = client.status()
        if not info["running"]:
            ok, message = client.start()
            if not ok:
                return _report(ok, message)
        if info["state"] in ("listening", "thinking", "speaking"):
            return _report(*client.cancel())
        return _listen(speak=True)

    if command == "ask":
        prompt = " ".join(args.prompt)
        if not client.running():
            ok, message = client.start()
            if not ok:
                return _report(ok, message)
        ok, answer = client.ask(prompt, speak=not args.no_speak, on_event=_echo)
        if getattr(args, "json", False):
            json.dump({"ok": ok, "answer": answer}, sys.stdout)
            sys.stdout.write("\n")
            return 0 if ok else 1
        if not sys.stdout.isatty():
            print(answer)
        elif not ok:
            print(answer, file=sys.stderr)
        return 0 if ok else 1

    if command == "listen":
        return _listen(speak=not args.no_speak)

    return 2


def _listen(*, speak: bool) -> int:
    if not client.running():
        ok, message = client.start()
        if not ok:
            return _report(ok, message)
    ok, answer = client.listen(speak=speak, on_event=_echo)
    if not ok:
        print(answer, file=sys.stderr)
        return 1
    return 0


_STREAMED = False


def _echo(event: Event) -> None:
    """Print streamed output as it arrives, when attached to a terminal."""
    global _STREAMED
    if not sys.stdout.isatty():
        return
    if event.event == "transcript":
        print(f"You: {event.text}")
    elif event.event == "delta":
        sys.stdout.write(event.text)
        sys.stdout.flush()
        _STREAMED = True
    elif event.event == "action":
        print(f"\n[{event.text}]")
    elif event.event in ("final", "error") and _STREAMED:
        print()
        _STREAMED = False


def _report(ok: bool, message: str) -> int:
    if message:
        print(message, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1
