"""Spotlight: fuzzy matching, the calculator, and provider isolation."""

from __future__ import annotations

import unittest

from halcyon import search
from halcyon.search import calc, match

from .helpers import IsolatedHalcyon


class TestMatching(unittest.TestCase):
    def test_accents_are_folded(self) -> None:
        self.assertEqual(match.normalise("Café"), "cafe")
        self.assertIsNotNone(match.score("cafe", "Café Player"))

    def test_exact_beats_prefix_beats_word_beats_substring(self) -> None:
        exact = match.score("files", "Files")
        prefix = match.score("fil", "Files")
        word = match.score("man", "File Manager")
        substring = match.score("ana", "File Manager")
        for value in (exact, prefix, word, substring):
            self.assertIsNotNone(value)
        assert exact and prefix and word and substring
        self.assertGreater(exact, prefix)
        self.assertGreater(prefix, word)
        self.assertGreater(word, substring)

    def test_acronyms_match(self) -> None:
        self.assertIsNotNone(match.subsequence_score("vsc", "visual studio code"))
        self.assertIsNone(match.subsequence_score("zzz", "visual studio code"))

    def test_shorter_names_win_a_tie(self) -> None:
        short = match.score("term", "Terminal")
        long = match.score("term", "Terminal Emulator Preferences")
        assert short and long
        self.assertGreater(short, long)

    def test_no_match_is_none_not_zero(self) -> None:
        self.assertIsNone(match.score("qqqq", "Files", "File manager"))

    def test_an_empty_query_matches_everything(self) -> None:
        self.assertEqual(match.score("", "Files"), 0.0)

    def test_the_first_field_outweighs_the_rest(self) -> None:
        name_hit = match.score("code", "Code", "A text editor")
        comment_hit = match.score("code", "Editor", "Code editing")
        assert name_hit and comment_hit
        self.assertGreater(name_hit, comment_hit)


class TestCalculator(unittest.TestCase):
    def test_arithmetic(self) -> None:
        self.assertEqual(calc.calculate("2+2"), 4)
        self.assertEqual(calc.calculate("(3 + 5) * 2"), 16)
        self.assertAlmostEqual(calc.calculate("10 / 4") or 0, 2.5)
        self.assertEqual(calc.calculate("2^10"), 1024)
        self.assertEqual(calc.calculate("10 mod 3"), 1)

    def test_percentages(self) -> None:
        self.assertAlmostEqual(calc.calculate("15% of 80") or 0, 12.0)

    def test_functions_and_constants(self) -> None:
        self.assertAlmostEqual(calc.calculate("sqrt(16)") or 0, 4.0)
        self.assertAlmostEqual(calc.calculate("round(pi, 2)") or 0, 3.14)

    def test_plain_text_is_not_a_calculation(self) -> None:
        for text in ("firefox", "", "hello world", "42"):
            self.assertIsNone(calc.calculate(text), msg=text)

    def test_nothing_outside_arithmetic_is_evaluated(self) -> None:
        # The calculator takes whatever is typed into Spotlight, so it
        # must never reach the interpreter's own namespace.
        hostile = [
            "__import__('os').system('id')",
            "open('/etc/passwd').read()",
            "(lambda: 1)()",
            "[x for x in range(3)]",
            "{'a': 1}['a']",
            "os.getcwd()",
            "1 if True else 2",
            "print(1)",
        ]
        for expression in hostile:
            self.assertIsNone(calc.calculate(expression), msg=expression)

    def test_expensive_expressions_are_refused_not_run(self) -> None:
        # 9**9**9 hangs a naive evaluator long enough to look like a crash.
        self.assertIsNone(calc.calculate("9**9**9"))

    def test_division_by_zero_is_not_an_answer(self) -> None:
        self.assertIsNone(calc.calculate("1/0"))

    def test_number_formatting(self) -> None:
        self.assertEqual(calc.format_number(1000), "1,000")
        self.assertEqual(calc.format_number(2.5), "2.5")
        self.assertEqual(calc.format_number(4.0), "4")


class TestConversion(IsolatedHalcyon):
    def test_length(self) -> None:
        result = calc.convert("10 km in miles")
        assert result
        self.assertAlmostEqual(result["value"], 6.2137, places=3)

    def test_temperature(self) -> None:
        result = calc.convert("100 c in f")
        assert result
        self.assertAlmostEqual(result["value"], 212.0, places=3)

    def test_mismatched_dimensions_say_so(self) -> None:
        result = calc.convert("10 kg in metres")
        assert result
        self.assertEqual(result["kind"], "error")

    def test_currency_stays_offline_unless_allowed(self) -> None:
        # Nothing should reach the network on a keystroke unless the user
        # turned web access on — and saying so beats a blank card.
        import urllib.request

        opened = []
        original = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: opened.append(a) # type: ignore[assignment]
        try:
            result = calc.convert("10 usd in eur", allow_network=False)
        finally:
            urllib.request.urlopen = original # type: ignore[assignment]

        self.assertEqual(opened, [])
        assert result
        self.assertEqual(result["kind"], "currency")
        self.assertIn("web access", result["detail"])

    def test_nonsense_is_not_a_conversion(self) -> None:
        self.assertIsNone(calc.convert("firefox"))


class TestOrchestration(IsolatedHalcyon):
    def setUp(self) -> None:
        super().setUp()
        from halcyon import settings as settings_module

        self.settings = settings_module.defaults()

    def test_a_calculation_produces_a_result(self) -> None:
        results = search.search("2+2", self.settings, providers=["calculator"])
        self.assertTrue(results)
        self.assertIn("4", results[0].title)

    def test_results_are_unique_and_ranked(self) -> None:
        results = search.search("e", self.settings, limit=25)
        ids = [r.id for r in results]
        self.assertEqual(len(ids), len(set(ids)))
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_the_limit_is_respected(self) -> None:
        results = search.search("a", self.settings, limit=5)
        self.assertLessEqual(len(results), 5)

    def test_one_broken_provider_does_not_break_the_search(self) -> None:
        def explode(_query: str, _settings: dict, _limit: int):
            raise RuntimeError("boom")

        search.REGISTRY["test.broken"] = explode
        try:
            results = search.search(
                "2+2", self.settings, providers=["test.broken", "calculator"]
            )
            self.assertTrue(results, "a failing provider silenced the others")
        finally:
            search.REGISTRY.pop("test.broken", None)

    def test_disabling_a_provider_in_settings_takes_effect(self) -> None:
        settings = dict(self.settings)
        settings["search"] = dict(settings.get("search", {}))
        settings["search"]["providers"] = {"calculator": False}
        self.assertNotIn("calculator", search.enabled_providers(settings))

    def test_an_empty_query_does_not_raise(self) -> None:
        search.search("", self.settings)


if __name__ == "__main__":
    unittest.main()
