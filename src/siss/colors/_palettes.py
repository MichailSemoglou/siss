"""
Curated palettes and palette-file loading.

Exports ``PALETTES``, ``get_palette``, ``list_palettes``, and
``load_palette_file``.
"""
import json
import os
from typing import Dict, Optional, Tuple

from ._parse import parse_color

# ---------------------------------------------------------------------------
# Curated palettes.
#
# Each palette is {"color1": hex, "color2": hex}, matching the existing CLI
# semantics:
#   * color1 -> dark areas in duotone / symbols in halftone
#   * color2 -> light areas in duotone / background in halftone
# ---------------------------------------------------------------------------
PALETTES: Dict[str, Dict[str, str]] = {
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
        If the file exceeds the size limit, is not valid JSON, a palette
        entry is missing ``color1`` or ``color2``, or a color value is
        invalid.
    """
    max_bytes = 1 * 1024 * 1024
    file_size = os.path.getsize(path)
    if file_size > max_bytes:
        raise ValueError(
            f"Palette file {path!r} is {file_size:_d} bytes; "
            f"the limit is {max_bytes:_d} bytes (1 MiB)."
        )

    with open(path, encoding="utf-8") as f:
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
        if len(name) > 64:
            raise ValueError(
                f"Palette name {name[:64]!r}... is {len(name)} characters; "
                f"names must be 64 characters or fewer."
            )
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
