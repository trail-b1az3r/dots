"""The assistant's voices: the AI voice (Gemini and OpenAI-compatible, against a fake server), the order engines are
tried in, what of a reply is read aloud, and `say` (the AI sidebar's replies). A stand-in audio player records what
would have been played. Run: python3 -m unittest discover -s tests"""

import base64
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
import unittest.mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon/assistant"))

from halcyon_assistant import cli, config, daemon, pcm, speech, tts_ai  # noqa: E402

PCM = bytes(range(256)) * 8


class VoiceServer:
    """Answers Gemini's generateContent with inline audio, and /v1/audio/speech with raw PCM."""

    def __init__(self, status=200):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append((self.path, body, {k.lower(): v for k, v in self.headers.items()}))
                if status != 200:
                    raw, kind = json.dumps({"error": {"message": "quota"}}).encode(), "application/json"
                elif ":generateContent" in self.path:
                    raw = json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {
                        "mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(PCM).decode()}}]}}]}).encode()
                    kind = "application/json"
                else:
                    raw, kind = PCM, "audio/pcm"
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def settings(**overrides):
    return {**config.DEFAULTS, **overrides}


def keys(**stored):
    """Patch the key lookup: only these keys exist."""
    return unittest.mock.patch.object(config, "api_key", side_effect=lambda key_id: stored.get(key_id))


class AIVoiceTest(unittest.TestCase):
    def test_gemini_is_asked_for_audio_in_the_chosen_voice(self):
        with VoiceServer() as server, keys(gemini="g-key"), \
                unittest.mock.patch.object(tts_ai, "GEMINI_URL", server.url + "/v1beta/models/{model}:generateContent"):
            data, rate = tts_ai.synthesize("Hello there.", settings(aiVoice="Puck"))
        self.assertEqual((data, rate), (PCM, 24000))
        path, body, headers = server.requests[0]
        self.assertEqual(path, "/v1beta/models/gemini-2.5-flash-preview-tts:generateContent")
        self.assertEqual(body["generationConfig"]["responseModalities"], ["AUDIO"])
        self.assertEqual(body["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"], "Puck")
        self.assertEqual(body["contents"][0]["parts"][0]["text"], "Hello there.")
        self.assertEqual(headers["x-goog-api-key"], "g-key")
        self.assertNotIn("g-key", path, "the key goes in a header, not the URL")

    def test_an_openai_compatible_server_is_asked_for_raw_pcm(self):
        with VoiceServer() as server, keys(openai="o-key"):
            data, rate = tts_ai.synthesize("Hi.", settings(aiVoiceProvider="openai", aiVoiceEndpoint=server.url + "/v1"))
        self.assertEqual((data, rate), (PCM, 24000))
        path, body, headers = server.requests[0]
        self.assertEqual(path, "/v1/audio/speech")
        self.assertEqual((body["model"], body["voice"], body["response_format"]), ("gpt-4o-mini-tts", "alloy", "pcm"))
        self.assertEqual(headers["authorization"], "Bearer o-key")

    def test_a_local_voice_server_needs_no_key(self):
        with VoiceServer() as server, keys():
            local = settings(aiVoiceProvider="openai", aiVoiceEndpoint=server.url + "/v1")
            self.assertEqual(tts_ai.provider(local), "openai")
            tts_ai.synthesize("Hi.", local)
        self.assertNotIn("authorization", server.requests[0][2])

    def test_which_provider_speaks(self):
        with keys(gemini="g", openai="o"):
            self.assertEqual(tts_ai.provider(settings()), "gemini")
            self.assertEqual(tts_ai.provider(settings(aiVoiceProvider="openai")), "openai")
        with keys(openai="o"):
            self.assertEqual(tts_ai.provider(settings()), "openai")
            self.assertIsNone(tts_ai.provider(settings(aiVoiceProvider="gemini")))
        with keys():
            self.assertIsNone(tts_ai.provider(settings()))

    def test_a_refusal_is_reported_not_swallowed(self):
        with VoiceServer(status=429) as server, keys(gemini="g"), \
                unittest.mock.patch.object(tts_ai, "GEMINI_URL", server.url + "/v1beta/models/{model}:generateContent"):
            with self.assertRaises(tts_ai.VoiceError) as caught:
                tts_ai.synthesize("Hi.", settings())
        self.assertIn("429", str(caught.exception))

    def test_long_replies_are_cut_before_they_are_sent(self):
        with VoiceServer() as server, keys(gemini="g"), \
                unittest.mock.patch.object(tts_ai, "GEMINI_URL", server.url + "/v1beta/models/{model}:generateContent"):
            tts_ai.synthesize("x" * 10000, settings())
        self.assertEqual(len(server.requests[0][1]["contents"][0]["parts"][0]["text"]), tts_ai.MAX_CHARS)


class EngineOrderTest(unittest.TestCase):
    def available(self, *, piper=True, key=True, espeak=True, spd=True):
        which = {"espeak-ng": espeak, "spd-say": spd}
        return [unittest.mock.patch.object(speech, "piper_binary", return_value="/x/piper" if piper else None),
                unittest.mock.patch.object(speech, "piper_voice", return_value=Path("/x/v.onnx") if piper else None),
                keys(gemini="g") if key else keys(),
                unittest.mock.patch.object(speech.shutil, "which", side_effect=lambda n: f"/usr/bin/{n}" if which.get(n) else None)]

    def engines(self, voice="auto", **available):
        patches = self.available(**available)
        for p in patches:
            p.start()
        try:
            return speech.engines(settings(voice=voice))
        finally:
            for p in patches:
                p.stop()

    def test_auto_prefers_piper_then_the_ai_voice_then_espeak(self):
        self.assertEqual(self.engines(), ["piper", "ai", "espeak-ng", "spd-say"])
        self.assertEqual(self.engines(piper=False), ["ai", "espeak-ng", "spd-say"])
        self.assertEqual(self.engines(piper=False, key=False), ["espeak-ng", "spd-say"])

    def test_a_chosen_voice_goes_first_and_the_others_stay_as_fallbacks(self):
        self.assertEqual(self.engines("ai"), ["ai", "piper", "espeak-ng", "spd-say"])
        self.assertEqual(self.engines("espeak"), ["espeak-ng", "piper", "ai", "spd-say"])
        self.assertEqual(self.engines("system"), ["spd-say", "piper", "ai", "espeak-ng"])

    def test_choosing_a_voice_that_is_missing_falls_back(self):
        self.assertEqual(self.engines("piper", piper=False), ["ai", "espeak-ng", "spd-say"])


class PlayingTest(unittest.TestCase):
    """The AI voice's audio reaches the player, through a stand-in that keeps what it was given."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name, "played")
        self.player = Path(self.tmp.name, "player")
        self.player.write_text(f"#!/bin/sh\ncat > {self.out}\n")
        self.player.chmod(self.player.stat().st_mode | stat.S_IEXEC)

    def test_ai_voice_audio_is_played_at_its_rate(self):
        rates = []

        def player(rate, channels=1):
            rates.append(rate)
            return [str(self.player)]

        with VoiceServer() as server, keys(gemini="g"), \
                unittest.mock.patch.object(tts_ai, "GEMINI_URL", server.url + "/v1beta/models/{model}:generateContent"), \
                unittest.mock.patch.object(pcm, "player", side_effect=player):
            self.assertIsNone(speech.speak_once("ai", "Hello.", settings=settings()))
        self.assertEqual(self.out.read_bytes(), PCM)
        self.assertEqual(rates, [24000])

    def test_a_failing_ai_voice_falls_back_to_the_next_engine(self):
        tried = []

        def fake_espeak(command, should_stop):
            tried.append(command[0])
            return None

        with VoiceServer(status=500) as server, keys(gemini="g"), \
                unittest.mock.patch.object(tts_ai, "GEMINI_URL", server.url + "/v1beta/models/{model}:generateContent"), \
                unittest.mock.patch.object(speech, "engines", return_value=["ai", "espeak-ng"]), \
                unittest.mock.patch.object(speech, "_speak_with", side_effect=fake_espeak), \
                self.assertLogs("halcyon.speech", level="ERROR") as logs:
            self.assertTrue(speech.say("Hello.", settings=settings()))
        self.assertEqual(tried, ["espeak-ng"])
        self.assertIn("500", "\n".join(logs.output))


class PlainTextTest(unittest.TestCase):
    def test_markdown_is_read_as_words(self):
        reply = ("## Steps\n**Open** the [settings](https://example.com) and run `halcyon doctor`.\n\n"
                 "```bash\nrm -rf build\n```\n- first\n- second\n<think>private</think>Done!")
        self.assertEqual(speech.plain(reply),
                         "Steps. Open the settings and run halcyon doctor. (code on screen) first. second. Done!")

    def test_long_replies_stop_at_a_sentence(self):
        spoken = speech.plain("This is a sentence. " * 200, limit=300)
        self.assertTrue(spoken.endswith("sentence. The rest is on screen."), spoken[-60:])
        self.assertLessEqual(len(spoken), 300 + len(" The rest is on screen."))

    def test_nothing_to_say(self):
        self.assertEqual(speech.plain("```\ncode only\n```").strip(" ."), "(code on screen)")
        self.assertEqual(speech.plain(""), "")


class SayTest(unittest.TestCase):
    def test_the_daemon_speaks_a_say_line_and_reports_busy(self):
        assistant = daemon.Assistant.__new__(daemon.Assistant)
        assistant.__init__()
        assistant.settings = settings()
        spoken = []
        with unittest.mock.patch.object(speech, "say", side_effect=lambda text, **kw: spoken.append(text) or True):
            self.assertEqual(assistant.handle("say **Hello** there"), "speaking")
            for _ in range(100):
                if spoken and not assistant.busy.is_set():
                    break
                threading.Event().wait(0.02)
        self.assertEqual(spoken, ["Hello there."])
        assistant.busy.set()
        self.assertEqual(assistant.handle("say again"), "busy")

    def test_cli_say_speaks_here_when_no_daemon_runs(self):
        spoken = []
        with unittest.mock.patch.object(daemon, "send", return_value=None), \
                unittest.mock.patch.object(config, "settings", return_value=settings()), \
                unittest.mock.patch.object(speech, "say", side_effect=lambda text, **kw: spoken.append(text) or True):
            self.assertEqual(cli.say(["--", "# Title", "and *words*"]), 0)
        self.assertEqual(spoken, ["Title and words."])

    def test_cli_say_hands_over_to_a_running_daemon(self):
        sent = []
        with unittest.mock.patch.object(daemon, "send", side_effect=lambda line: sent.append(line) or "speaking"), \
                unittest.mock.patch.object(config, "settings", return_value=settings()), \
                unittest.mock.patch.object(speech, "say") as local:
            self.assertEqual(cli.say(["Hello\nthere"]), 0)
        self.assertEqual(sent, ["say Hello. there."])
        local.assert_not_called()

    def test_cli_say_is_silent_when_speaking_is_off(self):
        with unittest.mock.patch.object(daemon, "send") as send, \
                unittest.mock.patch.object(config, "settings", return_value=settings(speak=False)):
            self.assertEqual(cli.say(["Hello"]), 0)
        send.assert_not_called()


class SettingsTest(unittest.TestCase):
    def test_voice_settings_are_checked(self):
        s = config.settings({"halcyon": {"assistant": {"voice": "robot", "aiVoiceProvider": "elevenlabs"}}})
        self.assertEqual((s["voice"], s["aiVoiceProvider"]), ("auto", "auto"))
        s = config.settings({"halcyon": {"assistant": {"voice": "ai", "aiVoiceProvider": "openai"}}})
        self.assertEqual((s["voice"], s["aiVoiceProvider"]), ("ai", "openai"))



class SidebarTest(unittest.TestCase):
    def test_a_finished_sidebar_reply_is_handed_to_say_once(self):
        ai = (ROOT / "dots/.config/quickshell/ii/services/Ai.qml").read_text(encoding="utf-8")
        mark = ai[ai.index("function markDone()"):ai.index("function makeRequest()")]
        self.assertIn("const finished = !requester.message.done;", mark)
        self.assertIn("if (finished)\n                root.speakReply(requester.message);", mark)
        speak = ai[ai.index("function speakReply(message)"):]
        self.assertIn('[root.halcyonAssistantTool, "say", "--", text]', speak)
        self.assertIn("!assistant?.sidebarSpeak", speak)


if __name__ == "__main__":
    unittest.main()
