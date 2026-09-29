"""Tests for the voice assistant: everything that doesn't need a microphone,
speakers or network. Run: python3 -m unittest discover -s tests"""

import array
import importlib.util
import json
import math
import random
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon/assistant"))

from halcyon_assistant import actions, audio, config, conversation, providers, wake  # noqa: E402


def frame(level, seed=0):
    rng = random.Random(seed)
    n = audio.FRAME_BYTES // 2
    return array.array("h", [int(level * math.sin(i / 3) + rng.gauss(0, 40)) for i in range(n)]).tobytes()


class EndOfSpeechTest(unittest.TestCase):
    def test_ends_after_silence_following_speech(self):
        detector = audio.EndOfSpeech(silence_ms=900)
        states = [detector.feed(frame(60, i)) for i in range(20)]
        states += [detector.feed(frame(3000, i)) for i in range(40)]
        states += [detector.feed(frame(60, i)) for i in range(40)]
        done = states.index("done")
        self.assertEqual(done, 20 + 40 + 900 // audio.FRAME_MS - 1)
        self.assertGreater(len(detector.buffer), 40 * audio.FRAME_BYTES)

    def test_hears_speech_that_starts_immediately(self):
        # People start talking as they press the key: the first frames are
        # speech, not room noise, and must not raise the threshold past it.
        detector = audio.EndOfSpeech()
        states = [detector.feed(frame(4000, i)) for i in range(30)]
        states += [detector.feed(frame(60, i)) for i in range(40)]
        self.assertIn("done", states)
        self.assertGreaterEqual(len(detector.buffer), 30 * audio.FRAME_BYTES)

    def test_a_noisy_room_is_not_speech(self):
        detector = audio.EndOfSpeech(wait_ms=3000)
        states = [detector.feed(frame(1200, i)) for i in range(150)]
        self.assertEqual(states[-1], "timeout")

    def test_gives_up_when_nobody_speaks(self):
        detector = audio.EndOfSpeech(wait_ms=3000)
        states = [detector.feed(frame(60, i)) for i in range(200)]
        self.assertIn("timeout", states)
        self.assertNotIn("speech", states)

    def test_stops_at_max_length(self):
        detector = audio.EndOfSpeech(max_ms=1500)
        states = [detector.feed(frame(4000, i)) for i in range(100)]
        self.assertEqual(states.index("done"), 1500 // audio.FRAME_MS - 1)


class ActionsTest(unittest.TestCase):
    def test_every_action_has_a_valid_schema_and_a_plan(self):
        samples = {"open_app": None, "set_volume": {"percent": 40}, "change_volume": {"delta": -5},
                   "toggle_mute": {"device": "microphone"}, "set_brightness": {"percent": 70},
                   "media": {"command": "next"}, "switch_workspace": {"number": 3},
                   "windows": {"command": "hide_others"},
                   "apply_theme": {"theme": "hsr"}, "set_effects": {"level": "light"},
                   "screenshot": {}, "lock_screen": {}, "web_search": {"query": "weather"}}
        self.assertEqual(set(samples), set(actions.ACTIONS))
        for name, spec in actions.ACTIONS.items():
            schema = spec["parameters"]
            self.assertFalse(schema["additionalProperties"])
            self.assertTrue(set(schema["required"]) <= set(schema["properties"]))
            if samples[name] is not None:
                commands, result = actions.plan(name, samples[name])
                self.assertTrue(commands and all(isinstance(c, list) for c in commands))
                self.assertIsInstance(result, str)

    def test_workspace_and_window_plans_use_lua_dispatchers(self):
        commands, _ = actions.plan("switch_workspace", {"number": 3})
        self.assertEqual(commands, [["hyprctl", "dispatch", "hl.dsp.focus({ workspace = 3 })"]])
        commands, _ = actions.plan("windows", {"command": "restore_all"})
        self.assertEqual(commands, [[str(actions.WINDOWS_TOOL), "restore", "--all"]])
        self.assertTrue(actions.WINDOWS_TOOL.is_file())

    def test_rejects_anything_outside_the_schema(self):
        bad = [("set_volume", {"percent": 101}), ("set_volume", {"percent": True}),
               ("set_volume", {}), ("media", {"command": "rm -rf"}), ("run_shell", {"cmd": "x"}),
               ("web_search", {"query": "x" * 500}), ("lock_screen", {"now": True})]
        for name, args in bad:
            with self.assertRaises(actions.ActionError, msg=(name, args)):
                actions.plan(name, args)

    def test_no_argument_reaches_a_shell(self):
        # Only the fixed screenshot script uses a shell, and it takes no input.
        _, result = actions.plan("web_search", {"query": "a; rm -rf ~"})
        commands, _ = actions.plan("web_search", {"query": "a; rm -rf ~"})
        self.assertEqual(commands[0][0], "xdg-open")
        self.assertNotIn(" ", commands[0][1])
        self.assertIn("rm", result)

    def test_themes_offered_are_the_themes_that_exist(self):
        shipped = {p.stem for p in (ROOT / "dots/.config/hypr/hyprland/halcyon/themes").glob("*.json")}
        self.assertEqual(set(actions.THEMES), shipped)

    def test_find_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "org.mozilla.firefox.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Firefox\nGenericName=Web Browser\n")
            (d / "kitty.desktop").write_text("[Desktop Entry]\nType=Application\nName=kitty\n")
            (d / "secret.desktop").write_text("[Desktop Entry]\nType=Application\nName=Secret\nNoDisplay=true\n")
            (d / "broken.desktop").write_text("not an ini file at all\x00")
            self.assertEqual(actions.find_app("Firefox", [d]), "org.mozilla.firefox")
            self.assertEqual(actions.find_app("browser", [d]), "org.mozilla.firefox")
            self.assertEqual(actions.find_app("terminal", [d]), "kitty")
            self.assertIsNone(actions.find_app("secret", [d]))
            self.assertIsNone(actions.find_app("photoshop", [d]))


class FakePost:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    def __call__(self, url, body, headers, timeout=90):
        self.requests.append((url, body, headers))
        return self.replies.pop(0)


HISTORY = [
    {"role": "user", "text": "volume to 30"},
    {"role": "assistant", "text": "", "calls": [{"id": "c1", "name": "set_volume", "args": {"percent": 30}}],
     "raw": None},
    {"role": "tool", "id": "c1", "name": "set_volume", "result": "volume 30%"},
]


class ProvidersTest(unittest.TestCase):
    def test_openai_compatible(self):
        post = FakePost({"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "x", "type": "function", "function": {"name": "media", "arguments": '{"command": "next"}'}}]}}]})
        answer = providers.OpenAICompatible("m", "https://api.example/v1/", "KEY", post=post).chat(
            HISTORY, "sys", actions.ACTIONS)
        url, body, headers = post.requests[0]
        self.assertEqual(url, "https://api.example/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer KEY")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user", "assistant", "tool"])
        self.assertEqual(json.loads(body["messages"][2]["tool_calls"][0]["function"]["arguments"]), {"percent": 30})
        self.assertEqual(answer["calls"], [{"id": "x", "name": "media", "args": {"command": "next"}}])

    def test_ollama_uses_object_arguments_and_makes_ids(self):
        post = FakePost({"message": {"content": "Done.", "tool_calls": [
            {"function": {"name": "lock_screen", "arguments": {}}}]}})
        answer = providers.Ollama("llama3.2", "http://localhost:11434", post=post).chat(HISTORY, "sys", actions.ACTIONS)
        url, body, _ = post.requests[0]
        self.assertTrue(url.endswith("/api/chat"))
        self.assertFalse(body["stream"])
        self.assertEqual(body["messages"][2]["tool_calls"][0]["function"]["arguments"], {"percent": 30})
        self.assertTrue(answer["calls"][0]["id"].startswith("call_"))

    def test_gemini_echoes_parts_and_strips_unsupported_schema(self):
        parts = [{"functionCall": {"name": "screenshot", "args": {}}, "thoughtSignature": "abc"}]
        post = FakePost({"candidates": [{"content": {"parts": parts}}]})
        gemini = providers.Gemini("gemini-2.5-flash", "KEY", post=post)
        answer = gemini.chat(HISTORY[:1], "sys", actions.ACTIONS)
        url, body, headers = post.requests[0]
        self.assertIn("gemini-2.5-flash:generateContent", url)
        self.assertEqual(headers["x-goog-api-key"], "KEY")
        self.assertNotIn("additionalProperties", json.dumps(body["tools"]))
        self.assertEqual(answer["raw"], parts)
        history = HISTORY[:1] + [{"role": "assistant", "text": "", "calls": answer["calls"], "raw": answer["raw"]},
                                 {"role": "tool", "id": answer["calls"][0]["id"], "name": "screenshot", "result": "ok"}]
        contents = gemini.contents(history)
        self.assertEqual(contents[1]["parts"][0]["thoughtSignature"], "abc")
        self.assertIn("functionResponse", contents[2]["parts"][0])

    def test_claude_groups_tool_results_and_echoes_raw_content(self):
        raw = [{"type": "thinking", "thinking": "", "signature": "s"},
               {"type": "tool_use", "id": "t1", "name": "set_volume", "input": {"percent": 30}},
               {"type": "tool_use", "id": "t2", "name": "media", "input": {"command": "next"}}]
        history = [HISTORY[0], {"role": "assistant", "text": "", "calls": [], "raw": raw},
                   {"role": "tool", "id": "t1", "name": "set_volume", "result": "ok"},
                   {"role": "tool", "id": "t2", "name": "media", "result": "error: playerctl is not installed"}]
        messages = providers.Claude.messages(history)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user"])
        self.assertIs(messages[1]["content"], raw)
        self.assertEqual([b["tool_use_id"] for b in messages[2]["content"]], ["t1", "t2"])
        self.assertTrue(messages[2]["content"][1]["is_error"])


class ClaudeCodeTest(unittest.TestCase):
    """The Claude Pro/Max provider, which runs Anthropic's Claude Code CLI."""

    class Run:
        def __init__(self, *outputs):
            self.outputs = list(outputs)
            self.calls = []

        def __call__(self, argv, **kwargs):
            self.calls.append((argv, kwargs))
            stdout, stderr = self.outputs.pop(0)

            class Done:
                pass
            done = Done()
            done.stdout, done.stderr, done.returncode = stdout, stderr, 0
            return done

    def test_command_line_locks_it_down_to_halcyon_actions(self):
        run = self.Run((json.dumps({"result": "Done.", "session_id": "s1", "is_error": False}), ""))
        provider = providers.ClaudeCode(run=run, workdir=tempfile.mkdtemp())
        with unittest.mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-should-not-be-used",
                                                     "HYPRLAND_INSTANCE_SIGNATURE": "abc"}):
            answer = provider.chat([{"role": "user", "text": "mute"}], "be brief", actions.ACTIONS)
        argv, kwargs = run.calls[0]
        self.assertEqual(argv[:4], ["claude", "-p", "--output-format", "json"])
        # No built-in tools, only our MCP server, only our actions allowed.
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", argv)
        allowed = argv[argv.index("--allowedTools") + 1:argv.index("--")]
        self.assertEqual(allowed, [f"mcp__halcyon__{n}" for n in actions.ACTIONS])
        mcp = json.loads(argv[argv.index("--mcp-config") + 1])["mcpServers"]["halcyon"]
        self.assertEqual(mcp["args"], ["-m", "halcyon_assistant.mcp_server"])
        self.assertEqual(mcp["env"]["HYPRLAND_INSTANCE_SIGNATURE"], "abc")
        self.assertEqual(argv[-2:], ["--", "mute"])
        self.assertNotIn("--model", argv)
        # The plan is the point: an API key in the environment must not win.
        self.assertNotIn("ANTHROPIC_API_KEY", kwargs["env"])
        self.assertEqual(answer, {"text": "Done.", "calls": [], "raw": None})

    def test_follow_ups_resume_the_session_and_new_conversations_do_not(self):
        reply = json.dumps({"result": "Ok.", "session_id": "s1"})
        run = self.Run((reply, ""), (reply, ""), (reply, ""))
        provider = providers.ClaudeCode(run=run, workdir=tempfile.mkdtemp())
        first = [{"role": "user", "text": "hi"}]
        provider.chat(first, "", {})
        provider.chat(first + [{"role": "assistant", "text": "Ok."}, {"role": "user", "text": "and?"}], "", {})
        provider.chat([{"role": "user", "text": "new topic"}], "", {})
        self.assertNotIn("--resume", run.calls[0][0])
        self.assertEqual(run.calls[1][0][run.calls[1][0].index("--resume") + 1], "s1")
        self.assertNotIn("--resume", run.calls[2][0])

    def test_without_actions_it_gets_no_tools(self):
        run = self.Run((json.dumps({"result": "Hi."}), ""))
        providers.ClaudeCode(run=run, workdir=tempfile.mkdtemp()).chat([{"role": "user", "text": "hi"}], "", {})
        argv = run.calls[0][0]
        self.assertNotIn("--mcp-config", argv)
        self.assertNotIn("--allowedTools", argv)

    def test_errors_explain_what_to_do(self):
        cases = [(("", "Not logged in · Please run /login"), "halcyon assistant login"),
                 ((json.dumps({"result": "Login expired", "is_error": True}), ""), "expired"),
                 ((json.dumps({"result": "overloaded", "is_error": True}), ""), "overloaded")]
        for output, expected in cases:
            provider = providers.ClaudeCode(run=self.Run(output), workdir=tempfile.mkdtemp())
            with self.assertRaises(providers.ProviderError) as caught:
                provider.chat([{"role": "user", "text": "x"}], "", {})
            self.assertIn(expected, str(caught.exception))


class McpServerTest(unittest.TestCase):
    def test_handshake_list_and_call(self):
        from halcyon_assistant import mcp_server
        init = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", init["result"]["capabilities"])
        self.assertIsNone(mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        listed = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        self.assertEqual({t["name"] for t in listed}, set(actions.ACTIONS))
        called = mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                    "params": {"name": "set_volume", "arguments": {"percent": 20}}},
                                   run=lambda name, args: f"ran {name} {args['percent']}")
        self.assertEqual(called["result"]["content"][0]["text"], "ran set_volume 20")
        self.assertFalse(called["result"]["isError"])
        unknown = mcp_server.handle({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
        self.assertEqual(unknown["error"]["code"], -32601)


class ConversationTest(unittest.TestCase):
    class Scripted:
        def __init__(self, *answers):
            self.answers = list(answers)
            self.calls = 0

        def chat(self, history, system, tools):
            self.calls += 1
            return self.answers.pop(0)

    def test_runs_actions_then_replies(self):
        provider = self.Scripted({"text": "", "calls": [{"id": "1", "name": "set_volume", "args": {"percent": 5}}]},
                                 {"text": "Quieter now.", "calls": []})
        ran = []
        reply = conversation.Conversation(provider).ask("quieter", run_action=lambda n, a: ran.append(n) or "ok")
        self.assertEqual(reply, "Quieter now.")
        self.assertEqual(ran, ["set_volume"])

    def test_stops_runaway_tool_loops(self):
        loop = {"text": "", "calls": [{"id": "1", "name": "lock_screen", "args": {}}]}
        provider = self.Scripted(*[dict(loop) for _ in range(10)])
        reply = conversation.Conversation(provider).ask("x", run_action=lambda n, a: "ok")
        self.assertEqual(provider.calls, conversation.MAX_TOOL_ROUNDS)
        self.assertIn("too many steps", reply)

    def test_actions_can_be_turned_off(self):
        provider = self.Scripted({"text": "", "calls": [{"id": "1", "name": "lock_screen", "args": {}}]},
                                 {"text": "I can't do that right now.", "calls": []})
        ran = []
        conversation.Conversation(provider, allow_actions=False).ask("lock", run_action=lambda n, a: ran.append(n))
        self.assertEqual(ran, [])

    def test_forgets_after_a_while_and_on_errors(self):
        now = [0.0]
        provider = self.Scripted({"text": "Hi.", "calls": []}, {"text": "Hello again.", "calls": []})
        chat = conversation.Conversation(provider, clock=lambda: now[0])
        chat.ask("hi")
        self.assertEqual(len(chat.history), 2)
        now[0] += conversation.MEMORY_SECONDS + 1
        chat.ask("hello")
        self.assertEqual([t["text"] for t in chat.history if t["role"] == "user"], ["hello"])

        class Failing:
            def chat(self, *a):
                raise providers.ProviderError("down")
        chat.provider = Failing()
        with self.assertRaises(providers.ProviderError):
            chat.ask("again")
        self.assertEqual([t["text"] for t in chat.history if t["role"] == "user"], ["hello"])


class ConfigTest(unittest.TestCase):
    def test_bad_values_fall_back_to_defaults(self):
        s = config.settings({"halcyon": {"assistant": {"provider": "skynet", "speak": "yes", "wakeWord": True,
                                                       "speechModel": "huge"}}})
        self.assertEqual((s["provider"], s["speak"], s["wakeWord"], s["speechModel"]), ("auto", True, True, "base"))

    def test_settings_page_and_defaults_agree(self):
        spec = importlib.util.spec_from_file_location("shellcfg", ROOT / "scripts/check-theme-shell-config.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        options = module.option_tree()
        qml = {k.rsplit(".", 1)[1]: v for k, v in options.items() if k.startswith("halcyon.assistant.")}
        self.assertEqual(set(qml), set(config.DEFAULTS))
        types = {"bool": bool, "string": str}
        for key, default in config.DEFAULTS.items():
            self.assertIs(types[qml[key]], type(default), key)

    def test_wake_phrase_matching(self):
        self.assertTrue(wake.matches("ok hey halcyon", "hey halcyon"))
        self.assertFalse(wake.matches("hey", "hey halcyon"))
        self.assertFalse(wake.matches("halcyon hey", "hey halcyon"))


if __name__ == "__main__":
    unittest.main()
