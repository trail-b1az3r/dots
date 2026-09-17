"""Fuzzy matching and scoring for Spotlight.

The ranking rule that matters: an exact or prefix match on a short name
must always beat a scattered subsequence match inside a long one. Without
that, typing "disc" surfaces "Disk Usage Analyser" above "Discord", and
the launcher feels broken even though the matcher "worked".
"""

from __future__ import annotations

import re
import unicodedata

_WORD_SPLIT = re.compile(r"[\s\-_./]+")


def normalise(text: str) -> str:
    """Casefold and strip accents so "café" matches "cafe"."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.casefold()


def subsequence_score(needle: str, haystack: str) -> float | None:
    """Score a subsequence match, or None when there is no match.

    Consecutive characters and matches at word boundaries score higher,
    which is what makes acronym typing ("vsc" → "Visual Studio Code")
    land where a user expects.
    """
    if not needle:
        return 0.0
    if not haystack:
        return None

    score = 0.0
    position = 0
    streak = 0

    for char in needle:
        found = haystack.find(char, position)
        if found < 0:
            return None
        if found == position and position > 0:
            streak += 1
            score += 3.0 + streak
        else:
            streak = 0
            score += 1.0
        if found == 0 or haystack[found - 1] in " -_./":
            score += 4.0
        position = found + 1

    # Prefer the shorter of two haystacks that both matched.
    score -= len(haystack) * 0.02
    return score


def score(query: str, *fields: str, weights: tuple[float, ...] = ()) -> float | None:
    """Best score across several fields, with the first weighted highest."""
    needle = normalise(query).strip()
    if not needle:
        return 0.0

    best: float | None = None
    for index, field in enumerate(fields):
        if not field:
            continue
        weight = weights[index] if index < len(weights) else max(0.25, 1.0 - index * 0.25)
        hay = normalise(field)

        if hay == needle:
            candidate = 1000.0
        elif hay.startswith(needle):
            candidate = 600.0 - len(hay) * 0.5
        elif any(word.startswith(needle) for word in _WORD_SPLIT.split(hay)):
            candidate = 400.0 - len(hay) * 0.5
        elif needle in hay:
            candidate = 250.0 - hay.index(needle) * 2 - len(hay) * 0.3
        else:
            sub = subsequence_score(needle, hay)
            candidate = None if sub is None else 60.0 + sub

        if candidate is None:
            continue
        candidate *= weight
        if best is None or candidate > best:
            best = candidate

    return best
