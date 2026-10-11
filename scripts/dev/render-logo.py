#!/usr/bin/env python3
"""Render assets/icons/halcyon.svg to the PNGs the shell loads.

Uses the system Chromium through Playwright, because it is the one SVG
renderer a development machine is most likely to already have. Nothing is
downloaded: the browser is taken from PLAYWRIGHT_BROWSERS_PATH or the
default location, and the run fails clearly if it is not there.
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ICONS = ROOT / "assets" / "icons"
SIZES = {"halcyon.png": 256, "halcyon-64.png": 64}


def render(svg_text: str, size: int, out: pathlib.Path) -> None:
    from playwright.sync_api import sync_playwright

    html = (
        '<html><body style="margin:0;background:transparent">'
        f'<div style="width:{size}px;height:{size}px">'
        + svg_text.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
        + "</div></body></html>"
    )
    executable = os.environ.get("HALCYON_CHROMIUM", "/opt/pw-browsers/chromium")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable if os.path.exists(executable) else None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(
            viewport={"width": size, "height": size}, device_scale_factor=1
        )
        page.set_content(html)
        page.screenshot(
            path=str(out),
            omit_background=True,
            clip={"x": 0, "y": 0, "width": size, "height": size},
        )
        browser.close()


def main() -> int:
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("Needs Playwright: pip install playwright", file=sys.stderr)
        return 2
    svg = (ICONS / "halcyon.svg").read_text(encoding="utf-8")
    for name, size in SIZES.items():
        render(svg, size, ICONS / name)
        print(f"wrote {ICONS / name} ({size} px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
