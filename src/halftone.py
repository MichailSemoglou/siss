"""
Module for applying halftone pattern effects to videos.
"""
import cv2
import numpy as np

from utils.video_processing import process_video_frames


def apply_halftone(video_path, output_path, symbol_size, color1_rgb, color2_rgb,
                  symbol_type='plus', grid_type='square'):
    """
    Apply halftone pattern effect to a video.

    Args:
        video_path (str): Path to the input video file
        output_path (str): Path where the processed video will be saved
        symbol_size (int): Size of the largest symbol in the halftone effect
        color1_rgb (tuple): RGB color for symbols (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for background (r, g, b), values 0-255
        symbol_type (str): Type of symbol to use ('plus', 'asterisk', 'slash', or 'dot')
        grid_type (str): Sampling grid layout ('square' or 'hex'). 'hex' offsets
            every other row by half a step, producing the staggered dot
            screen used in traditional print halftone reproduction.

    Raises:
        FileNotFoundError: If the input video cannot be opened
        ValueError: If the colors are not valid RGB values, or if symbol_type
            or grid_type is not one of the supported values
    """
    if not all(0 <= c <= 255 for c in color1_rgb + color2_rgb):
        raise ValueError("RGB color values must be between 0 and 255")

    if symbol_type not in ['plus', 'asterisk', 'slash', 'dot']:
        raise ValueError("Symbol type must be 'plus', 'asterisk', 'slash', or 'dot'")

    if grid_type not in ['square', 'hex']:
        raise ValueError("Grid type must be 'square' or 'hex'")

    if symbol_size <= 0:
        raise ValueError("Symbol size must be greater than 0")

    background_color = color2_rgb[::-1]
    symbol_color = color1_rgb[::-1]

    symbol_functions = {
        'plus': _draw_plus_symbol,
        'asterisk': _draw_asterisk_symbol,
        'slash': _draw_slash_symbol,
        'dot': _draw_dot_symbol,
    }
    draw_symbol = symbol_functions[symbol_type]

    def _halftone_frame(frame):
        # Determine grid parameters from the actual frame size
        h, w = frame.shape[:2]
        adjusted = min(symbol_size, w // 20)
        step = max(adjusted // 2, 4)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        halftone = np.ones_like(gray) * 255

        for y in range(0, h, step):
            row_offset = step // 2 if grid_type == 'hex' and (y // step) % 2 == 1 else 0
            for x in range(row_offset, w, step):
                if y < h and x < w:
                    region = gray[y:min(y + 3, h), x:min(x + 3, w)]
                    intensity = np.mean(region)
                    max_size = step // 2 - 1
                    size = int(max_size * (1 - intensity / 255))
                    if size > 0 and y + step // 2 < h and x + step // 2 < w:
                        draw_symbol(halftone, x + step // 2, y + step // 2, size)

        halftone_colored = np.zeros((h, w, 3), dtype=np.uint8)
        halftone_colored[:] = background_color
        symbol_mask = halftone == 0
        halftone_colored[symbol_mask] = symbol_color
        return halftone_colored

    process_video_frames(video_path, output_path, _halftone_frame)


def _draw_plus_symbol(halftone, center_x, center_y, size):
    """Draw a plus symbol on the halftone image."""
    y1 = center_y
    x1 = max(0, center_x - size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    cv2.line(halftone, (x1, y1), (x2, y1), 0, 1)

    x1 = center_x
    y1 = max(0, center_y - size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x1, y2), 0, 1)


def _draw_asterisk_symbol(halftone, center_x, center_y, size):
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


def _draw_slash_symbol(halftone, center_x, center_y, size):
    """Draw a slash symbol on the halftone image."""
    x1 = max(0, center_x - size)
    y1 = min(halftone.shape[0] - 1, center_y + size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    y2 = max(0, center_y - size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)


def _draw_dot_symbol(halftone, center_x, center_y, size):
    """Draw a filled dot (circle) symbol on the halftone image.

    This is the classic print-halftone symbol: a solid circle whose radius
    scales with local luminance, in place of the plus/asterisk/slash glyphs.
    """
    cv2.circle(halftone, (center_x, center_y), size, 0, -1)
