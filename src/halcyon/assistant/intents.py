"""Deterministic command understanding.

"Turn the volume up", "open Firefox", "lock the screen" — these are the
things a desktop assistant is actually asked to do, and they do not need
a language model. Matching them with rules is faster (no inference), more
reliable (no hallucinated parameters), and more honest about what the
assistant can do.

Anything that is not a recognised command falls through to the model,
which is for language rather than for control.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .. import actions as actions_module


@dataclass
class Intent:
    action: str
    params: dict[str, Any]
    confidence: float
    utterance: str = ""


Rule = tuple[re.Pattern[str], Callable[[re.Match[str]], Intent | None]]

_NUMBER_WORDS = {
    "zero": 0, "ten": 10, "twenty": 20, "twenty five": 25, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "seventy five": 75,
    "eighty": 80, "ninety": 90, "a hundred": 100, "one hundred": 100,
    "half": 50, "max": 100, "maximum": 100, "full": 100, "mute": 0,
}

_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _percent(text: str, default: int = 10) -> int:
    match = re.search(r"(\d{1,3})\s*(?:%|percent)?", text)
    if match:
        return max(0, min(100, int(match.group(1))))
    for word, value in _NUMBER_WORDS.items():
        if word in text:
            return value
    return default


def _rules() -> list[Rule]:
    def volume_set(match: re.Match[str]) -> Intent:
        return Intent("volume.set", {"percent": _percent(match.group(0), 50)}, 0.95)

    def volume_up(match: re.Match[str]) -> Intent:
        step = _percent(match.group(0), 10)
        return Intent("volume.adjust", {"delta": step if step else 10}, 0.95)

    def volume_down(match: re.Match[str]) -> Intent:
        step = _percent(match.group(0), 10)
        return Intent("volume.adjust", {"delta": -(step if step else 10)}, 0.95)

    def brightness_set(match: re.Match[str]) -> Intent:
        return Intent("brightness.set", {"percent": max(1, _percent(match.group(0), 50))}, 0.95)

    def brightness_up(match: re.Match[str]) -> Intent:
        return Intent("brightness.adjust", {"delta": _percent(match.group(0), 10) or 10}, 0.95)

    def brightness_down(match: re.Match[str]) -> Intent:
        return Intent("brightness.adjust", {"delta": -(_percent(match.group(0), 10) or 10)}, 0.95)

    def open_app(match: re.Match[str]) -> Intent | None:
        name = match.group("name").strip(" .!?")
        if not name or len(name) > 60:
            return None
        return Intent("app.open", {"name": name}, 0.9)

    def close_app(match: re.Match[str]) -> Intent | None:
        name = match.group("name").strip(" .!?")
        if not name or len(name) > 60:
            return None
        return Intent("app.close", {"name": name}, 0.88)

    def workspace(match: re.Match[str]) -> Intent | None:
        raw = match.group("index").strip().lower()
        index = _ORDINALS.get(raw)
        if index is None:
            try:
                index = int(raw)
            except ValueError:
                return None
        if not 1 <= index <= 20:
            return None
        return Intent("workspace.switch", {"index": index}, 0.92)

    def state_of(match: re.Match[str], on_words=("on", "enable", "turn on")) -> str:
        text = match.group(0).lower()
        if re.search(r"\b(off|disable|stop)\b", text):
            return "off"
        if re.search(r"\b(on|enable|start)\b", text):
            return "on"
        return "toggle"

    rules: list[Rule] = [
        (re.compile(r"\b(?:set\s+(?:the\s+)?volume\s+to|volume\s+to)\b.*", re.I), volume_set),
        (re.compile(r"\b(?:turn|put)?\s*(?:the\s+)?volume\s+(?:up|higher)\b.*|\blouder\b.*|\bturn it up\b.*", re.I), volume_up),
        (re.compile(r"\b(?:turn|put)?\s*(?:the\s+)?volume\s+(?:down|lower)\b.*|\bquieter\b.*|\bturn it down\b.*", re.I), volume_down),
        (re.compile(r"\b(?:mute|unmute|silence)\b(?!.*\b(?:mic|microphone)\b)", re.I),
         lambda m: Intent("volume.mute", {"state": "off" if "unmute" in m.group(0).lower() else "toggle"}, 0.93)),
        (re.compile(r"\b(?:mute|unmute)\b.*\b(?:mic|microphone)\b|\b(?:mic|microphone)\b.*\b(?:mute|unmute|off|on)\b", re.I),
         lambda m: Intent("mic.mute", {"state": "off" if "unmute" in m.group(0).lower() else "toggle"}, 0.93)),

        (re.compile(r"\b(?:set\s+)?(?:the\s+)?(?:screen\s+)?brightness\s+to\b.*", re.I), brightness_set),
        (re.compile(r"\bbrighter\b.*|\b(?:screen\s+)?brightness\s+up\b.*", re.I), brightness_up),
        (re.compile(r"\bdimmer\b.*|\bdim\s+(?:the\s+)?screen\b.*|\b(?:screen\s+)?brightness\s+down\b.*", re.I), brightness_down),

        (re.compile(r"\b(?:open|launch|start|run)\s+(?P<name>[\w .+-]{2,60})\s*$", re.I), open_app),
        (re.compile(r"\b(?:close|quit|exit)\s+(?P<name>[\w .+-]{2,60})\s*$", re.I), close_app),

        (re.compile(r"\b(?:switch|go|move)\s+to\s+(?:workspace|desktop|space)\s+(?P<index>\w+)", re.I), workspace),
        # "go to the second workspace" — the ordinal comes first here, so
        # it needs its own pattern rather than a wider one that would also
        # swallow "go to the settings workspace".
        (re.compile(
            r"\b(?:switch|go|move)\s+to\s+(?:the\s+)?(?P<index>\w+)\s+"
            r"(?:workspace|desktop|space)\b", re.I), workspace),
        (re.compile(r"\bworkspace\s+(?P<index>\d{1,2})\b", re.I), workspace),

        (re.compile(r"\b(?:turn\s+)?(?:wi-?fi|wireless)\s*(?:on|off)?\b", re.I),
         lambda m: Intent("wifi.set", {"state": state_of(m)}, 0.9)),
        (re.compile(r"\b(?:turn\s+)?bluetooth\s*(?:on|off)?\b", re.I),
         lambda m: Intent("bluetooth.set", {"state": state_of(m)}, 0.9)),
        (re.compile(r"\bairplane\s+mode\b", re.I),
         lambda m: Intent("airplane.set", {"state": state_of(m)}, 0.9)),

        (re.compile(r"\block\s+(?:the\s+)?(?:screen|session|computer|laptop)\b|\block it\b", re.I),
         lambda _m: Intent("session.lock", {}, 0.95)),
        (re.compile(r"\b(?:go\s+to\s+sleep|suspend|sleep\s+the\s+(?:computer|laptop))\b", re.I),
         lambda _m: Intent("session.suspend", {}, 0.9)),
        (re.compile(r"\b(?:reboot|restart)\s+(?:the\s+)?(?:computer|machine|system|laptop)\b", re.I),
         lambda _m: Intent("session.reboot", {}, 0.9)),
        (re.compile(r"\b(?:shut\s*down|power\s+off|turn\s+off)\s+(?:the\s+)?(?:computer|machine|system|laptop)\b", re.I),
         lambda _m: Intent("session.shutdown", {}, 0.9)),
        (re.compile(r"\blog\s*out\b", re.I), lambda _m: Intent("session.logout", {}, 0.9)),

        (re.compile(r"\b(?:next|skip)\s+(?:song|track)\b|\bskip\s+(?:this|it)\b", re.I),
         lambda _m: Intent("media.control", {"command": "next"}, 0.93)),
        (re.compile(r"\b(?:previous|last|go back a)\s+(?:song|track)\b", re.I),
         lambda _m: Intent("media.control", {"command": "previous"}, 0.93)),
        (re.compile(r"\b(?:pause|resume|play)\s+(?:the\s+)?(?:music|song|track|playback|it)\b|\bpause\s*$|\bplay\s*$", re.I),
         lambda _m: Intent("media.control", {"command": "play-pause"}, 0.9)),

        (re.compile(r"\b(?:dark|night)\s+mode\b", re.I),
         lambda _m: Intent("theme.mode", {"mode": "dark"}, 0.93)),
        (re.compile(r"\b(?:light|day)\s+mode\b", re.I),
         lambda _m: Intent("theme.mode", {"mode": "light"}, 0.93)),
        (re.compile(r"\b(?:change|next|new)\s+(?:the\s+)?wallpaper\b", re.I),
         lambda _m: Intent("wallpaper.next", {}, 0.92)),
        (re.compile(r"\b(?:do\s+not\s+disturb|dnd)\b", re.I),
         lambda m: Intent("notifications.dnd", {"state": state_of(m)}, 0.9)),

        (re.compile(r"\b(?:take|grab)\s+a?\s*screenshot\b|\bscreenshot\b", re.I),
         lambda m: Intent(
             "screenshot.take",
             {"mode": "region" if re.search(r"\bregion|selection|area\b", m.string, re.I) else "screen"},
             0.9,
         )),

        (re.compile(r"\b(?:battery\s+saver|save\s+battery|power\s+sav\w+)\b", re.I),
         lambda _m: Intent("power.profile", {"profile": "battery-saver"}, 0.9)),
        (re.compile(r"\b(?:performance\s+mode|max(?:imum)?\s+performance)\b", re.I),
         lambda _m: Intent("power.profile", {"profile": "performance"}, 0.9)),

        (re.compile(r"\b(?:open|show)\s+(?:the\s+)?settings\b", re.I),
         lambda _m: Intent("settings.open", {"section": ""}, 0.92)),
        (re.compile(r"\b(?:open|launch)\s+(?:a\s+)?terminal\b", re.I),
         lambda _m: Intent("terminal.open", {}, 0.93)),
    ]
    return rules


_RULES = _rules()

#: Filler people say to an assistant that should not change the meaning.
_PREAMBLE = re.compile(
    r"^\s*(?:hey\s+halcyon|halcyon|please|could you|can you|would you|i want you to|"
    r"i'd like you to|go ahead and)\s*,?\s*",
    re.IGNORECASE,
)


def parse(utterance: str) -> Intent | None:
    """Recognise a command, or return None to let the model answer."""
    text = _PREAMBLE.sub("", utterance or "").strip()
    if not text:
        return None

    best: Intent | None = None
    for pattern, builder in _RULES:
        match = pattern.search(text)
        if match is None:
            continue
        try:
            intent = builder(match)
        except (ValueError, IndexError, AttributeError):
            continue
        if intent is None:
            continue
        if intent.action not in actions_module.REGISTRY:
            continue
        intent.utterance = text
        if best is None or intent.confidence > best.confidence:
            best = intent
    return best
