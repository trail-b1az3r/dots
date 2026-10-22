"""Piper voices from the three places they come from: built-in, Hugging Face (rhasspy/piper-voices, against a fake
server) and the AUR (piper-voices-* packages in /usr/share/piper-voices, faked with a scratch folder), and choosing
one. Run: python3 -m unittest discover -s tests"""

import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon/assistant"))

from halcyon_assistant import cli, config, daemon, piper_voices, speech  # noqa: E402

ONNX = b"fake onnx model " * 64


def meta(code="en_GB", name="English", rate=22050, quality="medium", speakers=None):
    return json.dumps({"language": {"code": code, "name_english": name}, "audio": {"sample_rate": rate, "quality": quality},
                       "speaker_id_map": speakers or {}})


def put_voice(directory: Path, key: str, **kw):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{key}.onnx").write_bytes(ONNX)
    (directory / f"{key}.onnx.json").write_text(meta(**kw))
    return directory / f"{key}.onnx"


class Scratch(unittest.TestCase):
    """A scratch models folder, AUR folder and custom folder in place of the real ones."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.models, self.aur, self.custom = root / "models", root / "usr/share/piper-voices", root / "custom"
        self.state = root / "state"
        self.state.mkdir()
        patches = [
            unittest.mock.patch.object(config, "MODELS", self.models),
            unittest.mock.patch.object(config, "ASSISTANT_STATE", self.state),
            unittest.mock.patch.object(piper_voices, "search_dirs", lambda: [self.models / "piper", self.custom, self.aur]),
            unittest.mock.patch.object(piper_voices, "source_of", self.source_of),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def source_of(self, onnx):
        if onnx.parent == self.models / "piper":
            return "built-in" if onnx.stem == piper_voices.BUILTIN else "hugging face"
        return "aur" if self.aur in onnx.parents else "custom"


class InstalledTest(Scratch):
    def test_voices_from_every_place_each_once(self):
        put_voice(self.models / "piper", "en_US-lessac-medium", code="en_US")
        put_voice(self.models / "piper", "en_GB-alba-medium")
        put_voice(self.aur / "de/de_DE/thorsten/high", "de_DE-thorsten-high", code="de_DE", name="German", quality="high")
        put_voice(self.aur / "en/en_GB/alba/medium", "en_GB-alba-medium")      # the same key twice: the first wins
        put_voice(self.custom, "my-voice", code="en_US")
        (self.custom / "no-json.onnx").write_bytes(ONNX)                       # Piper can't use it without its JSON
        found = {v["key"]: v for v in piper_voices.installed()}
        self.assertEqual(set(found), {"en_US-lessac-medium", "en_GB-alba-medium", "de_DE-thorsten-high", "my-voice"})
        self.assertEqual(found["en_US-lessac-medium"]["source"], "built-in")
        self.assertEqual(found["en_GB-alba-medium"]["source"], "hugging face")
        self.assertEqual(found["de_DE-thorsten-high"]["source"], "aur")
        self.assertEqual(found["de_DE-thorsten-high"]["quality"], "high")
        self.assertEqual(found["my-voice"]["source"], "custom")

    def test_which_voice_speaks(self):
        self.assertIsNone(piper_voices.resolve(""))
        put_voice(self.custom, "zz-custom")
        self.assertEqual(piper_voices.resolve("")["key"], "zz-custom", "no built-in: the first found")
        put_voice(self.models / "piper", piper_voices.BUILTIN)
        self.assertEqual(piper_voices.resolve("")["key"], piper_voices.BUILTIN, "nothing chosen: the built-in one")
        self.assertEqual(piper_voices.resolve("zz-custom")["key"], "zz-custom")
        self.assertIsNone(piper_voices.resolve("not-here"))
        path = put_voice(Path(self.tmp.name) / "elsewhere", "by-path")
        self.assertEqual(piper_voices.resolve(str(path))["key"], "by-path")

    def test_speakers_by_name_or_number(self):
        voice = piper_voices.describe(put_voice(self.custom, "multi", speakers={"p225": 0, "p226": 1, "p227": 2}))
        self.assertEqual(voice["speakers"], ["p225", "p226", "p227"])
        self.assertEqual(piper_voices.speaker_id(voice, "p226"), 1)
        self.assertEqual(piper_voices.speaker_id(voice, "2"), 2)
        self.assertIsNone(piper_voices.speaker_id(voice, "9"))
        self.assertIsNone(piper_voices.speaker_id(voice, ""))
        single = piper_voices.describe(put_voice(self.custom, "single"))
        self.assertIsNone(piper_voices.speaker_id(single, "1"))

    def test_piper_is_run_with_the_chosen_voice_and_speaker(self):
        path = put_voice(self.custom, "multi", speakers={"a": 0, "b": 1})
        runs = []

        def fake_popen(command, **kw):
            runs.append(command)
            raise OSError("stop here")

        settings = dict(config.DEFAULTS, piperVoice="multi", piperSpeaker="b")
        with unittest.mock.patch.object(speech, "piper_binary", return_value="/x/piper"), \
                unittest.mock.patch.object(speech.pcm, "player", return_value=["play"]), \
                unittest.mock.patch.object(speech.subprocess, "Popen", side_effect=fake_popen):
            problem = speech._speak_with_piper("hi", lambda: False, settings)
        self.assertIn("stop here", problem)
        self.assertEqual(runs[0], ["/x/piper", "--model", str(path), "--output-raw", "--speaker", "1"])

    def test_a_chosen_voice_that_is_gone_says_so(self):
        settings = dict(config.DEFAULTS, piperVoice="gone")
        with unittest.mock.patch.object(speech, "piper_binary", return_value="/x/piper"):
            problem = speech._speak_with_piper("hi", lambda: False, settings)
        self.assertIn("gone", problem)


CATALOG = {
    "en_GB-alba-medium": {"key": "en_GB-alba-medium", "language": {"code": "en_GB", "name_english": "English",
                          "country_english": "Great Britain"}, "quality": "medium", "num_speakers": 1,
                          "files": {"en/en_GB/alba/medium/en_GB-alba-medium.onnx":
                                    {"size_bytes": len(ONNX), "md5_digest": hashlib.md5(ONNX).hexdigest()},
                                    "en/en_GB/alba/medium/en_GB-alba-medium.onnx.json":
                                    {"size_bytes": 10, "md5_digest": hashlib.md5(meta().encode()).hexdigest()},
                                    "en/en_GB/alba/medium/MODEL_CARD": {"size_bytes": 3, "md5_digest": "x"}}},
    "de_DE-bad-low": {"key": "de_DE-bad-low", "language": {"code": "de_DE"}, "quality": "low", "num_speakers": 1,
                      "files": {"de/de_DE/bad/low/de_DE-bad-low.onnx": {"size_bytes": 5, "md5_digest": "0" * 32},
                                "de/de_DE/bad/low/de_DE-bad-low.onnx.json": {"size_bytes": 5, "md5_digest": ""}}},
}


class HubServer:
    def __init__(self):
        self.paths = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.paths.append(self.path)
                body = ONNX if self.path.endswith(".onnx") else meta().encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *e):
        self.httpd.shutdown()
        self.httpd.server_close()


class HuggingFaceTest(Scratch):
    def catalog_patch(self):
        return unittest.mock.patch.object(piper_voices, "_fetch", return_value=json.dumps(CATALOG).encode())

    def test_the_catalogue_lists_voices_and_is_kept(self):
        with self.catalog_patch() as fetch:
            voices = piper_voices.catalog()
            piper_voices.catalog()
        self.assertEqual(fetch.call_count, 1, "kept for a week, not fetched each time")
        alba = next(v for v in voices if v["key"] == "en_GB-alba-medium")
        self.assertEqual((alba["language"], alba["country"], alba["size"]), ("en_GB", "Great Britain", len(ONNX)))
        self.assertEqual(sorted(alba["files"]), ["en/en_GB/alba/medium/en_GB-alba-medium.onnx",
                                                 "en/en_GB/alba/medium/en_GB-alba-medium.onnx.json"])

    def test_offline_the_last_list_is_used(self):
        with self.catalog_patch():
            piper_voices.catalog()
        with unittest.mock.patch.object(piper_voices, "_fetch", side_effect=piper_voices.VoiceError("offline")):
            # rhasspy's two, and the voices from other repos (GLaDOS)
            self.assertEqual(len(piper_voices.catalog(refresh=True)), 2 + len(piper_voices.FEATURED))

    def test_download_checks_and_keeps_the_voice(self):
        with HubServer() as hub, self.catalog_patch(), unittest.mock.patch.object(piper_voices, "HF_BASE", hub.url):
            path = piper_voices.download("en_GB-alba-medium")
        self.assertEqual(path.read_bytes(), ONNX)
        self.assertTrue(path.with_name(path.name + ".json").is_file())
        self.assertEqual(sorted(hub.paths), ["/en/en_GB/alba/medium/en_GB-alba-medium.onnx",
                                             "/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json"])
        self.assertEqual(piper_voices.resolve("en_GB-alba-medium")["source"], "hugging face")

    def test_a_download_that_does_not_match_its_checksum_is_not_kept(self):
        with HubServer() as hub, self.catalog_patch(), unittest.mock.patch.object(piper_voices, "HF_BASE", hub.url):
            with self.assertRaises(piper_voices.VoiceError) as caught:
                piper_voices.download("de_DE-bad-low")
        self.assertIn("checksum", str(caught.exception))
        self.assertEqual(list((self.models / "piper").iterdir()), [])

    def test_unknown_voice(self):
        with self.catalog_patch(), self.assertRaises(piper_voices.VoiceError):
            piper_voices.download("xx_XX-nobody-low")

    def test_remove_only_what_was_downloaded(self):
        put_voice(self.models / "piper", "en_GB-alba-medium")
        put_voice(self.aur, "de_DE-thorsten-high")
        piper_voices.remove("en_GB-alba-medium")
        self.assertEqual(list((self.models / "piper").iterdir()), [])
        with self.assertRaises(piper_voices.VoiceError):
            piper_voices.remove("de_DE-thorsten-high")


class AURTest(Scratch):
    ANSWER = {"results": [{"Name": "piper-voices-en-gb", "Version": "1.0.0-5", "Description": "Voices (en_GB)"},
                          {"Name": "piper-voices-common", "Version": "1.0.1-2", "Description": "common"},
                          {"Name": "piper-voices-de-de", "Version": "1.0.0-1", "Description": "Voices (de_DE)"}]}

    def test_the_voice_packages_and_which_are_installed(self):
        with unittest.mock.patch.object(piper_voices, "_fetch", return_value=json.dumps(self.ANSWER).encode()), \
                unittest.mock.patch.object(piper_voices, "installed_packages", return_value={"piper-voices-de-de"}):
            packages = piper_voices.aur_packages()
        self.assertEqual([(p["name"], p["installed"]) for p in packages],
                         [("piper-voices-de-de", True), ("piper-voices-en-gb", False)])

    def test_install_goes_through_the_aur_helper_and_only_for_voices(self):
        with unittest.mock.patch.object(piper_voices.shutil, "which", side_effect=lambda n: "/usr/bin/yay" if n == "yay" else None):
            self.assertEqual(piper_voices.aur_install_command("piper-voices-en-gb"), ["yay", "-S", "--needed", "piper-voices-en-gb"])
            with self.assertRaises(piper_voices.VoiceError):
                piper_voices.aur_install_command("firefox")
        with unittest.mock.patch.object(piper_voices.shutil, "which", return_value=None), \
                self.assertRaises(piper_voices.VoiceError):
            piper_voices.aur_install_command("piper-voices-en-gb")


class CliTest(Scratch):
    def run_cli(self, *args):
        written = {}
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(config, "write_setting", side_effect=lambda k, v: written.__setitem__(k, v)), \
                unittest.mock.patch.object(config, "settings", return_value=dict(config.DEFAULTS)), \
                unittest.mock.patch.object(daemon, "send", return_value=None), \
                redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(args))
        return code, out.getvalue(), err.getvalue(), written

    def test_use_a_voice_here_with_a_speaker(self):
        put_voice(self.aur, "en_GB-vctk-medium", speakers={"p225": 0, "p226": 1})
        code, out, _, written = self.run_cli("voice", "use", "en_GB-vctk-medium", "--speaker", "p226")
        self.assertEqual(code, 0)
        self.assertEqual(written, {"piperVoice": "en_GB-vctk-medium", "piperSpeaker": "p226"})

    def test_a_voice_not_here_or_a_wrong_speaker_is_refused(self):
        code, _, err, written = self.run_cli("voice", "use", "en_GB-alba-medium")
        self.assertEqual((code, written), (1, {}))
        self.assertIn("voice get en_GB-alba-medium", err)
        put_voice(self.custom, "single")
        code, _, err, written = self.run_cli("voice", "use", "single", "--speaker", "p9")
        self.assertEqual((code, written), (1, {}))

    def test_voices_json_has_the_three_sources(self):
        put_voice(self.models / "piper", piper_voices.BUILTIN)
        with unittest.mock.patch.object(piper_voices, "catalog", return_value=[{"key": "en_GB-alba-medium", "language": "en_GB"},
                                                                               {"key": piper_voices.BUILTIN, "language": "en_US"}]), \
                unittest.mock.patch.object(piper_voices, "aur_packages", return_value=[{"name": "piper-voices-en-gb"}]):
            code, out, _, _ = self.run_cli("voices", "--json", "--all")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["current"], piper_voices.BUILTIN)
        self.assertEqual([v["key"] for v in data["installed"]], [piper_voices.BUILTIN])
        self.assertEqual({v["key"]: v["installed"] for v in data["huggingface"]},
                         {"en_GB-alba-medium": False, piper_voices.BUILTIN: True})
        self.assertEqual(data["aur"], [{"name": "piper-voices-en-gb"}])


if __name__ == "__main__":
    unittest.main()
