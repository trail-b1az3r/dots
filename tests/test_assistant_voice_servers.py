"""Voices on servers of their own (voice_servers.py): Fish Audio S2 Pro on Fish Speech, drama3-small on audio.cpp,
against a fake server; and Piper voices from any Hugging Face repo (GLaDOS), against a fake hub.
Run: python3 -m unittest discover -s tests"""

import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
import unittest.mock
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon/assistant"))

from halcyon_assistant import cli, config, piper_voices, speech, voice_servers  # noqa: E402

WAV = b"RIFF" + b"\0" * 40
ONNX = b"glados onnx " * 50
GLADOS_CONFIG = json.dumps({"audio": {"sample_rate": 22050}, "espeak": {"voice": "en-us"}, "phoneme_id_map": {}})


class Fake(ThreadingHTTPServer):
    """Fish Speech (/v1/health, /v1/tts), audio.cpp (/health, /v1/audio/speech) and the Hugging Face API, at once."""

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.requests = []
        self.url = f"http://127.0.0.1:{self.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.shutdown()
        self.server_close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, body, kind="application/json", code=200):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/v1/health", "/health"):
            return self.send(b'{"status":"ok"}')
        if self.path.startswith("/api/models/systemofapwne/piper-en_US-glados-high/tree/main"):
            return self.send(json.dumps([
                {"type": "file", "path": "README.md", "size": 10},
                {"type": "file", "path": "config.json", "size": len(GLADOS_CONFIG)},
                {"type": "file", "path": "model.onnx", "size": len(ONNX),
                 "lfs": {"oid": hashlib.sha256(ONNX).hexdigest(), "size": len(ONNX)}},
            ]).encode())
        if self.path.endswith("/resolve/main/model.onnx"):
            return self.send(ONNX, "application/octet-stream")
        if self.path.endswith("/resolve/main/config.json"):
            return self.send(GLADOS_CONFIG.encode())
        self.send(b"not found", code=404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append((self.path, body))
        if self.path in ("/v1/tts", "/v1/audio/speech"):
            return self.send(WAV, "audio/wav")
        self.send(b"no", code=404)


class ServerVoiceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        for patch in (unittest.mock.patch.object(config, "MODELS", self.home / "models"),
                      unittest.mock.patch.dict("os.environ", {"XDG_CONFIG_HOME": str(self.home / "config")})):
            patch.start()
            self.addCleanup(patch.stop)

    def settings(self, **extra):
        return dict(config.DEFAULTS, **extra)

    def test_fish_sends_the_text_and_gets_a_wav(self):
        with Fake() as server:
            settings = self.settings(voice="fish", fishEndpoint=server.url, fishReference="my-voice")
            self.assertEqual(voice_servers.synthesize("fish", "[whisper] hello", settings), WAV)
        path, body = server.requests[0]
        self.assertEqual(path, "/v1/tts")
        self.assertEqual((body["text"], body["format"], body["reference_id"]), ("[whisper] hello", "wav", "my-voice"))

    def test_drama3_clones_from_the_recording(self):
        recording = self.home / "voice.wav"
        recording.write_bytes(WAV)
        with Fake() as server:
            settings = self.settings(voice="drama3", drama3Endpoint=server.url, drama3Reference=str(recording),
                                     drama3ReferenceText="This is me.")
            self.assertEqual(voice_servers.synthesize("drama3", "hello", settings), WAV)
        path, body = server.requests[0]
        self.assertEqual(path, "/v1/audio/speech")
        self.assertEqual(body["voice_ref"], {"type": "path", "path": str(recording)})
        self.assertEqual((body["model"], body["input"], body["reference_text"]), ("drama3-small", "hello", "This is me."))
        self.assertEqual(body["options"]["max_pause_frames"], "10")

    def test_drama3_without_a_recording_says_what_to_do(self):
        with Fake() as server, self.assertRaisesRegex(voice_servers.ServerError, "recording"):
            voice_servers.synthesize("drama3", "hi", self.settings(drama3Endpoint=server.url))

    def test_a_server_that_is_not_set_up_says_how(self):
        with self.assertRaisesRegex(voice_servers.ServerError, "setup --fish-s2"):
            voice_servers.synthesize("fish", "hi", self.settings(fishEndpoint="http://127.0.0.1:9"))

    def test_a_set_up_server_is_started_when_needed(self):
        voice_servers.write_unit("fish", "/bin/true", self.home)  # systemctl daemon-reload may fail here: fine
        started = []
        with Fake() as server:
            settings = self.settings(fishEndpoint=server.url)
            healthy = iter([False, True])
            with unittest.mock.patch.object(voice_servers, "healthy", lambda name, s: next(healthy)), \
                 unittest.mock.patch.object(voice_servers, "systemctl", lambda *a: started.append(a) or
                                            unittest.mock.Mock(returncode=1)):
                voice_servers.ensure_running("fish", settings)
        self.assertIn(("start", "halcyon-fish-speech.service"), started)

    def test_engines_include_a_chosen_or_set_up_server(self):
        self.assertIn("fish", speech.engines(self.settings(voice="fish")))
        self.assertEqual(speech.engines(self.settings(voice="fish"))[0], "fish")
        self.assertNotIn("drama3", speech.engines(self.settings(voice="auto")))
        voice_servers.write_unit("drama3", "/bin/true", self.home)
        self.assertIn("drama3", speech.engines(self.settings(voice="auto")))

    def test_voices_listed(self):
        self.assertIn("fish", config.VOICES)
        self.assertIn("drama3", config.VOICES)


class HuggingFaceRepoTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patch = unittest.mock.patch.object(config, "MODELS", Path(tmp.name) / "models")
        patch.start()
        self.addCleanup(patch.stop)

    def test_glados_from_its_repo(self):
        self.assertEqual(piper_voices.repo_of("hf:systemofapwne/piper-en_US-glados-high"),
                         "systemofapwne/piper-en_US-glados-high")
        self.assertEqual(piper_voices.repo_of("https://huggingface.co/systemofapwne/piper-en_US-glados-high"),
                         "systemofapwne/piper-en_US-glados-high")
        with Fake() as hub, unittest.mock.patch.object(piper_voices, "HF_API", hub.url + "/api/models/"), \
             unittest.mock.patch("urllib.request.urlopen", self.rewrite(hub.url)):
            path = piper_voices.download("hf:systemofapwne/piper-en_US-glados-high")
        self.assertEqual(path.name, "en_US-glados-high.onnx")
        self.assertEqual(path.read_bytes(), ONNX)
        meta = path.with_name(path.name + ".json")
        self.assertEqual(json.loads(meta.read_text())["audio"]["sample_rate"], 22050, "config.json saved as .onnx.json")
        self.assertEqual(piper_voices.describe(path)["key"], "en_US-glados-high")

    def test_glados_is_listed_with_the_rest(self):
        with unittest.mock.patch.object(piper_voices, "_cached", lambda *a, **k: b"{}"):
            listed = piper_voices.catalog()
        glados = next(v for v in listed if v["key"] == "en_US-glados-high")
        self.assertEqual(glados["repo"], "systemofapwne/piper-en_US-glados-high")

    @staticmethod
    def rewrite(base):
        """urlopen with huggingface.co sent to the fake hub."""
        import urllib.request as ur
        real = ur.urlopen

        def opener(request, *args, **kwargs):
            url = request.full_url if isinstance(request, ur.Request) else request
            url = url.replace("https://huggingface.co", base)
            return real(ur.Request(url, headers={"User-Agent": "t"}), *args, **kwargs)
        return opener


if __name__ == "__main__":
    unittest.main()
