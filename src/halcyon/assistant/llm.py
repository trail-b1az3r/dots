"""Talking to a language model.

Two transports, both over plain HTTP with `urllib`: Ollama's native chat
API and the OpenAI-compatible `/v1/chat/completions` shape that llama.cpp,
vLLM, LM Studio and most local servers also speak. Streaming is the
default because a spoken assistant that waits for a complete paragraph
before saying anything feels broken.

Tool calling is offered to the model when the server supports it, but the
assistant never depends on it: `halcyon.assistant.intents` handles the
commands that matter deterministically, and this layer is for language.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterator

Message = dict[str, Any]


@dataclass
class Chunk:
    """One streamed piece of a reply."""

    text: str = ""
    done: bool = False
    tool_calls: list[dict[str, Any]] | None = None


class LLMError(RuntimeError):
    """The model could not be reached, or refused the request."""


def _request(
    url: str, payload: dict[str, Any], *, timeout: float, headers: dict[str, str] | None = None
) -> Any:
    """POST JSON and return the open response.

    The return type is deliberately loose: `urllib`'s response object is
    not exported by the standard library's own stubs, and all this code
    needs from it is "iterable of lines, and closeable".
    """
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 — the host comes from settings
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace").strip()
        raise LLMError(f"{exc.code} from the model server: {detail[:400]}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise LLMError(f"cannot reach the model server: {exc}") from exc


class Backend:
    """Common interface both transports implement."""

    name = "none"

    def __init__(self, host: str, model: str, *, api_key: str = "", timeout: float = 180.0):
        self.host = host.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def health(self) -> tuple[bool, str]:
        raise NotImplementedError

    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> Iterator[Chunk]:
        raise NotImplementedError


class OllamaBackend(Backend):
    name = "ollama"

    def health(self) -> tuple[bool, str]:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5) as response:  # noqa: S310
                payload = json.loads(response.read(1 << 20))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return False, f"Ollama is not reachable at {self.host} ({exc})"

        names = {
            str(item.get("name", "")).split(":")[0]
            for item in payload.get("models", [])
            if isinstance(item, dict)
        }
        if not names:
            return False, "Ollama is running but has no models (try `ollama pull llama3.2`)"
        if self.model.split(":")[0] not in names:
            return False, (
                f"Ollama does not have {self.model!r} "
                f"(try `ollama pull {self.model}`)"
            )
        return True, f"Ollama · {self.model}"

    def chat(self, messages, *, tools=None, options=None, should_stop=None):
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": options or {},
        }
        if tools:
            payload["tools"] = tools

        response = _request(f"{self.host}/api/chat", payload, timeout=self.timeout)
        try:
            for raw in response:
                if should_stop is not None and should_stop():
                    return
                line = raw.strip()
                if not line:
                    continue
                try:
                    frame = json.loads(line)
                except ValueError:
                    continue
                if frame.get("error"):
                    raise LLMError(str(frame["error"]))
                message = frame.get("message") or {}
                text = str(message.get("content") or "")
                calls = message.get("tool_calls") or None
                if text or calls:
                    yield Chunk(text=text, tool_calls=calls)
                if frame.get("done"):
                    yield Chunk(done=True)
                    return
        finally:
            response.close()


class OpenAICompatibleBackend(Backend):
    name = "openai-compatible"

    def health(self) -> tuple[bool, str]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        request = urllib.request.Request(f"{self.host}/models", headers=headers)  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
                json.loads(response.read(1 << 20))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return False, f"No OpenAI-compatible server at {self.host} ({exc})"
        return True, f"{self.host} · {self.model}"

    def chat(self, messages, *, tools=None, options=None, should_stop=None):
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload.update(
                {
                    key: value
                    for key, value in options.items()
                    if key in ("temperature", "top_p", "max_tokens")
                }
            )
        if tools:
            payload["tools"] = tools

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = _request(
            f"{self.host}/chat/completions", payload, timeout=self.timeout, headers=headers
        )
        try:
            for raw in response:
                if should_stop is not None and should_stop():
                    return
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                body = line[len("data:"):].strip()
                if body == "[DONE]":
                    yield Chunk(done=True)
                    return
                try:
                    frame = json.loads(body)
                except ValueError:
                    continue
                choices = frame.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = str(delta.get("content") or "")
                calls = delta.get("tool_calls") or None
                if text or calls:
                    yield Chunk(text=text, tool_calls=calls)
                if choices[0].get("finish_reason"):
                    yield Chunk(done=True)
                    return
        finally:
            response.close()


def build(settings: dict[str, Any]) -> Backend | None:
    """Construct the backend the settings ask for."""
    local = settings.get("assistant", {}).get("local", {})
    kind = str(local.get("llmBackend", "ollama")).lower()
    host = str(local.get("llmHost", "http://127.0.0.1:11434"))
    model = str(local.get("llmModel", "llama3.2:3b"))

    if kind == "ollama":
        return OllamaBackend(host, model)
    if kind in ("openai", "openai-compatible", "llamacpp", "llama.cpp", "vllm"):
        base = host if host.rstrip("/").endswith("/v1") else host.rstrip("/") + "/v1"
        return OpenAICompatibleBackend(base, model, api_key=str(local.get("apiKey", "")))
    if kind == "none":
        return None
    return OllamaBackend(host, model)
