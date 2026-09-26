"""AI providers behind one interface.

A conversation is a list of turns:
    {"role": "user", "text": ...}
    {"role": "assistant", "text": ..., "calls": [{"id", "name", "args"}], "raw": <provider data>}
    {"role": "tool", "id": ..., "name": ..., "result": ...}
Each provider turns that into its own request format and back. "raw" keeps
a provider's reply exactly as it came, for providers that need it echoed
unchanged on the next request (Claude's thinking blocks, Gemini's thought
signatures).

Claude goes through the official anthropic SDK; the others are plain HTTPS
with the standard library, the way illogical-impulse's AI sidebar talks to
them.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import config


class ProviderError(Exception):
    pass


def _post(url, body, headers, timeout=90):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise ProviderError(f"HTTP {error.code}: {detail}") from None
    except urllib.error.URLError as error:
        raise ProviderError(f"can't reach {url.split('/')[2]}: {error.reason}") from None
    except (TimeoutError, ValueError) as error:
        raise ProviderError(str(error)) from None


def _new_id():
    return "call_" + uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Claude (Anthropic SDK)
# ---------------------------------------------------------------------------

class Claude:
    name = "claude"

    def __init__(self, model, key=None, client=None):
        self.model = model
        if client is None:
            import anthropic
            # With no stored key, the SDK finds ANTHROPIC_API_KEY or an
            # `ant auth login` profile on its own.
            client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        self.client = client

    @staticmethod
    def messages(history):
        out = []
        for turn in history:
            if turn["role"] == "user":
                out.append({"role": "user", "content": turn["text"]})
            elif turn["role"] == "assistant":
                # The response content exactly as returned, thinking blocks
                # included: the API requires them back unchanged.
                content = turn.get("raw") or [{"type": "text", "text": turn.get("text") or "…"}]
                out.append({"role": "assistant", "content": content})
            elif turn["role"] == "tool":
                result = {"type": "tool_result", "tool_use_id": turn["id"], "content": turn["result"]}
                if turn["result"].startswith("error:"):
                    result["is_error"] = True
                # All results for one assistant turn go back in one user message.
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(result)
                else:
                    out.append({"role": "user", "content": [result]})
        return out

    def chat(self, history, system, tools):
        import anthropic
        request = dict(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=self.messages(history),
            # Spoken replies should come back quickly; simple requests don't
            # need deep thinking.
            output_config={"effort": "low"},
            # If a safety classifier declines, re-run on Anthropic's
            # recommended fallback model instead of failing.
            betas=["server-side-fallback-2026-07-01"],
        )
        if tools:
            request["tools"] = [{"name": n, "description": t["description"], "input_schema": t["parameters"]}
                                for n, t in tools.items()]
        try:
            try:
                response = self.client.beta.messages.create(fallbacks="default", **request)
            except TypeError:
                # An SDK older than the fallbacks parameter: send it untyped.
                response = self.client.beta.messages.create(extra_body={"fallbacks": "default"}, **request)
        except anthropic.AuthenticationError:
            raise ProviderError("the Anthropic API key was rejected") from None
        except anthropic.RateLimitError:
            raise ProviderError("Anthropic's rate limit was hit; try again in a moment") from None
        except anthropic.APIStatusError as error:
            raise ProviderError(f"Anthropic API error {error.status_code}: {error.message}") from None
        except anthropic.APIConnectionError:
            raise ProviderError("can't reach the Anthropic API") from None

        if response.stop_reason == "refusal":
            return {"text": "Sorry, I can't help with that one.", "calls": [], "raw": None}
        text = " ".join(b.text for b in response.content if b.type == "text").strip()
        calls = [{"id": b.id, "name": b.name, "args": b.input}
                 for b in response.content if b.type == "tool_use"]
        return {"text": text, "calls": calls, "raw": response.content}


# ---------------------------------------------------------------------------
# Claude with a Pro or Max plan, through Claude Code
# ---------------------------------------------------------------------------

def claude_code_signed_in():
    """Whether Claude Code has a subscription login it can use."""
    if not shutil.which("claude"):
        return False
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return (config_dir / ".credentials.json").is_file()


class ClaudeCode:
    """Claude on your own Pro/Max plan, by running Claude Code headless.

    Anthropic doesn't let other apps sign in with a claude.ai account or
    reuse its login, so this doesn't: it runs Anthropic's own Claude Code
    CLI (`claude -p`), which you sign in to yourself. Its built-in tools are
    all switched off; the only tools it gets are Halcyon's desktop actions,
    served by mcp_server.py. Requests count against your plan's usage.
    """

    name = "claude-code"
    ENV_CREDENTIALS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE")
    DESKTOP_ENV = ("PATH", "HOME", "USER", "LANG", "HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY",
                   "DISPLAY", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
                   "XDG_DATA_DIRS", "XDG_CURRENT_DESKTOP", "DBUS_SESSION_BUS_ADDRESS")

    def __init__(self, model="", run=subprocess.run, workdir=None):
        self.model = model or "your plan's default"
        self._model_flag = model
        self.run = run
        self.session = None
        self.workdir = workdir or config.ASSISTANT_STATE

    def command(self, prompt, system, tools):
        package_root = str(Path(__file__).resolve().parent.parent)
        # What the actions need to reach the desktop, passed through
        # explicitly in case MCP servers get a trimmed environment.
        env = {k: os.environ[k] for k in self.DESKTOP_ENV if k in os.environ}
        env["PYTHONPATH"] = package_root
        mcp = {"mcpServers": {"halcyon": {
            "command": sys.executable, "args": ["-m", "halcyon_assistant.mcp_server"], "env": env}}}
        allowed = [f"mcp__halcyon__{name}" for name in tools]
        # No built-in tools at all (no shell, no files), and no MCP servers
        # but ours: Halcyon's actions are the only things it can do.
        argv = ["claude", "-p", "--output-format", "json", "--system-prompt", system,
                "--tools", "", "--strict-mcp-config"]
        if allowed:
            argv += ["--mcp-config", json.dumps(mcp), "--allowedTools", *allowed]
        if self._model_flag:
            argv += ["--model", self._model_flag]
        if self.session:
            argv += ["--resume", self.session]
        return argv + ["--", prompt]

    def chat(self, history, system, tools):
        # A fresh conversation (the first turn, or after memory lapsed)
        # starts a fresh Claude Code session; otherwise continue the last.
        if sum(1 for t in history if t["role"] == "user") <= 1:
            self.session = None
        prompt = next(t["text"] for t in reversed(history) if t["role"] == "user")
        # Claude Code prefers an API key over your subscription login when
        # one is in the environment; this provider exists to use the plan.
        env = {k: v for k, v in os.environ.items() if k not in self.ENV_CREDENTIALS}
        Path(self.workdir).mkdir(parents=True, exist_ok=True)
        try:
            done = self.run(self.command(prompt, system, tools), capture_output=True, text=True,
                            timeout=150, env=env, cwd=str(self.workdir), stdin=subprocess.DEVNULL)
        except FileNotFoundError:
            raise ProviderError("Claude Code isn't installed: run `halcyon assistant login`") from None
        except subprocess.TimeoutExpired:
            raise ProviderError("Claude Code took too long to answer") from None
        try:
            data = json.loads(done.stdout.strip().splitlines()[-1]) if done.stdout.strip() else {}
        except ValueError:
            data = {}
        if not data:
            detail = (done.stderr or done.stdout or "no output").strip().splitlines()[-1:] or ["no output"]
            if "login" in detail[0].lower() or "log in" in detail[0].lower():
                raise ProviderError("Claude Code isn't signed in: run `halcyon assistant login`")
            raise ProviderError(f"Claude Code failed: {detail[0][:200]}")
        self.session = data.get("session_id") or self.session
        text = (data.get("result") or "").strip()
        if data.get("is_error"):
            if "login" in text.lower():
                raise ProviderError("your Claude login has expired: run `halcyon assistant login`")
            raise ProviderError(f"Claude Code: {text[:200] or 'error'}")
        # Tools ran inside Claude Code already; nothing left for our loop.
        return {"text": text, "calls": [], "raw": None}


# ---------------------------------------------------------------------------
# OpenAI-compatible (OpenAI, Mistral, OpenRouter, llama.cpp, LM Studio...)
# ---------------------------------------------------------------------------

def _openai_messages(history, system, arguments_as_string=True):
    out = [{"role": "system", "content": system}]
    for turn in history:
        if turn["role"] == "user":
            out.append({"role": "user", "content": turn["text"]})
        elif turn["role"] == "assistant":
            message = {"role": "assistant", "content": turn.get("text") or ""}
            if turn.get("calls"):
                message["tool_calls"] = [{
                    "id": c["id"], "type": "function",
                    "function": {"name": c["name"],
                                 "arguments": json.dumps(c["args"]) if arguments_as_string else c["args"]},
                } for c in turn["calls"]]
            out.append(message)
        elif turn["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": turn["id"], "name": turn["name"], "content": turn["result"]})
    return out


def _openai_tools(tools):
    return [{"type": "function", "function": {"name": n, "description": t["description"],
                                              "parameters": t["parameters"]}} for n, t in tools.items()]


def _parse_arguments(raw):
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


class OpenAICompatible:
    name = "openai"

    def __init__(self, model, endpoint, key=None, post=_post):
        self.model, self.endpoint, self.key, self.post = model, endpoint.rstrip("/"), key, post

    def chat(self, history, system, tools):
        body = {"model": self.model, "messages": _openai_messages(history, system)}
        if tools:
            body["tools"] = _openai_tools(tools)
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        data = self.post(f"{self.endpoint}/chat/completions", body, headers)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"unexpected reply: {str(data)[:200]}") from None
        calls = [{"id": c.get("id") or _new_id(), "name": c["function"]["name"],
                  "args": _parse_arguments(c["function"].get("arguments"))}
                 for c in message.get("tool_calls") or []]
        return {"text": (message.get("content") or "").strip(), "calls": calls, "raw": None}


class Ollama:
    name = "ollama"

    def __init__(self, model, endpoint, post=_post):
        self.model, self.endpoint, self.post = model, endpoint.rstrip("/"), post

    def chat(self, history, system, tools):
        body = {"model": self.model, "stream": False,
                "messages": _openai_messages(history, system, arguments_as_string=False)}
        if tools:
            body["tools"] = _openai_tools(tools)
        try:
            data = self.post(f"{self.endpoint}/api/chat", body, {}, timeout=180)
        except ProviderError as error:
            if "can't reach" in str(error):
                raise ProviderError("Ollama isn't running (start it with `ollama serve`), "
                                    "or set a Claude or Gemini key") from None
            raise
        message = data.get("message") or {}
        calls = [{"id": _new_id(), "name": c["function"]["name"],
                  "args": _parse_arguments(c["function"].get("arguments"))}
                 for c in message.get("tool_calls") or []]
        return {"text": (message.get("content") or "").strip(), "calls": calls, "raw": None}


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def _gemini_schema(schema):
    """Gemini takes an OpenAPI subset: drop the keywords it rejects."""
    if isinstance(schema, dict):
        return {k: _gemini_schema(v) for k, v in schema.items()
                if k not in ("additionalProperties", "minimum", "maximum")}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema


class Gemini:
    name = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, model, key, post=_post):
        self.model, self.key, self.post = model, key, post

    @staticmethod
    def contents(history):
        out = []
        for turn in history:
            if turn["role"] == "user":
                out.append({"role": "user", "parts": [{"text": turn["text"]}]})
            elif turn["role"] == "assistant":
                # Echo the model's parts unchanged: they can carry thought
                # signatures that must come back with function calls.
                parts = turn.get("raw") or [{"text": turn.get("text") or "…"}]
                out.append({"role": "model", "parts": parts})
            elif turn["role"] == "tool":
                part = {"functionResponse": {"name": turn["name"], "response": {"result": turn["result"]}}}
                if out and out[-1]["role"] == "user" and "functionResponse" in out[-1]["parts"][0]:
                    out[-1]["parts"].append(part)
                else:
                    out.append({"role": "user", "parts": [part]})
        return out

    def chat(self, history, system, tools):
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": self.contents(history)}
        if tools:
            body["tools"] = [{"functionDeclarations": [
                {"name": n, "description": t["description"], "parameters": _gemini_schema(t["parameters"])}
                for n, t in tools.items() if t["parameters"]["properties"]] + [
                {"name": n, "description": t["description"]}
                for n, t in tools.items() if not t["parameters"]["properties"]]}]
        data = self.post(self.URL.format(model=self.model), body, {"x-goog-api-key": self.key})
        try:
            candidate = data["candidates"][0]
            parts = candidate.get("content", {}).get("parts", [])
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"unexpected reply: {str(data)[:200]}") from None
        text = " ".join(p["text"] for p in parts if "text" in p and not p.get("thought")).strip()
        calls = [{"id": _new_id(), "name": p["functionCall"]["name"], "args": p["functionCall"].get("args") or {}}
                 for p in parts if "functionCall" in p]
        return {"text": text, "calls": calls, "raw": parts}


# ---------------------------------------------------------------------------
# Choosing one
# ---------------------------------------------------------------------------

def _anthropic_credentials():
    return bool(config.api_key("anthropic") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config/anthropic").is_dir())


def resolve(settings):
    """The provider the settings ask for; "auto" picks the first one set up."""
    provider = settings["provider"]
    if provider == "auto":
        if _anthropic_credentials():
            provider = "claude"
        elif claude_code_signed_in():
            provider = "claude-code"
        elif config.api_key("gemini"):
            provider = "gemini"
        else:
            provider = "ollama"
    model = settings["model"] or config.DEFAULT_MODELS[provider]
    if provider == "claude-code":
        if not shutil.which("claude"):
            raise ProviderError("Claude Code isn't installed: run `halcyon assistant login`")
        return ClaudeCode(model)
    if provider == "claude":
        try:
            return Claude(model, key=config.api_key("anthropic"))
        except ImportError:
            raise ProviderError("the anthropic package is missing: run `halcyon assistant setup`") from None
    if provider == "gemini":
        key = config.api_key("gemini")
        if not key:
            raise ProviderError("no Gemini key: add one in the AI sidebar or `halcyon assistant key gemini`")
        return Gemini(model, key)
    if provider == "openai":
        key_id = settings["keyId"] or "openai"
        return OpenAICompatible(model, settings["endpoint"] or config.DEFAULT_ENDPOINTS["openai"],
                                config.api_key(key_id))
    return Ollama(model, settings["endpoint"] or config.DEFAULT_ENDPOINTS["ollama"])
