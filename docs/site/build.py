#!/usr/bin/env python3
"""Builds the Halcyon docs site (GitHub Pages) from the Markdown in docs/.

    python3 docs/site/build.py [--out _site] [--base-url URL]

The pages are the same files GitHub shows in the repository, so they stay the one source. Links between pages are
rewritten to the built pages, images in docs/assets are copied, and links to anything else in the repository go to
it on GitHub. Needs Python 3.9+ and the `markdown` package (pip install markdown).

    docs/halcyon/README.md          -> index.html
    docs/halcyon/<page>.md          -> <page>.html
    docs/illogical-impulse/<p>.md   -> illogical-impulse/<p>.html   (README.md -> index.html)
    docs/assets/*                   -> assets/*
"""

from __future__ import annotations

import argparse
import html
import os
import posixpath
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

import markdown
from markdown.extensions.toc import slugify_unicode

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SITE_FILES = Path(__file__).resolve().parent
REPO_URL = "https://github.com/trail-b1az3r/dots"
BRANCH = "main"
WIKI_URL = "https://trail-b1az3r.github.io/hyprland-plus/"

# (source, output, title in the navigation). The order is the navigation's.
HALCYON_PAGES = [
    ("README.md", "index.html", "Overview"),
    ("install.md", "install.html", "Install"),
    ("themes.md", "themes.html", "Themes"),
    ("keybinds.md", "keybinds.html", "Keybinds"),
    ("hyprland-plus.md", "hyprland-plus.html", "hyprland-plus"),
    ("voice-assistant.md", "voice-assistant.html", "Voice assistant"),
    ("architecture.md", "architecture.html", "Architecture"),
    ("development.md", "development.html", "Development"),
]
II_PAGES = [
    ("README.md", "illogical-impulse/index.html", "Overview"),
    ("introduction.md", "illogical-impulse/introduction.html", "Introduction"),
    ("setup.md", "illogical-impulse/setup.html", "Setup"),
    ("usage.md", "illogical-impulse/usage.html", "Usage"),
    ("config.md", "illogical-impulse/config.html", "Config"),
    ("faq.md", "illogical-impulse/faq.html", "FAQ"),
    ("troubleshooting.md", "illogical-impulse/troubleshooting.html", "Troubleshooting"),
    ("credits.md", "illogical-impulse/credits.html", "Credits"),
]

LINK_RE = re.compile(r'(?P<attr>href|src)="(?P<url>[^"]+)"')


def pages() -> list[tuple[Path, str, str, str]]:
    """(source path, output path, nav title, section) for every page that exists."""
    out = []
    for section, folder, table in (("Halcyon", DOCS / "halcyon", HALCYON_PAGES),
                                   ("illogical-impulse", DOCS / "illogical-impulse", II_PAGES)):
        for name, target, title in table:
            if (folder / name).is_file():
                out.append((folder / name, target, title, section))
        # Pages added later still get built, at the end of their section.
        listed = {name for name, _target, _title in table}
        for extra in sorted(folder.glob("*.md")):
            if extra.name not in listed:
                prefix = "" if section == "Halcyon" else "illogical-impulse/"
                out.append((extra, f"{prefix}{extra.stem}.html", extra.stem.replace("-", " ").capitalize(), section))
    return out


def github_url(repo_path: str, is_dir: bool) -> str:
    return f"{REPO_URL}/{'tree' if is_dir else 'blob'}/{BRANCH}/{repo_path}".rstrip("/")


def rewrite_links(body: str, source: Path, target: str, by_source: dict[str, str], assets: set[str]) -> str:
    """Point links at built pages, copied assets, or GitHub."""
    here = posixpath.dirname(target)

    def relative(to: str) -> str:
        return posixpath.relpath(to, here or ".")

    def fix(match: re.Match) -> str:
        attr, url = match.group("attr"), html.unescape(match.group("url"))
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or url.startswith(("#", "mailto:")):
            return match.group(0)
        path, _, fragment = url.partition("#")
        if not path:
            return match.group(0)
        resolved = os.path.normpath(os.path.join(source.parent, path))
        repo_path = os.path.relpath(resolved, ROOT).replace(os.sep, "/")
        anchor = f"#{fragment}" if fragment else ""
        if repo_path in by_source:
            new = relative(by_source[repo_path]) + anchor
        elif repo_path.startswith("docs/assets/") and repo_path in assets:
            new = relative("assets/" + repo_path[len("docs/assets/"):])
        else:
            new = github_url(repo_path, Path(resolved).is_dir() or path.endswith("/")) + anchor
        return f'{attr}="{html.escape(new, quote=True)}"'

    return LINK_RE.sub(fix, body)


def render(text: str) -> tuple[str, list[dict], str]:
    """HTML, the table of contents, and the page's first heading."""
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc"],
                           extension_configs={"toc": {"slugify": slugify_unicode, "permalink": "#",
                                                      "permalink_class": "anchor", "toc_depth": "2-3"}})
    body = md.convert(text)
    # Tables written with an empty header row (| | |) get no header at all.
    body = re.sub(r"<thead>\s*<tr>(?:\s*<th[^>]*>\s*</th>)+\s*</tr>\s*</thead>", "", body)
    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else ""
    return body, md.toc_tokens, title


def toc_html(tokens: list[dict]) -> str:
    items = []
    for token in tokens:
        if token["level"] == 1:
            items.extend(toc_entries(token.get("children", [])))
        else:
            items.extend(toc_entries([token]))
    if not items:
        return ""
    return '<nav class="toc" aria-label="On this page"><p class="toc-title">On this page</p><ul>' + "".join(items) + "</ul></nav>"


def toc_entries(tokens: list[dict]) -> list[str]:
    out = []
    for token in tokens:
        name = html.escape(re.sub(r"<[^>]+>", "", html.unescape(token["name"])))
        cls = "toc-sub" if token["level"] >= 3 else ""
        out.append(f'<li class="{cls}"><a href="#{token["id"]}">{name}</a></li>')
        out.extend(toc_entries(token.get("children", [])))
    return out


def nav_html(all_pages, current: str) -> str:
    here = posixpath.dirname(current)
    sections: dict[str, list[str]] = {}
    for _source, target, title, section in all_pages:
        href = posixpath.relpath(target, here or ".")
        active = ' aria-current="page" class="active"' if target == current else ""
        sections.setdefault(section, []).append(f'<li><a href="{href}"{active}>{html.escape(title)}</a></li>')
    parts = []
    for section, links in sections.items():
        parts.append(f'<p class="nav-section">{html.escape(section)}</p><ul>{"".join(links)}</ul>')
    parts.append('<p class="nav-section">Elsewhere</p><ul>'
                 f'<li><a href="{WIKI_URL}">hyprland-plus wiki</a></li>'
                 f'<li><a href="{REPO_URL}">Repository</a></li></ul>')
    return "".join(parts)


def page_html(template: str, *, title: str, body: str, nav: str, toc: str, current: str, source: Path,
              base_url: str, is_home: bool) -> str:
    root = posixpath.relpath(".", posixpath.dirname(current) or ".")
    root = "" if root == "." else root + "/"
    edit = f"{REPO_URL}/edit/{BRANCH}/{os.path.relpath(source, ROOT).replace(os.sep, '/')}"
    hero = ""
    if is_home:
        hero = (f'<header class="hero"><img src="{root}assets/hero.jpg" alt="" width="1600" height="900">'
                '<div class="hero-text"><p class="eyebrow">A Hyprland desktop</p><h1>Halcyon</h1>'
                "<p>end-4's illogical-impulse, with hand-made themes, a voice assistant, and hyprland-plus underneath.</p>"
                f'<p class="hero-links"><a class="button" href="{root}install.html">Install</a>'
                f'<a class="button ghost" href="{root}themes.html">See the themes</a></p></div>'
                '<p class="hero-credit">Wallpaper: Red Sun, by Kenami, from Wallpaper Heaven</p></header>')
    canonical = f'<link rel="canonical" href="{base_url.rstrip("/")}/{current}">' if base_url else ""
    return (template.replace("{{title}}", html.escape(title))
            .replace("{{root}}", root)
            .replace("{{canonical}}", canonical)
            .replace("{{hero}}", hero)
            .replace("{{nav}}", nav)
            .replace("{{toc}}", toc)
            .replace("{{body}}", body)
            .replace("{{edit}}", edit)
            .replace("{{home_class}}", " home" if is_home else ""))


def build(out: Path, base_url: str = "") -> list[str]:
    all_pages = pages()
    by_source = {os.path.relpath(source, ROOT).replace(os.sep, "/"): target for source, target, _t, _s in all_pages}
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)

    assets = set()
    for asset in sorted((DOCS / "assets").glob("*")) if (DOCS / "assets").is_dir() else []:
        shutil.copy2(asset, out / "assets" / asset.name)
        assets.add(f"docs/assets/{asset.name}")
    for static in ("style.css", "site.js"):
        shutil.copy2(SITE_FILES / static, out / "assets" / static)
    make_hero(out / "assets" / "hero.jpg")

    template = (SITE_FILES / "template.html").read_text(encoding="utf-8")
    written = []
    for source, target, title, section in all_pages:
        text = source.read_text(encoding="utf-8")
        body, tokens, heading = render(text)
        body = rewrite_links(body, source, target, by_source, assets)
        page_title = f"{heading or title} · Halcyon" if target != "index.html" else "Halcyon: a Hyprland desktop"
        is_home = target == "index.html"
        if is_home:
            # The hero carries the title on the home page.
            body = re.sub(r"^<h1[^>]*>.*?</h1>\s*", "", body, count=1, flags=re.S)
        doc = page_html(template, title=page_title, body=body, nav=nav_html(all_pages, target), toc=toc_html(tokens),
                        current=target, source=source, base_url=base_url, is_home=is_home)
        path = out / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc, encoding="utf-8")
        written.append(target)
    (out / ".nojekyll").write_text("")
    (out / "404.html").write_text(page_html(template, title="Not found · Halcyon",
                                            body='<h1>Not found</h1><p>That page is not here. <a href="index.html">Back to the start</a>.</p>',
                                            nav=nav_html(all_pages, "404.html"), toc="", current="404.html",
                                            source=DOCS / "halcyon/README.md", base_url=base_url, is_home=False),
                                  encoding="utf-8")
    return written


def make_hero(path: Path) -> None:
    """The Red Sun wallpaper, cut to 16:9 and made small enough for the web."""
    wallpaper = ROOT / "dots/.config/hypr/hyprland/halcyon/themes/wallpapers/red-sun.jpg"
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(wallpaper, path)
        return
    with Image.open(wallpaper) as img:
        img = img.convert("RGB")
        img.thumbnail((1600, 900))
        img.save(path, quality=80, optimize=True, progressive=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "_site"))
    parser.add_argument("--base-url", default="https://trail-b1az3r.github.io/dots/")
    args = parser.parse_args(argv)
    written = build(Path(args.out), args.base_url)
    print(f"built {len(written)} pages into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
