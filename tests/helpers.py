"""Shared fixtures: a Halcyon that writes to a temporary directory."""

from __future__ import annotations

import importlib
import os
import tempfile
import unittest


class IsolatedHalcyon(unittest.TestCase):
    """A test case with its own config, state and cache directories.

    Halcyon's paths are resolved at import time, so the environment has
    to be set before the modules load — and reloaded between test classes
    that use different directories.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name

        self._saved = {
            key: os.environ.get(key)
            for key in (
                "HALCYON_CONFIG_DIR",
                "HALCYON_GENERATED_DIR",
                "HALCYON_STATE_DIR",
                "HALCYON_CACHE_DIR",
                "HALCYON_DATA_DIR",
                "XDG_RUNTIME_DIR",
            )
        }

        os.environ["HALCYON_CONFIG_DIR"] = os.path.join(root, "config")
        os.environ["HALCYON_GENERATED_DIR"] = os.path.join(root, "config", "generated")
        os.environ["HALCYON_STATE_DIR"] = os.path.join(root, "state")
        os.environ["HALCYON_CACHE_DIR"] = os.path.join(root, "cache")
        os.environ["HALCYON_DATA_DIR"] = os.path.join(root, "share")
        os.environ["XDG_RUNTIME_DIR"] = os.path.join(root, "run")
        os.makedirs(os.environ["XDG_RUNTIME_DIR"], exist_ok=True)

        from halcyon import paths

        importlib.reload(paths)
        paths.ensure_dirs()
        self.root = root
        self.paths = paths

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        from halcyon import paths

        importlib.reload(paths)
        self._tmp.cleanup()
