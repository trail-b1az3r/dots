# Voice assistant

Press **`Super + Shift + Space`**, say what you want, and stop talking.
Halcyon answers in a notification and out loud. Press the shortcut again
to cancel. Turn on **"Hey Halcyon"** in **Settings > Halcyon > Assistant**
to start it by voice instead.

**One-time setup** (speech recognition, about 300 MB):

```sh
halcyon assistant setup            # add --wake for "Hey Halcyon", --piper for a natural voice
halcyon assistant login            # use your Claude Pro/Max plan: no API key needed
halcyon assistant doctor           # what's ready and what isn't
```

Or use an API key instead: `halcyon assistant key anthropic` (or `gemini`,
`openai`, `mistral`), or a key already entered in the AI sidebar.

### Using a Claude Pro or Max plan

Anthropic doesn't let other apps sign in with a claude.ai account or reuse
its login. The supported way to use a plan outside claude.ai is
**Claude Code**, Anthropic's own CLI, so that's what Halcyon uses.
`halcyon assistant login`, or **Sign in with Claude** in
**Settings > Halcyon > Assistant**, does the following:

1. Offers to install Claude Code with Anthropic's installer if it's
   missing (it asks first).
2. Runs Claude Code's own sign-in (`claude auth login`), which opens
   claude.ai in your browser. Halcyon never sees your login.
3. Switches the assistant to **Claude plan**.

After that, each request runs Claude Code headless (`claude -p`), locked
down so the only things it can do are Halcyon's desktop actions:

- all of its built-in tools are off: no shell, no files;
- it loads no MCP servers except Halcyon's, which serves the same
  twelve checked actions as every other provider;
- any `ANTHROPIC_API_KEY` in the environment is removed for the call, so
  your plan is what gets used.

Requests count against your plan's usage limits. The model is whatever
your plan's Claude Code uses; `halcyon assistant set model opus` picks
another.

**What happens:**

1. The microphone records until you pause (PipeWire).
2. **Whisper** turns your speech into text on this computer; the audio
   never leaves your machine.
3. The text goes to the AI you chose: **Claude on your Pro/Max plan**
   (through Claude Code), **Claude with an API key** (`claude-opus-5`),
   **Gemini**, a local **Ollama**, **LM Studio** or **HyperNix** model, a
   **HyperNix T1** server, or any **OpenAI-compatible** server. *Auto*
   picks an Anthropic API key if set, then your Claude plan, then Gemini,
   then a T1 server with a key, then whichever local server is running.
   Keys are shared with end-4's AI sidebar, so one entered there works
   here too.
4. The reply appears in a notification and is spoken, with Piper if you
   set it up, otherwise espeak-ng. If one voice fails the next is tried.

### Local models: LM Studio, HyperNix and T1

The assistant and the AI sidebar both use these. The sidebar lists every
model it finds (`/model` shows them), and gets the model ready before each
question, so picking one is enough.

| Provider | What Halcyon does |
| --- | --- |
| `lmstudio` | Starts LM Studio's server (`lms server start`) if it is off, and loads the model (`lms load`) if none is loaded. Needs LM Studio's `lms` command, which its installer puts in `~/.lmstudio/bin`. |
| `hypernix` | Starts HyperNix's runtime, `hnx runtime serve MODEL.gguf`, with a model from `~/.hypernix/models` (the newest, or the one you name), sub-bit models included. It stays running for the next question. |
| `t1` | Asks a HyperNix T1 server (`POST /inference/chat`) with your T1 key, so the server's registry, quotas and audit log apply. |

```sh
halcyon assistant set provider lmstudio          # or hypernix
halcyon assistant set provider t1
halcyon assistant set t1Server http://127.0.0.1:8000
halcyon assistant key t1 T1_...                  # or /key in the sidebar, on a T1 model
halcyon assistant models                         # what it found
```

Small local models often can't call tools. When a model refuses them, the
question is asked again without them, and the desktop actions stay off
for that conversation. T1 never gets tools: it only talks.

### When it doesn't speak

```sh
halcyon assistant test-voice    # speaks with each voice in turn, and says why one fails
halcyon assistant test-mic      # records 3 seconds and plays them back
```

PipeWire 1.2 changed `pw-play -` and `pw-record -` to mean a sound file,
not raw audio. Arch ships a newer PipeWire, so older Halcyon played
nothing and recorded noise: no voice, no wake word, and garbled
transcription. Halcyon now asks `pw-cat` whether it takes `--raw` and
passes it when it does.

**What it can do.** Only these actions, each checked against a strict
schema before anything runs:

- open an app by name;
- set or change volume, mute speakers or the microphone, set brightness;
- control media;
- switch workspace;
- change the Halcyon theme or effects level;
- take a screenshot, lock the screen, or search the web.

It can't run commands or scripts, and nothing it says is ever given to a
shell. Turn actions off entirely with **Let it control the desktop**.

**The wake word** is spotted by a small offline Vosk model that only
knows the phrase. It keeps the microphone open while it's on, so it's
off by default.

**Settings > Halcyon > Assistant** covers the provider, wake word, spoken
replies, desktop control and recognition accuracy. Anything else:

```sh
halcyon assistant set model claude-sonnet-5   # or any model your provider offers
halcyon assistant set provider openai && halcyon assistant set endpoint http://localhost:8080/v1
halcyon assistant ask "what's on workspace 3?"  # typed, prints the reply
```

It keeps a few minutes of conversation, so follow-ups work, and logs to
`~/.local/state/halcyon/assistant.log`.
