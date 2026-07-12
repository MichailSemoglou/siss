"""
Unit tests for the halftone module.
"""
import unittest
import os
import tempfile
import numpy as np
import cv2
from halftone import apply_halftone, apply_halftone_image


class TestHalftone(unittest.TestCase):
    """Tests for the halftone effect functions."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a small test video file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "test_input.mp4")
        self.output_path = os.path.join(self.temp_dir.name, "test_output.mp4")
        
        # Create a simple test video (10 frames, gradient color)
        width, height = 320, 240
        fps = 30
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.input_path, fourcc, fps, (width, height))
        
        # Create 10 frames
        for i in range(10):
            # Create gradient frame
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            for y in range(height):
                value = int(y * 255 / height)
                frame[y, :] = [value, value, value]
            
            out.write(frame)
        
        out.release()
    
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_apply_halftone_basic(self):
        """Test basic halftone effect application."""
        # Skip test if codec not available
        try:
            # Test with basic settings
            color1 = (0, 0, 0)  # Black
            color2 = (255, 255, 255)  # White
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
    
    def test_symbol_types(self):
        """Test different symbol types."""
        # Skip test if codec not available
        try:
            symbol_types = ['plus', 'asterisk', 'slash', 'dot']
            
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
            apply_halftone(self.input_path, self.output_path, 10, (0, 0, 0), (255, 255, 255), 'invalid_type')

        # Test with invalid grid type
        with self.assertRaises(ValueError):
            apply_halftone(
                self.input_path, self.output_path, 10, (0, 0, 0), (255, 255, 255),
                grid_type='invalid_grid'
            )
        
        # Test with invalid symbol size
        with self.assertRaises(ValueError):
            apply_halftone(self.input_path, self.output_path, 0, (0, 0, 0), (255, 255, 255))


class TestHalftoneImage(unittest.TestCase):
    """Tests for the still-image halftone path."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.temp_dir.name, "test_input.png")
        self.output_path = os.path.join(self.temp_dir.name, "test_output.png")

        # Create a simple gradient image
        height, width = 240, 320
        image = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            value = int(y * 255 / height)
            image[y, :] = [value, value, value]
        cv2.imwrite(self.input_path, image)

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


if __name__ == "__main__":
    unittest.main()
