"""The local backend: whisper.cpp, an LLM server, and Piper.

Assembled from whatever is installed, and degrading one layer at a time
rather than all at once. With no microphone it is still a text assistant;
with no model it still executes the deterministic command intents; with
no voice it still answers in writing. Each missing layer produces a
specific message, because "the assistant doesn't work" is not something a
user can act on.

Nothing the model produces is executed. Commands are recognised by
`halcyon.assistant.intents` before the model is consulted, and tool calls
the model makes are validated by `halcyon.actions` like any other request.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from ... import actions as actions_module
from .. import audio, intents as intents_module, llm as llm_module, stt, tts
from ..protocol import Event
from . import Provider

SYSTEM_PROMPT = (
    "You are Halcyon, the assistant built into this Linux desktop. "
    "Answer briefly and plainly — your replies are often read aloud, so "
    "keep them to a few sentences unless asked for detail. "
    "You can control the desktop only through the tools you are given; "
    "never claim to have done something you were not able to do. "
    "If you do not know something, say so."
)


class LocalProvider(Provider):
    id = "local"
    title = "Local AI"

    # ── availability ───────────────────────────────────────────────────

    def available(self) -> bool:
        # The intent layer needs nothing at all, so this backend can
        # always take a turn — it just may only be able to run commands.
        return True

    def health(self) -> tuple[bool, str]:
        backend = llm_module.build(self.settings)
        parts: list[str] = []

        if backend is None:
            parts.append("language model: disabled")
            model_ok = False
        else:
            model_ok, message = backend.health()
            parts.append(f"language model: {message}")

        parts.append(f"speech to text: {stt.describe(self.settings)}")
        parts.append(f"text to speech: {tts.describe(self.settings)}")
        if not audio.recorder_available():
            parts.append("microphone: no recorder (pipewire-utils or pulseaudio-utils)")

        # Commands work without a model, so "ok" means "can do something
        # useful", not "everything is installed".
        return True, " · ".join(parts) if model_ok else " · ".join(parts)

    def supports_voice_input(self) -> bool:
        return audio.recorder_available() and stt.available(self.settings)

    # ── listening ──────────────────────────────────────────────────────

    def listen(self, *, emit, should_stop) -> str | None:
        if not audio.recorder_available():
            emit(Event("error", text="No audio recorder is installed (pw-record, parecord or arecord)."))
            return None

        if self.settings.get("assistant", {}).get("microphone", {}).get("respectMute", True):
            if audio.microphone_muted():
                emit(Event("error", text="Your microphone is muted."))
                return None

        if not stt.available(self.settings):
            emit(Event("error", text=stt.describe(self.settings) + " — cannot transcribe speech."))
            return None

        device = str(self.settings.get("assistant", {}).get("microphone", {}).get("device", "default"))
        emit(Event("state", state="listening"))

        recording = audio.record(
            device=device if device != "default" else None,
            should_stop=should_stop,
        )
        if recording is None:
            emit(Event("error", text="Recording failed."))
            return None
        if recording.cancelled:
            return None
        if not recording.path:
            emit(Event("error", text="I did not hear anything."))
            return None

        emit(Event("state", state="thinking"))
        try:
            ok, text = stt.transcribe(recording.path, self.settings)
        finally:
            try:
                os.unlink(recording.path)
            except OSError:
                pass

        if not ok:
            emit(Event("error", text=f"Could not transcribe: {text}"))
            return None
        if not text:
            emit(Event("error", text="I did not catch that."))
            return None

        emit(Event("transcript", text=text))
        return text

    # ── answering ──────────────────────────────────────────────────────

    def respond(self, prompt, history, *, emit, should_stop) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return ""

        # 1. Deterministic commands first. Faster than inference, and it
        #    cannot invent a parameter the user did not say.
        intent = intents_module.parse(prompt)
        if intent is not None:
            return self._run_intent(intent, emit=emit)

        # 2. Otherwise it is a question, and questions need a model.
        backend = llm_module.build(self.settings)
        if backend is None:
            message = (
                "I can run desktop commands, but no language model is "
                "configured for questions (Settings → AI Assistant)."
            )
            emit(Event("error", text=message))
            return message

        ok, status = backend.health()
        if not ok:
            emit(Event("error", text=status))
            return status

        emit(Event("state", state="thinking"))

        local = self.settings.get("assistant", {}).get("local", {})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-12:])
        messages.append({"role": "user", "content": prompt})

        options = {
            "temperature": float(local.get("temperature", 0.6)),
            "num_predict": int(local.get("maxTokens", 1024)),
            "max_tokens": int(local.get("maxTokens", 1024)),
        }

        collected: list[str] = []
        pending_calls: list[dict[str, Any]] = []
        try:
            for chunk in backend.chat(
                messages,
                tools=_tool_schema(),
                options=options,
                should_stop=should_stop,
            ):
                if should_stop():
                    emit(Event("state", state="idle"))
                    return "".join(collected)
                if chunk.tool_calls:
                    pending_calls.extend(chunk.tool_calls)
                if chunk.text:
                    collected.append(chunk.text)
                    emit(Event("delta", text=chunk.text))
                if chunk.done:
                    break
        except llm_module.LLMError as exc:
            message = str(exc)
            emit(Event("error", text=message))
            return message

        if pending_calls and not should_stop():
            for outcome in self._run_tool_calls(pending_calls, emit=emit):
                collected.append(outcome)
                emit(Event("delta", text=outcome))

        return "".join(collected).strip()

    def _run_intent(self, intent: intents_module.Intent, *, emit) -> str:
        action = actions_module.REGISTRY.get(intent.action)
        emit(
            Event(
                "action",
                text=action.title if action else intent.action,
                data={"action": intent.action, "params": intent.params, "source": "intent"},
            )
        )
        invocation = actions_module.invoke(
            intent.action, intent.params, settings=self.settings
        )

        if invocation.needs_confirmation:
            emit(
                Event(
                    "confirm",
                    text=f"{action.title if action else intent.action}?",
                    data=invocation.as_dict(),
                )
            )
            return f"{invocation.message} Say yes to go ahead."

        emit(Event("delta", text=invocation.message))
        return invocation.message

    def _run_tool_calls(self, calls: list[dict[str, Any]], *, emit) -> list[str]:
        outcomes: list[str] = []
        for call in calls[:4]:
            function = (call or {}).get("function") or {}
            name = str(function.get("name", "")).replace("__", ".")
            raw_arguments = function.get("arguments")
            if isinstance(raw_arguments, str):
                try:
                    params = json.loads(raw_arguments)
                except ValueError:
                    params = {}
            elif isinstance(raw_arguments, dict):
                params = raw_arguments
            else:
                params = {}

            emit(
                Event(
                    "action",
                    text=name,
                    data={"action": name, "params": params, "source": "model"},
                )
            )
            invocation = actions_module.invoke(name, params, settings=self.settings)
            if invocation.needs_confirmation:
                emit(Event("confirm", text=invocation.message, data=invocation.as_dict()))
            outcomes.append(invocation.message)
        return outcomes

    # ── speaking ───────────────────────────────────────────────────────

    def speak(self, text: str, *, should_stop) -> bool:
        voice = self.settings.get("assistant", {}).get("voice", {})
        if not voice.get("enabled", True) or not text.strip():
            return False
        if should_stop():
            return False

        path = tts.synthesise(text, self.settings)
        if path is None:
            return False
        try:
            process = audio.play_async(path, volume=float(voice.get("volume", 1.0)))
            if process is None:
                return False
            while process.poll() is None:
                if should_stop():
                    process.terminate()
                    return False
                try:
                    process.wait(timeout=0.2)
                except Exception:  # noqa: BLE001 — timeout is the normal path
                    continue
            return process.returncode == 0
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


def _tool_schema() -> list[dict[str, Any]]:
    """The action registry, as OpenAI-style tool definitions.

    Offered to the model when the server supports tools. The model can
    only ever name an action and its parameters; `halcyon.actions`
    validates both before anything happens.
    """
    tools: list[dict[str, Any]] = []
    for action in actions_module.REGISTRY.values():
        properties: dict[str, Any] = {}
        required: list[str] = []
        for param in action.params:
            schema: dict[str, Any] = {
                "type": {
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                }.get(param.type, "string"),
                "description": param.description or param.name,
            }
            if param.choices:
                schema["enum"] = list(param.choices)
            if param.minimum is not None:
                schema["minimum"] = param.minimum
            if param.maximum is not None:
                schema["maximum"] = param.maximum
            properties[param.name] = schema
            if param.required:
                required.append(param.name)

        tools.append(
            {
                "type": "function",
                "function": {
                    # Dots are not valid in every server's function-name
                    # validation, so they travel as double underscores.
                    "name": action.id.replace(".", "__"),
                    "description": action.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )
    return tools
