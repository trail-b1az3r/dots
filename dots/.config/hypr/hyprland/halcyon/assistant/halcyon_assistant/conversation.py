"""One conversation with the model: history, the tool loop, short memory."""

import time
from datetime import datetime

from . import actions

SYSTEM = """You are Halcyon, the voice assistant built into this Linux desktop (Hyprland, \
with the illogical-impulse shell and Halcyon themes). What you say is read aloud, so answer \
in one to three short, natural sentences: no markdown, lists, emoji or URLs.

When the user asks you to do something on the computer, use one of your tools; say briefly \
what you did once it's done. If no tool can do what they asked, say so plainly instead of \
pretending. Don't use a tool when they only ask a question.

It is {now}."""

MAX_TOOL_ROUNDS = 5
MEMORY_SECONDS = 300
MAX_TURNS = 24


class Conversation:
    def __init__(self, provider, allow_actions=True, clock=time.monotonic):
        self.provider = provider
        self.allow_actions = allow_actions
        self.history = []
        self.clock = clock
        self.last = 0.0

    def _forget_if_stale(self):
        if self.clock() - self.last > MEMORY_SECONDS:
            self.history = []
        # Drop the oldest exchanges, cutting only at a user turn so a tool
        # call is never separated from its result.
        while len(self.history) > MAX_TURNS:
            cut = next((i for i, t in enumerate(self.history[1:], 1) if t["role"] == "user"), None)
            if cut is None:
                break
            self.history = self.history[cut:]

    def ask(self, text, run_action=actions.run, on_action=None):
        """Returns the reply to speak. Raises providers.ProviderError."""
        self._forget_if_stale()
        self.history.append({"role": "user", "text": text})
        tools = actions.ACTIONS if self.allow_actions else {}
        system = SYSTEM.format(now=datetime.now().strftime("%A %d %B %Y, %H:%M"))
        reply = ""
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                answer = self.provider.chat(self.history, system, tools)
                self.history.append({"role": "assistant", "text": answer["text"], "calls": answer["calls"],
                                     "raw": answer.get("raw")})
                reply = answer["text"] or reply
                if not answer["calls"]:
                    break
                for call in answer["calls"]:
                    if on_action:
                        on_action(call["name"], call["args"])
                    result = run_action(call["name"], call["args"]) if self.allow_actions \
                        else "error: actions are turned off"
                    self.history.append({"role": "tool", "id": call["id"], "name": call["name"], "result": result})
            else:
                reply = reply or "That took too many steps, so I stopped."
        except Exception:
            # Don't leave a half-finished exchange behind to confuse the next one.
            while self.history and self.history[-1]["role"] != "user":
                self.history.pop()
            if self.history:
                self.history.pop()
            raise
        self.last = self.clock()
        return reply or "Done."
