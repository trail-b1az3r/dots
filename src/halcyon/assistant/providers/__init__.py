"""Assistant backends, and how one gets chosen.

A backend answers questions and, optionally, speaks. Halcyon ships two:
NixOrb, driven through its own control socket and CLI, and a local stack
assembled from whisper.cpp, Ollama and Piper. Both can be installed at
once; `select()` decides which one a turn goes to.

Adding a third means implementing `Provider` and adding one line to
`REGISTRY` — see docs/ai-assistant.md.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

from ..protocol import Event

#: Called by a provider to stream progress back to the client.
Emit = Callable[[Event], None]


class Provider:
    """What every assistant backend has to be able to do."""

    id = "none"
    title = "None"

    def __init__(self, settings: dict[str, Any]):
        self.settings = settings

    def available(self) -> bool:
        """True when this backend could serve a turn right now."""
        raise NotImplementedError

    def health(self) -> tuple[bool, str]:
        """`(ok, human-readable status)` — shown in Settings and diagnose."""
        raise NotImplementedError

    def describe(self) -> dict[str, Any]:
        ok, message = self.health()
        return {"id": self.id, "title": self.title, "ok": ok, "status": message}

    def respond(
        self,
        prompt: str,
        history: list[dict[str, str]],
        *,
        emit: Emit,
        should_stop: Callable[[], bool],
    ) -> str:
        """Answer `prompt`, streaming through `emit`, returning the text."""
        raise NotImplementedError

    def speak(self, text: str, *, should_stop: Callable[[], bool]) -> bool:
        """Say `text` aloud. False when this backend cannot speak."""
        return False

    def listen(self, *, emit: Emit, should_stop: Callable[[], bool]) -> str | None:
        """Capture speech and return a transcript, or None."""
        return None

    def supports_voice_input(self) -> bool:
        return False


def registry() -> dict[str, type[Provider]]:
    from .local import LocalProvider
    from .nixorb import NixOrbProvider

    return {
        NixOrbProvider.id: NixOrbProvider,
        LocalProvider.id: LocalProvider,
    }


def build(name: str, settings: dict[str, Any]) -> Provider | None:
    factory = registry().get(name)
    return factory(settings) if factory else None


def select(settings: dict[str, Any]) -> tuple[Provider | None, str]:
    """Pick the backend for this turn, and say why.

    `automatic` prefers NixOrb when it is actually running — it owns the
    microphone and its own UI while it is up, and having two assistants
    listening at once is worse than either alone. Otherwise the local
    stack takes the turn.
    """
    configured = str(settings.get("assistant", {}).get("provider", "auto")).lower()
    available = registry()

    if configured in available:
        provider = build(configured, settings)
        if provider is not None and provider.available():
            return provider, f"{provider.title} (chosen in Settings)"
        if provider is not None:
            ok, message = provider.health()
            return None, f"{provider.title} is selected but unavailable: {message}"
        return None, f"Unknown assistant provider {configured!r}"

    for name in ("nixorb", "local"):
        provider = build(name, settings)
        if provider is not None and provider.available():
            return provider, f"{provider.title} (automatic)"

    return None, "No assistant backend is available"


def describe_all(settings: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, factory in registry().items():
        try:
            out.append(factory(settings).describe())
        except Exception as exc:  # noqa: BLE001 — a broken backend must still list
            out.append({"id": name, "title": name, "ok": False, "status": str(exc)})
    return out
