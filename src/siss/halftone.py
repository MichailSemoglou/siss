"""
Module for applying halftone pattern effects to videos and still images.
"""
import math
from typing import Callable, Dict, Optional, Tuple, Union

import cv2
import numpy as np

from .colors import validate_rgb
from .utils.video_processing import process_media, split_view_stitch

_GAMMA_DEFAULT = 1.0

SYMBOL_TYPES = ("plus", "asterisk", "slash", "dot", "ring")
GRID_TYPES = ("square", "hex")


def _validate_gamma(value: float, parameter_name: str = "gamma") -> None:
    """Validate gamma values for halftone processing."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{parameter_name} must be a positive number, got {value!r}")
    if not math.isfinite(float(value)) or float(value) <= 0:
        raise ValueError(f"{parameter_name} must be a positive number, got {value!r}")


def _make_halftone_processor(
    symbol_size: int,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    symbol_type: str = 'plus',
    grid_type: str = 'square',
    gamma: float = _GAMMA_DEFAULT,
    loss_map: bool = False,
) -> Callable[[np.ndarray], Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]:
    """Build and return the per-frame closure used by both video and image paths.

    Validates the input parameters and returns a callable that maps a BGR frame
    to a halftone BGR frame using the two RGB colors.

    Parameters
    ----------
    gamma : float, optional
        Luminance-curve gamma applied in the mean-to-size mapping. Values above
        1 suppress symbol growth in dark regions; values below 1 amplify it.
        The default 1.0 gives a linear mapping identical to previous versions.
    loss_map : bool, optional
        When True, the closure returns a (rendered, loss_map) tuple. The loss
        map is a grayscale uint8 frame at the same resolution as the input,
        encoding per-cell divergence between source luminance and quantized
        symbol size as a brightness value.
    """
    background_color = validate_rgb(color2_rgb)[::-1]
    symbol_color = validate_rgb(color1_rgb)[::-1]

    if symbol_type not in SYMBOL_TYPES:
        raise ValueError(
            "Symbol type must be one of "
            + ", ".join(SYMBOL_TYPES)
            + f", got {symbol_type!r}"
        )
    if grid_type not in GRID_TYPES:
        raise ValueError(
            "Grid type must be one of "
            + ", ".join(GRID_TYPES)
            + f", got {grid_type!r}"
        )
    if symbol_size <= 0:
        raise ValueError("Symbol size must be greater than 0")
    _validate_gamma(gamma)

    def _halftone_frame(frame: np.ndarray):
        h, w = frame.shape[:2]
        adjusted = min(symbol_size, w // 20)
        step = max(adjusted // 2, 4)
        half = step // 2
        max_size = half - 1

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        halftone = np.full((h, w), 255, dtype=np.uint8)
        if loss_map:
            loss_acc = np.zeros((h, w), dtype=np.float64)
            loss_count = np.zeros((h, w), dtype=np.float64)

        integral = cv2.integral(gray, sdepth=cv2.CV_64F)

        ys = np.arange(0, h, step)
        even_xs = np.arange(0, w, step)
        odd_xs = np.arange(half, w, step) if grid_type == 'hex' else even_xs

        for block_ys, block_xs in ((ys[0::2], even_xs), (ys[1::2], odd_xs)):
            if block_ys.size == 0 or block_xs.size == 0:
                continue
            means = _grid_means(integral, block_ys, block_xs, h, w)
            normalized = 1.0 - means / 255.0
            if gamma != 1.0:
                normalized = normalized ** gamma
            sizes = (max_size * normalized).astype(np.intp)
            cx = block_xs + half
            cy = block_ys + half
            keep = (sizes > 0) & (cx < w) & (cy[:, np.newaxis] < h)
            rows, cols = np.nonzero(keep)
            if rows.size:
                _draw_symbols(halftone, symbol_type, cx[cols], cy[rows],
                              sizes[rows, cols])

            if loss_map:
                scale = max_size
                for i, y0 in enumerate(block_ys):
                    row_losses = np.abs(
                        means[i, :] - (sizes[i, :] / scale * 255.0)
                    )
                    if row_losses.size == 0:
                        continue
                    expanded_blocks = np.repeat(row_losses[:, np.newaxis], step, axis=1)
                    expanded_blocks = np.repeat(expanded_blocks[np.newaxis, :, :], step, axis=0)
                    y1 = min(y0 + step, h)
                    for j, x0 in enumerate(block_xs):
                        x0 = int(x0)
                        x1 = min(x0 + step, w)
                        if x1 <= x0 or y1 <= y0:
                            continue
                        block = expanded_blocks[:, j, :]
                        loss_acc[y0:y1, x0:x1] += block[:y1 - y0, :x1 - x0]
                        loss_count[y0:y1, x0:x1] += 1.0

        halftone_colored = np.zeros((h, w, 3), dtype=np.uint8)
        halftone_colored[:] = background_color
        symbol_mask = halftone == 0
        halftone_colored[symbol_mask] = symbol_color

        if loss_map:
            loss_count[loss_count == 0] = 1.0
            loss_frame = (loss_acc / loss_count).astype(np.uint8)
            return halftone_colored, loss_frame
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
    bottom edge are drawn per cell with OpenCV instead of the former renderer
    clamps those line endpoints to the frame, and a clamped Bresenham line is
    not pixel-identical to a clipped 45-degree diagonal.
    """
    if sizes.size == 0:
        return
    h, w = halftone.shape
    for size in np.unique(sizes):
        sel = sizes == size
        x = cx[sel]
        y = cy[sel]
        if symbol_type in ('asterisk', 'slash'):
            edge = (x + size >= w) | (y + size >= h) | (x - size < 0) | (y - size < 0)
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


def _draw_ring_bulk(halftone: np.ndarray, x: np.ndarray, y: np.ndarray, size: int) -> None:
    """
    Draw hollow rings of one size centered at each (x, y).

    Rasterized from a filled-outer-circle stamp with the inner circle
    subtracted, matching per-cell cv2.circle calls exactly.
    """
    stamp = np.zeros((2 * size + 1, 2 * size + 1), dtype=np.uint8)
    cv2.circle(stamp, (size, size), size, 1, -1)
    inner_r = max(0, size - 1)
    cv2.circle(stamp, (size, size), inner_r, 0, -1)
    dy, dx = np.nonzero(stamp)
    _scatter(halftone, (y[:, np.newaxis] + (dy - size)).ravel(),
             (x[:, np.newaxis] + (dx - size)).ravel())


_BULK_DRAWERS: Dict[str, Callable[..., None]] = {
    'plus': _draw_plus_bulk,
    'asterisk': _draw_asterisk_bulk,
    'slash': _draw_slash_bulk,
    'dot': _draw_dot_bulk,
    'ring': _draw_ring_bulk,
}


def apply_halftone(
    video_path: str,
    output_path: str,
    symbol_size: int,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    *,
    symbol_type: str = 'plus',
    grid_type: str = 'square',
    no_audio: bool = False,
    split_direction: Optional[str] = None,
    gamma: float = _GAMMA_DEFAULT,
    loss_map_path: Optional[str] = None,
    alt_color1_rgb: Optional[Tuple[int, int, int]] = None,
    alt_color2_rgb: Optional[Tuple[int, int, int]] = None,
    alt_symbol_type: Optional[str] = None,
    alt_symbol_size: Optional[int] = None,
    alt_grid_type: Optional[str] = None,
    alt_gamma: Optional[float] = None,
) -> None:
    """
    Apply halftone pattern effect to a video or still image.

    The processing path is chosen from the output path extension: image
    extensions go through ``cv2.imread``/``cv2.imwrite``, anything else is
    processed frame by frame as a video.

    When ``alt_color1_rgb`` or ``alt_color2_rgb`` is provided, a second
    processor is built (alt params default to main values) and the two
    results are stitched via :func:`split_view_stitch` according to
    ``split_direction``.

    Args:
        video_path (str): Path to the input video or still image file
        output_path (str): Path where the processed result will be saved
        symbol_size (int): Size of the largest symbol in the halftone effect
        color1_rgb (tuple): RGB color for symbols (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for background (r, g, b), values 0-255
        symbol_type (str): Type of symbol to use
        grid_type (str): Sampling grid layout ('square' or 'hex')
        no_audio (bool): When True, skip the ffmpeg audio-merge step
        gamma (float): Luminance-curve gamma exponent
        loss_map_path (str, optional): When given, write a grayscale loss
            map to this path alongside the rendered output
        alt_color1_rgb (tuple, optional): Alternative symbol color
        alt_color2_rgb (tuple, optional): Alternative background color
        alt_symbol_type (str, optional): Alternative symbol type
        alt_symbol_size (int, optional): Alternative symbol size
        alt_grid_type (str, optional): Alternative grid type
        alt_gamma (float, optional): Alternative gamma

    Raises:
        FileNotFoundError: If the input cannot be opened
        ValueError: If the colors are not valid RGB values, or if symbol_type,
            grid_type, or gamma is not valid
    """
    main_proc = _make_halftone_processor(
        symbol_size, color1_rgb, color2_rgb,
        symbol_type=symbol_type, grid_type=grid_type, gamma=gamma,
        loss_map=bool(loss_map_path),
    )
    if (
        alt_color1_rgb is not None
        or alt_color2_rgb is not None
        or alt_symbol_type is not None
        or alt_symbol_size is not None
        or alt_grid_type is not None
        or alt_gamma is not None
    ):
        alt_proc = _make_halftone_processor(
            alt_symbol_size or symbol_size,
            alt_color1_rgb or color1_rgb,
            alt_color2_rgb or color2_rgb,
            symbol_type=alt_symbol_type or symbol_type,
            grid_type=alt_grid_type or grid_type,
            gamma=alt_gamma if alt_gamma is not None else gamma,
        )
        direction = split_direction or "vertical"

        def _composed(frame):
            main_result = main_proc(frame)
            alt_result = alt_proc(frame)
            if isinstance(main_result, tuple):
                main_render, loss = main_result
                return split_view_stitch(main_render, alt_result, direction), loss
            return split_view_stitch(main_result, alt_result, direction)

        process_media(
            video_path, output_path, _composed,
            no_audio=no_audio, split_direction=direction,
            loss_map_path=loss_map_path, _skip_split_concat=True,
        )
    else:
        process_media(
            video_path, output_path, main_proc,
            no_audio=no_audio, split_direction=split_direction,
            loss_map_path=loss_map_path,
        )


def apply_halftone_image(
    image_path: str,
    output_path: str,
    symbol_size: int,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    *,
    symbol_type: str = 'plus',
    grid_type: str = 'square',
    no_audio: bool = False,
    split_direction: Optional[str] = None,
    gamma: float = _GAMMA_DEFAULT,
    loss_map_path: Optional[str] = None,
    alt_color1_rgb: Optional[Tuple[int, int, int]] = None,
    alt_color2_rgb: Optional[Tuple[int, int, int]] = None,
    alt_symbol_type: Optional[str] = None,
    alt_symbol_size: Optional[int] = None,
    alt_grid_type: Optional[str] = None,
    alt_gamma: Optional[float] = None,
) -> None:
    """
    Apply halftone pattern effect to a still image.

    Kept for backward compatibility: apply_halftone() handles still images
    and videos through the same entry point, so this simply forwards to it.
    """
    apply_halftone(
        image_path,
        output_path,
        symbol_size,
        color1_rgb,
        color2_rgb,
        symbol_type=symbol_type,
        grid_type=grid_type,
        no_audio=no_audio,
        split_direction=split_direction,
        gamma=gamma,
        loss_map_path=loss_map_path,
        alt_color1_rgb=alt_color1_rgb,
        alt_color2_rgb=alt_color2_rgb,
        alt_symbol_type=alt_symbol_type,
        alt_symbol_size=alt_symbol_size,
        alt_grid_type=alt_grid_type,
        alt_gamma=alt_gamma,
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
