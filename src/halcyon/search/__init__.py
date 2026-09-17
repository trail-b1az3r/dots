"""Spotlight: one query in, ranked results out.

The orchestrator's job is to keep the list feeling instant. Providers run
in declaration order with a shared wall-clock budget; one that is slow or
throws is dropped from that query rather than being allowed to stall the
window. Results are then merged, de-duplicated and ranked globally, so a
calculator answer can outrank an application and a web search can never
outrank anything.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from .providers import REGISTRY, Result

__all__ = ["Result", "search", "REGISTRY"]

#: Total budget for a query. Past this, whatever has been collected is
#: returned — a launcher that is 40 ms late feels broken.
DEFAULT_BUDGET = 0.6


def enabled_providers(settings: dict[str, Any]) -> list[str]:
    configured = settings.get("search", {}).get("providers", {})
    return [name for name in REGISTRY if configured.get(name, True)]


def search(
    query: str,
    settings: dict[str, Any],
    *,
    limit: int | None = None,
    providers: Iterable[str] | None = None,
    budget: float = DEFAULT_BUDGET,
) -> list[Result]:
    """Run the providers and return a ranked, de-duplicated list."""
    query = query.strip()
    limit = limit or int(settings.get("search", {}).get("maxResults", 40))
    names = list(providers) if providers else enabled_providers(settings)

    deadline = time.monotonic() + budget
    collected: list[Result] = []

    for name in names:
        provider = REGISTRY.get(name)
        if provider is None:
            continue
        if time.monotonic() > deadline:
            break
        try:
            # Each provider is asked for a slice, not the whole list, so
            # one prolific source cannot crowd the others out.
            collected.extend(provider(query, settings, max(4, limit // 2)))
        except Exception:  # noqa: BLE001 — one bad provider must not break Spotlight
            continue

    seen: set[str] = set()
    unique: list[Result] = []
    for result in sorted(collected, key=lambda r: r.score, reverse=True):
        if result.id in seen:
            continue
        seen.add(result.id)
        unique.append(result)
        if len(unique) >= limit:
            break

    return unique
