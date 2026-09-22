#!/usr/bin/env python3
"""Check the sources against the oldest Python we claim to support.

The README says Python 3.9. Nothing else in the repository checks that,
and the failure mode is nasty: `from __future__ import annotations`
defers *annotations*, so `def f(x: int | None)` is fine on 3.9 — but a
type alias like

    Rule = tuple[re.Pattern[str], Callable[[...], Intent | None]]

is an ordinary assignment, evaluated at import, and `X | None` is a
TypeError before 3.10. The module imports fine on the developer's 3.11
and explodes on a user's 3.9, which is exactly the kind of thing CI
found after I had claimed the floor was safe.

Two checks:

* every file parses at the floor's grammar (`ast.parse` with
  `feature_version`), which catches match statements and the like;
* no `X | Y` outside an annotation, which catches the aliases.

Run with `--floor 3.10` to raise the floor after updating the README.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent.parent

#: Constructs that only exist after 3.9, by the version that added them.
LATER_THAN_39 = {
    "match statement": ast.Match,
}


def annotation_nodes(tree: ast.AST) -> set[int]:
    """Every node reachable from an annotation, by identity.

    Annotations are strings at runtime thanks to the __future__ import,
    so a union inside one is harmless however old the interpreter is.
    """
    found: set[int] = set()

    def mark(node: ast.AST | None) -> None:
        if node is not None:
            found.update(id(child) for child in ast.walk(node))

    for node in ast.walk(tree):
        mark(getattr(node, "annotation", None))
        mark(getattr(node, "returns", None))
        if isinstance(node, ast.arguments):
            for arg in (
                list(node.args) + list(node.kwonlyargs) + list(node.posonlyargs)
            ):
                mark(arg.annotation)
            if node.vararg is not None:
                mark(node.vararg.annotation)
            if node.kwarg is not None:
                mark(node.kwarg.annotation)
    return found


def looks_like_a_type(source: str) -> bool:
    """Distinguish `int | None` from `flags | BIT`.

    Bitwise-or on values is legitimate and common; a type union is not.
    The give-aways are `None`, a subscript, or both sides being names
    that start with a capital.
    """
    if "None" in source:
        return True
    if "[" in source:
        return True
    parts = [part.strip() for part in source.split("|")]
    return len(parts) > 1 and all(
        part[:1].isupper() or part.startswith('"') for part in parts if part
    )


def check(path: pathlib.Path, floor: tuple[int, int]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    try:
        tree = ast.parse(text, feature_version=floor)
    except SyntaxError as error:
        return [
            f"{path}:{error.lineno}: syntax not valid on Python "
            f"{floor[0]}.{floor[1]}: {error.msg}"
        ]

    if floor < (3, 10):
        annotations = annotation_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.BitOr):
                continue
            if id(node) in annotations:
                continue
            source = ast.get_source_segment(text, node) or ""
            if looks_like_a_type(source):
                problems.append(
                    f"{path}:{node.lineno}: `{source}` is evaluated at "
                    f"runtime and needs Python 3.10. Use Optional[...] or "
                    f"Union[...]."
                )

    for description, node_type in LATER_THAN_39.items():
        if floor >= (3, 10):
            break
        for node in ast.walk(tree):
            if isinstance(node, node_type):
                problems.append(
                    f"{path}:{node.lineno}: {description} needs Python 3.10"
                )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--floor", default="3.9",
        help="the oldest Python to check against (default: 3.9)",
    )
    parser.add_argument(
        "paths", nargs="*", default=[str(REPO / "src")],
        help="directories to check (default: src/)",
    )
    args = parser.parse_args()

    try:
        major, minor = (int(part) for part in args.floor.split("."))
    except ValueError:
        print(f"not a version: {args.floor}", file=sys.stderr)
        return 2
    floor = (major, minor)

    problems: list[str] = []
    count = 0
    for root in args.paths:
        for path in sorted(pathlib.Path(root).rglob("*.py")):
            count += 1
            problems.extend(check(path, floor))

    if problems:
        print(f"{len(problems)} problem(s) for Python {args.floor}:")
        for problem in problems:
            print("  " + problem)
        return 1

    print(f"{count} file(s) are valid on Python {args.floor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
