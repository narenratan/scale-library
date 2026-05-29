"""
Scale Workshop v2 magic link encoder.

Encoding spec (from scale-workshop/src/url-encode.ts):
  - Escape 'E' as 'EE'
  - Substitute: / → F, \\ → B, , → C, space → S, + → P, < → L, > → R, [ → Q
  - Encode digit sequences: each run of digits, preserving leading zeros,
    with the non-zero suffix encoded as base-36 (lowercase a–z for 10–35)
  - Lines joined with '_'

Colors:
  - 12-note scales: omit ?c= (SW default = standard piano keyboard)
  - All other sizes: N tildes e.g. ?c=~~~~~ (all white)
"""

import re
from urllib.parse import quote

_SUBSTITUTIONS = {
    "E": "EE",
    "/": "F",
    "\\": "B",
    ",": "C",
    " ": "S",
    "+": "P",
    "<": "L",
    ">": "R",
    "[": "Q",
}

_DIGIT_RE = re.compile(r"\d+")

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _base36(n: int) -> str:
    if n == 0:
        return "0"
    digits = []
    while n:
        digits.append(_DIGITS[n % 36])
        n //= 36
    return "".join(reversed(digits))


def _encode_digit_seq(s: str) -> str:
    """Encode a digit sequence, preserving leading zeros."""
    stripped = s.lstrip("0")
    prefix = "0" * (len(s) - len(stripped))
    if stripped:
        return prefix + _base36(int(stripped))
    return prefix  # all zeros


def _encode_line(line: str) -> str:
    # Apply character substitutions first, then encode digit runs.
    out = []
    for ch in line:
        out.append(_SUBSTITUTIONS.get(ch, ch))
    joined = "".join(out)
    return _DIGIT_RE.sub(lambda m: _encode_digit_seq(m.group()), joined)


_BARE_INTEGER_RE = re.compile(r"^\d+$")


def _normalize_line(line: str) -> str:
    """Normalize a scale line for Scale Workshop encoding.

    SCL files allow bare integers (e.g. '2') to represent ratios (2/1),
    but Scale Workshop requires the explicit '/1' form.
    """
    stripped = line.strip()
    if _BARE_INTEGER_RE.match(stripped):
        return stripped + "/1"
    return stripped


def encode_scale_lines(lines: list[str]) -> str:
    """Encode a list of scale lines (ratios/cents strings) for the ?l= parameter."""
    return "_".join(_encode_line(_normalize_line(line)) for line in lines)


def scale_workshop_url(name: str, lines: list[str]) -> str:
    """
    Build a Scale Workshop v2 URL for the given scale.

    Args:
        name: Scale description (used as ?n= value, URL-encoded).
        lines: List of tone strings as they appear in the scl file
               (e.g. ["9/8", "5/4", "2/1"]).

    Returns:
        Full Scale Workshop URL string.
    """
    encoded_lines = encode_scale_lines(lines)
    encoded_name = quote(name.strip())
    n = len(lines)
    url = (
        f"https://scaleworkshop.plainsound.org/"
        f"?n={encoded_name}&l={encoded_lines}&version=2.1.0"
    )
    if n != 12:
        colors = "~" * n
        url += f"&c={colors}"
    return url
