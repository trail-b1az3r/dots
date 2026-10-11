"""The Star Rail character cache: what is trusted, and when the network is used."""

from __future__ import annotations

import json
import pathlib
import random
import tempfile
import unittest
from unittest import mock

from halcyon import paths, starrail

INDEX = {
    "1001": {"id": "1001", "name": "March 7th", "element": "Ice", "path": "Knight", "rarity": 4},
    "1307": {"id": "1307", "name": "Black Swan", "element": "Wind", "path": "Warlock", "rarity": 5},
    "1100": {"id": "1100", "name": "Bailu", "element": "Thunder", "path": "Priest", "rarity": 5},
}
PNG = starrail.PNG_SIGNATURE + b"\x00" * 64


def _raw(data) -> bytes:
    return json.dumps(data).encode("utf-8")


class _Isolated(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        patch = mock.patch.object(paths, "CACHE_DIR", pathlib.Path(self._dir.name))
        patch.start()
        self.addCleanup(patch.stop)


class TestParsing(unittest.TestCase):
    def test_a_good_index_yields_every_usable_character(self) -> None:
        characters = starrail.parse_index(_raw(INDEX))
        self.assertEqual(set(characters), {"1001", "1307", "1100"})
        self.assertEqual(characters["1307"].name, "Black Swan")
        self.assertEqual(characters["1307"].accent, starrail.ELEMENT_ACCENTS["Wind"])

    def test_one_malformed_entry_does_not_hide_the_rest(self) -> None:
        data = dict(INDEX, broken={"id": "abc", "name": "x", "element": "Ice", "path": "Mage"},
                    nameless={"id": "9", "name": "  ", "element": "Ice", "path": "Mage"},
                    notadict="oops")
        self.assertEqual(len(starrail.parse_index(_raw(data))), 3)

    def test_a_document_that_is_not_an_index_is_refused(self) -> None:
        for raw in (b"<html>", b"[]", b"{}", _raw({"x": {"name": "no id"}})):
            with self.assertRaises(starrail.StarRailError, msg=raw):
                starrail.parse_index(raw)

    def test_an_unknown_element_has_no_accent_rather_than_a_guess(self) -> None:
        char = starrail.Character("1", "New", "Void", "Mage", 4)
        self.assertIsNone(char.accent)

    def test_only_png_data_is_accepted_as_a_portrait(self) -> None:
        self.assertEqual(starrail.validate_portrait(PNG), PNG)
        with self.assertRaises(starrail.StarRailError):
            starrail.validate_portrait(b"<!doctype html>")
        with self.assertRaises(starrail.StarRailError):
            starrail.validate_portrait(PNG + b"x" * starrail.MAX_PORTRAIT_BYTES)


class TestCache(_Isolated):
    def test_a_recent_index_is_not_downloaded_again(self) -> None:
        calls: list[str] = []

        def download(url, limit):
            calls.append(url)
            return _raw(INDEX)

        starrail.refresh(download=download)
        starrail.refresh(download=download)
        self.assertEqual(len(calls), 1)

    def test_an_old_index_is_refreshed(self) -> None:
        starrail.refresh(download=lambda url, limit: _raw(INDEX))
        later = starrail.time.time() + starrail.MAX_AGE_SECONDS + 60
        calls: list[str] = []
        starrail.refresh(now=lambda: later, download=lambda url, limit: calls.append(url) or _raw(INDEX))
        self.assertEqual(len(calls), 1)

    def test_a_failed_download_keeps_the_old_index(self) -> None:
        starrail.refresh(download=lambda url, limit: _raw(INDEX))
        later = starrail.time.time() + starrail.MAX_AGE_SECONDS + 60

        def offline(url, limit):
            raise starrail.StarRailError("could not download characters.json: URLError")

        with self.assertRaises(starrail.StarRailError):
            starrail.refresh(now=lambda: later, download=offline)
        self.assertEqual(len(starrail.load_characters()), 3)

    def test_the_portrait_is_fetched_once_then_read_from_disk(self) -> None:
        starrail.refresh(download=lambda url, limit: _raw(INDEX))
        char = starrail.load_characters()["1307"]
        calls: list[str] = []

        def download(url, limit):
            calls.append(url)
            return PNG

        first = starrail.portrait(char, download=download)
        second = starrail.portrait(char, download=download)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)
        self.assertTrue(pathlib.Path(first).read_bytes().startswith(starrail.PNG_SIGNATURE))

    def test_the_next_character_is_never_the_same_one(self) -> None:
        characters = starrail.parse_index(_raw(INDEX))
        starrail.refresh(download=lambda url, limit: _raw(INDEX))
        rng = random.Random(3)
        last = None
        for _ in range(20):
            chosen = starrail.choose_next(characters, rng=rng)
            self.assertNotEqual(chosen, last)
            last = chosen

    def test_status_reports_nothing_chosen_before_the_first_next(self) -> None:
        starrail.refresh(download=lambda url, limit: _raw(INDEX))
        payload = starrail.status()
        self.assertEqual(payload["characters"], 3)
        self.assertIsNone(payload["current"])

    def test_nothing_is_fetched_by_reading_the_status(self) -> None:
        with mock.patch.object(starrail, "_download", side_effect=AssertionError("network")):
            starrail.status()
            starrail.load_characters()


class TestConsent(unittest.TestCase):
    def test_the_star_rail_fetch_is_off_by_default(self) -> None:
        from halcyon import settings as settings_module

        defaults = settings_module.defaults()
        self.assertFalse(defaults["starRail"]["fetchCharacters"])
        self.assertFalse(defaults["starRail"]["accentFromCharacter"])


if __name__ == "__main__":
    unittest.main()
