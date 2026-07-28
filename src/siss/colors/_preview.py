"""
Palette preview contact-sheet renderer.

Renders an A4-landscape PNG showing every palette as a labeled swatch pair.
"""
import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from siss import __version__

from ._palettes import PALETTES
from ._parse import parse_color

_log = logging.getLogger(__name__)


def _find_mono_font(size: int):
    """Return (regular, bold) PIL ImageFont objects at *size* pt.

    Searches common monospaced system font paths. Falls back to PIL's
    default bitmap font when no TrueType font is found.
    """
    mono_paths = []
    if sys.platform == "darwin":
        mono_paths = [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Courier.ttc",
            "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
            "/System/Library/Fonts/Supplemental/PTMono.ttc",
        ]
    elif sys.platform == "win32":
        mono_paths = [
            "C:\\Windows\\Fonts\\consola.ttf",
            "C:\\Windows\\Fonts\\cour.ttf",
            "C:\\Windows\\Fonts\\lucon.ttf",
        ]
    else:
        mono_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        ]

    font: Any = None
    font_bold = font
    for path in mono_paths:
        if os.path.isfile(path):
            try:
                font = ImageFont.truetype(path, size=size, index=0)
                try:
                    font_bold = ImageFont.truetype(path, size=size, index=1)
                except Exception:
                    _log.debug("Could not load bold font from %r", path)
                    font_bold = font
                break
            except Exception:
                _log.debug("Could not load font from %r", path)
                continue
    if font is None:
        font = ImageFont.load_default()
        font_bold = font
    return font, font_bold


def export_palette_preview(
    output_path: str,
    custom_palettes: Optional[Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = None,
) -> None:
    """
    Render a PNG contact sheet showing every palette as a labeled swatch pair.

    Built-in palettes are rendered first, then custom palettes from a
    ``--palette-file``. Each card shows the two colors side by side with
    their hex and RGB values in a monospaced-like layout.

    Parameters
    ----------
    output_path : str
        File path for the output PNG.
    custom_palettes : dict or None
        Palettes loaded from a JSON file via :func:`load_palette_file`.
    """
    entries: list[tuple[str, tuple[int, int, int], tuple[int, int, int], str]] = []
    custom_names = {name.lower() for name in (custom_palettes or {})}
    for name in PALETTES:
        if name.lower() in custom_names:
            continue
        p = PALETTES[name]
        c1 = parse_color(p["color1"])
        c2 = parse_color(p["color2"])
        entries.append((name, c1, c2, p.get("description", "")))
    if custom_palettes is not None:
        for name in sorted(custom_palettes):
            tag = " (custom)"
            entries.append((name, *custom_palettes[name], tag))

    cols = 2
    margin = 40
    padding = 28
    canvas_w = 1754
    title_h = 70

    card_w = (canvas_w - (cols + 1) * padding) // cols

    font_size = 12
    font, font_bold = _find_mono_font(font_size)

    swatch_h = 80
    indent = 14
    # Minimum card height: name row (34 px) + swatch + hex/RGB labels + bottom gap.
    # The RGB label is drawn at cy + 34 + swatch_h + 28, so the card must be at
    # least that tall plus one text line and a small bottom margin.
    min_card_h = 34 + swatch_h + 28 + font_size + 10

    rows = (len(entries) + cols - 1) // cols
    nominal_body_h = 1240 - margin - title_h - margin
    computed_card_h = (nominal_body_h - padding) // rows - padding if rows > 0 else min_card_h
    card_h = max(min_card_h, computed_card_h)
    canvas_h = margin + title_h + rows * (card_h + padding) + padding + margin

    gray = (120, 120, 120)
    dark = (40, 40, 40)
    bg = (245, 245, 245)
    row_line = (210, 210, 210)

    img = Image.new("RGB", (canvas_w, canvas_h), bg)
    draw = ImageDraw.Draw(img)

    title = f"Siss palette contact sheet  v{__version__}"
    subtitle = f"{len(entries)} palettes  —  A4 landscape  —  use with --palette <name>"
    draw.text((margin, margin + 6), title, fill=dark, font=font_bold)
    draw.text((margin, margin + 28), subtitle, fill=gray, font=font)

    swatch_w = card_w // 3 + 20

    for idx, (name, c1, c2, desc) in enumerate(entries):
        row, col = divmod(idx, cols)
        cx = padding + col * (card_w + padding)
        cy = margin + title_h + (card_h + padding) * row

        draw.text((cx + indent, cy + 8), name, fill=dark, font=font_bold)
        if desc:
            name_w, _ = draw.textbbox((0, 0), name, font=font_bold)[2:]
            draw.text((cx + indent + name_w + 10, cy + 8), desc, fill=gray, font=font)

        gap = 14
        sx1 = cx + indent
        sy = cy + 34
        sx2 = sx1 + swatch_w + gap

        for sx, c in ((sx1, c1), (sx2, c2)):
            draw.rectangle((sx, sy, sx + swatch_w, sy + swatch_h), fill=c)

            hex_str = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
            draw.text((sx, sy + swatch_h + 8), hex_str, fill=gray, font=font)
            rgb_str = f"rgb({c[0]}, {c[1]}, {c[2]})"
            draw.text((sx, sy + swatch_h + 28), rgb_str, fill=gray, font=font)

    sep_y = margin + title_h
    for _ in range(rows):
        sep_y += card_h + padding
        draw.line((padding, sep_y, canvas_w - padding, sep_y), fill=row_line, width=1)

    img.save(output_path, format="PNG")
    print(f"Palette preview saved to {output_path}")
