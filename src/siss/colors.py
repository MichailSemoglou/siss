"""
Color utilities for Siss.

This module lets users describe colors the way designers actually do:

* **Hex strings** with or without a leading ``#``, 3- or 6-digit:
  ``"#ff0044"``, ``"ff0044"``, ``"#f04"``, ``"f04"``.
* **CSS named colors**: ``"rebeccapurple"``, ``"DarkSlateBlue"``,
  ``"RED"`` (case-insensitive).
* **RGB triples** of integers (0-255), as a list/tuple of ints/strings or a
  comma/space-separated string: ``[255, 0, 0]``, ``"255,0,0"``, ``"255 0 0"``.
  This is the original ``siss`` syntax, so existing commands keep working.

It also ships a small set of **curated palettes** accessible via
``--palette <name>`` from the command line.

Public API
----------
.. autosummary::

   parse_color
   get_palette
   list_palettes
   validate_rgb
   PALETTES
   CSS_NAMED_COLORS
"""
from __future__ import annotations

import json
from typing import Dict, Iterable, Optional, Tuple, Union

# A single color can be supplied as many things.
ColorLike = Union[str, Iterable]


# ---------------------------------------------------------------------------
# CSS / HTML named colors (CSS Color Module Level 3 + rebeccapurple).
# Values are RGB tuples, 0-255. Keys are lowercase.
# ---------------------------------------------------------------------------
CSS_NAMED_COLORS = {
    "aliceblue": (240, 248, 255),
    "antiquewhite": (250, 235, 215),
    "aqua": (0, 255, 255),
    "aquamarine": (127, 255, 212),
    "azure": (240, 255, 255),
    "beige": (245, 245, 220),
    "bisque": (255, 228, 196),
    "black": (0, 0, 0),
    "blanchedalmond": (255, 235, 205),
    "blue": (0, 0, 255),
    "blueviolet": (138, 43, 226),
    "brown": (165, 42, 42),
    "burlywood": (222, 184, 135),
    "cadetblue": (95, 158, 160),
    "chartreuse": (127, 255, 0),
    "chocolate": (210, 105, 30),
    "coral": (255, 127, 80),
    "cornflowerblue": (100, 149, 237),
    "cornsilk": (255, 248, 220),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "darkblue": (0, 0, 139),
    "darkcyan": (0, 139, 139),
    "darkgoldenrod": (184, 134, 11),
    "darkgray": (169, 169, 169),
    "darkgreen": (0, 100, 0),
    "darkgrey": (169, 169, 169),
    "darkkhaki": (189, 183, 107),
    "darkmagenta": (139, 0, 139),
    "darkolivegreen": (85, 107, 47),
    "darkorange": (255, 140, 0),
    "darkorchid": (153, 50, 204),
    "darkred": (139, 0, 0),
    "darksalmon": (233, 150, 122),
    "darkseagreen": (143, 188, 143),
    "darkslateblue": (72, 61, 139),
    "darkslategray": (47, 79, 79),
    "darkslategrey": (47, 79, 79),
    "darkturquoise": (0, 206, 209),
    "darkviolet": (148, 0, 211),
    "deeppink": (255, 20, 147),
    "deepskyblue": (0, 191, 255),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "dodgerblue": (30, 144, 255),
    "firebrick": (178, 34, 34),
    "floralwhite": (255, 250, 240),
    "forestgreen": (34, 139, 34),
    "fuchsia": (255, 0, 255),
    "gainsboro": (220, 220, 220),
    "ghostwhite": (248, 248, 255),
    "gold": (255, 215, 0),
    "goldenrod": (218, 165, 32),
    "gray": (128, 128, 128),
    "green": (0, 128, 0),
    "greenyellow": (173, 255, 47),
    "grey": (128, 128, 128),
    "honeydew": (240, 255, 240),
    "hotpink": (255, 105, 180),
    "indianred": (205, 92, 92),
    "indigo": (75, 0, 130),
    "ivory": (255, 255, 240),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "lavenderblush": (255, 240, 245),
    "lawngreen": (124, 252, 0),
    "lemonchiffon": (255, 250, 205),
    "lightblue": (173, 216, 230),
    "lightcoral": (240, 128, 128),
    "lightcyan": (224, 255, 255),
    "lightgoldenrodyellow": (250, 250, 210),
    "lightgray": (211, 211, 211),
    "lightgreen": (144, 238, 144),
    "lightgrey": (211, 211, 211),
    "lightpink": (255, 182, 193),
    "lightsalmon": (255, 160, 122),
    "lightseagreen": (32, 178, 170),
    "lightskyblue": (135, 206, 250),
    "lightslategray": (119, 136, 153),
    "lightslategrey": (119, 136, 153),
    "lightsteelblue": (176, 196, 222),
    "lightyellow": (255, 255, 224),
    "lime": (0, 255, 0),
    "limegreen": (50, 205, 50),
    "linen": (250, 240, 230),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "mediumaquamarine": (102, 205, 170),
    "mediumblue": (0, 0, 205),
    "mediumorchid": (186, 85, 211),
    "mediumpurple": (147, 112, 219),
    "mediumseagreen": (60, 179, 113),
    "mediumslateblue": (123, 104, 238),
    "mediumspringgreen": (0, 250, 154),
    "mediumturquoise": (72, 209, 204),
    "mediumvioletred": (199, 21, 133),
    "midnightblue": (25, 25, 112),
    "mintcream": (245, 255, 250),
    "mistyrose": (255, 228, 225),
    "moccasin": (255, 228, 181),
    "navajowhite": (255, 222, 173),
    "navy": (0, 0, 128),
    "oldlace": (253, 245, 230),
    "olive": (128, 128, 0),
    "olivedrab": (107, 142, 35),
    "orange": (255, 165, 0),
    "orangered": (255, 69, 0),
    "orchid": (218, 112, 214),
    "palegoldenrod": (238, 232, 170),
    "palegreen": (152, 251, 152),
    "paleturquoise": (175, 238, 238),
    "palevioletred": (219, 112, 147),
    "papayawhip": (255, 239, 213),
    "peachpuff": (255, 218, 185),
    "peru": (205, 133, 63),
    "pink": (255, 192, 203),
    "plum": (221, 160, 221),
    "powderblue": (176, 224, 230),
    "purple": (128, 0, 128),
    "rebeccapurple": (102, 51, 153),
    "red": (255, 0, 0),
    "rosybrown": (188, 143, 143),
    "royalblue": (65, 105, 225),
    "saddlebrown": (139, 69, 19),
    "salmon": (250, 128, 114),
    "sandybrown": (244, 164, 96),
    "seagreen": (46, 139, 87),
    "seashell": (255, 245, 238),
    "sienna": (160, 82, 45),
    "silver": (192, 192, 192),
    "skyblue": (135, 206, 235),
    "slateblue": (106, 90, 205),
    "slategray": (112, 128, 144),
    "slategrey": (112, 128, 144),
    "snow": (255, 250, 250),
    "springgreen": (0, 255, 127),
    "steelblue": (70, 130, 180),
    "tan": (210, 180, 140),
    "teal": (0, 128, 128),
    "thistle": (216, 191, 216),
    "tomato": (255, 99, 71),
    "turquoise": (64, 224, 208),
    "violet": (238, 130, 238),
    "wheat": (245, 222, 179),
    "white": (255, 255, 255),
    "whitesmoke": (245, 245, 245),
    "yellow": (255, 255, 0),
    "yellowgreen": (154, 205, 50),
}


# ---------------------------------------------------------------------------
# Curated palettes.
#
# Each palette is {"color1": hex, "color2": hex}, matching the existing CLI
# semantics:
#   * color1 -> dark areas in duotone / symbols in halftone
#   * color2 -> light areas in duotone / background in halftone
# ---------------------------------------------------------------------------
PALETTES = {
    "sunset": {
        "color1": "#3b1f4b",   # deep purple (darks / symbols)
        "color2": "#f6c453",   # warm gold (lights / background)
        "description": "Deep purple to warm gold. Warm and cinematic.",
    },
    "mint": {
        "color1": "#0b3142",   # dark teal
        "color2": "#a8e6cf",   # soft mint
        "description": "Dark teal to soft mint. Fresh and clean.",
    },
    "cyberpunk": {
        "color1": "#0d0221",   # near-black indigo
        "color2": "#ff2a6d",   # hot magenta
        "description": "Near-black indigo to hot magenta. Neon and edgy.",
    },
    "sepia": {
        "color1": "#2b1d0e",   # dark espresso
        "color2": "#d8b48f",   # faded sepia
        "description": "Dark espresso to faded sepia. Vintage film feel.",
    },
    "noir": {
        "color1": "#000000",   # pure black
        "color2": "#e5e5e5",   # soft white (not blown out)
        "description": "Pure black to soft white. Classic monochrome.",
    },
    "ocean": {
        "color1": "#001f3f",   # navy
        "color2": "#7fdbff",   # aqua
        "description": "Navy to aqua. Cool and aquatic.",
    },
    "forest": {
        "color1": "#1a2e1a",   # deep forest
        "color2": "#c7e9b4",   # pale leaf
        "description": "Deep forest to pale leaf. Earthy and natural.",
    },
    "rose": {
        "color1": "#5a1a2b",   # wine
        "color2": "#ffc0cb",   # pink
        "description": "Wine to pink. Soft and romantic.",
    },
    "slate": {
        "color1": "#1f2933",   # ink
        "color2": "#aab8c2",   # cool gray
        "description": "Ink to cool gray. Modern and neutral.",
    },
    "tropical": {
        "color1": "#003b46",   # deep teal
        "color2": "#ffd23f",   # sunshine yellow
        "description": "Deep teal to sunshine yellow. Bold and bright.",
    },
    "candy": {
        "color1": "#3a0ca3",   # electric indigo
        "color2": "#f72585",   # bright pink
        "description": "Electric indigo to bright pink. Playful and loud.",
    },
    "paper": {
        "color1": "#222222",   # ink black
        "color2": "#f4f1de",   # warm cream
        "description": "Ink black to warm cream. Print-/screen-friendly.",
    },
}


def parse_color(color: ColorLike) -> Tuple[int, int, int]:
    """
    Parse a color from a flexible input into an ``(r, g, b)`` tuple.

    Accepted forms
    --------------
    * Hex string (with/without ``#``, 3 or 6 digits): ``"#ff0044"``,
      ``"ff0044"``, ``"#f04"``, ``"f04"``.
    * CSS named color: ``"rebeccapurple"``, ``"DarkSlateBlue"`` (any case).
    * RGB ints as a list/tuple: ``[255, 0, 0]`` or ``(255, 0, 0)``.
    * RGB ints as a string of space- or comma-separated values:
      ``"255 0 0"``, ``"255,0,0"``, ``"255, 0, 0"``.

    Parameters
    ----------
    color : str | int | list | tuple
        The color to parse.

    Returns
    -------
    tuple
        ``(r, g, b)`` with each component an int in ``0..255``.

    Raises
    ------
    ValueError
        If the input cannot be interpreted as a color, or if any channel
        is outside ``0..255``.
    """
    # --- RGB given as a list/tuple of ints/strings ---------------------------
    if isinstance(color, (list, tuple)):
        if len(color) != 3:
            raise ValueError(
                f"Expected 3 RGB values, got {len(color)}: {color!r}"
            )
        return _coerce_rgb(color)

    if not isinstance(color, str):
        raise ValueError(
            f"Unsupported color type {type(color).__name__}: {color!r}"
        )

    text = color.strip()
    if not text:
        raise ValueError("Empty color string")

    # --- Hex (with or without '#') -------------------------------------------
    if text.startswith("#"):
        digits = text[1:]
        if _looks_like_hex(digits):
            return _parse_hex(digits)
        raise ValueError(
            f"Could not parse color {color!r}. Use a hex string ('#ff0044'), "
            f"a CSS name ('rebeccapurple'), or 3 RGB ints ([255, 0, 0])."
        )
    # Heuristic: bare hex like "ff0044" or "f04". We deliberately exclude
    # values that are valid CSS names (e.g. "bad" would otherwise be read
    # as the 3-digit hex #baaadd), so try CSS names first for short tokens.
    lower = text.lower()
    if lower in CSS_NAMED_COLORS:
        return CSS_NAMED_COLORS[lower]

    # A bare token that's all hex digits and length 3 or 6 -> treat as hex.
    if _looks_like_hex(text):
        return _parse_hex(text)

    # --- RGB as a single comma/space-separated string ------------------------
    if "," in text or " " in text:
        parts = [p for p in text.replace(",", " ").split() if p]
        if len(parts) == 3:
            return _coerce_rgb(parts)

    raise ValueError(
        f"Could not parse color {color!r}. Use a hex string ('#ff0044'), "
        f"a CSS name ('rebeccapurple'), or 3 RGB ints ([255, 0, 0])."
    )


def get_palette(
    name: str,
    custom_palettes: Optional[Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = None,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Look up a palette by name and return ``(color1_rgb, color2_rgb)``.

    Custom palettes from a ``--palette-file`` take precedence over the
    built-in ones when both share the same name.

    Parameters
    ----------
    name : str
        Palette name (case-insensitive).
    custom_palettes : dict or None
        Palette mapping loaded from a JSON file via :func:`load_palette_file`,
        or ``None`` when ``--palette-file`` was not passed.

    Returns
    -------
    tuple
        ``((r, g, b), (r, g, b))`` for ``color1`` and ``color2``.

    Raises
    ------
    ValueError
        If the palette name is unknown. The error message lists the
        available palettes to help discovery.
    """
    key = name.strip().lower()
    if custom_palettes and key in custom_palettes:
        return custom_palettes[key]
    if key not in PALETTES:
        available = sorted(set(PALETTES.keys()) | set(custom_palettes or {}))
        raise ValueError(
            f"Unknown palette {name!r}. Available palettes: "
            f"{', '.join(available)}."
        )
    palette = PALETTES[key]
    return parse_color(palette["color1"]), parse_color(palette["color2"])


def list_palettes(
    custom_palettes: Optional[Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = None,
) -> str:
    """
    Return a human-readable, plain-text catalog of the available palettes.

    When *custom_palettes* is not ``None``, entries from the
    ``--palette-file`` are included and marked as custom. Custom names
    that shadow built-in ones replace the built-in entry in the listing.

    Suitable for printing directly from the CLI.
    """
    lines = ["Curated palettes (--palette <name>):", ""]
    custom_names = {name.lower() for name in (custom_palettes or {})}

    # Built-in palettes, skipping any names overridden by custom palettes.
    for name, p in PALETTES.items():
        if name.lower() in custom_names:
            continue
        lines.append(
            f"  {name:<10} {p['color1']} -> {p['color2']}"
            f"   {p.get('description', '')}"
        )

    # Custom palettes (from --palette-file).
    if custom_palettes:
        lines.append("")
        lines.append("Custom palettes (--palette-file):")
        lines.append("")
        for name in sorted(custom_palettes):
            c1, c2 = custom_palettes[name]
            tag = " (overrides built-in)" if name.lower() in PALETTES else ""
            c1_hex = f"#{c1[0]:02x}{c1[1]:02x}{c1[2]:02x}"
            c2_hex = f"#{c2[0]:02x}{c2[1]:02x}{c2[2]:02x}"
            lines.append(f"  {name:<10} {c1_hex} -> {c2_hex}{tag}")

    lines.append("")
    lines.append(
        "Tip: override one slot with --color1/--color2 "
        "(hex, CSS name, or 'R G B')."
    )
    return "\n".join(lines)


def load_palette_file(path: str) -> Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
    """
    Load custom palettes from a JSON file and return a mapping of
    ``{name: (color1_rgb, color2_rgb)}``.

    The file must be a JSON object whose keys are palette names and whose
    values are objects with ``"color1"`` and ``"color2"`` keys. Each
    color value is parsed through :func:`parse_color`, so it accepts hex
    strings, CSS names, and RGB triples.

    Parameters
    ----------
    path : str
        Path to a JSON palette file.

    Returns
    -------
    dict
        ``{name: (color1_rgb, color2_rgb)}``, with names lowercased.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file is not valid JSON, a palette entry is missing
        ``color1`` or ``color2``, or a color value is invalid.
    """
    with open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in palette file {path!r}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Palette file {path!r} must contain a JSON object, "
            f"got {type(data).__name__}"
        )

    palettes: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {}
    for name, spec in data.items():
        if not isinstance(spec, dict):
            raise ValueError(
                f"Palette entry {name!r} must be an object with "
                f"'color1' and 'color2' keys"
            )
        missing = [k for k in ("color1", "color2") if k not in spec]
        if missing:
            raise ValueError(
                f"Palette entry {name!r} is missing key(s): "
                f"{', '.join(missing)}"
            )
        c1 = parse_color(spec["color1"])
        c2 = parse_color(spec["color2"])
        palettes[name.strip().lower()] = (c1, c2)
    return palettes


def validate_rgb(color: Iterable) -> Tuple[int, int, int]:
    """
    Validate an RGB triple and return it as a tuple of three ints.

    Shared by the effect processors, which receive colors that did not
    necessarily pass through :func:`parse_color`.

    Parameters
    ----------
    color : iterable
        Candidate ``(r, g, b)`` value.

    Returns
    -------
    tuple
        ``(r, g, b)`` with each component in ``0..255``.

    Raises
    ------
    ValueError
        If the value is not iterable, does not have exactly three
        channels, contains a non-integer (or boolean) channel, or any
        channel is outside ``0..255``.
    """
    try:
        values = tuple(color)
    except TypeError:
        raise ValueError(f"Expected an iterable of 3 RGB values, got {color!r}") from None
    if len(values) != 3:
        raise ValueError(
            f"Expected 3 RGB values, got {len(values)}: {color!r}"
        )
    if not all(isinstance(c, int) and not isinstance(c, bool) for c in values):
        raise ValueError(
            f"RGB color values must be integers, got {values!r}"
        )
    if not all(0 <= c <= 255 for c in values):
        raise ValueError(
            f"RGB color values must be between 0 and 255, got {values}"
        )
    return values


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_HEX_DIGITS = set("0123456789abcdefABCDEF")


def _looks_like_hex(text: str) -> bool:
    return len(text) in (3, 6) and all(c in _HEX_DIGITS for c in text)


def _parse_hex(digits: str) -> Tuple[int, int, int]:
    """Convert a hex string (with or without '#', length 3 or 6) into RGB.

    Callers guarantee the input is valid hex; this function does not
    re-validate the digit characters.
    """
    digits = digits.lstrip("#")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))


def _coerce_rgb(values: Iterable[Union[str, int]]) -> Tuple[int, int, int]:
    """Validate and convert a 3-element iterable of int-like values to RGB."""
    values = tuple(values)
    for v in values:
        if isinstance(v, bool) or isinstance(v, float):
            raise ValueError(f"RGB values must be integers: {values!r}")
    try:
        rgb = tuple(int(v) for v in values)
    except (TypeError, ValueError):
        raise ValueError(f"RGB values must be integers: {values!r}")
    return validate_rgb(rgb)
