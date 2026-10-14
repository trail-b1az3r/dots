"""LM Studio, HyperNix's own runtime, and HyperNix's T1 gateway: finding their models and getting them ready.

Shared by the voice assistant (providers.py) and the AI sidebar (`halcyon-assistant models --sidebar`, which the
sidebar runs to list models, and `halcyon-assistant ensure ...`, which it runs before a request).

  LM Studio   OpenAI-compatible, on localhost:1234. `lms` (LM Studio's command line) starts its server and loads a
              model when none is loaded, so asking for one is enough.
  HyperNix    `hnx runtime serve MODEL.gguf`: HyperNix's patched llama.cpp, which also runs its sub-bit (IQ0.x)
              models, as an OpenAI-compatible server on localhost:8080. Started on demand with a model from
              ~/.hypernix/models, and left running for the next question.
  T1          a HyperNix T1 server (`hypernix-t1 start`): POST /inference/chat with a T1_ or T2_ key, under the
              server's registry, quotas and audit log. Its models are its registry's (GET /models).

Plain HTTP with the standard library only, so the sidebar can run it without the assistant's virtual environment.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state") / "halcyon/assistant"
LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://127.0.0.1:1234")
HYPERNIX_PORT = int(os.environ.get("HALCYON_HYPERNIX_PORT", "8080"))
HYPERNIX_URL = f"http://127.0.0.1:{HYPERNIX_PORT}"
HYPERNIX_MODELS = Path(os.environ.get("HYPERNIX_MODELS") or HOME / ".hypernix/models")


class LocalAIError(Exception):
    pass


# --- HTTP ---------------------------------------------------------------------------------------------------

def http_json(url: str, body: dict | None = None, headers: dict | None = None, timeout: float = 4.0):
    """GET (or POST with a body) and parse JSON. Raises LocalAIError with the server's own message."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
    except urllib.error.HTTPError as error:
        raise LocalAIError(f"HTTP {error.code}: {error_message(error.read().decode(errors='replace'))}") from None
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise LocalAIError(f"can't reach {url.split('/')[2]}: {reason}") from None
    try:
        return json.loads(raw) if raw.strip() else {}
    except ValueError:
        raise LocalAIError(f"{url.split('/')[2]} did not answer with JSON") from None


def error_message(text: str) -> str:
    """The readable part of an error body: T1's {"error": {"message"}}, OpenAI's, FastAPI's {"detail"}."""
    try:
        data = json.loads(text)
    except ValueError:
        return text.strip()[:300]
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            return f"{err.get('message') or err}" + (f" ({code})" if code else "")
        if isinstance(err, str):
            return err
        if "detail" in data:
            return str(data["detail"])[:300]
    return text.strip()[:300]


def reachable(url: str, path: str = "/v1/models", timeout: float = 0.6) -> bool:
    try:
        http_json(url.rstrip("/") + path, timeout=timeout)
        return True
    except LocalAIError:
        return False


def _wait_until(check, seconds: float, step: float = 0.5) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(step)
    return check()


# --- LM Studio ----------------------------------------------------------------------------------------------

def lms_cli() -> str | None:
    """LM Studio's command line. The installer puts it in ~/.lmstudio/bin, which is often not on Hyprland's PATH."""
    found = shutil.which("lms")
    if found:
        return found
    for candidate in (HOME / ".lmstudio/bin/lms", HOME / ".cache/lm-studio/bin/lms"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def lmstudio_models(base: str | None = None) -> list[dict]:
    """[{id, loaded, type}] for the chat models LM Studio has. The native API says which are loaded; the OpenAI
    one only lists them."""
    base = base or LMSTUDIO_URL
    try:
        data = http_json(base.rstrip("/") + "/api/v0/models", timeout=2)
        out = []
        for item in data.get("data", []) if isinstance(data, dict) else []:
            kind = item.get("type", "llm")
            if kind in ("llm", "vlm"):
                out.append({"id": item.get("id", ""), "loaded": item.get("state") == "loaded", "type": kind})
        return [m for m in out if m["id"]]
    except LocalAIError:
        pass
    data = http_json(base.rstrip("/") + "/v1/models", timeout=2)
    return [{"id": item.get("id", ""), "loaded": None, "type": "llm"}
            for item in (data.get("data", []) if isinstance(data, dict) else [])
            if item.get("id") and "embed" not in item.get("id", "")]


def lms_downloaded() -> list[str]:
    """What `lms ls` lists, for when the server is not running yet."""
    lms = lms_cli()
    if not lms:
        return []
    try:
        out = subprocess.run([lms, "ls", "--json"], capture_output=True, text=True, timeout=20, check=False)
        items = json.loads(out.stdout or "[]")
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    names = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and item.get("type", "llm") in ("llm", "vlm"):
            name = item.get("modelKey") or item.get("path") or item.get("id")
            if name:
                names.append(name)
    return names


def lmstudio_ensure(model: str = "", base: str | None = None, load_timeout: float = 300) -> str:
    """Make LM Studio ready to answer with `model` (or whatever is loaded, or the first downloaded). Returns the
    model id to ask for."""
    base = base or LMSTUDIO_URL
    lms = lms_cli()
    if not reachable(base):
        if not lms:
            raise LocalAIError("LM Studio's server isn't running: start it in LM Studio (Developer tab), "
                               "or install its `lms` command so Halcyon can start it")
        subprocess.run([lms, "server", "start"], capture_output=True, timeout=60, check=False)
        if not _wait_until(lambda: reachable(base), 30):
            raise LocalAIError("`lms server start` ran, but LM Studio's server did not come up on " + base)
    models = lmstudio_models(base)
    loaded = [m["id"] for m in models if m["loaded"]]
    if model:
        if model in loaded or not lms or any(m["loaded"] is None for m in models):
            return model  # LM Studio loads a known model just in time when it is asked for it
        subprocess.run([lms, "load", model, "--yes"], capture_output=True, timeout=load_timeout, check=False)
        return model
    if loaded:
        return loaded[0]
    if models and models[0]["loaded"] is None:
        return models[0]["id"]
    candidates = [m["id"] for m in models] or lms_downloaded()
    if not candidates:
        raise LocalAIError("LM Studio has no chat model: download one in LM Studio, or `lms get <model>`")
    if not lms:
        raise LocalAIError("no model is loaded in LM Studio: load one there")
    done = subprocess.run([lms, "load", candidates[0], "--yes"], capture_output=True, text=True,
                          timeout=load_timeout, check=False)
    if done.returncode != 0:
        raise LocalAIError(f"`lms load {candidates[0]}` failed: {(done.stderr or done.stdout).strip()[-200:]}")
    return candidates[0]


# --- HyperNix runtime ---------------------------------------------------------------------------------------

def hnx_cli() -> str | None:
    for name in ("hnx", "hypernix"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (HOME / ".local/bin/hnx", HOME / ".hypernix/venv/bin/hnx", HOME / ".hypernix/t1api/venv/bin/hnx"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def hypernix_models(folder: Path | None = None) -> list[Path]:
    """The GGUF models in ~/.hypernix/models (and one folder down), newest first. Projector files are not models."""
    folder = folder or HYPERNIX_MODELS
    if not folder.is_dir():
        return []
    found = []
    for path in list(folder.glob("*.gguf")) + list(folder.glob("*/*.gguf")):
        if path.name.startswith("mmproj") or not path.exists():
            continue
        found.append(path)
    return sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)


def hypernix_resolve(model: str, folder: Path | None = None) -> Path | None:
    """A model given as a path, a file name, or a name without .gguf, found in ~/.hypernix/models."""
    if not model:
        models = hypernix_models(folder)
        return models[0] if models else None
    direct = Path(model).expanduser()
    if direct.is_file():
        return direct
    for path in hypernix_models(folder):
        if model in (path.name, path.stem, str(path)):
            return path
    return None


def hypernix_served(base: str | None = None) -> list[str]:
    try:
        data = http_json((base or HYPERNIX_URL) + "/v1/models", timeout=0.8)
    except LocalAIError:
        return []
    return [item.get("id", "") for item in data.get("data", []) if isinstance(item, dict)]


def _runtime_pid_file() -> Path:
    return STATE / "hypernix-runtime.json"


def hypernix_stop() -> bool:
    """Stop the runtime this module started (never one started by hand)."""
    try:
        info = json.loads(_runtime_pid_file().read_text(encoding="utf-8"))
        os.kill(int(info["pid"]), 15)
    except (OSError, ValueError, KeyError):
        return False
    _runtime_pid_file().unlink(missing_ok=True)
    return True


def hypernix_ensure(model: str = "", base: str | None = None, start_timeout: float = 240) -> str:
    """Make HyperNix's runtime serve `model` (default: the newest in ~/.hypernix/models). Returns the name it
    answers to."""
    base = base or HYPERNIX_URL
    served = hypernix_served(base)
    path = hypernix_resolve(model)
    if served and (not model or path is None or path.stem in served or any(path.stem in s for s in served)):
        return served[0]
    if path is None:
        if model:
            raise LocalAIError(f"no HyperNix model called {model!r} in {HYPERNIX_MODELS}")
        raise LocalAIError(f"no models in {HYPERNIX_MODELS}: download one with HyperLink or `hypernix download`, "
                           "or drop a .gguf there")
    hnx = hnx_cli()
    if not hnx:
        raise LocalAIError("HyperNix isn't installed: pip install hypernix (it provides `hnx runtime serve`)")
    if served:
        hypernix_stop()  # serving another model, and we started it: switch
        _wait_until(lambda: not hypernix_served(base), 10)
        if hypernix_served(base):
            raise LocalAIError(f"another model is running on port {HYPERNIX_PORT}; stop it, or ask for that one")
    STATE.mkdir(parents=True, exist_ok=True)
    port = base.rstrip("/").rsplit(":", 1)[-1] if base.rstrip("/").rsplit(":", 1)[-1].isdigit() else str(HYPERNIX_PORT)
    with open(STATE / "hypernix-runtime.log", "ab") as log:  # the runtime keeps its own copy of the handle
        process = subprocess.Popen([hnx, "runtime", "serve", str(path), "--port", port, "--alias", path.stem],
                                   stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    _runtime_pid_file().write_text(json.dumps({"pid": process.pid, "model": str(path)}), encoding="utf-8")
    if not _wait_until(lambda: bool(hypernix_served(base)) or process.poll() is not None, start_timeout, 1.0):
        raise LocalAIError(f"HyperNix's runtime did not start in {int(start_timeout)} s; see {STATE / 'hypernix-runtime.log'}")
    if process.poll() is not None and not hypernix_served(base):
        raise LocalAIError(f"`hnx runtime serve` exited {process.returncode}; see {STATE / 'hypernix-runtime.log'} "
                           "(it needs the patched llama.cpp: `hnx runtime status`)")
    return path.stem


# --- T1 -----------------------------------------------------------------------------------------------------

def t1_models(server: str, key: str | None = None) -> list[dict]:
    """[{id, name, available}] from a T1 server's registry. GET /models needs no key."""
    data = http_json(server.rstrip("/") + "/models", timeout=4)
    out = []
    for item in data.get("models", []) if isinstance(data, dict) else []:
        out.append({"id": item.get("model_id", ""), "name": item.get("display_name") or item.get("model_id", ""),
                    "available": item.get("availability") not in ("unavailable", "disabled")})
    return [m for m in out if m["id"]]


def t1_default_model(server: str, key: str) -> str:
    """What the server would answer with: the runner's loaded model, else the first available registry entry."""
    try:
        data = http_json(server.rstrip("/") + "/inference/backends", headers={"Authorization": f"Bearer {key}"})
        for backend in data.get("backends", []):
            if backend.get("reachable") and backend.get("model_id"):
                return backend["model_id"]
    except LocalAIError:
        pass
    models = [m for m in t1_models(server) if m["available"]]
    if not models:
        raise LocalAIError(f"the T1 server at {server} lists no available models")
    return models[0]["id"]


def t1_chat(server: str, key: str, model: str, messages: list[dict], timeout: float = 180) -> dict:
    """One chat completion through T1's governed inference. Returns the server's InferenceResponse."""
    if not key:
        raise LocalAIError("no T1 key: `halcyon assistant key t1 T1_...` (or set it in the AI sidebar with /key)")
    return http_json(server.rstrip("/") + "/inference/chat",
                     {"model": model, "messages": messages, "max_tokens": 1024},
                     {"Authorization": f"Bearer {key}"}, timeout=timeout)


# --- for the AI sidebar -------------------------------------------------------------------------------------

def sidebar_models(t1_server: str = "", t1_key_present: bool = False) -> dict[str, dict]:
    """Model entries in the shape services/Ai.qml's addModel takes, keyed by a safe id."""
    tool = str(Path(__file__).resolve().parent.parent / "halcyon-assistant")
    models: dict[str, dict] = {}
    # LM Studio: what it has, or what `lms` says is downloaded when the server is off.
    lm_ids: list[str] = []
    try:
        lm_ids = [m["id"] for m in lmstudio_models()]
    except LocalAIError:
        lm_ids = lms_downloaded()
    for model_id in lm_ids:
        models[f"lmstudio-{_safe(model_id)}"] = {
            "name": f"{_pretty(model_id)} (LM Studio)",
            "icon": "lmstudio-symbolic",
            "description": f"Local | LM Studio | {model_id}\nHalcyon starts LM Studio's server and loads the model when needed.",
            "homepage": "https://lmstudio.ai",
            "endpoint": f"{LMSTUDIO_URL}/v1/chat/completions",
            "model": model_id,
            "requires_key": False,
            "api_format": "openai",
            "halcyon_prepare": [tool, "ensure", "lmstudio", model_id],
        }
    # HyperNix: every GGUF in ~/.hypernix/models, served by its own runtime.
    for path in hypernix_models():
        models[f"hypernix-{_safe(path.stem)}"] = {
            "name": f"{_pretty(path.stem)} (HyperNix)",
            "icon": "hypernix-symbolic",
            "description": f"Local | HyperNix runtime | {path.name}\nRuns sub-bit models too. Starts `hnx runtime serve` when needed.",
            "homepage": "https://github.com/trail-b1az3r/HyperNix-pip",
            "endpoint": f"{HYPERNIX_URL}/v1/chat/completions",
            "model": path.stem,
            "requires_key": False,
            "api_format": "openai",
            "halcyon_prepare": [tool, "ensure", "hypernix", str(path)],
        }
    # T1: the registry of the configured server.
    if t1_server:
        try:
            registry = t1_models(t1_server)
        except LocalAIError:
            registry = []
        for item in registry:
            models[f"t1-{_safe(item['id'])}"] = {
                "name": f"{item['name']} (T1)",
                "icon": "hypernix-symbolic",
                "description": f"HyperNix T1 server | {t1_server}\nGoverned inference: your key's plan, quota and audit log apply.",
                "homepage": t1_server.rstrip("/") + "/docs",
                "endpoint": t1_server.rstrip("/") + "/inference/chat/stream",
                "model": item["id"],
                "requires_key": True,
                "key_id": "t1",
                "key_get_description": "A T1_ or T2_ key from your T1 server's admin: `gkey create`, or `waiter serv`.",
                "api_format": "openai",
            }
    return models


def _safe(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:60]


def _pretty(model_id: str) -> str:
    base = model_id.rsplit("/", 1)[-1]
    for suffix in (".gguf",):
        base = base[: -len(suffix)] if base.endswith(suffix) else base
    return base.replace("-", " ").replace("_", " ")
