"""Colour maths on `#rrggbb` strings: WCAG contrast and mixing."""

from __future__ import annotations

import math

_LINEAR_THRESHOLD = 0.04045


def _rgb(colour: str) -> tuple[int, int, int]:
    value = colour.removeprefix("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in range(0, 6, 2))
    return red, green, blue


def _luminance(colour: str) -> float:
    def linear(channel: int) -> float:
        if (srgb := channel / 255) <= _LINEAR_THRESHOLD:
            return srgb / 12.92
        return math.pow((srgb + 0.055) / 1.055, 2.4)

    red, green, blue = (linear(c) for c in _rgb(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """WCAG contrast ratio of two `#rrggbb` colours."""
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def mix(colour: str, background: str, *, share: float) -> str:
    """`share` of `colour` laid over `background`, as `#rrggbb`."""
    channels = zip(_rgb(colour), _rgb(background), strict=True)
    mixed = (round(c * share + b * (1 - share)) for c, b in channels)
    return "#" + "".join(f"{c:02x}" for c in mixed)
