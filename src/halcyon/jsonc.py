"""A JSON reader that tolerates comments and trailing commas.

Waybar's own configuration format is JSON with `//` comments, and the
shipped module definitions use them heavily — they are the only place a
reader finds out what a module is for. `json` in the standard library
will not parse that, and pulling in json5 for twenty lines of stripping
is not worth a dependency on a machine that may have no pip at all.
"""

from __future__ import annotations

import json
from typing import Any


def strip(text: str) -> str:
    """Remove `//` and `/* */` comments and trailing commas.

    String-aware: a `//` inside a JSON string (a URL, a format spec) is
    left alone, which a regex-based stripper gets wrong.
    """
    out: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    escaped = False

    while index < length:
        char = text[index]

        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue

        if char == "/" and index + 1 < length:
            following = text[index + 1]
            if following == "/":
                while index < length and text[index] != "\n":
                    index += 1
                continue
            if following == "*":
                index += 2
                while index + 1 < length and not (
                    text[index] == "*" and text[index + 1] == "/"
                ):
                    index += 1
                index += 2
                continue

        out.append(char)
        index += 1

    return _drop_trailing_commas("".join(out))


def _drop_trailing_commas(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            out.append(char)
            continue

        if char == ",":
            rest = text[index + 1:]
            stripped = rest.lstrip()
            if stripped[:1] in ("}", "]"):
                continue

        out.append(char)

    return "".join(out)


def loads(text: str) -> Any:
    return json.loads(strip(text))


def load_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return loads(handle.read())
