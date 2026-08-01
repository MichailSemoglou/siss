"""
Module for applying duotone color effects to videos and still images.
"""
from typing import Callable, Optional, Tuple

import cv2
import numpy as np

from .colors import validate_rgb
from .utils.video_processing import process_media, split_view_stitch


def _make_duotone_processor(
    color1_rgb: Tuple[int, int, int], color2_rgb: Tuple[int, int, int]
) -> Callable[[np.ndarray], np.ndarray]:
    """
    Build and return the per-frame closure used by both video and image paths.

    Validates the input colors and returns a callable that maps a BGR frame
    to a duotone BGR frame using the two RGB colors.
    """
    color1 = validate_rgb(color1_rgb)[::-1]
    color2 = validate_rgb(color2_rgb)[::-1]

    def _duotone_frame(frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        normalized = gray.astype(np.float32)[:, :, np.newaxis] / 255.0
        color1_arr = np.asarray(color1, dtype=np.float32)
        color2_arr = np.asarray(color2, dtype=np.float32)
        duotone = (1 - normalized) * color1_arr + normalized * color2_arr
        return np.round(duotone).astype(np.uint8)

    return _duotone_frame


def apply_duotone(video_path: str, output_path: str, color1_rgb: Tuple[int, int, int], color2_rgb: Tuple[int, int, int], *, no_audio: bool = False, split_direction: Optional[str] = None, alt_color1_rgb: Optional[Tuple[int, int, int]] = None, alt_color2_rgb: Optional[Tuple[int, int, int]] = None) -> None:
    """
    Apply duotone color effect to a video or still image.

    The processing path is chosen from the output path extension: image
    extensions go through ``cv2.imread``/``cv2.imwrite``, anything else is
    processed frame by frame as a video.

    When ``alt_color1_rgb`` or ``alt_color2_rgb`` is provided, a second
    processor is built and the two results are stitched via
    :func:`split_view_stitch` according to ``split_direction``.

    Args:
        video_path (str): Path to the input video or still image file
        output_path (str): Path where the processed result will be saved
        color1_rgb (tuple): RGB color for dark areas (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for light areas (r, g, b), values 0-255
        no_audio (bool): When True, skip the ffmpeg audio-merge step
        alt_color1_rgb (tuple, optional): Alternative dark-area color
        alt_color2_rgb (tuple, optional): Alternative light-area color

    Raises:
        FileNotFoundError: If the input cannot be opened
        ValueError: If the colors are not valid RGB values
    """
    main_proc = _make_duotone_processor(color1_rgb, color2_rgb)
    if alt_color1_rgb is not None or alt_color2_rgb is not None:
        alt_proc = _make_duotone_processor(
            alt_color1_rgb or color1_rgb,
            alt_color2_rgb or color2_rgb,
        )
        direction = split_direction or "vertical"

        def _composed(frame):
            return split_view_stitch(
                main_proc(frame), alt_proc(frame), direction
            )

        process_media(video_path, output_path, _composed, no_audio=no_audio,
                       split_direction=direction, _skip_split_concat=True)
    else:
        process_media(
            video_path, output_path, main_proc,
            no_audio=no_audio, split_direction=split_direction,
        )


def apply_duotone_image(image_path: str, output_path: str, color1_rgb: Tuple[int, int, int], color2_rgb: Tuple[int, int, int], *, no_audio: bool = False, split_direction: Optional[str] = None, alt_color1_rgb: Optional[Tuple[int, int, int]] = None, alt_color2_rgb: Optional[Tuple[int, int, int]] = None) -> None:
    """
    Apply duotone color effect to a still image.

    Kept for backward compatibility: apply_duotone() handles still images
    and videos through the same entry point, so this simply forwards to it.
    """
    apply_duotone(image_path, output_path, color1_rgb, color2_rgb, no_audio=no_audio, split_direction=split_direction, alt_color1_rgb=alt_color1_rgb, alt_color2_rgb=alt_color2_rgb)
