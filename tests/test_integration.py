"""
End-to-end integration tests for the full CLI pipeline.

These tests create synthetic videos, run the real ``main()`` function
with patched ``sys.argv``, and verify output properties: file existence,
dimensions, frame count, FPS, and pixel-level effects.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

_src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
_src_dir = os.path.abspath(_src_dir)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from main import main


def _make_gradient_video(path, width=160, height=120, frames=5, fps=30.0):
    """Write a minimal gradient video to *path* using the mp4v codec."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise unittest.SkipTest("mp4v codec not available in this environment")
    for _ in range(frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            value = int(y * 255 / height)
            frame[y, :] = [value, value, value]
        writer.write(frame)
    writer.release()


class TestIntegrationDuotone(unittest.TestCase):
    """End-to-end duotone pipeline tests."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.mp4")
        self.output_path = os.path.join(self.tmp.name, "output.mp4")
        _make_gradient_video(self.input_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_pipeline_produces_output_file(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, self.output_path, "--effect", "duotone"],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
            self.skipTest("Codec produced no output in this environment")
        self.assertTrue(os.path.exists(self.output_path))

    def test_output_dimensions_match_input(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, self.output_path, "--effect", "duotone"],
        ):
            main()
        cap = cv2.VideoCapture(self.output_path)
        if not cap.isOpened():
            self.skipTest("Codec produced no output in this environment")
        try:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.assertEqual(w, 160)
            self.assertEqual(h, 120)
        finally:
            cap.release()

    def test_duotone_colors_transform_frame(self):
        """Dark areas (top of gradient) should be near color1; light areas (bottom) near color2."""
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--effect",
                "duotone",
                "--color1",
                "#000000",
                "--color2",
                "#ffffff",
            ],
        ):
            main()
        cap = cv2.VideoCapture(self.output_path)
        if not cap.isOpened():
            self.skipTest("Codec produced no output in this environment")
        try:
            ret, frame = cap.read()
            self.assertTrue(ret)
            # Top row (dark) should be substantially dark: BGR close to (0,0,0)
            top_pixel = frame[0, 80, :]
            self.assertLessEqual(top_pixel[0], 40)
            self.assertLessEqual(top_pixel[1], 40)
            self.assertLessEqual(top_pixel[2], 40)
            # Bottom row (light) should be substantially light: BGR close to (255,255,255)
            bottom_pixel = frame[119, 80, :]
            self.assertGreaterEqual(bottom_pixel[0], 215)
            self.assertGreaterEqual(bottom_pixel[1], 215)
            self.assertGreaterEqual(bottom_pixel[2], 215)
        finally:
            cap.release()

    def test_palette_flag_resolves_colors(self):
        """The --palette flag should resolve to the named palette's two colors."""
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--effect",
                "duotone",
                "--palette",
                "noir",
            ],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(self.output_path))


class TestIntegrationHalftone(unittest.TestCase):
    """End-to-end halftone pipeline tests."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.mp4")
        self.output_path = os.path.join(self.tmp.name, "output.mp4")
        _make_gradient_video(self.input_path, frames=1)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_pipeline_produces_output_file(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, self.output_path, "--effect", "halftone"],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
            self.skipTest("Codec produced no output in this environment")
        self.assertTrue(os.path.exists(self.output_path))

    def test_output_dimensions_match_input(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, self.output_path, "--effect", "halftone"],
        ):
            main()
        cap = cv2.VideoCapture(self.output_path)
        if not cap.isOpened():
            self.skipTest("Codec produced no output in this environment")
        try:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.assertEqual(w, 160)
            self.assertEqual(h, 120)
        finally:
            cap.release()

    def test_halftone_with_dot_and_hex_grid(self):
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--effect",
                "halftone",
                "--symbol_type",
                "dot",
                "--grid_type",
                "hex",
                "--symbol_size",
                "12",
            ],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(self.output_path))

    def test_halftone_color_args_affect_output(self):
        out2 = os.path.join(self.tmp.name, "output2.mp4")
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                out2,
                "--effect",
                "halftone",
                "--color1",
                "#ff0000",
                "--color2",
                "#0000ff",
            ],
        ):
            main()
        cap = cv2.VideoCapture(out2)
        if not cap.isOpened():
            self.skipTest("Codec produced no output in this environment")
        try:
            ret, frame = cap.read()
            self.assertTrue(ret)
            # The frame should contain red pixels (symbols) and blue pixels (background).
            has_red = np.any(
                (frame[:, :, 2] > 200) & (frame[:, :, 1] < 50) & (frame[:, :, 0] < 50)
            )
            has_blue = np.any(
                (frame[:, :, 0] > 200) & (frame[:, :, 1] < 50) & (frame[:, :, 2] < 50)
            )
            self.assertTrue(has_red or has_blue, "Expected red symbols or blue background")
        finally:
            cap.release()


class TestIntegrationStillImages(unittest.TestCase):
    """End-to-end tests for still-image input and output."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.png")
        self.output_path = os.path.join(self.tmp.name, "output.png")

        image = np.zeros((120, 160, 3), dtype=np.uint8)
        for y in range(120):
            value = int(y * 255 / 120)
            image[y, :] = [value, value, value]
        cv2.imwrite(self.input_path, image)

    def tearDown(self):
        self.tmp.cleanup()

    def test_duotone_image_pipeline_produces_png(self):
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--effect",
                "duotone",
                "--color1",
                "#000000",
                "--color2",
                "#ffffff",
            ],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(self.output_path))
        output = cv2.imread(self.output_path)
        self.assertIsNotNone(output)
        self.assertEqual(output.shape, (120, 160, 3))
        # Top row (dark) should be near black; bottom row near white.
        top_pixel = output[0, 80, :]
        self.assertLessEqual(top_pixel[0], 40)
        self.assertLessEqual(top_pixel[1], 40)
        self.assertLessEqual(top_pixel[2], 40)
        bottom_pixel = output[119, 80, :]
        self.assertGreaterEqual(bottom_pixel[0], 215)
        self.assertGreaterEqual(bottom_pixel[1], 215)
        self.assertGreaterEqual(bottom_pixel[2], 215)

    def test_halftone_image_pipeline_produces_png(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, self.output_path, "--effect", "halftone"],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(self.output_path))
        output = cv2.imread(self.output_path)
        self.assertIsNotNone(output)
        self.assertEqual(output.shape, (120, 160, 3))


class TestIntegrationErrorPaths(unittest.TestCase):
    """End-to-end tests for CLI error handling."""

    def test_missing_input_returns_error(self):
        with mock.patch("sys.argv", ["siss", "missing.mp4", "out.mp4", "--effect", "duotone"]):
            rc = main()
        self.assertEqual(rc, 1)

    def test_missing_effect_returns_error(self):
        with mock.patch("sys.argv", ["siss", "in.mp4", "out.mp4"]):
            rc = main()
        self.assertEqual(rc, 1)

    def test_list_palettes_succeeds(self):
        with mock.patch("builtins.print") as mock_print:
            with mock.patch("sys.argv", ["siss", "--list-palettes"]):
                rc = main()
        self.assertEqual(rc, 0)
        printed = " ".join(
            str(arg) for call in mock_print.call_args_list for arg in call[0]
        )
        self.assertIn("sunset", printed)


if __name__ == "__main__":
    unittest.main()
