"""
Unit tests for the halftone module.
"""
import os
import tempfile
import unittest

import cv2
import numpy as np

from siss.halftone import apply_halftone, apply_halftone_image
from tests.helpers import _SplitViewImageTestMixin, make_gradient_image, make_test_video


class TestHalftone(unittest.TestCase):
    """Tests for the halftone effect functions."""

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

    def test_apply_halftone_basic(self):
        """Test basic halftone effect application."""
        # Skip test if codec not available
        try:
            # Test with basic settings
            color1 = (0, 0, 0)
            color2 = (255, 255, 255)
            symbol_size = 8

            apply_halftone(self.input_path, self.output_path, symbol_size, color1, color2)

            # Verify the output exists
            self.assertTrue(os.path.exists(self.output_path))

            # Verify the output has correct content
            cap = cv2.VideoCapture(self.output_path)
            self.assertTrue(cap.isOpened())

            # Read the first frame and check dimensions
            ret, frame = cap.read()
            self.assertTrue(ret)

            # Check frame dimensions
            self.assertEqual(frame.shape[1], 320)  # Width
            self.assertEqual(frame.shape[0], 240)  # Height

            # Close video
            cap.release()
        except cv2.error:
            self.skipTest("Codec not available")

    def test_dual_halftone_video_full_canvas_dimensions(self):
        """Full-canvas split video output preserves the doubled width."""
        try:
            output_path = os.path.join(self.temp_dir.name, "full_canvas.mp4")
            apply_halftone(
                self.input_path,
                output_path,
                8,
                (0, 0, 0),
                (255, 255, 255),
                alt_color1_rgb=(255, 0, 0),
                alt_color2_rgb=(0, 0, 0),
                split_direction="vertical-full",
                no_audio=True,
            )

            cap = cv2.VideoCapture(output_path)
            self.assertTrue(cap.isOpened())
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[1], 640)
            self.assertEqual(frame.shape[0], 240)
            cap.release()
        except cv2.error:
            self.skipTest("Codec not available")

    def test_symbol_types(self):
        """Test different symbol types."""
        # Skip test if codec not available
        try:
            symbol_types = ['plus', 'asterisk', 'slash', 'dot', 'ring']

            for symbol_type in symbol_types:
                output_path = os.path.join(self.temp_dir.name, f"test_{symbol_type}.mp4")

                apply_halftone(
                    self.input_path,
                    output_path,
                    symbol_size=8,
                    color1_rgb=(0, 0, 0),
                    color2_rgb=(255, 255, 255),
                    symbol_type=symbol_type
                )

                # Verify the output exists
                self.assertTrue(os.path.exists(output_path))
        except cv2.error:
            self.skipTest("Codec not available")

    def test_grid_types(self):
        """Test square and hex grid layouts."""
        # Skip test if codec not available
        try:
            for grid_type in ['square', 'hex']:
                output_path = os.path.join(self.temp_dir.name, f"test_grid_{grid_type}.mp4")

                apply_halftone(
                    self.input_path,
                    output_path,
                    symbol_size=8,
                    color1_rgb=(0, 0, 0),
                    color2_rgb=(255, 255, 255),
                    symbol_type='dot',
                    grid_type=grid_type
                )

                # Verify the output exists
                self.assertTrue(os.path.exists(output_path))
        except cv2.error:
            self.skipTest("Codec not available")

    def test_invalid_inputs(self):
        """Test error handling for invalid inputs."""
        # Test with non-existent input file
        with self.assertRaises(FileNotFoundError):
            apply_halftone("nonexistent.mp4", self.output_path, 10, (0, 0, 0), (255, 255, 255))

        # Test with invalid colors
        with self.assertRaises(ValueError):
            apply_halftone(self.input_path, self.output_path, 10, (300, 0, 0), (255, 255, 255))

        # Test with invalid symbol type
        with self.assertRaises(ValueError):
            apply_halftone(self.input_path, self.output_path, 10, (0, 0, 0), (255, 255, 255), symbol_type='invalid_type')

        # Test with invalid grid type
        with self.assertRaises(ValueError):
            apply_halftone(
                self.input_path, self.output_path, 10, (0, 0, 0), (255, 255, 255),
                grid_type='invalid_grid'
            )

        # Test with invalid symbol size
        with self.assertRaises(ValueError):
            apply_halftone(self.input_path, self.output_path, 0, (0, 0, 0), (255, 255, 255))


    def test_invalid_gamma_values_raise(self):
        """Direct halftone calls should reject booleans and non-finite gamma values."""
        for gamma in (True, float("inf"), float("nan"), 0, -1.0):
            with self.assertRaises(ValueError):
                apply_halftone(
                    self.input_path,
                    self.output_path,
                    10,
                    (0, 0, 0),
                    (255, 255, 255),
                    gamma=gamma,
                )

    def test_negative_symbol_size_raises(self):
        """Negative symbol_size should raise ValueError, not silently produce invalid output."""
        with self.assertRaises(ValueError):
            apply_halftone(self.input_path, self.output_path,
                           -5, (0, 0, 0), (255, 255, 255))


class TestHalftoneSplitView(unittest.TestCase, _SplitViewImageTestMixin):
    """End-to-end tests for halftone with --split-view."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "input.png")
        self.output_path = os.path.join(self.temp_dir.name, "output.png")
        h, w = 60, 80
        self.original = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
        cv2.imwrite(self.input_path, self.original)
        self.effect_func = apply_halftone
        self.base_args = (10, (0, 0, 0), (255, 255, 255))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_view_vertical_doubles_width(self):
        self._test_split_view_vertical()

    def test_split_view_horizontal_doubles_height(self):
        self._test_split_view_horizontal()

    def test_no_split_preserves_dimensions(self):
        self._test_no_split_preserves_dimensions()


class TestHalftoneImage(unittest.TestCase):
    """Tests for the still-image halftone path."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "test_input.png")
        self.output_path = os.path.join(self.temp_dir.name, "test_output.png")

        # Create a simple gradient image
        make_gradient_image(self.input_path, width=320, height=240)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_apply_halftone_image_basic(self):
        """Test basic halftone effect on a still image."""
        color1 = (0, 0, 0)  # Black
        color2 = (255, 255, 255)  # White
        symbol_size = 8

        apply_halftone_image(self.input_path, self.output_path, symbol_size, color1, color2)

        self.assertTrue(os.path.exists(self.output_path))

        output_image = cv2.imread(self.output_path)
        self.assertIsNotNone(output_image)
        self.assertEqual(output_image.shape[1], 320)  # Width
        self.assertEqual(output_image.shape[0], 240)  # Height

    def test_solid_white_frame_renders_no_symbols(self):
        """A fully white frame has zero luminance-driven sizes: background only."""
        cv2.imwrite(self.input_path, np.full((120, 160, 3), 255, dtype=np.uint8))

        for symbol_type in ('plus', 'asterisk', 'slash', 'dot', 'ring'):
            for grid_type in ('square', 'hex'):
                apply_halftone_image(
                    self.input_path, self.output_path, 10,
                    (0, 0, 0), (255, 200, 100),
                    symbol_type=symbol_type, grid_type=grid_type,
                )
                output = cv2.imread(self.output_path)
                # Background color in BGR, as written by the renderer.
                expected = np.full((120, 160, 3), (100, 200, 255), dtype=np.uint8)
                np.testing.assert_array_equal(output, expected)

    def test_solid_black_frame_renders_symbols(self):
        """A fully black frame gives every cell the maximum symbol size."""
        cv2.imwrite(self.input_path, np.zeros((120, 160, 3), dtype=np.uint8))

        for symbol_type in ('plus', 'asterisk', 'slash', 'dot', 'ring'):
            for grid_type in ('square', 'hex'):
                apply_halftone_image(
                    self.input_path, self.output_path, 10,
                    (0, 0, 0), (255, 255, 255),
                    symbol_type=symbol_type, grid_type=grid_type,
                )
                output = cv2.imread(self.output_path)
                # Symbol color in BGR must appear somewhere in the frame.
                self.assertTrue(np.any(np.all(output == (0, 0, 0), axis=-1)))

    def test_invalid_image_input_raises(self):
        """Test error handling for a missing input image."""
        with self.assertRaises(FileNotFoundError):
            apply_halftone_image("nonexistent.png", self.output_path, 10, (0, 0, 0), (255, 255, 255))

    def test_invalid_image_colors_raise(self):
        """Test error handling for invalid colors on the image path."""
        with self.assertRaises(ValueError):
            apply_halftone_image(self.input_path, self.output_path, 10, (300, 0, 0), (255, 255, 255))

    def test_invalid_image_symbol_type_raises(self):
        """Test error handling for invalid symbol type on the image path."""
        with self.assertRaises(ValueError):
            apply_halftone_image(self.input_path, self.output_path, 10, (0, 0, 0), (255, 255, 255), symbol_type='invalid_type')


class TestHalftoneLossMap(unittest.TestCase):
    """Tests for the loss-map feature."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "input.png")
        self.output_path = os.path.join(self.temp_dir.name, "output.png")
        self.loss_path = os.path.join(self.temp_dir.name, "loss.png")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_loss_map_tuple_return(self):
        """When loss_map=True, the processor returns a (rendered, loss_map) tuple."""
        from siss.halftone import _make_halftone_processor

        proc = _make_halftone_processor(10, (0, 0, 0), (255, 255, 255), loss_map=True)
        frame = np.random.randint(0, 256, (60, 80, 3), dtype=np.uint8)
        result = proc(frame)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        rendered, loss = result
        self.assertEqual(rendered.shape, (60, 80, 3))
        self.assertEqual(loss.shape, (60, 80))
        self.assertEqual(loss.dtype, np.uint8)

    def test_loss_map_uniform_frame_shape(self):
        """Loss map matches input dimensions and is non-negative."""
        from siss.halftone import _make_halftone_processor

        frame = np.full((60, 80, 3), 128, dtype=np.uint8)
        proc = _make_halftone_processor(50, (0, 0, 0), (255, 255, 255), loss_map=True)
        _, loss = proc(frame)
        self.assertEqual(loss.shape, (60, 80))
        self.assertTrue(np.all(loss >= 0))

    def test_loss_map_image_writes(self):
        """A loss map image is written alongside the render."""
        frame = np.random.randint(0, 256, (60, 80, 3), dtype=np.uint8)
        cv2.imwrite(self.input_path, frame)
        apply_halftone(self.input_path, self.output_path, 50, (0, 0, 0), (255, 255, 255),
                       loss_map_path=self.loss_path)
        self.assertTrue(os.path.isfile(self.output_path))
        self.assertTrue(os.path.isfile(self.loss_path))
        loss_img = cv2.imread(self.loss_path, cv2.IMREAD_GRAYSCALE)
        self.assertEqual(loss_img.shape, (60, 80))

    def test_loss_map_omitted_when_path_none(self):
        """When loss_map_path is None, no loss map file is written."""
        frame = np.random.randint(0, 256, (60, 80, 3), dtype=np.uint8)
        cv2.imwrite(self.input_path, frame)
        apply_halftone(self.input_path, self.output_path, 50, (0, 0, 0), (255, 255, 255))
        self.assertTrue(os.path.isfile(self.output_path))
        self.assertFalse(os.path.isfile(self.loss_path))

    def test_loss_map_random_noise_nonzero_loss(self):
        """A random-noise frame produces nonzero loss across cells."""
        from siss.halftone import _make_halftone_processor

        frame = np.random.randint(0, 256, (60, 80, 3), dtype=np.uint8)
        proc = _make_halftone_processor(50, (0, 0, 0), (255, 255, 255), loss_map=True)
        _, loss = proc(frame)
        self.assertTrue(np.any(loss > 0))

    def test_loss_map_hex_grid_nonzero_loss(self):
        """A hex-grid loss map still marks cells as having nonzero loss."""
        from siss.halftone import _make_halftone_processor

        frame = np.linspace(0, 255, 60 * 80 * 3, dtype=np.uint8).reshape((60, 80, 3))
        proc = _make_halftone_processor(
            10, (0, 0, 0), (255, 255, 255), loss_map=True, grid_type='hex'
        )
        _, loss = proc(frame)
        self.assertEqual(loss.shape, (60, 80))
        self.assertTrue(np.any(loss > 0))


class TestHalftoneDualSplit(unittest.TestCase):
    """Tests for split-view with dual-style processors."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "input.png")
        self.output_path = os.path.join(self.temp_dir.name, "output.png")
        frame = np.random.randint(0, 256, (60, 80, 3), dtype=np.uint8)
        cv2.imwrite(self.input_path, frame)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dual_halftone_vertical_stitch(self):
        apply_halftone(
            self.input_path, self.output_path, 20,
            (255, 0, 0), (255, 255, 255),
            alt_color1_rgb=(0, 0, 255), alt_color2_rgb=(0, 0, 0),
        )
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], 60)
        self.assertEqual(result.shape[1], 80)
        left_half = result[:, :40]
        right_half = result[:, 40:]
        self.assertTrue(np.any(np.all(left_half == (0, 0, 0), axis=-1)))
        self.assertTrue(np.any(np.all(right_half == (255, 255, 255), axis=-1)))

    def test_dual_halftone_full_canvas(self):
        apply_halftone(
            self.input_path, self.output_path, 20,
            (255, 0, 0), (255, 255, 255),
            alt_color1_rgb=(0, 255, 0), alt_color2_rgb=(255, 255, 255),
            split_direction="vertical-full",
        )
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], 60)
        self.assertEqual(result.shape[1], 160)

    def test_dual_halftone_full_canvas_video(self):
        video_path = os.path.join(self.temp_dir.name, "input.mp4")
        output_path = os.path.join(self.temp_dir.name, "output.mp4")
        make_test_video(video_path, width=80, height=60, frames=3, fps=10.0)
        try:
            apply_halftone(
                video_path, output_path, 20,
                (255, 0, 0), (255, 255, 255),
                alt_color1_rgb=(0, 255, 0), alt_color2_rgb=(255, 255, 255),
                split_direction="vertical-full",
                no_audio=True,
            )
            cap = cv2.VideoCapture(output_path)
            self.assertTrue(cap.isOpened())
            try:
                ret, frame = cap.read()
                self.assertTrue(ret)
                self.assertEqual(frame.shape[0], 60)
                self.assertEqual(frame.shape[1], 160)
            finally:
                cap.release()
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_dual_halftone_uses_alt_symbol_setting_without_alt_colors(self):
        apply_halftone(
            self.input_path, self.output_path, 20,
            (255, 0, 0), (255, 255, 255),
            alt_symbol_type="ring",
            split_direction="vertical-full",
        )
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], 60)
        self.assertEqual(result.shape[1], 160)


if __name__ == "__main__":
    unittest.main()
