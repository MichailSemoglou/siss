"""
Shared fixtures for the Siss test suite.

One place that builds the synthetic inputs the effect and pipeline tests
use, so the scaffolding does not drift between test files.
"""
import unittest

import cv2
import numpy as np


def make_gradient_array(width=160, height=120):
    """Return a vertical black-to-white gradient as a BGR uint8 array."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        value = int(y * 255 / height)
        frame[y, :] = [value, value, value]
    return frame


def make_test_video(path, width=160, height=120, frames=5, fps=30.0,
                    gradient=False):
    """
    Write a minimal test video to *path* using the mp4v codec.

    Frames are solid black by default, or a vertical black-to-white
    gradient when *gradient* is True.

    Raises unittest.SkipTest if the writer cannot be opened, so tests skip
    gracefully in environments where mp4v or the target container is
    unavailable.
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise unittest.SkipTest("mp4v codec not available in this environment")
    for _ in range(frames):
        if gradient:
            writer.write(make_gradient_array(width, height))
        else:
            writer.write(np.zeros((height, width, 3), dtype=np.uint8))
    writer.release()


def make_gradient_image(path, width=160, height=120):
    """Write a vertical black-to-white gradient image to *path*."""
    cv2.imwrite(path, make_gradient_array(width, height))
