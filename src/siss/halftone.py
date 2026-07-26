"""
Module for applying halftone pattern effects to videos and still images.
"""
from typing import Callable, Dict, Tuple

import cv2
import numpy as np

from .colors import validate_rgb
from .utils.video_processing import process_media


def _make_halftone_processor(
    symbol_size: int,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    symbol_type: str = 'plus',
    grid_type: str = 'square',
) -> Callable[[np.ndarray], np.ndarray]:
    """
    Build and return the per-frame closure used by both video and image paths.

    Validates the input parameters and returns a callable that maps a BGR frame
    to a halftone BGR frame using the two RGB colors.
    """
    background_color = validate_rgb(color2_rgb)[::-1]
    symbol_color = validate_rgb(color1_rgb)[::-1]

    if symbol_type not in ['plus', 'asterisk', 'slash', 'dot']:
        raise ValueError("Symbol type must be 'plus', 'asterisk', 'slash', or 'dot'")

    if grid_type not in ['square', 'hex']:
        raise ValueError("Grid type must be 'square' or 'hex'")

    if symbol_size <= 0:
        raise ValueError("Symbol size must be greater than 0")

    def _halftone_frame(frame):
        h, w = frame.shape[:2]

        # Grid density scales with frame width: the largest symbol is at
        # most 1/20th of the width.  The minimum sampling step is 4 px so
        # that single-pixel or blank frames still produce a visible grid.
        adjusted = min(symbol_size, w // 20)
        step = max(adjusted // 2, 4)
        half = step // 2
        max_size = half - 1

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        halftone = np.full((h, w), 255, dtype=np.uint8)

        # Mean luminance of the 3x3 region at every grid point, computed in
        # one pass from the integral image instead of a per-cell Python loop.
        integral = cv2.integral(gray, sdepth=cv2.CV_64F)

        # On a hex grid, odd rows shift right by half a step.
        ys = np.arange(0, h, step)
        even_xs = np.arange(0, w, step)
        odd_xs = np.arange(half, w, step) if grid_type == 'hex' else even_xs

        for block_ys, block_xs in ((ys[0::2], even_xs), (ys[1::2], odd_xs)):
            if block_ys.size == 0 or block_xs.size == 0:
                continue

            means = _grid_means(integral, block_ys, block_xs, h, w)
            sizes = (max_size * (1.0 - means / 255.0)).astype(np.intp)

            cx = block_xs + half
            cy = block_ys + half
            keep = (sizes > 0) & (cx < w) & (cy[:, np.newaxis] < h)
            rows, cols = np.nonzero(keep)
            if rows.size:
                _draw_symbols(halftone, symbol_type, cx[cols], cy[rows],
                              sizes[rows, cols])

        halftone_colored = np.zeros((h, w, 3), dtype=np.uint8)
        halftone_colored[:] = background_color
        symbol_mask = halftone == 0
        halftone_colored[symbol_mask] = symbol_color
        return halftone_colored

    return _halftone_frame


def _grid_means(integral: np.ndarray, ys: np.ndarray, xs: np.ndarray, h: int, w: int, k: int = 3) -> np.ndarray:
    """
    Mean luminance of the k x k region anchored at each grid point.

    Returns an array of shape (len(ys), len(xs)). Regions are clipped at the
    right and bottom frame edges, matching the per-cell slicing of the former
    loop-based renderer.
    """
    y2 = np.minimum(ys + k, h)
    x2 = np.minimum(xs + k, w)
    sums = (integral[np.ix_(y2, x2)] - integral[np.ix_(ys, x2)]
            - integral[np.ix_(y2, xs)] + integral[np.ix_(ys, xs)])
    counts = (y2 - ys)[:, np.newaxis] * (x2 - xs)
    return sums / counts


def _draw_symbols(halftone: np.ndarray, symbol_type: str, cx: np.ndarray, cy: np.ndarray, sizes: np.ndarray) -> None:
    """
    Draw a batch of symbols on the single-channel mask, grouped by size.

    Each size group is drawn with vectorized index operations. The diagonal
    strokes of asterisk and slash symbols in cells touching the right or
    bottom edge are drawn per cell with OpenCV instead: the former renderer
    clamps those line endpoints to the frame, and a clamped Bresenham line is
    not pixel-identical to a clipped 45-degree diagonal.
    """
    h, w = halftone.shape
    for size in np.unique(sizes):
        sel = sizes == size
        x = cx[sel]
        y = cy[sel]
        if symbol_type in ('asterisk', 'slash'):
            edge = (x + size >= w) | (y + size >= h)
            if edge.any():
                draw_edge = _EDGE_DRAWERS[symbol_type]
                for ex, ey in zip(x[edge], y[edge]):
                    draw_edge(halftone, int(ex), int(ey), int(size))
                x = x[~edge]
                y = y[~edge]
        _BULK_DRAWERS[symbol_type](halftone, x, y, int(size))


def _scatter(halftone: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> None:
    """Zero the in-bounds (row, col) positions of the symbol mask."""
    h, w = halftone.shape
    keep = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
    halftone[rows[keep], cols[keep]] = 0


def _draw_plus_bulk(halftone: np.ndarray, x: np.ndarray, y: np.ndarray, size: int) -> None:
    """Draw plus symbols of one size centered at each (x, y)."""
    d = np.arange(-size, size + 1)
    _scatter(halftone, np.repeat(y, d.size), (x[:, np.newaxis] + d).ravel())
    _scatter(halftone, (y[:, np.newaxis] + d).ravel(), np.repeat(x, d.size))


def _draw_asterisk_bulk(halftone: np.ndarray, x: np.ndarray, y: np.ndarray, size: int) -> None:
    """Draw asterisk symbols of one size centered at each (x, y)."""
    _draw_plus_bulk(halftone, x, y, size)
    d = np.arange(-size, size + 1)
    cols = (x[:, np.newaxis] + d).ravel()
    _scatter(halftone, (y[:, np.newaxis] + d).ravel(), cols)
    _scatter(halftone, (y[:, np.newaxis] - d).ravel(), cols)


def _draw_slash_bulk(halftone: np.ndarray, x: np.ndarray, y: np.ndarray, size: int) -> None:
    """Draw slash symbols of one size centered at each (x, y)."""
    d = np.arange(-size, size + 1)
    _scatter(halftone, (y[:, np.newaxis] - d).ravel(),
             (x[:, np.newaxis] + d).ravel())


def _draw_dot_bulk(halftone: np.ndarray, x: np.ndarray, y: np.ndarray, size: int) -> None:
    """
    Draw filled dots of one size centered at each (x, y).

    Offsets come from a stamp rasterized by cv2.circle, so the result matches
    per-cell cv2.circle calls exactly.
    """
    stamp = np.zeros((2 * size + 1, 2 * size + 1), dtype=np.uint8)
    cv2.circle(stamp, (size, size), size, 1, -1)
    dy, dx = np.nonzero(stamp)
    _scatter(halftone, (y[:, np.newaxis] + (dy - size)).ravel(),
             (x[:, np.newaxis] + (dx - size)).ravel())


_BULK_DRAWERS: Dict[str, Callable[..., None]] = {
    'plus': _draw_plus_bulk,
    'asterisk': _draw_asterisk_bulk,
    'slash': _draw_slash_bulk,
    'dot': _draw_dot_bulk,
}


def apply_halftone(
    video_path: str,
    output_path: str,
    symbol_size: int,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    symbol_type: str = 'plus',
    grid_type: str = 'square',
    no_audio: bool = False,
) -> None:
    """
    Apply halftone pattern effect to a video or still image.

    The processing path is chosen from the output path extension: image
    extensions go through ``cv2.imread``/``cv2.imwrite``, anything else is
    processed frame by frame as a video.

    Args:
        video_path (str): Path to the input video or still image file
        output_path (str): Path where the processed result will be saved
        symbol_size (int): Size of the largest symbol in the halftone effect
        color1_rgb (tuple): RGB color for symbols (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for background (r, g, b), values 0-255
        symbol_type (str): Type of symbol to use ('plus', 'asterisk', 'slash', or 'dot')
        grid_type (str): Sampling grid layout ('square' or 'hex'). 'hex' offsets
            every other row by half a step, producing the staggered dot
            screen used in traditional print halftone reproduction.
        no_audio (bool): When True, skip the ffmpeg audio-merge step (videos only)

    Raises:
        FileNotFoundError: If the input cannot be opened
        ValueError: If the colors are not valid RGB values, or if symbol_type
            or grid_type is not one of the supported values
    """
    process_media(
        video_path,
        output_path,
        _make_halftone_processor(
            symbol_size, color1_rgb, color2_rgb,
            symbol_type=symbol_type, grid_type=grid_type,
        ),
        no_audio=no_audio,
    )


def apply_halftone_image(
    image_path: str,
    output_path: str,
    symbol_size: int,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    symbol_type: str = 'plus',
    grid_type: str = 'square',
) -> None:
    """
    Apply halftone pattern effect to a still image.

    Kept for backward compatibility: apply_halftone() handles still images
    and videos through the same entry point, so this simply forwards to it.
    """
    apply_halftone(
        image_path, output_path, symbol_size, color1_rgb, color2_rgb,
        symbol_type=symbol_type, grid_type=grid_type,
    )


def _draw_plus_symbol(halftone: np.ndarray, center_x: int, center_y: int, size: int) -> None:
    """Draw a plus symbol on the halftone image."""
    y1 = center_y
    x1 = max(0, center_x - size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    cv2.line(halftone, (x1, y1), (x2, y1), 0, 1)

    x1 = center_x
    y1 = max(0, center_y - size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x1, y2), 0, 1)


def _draw_asterisk_symbol(halftone: np.ndarray, center_x: int, center_y: int, size: int) -> None:
    """Draw an asterisk symbol on the halftone image."""
    _draw_plus_symbol(halftone, center_x, center_y, size)

    x1 = max(0, center_x - size)
    y1 = max(0, center_y - size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)

    x1 = min(halftone.shape[1] - 1, center_x + size)
    y1 = max(0, center_y - size)
    x2 = max(0, center_x - size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)


def _draw_slash_symbol(halftone: np.ndarray, center_x: int, center_y: int, size: int) -> None:
    """Draw a slash symbol on the halftone image."""
    x1 = max(0, center_x - size)
    y1 = min(halftone.shape[0] - 1, center_y + size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    y2 = max(0, center_y - size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)


_EDGE_DRAWERS: Dict[str, Callable[..., None]] = {
    'asterisk': _draw_asterisk_symbol,
    'slash': _draw_slash_symbol,
}
