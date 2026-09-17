"""Halcyon's test suite.

Run with:

    PYTHONPATH=src python3 -m unittest discover -s tests

The tests are deliberately narrow: they cover the logic that is easy to
get quietly wrong — colour maths, settings merging, the Lua and CSS
generators, the action allow-list, and the search providers — rather than
trying to exercise a compositor that is not running.
"""
