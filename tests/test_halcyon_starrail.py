"""The Star Rail character list: parsing, validation and the banner command."""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dots", ".config", "hypr", "hyprland", "halcyon"))

import starrail  # noqa: E402

INDEX = {
    "1001": {"id": "1001", "name": "March 7th", "element": "Ice", "path": "Knight", "rarity": 4},
    "8001": {"id": "8001", "name": "{NICKNAME}", "element": "Physical", "path": "Warrior", "rarity": 4},
    "1307": {"id": "1307", "name": "Black Swan", "element": "Wind", "path": "Warlock", "rarity": 5},
}


class TestParsing(unittest.TestCase):
    def test_a_good_index_yields_every_usable_character(self) -> None:
        characters = starrail.parse_index(json.dumps(INDEX).encode())
        self.assertEqual(set(characters), {"1001", "1307"})

    def test_the_player_placeholder_is_never_listed(self) -> None:
        characters = starrail.parse_index(json.dumps(INDEX).encode())
        self.assertNotIn("8001", characters)

    def test_a_document_that_is_not_an_index_is_refused(self) -> None:
        for raw in (b"<html>", b"[]", b"{}"):
            with self.assertRaises(starrail.StarRailError):
                starrail.parse_index(raw)

    def test_only_png_data_is_accepted_as_a_portrait(self) -> None:
        png = starrail.PNG_SIGNATURE + b"\x00" * 16
        self.assertEqual(starrail.validate_portrait(png), png)
        with self.assertRaises(starrail.StarRailError):
            starrail.validate_portrait(b"<!doctype html>")

    def test_an_unknown_element_has_no_accent(self) -> None:
        self.assertIsNone(starrail.Character("1", "New", "Void", "Mage", 4).accent)


if __name__ == "__main__":
    unittest.main()
