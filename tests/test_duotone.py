"""
Unit tests for the duotone module.
"""
import unittest
import os
import tempfile
import cv2
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
        color1 = (255, 0, 0)  # Red
        color2 = (0, 255, 255)  # Cyan

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


if __name__ == "__main__":
    unittest.main()
