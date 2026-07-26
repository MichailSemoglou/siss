"""
Module for fixing codec issues in OpenCV video writing.

This module provides functions to address common codec issues when writing
videos with OpenCV, particularly on different operating systems.
"""
import os
import platform
import tempfile
from pathlib import Path

import cv2
import numpy as np

# Default codec per extension, used on Linux and other platforms. Per-OS
# overrides are merged on top of this base map.
_DEFAULT_CODECS = {
    '.avi': 'XVID',
    '.mp4': 'mp4v',  # DIVX, X264 are also options
    '.mov': 'mp4v',
    '.mkv': 'X264',
    '.wmv': 'WMV2',
}

_OS_CODEC_OVERRIDES = {
    'Windows': {'.mp4': 'H264', '.mov': 'H264', '.mkv': 'H264'},  # DIVX also an option
    'Darwin': {'.mp4': 'avc1', '.mov': 'avc1', '.mkv': 'avc1'},  # H.264 codec
}


def get_compatible_codec(output_path: str) -> str:
    """
    Get a compatible codec for the current operating system and output format.

    Args:
        output_path (str): Path where the video will be saved

    Returns:
        str: Four character codec code
    """
    ext = Path(output_path).suffix.lower()
    codec_map = {
        **_DEFAULT_CODECS,
        **_OS_CODEC_OVERRIDES.get(platform.system(), {}),
    }

    # Default to a generally compatible codec if extension not found
    return codec_map.get(ext, 'mp4v')


def validate_codec(codec: str, width: int, height: int, fps: float = 30.0, ext: str = '.mp4') -> bool:
    """
    Test if the codec works on the current system.

    Args:
        codec (str): Four-character codec code
        width (int): Width of test video
        height (int): Height of test video
        fps (float): Frame rate for test
        ext (str): Output container extension (e.g. '.mp4', '.avi') used
            for the temporary probe file, so the codec is validated
            against the actual target container

    Returns:
        bool: True if codec works, False otherwise
    """
    tmp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(tmp_fd)
    try:
        fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore[attr-defined]
        writer = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
        if not writer.isOpened():
            return False
        try:
            writer.write(np.zeros((height, width, 3), dtype=np.uint8))
        finally:
            writer.release()
        return os.path.exists(temp_path) and os.path.getsize(temp_path) > 0
    except Exception:
        return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def get_working_codec(output_path: str, width: int, height: int, fps: float = 30.0) -> str:
    """
    Find a working codec for the current system and output format.

    This function tries multiple codecs until it finds one that works.

    Args:
        output_path (str): Path where the video will be saved
        width (int): Width of the video
        height (int): Height of the video
        fps (float): Frame rate

    Returns:
        str: Working four-character codec code

    Raises:
        RuntimeError: If no compatible codec is found
    """
    ext = Path(output_path).suffix.lower()

    # Fallback codec options by extension
    fallback_codecs = {
        '.mp4': ['mp4v', 'avc1', 'H264', 'DIVX', 'X264'],
        '.avi': ['XVID', 'MJPG', 'DIVX'],
        '.mov': ['mp4v', 'avc1', 'H264'],
        '.mkv': ['X264', 'mp4v'],
        '.wmv': ['WMV2', 'WMV1']
    }

    # Candidates in priority order: the OS-specific primary codec first, then
    # the extension's fallbacks, with MJPG as a last resort that works on
    # almost all platforms. Each codec is validated at most once.
    candidates = (
        [get_compatible_codec(output_path)]
        + fallback_codecs.get(ext, ['mp4v', 'XVID', 'MJPG'])
        + ['MJPG']
    )

    tried = set()
    for codec in candidates:
        if codec in tried:
            continue
        tried.add(codec)
        if validate_codec(codec, width, height, fps, ext=ext):
            return codec

    raise RuntimeError(f"No compatible codec found for {ext} format on this system")


def create_video_writer(output_path: str, fps: float, width: int, height: int) -> cv2.VideoWriter:
    """
    Create a VideoWriter with a compatible codec.

    Args:
        output_path (str): Path where the video will be saved
        fps (float): Frames per second
        width (int): Frame width
        height (int): Frame height

    Returns:
        cv2.VideoWriter: Initialized VideoWriter object

    Raises:
        RuntimeError: If no compatible codec is found
    """
    # Try to find a working codec
    codec = get_working_codec(output_path, width, height, fps)

    # Create writer with the codec
    fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        raise RuntimeError(f"Failed to create VideoWriter with codec {codec}")

    return writer
