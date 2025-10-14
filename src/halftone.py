"""
Module for applying halftone pattern effects to videos.
"""
import cv2
import numpy as np
import os
from tqdm import tqdm
from utils.video_processing import get_codec_for_file
from codec_fix import create_video_writer


def apply_halftone(video_path, output_path, symbol_size, color1_rgb, color2_rgb, 
                  symbol_type='plus', use_codec_fix=False):
    """
    Apply halftone pattern effect to a video.

    Args:
        video_path (str): Path to the input video file
        output_path (str): Path where the processed video will be saved
        symbol_size (int): Size of the largest symbol in the halftone effect
        color1_rgb (tuple): RGB color for symbols (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for background (r, g, b), values 0-255
        symbol_type (str): Type of symbol to use ('plus', 'asterisk', or 'slash')
        use_codec_fix (bool): Whether to use codec compatibility fix

    Raises:
        FileNotFoundError: If the input video cannot be opened
        ValueError: If the colors are not valid RGB values or invalid symbol_type
    """
    # Validate inputs
    if not all(0 <= c <= 255 for c in color1_rgb + color2_rgb):
        raise ValueError("RGB color values must be between 0 and 255")
    
    if symbol_type not in ['plus', 'asterisk', 'slash']:
        raise ValueError("Symbol type must be 'plus', 'asterisk', or 'slash'")
    
    if symbol_size <= 0:
        raise ValueError("Symbol size must be greater than 0")

    # Convert RGB to BGR for OpenCV
    background_color = color2_rgb[::-1]  # Convert RGB to BGR
    symbol_color = color1_rgb[::-1]      # Convert RGB to BGR

    # Load the video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Video not found or cannot be opened: {video_path}")

    try:
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Create video writer
        if use_codec_fix:
            out = create_video_writer(output_path, fps, width, height)
        else:
            # Define the codec based on output file extension
            codec = get_codec_for_file(output_path)
            fourcc = cv2.VideoWriter_fourcc(*codec)
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Create a dictionary of symbol drawing functions for cleaner code
        symbol_functions = {
            'plus': _draw_plus_symbol,
            'asterisk': _draw_asterisk_symbol,
            'slash': _draw_slash_symbol
        }
        
        draw_symbol = symbol_functions[symbol_type]

        # Adjust symbol_size based on video width to ensure visible symbols
        adjusted_symbol_size = min(symbol_size, width // 20)
        step = max(adjusted_symbol_size // 2, 4)

        # Process frames with progress bar
        progress_bar = tqdm(total=frame_count, desc="Processing frames")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Create a blank image for the halftone
            halftone = np.ones_like(gray) * 255

            # Create a halftone pattern with the chosen symbol
            for y in range(0, gray.shape[0], step):
                for x in range(0, gray.shape[1], step):
                    # Get pixel intensity
                    if y < gray.shape[0] and x < gray.shape[1]:
                        # Sample a small region for better averaging
                        region = gray[y:min(y+3, gray.shape[0]), x:min(x+3, gray.shape[1])]
                        intensity = np.mean(region)

                        max_size = step // 2 - 1
                        size = int(max_size * (1 - intensity / 255))

                        if size > 0 and y + step//2 < halftone.shape[0] and x + step//2 < halftone.shape[1]:
                            center_y = y + step//2
                            center_x = x + step//2
                            
                            # Draw the appropriate symbol
                            draw_symbol(halftone, center_x, center_y, size)

            # Create colored halftone image
            halftone_colored = np.zeros((halftone.shape[0], halftone.shape[1], 3), dtype=np.uint8)
            halftone_colored[:] = background_color  # Background color
            symbol_mask = halftone == 0
            halftone_colored[symbol_mask] = symbol_color  # Symbol color

            # Write the frame to the output video
            out.write(halftone_colored)
            
            # Update progress
            progress_bar.update(1)

        # Close progress bar
        progress_bar.close()
        
        print(f"Processed video saved to {output_path}")
        
    finally:
        # Release resources even if an error occurs
        cap.release()
        if 'out' in locals():
            out.release()


def _draw_plus_symbol(halftone, center_x, center_y, size):
    """Draw a plus symbol on the halftone image."""
    # Horizontal line
    y1 = center_y
    x1 = max(0, center_x - size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    cv2.line(halftone, (x1, y1), (x2, y1), 0, 1)

    # Vertical line
    x1 = center_x
    y1 = max(0, center_y - size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x1, y2), 0, 1)


def _draw_asterisk_symbol(halftone, center_x, center_y, size):
    """Draw an asterisk symbol on the halftone image."""
    # Draw plus symbol first
    _draw_plus_symbol(halftone, center_x, center_y, size)

    # Add diagonal lines
    # Diagonal: top-left to bottom-right
    x1 = max(0, center_x - size)
    y1 = max(0, center_y - size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)

    # Diagonal: top-right to bottom-left
    x1 = min(halftone.shape[1] - 1, center_x + size)
    y1 = max(0, center_y - size)
    x2 = max(0, center_x - size)
    y2 = min(halftone.shape[0] - 1, center_y + size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)


def _draw_slash_symbol(halftone, center_x, center_y, size):
    """Draw a slash symbol on the halftone image."""
    # Diagonal line (/)
    x1 = max(0, center_x - size)
    y1 = min(halftone.shape[0] - 1, center_y + size)
    x2 = min(halftone.shape[1] - 1, center_x + size)
    y2 = max(0, center_y - size)
    cv2.line(halftone, (x1, y1), (x2, y2), 0, 1)
