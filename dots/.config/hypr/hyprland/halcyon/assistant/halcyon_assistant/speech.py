"""Reading replies aloud: Piper if a voice is set up, else an AI voice (Gemini or OpenAI, when a key is stored),
else espeak-ng, else speech-dispatcher. Settings > Halcyon > Assistant > Voice puts one of them first.

Each engine that can run is tried in turn, so one that fails (a missing voice file, an audio player that does not
take the stream, a provider that says no) falls back to the next instead of leaving the reply silent. Why each one
failed goes to the assistant's log, and `halcyon assistant test-voice` runs the same thing and prints it.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile

from pathlib import Path

from . import config, local_tts, pcm, piper_voices, tts_ai

log = logging.getLogger("halcyon.speech")

DEFAULT_RATE = 22050


def piper_voice(settings=None):
    """The chosen Piper voice's .onnx (Settings > Assistant > Voice > Piper voice), else the built-in one, else the
    first found (piper_voices.py says where it looks). None when there is none."""
    settings = config.settings() if settings is None else settings
    voice = piper_voices.resolve(settings.get("piperVoice", ""))
    return Path(voice["path"]) if voice else None


def piper_rate(voice) -> int:
    """The voice's sample rate, from the .onnx.json beside it. Low-quality voices are 16 kHz, most 22.05 kHz."""
    try:
        data = json.loads(voice.with_name(voice.name + ".json").read_text(encoding="utf-8"))
        return int(data["audio"]["sample_rate"])
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_RATE


def piper_binary():
    """The piper program. Hyprland's PATH may not include the place setup put it, so look there too."""
    found = shutil.which("piper")
    if found:
        return found
    for candidate in (config.VENV / "bin/piper", config.HOME / ".local/bin/piper"):
        if candidate.exists():
            return str(candidate)
    return None


# Settings > Voice names a family; these are the engines in it.
FAMILY = {"piper": "piper", "kokoro": "kokoro", "command": "command", "ai": "ai", "espeak-ng": "espeak",
          "espeak": "espeak", "spd-say": "system"}


def engines(settings=None):
    """The engines that can run, in the order they are tried: the chosen voice first, then the rest, best first."""
    settings = config.settings() if settings is None else settings
    found = []
    if local_tts.command_configured(settings):
        found.append("command")
    if local_tts.kokoro_installed():
        found.append("kokoro")
    if piper_binary() and piper_voice(settings):
        found.append("piper")
    if tts_ai.provider(settings):
        found.append("ai")
    if shutil.which("espeak-ng"):
        found.append("espeak-ng")
    elif shutil.which("espeak"):
        found.append("espeak")
    if shutil.which("spd-say"):
        found.append("spd-say")
    chosen = settings.get("voice", "auto")
    if chosen != "auto":
        found.sort(key=lambda name: FAMILY[name] != chosen)  # stable: the chosen one first, the others in order
    return found


def engine(settings=None):
    """The engine that will be tried first, or None."""
    available = engines(settings)
    return available[0] if available else None


def plain(text, limit=1500):
    """What to read aloud from a reply written for the screen: no code, markdown marks, links or thinking.
    Long replies are cut at a sentence, with a word that the rest is on screen."""
    text = re.sub(r"<think>.*?</think>", " ", str(text), flags=re.S | re.I)
    text = re.sub(r"```.*?(```|$)", " (code on screen) ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)            # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)          # links: their words
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^\s{0,3}(#{1,6}|[-*+]|\d+[.)]|>)\s+", "", text, flags=re.M)  # headings, bullets, quotes
    text = re.sub(r"(\*\*|__|\*|_|~~)(?=\S)(.+?)(?<=\S)\1", r"\2", text)  # emphasis
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.M)         # tables
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    # A heading or a list item ends where its line does: a pause, so it doesn't run into the next one.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = " ".join(line if line[-1] in ".!?:;,)" else line + "." for line in lines)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        cut = max(text.rfind(". ", 0, limit), text.rfind("? ", 0, limit), text.rfind("! ", 0, limit))
        text = text[: cut + 1 if cut > limit // 2 else limit].rstrip() + " The rest is on screen."
    return text


def _wait(processes, should_stop):
    """Wait for the processes. Returns True if they were stopped early."""
    stopped = False
    while any(p.poll() is None for p in processes):
        if should_stop():
            stopped = True
            for p in processes:
                p.terminate()
            break
        try:
            processes[-1].wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
    for p in processes:
        p.wait()
    return stopped


def _speak_with_piper(text, should_stop, settings=None):
    settings = config.settings() if settings is None else settings
    voice = piper_voice(settings)
    if voice is None:
        chosen = settings.get("piperVoice") or "built-in"
        return f"the Piper voice {chosen} is not on this computer (halcyon assistant voices lists the ones that are)"
    command = [piper_binary(), "--model", str(voice), "--output-raw"]
    speaker = piper_voices.speaker_id(piper_voices.describe(voice) or {}, settings.get("piperSpeaker", ""))
    if speaker is not None:
        command += ["--speaker", str(speaker)]
    player = pcm.player(piper_rate(voice))
    if player is None:
        return "no audio player (install pipewire, pulseaudio-utils or alsa-utils)"
    synth_errors = tempfile.TemporaryFile()
    play_errors = tempfile.TemporaryFile()
    try:
        synth = subprocess.Popen(command,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=synth_errors)
        play = subprocess.Popen(player, stdin=synth.stdout, stderr=play_errors)
    except OSError as error:
        synth_errors.close()
        play_errors.close()
        return f"could not start piper or {player[0]}: {error}"
    synth.stdout.close()  # piper gets a broken pipe if the player stops early
    # A piper that dies at once (a bad voice, say) breaks the pipe; the write is buffered, so that can surface on
    # close as well. Its exit code and message are reported below.
    try:
        synth.stdin.write(text.encode())
        synth.stdin.close()
    except BrokenPipeError:
        try:
            synth.stdin.close()
        except BrokenPipeError:
            pass
    stopped = _wait([synth, play], should_stop)
    problems = []
    for name, handle, proc in (("piper", synth_errors, synth), (player[0], play_errors, play)):
        handle.seek(0)
        output = handle.read().decode(errors="replace").strip()
        handle.close()
        if proc.returncode and not stopped:
            problems.append(f"{name} exited {proc.returncode}: {output[-300:] or 'no message'}")
    return "; ".join(problems) or None


def _speak_with(command, should_stop):
    try:
        proc = subprocess.Popen(command, stderr=subprocess.PIPE)
    except OSError as error:
        return f"could not start {command[0]}: {error}"
    stopped = _wait([proc], should_stop)
    if proc.returncode and not stopped:
        return f"{command[0]} exited {proc.returncode}: {proc.stderr.read().decode(errors='replace').strip()[-300:]}"
    return None


def play_pcm(data, rate, should_stop=lambda: False):
    """Play raw s16 mono PCM. Returns None when it played, else why not."""
    player = pcm.player(rate)
    if player is None:
        return "no audio player (install pipewire, pulseaudio-utils or alsa-utils)"
    errors = tempfile.TemporaryFile()
    try:
        play = subprocess.Popen(player, stdin=subprocess.PIPE, stderr=errors)
    except OSError as error:
        return f"could not start {player[0]}: {error}"
    try:
        for start in range(0, len(data), 1 << 15):
            if should_stop():
                break
            play.stdin.write(data[start:start + (1 << 15)])
        play.stdin.close()
    except BrokenPipeError:
        pass
    stopped = _wait([play], should_stop)
    errors.seek(0)
    output = errors.read().decode(errors="replace").strip()
    errors.close()
    if play.returncode and not stopped:
        return f"{player[0]} exited {play.returncode}: {output[-300:] or 'no message'}"
    return None


def play_wav(path, should_stop=lambda: False):
    """Play a WAV file with whichever player there is. Returns None when it played, else why not."""
    for player in (["pw-play"], ["paplay"], ["aplay", "-q"]):
        if shutil.which(player[0]):
            return _speak_with(player + [str(path)], should_stop)
    return "no audio player (install pipewire, pulseaudio-utils or alsa-utils)"


def _speak_with_kokoro(text, should_stop, settings):
    try:
        data, rate = local_tts.kokoro_pcm(text, settings)
    except local_tts.LocalVoiceError as error:
        return str(error)
    if should_stop():
        return None
    return play_pcm(data, rate, should_stop)


def _speak_with_command(text, should_stop, settings):
    wav, problem = local_tts.run_command(text, settings)
    if problem or wav is None or should_stop():
        return problem
    path = local_tts.wav_file(wav)
    try:
        return play_wav(path, should_stop)
    finally:
        path.unlink(missing_ok=True)


def _speak_with_ai(text, should_stop, settings):
    try:
        data, rate = tts_ai.synthesize(text, settings)
    except tts_ai.VoiceError as error:
        return f"{tts_ai.provider(settings) or 'AI voice'}: {error}"
    if should_stop():
        return None
    return play_pcm(data, rate, should_stop)


def speak_once(name, text, should_stop=lambda: False, settings=None):
    """Speak with one engine. Returns None when it worked, else why not."""
    if name == "piper":
        return _speak_with_piper(text, should_stop, settings)
    settings = config.settings() if settings is None else settings
    if name == "kokoro":
        return _speak_with_kokoro(text, should_stop, settings)
    if name == "command":
        return _speak_with_command(text, should_stop, settings)
    if name == "ai":
        return _speak_with_ai(text, should_stop, settings)
    if name in ("espeak-ng", "espeak"):
        return _speak_with([name, "-s", "165", text], should_stop)
    if name == "spd-say":
        return _speak_with(["spd-say", "--wait", text], should_stop)
    return f"unknown engine {name}"


def say(text, should_stop=lambda: False, settings=None):
    """Speak text with the best engine that works. Returns False if none did. Stops if asked."""
    if not text.strip():
        return True  # nothing to say is not a failure
    settings = config.settings() if settings is None else settings
    available = engines(settings)
    if not available:
        log.error("no voice engine: install espeak-ng, run `halcyon assistant setup --piper`, "
                  "or store a Gemini or OpenAI key for an AI voice")
        return False
    for name in available:
        problem = speak_once(name, text, should_stop, settings)
        if problem is None:
            return True
        log.error("speaking with %s failed: %s", name, problem)
        if should_stop():
            return True
    return False
