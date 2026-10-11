"""Window shapes: aspect ratios a window can be held to.

Hyprland has no "make this window 3:2" rule. What it has is a `size`
rule, evaluated against the window's monitor each time the window opens,
and a `keep_aspect_ratio` effect that preserves whatever ratio a window
had when a mouse resize began. A fixed shape is the two together: open
at exactly W:H, then keep it there while the user resizes.

Only floating windows can be held to a shape. A tiled window is sized by
the layout, which fills the space it is given, so a ratio rule on one
would either be ignored or fight the layout. Callers that want a shape
must float the window as well.

Everything here is pure — no files, no compositor — so the arithmetic
can be tested exactly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Shape:
    """A width:height ratio with a name a person would recognise."""

    width: int
    height: int
    description: str

    @property
    def ratio(self) -> float:
        return self.width / self.height


#: Named shapes. Add one and it is accepted by `settings set`, offered in
#: Settings, and covered by the tests without further wiring.
PRESETS: dict[str, Shape] = {
    # 2736 × 1824 pixels, which reduces to exactly 3:2.
    "surface-pro-5": Shape(3, 2, "Microsoft Surface Pro 5 (2736 × 1824)"),
}

#: The setting value that means "do not touch the window".
OFF = "off"

#: How much of the monitor the window may occupy, per axis. The window
#: is the largest 3:2 that fits inside this fraction of the screen, so
#: it never overflows a monitor of any proportion.
FILL = 0.85


def choices() -> tuple[str, ...]:
    """Every value the aspect-ratio setting accepts."""
    return (OFF, *PRESETS)


def _number(value: float) -> str:
    """A compact fixed-point decimal, never exponent notation.

    `format(x, "g")` is tempting and wrong: it writes small values as
    `1e-05`, which is not an expression muParser should be asked to
    read. Fixed-point, with the trailing zeros trimmed, is.
    """
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return text or "0"


def size_expression(shape: Shape, fill: float = FILL) -> str:
    """The `size` rule value for a shape: `"<width> <height>"`.

    Both axes are expressions over `monitor_w` and `monitor_h`, evaluated
    by Hyprland when the window opens. A window of this shape is limited
    either by the monitor's width or by its height, whichever runs out
    first, so each axis takes the `min` of the width-limited and the
    height-limited candidate. The result is the biggest window of this
    shape inside `fill` of the monitor, whatever the monitor's own
    proportions are: a portrait display gets a 3:2 landscape window that
    fits its width, rather than one that hangs off the edges.

    The two expressions are separated by whitespace and Hyprland splits
    on the *first* whitespace it finds. Neither may therefore contain
    any, which is why there is no space after the commas.
    """
    if not 0.0 < fill <= 1.0:
        raise ValueError(f"fill must be above 0 and at most 1, got {fill!r}")

    f = _number(fill)
    w, h = shape.width, shape.height
    width = f"min(monitor_w*{f},monitor_h*{f}*{w}/{h})"
    height = f"min(monitor_w*{f}*{h}/{w},monitor_h*{f})"
    return f"{width} {height}"


def resolve(value: object) -> Shape | None:
    """The shape a setting value names, or None for off or anything else.

    "Anything else" includes a value from a hand-edited settings file
    that this build does not know. That is deliberately not an error
    here: it must never be able to stop the desktop being generated.
    Callers that care report it with `is_known`.
    """
    if isinstance(value, str):
        return PRESETS.get(value.strip().lower())
    return None


def is_known(value: object) -> bool:
    return isinstance(value, str) and value.strip().lower() in choices()
