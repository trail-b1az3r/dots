# The AI assistant

Two backends, both real. Neither is a stub, and neither is required —
the assistant is one feature of the desktop, not a dependency of it.

## Choosing a backend

**Settings → AI Assistant → Provider**, or:

```sh
halcyon settings set assistant.provider nixorb   # or: local, auto
halcyon assistant providers                      # what is installed, and healthy
halcyon assistant status                         # which one answered, and why
```

Switching takes effect on the next request. There is no file to edit and
no service to restart.

| Provider | What it uses |
|---|---|
| `nixorb` | NixOrb, over its socket, falling back to its CLI. |
| `local` | Whisper (or whisper.cpp) + Ollama (or any OpenAI-compatible server) + Piper (falling back to espeak-ng). |
| `auto` | NixOrb when it answers; local otherwise. |

Both can be installed at once. They do not share state and do not
interfere.

## How a request is handled

1. **Capture.** `pw-record`, `parecord` or `arecord`, whichever exists.
   Silence detection samples the tail of the WAV, so recording stops
   when you do rather than after a fixed timeout.
2. **Transcribe.** Locally, by whisper.cpp or whisper.
3. **Intent rules.** `intents.py` matches the text against regex rules
   built over the action registry. "Turn the volume down", "open
   Firefox", "go to the second workspace" all match. **If a rule
   matches, the action runs and no model is invoked.** This is most of
   what people actually ask for, and it is instant and offline.
4. **The model, only if nothing matched.** The request, the conversation
   history and the action catalog go to the LLM.
5. **Tool calls are validated.** The model names an action and supplies
   parameters. Those are type-checked, range-checked and
   pattern-checked before anything happens. The model cannot name a
   shell command, because no action takes one.
6. **Destructive actions stop and ask.** Suspend, reboot, shut down and
   log out return `needs_confirmation` rather than running.
7. **Speak,** if `assistant.voice.enabled`.

## What leaves your machine

With `provider: local` and the privacy settings at their defaults:
**nothing**. No audio, no text, no screen content.

Three settings each open one door, and all three are **off by default**:

| Setting | What it permits |
|---|---|
| `assistant.privacy.allowWebAccess` | Actions that reach the network — web search, currency rates. |
| `assistant.privacy.allowScreenContext` | The assistant seeing the screen. |
| `assistant.privacy.allowClipboardContext` | The assistant reading the clipboard. |

Two more control what is kept locally:

| Setting | Effect |
|---|---|
| `assistant.privacy.storeConversations` | Off keeps history in memory only. |
| `assistant.privacy.confirmDestructiveActions` | Off lets suspend/reboot run without asking. |

`assistant.microphone.respectMute` is on by default: the assistant
refuses to listen while the microphone is muted. The mute key means
mute.

The wake word is **off by default**. An always-listening microphone
should be something you switch on deliberately.

The daemon listens on a Unix socket in `$XDG_RUNTIME_DIR`, mode 0600 —
not a TCP port, and not reachable from another user account.

```sh
halcyon assistant history     # what it has kept
halcyon assistant clear       # forget it
```

## Setting up the local stack

```sh
./install.sh --with-ai
ollama pull llama3.2:3b
halcyon settings set assistant.provider local
halcyon assistant status
```

A 3B model is enough for desktop commands and short answers, and it
leaves the GPU free. Larger models work:

```sh
halcyon settings set assistant.local.llmModel qwen2.5:7b
halcyon settings set assistant.local.maxTokens 2048
```

### Pointing at another server

Anything OpenAI-compatible — llama.cpp's server, vLLM, LM Studio:

```sh
halcyon settings set assistant.local.llmBackend openai
halcyon settings set assistant.local.llmHost http://127.0.0.1:8080
halcyon settings set assistant.local.llmModel local-model
```

### Speech

Whisper models are found automatically; point at one explicitly if you
keep them somewhere unusual:

```sh
halcyon settings set assistant.local.sttModel ~/models/ggml-base.en.bin
halcyon settings set assistant.voice.name en_GB-alba-medium
halcyon settings set assistant.voice.speed 1.1
```

Without Piper, `espeak-ng` is used. It sounds worse and works
everywhere.

## Setting up NixOrb

```sh
halcyon settings set assistant.provider nixorb
halcyon assistant status
```

The adapter tries NixOrb's socket first and its CLI second, and reports
which it used. If the socket is somewhere non-standard:

```sh
halcyon settings set assistant.nixorb.socketPath /run/user/1000/nixorb.sock
halcyon settings set assistant.nixorb.autostart true
```

`autostart` starts NixOrb with the session if it is not already running.

## Using it

| Shortcut | What it does |
|---|---|
| `Super + A` | Push-to-talk. |
| `Super + Shift + Space` | Type a question. |
| `Super + Shift + A` | Cancel the current turn. |

From anywhere:

```sh
halcyon assistant ask "what's my battery at"
halcyon assistant listen
halcyon assistant toggle        # listen, or cancel if already busy
halcyon assistant confirm       # approve a pending destructive action
```

## What it can do

33 actions, in eight categories: `apps`, `windows`, `display`, `audio`,
`capture`, `appearance`, `power` and `network`.

```sh
halcyon action --list                    # the catalog, with parameters
halcyon action volume.set percent=30
halcyon action session.reboot --confirm  # destructive ones need this
```

Adding one makes it available to the assistant, Spotlight and the CLI at
the same time — see [Extending Halcyon](../README.md#extending-halcyon).

## Adding a backend

Create `src/halcyon/assistant/providers/<name>.py` with a class
exposing:

```python
def available(self) -> bool: ...
def status(self) -> dict[str, Any]: ...
def ask(self, text: str, context: Context) -> Iterator[Event]: ...
```

`ask` yields `Event`s — `token`, `action`, `error`, `done`. Register it
in `providers/__init__.py` and add its name to the `assistant.provider`
choices in `config/system/settings.default.json`. It appears in Settings
without any UI work.

`providers/local.py` is the reference implementation: intent parsing,
streaming, tool calls, and error handling that does not poison the
conversation history.

## Troubleshooting

```sh
halcyon assistant status
journalctl --user -u halcyon-assistant -n 50
```

**"No backend available."** Neither NixOrb nor the local stack is
installed. `halcyon assistant providers` says which pieces are missing.

**It transcribes but does not answer.** The LLM is unreachable. Check
`assistant.local.llmHost`, and that `ollama serve` is running.

**It answers but does not speak.** Piper is missing or the voice model
is not found. `assistant.voice.name` must match an installed model.

**It hears nothing.** Check the microphone is not muted
(`assistant.microphone.respectMute` is on by default), and that
`assistant.microphone.device` names a real PipeWire source —
`wpctl status` lists them.
