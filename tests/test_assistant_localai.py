"""Tests for the assistant's audio commands and its LM Studio, HyperNix and T1 support, against fake programs and
fake servers. Run: python3 -m unittest discover -s tests"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import unittest.mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon/assistant"))

from halcyon_assistant import actions, cli, config, localai, pcm, providers  # noqa: E402


class FakeServer:
    """A local HTTP server answering from a dict of {(method, path): handler(body, headers) -> (status, json)}."""

    def __init__(self, routes):
        self.routes, self.requests = routes, []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _answer(self, method):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"null") if length else None
                outer.requests.append((method, self.path, body, dict(self.headers)))
                handler = outer.routes.get((method, self.path))
                status, data = handler(body, self.headers) if handler else (404, {"detail": "Not Found"})
                raw = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self._answer("GET")

            def do_POST(self):
                self._answer("POST")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


HISTORY = [{"role": "user", "text": "turn the volume down"}]


class PcmTest(unittest.TestCase):
    """PipeWire 1.2 made `-` a sound file; raw samples need --raw. The commands must ask pw-cat which it is."""

    def _with_pw_cat(self, help_text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bin_dir = Path(tmp.name)
        for tool in ("pw-cat", "pw-play", "pw-record"):
            executable(bin_dir / tool, f"echo '{help_text}'\n")
        pcm.pipewire_has_raw.cache_clear()
        self.addCleanup(pcm.pipewire_has_raw.cache_clear)
        patcher = unittest.mock.patch.dict(os.environ, {"PATH": str(bin_dir)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_new_pipewire_gets_raw(self):
        self._with_pw_cat("  -a, --raw    RAW mode")
        self.assertEqual(pcm.player(22050), ["pw-play", "--raw", "--rate", "22050", "--channels", "1",
                                             "--format", "s16", "-"])
        self.assertEqual(pcm.recorder(16000)[:2], ["pw-record", "--raw"])

    def test_old_pipewire_does_not(self):
        self._with_pw_cat("  --rate  sample rate")
        self.assertNotIn("--raw", pcm.player(22050))
        self.assertNotIn("--raw", pcm.recorder(16000))

    def test_falls_back_to_pulseaudio_then_alsa(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable(Path(tmp, "aplay"), "exit 0\n")
            with unittest.mock.patch.dict(os.environ, {"PATH": tmp}):
                self.assertEqual(pcm.player(16000)[0], "aplay")
                self.assertIsNone(pcm.recorder(16000))
            executable(Path(tmp, "paplay"), "exit 0\n")
            with unittest.mock.patch.dict(os.environ, {"PATH": tmp}):
                self.assertEqual(pcm.player(16000)[:2], ["paplay", "--raw"])


class SpeechFallbackTest(unittest.TestCase):
    def test_piper_rate_comes_from_the_voice(self):
        from halcyon_assistant import speech
        with tempfile.TemporaryDirectory() as tmp:
            voice = Path(tmp, "v.onnx")
            voice.write_text("")
            self.assertEqual(speech.piper_rate(voice), speech.DEFAULT_RATE)
            Path(tmp, "v.onnx.json").write_text(json.dumps({"audio": {"sample_rate": 16000}}))
            self.assertEqual(speech.piper_rate(voice), 16000)

    def test_a_failing_engine_falls_back_to_the_next(self):
        from halcyon_assistant import speech
        tried = []

        def speak_once(name, text, should_stop=None, settings=None):
            tried.append(name)
            return "broken" if name == "piper" else None

        with unittest.mock.patch.object(speech, "engines", return_value=["piper", "espeak-ng"]), \
                unittest.mock.patch.object(speech, "speak_once", side_effect=speak_once), \
                self.assertLogs("halcyon.speech", level="ERROR"):
            self.assertTrue(speech.say("hi"))
        self.assertEqual(tried, ["piper", "espeak-ng"])


def lmstudio_routes(loaded=True, tools_ok=True):
    def models(_body, _headers):
        return 200, {"data": [{"id": "qwen3-4b", "type": "llm", "state": "loaded" if loaded else "not-loaded"},
                              {"id": "nomic-embed", "type": "embeddings", "state": "not-loaded"}]}

    def chat(body, _headers):
        if "tools" in body and not tools_ok:
            return 400, {"error": "This model does not support tools"}
        return 200, {"choices": [{"message": {"content": f"ok from {body['model']}"}}]}

    return {("GET", "/api/v0/models"): models, ("GET", "/v1/models"): lambda b, h: (200, {"data": [{"id": "qwen3-4b"}]}),
            ("POST", "/v1/chat/completions"): chat}


class LMStudioTest(unittest.TestCase):
    def test_lists_chat_models_and_which_are_loaded(self):
        with FakeServer(lmstudio_routes()) as server:
            self.assertEqual(localai.lmstudio_models(server.url), [{"id": "qwen3-4b", "loaded": True, "type": "llm"}])
            self.assertEqual(localai.lmstudio_ensure("", server.url), "qwen3-4b")

    def test_provider_asks_the_loaded_model(self):
        with FakeServer(lmstudio_routes()) as server:
            provider = providers.LMStudio("", server.url + "/v1")
            answer = provider.chat(HISTORY, "sys", actions.ACTIONS)
            self.assertEqual(answer["text"], "ok from qwen3-4b")
            self.assertEqual(provider.model, "qwen3-4b")
            self.assertIn("tools", server.requests[-1][2])

    def test_a_model_without_tools_is_asked_again_without_them(self):
        with FakeServer(lmstudio_routes(tools_ok=False)) as server:
            provider = providers.LMStudio("qwen3-4b", server.url)
            self.assertEqual(provider.chat(HISTORY, "sys", actions.ACTIONS)["text"], "ok from qwen3-4b")
            self.assertFalse(provider.tools_ok)
            provider.chat(HISTORY, "sys", actions.ACTIONS)
            self.assertNotIn("tools", server.requests[-1][2])  # remembered: no failing first try

    def test_not_running_and_no_lms_says_what_to_do(self):
        with unittest.mock.patch.object(localai, "lms_cli", return_value=None):
            provider = providers.LMStudio("", "http://127.0.0.1:9")
            with self.assertRaisesRegex(providers.ProviderError, "LM Studio's server isn't running"):
                provider.chat(HISTORY, "sys", {})

    def test_lms_starts_the_server_and_loads_a_model(self):
        with tempfile.TemporaryDirectory() as tmp, FakeServer(lmstudio_routes(loaded=False)) as server:
            log = Path(tmp, "lms.log")
            executable(Path(tmp, "lms"), f'echo "$@" >> {log}\n')
            with unittest.mock.patch.object(localai, "lms_cli", return_value=str(Path(tmp, "lms"))):
                self.assertEqual(localai.lmstudio_ensure("", server.url), "qwen3-4b")
            self.assertIn("load qwen3-4b --yes", log.read_text())


class HyperNixTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.models = Path(tmp.name, "models")
        self.models.mkdir()
        (self.models / "nano-iq0.gguf").write_text("")
        (self.models / "mmproj-nano.gguf").write_text("")
        patcher = unittest.mock.patch.object(localai, "HYPERNIX_MODELS", self.models)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.state = Path(tmp.name, "state")
        patcher = unittest.mock.patch.object(localai, "STATE", self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_models_skip_projectors(self):
        self.assertEqual([p.name for p in localai.hypernix_models()], ["nano-iq0.gguf"])
        self.assertEqual(localai.hypernix_resolve("nano-iq0").name, "nano-iq0.gguf")
        self.assertIsNone(localai.hypernix_resolve("missing"))

    def test_an_already_running_runtime_is_used(self):
        routes = {("GET", "/v1/models"): lambda b, h: (200, {"data": [{"id": "nano-iq0"}]}),
                  ("POST", "/v1/chat/completions"): lambda b, h: (200, {"choices": [{"message": {"content": "hi"}}]})}
        with FakeServer(routes) as server:
            provider = providers.HyperNix("", server.url)
            self.assertEqual(provider.chat(HISTORY, "sys", {})["text"], "hi")
            self.assertEqual(provider.model, "nano-iq0")

    def test_starts_hnx_runtime_serve_with_the_model(self):
        # A fake `hnx` that records its arguments; the "runtime" comes up as the fake server.
        log = self.state.parent / "hnx.log"
        hnx = self.state.parent / "hnx"
        executable(hnx, f'echo "$@" > {log}\nsleep 5\n')
        up = {"now": False}
        routes = {("GET", "/v1/models"): lambda b, h: (200, {"data": [{"id": "nano-iq0"}]}) if up["now"]
                  else (503, {"error": "loading"})}
        with FakeServer(routes) as server, unittest.mock.patch.object(localai, "hnx_cli", return_value=str(hnx)):
            timer = threading.Timer(0.6, lambda: up.update(now=True))
            timer.start()
            try:
                self.assertEqual(localai.hypernix_ensure("", server.url, start_timeout=10), "nano-iq0")
            finally:
                timer.cancel()
                localai.hypernix_stop()
        args = log.read_text().split()
        self.assertEqual(args[:2], ["runtime", "serve"])
        self.assertTrue(args[2].endswith("nano-iq0.gguf"))
        self.assertIn("--alias", args)

    def test_no_models_says_where_to_put_one(self):
        (self.models / "nano-iq0.gguf").unlink()
        with self.assertRaisesRegex(localai.LocalAIError, "no models in"):
            localai.hypernix_ensure("", "http://127.0.0.1:9")


def t1_routes(content="Hello from T1", model="hnx-nano", keyless=False):
    """A T1 server: a T1 or a T2 key gets in; no key only when it trusts this computer (keyless)."""
    def allowed(headers):
        auth = headers.get("Authorization")
        return auth in ("Bearer T1_good", "Bearer T2_good-3") or (keyless and auth is None)

    unauthorized = (401, {"error": {"code": "unauthorized", "hx_code": "HX401", "message": "invalid API key"},
                          "request_id": "r1"})

    def chat(body, headers):
        if not allowed(headers):
            return unauthorized
        return 200, {"model": body["model"], "requested_model": body["model"], "content": content,
                     "finish_reason": "stop", "input_tokens": 5, "output_tokens": 3, "backend_name": "local"}

    def backends(body, headers):
        if not allowed(headers):
            return unauthorized
        return 200, {"backends": [{"name": "local", "kind": "runner", "reachable": True, "model_id": model}],
                     "default": "local"}

    return {("GET", "/models"): lambda b, h: (200, {"models": [{"model_id": model, "display_name": "HNX Nano",
                                                                 "availability": "available"}], "count": 1}),
            ("GET", "/inference/backends"): backends,
            ("POST", "/inference/chat"): chat}


class T1Test(unittest.TestCase):
    def test_chat_with_the_servers_default_model(self):
        with FakeServer(t1_routes()) as server:
            provider = providers.T1("", server.url, "T1_good")
            answer = provider.chat(HISTORY + [{"role": "assistant", "text": "", "calls": [{"id": "1", "name": "x",
                                                                                          "args": {}}]},
                                              {"role": "tool", "id": "1", "name": "x", "result": "done"}],
                                   "sys", actions.ACTIONS)
            self.assertEqual(answer, {"text": "Hello from T1", "calls": [], "raw": None})
            _method, path, body, _headers = server.requests[-1]
            self.assertEqual(path, "/inference/chat")
            self.assertEqual(body["model"], "hnx-nano")
            self.assertNotIn("tools", body)
            self.assertEqual([m["role"] for m in body["messages"]], ["system", "user", "user"])

    def test_a_bad_key_shows_the_servers_message(self):
        with FakeServer(t1_routes()) as server:
            with self.assertRaisesRegex(providers.ProviderError, "invalid API key"):
                providers.T1("hnx-nano", server.url, "T1_bad").chat(HISTORY, "sys", {})

    def test_resolve_needs_a_server_and_a_key(self):
        settings = config.settings({"halcyon": {"assistant": {"provider": "t1"}}})
        with self.assertRaisesRegex(providers.ProviderError, "no T1 server"):
            providers.resolve(settings)
        settings["t1Server"] = "http://127.0.0.1:9"
        with unittest.mock.patch.object(config, "api_key", return_value=None):
            with self.assertRaisesRegex(providers.ProviderError, "no T1 key: the T1 server wants a key"):
                providers.resolve(settings)

    def test_a_t2_key_works_too(self):
        with FakeServer(t1_routes()) as server:
            answer = providers.T1("", server.url, "T2_good-3").chat(HISTORY, "sys", {})
            self.assertEqual(answer["text"], "Hello from T1")

    def test_no_key_says_what_key_it_wants(self):
        with FakeServer(t1_routes()) as server:
            with self.assertRaisesRegex(providers.ProviderError, "T1_ or T2_ key"):
                providers.T1("hnx-nano", server.url, None).chat(HISTORY, "sys", {})

    def test_a_server_that_trusts_this_computer_needs_no_key(self):
        settings = config.settings({"halcyon": {"assistant": {"provider": "t1"}}})
        with FakeServer(t1_routes(keyless=True)) as server, \
                unittest.mock.patch.object(config, "api_key", return_value=None):
            settings["t1Server"] = server.url
            provider = providers.resolve(settings)
            self.assertEqual(provider.chat(HISTORY, "sys", {})["text"], "Hello from T1")
            _method, _path, _body, headers = server.requests[-1]
            self.assertNotIn("Authorization", headers)
            models = localai.sidebar_models(server.url, False)
            self.assertFalse(next(iter(models.values()))["requires_key"])
        with FakeServer(t1_routes()) as server:
            models = localai.sidebar_models(server.url, False)
            self.assertTrue(next(iter(models.values()))["requires_key"])

    def test_auto_prefers_t1_over_local_models_when_set_up(self):
        settings = config.settings({"halcyon": {"assistant": {"t1Server": "http://t1.example"}}})
        keys = {"t1": "T1_good"}
        with unittest.mock.patch.object(providers, "_anthropic_credentials", return_value=False), \
                unittest.mock.patch.object(providers, "claude_code_signed_in", return_value=False), \
                unittest.mock.patch.object(config, "api_key", side_effect=keys.get):
            self.assertIsInstance(providers.resolve(settings), providers.T1)


class AutoLocalTest(unittest.TestCase):
    def test_auto_finds_a_running_lm_studio(self):
        settings = config.settings({})
        with FakeServer(lmstudio_routes()) as server, \
                unittest.mock.patch.object(localai, "LMSTUDIO_URL", server.url), \
                unittest.mock.patch.dict(config.DEFAULT_ENDPOINTS, {"ollama": "http://127.0.0.1:9"}), \
                unittest.mock.patch.object(providers, "_anthropic_credentials", return_value=False), \
                unittest.mock.patch.object(providers, "claude_code_signed_in", return_value=False), \
                unittest.mock.patch.object(config, "api_key", return_value=None):
            provider = providers.resolve(settings)
            self.assertIsInstance(provider, providers.LMStudio)
            self.assertEqual(provider.base, server.url)


class SidebarTest(unittest.TestCase):
    def test_sidebar_lists_every_kind_with_a_prepare_step(self):
        with tempfile.TemporaryDirectory() as tmp, FakeServer({**lmstudio_routes(), **t1_routes()}) as server:
            Path(tmp, "small.gguf").write_text("")
            with unittest.mock.patch.object(localai, "LMSTUDIO_URL", server.url), \
                    unittest.mock.patch.object(localai, "HYPERNIX_MODELS", Path(tmp)):
                models = localai.sidebar_models(server.url, True)
        self.assertEqual(sorted(models), ["hypernix-small", "lmstudio-qwen3-4b", "t1-hnx-nano"])
        lm = models["lmstudio-qwen3-4b"]
        self.assertEqual(lm["endpoint"], server.url + "/v1/chat/completions")
        self.assertEqual(lm["halcyon_prepare"][1:], ["ensure", "lmstudio", "qwen3-4b"])
        self.assertTrue(Path(lm["halcyon_prepare"][0]).name == "halcyon-assistant")
        self.assertEqual(models["hypernix-small"]["halcyon_prepare"][1:3], ["ensure", "hypernix"])
        t1 = models["t1-hnx-nano"]
        self.assertEqual((t1["endpoint"], t1["key_id"], t1["requires_key"], t1["api_format"]),
                         (server.url + "/inference/chat/stream", "t1", True, "openai"))
        for entry in models.values():
            for icon in (entry["icon"],):
                self.assertTrue((ROOT / f"dots/.config/quickshell/ii/assets/icons/{icon}.svg").is_file(), icon)

    def test_ensure_prints_an_sse_error_the_sidebar_can_show(self):
        out = io.StringIO()
        with unittest.mock.patch.object(localai, "lms_cli", return_value=None), \
                unittest.mock.patch.object(localai, "LMSTUDIO_URL", "http://127.0.0.1:9"), \
                contextlib.redirect_stdout(out):
            self.assertEqual(cli.ensure(["lmstudio", "--sse-error"]), 1)
        line = out.getvalue().strip()
        self.assertTrue(line.startswith("data: "))
        self.assertIn("LM Studio", json.loads(line[6:])["error"]["message"])

    def test_the_sidebar_runs_the_prepare_step_before_curl(self):
        qml = (ROOT / "dots/.config/quickshell/ii/services/Ai.qml").read_text()
        self.assertIn('"models", "--sidebar"', qml)
        self.assertIn("scriptPrepareContent + scriptRequestContent", qml)
        self.assertIn("--sse-error 2>/dev/null || exit 0", qml)
        self.assertIn("property var halcyon_prepare", (ROOT / "dots/.config/quickshell/ii/services/ai/AiModel.qml").read_text())


if __name__ == "__main__":
    unittest.main()


class T1KeyTest(unittest.TestCase):
    WHOLE = "T1_" + "a" * 20 + "xy" + "!$`'~" + "\\" + "7"

    def test_whole_keys_and_the_t2_family(self):
        self.assertEqual(config.t1_key_problem(self.WHOLE), "")
        for key in ("T2_abc_def-3", "T2S_" + "a" * 26, "T2C_sealed", "T2P_billing-2", "T1S.payload.sig"):
            self.assertEqual(config.t1_key_problem(key), "", key)

    def test_a_key_the_shell_cut_short(self):
        # What bash leaves of the key above typed unquoted: the symbols after `$` are gone.
        self.assertIn("isn't whole", config.t1_key_problem("T1_" + "a" * 20 + "xy!"))
        self.assertIn("T1_ or T2_", config.t1_key_problem("sk-ant-123"))

    def test_store_refuses_a_broken_key(self):
        with self.assertRaisesRegex(ValueError, "isn't whole"):
            config.store_api_key("t1", "T1_" + "a" * 20 + "xy")

    def test_found_where_hypernix_keeps_it(self):
        with tempfile.TemporaryDirectory() as folder, \
                unittest.mock.patch.object(config, "_keyring_data", return_value={}), \
                unittest.mock.patch.dict(os.environ, {"T1_CONFIG_DIR": folder}, clear=False):
            for name in config.KEY_ENV["t1"]:
                os.environ.pop(name, None)
            self.assertIsNone(config.api_key("t1"))
            Path(folder, ".env").write_text("T1_HOST=0.0.0.0\nT1_BOOTSTRAP_KEY='%s'\n" % self.WHOLE)
            self.assertEqual(config.api_key("t1"), self.WHOLE)
            with unittest.mock.patch.dict(os.environ, {"T2_API_KEY": "T2_env-4"}):
                self.assertEqual(config.api_key("t1"), "T2_env-4")


class T1KeyCommandTest(unittest.TestCase):
    """`halcyon-assistant key t1` with the key on stdin, as Settings sends it, against a stand-in secret-tool."""

    TOOL = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon/assistant/halcyon-assistant"

    def run_key(self, key, folder):
        bin_dir = Path(folder, "bin")
        bin_dir.mkdir(exist_ok=True)
        store = Path(folder, "keyring.json")
        if not store.exists():
            store.write_text(json.dumps({"apiKeys": {"gemini": "AIza-kept"}}))
        executable(bin_dir / "secret-tool", f"""if [ "$1" = lookup ]; then cat '{store}'; else cat > '{store}'; fi
""")
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "XDG_STATE_HOME": str(Path(folder, "state"))}
        done = subprocess.run([sys.executable, str(self.TOOL), "key", "t1"], input=key + "\n", capture_output=True,
                              text=True, env=env, timeout=60)
        return done, json.loads(store.read_text())

    def test_a_whole_key_is_added_beside_the_others(self):
        with tempfile.TemporaryDirectory() as folder:
            done, data = self.run_key(T1KeyTest.WHOLE, folder)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(data["apiKeys"], {"gemini": "AIza-kept", "t1": T1KeyTest.WHOLE})

    def test_a_broken_key_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            done, data = self.run_key("T1_shortxy", folder)
            self.assertEqual(done.returncode, 2)
            self.assertIn("isn't whole", done.stderr)
            self.assertNotIn("t1", data["apiKeys"])
