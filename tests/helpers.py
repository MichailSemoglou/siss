"""
Shared fixtures for the Siss test suite.

One place that builds the synthetic inputs the effect and pipeline tests
use, so the scaffolding does not drift between test files.
"""
import os
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


class _SplitViewImageTestMixin:
    """
    Mixin for split-view end-to-end tests on still images.

    Subclasses must set :attr:`effect_func` and :attr:`base_args` in
    ``setUp``.  *effect_func* is the ``apply_*`` entry point to call.
    *base_args* is a tuple of positional arguments passed after the
    input and output paths.
    """

    def _apply_effect(self, output_path, **kwargs):
        self.effect_func(self.input_path, output_path, *self.base_args, **kwargs)

    def _test_split_view_vertical(self):
        w = self.original.shape[1]
        half = w // 2
        nosplit_path = os.path.join(self.temp_dir.name, "nosplit_v.png")
        self._apply_effect(nosplit_path)
        nosplit_render = cv2.imread(nosplit_path)

        self._apply_effect(self.output_path, split_direction="vertical")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)
        np.testing.assert_array_equal(
            result[:, :half], self.original[:, :half],
            err_msg="left half should equal left half of the original image",
        )
        np.testing.assert_array_equal(
            result[:, half:], nosplit_render[:, half:],
            err_msg="right half should equal right half of the effect render",
        )

    def _test_split_view_horizontal(self):
        h = self.original.shape[0]
        half = h // 2
        nosplit_path = os.path.join(self.temp_dir.name, "nosplit_h.png")
        self._apply_effect(nosplit_path)
        nosplit_render = cv2.imread(nosplit_path)

        self._apply_effect(self.output_path, split_direction="horizontal")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)
        np.testing.assert_array_equal(
            result[:half, :], self.original[:half, :],
            err_msg="top half should equal top half of the original image",
        )
        np.testing.assert_array_equal(
            result[half:, :], nosplit_render[half:, :],
            err_msg="bottom half should equal bottom half of the effect render",
        )

    def _test_no_split_preserves_dimensions(self):
        self._apply_effect(self.output_path)
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)
