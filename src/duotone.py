"""
Module for applying duotone color effects to videos and still images.
"""
import cv2
import numpy as np

from utils.video_processing import process_image, process_video_frames


def _make_duotone_processor(color1_rgb, color2_rgb):
    """
    Build and return the per-frame closure used by both video and image paths.

    Validates the input colors and returns a callable that maps a BGR frame
    to a duotone BGR frame using the two RGB colors.
    """
    for color in [color1_rgb, color2_rgb]:
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("RGB color values must be between 0 and 255")

    color1 = color1_rgb[::-1]
    color2 = color2_rgb[::-1]

    def _duotone_frame(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        duotone = np.zeros((h, w, 3), dtype=np.uint8)
        normalized = gray.astype(float) / 255.0
        for i in range(3):
            duotone[:, :, i] = (1 - normalized) * color1[i] + normalized * color2[i]
        return duotone.astype(np.uint8)

    return _duotone_frame


def apply_duotone(video_path, output_path, color1_rgb, color2_rgb):
    """
    Apply duotone color effect to a video.

    Args:
        video_path (str): Path to the input video file
        output_path (str): Path where the processed video will be saved
        color1_rgb (tuple): RGB color for dark areas (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for light areas (r, g, b), values 0-255

    Raises:
        FileNotFoundError: If the input video cannot be opened
        ValueError: If the colors are not valid RGB values
    """
    process_video_frames(
        video_path, output_path, _make_duotone_processor(color1_rgb, color2_rgb)
    )


def apply_duotone_image(image_path, output_path, color1_rgb, color2_rgb):
    """
    Apply duotone color effect to a still image.

    Args:
        image_path (str): Path to the input image file
        output_path (str): Path where the processed image will be saved
        color1_rgb (tuple): RGB color for dark areas (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for light areas (r, g, b), values 0-255

    Raises:
        FileNotFoundError: If the input image cannot be opened
        ValueError: If the colors are not valid RGB values
    """
    process_image(
        image_path, output_path, _make_duotone_processor(color1_rgb, color2_rgb)
    )
