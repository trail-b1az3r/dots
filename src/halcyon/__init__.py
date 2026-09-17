"""Halcyon — a Liquid-Glass-inspired desktop environment for Hyprland.

This package is the non-visual half of Halcyon: it owns the settings
file, derives every theme artefact the shell reads, answers Spotlight
queries, brokers desktop actions for the AI assistant, and adapts to
whatever power-management and AI backends the machine happens to have.

It is deliberately written against the Python standard library alone.
The installer has to be able to run it on a machine where nothing has
been installed yet, and the Spotlight path has to start fast enough that
a keystroke feels instant.
"""

__version__ = "1.0.0"

# Bumped whenever settings.json needs migrating. `halcyon.settings`
# refuses to silently reinterpret a file from a newer schema.
SETTINGS_SCHEMA_VERSION = 1

__all__ = ["__version__", "SETTINGS_SCHEMA_VERSION"]
