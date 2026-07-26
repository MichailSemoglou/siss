"""
Module for applying duotone color effects to videos and still images.
"""
from typing import Callable, Tuple

import cv2
import numpy as np

from .colors import validate_rgb
from .utils.video_processing import process_media


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

    def _duotone_frame(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        duotone = np.zeros((h, w, 3), dtype=np.uint8)
        normalized = gray.astype(float) / 255.0
        for i in range(3):
            duotone[:, :, i] = (1 - normalized) * color1[i] + normalized * color2[i]
        return duotone.astype(np.uint8)

    return _duotone_frame


def apply_duotone(video_path: str, output_path: str, color1_rgb: Tuple[int, int, int], color2_rgb: Tuple[int, int, int], no_audio: bool = False) -> None:
    """
    Apply duotone color effect to a video or still image.

    The processing path is chosen from the output path extension: image
    extensions go through ``cv2.imread``/``cv2.imwrite``, anything else is
    processed frame by frame as a video.

    Args:
        video_path (str): Path to the input video or still image file
        output_path (str): Path where the processed result will be saved
        color1_rgb (tuple): RGB color for dark areas (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for light areas (r, g, b), values 0-255
        no_audio (bool): When True, skip the ffmpeg audio-merge step (videos only)

    Raises:
        FileNotFoundError: If the input cannot be opened
        ValueError: If the colors are not valid RGB values
    """
    process_media(
        video_path, output_path,
        _make_duotone_processor(color1_rgb, color2_rgb),
        no_audio=no_audio,
    )


def apply_duotone_image(image_path: str, output_path: str, color1_rgb: Tuple[int, int, int], color2_rgb: Tuple[int, int, int]) -> None:
    """
    Apply duotone color effect to a still image.

    Kept for backward compatibility: apply_duotone() handles still images
    and videos through the same entry point, so this simply forwards to it.
    """
    apply_duotone(image_path, output_path, color1_rgb, color2_rgb)
