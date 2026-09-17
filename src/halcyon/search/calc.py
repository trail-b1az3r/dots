"""The calculator and unit converter behind Spotlight.

`eval` is not used anywhere here. Expressions are parsed with `ast` and
walked against an allow-list of node types, so a query typed into a
launcher — or produced by a language model — cannot reach the filesystem,
import a module, or call anything that was not explicitly permitted.

Unit conversion is offline and exact. Currency needs live rates, so it is
gated on the user's web-access setting and says plainly when it has no
rates rather than inventing a number.
"""

from __future__ import annotations

import ast
import json
import math
import operator
import os
import re
import time
from typing import Any, Callable

from .. import paths

# ── Safe arithmetic ────────────────────────────────────────────────────

_BINARY: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitXor: operator.xor,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
}

_UNARY: dict[type, Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Invert: operator.invert,
}

#: The functions an expression may call. Typed loosely because the
#: builtins in here (abs, round, min, max, gcd) are generic over their
#: argument type; `_evaluate` checks that the result is a real number.
_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "ln": math.log,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "hypot": math.hypot,
    "degrees": math.degrees,
    "radians": math.radians,
    "factorial": lambda n: math.factorial(int(n)),
    "gcd": math.gcd,
}

_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

#: Guards against a pathological exponent locking the launcher up.
_MAX_POW = 1_000_000


class CalcError(ValueError):
    """The expression is not something this calculator will evaluate."""


def _evaluate(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalcError("only numbers are allowed")
    if isinstance(node, ast.BinOp):
        handler = _BINARY.get(type(node.op))
        if handler is None:
            raise CalcError("that operator is not supported")
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POW:
            raise CalcError("that exponent is too large")
        return handler(left, right)
    if isinstance(node, ast.UnaryOp):
        handler = _UNARY.get(type(node.op))
        if handler is None:
            raise CalcError("that operator is not supported")
        return handler(_evaluate(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalcError("only plain function calls are allowed")
        function = _FUNCTIONS.get(node.func.id)
        if function is None:
            raise CalcError(f"unknown function {node.func.id!r}")
        if node.keywords:
            raise CalcError("keyword arguments are not supported")
        return function(*[_evaluate(arg) for arg in node.args])
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalcError(f"unknown name {node.id!r}")
    raise CalcError("that is not an arithmetic expression")


def _tidy(expression: str) -> str:
    text = expression.strip()
    text = text.replace("×", "*").replace("÷", "/").replace("−", "-")
    text = text.replace("^", "**")
    # "50% of 200" and "10 % 3" mean different things; only rewrite the
    # first, where a word follows.
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%\s+of\s+", r"(\1/100)*", text, flags=re.I)
    text = re.sub(r"\bmod\b", "%", text, flags=re.I)
    return text


def calculate(expression: str) -> float | int | None:
    """Evaluate an arithmetic expression, or return None if it is not one."""
    text = _tidy(expression)
    if not text or not re.search(r"[\d)]", text):
        return None
    # A bare number is not a calculation worth showing a result card for.
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        return None
    if not re.search(r"[+\-*/%()^]|\b(" + "|".join(_FUNCTIONS) + r")\b", text):
        return None

    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError):
        return None
    try:
        value = _evaluate(tree)
    except CalcError:
        return None
    except (ArithmeticError, TypeError, ValueError, OverflowError, RecursionError):
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def format_number(value: float | int) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    rounded = round(float(value), 10)
    text = f"{rounded:,.10f}".rstrip("0").rstrip(".")
    return text or "0"


# ── Units ──────────────────────────────────────────────────────────────

#: Everything is expressed relative to one base unit per dimension.
_UNITS: dict[str, tuple[str, float, tuple[str, ...]]] = {
    # length (metre)
    "m": ("length", 1.0, ("meter", "meters", "metre", "metres")),
    "km": ("length", 1000.0, ("kilometer", "kilometers", "kilometre", "kilometres")),
    "cm": ("length", 0.01, ("centimeter", "centimeters", "centimetre", "centimetres")),
    "mm": ("length", 0.001, ("millimeter", "millimeters", "millimetre", "millimetres")),
    "mi": ("length", 1609.344, ("mile", "miles")),
    "yd": ("length", 0.9144, ("yard", "yards")),
    "ft": ("length", 0.3048, ("foot", "feet")),
    "in": ("length", 0.0254, ("inch", "inches")),
    "nmi": ("length", 1852.0, ("nauticalmile", "nauticalmiles")),
    # mass (kilogram)
    "kg": ("mass", 1.0, ("kilogram", "kilograms", "kilo", "kilos")),
    "g": ("mass", 0.001, ("gram", "grams")),
    "mg": ("mass", 1e-6, ("milligram", "milligrams")),
    "lb": ("mass", 0.45359237, ("pound", "pounds", "lbs")),
    "oz": ("mass", 0.028349523125, ("ounce", "ounces")),
    "st": ("mass", 6.35029318, ("stone", "stones")),
    "t": ("mass", 1000.0, ("tonne", "tonnes", "metricton")),
    # time (second)
    "s": ("time", 1.0, ("sec", "secs", "second", "seconds")),
    "ms": ("time", 0.001, ("millisecond", "milliseconds")),
    "min": ("time", 60.0, ("minute", "minutes")),
    "h": ("time", 3600.0, ("hr", "hrs", "hour", "hours")),
    "d": ("time", 86400.0, ("day", "days")),
    "wk": ("time", 604800.0, ("week", "weeks")),
    # data (byte)
    "b": ("data", 0.125, ("bit", "bits")),
    "byte": ("data", 1.0, ("bytes",)),
    "kb": ("data", 1000.0, ("kilobyte", "kilobytes")),
    "mb": ("data", 1e6, ("megabyte", "megabytes")),
    "gb": ("data", 1e9, ("gigabyte", "gigabytes")),
    "tb": ("data", 1e12, ("terabyte", "terabytes")),
    "kib": ("data", 1024.0, ("kibibyte", "kibibytes")),
    "mib": ("data", 1024.0**2, ("mebibyte", "mebibytes")),
    "gib": ("data", 1024.0**3, ("gibibyte", "gibibytes")),
    "tib": ("data", 1024.0**4, ("tebibyte", "tebibytes")),
    # speed (metre per second)
    "mps": ("speed", 1.0, ("m/s", "meterspersecond")),
    "kmh": ("speed", 1 / 3.6, ("km/h", "kph", "kilometersperhour")),
    "mph": ("speed", 0.44704, ("milesperhour",)),
    "kn": ("speed", 0.514444, ("knot", "knots")),
}

_TEMPERATURE = ("c", "f", "k", "celsius", "fahrenheit", "kelvin")

_ALIASES: dict[str, str] = {}
for _symbol, (_dimension, _factor, _names) in _UNITS.items():
    _ALIASES[_symbol] = _symbol
    for _name in _names:
        _ALIASES[_name] = _symbol


#: How a unit is written back to the user. Data units are the only ones
#: that look wrong in lower case.
_DISPLAY = {
    "b": "bit", "byte": "B", "kb": "kB", "mb": "MB", "gb": "GB", "tb": "TB",
    "kib": "KiB", "mib": "MiB", "gib": "GiB", "tib": "TiB",
    "kmh": "km/h", "mps": "m/s", "kn": "kn",
}


def _display(symbol: str) -> str:
    return _DISPLAY.get(symbol, symbol)


def _resolve_unit(token: str) -> str | None:
    key = token.strip().lower().replace(" ", "")
    return _ALIASES.get(key)


_CONVERSION_RE = re.compile(
    r"^\s*(-?\d+(?:[\d,]*\d)?(?:\.\d+)?)\s*([a-zA-Z°/$€£¥]+)\s*"
    r"(?:in|to|as|into|>)\s+([a-zA-Z°/$€£¥]+)\s*$",
    re.IGNORECASE,
)


def _to_celsius(value: float, unit: str) -> float:
    if unit in ("f", "fahrenheit"):
        return (value - 32.0) * 5.0 / 9.0
    if unit in ("k", "kelvin"):
        return value - 273.15
    return value


def _from_celsius(value: float, unit: str) -> float:
    if unit in ("f", "fahrenheit"):
        return value * 9.0 / 5.0 + 32.0
    if unit in ("k", "kelvin"):
        return value + 273.15
    return value


def convert(query: str, *, allow_network: bool = False) -> dict[str, Any] | None:
    """Convert `<number> <unit> in <unit>`, including currency."""
    match = _CONVERSION_RE.match(query)
    if not match:
        return None

    raw_amount, source_token, target_token = match.groups()
    try:
        amount = float(raw_amount.replace(",", ""))
    except ValueError:
        return None

    source = source_token.strip().lower().lstrip("°")
    target = target_token.strip().lower().lstrip("°")

    if source in _TEMPERATURE and target in _TEMPERATURE:
        celsius = _to_celsius(amount, source)
        result = _from_celsius(celsius, target)
        return {
            "kind": "temperature",
            "value": result,
            "text": f"{format_number(round(result, 4))}°{target[0].upper()}",
            "detail": f"{format_number(amount)}°{source[0].upper()}",
        }

    source_unit = _resolve_unit(source)
    target_unit = _resolve_unit(target)
    if source_unit and target_unit:
        source_dimension, source_factor, _ = _UNITS[source_unit]
        target_dimension, target_factor, _ = _UNITS[target_unit]
        if source_dimension != target_dimension:
            return {
                "kind": "error",
                "text": (
                    f"{_display(source_unit)} and {_display(target_unit)} "
                    "measure different things"
                ),
                "detail": f"{source_dimension} versus {target_dimension}",
            }
        result = amount * source_factor / target_factor
        return {
            "kind": source_dimension,
            "value": result,
            "text": f"{format_number(round(result, 6))} {_display(target_unit)}",
            "detail": f"{format_number(amount)} {_display(source_unit)}",
        }

    return _convert_currency(amount, source, target, allow_network=allow_network)


# ── Currency ───────────────────────────────────────────────────────────

_CURRENCY_SYMBOLS = {"$": "usd", "€": "eur", "£": "gbp", "¥": "jpy"}
_RATES_TTL = 12 * 3600


def _rates_file() -> str:
    return str(paths.CACHE_DIR / "exchange-rates.json")


def _load_rates() -> tuple[dict[str, float], float] | None:
    try:
        with open(_rates_file(), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        rates = {str(k).lower(): float(v) for k, v in payload["rates"].items()}
        return rates, float(payload.get("fetched", 0))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _fetch_rates() -> dict[str, float] | None:
    """Fetch rates from the ECB's daily reference feed.

    Only called when the user has allowed web access. The feed is a
    public XML file with no key and no tracking, and it is parsed with
    `defusedxml`-style care: we read attributes off a fixed element name
    with a regex rather than expanding any XML entity.
    """
    import urllib.error
    import urllib.request

    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:  # noqa: S310
            body = response.read(200_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None

    rates = {"eur": 1.0}
    for currency, rate in re.findall(
        r"currency=['\"]([A-Z]{3})['\"]\s+rate=['\"]([\d.]+)['\"]", body
    ):
        try:
            rates[currency.lower()] = float(rate)
        except ValueError:
            continue

    if len(rates) < 5:
        return None

    try:
        paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_rates_file(), "w", encoding="utf-8") as handle:
            json.dump({"fetched": time.time(), "rates": rates}, handle)
    except OSError:
        pass
    return rates


def _convert_currency(
    amount: float, source: str, target: str, *, allow_network: bool
) -> dict[str, Any] | None:
    source = _CURRENCY_SYMBOLS.get(source, source)
    target = _CURRENCY_SYMBOLS.get(target, target)
    if len(source) != 3 or len(target) != 3 or not source.isalpha() or not target.isalpha():
        return None

    cached = _load_rates()
    rates: dict[str, float] | None = None
    stale = False

    if cached is not None:
        rates, fetched = cached
        stale = (time.time() - fetched) > _RATES_TTL

    if (rates is None or stale) and allow_network:
        fresh = _fetch_rates()
        if fresh is not None:
            rates, stale = fresh, False

    if rates is None:
        return {
            "kind": "currency",
            "text": "No exchange rates available",
            "detail": (
                "Turn on Settings → Privacy → Allow web access to fetch "
                "daily reference rates from the European Central Bank."
            ),
        }

    if source not in rates or target not in rates:
        missing = source if source not in rates else target
        return {
            "kind": "currency",
            "text": f"No rate for {missing.upper()}",
            "detail": "The ECB reference feed does not publish that currency.",
        }

    # Rates are quoted against the euro, so convert through it.
    in_euro = amount / rates[source]
    result = in_euro * rates[target]
    detail = f"{format_number(amount)} {source.upper()}"
    if stale:
        detail += " · rates may be out of date"

    return {
        "kind": "currency",
        "value": result,
        "text": f"{result:,.2f} {target.upper()}",
        "detail": detail,
    }
