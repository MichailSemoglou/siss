"""
Color utilities for Siss.

This package provides color parsing, validation, palette management, and a
palette preview contact-sheet renderer. The public API is re-exported from
three internal modules so callers see a single flat namespace:

* ``parse_color``, ``CSS_NAMED_COLORS`` — from ``_parse``
* ``get_palette``, ``list_palettes``, ``load_palette_file``, ``validate_rgb``,
  ``PALETTES`` — from ``_palettes``
* ``export_palette_preview`` — from ``_preview``
"""

from ._palettes import (  # noqa: F401
    PALETTES,
    get_palette,
    list_palettes,
    load_palette_file,
)
from ._parse import CSS_NAMED_COLORS, ColorLike, parse_color, validate_rgb  # noqa: F401
from ._preview import export_palette_preview  # noqa: F401
