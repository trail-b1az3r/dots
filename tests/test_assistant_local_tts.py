"""Local voice models besides Piper: Kokoro (its model faked, so no 340 MB download) and a voice program of your
own (real little programs). Run: python3 -m unittest discover -s tests"""

import io
import struct
import sys
import tempfile
import unittest
import unittest.mock
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon/assistant"))

from halcyon_assistant import config, local_tts, speech  # noqa: E402

try:
    import numpy
except ImportError:
    numpy = None


def settings(**kw):
    return {**config.DEFAULTS, **kw}


def wav_bytes():
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack("<4h", 0, 1000, -1000, 0))
    return out.getvalue()


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def script(self, name, body):
        path = self.dir / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)
        return path

    def test_the_text_goes_in_on_stdin_never_through_a_shell(self):
        said = self.dir / "said"
        prog = self.script("speak", f'cat > "{said}"')
        wav, problem = local_tts.run_command("hi; rm -rf ~ $(whoami)", settings(ttsCommand=f"'{prog}'"))
        self.assertEqual((wav, problem), (None, None), "it played itself: nothing to play here")
        self.assertEqual(said.read_text(), "hi; rm -rf ~ $(whoami)")

    def test_a_wav_on_stdout_is_played(self):
        data = self.dir / "a.wav"
        data.write_bytes(wav_bytes())
        prog = self.script("tts", f'cat > /dev/null; cat "{data}"')
        played = []
        with unittest.mock.patch.object(speech, "play_wav", side_effect=lambda path, stop: played.append(Path(path).read_bytes())):
            self.assertIsNone(speech.speak_once("command", "hello", settings=settings(ttsCommand=str(prog))))
        self.assertEqual(played, [wav_bytes()])

    def test_failures_are_said_plainly(self):
        self.assertIn("is not installed", local_tts.run_command("x", settings(ttsCommand="no-such-voice-prog"))[1])
        prog = self.script("broken", 'echo "model missing" >&2; exit 4')
        self.assertIn("model missing", local_tts.run_command("x", settings(ttsCommand=str(prog)))[1])
        self.assertIn("can't be read", local_tts.run_command("x", settings(ttsCommand="say 'unclosed"))[1])
        self.assertFalse(local_tts.command_configured(settings(ttsCommand="  ")))

    def test_a_command_goes_first_when_set_and_is_never_tried_when_not(self):
        with unittest.mock.patch.object(local_tts, "kokoro_installed", return_value=False), \
                unittest.mock.patch.object(speech, "piper_binary", return_value=None), \
                unittest.mock.patch.object(speech.tts_ai, "provider", return_value=None), \
                unittest.mock.patch.object(speech.shutil, "which", return_value=None):
            self.assertEqual(speech.engines(settings(ttsCommand="my-tts")), ["command"])
            self.assertEqual(speech.engines(settings()), [])


class FakeKokoro:
    def __init__(self, model, voices):
        self.paths = (model, voices)
        self.calls = []

    def create(self, text, voice, lang):
        self.calls.append((text, voice, lang))
        if voice == "nope":
            raise ValueError("Voice nope not found")
        return numpy.array([0.0, 0.5, -1.5, 1.0], dtype="float32"), 24000

    def get_voices(self):
        return ["bf_emma", "af_heart"]


@unittest.skipUnless(numpy, "numpy is not installed")
class KokoroTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        models = Path(self.tmp.name)
        (models / "kokoro").mkdir()
        for name in local_tts.KOKORO_FILES:
            (models / "kokoro" / name).write_bytes(b"x")
        fake_module = unittest.mock.MagicMock(Kokoro=FakeKokoro)
        for p in (unittest.mock.patch.object(config, "MODELS", models),
                  unittest.mock.patch.dict(sys.modules, {"kokoro_onnx": fake_module}),
                  unittest.mock.patch.object(local_tts.importlib.util, "find_spec", return_value=object()),
                  unittest.mock.patch.object(local_tts, "_kokoro", None)):
            p.start()
            self.addCleanup(p.stop)

    def test_the_voice_picks_its_language_and_audio_is_16_bit(self):
        pcm, rate = local_tts.kokoro_pcm("Hello.", settings(kokoroVoice="bf_emma"))
        self.assertEqual(rate, 24000)
        self.assertEqual(struct.unpack("<4h", pcm), (0, 16383, -32767, 32767), "clipped, not wrapped")
        self.assertEqual(local_tts._kokoro.calls, [("Hello.", "bf_emma", "en-gb")])

    def test_default_voice_and_languages(self):
        local_tts.kokoro_pcm("Hi.", settings())
        self.assertEqual(local_tts._kokoro.calls[-1][1:], ("af_heart", "en-us"))
        self.assertEqual([local_tts.kokoro_lang(v) for v in ("jf_alpha", "zf_xiaobei", "ff_siwis", "xx")],
                         ["ja", "cmn", "fr-fr", "en-us"])

    def test_an_unknown_voice_is_reported(self):
        with self.assertRaises(local_tts.LocalVoiceError) as caught:
            local_tts.kokoro_pcm("Hi.", settings(kokoroVoice="nope"))
        self.assertIn("nope", str(caught.exception))

    def test_without_the_model_files_it_is_not_offered(self):
        (config.MODELS / "kokoro" / "voices-v1.0.bin").unlink()
        self.assertFalse(local_tts.kokoro_installed())
        with self.assertRaises(local_tts.LocalVoiceError):
            local_tts.kokoro_pcm("Hi.", settings())

    def test_kokoro_comes_before_piper_in_auto(self):
        with unittest.mock.patch.object(speech, "piper_binary", return_value="/x/piper"), \
                unittest.mock.patch.object(speech, "piper_voice", return_value=Path("/x/v.onnx")), \
                unittest.mock.patch.object(speech.tts_ai, "provider", return_value=None), \
                unittest.mock.patch.object(speech.shutil, "which", return_value=None):
            self.assertEqual(speech.engines(settings()), ["kokoro", "piper"])
            self.assertEqual(speech.engines(settings(voice="piper")), ["piper", "kokoro"])


if __name__ == "__main__":
    unittest.main()
