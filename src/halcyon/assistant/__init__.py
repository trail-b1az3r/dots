"""Halcyon's voice assistant.

Two backends sit behind one interface. NixOrb, when it is installed, is
driven through its documented control socket and CLI. The local backend
composes whatever speech, language and voice tools the machine has —
whisper.cpp, Ollama, Piper — and degrades one layer at a time rather than
all at once: no microphone still leaves you a text assistant, no model
still leaves you the deterministic command intents.

Nothing here can run a shell command the model chose. Every effect on the
machine goes through `halcyon.actions`, which validates an action id and
typed parameters against an allow-list.
"""

from __future__ import annotations

#: Conversation states the UI animates between.
STATES = ("offline", "idle", "listening", "thinking", "speaking")

__all__ = ["STATES"]
