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
   **Gemini**, a local **Ollama** model, or any **OpenAI-compatible**
   server. *Auto* picks an Anthropic API key if set, then your Claude
   plan, then Gemini, then Ollama. Keys are shared with end-4's AI sidebar, so one entered
   there works here too.
4. The reply appears in a notification and is spoken, with Piper if you
   set it up, otherwise espeak-ng.

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
