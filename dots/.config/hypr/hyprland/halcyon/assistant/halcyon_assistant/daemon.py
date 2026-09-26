"""The assistant daemon: listens on a socket, owns the microphone.

Commands (one line each, over $XDG_RUNTIME_DIR/halcyon-assistant.sock):
    listen   start listening; while busy, cancels instead (push-to-talk toggle)
    cancel   stop listening, thinking or speaking
    ask TEXT answer typed text as if it were spoken
    reload   re-read settings (the Settings page sends this)
    status   one line of JSON
"""

import json
import logging
import os
import socket
import threading

from . import audio, config, conversation, notify, providers, speech, stt, wake

log = logging.getLogger("halcyon-assistant")


class Assistant:
    def __init__(self):
        self.settings = config.settings()
        self.busy = threading.Event()
        self.cancel = threading.Event()
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.conversation = None
        self.conversation_key = None
        self.state = "idle"
        self.wake_thread = None

    # -- commands -----------------------------------------------------------

    def handle(self, line):
        command, _, rest = line.strip().partition(" ")
        if command == "listen":
            if self.busy.is_set():
                self.cancel.set()
                return "cancelled"
            self._start(self.listen_and_answer)
            return "listening"
        if command == "ask" and rest:
            if self.busy.is_set():
                return "busy"
            self._start(self.answer, rest)
            return "thinking"
        if command == "cancel":
            self.cancel.set()
            return "cancelled"
        if command == "reload":
            self.settings = config.settings()
            self.conversation = None
            self._restart_wake()
            return "reloaded"
        if command == "status":
            return json.dumps({"state": self.state, "provider": self.settings["provider"],
                               "wakeWord": self.settings["wakeWord"] and wake.available(),
                               "speech": stt.available(), "voice": speech.engine()})
        return "unknown command"

    def _start(self, target, *args):
        with self.lock:
            if self.busy.is_set():
                return
            self.busy.set()
            self.cancel.clear()

        def run():
            try:
                target(*args)
            except Exception as error:  # never let one request kill the daemon
                log.exception("request failed")
                notify.show("Assistant error", str(error), icon="dialog-error")
            finally:
                self.state = "idle"
                self.busy.clear()
        threading.Thread(target=run, daemon=True).start()

    # -- the pipeline -------------------------------------------------------

    def listen_and_answer(self):
        if not stt.available():
            notify.show("Speech recognition isn't set up",
                        "Run `halcyon assistant setup` in a terminal. Typing works meanwhile: halcyon assistant ask …",
                        icon="dialog-warning")
            return
        notify.reset()
        self.state = "listening"
        notify.show("Listening…", "Speak now. Press the shortcut again to cancel.", timeout_ms=20000)
        notify.chime("start")
        pcm = audio.record_utterance(cancelled=self.cancel.is_set)
        notify.chime("stop")
        if self.cancel.is_set():
            notify.show("Cancelled", "", timeout_ms=1500)
            return
        if not pcm:
            notify.show("I didn't catch that", "Nothing was heard. Check your microphone in Settings > Audio.",
                        icon="audio-input-microphone-muted", timeout_ms=4000)
            return
        self.state = "transcribing"
        notify.show("…", "Working out what you said", timeout_ms=20000)
        text = stt.transcribe(pcm, self.settings["speechModel"], self.settings["language"])
        if not text:
            notify.show("I didn't catch that", "", timeout_ms=3000)
            return
        self.answer(text)

    def answer(self, text):
        self.state = "thinking"
        notify.show(f"“{text}”", "Thinking…", timeout_ms=30000)
        key = (self.settings["provider"], self.settings["model"], self.settings["endpoint"])
        if self.conversation is None or self.conversation_key != key:
            self.conversation = conversation.Conversation(providers.resolve(self.settings),
                                                          self.settings["allowActions"])
            self.conversation_key = key
        try:
            reply = self.conversation.ask(
                text, on_action=lambda name, args: notify.show(f"“{text}”", f"Doing: {name.replace('_', ' ')}",
                                                                timeout_ms=30000))
        except providers.ProviderError as error:
            notify.show("The assistant couldn't answer", str(error), icon="dialog-error", timeout_ms=10000)
            return
        if self.cancel.is_set():
            return
        self.state = "speaking"
        notify.show(f"“{text}”", reply, icon="audio-input-microphone", timeout_ms=max(6000, 90 * len(reply)))
        if self.settings["speak"]:
            speech.say(reply, should_stop=self.cancel.is_set)

    # -- wake word ------------------------------------------------------------

    def _restart_wake(self):
        if self.wake_thread and self.wake_thread.is_alive():
            self._wake_stop = True
            self.wake_thread.join(timeout=3)
        self._wake_stop = False
        if not self.settings["wakeWord"]:
            return
        if not wake.available():
            notify.show("Wake word isn't set up", "Run `halcyon assistant setup --wake`.", icon="dialog-warning")
            return

        def on_wake():
            self._start(self.listen_and_answer)

        self.wake_thread = threading.Thread(
            target=wake.listen, daemon=True,
            args=(self.settings["wakePhrase"], on_wake,
                  lambda: self.stop.is_set() or self._wake_stop, self.busy.is_set))
        self.wake_thread.start()

    # -- serving ----------------------------------------------------------------

    def serve(self):
        config.SOCKET.parent.mkdir(parents=True, exist_ok=True)
        if config.SOCKET.exists():
            if send("status") is not None:
                print("the assistant is already running")
                return 1
            config.SOCKET.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(config.SOCKET))
        os.chmod(config.SOCKET, 0o600)
        server.listen(4)
        log.info("listening on %s", config.SOCKET)
        self._restart_wake()
        if stt.available():
            # Load Whisper now, so the first request doesn't wait for it.
            threading.Thread(target=lambda: stt.load(self.settings["speechModel"]), daemon=True).start()
        try:
            while not self.stop.is_set():
                connection, _ = server.accept()
                with connection:
                    line = connection.makefile().readline()
                    if line.strip() == "quit":
                        connection.sendall(b"bye\n")
                        break
                    connection.sendall((self.handle(line) + "\n").encode())
        finally:
            self.stop.set()
            server.close()
            config.SOCKET.unlink(missing_ok=True)
        return 0


def send(line, timeout=3):
    """Send one command to a running daemon; None if there isn't one."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(str(config.SOCKET))
            client.sendall((line.strip() + "\n").encode())
            return client.makefile().readline().strip()
    except OSError:
        return None
