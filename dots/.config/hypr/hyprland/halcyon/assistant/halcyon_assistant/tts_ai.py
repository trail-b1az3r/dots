"""A natural voice from an AI provider: Gemini's text-to-speech, or any OpenAI-compatible /audio/speech (OpenAI,
or a local server such as Kokoro-FastAPI or LocalAI). Both answer with raw 16-bit PCM, which pcm.player plays.

The text of the reply is sent to that provider, and nothing else. The keys are the ones the assistant and the AI
sidebar already share (`halcyon assistant key gemini|openai`).
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request

from . import config

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_VOICE = "Kore"
OPENAI_MODEL = "gpt-4o-mini-tts"
OPENAI_VOICE = "alloy"
PCM_RATE = 24000          # both answer at 24 kHz unless they say otherwise
MAX_CHARS = 4000          # longer replies are cut, so a wall of text does not cost a fortune


class VoiceError(Exception):
    pass


def provider(settings) -> str | None:
    """Which provider speaks: the one chosen, else Gemini if its key is stored, else OpenAI. None when neither can."""
    chosen = settings.get("aiVoiceProvider", "auto")
    if chosen == "gemini":
        return "gemini" if config.api_key("gemini") else None
    if chosen == "openai":
        return "openai" if (config.api_key("openai") or _local_openai(settings)) else None
    if config.api_key("gemini"):
        return "gemini"
    if config.api_key("openai"):
        return "openai"
    return None


def _local_openai(settings) -> bool:
    """An OpenAI-compatible voice server on this machine needs no key."""
    endpoint = settings.get("aiVoiceEndpoint") or ""
    return bool(re.match(r"https?://(127\.0\.0\.1|localhost|\[::1\])[:/]", endpoint))


def _request(url, body, headers, timeout=60) -> tuple[bytes, str]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        raise VoiceError(f"HTTP {error.code}: {error.read().decode(errors='replace')[:300]}") from None
    except urllib.error.URLError as error:
        raise VoiceError(f"can't reach {url.split('/')[2]}: {error.reason}") from None
    except (TimeoutError, OSError) as error:
        raise VoiceError(str(error)) from None


def rate_from_mime(mime: str, default: int = PCM_RATE) -> int:
    """Gemini says "audio/L16;codec=pcm;rate=24000"."""
    match = re.search(r"rate=(\d+)", mime or "")
    return int(match.group(1)) if match else default


def gemini_pcm(text: str, settings) -> tuple[bytes, int]:
    key = config.api_key("gemini")
    if not key:
        raise VoiceError("no Gemini key: halcyon assistant key gemini")
    model = settings.get("aiVoiceModel") or GEMINI_MODEL
    body = {
        "contents": [{"parts": [{"text": text[:MAX_CHARS]}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": settings.get("aiVoice") or GEMINI_VOICE}}},
        },
    }
    raw, _ = _request(GEMINI_URL.format(model=model), body, {"x-goog-api-key": key})
    return parse_gemini(raw)


def parse_gemini(raw: bytes) -> tuple[bytes, int]:
    try:
        data = json.loads(raw.decode())
        part = next(p for p in data["candidates"][0]["content"]["parts"] if "inlineData" in p)
        inline = part["inlineData"]
        return base64.b64decode(inline["data"]), rate_from_mime(inline.get("mimeType", ""))
    except (ValueError, KeyError, IndexError, StopIteration, TypeError):
        raise VoiceError(f"Gemini sent no audio: {raw[:200].decode(errors='replace')}") from None


def openai_pcm(text: str, settings) -> tuple[bytes, int]:
    endpoint = (settings.get("aiVoiceEndpoint") or config.DEFAULT_ENDPOINTS["openai"]).rstrip("/")
    key = config.api_key("openai")
    if not key and not _local_openai(settings):
        raise VoiceError("no OpenAI key: halcyon assistant key openai")
    body = {"model": settings.get("aiVoiceModel") or OPENAI_MODEL, "input": text[:MAX_CHARS],
            "voice": settings.get("aiVoice") or OPENAI_VOICE, "response_format": "pcm"}
    raw, mime = _request(f"{endpoint}/audio/speech", body, {"Authorization": f"Bearer {key}"} if key else {})
    if mime.startswith("application/json"):
        raise VoiceError(f"no audio from {endpoint}: {raw[:200].decode(errors='replace')}")
    return raw, PCM_RATE


def synthesize(text: str, settings) -> tuple[bytes, int]:
    """(PCM, sample rate) for the text, from the provider settings choose. Raises VoiceError."""
    which = provider(settings)
    if which == "gemini":
        return gemini_pcm(text, settings)
    if which == "openai":
        return openai_pcm(text, settings)
    raise VoiceError("no AI voice: store a key (halcyon assistant key gemini, or key openai)")
