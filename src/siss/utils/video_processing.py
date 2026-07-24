"""
Utility functions for video processing operations.

This module provides helper functions for common video operations like
loading videos and saving processed results.
"""
import cv2
import os
from tqdm import tqdm

from ..codec_fix import create_video_writer


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


def process_media(input_path, output_path, process_function, **kwargs):
    """
    Process a video or still image, chosen from the output path extension.

    Still-image extensions dispatch to process_image(), everything else to
    process_video_frames(). This is the single dispatch point used by the
    effect entry points, so callers do not repeat the extension check.

    Args:
        input_path (str): Path to the input video or image
        output_path (str): Path where the processed result will be saved
        process_function (callable): Function to apply to each frame
        **kwargs: Additional arguments to pass to the process_function
    """
    if is_image_file(output_path):
        return process_image(input_path, output_path, process_function, **kwargs)
    return process_video_frames(input_path, output_path, process_function, **kwargs)
