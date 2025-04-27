"""
Module for applying duotone color effects to videos.
"""
import cv2
import numpy as np
import os
from tqdm import tqdm
from src.utils.video_processing import get_codec_for_file
from src.codec_fix import create_video_writer


def apply_duotone(video_path, output_path, color1_rgb, color2_rgb, use_codec_fix=False):
    """
    Apply duotone color effect to a video.

    Args:
        video_path (str): Path to the input video file
        output_path (str): Path where the processed video will be saved
        color1_rgb (tuple): RGB color for dark areas (r, g, b), values 0-255
        color2_rgb (tuple): RGB color for light areas (r, g, b), values 0-255
        use_codec_fix (bool): Whether to use codec compatibility fix

    Raises:
        FileNotFoundError: If the input video cannot be opened
        ValueError: If the colors are not valid RGB values
    """
    # Validate color inputs
    for color in [color1_rgb, color2_rgb]:
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("RGB color values must be between 0 and 255")

    # Convert RGB colors to BGR for OpenCV
    color1 = color1_rgb[::-1]
    color2 = color2_rgb[::-1]

    # Open the video
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

        # Process frames with progress bar
        progress_bar = tqdm(total=frame_count, desc="Processing frames")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Create a blank RGB image
            duotone = np.zeros((height, width, 3), dtype=np.uint8)

            # Normalize the grayscale image to range 0-1
            normalized = gray.astype(float) / 255.0

            # For each pixel, interpolate between color1 and color2 based on intensity
            for i in range(3):  # For each color channel (BGR)
                duotone[:, :, i] = (1 - normalized) * color1[i] + normalized * color2[i]

            # Convert to uint8
            duotone = duotone.astype(np.uint8)

            # Write the frame to the output video
            out.write(duotone)
            
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
