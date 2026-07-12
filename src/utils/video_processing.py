"""
Utility functions for video processing operations.

This module provides helper functions for common video operations like
loading videos, extracting frames, and saving processed results.
"""
import cv2
import numpy as np
import os
from tqdm import tqdm

from codec_fix import create_video_writer


def load_video(video_path):
    """
    Load a video file and return a VideoCapture object.

    Args:
        video_path (str): Path to the video file

    Returns:
        cv2.VideoCapture: OpenCV VideoCapture object

    Raises:
        FileNotFoundError: If the video file cannot be opened
    """
    video_capture = cv2.VideoCapture(video_path)
    if not video_capture.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")
    return video_capture


def get_video_properties(video_capture):
    """
    Get properties of a video.

    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object

    Returns:
        dict: Dictionary with video properties (fps, width, height, frame_count)
    """
    return {
        'fps': video_capture.get(cv2.CAP_PROP_FPS),
        'width': int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'frame_count': int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT)),
    }


def extract_frames(video_capture, show_progress=True):
    """
    Extract all frames from a video.

    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object
        show_progress (bool): Whether to show a progress bar

    Returns:
        list: List of frames as numpy arrays
    """
    frames = []
    frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

    if show_progress:
        progress_bar = tqdm(total=frame_count, desc="Extracting frames")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        frames.append(frame)

        if show_progress:
            progress_bar.update(1)

    if show_progress:
        progress_bar.close()

    return frames


def save_video(output_path, frames, fps, show_progress=True):
    """
    Save a list of frames as a video file.

    Args:
        output_path (str): Path where the video will be saved
        frames (list): List of frames as numpy arrays
        fps (float): Frames per second for the output video
        show_progress (bool): Whether to show a progress bar

    Raises:
        ValueError: If no frames are provided
    """
    if not frames:
        raise ValueError("No frames to save.")

    height, width, _ = frames[0].shape
    video_writer = create_video_writer(output_path, fps, width, height)

    progress_bar = tqdm(total=len(frames), desc="Saving video") if show_progress else None

    try:
        for frame in frames:
            video_writer.write(frame)
            if progress_bar is not None:
                progress_bar.update(1)
    finally:
        if progress_bar is not None:
            progress_bar.close()
        video_writer.release()

    print(f"Video saved to {output_path}")


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


def is_image_file(file_path):
    """
    Return True if *file_path* has a still-image extension.

    The check is case-insensitive and covers the formats OpenCV's
    ``cv2.imread``/``cv2.imwrite`` commonly handle.
    """
    return os.path.splitext(file_path)[1].lower() in IMAGE_EXTENSIONS


def process_image(image_path, output_path, process_function, **kwargs):
    """
    Process a still image by applying a function to it.

    Args:
        image_path (str): Path to the input image
        output_path (str): Path where the processed image will be saved
        process_function (callable): Function to apply to the image
            The function should take a frame and return a processed frame
        **kwargs: Additional arguments to pass to the process_function

    Raises:
        FileNotFoundError: If the image file cannot be opened

    Example:
        def grayscale(frame):
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        process_image('input.png', 'output.png', grayscale)
    """
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Cannot open image file: {image_path}")

    processed_frame = process_function(frame, **kwargs)
    success = cv2.imwrite(output_path, processed_frame)
    if not success:
        raise RuntimeError(f"Failed to write image file: {output_path}")
    print(f"Processed image saved to {output_path}")


def process_video_frames(video_path, output_path, process_function, **kwargs):
    """
    Process a video by applying a function to each frame.

    Args:
        video_path (str): Path to the input video
        output_path (str): Path where processed video will be saved
        process_function (callable): Function to apply to each frame
            The function should take a frame and return a processed frame
        **kwargs: Additional arguments to pass to the process_function

    Example:
        def grayscale(frame):
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        process_video_frames('input.mp4', 'output.mp4', grayscale)
    """
    cap = load_video(video_path)

    try:
        props = get_video_properties(cap)
        out = create_video_writer(
            output_path, props['fps'], props['width'], props['height']
        )

        progress_bar = tqdm(total=props['frame_count'], desc="Processing frames")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                processed_frame = process_function(frame, **kwargs)
                out.write(processed_frame)
                progress_bar.update(1)
        finally:
            progress_bar.close()

        print(f"Processed video saved to {output_path}")

    finally:
        cap.release()
        if 'out' in locals():
            out.release()


def release_resources(video_capture, video_writer=None):
    """
    Release video resources.

    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object
        video_writer (cv2.VideoWriter, optional): OpenCV VideoWriter object
    """
    if video_capture is not None:
        video_capture.release()

    if video_writer is not None:
        video_writer.release()
