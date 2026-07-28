"""
Unit tests for the duotone module.
"""
import os
import tempfile
import unittest

import cv2
import numpy as np

from siss.duotone import apply_duotone, apply_duotone_image
from tests.helpers import make_gradient_image, make_test_video


class TestDuotone(unittest.TestCase):
    """Tests for the duotone effect functions."""

    def setUp(self):
        """Set up test environment."""
        # Create a small test video file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "test_input.mp4")
        self.output_path = os.path.join(self.temp_dir.name, "test_output.mp4")

        # Create a simple test video (10 frames, gradient color)
        make_test_video(self.input_path, width=320, height=240, frames=10, gradient=True)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_apply_duotone_basic(self):
        """Test basic duotone effect application."""
        # Skip test if codec not available
        try:
            # Test with basic colors
            color1 = (255, 0, 0)  # Red
            color2 = (0, 255, 255)  # Cyan

            apply_duotone(self.input_path, self.output_path, color1, color2)

            # Verify the output exists
            self.assertTrue(os.path.exists(self.output_path))

            # Verify the output has correct content
            cap = cv2.VideoCapture(self.output_path)
            self.assertTrue(cap.isOpened())

            # Read the first frame and check colors
            ret, frame = cap.read()
            self.assertTrue(ret)

            # Check frame dimensions
            self.assertEqual(frame.shape[1], 320)  # Width
            self.assertEqual(frame.shape[0], 240)  # Height

            # Close video
            cap.release()
        except cv2.error:
            self.skipTest("Codec not available")

    def test_invalid_inputs(self):
        """Test error handling for invalid inputs."""
        # Test with non-existent input file
        with self.assertRaises(FileNotFoundError):
            apply_duotone("nonexistent.mp4", self.output_path, (255, 0, 0), (0, 255, 255))

        # Test with invalid colors
        with self.assertRaises(ValueError):
            apply_duotone(self.input_path, self.output_path, (300, 0, 0), (0, 255, 255))

        with self.assertRaises(ValueError):
            apply_duotone(self.input_path, self.output_path, (255, 0, 0), (-10, 255, 255))


class TestDuotoneImage(unittest.TestCase):
    """Tests for the still-image duotone path."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "test_input.png")
        self.output_path = os.path.join(self.temp_dir.name, "test_output.png")

        # Create a simple gradient image
        make_gradient_image(self.input_path, width=320, height=240)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_apply_duotone_image_basic(self):
        """Test basic duotone effect on a still image."""
        color1 = (255, 0, 0)
        color2 = (0, 255, 255)

        apply_duotone_image(self.input_path, self.output_path, color1, color2)

        self.assertTrue(os.path.exists(self.output_path))

        output_image = cv2.imread(self.output_path)
        self.assertIsNotNone(output_image)
        self.assertEqual(output_image.shape[1], 320)  # Width
        self.assertEqual(output_image.shape[0], 240)  # Height

    def test_invalid_image_input_raises(self):
        """Test error handling for a missing input image."""
        with self.assertRaises(FileNotFoundError):
            apply_duotone_image("nonexistent.png", self.output_path, (255, 0, 0), (0, 255, 255))

    def test_invalid_image_colors_raise(self):
        """Test error handling for invalid colors on the image path."""
        with self.assertRaises(ValueError):
            apply_duotone_image(self.input_path, self.output_path, (300, 0, 0), (0, 255, 255))


class TestDuotoneSplitView(unittest.TestCase):
    """End-to-end tests for duotone with --split-view."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "input.png")
        self.output_path = os.path.join(self.temp_dir.name, "output.png")
        h, w = 60, 80
        self.original = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
        cv2.imwrite(self.input_path, self.original)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_view_vertical_doubles_width(self):
        w = self.original.shape[1]
        nosplit_path = os.path.join(self.temp_dir.name, "nosplit_v.png")
        apply_duotone(self.input_path, nosplit_path, (255, 0, 0), (0, 255, 255))
        duotone_render = cv2.imread(nosplit_path)

        apply_duotone(self.input_path, self.output_path,
                      (255, 0, 0), (0, 255, 255), split_direction="vertical")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], self.original.shape[0])
        self.assertEqual(result.shape[1], self.original.shape[1] * 2)
        np.testing.assert_array_equal(
            result[:, :w], self.original,
            err_msg="left half should equal the original image",
        )
        np.testing.assert_array_equal(
            result[:, w:], duotone_render,
            err_msg="right half should equal the duotone render",
        )

    def test_split_view_horizontal_doubles_height(self):
        h = self.original.shape[0]
        nosplit_path = os.path.join(self.temp_dir.name, "nosplit_h.png")
        apply_duotone(self.input_path, nosplit_path, (255, 0, 0), (0, 255, 255))
        duotone_render = cv2.imread(nosplit_path)

        apply_duotone(self.input_path, self.output_path,
                      (255, 0, 0), (0, 255, 255), split_direction="horizontal")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], self.original.shape[0] * 2)
        self.assertEqual(result.shape[1], self.original.shape[1])
        np.testing.assert_array_equal(
            result[:h, :], self.original,
            err_msg="top half should equal the original image",
        )
        np.testing.assert_array_equal(
            result[h:, :], duotone_render,
            err_msg="bottom half should equal the duotone render",
        )

    def test_no_split_produces_same_dimensions(self):
        apply_duotone(self.input_path, self.output_path,
                       (255, 0, 0), (0, 255, 255))
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)


if __name__ == "__main__":
    unittest.main()
